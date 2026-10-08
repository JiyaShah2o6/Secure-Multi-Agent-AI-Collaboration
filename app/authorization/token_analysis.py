# Token usage and prompt efficiency analysis


def estimate_tokens(text):
    """
    Estimate the number of tokens in a text.

    This is a simple approximation for our prototype.
    """

    if not text:
        return 0

    words = text.split()

    # Simple approximation:
    # 1 token ≈ 0.75 words
    estimated_tokens = int(len(words) / 0.75)

    return max(1, estimated_tokens)


def analyze_prompt(text, token_limit=100):
    """
    Analyze token usage of an agent request.

    Returns the estimated token count,
    efficiency status, and optimization suggestion.
    """

    token_count = estimate_tokens(text)

    if token_count == 0:
        return {
            "token_count": 0,
            "token_limit": token_limit,
            "status": "empty",
            "message": "No request content was provided.",
            "suggestion": "Provide only the information required for the task."
        }

    if token_count <= token_limit:
        return {
            "token_count": token_count,
            "token_limit": token_limit,
            "status": "efficient",
            "message": "Token usage is within the recommended limit.",
            "suggestion": "No optimization is required."
        }

    return {
        "token_count": token_count,
        "token_limit": token_limit,
        "status": "high",
        "message": "Token usage is higher than the recommended limit.",
        "suggestion": (
            "Reduce unnecessary information and request only "
            "the fields required for the task."
        )
    }


if __name__ == "__main__":

    prompt = """
    Agent A requests customer information from Agent B.
    Customer C101 has contacted the support team regarding
    a product issue and wants an update about the complaint.
    Please provide the complaint status, complaint ID,
    customer name, email address, phone number, address,
    complaint description, bank account information,
    card details, previous complaint information,
    customer history, transaction information,
    internal notes, support history, account information,
    and any other available information about the customer.
    """

    result = analyze_prompt(
        prompt,
        token_limit=50
    )

    print("Token Usage Analysis")
    print("--------------------")
    print("Estimated tokens:", result["token_count"])
    print("Recommended limit:", result["token_limit"])
    print("Status:", result["status"])
    print("Message:", result["message"])
    print("Suggestion:", result["suggestion"])