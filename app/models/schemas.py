from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class AgentRequest:
    sender: str
    receiver: str
    customer_id: str
    requested_fields: list[str]
    purpose: str
    request_id: Optional[str] = None


@dataclass
class AgentResponse:
    status: str
    data: dict[str, Any]
    message: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Request:
    request_id: str
    sender: str
    receiver: str
    customer_id: str
    requested_fields: list[str]
    purpose: str


def validate_request_schema(request: Any) -> None:
    """
    Validate that a request object contains all minimum required fields
    and that their types and values conform to specification.
    """
    if request is None:
        raise ValueError("Request object cannot be None.")
    if not hasattr(request, "sender") or not hasattr(request, "receiver"):
        raise ValueError("Request is missing sender or receiver attributes.")
    if not hasattr(request, "customer_id") or not hasattr(request, "purpose"):
        raise ValueError("Request is missing customer_id or purpose attributes.")
    if not hasattr(request, "requested_fields"):
        raise ValueError("Request is missing requested_fields attribute.")

    strings = {
        "sender": getattr(request, "sender", None),
        "receiver": getattr(request, "receiver", None),
        "customer_id": getattr(request, "customer_id", None),
        "purpose": getattr(request, "purpose", None),
    }
    for field_name, value in strings.items():
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"Field '{field_name}' must be a non-empty string.")

    fields = getattr(request, "requested_fields", None)
    if not isinstance(fields, list) or not fields:
        raise ValueError("Requested fields must be a non-empty list of strings.")
    if not all(isinstance(f, str) and f.strip() for f in fields):
        raise ValueError("Each field in requested_fields must be a non-empty string.")

    request_id = getattr(request, "request_id", None)
    if request_id is not None and (not isinstance(request_id, str) or not request_id.strip()):
        raise ValueError("When provided, request_id must be a non-empty string.")


class ReviewStatus:
    PENDING_REVIEW = "PENDING_REVIEW"
    APPROVED = "APPROVED"
    RESTRICTED = "RESTRICTED"
    MODIFIED = "MODIFIED"
    REJECTED = "REJECTED"
    COMPLETED = "COMPLETED"
    CLOSED = "CLOSED"


@dataclass
class ReviewItem:
    request_id: str
    status: str
    request: Request
    previous_result: GovernanceResult
    review_scope: Optional[list[str]] = None
    created_at: str = ""
    reviewer_id: Optional[str] = None
    action: Optional[str] = None
    action_timestamp: Optional[str] = None
    reason: Optional[str] = None
    resulting_decision: Optional[str] = None


@dataclass
class ApprovalTicket:
    token: str
    request_id: str
    customer_id: str
    requested_fields: list[str]
    decision: str
    created_at: float
    ttl_seconds: float = 30.0
    consumed: bool = False


@dataclass
class Finding:
    analyzer: str
    severity: str
    labels: list[str]
    evidence: str
    explanation: str
    suggested_action: str


@dataclass
class GovernanceResult:
    request_id: str
    risk_level: str
    findings: list[Finding]
    decision: str
    reason: str
    suggested_action: str
    modified_request: Optional[Request] = None
    trajectory: list[dict[str, Any]] = field(default_factory=list)
    authorization: Optional[bool] = None
