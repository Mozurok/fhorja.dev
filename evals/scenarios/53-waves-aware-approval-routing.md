# Eval scenario 53: waves-aware approval routing

- **Tags**: ADR-0042, ADR-0041, routing, approve-plan, implement-fleet, handoff-contract
- **Last reviewed**: 2026-06-13
- **Status**: active

## Goal

Validates **ADR-0042** (waves-aware routing promotion) as enforced by `approve-plan` and `implement-approved-slice`. When the approved plan's `## Execution waves` section shows a remaining wave of size 2 or more whose slices declare `Scope` and `Depends-on`, the execution handoff must route to `implement-fleet`; when the plan is a chain, it must route to `implement-approved-slice`. This closes the gap where the fleet was unreachable from the routing graph and the operator had to ask for parallelism.

This exercises:

- The waves-aware routing rule stated verbatim in `commands/approve-plan.md` (Goal + Operating rules + Definition of done).
- The mirrored next-command edges in `WORKFLOW_OPERATING_SYSTEM.md` `## Command roles`, `wos/command-roles.md`, and `COMMAND_PROMPT_STUBS.md`.
- The terminal-safe routing in `commands/implement-approved-slice.md` (last slice routes to `where-we-at` or `task-close`).

## Setup

A task `projects/acme__widgets/active/2026-06-13_widget-dashboard/` with an `IMPLEMENTATION_PLAN.md` last touched by `implementation-plan`, no `[NEEDS CLARIFICATION:]` markers, not yet approved.

## Input prompt (turn 1: plan with a parallelizable first wave)

```text
Run @commands/approve-plan.md

Task folder: projects/acme__widgets/active/2026-06-13_widget-dashboard/

IMPLEMENTATION_PLAN.md slices (ready to lock):
- Slice 1 design-tokens.  Scope: src/theme/tokens.ts.            Depends-on: none
- Slice 2 data-layer.     Scope: src/data/widgets.ts.           Depends-on: none
- Slice 3 dashboard-ui.   Scope: src/features/dashboard/**.     Depends-on: 1, 2

## Execution waves
- Wave 1: [1, 2]
- Wave 2: [3]
Mode: Agent
```

## Input prompt (turn 2: pure chain)

```text
Run @commands/approve-plan.md

Task folder: projects/acme__widgets/active/2026-06-13_widget-dashboard/

IMPLEMENTATION_PLAN.md slices (ready to lock):
- Slice 1 schema.   Scope: prisma/schema.prisma.  Depends-on: none
- Slice 2 dal.      Scope: src/lib/dal.ts.         Depends-on: 1
- Slice 3 route.    Scope: src/app/route.ts.       Depends-on: 2

## Execution waves
- Wave 1: [1]
- Wave 2: [2]
- Wave 3: [3]
Mode: Agent
```

## Expected response shape (turn 1: parallelizable first wave)

- The plan is locked: a `## Approval log` entry is appended with date, slice count, and first slice id, and `TASK_STATE.md` is stamped APPROVED.
- The Handoff `Run now:` line is `implement-fleet` (not `implement-approved-slice`), because Wave 1 `[1, 2]` has size 2 and both slices declare `Scope` and `Depends-on`.
- The `TASK_STATE.md ## Recommended next step` matches: `Command: implement-fleet`.
- The reason names the parallelizable wave (Wave 1 has two file-disjoint slices).

## Expected response shape (turn 2: chain)

- The plan is locked the same way.
- The Handoff `Run now:` line is `implement-approved-slice` for Slice 1, because every wave has size one (the DAG is a chain).
- The response does not claim any parallelism.

## What a FAIL looks like

- The handoff routes to `implement-approved-slice` in turn 1 despite a width-2 first wave (the pre-ADR-0042 hard-coded behavior).
- The handoff routes to `implement-fleet` in turn 2 (a chain has nothing to parallelize).
- Approval is half-applied (Approval log without the TASK_STATE stamp, or vice versa).
