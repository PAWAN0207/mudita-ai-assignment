
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from integrations.calendar_client import (
    create_calendar_booking,
    find_available_slots,
)

TIMEZONE = ZoneInfo("Asia/Kolkata")

print("=" * 55)
print("MUDITA AI - GOOGLE CALENDAR BOOKING TEST")
print("=" * 55)

# Test 1: Verify available slots.
today = datetime.now(TIMEZONE).date()

# Find the next weekday, excluding today.
days_ahead = 1

while True:
    candidate_date = today + timedelta(days=days_ahead)

    if candidate_date.weekday() < 5:
        break

    days_ahead += 1

test_date = candidate_date

slots = find_available_slots(
    test_date.isoformat(),
    start_hour=10,
    end_hour=18,
    duration_minutes=30,
)

print(f"\nTest date: {test_date}")
print(f"Available slots found: {len(slots)}")

if not slots:
    print("FAIL: No available slots found.")
    raise SystemExit(1)

# Use a slot that is currently available.
selected_slot = slots[0]

print(f"Selected slot: {selected_slot['start']}")

# Test 2: Booking without customer confirmation must fail.
print("\nTest 1: Reject booking without confirmation")

try:
    create_calendar_booking(
        customer_name="Mudita Safety Test",
        customer_email="safety-test@example.com",
        service_name="AI Automation",
        start_time=selected_slot["start"],
        customer_confirmed=False,
    )

    print("FAIL: Booking was not rejected.")
    raise SystemExit(1)

except ValueError as error:
    if "confirmation" in str(error).lower():
        print("PASS: Booking rejected without confirmation.")
    else:
        raise

# Test 3: Create a booking with explicit confirmation.
# This creates a real event in the connected Google Calendar.
print("\nTest 2: Create a confirmed test booking")

booking_details = {
    "customer_name": "Mudita Safety Test",
    "customer_email": "safety-test@example.com",
    "service_name": "AI Automation",
    "start_time": selected_slot["start"],
    "customer_confirmed": True,
}

first = create_calendar_booking(**booking_details)

print("First result:", first["status"])

if first["status"] not in {"booked", "already_booked"}:
    print("FAIL: Unexpected booking status.")
    raise SystemExit(1)

# Test 4: Repeating the same request must not create a duplicate.
print("\nTest 3: Prevent duplicate booking")

second = create_calendar_booking(**booking_details)

print("Second result:", second["status"])

if second["status"] != "already_booked":
    print("FAIL: Duplicate booking protection did not pass.")
    raise SystemExit(1)

if first.get("event_id") != second.get("event_id"):
    print("FAIL: Event IDs do not match.")
    raise SystemExit(1)

print("PASS: Duplicate booking prevented.")
print("\nALL BOOKING SAFETY TESTS PASSED.")
