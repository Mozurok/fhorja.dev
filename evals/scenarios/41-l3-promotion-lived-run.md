# Scenario 41 -- L3 Promotion Lived-Run Gate

## Intent

Validate the lived-run acceptance gate that fleet commands must clear in order to be promoted to L3 on the maturity ladder. Static audit (ADR-0038 Rules 1/2/3) is necessary but not sufficient; a single real-project execution must demonstrate that the contract holds at runtime, not just in source.

## Setup

- A fleet command exists under `commands/_fleet/` (e.g. `atom-audit-fleet`, `external-research-fleet`, `screen-spec-fleet`, `verify-against-rubric-fleet`, `task-init-fleet`).
- Static ADR-0038 audit has been executed and reports Rule 1 = PASS, Rule 2 = PASS, Rule 3 = PASS for the command.
- A real project is selected with sufficient parallel scope:
  - `atom-audit-fleet`: project surface contains atoms >= 6.
  - `external-research-fleet`: research brief lists distinct angles >= 3.
  - `screen-spec-fleet`: design handoff exposes screens >= 3.
  - `verify-against-rubric-fleet`: rubric items >= 4.
  - `task-init-fleet`: target repos >= 2.
- `scan-substrate-orphans.py` is available and the workspace is clean (no unrelated drift).
- `VERIFICATION_LOG.jsonl` is writable at the canonical path.

## Procedure

1. Invoke the fleet command in a fresh chat against the chosen project.
2. Observe the orchestrator turn: it MUST emit a `StructuredOutput` tool call describing the worker dispatch plan (one entry per parallel unit), not a free-text plan.
3. Allow the workers to run to completion. Confirm the orchestrator applies worker outputs sequentially in a single follow-up turn (no overlapping writes, no parallel apply).
4. On every file the orchestrator touched during the apply step, run `scan-substrate-orphans.py` and capture exit codes.
5. Open `VERIFICATION_LOG.jsonl` and confirm a fleet-merge event was appended for this run with `command`, `run_id`, `worker_count`, and `outcome` fields populated.
6. Cross-check the maturity-ladder entry for this command and confirm the lived-run evidence is recorded (run id + date) before promotion to L3.

## Pass Criteria

1. The orchestrator's dispatch turn uses `StructuredOutput` (not prose) and lists exactly the expected number of workers for the project's scope (ADR-0038 Rule 1, lived).
2. Workers execute in parallel (visible in the run trace) but the orchestrator's apply step is a single sequential turn (ADR-0038 Rule 2, lived).
3. `scan-substrate-orphans.py` exits 0 on every file touched during apply; no orphaned substrate is produced (ADR-0038 Rule 3, lived).
4. `VERIFICATION_LOG.jsonl` contains a new fleet-merge entry whose `command` matches the invocation and whose `outcome` is `success`.
5. No worker output is silently dropped: the apply turn references every dispatched worker, either merging its output or recording an explicit skip reason.
6. The maturity-ladder file (`wos/maturity-ladder.md`) is updated in the same session to cite this run as the L3 promotion evidence.
7. No retries, manual re-prompts, or out-of-band fixes were required to reach a clean state.
8. The command is now eligible for L3 promotion per ADR-0036 Path B (static audit + one lived run + clean scan).

## Failure Modes

- Orchestrator dispatches workers via prose instead of `StructuredOutput`: Rule 1 fails lived even if static audit passed; block promotion and file a regression.
- Apply step interleaves worker outputs across multiple turns or shows write conflicts: Rule 2 fails lived; demote to L2 and require contract fix.
- `scan-substrate-orphans.py` exits non-zero on any touched file: Rule 3 fails lived; do not write the `VERIFICATION_LOG.jsonl` success entry and revert the merge.
- `VERIFICATION_LOG.jsonl` entry is missing, malformed, or references a different command/run: treat as audit-trail failure and re-run before considering promotion.

## References

- ADR-0036 -- Maturity ladder + Path B promotion criteria.
- ADR-0038 -- Fleet command contract: Rule 1 (StructuredOutput dispatch), Rule 2 (sequential apply), Rule 3 (no orphaned substrate).
- `wos/maturity-ladder.md` -- canonical record of L0..L3 status per command and the evidence cited for each promotion.
