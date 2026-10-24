
from copy import deepcopy

DEFAULT_POLICY = {
    "company_name": "InsightEdge Analytics",
    "timezone": "Asia/Kolkata",

    "services": [
        "AI Automation",
        "Data Analytics",
        "Power BI Consulting",
    ],

    "qualification": {
        "minimum_budget_inr": 50000,
        "maximum_timeline_days": 90,
    },

    "representatives": [
        {
            "id": "REP-001",
            "name": "Aisha Mehta",
            "specializations": ["AI Automation"],
        },
        {
            "id": "REP-002",
            "name": "Rahul Shah",
            "specializations": [
                "Data Analytics",
                "Power BI Consulting",
            ],
        },
    ],

    "working_hours": {
        "days": [
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
        ],
        "start": "10:00",
        "end": "18:00",
        "meeting_duration_minutes": 30,
    },
}


def get_default_policy():
    return deepcopy(DEFAULT_POLICY)


def validate_policy(policy):
    if not policy.get("company_name"):
        raise ValueError("Company name is required.")

    if not policy.get("services"):
        raise ValueError("At least one service is required.")

    qualification = policy.get("qualification", {})

    if qualification.get("minimum_budget_inr", 0) < 0:
        raise ValueError("Minimum budget cannot be negative.")

    if qualification.get("maximum_timeline_days", 0) <= 0:
        raise ValueError("Maximum timeline must be positive.")

    representatives = policy.get("representatives", [])

    if len(representatives) != 2:
        raise ValueError("Exactly two representatives are required.")

    rep_ids = [rep["id"] for rep in representatives]

    if len(set(rep_ids)) != len(rep_ids):
        raise ValueError("Representative IDs must be unique.")

    return True
