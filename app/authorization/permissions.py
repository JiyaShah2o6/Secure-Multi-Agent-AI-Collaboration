# Permissions for Agent A (Support Agent)

AGENT_PERMISSIONS = {
    "AgentA": {
        "customer_id",
        "name",
        "complaint_id",
        "complaint_status"
    }
}


def is_authorized(agent_name, requested_fields):
    """
    Check whether an agent is authorized
    to access all requested fields.
    """

    allowed_fields = AGENT_PERMISSIONS.get(agent_name, set())

    unauthorized_fields = [
        field for field in requested_fields
        if field not in allowed_fields
    ]

    if unauthorized_fields:
        return {
            "authorized": False,
            "unauthorized_fields": unauthorized_fields
        }

    return {
        "authorized": True,
        "unauthorized_fields": []
    }