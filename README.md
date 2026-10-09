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
.\.venv\Scripts\python.exe scripts/seed_database.py
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

To run the reproducible quantitative evaluation benchmark (42 structured scenarios, confusion matrix, and latency profile):

```text
python scripts/run_evaluation.py
```

Install requirements before testing: the suite includes Streamlit AppTest tests.
The test suite contains 161 automated tests, including the Phase 1 governance suite
(18 tests), Phase 2 database & repository suite (13 tests), Phase 3 UI suite (12 tests),
Phase 4 evaluation suite (2 tests covering 42 scenarios), Phase 4 E2E security suite (13 tests),
and existing Governance, Person 2, and regression tests. AppTest may print a harmless
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
complaint. Requesting only it for that purpose yields RESTRICT with no data; requesting `name`
for **Contact customer** is permitted. Authorization and necessity are separate checks.
Explicit requests can only lose fields during minimization: returned fields must also
be in the original request. Only wildcard proposals may expand into a permitted,
purpose-required projection; reviewer limits always remain binding.

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

## Governance Console & Theme Architecture

The user interface is structured as an enterprise security console with persistent top navigation across 7 functional destinations and built-in Light and Dark themes:

- **Theme Control**: Accessible in the top header via a single-click symbol toggle button (`🌙` in Light mode to switch to Dark; `☀️` in Dark mode to switch to Light). The theme toggle switches instantaneously without dropdown menus, page reloads, or unintended request submissions. The active theme preference persists across page navigation in session state and across browser refreshes via URL query parameters (`?theme=Light|Dark`).
- **Comprehensive Palette**:
  - *Light Mode*: Soft slate canvas (`#f8fafc`), clean white surfaces, dark charcoal headings, accessible status badges, and subtle borders.
  - *Dark Mode*: Deep slate/charcoal canvas (`#0b0f19`), elevated slate surfaces (`#1e293b`), off-white typography (`#f8fafc`), dark-mode table cards, and high-contrast status badges.
- **Top Navigation (7 Destinations)**:
  1. **Overview**: Live audit database statistics (total, allowed, blocked, human review), simplified architecture flow (`Agent A → Governance → Agent B`), recent governance activity log, and collapsible sequential pipeline technical details.
  2. **Request Console**: Structured workspace to formulate agent requests, inspect multi-pass analysis trajectories, risk scores, data minimization projections, and approved single-use token data retrieval.
  3. **Human Review**: Dedicated reviewer decision console displaying strictly decision-critical metadata (requested fields, sensitivity tiers, escalation findings, confirmed purpose, field scope) with confirmation safeguards before applying actions (Approve, Restrict, Modify, Reject).
  4. **Audit Trail**: Real-time audit log explorer with multi-criteria filtering (request ID search, decision, risk level) and masked sensitive values.
  5. **Confidentiality**: Field sensitivity categorization explorer (Internal, Confidential, Restricted, Unknown) grounded directly in the backend policy engine.
  6. **Security Analysis**: Interactive prompt security test bench evaluating input text against deterministic threat detectors (injection patterns, system prompt extraction, privilege escalations).
  7. **Token Monitor**: Token efficiency estimator and budget evaluator with optimization guidance, strictly isolated from security authorization logic.

## Architecture and existing work

```text
SupportAgent → AgentCommunication → govern_request(enforce_policy=True)
  → existing permissions → confidentiality/security → risk → mitigation
  → bounded re-analysis / human review → SQLite policy audit
  → one-use approval → DataAgent → CustomerRepository (parameterized SQL)
  → synthetic database fields → execution audit → response
```

- `app/authorization/permissions.py` remains the single permission policy.
- `app/authorization/data_minimization.py` supplies purpose rules and permitted projections.
- `app/governance/` provides findings, risk, mitigation, re-analysis and audit.
- `app/agents/communication.py` connects both contributors' components and gates reads.
- `app/data/customer_repository.py` provides the persistent SQL repository with foreign keys, indexes, parameterized SQL, and column allowlists.
- `app/data/seed.py` and `scripts/seed_database.py` provide deterministic, repeat-safe seeding for 100 synthetic customer records across `customers`, `complaints`, and `financial_records`.
- All five schema classes remain available: `AgentRequest`, `AgentResponse`,
  `Request`, `Finding`, and `GovernanceResult`.
- Token estimates are metadata, not customer data or a security risk score.

Use `SupportAgent` / `AgentCommunication` for application requests. The original
standalone `govern_request()` analyzer API retains its optional-authorization behavior
for compatibility; direct application integrations must pass `enforce_policy=True`.

## Repository layout

```text
Secure-Multi-Agent-AI-Collaboration/
├── app/
│   ├── agents/               # Simulated agent endpoints (SupportAgent, DataAgent, AgentCommunication)
│   ├── authorization/        # Single-source RBAC policy (permissions.py) and data minimization
│   ├── data/                 # SQLite repository, schema definitions, and synthetic data seeder
│   ├── governance/           # Decision engine, confidentiality, security rules, risk, and audit logger
│   ├── models/               # Shared dataclasses (AgentRequest, AgentResponse, Request, Finding, etc.)
│   └── ui/                   # Streamlit Governance Console (streamlit_app.py)
├── docs/                     # Architectural, research, methodology, and workflow documentation
├── scripts/                  # Seeder (seed_database.py) and evaluation benchmark (run_evaluation.py)
├── tests/                    # Unit, integration, security E2E, UI, and 42-scenario evaluation suites
├── main.py                   # Command-line multi-scenario demonstration runner
├── requirements.txt          # Python dependencies
└── README.md                 # Project guide and evaluation manual
```

## Governance decision semantics

The governance layer outputs one of five explicit decision outcomes:

- **ALLOW**: Low risk (`LOW`). The requesting agent is authorized for all requested fields, the fields are necessary for the stated purpose, and no security patterns are violated. Retrieval proceeds.
- **BLOCK**: High risk (`HIGH`). Triggered by unauthorized role fields, hostile prompt injection overrides, indirect exfiltration relays, SQL/path injection, or malformed input. Retrieval is denied; no protected data is accessed.
- **MODIFY**: Medium risk (`MEDIUM`). The request is authorized in principle but requests unnecessary fields or uses a wildcard proposal (`*`). The engine scopes the request down to the permitted, purpose-required subset and initiates re-analysis.
- **RESTRICT**: Medium risk (`MEDIUM`). The request has been minimized to an empty set (no permitted fields needed for the purpose), or repeated rapid probing exceeds the rate threshold (3 requests/60s). Retrieval is withheld.
- **HUMAN_REVIEW**: High risk (`HIGH`) or pending review. The stated purpose is uncatalogued or requires operational human supervisor approval. Customer data is withheld until an authorized reviewer approves, restricts, or rejects the request.

## Database architecture, audit, and safe failure

Customer data and audit records are strictly isolated into separate SQLite databases:
- **Customer database**: Stored at `.runtime/customers.db` (or configurable via `CUSTOMER_DB_PATH`). Consists of `customers`, `complaints` (with FK referencing `customers` and index), and `financial_records` (with FK referencing `customers` and index). `DataAgent` queries through `CustomerRepository` using parameterized SQL and column allowlists.
- **Audit database**: Stored in `.runtime/audit/` (Streamlit) or `.runtime/demo_audit.db` (CLI, or via `GOVERNANCE_AUDIT_PATH`). Manages append-only policy logs, execution events, and failure logs. Both files are excluded from Git. Parent directories must be writable.

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
