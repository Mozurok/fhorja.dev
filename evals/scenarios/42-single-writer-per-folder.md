# Eval scenario 42: Single-writer-per-folder enforcement in fleet dispatch

- **Tags**: ADR-0040, ADR-0038, fleet-dispatch, sub-agent-orchestration, scope-disjointness, single-writer
- **Last reviewed**: 2026-06-05
- **Status**: active

## Goal

Validates **ADR-0040** (the single-writer-per-folder amendment to ADR-0038) as enforced by fleet-dispatch commands and the orchestrator's Step 2 scope-disjointness check. The original ADR-0038 Rule 2 required sequential apply for any shared write surface; ADR-0040 amends this so that parallel workers may proceed concurrently **iff** each is the unique writer of its assigned task folder. The orchestrator must prove disjointness before dispatch, and must block any dispatch where two workers would write the same path.

This exercises:

- The Step 2 (scope-disjointness validation) gate in `wos/sub-agent-orchestration.md`.
- The fleet-folder assignment contract in `commands/task-init-fleet.md`.
- The ADR-0040 equivalence claim: single-writer-per-folder is observationally equivalent to sequential apply for Rule 2.

## Setup

A bootstrapped project `projects/acme__widget-pricing/` with an empty `active/` directory. No conflicting task folders pre-exist.

## Input prompt (turn 1: happy-path fleet dispatch)

```text
Run @commands/task-init-fleet.md

Project: acme__widget-pricing
Workers: 3
Task slugs:
  - 2026-06-05_price-query-handler
  - 2026-06-05_price-cache-layer
  - 2026-06-05_price-audit-log
Mode: Ask
```

## Input prompt (turn 2: misconfigured dispatch with scope overlap)

```text
Run @commands/task-init-fleet.md

Project: acme__widget-pricing
Workers: 2
Task slugs:
  - 2026-06-05_price-query-handler
  - 2026-06-05_price-query-handler
Mode: Ask
```

## Expected response shape (turn 1: happy-path)

- Orchestrator runs Step 2 explicitly and logs the per-worker folder assignment table: each worker is bound to a unique `projects/acme__widget-pricing/active/2026-06-05_*/` path.
- Step 2 output explicitly cites ADR-0040 by name and states the disjointness conclusion (e.g. "3 of 3 worker folders unique; ADR-0040 single-writer condition satisfied; Rule 2 holds via amendment").
- Parallel dispatch proceeds; each worker proposes its own 5-file task layer scoped to its own folder. No worker proposes a write outside its assigned folder.
- The orchestrator's final response includes a per-worker artifact-changes summary, all PROPOSED, no PATH appearing under two workers.

## Expected response shape (turn 2: scope-overlap)

- Step 2 detects that two workers are assigned the same target folder.
- Dispatch is **BLOCKED** before any worker is invoked. The response includes an explicit BLOCK reason naming "scope-overlap detected" and pointing at the duplicated folder path.
- The orchestrator cites ADR-0040 and ADR-0038 Rule 2 by name as the basis for the block.
- The response proposes a remediation (e.g. rename one task slug, drop the duplicate, or fall back to sequential apply).
- No task-folder files are created in turn 2.

## Pass criteria

1. **Turn 1 -- Step 2 cited**: Response shows the orchestrator ran Step 2 scope-disjointness validation explicitly, not implicitly.
2. **Turn 1 -- per-worker folder table**: Output lists each worker with its assigned `projects/<client>__<project>/active/<slug>/` path; all paths are unique.
3. **Turn 1 -- ADR-0040 named**: Step 2 output cites ADR-0040 by identifier and states the single-writer-per-folder conclusion that satisfies Rule 2.
4. **Turn 1 -- parallel dispatch proceeds**: All 3 workers are dispatched in parallel; no fallback to sequential apply; no scope leakage across workers.
5. **Turn 2 -- block before dispatch**: When two workers share a folder, dispatch is BLOCKED at Step 2; no worker is invoked; no task-folder files are proposed.
6. **Turn 2 -- explicit block reason**: BLOCK message includes the literal phrase "scope-overlap detected" (or close equivalent) and names the duplicated folder path.
7. **Turn 2 -- ADR citations**: BLOCK message references both ADR-0040 (the amendment) and ADR-0038 Rule 2 (the underlying invariant) by identifier.
8. **Turn 2 -- remediation proposed**: BLOCK message suggests at least one concrete next step (rename slug, drop duplicate, or sequential apply) rather than silently failing.

## Failure modes to watch

- **Silent parallel dispatch with shared folder**: Step 2 is skipped or returns OK despite overlapping paths; two workers race to write the same task folder. This is a direct ADR-0040 / ADR-0038 Rule 2 violation.
- **False overlap block in turn 1**: Step 2 blocks the happy-path even though all three folders are unique, often because the disjointness check compares slugs as substrings rather than as full normalized paths.
- **ADR not cited**: Step 2 enforces disjointness in turn 1 or blocks in turn 2 but does not name ADR-0040 (or ADR-0038), making the reasoning unauditable and the amendment chain invisible to reviewers.
- **Fallback to sequential apply instead of block**: On detected overlap, the orchestrator quietly downgrades to sequential apply instead of surfacing the misconfiguration to the user. This hides the bug and burns budget on a dispatch the user did not intend.

## References

- `internal/docs/adr/0040-single-writer-per-folder-amendment.md` (the amendment under test)
- `internal/docs/adr/0038-parallel-sub-agent-rules.md` (Rule 2 invariant being amended)
- `internal/wos/sub-agent-orchestration.md` (Step 2 scope-disjointness validation gate)
- `internal/commands/task-init-fleet.md` (fleet-folder assignment contract)
