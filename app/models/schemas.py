from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Request:
    request_id: str
    sender: str
    receiver: str
    customer_id: str
    requested_fields: list[str]
    purpose: str


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
