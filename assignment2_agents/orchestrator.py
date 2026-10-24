
import json
import uuid
from datetime import datetime, timezone

from core.database import (
    SessionLocal,
    WorkflowRun,
    init_database,
)

from core.schemas import (
    IntakeOutput,
    PlannedTask,
    ReviewOutput,
)

from assignment2_agents.intake_agent import run_intake_agent
from assignment2_agents.planning_agent import run_planning_agent
from assignment2_agents.review_agent import run_review_agent


MAX_REVIEW_ATTEMPTS = 3


# ============================================================
# UTILITIES
# ============================================================

def utc_now():
    return datetime.now(timezone.utc)


def save_run(db, record):
    """Persist the current workflow state."""
    record.updated_at = utc_now()
    db.commit()
    db.refresh(record)


def json_load(value, default=None):
    """Safely decode persisted JSON."""
    if not value:
        return default

    return json.loads(value)


def build_result(record):
    """Reconstruct the public workflow result from database state."""

    return {
        "run_id": record.run_id,
        "status": record.status,
        "current_stage": record.current_stage,
        "intake": json_load(record.intake_json),
        "plan": json_load(record.plan_json, []),
        "review": json_load(record.review_json),
        "attempts": record.attempts,
        "feedback_history": json_load(
            record.feedback_history_json,
            [],
        ),
        "error": record.error,
    }


def persist_feedback(db, record, feedback_history):
    record.feedback_history_json = json.dumps(
        feedback_history,
        ensure_ascii=False,
    )
    save_run(db, record)


def persist_intake(db, record, intake):
    record.intake_json = json.dumps(
        intake.model_dump(),
        ensure_ascii=False,
    )
    record.current_stage = "planning"
    save_run(db, record)


def persist_plan(db, record, tasks):
    record.plan_json = json.dumps(
        [task.model_dump() for task in tasks],
        ensure_ascii=False,
    )
    record.current_stage = "review"
    save_run(db, record)


def persist_review(db, record, review):
    record.review_json = json.dumps(
        review.model_dump(),
        ensure_ascii=False,
    )
    save_run(db, record)


def make_feedback(review):
    """Convert review issues into planning instructions."""

    feedback = [
        (
            f"{issue.issue} "
            f"Required correction: {issue.correction}"
        )
        for issue in review.issues
    ]

    feedback.extend(
        "Unresolved question: " + question
        for question in review.unresolved_issues
    )

    return feedback


# ============================================================
# WORKFLOW EXECUTION
# ============================================================

def _execute_workflow(record, db):
    """
    Execute or resume a persisted workflow.

    Stages:
        intake   -> planning -> review
        planning -> review
        review   -> review current saved plan

    Completed saved stages are reused whenever possible.
    """

    transcript = record.transcript

    company_rules = json_load(
        record.company_rules_json,
        {},
    )

    feedback_history = json_load(
        record.feedback_history_json,
        [],
    )

    result = build_result(record)

    record.status = "running"
    record.error = None
    save_run(db, record)

    # --------------------------------------------------------
    # STAGE 1: INTAKE
    # --------------------------------------------------------

    if not record.intake_json:
        record.current_stage = "intake"
        save_run(db, record)

        intake = run_intake_agent(
            transcript=transcript,
            company_rules=company_rules,
        )

        persist_intake(db, record, intake)

    else:
        intake = IntakeOutput.model_validate(
            json_load(record.intake_json)
        )

        # If the stored stage says intake, its output is already
        # persisted, so continue to planning instead of rerunning.
        if record.current_stage == "intake":
            record.current_stage = "planning"
            save_run(db, record)

    # --------------------------------------------------------
    # LOAD PREVIOUS FEEDBACK
    # --------------------------------------------------------

    feedback = []

    if feedback_history:
        feedback = feedback_history[-1].get(
            "feedback",
            [],
        )

    # --------------------------------------------------------
    # STAGES 2 AND 3: PLANNING + REVIEW
    # --------------------------------------------------------

    while record.attempts < MAX_REVIEW_ATTEMPTS:

        # If a plan was saved and the last stage was review,
        # reuse the plan and retry review without regenerating it.
        reuse_saved_plan = (
            record.current_stage == "review"
            and bool(record.plan_json)
        )

        if reuse_saved_plan:
            tasks = [
                PlannedTask.model_validate(item)
                for item in json_load(record.plan_json, [])
            ]

        else:
            # A new planning attempt is needed.
            record.current_stage = "planning"
            record.attempts += 1
            save_run(db, record)

            tasks = run_planning_agent(
                intake=intake,
                company_rules=company_rules,
                review_feedback=feedback,
            )

            persist_plan(db, record, tasks)

        # At this point the plan is persisted and the next stage
        # is review. A failure here can resume from the saved plan.
        record.current_stage = "review"
        save_run(db, record)

        review = run_review_agent(
            transcript=transcript,
            intake=intake,
            tasks=tasks,
            company_rules=company_rules,
        )

        persist_review(db, record, review)

        if review.approved:
            record.status = "approved"
            record.current_stage = "completed"
            record.completed = True
            record.error = None
            save_run(db, record)

            return build_result(record)

        # Review rejected the plan: persist feedback for the
        # next planning attempt.
        feedback = make_feedback(review)

        feedback_history.append(
            {
                "attempt": record.attempts,
                "feedback": feedback.copy(),
            }
        )

        persist_feedback(
            db,
            record,
            feedback_history,
        )

        # The saved plan was reviewed but not approved.
        # The next loop iteration must create a corrected plan.
        record.current_stage = "planning"
        save_run(db, record)

    # --------------------------------------------------------
    # HUMAN REVIEW REQUIRED
    # --------------------------------------------------------

    record.status = "needs_human_review"
    record.current_stage = "completed"
    record.completed = False
    record.error = None
    save_run(db, record)

    return build_result(record)


