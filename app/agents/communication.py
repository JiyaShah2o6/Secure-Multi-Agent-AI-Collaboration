from app.agents.data_agent import DataAgent
from app.governance import govern_request
from app.models.schemas import Request, GovernanceResult


class AgentCommunication:
    def __init__(self, auth_provider):
        self.data_agent = DataAgent()
        self.auth_provider = auth_provider

    def send_request(self, request):
        """
        Send Agent A's request through the Governance Layer
        before allowing it to reach Agent B.
        """

        governance_request = Request(
            request_id="REQ001",
            sender="support_agent",
            receiver="data_agent",
            customer_id=request.customer_id,
            requested_fields=request.requested_fields,
            purpose=request.purpose
        )

        result: GovernanceResult = govern_request(
            request=governance_request,
            auth_provider=self.auth_provider
        )

        # ALLOW → send request to Agent B
        if result.decision == "ALLOW":
            final_request = result.modified_request or governance_request

            request_data = {
                "customer_id": final_request.customer_id,
                "requested_fields": final_request.requested_fields
            }

            return self.data_agent.handle_request(request_data)

        # BLOCK → stop request
        if result.decision == "BLOCK":
            return {
                "status": "blocked",
                "data": {},
                "message": result.reason
            }

        # HUMAN_REVIEW → stop and wait for human
        if result.decision == "HUMAN_REVIEW":
            return {
                "status": "human_review",
                "data": {},
                "message": result.reason
            }

        # RESTRICT → do not forward
        if result.decision == "RESTRICT":
            return {
                "status": "restricted",
                "data": {},
                "message": result.reason
            }

        return {
            "status": "error",
            "data": {},
            "message": f"Unknown governance decision: {result.decision}"
        }