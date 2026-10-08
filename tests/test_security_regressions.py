import json
import unittest
from dataclasses import asdict
from unittest.mock import patch

from app.agents.communication import AgentCommunication
from app.governance.audit import AuditLogger
from app.models.schemas import AgentRequest, AgentResponse


class TestBoundaryRegressions(unittest.TestCase):
    def setUp(self):
        self.logger = AuditLogger(":memory:")
        self.addCleanup(self.logger.close)
        self.transport = AgentCommunication(audit_logger=self.logger)

    def request(self, fields=None):
        return AgentRequest("AgentA", "AgentB", "C101", fields or ["complaint_status"],
                            "Resolve customer complaint")

    def test_all_non_success_payloads_and_messages_are_withheld(self):
        for status in ("error", "blocked", "unauthorized", "restricted", "unexpected"):
            with self.subTest(status=status):
                transport = AgentCommunication(audit_logger=self.logger)
                fake = AgentResponse(status, {"bank_account": "SYNTHETIC_SECRET"},
                                     "SYNTHETIC_SECRET", {"debug": "SYNTHETIC_SECRET"})
                with patch.object(transport.data_agent, "handle_request", return_value=fake):
                    response = transport.send_request(self.request())
                self.assertEqual(response.status, "error")
                self.assertEqual(response.data, {})
                self.assertNotIn("SYNTHETIC_SECRET", str(asdict(response)))
                record = self.logger.get_records_by_request_id(response.metadata["request_id"])[0]
                self.assertEqual(record.details["execution"]["returned_fields"], [])

    def test_malformed_downstream_response_is_safe(self):
        for fake in (None, {}, AgentResponse("success", None)):
            with self.subTest(fake=fake):
                transport = AgentCommunication(audit_logger=self.logger)
                with patch.object(transport.data_agent, "handle_request", return_value=fake):
                    response = transport.send_request(self.request())
                self.assertEqual(response.status, "error")
                self.assertFalse(response.data)

    def test_unknown_field_is_redacted_everywhere_in_persisted_record(self):
        marker = "private@example.com\nFAKE_LOG_ENTRY"
        response = self.transport.send_request(self.request([marker]))
        self.assertEqual(response.metadata["governance"]["decision"], "BLOCK")
        record = self.logger.get_records_by_request_id(response.metadata["request_id"])[0]
        serialized = json.dumps(asdict(record))
        self.assertNotIn("private@example.com", serialized)
        self.assertNotIn("FAKE_LOG_ENTRY", serialized)
        self.assertIn("UNKNOWN_FIELD", serialized)
        self.assertEqual(record.details["requested_fields"], ["[unknown field]"])

    def test_rejection_audit_accepts_malformed_values_without_serializing_them(self):
        marker = "SYNTHETIC_SECRET"
        record = self.logger.record_rejection("rejected", sender=marker, receiver=[marker],
            customer_id=marker, requested_fields=[{marker: marker}, marker], purpose={marker: marker})
        self.assertEqual(record.decision, "BLOCK")
        self.assertFalse(record.details["authorization"])
        self.assertNotIn(marker, json.dumps(asdict(record)))
        self.assertIn("MALFORMED_REQUEST", str(record.findings))


if __name__ == "__main__":
    unittest.main()
