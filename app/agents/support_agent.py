from app.agents.data_agent import DataAgent


class SupportAgent:
    def __init__(self):
        self.name = "AgentA"
        self.data_agent = DataAgent()

    def request_customer_data(self, customer_id, requested_fields, purpose):
        request = {
            "sender": self.name,
            "receiver": "AgentB",
            "customer_id": customer_id,
            "requested_fields": requested_fields,
            "purpose": purpose
        }

        print(f"{self.name} sending request to AgentB:")
        print(request)

        response = self.data_agent.handle_request(request)

        return response