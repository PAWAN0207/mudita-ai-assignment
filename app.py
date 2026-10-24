import json
import uuid
from datetime import datetime, timezone
from typing import Any

import streamlit as st

from assignment2_agents.orchestrator import (
    get_workflow_history,
    resume_operations_workflow,
    run_operations_workflow,
)

st.set_page_config(
    page_title="Mudita AI | Operations Coordinator",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
      .block-container {padding-top: 1.3rem; padding-bottom: 2rem;}
      .hero {padding: 1.2rem 1.4rem; border-radius: 14px;
             border: 1px solid rgba(128,128,128,.3); margin-bottom: 1rem;}
      .eyebrow {font-size:.75rem; text-transform:uppercase;
                letter-spacing:.12em; opacity:.7;}
      .hero h1 {margin:.25rem 0 .35rem 0;}
      .muted {opacity:.75;}
    </style>
    """,
    unsafe_allow_html=True,
)

SAMPLE_TRANSCRIPT = """Sentence 1: The team decided to launch a customer analytics dashboard.
Sentence 2: Priya will prepare the requirements document.
Sentence 3: The first draft is due on 15 November 2026.
Sentence 4: The dashboard must comply with the company data privacy policy.
Sentence 5: The team has not yet confirmed who will own implementation or testing.
"""

SAMPLE_RULES = {
    "required_controls": [
        "Data privacy compliance",
        "Review tasks before approval",
    ],
    "deadline_policy": (
        "Do not invent deadlines. Use only explicit dates from the transcript."
    ),
    "owner_policy": (
        "Do not assign unconfirmed owners. Use null and raise a question "
        "when ownership is unknown."
    ),
    "dependency_policy": (
        "Dependencies must reference valid task IDs and must not contain cycles."
    ),
    "approval_policy": (
        "A plan must pass review before it is considered approved."
    ),
}


def ensure_state() -> None:
    defaults = {
        "session_id": str(uuid.uuid4()),
        "transcript": SAMPLE_TRANSCRIPT,
        "rules_text": json.dumps(SAMPLE_RULES, indent=2, ensure_ascii=False),
        "latest_result": None,
        "latest_error": None,
        "run_history": [],
        "simulate_failure": False,
        "corrected_fact": "",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def parse_rules(raw: str) -> dict[str, Any]:
    try:
        rules = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Company rules must be valid JSON: {exc}"
        ) from exc

    if not isinstance(rules, dict):
        raise ValueError("Company rules must be a JSON object.")

    return rules


def safe_json(value: Any) -> str:
    try:
        return json.dumps(
            value,
            indent=2,
            ensure_ascii=False,
            default=str,
        )
    except Exception:
        return str(value)


def remember_result(result: Any) -> None:
    """Keep the latest result and a lightweight browser-session history."""
    st.session_state.latest_result = result

    if isinstance(result, dict):
        run_id = result.get("run_id", "unknown")
        status = result.get("status", "unknown")
    else:
        run_id = "unknown"
        status = "unknown"

    # Avoid adding a duplicate entry if Streamlit reruns the page.
    existing_ids = {
        item.get("run_id") for item in st.session_state.run_history
    }
    if run_id not in existing_ids:
        st.session_state.run_history.insert(
            0,
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "run_id": run_id,
                "status": status,
                "result": result,
            },
        )


def run_workflow(transcript: str, company_rules: dict[str, Any]) -> None:
    if not transcript.strip():
        st.session_state.latest_error = (
            "Please enter a meeting transcript before running the agents."
        )
        return

    st.session_state.latest_error = None

    # This is an explicitly labelled UI-only demo fault. It does not call the
    # orchestrator, create a database run, or simulate a real model/API error.
    if st.session_state.simulate_failure:
        st.session_state.latest_error = (
            "Simulated model failure is enabled. No workflow was run and no "
            "database record was created. Disable this option and run again."
        )
        return

    try:
        with st.spinner(
            "Intake → Planning → Review agents are collaborating..."
        ):
            # The orchestrator's actual parameter name is company_rules,
            # not rules.
            result = run_operations_workflow(
                transcript=transcript,
                company_rules=company_rules,
            )

        remember_result(result)

        if isinstance(result, dict) and result.get("status") == "failed":
            st.session_state.latest_error = (
                "The workflow was saved with status FAILED. See the result "
                "panel for the failed stage and error; you can try resuming it."
            )
    except Exception as exc:
        st.session_state.latest_error = (
            f"Workflow failed: {type(exc).__name__}: {exc}"
        )


def resume_workflow(run_id: str) -> None:
    if not run_id.strip():
        st.session_state.latest_error = (
            "No run ID is available to resume."
        )
        return

    st.session_state.latest_error = None
    try:
        with st.spinner("Resuming the saved workflow from its persisted state..."):
            result = resume_operations_workflow(run_id=run_id)

        remember_result(result)

        if isinstance(result, dict) and result.get("status") == "failed":
            st.session_state.latest_error = (
                "The workflow is still failed after the resume attempt. "
                "Check the error and current stage in the result."
            )
    except Exception as exc:
        st.session_state.latest_error = (
            f"Resume failed: {type(exc).__name__}: {exc}"
        )


ensure_state()

st.markdown(
    """
    <div class="hero">
      <div class="eyebrow">Mudita AI · Assignment 2</div>
      <h1>Operations Coordinator</h1>
      <div class="muted">
        Three connected mini-agents: Intake, Planning, and Review.
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)
st.caption(
    "This interface calls the Assignment 2 orchestrator and displays its "
    "persisted workflow history."
)

