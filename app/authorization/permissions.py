# Role-based permissions for agents

AGENT_PERMISSIONS = {
    "AgentA": {
        "customer_id",
        "name",
        "complaint_id",
        "complaint_status"
    }
}


def get_allowed_fields(agent_name):
    """Return the fields that an agent is allowed to access."""
    return AGENT_PERMISSIONS.get(agent_name, set())


def is_authorized(agent_name, requested_fields):
    """
    Check whether an agent is authorized
    to access all requested fields.
    """

    allowed_fields = get_allowed_fields(agent_name)

    unauthorized_fields = [
        field
        for field in requested_fields
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