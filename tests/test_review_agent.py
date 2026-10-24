
from core.schemas import PlannedTask
from assignment2_agents.review_agent import validate_task_structure


def make_task(task_id, dependencies=None):
    return PlannedTask(
        task_id=task_id,
        title=f"Task {task_id}",
        dependencies=dependencies or [],
        supported_facts=[],
        recommendations=[],
        unresolved_questions=[],
    )


def test_valid_dependencies_pass():
    tasks = [
        make_task("T1"),
        make_task("T2", ["T1"]),
    ]

    issues = validate_task_structure(tasks)

    assert issues == []


def test_self_dependency_is_detected():
    tasks = [
        make_task("T1", ["T1"]),
    ]

    issues = validate_task_structure(tasks)

    assert any(
        "depend on itself" in issue.issue
        for issue in issues
    )


def test_unknown_dependency_is_detected():
    tasks = [
        make_task("T1", ["UNKNOWN"]),
    ]

    issues = validate_task_structure(tasks)

    assert any(
        "Unknown dependency" in issue.issue
        for issue in issues
    )


def test_circular_dependency_is_detected():
    tasks = [
        make_task("T1", ["T2"]),
        make_task("T2", ["T1"]),
    ]

    issues = validate_task_structure(tasks)

    assert any(
        "Circular task dependency" in issue.issue
        for issue in issues
    )


def test_duplicate_task_ids_are_detected():
    tasks = [
        make_task("T1"),
        make_task("T1"),
    ]

    issues = validate_task_structure(tasks)

    assert any(
        "Duplicate task ID" in issue.issue
        for issue in issues
    )
