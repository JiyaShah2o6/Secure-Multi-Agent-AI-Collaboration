from app.data.customers import customers
from app.models.schemas import AgentResponse


class DataAgent:
    def __init__(self, approval_resolver=None):
        self.name = "AgentB"
        self._approval_resolver = approval_resolver

    def handle_request(self, approval_ticket):
        """Read only a one-use request approved by the in-process Governance transport."""
        request = self._approval_resolver(approval_ticket) if self._approval_resolver else None
        if request is None:
            return AgentResponse("blocked", {}, "A Governance approval is required.")
        if request.customer_id not in customers:
            return AgentResponse("error", {}, "Customer not found")
        customer = customers[request.customer_id]
        response = {}
        for field in request.requested_fields:
            if field == "customer_id":
                response[field] = request.customer_id
            elif field in customer:
                response[field] = customer[field]
            else:
                return AgentResponse("error", {}, "Approved field is unavailable in the customer schema.")
        return AgentResponse("success", response)
