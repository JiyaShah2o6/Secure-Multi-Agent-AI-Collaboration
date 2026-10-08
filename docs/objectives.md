# Objectives and acceptance evidence

| Objective | Implementation / verification |
| --- | --- |
| Intercept A → B data requests | AgentCommunication calls Governance before issuing an approval |
| Reuse authorization policy | Existing AgentA permissions; rechecked after modifications |
| Detect confidentiality/security risks | Field classification and deterministic payload/probing rules |
| Classify and mitigate | LOW/MEDIUM/HIGH; ALLOW, MODIFY, RESTRICT, BLOCK, HUMAN_REVIEW |
| Minimize over-broad requests | Purpose-required fields intersected with permissions; bounded re-analysis |
| Prevent unsafe reads | No reader call on blocked/error paths; one-use approval required |
| Explain decisions | Per-pass findings, reasons, authorization and trajectory in UI/audit |
| Represent human review | Local approve/restrict/reject with policy recheck |
| Preserve evidence | SQLite policy and execution events without returned customer values |
| Provide a reproducible demo | Four JSON scenarios, CLI assertions, Streamlit and unittest suite |

The prototype remains local and free of paid APIs. Full response analysis, real LLMs,
authenticated reviewers, and production deployment are outside the accepted scope.
