from __future__ import annotations

import re
import time
from typing import Final, Optional

from app.models.schemas import Finding, Request

_OVER_BROAD_KEYWORDS: Final[set[str]] = {"*", "all", "all_fields", "everything"}
_OVER_BROAD_THRESHOLD: Final[int] = 6

_OVER_BROAD_PURPOSE_REGEX: Final[re.Pattern[str]] = re.compile(
    r"\b(?:dump\s+(?:all\s+)?data|export\s+(?:entire\s+)?database|select\s+\*|all\s+customers|all\s+records)\b",
    re.IGNORECASE,
)

_OVERRIDE_REGEXES: Final[list[re.Pattern[str]]] = [
    re.compile(
        r"\b(?:ignore\s+(?:all\s+)?(?:previous|prior|above)\s+(?:instructions|prompts|rules|guidelines))\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:override\s+(?:all\s+)?(?:safety|policy|policies|rules|restrictions|guardrails))\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:disregard\s+(?:all\s+)?(?:previous|prior|system|security)\s+(?:instructions|rules|policies))\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:bypass\s+(?:all\s+)?(?:security|policy|restrictions|rules|guardrails|filters))\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:you\s+are\s+now|act\s+as|pretend\s+(?:you\s+are|to\s+be))\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:system\s*:|<\|system\|>|<<\s*sys\s*>>)",
        re.IGNORECASE,
    ),
]

_RELAY_REGEX: Final[re.Pattern[str]] = re.compile(
    r"\b(?:forward\s+(?:all\s+)?(?:data|records?|results?|response)\s+to|relay\s+(?:all\s+)?(?:data|records?|to)|proxy\s+(?:to|for)|send\s+to\s+external|send\s+(?:data|results?)\s+to\s+https?://|webhook)\b",
    re.IGNORECASE,
)
_EXTERNAL_URL_REGEX: Final[re.Pattern[str]] = re.compile(
    r"\b(?:curl|wget|fetch)\s+https?://",
    re.IGNORECASE,
)

_SQLI_REGEX: Final[re.Pattern[str]] = re.compile(
    r"(?:'\s*or\s*'1'='1|'\s*or\s*1=1|;\s*drop\s+table|;\s*delete\s+from|\bunion\b\s+\bselect\b|--\s*$)",
    re.IGNORECASE,
)
_TRAVERSAL_REGEX: Final[re.Pattern[str]] = re.compile(
    r"(?:\.\./|\.\.\\|;\s*(?:rm|cat|sh|bash|powershell|cmd)\b)",
    re.IGNORECASE,
)
_XSS_REGEX: Final[re.Pattern[str]] = re.compile(
    r"(?:<script\b|javascript:)",
    re.IGNORECASE,
)
_SUSPICIOUS_ID_CHARS: Final[re.Pattern[str]] = re.compile(r"['\";\\]")


class ProbingTracker:
    def __init__(self, threshold: int = 3, window_seconds: float = 60.0) -> None:
        self.threshold = threshold
        self.window_seconds = window_seconds
        self._history: dict[str, list[float]] = {}

    def record_and_check(
        self, sender: str, current_time: Optional[float] = None
    ) -> tuple[bool, int]:
        now = time.time() if current_time is None else current_time
        cutoff = now - self.window_seconds

        timestamps = self._history.setdefault(sender, [])
        valid_timestamps = [t for t in timestamps if t >= cutoff]
        valid_timestamps.append(now)
        self._history[sender] = valid_timestamps

        count = len(valid_timestamps)
        return count >= self.threshold, count

    def reset(self) -> None:
        self._history.clear()


default_probing_tracker = ProbingTracker()


def analyze_security(
    request: Request,
    tracker: Optional[ProbingTracker] = None,
    current_time: Optional[float] = None,
    record_probe: bool = True,
) -> list[Finding]:
    findings: list[Finding] = []
    active_tracker = tracker if tracker is not None else default_probing_tracker

    has_wildcard = any(
        f.strip().lower() in _OVER_BROAD_KEYWORDS for f in request.requested_fields
    )
    is_excessive_count = len(request.requested_fields) >= _OVER_BROAD_THRESHOLD
    purpose_over_broad = _OVER_BROAD_PURPOSE_REGEX.search(request.purpose)

    if has_wildcard or is_excessive_count or purpose_over_broad:
        evidence = (
            ", ".join(request.requested_fields)
            if (has_wildcard or is_excessive_count)
            else (purpose_over_broad.group() if purpose_over_broad else "")
        )
        findings.append(
            Finding(
                analyzer="security",
                severity="MEDIUM",
                labels=["OVER_BROAD_REQUEST"],
                evidence=evidence,
                explanation="Request asks for all fields or exceeds allowable query breadth.",
                suggested_action="RESTRICT",
            )
        )

    for override_pattern in _OVERRIDE_REGEXES:
        match = override_pattern.search(request.purpose)
        if match:
            findings.append(
                Finding(
                    analyzer="security",
                    severity="CRITICAL",
                    labels=["INSTRUCTION_OVERRIDE"],
                    evidence=match.group(),
                    explanation="Instruction or policy override pattern detected in request.",
                    suggested_action="BLOCK",
                )
            )
            break

    is_probing, count = (
        active_tracker.record_and_check(request.sender, current_time=current_time)
        if record_probe else (False, 0)
    )
    if is_probing:
        findings.append(
            Finding(
                analyzer="security",
                severity="MEDIUM",
                labels=["REPEATED_PROBING"],
                evidence=f"{request.sender} made {count} requests within {active_tracker.window_seconds:.0f}s",
                explanation="Repeated probing pattern detected from the same sender.",
                suggested_action="THROTTLE",
            )
        )

    relay_match = _RELAY_REGEX.search(request.purpose)
    url_match = _EXTERNAL_URL_REGEX.search(request.purpose)
    is_self_relay = request.sender.strip().lower() == request.receiver.strip().lower()

    if relay_match or url_match or is_self_relay:
        evidence = (
            relay_match.group()
            if relay_match
            else (
                url_match.group()
                if url_match
                else f"sender==receiver ({request.sender})"
            )
        )
        findings.append(
            Finding(
                analyzer="security",
                severity="HIGH",
                labels=["INDIRECT_RELAY_REQUEST"],
                evidence=evidence,
                explanation="Indirect relay or out-of-band forwarding pattern detected.",
                suggested_action="BLOCK",
            )
        )

    cid = request.customer_id.strip()
    sqli_match = _SQLI_REGEX.search(cid) or _SQLI_REGEX.search(request.purpose)
    traversal_match = _TRAVERSAL_REGEX.search(cid) or _TRAVERSAL_REGEX.search(
        request.purpose
    )
    xss_match = _XSS_REGEX.search(request.purpose) or _XSS_REGEX.search(cid)
    suspicious_chars = _SUSPICIOUS_ID_CHARS.search(cid)
    is_invalid_id = cid in {"*", "null", "undefined", "admin", "root", ""}

    if sqli_match or traversal_match or xss_match or suspicious_chars or is_invalid_id:
        evidence = (
            sqli_match.group()
            if sqli_match
            else (
                traversal_match.group()
                if traversal_match
                else (
                    xss_match.group()
                    if xss_match
                    else (suspicious_chars.group() if suspicious_chars else cid)
                )
            )
        )
        findings.append(
            Finding(
                analyzer="security",
                severity="CRITICAL",
                labels=["SUSPICIOUS_PAYLOAD"],
                evidence=evidence,
                explanation="Suspicious injection pattern or malformed identifier detected.",
                suggested_action="BLOCK",
            )
        )

    return findings
