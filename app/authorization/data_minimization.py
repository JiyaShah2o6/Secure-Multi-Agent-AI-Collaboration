# Fields required for each supported purpose

PURPOSE_FIELDS = {
    "Resolve customer complaint": {
        "customer_id",
        "complaint_id",
        "complaint_status",
        "complaint_description"
    },

    "Contact customer": {
        "customer_id",
        "name",
        "email",
        "phone"
    },

    "Process payment/refund": {
        "customer_id",
        "bank_account"
    }
}


def check_data_minimization(purpose, requested_fields):
    """
    Check whether the requested fields are necessary
    for the given purpose.
    """

    required_fields = PURPOSE_FIELDS.get(purpose)

    # Check for unknown purpose
    if required_fields is None:
        return {
            "valid": False,
            "unnecessary_fields": requested_fields,
            "message": "Unknown purpose"
        }

    unnecessary_fields = [
        field
        for field in requested_fields
        if field not in required_fields
    ]

    if unnecessary_fields:
        return {
            "valid": False,
            "unnecessary_fields": unnecessary_fields,
            "message": "Some requested fields are unnecessary for this purpose"
        }

    return {
        "valid": True,
        "unnecessary_fields": [],
        "message": "Requested fields are appropriate for the purpose"
    }