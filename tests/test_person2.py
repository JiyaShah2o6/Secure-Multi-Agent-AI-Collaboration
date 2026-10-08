import unittest

from app.agents.data_agent import DataAgent
from app.agents.support_agent import SupportAgent
from app.agents.communication import AgentCommunication
from app.governance.audit import AuditLogger
from app.authorization.permissions import is_authorized
from app.authorization.data_minimization import check_data_minimization
from app.authorization.token_analysis import analyze_prompt


class TestPermissions(unittest.TestCase):

    def test_authorized_field(self):
        result = is_authorized(
            "AgentA",
            ["complaint_status"]
        )

        self.assertTrue(result["authorized"])
        self.assertEqual(
            result["unauthorized_fields"],
            []
        )

    def test_unauthorized_field(self):
        result = is_authorized(
            "AgentA",
            ["bank_account"]
        )

        self.assertFalse(result["authorized"])
        self.assertIn(
            "bank_account",
            result["unauthorized_fields"]
        )


class TestDataMinimization(unittest.TestCase):

    def test_necessary_field(self):
        result = check_data_minimization(
            "Resolve customer complaint",
            ["complaint_status"]
        )

        self.assertTrue(result["valid"])
        self.assertEqual(
            result["unnecessary_fields"],
            []
        )

    def test_unnecessary_field(self):
        result = check_data_minimization(
            "Resolve customer complaint",
            ["name"]
        )

        self.assertFalse(result["valid"])
        self.assertIn(
            "name",
            result["unnecessary_fields"]
        )


class TestTokenAnalysis(unittest.TestCase):

    def test_empty_prompt(self):
        result = analyze_prompt("")

        self.assertEqual(
            result["token_count"],
            0
        )

    def test_short_prompt_is_efficient(self):
        result = analyze_prompt(
            "Give complaint status for C101."
        )

        self.assertEqual(
            result["status"],
            "efficient"
        )

    def test_long_prompt_exceeds_limit(self):
        long_prompt = "customer information " * 100

        result = analyze_prompt(
            long_prompt,
            token_limit=50
        )

        self.assertEqual(
            result["status"],
            "high"
        )


class TestDataAgent(unittest.TestCase):

    def test_customer_data_retrieval(self):
        logger = AuditLogger(":memory:")
        self.addCleanup(logger.close)
        agent = SupportAgent(AgentCommunication(audit_logger=logger))
        response = agent.request_customer_data(
            "C101", ["complaint_status"], "Resolve customer complaint"
        )

        self.assertEqual(
            response.status,
            "success"
        )

        self.assertEqual(
            response.data["complaint_status"],
            "In Progress"
        )

    def test_unknown_customer(self):
        logger = AuditLogger(":memory:")
        self.addCleanup(logger.close)
        agent = SupportAgent(AgentCommunication(audit_logger=logger))
        response = agent.request_customer_data(
            "C999", ["complaint_status"], "Resolve customer complaint"
        )

        self.assertEqual(
            response.status,
            "error"
        )


class TestSupportAgent(unittest.TestCase):

    def setUp(self):
        logger = AuditLogger(":memory:")
        self.addCleanup(logger.close)
        self.agent = SupportAgent(AgentCommunication(audit_logger=logger))

    def test_authorized_request(self):
        response = self.agent.request_customer_data(
            customer_id="C101",
            requested_fields=[
                "complaint_status"
            ],
            purpose="Resolve customer complaint"
        )

        self.assertEqual(
            response.status,
            "success"
        )

        self.assertEqual(
            response.data["complaint_status"],
            "In Progress"
        )

    def test_unauthorized_request(self):
        response = self.agent.request_customer_data(
            customer_id="C101",
            requested_fields=[
                "bank_account"
            ],
            purpose="Resolve customer complaint"
        )

        self.assertEqual(
            response.status,
            "unauthorized"
        )

        self.assertIn(
            "bank_account",
            response.metadata["authorization"]["unauthorized_fields"]
        )

    def test_data_minimization_violation(self):
        response = self.agent.request_customer_data(
            customer_id="C101",
            requested_fields=[
                "name"
            ],
            purpose="Resolve customer complaint"
        )

        self.assertEqual(
            response.status,
            "success"
        )

        self.assertIn(
            "name",
            response.metadata["data_minimization"]["unnecessary_fields"]
        )

        self.assertEqual(set(response.data), {"customer_id", "complaint_id", "complaint_status"})
        self.assertEqual(
            [p["decision"] for p in response.metadata["governance"]["trajectory"]],
            ["MODIFY", "ALLOW"],
        )


if __name__ == "__main__":
    unittest.main()