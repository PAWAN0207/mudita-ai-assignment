
"""Gmail API integration for the Mudita AI Sales Assistant."""

import base64
import json
import os
from pathlib import Path
from typing import Any

import streamlit as st
from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


BASE_DIR = Path(__file__).resolve().parent.parent
CREDENTIALS_FILE = BASE_DIR / "credentials.json"
GMAIL_TOKEN_FILE = BASE_DIR / "gmail_token.json"

# Gmail remains strictly read-only.
GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
]


class GmailConnectionError(RuntimeError):
    """Raised when Gmail authorization or API access fails."""


def _get_secret(name: str, default=None):
    """Read a value from Streamlit Secrets or environment variables."""

    try:
        value = st.secrets.get(name)
        if value not in (None, ""):
            return value
    except Exception:
        # Streamlit Secrets may not be configured during local execution.
        pass

    return os.getenv(name, default)


def _get_gmail_credentials() -> Credentials:
    """Load Gmail credentials from Cloud Secrets or the local token file."""

    credentials = None

    # Preferred cloud configuration: authorized-user token JSON in Secrets.
    token_json = _get_secret("GMAIL_TOKEN_JSON")

    if token_json:
        try:
            if isinstance(token_json, str):
                token_data = json.loads(token_json)
            else:
                token_data = dict(token_json)

            credentials = Credentials.from_authorized_user_info(
                token_data,
                GMAIL_SCOPES,
            )
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            raise GmailConnectionError(
                "GMAIL_TOKEN_JSON is invalid. "
                "Configure a valid authorized-user token in Streamlit Secrets."
            ) from exc

    # Local development fallback.
    if credentials is None and GMAIL_TOKEN_FILE.exists():
        try:
            credentials = Credentials.from_authorized_user_file(
                str(GMAIL_TOKEN_FILE),
                GMAIL_SCOPES,
            )
        except (ValueError, OSError) as exc:
            raise GmailConnectionError(
                "The local Gmail token file could not be read."
            ) from exc

    if credentials is None:
        raise GmailConnectionError(
            "Gmail credentials are unavailable. Configure GMAIL_TOKEN_JSON "
            "in Streamlit Secrets or provide a valid local gmail_token.json."
        )

    if credentials.expired and credentials.refresh_token:
        try:
            credentials.refresh(Request())
        except RefreshError as exc:
            raise GmailConnectionError(
                "Gmail authorization has expired or been revoked. "
                "Generate a fresh authorized-user token."
            ) from exc

        # Persist refreshed credentials locally when possible.
        if GMAIL_TOKEN_FILE.exists() and not _get_secret("GMAIL_TOKEN_JSON"):
            GMAIL_TOKEN_FILE.write_text(
                credentials.to_json(),
                encoding="utf-8",
            )

    if not credentials.valid:
        raise GmailConnectionError(
            "Gmail credentials are invalid. Reauthorize the Gmail account."
        )

    return credentials


def get_gmail_service():
    """Authorize Gmail and return a Gmail API service."""

    credentials = _get_gmail_credentials()

    return build(
        "gmail",
        "v1",
        credentials=credentials,
        cache_discovery=False,
    )


def test_gmail_connection() -> dict[str, Any]:
    """Verify the authorized Gmail account."""

    try:
        service = get_gmail_service()
        profile = service.users().getProfile(userId="me").execute()

        return {
            "status": "connected",
            "email": profile.get("emailAddress"),
            "messages_total": profile.get("messagesTotal", 0),
            "threads_total": profile.get("threadsTotal", 0),
        }

    except GmailConnectionError:
        raise
    except HttpError as exc:
        status_code = getattr(exc.resp, "status", "unknown")
        raise GmailConnectionError(
            f"Gmail API request failed (HTTP {status_code}). "
            "Check Gmail API access and OAuth permissions."
        ) from exc


def list_recent_emails(max_results: int = 10) -> list[dict[str, Any]]:
    """Fetch recent inbox emails and return basic message details."""

    if not 1 <= max_results <= 50:
        raise ValueError("max_results must be between 1 and 50.")

    try:
        service = get_gmail_service()

        response = (
            service.users()
            .messages()
            .list(
                userId="me",
                labelIds=["INBOX"],
                maxResults=max_results,
            )
            .execute()
        )

        emails = []

        for item in response.get("messages", []):
            message = (
                service.users()
                .messages()
                .get(
                    userId="me",
                    id=item["id"],
                    format="metadata",
                    metadataHeaders=["From", "To", "Subject", "Date"],
                )
                .execute()
            )

            headers = {
                header["name"].lower(): header["value"]
                for header in message.get("payload", {}).get("headers", [])
            }

            emails.append(
                {
                    "id": message.get("id"),
                    "thread_id": message.get("threadId"),
                    "from": headers.get("from", ""),
                    "to": headers.get("to", ""),
                    "subject": headers.get("subject", "(No subject)"),
                    "date": headers.get("date", ""),
                    "snippet": message.get("snippet", ""),
                }
            )

        return emails

    except GmailConnectionError:
        raise
    except HttpError as exc:
        status_code = getattr(exc.resp, "status", "unknown")
        raise GmailConnectionError(
            f"Could not read Gmail inbox (HTTP {status_code})."
        ) from exc


def get_email_details(message_id: str) -> dict[str, Any]:
    """Fetch readable email content without modifying the message."""

    if not message_id or not isinstance(message_id, str):
        raise ValueError("A valid Gmail message ID is required.")

    try:
        service = get_gmail_service()

        message = (
            service.users()
            .messages()
            .get(
                userId="me",
                id=message_id,
                format="full",
            )
            .execute()
        )

        payload = message.get("payload", {})
        headers = {
            header["name"].lower(): header["value"]
            for header in payload.get("headers", [])
        }

        text_parts = []

        def extract_text(part):
            mime_type = part.get("mimeType", "")
            body = part.get("body", {})
            data = body.get("data")

            if mime_type == "text/plain" and data:
                decoded = base64.urlsafe_b64decode(
                    data + "=" * (-len(data) % 4)
                )
                text_parts.append(
                    decoded.decode("utf-8", errors="replace")
                )

            for child in part.get("parts", []):
                extract_text(child)

        extract_text(payload)

        body_text = "\n".join(text_parts).strip()

        if not body_text:
            body_text = message.get("snippet", "")

        return {
            "id": message.get("id"),
            "thread_id": message.get("threadId"),
            "from": headers.get("from", ""),
            "to": headers.get("to", ""),
            "subject": headers.get("subject", "(No subject)"),
            "date": headers.get("date", ""),
            "body": body_text,
        }

    except GmailConnectionError:
        raise
    except HttpError as exc:
        status_code = getattr(exc.resp, "status", "unknown")
        raise GmailConnectionError(
            f"Could not read email details (HTTP {status_code})."
        ) from exc
