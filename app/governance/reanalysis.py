from __future__ import annotations

from typing import Callable, Final, Optional

from app.governance.audit import AuditLogger, default_audit_logger
from app.governance.confidentiality import analyze_confidentiality
from app.governance.mitigation import determine_mitigation
from app.governance.risk_engine import evaluate_risk
from app.governance.security import ProbingTracker, analyze_security
from app.models.schemas import GovernanceResult, Request

DEFAULT_MAX_REANALYSIS_LIMIT: Final[int] = 2


def run_single_governance_pass(
    request: Request,
    is_authorized: Optional[bool] = None,
    tracker: Optional[ProbingTracker] = None,
) -> GovernanceResult:
    findings = analyze_confidentiality(request) + analyze_security(
        request, tracker=tracker
    )
    risk_eval = evaluate_risk(findings, is_authorized=is_authorized)
    mitigation = determine_mitigation(
        request, risk_eval.risk_level, findings, is_authorized=is_authorized
    )

    return GovernanceResult(
        request_id=request.request_id,
        risk_level=risk_eval.risk_level,
        findings=findings,
        decision=mitigation.decision,
        reason=mitigation.reason,
        suggested_action=mitigation.suggested_action,
        modified_request=mitigation.modified_request,
    )


def reanalyze_request(
    request: Request,
    is_authorized: Optional[bool] = None,
    max_reanalysis_limit: int = DEFAULT_MAX_REANALYSIS_LIMIT,
    governance_fn: Optional[Callable[[Request], GovernanceResult]] = None,
    tracker: Optional[ProbingTracker] = None,
) -> tuple[GovernanceResult, list[GovernanceResult]]:
    reanalysis_tracker = ProbingTracker(threshold=9999)

    def default_analyze(req: Request, is_reanalysis: bool) -> GovernanceResult:
        active_tracker = reanalysis_tracker if is_reanalysis else tracker
        return run_single_governance_pass(
            req, is_authorized=is_authorized, tracker=active_tracker
        )

    analyze = (
        governance_fn
        if governance_fn is not None
        else (lambda req: default_analyze(req, is_reanalysis=False))
    )

    history: list[GovernanceResult] = []
    current_request = request
    reanalysis_count = 0

    while True:
        if governance_fn is not None:
            result = governance_fn(current_request)
        else:
            result = default_analyze(
                current_request, is_reanalysis=(reanalysis_count > 0)
            )

        history.append(result)

        if result.decision == "MODIFY" and result.modified_request is not None:
            if reanalysis_count >= max_reanalysis_limit:
                loop_prevention_result = GovernanceResult(
                    request_id=request.request_id,
                    risk_level="HIGH",
                    findings=result.findings,
                    decision="BLOCK",
                    reason=f"Maximum re-analysis limit ({max_reanalysis_limit}) exceeded without resolving to a safe state.",
                    suggested_action="BLOCK",
                    modified_request=None,
                )
                history.append(loop_prevention_result)
                return loop_prevention_result, history

            reanalysis_count += 1
            current_request = result.modified_request
            continue

        return result, history


def govern_request(
    request: Request,
    is_authorized: Optional[bool] = None,
    auth_provider: Optional[Callable[[Request], bool]] = None,
    audit_logger: Optional[AuditLogger] = None,
    tracker: Optional[ProbingTracker] = None,
) -> GovernanceResult:
    effective_is_authorized: Optional[bool] = is_authorized
    if auth_provider is not None:
        effective_is_authorized = auth_provider(request)

    final_result, history = reanalyze_request(
        request=request,
        is_authorized=effective_is_authorized,
        tracker=tracker,
    )

    if (
        final_result.decision == "ALLOW"
        and len(history) > 1
        and history[0].decision == "MODIFY"
    ):
        final_result.modified_request = history[0].modified_request

    logger = audit_logger if audit_logger is not None else default_audit_logger
    reanalysis_info = None
    if len(history) > 1:
        reanalysis_info = {
            "passes": len(history),
            "initial_decision": history[0].decision,
            "initial_risk": history[0].risk_level,
            "modified_fields": (
                history[0].modified_request.requested_fields
                if history[0].modified_request
                else None
            ),
            "final_decision": final_result.decision,
            "final_risk": final_result.risk_level,
            "trajectory": [
                {
                    "pass": idx,
                    "decision": res.decision,
                    "risk_level": res.risk_level,
                    "modified_fields": (
                        res.modified_request.requested_fields
                        if res.modified_request
                        else None
                    ),
                }
                for idx, res in enumerate(history)
            ],
        }

    logger.record_audit(
        request=request,
        result=final_result,
        human_action=None,
        reanalysis_info=reanalysis_info,
    )

    return final_result
