import sys
import json
import os
from dataclasses import asdict
from uuid import uuid4
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.agents.support_agent import SupportAgent
from app.data.customers import customers
from app.agents.communication import AgentCommunication
from app.authorization.data_minimization import PURPOSE_FIELDS
from app.governance.audit import AuditLogger

st.set_page_config(page_title="Secure Multi-Agent AI Collaboration", layout="wide")
st.markdown("""
<style>
.block-container {max-width:1200px; padding-top:2.5rem;}
[data-testid="stAppViewContainer"], [data-testid="stHeader"] {background:#f5f7fa;}
[data-testid="stMain"] {color:#172b4d;}
h1 {font-size:1.65rem !important; font-weight:650 !important;}
h2 {font-size:1.3rem !important;}
h3 {font-size:1.05rem !important;}
[data-testid="stSidebar"] {background:#14243b; color:#edf2f8;}
[data-testid="stSidebar"] h1, [data-testid="stSidebar"] p,
[data-testid="stSidebar"] label {color:#edf2f8;}
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] p {color:#b8c6d8;}
[data-testid="stSidebar"] [data-baseweb="select"] {color:#172b4d;}
[data-testid="stSidebar"] button p {color:#172b4d;}
button, [data-baseweb="select"] > div, [data-baseweb="input"] {border-radius:4px !important;}
button[kind="primary"] {background:#245caa; border-color:#245caa; color:white;}
[data-testid="stMetricValue"] {font-size:1.4rem;}
[data-testid="stDataFrame"], [data-testid="stTable"], [data-testid="stExpander"] {border-radius:3px;}
.status {display:inline-block; padding:4px 10px; border:1px solid; border-radius:3px; font-size:.85rem; font-weight:600;}
.status.good {color:#17603b; background:#edf7f0; border-color:#a3cdb1;}
.status.bad {color:#9d2525; background:#fff1f1; border-color:#e1b0b0;}
.status.pending {color:#805900; background:#fff8e7; border-color:#ddc58c;}
</style>
""", unsafe_allow_html=True)


def open_request(preset="Custom Request"):
    st.session_state.scenario = preset
    st.session_state.page = "New Request"


def show_request_page():
    st.session_state.page = "New Request"


def field_list(fields):
    return ", ".join(str(field) for field in fields) if fields else "None"


def authorization_label(value):
    return "Passed" if value is True else "Denied" if value is False else "Not reported"


scenarios = json.loads((PROJECT_ROOT / "app/data/scenarios.json").read_text(encoding="utf-8"))
scenario_map = {item["name"]: item for item in scenarios}
st.sidebar.title("Secure Data Exchange")
st.sidebar.caption("CSE research prototype\n\nTwo agents. One governance boundary.")
page = st.sidebar.radio("Workspace", ["Overview", "New Request", "Demo Scenarios", "Audit Log", "System Info"],
                        index=1, key="page")
st.sidebar.divider()
for key in ("purpose_option", "custom_purpose", "custom_fields", "customer", "token_limit",
            "review_action", "review_purpose", "review_fields"):
    if key in st.session_state:
        st.session_state[key] = st.session_state[key]
scenario = st.sidebar.selectbox("Request preset", ["Custom Request", *scenario_map],
                                key="scenario", on_change=show_request_page)

if "demo_session" not in st.session_state:
    st.session_state.demo_session = str(uuid4())
    st.session_state.agents = {}
    st.session_state.responses = {}

if "submitted_details" not in st.session_state:
    st.session_state.submitted_details = {}

if st.sidebar.button("New session for this scenario"):
    st.session_state.agents.pop(scenario, None)
    st.session_state.responses.pop(scenario, None)
    st.session_state.submitted_details.pop(scenario, None)

if scenario not in st.session_state.agents:
    audit_path = Path(os.environ.get(
        "GOVERNANCE_AUDIT_PATH",
        str(PROJECT_ROOT / ".runtime" / "audit" / (st.session_state.demo_session + ".db")),
    ))
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    transport = AgentCommunication(audit_logger=AuditLogger(str(audit_path)))
    st.session_state.agents[scenario] = SupportAgent(transport)
agent = st.session_state.agents[scenario]
st.sidebar.caption("Three requests within 60 seconds trigger probing restriction. Each preset retains its own history. Reset its session before repeating a demonstration.")
st.sidebar.divider()
st.sidebar.caption("Local execution · Synthetic records\n\nNo external AI services")

st.title("Secure Multi-Agent AI Collaboration")
st.caption("Governed access to synthetic customer data")
st.divider()

