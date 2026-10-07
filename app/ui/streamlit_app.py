import sys
from pathlib import Path

import streamlit as st


# Add project root to Python import path
PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from app.agents.support_agent import SupportAgent
from app.data.customers import customers


# --------------------------------------------------
# Page configuration
# --------------------------------------------------

st.set_page_config(
    page_title="Secure Multi-Agent AI Collaboration",
    page_icon="🔐",
    layout="wide"
)


# --------------------------------------------------
# Custom styling
# --------------------------------------------------

st.markdown(
    """
    <style>
        .main-title {
            font-size: 42px;
            font-weight: 700;
            margin-bottom: 5px;
        }

        .subtitle {
            font-size: 17px;
            color: #9ca3af;
            margin-bottom: 30px;
        }

        .section-title {
            font-size: 24px;
            font-weight: 600;
            margin-top: 15px;
            margin-bottom: 15px;
        }

        .flow-box {
            padding: 18px;
            border-radius: 12px;
            text-align: center;
            background-color: #1f2937;
            border: 1px solid #374151;
        }

        .flow-arrow {
            text-align: center;
            font-size: 25px;
            padding-top: 18px;
        }

        .info-box {
            padding: 15px;
            border-radius: 10px;
            background-color: #111827;
            border: 1px solid #374151;
        }
    </style>
    """,
    unsafe_allow_html=True
)


# --------------------------------------------------
# Initialize Agent A
# --------------------------------------------------

agent = SupportAgent()


# --------------------------------------------------
# Header
# --------------------------------------------------

st.markdown(
    '<div class="main-title">🔐 Secure Multi-Agent AI Collaboration</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">'
    'Secure communication and controlled data sharing between AI agents'
    '</div>',
    unsafe_allow_html=True
)


# --------------------------------------------------
# Architecture flow
# --------------------------------------------------

st.subheader("System Flow")

flow1, arrow1, flow2, arrow2, flow3 = st.columns(
    [2, 0.5, 2, 0.5, 2]
)

with flow1:
    st.markdown(
        '<div class="flow-box"><b>🤖 Agent A</b><br>'
        'Support Agent</div>',
        unsafe_allow_html=True
    )

with arrow1:
    st.markdown(
        '<div class="flow-arrow">→</div>',
        unsafe_allow_html=True
    )

with flow2:
    st.markdown(
        '<div class="flow-box"><b>🛡️ Security Checks</b><br>'
        'Authorization<br>'
        'Data Minimization<br>'
        'Token Analysis</div>',
        unsafe_allow_html=True
    )

with arrow2:
    st.markdown(
        '<div class="flow-arrow">→</div>',
        unsafe_allow_html=True
    )

with flow3:
    st.markdown(
        '<div class="flow-box"><b>🗄️ Agent B</b><br>'
        'Data Agent</div>',
        unsafe_allow_html=True
    )


st.divider()


# --------------------------------------------------
# Sidebar configuration
# --------------------------------------------------

st.sidebar.header("Request Configuration")


scenario = st.sidebar.selectbox(
    "Demo Scenario",
    [
        "Custom Request",
        "Scenario 1 - Authorized",
        "Scenario 2 - Unauthorized",
        "Scenario 3 - Unnecessary Data"
    ]
)


customer_id = st.sidebar.selectbox(
    "Customer",
    list(customers.keys())
)


purpose_options = [
    "Resolve customer complaint",
    "Contact customer",
    "Process payment/refund"
]


# --------------------------------------------------
# Scenario presets
# --------------------------------------------------

if scenario == "Scenario 1 - Authorized":

    purpose = "Resolve customer complaint"

    requested_fields = [
        "complaint_status"
    ]

elif scenario == "Scenario 2 - Unauthorized":

    purpose = "Resolve customer complaint"

    requested_fields = [
        "bank_account"
    ]

elif scenario == "Scenario 3 - Unnecessary Data":

    purpose = "Resolve customer complaint"

    requested_fields = [
        "name"
    ]

else:

    purpose = st.sidebar.selectbox(
        "Purpose",
        purpose_options
    )

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


# --------------------------------------------------
# Request section
# --------------------------------------------------

st.subheader("Agent A → Agent B Request")

st.write(
    "Agent A requests customer information from Agent B. "
    "The request is analyzed before the information is shared."
)


request_col1, request_col2, request_col3 = st.columns(3)


with request_col1:

    st.markdown("**Customer ID**")

    st.info(customer_id)


with request_col2:

    st.markdown("**Purpose**")

    st.info(purpose)


with request_col3:

    st.markdown("**Requested Fields**")

    if requested_fields:
        st.info(", ".join(requested_fields))
    else:
        st.warning("No fields selected")


# --------------------------------------------------
# Send request
# --------------------------------------------------

if st.button(
    "🚀 Send Request",
    type="primary",
    use_container_width=True
):

    if not requested_fields:

        st.warning("Please select at least one field.")

    else:

        response = agent.request_customer_data(
            customer_id=customer_id,
            requested_fields=requested_fields,
            purpose=purpose
        )

        st.divider()

        # --------------------------------------------------
        # Request result
        # --------------------------------------------------

        st.subheader("Security Analysis Result")


        if response.status == "success":

            st.success("🟢 Request Allowed")

        elif response.status == "unauthorized":

            st.error("🔴 Request Unauthorized")

        elif response.status == "data_minimization_violation":

            st.warning("🟡 Data Minimization Violation")

        else:

            st.info(response.status)


        if response.message:

            st.write(response.message)


        # --------------------------------------------------
        # Analysis cards
        # --------------------------------------------------

        token_analysis = response.data.get(
            "token_analysis"
        )


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

                status = token_analysis["status"].title()

                st.metric(
                    "Efficiency",
                    status
                )


            if token_analysis["status"] == "efficient":

                st.success(
                    token_analysis["message"]
                )

            else:

                st.warning(
                    token_analysis["message"]
                )


        # --------------------------------------------------
        # Unauthorized information
        # --------------------------------------------------

        if response.status == "unauthorized":

            unauthorized_fields = response.data.get(
                "unauthorized_fields",
                []
            )


            if unauthorized_fields:

                st.subheader("Authorization Analysis")

                st.error(
                    "The following fields are not authorized "
                    "for Agent A:"
                )


                for field in unauthorized_fields:

                    st.write(f"❌ `{field}`")


        # --------------------------------------------------
        # Data minimization information
        # --------------------------------------------------

        if response.status == "data_minimization_violation":

            unnecessary_fields = response.data.get(
                "unnecessary_fields",
                []
            )


            if unnecessary_fields:

                st.subheader("Data Minimization Analysis")

                st.warning(
                    "The following fields are not necessary "
                    "for the selected purpose:"
                )


                for field in unnecessary_fields:

                    st.write(f"⚠️ `{field}`")


        # --------------------------------------------------
        # Agent B response
        # --------------------------------------------------

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

                st.info(
                    "Agent B did not return any data."
                )


# --------------------------------------------------
# Footer
# --------------------------------------------------

st.divider()

st.caption(
    "Prototype: Secure Multi-Agent AI Collaboration | "
    "Agent A → Security Checks → Agent B"
)