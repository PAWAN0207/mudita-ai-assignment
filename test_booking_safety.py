
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from integrations.calendar_client import create_calendar_booking

start = (
    datetime.now(ZoneInfo("Asia/Kolkata")) + timedelta(days=1)
).replace(
    hour=10,
    minute=0,
    second=0,
    microsecond=0,
).isoformat()

try:
    create_calendar_booking(
        customer_name="Demo Customer",
        customer_email="demo@example.com",
        service_name="AI Automation",
        start_time=start,
        customer_confirmed=False,
    )

    print("ERROR: Booking should not have been created!")

except ValueError as exc:
    print("Safety test passed:", exc)

