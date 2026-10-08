from app.data.customers import customers
from app.models.schemas import AgentResponse


class DataAgent:
    def __init__(self):
        self.name = "AgentB"

    def handle_request(self, request):
        customer_id = request["customer_id"]
        requested_fields = request["requested_fields"]

        # Check if customer exists
        if customer_id not in customers:
            return AgentResponse(
                status="error",
                data={},
                message="Customer not found"
            )

        customer = customers[customer_id]

        response = {}

        # Return only requested fields
        for field in requested_fields:
            if field in customer:
                response[field] = customer[field]

        return AgentResponse(
            status="success",
            data=response
        )