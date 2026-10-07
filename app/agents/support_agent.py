from app.agents.communication import AgentCommunication
from app.authorization.permissions import is_authorized
from app.authorization.data_minimization import check_data_minimization
from app.authorization.token_analysis import analyze_prompt
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

        # Create a text representation of the request
        request_text = (
            f"Customer ID: {request.customer_id}\n"
            f"Requested fields: {', '.join(request.requested_fields)}\n"
            f"Purpose: {request.purpose}"
        )

        # Analyze token usage
        token_analysis = analyze_prompt(request_text)

        print("\nToken Usage Analysis")
        print("--------------------")
        print("Estimated tokens:", token_analysis["token_count"])
        print("Recommended limit:", token_analysis["token_limit"])
        print("Status:", token_analysis["status"])
        print("Message:", token_analysis["message"])

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
                    "unauthorized_fields": authorization_result[
                        "unauthorized_fields"
                    ],
                    "token_analysis": token_analysis
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
                    "unnecessary_fields": minimization_result[
                        "unnecessary_fields"
                    ],
                    "token_analysis": token_analysis
                },
                message=minimization_result["message"]
            )

        print(f"\n{self.name} sending request to AgentB:")
        print(request)

        # Send request through communication layer
        response = self.communication.send_request(request)

        # Add token analysis to the response
        response.data["token_analysis"] = token_analysis

        return response