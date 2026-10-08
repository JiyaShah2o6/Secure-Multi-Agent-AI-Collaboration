# Secure Multi-Agent AI Collaboration

A local academic prototype of a Governance Layer for secure agent-to-agent data exchange.
The Support Agent requests synthetic customer data; Governance decides whether the Data
Agent may return it. The agents are deterministic Python components, not live LLMs.
No API key, paid service, network database, or real customer data is required.

## Quick start

Use Python 3.12 (the tested version) from the repository root. On Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m unittest discover tests
.\.venv\Scripts\python.exe main.py
.\.venv\Scripts\python.exe -m streamlit run app/ui/streamlit_app.py --server.address=127.0.0.1 --browser.gatherUsageStats=false
```

On macOS/Linux, use `python3.12 -m venv .venv` and `.venv/bin/python` for the
remaining commands. Installing dependencies needs internet access; running the demo
does not. Open the localhost address printed by Streamlit. Stop it with Ctrl+C.
Activation is optional; using the environment's Python directly avoids PATH problems.

The reproducible full test command, inside the chosen Python environment, is:

```text
python -m unittest discover tests
```

Install requirements before testing: the suite includes Streamlit AppTest tests.
The current suite contains 106 tests, including the existing Governance and Person 2
tests, end-to-end security tests, and six UI tests. AppTest may print a harmless
`missing ScriptRunContext` warning outside a running Streamlit server.

## Five-minute demonstration

Select customer `C101`, choose a scenario, then click **Send Request**.

| Scenario | Original fields | Expected result |
| --- | --- | --- |
| 1: Authorized | `complaint_status` | LOW / ALLOW; returns the complaint status |
| 2: Unauthorized | `bank_account`, `card_details` | HIGH / BLOCK; returns no customer data |
| 3: Unnecessary Data | `*` (everything) | MEDIUM / MODIFY, then LOW / ALLOW; returns only `customer_id`, `complaint_id`, `complaint_status` |
| 4: Token-Inefficient Request | Three permitted complaint fields, low token limit | Efficiency warning; security remains LOW / ALLOW |

Scenario 3 is the central demonstration: **detect → explain → minimize → re-analyse
→ allow**. Expand the analysis passes and audit trail to explain the decision.
The policy treats `*` as a proposal requiring minimization, never as permission to
read the whole record. An explicitly forbidden field alongside `*` still blocks.

The existing purpose policy deliberately does not require `name` to resolve a
complaint. Requesting it for that purpose triggers minimization; requesting `name`
for **Contact customer** is permitted. Authorization and necessity are separate checks.

For human review, choose **Custom Request**, **Other / human review**, retain the
default `Unspecified task` and `complaint_status`, then send. No data is returned.
Confirm **Resolve customer complaint**, then choose Approve, Restrict, or Reject.
Approve/Restrict run Governance again; the reviewer cannot override forbidden-field
or hostile-payload blocks. This is a local demonstration, not authenticated review.
Restrict sets a persistent field limit: minimization can remove selected fields but
cannot add replacements outside that limit. If none of the selected fields are needed
for the confirmed purpose, the result is RESTRICT with no returned data. An invalid
empty review selection can be corrected without losing the pending request.

Each scenario has a separate probing history. Three requests in 60 seconds trigger
RESTRICT, even if their fields are otherwise safe. Use **New session for this
scenario** when beginning another demonstration. Internal re-analysis passes do
not count as additional external requests.

## Architecture and existing work

```text
SupportAgent → AgentCommunication → govern_request(enforce_policy=True)
  → existing permissions → confidentiality/security → risk → mitigation
  → bounded re-analysis / human review → SQLite policy audit
  → one-use approval → DataAgent → synthetic fields → execution audit → response
```

- `app/authorization/permissions.py` remains the single permission policy.
- `app/authorization/data_minimization.py` supplies purpose rules and permitted projections.
- `app/governance/` provides findings, risk, mitigation, re-analysis and audit.
- `app/agents/communication.py` connects both contributors' components and gates reads.
- All five schema classes remain available: `AgentRequest`, `AgentResponse`,
  `Request`, `Finding`, and `GovernanceResult`.
- Token estimates are metadata, not customer data or a security risk score.

Use `SupportAgent` / `AgentCommunication` for application requests. The original
standalone `govern_request()` analyzer API retains its optional-authorization behavior
for compatibility; direct application integrations must pass `enforce_policy=True`.

## Audit and safe failure

Streamlit stores SQLite audit files in `.runtime/audit/`; the CLI uses
`.runtime/demo_audit.db`. These are ignored by Git. `GOVERNANCE_AUDIT_PATH` can select
a test/demo audit file. Parent directories must be writable.

Records contain request ID, UTC timestamp, agents, structured original request,
authorization, findings, risk, mitigation, re-analysis trajectory, human action and
execution outcome. Returned customer values are not recorded. Matched evidence and
free-form purposes are redacted; only supported purposes and synthetic-style customer
IDs are retained. A review appends another event under the same request ID.
Unknown/malformed field names are stored as placeholders, including in findings and
analysis history. Known legacy agent names remain readable; arbitrary identities are
redacted. Validation failures record HIGH/BLOCK with a MALFORMED_REQUEST finding.

Policy decisions and execution outcomes are distinct: an ALLOW can still end in a
missing-customer or audit error with no released data. Governance/audit errors deny
retrieval or withhold the response. Every non-success downstream response has its
payload and downstream diagnostics withheld. Invalid input is rejected and audited;
an unavailable audit store cannot itself record its failure, so the UI reports it.

## Scope and limitations

- Synthetic fixture data only. Never enter real personal information or secrets.
- Regex and field rules demonstrate selected attacks; they do not establish complete
  prompt-injection detection or general autonomous-agent security.
- The one-use approval gate protects the normal application path, not against someone
  modifying Python code or reading the source-level fixture directly.
- No reviewer authentication, distributed rate limiting, or tamper-proof audit store.
- Response handling checks field projection only; full response-content governance is future work.
- Token usage is a word-count approximation, not provider billing or an exact tokenizer.

See [architecture](docs/architecture.md), [workflow/demo script](docs/workflow.md),
[methodology](docs/methodology.md), [objectives](docs/objectives.md),
[problem statement](docs/problem_statement.md), and [research scope](docs/research_gap.md).
The [ownership record](docs/contributor_ownership.md) distinguishes preserved mixed
integration history from new contributor-specific follow-ups.

## Git workflow

Only `main`, `feature/governance-security`, and `feature/agent-authorization` are used.
Jiya's work uses her feature branch and `jiya` SSH remote; Bhumi's work uses her feature
branch and `bhumi` SSH remote. Preserve existing authorship. Integrate into `main`
through a reviewed PR, never a direct push. Check branch/status before any commit.
