import sys
import json
import os
from uuid import uuid4
from pathlib import Path

import streamlit as st


# Add project root to Python import path
PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from app.agents.support_agent import SupportAgent
from app.data.customers import customers
from app.agents.communication import AgentCommunication
from app.authorization.data_minimization import PURPOSE_FIELDS
from app.governance.audit import AuditLogger


st.set_page_config(
    page_title="Secure Multi-Agent AI Collaboration",
    page_icon="🔐",
    layout="wide"
)


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




# ---------------------------------------------------------
# HEADER
# ---------------------------------------------------------

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


# ---------------------------------------------------------
# SYSTEM FLOW
# ---------------------------------------------------------

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
        'Confidentiality / Security<br>'
        'Risk / Mitigation / Re-analysis<br>'
        'Audit Logging</div>',
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


# ---------------------------------------------------------
# SIDEBAR CONFIGURATION
# ---------------------------------------------------------

st.caption("Deterministic academic prototype. Simulated agents and fake data only; no LLM/API or cost calculation.")
scenarios = json.loads((PROJECT_ROOT / "app/data/scenarios.json").read_text(encoding="utf-8"))
scenario_map = {item["name"]: item for item in scenarios}
scenario = st.sidebar.selectbox("Demo Scenario", ["Custom Request", *scenario_map], key="scenario")
customer_id = st.sidebar.selectbox("Customer", list(customers), key="customer")

if "demo_session" not in st.session_state:
    st.session_state.demo_session = str(uuid4())
    st.session_state.agents = {}
    st.session_state.responses = {}

if st.sidebar.button("New session for this scenario"):
    st.session_state.agents.pop(scenario, None)
    st.session_state.responses.pop(scenario, None)

if scenario not in st.session_state.agents:
    audit_path = Path(os.environ.get(
        "GOVERNANCE_AUDIT_PATH",
        str(PROJECT_ROOT / ".runtime" / "audit" / (st.session_state.demo_session + ".db")),
    ))
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    transport = AgentCommunication(audit_logger=AuditLogger(str(audit_path)))
    st.session_state.agents[scenario] = SupportAgent(transport)
agent = st.session_state.agents[scenario]
st.sidebar.caption("Each scenario has its own session. Three requests within 60 seconds trigger probing restriction; changing scenarios does not reset that scenario's history.")

available_fields = ["customer_id", "name", "email", "phone", "complaint_id", "complaint_status",
                    "complaint_description", "address", "bank_account", "card_details", "*"]
if scenario == "Custom Request":
    purpose_option = st.sidebar.selectbox("Purpose", [*PURPOSE_FIELDS, "Other / human review"], key="purpose_option")
    purpose = (st.sidebar.text_input("Describe purpose", "Unspecified task", key="custom_purpose")
               if purpose_option == "Other / human review" else purpose_option)
    requested_fields = st.sidebar.multiselect("Requested Fields", available_fields,
                                              default=["complaint_status"], key="custom_fields")
    token_limit = st.sidebar.number_input("Token Limit", min_value=1, max_value=500, value=100, key="token_limit")
else:
    config = scenario_map[scenario]
    purpose, requested_fields, token_limit = config["purpose"], config["requested_fields"], config["token_limit"]

st.subheader("Agent A → Governance → Agent B Request")
if scenario != "Custom Request" and config.get("description"):
    st.info(config["description"])
left, middle, right = st.columns(3)
left.write("**Customer:** " + customer_id)
middle.write("**Purpose:** " + (purpose if purpose in PURPOSE_FIELDS else "Custom purpose (analyzed, not echoed)"))
right.write("**Requested fields:** " + ", ".join(requested_fields))
if scenario == "Scenario 4 - Token-Inefficient Request":
    st.info("A deliberately low token limit demonstrates an efficiency warning. It does not increase security risk.")

if st.button("Send Request", type="primary", key="send"):
    if not requested_fields:
        st.warning("Please select at least one field.")
    else:
        st.session_state.responses[scenario] = agent.request_customer_data(
            customer_id, requested_fields, purpose, token_limit=token_limit,
        )