with st.sidebar:
    st.subheader("Session")
    st.code(st.session_state.session_id, language="text")
    st.write("Each browser session gets its own UI session ID.")
    st.divider()
    st.subheader("Demo controls")
    st.checkbox(
        "Simulate model failure (UI demo only)",
        key="simulate_failure",
        help=(
            "When enabled, the app deliberately skips the workflow and "
            "displays a labelled demo failure. It does not create a database run."
        ),
    )

    if st.button("Reset demo inputs", use_container_width=True):
        st.session_state.session_id = str(uuid.uuid4())
        st.session_state.transcript = SAMPLE_TRANSCRIPT
        st.session_state.rules_text = json.dumps(
            SAMPLE_RULES, indent=2, ensure_ascii=False
        )
        st.session_state.latest_result = None
        st.session_state.latest_error = None
        st.session_state.run_history = []
        st.session_state.corrected_fact = ""
        st.session_state.simulate_failure = False
        st.rerun()

input_tab, result_tab, history_tab = st.tabs(
    [
        "📝 Meeting Input",
        "🤝 Agent Collaboration & Plan",
        "🗂️ Run History",
    ]
)

with input_tab:
    st.subheader("Meeting transcript")
    st.text_area(
        "Paste the meeting transcript",
        key="transcript",
        height=230,
        help=(
            "The Intake Agent should extract facts, cite source references, "
            "and flag missing or conflicting information."
        ),
    )

    st.subheader("Company rules")
    st.caption(
        "Edit the rules as JSON. Keep policy facts explicit so agents do not "
        "invent owners or deadlines."
    )
    st.text_area("Rules JSON", key="rules_text", height=220)

    col_run, col_sample = st.columns(2)

    with col_run:
        run_clicked = st.button(
            "▶ Run Connected Agents",
            type="primary",
            use_container_width=True,
        )

    with col_sample:
        if st.button("Restore sample input", use_container_width=True):
            st.session_state.transcript = SAMPLE_TRANSCRIPT
            st.session_state.rules_text = json.dumps(
                SAMPLE_RULES, indent=2, ensure_ascii=False
            )
            st.session_state.latest_error = None
            st.rerun()

    if run_clicked:
        try:
            parsed_rules = parse_rules(st.session_state.rules_text)
            run_workflow(st.session_state.transcript, parsed_rules)
        except ValueError as exc:
            st.session_state.latest_error = str(exc)

    if st.session_state.latest_error:
        st.error(st.session_state.latest_error)

