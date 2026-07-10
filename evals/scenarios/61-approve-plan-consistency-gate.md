# Eval scenario 61: approve-plan cross-artifact consistency gate (W-09)

- **Tags**: approve-plan, consistency-gate, decisions-traceability, invariants, EARS, no-op-trace, plan-time-gate
- **Last reviewed**: 2026-06-22
- **Status**: active

## Goal

Validates the W-09 cross-artifact consistency gate added to `approve-plan`. Before locking the plan, `approve-plan` must assert that `IMPLEMENTATION_PLAN.md` still agrees with `DECISIONS.md` and `INVARIANTS_AND_NON_GOALS.md`: every slice traces to a decision, no slice violates an invariant, and the exit criteria cover the locked decisions. This is a read-only assertion at the approval boundary, distinct from the existing `[NEEDS CLARIFICATION:]` marker check (which only catches unresolved markers). On a CRITICAL mismatch the command refuses with `NO_OP_TRACE` and routes to `decision-interview` (decision gap) or `implementation-plan` (plan fix); it never re-plans itself.

## Setup

A task with an approved-ready `IMPLEMENTATION_PLAN.md`. Two variants:

- Variant A (clean): every slice maps to a `DECISIONS.md` entry, no slice touches anything an invariant forbids, exit criteria cover the locked decisions.
- Variant B (inconsistent): one slice introduces a behavior with no backing `DECISIONS.md` entry, and a second slice's scope writes to a path an `INVARIANTS_AND_NON_GOALS.md` invariant marks as must-not-change. No `[NEEDS CLARIFICATION:]` markers are present (so the old check would pass).

## Input prompt (both variants)

```text
Run @commands/approve-plan.md
Task folder: projects/acme__svc/active/2026-06-22_feature-x/
Mode: Agent
```

## Expected response shape (Variant A: clean)

- Runs the consistency check and confirms it passed (slices trace to decisions, no invariant violated, exit criteria cover the locked decisions) in addition to confirming no `[NEEDS CLARIFICATION:]` markers.
- Appends the `## Approval log` entry and stamps TASK_STATE.md `plan APPROVED`.
- Routes the Handoff waves-aware (implement-fleet for a parallelizable first wave, else implement-approved-slice).

## Expected response shape (Variant B: inconsistent)

- Refuses with `NO_OP_TRACE`: does NOT append an Approval log entry and does NOT stamp `plan APPROVED`.
- Names the two specific mismatches (the untraceable slice; the invariant-violating scope) with the slice ids.
- Routes to `decision-interview` for the missing decision and `implementation-plan` for the invariant-violating slice, not to an execution command.
- Distinguishes this from a NEEDS_CLARIFICATION refusal (no markers were present; the gate is traceability, not unresolved markers).

## What a FAIL looks like

- Variant B is approved anyway (the gate is absent or only checks NEEDS_CLARIFICATION markers).
- The command re-plans or edits slices itself instead of routing to `implementation-plan` (the gate is read-only at the approval boundary).
- A half-applied approval (Approval log appended but TASK_STATE not stamped, or vice versa) on either variant.
- Variant A is refused despite being consistent (false positive that blocks a clean approval).
