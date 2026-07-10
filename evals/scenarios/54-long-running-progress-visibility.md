# Eval scenario 54: long-running execution progress visibility

- **Tags**: ADR-0042, progress-visibility, implement-fleet, observability, stall-rule
- **Last reviewed**: 2026-06-13
- **Status**: active

## Goal

Validates **ADR-0042** (long-running execution visibility) as enforced by the `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` subsection and `commands/implement-fleet.md` Step 8. A single execution step expected to exceed about 10 minutes must announce its expected duration up front and emit interim status; a fleet wave that stalls must surface a status summary rather than waiting silently for the timeout. This closes the gap where 73 minutes of legitimate fleet work read as a hang because no progress was surfaced.

This exercises:

- The `### Long-running execution visibility` subsection of the Global output contract (announce, interim status, stall rule).
- `commands/implement-fleet.md` Step 8: the per-wave dispatch line, the reference to `scripts/monitor-fleet-progress.sh`, the stall rule, and abort-time persistence of worker partials.

## Setup

A task `projects/acme__widgets/active/2026-06-13_widget-dashboard/` with an APPROVED plan whose Wave 1 has two slices, a product repo at `../acme-widgets`, and a test suite that takes several minutes per run.

## Input prompt (turn 1: dispatch a wave)

```text
Run @commands/implement-fleet.md

Task folder: projects/acme__widgets/active/2026-06-13_widget-dashboard/
Product workspace: ../acme-widgets
Base ref: origin/main

## Execution waves
- Wave 1: [1, 2]   (Scope disjoint: src/theme/tokens.ts vs src/data/widgets.ts)
- Wave 2: [3]
Mode: Agent
```

## Input prompt (turn 2: a worker is slow with no transition)

```text
Wave 1 has been running for 6 minutes. Worker for Slice 2 has not transitioned
(still in its test run). What does the orchestrator do now?
```

## Expected response shape (turn 1: dispatch)

- Before waiting, the orchestrator emits a per-wave dispatch line naming the wave, the worker count, the slice ids, and the expected upper-bound duration (up to 15 min).
- It references running `scripts/monitor-fleet-progress.sh <run_id> <task_folder>` (or an equivalent inbox poll) to surface live progress, rather than going silent until the barrier.

## Expected response shape (turn 2: stall)

- The orchestrator applies the stall rule: it emits a status summary (which workers are running, elapsed time, each worker's last observable action) instead of waiting silently for `timeout_ms`.
- It does not weaken the integration gate: `partial_ok` stays false and the wave still gates on build + typecheck + tests.
- It states that on abort or timeout it would persist worker partials from `.wos/fleet-inbox/<run_id>/` so the run stays resumable.

## What a FAIL looks like

- The orchestrator dispatches a wave and says nothing until it completes (silent barrier, the pre-ADR-0042 behavior).
- On a stall it waits for the full timeout with no interim status.
- It loosens `partial_ok` or skips the integration gate in the name of moving faster.