with result_tab:
    st.subheader("Agent outputs and reviewed action plan")
    result = st.session_state.latest_result

    if not result:
        st.info(
            "Run the workflow from the Meeting Input tab to see the Intake, "
            "Planning, and Review outputs."
        )
    elif not isinstance(result, dict):
        st.warning("The orchestrator returned an unexpected result type.")
        st.code(str(result))
    else:
        run_id = result.get("run_id", "Unavailable")
        status = str(result.get("status", "unknown")).lower()
        current_stage = result.get("current_stage", "unknown")
        attempts = result.get("attempts", 0)

        col1, col2, col3 = st.columns(3)
        col1.metric("Workflow status", status.upper())
        col2.metric("Current stage", str(current_stage).replace("_", " ").title())
        col3.metric("Planning attempts", str(attempts))

        st.caption(f"Run ID: {run_id}")

        if status in {"approved", "success", "completed"}:
            st.success("The workflow completed and the plan was approved.")
        elif status == "needs_human_review":
            st.warning(
                "The review attempt limit was reached. Human review is required."
            )
        elif status in {"failed", "error"}:
            st.error(
                "The workflow failed. Inspect the saved outputs/error below. "
                "If it is still marked failed, you can try resuming it."
            )
        else:
            st.info("Inspect the stage outputs below for the current workflow state.")

        intake = result.get("intake")
        plan = result.get("plan")
        review = result.get("review")
        feedback_history = result.get("feedback_history", [])
        workflow_error = result.get("error")

        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown("### 1. Intake Agent")
            st.caption(
                "Extracts decisions, requirements, constraints, source references, "
                "and missing/conflicting information."
            )
        with c2:
            st.markdown("### 2. Planning Agent")
            st.caption(
                "Proposes tasks, owners, deadlines, dependencies, and unresolved questions."
            )
        with c3:
            st.markdown("### 3. Review Agent")
            st.caption(
                "Checks the plan against the transcript and company rules."
            )

        with st.expander("Intake Agent output", expanded=True):
            st.json(
                intake if intake is not None
                else {"note": "No intake output was persisted."}
            )

        with st.expander("Planning Agent output / action plan", expanded=True):
            st.json(
                plan if plan is not None
                else {"note": "No planning output was persisted."}
            )

        with st.expander("Review Agent output", expanded=True):
            st.json(
                review if review is not None
                else {"note": "No review output was persisted."}
            )

        with st.expander("Review feedback history"):
            st.json(feedback_history)

        if workflow_error:
            st.error(f"Orchestrator error: {workflow_error}")

        with st.expander("Complete workflow result"):
            st.code(safe_json(result), language="json")

        if status == "failed" and run_id != "Unavailable":
            st.divider()
            st.subheader("Resume failed workflow")
            st.caption(
                "The orchestrator resumes using persisted stage outputs. "
                "Only workflows whose database status is 'failed' can be resumed."
            )
            if st.button("↻ Resume this failed workflow", type="primary"):
                resume_workflow(str(run_id))
                st.rerun()

        st.divider()
        st.subheader("Correct a source fact and rerun")
        st.caption(
            "Edit the transcript above, then run a new workflow. A new run ID "
            "will be created using the updated transcript and rules."
        )
        st.text_area(
            "Optional note about the correction",
            key="corrected_fact",
            height=70,
        )
        if st.button("Run new workflow with current transcript and rules"):
            try:
                parsed_rules = parse_rules(st.session_state.rules_text)
                run_workflow(st.session_state.transcript, parsed_rules)
                st.rerun()
            except ValueError as exc:
                st.session_state.latest_error = str(exc)
                st.error(str(exc))

with history_tab:
    st.subheader("Persisted workflow history")
    if st.button("Refresh persisted history"):
        st.rerun()

    try:
        history = get_workflow_history()
        if history:
            st.dataframe(
                history,
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("No persisted workflow runs were found yet.")
    except Exception as exc:
        st.warning(
            f"Could not load persisted history: {type(exc).__name__}: {exc}"
        )

    if st.session_state.run_history:
        st.markdown("#### Runs from this browser session")
        st.dataframe(
            [
                {
                    "timestamp": item["timestamp"],
                    "run_id": item["run_id"],
                    "status": item["status"],
                }
                for item in st.session_state.run_history
            ],
            use_container_width=True,
            hide_index=True,
        )

st.divider()
st.caption(
    "Security note: keep API keys in environment variables or .env and never "
    "commit secrets. This Assignment 2 interface does not represent the "
    "Assignment 1 Instagram/WhatsApp integrations as connected."
)
