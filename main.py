"""Run the four independent, deterministic demonstration scenarios."""
import json
from pathlib import Path

from app.agents.communication import AgentCommunication
from app.agents.support_agent import SupportAgent
from app.governance.audit import AuditLogger


def run_demo():
    root = Path(__file__).resolve().parent
    scenarios = json.loads((root / "app/data/scenarios.json").read_text(encoding="utf-8"))
    audit_path = root / ".runtime" / "demo_audit.db"
    audit_path.parent.mkdir(exist_ok=True)
    logger = AuditLogger(str(audit_path))
    for scenario in scenarios:
        # Independent demo cases are not one probing session.
        agent = SupportAgent(AgentCommunication(audit_logger=logger))
        response = agent.request_customer_data(
            "C101", scenario["requested_fields"], scenario["purpose"], scenario["token_limit"],
        )
        result = response.metadata["governance"]
        assert result["decision"] == scenario["expected_decision"]
        assert result["risk_level"] == scenario["expected_risk"]
        if "expected_trajectory" in scenario:
            assert [p["decision"] for p in result["trajectory"]] == scenario["expected_trajectory"]
        if "expected_token_status" in scenario:
            assert response.metadata["token_analysis"]["status"] == scenario["expected_token_status"]
        print(scenario["name"])
        print("  Flow:", " -> ".join(p["decision"] for p in result["trajectory"]))
        print("  Risk:", result["risk_level"], "| Token efficiency:", response.metadata["token_analysis"]["status"])
        print("  Data:", response.data)
    print("All four demo scenarios passed.")


if __name__ == "__main__":
    run_demo()
