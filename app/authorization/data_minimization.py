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


from app.authorization.permissions import CUSTOMER_SCHEMA_FIELDS


def suggest_minimum_fields(purpose, allowed_fields, field_scope=None):
    """
    Purpose-specific minimal projection satisfying all three conditions:
    1. Fields are relevant to the purpose.
    2. Fields are permitted for the requester.
    3. Fields exist in the supported customer data schema.
    """
    required = PURPOSE_FIELDS.get(purpose, set())
    order = ["customer_id", "name", "complaint_id", "complaint_status",
             "email", "phone", "complaint_description", "bank_account"]
    return [name for name in order
            if name in required
            and name in allowed_fields
            and name in CUSTOMER_SCHEMA_FIELDS
            and (field_scope is None or name in field_scope)]
