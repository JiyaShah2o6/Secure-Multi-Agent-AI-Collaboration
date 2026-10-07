import sys
from pathlib import Path

import streamlit as st


# Add the project root to Python's import path
PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from app.agents.support_agent import SupportAgent
from app.data.customers import customers


# Page configuration
st.set_page_config(
    page_title="Secure Multi-Agent AI Collaboration",
    page_icon="🔐",
    layout="wide"
)


# Initialize Agent A
agent = SupportAgent()


# Page title
st.title("🔐 Secure Multi-Agent AI Collaboration")
st.caption("Agent-to-Agent Data Request and Security Prototype")


# Sidebar
st.sidebar.header("Request Configuration")


customer_id = st.sidebar.selectbox(
    "Select Customer",
    list(customers.keys())
)


purpose = st.sidebar.selectbox(
    "Purpose",
    [
        "Resolve customer complaint",
        "Contact customer",
        "Process payment/refund"
    ]
)


# Available customer fields
available_fields = [
    "customer_id",
    "name",
    "email",
    "phone",
    "complaint_id",
    "complaint_status",
    "complaint_description",
    "address",
    "bank_account",
    "card_details"
]


requested_fields = st.sidebar.multiselect(
    "Requested Fields",
    available_fields,
    default=["complaint_status"]
)


# Main section
st.subheader("Agent A → Agent B Request")

st.write(
    "Agent A requests customer information from Agent B. "
    "The request is checked for authorization, data minimization, "
    "and token usage before being processed."
)


if st.button("Send Request", type="primary"):

    if not requested_fields:
        st.warning("Please select at least one field.")

    else:

        response = agent.request_customer_data(
            customer_id=customer_id,
            requested_fields=requested_fields,
            purpose=purpose
        )

        st.divider()

        # Request details
        st.subheader("Request Details")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.write("**Customer ID**")
            st.write(customer_id)

        with col2:
            st.write("**Purpose**")
            st.write(purpose)

        with col3:
            st.write("**Requested Fields**")
            st.write(", ".join(requested_fields))


        # Request result
        st.subheader("Request Result")

        if response.status == "success":
            st.success("Request Allowed")

        elif response.status == "unauthorized":
            st.error("Request Unauthorized")

        elif response.status == "data_minimization_violation":
            st.warning("Data Minimization Violation")

        else:
            st.info(response.status)


        if response.message:
            st.write(response.message)


        # Token analysis
        token_analysis = response.data.get("token_analysis")

        if token_analysis:

            st.subheader("Token Usage Analysis")

            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric(
                    "Estimated Tokens",
                    token_analysis["token_count"]
                )

            with col2:
                st.metric(
                    "Recommended Limit",
                    token_analysis["token_limit"]
                )

            with col3:
                st.metric(
                    "Status",
                    token_analysis["status"].title()
                )

            st.caption(token_analysis["message"])


        # Agent B response
        if response.status == "success":

            st.subheader("Agent B Response")

            response_data = {
                key: value
                for key, value in response.data.items()
                if key != "token_analysis"
            }

            if response_data:
                st.json(response_data)

            else:
                st.info("No data returned.")


        # Unauthorized fields
        if response.status == "unauthorized":

            unauthorized_fields = response.data.get(
                "unauthorized_fields",
                []
            )

            if unauthorized_fields:

                st.write("**Unauthorized Fields:**")

                for field in unauthorized_fields:
                    st.error(field)


        # Unnecessary fields
        if response.status == "data_minimization_violation":

            unnecessary_fields = response.data.get(
                "unnecessary_fields",
                []
            )

            if unnecessary_fields:

                st.write("**Unnecessary Fields:**")

                for field in unnecessary_fields:
                    st.warning(field)