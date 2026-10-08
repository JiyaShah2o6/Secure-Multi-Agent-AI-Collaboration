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


st.markdown("""
<style>
.block-container {max-width: 1280px; padding-top: 4rem;}
.eyebrow {font: 600 .75rem monospace; letter-spacing: .14em; color: #58a6b0; margin-bottom: .6rem;}
.dashboard-title {font-size: clamp(1.8rem, 3vw, 2.6rem); font-weight: 700; line-height: 1.15; margin-bottom: .6rem;}
.dashboard-subtitle {opacity: .7; margin-bottom: 1.6rem;}
.route {display: grid; grid-template-columns: 1fr auto 1fr auto 1.3fr auto 1fr auto 1fr; align-items: center; gap: .6rem; margin: 1rem 0 1.5rem;}
.node {border: 1px solid #64748b55; border-radius: 10px; padding: 1rem; min-height: 98px;}
.node small {display:block; opacity:.65; font-size:.72rem; margin-bottom:.4rem;}
.node strong {font-size:.95rem;}
.node.gate {border: 1px solid #399b9b; background: #399b9b18;}
.arrow {color:#58a6b0;}
@media(max-width:850px) {.route {grid-template-columns:1fr;} .node {min-height:0;} .arrow {text-align:center; transform:rotate(90deg);}}
</style>
<div class="eyebrow">INTERACTION SECURITY / ACADEMIC PROTOTYPE</div>
<div class="dashboard-title">Two-Agent Governance Console</div>
<div class="dashboard-subtitle">Inspect the exchange. Enforce the policy. Explain the decision.</div>
<div class="route" aria-label="Customer to Agent A to Governance to Agent B to Synthetic Customer Data">
<div class="node"><small>REQUEST ORIGIN</small><strong>Customer</strong></div><span class="arrow">→</span>
<div class="node"><small>AGENT A</small><strong>Support Agent</strong></div><span class="arrow">→</span>
<div class="node gate"><small>SECURITY BOUNDARY</small><strong>Governance Layer</strong></div><span class="arrow">→</span>
<div class="node"><small>AGENT B</small><strong>Data Agent</strong></div><span class="arrow">→</span>
<div class="node"><small>LOCAL FIXTURES</small><strong>Synthetic Customer Data</strong></div>
</div>
""", unsafe_allow_html=True)
st.caption("Local, deterministic agents · Synthetic records only · No paid APIs")
with st.expander("Three core demonstrations", expanded=True):
    safe, blocked, broad = st.columns(3)
    safe.markdown("**01 / SAFE**\n\nLOW → ALLOW")
    blocked.markdown("**02 / BANK & CARD**\n\nHIGH → BLOCK → No data")
    broad.markdown("**03 / OVER-BROAD**\n\nMODIFY → RE-ANALYSE → ALLOW")
st.sidebar.title("Request controls")
st.sidebar.caption("Configure Agent A's structured message")
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

st.subheader("01 / Agent A — outbound request")
st.caption("Agent A → Governance · Request preview; not yet an authorization grant")
if scenario != "Custom Request" and config.get("description"):
    st.info(config["description"])
left, middle, right = st.columns(3)
left.write("**Customer:** " + customer_id)
middle.write("**Purpose:** " + (purpose if purpose in PURPOSE_FIELDS else "Custom purpose (analyzed, not echoed)"))
right.write("**Requested fields:** " + ", ".join(requested_fields))
if scenario == "Scenario 4 - Token-Inefficient Request":
    st.info("A deliberately low token limit demonstrates an efficiency warning. It does not increase security risk.")

if st.button("Send Request", type="primary", key="send"):
    st.session_state.responses[scenario] = agent.request_customer_data(
        customer_id, requested_fields, purpose, token_limit=token_limit,
    )

response = st.session_state.responses.get(scenario)
if response is not None and response.status == "human_review":
    st.subheader("Human review — decision required")
    st.warning("No data has been retrieved. This is a local demo reviewer, not an authenticated supervisor system.")
    st.caption("Confirm a supported purpose. Approve and Restrict re-run all checks; forbidden fields and hostile requests cannot be overridden.")
    st.caption("Restrict sets an upper bound: later minimization cannot add fields you did not keep.")
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
        if reviewed.status == "error":
            st.error(reviewed.message)
        else:
            reviewed.metadata["token_analysis"] = response.metadata.get("token_analysis", {})
            st.session_state.responses[scenario] = reviewed
            st.rerun()

