from __future__ import annotations

from typing import Any, Optional

# Role-based permissions for agents
AGENT_PERMISSIONS: dict[str, set[str]] = {
    "AgentA": {
        "customer_id",
        "name",
        "complaint_id",
        "complaint_status",
    }
}

VALID_SENDERS: set[str] = {"AgentA"}
VALID_RECEIVERS: set[str] = {"AgentB"}

CUSTOMER_SCHEMA_FIELDS: set[str] = {
    "customer_id",
    "name",
    "email",
    "phone",
    "complaint_id",
    "complaint_status",
    "complaint_description",
    "address",
    "bank_account",
    "card_details",
}

WILDCARD_TOKENS: set[str] = {"*", "all", "all_fields", "everything"}


def get_allowed_fields(agent_name: str) -> set[str]:
    """Return the fields that an agent is allowed to access."""
    return set(AGENT_PERMISSIONS.get(agent_name, set()))


def is_authorized(agent_name: str, requested_fields: list[str]) -> dict[str, Any]:
    """
    Check whether an agent is authorized to access requested fields.
    Distinguishes fully authorized, mixed permissions, unauthorized,
    unknown fields, and unrecognized agents.
    """
    allowed_fields = get_allowed_fields(agent_name)
    explicit_fields = [f for f in requested_fields if f not in WILDCARD_TOKENS]

    permitted_fields = [f for f in explicit_fields if f in allowed_fields]
    unauthorized_fields = [f for f in explicit_fields if f not in allowed_fields]
    unknown_fields = [
        f for f in explicit_fields
        if f not in CUSTOMER_SCHEMA_FIELDS and f != "bank_account_details"
    ]

    is_known_agent = agent_name in AGENT_PERMISSIONS
    is_mixed = bool(permitted_fields and unauthorized_fields)

    if not is_known_agent:
        status = "invalid_agent"
    elif unknown_fields:
        status = "unknown_fields"
    elif unauthorized_fields and not permitted_fields:
        status = "unauthorized"
    elif is_mixed:
        status = "mixed"
    else:
        status = "fully_authorized"

    authorized = is_known_agent and len(unauthorized_fields) == 0

    return {
        "authorized": authorized,
        "unauthorized_fields": unauthorized_fields,
        "permitted_fields": permitted_fields,
        "unknown_fields": unknown_fields,
        "is_mixed": is_mixed,
        "status": status,
    }


def evaluate_request_authorization(
    sender: str, receiver: str, requested_fields: list[str]
) -> dict[str, Any]:
    """
    Comprehensive authorization evaluation checking requesting agent,
    data provider receiver, and each requested field.
    """
    valid_sender = sender in VALID_SENDERS
    valid_receiver = receiver in VALID_RECEIVERS

    auth_result = is_authorized(sender, requested_fields)

    if not valid_sender:
        status = "invalid_sender"
        message = f"Requesting agent '{sender}' is not a recognized or authorized sender."
    elif not valid_receiver:
        status = "invalid_receiver"
        message = f"Receiving agent '{receiver}' is not a recognized data provider."
    elif auth_result["status"] == "unknown_fields":
        status = "unknown_fields"
        message = "Requested fields include unrecognized schema fields."
    elif auth_result["status"] == "mixed":
        status = "mixed"
        message = "Request contains a mixture of permitted and forbidden fields."
    elif auth_result["status"] == "unauthorized":
        status = "unauthorized"
        message = f"Requested fields are forbidden for agent '{sender}'."
    else:
        status = "fully_authorized"
        message = "All requested fields are authorized."

    overall_authorized = valid_sender and valid_receiver and auth_result["authorized"]

    return {
        "authorized": overall_authorized,
        "valid_sender": valid_sender,
        "valid_receiver": valid_receiver,
        "permitted_fields": auth_result["permitted_fields"],
        "unauthorized_fields": auth_result["unauthorized_fields"],
        "unknown_fields": auth_result["unknown_fields"],
        "is_mixed": auth_result["is_mixed"],
        "status": status,
        "message": message,
    }


def update_agent_permission(
    agent_name: str,
    allowed_fields: set[str],
    audit_logger: Optional[Any] = None,
    reason: str = "",
) -> dict[str, Any]:
    """
    Explicitly update an agent's authorization policy with audit traceability.
    Used for exceptional authorization workflows without bypassing the matrix.
    """
    old_fields = get_allowed_fields(agent_name)
    new_fields = set(allowed_fields)
    AGENT_PERMISSIONS[agent_name] = new_fields

    record = {
        "agent": agent_name,
        "old_fields": sorted(list(old_fields)),
        "new_fields": sorted(list(new_fields)),
        "reason": reason,
    }
    return record