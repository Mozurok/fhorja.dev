# Scenario 40 -- Fleet Command ADR-0038 Compliance

## Purpose

Validate that any newly authored fleet command file satisfies the three structural rules locked by ADR-0038 (Sub-Agent Orchestration Contract). A fleet command is a multi-worker dispatch command (suffix `-fleet`) where an orchestrator spawns N parallel sub-agents and reconciles their outputs into substrate.

This scenario is the canonical lint contract for new fleet commands. It MUST be runnable against:

- Existing fleet commands (regression guard): `atom-audit-fleet`, `task-init-fleet`, `screen-spec-fleet`, `external-research-fleet`, `verify-against-rubric-fleet`
- Hypothetical new fleet commands (gate before merge): e.g. `eval-fleet`, `journey-map-fleet`, `pattern-doc-fleet`

## Coverage

### Case A: compliant new fleet command

- Given: an author drafts a new fleet command file under `_shared/commands/<name>-fleet.md`
- When: the file is reviewed against ADR-0038
- Then: the file MUST contain ALL of the following evidence:
  - **Rule 1 evidence (worker contract is structured):**
    - Explicit instruction string: "Worker MUST invoke StructuredOutput tool exactly once"
    - `worker_output_schema` block in frontmatter declaring the worker payload shape
    - Worker prompt explicitly forbids free-text final response
  - **Rule 2 evidence (orchestrator is sole substrate writer):**
    - Explicit instruction string: "Workers NEVER write substrate. The orchestrator is the SOLE writer."
    - A sequential "apply" step after worker fan-out where the orchestrator iterates worker payloads and writes substrate one-by-one
    - No `Write`, `Edit`, or `StructuredOutput` (mode=write/append) calls inside the worker prompt
  - **Rule 3 evidence (substrate orphan scan):**
    - A step labelled "Step X.5: scan substrate orphans" (X = the apply step number) that runs `scan-substrate-orphans.py` against every touched file
    - A rollback branch: if the scan exits non-zero, revert the most recent apply and emit NO_OP_TRACE describing which worker payload caused the orphan
    - NO_OP_TRACE format matches the ADR-0040 trace schema
  - **DoD bullet** in the command's Definition of Done: "scan-substrate-orphans.py exit code 0 on every touched file"
  - **Quality bar crosslink** in the command header references both:
    - `internal/docs/adr/0038-sub-agent-orchestration-contract.md`
    - `internal/wos/bug-classes/substrate-bullet-orphan.md`

### Case B: non-compliant fleet command

- Given: a fleet command file missing ANY of the five evidence items above
- When: `code-review` or the fleet-lint check runs
- Then: the command MUST be flagged as non-compliant with a specific finding citing the missing rule(s); merge MUST be blocked until remediated

## Pass criteria

1. The file contains the literal string "Worker MUST invoke StructuredOutput tool" (case-sensitive substring).
2. The frontmatter declares a `worker_output_schema` key with a non-empty value.
3. The file contains the literal string "Workers NEVER write substrate. The orchestrator is the SOLE writer."
4. The apply step is sequential (iterates worker payloads one-by-one) and lives only in the orchestrator section.
5. A step explicitly titled "scan substrate orphans" exists, invokes `scan-substrate-orphans.py`, and defines a rollback + NO_OP_TRACE branch.
6. The DoD section lists "scan-substrate-orphans.py exit code 0 on every touched file" as a bullet.
7. The command header crosslinks both ADR-0038 and `wos/bug-classes/substrate-bullet-orphan.md`.
8. Running the scenario against the existing fleet command set (5 commands listed in Purpose) yields zero findings (regression guard).

## Failure modes

- **F1 -- worker free-text drift:** Worker prompt allows or implies a natural-language final response instead of StructuredOutput, breaking Rule 1 and causing schema-less reconciliation.
- **F2 -- parallel substrate writes:** Workers are instructed (explicitly or implicitly) to call `Write` / `Edit` directly, breaking Rule 2 and producing race-condition orphans.
- **F3 -- orphan scan missing or advisory:** Scan step exists but is not gating (no rollback, no NO_OP_TRACE), so orphan bullets reach substrate undetected -- the exact failure ADR-0038 was created to prevent.
- **F4 -- crosslinks missing:** Command lacks ADR-0038 or `substrate-bullet-orphan.md` references, so future authors copying the file lose the contract trail.

## References

- `internal/docs/adr/0038-sub-agent-orchestration-contract.md` -- the three rules being validated
- `internal/docs/adr/0040-no-op-trace-schema.md` -- NO_OP_TRACE format for the Rule 3 rollback branch
- `internal/wos/sub-agent-orchestration.md` -- canonical sub-agent dispatch pattern
- `internal/wos/bug-classes/substrate-bullet-orphan.md` -- the bug class this scenario guards against
