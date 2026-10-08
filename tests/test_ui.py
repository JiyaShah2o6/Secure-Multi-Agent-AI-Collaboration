import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parents[1] / "app/ui/streamlit_app.py"


class TestStreamlitDemo(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.env = patch.dict(os.environ, {"GOVERNANCE_AUDIT_PATH": str(Path(self.directory.name) / "ui.db")})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.app = AppTest.from_file(str(APP), default_timeout=30).run()
        self.assertFalse(self.app.exception)

    def send(self, scenario):
        self.app.selectbox(key="scenario").select(scenario).run()
        self.app.button(key="send").click().run()
        self.assertFalse(self.app.exception)
        return self.app.session_state["responses"][scenario]

    def test_all_four_scenarios_in_one_browser_session(self):
        cases = [("Scenario 1 - Authorized", "ALLOW"), ("Scenario 2 - Unauthorized", "BLOCK"),
                 ("Scenario 3 - Unnecessary Data", "ALLOW"), ("Scenario 4 - Token-Inefficient Request", "ALLOW")]
        for name, decision in cases:
            with self.subTest(name=name):
                response = self.send(name)
                self.assertEqual(response.metadata["governance"]["decision"], decision)
                self.assertTrue(any(m.label == "Decision" and m.value == decision for m in self.app.metric))
        self.assertEqual(response.metadata["token_analysis"]["status"], "high")
        self.assertTrue(any("Token efficiency warning" in w.value for w in self.app.warning))
        third = self.app.session_state["responses"][cases[2][0]]
        self.assertEqual(third.metadata["requested_fields"], ["*"])
        self.assertEqual([s["risk_level"] for s in third.metadata["governance"]["trajectory"]], ["MEDIUM", "LOW"])
        self.assertEqual([s["decision"] for s in third.metadata["governance"]["trajectory"]], ["MODIFY", "ALLOW"])
        self.assertEqual(set(third.data), {"customer_id", "complaint_id", "complaint_status"})

    def test_repeated_requests_restrict_until_new_demo_session(self):
        name = "Scenario 1 - Authorized"
        self.send(name); self.send(name)
        response = self.send(name)
        self.assertEqual(response.status, "restricted")
        self.app.sidebar.button[0].click().run()
        self.assertEqual(self.send(name).status, "success")

    def test_human_approval(self):
        self.app.selectbox(key="purpose_option").select("Other / human review").run()
        self.app.button(key="send").click().run()
        self.assertEqual(self.app.session_state["responses"]["Custom Request"].status, "human_review")
        self.app.button(key="review_submit").click().run()
        self.assertFalse(self.app.exception)
        response = self.app.session_state["responses"]["Custom Request"]
        self.assertEqual(response.status, "success")
        self.assertEqual(response.data, {"complaint_status": "In Progress"})

    def test_human_rejection(self):
        self.app.selectbox(key="purpose_option").select("Other / human review").run()
        self.app.button(key="send").click().run()
        self.app.selectbox(key="review_action").select("Reject").run()
        self.app.button(key="review_submit").click().run()
        self.assertFalse(self.app.exception)
        response = self.app.session_state["responses"]["Custom Request"]
        self.assertEqual(response.status, "blocked")
        self.assertFalse(response.data)

    def test_empty_submission_is_rejected_and_audited(self):
        self.app.multiselect(key="custom_fields").set_value([]).run()
        self.app.button(key="send").click().run()
        self.assertFalse(self.app.exception)
        response = self.app.session_state["responses"]["Custom Request"]
        self.assertEqual(response.status, "error")
        agent = self.app.session_state["agents"]["Custom Request"]
        records = agent.communication.audit_logger.get_records_by_request_id(response.metadata["request_id"])
        self.assertEqual(records[0].decision, "BLOCK")

    def test_reviewer_restriction_does_not_expand_in_ui(self):
        self.app.multiselect(key="custom_fields").set_value(["name", "complaint_status"]).run()
        self.app.selectbox(key="purpose_option").select("Other / human review").run()
        self.app.button(key="send").click().run()
        self.app.selectbox(key="review_action").select("Restrict").run()
        self.app.multiselect(key="review_fields").set_value([]).run()
        self.app.button(key="review_submit").click().run()
        self.assertEqual(self.app.session_state["responses"]["Custom Request"].status, "human_review")
        self.assertTrue(self.app.error)
        self.app.multiselect(key="review_fields").set_value(["name"]).run()
        self.app.button(key="review_submit").click().run()
        self.assertFalse(self.app.exception)
        response = self.app.session_state["responses"]["Custom Request"]
        self.assertEqual(response.status, "restricted")
        self.assertEqual(response.metadata["review_scope"], ["name"])
        self.assertFalse(response.data)


if __name__ == "__main__":
    unittest.main()
