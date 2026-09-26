# Scenario 40 -- Fleet Command ADR-0038 Compliance

## Purpose

Validate that any newly authored fleet command file satisfies the three structural rules locked by ADR-0038 with the carrier amendment in ADR-0158. A fleet command is a multi-worker dispatch command (suffix `-fleet`) where an orchestrator spawns N parallel sub-agents and reconciles their outputs into substrate.

This scenario is the canonical lint contract for new fleet commands. It MUST be runnable against:

- Existing fleet commands (the carrier regression cases below): `atom-audit-fleet`, `task-init-fleet`, `screen-spec-fleet`, `external-research-fleet`, `verify-against-rubric-fleet`, `feature-library-scout-fleet`, `implement-fleet`
- Hypothetical new fleet commands (gate before merge): e.g. `eval-fleet`, `journey-map-fleet`, `pattern-doc-fleet`

## Coverage

### Case A: compliant new fleet command

- Given: an author drafts a new fleet command file under `commands/<name>-fleet.md`
- When: the file is reviewed against ADR-0038 and ADR-0158
- Then: the file MUST contain ALL of the following evidence:
  - **Rule 1 evidence (worker contract is structured):**
    - Explicit selected carrier: a typed runtime result on the dynamic-workflow path, or the worker-written assigned run-inbox JSON file on the Agent path; no worker-side tool mandate
    - `worker_output_schema` block in frontmatter declaring the worker payload shape
    - Worker prompt explicitly forbids free-text final response
  - **Rule 2 evidence (orchestrator is sole substrate writer):**
    - The orchestrator alone writes shared merge targets; the native return-file exception and existing command-specific disjoint output grants are explicit
    - A sequential "apply" step after worker fan-out where the orchestrator iterates worker payloads and writes substrate one-by-one
    - No worker writes outside its assigned native return file and the command's pre-existing disjoint output grants
  - **Rule 3 evidence (substrate orphan scan):**
    - A step labelled "Step X.5: scan substrate orphans" (X = the apply step number) that runs `scan-substrate-orphans.py` against every touched file
    - A rollback branch: if the scan exits non-zero, revert the most recent apply and emit NO_OP_TRACE describing which worker payload caused the orphan
    - NO_OP_TRACE describes the apply failure under the global output contract
  - **DoD bullet** in the command's Definition of Done: "scan-substrate-orphans.py exit code 0 on every touched file"
  - **Quality bar crosslink** in the command header references both:
    - `docs/adr/0038-workflow-tool-as-parallel-orchestration-primitive.md`
    - `wos/bug-classes/substrate-bullet-orphan.md`

### Case B: non-compliant fleet command

- Given: a fleet command file missing ANY of the five evidence items above
- When: `review-hard` or the applicable structural check runs
- Then: the command MUST be flagged as non-compliant with a specific finding citing the missing rule(s); merge MUST be blocked until remediated

## Carrier regression cases

- Native valid: the worker writes schema-conforming JSON to its assigned absolute run-inbox
  path, with no StructuredOutput call. Its payload is accepted under the existing status policy.
- Dynamic valid: the runtime supplies the declared typed payload; the worker prompt never
  requests that tool. An orchestrator-owned replay copy does not add another worker result.
- Missing or invalid: prose, absent JSON, malformed JSON and a payload at another worker or
  run destination cannot replace the expected result; existing failure classifications apply.
- Screen replay: validate the selected result before the orchestrator creates the
  .partial.json copy; merge only that expected worker's copy, once.
- Worktree boundary: the assigned return path is the orchestrator task inbox, not an
  unannounced file in the implementation worktree. Other out-of-scope writes remain violations.
- Rubric isolation: artifact ID, schema and delivery metadata are permitted; author reasoning,
  task memory and sibling artifacts are absent.

## Pass criteria

1. A valid payload through either declared carrier satisfies Rule 1 without a worker-side tool call. Prose, absent, malformed and wrong-destination payloads cannot satisfy it.
2. The frontmatter declares a `worker_output_schema` key with a non-empty value.
3. Shared merge targets remain orchestrator-owned. Native workers may write only the assigned return file in addition to pre-existing command-specific task-folder, spec or worktree outputs.
4. The apply step is sequential (iterates worker payloads one-by-one) and lives only in the orchestrator section.
5. A step explicitly titled "scan substrate orphans" exists, invokes `scan-substrate-orphans.py`, and defines a rollback + NO_OP_TRACE branch.
6. The DoD section lists "scan-substrate-orphans.py exit code 0 on every touched file" as a bullet.
7. The command header crosslinks both ADR-0038 and `wos/bug-classes/substrate-bullet-orphan.md`.
8. Running the carrier regression cases against the seven commands listed in Purpose yields zero carrier or return-permission findings. The broader new-command checks above do not assert that every legacy command already satisfies every orphan-scan requirement: implement-fleet lacks that gate, and feature-library-scout-fleet's Step 12 lacks the prescribed rollback. Those existing gaps remain outside this carrier correction.

## Failure modes

- **F1 -- worker free-text drift:** Worker prompt allows or implies a natural-language final response in place of the declared typed payload, breaking Rule 1 and causing schema-less reconciliation.
- **F2 -- parallel substrate writes:** Workers write shared merge targets or exceed the explicit return-file and disjoint-output grants, breaking Rule 2. The assigned native JSON write is permitted.
- **F3 -- orphan scan missing or advisory:** Scan step exists but is not gating (no rollback, no NO_OP_TRACE), so orphan bullets reach substrate undetected -- the exact failure ADR-0038 was created to prevent.
- **F4 -- crosslinks missing:** Command lacks ADR-0038 or `substrate-bullet-orphan.md` references, so future authors copying the file lose the contract trail.

## References

- `docs/adr/0038-workflow-tool-as-parallel-orchestration-primitive.md` -- the three rules being validated
- `WORKFLOW_OPERATING_SYSTEM.md` -- global output contract and NO_OP_TRACE
- `docs/adr/0158-the-fleet-return-transport-is-the-file.md` -- typed runtime and native JSON carriers
- `wos/sub-agent-orchestration.md` -- canonical sub-agent dispatch pattern
- `wos/bug-classes/substrate-bullet-orphan.md` -- the bug class this scenario guards against
