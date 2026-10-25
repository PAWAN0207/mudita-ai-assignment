
"""Google Calendar integration for the Mudita AI Sales Assistant."""

import hashlib
import json
import os
from datetime import date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import streamlit as st
from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from assignment1_sales.policy import get_default_policy


BASE_DIR = Path(__file__).resolve().parent.parent
TOKEN_FILE = BASE_DIR / "token.json"

TIMEZONE_NAME = "Asia/Kolkata"
TIMEZONE = ZoneInfo(TIMEZONE_NAME)

SCOPES = ["https://www.googleapis.com/auth/calendar"]


def _get_secret(name: str, default=None):
    """Read a value from Streamlit Secrets or environment variables."""

    try:
        value = st.secrets.get(name)
        if value not in (None, ""):
            return value
    except Exception:
        pass

    return os.getenv(name, default)


def get_calendar_service():
    """Authenticate and return the Google Calendar API service."""

    credentials = None

    # Preferred cloud configuration: authorized-user token JSON in Secrets.
    token_json = _get_secret("CALENDAR_TOKEN_JSON")

    if token_json:
        try:
            if isinstance(token_json, str):
                token_data = json.loads(token_json)
            else:
                token_data = dict(token_json)

            credentials = Credentials.from_authorized_user_info(
                token_data,
                SCOPES,
            )
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            raise RuntimeError(
                "CALENDAR_TOKEN_JSON is invalid. "
                "Configure a valid authorized-user token in Streamlit Secrets."
            ) from exc

    # Local development fallback.
    if credentials is None and TOKEN_FILE.exists():
        try:
            credentials = Credentials.from_authorized_user_file(
                str(TOKEN_FILE),
                SCOPES,
            )
        except (ValueError, OSError) as exc:
            raise RuntimeError(
                "The local Calendar token file could not be read."
            ) from exc

    if credentials is None:
        raise RuntimeError(
            "Calendar credentials are unavailable. Configure "
            "CALENDAR_TOKEN_JSON in Streamlit Secrets or provide "
            "a valid local token.json."
        )

    if credentials.expired and credentials.refresh_token:
        try:
            credentials.refresh(Request())
        except RefreshError as exc:
            raise RuntimeError(
                "Google Calendar authorization has expired or been revoked. "
                "Generate a fresh authorized-user token."
            ) from exc

        # Persist refreshed credentials locally when possible.
        if TOKEN_FILE.exists() and not _get_secret("CALENDAR_TOKEN_JSON"):
            TOKEN_FILE.write_text(
                credentials.to_json(),
                encoding="utf-8",
            )

    if not credentials.valid:
        raise RuntimeError(
            "Google Calendar credentials are invalid. "
            "Reauthorize the Calendar account."
        )

    return build(
        "calendar",
        "v3",
        credentials=credentials,
        cache_discovery=False,
    )


def parse_calendar_datetime(value):
    """Parse a timezone-aware datetime and convert it to Asia/Kolkata."""

    if isinstance(value, datetime):
        parsed = value
    else:
        value = str(value).strip()

        if value.endswith("Z"):
            value = value[:-1] + "+00:00"

        parsed = datetime.fromisoformat(value)

    if parsed.tzinfo is None:
        raise ValueError(
            "Datetime must include a timezone. "
            "Example: 2026-10-25T10:00:00+05:30"
        )

    return parsed.astimezone(TIMEZONE)


def _parse_customer_start_time(value):
    """Parse a requested booking start time; timezone is required."""

    return parse_calendar_datetime(value)


def _parse_date(date_text):
    """Accept a date object or YYYY-MM-DD string."""

    if isinstance(date_text, datetime):
        return date_text.date()

    if isinstance(date_text, date):
        return date_text

    return date.fromisoformat(str(date_text))


