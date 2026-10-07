from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Optional

from app.models.schemas import Finding

_HIGH_RISK_LABELS: Final[set[str]] = {
    "INSTRUCTION_OVERRIDE",
    "SUSPICIOUS_PAYLOAD",
    "INDIRECT_RELAY_REQUEST",
    "RESTRICTED",
    "UNKNOWN_FIELD",
}

_MEDIUM_RISK_LABELS: Final[set[str]] = {
    "OVER_BROAD_REQUEST",
    "CONFIDENTIAL",
    "REPEATED_PROBING",
}


@dataclass
class RiskEvaluation:
    risk_level: str
    reason: str


def classify_risk(
    findings: list[Finding], is_authorized: Optional[bool] = None
) -> str:
    return evaluate_risk(findings, is_authorized).risk_level


def evaluate_risk(
    findings: list[Finding], is_authorized: Optional[bool] = None
) -> RiskEvaluation:
    if is_authorized is False:
        restricted_or_threat = any(
            f.severity in {"HIGH", "CRITICAL"}
            or any(lbl in _HIGH_RISK_LABELS for lbl in f.labels)
            for f in findings
        )
        if restricted_or_threat:
            return RiskEvaluation(
                risk_level="HIGH",
                reason="Unauthorized request attempting to access restricted data or violating security policy.",
            )
        return RiskEvaluation(
            risk_level="HIGH",
            reason="Request failed authorization check.",
        )

    for finding in findings:
        if finding.severity in {"HIGH", "CRITICAL"}:
            return RiskEvaluation(
                risk_level="HIGH",
                reason=f"High-severity finding detected: {finding.explanation}",
            )
        for label in finding.labels:
            if label in _HIGH_RISK_LABELS:
                return RiskEvaluation(
                    risk_level="HIGH",
                    reason=f"Critical risk indicator '{label}' detected: {finding.explanation}",
                )

    for finding in findings:
        if finding.severity == "MEDIUM":
            return RiskEvaluation(
                risk_level="MEDIUM",
                reason=f"Medium-severity finding detected: {finding.explanation}",
            )
        for label in finding.labels:
            if label in _MEDIUM_RISK_LABELS:
                return RiskEvaluation(
                    risk_level="MEDIUM",
                    reason=f"Medium risk indicator '{label}' detected: {finding.explanation}",
                )

    return RiskEvaluation(
        risk_level="LOW",
        reason="No significant confidentiality or security issues detected.",
    )
