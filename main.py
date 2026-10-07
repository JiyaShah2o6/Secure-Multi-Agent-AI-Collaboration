from app.agents.data_agent import DataAgent


agent_b = DataAgent()

request = {
    "customer_id": "C101",
    "requested_fields": ["complaint_status"]
}

response = agent_b.handle_request(request)

print("Agent B Response:")
print(response)