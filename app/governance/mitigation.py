from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final, Optional

from app.models.schemas import Finding, Request

_COMPLAINT_CONTEXT: Final[re.Pattern[str]] = re.compile(
    r"\b(?:complaint|ticket|issue|status|dispute)\b", re.IGNORECASE
)
_CONTACT_CONTEXT: Final[re.Pattern[str]] = re.compile(
    r"\b(?:contact|notify|reach|message|email|phone)\b", re.IGNORECASE
)
_ADDRESS_CONTEXT: Final[re.Pattern[str]] = re.compile(
    r"\b(?:shipping|delivery|address|location)\b", re.IGNORECASE
)

_HOSTILE_LABELS: Final[set[str]] = {
    "INSTRUCTION_OVERRIDE",
    "SUSPICIOUS_PAYLOAD",
    "INDIRECT_RELAY_REQUEST",
}


@dataclass
class MitigationDecision:
    decision: str
    reason: str
    suggested_action: str
    modified_request: Optional[Request] = None


def suggest_safer_fields(request: Request) -> list[str]:
    purpose = request.purpose

    if _COMPLAINT_CONTEXT.search(purpose):
        return ["customer_id", "complaint_id", "complaint_status"]
    if _CONTACT_CONTEXT.search(purpose):
        return ["customer_id", "name", "email"]
    if _ADDRESS_CONTEXT.search(purpose):
        return ["customer_id", "name", "address"]

    return ["customer_id", "name"]


def determine_mitigation(
    request: Request,
    risk_level: str,
    findings: list[Finding],
    is_authorized: Optional[bool] = None,
) -> MitigationDecision:
    if is_authorized is False:
        return MitigationDecision(
            decision="BLOCK",
            reason="Request blocked: unauthorized access.",
            suggested_action="BLOCK",
            modified_request=None,
        )
    if risk_level == "LOW":
        return MitigationDecision(
            decision="ALLOW",
            reason="Request is low risk and approved for processing.",
            suggested_action="ALLOW",
            modified_request=None,
        )

    if risk_level == "MEDIUM":
        if any("REPEATED_PROBING" in f.labels for f in findings):
            return MitigationDecision(
                "RESTRICT", "Repeated requests require throttling; try again after the window.",
                "THROTTLE",
            )
        is_over_broad = any("OVER_BROAD_REQUEST" in f.labels for f in findings)
        if is_over_broad:
            safer_fields = suggest_safer_fields(request)
            modified = Request(
                request_id=request.request_id,
                sender=request.sender,
                receiver=request.receiver,
                customer_id=request.customer_id,
                requested_fields=safer_fields,
                purpose=request.purpose,
            )
            return MitigationDecision(
                decision="MODIFY",
                reason="Over-broad request scoped down to contextually relevant fields.",
                suggested_action="MODIFY",
                modified_request=modified,
            )

        return MitigationDecision(
            decision="RESTRICT",
            reason="Request restricted due to medium-risk confidentiality or rate limit indicators.",
            suggested_action="RESTRICT",
            modified_request=None,
        )

    has_hostile_violation = any(
        any(lbl in _HOSTILE_LABELS for lbl in f.labels) for f in findings
    )
    if has_hostile_violation:
        return MitigationDecision(
            decision="BLOCK",
            reason="Request blocked due to security policy override or hostile payload.",
            suggested_action="BLOCK",
            modified_request=None,
        )

    if any("UNKNOWN_PURPOSE" in f.labels for f in findings):
        return MitigationDecision(
            "HUMAN_REVIEW",
            "The request purpose is unrecognized. A reviewer must confirm a supported purpose before re-analysis.",
            "HUMAN_REVIEW",
        )

    has_restricted_data = any(
        "RESTRICTED" in f.labels or "UNKNOWN_FIELD" in f.labels
        for f in findings
    )
    if has_restricted_data:
        return MitigationDecision(
            decision="HUMAN_REVIEW",
            reason="Access to restricted financial data or unverified fields requires human supervisor authorization.",
            suggested_action="HUMAN_REVIEW",
            modified_request=None,
        )

    return MitigationDecision(
        decision="BLOCK",
        reason="Request blocked due to high-risk policy violation.",
        suggested_action="BLOCK",
        modified_request=None,
    )
