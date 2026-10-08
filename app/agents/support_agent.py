from app.agents.communication import AgentCommunication
from app.authorization.token_analysis import analyze_prompt
from app.models.schemas import AgentRequest


class SupportAgent:
    def __init__(self, communication=None):
        self.name = "AgentA"
        self.communication = communication if communication is not None else AgentCommunication()

    def request_customer_data(self, customer_id, requested_fields, purpose, token_limit=100):
        request = AgentRequest(self.name, "AgentB", customer_id, requested_fields, purpose)
        request_text = (
            f"Customer ID: {customer_id}\nRequested fields: {requested_fields}\nPurpose: {purpose}"
        )
        token_analysis = analyze_prompt(request_text, token_limit=token_limit)
        response = self.communication.send_request(request)
        response.metadata["token_analysis"] = token_analysis
        return response
