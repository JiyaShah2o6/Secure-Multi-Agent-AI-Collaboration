# Methodology

This is a deterministic prototype experiment, not an evaluation of a deployed LLM.
The unit of analysis is the request crossing the Agent A / Agent B boundary.

1. Keep the synthetic records, permission matrix and purpose rules fixed.
2. Send safe, unauthorized, over-broad and hostile requests through the same transport.
3. Record authorization, analyzer findings, risk, mitigation, modification trajectory
   and whether any customer fields were released.
4. Assert forbidden fields never appear and blocked requests never call the data reader.
5. Exercise audit errors, analysis errors, modified-request reauthorization, direct-read
   bypass attempts, single-use approvals, review decisions and session repetition.
6. Validate the same scenario definitions with CLI and Streamlit AppTest; inspect the
   live browser for the three core scenarios.

Reproduce with `python -m unittest discover tests` after installing requirements.
The suite includes the original Governance tests, adapted integrated Person 2 tests,
and new end-to-end/UI tests. Existing agent tests now assert the intended governed
flow: unnecessary fields can be minimized instead of rejected before Governance.
Tests were not removed merely to pass.

Expected observations: safe → ALLOW; explicit forbidden data → BLOCK; wildcard →
MODIFY → ALLOW with only a permitted purpose projection; repeated calls → RESTRICT.
Human review cannot turn an explicitly unauthorized request into a data read.

These finite tests establish behavior for the supplied cases, not detection accuracy
on unseen attacks. Report test results separately from security effectiveness claims.
