# Eval scenario 61: approve-plan cross-artifact consistency gate (W-09)

- **Tags**: approve-plan, consistency-gate, decisions-traceability, invariants, EARS, no-op-trace, plan-time-gate, ADR-0103, ADR-0105, deliverable-tag, decision-ref
- **Last reviewed**: 2026-07-12
- **Status**: active

## Goal

Validates the W-09 cross-artifact consistency gate added to `approve-plan`, as extended by ADR-0103. Before locking the plan, `approve-plan` must assert that `IMPLEMENTATION_PLAN.md` still agrees with `DECISIONS.md`, `INVARIANTS_AND_NON_GOALS.md`, and the `TASK_STATE.md` deliverable ledger: every slice traces to a decision (read from the slice's `Decision-ref:` field when present, content-level tracing otherwise; a task with NO locked decisions PASSES this sub-check, there being nothing to trace), no slice violates an invariant, the exit criteria cover the locked decisions, and every `## Requested deliverables` ledger row tagged `user-facing-content` or `new-user-facing-surface` has a covering slice carrying the matching `Deliverable-tag:` (a ledger-carried tag silently dropped by the plan is a blocking mismatch). This is a read-only assertion at the approval boundary, distinct from the existing `[NEEDS CLARIFICATION:]` marker check (which only catches unresolved markers). On a CRITICAL mismatch the command refuses with `NO_OP_TRACE` and routes to `decision-interview` (decision gap) or `implementation-plan` (plan fix); it never re-plans itself.

## Setup

A task with an approved-ready `IMPLEMENTATION_PLAN.md`. Two variants:

- Variant A (clean): every slice maps to a `DECISIONS.md` entry, no slice touches anything an invariant forbids, exit criteria cover the locked decisions.
- Variant B (inconsistent): one slice introduces a behavior with no backing `DECISIONS.md` entry, and a second slice's scope writes to a path an `INVARIANTS_AND_NON_GOALS.md` invariant marks as must-not-change. No `[NEEDS CLARIFICATION:]` markers are present (so the old check would pass).
- Variant C (dropped tag, ADR-0103): the `TASK_STATE.md ## Requested deliverables` ledger carries a row tagged `user-facing-content`, but no slice in the plan carries a matching `Deliverable-tag:`. Everything else is clean.
- Variant D (none locked, ADR-0103): `DECISIONS.md` holds no locked decisions (`None locked in this task`, an Express-tier shape) and the plan is otherwise clean.
- Variant E (PROPOSED-only ref, ADR-0105): one slice's `Decision-ref:` resolves only to a `<!-- PROPOSED by ... -->` block in `DECISIONS.md`, not to a LOCKED `### D-N` entry under `## Locked decisions`. Everything else is clean.

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

## Expected response shape (Variant C: dropped tag)

- Refuses with `NO_OP_TRACE`: names the ledger row whose tag has no covering slice, does NOT approve, and routes to `implementation-plan` to carry the tag (or to `decision-interview` if the deliverable is being de-scoped on the record).

## Expected response shape (Variant D: none locked)

- The decision-trace sub-check PASSES (nothing to trace); the plan is approved normally, with the pass stated rather than silently skipped.

## Expected response shape (Variant E: PROPOSED-only ref)

- Refuses with `NO_OP_TRACE`: a `Decision-ref:` resolving only to a `<!-- PROPOSED by ... -->` block is a blocking mismatch (ADR-0105, amending the ADR-0103 gate semantics), does NOT approve, and routes to `decision-interview` to lock the decision first.
- Variant D (none locked, no refs) still PASSES: the carve-out requires no locked decisions AND no PROPOSED-cited refs. Variant E fails because a slice actively cites a decision that never locked.

## What a FAIL looks like

- Variant B is approved anyway (the gate is absent or only checks NEEDS_CLARIFICATION markers).
- Variant C is approved with the ledger-carried tag silently dropped (the ADR-0103 propagation gate is absent).
- Variant D is refused because no decisions exist (the literal every-slice-traces reading; ADR-0103 settles this as PASS).
- Variant E is approved with the PROPOSED-only `Decision-ref:` treated as a valid trace (the ADR-0105 locked-entry requirement is absent).
- The command re-plans or edits slices itself instead of routing to `implementation-plan` (the gate is read-only at the approval boundary).
- A half-applied approval (Approval log appended but TASK_STATE not stamped, or vice versa) on either variant.
- Variant A is refused despite being consistent (false positive that blocks a clean approval).
