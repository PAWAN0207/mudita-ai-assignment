# Mudita AI — AI-Powered Business Workflow Automation

Two AI application prototypes developed for the Mudita AI Generalist Assignment.

This repository brings together two projects focused on automating business workflows using Large Language Models (LLMs), structured decision-making, external integrations, and validation.

## Projects

### 1. AI Sales Assistant

An AI-assisted sales workflow designed to support customer conversations, qualify incoming leads, route qualified prospects, and schedule meetings through Google Calendar.

**Key capabilities**

* AI-assisted customer conversation.
* Policy-based lead qualification and representative routing.
* Gmail integration for inbox visibility.
* Google Calendar availability and booking.
* Booking confirmation safeguards and duplicate-prevention logic.
* Conversation persistence and action logging.
* Human takeover controls.

**Documentation:** [`docs/README_Assignment_1_Sales_Assistant.md`](docs/README_Assignment_1_Sales_Assistant.md)

**Known limitation:** Instagram and WhatsApp are not connected in the current version.

### 2. Operations Coordinator — Three Connected LLM Agents

A multi-agent workflow that converts meeting transcripts and company rules into a structured action plan.

**Agents**

1. **Intake Agent** — extracts decisions, requirements, constraints, missing information, and conflicts.
2. **Planning Agent** — proposes tasks, ownership, deadlines, dependencies, and unresolved questions.
3. **Review Agent** — evaluates the proposed plan against source information and company rules.

**Workflow capabilities**

* Structured agent inputs and outputs.
* Orchestration and persisted workflow state.
* Review feedback and bounded retries.
* Workflow history and failed-run inspection.
* Resume support for eligible failed workflows.
* Deterministic task-dependency validation.

**Documentation:** [`docs/README_Assignment_2_Operations_Coordinator.md`](docs/README_Assignment_2_Operations_Coordinator.md)

**Known limitation:** A previous live Gemini API run encountered a quota-exceeded `429` error. Successful live execution must be verified when API quota is available.

## Technology Stack

The projects use technologies including:

* Python
* Streamlit
* Google Gemini API
* Google Gmail API
* Google Calendar API
* Pydantic
* SQLAlchemy
* pytest

Refer to each project's documentation and `requirements.txt` for setup details.

## Repository Structure

```text
mudita-ai-assignment/
├── assignment1_sales/
├── assignment2_agents/
├── core/
├── integrations/
├── pages/
├── tests/
├── docs/
│   ├── README_Assignment_1_Sales_Assistant.md
│   └── README_Assignment_2_Operations_Coordinator.md
├── app.py
├── sales_app.py
├── requirements.txt
├── .gitignore
└── README.md
```

This is a representative overview of the repository. Refer to the actual project files for the complete structure.

## Setup and Execution

Use the dedicated documentation for installation, environment configuration, integrations, and application-specific commands:

* [Assignment 1 — Sales Assistant](docs/README_Assignment_1_Sales_Assistant.md)
* [Assignment 2 — Operations Coordinator](docs/README_Assignment_2_Operations_Coordinator.md)

Before running either application, configure the required credentials locally. Never commit API keys, OAuth credentials, access tokens, or other secrets.

## Testing

The previously recorded test results were:

| Project                | Recorded result                                   |
| ---------------------- | ------------------------------------------------- |
| Sales Assistant        | 11/11 calendar safety and validation tests passed |
| Operations Coordinator | 10/10 automated tests passed                      |

These are historical test results and should be reconfirmed against the exact code being submitted. Automated tests do not establish that every external integration or live LLM workflow is currently available.

## Security and Responsible Use

* Keep secrets and OAuth tokens out of version control.
* Use authorised test accounts and calendars.
* Require explicit confirmation before creating calendar bookings.
* Validate structured model outputs before using them.
* Treat external messages and transcripts as untrusted input.
* Document provider limitations and unverified functionality honestly.

## Project Status

Both projects have core implementations and previously recorded passing tests. Some external integrations and end-to-end scenarios still require verification. See the individual project documentation for known limitations and current testing context.

## Author

**Pawan Prasad**

AI Engineering | Generative AI | LLM Applications | Workflow Automation
