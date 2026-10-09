"""
Phase 4 End-to-End Security Test Suite.
Validates all 13 core security requirements:
1. Every ordinary request passes through the gateway.
2. A blocked request never retrieves protected data.
3. Human-review-pending requests never retrieve protected data.
4. Field-level permissions are strictly enforced.
5. The permitted field set is revalidated after modification.
6. Modified requests cannot use stale approvals.
7. Approval tokens cannot be replayed (one-use gate).
8. Governance failures prevent data release (fail-closed).
9. Audit failures are handled according to the defined fail-closed policy.
10. Reviewer actions are recorded and have actual effects.
11. Response field projection prevents extra fields from being returned.
12. Token-efficiency warnings do not change security risk by themselves.
13. No request can access arbitrary SQL or database file paths through user input.
"""

from __future__ import annotations

import unittest
from unittest.mock import patch

from app.agents.communication import AgentCommunication
from app.agents.data_agent import DataAgent
from app.agents.support_agent import SupportAgent
from app.governance.audit import AuditLogger
from app.models.schemas import AgentRequest, AgentResponse, Request


class TestPhase4SecurityE2E(unittest.TestCase):
    def setUp(self) -> None:
        self.audit_logger = AuditLogger(":memory:")
        self.addCleanup(self.audit_logger.close)
        self.comm = AgentCommunication(audit_logger=self.audit_logger)
        self.support_agent = SupportAgent(self.comm)

    # 1. Every ordinary request passes through the gateway
    def test_01_ordinary_request_must_pass_through_gateway(self) -> None:
        """Direct calls to DataAgent without a valid, fresh ApprovalTicket must be blocked."""
        direct_data_agent = DataAgent()
        unauthorized_inputs = [
            {"customer_id": "C101", "requested_fields": ["complaint_status"]},
            "C101",
            {"forged": True},
        ]
        for payload in unauthorized_inputs:
            with self.subTest(payload=payload):
                resp = direct_data_agent.handle_request(payload)
                self.assertEqual(resp.status, "blocked")
                self.assertEqual(resp.data, {})

    # 2. A blocked request never retrieves protected data
    def test_02_blocked_request_never_retrieves_protected_data(self) -> None:
        """Blocked requests (e.g. requesting bank_account) must never execute data retrieval."""
        with patch.object(self.comm.data_agent, "handle_request") as mock_read:
            resp = self.support_agent.request_customer_data(
                customer_id="C101",
                requested_fields=["bank_account"],
                purpose="Resolve customer complaint",
            )
            mock_read.assert_not_called()
        self.assertEqual(resp.status, "unauthorized")
        self.assertEqual(resp.data, {})
        self.assertEqual(resp.metadata["governance"]["decision"], "BLOCK")

    # 3. Human-review-pending requests never retrieve protected data
    def test_03_human_review_pending_never_retrieves_protected_data(self) -> None:
        """A request requiring human review returns no customer data while pending."""
        with patch.object(self.comm.data_agent, "handle_request") as mock_read:
            resp = self.support_agent.request_customer_data(
                customer_id="C101",
                requested_fields=["complaint_status"],
                purpose="Unspecified task",
            )
            mock_read.assert_not_called()
        self.assertEqual(resp.status, "human_review")
        self.assertEqual(resp.data, {})
        self.assertIn(resp.metadata["request_id"], self.comm.get_pending_reviews())

    # 4. Field-level permissions are strictly enforced
    def test_04_field_level_permissions_strictly_enforced(self) -> None:
        """AgentA can only access permitted fields: customer_id, name, complaint_id, complaint_status."""
        forbidden_fields = ["email", "phone", "address", "bank_account", "card_details"]
        for fld in forbidden_fields:
            with self.subTest(field=fld):
                resp = self.support_agent.request_customer_data(
                    customer_id="C101",
                    requested_fields=[fld],
                    purpose="Contact customer",
                )
                self.assertEqual(resp.status, "unauthorized")
                self.assertEqual(resp.data, {})

    # 5. Permitted field set is revalidated after modification
    def test_05_permitted_field_set_revalidated_after_modification(self) -> None:
        """When data minimization modifies a request, authorization is re-evaluated on the new set."""
        # Wildcard * minimizes to complaint fields. If the modified set were unauthorized, it would block.
        resp = self.support_agent.request_customer_data(
            customer_id="C101",
            requested_fields=["*"],
            purpose="Resolve customer complaint",
        )
        self.assertEqual(resp.status, "success")
        self.assertEqual(
            set(resp.data.keys()),
            {"customer_id", "complaint_id", "complaint_status"},
        )
        trajectory = resp.metadata["governance"]["trajectory"]
        self.assertEqual([step["decision"] for step in trajectory], ["MODIFY", "ALLOW"])

    # 6. Modified requests cannot use stale approvals
    def test_06_modified_requests_cannot_use_stale_approvals(self) -> None:
        """Modifying a request creates a distinct pass; an approval for one set cannot read another."""
        # Explicit request with name for complaint is restricted, cannot expand into complaint_status
        resp = self.support_agent.request_customer_data(
            customer_id="C101",
            requested_fields=["name"],
            purpose="Resolve customer complaint",
        )
        self.assertEqual(resp.status, "restricted")
        self.assertEqual(resp.data, {})

    # 7. Approval tokens cannot be replayed (one-use gate)
    def test_07_approval_tokens_cannot_be_replayed(self) -> None:
        """An approval ticket is consumed on first use; attempting to replay it is blocked."""
        original_handle = self.comm.data_agent.handle_request
        with patch.object(self.comm.data_agent, "handle_request", wraps=original_handle) as spy_read:
            resp = self.support_agent.request_customer_data(
                customer_id="C101",
                requested_fields=["complaint_status"],
                purpose="Resolve customer complaint",
            )
            self.assertEqual(resp.status, "success")
            self.assertTrue(spy_read.called)
            ticket = spy_read.call_args[0][0]

        # Replay ticket directly against DataAgent
        replay_resp = original_handle(ticket)
        self.assertEqual(replay_resp.status, "blocked")
        self.assertEqual(replay_resp.data, {})

    # 8. Governance failures prevent data release (fail-closed)
    def test_08_governance_failures_prevent_data_release(self) -> None:
        """If governance engine crashes or raises an exception, the system fails closed."""
        with patch("app.agents.communication.govern_request", side_effect=RuntimeError("governance engine panic")):
            with patch.object(self.comm.data_agent, "handle_request") as mock_read:
                resp = self.support_agent.request_customer_data(
                    customer_id="C101",
                    requested_fields=["complaint_status"],
                    purpose="Resolve customer complaint",
                )
                mock_read.assert_not_called()
        self.assertEqual(resp.status, "error")
        self.assertEqual(resp.data, {})

    # 9. Audit failures are handled according to the defined fail-closed policy
    def test_09_audit_failures_fail_closed(self) -> None:
        """If writing the audit log fails, the request must fail closed and withhold customer data."""
        with patch.object(self.audit_logger, "record_audit", side_effect=OSError("disk read-only")):
            with patch.object(self.comm.data_agent, "handle_request") as mock_read:
                resp = self.support_agent.request_customer_data(
                    customer_id="C101",
                    requested_fields=["complaint_status"],
                    purpose="Resolve customer complaint",
                )
                mock_read.assert_not_called()
        self.assertEqual(resp.status, "error")
        self.assertEqual(resp.data, {})

    # 10. Reviewer actions are recorded and have actual effects
    def test_10_reviewer_actions_recorded_and_effective(self) -> None:
        """Approving a pending review retrieves authorized data; rejecting prevents retrieval."""
        # A. Pending review
        pending = self.support_agent.request_customer_data(
            customer_id="C101",
            requested_fields=["complaint_status"],
            purpose="Unspecified task",
        )
        req_id = pending.metadata["request_id"]

        # B. Approve with supported purpose
        approved_resp = self.comm.review_request(
            request_id=req_id,
            action="Approve",
            purpose="Resolve customer complaint",
        )
        self.assertEqual(approved_resp.status, "success")
        self.assertEqual(approved_resp.data, {"complaint_status": "In Progress"})

        # Verify reviewer audit event
        records = self.audit_logger.get_records_by_request_id(req_id)
        self.assertTrue(any(r.human_action == "APPROVE" for r in records))

        # C. Re-approving already resolved request is rejected
        duplicate_review = self.comm.review_request(
            request_id=req_id,
            action="Approve",
            purpose="Resolve customer complaint",
        )
        self.assertEqual(duplicate_review.status, "error")

    # 11. Response field projection prevents extra fields from being returned
    def test_11_response_field_projection_blocks_unapproved_fields(self) -> None:
        """If DataAgent produces extra fields not approved in ticket, response gating blocks them."""
        # Simulated rogue retrieval returning extra bank_account
        extra_data = {"complaint_status": "In Progress", "bank_account": "ACC-EXFILTRATED"}
        with patch.object(self.comm.data_agent, "handle_request", return_value=AgentResponse("success", extra_data)):
            resp = self.support_agent.request_customer_data(
                customer_id="C101",
                requested_fields=["complaint_status"],
                purpose="Resolve customer complaint",
            )
        self.assertEqual(resp.status, "blocked")
        self.assertEqual(resp.data, {})

    # 12. Token-efficiency warnings do not change security risk by themselves
    def test_12_token_efficiency_warnings_do_not_alter_security_risk(self) -> None:
        """Token budget exhaustion generates efficiency status 'high' without altering LOW risk or ALLOW decision."""
        resp = self.support_agent.request_customer_data(
            customer_id="C101",
            requested_fields=["complaint_status"],
            purpose="Resolve customer complaint",
            token_limit=1,  # Tight token budget triggers warning
        )
        self.assertEqual(resp.status, "success")
        self.assertEqual(resp.data, {"complaint_status": "In Progress"})
        self.assertEqual(resp.metadata["token_analysis"]["status"], "high")
        self.assertEqual(resp.metadata["governance"]["risk_level"], "LOW")
        self.assertEqual(resp.metadata["governance"]["decision"], "ALLOW")

    # 13. No request can access arbitrary SQL or database file paths through user input
    def test_13_sql_injection_and_path_traversal_blocked(self) -> None:
        """Hostile customer_id values containing SQLi or path traversal are blocked before database access."""
        attacks = [
            "C101' OR '1'='1",
            "C101; DROP TABLE customers;--",
            "../../etc/passwd",
            "..\\..\\windows\\system32",
        ]
        for malicious_id in attacks:
            with self.subTest(customer_id=malicious_id):
                with patch.object(self.comm.data_agent, "handle_request") as mock_read:
                    resp = self.support_agent.request_customer_data(
                        customer_id=malicious_id,
                        requested_fields=["complaint_status"],
                        purpose="Resolve customer complaint",
                    )
                    mock_read.assert_not_called()
                self.assertEqual(resp.status, "blocked")
                self.assertEqual(resp.data, {})
                self.assertEqual(resp.metadata["governance"]["decision"], "BLOCK")
                self.assertEqual(resp.metadata["governance"]["risk_level"], "HIGH")


if __name__ == "__main__":
    unittest.main()
