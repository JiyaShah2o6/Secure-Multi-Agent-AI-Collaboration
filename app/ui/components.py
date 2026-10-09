"""
Shared UI Components for the Governance Console.
Provides consistent, theme-aware visual components across all console views.
"""

from __future__ import annotations

import streamlit as st


def get_tone_for_status(value: str) -> str:
    """Map governance decisions, risk tiers, and sensitivity classifications to semantic tones."""
    norm = str(value).strip().upper()
    if norm in {"ALLOW", "PASSED", "LOW", "SUCCESS", "APPROVE", "EFFICIENT"}:
        return "good"
    if norm in {"BLOCK", "DENIED", "HIGH", "CRITICAL", "BLOCKED", "ERROR", "UNAUTHORIZED", "RESTRICTED", "REJECT"}:
        return "bad"
    if norm in {"HUMAN_REVIEW", "PENDING", "MEDIUM", "RESTRICT", "MODIFY", "CONFIDENTIAL", "WARN"}:
        return "warn"
    if norm in {"INTERNAL", "UNKNOWN"}:
        return "neutral"
    return "info"


def render_status_badge(label: str, tone: str | None = None) -> str:
    """Return HTML string for an accessible, theme-aware status badge."""
    if not tone:
        tone = get_tone_for_status(label)
    return f'<span class="status {tone}">{label}</span>'


def render_page_header(title: str, subtitle: str | None = None) -> None:
    """Render consistent page heading and concise subtitle with standard spacing tokens."""
    st.markdown(f"<h1>{title}</h1>", unsafe_allow_html=True)
    if subtitle:
        st.markdown(f"<p class='page-subtitle'>{subtitle}</p>", unsafe_allow_html=True)


def render_empty_state(title: str, description: str | None = None) -> None:
    """Render an accessible, consistent empty state card."""
    desc_html = f"<p class='empty-desc'>{description}</p>" if description else ""
    st.markdown(
        f"""
        <div class="gov-card empty-state-box">
            <div class="empty-title">{title}</div>
            {desc_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_card(title: str, content_html: str) -> None:
    """Render a content card with title and theme-aware surface."""
    st.markdown(
        f"""
        <div class="gov-card">
            <h4>{title}</h4>
            <div>{content_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_technical_pipeline_details() -> None:
    """Render the collapsible technical details section on the Overview page."""
    with st.expander("Technical Details: Sequential Governance Pipeline", expanded=False):
        st.markdown(
            """
            The central governance boundary enforces sequential security and compliance stages on every inter-agent request:
            """
        )
        st.table([
            {"Stage": "1. Request Validation", "Function": "Enforces minimum schema: sender, receiver, customer_id, fields, stated purpose."},
            {"Stage": "2. Authorization Matrix", "Function": "Evaluates agent-role permissions per requested field; identifies forbidden & unknown attributes."},
            {"Stage": "3. Confidentiality Analysis", "Function": "Classifies requested data into Internal, Confidential, Restricted, or Unknown sensitivity tiers."},
            {"Stage": "4. Security & Anti-Probing", "Function": "Detects instruction overrides, payload injection, exfiltration relays, and repeated probing."},
            {"Stage": "5. Risk Classification", "Function": "Evaluates combined findings into deterministic LOW, MEDIUM, or HIGH risk ratings."},
            {"Stage": "6. Data Minimization", "Function": "Narrows over-broad requests down to purpose-justified, permitted schema projections."},
            {"Stage": "7. Human Review", "Function": "Routes complex/unrecognized requests to manual oversight with explicit state transitions."},
            {"Stage": "8. Approval Gate", "Function": "Issues cryptographically random, short-lived single-use tokens bound to the approved field set."},
        ])
        st.caption("Control flow: Agent A (Support) ──► Request Gateway ──► Governance Engine ──[ Single-Use Ticket ]──► Agent B (Data) ──► Synthetic Database")
