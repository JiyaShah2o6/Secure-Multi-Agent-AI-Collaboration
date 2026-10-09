import time
import unittest
from unittest.mock import patch

from app.agents.communication import AgentCommunication
from app.agents.data_agent import DataAgent
from app.agents.support_agent import SupportAgent
from app.governance.audit import AuditLogger
from app.governance.reanalysis import govern_request
from app.governance.security import ProbingTracker
from app.models.schemas import AgentRequest, AgentResponse, Request, ReviewStatus

PURPOSE_COMPLAINT = "Resolve customer complaint"
PURPOSE_CONTACT = "Contact customer"


class TestPhase1Governance(unittest.TestCase):
    def setUp(self):
        self.logger = AuditLogger(":memory:")
        self.addCleanup(self.logger.close)
        self.tracker = ProbingTracker()
        self.transport = AgentCommunication(audit_logger=self.logger, tracker=self.tracker)
        self.agent = SupportAgent(self.transport)

    # 1. Authorized field access
    def test_authorized_field_access(self):
        response = self.agent.request_customer_data(
            "C101", ["complaint_status"], PURPOSE_COMPLAINT
        )
        self.assertEqual(response.status, "success")
        self.assertEqual(response.data, {"complaint_status": "In Progress"})
        self.assertEqual(response.metadata["governance"]["decision"], "ALLOW")

    # 2. Unauthorized field access
    def test_unauthorized_field_access(self):
        with patch.object(self.transport.data_agent, "handle_request") as read:
            response = self.agent.request_customer_data(
                "C101", ["bank_account"], PURPOSE_COMPLAINT
            )
            read.assert_not_called()
        self.assertEqual(response.status, "unauthorized")
        self.assertEqual(response.data, {})
        gov = response.metadata["governance"]
        self.assertEqual(gov["decision"], "BLOCK")
        self.assertEqual(gov["risk_level"], "HIGH")
        findings_labels = [lbl for f in gov["findings"] for lbl in f["labels"]]
        self.assertIn("UNAUTHORIZED_ACCESS", findings_labels)
        self.assertIn("UNAUTHORIZED_FIELD", findings_labels)

    # 3. Mixed permitted and forbidden fields
    def test_mixed_permitted_and_forbidden_fields(self):
        with patch.object(self.transport.data_agent, "handle_request") as read:
            response = self.agent.request_customer_data(
                "C101", ["complaint_status", "bank_account"], PURPOSE_COMPLAINT
            )
            read.assert_not_called()
        self.assertEqual(response.status, "unauthorized")
        self.assertEqual(response.data, {})
        gov = response.metadata["governance"]
        self.assertEqual(gov["decision"], "BLOCK")
        findings_labels = [lbl for f in gov["findings"] for lbl in f["labels"]]
        self.assertIn("MIXED_PERMISSIONS", findings_labels)
        self.assertIn("UNAUTHORIZED_ACCESS", findings_labels)

    # 4. Unknown fields
    def test_unknown_fields(self):
        with patch.object(self.transport.data_agent, "handle_request") as read:
            response = self.agent.request_customer_data(
                "C101", ["unknown_credit_score"], PURPOSE_COMPLAINT
            )
            read.assert_not_called()
        self.assertEqual(response.data, {})
        gov = response.metadata["governance"]
        self.assertEqual(gov["decision"], "BLOCK")
        findings_labels = [lbl for f in gov["findings"] for lbl in f["labels"]]
        self.assertIn("UNKNOWN_FIELD", findings_labels)

    # 5. Invalid agent identity (sender)
    def test_invalid_agent_sender(self):
        bad_request = AgentRequest("ImposterAgent", "AgentB", "C101", ["name"], PURPOSE_COMPLAINT)
        response = self.transport.send_request(bad_request)
        self.assertEqual(response.status, "unauthorized")
        self.assertEqual(response.data, {})
        gov = response.metadata["governance"]
        self.assertEqual(gov["decision"], "BLOCK")
        findings_labels = [lbl for f in gov["findings"] for lbl in f["labels"]]
        self.assertIn("INVALID_SENDER", findings_labels)
        self.assertIn("UNAUTHORIZED_ACCESS", findings_labels)

    # 6. Invalid receiver
    def test_invalid_receiver(self):
        bad_request = AgentRequest("AgentA", "UnknownDatabase", "C101", ["name"], PURPOSE_COMPLAINT)
        response = self.transport.send_request(bad_request)
        self.assertEqual(response.status, "unauthorized")
        self.assertEqual(response.data, {})
        gov = response.metadata["governance"]
        self.assertEqual(gov["decision"], "BLOCK")
        findings_labels = [lbl for f in gov["findings"] for lbl in f["labels"]]
        self.assertIn("INVALID_RECEIVER", findings_labels)
        self.assertIn("UNAUTHORIZED_ACCESS", findings_labels)

    # 7. Over-broad request modification
    def test_over_broad_request_modification(self):
        response = self.agent.request_customer_data("C101", ["*"], PURPOSE_COMPLAINT)
        gov = response.metadata["governance"]
        self.assertEqual(len(gov["trajectory"]), 2)
        self.assertEqual(gov["trajectory"][0]["decision"], "MODIFY")
        self.assertEqual(
            gov["trajectory"][0]["modified_fields"],
            ["customer_id", "complaint_id", "complaint_status"],
        )

    # 8. Re-analysis resulting in ALLOW
    def test_reanalysis_resulting_in_allow(self):
        response = self.agent.request_customer_data("C101", ["*"], PURPOSE_COMPLAINT)
        self.assertEqual(response.status, "success")
        gov = response.metadata["governance"]
        self.assertEqual(gov["decision"], "ALLOW")
        self.assertEqual([p["decision"] for p in gov["trajectory"]], ["MODIFY", "ALLOW"])
        self.assertEqual(
            set(response.data.keys()),
            {"customer_id", "complaint_id", "complaint_status"},
        )

    # 9. Re-analysis resulting in BLOCK
    def test_reanalysis_resulting_in_block(self):
        req = Request("block-reanalysis", "AgentA", "AgentB", "C101", ["*"], PURPOSE_COMPLAINT)
        # Auth provider that approves pass 0 (wildcard) but rejects pass 1 (concrete fields)
        def provider(candidate):
            return candidate.requested_fields == ["*"]

        res = govern_request(
            req,
            auth_provider=provider,
            enforce_policy=True,
            audit_logger=self.logger,
            tracker=self.tracker,
        )
        self.assertEqual(res.decision, "BLOCK")
        self.assertEqual(res.risk_level, "HIGH")

    # 10. Re-analysis limit exceeded
    def test_reanalysis_limit_exceeded(self):
        req = Request("limit-req", "AgentA", "AgentB", "C101", ["*"], PURPOSE_COMPLAINT)
        # A governance function that persistently returns MODIFY
        def loop_fn(r):
            res = govern_request(
                r,
                enforce_policy=True,
                audit_logger=self.logger,
                tracker=self.tracker,
            )
            res.decision = "MODIFY"
            res.modified_request = req
            return res

        from app.governance.reanalysis import reanalyze_request
        final, history = reanalyze_request(req, governance_fn=loop_fn, max_reanalysis_limit=2)
        self.assertEqual(final.decision, "BLOCK")
        self.assertIn("Maximum re-analysis limit (2) exceeded", final.reason)
        # Pass 0, pass 1, pass 2 + final blocked record = 4 entries in trajectory history
        self.assertEqual(len(history), 4)

    # 11. Pending human review does not retrieve data
    def test_pending_human_review_does_not_retrieve_data(self):
        with patch.object(self.transport.data_agent, "handle_request") as read:
            response = self.transport.send_request(
                AgentRequest("AgentA", "AgentB", "C101", ["complaint_status"], "Unspecified task")
            )
            read.assert_not_called()
        self.assertEqual(response.status, "human_review")
        self.assertEqual(response.data, {})
        review_item = self.transport.get_review_item(response.metadata["request_id"])
        self.assertIsNotNone(review_item)
        self.assertEqual(review_item.status, ReviewStatus.PENDING_REVIEW)

    # 12. Reviewer rejection does not retrieve data
    def test_reviewer_rejection_does_not_retrieve_data(self):
        pending = self.transport.send_request(
            AgentRequest("AgentA", "AgentB", "C101", ["complaint_status"], "Unspecified task")
        )
        req_id = pending.metadata["request_id"]
        with patch.object(self.transport.data_agent, "handle_request") as read:
            res = self.transport.review_request(req_id, "Reject", reviewer_id="supervisor_alice")
            read.assert_not_called()
        self.assertEqual(res.status, "blocked")
        self.assertEqual(res.data, {})
        review_item = self.transport.get_review_item(req_id)
        self.assertEqual(review_item.status, ReviewStatus.REJECTED)
        self.assertEqual(review_item.reviewer_id, "supervisor_alice")

    # 13. Reviewer modification is revalidated
    def test_reviewer_modification_is_revalidated(self):
        pending = self.transport.send_request(
            AgentRequest("AgentA", "AgentB", "C101", ["complaint_status"], "Unspecified task")
        )
        req_id = pending.metadata["request_id"]
        # Reviewer modifies purpose to valid purpose and adds permitted fields
        reviewed = self.transport.review_request(
            req_id, "Modify", purpose=PURPOSE_COMPLAINT, fields=["complaint_status"]
        )
        self.assertEqual(reviewed.status, "success")
        self.assertEqual(reviewed.data, {"complaint_status": "In Progress"})
        review_item = self.transport.get_review_item(req_id)
        self.assertEqual(review_item.status, ReviewStatus.COMPLETED)

    # 14. Unauthorized access cannot be overridden by simple approval
    def test_unauthorized_access_cannot_be_overridden_by_simple_approval(self):
        # 14a. Hard unauthorized requests are blocked at gateway and never even queued for review
        blocked_direct = self.transport.send_request(
            AgentRequest("AgentA", "AgentB", "C101", ["bank_account"], PURPOSE_COMPLAINT)
        )
        self.assertEqual(blocked_direct.status, "unauthorized")
        self.assertNotIn(blocked_direct.metadata["request_id"], self.transport._pending)

        # 14b. If a request is in pending review, reviewer cannot inject or approve unauthorized fields
        pending = self.transport.send_request(
            AgentRequest("AgentA", "AgentB", "C101", ["complaint_status"], "Unspecified task")
        )
        req_id = pending.metadata["request_id"]
        with patch.object(self.transport.data_agent, "handle_request") as read:
            # Reviewer attempts to modify request to inject forbidden field bank_account
            modified_unauth = self.transport.review_request(
                req_id, "Modify", fields=["bank_account"], purpose="Process payment/refund"
            )
            read.assert_not_called()
        self.assertEqual(modified_unauth.status, "unauthorized")
        self.assertEqual(modified_unauth.data, {})
        self.assertEqual(modified_unauth.metadata["governance"]["decision"], "BLOCK")

    # 15. Approval token reuse fails
    def test_approval_token_reuse_fails(self):
        original_handle = self.transport.data_agent.handle_request
        captured_ticket = []

        def spy_handle(ticket, *args, **kwargs):
            captured_ticket.append(ticket)
            return original_handle(ticket, *args, **kwargs)

        with patch.object(self.transport.data_agent, "handle_request", side_effect=spy_handle):
            res = self.agent.request_customer_data("C101", ["complaint_status"], PURPOSE_COMPLAINT)
            self.assertEqual(res.status, "success")

        token = captured_ticket[0]
        # Direct attempt to reuse consumed token fails
        replay = self.transport.data_agent.handle_request(token)
        self.assertEqual(replay.status, "blocked")

    # 16. Approval token / request field mismatch fails
    def test_approval_token_request_field_mismatch_fails(self):
        # Manually issue a ticket bound to ["complaint_status"]
        import secrets
        from app.models.schemas import ApprovalTicket
        fake_token = secrets.token_urlsafe(32)
        self.transport._approved[fake_token] = ApprovalTicket(
            token=fake_token,
            request_id="mismatch-test",
            customer_id="C101",
            requested_fields=["complaint_status"],
            decision="ALLOW",
            created_at=time.time(),
            ttl_seconds=30.0,
        )
        # DataAgent called with mismatched customer
        mismatched_cust = self.transport.data_agent.handle_request(
            fake_token, customer_id="C102", requested_fields=["complaint_status"]
        )
        self.assertEqual(mismatched_cust.status, "blocked")

        # Now test field mismatch
        fake_token2 = secrets.token_urlsafe(32)
        self.transport._approved[fake_token2] = ApprovalTicket(
            token=fake_token2,
            request_id="mismatch-test-2",
            customer_id="C101",
            requested_fields=["complaint_status"],
            decision="ALLOW",
            created_at=time.time(),
            ttl_seconds=30.0,
        )
        mismatched_fields = self.transport.data_agent.handle_request(
            fake_token2, customer_id="C101", requested_fields=["bank_account"]
        )
        self.assertEqual(mismatched_fields.status, "blocked")

    # 17. Governance errors prevent retrieval (fail closed)
    def test_governance_errors_prevent_retrieval(self):
        with patch("app.agents.communication.govern_request", side_effect=RuntimeError("Governance crashed!")):
            with patch.object(self.transport.data_agent, "handle_request") as read:
                response = self.agent.request_customer_data(
                    "C101", ["complaint_status"], PURPOSE_COMPLAINT
                )
                read.assert_not_called()
        self.assertEqual(response.status, "error")
        self.assertEqual(response.data, {})
        self.assertIn("Governance or audit unavailable", response.message)

    # 18. Only final approved fields reach Agent B
    def test_only_final_approved_fields_reach_agent_b(self):
        # Request with wildcard
        response = self.agent.request_customer_data("C101", ["*"], PURPOSE_COMPLAINT)
        self.assertEqual(response.status, "success")
        # Allowed for Agent A and required for complaint
        expected_fields = {"customer_id", "complaint_id", "complaint_status"}
        self.assertEqual(set(response.data.keys()), expected_fields)
        self.assertNotIn("bank_account", response.data)
        self.assertNotIn("card_details", response.data)
        self.assertNotIn("address", response.data)
        self.assertNotIn("name", response.data)


if __name__ == "__main__":
    unittest.main()
