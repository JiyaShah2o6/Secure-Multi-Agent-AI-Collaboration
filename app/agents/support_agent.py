from app.agents.data_agent import DataAgent
from app.authorization.permissions import is_authorized


class SupportAgent:
    def __init__(self):
        self.name = "AgentA"
        self.data_agent = DataAgent()

    def request_customer_data(self, customer_id, requested_fields, purpose):

        # Check whether Agent A is authorized
        authorization_result = is_authorized(
            self.name,
            requested_fields
        )

        # Stop the request if Agent A is not authorized
        if not authorization_result["authorized"]:
            return {
                "status": "unauthorized",
                "message": "Agent A is not authorized to access the requested fields.",
                "unauthorized_fields": authorization_result["unauthorized_fields"]
            }

        # Create the request
        request = {
            "sender": self.name,
            "receiver": "AgentB",
            "customer_id": customer_id,
            "requested_fields": requested_fields,
            "purpose": purpose
        }

        print(f"{self.name} sending request to AgentB:")
        print(request)

        # Send request to Agent B
        response = self.data_agent.handle_request(request)

        return response