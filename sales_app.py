import json
import re
import uuid
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import streamlit as st

from core.database import (
    init_database, save_sales_action, get_sales_action_logs,
    save_sales_conversation, load_sales_conversation,
)
from assignment1_sales.conversation import process_customer_message
from assignment1_sales.policy import get_default_policy
from assignment1_sales.qualification import qualify_lead
from assignment1_sales.routing import assign_representative
from integrations.calendar_client import (
    create_calendar_booking, find_available_slots, get_calendar_service,
)
from integrations.gmail_client import (
    GmailConnectionError, get_email_details, list_recent_emails,
    test_gmail_connection,
)

st.set_page_config(
    page_title="Mudita AI | Sales Assistant",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

TIMEZONE = ZoneInfo("Asia/Kolkata")
POLICY = get_default_policy()
init_database()

st.markdown(
    """
    <style>
    .block-container {padding-top: 1.5rem; padding-bottom: 2rem;}
    .mudita-hero {padding: 1.35rem 1.5rem; border-radius: 16px;
    border: 1px solid rgba(120,120,120,.25); margin-bottom: 1rem;}
    .mudita-label {font-size:.78rem;text-transform:uppercase;
    letter-spacing:.14em;opacity:.75;margin-bottom:.25rem}
    .mudita-title {font-size:2rem;font-weight:750;margin:0}
    .mudita-subtitle {opacity:.8;margin-top:.4rem}
    </style>
    """,
    unsafe_allow_html=True,
)


def get_initial_lead_id():
    try:
        existing = st.query_params.get("lead_id")
    except Exception:
        existing = None
    if existing:
        try:
            return str(uuid.UUID(str(existing)))
        except ValueError:
            pass
    return str(uuid.uuid4())


def initialize_state():
    defaults = {
        "lead_id": get_initial_lead_id(),
        "messages": [],
        "conversation_history": [],
        "customer_name": "",
        "customer_email": "",
        "service_interest": None,
        "budget_inr": None,
        "timeline_days": None,
        "qualification": None,
        "representative": None,
        "human_takeover": False,
        "booking_result": None,
        "available_slots": [],
        "slot_date": (datetime.now(TIMEZONE).date() + timedelta(days=1)).isoformat(),
        "customer_booking_confirmation": False,
        "gmail_emails": [],
        "gmail_account": None,
        "gmail_error": None,
        "gmail_last_checked": None,
        "gmail_analysis": None,
        "gmail_selected_email_details": None,
        "calendar_status_result": None,
        "conversation_loaded": False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

    if not st.session_state.conversation_loaded:
        saved = load_sales_conversation(st.session_state.lead_id)
        if saved:
            st.session_state.messages = saved["messages"]
            st.session_state.conversation_history = saved["conversation_history"]
            st.session_state.customer_name = saved["customer_name"]
            st.session_state.customer_email = saved["customer_email"]
            st.session_state.service_interest = saved["service_interest"]
            st.session_state.budget_inr = saved["budget_inr"]
            st.session_state.timeline_days = saved["timeline_days"]
            st.session_state.qualification = None
            st.session_state.representative = saved["representative"]
            st.session_state.human_takeover = saved["human_takeover"]
            st.session_state.booking_result = saved["booking_result"]
        st.session_state.conversation_loaded = True
        try:
            st.query_params["lead_id"] = st.session_state.lead_id
        except Exception:
            pass


def qualification_to_dict(value):
    if value is None:
        return None
    if isinstance(value, dict):
        return value
    return {
        "status": getattr(value, "status", None),
        "evidence": getattr(value, "evidence", []),
        "missing_information": getattr(value, "missing_information", []),
    }


def persist_conversation():
    try:
        save_sales_conversation(
            lead_id=st.session_state.lead_id,
            messages=st.session_state.messages,
            conversation_history=st.session_state.conversation_history,
            customer_name=st.session_state.customer_name,
            customer_email=st.session_state.customer_email,
            service_interest=st.session_state.service_interest,
            budget_inr=st.session_state.budget_inr,
            timeline_days=st.session_state.timeline_days,
            qualification=qualification_to_dict(st.session_state.qualification),
            representative=st.session_state.representative,
            human_takeover=st.session_state.human_takeover,
            booking_result=st.session_state.booking_result,
        )
    except Exception as error:
        st.error(f"Could not persist conversation: {error}")


def log_action(action, details, status="success"):
    serialized = details if isinstance(details, str) else json.dumps(
        details, ensure_ascii=False, default=str
    )
    try:
        save_sales_action(
            lead_id=st.session_state.lead_id,
            action=action,
            details=serialized,
            status=status,
        )
    except Exception as error:
        st.error(f"Could not save action log: {error}")


def start_new_conversation():
    st.session_state.lead_id = str(uuid.uuid4())
    st.session_state.messages = []
    st.session_state.conversation_history = []
    st.session_state.customer_name = ""
    st.session_state.customer_email = ""
    st.session_state.service_interest = None
    st.session_state.budget_inr = None
    st.session_state.timeline_days = None
    st.session_state.qualification = None
    st.session_state.representative = None
    st.session_state.human_takeover = False
    st.session_state.booking_result = None
    st.session_state.available_slots = []
    st.session_state.customer_booking_confirmation = False
    st.session_state.conversation_loaded = True
    try:
        st.query_params["lead_id"] = st.session_state.lead_id
    except Exception:
        pass
    persist_conversation()
    log_action("new_customer_conversation", "Started a new isolated customer conversation.")


def parse_budget(value):
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return int(value)
    text = str(value).strip().lower().replace(",", "").replace("₹", "").replace("rs.", "")
    text = text.replace("inr", "").strip()
    match = re.search(r"(\d+(?:\.\d+)?)\s*(lakh|lakhs|lac|lacs|k)?", text)
    if not match:
        return None
    amount = float(match.group(1))
    unit = match.group(2)
    if unit in {"lakh", "lakhs", "lac", "lacs"}:
        amount *= 100000
    elif unit == "k":
        amount *= 1000
    return int(amount)


def parse_timeline(value):
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return int(value)
    match = re.search(r"\d+", str(value))
    return int(match.group()) if match else None


def parse_service(value):
    if not value:
        return None
    normalized = re.sub(r"[^a-z0-9]+", "", str(value).strip().casefold())
    for service in POLICY["services"]:
        candidate = re.sub(r"[^a-z0-9]+", "", service.casefold())
        if normalized == candidate:
            return service
    return None


def update_customer_facts(extracted_facts):
    if not isinstance(extracted_facts, dict):
        return

    service_value = extracted_facts.get("service_interest")

    # Normalize and validate the service against the configured policy.
    if service_value is not None:
        service = parse_service(str(service_value))
        if service:
            st.session_state.service_interest = service

    budget_value = extracted_facts.get("budget_inr")
    if budget_value is not None:
        budget = parse_budget(budget_value)
        if budget is not None:
            st.session_state.budget_inr = budget

    timeline_value = extracted_facts.get("timeline_days")
    if timeline_value is not None:
        timeline = parse_timeline(timeline_value)
        if timeline is not None:
            st.session_state.timeline_days = timeline


def evaluate_lead():
    result = qualify_lead(
        service_interest=st.session_state.service_interest,
        budget_inr=st.session_state.budget_inr,
        timeline_days=st.session_state.timeline_days,
        policy=POLICY,
    )
    st.session_state.qualification = result
    log_action("lead_qualification", {
        "status": result.status,
        "evidence": result.evidence,
        "missing_information": result.missing_information,
    })
    representative = None
    if result.status == "qualified":
        representative = assign_representative(
            st.session_state.service_interest, policy=POLICY
        )
    st.session_state.representative = representative
    if representative:
        log_action("representative_assignment", {
            "representative_id": representative["id"],
            "representative_name": representative["name"],
        })
    persist_conversation()
    return result

def parse_requested_appointment(message):
    """Extract a date and optional time from common English appointment requests."""
    import re
    from datetime import datetime

    date_match = re.search(
        r"\b(\d{1,2}\s+[A-Za-z]+\s+\d{4})\b",
        message,
    )

    if not date_match:
        return None, None

    try:
        requested_date = datetime.strptime(
            date_match.group(1), "%d %B %Y"
        ).date()
    except ValueError:
        try:
            requested_date = datetime.strptime(
                date_match.group(1), "%d %b %Y"
            ).date()
        except ValueError:
            return None, None

    time_match = re.search(
        r"\b(\d{1,2}(?::\d{2})?\s*[AP]M)\b",
        message,
        re.IGNORECASE,
    )

    requested_time = None

    if time_match:
        time_text = re.sub(r"\s+", " ", time_match.group(1).upper())
        for fmt in ("%I:%M %p", "%I %p"):
            try:
                requested_time = datetime.strptime(
                    time_text, fmt
                ).time()
                break
            except ValueError:
                continue

    return requested_date, requested_time


def check_requested_slot(requested_date, requested_time):
    """Check a requested slot against live Google Calendar availability."""
    from datetime import datetime, timedelta

    if requested_date.weekday() >= 5:
        return {
            "available": False,
            "slots": [],
            "message": "Appointments are available Monday to Friday only.",
        }

    slots = find_available_slots(
        date_text=requested_date.isoformat(),
        start_hour=10,
        end_hour=18,
        duration_minutes=30,
    )

    if requested_time is None:
        return {
            "available": bool(slots),
            "slots": slots[:5],
            "message": "Available slots retrieved from Google Calendar.",
        }

    requested_start = datetime.combine(
        requested_date, requested_time, tzinfo=TIMEZONE
    )

    matching_slot = next(
        (
            slot for slot in slots
            if datetime.fromisoformat(slot["start"]) == requested_start
        ),
        None,
    )

    if matching_slot:
        return {
            "available": True,
            "slots": [matching_slot],
            "message": "The requested slot is available.",
        }

    alternatives = [
        slot for slot in slots
        if datetime.fromisoformat(slot["start"]) > requested_start
    ][:3]

    return {
        "available": False,
        "slots": alternatives,
        "message": "The requested slot is not available.",
    }

def send_customer_message(message):
    """Process a customer message, check calendar availability, or confirm a booking."""
    message = message.strip()

    if not message:
        st.warning("Please enter a message.")
        return

    if st.session_state.human_takeover:
        st.warning("Human takeover is active. AI processing is paused.")
        return

    st.session_state.messages.append({"role": "user", "content": message})

    try:
        normalized = message.casefold()
        requested_date, requested_time = parse_requested_appointment(message)

        confirmation_phrases = (
            "yes, book",
            "please book",
            "confirm my booking",
            "confirm the booking",
            "book that slot",
            "go ahead and book",
            "i confirm",
            "please proceed with the booking",
        )
        is_booking_confirmation = any(
            phrase in normalized for phrase in confirmation_phrases
        )

        pending = st.session_state.get("pending_appointment")
        reply = None

        if is_booking_confirmation:
            if not pending:
                reply = (
                    "I don't have a selected appointment slot to confirm. "
                    "Please ask me to check a specific date and time first. "
                    "No booking has been created."
                )
            elif requested_date is None or requested_time is None:
                reply = (
                    "For safety, please confirm the exact appointment date "
                    "and start time, for example: "
                    "'I confirm 26 October 2026 at 10:30 AM IST.' "
                    "No booking has been created."
                )
            else:
                pending_start = datetime.fromisoformat(pending["start"])
                requested_start = datetime.combine(
                    requested_date, requested_time, tzinfo=TIMEZONE
                )

                if pending_start != requested_start:
                    reply = (
                        "Your confirmation does not match the currently "
                        "selected appointment slot. Please check availability "
                        "for the exact slot again. No booking has been created."
                    )
                elif not st.session_state.customer_name.strip():
                    reply = (
                        "Before booking, please enter and save the customer's "
                        "name in Customer Details. No booking has been created."
                    )
                elif not st.session_state.customer_email.strip():
                    reply = (
                        "Before booking, please enter and save the customer's "
                        "email in Customer Details. No booking has been created."
                    )
                elif not st.session_state.service_interest:
                    reply = (
                        "I need a confirmed service before booking. "
                        "Please identify the service first. No booking has been created."
                    )
                else:
                    # Recheck live availability immediately before booking.
                    fresh = check_requested_slot(requested_date, requested_time)

                    if not fresh.get("available") or not fresh.get("slots"):
                        st.session_state.pending_appointment = None
                        reply = (
                            "That slot is no longer available. I have not "
                            "created a booking. Please request another slot."
                        )
                    else:
                        fresh_slot = next(
                            (
                                slot for slot in fresh["slots"]
                                if datetime.fromisoformat(slot["start"]) == pending_start
                            ),
                            None,
                        )

                        if fresh_slot is None:
                            st.session_state.pending_appointment = None
                            reply = (
                                "The selected slot could not be revalidated. "
                                "No booking has been created. Please check "
                                "availability again."
                            )
                        else:
                            booking_result = create_calendar_booking(
                                customer_name=st.session_state.customer_name,
                                customer_email=st.session_state.customer_email,
                                service_name=st.session_state.service_interest,
                                start_time=fresh_slot["start"],
                                customer_confirmed=True,
                                duration_minutes=30,
                            )
                            st.session_state.booking_result = booking_result
                            status = booking_result.get("status", "unknown")

                            log_action(
                                "calendar_booking",
                                booking_result,
                                status=status,
                            )

                            if status == "booked":
                                end_time = datetime.fromisoformat(fresh_slot["end"])
                                reply = (
                                    "Your consultation has been booked successfully!\n\n"
                                    f"Date: {requested_date.strftime('%A, %d %B %Y')}\n"
                                    f"Time: {pending_start.strftime('%I:%M %p')}–"
                                    f"{end_time.strftime('%I:%M %p')} IST\n"
                                    "Please check the calendar confirmation for representative details."
                                )
                                st.session_state.pending_appointment = None
                            elif status == "already_booked":
                                reply = (
                                    "This appointment already exists in Google "
                                    "Calendar. No duplicate event was created."
                                )
                                st.session_state.pending_appointment = None
                            elif status == "booking_conflict":
                                reply = (
                                    "Google Calendar reported a booking conflict. "
                                    "No new booking was confirmed. Please check availability again."
                                )
                                st.session_state.pending_appointment = None
                            else:
                                reply = (
                                    "Google Calendar did not confirm a successful booking. "
                                    f"Result: {status}. Please check Calendar before retrying."
                                )

        elif (
            requested_date is not None
            and any(
                word in normalized
                for word in (
                    "available", "availability", "check", "schedule",
                    "appointment", "consultation", "slot",
                )
            )
        ):
            availability = check_requested_slot(requested_date, requested_time)

            if availability.get("available") and availability.get("slots"):
                slots = availability["slots"]
                formatted_slots = []

                for slot in slots:
                    start = datetime.fromisoformat(slot["start"])
                    end = datetime.fromisoformat(slot["end"])
                    formatted_slots.append(
                        f"- {start.strftime('%A, %d %B %Y, %I:%M %p')} "
                        f"to {end.strftime('%I:%M %p')} IST"
                    )

                reply = (
                    "I checked the live Google Calendar availability:\n\n"
                    + "\n".join(formatted_slots)
                    + "\n\nTo book, please confirm one exact date and time. "
                    "No booking has been created yet."
                )

                # Only store a pending slot when the customer requested an exact time.
                st.session_state.pending_appointment = (
                    slots[0] if requested_time is not None else None
                )

                log_action(
                    "calendar_availability_checked",
                    {
                        "requested_date": requested_date.isoformat(),
                        "requested_time": (
                            requested_time.isoformat() if requested_time else None
                        ),
                        "available_slots": slots,
                    },
                )
            else:
                st.session_state.pending_appointment = None
                alternatives = availability.get("slots", [])

                if alternatives:
                    reply = (
                        "The requested slot is unavailable. Available alternatives:\n\n"
                        + "\n".join(
                            f"- {datetime.fromisoformat(slot['start']).strftime('%I:%M %p')}–"
                            f"{datetime.fromisoformat(slot['end']).strftime('%I:%M %p')} IST"
                            for slot in alternatives
                        )
                        + "\n\nNo booking has been created."
                    )
                else:
                    reply = (
                        "No matching available slot was found. Try another "
                        "weekday between 10 AM and 6 PM IST. No booking has been created."
                    )
        else:
            result = process_customer_message(
                message=message,
                conversation_history=st.session_state.conversation_history,
                policy=POLICY,
            )
            reply = result.reply
            update_customer_facts(result.extracted_facts)

            log_action(
                "customer_message_processed",
                {
                    "message": message,
                    "extracted_facts": result.extracted_facts,
                    "follow_up_required": result.follow_up_required,
                },
            )

            qualification = evaluate_lead()
            if qualification.status == "qualified":
                st.toast("Lead qualified successfully!")

        st.session_state.conversation_history.extend(
            [
                {"role": "user", "content": message},
                {"role": "assistant", "content": reply},
            ]
        )
        st.session_state.messages.append({"role": "assistant", "content": reply})
        persist_conversation()

    except Exception as error:
        log_action(
            "customer_message_processing",
            {"error": str(error), "message": message},
            status="failed",
        )
        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": (
                    "I couldn't complete the request. No successful booking "
                    "was confirmed. Check the application logs before retrying."
                ),
            }
        )
        persist_conversation()
        st.error(f"Request failed: {error}")

