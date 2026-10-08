from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, replace
from typing import Callable, Final, Optional

from app.authorization.data_minimization import (
    PURPOSE_FIELDS, check_data_minimization, suggest_minimum_fields,
)
from app.authorization.permissions import get_allowed_fields, is_authorized as check_permission
from app.governance.audit import AuditLogger, default_audit_logger
from app.governance.confidentiality import analyze_confidentiality
from app.governance.mitigation import determine_mitigation
from app.governance.risk_engine import evaluate_risk
from app.governance.security import ProbingTracker, analyze_security
from app.models.schemas import Finding, GovernanceResult, Request

DEFAULT_MAX_REANALYSIS_LIMIT: Final[int] = 2
WILDCARDS = {"*", "all", "all_fields", "everything"}


def _finding(analyzer, severity, label, evidence, explanation, action):
    return Finding(analyzer, severity, [label], evidence, explanation, action)


def authorization_provider(request: Request) -> bool:
    """Adapt the existing permissions dictionary; wildcards are proposals, not grants."""
    if request.sender != "AgentA" or request.receiver != "AgentB":
        return False
    explicit = [f for f in request.requested_fields if f not in WILDCARDS]
    return check_permission(request.sender, explicit)["authorized"] is True


def run_single_governance_pass(
    request: Request,
    is_authorized: Optional[bool] = None,
    tracker: Optional[ProbingTracker] = None,
    *,
    auth_provider: Optional[Callable[[Request], bool]] = None,
    enforce_policy: bool = False,
    record_probe: bool = True,
    field_scope: Optional[list[str]] = None,
) -> GovernanceResult:
    """Standalone analyzer API is retained; application calls enforce_policy=True."""
    findings = []
    provider = auth_provider or (authorization_provider if enforce_policy else None)
    authorized = is_authorized
    if provider is not None:
        try:
            authorized = provider(request)
            if type(authorized) is not bool:
                raise ValueError("Authorization must return bool")
        except Exception:
            authorized = False
            findings.append(_finding("authorization", "HIGH", "AUTHORIZATION_ERROR", "",
                                     "Authorization provider failed or returned an invalid result.", "BLOCK"))
    if authorized is False:
        findings.append(_finding("authorization", "HIGH", "UNAUTHORIZED_ACCESS", "",
                                 "Request contains forbidden fields or an invalid agent identity.", "BLOCK"))

    findings.extend(analyze_confidentiality(request))
    findings.extend(analyze_security(request, tracker=tracker, record_probe=record_probe))

    minimum = None
    if enforce_policy:
        # Explicit requests may only narrow. Only a wildcard proposes new fields;
        # a reviewer limit remains binding even for that proposal.
        if not any(f in WILDCARDS for f in request.requested_fields):
            field_scope = [f for f in request.requested_fields
                           if field_scope is None or f in field_scope]
        minimization = check_data_minimization(request.purpose, request.requested_fields)
        if request.purpose not in PURPOSE_FIELDS:
            findings.append(_finding("data_minimization", "HIGH", "UNKNOWN_PURPOSE", "",
                                     "Unrecognized purpose requires a human to select a supported purpose.", "REVIEW"))
        elif not minimization["valid"]:
            minimum = suggest_minimum_fields(request.purpose, get_allowed_fields(request.sender), field_scope)
            findings.append(_finding("data_minimization", "MEDIUM", "DATA_MINIMIZATION", "",
                                     "Requested fields exceed the needs of the stated purpose.", "MODIFY"))

    risk = evaluate_risk(findings, is_authorized=authorized)
    mitigation = determine_mitigation(request, risk.risk_level, findings, is_authorized=authorized)
    probing = any("REPEATED_PROBING" in f.labels for f in findings)
    if enforce_policy and risk.risk_level == "MEDIUM" and not probing:
        if minimum is not None or mitigation.decision == "MODIFY":
            minimum = minimum if minimum is not None else suggest_minimum_fields(
                request.purpose, get_allowed_fields(request.sender), field_scope
            )
            if minimum:
                mitigation.decision = "MODIFY"
                mitigation.suggested_action = "MODIFY"
                mitigation.reason = "Replace the request with purpose-required, permitted fields and re-analyze."
                mitigation.modified_request = replace(request, requested_fields=minimum)
            else:
                mitigation.decision = "RESTRICT"
                mitigation.suggested_action = "RESTRICT"
                mitigation.reason = "No permitted projection exists for this purpose."
                mitigation.modified_request = None
    return GovernanceResult(request.request_id, risk.risk_level, findings,
                            mitigation.decision, mitigation.reason,
                            mitigation.suggested_action, mitigation.modified_request,
                            authorization=authorized)


