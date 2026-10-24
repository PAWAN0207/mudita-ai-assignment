
from assignment1_sales.policy import get_default_policy


def assign_representative(
    service_interest: str,
    policy: dict | None = None,
) -> dict | None:

    if not service_interest:
        return None

    active_policy = policy or get_default_policy()

    requested_service = service_interest.strip().casefold()

    for representative in active_policy["representatives"]:
        specializations = [
            service.casefold()
            for service in representative["specializations"]
        ]

        if requested_service in specializations:
            return representative.copy()

    return None

