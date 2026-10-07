from app.agents.data_agent import DataAgent
from app.authorization.permissions import is_authorized
from app.models.schemas import AgentRequest
from app.authorization.data_minimization import check_data_minimization

class SupportAgent:
    def __init__(self):
        self.name = "AgentA"
        self.data_agent = DataAgent()

    def request_customer_data(self, customer_id, requested_fields, purpose):

        # Create a standardized request
        request = AgentRequest(
            sender=self.name,
            receiver="AgentB",
            customer_id=customer_id,
            requested_fields=requested_fields,
            purpose=purpose
        )

        # Check authorization
        authorization_result = is_authorized(
            request.sender,
            request.requested_fields
        )

        # Reject unauthorized request
        if not authorization_result["authorized"]:
            return {
                "status": "unauthorized",
                "message": "Agent A is not authorized to access the requested fields.",
                "unauthorized_fields": authorization_result["unauthorized_fields"]
            }

            # Check whether requested fields are necessary for the purpose
        minimization_result = check_data_minimization(
            request.purpose,
            request.requested_fields
        )

        # Reject request if it contains unnecessary fields
        if not minimization_result["valid"]:
            return {
                "status": "data_minimization_violation",
                "message": minimization_result["message"],
                "unnecessary_fields": minimization_result["unnecessary_fields"]
            }

        print(f"{self.name} sending request to AgentB:")
        print(request)

        # Convert request to dictionary for Agent B
        request_data = {
            "customer_id": request.customer_id,
            "requested_fields": request.requested_fields
        }

        # Send request to Agent B
        response = self.data_agent.handle_request(request_data)

        return response