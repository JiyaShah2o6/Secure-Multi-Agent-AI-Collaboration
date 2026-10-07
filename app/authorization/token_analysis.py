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

    Returns the estimated token count and
    whether the request is within the recommended limit.
    """

    token_count = estimate_tokens(text)

    if token_count <= token_limit:
        status = "efficient"
        message = "Token usage is within the recommended limit."
    else:
        status = "high"
        message = (
            "Token usage is high. Consider removing unnecessary "
            "information from the request."
        )

    return {
        "token_count": token_count,
        "token_limit": token_limit,
        "status": status,
        "message": message
    }


if __name__ == "__main__":

    prompt = """
    Agent A requests the complaint status of customer C101.
    The customer has contacted support regarding a product issue.
    Please provide only the current complaint status.
    """

    result = analyze_prompt(prompt)

    print("Token Usage Analysis")
    print("--------------------")
    print("Estimated tokens:", result["token_count"])
    print("Recommended limit:", result["token_limit"])
    print("Status:", result["status"])
    print("Message:", result["message"])