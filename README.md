<div align="center">
# 🤖 Mudita AI — Applied AI Engineering Assignments
**AI Sales Assistant · AI Operations Coordinator**

Two practical AI applications combining LLMs, structured workflows, real integrations, and human-centred safeguards.

[![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python&logoColor=white)](https://www.python.org/)

[![Streamlit](https://img.shields.io/badge/Streamlit-Apps-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io/)

[![Google Gemini](https://img.shields.io/badge/LLM-Google%20Gemini-4285F4?logo=googlegemini&logoColor=white)](https://ai.google.dev/)

[![Tests](https://img.shields.io/badge/Tests-22%20Passed-brightgreen)](#testing)

[![Deployment](https://img.shields.io/badge/Deployment-Streamlit%20Cloud-FF4B4B)](https://streamlit.io/cloud)

</div>

---
## 🚀 Live Applications
### Assignment 1 — AI Sales Assistant
[🔗 Open Sales Assistant Live App](https://mudita-sales-assistant.streamlit.app/)

Customer conversations, lead qualification, Gmail lead analysis, Calendar availability and booking, human takeover, and action logs.
### Assignment 2 — AI Operations Coordinator
[🔗 Open Operations Coordinator Live App](https://mudita-operations-coordinator.streamlit.app/)

Submit a business request and inspect the Intake → Planning → Review multi-agent workflow.

> **Demo access:** Open either link in your browser; local installation is not required to view the hosted app. Live feature availability depends on deployment configuration, API quota, and third-party authorization. Use synthetic, non-sensitive demo data only.

---
## 🎥 Full Project Walkthrough

Watch the complete project demo to see both applications in action: the AI Sales Assistant and the AI Operations Coordinator. The walkthrough covers the main features and end-to-end workflows.

[▶️ Watch the Full Project Demo on Loom](https://www.loom.com/share/9d17b22aadfe48e9bbb52e88632c0385)

---
## 📌 Project Overview
This repository contains two independent Streamlit applications built for practical AI workflow automation.

- **AI Sales Assistant:** Supports customer conversations, lead qualification, representative routing, Gmail-based lead analysis, and appointment scheduling.

- **AI Operations Coordinator:** Converts unstructured business instructions into a structured task plan using three specialized agents.

The central design principle is to **combine LLM language understanding with explicit Python business rules, structured validation, real integrations, and clear workflow boundaries** rather than relying on a single unconstrained prompt.
## ✨ What Makes This Project Stand Out?
- **Structured AI responses:** The Sales Assistant requests JSON and validates the response with a Pydantic model before using extracted facts.

- **LLM/business-logic separation:** Gemini supports natural-language understanding; dedicated Python functions handle lead qualification and representative routing.

- **Real Gmail retrieval:** Retrieves emails and analyses selected content using pattern/regex-based extraction. The inbox workflow is read-only.

- **Confirmation-gated scheduling:** Booking requires explicit confirmation, validates required details, checks availability, and handles duplicate/conflict outcomes.

- **Human takeover:** A representative can pause AI message processing and resume it when appropriate.

- **Three specialized agents:** Intake, Planning, and Review have distinct responsibilities and pass structured context between stages.

- **Transparent missing information:** Unresolved task owners remain visible instead of being silently invented.

- **Traceability:** Conversation/workflow persistence and action/execution history support review and debugging.

- **Modular, testable design:** UI, business rules, integrations, schemas, model access, and orchestration are separated into dedicated modules.

---
# Assignment 1 — AI Sales Assistant
## Objective
Reduce repetitive sales operations by bringing customer conversations, lead qualification, representative routing, inbound email analysis, and appointment scheduling into one interface.
## Key Features
### Customer Conversation
- Uses Google Gemini to generate context-aware customer responses.

- Includes company policy and conversation history in the prompt.

- Requests structured output containing a reply, extracted facts, and follow-up status.

- Validates the response using the `SalesConversationResponse` schema.

- Filters extracted facts to supported fields such as service interest, budget, and timeline.

- Instructs the model not to invent unsupported services or claim a booking before confirmation.
### Lead Qualification & Representative Routing
- Uses a dedicated Python qualification function to evaluate service interest, budget, and timeline against configured business rules.

- Separates language interpretation from qualification logic.

- Routes qualified leads through a dedicated representative-assignment function.

- Preserves missing information rather than treating unknown values as confirmed facts.
### Gmail Inbox Analysis
- Checks the Gmail connection and retrieves recent emails.

- Supports selecting up to 50 recent emails.

- Retrieves full details for a selected email before analysis.

- Uses configured service names and regex/pattern matching to extract service interest, budget, and timeline.

- Reuses lead qualification and routing logic after extraction.

- **Read-only workflow:** does not send, delete, or modify emails.
### Google Calendar Availability & Booking
- Checks available 30-minute appointment slots within configured business hours.

- Uses the `Asia/Kolkata` timezone in the Calendar client.

- Requires explicit confirmation before creating a booking.

- Validates required customer details and date/time constraints.

- Rechecks availability in the conversation booking flow before event creation.

- Handles outcomes such as `booked`, `already_booked`, and `booking_conflict`.
### Human Takeover & Action Logs
- Pauses AI message processing while human takeover is active.

- Provides a control to resume AI handling.

- Persists conversation information and records actions through the database layer.

- Includes an Action Logs view to inspect recorded activity.
## Architecture
```text

Customer / Sales User

         |

         v

    Streamlit UI

         |

    +----+---------------------------+

    |                                |

    v                                v

Customer Conversation             Gmail Client

    |                                |

    v                                v

Shared Gemini Client          Pattern/Regex Analysis

    |                                |

    +---------------+----------------+

                    v

            Extracted Lead Facts

                    |

                    v

            Lead Qualification

                    |

                    v

          Representative Routing

Calendar Client <--> Availability Check

                            |

                            v

                  Explicit Confirmation

                            |

                            v

                     Recheck & Booking

Conversation State / Actions --> Database & Action Logs

Human Takeover ----------------> Pauses AI message processing

```
### Conversation Data Flow
1. The customer submits a message.

2. The application checks input validity and human-takeover state.

3. Normal messages are processed with company policy and conversation history.

4. Gemini returns a structured response.

5. The response is parsed and validated before extracted facts are used.

6. The application evaluates the lead and may route a qualified lead.

7. Conversation state and key actions can be persisted.

8. Appointment requests follow a separate availability and confirmation workflow.

---
# Assignment 2 — AI Operations Coordinator
## Objective
Transform unstructured business instructions into a structured, reviewable action plan through three specialized agents.
## The Three Agents
### 1. Intake Agent — Understand the Request
Extracts the business objective, requirements, deadlines, constraints, missing information, and potential conflicts from the original request.
### 2. Planning Agent — Build the Task Plan
Uses the structured intake information to generate tasks, owners where known, and dependencies.

Example plan:

```text

TASK-001: Prepare requirements document (Owner: Priya)

                         |

                         v

TASK-002: Implement dashboard (Owner: Unassigned)

                         |

                         v

TASK-003: Test dashboard (Owner: Unassigned)

```

This example illustrates proposed dependencies; it does not mean the tasks have been executed. Unknown owners remain unresolved rather than being invented.
### 3. Review Agent — Evaluate the Plan
Reviews the generated plan and returns a structured result that includes approval status and reported issues.

**Important:** `APPROVED` means the proposed plan passed the configured review stage. It does **not** mean the underlying business work has been completed.
## Orchestration & Context Sharing
```text

                 Business Request

                        |

                        v

                  Intake Agent

                        |

             Structured intake context

                        |

                        v

                  Planning Agent

                        |

                Proposed task plan

                        |

                        v

                   Review Agent

                        |

                        v

                 Workflow Result

           Orchestrator coordinates stages

```

The orchestrator coordinates the sequence and passes information between stages. Planning uses the structured intake output, and Review evaluates the generated plan. This separation makes the workflow easier to inspect, test, and debug.
## Reliability Features
- Shared Gemini client for centralized model configuration and error handling.

- Bounded retries for selected temporary server errors (HTTP 500, 502, 503, and 504).

- Structured schemas for expected data shapes.

- Workflow status and execution identifiers for tracking.

- Database-backed history/persistence as implemented in the project.

- Unresolved task owners and other missing information can remain visible in the result.
## Example Workflow Result
A tested example requested a plan for launching a customer analytics dashboard. The workflow identified a requirements-document task for Priya, a November 15, 2026 deadline, and a data-privacy constraint. It generated implementation and testing dependencies while leaving their owners unresolved. The recorded result was `APPROVED`, with the workflow marked `Completed` and no reported review issues. This demonstrates plan generation and review for that run—not implementation or testing of the actual dashboard.

---
## Technology Stack
| **Layer** | **Technology** | **Purpose** |

|---|---|---|

| Language | Python | Application and workflow logic |

| User interface | Streamlit | Interactive web applications |

| LLM | Google Gemini API | Natural-language understanding and generation |

| Schema validation | Pydantic | Validate structured model responses |

| Email integration | Gmail API | Read and analyse selected emails (Assignment 1) |

| Scheduling integration | Google Calendar API | Availability and appointment booking (Assignment 1) |

| Workflow orchestration | Modular Python functions and three-agent workflow | Coordinate Intake, Planning, and Review (Assignment 2) |

| Persistence | Database layer / SQLite fallback | Store conversation and workflow information as configured |

| Testing | pytest | Automated tests |

| Hosting | Streamlit Community Cloud | Public demo applications |

| Version control | Git and GitHub | Source control and repository hosting |
## Repository Structure
```text

mudita-ai-assignment/

├── assignment1_sales/

│   ├── conversation.py       # Gemini-powered customer conversation

│   ├── policy.py             # Company policy and defaults

│   ├── qualification.py      # Lead qualification rules

│   └── routing.py            # Representative assignment

├── assignment2_agents/

│   ├── intake_agent.py       # Request understanding and extraction

│   ├── planning_agent.py    # Task planning and dependencies

│   ├── review_agent.py      # Plan review

│   └── orchestrator.py     # Agent coordination and handoffs

├── core/

│   ├── config.py             # Shared configuration

│   ├── database.py           # Persistence and action history

│   ├── gemini_client.py      # Shared Gemini API client

│   └── schemas.py            # Structured response schemas

├── integrations/

│   ├── calendar_client.py    # Calendar availability and booking

│   └── gmail_client.py       # Gmail connection and retrieval

├── docs/                     # Assignment-specific documentation

├── tests/                    # Automated tests

├── sales_app.py              # Assignment 1 Streamlit entry point

├── app.py                    # Assignment 2 Streamlit entry point

├── requirements.txt

└── .gitignore

```

---
## Local Setup
### Prerequisites
- Python version compatible with `requirements.txt` (use the environment in which the project was tested).

- Git.

- A Gemini API key for AI-powered features.

- Google OAuth authorization/token data for Gmail and Calendar features.
### 1. Clone the repository
```bash

git clone https://github.com/PAWAN0207/mudita-ai-assignment.git

cd mudita-ai-assignment

```
### 2. Create and activate a virtual environment
**Windows PowerShell**

```powershell

python -m venv .venv

..venv\Scripts\Activate.ps1

```

**macOS / Linux**

```bash

python3 -m venv .venv

source .venv/bin/activate

```
### 3. Install dependencies
```bash

python -m pip install --upgrade pip

pip install -r requirements.txt

```
### 4. Configure environment variables
Create a local `.env` file in the repository root and set only the values needed for your setup.

```dotenv

GEMINI_API_KEY=your_own_api_key

GEMINI_MODEL=gemini-3.8-flash

DATABASE_URL=

```

| **Variable** | **Purpose** |

|---|---|

| `GEMINI_API_KEY` | API key used by Gemini-powered features. |

| `GEMINI_MODEL` | Optional model override. The shared Gemini client defaults to `gemini-3.8-flash`; `core/config.py` has a separate default for its configuration consumers. Set it explicitly if both should use the same model. |

| `DATABASE_URL` | Optional database connection URL. When omitted, the Sales Assistant configuration falls back to a local SQLite database under `data/`. |

| `GMAIL_TOKEN_JSON` | Authorized-user OAuth token JSON for Gmail, when configured through environment variables or deployment secrets. |

| `CALENDAR_TOKEN_JSON` | Authorized-user OAuth token JSON for Calendar, when configured through environment variables or deployment secrets. |

The Gmail and Calendar clients may also use local token files expected by their implementation (Gmail: `gmail_token.json`; Calendar: `token.json`). Enable the required Google APIs and grant only the scopes the application needs.

> **Security:** Never commit `.env`, `credentials.json`, `gmail_token.json`, `token.json`, API keys, OAuth tokens, or account credentials. Use dedicated test accounts for demonstrations.
### 5. Run Assignment 1 — Sales Assistant
```bash

streamlit run sales_app.py

```
### 6. Run Assignment 2 — Operations Coordinator
Open a second terminal, activate the same environment, and run:

```bash

streamlit run app.py

```

Open the local URL printed by Streamlit for each app.

---
## Streamlit Cloud Deployment & Demo Access
### Assignment 1 — AI Sales Assistant
**Live URL:** https://mudita-sales-assistant.streamlit.app/
### Assignment 2 — AI Operations Coordinator
**Live URL:** https://mudita-operations-coordinator.streamlit.app/

Configure required secrets in the corresponding Streamlit Cloud app settings. Do not store secret values in source code or this README.

Example **secret names** (configure only those required by the deployed features):

```toml

GEMINI_API_KEY = "..."

GEMINI_MODEL = "gemini-3.8-flash"

GMAIL_TOKEN_JSON = "..."

CALENDAR_TOKEN_JSON = "..."

DATABASE_URL = "..."

```
### Public Demo Safety
The app URLs are public. Do not expose a personal Gmail inbox or personal Calendar to arbitrary visitors. Use a dedicated test Google account, synthetic emails, and a test calendar. Restrict or disable sensitive actions if that isolation is not configured. Public UI access does not automatically make OAuth-backed operations safe for unrestricted public use.

---
## Testing
### Automated test result: **22 tests passed
Run the test suite against the final code before submission to ensure the result matches the exact version being submitted.

```bash

python -m pytest -v

```

If tests are split into separate suites, run the test paths present in the repository. Tests can validate local logic and mocked behavior, but they do not guarantee live Gemini, Gmail, or Calendar availability. Live behavior depends on credentials, permissions, quota, network access, and provider status.

---
## Approximate Model Cost per Run
The application does not currently meter token usage per workflow, so the figures below are **illustrative estimates, not measured billing results**. They assume example paid rates of **US$0.75 per 1 million input tokens** and **US$3.75 per 1 million output tokens** for the selected Gemini model. Check the [official Gemini API pricing page](https://ai.google.dev/gemini-api/docs/pricing) before submission because model rates and terms can change.

| **Workflow** | **Example token assumption** | **Approximate cost** |

|---|---|---:|

| Assignment 1 — one customer response | 1,000 input + 300 output tokens | **US$0.0019 per model call** |

| Assignment 2 — three-agent workflow | 6,000 input + 2,000 output tokens across all agent calls | **US$0.012 per workflow** |

**Calculations**

- Sales: `(1,000 × $0.75 + 300 × $3.75) / 1,000,000 ≈ $0.0019`

- Operations: `(6,000 × $0.75 + 2,000 × $3.75) / 1,000,000 = $0.012`

Actual cost depends on model selection, prompt/context size, output length, retries, and current provider pricing. Extra retries may increase usage. Requests covered by an applicable free tier may incur no API charge, subject to quota and current terms. These estimates are not measured per-run costs.

---
## Known Limitations
### Assignment 1 — Sales Assistant
- Model responses can be malformed or factually incorrect; schema validation checks structure, not truth.

- Regex-based Gmail extraction may miss information expressed in unusual wording.

- Gmail functionality is read-only; the app does not send emails.

- Instagram and WhatsApp are not connected in this version.

- Gmail and Calendar features require valid authorization and depend on third-party availability.

- Calendar availability can change between checks. Revalidation and duplicate safeguards reduce, but do not eliminate, concurrent booking conflicts.

- Public demonstrations should use dedicated test accounts rather than personal inboxes or calendars.
### Assignment 2 — Operations Coordinator
- Output quality depends on input completeness and model responses.

- Missing owners or ambiguous requirements may require human clarification.

- `APPROVED` indicates the proposed plan passed the configured review stage; it does not mean tasks were executed.

- Retries cover selected transient server errors, not every quota, permission, authentication, or invalid-request error.

- A successful run does not guarantee continuous model availability.

- Persistence and recovery behavior depends on the configured database and hosting environment.
### Shared Limitations
- Live API calls depend on credentials, permissions, quota, network, and provider availability.

- Automated tests do not replace a live smoke test of each deployed application.

- Cost estimates are illustrative; per-run token usage is not currently metered.

---
## Security Checklist
- [ ] Keep `.env` out of Git.

- [ ] Never commit API keys, OAuth client secrets, access tokens, or credential JSON files.

- [ ] Store deployment secrets in Streamlit Cloud Secrets.

- [ ] Use dedicated test Gmail and Calendar accounts.

- [ ] Use synthetic, non-sensitive demo data.

- [ ] Require explicit confirmation for booking actions.

- [ ] Do not expose personal inboxes/calendars to public visitors.

- [ ] Rotate any secret that may have been published accidentally.

---
## Author
**Pawan Ajay Prasad**  

Applied AI Engineering · Generative AI · Python · LLM Applications

- **GitHub:** [PAWAN0207](https://github.com/PAWAN0207)

- **Repository:** [mudita-ai-assignment](https://github.com/PAWAN0207/mudita-ai-assignment)

---

<div align="center">

Built with a focus on practical AI workflows, clear architecture, external integrations, safety, and testability.

</div>