response = st.session_state.responses.get(scenario)
if response is not None:
    st.divider()
    st.subheader("02 / Governance — security decision")
    metadata = response.metadata
    governance = metadata.get("governance", {})
    if response.status == "success":
        st.success("ALLOW — approved request processed")
    elif response.status in {"blocked", "unauthorized", "error"}:
        st.error(response.message or "Request withheld")
    else:
        st.warning(response.message or response.status)
    st.caption("Request ID: " + metadata.get("request_id", "unavailable"))
    cols = st.columns(4)
    cols[3].metric("Authorization", "Passed" if governance.get("authorization") is True else "Denied" if governance.get("authorization") is False else "Not reported")
    cols[0].metric("Final risk", governance.get("risk_level", "Unavailable"))
    cols[1].metric("Decision", governance.get("decision", "ERROR"))
    cols[2].metric("Data returned", "Yes" if response.data else "No")
    st.write(governance.get("reason", response.message))

    trajectory = governance.get("trajectory", [])
    if trajectory:
        st.subheader("Security analysis & re-analysis")
        if any(step["decision"] == "MODIFY" for step in trajectory):
            st.info("DETECT excessive data → EXPLAIN the risk → MITIGATE with fewer fields → RE-ANALYSE → ALLOW only if safe")
        st.write(" → ".join(step["decision"] for step in trajectory))
        for step in trajectory:
            with st.expander(f"Pass {step['pass'] + 1}: {step['risk_level']} / {step['decision']}", expanded=(len(trajectory) > 1)):
                st.write(step["reason"])
                if step.get("authorization") is not None:
                    st.write("Authorization:", "Passed" if step["authorization"] else "Denied")
                if step["findings"]:
                    st.dataframe(step["findings"], use_container_width=True, hide_index=True)
                else:
                    st.write("No findings.")
                if step.get("modified_fields"):
                    st.write("Proposed fields: " + ", ".join(step["modified_fields"]))

    with st.expander("Permission & minimization details"):
        initial_auth = metadata.get("authorization", {})
        minimum = metadata.get("data_minimization", {})
        st.write("Original field permissions:", initial_auth)
        st.write("Original purpose check:", minimum)
        st.write("Effective fields:", metadata.get("effective_fields", []))
        if metadata.get("review_scope") is not None:
            st.write("Reviewer field limit:", metadata["review_scope"])
        if "*" in metadata.get("requested_fields", []):
            st.caption("Wildcard proposes a projection; only permitted, purpose-required fields proceed after re-analysis.")

    st.subheader("03 / Governance → Agent B — delivery & response")
    delivery, payload = st.columns([1, 2])
    with delivery:
        with st.container(border=True):
            st.markdown("**Governance dispatch**")
            if response.status == "success":
                st.success("Delivered · approved request")
            elif governance.get("decision") == "ALLOW":
                st.warning("Policy allowed · execution did not succeed")
            else:
                st.info("Withheld · no data released")
            st.caption("Agent B returns only the approved projection. Customer values are separate from security diagnostics.")
    with payload:
        with st.container(border=True):
            st.markdown("**Agent B / Data Agent**")
            if response.status == "success":
                st.json(response.data)
            else:
                st.write("No customer data released.")
    st.subheader("04 / Audit — decision evidence")
    with st.expander("Audit trail for this request"):
        try:
            from dataclasses import asdict
            records = agent.communication.audit_logger.get_records_by_request_id(metadata.get("request_id", ""))
            st.caption(f"{len(records)} recorded event(s) · Policy decisions and execution outcomes")
            st.dataframe([{"Decision": r.decision, "Risk": r.risk_level,
                           "Review": r.human_action or "—", "Timestamp (UTC)": r.timestamp}
                          for r in records], use_container_width=True, hide_index=True)
            st.json([asdict(record) for record in records], expanded=False)
        except Exception:
            st.error("Audit storage is unavailable.")

    token = metadata.get("token_analysis", {})
    if token:
        st.subheader("Resource monitor / Token efficiency")
        cols = st.columns(3)
        cols[0].metric("Estimated tokens", token.get("token_count", 0))
        cols[1].metric("Recommended limit", token.get("token_limit", 0))
        cols[2].metric("Efficiency", token.get("status", "unknown").upper())
        if token.get("status") == "high":
            st.warning("Token efficiency warning: " + token.get("suggestion", "Reduce unnecessary content."))
        else:
            st.info(token.get("message", ""))
        st.caption("Word-count approximation; not an exact tokenizer and not a cost calculator.")


st.divider()
st.caption("Governance is the central decision-maker. Response monitoring checks field projection only; full response-content analysis is future work.")
