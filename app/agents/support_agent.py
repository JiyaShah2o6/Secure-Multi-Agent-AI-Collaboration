from app.agents.communication import AgentCommunication
from app.authorization.permissions import is_authorized
from app.authorization.data_minimization import check_data_minimization
from app.models.schemas import AgentRequest, AgentResponse


class SupportAgent:
    def __init__(self):
        self.name = "AgentA"
        self.communication = AgentCommunication()

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
            return AgentResponse(
                status="unauthorized",
                data={
                    "unauthorized_fields": authorization_result["unauthorized_fields"]
                },
                message="Agent A is not authorized to access the requested fields."
            )

        # Check whether requested fields are necessary
        minimization_result = check_data_minimization(
            request.purpose,
            request.requested_fields
        )

        # Reject request if it contains unnecessary fields
        if not minimization_result["valid"]:
            return AgentResponse(
                status="data_minimization_violation",
                data={
                    "unnecessary_fields": minimization_result["unnecessary_fields"]
                },
                message=minimization_result["message"]
            )

        print(f"{self.name} sending request to AgentB:")
        print(request)

        # Send request through communication layer
        response = self.communication.send_request(request)

        return response