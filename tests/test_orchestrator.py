
import json
from unittest.mock import patch

import pytest

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
from assignment2_agents.orchestrator import (
    run_operations_workflow,
    resume_operations_workflow,
    get_workflow_history,
)


@pytest.fixture
def workflow_db():
    """
    Use the configured application database.

    Tests create uniquely identified workflow runs. They do not
    drop tables or delete existing application data.
    """
    init_database()
    yield


def fake_intake(*args, **kwargs):
    return IntakeOutput(
        decisions=[
            {
                "fact_id": "d1",
                "text": "Launch the dashboard.",
                "source_reference": "transcript",
                "confidence": "high",
            }
        ],
        requirements=[],
        constraints=[],
        missing_information=[],
        conflicts=[],
    )


def fake_plan(*args, **kwargs):
    return [
        PlannedTask(
            task_id="T1",
            title="Prepare requirements",
            owner="Priya",
            deadline="2026-11-15",
            dependencies=[],
            supported_facts=["d1"],
            recommendations=[],
            unresolved_questions=[],
        )
    ]


def fake_review_approved(*args, **kwargs):
    return ReviewOutput(
        approved=True,
        issues=[],
        unresolved_issues=[],
    )


def fake_review_rejected(*args, **kwargs):
    return ReviewOutput(
        approved=False,
        issues=[
            {
                "task_id": "T1",
                "issue": "The task needs a clearer scope.",
                "correction": "Specify the required deliverable.",
            }
        ],
        unresolved_issues=[],
    )


def get_run(run_id):
    with SessionLocal() as db:
        record = (
            db.query(WorkflowRun)
            .filter(WorkflowRun.run_id == run_id)
            .one_or_none()
        )

        if record is None:
            return None

        return {
            "run_id": record.run_id,
            "status": record.status,
            "current_stage": record.current_stage,
            "attempts": record.attempts,
            "completed": record.completed,
            "intake_json": record.intake_json,
            "plan_json": record.plan_json,
            "review_json": record.review_json,
            "feedback_history_json": record.feedback_history_json,
            "error": record.error,
        }


def test_approved_workflow_is_persisted(workflow_db):
    with (
        patch(
            "assignment2_agents.orchestrator.run_intake_agent",
            side_effect=fake_intake,
        ) as intake_mock,
        patch(
            "assignment2_agents.orchestrator.run_planning_agent",
            side_effect=fake_plan,
        ) as planning_mock,
        patch(
            "assignment2_agents.orchestrator.run_review_agent",
            side_effect=fake_review_approved,
        ) as review_mock,
    ):
        result = run_operations_workflow(
            transcript="Launch the dashboard.",
            company_rules={},
        )

    assert result["status"] == "approved"
    assert result["current_stage"] == "completed"
    assert result["attempts"] == 1
    assert result["intake"] is not None
    assert len(result["plan"]) == 1
    assert result["review"]["approved"] is True

    saved = get_run(result["run_id"])

    assert saved is not None
    assert saved["status"] == "approved"
    assert saved["completed"] is True
    assert saved["intake_json"] is not None
    assert saved["plan_json"] is not None
    assert saved["review_json"] is not None

    intake_mock.assert_called_once()
    planning_mock.assert_called_once()
    review_mock.assert_called_once()


def test_failed_review_can_resume_without_rerunning_intake(
    workflow_db,
):
    with (
        patch(
            "assignment2_agents.orchestrator.run_intake_agent",
            side_effect=fake_intake,
        ) as intake_mock,
        patch(
            "assignment2_agents.orchestrator.run_planning_agent",
            side_effect=fake_plan,
        ) as planning_mock,
        patch(
            "assignment2_agents.orchestrator.run_review_agent",
            side_effect=RuntimeError("Simulated review failure"),
        ),
    ):
        first_result = run_operations_workflow(
            transcript="Launch the dashboard.",
            company_rules={},
        )

    assert first_result["status"] == "failed"
    assert first_result["error"] is not None

    saved_before_resume = get_run(first_result["run_id"])

    assert saved_before_resume is not None
    assert saved_before_resume["intake_json"] is not None
    assert saved_before_resume["plan_json"] is not None
    assert saved_before_resume["current_stage"] == "review"

    with (
        patch(
            "assignment2_agents.orchestrator.run_intake_agent",
            side_effect=AssertionError(
                "Saved Intake output should be reused."
            ),
        ) as intake_resume_mock,
        patch(
            "assignment2_agents.orchestrator.run_planning_agent",
            side_effect=AssertionError(
                "Saved plan should be reviewed before replanning."
            ),
        ) as planning_resume_mock,
        patch(
            "assignment2_agents.orchestrator.run_review_agent",
            side_effect=fake_review_approved,
        ) as review_resume_mock,
    ):
        resumed = resume_operations_workflow(
            first_result["run_id"]
        )

    assert resumed["status"] == "approved"
    assert resumed["current_stage"] == "completed"
    assert resumed["intake"] is not None
    assert len(resumed["plan"]) == 1

    intake_mock.assert_called_once()
    planning_mock.assert_called_once()

    intake_resume_mock.assert_not_called()
    planning_resume_mock.assert_not_called()
    review_resume_mock.assert_called_once()


def test_review_retries_are_bounded(workflow_db):
    with (
        patch(
            "assignment2_agents.orchestrator.run_intake_agent",
            side_effect=fake_intake,
        ),
        patch(
            "assignment2_agents.orchestrator.run_planning_agent",
            side_effect=fake_plan,
        ) as planning_mock,
        patch(
            "assignment2_agents.orchestrator.run_review_agent",
            side_effect=fake_review_rejected,
        ) as review_mock,
    ):
        result = run_operations_workflow(
            transcript="Launch the dashboard.",
            company_rules={},
        )

    assert result["status"] == "needs_human_review"
    assert result["attempts"] == 3
    assert planning_mock.call_count == 3
    assert review_mock.call_count == 3
    assert len(result["feedback_history"]) == 3

    saved = get_run(result["run_id"])

    assert saved is not None
    assert saved["status"] == "needs_human_review"
    assert saved["completed"] is False

    history = get_workflow_history(100)

    assert any(
        item["run_id"] == result["run_id"]
        for item in history
    )


def test_approved_workflow_cannot_be_resumed(workflow_db):
    with (
        patch(
            "assignment2_agents.orchestrator.run_intake_agent",
            side_effect=fake_intake,
        ),
        patch(
            "assignment2_agents.orchestrator.run_planning_agent",
            side_effect=fake_plan,
        ),
        patch(
            "assignment2_agents.orchestrator.run_review_agent",
            side_effect=fake_review_approved,
        ),
    ):
        result = run_operations_workflow(
            transcript="Launch the dashboard.",
            company_rules={},
        )

    with pytest.raises(ValueError, match="Only failed workflows"):
        resume_operations_workflow(result["run_id"])


def test_history_includes_current_stage(workflow_db):
    with (
        patch(
            "assignment2_agents.orchestrator.run_intake_agent",
            side_effect=fake_intake,
        ),
        patch(
            "assignment2_agents.orchestrator.run_planning_agent",
            side_effect=fake_plan,
        ),
        patch(
            "assignment2_agents.orchestrator.run_review_agent",
            side_effect=fake_review_approved,
        ),
    ):
        result = run_operations_workflow(
            transcript="Launch the dashboard.",
            company_rules={},
        )

    history = get_workflow_history(100)

    matching = [
        item
        for item in history
        if item["run_id"] == result["run_id"]
    ]

    assert len(matching) == 1
    assert matching[0]["current_stage"] == "completed"
    assert matching[0]["status"] == "approved"
