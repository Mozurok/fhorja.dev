# Eval scenario 61: approve-plan cross-artifact consistency gate (W-09)

- **Tags**: approve-plan, consistency-gate, decisions-traceability, invariants, EARS, no-op-trace, plan-time-gate, ADR-0103, ADR-0105, ADR-0208, ADR-0225, ADR-0233, deliverable-tag, decision-ref
- **Last reviewed**: 2026-09-24
- **Status**: active

## Goal

Validates the W-09 cross-artifact consistency gate added to `approve-plan`, as extended by ADR-0103. Before locking the plan, `approve-plan` must assert that `IMPLEMENTATION_PLAN.md` still agrees with `DECISIONS.md`, `INVARIANTS_AND_NON_GOALS.md`, and the `TASK_STATE.md` deliverable ledger: every slice traces to a decision (read from the slice's `Decision-ref:` field when present, content-level tracing otherwise; a task with NO locked decisions PASSES this sub-check, there being nothing to trace), no slice violates an invariant, the exit criteria cover the locked decisions, and every `## Requested deliverables` ledger row tagged `user-facing-content` or `new-user-facing-surface` has a covering slice carrying the matching `Deliverable-tag:` (a ledger-carried tag silently dropped by the plan is a blocking mismatch). This is a read-only assertion at the approval boundary, distinct from the existing `[NEEDS CLARIFICATION:]` marker check (which only catches unresolved markers). On a CRITICAL mismatch the command refuses with `NO_OP_TRACE` and routes to `decision-interview` (decision gap) or `implementation-plan` (plan fix); it never re-plans itself.

## Setup

A task with an approved-ready `IMPLEMENTATION_PLAN.md`. Two variants:

- Variant A (clean): every slice maps to a `DECISIONS.md` entry, no slice touches anything an invariant forbids, exit criteria cover the locked decisions.
- Variant B (inconsistent): one slice introduces a behavior with no backing `DECISIONS.md` entry, and a second slice's scope writes to a path an `INVARIANTS_AND_NON_GOALS.md` invariant marks as must-not-change. No `[NEEDS CLARIFICATION:]` markers are present (so the old check would pass).
- Variant C (dropped tag, ADR-0103): the `TASK_STATE.md ## Requested deliverables` ledger carries a row tagged `user-facing-content`, but no slice in the plan carries a matching `Deliverable-tag:`. Everything else is clean.
- Variant D (none locked, ADR-0103): `DECISIONS.md` holds no locked decisions (`None locked in this task`, the shape of a task with no escalation) and the plan is otherwise clean.
- Variant E (PROPOSED-only ref, ADR-0105): one slice's `Decision-ref:` resolves only to a `<!-- PROPOSED by ... -->` block in `DECISIONS.md`, not to a LOCKED `### D-N` entry under `## Locked decisions`. Everything else is clean.
- Variant F (Express attended, ADR-0208): `TASK_STATE.md ## Recommended pipeline` records `Escalations: none` (the default path; ADR-0207 retired the `Express` label and kept the rule), the run is Agent and attended. The command under test is `implementation-plan`. Until 2026-09-16 this variant tested the ADR-0159 mechanism, in which `implementation-plan` ran the consistency gate itself, wrote the Approval log inline and handed straight to `implement-approved-slice`. ADR-0208 removed that: approval no longer takes a human turn, so the inline log had no remaining purpose, and every plan now hands to `approve-plan`. The variant now guards against that mechanism returning. It is not the one-slice route (ADR-0225): there `task-init` writes the only plan and its approval line, and `implementation-plan` never runs. Whenever `implementation-plan` does run, including on a plan written after the route ended, what this variant asserts holds. The consistency fail cases (dropped tag, PROPOSED-only ref) are `approve-plan`'s and stay with Variants C and E.
- Variant G (rests on provisional, ADR-0233): one slice's `Decision-ref:` reads `rests on provisional P-1`, and `DECISIONS.md ## Provisional decisions` carries a matching `### P-1` with `Evidence:`, `Impact: normal`, and `Status: provisional`. Everything else is clean and the run is an attended chain on a task branch. This is NOT Variant E: the ref traces to a real provisional entry, not to nothing, so the consistency check passes it, but only labeled.
- Variant H (ESCALATED, attended chain, ADR-0233): the blinded review returns `failed` on one slice for a product commitment the locked decisions do not authorize (the same shape that hand-back to the maintainer in an unattended or non-task-branch run), and the run is attended on a task branch. The commitment is a normal-impact product choice, not one touching data, security, payments, or cost.

## Input prompt (both variants)

```text
Run @commands/approve-plan.md
Task folder: projects/acme__svc/active/2026-06-22_feature-x/
Mode: Agent
```

## Expected response shape (Variant A: clean)

- Runs the consistency check and confirms it passed (slices trace to decisions, no invariant violated, exit criteria cover the locked decisions) in addition to confirming no `[NEEDS CLARIFICATION:]` markers.
- Appends the `## Approval log` entry and stamps TASK_STATE.md `plan APPROVED`.
- Routes the Handoff waves-aware (implement-fleet for a parallelizable wave, else implement-approved-slice).

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

## Expected response shape (Variant G: rests on provisional)

- Runs the consistency check and confirms the P-1-backed slice traces LABELED, not as authorized: the response states plainly that `## Locked decisions` stayed the only authorization and this slice rests on a provisional entry instead.
- Checks P-1's own `Evidence:` line against the task branch (or the request) and confirms it resolves and supports the pick; a `Decision-ref:` naming a P-N whose evidence does not resolve, or whose `Impact:` reads `normal` on a choice touching data, security, payments, or cost, is not a refusal: the blinded review returns `needs_revision`, `approve-plan` does not approve, and the Handoff routes back to `implementation-plan` to fix the plan, after which `approve-plan` runs again (`commands/approve-plan.md`, the provisional-decisions rubric and the `needs_revision` iteration rule).
- Appends the Approval log entry with `Rests on provisional: P-1`, and the same entry names 0 for any decision this run cannot verify.
- Routes the Handoff waves-aware, the same as Variant A: a provisional entry does not add a review round beyond the one already dispatched.

## Expected response shape (Variant H: ESCALATED, attended chain)

- Records the ESCALATED exit exactly as an unattended run would (names the slice, the commitment, and the decision that does not cover it), but does NOT hand back to the maintainer as the terminal stop.
- The Handoff is `Run now: decision-interview`, `Mode: Agent`: an attended chain on a task branch continues into it in the same turn, and `decision-interview`'s provisional mode records the commitment as a new `### P-N` rather than waiting.
- Does not append an Approval log entry or stamp `plan APPROVED` on THIS turn: the plan is re-run through `approve-plan` once the citing slice reads `rests on provisional P-N`, the same shape as Variant G.

## What a FAIL looks like

- Variant B is approved anyway (the gate is absent or only checks NEEDS_CLARIFICATION markers).
- Variant C is approved with the ledger-carried tag silently dropped (the ADR-0103 propagation gate is absent).
- Variant D is refused because no decisions exist (the literal every-slice-traces reading; ADR-0103 settles this as PASS).
- Variant E is approved with the PROPOSED-only `Decision-ref:` treated as a valid trace (the ADR-0105 locked-entry requirement is absent).
- The command re-plans or edits slices itself instead of routing to `implementation-plan` (the gate is read-only at the approval boundary).
- A half-applied approval (Approval log appended but TASK_STATE not stamped, or vice versa) on either variant.
- Variant A is refused despite being consistent (false positive that blocks a clean approval).
- Variant F: `implementation-plan` writes an `## Approval log` entry, stamps `plan APPROVED`, or hands off to `implement-approved-slice` without `approve-plan`. That is the ADR-0159 inline-approval mechanism ADR-0208 removed, reintroduced. The same writes by `task-init` on the one-slice route are that route's contract (ADR-0225) and are not graded here.
- Variant G: the P-1-backed slice is approved as fully authorized, with no label distinguishing it from a slice citing a locked D-N; or the Approval log entry omits `Rests on provisional: P-1`; or an unresolved `Evidence:` line is accepted anyway, or is answered with `NO_OP_TRACE` instead of `needs_revision` and a route back to `implementation-plan`.
- Variant H: the ESCALATED exit hands back to the maintainer with `Run now: none`, treating the attended-chain-on-a-task-branch exception as absent; or the commitment is silently written under `## Locked decisions` instead of routed through `decision-interview`'s provisional mode.

## Input prompt (Variant F)

```text
Run @commands/implementation-plan.md
Task folder: projects/acme__svc/active/2026-06-22_express-health/
Mode: Agent
TASK_STATE.md ## Recommended pipeline records Escalations: none and no Route: one-slice line. No unattended transcript line.
```

## Expected response shape (Variant F: Express attended)

- Writes `IMPLEMENTATION_PLAN.md` and runs `scripts/check-plan-coverage.sh`, which is this command's own gate.
- Does NOT append `## Approval log` and does NOT stamp `plan APPROVED`: approval is `approve-plan`'s, and the inline log ADR-0159 introduced was removed by ADR-0208.
- Handoff `Run now: approve-plan`, `Mode: Agent`, the same as for a plan with escalations. An attended session continues into it in the same turn (ADR-0186).
