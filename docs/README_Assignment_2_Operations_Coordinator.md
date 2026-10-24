# Mudita AI — Operations Coordinator
### Assignment 02 · Three Connected LLM Mini-Agents

A Streamlit prototype that turns a meeting transcript and company rules into a structured action plan using three distinct LLM-powered agents: Intake, Planning, and Review. An orchestrator coordinates the workflow and persists run state so failed workflows can be inspected and, where supported, resumed.

> **Implementation status:** The project includes the three agent modules, a persisted workflow orchestrator, structured schemas, database storage, a Streamlit interface, and automated tests. The latest recorded test run reported **10/10 tests passing**. Live Gemini execution has also encountered a `429` quota-exceeded response, so a successful end-to-end live run must be verified when quota is available.

## Table of Contents
- [Problem and Goal](#problem-and-goal)
- [Agent Responsibilities](#agent-responsibilities)
- [Workflow](#workflow)
- [Architecture](#architecture)
- [Technology Stack](#technology-stack)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Setup](#setup)
- [Run the Application](#run-the-application)
- [Run Tests](#run-tests)
- [Failure Handling and Recovery](#failure-handling-and-recovery)
- [Known Limitations](#known-limitations)
- [Demo Checklist](#demo-checklist)

## Problem and Goal

Meeting notes often contain decisions, requirements, constraints, missing information, and unresolved ownership. This project demonstrates a structured workflow that extracts supported facts, turns them into an actionable plan, and independently reviews that plan against the original transcript and company rules.

The system is designed not to invent owners or deadlines and to surface unresolved questions rather than hiding uncertainty.

## Agent Responsibilities

### 1. Intake Agent
File: `assignment2_agents/intake_agent.py`

- Extracts decisions, requirements, and constraints from a transcript.
- Adds source references and confidence values to extracted facts.
- Flags missing information and conflicting statements.
- Returns structured output validated against the Intake schema.
- Treats transcript content as data rather than instructions.

### 2. Planning Agent
File: `assignment2_agents/planning_agent.py`

- Consumes the structured Intake output and company rules.
- Proposes tasks with owners, deadlines, dependencies, supported fact IDs, recommendations, and unresolved questions.
- Uses `null` for unknown owners or deadlines.
- Validates duplicate task IDs, unknown dependencies, self-dependencies, and dependency cycles.

### 3. Review Agent
File: `assignment2_agents/review_agent.py`

- Checks the plan against the original transcript, Intake output, and company rules.
- Returns structured issues and corrections.
- Applies deterministic checks for duplicate IDs and invalid/circular dependencies.
- Blocks approval when issues remain according to the implemented review policy.

## Workflow

```text
Meeting transcript + company rules
                 |
                 v
            Intake Agent
                 |
       Structured IntakeOutput
                 |
                 v
           Planning Agent
                 |
             Proposed plan
                 |
                 v
            Review Agent
                 |
          +------+------+
          |             |
       Approved       Rejected
          |             |
          v             v
      Completed     Feedback saved
                        |
                        v
                 Planning Agent
                        |
                 Bounded review loop
                        |
                        v
               Approved or human review
```

The orchestrator persists the workflow run and stage outputs. The configured maximum review-attempt count is three.

## Architecture

```text
Streamlit UI (app.py)
        |
        v
Workflow Orchestrator
        |
        +--> Intake Agent
        |
        +--> Planning Agent
        |
        +--> Review Agent
        |
        v
Structured Pydantic schemas
        |
        v
Database persistence
        |
        +--> Run status and current stage
        +--> Intake output
        +--> Proposed plan
        +--> Review output
        +--> Feedback history
```

## Technology Stack

- Python
- Streamlit
- Google Gemini API
- Pydantic structured schemas
- SQLAlchemy and the configured database
- pytest

Refer to `requirements.txt` and the configuration modules for the exact versions and settings in the current environment.

## Project Structure

The current VS Code screenshots show both assignments in a shared workspace. Relevant Assignment 2 files include:

```text
mudita-ai-assignment/
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
├── tests/
│   ├── test_orchestrator.py
│   └── test_review_agent.py
├── app.py
├── requirements.txt
└── .gitignore
```

The tree is representative rather than exhaustive. Keep the actual current files as the source of truth.

## Prerequisites

- Python environment compatible with the project's installed dependencies.
- Gemini API key and available model quota.
- Dependencies installed from `requirements.txt`.

Do not publish `.env`, API keys, tokens, or other secrets.

## Setup

Run commands from the repository root in PowerShell.

```powershell
# Activate an existing virtual environment
.\.venv\Scripts\Activate.ps1

# Or create one if needed
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install dependencies
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Set the Gemini API key using the exact environment-variable name expected by `core/config.py` and `core/gemini_client.py`. Do not commit the key. If you create `.env.example`, include variable names and safe placeholders only.

## Run the Application

```powershell
python -m streamlit run app.py
```

Open the local URL printed by Streamlit. If another process is already using the port, stop that process or use the URL/port Streamlit reports.

## Run Tests

```powershell
python -m pytest tests -v
```

### Previously recorded result

The latest saved test output reported **10 passed**. The covered cases were:

| Test | Recorded result |
|---|---|
| Approved workflow is persisted | PASS |
| Failed review can resume without rerunning Intake | PASS |
| Review retries are bounded | PASS |
| Approved workflow cannot be resumed | PASS |
| History includes current stage | PASS |
| Valid dependencies pass | PASS |
| Self-dependency is detected | PASS |
| Unknown dependency is detected | PASS |
| Circular dependency is detected | PASS |
| Duplicate task IDs are detected | PASS |

These tests verify the listed code paths. They do not by themselves prove that the live Gemini API call succeeds, that every PDF requirement is implemented, or that all session-isolation and context-versioning scenarios have been demonstrated.

## Failure Handling and Recovery

- Workflow runs are assigned a run ID and persisted.
- The orchestrator records status, current stage, agent outputs, and review feedback.
- Failed runs can be inspected and eligible failed runs can be resumed through the implemented resume function.
- Review attempts are bounded.
- Model/provider errors, including quota errors, should be shown as failures rather than misrepresented as successful results.

### Gemini quota note

A previous live run returned HTTP/API error `429` for `gemini-2.5-flash` because the Free Tier request quota was exceeded. A live end-to-end success has therefore not been confirmed in the latest recorded session. Check the Google AI quota dashboard before repeating live runs.

## Known Limitations and Verification Items

- **Live end-to-end workflow:** Re-run once Gemini quota is available and record the actual result.
- **Context versioning and stale-context invalidation:** Verify against the explicit assignment requirement; the presence of database persistence alone does not prove this is fully implemented.
- **Visible handoff messages and agent-level status/input/output:** Confirm the UI exposes each handoff clearly.
- **Source-fact correction:** Demonstrate that a changed fact invalidates or updates dependent outputs rather than leaving stale results.
- **Session isolation:** Test separate browser sessions and confirm that their workflow data is not mixed.
- **Simulated failure recovery:** Demonstrate the required failure and recovery path and label simulated failures clearly.
- **Deployment URL and Loom walkthrough:** Add only after deployment and recording are complete.

## Demo Checklist

- [ ] Run a normal workflow and show Intake, Planning, Review, and final status.
- [ ] Show source references and missing information.
- [ ] Show a review rejection, specific feedback, and a corrected plan.
- [ ] Demonstrate bounded review attempts.
- [ ] Demonstrate a failed run and resume without rerunning completed stages.
- [ ] Change a source fact and show dependent outputs update.
- [ ] Run two separate sessions and verify isolation.
- [ ] Demonstrate simulated failure and recovery.
- [ ] Show run history and persisted state.
- [ ] Run `python -m pytest tests -v` and record the current result.
- [ ] Verify at least one successful live Gemini workflow when quota is available.