def check_calendar_connection():
    try:
        service = get_calendar_service()
        info = service.calendars().get(calendarId="primary").execute()
        return {"status": "connected", "calendar": info.get("summary", "Primary Calendar")}
    except Exception as error:
        return {"status": "error", "error": str(error)}


def refresh_gmail_inbox(max_results=10):
    try:
        account = test_gmail_connection()
        emails = list_recent_emails(max_results=max_results)
        st.session_state.gmail_account = account
        st.session_state.gmail_emails = emails
        st.session_state.gmail_error = None
        st.session_state.gmail_last_checked = datetime.now(TIMEZONE).isoformat()
        st.session_state.gmail_analysis = None
        st.session_state.gmail_selected_email_details = None
        log_action("gmail_inbox_refreshed", {
            "account": account.get("email"),
            "retrieved_count": len(emails),
        })
        return True
    except GmailConnectionError as error:
        st.session_state.gmail_error = str(error)
        log_action("gmail_inbox_refreshed", str(error), status="failed")
        return False
    except Exception:
        st.session_state.gmail_error = "Unexpected Gmail error. Check authorization and application logs."
        log_action("gmail_inbox_refreshed", st.session_state.gmail_error, status="failed")
        return False


def analyze_gmail_email(email_details):
    """Extract explicit email facts and apply deterministic company policy."""
    subject = email_details.get("subject", "")
    body = email_details.get("body", "")
    content = f"{subject}\n{body}"
    normalized_content = content.casefold()

    service_matches = []
    for service in POLICY["services"]:
        index = normalized_content.find(service.casefold())
        if index >= 0:
            service_matches.append((index, service))
    service_interest = min(service_matches, key=lambda item: item[0])[1] if service_matches else None

    budget_inr = None
    budget_patterns = [
        r"(?:budget|investment|spend|cost)[^\d₹]{0,35}₹\s*([\d,]+)",
        r"(?:budget|investment|spend|cost)[^\d]{0,35}([\d,]+)\s*(?:INR|rupees)\b",
        r"₹\s*([\d,]+)",
        r"\bINR\s*([\d,]+)\b",
    ]
    for pattern in budget_patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            try:
                budget_inr = int(match.group(1).replace(",", ""))
                break
            except (ValueError, TypeError):
                continue

    timeline_days = None
    timeline_patterns = [
        r"\bwithin\s+(\d+)\s+days?\b",
        r"\b(?:timeline|timeframe|delivery)\s*[:\-]?\s*(\d+)\s+days?\b",
        r"\b(\d+)\s+days?\b",
    ]
    for pattern in timeline_patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            try:
                timeline_days = int(match.group(1))
                break
            except (ValueError, TypeError):
                continue

    qualification = qualify_lead(
        service_interest=service_interest,
        budget_inr=budget_inr,
        timeline_days=timeline_days,
        policy=POLICY,
    )
    representative = None
    if qualification.status == "qualified" and service_interest:
        representative = assign_representative(service_interest, policy=POLICY)

    return {
        "source": "gmail",
        "message_id": email_details.get("id"),
        "sender": email_details.get("from", ""),
        "subject": subject,
        "service_interest": service_interest,
        "budget_inr": budget_inr,
        "timeline_days": timeline_days,
        "status": qualification.status,
        "evidence": qualification.evidence,
        "missing_information": qualification.missing_information,
        "representative": representative,
    }