response = st.session_state.responses.get(scenario)
if response is not None and response.status == "human_review":
    st.subheader("Human Review")
    st.warning("No data has been retrieved. This is a local demo reviewer, not an authenticated supervisor system.")
    st.caption("Confirm a supported purpose. Approve and Restrict re-run all checks; forbidden fields and hostile requests cannot be overridden.")
    action = st.selectbox("Review action", ["Approve", "Restrict", "Reject"], key="review_action")
    review_purpose = st.selectbox("Confirmed purpose", list(PURPOSE_FIELDS), key="review_purpose")
    review_fields = response.metadata.get("requested_fields", [])
    if action == "Restrict":
        review_fields = st.multiselect("Keep only these fields", review_fields,
                                       default=review_fields, key="review_fields")
    if st.button("Apply review action", key="review_submit"):
        reviewed = agent.communication.review_request(
            response.metadata["request_id"], action, purpose=review_purpose, fields=review_fields,
        )
        reviewed.metadata["token_analysis"] = response.metadata.get("token_analysis", {})
        st.session_state.responses[scenario] = reviewed
        st.rerun()

response = st.session_state.responses.get(scenario)
if response is not None:
    st.divider()
    st.subheader("Governance Result")
    metadata = response.metadata
    governance = metadata.get("governance", {})
    if response.status == "success":
        st.success("ALLOW — approved request processed")
    elif response.status in {"blocked", "unauthorized", "error"}:
        st.error(response.message or "Request withheld")
    else:
        st.warning(response.message or response.status)
    st.caption("Request ID: " + metadata.get("request_id", "unavailable"))
    cols = st.columns(3)
    cols[0].metric("Final risk", governance.get("risk_level", "Unavailable"))
    cols[1].metric("Decision", governance.get("decision", "ERROR"))
    cols[2].metric("Data returned", "Yes" if response.data else "No")
    st.write(governance.get("reason", response.message))

    trajectory = governance.get("trajectory", [])
    if trajectory:
        st.subheader("Analysis and Re-analysis")
        if any(step["decision"] == "MODIFY" for step in trajectory):
            st.info("DETECT excessive data → EXPLAIN the risk → MITIGATE with fewer fields → RE-ANALYSE → ALLOW only if safe")
        st.write(" → ".join(step["decision"] for step in trajectory))
        for step in trajectory:
            with st.expander(f"Pass {step['pass'] + 1}: {step['risk_level']} / {step['decision']}", expanded=True):
                st.write(step["reason"])
                if step.get("authorization") is not None:
                    st.write("Authorization:", "Passed" if step["authorization"] else "Denied")
                if step["findings"]:
                    st.dataframe(step["findings"], use_container_width=True, hide_index=True)
                else:
                    st.write("No findings.")
                if step.get("modified_fields"):
                    st.write("Proposed fields: " + ", ".join(step["modified_fields"]))

    st.subheader("Authorization and Data Minimization")
    initial_auth = metadata.get("authorization", {})
    minimum = metadata.get("data_minimization", {})
    st.write("Original field permissions:", initial_auth)
    st.write("Original purpose check:", minimum)
    st.write("Effective fields:", metadata.get("effective_fields", []))
    if "*" in metadata.get("requested_fields", []):
        st.caption("Wildcard is a projection proposal. Only permitted, purpose-required concrete fields can proceed after re-analysis.")

    token = metadata.get("token_analysis", {})
    if token:
        st.subheader("Token Efficiency")
        cols = st.columns(3)
        cols[0].metric("Estimated tokens", token.get("token_count", 0))
        cols[1].metric("Recommended limit", token.get("token_limit", 0))
        cols[2].metric("Efficiency", token.get("status", "unknown").upper())
        if token.get("status") == "high":
            st.warning("Token efficiency warning: " + token.get("suggestion", "Reduce unnecessary content."))
        else:
            st.info(token.get("message", ""))
        st.caption("Word-count approximation; not an exact tokenizer and not a cost calculator.")

    st.subheader("Agent B Response")
    if response.status == "success":
        st.json(response.data)
    else:
        st.info("No customer data released.")
    with st.expander("Audit trail for this request"):
        try:
            from dataclasses import asdict
            records = agent.communication.audit_logger.get_records_by_request_id(metadata.get("request_id", ""))
            st.json([asdict(record) for record in records])
        except Exception:
            st.error("Audit storage is unavailable.")

st.divider()
st.caption("Governance is the central decision-maker. Response monitoring checks field projection only; full response-content analysis is future work.")
