# Post-PR3 ownership and completion

PRs #1, #2 and #3 are merged historical work. Commits b352edf, c22247b,
a1d026a, c319fc2 and 75278ed remain unchanged, including their existing authors.
File ownership below describes responsibility, not a claim that the historical
integration commits were authored separately by both contributors.

| Work | Existing status / location | Owner | Forward work and branch |
| --- | --- | --- | --- |
| Agents, records, permissions, token estimates | Completed in PR3; main and agent branch | Bhumi | Preserve; agent fixes on feature/agent-authorization |
| Original confidentiality/security/risk/mitigation/audit | Completed in PR2; main | Jiya | Security fixes on feature/governance-security |
| Purpose minimization helper | PR3 rules plus post-PR3 integration on governance branch | Bhumi | Correct reviewer bounds on agent branch |
| Governed transport and one-use reads | Existing post-PR3 integrated history on governance branch | Shared | Preserve history; contributor-specific follow-ups |
| Audit sanitization and rejected-request event API | Incomplete baseline | Jiya | Governance branch; security regression tests |
| Non-success response security boundary | Incomplete baseline | Jiya | Governance branch; withhold payloads and diagnostics |
| Human review and validation-to-audit wiring | Incomplete baseline | Bhumi | Agent branch; review/UI/authorization tests |
| Demo, integration tests and setup/research docs | Existing post-PR3 integrated history | Shared | Preserve and update transparently with actual follow-up authors |

Integration order: PR the existing integrated baseline plus Jiya's security fixes
into main; bring that merged dependency into Bhumi's existing branch without
recreating commits; PR Bhumi's new agent/review corrections into main. Each milestone
runs the complete suite and pushes with its contributor's SSH remote. No historical
commit is split, rebased, reauthored or cherry-picked for contribution appearance.

Review scope is an upper bound, not permission to add replacement fields. Error
responses must carry no customer payload or downstream diagnostics. Audit records
must preserve security decisions without persisting arbitrary malformed input.

## Implemented follow-ups

- Jiya: 3916577 adds response-boundary confidentiality, audit sanitization, the
  validation-rejection audit API, and four security regression tests. PR #4 merged
  it alongside the preserved integrated history.
- Bhumi: reviewer fields now bound minimization and the authorization callback on
  every pass, including a later review attempt. Agent validation calls Jiya's audit
  API. The UI preserves pending review after invalid selections and displays the
  field limit. Seven authorization/review tests and two UI tests cover these cases.
- The small `field_scope` argument passed through Governance orchestration is shared
  interface wiring needed by Bhumi's minimization fix; the Governance policy engine
  and historical commits are not replaced.

Validation baseline grew from 93 to 106 tests: four Jiya security tests plus nine
Bhumi authorization/UI tests. All original test cases and assertions remain present.
