import unittest
from unittest.mock import patch

from app.agents.communication import AgentCommunication
from app.governance.audit import AuditLogger
from app.governance.security import ProbingTracker
from app.models.schemas import AgentRequest


class TestReviewAndValidation(unittest.TestCase):
    def setUp(self):
        self.logger = AuditLogger(":memory:")
        self.addCleanup(self.logger.close)
        self.transport = AgentCommunication(audit_logger=self.logger)

    def pending(self, fields):
        return self.transport.send_request(AgentRequest(
            "AgentA", "AgentB", "C101", fields, "Unspecified task"))

    def test_reviewer_name_only_cannot_expand_into_complaint_fields(self):
        pending = self.pending(["name", "complaint_status"])
        with patch.object(self.transport.data_agent, "handle_request") as read:
            result = self.transport.review_request(pending.metadata["request_id"], "Restrict",
                fields=["name"], purpose="Resolve customer complaint")
            read.assert_not_called()
        self.assertEqual(result.status, "restricted")
        self.assertEqual(result.data, {})
        self.assertEqual(result.metadata["review_scope"], ["name"])
        records = self.logger.get_records_by_request_id(pending.metadata["request_id"])
        self.assertEqual(records[-1].human_action, "RESTRICT")
        self.assertEqual(records[-1].decision, "RESTRICT")

    def test_review_minimizes_within_selected_fields(self):
        pending = self.pending(["name", "complaint_status"])
        result = self.transport.review_request(pending.metadata["request_id"], "Restrict",
            fields=["name", "complaint_status"], purpose="Resolve customer complaint")
        self.assertEqual(result.data, {"complaint_status": "In Progress"})
        self.assertEqual([s["decision"] for s in result.metadata["governance"]["trajectory"]],
                         ["MODIFY", "ALLOW"])
        self.assertEqual(result.metadata["effective_fields"], ["complaint_status"])

    def test_review_scope_is_reauthorized_even_if_projection_is_wrong(self):
        pending = self.pending(["name", "complaint_status"])
        with patch("app.governance.reanalysis.suggest_minimum_fields", return_value=["customer_id"]):
            with patch.object(self.transport.data_agent, "handle_request") as read:
                result = self.transport.review_request(pending.metadata["request_id"], "Restrict",
                    fields=["name", "complaint_status"], purpose="Resolve customer complaint")
                read.assert_not_called()
        self.assertEqual(result.metadata["governance"]["decision"], "BLOCK")
        self.assertFalse(result.data)

    def test_scope_survives_a_second_pending_review(self):
        self.transport = AgentCommunication(audit_logger=self.logger, tracker=ProbingTracker(threshold=10))
        pending = self.pending(["name", "complaint_status"])
        restricted = self.transport.review_request(pending.metadata["request_id"], "Restrict",
                                                   fields=["name"])
        self.assertEqual(restricted.status, "human_review")
        final = self.transport.review_request(pending.metadata["request_id"], "Approve",
                                             purpose="Resolve customer complaint")
        self.assertEqual(final.status, "restricted")
        self.assertEqual(final.metadata["review_scope"], ["name"])
        self.assertFalse(final.data)

    def test_malformed_submissions_are_audited_without_data_access(self):
        cases = [None, {}, AgentRequest("AgentA", "AgentB", "C101", [], "Resolve customer complaint"),
                 AgentRequest("AgentA", "AgentB", "C101", [None], "Resolve customer complaint"),
                 AgentRequest("AgentA", "AgentB", "C101", "private@example.com", "Resolve customer complaint"),
                 AgentRequest("AgentA", "AgentB", None, ["name"], "Resolve customer complaint")]
        with patch.object(self.transport.data_agent, "handle_request") as read:
            for request in cases:
                result = self.transport.send_request(request)
                self.assertEqual(result.status, "error")
                self.assertFalse(result.data)
                record = self.logger.get_records_by_request_id(result.metadata["request_id"])[0]
                self.assertEqual(record.decision, "BLOCK")
                self.assertIn("MALFORMED_REQUEST", str(record.findings))
            read.assert_not_called()
        self.assertEqual(len(self.logger.get_all_records()), len(cases))
        self.assertNotIn("private@example.com", str(self.logger.get_all_records()))

    def test_validation_audit_failure_still_denies_access(self):
        with patch.object(self.logger, "record_rejection", side_effect=OSError("disk full")):
            with patch.object(self.transport.data_agent, "handle_request") as read:
                result = self.transport.send_request(None)
                read.assert_not_called()
        self.assertEqual(result.status, "error")
        self.assertFalse(result.data)
        self.assertIn("audit unavailable", result.message)

    def test_invalid_review_selection_can_be_corrected(self):
        pending = self.pending(["complaint_status"])
        invalid = self.transport.review_request(pending.metadata["request_id"], "Restrict", fields=[])
        self.assertEqual(invalid.status, "error")
        valid = self.transport.review_request(pending.metadata["request_id"], "Restrict",
            fields=["complaint_status"], purpose="Resolve customer complaint")
        self.assertEqual(valid.data, {"complaint_status": "In Progress"})


if __name__ == "__main__":
    unittest.main()
