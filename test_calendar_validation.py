
from datetime import datetime, timedelta
from unittest.mock import patch
from zoneinfo import ZoneInfo

import pytest

from integrations.calendar_client import create_calendar_booking

TZ = ZoneInfo("Asia/Kolkata")


def next_weekday(weekday):
    """Return the next date matching weekday (Monday=0, Sunday=6)."""
    today = datetime.now(TZ).date()
    days_ahead = (weekday - today.weekday()) % 7

    if days_ahead == 0:
        days_ahead = 7

    return today + timedelta(days=days_ahead)


def make_start(day, hour, minute=0):
    return datetime(
        day.year,
        day.month,
        day.day,
        hour,
        minute,
        tzinfo=TZ,
    ).isoformat()


def attempt_booking(start_time, **overrides):
    details = {
        "customer_name": "Validation Test",
        "customer_email": "validation@example.com",
        "service_name": "AI Automation",
        "start_time": start_time,
        "customer_confirmed": True,
    }
    details.update(overrides)

    return create_calendar_booking(**details)


def test_missing_confirmation_is_rejected_without_calendar_api():
    start = (
        datetime.now(TZ) + timedelta(days=2)
    ).replace(hour=11, minute=0, second=0, microsecond=0)

    with patch("integrations.calendar_client.get_calendar_service") as api:
        with pytest.raises(ValueError, match="confirmation"):
            attempt_booking(
                start.isoformat(),
                customer_confirmed=False,
            )

        api.assert_not_called()


def test_past_appointment_is_rejected_without_calendar_api():
    past = datetime.now(TZ) - timedelta(days=1)

    with patch("integrations.calendar_client.get_calendar_service") as api:
        with pytest.raises(ValueError, match="future"):
            attempt_booking(past.isoformat())

        api.assert_not_called()


def test_invalid_email_is_rejected_without_calendar_api():
    start = (
        datetime.now(TZ) + timedelta(days=2)
    ).replace(hour=11, minute=0, second=0, microsecond=0)

    with patch("integrations.calendar_client.get_calendar_service") as api:
        with pytest.raises(ValueError, match="email"):
            attempt_booking(
                start.isoformat(),
                customer_email="not-an-email",
            )

        api.assert_not_called()


def test_empty_customer_name_is_rejected_without_calendar_api():
    start = (
        datetime.now(TZ) + timedelta(days=2)
    ).replace(hour=11, minute=0, second=0, microsecond=0)

    with patch("integrations.calendar_client.get_calendar_service") as api:
        with pytest.raises(ValueError, match="name"):
            attempt_booking(
                start.isoformat(),
                customer_name="   ",
            )

        api.assert_not_called()


def test_empty_service_is_rejected_without_calendar_api():
    start = (
        datetime.now(TZ) + timedelta(days=2)
    ).replace(hour=11, minute=0, second=0, microsecond=0)

    with patch("integrations.calendar_client.get_calendar_service") as api:
        with pytest.raises(ValueError, match="(?i)service"):
            attempt_booking(
                start.isoformat(),
                service_name="   ",
            )

        api.assert_not_called()


def test_non_positive_duration_is_rejected_without_calendar_api():
    start = (
        datetime.now(TZ) + timedelta(days=2)
    ).replace(hour=11, minute=0, second=0, microsecond=0)

    with patch("integrations.calendar_client.get_calendar_service") as api:
        with pytest.raises(ValueError, match="duration"):
            attempt_booking(
                start.isoformat(),
                duration_minutes=0,
            )

        api.assert_not_called()

def test_weekend_booking_is_rejected_without_calendar_api():
    # Find the next Saturday.
    saturday = next_weekday(5)
    start = make_start(saturday, 11)

    with patch("integrations.calendar_client.get_calendar_service") as api:
        with pytest.raises(ValueError, match="(?i)monday through friday"):
            attempt_booking(start)

        api.assert_not_called()


def test_booking_before_working_hours_is_rejected():
    monday = next_weekday(0)
    start = make_start(monday, 9)

    with patch("integrations.calendar_client.get_calendar_service") as api:
        with pytest.raises(ValueError, match="(?i)working hours"):
            attempt_booking(start)

        api.assert_not_called()


def test_booking_after_working_hours_is_rejected():
    monday = next_weekday(0)
    start = make_start(monday, 18)

    with patch("integrations.calendar_client.get_calendar_service") as api:
        with pytest.raises(ValueError, match="(?i)working hours"):
            attempt_booking(start)

        api.assert_not_called()


def test_booking_that_finishes_after_closing_is_rejected():
    monday = next_weekday(0)
    start = make_start(monday, 17, 45)

    with patch("integrations.calendar_client.get_calendar_service") as api:
        with pytest.raises(ValueError, match="(?i)finish by"):
            attempt_booking(start)

        api.assert_not_called()


def test_non_policy_meeting_duration_is_rejected():
    monday = next_weekday(0)
    start = make_start(monday, 11)

    with patch("integrations.calendar_client.get_calendar_service") as api:
        with pytest.raises(ValueError, match="(?i)duration"):
            attempt_booking(start, duration_minutes=60)

        api.assert_not_called()
