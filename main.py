from app.agents.support_agent import SupportAgent


agent_a = SupportAgent()


# TEST 1 - Authorized + Necessary
print("TEST 1 - Authorized + Necessary")

response = agent_a.request_customer_data(
    customer_id="C101",
    requested_fields=["complaint_status"],
    purpose="Resolve customer complaint"
)

print("Response:")
print(response)


# TEST 2 - Unauthorized
print("\nTEST 2 - Unauthorized")

response = agent_a.request_customer_data(
    customer_id="C101",
    requested_fields=["bank_account"],
    purpose="Resolve customer complaint"
)

print("Response:")
print(response)


# TEST 3 - Authorized but Unnecessary
print("\nTEST 3 - Authorized but Unnecessary")

response = agent_a.request_customer_data(
    customer_id="C101",
    requested_fields=["name"],
    purpose="Resolve customer complaint"
)

print("Response:")
print(response)