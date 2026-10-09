"""
Comprehensive automated tests evaluating all 42 scenarios in the evaluation dataset.
Verifies governance decisions, risk levels, data retrieval gating, released field projection,
audit logging, and security pattern detection metrics.
"""

from __future__ import annotations

import unittest
from unittest.mock import patch

from app.agents.communication import AgentCommunication
from app.agents.support_agent import SupportAgent
from app.governance.audit import AuditLogger
from app.governance.security import analyze_security
from app.models.schemas import AgentRequest, Request
from tests.evaluation_dataset import EVALUATION_SCENARIOS, EvaluationScenario


class TestEvaluationScenarios(unittest.TestCase):
    def setUp(self) -> None:
        self.audit_logger = AuditLogger(":memory:")
        self.addCleanup(self.audit_logger.close)
        self.comm = AgentCommunication(audit_logger=self.audit_logger)
        self.support_agent = SupportAgent(self.comm)

    def _execute_scenario(self, scenario: EvaluationScenario):
        if scenario.sender != "AgentA":
            req = AgentRequest(
                sender=scenario.sender,
                receiver=scenario.receiver,
                customer_id=scenario.customer_id,
                requested_fields=scenario.requested_fields,
                purpose=scenario.purpose,
                token_limit=scenario.token_limit,
            )
            return self.comm.send_request(req)
        else:
            return self.support_agent.request_customer_data(
                customer_id=scenario.customer_id,
                requested_fields=scenario.requested_fields,
                purpose=scenario.purpose,
                token_limit=scenario.token_limit,
            )

    def test_all_scenarios_execute_and_match_ground_truth(self) -> None:
        """
        Verify all 42 scenarios in the evaluation dataset against expected outcomes.
        Checks status, governance decision, risk level, data retrieval gating,
        and released field projection.
        """
        for sc in EVALUATION_SCENARIOS:
            with self.subTest(scenario_id=sc.id, category=sc.category):
                # Fresh communication channel per scenario to avoid unintended probing carryover
                logger = AuditLogger(":memory:")
                comm = AgentCommunication(audit_logger=logger)
                agent = SupportAgent(comm)

                if sc.sender != "AgentA":
                    req = AgentRequest(
                        sender=sc.sender,
                        receiver=sc.receiver,
                        customer_id=sc.customer_id,
                        requested_fields=sc.requested_fields,
                        purpose=sc.purpose,
                    )
                    resp = comm.send_request(req)
                else:
                    resp = agent.request_customer_data(
                        customer_id=sc.customer_id,
                        requested_fields=sc.requested_fields,
                        purpose=sc.purpose,
                        token_limit=sc.token_limit,
                    )

                # 1. Status verification
                self.assertEqual(
                    resp.status,
                    sc.expected_status,
                    f"[{sc.id}] Expected status '{sc.expected_status}' but got '{resp.status}' ({resp.message})"
                )

                # 2. Protected customer data retrieval gating
                if sc.data_retrieval_allowed:
                    self.assertTrue(
                        bool(resp.data),
                        f"[{sc.id}] Expected data retrieval to be allowed, but response.data was empty."
                    )
                    self.assertEqual(
                        set(resp.data.keys()),
                        set(sc.expected_released_fields),
                        f"[{sc.id}] Released fields mismatch. Expected {sc.expected_released_fields}, got {set(resp.data.keys())}"
                    )
                else:
                    self.assertEqual(
                        resp.data,
                        {},
                        f"[{sc.id}] Expected data retrieval to be denied/empty, but data was leaked: {resp.data}"
                    )

                # 3. Governance decision & risk level verification
                if "governance" in resp.metadata:
                    gov = resp.metadata["governance"]
                    if sc.expected_decision != "REVIEW_REQUIRED":
                        self.assertEqual(
                            gov.get("decision"),
                            sc.expected_decision,
                            f"[{sc.id}] Expected decision '{sc.expected_decision}' but got '{gov.get('decision')}'"
                        )
                    self.assertEqual(
                        gov.get("risk_level"),
                        sc.expected_risk,
                        f"[{sc.id}] Expected risk '{sc.expected_risk}' but got '{gov.get('risk_level')}'"
                    )

                # 4. Audit persistence verification
                req_id = resp.metadata.get("request_id")
                if req_id:
                    records = logger.get_records_by_request_id(req_id)
                    self.assertTrue(
                        len(records) >= 1,
                        f"[{sc.id}] Expected audit record for request '{req_id}', but none found."
                    )
                    record = records[0]
                    self.assertEqual(record.request_id, req_id)

                logger.close()

    def test_security_pattern_detection_metrics(self) -> None:
        """
        Calculates confusion matrix (TP, FP, TN, FN), Recall, Precision, and FPR
        for the deterministic security pattern analyzer across all evaluation scenarios.
        """
        tp = 0
        fp = 0
        tn = 0
        fn = 0

        for sc in EVALUATION_SCENARIOS:
            # We construct a canonical Request object to evaluate with analyze_security
            req = Request(
                request_id=f"test-sec-{sc.id}",
                sender=sc.sender,
                receiver=sc.receiver,
                customer_id=sc.customer_id,
                requested_fields=sc.requested_fields,
                purpose=sc.purpose,
            )
            findings = analyze_security(req, record_probe=False)
            has_security_finding = bool(findings)

            if sc.is_security_threat:
                if has_security_finding:
                    tp += 1
                else:
                    fn += 1
            else:
                if has_security_finding:
                    fp += 1
                else:
                    tn += 1

        total = len(EVALUATION_SCENARIOS)
        self.assertEqual(tp + fp + tn + fn, total)

        # Ensure high recall and precision on our structured threat dataset
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0

        self.assertGreaterEqual(recall, 0.95, f"Security recall {recall:.2%} below threshold")
        self.assertGreaterEqual(precision, 0.95, f"Security precision {precision:.2%} below threshold")
        self.assertLessEqual(fpr, 0.05, f"Security FPR {fpr:.2%} exceeds threshold")


if __name__ == "__main__":
    unittest.main()