if page == "Overview":
    st.header("Overview")
    st.write("Inspect what a support agent requests before a data agent releases it. The system checks permissions, sensitive fields and purpose, then allows, modifies or blocks the exchange.")
    st.subheader("Start here")
    st.write("Use **New Request** to choose a purpose and fields, or **Demo Scenarios** for the three prepared presentation cases. Results explain the decision and show whether Agent B returned data.")
    left, right = st.columns(2)
    left.button("Create a request", on_click=open_request, use_container_width=True)
    right.button("Open demo scenarios", on_click=lambda: st.session_state.update(page="Demo Scenarios"), use_container_width=True)
    st.subheader("System responsibilities")
    st.table([
        {"Stage": "1. Customer input", "Responsibility": "Select a customer, purpose and requested fields."},
        {"Stage": "2. Agent A · Support", "Responsibility": "Build a structured request and submit it to governance."},
        {"Stage": "3. Governance", "Responsibility": "Authorize, inspect, minimize, re-analyze and audit the request."},
        {"Stage": "4. Agent B · Data", "Responsibility": "Read only the approved fields using a single-use approval."},
        {"Stage": "5. Synthetic records", "Responsibility": "Three local customer fixtures; no real customer database."},
    ])

elif page == "Demo Scenarios":
    st.header("Demo Scenarios")
    st.write("Choose a case below. On New Request, keep customer C101 and click **Analyze Request**. No data is retrieved until you analyze the request.")
    st.table([
        {"Case": "Authorized", "Request": "complaint_status", "Expected result": "LOW → ALLOW"},
        {"Case": "Sensitive / unauthorized", "Request": "bank_account, card_details", "Expected result": "HIGH → BLOCK · No data"},
        {"Case": "Over-broad", "Request": "* (all fields)", "Expected result": "MEDIUM → MODIFY → RE-ANALYZE → LOW → ALLOW"},
    ])
    for label, name in zip(["1. Authorized request", "2. Sensitive / unauthorized request", "3. Over-broad request"], scenario_map):
        st.button(label, on_click=open_request, args=(name,), use_container_width=True)
    st.caption("The existing fourth token-efficiency demonstration is available from Request preset in the sidebar.")

elif page == "New Request":
    st.header("New Request")
    st.write("Choose the task and the information needed. Governance checks this request before Agent B can read customer data.")
    available_fields = ["customer_id", "name", "email", "phone", "complaint_id", "complaint_status",
                        "complaint_description", "address", "bank_account", "card_details", "*"]
    if scenario == "Custom Request":
        purpose_option = st.selectbox("1. Purpose", [*PURPOSE_FIELDS, "Other / human review"], key="purpose_option")
        purpose = (st.text_input("Describe purpose", "Unspecified task", key="custom_purpose")
                   if purpose_option == "Other / human review" else purpose_option)
    else:
        config = scenario_map[scenario]
        purpose, requested_fields, token_limit = config["purpose"], config["requested_fields"], config["token_limit"]
        st.caption("Prepared case: " + scenario)
        st.text_input("1. Purpose", value=purpose, disabled=True)
    st.text_input("2. Agent", value="Agent A — Support Agent (requesting from Agent B — Data Agent)", disabled=True)
    customer_id = st.selectbox("3. Customer ID", list(customers), key="customer")
    if scenario == "Custom Request":
        requested_fields = st.multiselect("4. Requested Fields", available_fields,
                                          default=["complaint_status"], key="custom_fields",
                                          help="Choose only what the purpose needs. * requests a broad projection that must be minimized.")
        with st.expander("Token efficiency settings"):
            token_limit = st.number_input("Token Limit", min_value=1, max_value=500, value=100, key="token_limit")
    else:
        st.text_input("4. Requested Fields", value=field_list(requested_fields), disabled=True)
    if st.button("Analyze Request", type="primary", key="send"):
        st.session_state.submitted_details[scenario] = {
            "Customer": customer_id,
            "Purpose": purpose if purpose in PURPOSE_FIELDS else "Custom purpose (not echoed)",
        }
        st.session_state.responses[scenario] = agent.request_customer_data(
            customer_id, requested_fields, purpose, token_limit=token_limit,
        )

    response = st.session_state.responses.get(scenario)
    if response is not None and response.status == "human_review":
        st.subheader("Human review required")
        st.warning("No data retrieved. Confirm a supported purpose before continuing.")
        st.caption("Local demo review only. Approval cannot override forbidden fields or hostile requests. Restrictions remain an upper bound during re-analysis.")
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
        metadata = response.metadata
        governance = metadata.get("governance", {})
        trajectory = governance.get("trajectory", [])
        st.divider()
        st.header("Analysis result")
        st.caption("Last submitted request for this preset. Changing input fields does not run a new analysis.")
        decision = governance.get("decision", "ERROR")
        label = decision if decision in {"ALLOW", "BLOCK", "MODIFY", "RESTRICT", "HUMAN_REVIEW"} else "ERROR"
        tone = "good" if response.status == "success" else "bad" if response.status in {"blocked", "unauthorized", "error"} else "pending"
        st.markdown(f'<span class="status {tone}">{label}</span>', unsafe_allow_html=True)
        st.write(governance.get("reason", response.message))
        cols = st.columns(3)
        cols[0].metric("Final risk", governance.get("risk_level", "Unavailable"))
        cols[1].metric("Decision", decision)
        cols[2].metric("Data returned", "Yes" if response.data else "No")
        st.subheader("Request Details")
        st.table([
            {"Item": "Request ID", "Value": metadata.get("request_id", "Unavailable")},
            {"Item": "Route", "Value": "Agent A / Support to Agent B / Data"},
            *[{"Item": key, "Value": value} for key, value in st.session_state.submitted_details.get(scenario, {}).items()],
            {"Item": "Submitted fields", "Value": field_list(metadata.get("requested_fields", []))},
        ])
        st.subheader("Authorization, Confidentiality & Data Minimization")
        findings = [finding for step in trajectory for finding in step.get("findings", [])]
        if not trajectory:
            findings = governance.get("findings", [])
        confidential = [f for f in findings if f.get("analyzer") == "confidentiality"]
        minimum = metadata.get("data_minimization", {})
        st.table([
            {"Check": "Authorization", "Result": authorization_label(governance.get("authorization")),
             "Explanation": "Current governance pass; explicit forbidden fields are denied."},
            {"Check": "Confidentiality", "Result": f"{len(confidential)} finding(s)" if trajectory or governance.get("findings") else "Not reported",
             "Explanation": "; ".join(dict.fromkeys(f["explanation"] for f in confidential)) or "No confidentiality findings reported."},
            {"Check": "Data minimization", "Result": "Modified and re-analyzed" if any(s["decision"] == "MODIFY" for s in trajectory) else "Appropriate" if minimum.get("valid") else "Not satisfied" if minimum else "Not reported",
             "Explanation": minimum.get("message", "See decision and audit evidence.")},
        ])
        if trajectory:
            st.subheader("Risk & Final Decision")
            st.table([{"Pass": step["pass"] + 1, "Authorization": authorization_label(step.get("authorization")),
                       "Risk": step["risk_level"], "Action": step["decision"],
                       "Proposed fields": field_list(step.get("modified_fields")), "Reason": step["reason"]}
                      for step in trajectory])
            with st.expander("Security findings and field scope"):
                if findings:
                    st.dataframe([{k: f.get(k, "") for k in ("analyzer", "severity", "explanation", "suggested_action")}
                                  for f in findings], use_container_width=True, hide_index=True)
                else:
                    st.write("No findings.")
                st.write("Effective request fields:", field_list(metadata.get("effective_fields", [])))
                if metadata.get("review_scope") is not None:
                    st.write("Reviewer field limit:", field_list(metadata["review_scope"]))
                st.caption("Effective fields are diagnostic information, not a release grant. Only ALLOW can proceed to retrieval.")
        st.subheader("Agent B Response")
        if response.status == "success":
            st.write("Approved request delivered. Agent B returned only the following fields:")
            st.table([{"Field": key, "Value": str(value)} for key, value in response.data.items()])
        elif decision == "ALLOW":
            st.error("Policy allowed the request, but execution failed. No customer data released.")
        else:
            st.write("Request withheld. No customer data released.")
        st.caption("Policy and execution evidence is available on the Audit Log page.")
        token = metadata.get("token_analysis", {})
        if token:
            with st.expander("Token efficiency"):
                st.table([{"Estimated tokens": token.get("token_count", 0), "Limit": token.get("token_limit", 0),
                           "Efficiency": token.get("status", "unknown")}])
                if token.get("status") == "high":
                    st.warning("Token efficiency warning: " + token.get("suggestion", "Reduce unnecessary content."))
                st.caption("Word-count approximation; not billing or a security risk score.")

