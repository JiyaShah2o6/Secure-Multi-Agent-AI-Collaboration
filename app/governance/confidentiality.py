from __future__ import annotations

import re
from typing import Final

from app.models.schemas import Finding, Request

INTERNAL_FIELDS: Final[set[str]] = {
    "customer_id",
    "name",
    "complaint_id",
    "complaint_status",
}

CONFIDENTIAL_FIELDS: Final[set[str]] = {
    "email",
    "phone",
    "complaint_description",
    "address",
}

RESTRICTED_FIELDS: Final[set[str]] = {
    "bank_account",
    "bank_account_details",
    "card_details",
}

_EMAIL_REGEX: Final[re.Pattern[str]] = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
)
_PHONE_REGEX: Final[re.Pattern[str]] = re.compile(
    r"(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"
)
_CARD_REGEX: Final[re.Pattern[str]] = re.compile(
    r"\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13})\b"
)
_ACCOUNT_KEYWORD_REGEX: Final[re.Pattern[str]] = re.compile(
    r"\b(?:bank[_\s]?account|credit[_\s]?card|cvv|pin)\b", re.IGNORECASE
)


_WILDCARD_FIELDS: Final[set[str]] = {"*", "all", "all_fields", "everything"}


def classify_field(field_name: str) -> str:
    cleaned = field_name.strip().lower()
    if cleaned in _WILDCARD_FIELDS:
        return "WILDCARD"
    if cleaned in INTERNAL_FIELDS:
        return "INTERNAL"
    if cleaned in CONFIDENTIAL_FIELDS:
        return "CONFIDENTIAL"
    if cleaned in RESTRICTED_FIELDS:
        return "RESTRICTED"
    return "UNKNOWN"


def analyze_confidentiality(request: Request) -> list[Finding]:
    findings: list[Finding] = []

    for raw_field in request.requested_fields:
        field_name = raw_field.strip().lower()
        classification = classify_field(field_name)

        if classification == "WILDCARD":
            continue

        if classification == "CONFIDENTIAL":
            findings.append(
                Finding(
                    analyzer="confidentiality",
                    severity="MEDIUM",
                    labels=["CONFIDENTIAL", field_name],
                    evidence=raw_field,
                    explanation=f"Requested field '{raw_field}' contains confidential customer data.",
                    suggested_action="REDACT",
                )
            )
        elif classification == "RESTRICTED":
            findings.append(
                Finding(
                    analyzer="confidentiality",
                    severity="HIGH",
                    labels=["RESTRICTED", field_name],
                    evidence=raw_field,
                    explanation=f"Requested field '{raw_field}' contains restricted customer financial data.",
                    suggested_action="BLOCK",
                )
            )
        elif classification == "UNKNOWN":
            findings.append(
                Finding(
                    analyzer="confidentiality",
                    severity="HIGH",
                    labels=["UNKNOWN_FIELD", field_name],
                    evidence=raw_field,
                    explanation=f"Requested field '{raw_field}' is not in the recognized customer schema.",
                    suggested_action="BLOCK",
                )
            )

    purpose_text = request.purpose
    for match in _CARD_REGEX.finditer(purpose_text):
        findings.append(
            Finding(
                analyzer="confidentiality",
                severity="HIGH",
                labels=["RESTRICTED", "EMBEDDED_CARD"],
                evidence=match.group(),
                explanation="Potential card number pattern detected in request purpose.",
                suggested_action="REDACT",
            )
        )

    for match in _EMAIL_REGEX.finditer(purpose_text):
        findings.append(
            Finding(
                analyzer="confidentiality",
                severity="MEDIUM",
                labels=["CONFIDENTIAL", "EMBEDDED_EMAIL"],
                evidence=match.group(),
                explanation="Email address pattern detected in request purpose.",
                suggested_action="REDACT",
            )
        )

    for match in _PHONE_REGEX.finditer(purpose_text):
        findings.append(
            Finding(
                analyzer="confidentiality",
                severity="MEDIUM",
                labels=["CONFIDENTIAL", "EMBEDDED_PHONE"],
                evidence=match.group(),
                explanation="Phone number pattern detected in request purpose.",
                suggested_action="REDACT",
            )
        )

    for match in _ACCOUNT_KEYWORD_REGEX.finditer(purpose_text):
        findings.append(
            Finding(
                analyzer="confidentiality",
                severity="HIGH",
                labels=["RESTRICTED", "FINANCIAL_KEYWORD"],
                evidence=match.group(),
                explanation="Sensitive financial keyword detected in request purpose.",
                suggested_action="REVIEW",
            )
        )

    return findings