def list_upcoming_events(max_results=10):
    """Return upcoming events from the primary Google Calendar."""

    if max_results < 1:
        raise ValueError("max_results must be at least 1.")

    service = get_calendar_service()
    now = datetime.now(TIMEZONE)

    response = (
        service.events()
        .list(
            calendarId="primary",
            timeMin=now.isoformat(),
            maxResults=max_results,
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )

    events = []

    for event in response.get("items", []):
        start_info = event.get("start", {})
        end_info = event.get("end", {})

        events.append(
            {
                "id": event.get("id"),
                "summary": event.get("summary", "(No title)"),
                "start": start_info.get("dateTime", start_info.get("date")),
                "end": end_info.get("dateTime", end_info.get("date")),
                "htmlLink": event.get("htmlLink"),
            }
        )

    return events


def find_available_slots(
    date_text,
    start_hour=10,
    end_hour=18,
    duration_minutes=30,
):
    """Find future, non-overlapping slots on a requested date."""

    requested_date = _parse_date(date_text)

    if not 0 <= start_hour < 24:
        raise ValueError("start_hour must be between 0 and 23.")

    if not 1 <= end_hour <= 24:
        raise ValueError("end_hour must be between 1 and 24.")

    if start_hour >= end_hour:
        raise ValueError("start_hour must be earlier than end_hour.")

    if duration_minutes <= 0:
        raise ValueError("duration_minutes must be positive.")

    service = get_calendar_service()

    day_start = datetime.combine(
        requested_date,
        time(start_hour, 0),
        tzinfo=TIMEZONE,
    )

    day_end = datetime.combine(
        requested_date,
        time.min,
        tzinfo=TIMEZONE,
    ) + timedelta(days=1)

    response = (
        service.events()
        .list(
            calendarId="primary",
            timeMin=day_start.isoformat(),
            timeMax=day_end.isoformat(),
            singleEvents=True,
            orderBy="startTime",
            maxResults=2500,
        )
        .execute()
    )

    busy_intervals = []

    for event in response.get("items", []):
        start_info = event.get("start", {})
        end_info = event.get("end", {})

        event_start_value = start_info.get(
            "dateTime",
            start_info.get("date"),
        )
        event_end_value = end_info.get(
            "dateTime",
            end_info.get("date"),
        )

        if not event_start_value or not event_end_value:
            continue

        if "dateTime" in start_info:
            event_start = parse_calendar_datetime(event_start_value)
        else:
            event_start = datetime.combine(
                date.fromisoformat(event_start_value),
                time.min,
                tzinfo=TIMEZONE,
            )

        if "dateTime" in end_info:
            event_end = parse_calendar_datetime(event_end_value)
        else:
            event_end = datetime.combine(
                date.fromisoformat(event_end_value),
                time.min,
                tzinfo=TIMEZONE,
            )

        busy_intervals.append((event_start, event_end))

    available_slots = []
    current_slot = day_start

    working_day_end = datetime.combine(
        requested_date,
        time.min,
        tzinfo=TIMEZONE,
    ) + timedelta(hours=end_hour)

    now = datetime.now(TIMEZONE)

    while (
        current_slot + timedelta(minutes=duration_minutes)
        <= working_day_end
    ):
        slot_end = current_slot + timedelta(minutes=duration_minutes)

        if current_slot > now:
            overlaps = any(
                current_slot < busy_end and slot_end > busy_start
                for busy_start, busy_end in busy_intervals
            )

            if not overlaps:
                available_slots.append(
                    {
                        "start": current_slot.isoformat(),
                        "end": slot_end.isoformat(),
                    }
                )

        current_slot += timedelta(minutes=duration_minutes)

    return available_slots


def create_calendar_booking(
    customer_name,
    customer_email,
    service_name,
    start_time,
    customer_confirmed=False,
    duration_minutes=30,
):
    """Create a booking only after explicit customer confirmation."""

    if customer_confirmed is not True:
        raise ValueError(
            "Booking rejected: explicit customer confirmation "
            "is required before creating a calendar event."
        )

    customer_name = str(customer_name).strip()
    customer_email = str(customer_email).strip().lower()
    service_name = str(service_name).strip()

    if not customer_name:
        raise ValueError("Customer name is required.")

    if (
        not customer_email
        or "@" not in customer_email
        or customer_email.startswith("@")
        or customer_email.endswith("@")
    ):
        raise ValueError("A valid customer email is required.")

    if not service_name:
        raise ValueError("Service name is required.")

    if duration_minutes <= 0:
        raise ValueError("duration_minutes must be positive.")

    start = _parse_customer_start_time(start_time)
    now = datetime.now(TIMEZONE)

    if start <= now:
        raise ValueError(
            "Booking rejected: appointment must be in the future."
        )

    policy = get_default_policy()
    working_hours = policy["working_hours"]

    allowed_days = {
        day.lower() for day in working_hours["days"]
    }

    if start.strftime("%A").lower() not in allowed_days:
        raise ValueError(
            "Booking rejected: appointments are only allowed "
            "Monday through Friday."
        )

    opening_time = time.fromisoformat(working_hours["start"])
    closing_time = time.fromisoformat(working_hours["end"])
    start_clock = start.time().replace(tzinfo=None)

    if not opening_time <= start_clock < closing_time:
        raise ValueError(
            "Booking rejected: appointment must start within "
            f"working hours ({working_hours['start']}–"
            f"{working_hours['end']} {TIMEZONE_NAME})."
        )

    policy_duration = working_hours["meeting_duration_minutes"]

    if duration_minutes != policy_duration:
        raise ValueError(
            "Booking rejected: meeting duration must be "
            f"{policy_duration} minutes according to company policy."
        )

    end = start + timedelta(minutes=duration_minutes)

    if (
        end.date() != start.date()
        or end.time().replace(tzinfo=None) > closing_time
    ):
        raise ValueError(
            "Booking rejected: appointment must finish by "
            f"{working_hours['end']} {TIMEZONE_NAME}."
        )

    identity = (
        f"{customer_email}|{service_name.casefold()}|{start.isoformat()}"
    )

    event_id = hashlib.sha256(
        identity.encode("utf-8")
    ).hexdigest()[:40]

    service = get_calendar_service()

    # Check whether this exact booking already exists.
    try:
        existing_event = (
            service.events()
            .get(calendarId="primary", eventId=event_id)
            .execute()
        )

        return {
            "status": "already_booked",
            "event_id": existing_event.get("id"),
            "event_link": existing_event.get("htmlLink"),
            "customer_name": customer_name,
            "customer_email": customer_email,
            "service_name": service_name,
            "start": start.isoformat(),
            "end": end.isoformat(),
            "message": (
                "This booking already exists. "
                "No duplicate event was created."
            ),
        }

    except HttpError as error:
        if error.resp.status != 404:
            raise

    # Recheck availability immediately before insertion.
    available_slots = find_available_slots(
        start.date().isoformat(),
        start_hour=opening_time.hour,
        end_hour=closing_time.hour,
        duration_minutes=duration_minutes,
    )

    matching_slot = any(
        parse_calendar_datetime(slot["start"]) == start
        and parse_calendar_datetime(slot["end"]) == end
        for slot in available_slots
    )

    if not matching_slot:
        raise ValueError(
            "Selected slot is no longer available. "
            "Refresh availability and select another slot."
        )

    event_body = {
        "id": event_id,
        "summary": f"{service_name} consultation - {customer_name}",
        "description": (
            f"Service: {service_name}\n"
            f"Customer: {customer_name}\n"
            f"Customer email: {customer_email}\n"
            "Created by the Mudita AI demo sales assistant."
        ),
        "start": {
            "dateTime": start.isoformat(),
            "timeZone": TIMEZONE_NAME,
        },
        "end": {
            "dateTime": end.isoformat(),
            "timeZone": TIMEZONE_NAME,
        },
        "attendees": [{"email": customer_email}],
    }

    try:
        event = (
            service.events()
            .insert(
                calendarId="primary",
                body=event_body,
                sendUpdates="none",
            )
            .execute()
        )

        return {
            "status": "booked",
            "event_id": event.get("id"),
            "event_link": event.get("htmlLink"),
            "customer_name": customer_name,
            "customer_email": customer_email,
            "service_name": service_name,
            "start": start.isoformat(),
            "end": end.isoformat(),
            "message": "Booking created successfully.",
        }

    except HttpError as error:
        if error.resp.status == 409:
            try:
                existing_event = (
                    service.events()
                    .get(calendarId="primary", eventId=event_id)
                    .execute()
                )

                return {
                    "status": "already_booked",
                    "event_id": existing_event.get("id"),
                    "event_link": existing_event.get("htmlLink"),
                    "message": (
                        "This booking already exists. "
                        "No duplicate event was created."
                    ),
                }

            except HttpError:
                return {
                    "status": "booking_conflict",
                    "event_id": event_id,
                    "message": (
                        "Google Calendar reported a booking conflict. "
                        "Please check the calendar before retrying."
                    ),
                }

        raise


if __name__ == "__main__":
    print("Connecting to Google Calendar...")

    try:
        calendar_service = get_calendar_service()

        calendar_info = (
            calendar_service.calendars()
            .get(calendarId="primary")
            .execute()
        )

        print("Calendar connection: SUCCESS")
        print("Calendar:", calendar_info.get("summary", "Primary Calendar"))

        events = list_upcoming_events(max_results=5)
        print("Upcoming events:", len(events))

        for event in events:
            print(event["start"], "|", event["summary"])

    except Exception as error:
        print("Calendar connection: FAILED")
        print(f"Error: {error}")