elif page == "Audit Log":
    st.header("Audit Log")
    st.write("Recorded policy decisions and execution outcomes for the current browser demo session. Customer response values are not stored in the audit.")
    try:
        records = agent.communication.audit_logger.get_all_records()
        if records:
            st.dataframe([{"Request ID": r.request_id, "Timestamp (UTC)": r.timestamp,
                           "Risk": r.risk_level, "Decision": r.decision,
                           "Review": r.human_action or "—", "Execution": r.details.get("execution", {}).get("status", "Not recorded")}
                          for r in records], use_container_width=True, hide_index=True)
            with st.expander("Full sanitized audit evidence"):
                st.json([asdict(record) for record in records], expanded=False)
        else:
            st.write("No audit records yet. Analyze a request to create a policy record.")
    except Exception:
        st.error("Audit storage is unavailable.")

elif page == "System Info":
    st.header("System Info")
    st.table([
        {"Component": "Agents", "Implementation": "Two deterministic Python components, not live LLMs."},
        {"Component": "Communication", "Implementation": "In-process structured requests through AgentCommunication."},
        {"Component": "Authorization", "Implementation": "Fixed Agent A permission matrix; checked before data access."},
        {"Component": "Governance", "Implementation": "Rule/regex findings, risk classification, mitigation and bounded re-analysis."},
        {"Component": "Customer data", "Implementation": "Three synthetic records in a local Python dictionary."},
        {"Component": "Audit", "Implementation": "Local SQLite; sanitized request and decision evidence."},
        {"Component": "Human review", "Implementation": "Local demonstration; no reviewer authentication."},
        {"Component": "Response protection", "Implementation": "Approved field projection and safe failure; no full content analysis."},
        {"Component": "Token monitoring", "Implementation": "Word-count estimate; no paid services or cost calculation."},
    ])
    st.caption("Academic prototype. Fixed rules and local approvals do not protect against someone modifying the Python process or reading the fixture source directly.")