def reanalyze_request(
    request: Request,
    is_authorized: Optional[bool] = None,
    max_reanalysis_limit: int = DEFAULT_MAX_REANALYSIS_LIMIT,
    governance_fn: Optional[Callable[[Request], GovernanceResult]] = None,
    tracker: Optional[ProbingTracker] = None,
    *,
    auth_provider: Optional[Callable[[Request], bool]] = None,
    enforce_policy: bool = False,
    field_scope: Optional[list[str]] = None,
) -> tuple[GovernanceResult, list[GovernanceResult]]:
    if max_reanalysis_limit < 0:
        raise ValueError("Re-analysis limit must be nonnegative")
    history = []
    current = deepcopy(request)
    for attempt in range(max_reanalysis_limit + 1):
        result = (governance_fn(current) if governance_fn else run_single_governance_pass(
            current, is_authorized, tracker, auth_provider=auth_provider,
            enforce_policy=enforce_policy, record_probe=(attempt == 0),
            field_scope=field_scope,
        ))
        history.append(deepcopy(result))
        if result.decision != "MODIFY" or result.modified_request is None:
            if result.decision == "ALLOW" and current != request:
                result.modified_request = deepcopy(current)
            return result, history
        if attempt == max_reanalysis_limit:
            blocked = GovernanceResult(
                request.request_id, "HIGH", result.findings, "BLOCK",
                f"Maximum re-analysis limit ({max_reanalysis_limit}) exceeded without resolving to a safe state.",
                "BLOCK",
            )
            history.append(deepcopy(blocked))
            return blocked, history
        current = deepcopy(result.modified_request)
    raise AssertionError("Unreachable")


def govern_request(
    request: Request,
    is_authorized: Optional[bool] = None,
    auth_provider: Optional[Callable[[Request], bool]] = None,
    audit_logger: Optional[AuditLogger] = None,
    tracker: Optional[ProbingTracker] = None,
    *,
    enforce_policy: bool = False,
    human_action: Optional[str] = None,
    field_scope: Optional[list[str]] = None,
) -> GovernanceResult:
    final, history = reanalyze_request(
        request, is_authorized, tracker=tracker, auth_provider=auth_provider,
        enforce_policy=enforce_policy, field_scope=field_scope,
    )
    final.trajectory = []
    for idx, result in enumerate(history):
        findings = [asdict(f) for f in result.findings]
        for finding in findings:
            finding["evidence"] = "[redacted]" if finding["evidence"] else ""
        final.trajectory.append({
            "pass": idx, "decision": result.decision, "risk_level": result.risk_level,
            "authorization": result.authorization,
            "reason": result.reason, "findings": findings,
            "modified_fields": result.modified_request.requested_fields if result.modified_request else None,
        })
    info = None
    if len(history) > 1:
        info = {
            "passes": len(history), "initial_decision": history[0].decision,
            "initial_risk": history[0].risk_level, "final_decision": final.decision,
            "final_risk": final.risk_level,
            "modified_fields": final.modified_request.requested_fields if final.modified_request else None,
            "trajectory": final.trajectory,
        }
    logger = audit_logger if audit_logger is not None else default_audit_logger
    logger.record_audit(request, final, human_action=human_action, reanalysis_info=info)
    return final
