from app.agents.support_agent import SupportAgent


agent_a = SupportAgent()


# Test 1: Authorized request
print("TEST 1 - Authorized Request")

response = agent_a.request_customer_data(
    customer_id="C101",
    requested_fields=["complaint_status"],
    purpose="Resolve customer complaint"
)

print("Response:")
print(response)


# Test 2: Unauthorized request
print("\nTEST 2 - Unauthorized Request")

response = agent_a.request_customer_data(
    customer_id="C101",
    requested_fields=["bank_account"],
    purpose="Resolve customer complaint"
)

print("Response:")
print(response)