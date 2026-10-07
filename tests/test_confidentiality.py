import unittest

from app.governance.confidentiality import (
    analyze_confidentiality,
    classify_field,
)
from app.models.schemas import Request


class TestConfidentialityAnalysis(unittest.TestCase):
    def test_normal_internal_request(self) -> None:
        req = Request(
            request_id="req-001",
            sender="support_agent",
            receiver="data_agent",
            customer_id="cust-101",
            requested_fields=["customer_id", "name", "complaint_status"],
            purpose="Routine customer ticket lookup",
        )
        findings = analyze_confidentiality(req)
        self.assertEqual(len(findings), 0)

    def test_confidential_field_detected(self) -> None:
        req = Request(
            request_id="req-002",
            sender="support_agent",
            receiver="data_agent",
            customer_id="cust-102",
            requested_fields=["name", "email"],
            purpose="Send confirmation email",
        )
        findings = analyze_confidentiality(req)
        self.assertEqual(len(findings), 1)
        finding = findings[0]
        self.assertEqual(finding.analyzer, "confidentiality")
        self.assertEqual(finding.severity, "MEDIUM")
        self.assertIn("CONFIDENTIAL", finding.labels)
        self.assertIn("email", finding.labels)
        self.assertEqual(finding.suggested_action, "REDACT")

    def test_restricted_field_detected(self) -> None:
        req = Request(
            request_id="req-003",
            sender="support_agent",
            receiver="data_agent",
            customer_id="cust-103",
            requested_fields=["card_details"],
            purpose="Process refund",
        )
        findings = analyze_confidentiality(req)
        self.assertEqual(len(findings), 1)
        finding = findings[0]
        self.assertEqual(finding.analyzer, "confidentiality")
        self.assertEqual(finding.severity, "HIGH")
        self.assertIn("RESTRICTED", finding.labels)
        self.assertEqual(finding.suggested_action, "BLOCK")

    def test_multiple_sensitive_fields(self) -> None:
        req = Request(
            request_id="req-004",
            sender="support_agent",
            receiver="data_agent",
            customer_id="cust-104",
            requested_fields=[
                "name",
                "email",
                "phone",
                "bank_account_details",
                "card_details",
            ],
            purpose="Account auditing",
        )
        findings = analyze_confidentiality(req)
        self.assertEqual(len(findings), 4)

        severities = {f.severity for f in findings}
        self.assertIn("MEDIUM", severities)
        self.assertIn("HIGH", severities)

        evidence_fields = {f.evidence for f in findings}
        self.assertEqual(
            evidence_fields,
            {"email", "phone", "bank_account_details", "card_details"},
        )

    def test_unknown_field_handled_safely(self) -> None:
        req = Request(
            request_id="req-005",
            sender="support_agent",
            receiver="data_agent",
            customer_id="cust-105",
            requested_fields=["internal_token", "salary_estimate"],
            purpose="Credit check",
        )
        findings = analyze_confidentiality(req)
        self.assertEqual(len(findings), 2)
        for finding in findings:
            self.assertEqual(finding.severity, "HIGH")
            self.assertIn("UNKNOWN_FIELD", finding.labels)
            self.assertEqual(finding.suggested_action, "BLOCK")

    def test_embedded_sensitive_data_in_purpose(self) -> None:
        req = Request(
            request_id="req-006",
            sender="support_agent",
            receiver="data_agent",
            customer_id="cust-106",
            requested_fields=["name"],
            purpose="Notify customer at test.user@example.com regarding card 4111111111111111",
        )
        findings = analyze_confidentiality(req)
        labels = [lbl for f in findings for lbl in f.labels]
        self.assertIn("EMBEDDED_EMAIL", labels)
        self.assertIn("EMBEDDED_CARD", labels)

    def test_classify_field_helper(self) -> None:
        self.assertEqual(classify_field("customer_id"), "INTERNAL")
        self.assertEqual(classify_field("complaint_description"), "CONFIDENTIAL")
        self.assertEqual(classify_field("bank_account_details"), "RESTRICTED")
        self.assertEqual(classify_field("non_existent_column"), "UNKNOWN")


if __name__ == "__main__":
    unittest.main()
