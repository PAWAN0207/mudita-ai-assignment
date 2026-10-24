# Mudita AI Engineering Portfolio

### AI Sales Automation | Multi-Agent Workflow Orchestration | LLM-Powered Applications

A portfolio of two Python-based AI applications demonstrating conversational sales automation, workflow orchestration, agent collaboration, and integration with external services.

The project combines modular Python development, Streamlit interfaces, automated testing, and LLM integration to explore practical AI engineering use cases.

**Project Status: Implemented and locally tested**

**Automated Testing: 21/21 tests passed**

---

## Applications

### 01 · AI Sales Assistant

A conversational application designed to support lead qualification, customer conversation management, routing, and scheduling workflows.

**Key capabilities**

* Structured conversational workflows
* Lead qualification and routing
* Conversation and policy management
* Google Calendar scheduling integration
* Gmail integration
* Booking validation and duplicate-booking safeguards

**Application entry point:** `sales_app.py`

**Detailed documentation:** [Sales Assistant Documentation](docs/README_Assignment_1_Sales_Assistant.md)

**Live Demo:** Add the deployed application URL here after deployment.

---

### 02 · Multi-Agent Operations Coordinator

An LLM-powered workflow application built around three specialized agents: Intake, Planning, and Review.

The workflow is designed to transform operational inputs into structured plans and review their outputs against defined requirements.

**Key capabilities**

* Specialized Intake, Planning, and Review agents
* Workflow orchestration and agent handoffs
* Dependency validation
* Workflow persistence and execution history
* Review retries with bounded attempts
* Failure recovery and workflow resumption
* Automated tests for workflow behavior and validation

**Application entry point:** `app.py`

**Detailed documentation:** [Operations Coordinator Documentation](docs/README_Assignment_2_Operations_Coordinator.md)

**Live Demo:** Add the deployed application URL here after deployment.

---

## Architecture Overview

```text
                 MUDITA AI ASSIGNMENT
                          |
             +------------+------------+
             |                         |
      AI Sales Assistant       Operations Coordinator
             |                         |
     Conversation Flow          Intake Agent
             |                         |
     Qualification & Routing    Planning Agent
             |                         |
     Gmail / Calendar           Review Agent
             |                         |
     Booking Workflows          Orchestrator / Database
             |                         |
             +------------+------------+
                          |
                 Streamlit Interfaces
```

The applications are organized into reusable modules to separate interface logic, business workflows, integrations, and shared components.

---

## Technology Stack

| Category          | Technologies                |
| ----------------- | --------------------------- |
| Language          | Python                      |
| User Interface    | Streamlit                   |
| AI / LLM          | Google Gemini integration   |
| Workflow Design   | Modular agent orchestration |
| Integrations      | Gmail, Google Calendar      |
| Persistence       | Database components         |
| Testing           | Pytest                      |
| Version Control   | Git, GitHub                 |
| Deployment Target | Streamlit Community Cloud   |

---

## Quality & Testing

Automated tests cover core workflow behavior, validation, and safety-related scenarios.

| Application                        | Automated Tests Passed |
| ---------------------------------- | ---------------------: |
| AI Sales Assistant                 |                  11/11 |
| Multi-Agent Operations Coordinator |                  10/10 |
| **Total**                          |              **21/21** |

**Testing result: All 21 reported automated tests passed.**

The tests include calendar booking validation, duplicate-booking prevention, workflow persistence, dependency validation, review retry limits, and workflow recovery scenarios.

Automated test results are distinct from external-service availability. Live integrations may depend on API credentials, permissions, quotas, and service availability.

---

## Repository Structure

```text
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
├── docs/
│   ├── README_Assignment_1_Sales_Assistant.md
│   └── README_Assignment_2_Operations_Coordinator.md
├── integrations/
│   ├── calendar_client.py
│   └── gmail_client.py
├── tests/
├── app.py
├── sales_app.py
├── requirements.txt
└── .gitignore
```

---

## Run Locally

### 1. Clone the repository

```bash
git clone https://github.com/PAWAN0207/mudita-ai-assignment.git
cd mudita-ai-assignment
```

### 2. Create and activate a virtual environment

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Launch the Sales Assistant

```bash
streamlit run sales_app.py
```

### 5. Launch the Operations Coordinator

Open a separate terminal, activate the environment, and run:

```bash
streamlit run app.py
```

Configure required API keys and service credentials locally before using integrations that depend on external services.

---

## Run Automated Tests

### Sales Assistant

```bash
python -m pytest test_booking_safety.py test_calendar_booking.py test_calendar_validation.py -v
```

### Operations Coordinator

```bash
python -m pytest tests/ -v
```

---

## Security

* Secrets and local credentials are excluded through `.gitignore`.
* API keys and OAuth credentials should be configured outside the source code.
* Public deployment requires secure configuration of external service credentials.
* Never commit `.env`, OAuth credential files, or access tokens to GitHub.

---

## Project Documentation

* [AI Sales Assistant — Technical Documentation](docs/README_Assignment_1_Sales_Assistant.md)
* [Multi-Agent Operations Coordinator — Technical Documentation](docs/README_Assignment_2_Operations_Coordinator.md)

---

## Author

**Pawan Ajay Prasad**

AI Engineering · Generative AI · Python · LLM Applications

GitHub: [PAWAN0207](https://github.com/PAWAN0207)

---

*Built as an applied AI engineering project focused on modular application design, workflow automation, and testable AI systems.*
