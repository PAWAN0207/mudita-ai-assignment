# Mudita AI --- Applied AI Engineering Assignments

**AI Sales Assistant · Multi-Agent Operations Coordinator**

Two Python/Streamlit applications demonstrating practical LLM
integration, structured business workflows, external-service
integrations, validation, and human-controlled safeguards.

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/UI-Streamlit-FF4B4B)](https://streamlit.io/)
[![Gemini](https://img.shields.io/badge/LLM-Google%20Gemini-4285F4)](https://ai.google.dev/)
[![Tests](https://img.shields.io/badge/Tests-21%20previously%20reported%20passing-brightgreen)](#testing)

> **Public demo guidance:** Use synthetic, non-sensitive test inputs. Do
> not enter passwords, confidential business information, or personal
> data.

## Live Applications

  --------------------------------------------------------------------------------------------------------------------
  Assignment              Live demo                                                            Explore
  ----------------------- -------------------------------------------------------------------- -----------------------
  **1 --- AI Sales        [Open Sales                                                          Customer conversation,
  Assistant**             Assistant](https://mudita-sales-assistant.streamlit.app/)            lead qualification,
                                                                                               Gmail inbox analysis,
                                                                                               Calendar
                                                                                               availability/booking,
                                                                                               human takeover, action
                                                                                               logs.

  **2 --- AI Operations   [Open Operations                                                     Submit an operational
  Coordinator**           Coordinator](https://mudita-operations-coordinator.streamlit.app/)   request and inspect the
                                                                                               Intake → Planning →
                                                                                               Review workflow.
  --------------------------------------------------------------------------------------------------------------------

**Access:** Open a link in your browser; no local installation is
required to view the hosted UI. Feature availability depends on deployed
secrets, API quota, and third-party authorization. Recheck both apps
before submission and keep them accessible for at least **seven days
after submission**. A page loading successfully does not guarantee every
integration is connected.

## What Makes This Project Different?

This is more than a chat interface. The applications combine LLM
capabilities with explicit Python business logic and safeguards.

-   **Structured LLM output:** The Sales Assistant requests JSON and
    validates it with a Pydantic model before using extracted facts.
-   **AI/business-logic separation:** Gemini interprets customer
    language; dedicated Python functions perform lead qualification and
    representative routing.
-   **Read-only Gmail lead workflow:** Retrieves emails and uses
    pattern/regex extraction on selected email content. It does not send
    or modify email.
-   **Confirmation-gated scheduling:** Calendar booking requires
    explicit confirmation, validates required details and business-hour
    rules, rechecks availability, and handles duplicate/conflict
    outcomes.
-   **Human takeover:** A representative can pause AI message processing
    and resume it later.
-   **Three distinct agents:** Intake extracts operational information,
    Planning creates tasks and dependencies, and Review evaluates the
    proposed plan.
-   **Explicit context handoffs:** Structured output from one stage is
    passed to the next instead of treating the workflow as one
    undifferentiated prompt.
-   **Transparent unresolved information:** Missing task owners remain
    unresolved rather than being silently invented.
-   **Persistence and traceability:** Database-backed
    conversation/workflow records and action/execution history support
    review and debugging.
-   **Modular, testable design:** UI, business rules, integrations,
    schemas, model access, and orchestration are separated.

------------------------------------------------------------------------

# Assignment 1 --- AI Sales Assistant

## Goal

Support sales workflows by managing customer inquiries, extracting
qualification details, routing qualified leads, analyzing inbound Gmail
messages, and scheduling consultations through Google Calendar.

## Features

### Customer conversation

-   Uses Google Gemini to generate context-aware responses.
-   Includes company policy and conversation history in the prompt.
-   Requests structured JSON containing a reply, extracted facts, and
    follow-up status.
-   Validates the response with `SalesConversationResponse`.
-   Filters extracted facts to supported fields such as service
    interest, budget, and timeline.
-   Avoids claiming a booking succeeded before Calendar confirms it.

### Lead qualification and representative routing

-   Uses a dedicated Python function to evaluate service interest,
    budget, and timeline against configured policy.
-   Keeps qualification logic separate from LLM-generated conversation
    text.
-   Routes qualified leads through a separate representative-assignment
    function.
-   Preserves missing information rather than treating unknown values as
    facts.

### Gmail inbox analysis

-   Checks the authorized Gmail connection and retrieves recent inbox
    messages.
-   Supports up to 50 recent messages.
-   Retrieves full details for a selected email.
-   Uses configured service names and regex/pattern matching to extract
    service interest, budget, and timeline.
-   Reuses qualification and routing logic after extraction.
-   **Read-only:** uses Gmail's read-only scope; it does not send,
    delete, or modify email.

### Google Calendar availability and booking

-   Checks available 30-minute slots within configured working hours.
-   Uses the `Asia/Kolkata` timezone in the Calendar client.
-   Requires explicit confirmation before creating a booking.
-   Validates customer name, email, service, date/time, working days,
    and duration.
-   Rechecks availability before event creation.
-   Uses a deterministic event identifier to help prevent duplicate
    bookings.
-   Handles `booked`, `already_booked`, and `booking_conflict` outcomes.

### Human takeover and action history

-   Pauses AI processing while human takeover is active.
-   Provides a control to resume AI handling.
-   Persists conversation state and records key actions through the
    database layer.
-   Provides an Action Logs view.

## Sales Assistant architecture

``` text
Customer message ──> Streamlit UI ──> Gemini conversation processing
                                         |
                                         v
                               Structured JSON response
                                         |
                                         v
                               Schema validation/fact update
                                         |
                                         v
                               Policy-based lead qualification
                                         |
                                         v
                               Representative routing

Gmail API ──> Recent emails ──> Pattern/regex extraction ──┘

Calendar API <──> Availability check ──> Explicit confirmation
                                      ──> Recheck ──> Create event

Conversation state and actions ──> Database / Action Logs
Human takeover ──> Pauses AI message processing
```

------------------------------------------------------------------------

# Assignment 2 --- AI Operations Coordinator

## Goal

Transform unstructured business instructions into a structured,
reviewable action plan using three specialized agents.

### 1. Intake Agent

Extracts the objective, requirements, deadlines, constraints, missing
information, and potential conflicts from the original request. It
should preserve unknown details instead of inventing owners or
deadlines.

### 2. Planning Agent

Converts structured intake information into actionable tasks. The plan
can include task IDs, descriptions, known owners, dependencies, and
unresolved details. Dependencies describe the proposed plan; they do not
prove that the real-world work has been completed.

### 3. Review Agent

Evaluates the generated plan and returns a structured review result,
including approval status and reported issues. `APPROVED` means the
proposed plan passed the configured review stage---not that the
underlying business tasks were executed.

### Orchestration and context sharing

``` text
Business request
      |
      v
Intake Agent ──> requirements, deadlines, constraints, missing details
      |
      v
Planning Agent ──> tasks, owners, dependencies, unresolved details
      |
      v
Review Agent ──> approval result and reported issues
      |
      v
Workflow result / execution history
```

The orchestrator coordinates the stages. The Planning Agent uses the
structured information produced by Intake, and the Review Agent
evaluates the generated plan. This makes the workflow easier to inspect,
test, and debug.

### Reliability features

-   Shared Gemini client for centralized model configuration.
-   Bounded retries for selected temporary server errors (HTTP 500, 502,
    503, 504).
-   No automatic retries for quota/authentication errors in the shared
    client.
-   Structured schemas for expected data shapes.
-   Workflow status and execution identifiers for tracking.
-   Database-backed history/persistence as implemented in the project.
-   Missing owners and unresolved details can remain visible in the
    result.

### Example workflow result

A tested example requested a customer analytics dashboard. The workflow
extracted a requirements-document task for Priya, a November 15, 2026
deadline, and a data-privacy constraint. It generated implementation and
testing dependencies while leaving their owners unresolved. The recorded
run returned `APPROVED`, `Completed`, and `approved: true`, with no
reported review issues. This demonstrates plan generation and review for
that run---not completion of the actual dashboard.

------------------------------------------------------------------------

# Technology Stack

  -----------------------------------------------------------------------
  Area                                Technology
  ----------------------------------- -----------------------------------
  Language / UI                       Python, Streamlit

  LLM                                 Google Gemini API

  Structured validation               Pydantic

  External integrations               Gmail API and Google Calendar API
                                      (Assignment 1)

  Workflow design                     Modular Python functions and
                                      multi-agent orchestration
                                      (Assignment 2)

  Persistence                         Database layer; Sales Assistant
                                      defaults to local SQLite when
                                      `DATABASE_URL` is not set

  Testing                             pytest

  Deployment / VCS                    Streamlit Community Cloud, Git,
                                      GitHub
  -----------------------------------------------------------------------

## Repository structure

``` text
mudita-ai-assignment/
├── assignment1_sales/
│   ├── conversation.py
│   ├── policy.py
│   ├── qualification.py
│   └── routing.py
├── assignment2_agents/
│   ├── intake_agent.py
│   ├── planning_agent.py
│   ├── review_agent.py
│   └── orchestrator.py
├── core/
│   ├── config.py
│   ├── database.py
│   ├── gemini_client.py
│   └── schemas.py
├── integrations/
│   ├── calendar_client.py
│   └── gmail_client.py
├── docs/
├── tests/
├── sales_app.py
├── app.py
├── requirements.txt
└── .gitignore
```

------------------------------------------------------------------------

# Local Setup

## Prerequisites

-   Python compatible with `requirements.txt` (use the project's tested
    environment where possible).
-   Git.
-   Gemini API key for AI-powered features.
-   Google OAuth authorization/token data if using Gmail or Calendar.

## 1. Clone and install

``` bash
git clone https://github.com/PAWAN0207/mudita-ai-assignment.git
cd mudita-ai-assignment
python -m venv .venv
```

**Windows PowerShell**

``` powershell
.\.venv\Scripts\Activate.ps1
```

**macOS / Linux**

``` bash
source .venv/bin/activate
```

Install dependencies:

``` bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## 2. Environment variables and secrets

Create a local `.env` file in the repository root and set only the
values needed for the features you use:

``` dotenv
GEMINI_API_KEY=replace_with_your_own_key
GEMINI_MODEL=gemini-3.8-flash
DATABASE_URL=
```

-   `GEMINI_API_KEY` --- required for Gemini-powered features.
-   `GEMINI_MODEL` --- optional model override. The shared Gemini client
    defaults to `gemini-3.8-flash`; `core/config.py` has a separate
    default for its configuration consumers. Set this variable
    explicitly if both should use the same model.
-   `DATABASE_URL` --- optional database connection URL. When omitted,
    the Sales Assistant configuration falls back to SQLite under
    `data/`.

For Gmail and Calendar, the integration clients support authorized-user
token JSON through `GMAIL_TOKEN_JSON` and `CALENDAR_TOKEN_JSON`. Local
token files can also be used: - Gmail: `gmail_token.json` - Calendar:
`token.json`

These values/files contain sensitive OAuth information. Never commit
`.env`, `credentials.json`, `gmail_token.json`, `token.json`, API keys,
OAuth tokens, or account credentials. Enable the required Google APIs
and grant only the necessary scopes. Use dedicated test accounts.

## 3. Run each application

**Assignment 1 --- Sales Assistant**

``` bash
streamlit run sales_app.py
```

**Assignment 2 --- Operations Coordinator** (in a second terminal)

``` bash
streamlit run app.py
```

Use the local URL printed by Streamlit.

------------------------------------------------------------------------

# Streamlit Cloud Deployment and Demo Access

-   **Sales Assistant:** https://mudita-sales-assistant.streamlit.app/
-   **Operations Coordinator:**
    https://mudita-operations-coordinator.streamlit.app/

Configure secrets in each app's Streamlit Cloud settings. Do not place
secret values in source code or README files. Secret names used by the
current code include:

``` toml
GEMINI_API_KEY = "..."
GEMINI_MODEL = "gemini-3.8-flash"
GMAIL_TOKEN_JSON = "..."
CALENDAR_TOKEN_JSON = "..."
DATABASE_URL = "..."
```

Configure only the secrets required by the features you intend to
expose. Local SQLite/filesystem persistence may not survive all cloud
restarts or redeploys; verify deployed persistence before relying on it.

### Public-demo security

The Streamlit URLs are publicly reachable. Do not expose a personal
Gmail inbox or personal Calendar to arbitrary visitors. For a public
demo, use a dedicated test Google account, synthetic emails, and a test
calendar. Restrict or disable sensitive integration actions if that
isolation is not in place. Public access to the UI does not
automatically make OAuth-backed actions safe for unrestricted use.

### Seven-day availability checklist

1.  Open both links in a private/incognito browser window.
2.  Confirm each app loads.
3.  Test the main workflow using safe sample data.
4.  Check integration status separately from page-load status.
5.  Keep both deployments available for at least seven days after
    submission.
6.  Recheck the links during that window.

------------------------------------------------------------------------

# Testing

Previously recorded test results:

  Suite                                       Reported result
  ----------------------------------------- -----------------
  Assignment 1 --- Sales Assistant                      11/11
  Assignment 2 --- Operations Coordinator               10/10
  **Total**                                         **21/21**

These are the earlier recorded results, not a guarantee for any later
code revision. Re-run tests against the exact final code before
submission and update this section if results change.

**Sales Assistant safety/calendar tests**

``` bash
python -m pytest test_booking_safety.py test_calendar_booking.py test_calendar_validation.py -v
```

**Operations Coordinator**

``` bash
python -m pytest tests/ -v
```

**Full test discovery (optional)**

``` bash
python -m pytest -v
```

Automated tests do not guarantee live Gemini, Gmail, or Calendar
availability. Live behavior depends on credentials, scopes, quota,
network access, and provider status.

------------------------------------------------------------------------

# Approximate Model Cost per Run

The application does not currently record token usage per workflow. The
numbers below are **illustrative estimates, not measured billing
results**. They assume the published standard paid rates for Gemini 3.8
Flash through December 31, 2026: **US\$0.75 per 1M input tokens** and
**US\$3.75 per 1M output tokens**. See [official Gemini API
pricing](https://ai.google.dev/gemini-api/docs/pricing).

  ------------------------------------------------------------------------
  Workflow              Illustrative token           Approximate paid cost
                        assumption            
  --------------------- --------------------- ----------------------------
  Assignment 1 --- one  1,000 input + 300           **US\$0.0019 per model
  customer-message      output tokens                               call**
  response                                    

  Assignment 2 --- full 6,000 input + 2,000     **US\$0.012 per workflow**
  three-agent workflow  output tokens across  
                        agent calls           
  ------------------------------------------------------------------------

Calculations: - Sales:
`(1,000 × $0.75 + 300 × $3.75) / 1,000,000 ≈ $0.0019` - Operations:
`(6,000 × $0.75 + 2,000 × $3.75) / 1,000,000 = $0.012`

Actual cost depends on model selection, prompt/context size, output
length, retries, and current pricing. Extra retries can increase usage.
Requests covered by an applicable free tier may incur no API charge,
subject to quota and current terms. These estimates should not be
presented as measured costs.

------------------------------------------------------------------------

# Known Limitations

## Assignment 1 --- Sales Assistant

-   Model responses can be malformed or factually incorrect; JSON
    validation checks structure, not truth.
-   Regex-based Gmail extraction can miss unusual wording.
-   Gmail functionality is read-only; the app does not send emails.
-   Instagram and WhatsApp are not connected in this version.
-   Gmail and Calendar features require valid authorized credentials and
    third-party availability.
-   Calendar availability can change between checks. Revalidation and
    duplicate safeguards reduce, but do not eliminate, concurrent
    booking conflicts.
-   Public demos should use dedicated test accounts rather than personal
    inboxes/calendars.

## Assignment 2 --- Operations Coordinator

-   Output quality depends on the completeness of the input and the
    model response.
-   Missing owners or ambiguous requirements may require human
    clarification.
-   `APPROVED` means the proposed plan passed the configured review
    stage; it does not mean tasks were executed.
-   Retries cover selected transient server errors, not all quota,
    permission, authentication, or invalid-request errors.
-   A successful earlier run does not guarantee continuous model
    availability.
-   Persistence and recovery behavior depends on the configured database
    and deployment environment.

## Shared limitations

-   Live API calls depend on credentials, permissions, quota, and
    provider availability.
-   Automated tests do not replace live smoke tests of both deployments.
-   Cost estimates are illustrative; per-run token usage is not
    currently metered.

------------------------------------------------------------------------

# Security Checklist

-   [ ] Keep `.env` out of Git.
-   [ ] Never commit API keys, OAuth client secrets, tokens, or
    credential JSON files.
-   [ ] Use Streamlit Cloud Secrets for deployment secrets.
-   [ ] Use dedicated test Gmail and Calendar accounts for public demos.
-   [ ] Use synthetic, non-sensitive demo data.
-   [ ] Confirm booking actions require explicit confirmation.
-   [ ] Do not expose personal inboxes/calendars to public visitors.
-   [ ] Rotate any secret that may have been published accidentally.

# Loom Walkthrough (8--12 minutes)

The walkthrough should cover both assignments: 1. Build approach,
problem statements, and technology choices. 2. Assignment 1 success
demo: conversation, extracted facts, qualification, routing. 3.
Assignment 1 integrations: Gmail read-only analysis and Calendar
confirmation safeguards. 4. Assignment 2 success demo: Intake, Planning,
Review, dependencies, unresolved owners. 5. Architecture and context
sharing across modules/agents. 6. One real observed failure or edge
case; distinguish incomplete input from a technical failure. 7. One
diagnosed bug: explain its impact and claim a fix only if it has been
implemented and tested. 8. Remaining limitations and conclusion.

Reuse already-tested outputs where possible to conserve API quota. Do
not present a failed live request as a successful result.

## Detailed Documentation

-   [Assignment 1 --- Sales
    Assistant](docs/README_Assignment_1_Sales_Assistant.md)
-   [Assignment 2 --- Operations
    Coordinator](docs/README_Assignment_2_Operations_Coordinator.md)

## Author

**Pawan Ajay Prasad** · Applied AI Engineering · Generative AI · Python
· LLM Applications

-   GitHub: [PAWAN0207](https://github.com/PAWAN0207)
-   Repository:
    [mudita-ai-assignment](https://github.com/PAWAN0207/mudita-ai-assignment)

------------------------------------------------------------------------

*Built as an applied AI engineering project focused on practical LLM
applications, explicit workflow logic, external-service integrations,
safety checks, and testable software design.*
