# Mudita AI — Intelligent Sales Assistant
### Assignment 01 · AI Generalist Hiring Assignment

An AI-assisted sales workflow prototype for handling customer inquiries, extracting qualification details, routing qualified leads to the appropriate sales representative, and safely scheduling meetings through Google Calendar.

> **Implementation status:** The current application includes a Streamlit interface, Gemini-powered conversation logic, policy-based qualification and routing, Gmail inbox visibility, Google Calendar availability/booking, conversation persistence, human takeover, and action logs. Instagram and WhatsApp are **not connected** in the current version. See [Known Limitations](#known-limitations).

## Table of Contents
- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Technology Stack](#technology-stack)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Local Setup](#local-setup)
- [Google Integrations](#google-integrations)
- [Run the Application](#run-the-application)
- [Testing](#testing)
- [Security and Reliability](#security-and-reliability)
- [Known Limitations](#known-limitations)
- [Demo Checklist](#demo-checklist)

## Overview

The prototype demonstrates how an AI sales assistant can help a fictional analytics consultancy manage inbound leads. It brings the customer conversation, lead qualification, Gmail inbox visibility, calendar scheduling, and action history into one Streamlit interface.

The system is designed to use explicit company policy for qualification and representative assignment rather than allowing the model to invent business rules or staff.

## Features

- **AI-assisted conversation:** Uses a configured Gemini model to understand customer messages and produce contextual responses.
- **Editable business policy:** Uses company services, qualification criteria, representatives, routing rules, timezone, and working-hour settings defined by the application.
- **Lead qualification:** Extracts available service interest, budget, and timeline details; returns a qualification outcome with supporting evidence and missing information.
- **Representative routing:** Applies explicit routing rules to qualified leads.
- **Gmail inbox visibility:** Connects to an authorised Gmail account and displays recent email inquiries.
- **Google Calendar integration:** Reads calendar availability and supports booking through the application.
- **Booking safeguards:** Requires explicit customer confirmation, rechecks availability before booking, and uses deterministic event identifiers to help prevent duplicate events.
- **Human takeover:** Provides a control to pause AI processing for manual handling.
- **Persistence and action logs:** Stores conversation state and records key workflow actions using the application's database layer.
- **Streamlit UI:** Provides dedicated areas for customer conversations, lead qualification, Gmail, calendar booking, and action logs.

## Architecture

```text
Customer message / Gmail inquiry
              |
              v
     Streamlit application
              |
       +------+------+
       |             |
       v             v
 Gemini conversation  Gmail integration
       |
       v
 Extract qualification details
       |
       v
 Policy-based qualification
       |
       v
 Representative routing
       |
       v
 Google Calendar availability
       |
       v
 Explicit confirmation required
       |
       v
 Recheck slot -> Create event
       |
       v
 Persist state and action log
```

The architecture is a focused prototype rather than a production deployment. Provider-specific channel integrations depend on authorised credentials and API access.

## Technology Stack

- Python
- Streamlit
- Google Gemini API
- Google Gmail API
- Google Calendar API
- Google OAuth 2.0
- SQLite / SQLAlchemy-based persistence (as configured in the project)
- pytest for automated tests

Check the project’s `requirements.txt` for the exact dependency versions used in the current environment.

## Project Structure

The workspace screenshot shows the following relevant files and directories. The layout may include additional files not listed here.

```text
mudita-ai-assignment/
├── assignment1_sales/
│   ├── conversation.py
│   ├── policy.py
│   ├── qualification.py
│   └── routing.py
├── integrations/
│   ├── calendar_client.py
│   ├── gmail_client.py
│   └── conversation.py          # if present in your current tree
├── core/                        # shared configuration/persistence modules
├── pages/
├── tests/
│   ├── test_booking_safety.py
│   ├── test_calendar_booking.py
│   ├── test_calendar_validation.py
│   └── test_gmail_connection.py
├── sales_app.py
├── requirements.txt
└── .gitignore
```

Use the actual files in your local repository as the source of truth; the screenshot shows both assignments in one workspace.

## Prerequisites

- Python installed (the recorded development environment used Python 3.10.10).
- A virtual environment.
- Google Cloud project with the required APIs enabled.
- OAuth credentials for Gmail and Google Calendar, where those integrations are used.
- A Gemini API key with available quota.

Python 3.10.10 produced a Google API client warning in a previous run. For a fresh setup, prefer a currently supported Python version compatible with the project dependencies, and rerun the tests after changing Python versions.

## Local Setup

Run commands from the repository root in PowerShell.

```powershell
# Activate the existing virtual environment, if already created
.\.venv\Scripts\Activate.ps1

# Otherwise create a virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install project dependencies
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Configure required credentials using the variable names expected by the current code and its configuration modules. Do not commit API keys, OAuth client secrets, OAuth tokens, or personal data.

If the repository does not yet contain an `.env.example`, create one containing **variable names only** after confirming the exact names used in `core/config.py` and `core/gemini_client.py`. Do not guess variable names.

## Google Integrations

### Gmail
1. Create or select a Google Cloud project.
2. Enable the Gmail API.
3. Configure OAuth consent and an authorised test account.
4. Store OAuth client credentials locally using the filename/path expected by the application.
5. Test the connection from the app.
6. Keep token files private and out of version control.

### Google Calendar
1. Enable the Google Calendar API in the same or a suitable Google Cloud project.
2. Configure OAuth credentials for an authorised test calendar.
3. Start the app and complete the OAuth flow when prompted.
4. Verify that availability reflects the test calendar.
5. Use a clearly identified test event and authorised recipient for booking tests.

The current calendar client references `credentials.json` and `token.json` in the repository root. These files are sensitive and must not be committed.

### Gemini
Configure the Gemini API key using the exact mechanism expected by the project's configuration/client code. Check the current quota before running live LLM scenarios.

## Run the Application

```powershell
python -m streamlit run sales_app.py
```

Open the local address printed by Streamlit in the terminal. If the default port is occupied, stop the other Streamlit process or allow Streamlit to select another available port.

## Testing

Run the test suite from the repository root:

```powershell
python -m pytest tests -v
```

Previous recorded testing evidence includes **11/11 calendar safety/validation tests passing**. A previous safety check also confirmed that a booking request without explicit customer confirmation was rejected.

Re-run the suite against the exact code being submitted and update this section if the results change. Automated tests do not establish that every external provider integration is available or that Instagram/WhatsApp are connected.

## Security and Reliability

- Keep OAuth credentials, API keys, tokens, and local databases containing personal data out of public repositories.
- Require explicit customer confirmation before creating a calendar event.
- Recheck calendar availability immediately before booking.
- Avoid blind retries when a provider request may have succeeded but its response was lost.
- Use only authorised test accounts and recipients.
- Treat customer messages as untrusted input; business policy must take precedence over instructions embedded in customer content.
- Verify that human takeover stops automatic processing before demonstrating the feature.

## Known Limitations

- **Instagram and WhatsApp are not connected** in the current version; they must not be presented as completed integrations.
- Gmail and Calendar require valid OAuth setup and provider access.
- Live Gemini functionality depends on API quota and provider availability.
- Deployment, public demo URLs, and a Loom walkthrough must be added only after they exist and have been verified.
- The current prototype should not be described as production-ready.

## Demo Checklist

- [ ] Confirm Gmail and Google Calendar connection status.
- [ ] Demonstrate a new customer inquiry and contextual follow-up.
- [ ] Demonstrate qualification evidence, missing information, and policy-based routing.
- [ ] Demonstrate calendar availability.
- [ ] Demonstrate that booking is rejected without explicit confirmation.
- [ ] Confirm a specific slot and show the resulting test-calendar event.
- [ ] Repeat the confirmation and verify that no duplicate event is created.
- [ ] Demonstrate human takeover and confirm automatic processing pauses.
- [ ] Show action logs.
- [ ] Clearly disclose that Instagram and WhatsApp are not connected.
- [ ] Run tests and record the actual result.
