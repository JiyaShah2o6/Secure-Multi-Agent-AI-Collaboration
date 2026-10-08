from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, replace
from uuid import uuid4

from app.agents.data_agent import DataAgent
from app.authorization.data_minimization import check_data_minimization
from app.authorization.permissions import is_authorized
from app.governance.audit import AuditLogger, default_audit_logger
from app.governance.reanalysis import govern_request
from app.governance.security import ProbingTracker
from app.models.schemas import AgentResponse, GovernanceResult, Request


class AgentCommunication:
    """One session's governed transport. Raw requests cannot call the data reader."""

    def __init__(self, audit_logger=None, tracker=None):
        self.audit_logger = audit_logger if audit_logger is not None else default_audit_logger
        self.tracker = tracker if tracker is not None else ProbingTracker()
        self._approved = {}
        self._pending = {}
        self.data_agent = DataAgent(self._consume_approval)

    def _consume_approval(self, ticket):
        return self._approved.pop(ticket, None) if isinstance(ticket, str) else None

    def send_request(self, request):
        request_id = str(uuid4())
        try:
            strings = [request.sender, request.receiver, request.customer_id, request.purpose]
            if not all(isinstance(value, str) and value.strip() for value in strings):
                raise ValueError("Agent identities, customer ID, and purpose are required.")
            if (not isinstance(request.requested_fields, list) or not request.requested_fields
                    or not all(isinstance(f, str) and f.strip() for f in request.requested_fields)):
                raise ValueError("Requested fields must be a nonempty list of strings.")
            fields = [f.strip().lower() for f in request.requested_fields]
            fields = ["bank_account" if f == "bank_account_details" else f for f in fields]
            candidate = Request(request_id, request.sender, request.receiver,
                                request.customer_id.strip(), fields, request.purpose.strip())
        except (AttributeError, ValueError) as error:
            return AgentResponse("error", {}, str(error), {"request_id": request_id})
        return self._evaluate(candidate)

    def _evaluate(self, request, human_action=None):
        try:
            result = govern_request(request, audit_logger=self.audit_logger,
                                    tracker=self.tracker, enforce_policy=True,
                                    human_action=human_action)
        except Exception:
            # Audit/analysis failure must never fall through to the data agent.
            return AgentResponse("error", {}, "Governance or audit unavailable; no data retrieved.",
                                 {"request_id": request.request_id})
        if result.decision == "HUMAN_REVIEW":
            self._pending[request.request_id] = (deepcopy(request), deepcopy(result))
        effective = deepcopy(result.modified_request or request)
        policy = asdict(result)
        for finding in policy["findings"]:
            finding["evidence"] = "[redacted]" if finding["evidence"] else ""
        # Only structured fields are displayed; raw purpose/payloads stay out of diagnostics.
        policy["modified_request"] = {"requested_fields": effective.requested_fields} if result.modified_request else None
        metadata = {
            "request_id": request.request_id,
            "requested_fields": list(request.requested_fields),
            "effective_fields": list(effective.requested_fields),
            "authorization": is_authorized(request.sender, request.requested_fields),
            "data_minimization": check_data_minimization(request.purpose, request.requested_fields),
            "governance": policy,
        }
        if result.decision != "ALLOW":
            status = "unauthorized" if any("UNAUTHORIZED_ACCESS" in f.labels for f in result.findings) else {
                "BLOCK": "blocked", "RESTRICT": "restricted", "HUMAN_REVIEW": "human_review",
            }.get(result.decision, "blocked")
            return AgentResponse(status, {}, result.reason, metadata)
        # Ticket is opaque, single-use, and bound to a copy of the approved request.
        ticket = str(uuid4())
        self._approved[ticket] = effective
        try:
            response = self.data_agent.handle_request(ticket)
        except Exception:
            response = AgentResponse("error", {}, "Data retrieval failed.")
        finally:
            self._approved.pop(ticket, None)
        # Defense against accidental extra-field responses from the data module.
        if response.status == "success" and not set(response.data).issubset(effective.requested_fields):
            response = AgentResponse("blocked", {}, "Unexpected response fields withheld.")
        try:
            self.audit_logger.record_execution(request.request_id, response.status, list(response.data))
        except Exception:
            response = AgentResponse("error", {}, "Execution audit failed; response withheld.")
        response.metadata = metadata
        return response

    def review_request(self, request_id, action, *, purpose=None, fields=None):
        """Local demo reviewer: no ability to override permission or hostile-payload blocks."""
        if action not in {"Approve", "Restrict", "Reject"}:
            return AgentResponse("error", {}, "Unknown review action.")
        pending = self._pending.get(request_id)
        if pending is None:
            return AgentResponse("error", {}, "No pending review in this session.")
        request, previous = deepcopy(pending)
        if action == "Reject":
            result = GovernanceResult(request_id, previous.risk_level, previous.findings,
                                      "BLOCK", "Rejected by the demo reviewer.", "BLOCK")
            try:
                self.audit_logger.record_audit(request, result, human_action="REJECT")
            except Exception:
                return AgentResponse("error", {}, "Audit unavailable; review not completed.")
            self._pending.pop(request_id)
            return AgentResponse("blocked", {}, result.reason,
                                 {"request_id": request_id, "governance": asdict(result)})
        if purpose is not None:
            if not isinstance(purpose, str) or not purpose.strip():
                return AgentResponse("error", {}, "Select a supported review purpose.")
            request = replace(request, purpose=purpose.strip())
        if action == "Restrict":
            if (not isinstance(fields, list) or not fields
                    or not all(isinstance(f, str) and f in request.requested_fields for f in fields)):
                return AgentResponse("error", {}, "Restriction must select a nonempty subset of the pending fields.")
            request = replace(request, requested_fields=list(fields))
        self._pending.pop(request_id)
        response = self._evaluate(request, human_action=action.upper())
        if response.status == "error":
            self._pending[request_id] = pending
        return response
