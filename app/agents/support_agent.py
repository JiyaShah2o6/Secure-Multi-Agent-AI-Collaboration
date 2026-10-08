from app.agents.communication import AgentCommunication
from app.authorization.permissions import is_authorized
from app.authorization.data_minimization import check_data_minimization
from app.authorization.token_analysis import analyze_prompt
from app.models.schemas import AgentRequest, AgentResponse


class SupportAgent:
    def __init__(self):
        self.name = "AgentA"
        self.communication = AgentCommunication()

    def request_customer_data(
        self,
        customer_id,
        requested_fields,
        purpose,
        token_limit=100
    ):

        request = AgentRequest(
            sender=self.name,
            receiver="AgentB",
            customer_id=customer_id,
            requested_fields=requested_fields,
            purpose=purpose
        )

        request_text = (
            f"Customer ID: {request.customer_id}\n"
            f"Requested fields: {', '.join(request.requested_fields)}\n"
            f"Purpose: {request.purpose}"
        )

        token_analysis = analyze_prompt(
            request_text,
            token_limit=token_limit
        )

        print("\nToken Usage Analysis")
        print("--------------------")
        print("Estimated tokens:", token_analysis["token_count"])
        print("Recommended limit:", token_analysis["token_limit"])
        print("Status:", token_analysis["status"])
        print("Message:", token_analysis["message"])

        authorization_result = is_authorized(
            request.sender,
            request.requested_fields
        )

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

        minimization_result = check_data_minimization(
            request.purpose,
            request.requested_fields
        )

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

        response = self.communication.send_request(request)

        response.data["token_analysis"] = token_analysis

        return response