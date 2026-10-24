
from core.schemas import LeadQualification
from assignment1_sales.policy import get_default_policy


def qualify_lead(
    service_interest: str | None,
    budget_inr: int | None,
    timeline_days: int | None,
    policy: dict | None = None,
) -> LeadQualification:

    active_policy = policy or get_default_policy()

    criteria = active_policy["qualification"]
    services = active_policy["services"]

    evidence = []
    missing_information = []

    if not service_interest:
        missing_information.append("service_interest")
    else:
        normalized_service = service_interest.strip().casefold()

        supported_service = next(
            (
                service
                for service in services
                if service.casefold() == normalized_service
            ),
            None,
        )

        if supported_service is None:
            return LeadQualification(
                status="not_qualified",
                evidence=[
                    "Requested service is not offered by the company."
                ],
                missing_information=[],
                service_interest=service_interest,
                budget_inr=budget_inr,
                timeline_days=timeline_days,
            )

        evidence.append(
            f"Requested service is available: {supported_service}."
        )

    if budget_inr is None:
        missing_information.append("budget_inr")
    elif budget_inr < criteria["minimum_budget_inr"]:
        return LeadQualification(
            status="not_qualified",
            evidence=[
                (
                    f"Budget ₹{budget_inr:,} is below the minimum "
                    f"required budget of "
                    f"₹{criteria['minimum_budget_inr']:,}."
                )
            ],
            missing_information=[],
            service_interest=service_interest,
            budget_inr=budget_inr,
            timeline_days=timeline_days,
        )
    else:
        evidence.append(
            f"Budget ₹{budget_inr:,} meets the minimum requirement."
        )

    if timeline_days is None:
        missing_information.append("timeline_days")
    elif timeline_days <= 0:
        return LeadQualification(
            status="needs_more_information",
            evidence=["Timeline must be a positive number of days."],
            missing_information=["timeline_days"],
            service_interest=service_interest,
            budget_inr=budget_inr,
            timeline_days=timeline_days,
        )
    elif timeline_days > criteria["maximum_timeline_days"]:
        return LeadQualification(
            status="not_qualified",
            evidence=[
                (
                    f"Timeline of {timeline_days} days exceeds "
                    f"the maximum of "
                    f"{criteria['maximum_timeline_days']} days."
                )
            ],
            missing_information=[],
            service_interest=service_interest,
            budget_inr=budget_inr,
            timeline_days=timeline_days,
        )
    else:
        evidence.append(
            f"Timeline of {timeline_days} days meets the requirement."
        )

    if missing_information:
        status = "needs_more_information"
    else:
        status = "qualified"

    return LeadQualification(
        status=status,
        evidence=evidence,
        missing_information=missing_information,
        service_interest=service_interest,
        budget_inr=budget_inr,
        timeline_days=timeline_days,
    )