# ============================================================
# CREATE A NEW WORKFLOW
# ============================================================

def run_operations_workflow(
    transcript: str,
    company_rules: dict,
) -> dict:

    if not transcript or not transcript.strip():
        raise ValueError("Transcript cannot be empty.")

    if not isinstance(company_rules, dict):
        raise ValueError("company_rules must be a dictionary.")

    init_database()

    run_id = str(uuid.uuid4())

    db = SessionLocal()

    try:
        record = WorkflowRun(
            run_id=run_id,
            status="running",
            current_stage="intake",
            transcript=transcript,
            company_rules_json=json.dumps(
                company_rules,
                ensure_ascii=False,
            ),
            feedback_history_json="[]",
            attempts=0,
            completed=False,
        )

        db.add(record)
        db.commit()
        db.refresh(record)

        try:
            return _execute_workflow(record, db)

        except Exception as exc:
            db.rollback()

            # Reload the record so already committed outputs and
            # stage information are preserved.
            record = (
                db.query(WorkflowRun)
                .filter(WorkflowRun.run_id == run_id)
                .one()
            )

            record.status = "failed"
            record.error = str(exc)
            record.completed = False
            save_run(db, record)

            return build_result(record)

    finally:
        db.close()


# ============================================================
# RESUME A FAILED WORKFLOW
# ============================================================

def resume_operations_workflow(run_id: str) -> dict:
    """
    Resume a failed workflow using its persisted state.

    Only failed workflows can be resumed through this function.
    Approved and human-review workflows remain unchanged.
    """

    if not run_id or not run_id.strip():
        raise ValueError("run_id cannot be empty.")

    init_database()

    db = SessionLocal()

    try:
        record = (
            db.query(WorkflowRun)
            .filter(WorkflowRun.run_id == run_id)
            .one_or_none()
        )

        if record is None:
            raise ValueError(
                f"No workflow found for run_id: {run_id}"
            )

        if record.status != "failed":
            raise ValueError(
                "Only failed workflows can be resumed. "
                f"Current status: {record.status}"
            )

        if record.completed:
            raise ValueError(
                "This workflow is already marked completed."
            )

        # The stage and outputs were committed before each agent
        # call. Resume uses these values to avoid rerunning
        # previously persisted stages.
        try:
            return _execute_workflow(record, db)

        except Exception as exc:
            db.rollback()

            record = (
                db.query(WorkflowRun)
                .filter(WorkflowRun.run_id == run_id)
                .one()
            )

            record.status = "failed"
            record.error = str(exc)
            record.completed = False
            save_run(db, record)

            return build_result(record)

    finally:
        db.close()


# ============================================================
# WORKFLOW HISTORY
# ============================================================

def get_workflow_history(limit: int = 20) -> list[dict]:
    """Return recent persisted workflow runs."""

    if limit < 1:
        raise ValueError("Limit must be at least 1.")

    init_database()

    db = SessionLocal()

    try:
        records = (
            db.query(WorkflowRun)
            .order_by(WorkflowRun.created_at.desc())
            .limit(limit)
            .all()
        )

        return [
            {
                "run_id": record.run_id,
                "status": record.status,
                "current_stage": record.current_stage,
                "attempts": record.attempts,
                "error": record.error,
                "completed": record.completed,
                "created_at": (
                    record.created_at.isoformat()
                    if record.created_at
                    else None
                ),
                "updated_at": (
                    record.updated_at.isoformat()
                    if record.updated_at
                    else None
                ),
            }
            for record in records
        ]

    finally:
        db.close()
