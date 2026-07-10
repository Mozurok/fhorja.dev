# Eval scenario 63: implement-approved-slice on-slice-close fleet handoff

- **Tags**: ADR-0042, routing, implement-approved-slice, what-next, implement-fleet, handoff-contract, careers-page-dogfooding
- **Last reviewed**: 2026-06-23
- **Status**: active

## Goal

Regression net for the careers-page dogfooding finding (2026-06-23): the ADR-0042 waves-aware
routing rule was present in `implement-approved-slice` and `approve-plan` since 2026-06-13, yet
in a real session the model closed Slice 1 and routed to sequential `implement-approved-slice`
for the next slice even though the remaining wave was parallelizable, never surfacing
`implement-fleet`. The operator had to ask for parallelism. Scenario 53 covers `approve-plan`'s
routing; this scenario covers the two surfaces 53 does not: `implement-approved-slice`'s
on-slice-close handoff and `what-next`.

This exercises:

- The REQUIRED `Next-wave decision:` line in `commands/implement-approved-slice.md` (the
  hardening that makes the waves handoff non-skippable).
- The waves-aware routing rule in `commands/what-next.md`.

## Setup

A task `projects/acme__widgets/active/2026-06-13_widget-dashboard/` with an approved
`IMPLEMENTATION_PLAN.md` whose slices declare `Scope` and `Depends-on`, an `## Execution waves`
section `Wave 1: [1]`, `Wave 2: [2, 3, 4]`. Slice 1 has just been implemented and its exit
criteria pass.

## Input prompt (turn 1: close Slice 1 via implement-approved-slice)

```text
Run @commands/implement-approved-slice.md

Task folder: projects/acme__widgets/active/2026-06-13_widget-dashboard/
Current slice: Slice 1 (route scaffold). Scope: src/app/layout.tsx. Depends-on: none.
The slice is implemented; build + lint pass.

## Execution waves
- Wave 1: [1]
- Wave 2: [2, 3, 4]   (Slice 2 Scope: src/features/a/**; Slice 3 Scope: src/features/b/**; Slice 4 Scope: src/features/c/**; each Depends-on: 1)
Mode: Agent
```

## Input prompt (turn 2: ask what-next on the same task after Slice 1 closed)

```text
Run @commands/what-next.md

Task folder: projects/acme__widgets/active/2026-06-13_widget-dashboard/
Slice 1 is closed. Remaining waves per the approved plan: Wave 2 [2, 3, 4], file-disjoint, each Depends-on 1.
```

## Expected response shape (turn 1: implement-approved-slice)

- The slice completion check confirms Slice 1's exit criteria.
- The output contains a `Next-wave decision:` line that reads `fleet` and names the parallelizable
  wave (e.g. "fleet because the next wave [Slice 2, Slice 3, Slice 4] has size 3 with Scope and
  Depends-on declared").
- The Handoff `Run now:` line is `implement-fleet` (not `implement-approved-slice` for Slice 2).

## Expected response shape (turn 2: what-next)

- The recommended next command is `implement-fleet`, justified by the width-3 ready wave.
- The response does not default to recommending `implement-approved-slice` for a single next slice.

## What a FAIL looks like

- Turn 1 omits the `Next-wave decision:` line (the pre-hardening behavior that let the careers-page
  session silently skip the fleet handoff).
- Turn 1 or turn 2 routes to `implement-approved-slice` for one sequential slice despite the
  width-3 ready wave (the exact careers-page miss).
- Turn 1 emits `Next-wave decision: sequential` or `terminal` when a parallelizable wave remains.
