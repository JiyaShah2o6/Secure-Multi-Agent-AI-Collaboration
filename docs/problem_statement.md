# Problem statement

A support agent may ask for more customer information than it needs while an internal
data agent legitimately has access to sensitive records. The interaction can disclose
data even though the components have reasonable individual responsibilities.

This project asks whether inspecting that interaction before retrieval can identify
unauthorized or unnecessary requests, constrain the exchange, and explain the outcome.
The prototype places a Governance Layer between simulated agents and a synthetic CRM.
It combines the existing permissions and purpose rules with confidentiality/security
analysis, risk classification, mitigation, bounded re-analysis and an audit trail.

The intended result is a demonstrable safe request, blocked restricted request, and
over-broad request transformed into an allowed minimal request. This project does not
claim production security or general natural-language understanding.
