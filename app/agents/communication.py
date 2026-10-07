from app.agents.data_agent import DataAgent


class AgentCommunication:
    def __init__(self):
        self.data_agent = DataAgent()

    def send_request(self, request):
        """
        Send a request from Agent A to Agent B.

        Governance integration will be added later.
        """

        request_data = {
            "customer_id": request.customer_id,
            "requested_fields": request.requested_fields
        }

        response = self.data_agent.handle_request(request_data)

        return response