initialize_state()

# Additional session state used by the calendar workflow.
if "pending_appointment" not in st.session_state:
    st.session_state.pending_appointment = None

st.markdown(
    """
    <div class="mudita-hero">
        <div class="mudita-label">Mudita AI · Assignment 1</div>
        <p class="mudita-title">Sales Assistant</p>
        <p class="mudita-subtitle">
            Customer conversations, lead qualification,
            Gmail inbox visibility and safe Google Calendar booking.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.caption("Gemini-powered sales workflow · Gmail inbox · Google Calendar")


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("Company Policy")

    if st.button("New Customer Conversation", use_container_width=True):
        start_new_conversation()
        st.rerun()

    st.caption(f"Current Lead ID: {st.session_state.lead_id}")
    st.divider()

    st.write("**Company:**", POLICY["company_name"])
    st.write("**Services:**")
    for service in POLICY["services"]:
        st.write(f"- {service}")

    st.write(
        "**Minimum budget:**",
        f"₹{POLICY['qualification']['minimum_budget_inr']:,}",
    )
    st.write(
        "**Maximum timeline:**",
        f"{POLICY['qualification']['maximum_timeline_days']} days",
    )

    st.divider()
    st.subheader("Representatives")
    for representative in POLICY["representatives"]:
        st.write(f"**{representative['name']}**")
        st.caption(", ".join(representative["specializations"]))

    st.divider()
    if st.button("Request Human Takeover", use_container_width=True):
        st.session_state.human_takeover = True
        persist_conversation()
        log_action(
            "human_takeover_requested",
            "AI messaging paused for manual handling.",
        )
        st.rerun()

    if st.session_state.human_takeover:
        st.warning("Human takeover is active.")
        if st.button("Resume AI Assistant", use_container_width=True):
            st.session_state.human_takeover = False
            persist_conversation()
            log_action(
                "human_takeover_released",
                "AI messaging resumed.",
            )
            st.rerun()

    st.divider()
    if st.button("Reset Demo", use_container_width=True):
        start_new_conversation()
        st.rerun()


# ---------------------------------------------------------------------------
# Integration status cards
# ---------------------------------------------------------------------------
c1, c2, c3 = st.columns(3)

with c1:
    st.markdown("**Gmail Inbox**")
    if st.session_state.gmail_account:
        st.success(
            "Connected · "
            f"{st.session_state.gmail_account.get('email', '')}"
        )
    elif st.session_state.gmail_error:
        st.error("Connection needs attention")
    else:
        st.info("Not checked in this session")

with c2:
    st.markdown("**Google Calendar**")
    if st.button(
        "Check Calendar Connection",
        key="calendar_status_check",
    ):
        st.session_state.calendar_status_result = check_calendar_connection()

    cal_status = st.session_state.calendar_status_result
    if cal_status and cal_status.get("status") == "connected":
        st.success(
            f"Connected · {cal_status.get('calendar', 'Calendar')}"
        )
    elif cal_status:
        st.error("Calendar connection failed")
        st.caption(str(cal_status.get("error", ""))[:250])
    else:
        st.info("Click to verify connection")

with c3:
    st.markdown("**Other Channels**")
    st.warning("Instagram and WhatsApp are not connected")


# ---------------------------------------------------------------------------
# Main tabs
# ---------------------------------------------------------------------------
tab_chat, tab_lead, tab_gmail, tab_calendar, tab_logs = st.tabs(
    [
        "Customer Conversation",
        "Lead Qualification",
        "Gmail Inbox",
        "Calendar Booking",
        "Action Logs",
    ]
)


# ---------------------------------------------------------------------------
# Customer conversation
# ---------------------------------------------------------------------------
with tab_chat:
    st.subheader("Customer Conversation")
    left, right = st.columns([2, 1])

    with left:
        for item in st.session_state.messages:
            with st.chat_message(item["role"]):
                st.markdown(item["content"])

        if st.session_state.human_takeover:
            st.warning(
                "Human takeover is active. AI responses are paused."
            )
        else:
            with st.form(
                "customer_message_form",
                clear_on_submit=True,
            ):
                customer_message = st.text_area(
                    "Enter customer inquiry",
                    placeholder=(
                        "Example: I need AI Automation, my budget is "
                        "₹2 lakh, and I need it in 60 days."
                    ),
                    height=100,
                )
                submitted = st.form_submit_button(
                    "Send Message",
                    type="primary",
                )

            if submitted:
                send_customer_message(customer_message)
                st.rerun()

    with right:
        st.markdown("#### Customer Details")
        with st.form("customer_details_form"):
            customer_name = st.text_input(
                "Customer name",
                value=st.session_state.customer_name,
            )
            customer_email = st.text_input(
                "Customer email",
                value=st.session_state.customer_email,
            )
            save_details = st.form_submit_button(
                "Save Customer Details"
            )

        if save_details:
            normalized_email = customer_email.strip().lower()
            if normalized_email and not re.fullmatch(
                r"[^@\s]+@[^@\s]+\.[^@\s]+",
                normalized_email,
            ):
                st.error("Enter a valid email address.")
            else:
                st.session_state.customer_name = customer_name.strip()
                st.session_state.customer_email = normalized_email
                persist_conversation()
                log_action(
                    "customer_details_updated",
                    {
                        "customer_name": customer_name.strip(),
                        "customer_email": normalized_email,
                    },
                )
                st.success("Customer details saved.")
                st.rerun()


# ---------------------------------------------------------------------------
# Lead qualification
# ---------------------------------------------------------------------------
with tab_lead:
    st.subheader("Lead Qualification")
    st.caption(
        "Qualification uses configured company policy and extracted "
        "customer facts."
    )

    with st.form("manual_lead_form"):
        service_options = ["Not provided"] + POLICY["services"]
        current_service = st.session_state.service_interest
        service_index = (
            service_options.index(current_service)
            if current_service in service_options
            else 0
        )

        selected_service = st.selectbox(
            "Service interest",
            options=service_options,
            index=service_index,
        )
        budget_value = st.number_input(
            "Budget (INR)",
            min_value=0,
            value=int(st.session_state.budget_inr or 0),
            step=5000,
        )
        timeline_value = st.number_input(
            "Timeline (days)",
            min_value=0,
            value=int(st.session_state.timeline_days or 0),
            step=5,
        )
        evaluate_button = st.form_submit_button(
            "Evaluate Lead",
            type="primary",
        )

    if evaluate_button:
        st.session_state.service_interest = (
            None if selected_service == "Not provided" else selected_service
        )
        st.session_state.budget_inr = (
            None if budget_value == 0 else int(budget_value)
        )
        st.session_state.timeline_days = (
            None if timeline_value == 0 else int(timeline_value)
        )
        evaluate_lead()
        st.success("Lead evaluation completed.")

    result = st.session_state.qualification
    if result:
        if isinstance(result, dict):
            status = result.get("status")
            evidence = result.get("evidence", [])
            missing = result.get("missing_information", [])
        else:
            status = getattr(result, "status", None)
            evidence = getattr(result, "evidence", [])
            missing = getattr(result, "missing_information", [])

        labels = {
            "qualified": "✅ Qualified",
            "not_qualified": "❌ Not Qualified",
            "needs_more_information": "🟡 Needs More Information",
        }
        st.metric("Qualification Status", labels.get(status, status))

        st.markdown("#### Evidence")
        for item in evidence or []:
            st.write(f"- {item}")

        if missing:
            st.markdown("#### Missing Information")
            for item in missing:
                st.write(f"- {item}")

        representative = st.session_state.representative
        if status == "qualified" and representative:
            st.markdown("#### Assigned Representative")
            st.success(
                f"{representative['name']} ({representative['id']})"
            )
            st.write(
                "Specializations:",
                ", ".join(representative["specializations"]),
            )


# ---------------------------------------------------------------------------
# Gmail inbox and lead analysis
# ---------------------------------------------------------------------------
with tab_gmail:
    st.subheader("Gmail Inbox")
    st.caption(
        "Read-only Gmail integration. Select an email to read its full body "
        "and analyze it against configured business policy. No emails are "
        "sent or modified."
    )

    c_left, c_right = st.columns([1, 2])
    with c_left:
        email_limit = st.selectbox(
            "Emails to load",
            [5, 10, 20, 50],
            index=1,
            key="gmail_email_limit",
        )
        refresh = st.button(
            "🔄 Connect / Refresh Inbox",
            type="primary",
            use_container_width=True,
            key="gmail_refresh_button",
        )

    with c_right:
        account = st.session_state.gmail_account
        if account:
            st.metric(
                "Authorized account",
                account.get("email", "Connected"),
            )
            m1, m2 = st.columns(2)
            m1.metric("Messages", account.get("messages_total", 0))
            m2.metric("Threads", account.get("threads_total", 0))

    if refresh:
        with st.spinner("Connecting to Gmail and loading inbox..."):
            ok = refresh_gmail_inbox(email_limit)
        if ok:
            st.success(
                "Gmail connected. Loaded "
                f"{len(st.session_state.gmail_emails)} emails."
            )
        else:
            st.error(
                st.session_state.gmail_error or "Gmail connection failed."
            )

    if st.session_state.gmail_error:
        st.error(st.session_state.gmail_error)

    if st.session_state.gmail_last_checked:
        st.caption(
            "Last refreshed: " + st.session_state.gmail_last_checked
        )

    emails = st.session_state.gmail_emails
    if not emails:
        st.info(
            "No inbox messages loaded. Click 'Connect / Refresh Inbox'."
        )
    else:
        email_by_id = {
            str(item["id"]): item
            for item in emails
            if item.get("id")
        }

        if not email_by_id:
            st.warning("No valid Gmail message IDs were returned.")
        else:
            def email_label(message_id):
                item = email_by_id[message_id]
                subject = item.get("subject") or "(No subject)"
                sender = item.get("from") or "Unknown sender"
                date = item.get("date") or "Date unavailable"
                return f"{subject} | {sender} | {date}"

            selected_message_id = st.selectbox(
                "Select an email for analysis",
                options=list(email_by_id.keys()),
                format_func=email_label,
                key="gmail_selected_message_id",
            )
            selected_email = email_by_id[selected_message_id]

            if (
                st.session_state.gmail_analysis
                and st.session_state.gmail_analysis.get("message_id")
                != selected_message_id
            ):
                st.session_state.gmail_analysis = None
                st.session_state.gmail_selected_email_details = None

            st.markdown("### Selected Email")
            st.markdown(
                f"**Subject:** "
                f"{selected_email.get('subject') or '(No subject)'}"
            )
            st.write(
                "**From:**",
                selected_email.get("from") or "Unknown sender",
            )
            st.write(
                "**Date:**",
                selected_email.get("date") or "Date unavailable",
            )
            st.write(
                "**Preview:**",
                selected_email.get("snippet") or "(No preview available)",
            )

            with st.expander("Gmail technical details"):
                st.write("Message ID:", selected_message_id)
                st.write(
                    "Thread ID:",
                    selected_email.get("thread_id", "Unavailable"),
                )

            if st.button(
                "🔍 Read Full Email & Analyze Lead",
                type="primary",
                use_container_width=True,
                key="gmail_analyze_button",
            ):
                try:
                    with st.spinner(
                        "Reading email and applying company policy..."
                    ):
                        details = get_email_details(selected_message_id)
                        st.session_state.gmail_selected_email_details = details
                        analysis = analyze_gmail_email(details)
                        st.session_state.gmail_analysis = analysis

                        log_action(
                            "gmail_lead_analysis",
                            {
                                "message_id": analysis["message_id"],
                                "sender": analysis["sender"],
                                "subject": analysis["subject"],
                                "service_interest": analysis["service_interest"],
                                "budget_inr": analysis["budget_inr"],
                                "timeline_days": analysis["timeline_days"],
                                "qualification_status": analysis["status"],
                                "evidence": analysis["evidence"],
                                "missing_information": (
                                    analysis["missing_information"]
                                ),
                                "representative": analysis["representative"],
                            },
                        )
                except GmailConnectionError as error:
                    st.session_state.gmail_analysis = None
                    st.session_state.gmail_selected_email_details = None
                    log_action(
                        "gmail_lead_analysis",
                        {
                            "message_id": selected_message_id,
                            "error": str(error),
                        },
                        status="failed",
                    )
                    st.error(
                        "Could not read the selected email. Check Gmail "
                        "authorization and API access."
                    )
                except Exception:
                    st.session_state.gmail_analysis = None
                    st.session_state.gmail_selected_email_details = None
                    log_action(
                        "gmail_lead_analysis",
                        {
                            "message_id": selected_message_id,
                            "error": "Unexpected analysis failure.",
                        },
                        status="failed",
                    )
                    st.error(
                        "Email analysis failed. Check Action Logs and try again."
                    )

            analysis = st.session_state.gmail_analysis
            if (
                analysis
                and analysis.get("message_id") == selected_message_id
            ):
                st.divider()
                st.markdown("### Full Email Content")
                details = (
                    st.session_state.gmail_selected_email_details or {}
                )
                st.text(details.get("body", "(Email body unavailable)"))

                st.divider()
                st.markdown("### Lead Analysis")
                st.write(
                    "**Service:**",
                    analysis["service_interest"] or "Not identified",
                )

                budget = analysis["budget_inr"]
                st.write(
                    "**Budget:**",
                    f"₹{budget:,}" if budget is not None else "Not identified",
                )

                timeline = analysis["timeline_days"]
                st.write(
                    "**Timeline:**",
                    f"{timeline} days"
                    if timeline is not None
                    else "Not identified",
                )

                labels = {
                    "qualified": "Qualified",
                    "not_qualified": "Not Qualified",
                    "needs_more_information": "Needs More Information",
                }
                status = analysis["status"]

                if status == "qualified":
                    st.success(f"✅ {labels.get(status, status)}")
                elif status == "not_qualified":
                    st.error(f"❌ {labels.get(status, status)}")
                else:
                    st.warning(f"🟡 {labels.get(status, status)}")

                st.markdown("#### Evidence")
                for item in analysis["evidence"] or [
                    "No qualification evidence was generated."
                ]:
                    st.write(f"- {item}")

                if analysis["missing_information"]:
                    st.markdown("#### Missing Information")
                    for item in analysis["missing_information"]:
                        st.write(f"- {item}")

                representative = analysis["representative"]
                st.markdown("#### Representative Assignment")
                if representative:
                    st.success(
                        f"{representative['name']} "
                        f"({representative['id']})"
                    )
                    st.write(
                        "Specializations:",
                        ", ".join(representative["specializations"]),
                    )
                elif status == "qualified":
                    st.warning(
                        "The lead qualifies, but no representative matches "
                        "the current routing policy."
                    )
                else:
                    st.info(
                        "Representative assignment is deferred until "
                        "the lead qualifies."
                    )

                st.caption(
                    "This baseline uses pattern-based fact extraction and "
                    "deterministic business rules, not LLM-based email "
                    "extraction. It does not send a reply, create a calendar "
                    "booking, or merge this email with a customer conversation."
                )


# ---------------------------------------------------------------------------
# Google Calendar availability and booking
# ---------------------------------------------------------------------------
with tab_calendar:
    st.subheader("Google Calendar Availability")
    st.warning(
        "Create a booking only after the customer explicitly confirms "
        "the selected date and time."
    )

    date_value = st.date_input(
        "Appointment date",
        value=datetime.fromisoformat(st.session_state.slot_date).date(),
        min_value=datetime.now(TIMEZONE).date(),
    )
    st.session_state.slot_date = date_value.isoformat()

    if st.button("🔎 Check Available Slots"):
        if date_value.weekday() >= 5:
            st.warning(
                "The configured policy lists Monday to Friday as working "
                "days. Choose a weekday."
            )
        else:
            try:
                slots = find_available_slots(
                    date_text=date_value.isoformat(),
                    start_hour=10,
                    end_hour=18,
                    duration_minutes=30,
                )
                st.session_state.available_slots = slots
                log_action(
                    "calendar_availability_checked",
                    {
                        "date": date_value.isoformat(),
                        "available_slot_count": len(slots),
                    },
                )
                st.success(f"{len(slots)} available slots found.")
            except Exception:
                log_action(
                    "calendar_availability_checked",
                    "Calendar availability request failed.",
                    status="failed",
                )
                st.error(
                    "Could not fetch calendar availability. Check Google "
                    "Calendar authorization and API status."
                )

    valid_slots = [
        slot
        for slot in st.session_state.available_slots
        if slot["start"].startswith(date_value.isoformat())
    ]

    if valid_slots:
        labels = [
            datetime.fromisoformat(slot["start"]).strftime("%I:%M %p")
            + " – "
            + datetime.fromisoformat(slot["end"]).strftime("%I:%M %p")
            for slot in valid_slots
        ]
        selected_index = st.selectbox(
            "Select an available time",
            list(range(len(valid_slots))),
            format_func=lambda index: labels[index],
        )
        selected_slot = valid_slots[selected_index]

        st.markdown("#### Booking Details")
        st.write(
            "**Customer:**",
            st.session_state.customer_name or "Not provided",
        )
        st.write(
            "**Email:**",
            st.session_state.customer_email or "Not provided",
        )
        st.write(
            "**Service:**",
            st.session_state.service_interest or "Not provided",
        )

        if st.session_state.qualification:
            qualification = st.session_state.qualification
            lead_status = (
                qualification.get("status", "saved")
                if isinstance(qualification, dict)
                else getattr(qualification, "status", "saved")
            )
            st.write("**Lead status:**", lead_status)

        confirmed = st.checkbox(
            "The customer has explicitly confirmed this exact date and time.",
            key="customer_booking_confirmation",
        )

        if st.button("📅 Create Confirmed Booking", type="primary"):
            if not confirmed:
                st.error(
                    "Booking rejected: customer confirmation is required."
                )
                log_action(
                    "calendar_booking",
                    "Rejected because customer confirmation was missing.",
                    status="rejected",
                )
            elif not st.session_state.customer_name:
                st.error("Enter and save the customer's name first.")
            elif not st.session_state.customer_email:
                st.error("Enter and save the customer's email first.")
            elif not st.session_state.service_interest:
                st.error("Select a supported service first.")
            else:
                try:
                    booking_result = create_calendar_booking(
                        customer_name=st.session_state.customer_name,
                        customer_email=st.session_state.customer_email,
                        service_name=st.session_state.service_interest,
                        start_time=selected_slot["start"],
                        customer_confirmed=True,
                        duration_minutes=30,
                    )
                    st.session_state.booking_result = booking_result
                    persist_conversation()
                    log_action(
                        "calendar_booking",
                        booking_result,
                        status=booking_result.get("status", "unknown"),
                    )

                    booking_status = booking_result.get("status")
                    if booking_status == "booked":
                        st.success("Booking created successfully!")
                    elif booking_status == "already_booked":
                        st.info(
                            "This booking already exists. "
                            "No duplicate event was created."
                        )
                    elif booking_status == "booking_conflict":
                        st.warning(
                            "Calendar reported a conflict. Check the "
                            "calendar before retrying."
                        )
                    st.json(booking_result)
                except Exception:
                    log_action(
                        "calendar_booking",
                        "Calendar booking request failed.",
                        status="failed",
                    )
                    st.error(
                        "Booking failed. Refresh availability and check "
                        "the calendar before retrying."
                    )
    else:
        st.info(
            "Choose a weekday and click 'Check Available Slots' to load "
            "real calendar availability."
        )


# ---------------------------------------------------------------------------
# Persistent action logs
# ---------------------------------------------------------------------------
with tab_logs:
    st.subheader("Persistent Action Logs")
    st.caption(
        "Logs are loaded from SQLite and remain available after "
        "application restart."
    )

    if st.button("🔄 Refresh Logs"):
        st.rerun()

    try:
        logs = get_sales_action_logs(limit=200)
        if logs:
            st.dataframe(
                logs,
                use_container_width=True,
                hide_index=True,
            )
            st.download_button(
                "Download Action Logs (JSON)",
                data=json.dumps(
                    logs,
                    indent=2,
                    ensure_ascii=False,
                    default=str,
                ),
                file_name="mudita_sales_action_logs.json",
                mime="application/json",
            )
        else:
            st.info("No action logs have been recorded yet.")
    except Exception as error:
        st.error(f"Could not load action logs: {error}")
