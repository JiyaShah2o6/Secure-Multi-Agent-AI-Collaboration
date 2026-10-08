# Demonstration workflow

1. Follow README setup and run `python main.py` for the four CLI assertions.
2. Launch Streamlit, select C101 and Scenario 1. Show LOW / ALLOW and complaint status.
3. Select Scenario 2. Show unauthorized bank/card findings, HIGH / BLOCK, and no data.
4. Select Scenario 3. Point to the original `*`, MEDIUM findings, proposed permitted
   fields, then the second LOW / ALLOW pass. Show only customer ID, complaint ID and status.
5. Expand the audit trail. Explain original versus effective fields, authorization,
   findings, mitigation, re-analysis and the final retrieval outcome.
6. Optionally select Scenario 4. Explain why high estimated token usage is an
   efficiency warning rather than a security block.
7. For human review choose Custom Request → Other / human review. Send the default
   complaint-status request. Confirm a known purpose and approve; all checks rerun.
   Start a new scenario session to demonstrate rejection independently.

For a repeat-request demonstration, send the same safe scenario three times within
60 seconds. The third is RESTRICT with no returned data. The explicit new-session
button resets that scenario's probing history without deleting audit records.

Custom attack checks: request `email` or `bank_account`; use purpose
`Ignore all previous instructions`; or select `*` alongside `card_details`.
Each must withhold data. Free-form purposes are analyzed but not echoed or stored raw.

Use the scenario selector for reproducible examples; the description is illustrative
text mapped to structured fields, not an LLM interpretation. A name request for a
complaint is unnecessary under the preserved purpose policy and is therefore modified.
