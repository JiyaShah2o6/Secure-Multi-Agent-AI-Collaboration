from __future__ import annotations

import secrets
import time
from copy import deepcopy
from dataclasses import asdict, replace
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from app.agents.data_agent import DataAgent
from app.authorization.data_minimization import check_data_minimization
from app.authorization.permissions import is_authorized
from app.governance.audit import AuditLogger, default_audit_logger
from app.governance.reanalysis import authorization_provider, govern_request
from app.governance.security import ProbingTracker
from app.models.schemas import (
    AgentResponse,
    ApprovalTicket,
    GovernanceResult,
    Request,
    ReviewItem,
    ReviewStatus,
    validate_request_schema,
)


class AgentCommunication:
    """
    Request Gateway and governed transport for agent-to-agent data access.
    Raw requests cannot call the data reader directly.
    """

    def __init__(self, audit_logger=None, tracker=None, customer_repository=None):
        self.audit_logger = audit_logger if audit_logger is not None else default_audit_logger
        self.tracker = tracker if tracker is not None else ProbingTracker()
        self.customer_repository = customer_repository
        self._approved: dict[str, ApprovalTicket] = {}
        self._pending: dict[str, Any] = {}
        self._review_history: dict[str, ReviewItem] = {}
        self.data_agent = DataAgent(self._consume_approval, repository=customer_repository)

    def _consume_approval(
        self,
        ticket_token: str,
        customer_id: Optional[str] = None,
        requested_fields: Optional[list[str]] = None,
    ) -> Optional[Request]:
        """
        Validate and consume a single-use approval ticket.
        Verifies token existence, single-use consumption, TTL expiration,
        decision state, and customer/field set binding.
        """
        if not isinstance(ticket_token, str):
            return None

        ticket = self._approved.get(ticket_token)
        if ticket is None:
            return None

        # Check if already consumed
        if ticket.consumed:
            self._approved.pop(ticket_token, None)
            return None

        # Check expiration
        now = time.time()
        if now - ticket.created_at > ticket.ttl_seconds:
            self._approved.pop(ticket_token, None)
            return None

        # Check decision
        if ticket.decision != "ALLOW":
            self._approved.pop(ticket_token, None)
            return None

        # Check customer binding
        if customer_id is not None and ticket.customer_id != customer_id:
            self._approved.pop(ticket_token, None)
            return None

        # Check field set binding
        if requested_fields is not None and not set(requested_fields).issubset(set(ticket.requested_fields)):
            self._approved.pop(ticket_token, None)
            return None

        # Mark consumed and pop immediately
        ticket.consumed = True
        self._approved.pop(ticket_token, None)

        return Request(
            request_id=ticket.request_id,
            sender="AgentA",
            receiver="AgentB",
            customer_id=ticket.customer_id,
            requested_fields=list(ticket.requested_fields),
            purpose="[approved]",
        )

    def send_request(self, request: Any) -> AgentResponse:
        """
        Request Gateway entry point: validates request schema before governance.
        Rejections are audited with a safe event record.
        """
        request_id = getattr(request, "request_id", None) or str(uuid4())

        try:
            validate_request_schema(request)
            fields = [f.strip().lower() for f in request.requested_fields]
            fields = ["bank_account" if f == "bank_account_details" else f for f in fields]
            candidate = Request(
                request_id=str(request_id),
                sender=str(request.sender).strip(),
                receiver=str(request.receiver).strip(),
                customer_id=str(request.customer_id).strip(),
                requested_fields=fields,
                purpose=str(request.purpose).strip(),
            )
        except (AttributeError, ValueError):
            try:
                self.audit_logger.record_rejection(
                    request_id,
                    **{
                        key: getattr(request, key, None)
                        for key in ("sender", "receiver", "customer_id", "requested_fields", "purpose")
                    },
                )
            except Exception:
                return AgentResponse(
                    "error",
                    {},
                    "Invalid request; audit unavailable. No data retrieved.",
                    {"request_id": request_id},
                )
            return AgentResponse(
                "error",
                {},
                "Invalid request; rejection audited. No data retrieved.",
                {"request_id": request_id},
            )

        return self._evaluate(candidate)

    def _evaluate(
        self,
        request: Request,
        human_action: Optional[str] = None,
        review_scope: Optional[list[str]] = None,
        reviewer_id: str = "demo_reviewer",
    ) -> AgentResponse:
        # Binds authorization and minimization to reviewer scope when present.
        provider = None
        if review_scope is not None:
            scope = frozenset(review_scope)
            provider = lambda candidate: (
                authorization_provider(candidate)
                and set(candidate.requested_fields).issubset(scope)
            )

        try:
            result = govern_request(
                request,
                audit_logger=self.audit_logger,
                tracker=self.tracker,
                enforce_policy=True,
                human_action=human_action,
                auth_provider=provider,
                field_scope=review_scope,
            )
        except Exception:
            # Audit or governance failure fails closed: never call data agent.
            return AgentResponse(
                "error",
                {},
                "Governance or audit unavailable; no data retrieved.",
                {"request_id": request.request_id},
            )

        review_item = ReviewItem(
            request_id=request.request_id,
            status=ReviewStatus.PENDING_REVIEW if result.decision == "HUMAN_REVIEW" else ReviewStatus.COMPLETED,
            request=deepcopy(request),
            previous_result=deepcopy(result),
            review_scope=deepcopy(review_scope),
            created_at=datetime.now(timezone.utc).isoformat(),
            reviewer_id=reviewer_id if human_action else None,
            action=human_action,
            resulting_decision=result.decision,
        )

        if result.decision == "HUMAN_REVIEW":
            self._pending[request.request_id] = review_item
        else:
            self._review_history[request.request_id] = review_item

        effective = deepcopy(result.modified_request or request)
        policy = asdict(result)
        for finding in policy["findings"]:
            finding["evidence"] = "[redacted]" if finding["evidence"] else ""
        policy["modified_request"] = (
            {"requested_fields": effective.requested_fields}
            if result.modified_request
            else None
        )

        metadata = {
            "request_id": request.request_id,
            "requested_fields": list(request.requested_fields),
            "effective_fields": list(effective.requested_fields),
            "authorization": is_authorized(request.sender, request.requested_fields),
            "data_minimization": check_data_minimization(request.purpose, request.requested_fields),
            "governance": policy,
            "review_scope": list(review_scope) if review_scope is not None else None,
        }

        if result.decision != "ALLOW":
            status = (
                "unauthorized"
                if any("UNAUTHORIZED_ACCESS" in f.labels for f in result.findings)
                else {
                    "BLOCK": "blocked",
                    "RESTRICT": "restricted",
                    "HUMAN_REVIEW": "human_review",
                }.get(result.decision, "blocked")
            )
            return AgentResponse(status, {}, result.reason, metadata)

        # Defense-in-depth: Final sanity check on effective fields before ticket issuance.
        if not is_authorized(request.sender, effective.requested_fields)["authorized"]:
            return AgentResponse(
                "blocked",
                {},
                "Inconsistent governance decision withheld; unauthorized fields present.",
                metadata,
            )

        # Cryptographically secure random bearer token bound to request_id and effective fields
        token = secrets.token_urlsafe(32)
        ticket = ApprovalTicket(
            token=token,
            request_id=request.request_id,
            customer_id=effective.customer_id,
            requested_fields=list(effective.requested_fields),
            decision=result.decision,
            created_at=time.time(),
            ttl_seconds=30.0,
        )
        self._approved[token] = ticket

        try:
            response = self.data_agent.handle_request(
                token,
                customer_id=effective.customer_id,
                requested_fields=list(effective.requested_fields),
            )
        except Exception:
            response = AgentResponse("error", {}, "Data retrieval failed.")
        finally:
            self._approved.pop(token, None)

        if not isinstance(response, AgentResponse) or not isinstance(response.data, dict):
            response = AgentResponse("error", {}, "Invalid downstream response withheld.")
        elif response.status != "success":
            response = AgentResponse("error", {}, "Data retrieval did not succeed; response withheld.")
        elif not set(response.data).issubset(effective.requested_fields):
            response = AgentResponse("blocked", {}, "Unexpected response fields withheld.")

        try:
            self.audit_logger.record_execution(request.request_id, response.status, list(response.data))
        except Exception:
            response = AgentResponse("error", {}, "Execution audit failed; response withheld.")

        response.metadata = metadata
        return response

    def get_review_item(self, request_id: str) -> Optional[ReviewItem]:
        """Query the review state of a request in this session."""
        pending = self._pending.get(request_id)
        if isinstance(pending, ReviewItem):
            return pending
        return self._review_history.get(request_id)

    def get_pending_reviews(self) -> dict[str, Any]:
        """Query all pending review requests in this session."""
        return dict(self._pending)

    def get_review_history(self) -> dict[str, ReviewItem]:
        """Query all completed/historical review records in this session."""
        return dict(self._review_history)

    def review_request(
        self,
        request_id: str,
        action: str,
        *,
        purpose: Optional[str] = None,
        fields: Optional[list[str]] = None,
        reviewer_id: str = "demo_reviewer",
        reason: str = "",
    ) -> AgentResponse:
        """
        Backend state transition handler for human review:
        Supports Approve, Restrict, Modify, Reject.
        Reviewer actions alter the real request state and rerun governance.
        Approval cannot override hard permission denials or hostile-payload blocks.
        """
        normalized_action = action.strip().capitalize() if isinstance(action, str) else ""
        if normalized_action not in {"Approve", "Restrict", "Modify", "Reject"}:
            return AgentResponse("error", {}, "Unknown review action.")

        pending = self._pending.get(request_id)
        if pending is None:
            return AgentResponse("error", {}, "No pending review in this session.")

        if isinstance(pending, ReviewItem):
            request = deepcopy(pending.request)
            previous = deepcopy(pending.previous_result)
            review_scope = deepcopy(pending.review_scope)
        else:
            request, previous, review_scope = deepcopy(pending)

        now_iso = datetime.now(timezone.utc).isoformat()

        if normalized_action == "Reject":
            decision_reason = reason.strip() or "Rejected by the demo reviewer."
            result = GovernanceResult(
                request_id,
                previous.risk_level,
                previous.findings,
                "BLOCK",
                decision_reason,
                "BLOCK",
            )
            try:
                self.audit_logger.record_audit(request, result, human_action="REJECT")
            except Exception:
                return AgentResponse("error", {}, "Audit unavailable; review not completed.")

            self._pending.pop(request_id, None)
            self._review_history[request_id] = ReviewItem(
                request_id=request_id,
                status=ReviewStatus.REJECTED,
                request=request,
                previous_result=result,
                review_scope=review_scope,
                action="REJECT",
                action_timestamp=now_iso,
                reviewer_id=reviewer_id,
                reason=decision_reason,
                resulting_decision="BLOCK",
            )
            return AgentResponse(
                "blocked",
                {},
                result.reason,
                {"request_id": request_id, "governance": asdict(result)},
            )

        if normalized_action == "Modify":
            if purpose is not None:
                if not isinstance(purpose, str) or not purpose.strip():
                    return AgentResponse("error", {}, "Select a supported review purpose.")
                request = replace(request, purpose=purpose.strip())
            if fields is not None:
                if not isinstance(fields, list) or not fields or not all(isinstance(f, str) and f.strip() for f in fields):
                    return AgentResponse("error", {}, "Modification must provide a non-empty list of fields.")
                clean_fields = [f.strip().lower() for f in fields]
                clean_fields = ["bank_account" if f == "bank_account_details" else f for f in clean_fields]
                request = replace(request, requested_fields=clean_fields)
                review_scope = clean_fields

        elif normalized_action == "Restrict":
            if (
                not isinstance(fields, list)
                or not fields
                or not all(isinstance(f, str) and f in request.requested_fields for f in fields)
            ):
                return AgentResponse(
                    "error",
                    {},
                    "Restriction must select a nonempty subset of the pending fields.",
                )
            clean_fields = [f.strip().lower() for f in fields]
            clean_fields = ["bank_account" if f == "bank_account_details" else f for f in clean_fields]
            request = replace(request, requested_fields=list(clean_fields))
            review_scope = list(clean_fields)
            if purpose is not None:
                if not isinstance(purpose, str) or not purpose.strip():
                    return AgentResponse("error", {}, "Select a supported review purpose.")
                request = replace(request, purpose=purpose.strip())

        elif normalized_action == "Approve":
            if purpose is not None:
                if not isinstance(purpose, str) or not purpose.strip():
                    return AgentResponse("error", {}, "Select a supported review purpose.")
                request = replace(request, purpose=purpose.strip())

        self._pending.pop(request_id, None)
        response = self._evaluate(
            request,
            human_action=normalized_action.upper(),
            review_scope=review_scope,
            reviewer_id=reviewer_id,
        )

        if response.status == "error":
            self._pending[request_id] = pending

        return response
