
"""Gmail API integration for the Mudita AI Sales Assistant."""

from pathlib import Path
from typing import Any

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


BASE_DIR = Path(__file__).resolve().parent.parent
CREDENTIALS_FILE = BASE_DIR / "credentials.json"
GMAIL_TOKEN_FILE = BASE_DIR / "gmail_token.json"

# Read-only access: the app can read email but cannot send, delete,
# or modify messages.
GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
]


class GmailConnectionError(RuntimeError):
    """Raised when Gmail authorization or API access fails."""


def get_gmail_service():
    """Authorize Gmail and return a Gmail API service."""

    credentials = None

    if GMAIL_TOKEN_FILE.exists():
        try:
            credentials = Credentials.from_authorized_user_file(
                str(GMAIL_TOKEN_FILE),
                GMAIL_SCOPES,
            )
        except (ValueError, OSError) as exc:
            raise GmailConnectionError(
                "The Gmail token file could not be read. "
                "Check the local OAuth setup."
            ) from exc

    if credentials and credentials.expired and credentials.refresh_token:
        try:
            credentials.refresh(Request())
        except RefreshError as exc:
            raise GmailConnectionError(
                "Gmail authorization has expired or been revoked. "
                "Reconnect Gmail using the authorization flow."
            ) from exc

    if not credentials or not credentials.valid:
        if not CREDENTIALS_FILE.exists():
            raise GmailConnectionError(
                "credentials.json was not found in the project root."
            )

        flow = InstalledAppFlow.from_client_secrets_file(
            str(CREDENTIALS_FILE),
            GMAIL_SCOPES,
        )

        credentials = flow.run_local_server(port=0)

    GMAIL_TOKEN_FILE.write_text(
        credentials.to_json(),
        encoding="utf-8",
    )

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
            "Check API access and OAuth permissions."
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
                    metadataHeaders=[
                        "From",
                        "To",
                        "Subject",
                        "Date",
                    ],
                )
                .execute()
            )

            headers = {
                header["name"].lower(): header["value"]
                for header in message.get("payload", {}).get(
                    "headers", []
                )
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
            f"Could not read Gmail inbox (HTTP {status_code}). "
            "Check the Gmail API and authorization permissions."
        ) from exc

def get_email_details(message_id: str) -> dict[str, Any]:
    """Fetch the full readable content of one Gmail message.

    The Gmail integration remains read-only.
    """

    import base64
    from email.utils import parsedate_to_datetime

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

