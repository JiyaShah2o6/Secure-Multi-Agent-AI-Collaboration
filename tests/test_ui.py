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


    def test_navigation_all_seven_destinations(self):
        destinations = [
            "Overview",
            "Request Console",
            "Human Review",
            "Audit Trail",
            "Confidentiality",
            "Security Analysis",
            "Token Monitor",
        ]
        for dest in destinations:
            with self.subTest(destination=dest):
                self.app.radio(key="top_nav").set_value(dest).run()
                self.assertFalse(self.app.exception)
                self.assertEqual(self.app.session_state["page"], dest)

    def test_confidentiality_page_inspection(self):
        self.app.radio(key="top_nav").set_value("Confidentiality").run()
        self.assertFalse(self.app.exception)
        self.app.selectbox(key="conf_field_select").select("bank_account").run()
        self.assertFalse(self.app.exception)

    def test_security_analysis_page_tester(self):
        self.app.radio(key="top_nav").set_value("Security Analysis").run()
        self.assertFalse(self.app.exception)
        # Click Run Security Analyzer button
        self.app.button(key="run_sec_test").click().run()
        self.assertFalse(self.app.exception)

    def test_token_monitor_page_simulation(self):
        self.app.radio(key="top_nav").set_value("Token Monitor").run()
        self.assertFalse(self.app.exception)
        self.assertTrue(any("Estimated Tokens" in m.label for m in self.app.metric))
        self.assertTrue(any(m.label == "Efficiency" for m in self.app.metric))

    def test_human_review_queue_display(self):
        # 1. Trigger human review from Request Console
        self.app.radio(key="top_nav").set_value("Request Console").run()
        self.app.selectbox(key="purpose_option").select("Other / human review").run()
        self.app.button(key="send").click().run()
        self.assertEqual(self.app.session_state["responses"]["Custom Request"].status, "human_review")

        # 2. Navigate to Human Review page
        self.app.radio(key="top_nav").set_value("Human Review").run()
        self.assertFalse(self.app.exception)
        # Verify page renders pending queue
        self.assertTrue(any("Total requests pending review" in str(getattr(t, "value", "")) for t in self.app.markdown))

    def test_audit_trail_page_filtering(self):
        # Run a request to ensure audit records exist
        self.send("Scenario 1 - Authorized")
        self.app.radio(key="top_nav").set_value("Audit Trail").run()
        self.assertFalse(self.app.exception)
        self.assertTrue(len(self.app.dataframe) > 0)

    def test_theme_switcher_modes_and_persistence(self):
        # Initial theme defaults to Light
        self.assertEqual(self.app.session_state["theme_mode"], "Light")
        initial_responses_count = len(self.app.session_state["responses"])

        # Click theme toggle button to switch to Dark
        self.app.button(key="theme_toggle").click().run()
        self.assertFalse(self.app.exception)
        self.assertEqual(self.app.session_state["theme_mode"], "Dark")

        # Verify switching theme did NOT execute or submit any request
        self.assertEqual(len(self.app.session_state["responses"]), initial_responses_count)

        # Navigate across pages and verify theme persists
        self.app.radio(key="top_nav").set_value("Audit Trail").run()
        self.assertFalse(self.app.exception)
        self.assertEqual(self.app.session_state["theme_mode"], "Dark")

        self.app.radio(key="top_nav").set_value("Human Review").run()
        self.assertFalse(self.app.exception)
        self.assertEqual(self.app.session_state["theme_mode"], "Dark")

        # Click theme toggle button again to switch back to Light
        self.app.button(key="theme_toggle").click().run()
        self.assertFalse(self.app.exception)
        self.assertEqual(self.app.session_state["theme_mode"], "Light")

    def test_empty_human_review_queue_display(self):
        # When no reviews are pending, navigate directly to Human Review
        self.app.radio(key="top_nav").set_value("Human Review").run()
        self.assertFalse(self.app.exception)
        self.assertTrue(
            any("No requests are awaiting review" in str(getattr(t, "value", ""))
                for t in self.app.markdown)
        )

    def test_sidebar_cleanup_and_branding(self):
        # Sidebar should contain single descriptive subtitle and no persistent architecture/probing text
        sidebar_captions = [str(getattr(c, "value", "")) for c in self.app.sidebar.caption]
        self.assertTrue(any("Policy enforcement for secure agent-to-agent data exchange" in c for c in sidebar_captions))
        self.assertFalse(any("System architecture:" in c for c in sidebar_captions))
        self.assertFalse(any("Three requests within 60 seconds" in c for c in sidebar_captions))

    def test_confidentiality_matrix_accurate_authorization_labels(self):
        self.app.radio(key="top_nav").set_value("Confidentiality").run()
        self.assertFalse(self.app.exception)
        # Check that table rows for bank_account and card_details are Denied, while customer_id is Allowed
        table_df = self.app.table[0].value
        row_dict = dict(zip(table_df["Field"], table_df["Agent A Access"]))
        self.assertEqual(row_dict["bank_account"], "Denied")
        self.assertEqual(row_dict["card_details"], "Denied")
        self.assertEqual(row_dict["customer_id"], "Allowed")

    def test_overview_page_content_and_navigation(self):
        self.app.radio(key="top_nav").set_value("Overview").run()
        self.assertFalse(self.app.exception)
        # Check summary metric cards exist
        self.assertTrue(any("Total Requests" in getattr(m, "label", "") for m in self.app.metric))
        self.assertTrue(any("Pending Reviews" in getattr(m, "label", "") for m in self.app.metric))
        # Navigate using top navigation bar
        self.app.radio(key="top_nav").set_value("Request Console").run()
        self.assertFalse(self.app.exception)
        self.assertEqual(self.app.session_state["page"], "Request Console")

    def test_theme_tokens_unit_checks(self):
        from app.ui.theme import get_theme_tokens, build_theme_stylesheet
        light = get_theme_tokens("Light")
        dark = get_theme_tokens("Dark")
        self.assertEqual(light.name, "Light")
        self.assertEqual(dark.name, "Dark")
        self.assertNotEqual(light.bg_app, dark.bg_app)
        self.assertNotEqual(light.text_primary, dark.text_primary)

        # Verify both generate valid CSS strings with non-empty length
        css_light = build_theme_stylesheet("Light")
        css_dark = build_theme_stylesheet("Dark")
        self.assertIn("THEME: LIGHT", css_light)
        self.assertIn("THEME: DARK", css_dark)


if __name__ == "__main__":
    unittest.main()
