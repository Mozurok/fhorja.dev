---
activation: model_decision
description: The generalized slice-closure floors, verbatim per-command variants for implement-approved-slice (inline-close) and slice-closure. Load before deciding any slice closure verdict.
---

# Closure floors

The generalized floors that gate a slice from closing. Each is written once here,
with its per-command variant, and is referenced from `commands/slice-closure.md`
and `commands/implement-approved-slice.md` rather than duplicated into both.

## When to load this file

**Always, before emitting a closure verdict.** Unlike `wos/platform-runtime-floors.md`,
which fires only on a Godot or mobile task signature, these floors are
UNCONDITIONAL: every slice passes through them. The load is lazy only in the sense
that a run which never reaches a closure decision never pays for it. A run that is
deciding whether a slice closes MUST read this file first; skipping it is not an
optimization, it is skipping the gate.

Two homes, always. `implement-approved-slice` closes a LOW or MEDIUM slice inline
and does not route to `slice-closure`, so each floor carries an inline-close
variant and a slice-closure variant. The rule behind that pairing, and why a floor
written to one home only never fires, is `wos/gate-conditions.md`
`### A closure floor needs two homes, or it does not exist`.

**G3 safeguard (same rule as the platform floors).** The closure notes SHALL cite
which subsections were read and applied. A lazy load that degrades into a
paraphrase is the failure mode this citation exists to catch: a floor recalled
from memory is a floor that drifts.

**Not here:** `task-close.md` keeps its whole-task backstops inline. They read
recorded evidence across every slice rather than gating one, and moving them would
widen this change past the two files that needed it.


---

## Commit-evidence floor (ADR-0084, bounded deferral per ADR-0100)

### implement-approved-slice variant (inline-close)

**Commit-evidence floor (inline-close; ADR-0084, bounded deferral per ADR-0100, third home per ADR-0105).** A slice SHALL NOT close inline (the LOW/MEDIUM path) unless its work is committed (cite the commit reference in the slice notes) OR an explicit committing-waiver covering only genuinely discardable work (a deliberate throwaway, a spike whose value was the learning) is recorded. Real work awaiting a human commit, including an unattended session where git is unavailable or forbidden, is a BOUNDED DEFERRAL: record `deferred: pending human commit (<one-line context>)`, do NOT inline-close, and leave the slice open for the next human session. IF none of the three is present THEN do not inline-close; route to `branch-commit`.

### slice-closure variant

**Commit-evidence floor (ADR-0084, bounded deferral per ADR-0100).** A slice is not `ready to close` unless its work is committed (cite the commit reference in the closure notes) or an explicit waiver of committing is recorded. A committing-waiver covers ONLY genuinely discardable work (a deliberate throwaway, a spike whose value was the learning); real work awaiting a human commit, including an unattended session where git is unavailable or forbidden, is a BOUNDED DEFERRAL: record it as `deferred: pending human commit (<one-line context>)`, classify the slice `not ready to close`, leave it open for the next human session, and route to `/sync-task-state` so the open deferral is persisted; `branch-commit` is the first action of that human session. A waiver line on real work does not satisfy this floor. IF the slice's work is neither committed, genuinely waived, nor recorded as a bounded deferral THEN classify it `not ready to close` and route to `branch-commit`. This is the slice-level counterpart to the `task-close` floor; it closes the observed failure where slices were marked done with the work uncommitted (the dogfood behind ADR-0084), and the ADR-0100 refinement closes the follow-on failure where an unattended run could waive real work closed (5 of 10 paths in the 2026-07-11 wave hit exactly this gap).


---

## Experience-verdict floor (ADR-0091, generalizes ADR-0089 D-4)

### implement-approved-slice variant (inline-close)

**Experience-verdict floor (inline-close, generalized, ADR-0091).** WHEN the slice's deliverable carries the tag `user-facing-content` or `new-user-facing-surface` (the D-1 ledger and plan tags), the slice SHALL NOT close inline unless a recorded human experience verdict on a sample (an `## Experience verdict` block with `Overall: PASS` cited in the slice notes) is present OR an explicit one-line skip reason is recorded. Machine-green evidence (lint, tests, a runtime PASS) SHALL NOT substitute for the human verdict. IF the deliverable text plainly indicates user-facing content and no tag is present THEN treat the slice as tagged and flag the missing tag. IF neither is present THEN do NOT inline-close; route to the experience-verdict check first. WHILE the Godot task signature is present this floor stands down in favor of the D-4 feel-verdict floor above. This generalizes ADR-0089 D-4 off Godot: the 2026-07-10 connector dogfood shipped four machine-authored session packs with no human validation of one. Same bounded-vs-permanent skip rule as the D-4 floor above applies here (ADR-0098): a "no human, ever" skip reason does not satisfy this floor.

### slice-closure variant

**Experience-verdict floor (generalized, ADR-0091).** WHEN the closing slice's own deliverable carries the tag `user-facing-content` or `new-user-facing-surface` (the D-1 ledger and plan tags; a tag on a different slice's row does not fire this floor), closure at this home SHALL require a recorded human experience verdict on a sample (an `## Experience verdict` block with `Overall: PASS` cited in the slice notes or task record) OR an explicit one-line skip reason. Machine-green evidence (lint, tests, a runtime PASS) SHALL NOT substitute for the human verdict. IF the deliverable text plainly indicates user-facing content and no tag is present THEN treat the slice as tagged and flag the missing tag. IF neither the verdict nor a skip reason is present THEN classify the slice `not ready to close` and route to the experience-verdict check. WHILE the Godot task signature is present this floor stands down in favor of the D-4 feel-verdict floor above. This generalizes ADR-0089 D-4 off Godot: the 2026-07-10 connector dogfood shipped four machine-authored session packs with no human validation of one. Same bounded-vs-permanent skip rule as the D-4 floor above applies here (ADR-0098): a "no human, ever" skip reason does not satisfy this floor.


---

## Entry-path probe floor (ADR-0091)

### implement-approved-slice variant (inline-close)

**Entry-path probe floor (inline-close, ADR-0091).** WHEN the slice ships a deliverable tagged `new-user-facing-surface`, it SHALL NOT close inline unless one recorded exercised run through the user's real entry path (the way an end user reaches the surface, not the API underneath) is cited in the slice notes OR an explicit one-line skip reason is recorded. IF neither is present THEN do NOT inline-close; route the operator to run the entry path once. The dogfooded surface shipped as MCP prompts a chat model never invokes, a gap found only after it had already scaled four times over. WHILE the Godot task signature is present this floor stands down in favor of the D-4 feel-verdict floor above.

### slice-closure variant

**Entry-path probe floor (ADR-0091).** WHEN the slice ships a deliverable tagged `new-user-facing-surface`, closure at this home SHALL require one recorded exercised run through the user's real entry path (the way an end user reaches the surface, not the API underneath) cited in the slice notes OR an explicit one-line skip reason. IF neither is present THEN classify the slice `not ready to close` and route the operator to run the entry path once. The dogfooded surface shipped as MCP prompts a chat model never invokes, a gap found only after it had already scaled four times over. WHILE the Godot task signature is present this floor stands down in favor of the D-4 feel-verdict floor above.


---

## Eval-threshold floor (ADR-0104)

### implement-approved-slice variant (inline-close)

**Eval-threshold floor (inline-close, ADR-0104).** WHEN an `AI_EVAL_PLAN.md` exists in the task folder covering the feature this slice ships or changes, the slice SHALL NOT close inline unless the recorded eval OUTCOME (the score against the plan's pass threshold on its held-out set) is cited in the slice notes with the threshold met, OR an explicit one-line skip reason is recorded (bounded-vs-permanent per ADR-0098: a bounded deferral satisfies it, a permanent "the eval will never run" does not). An exit criterion worded around the harness mechanism ("the harness runs", "the eval executes") SHALL NOT substitute for the threshold outcome: a green harness execution with a failing score FAILS this floor. IF the outcome is absent THEN do NOT inline-close; run the eval per `AI_EVAL_PLAN.md` first.

### slice-closure variant

**Eval-threshold floor (ADR-0104).** WHEN an `AI_EVAL_PLAN.md` exists in the task folder covering the feature the closing slice ships or changes, the slice is not `ready to close` unless the recorded eval OUTCOME (the score against the plan's pass threshold on its held-out set) is cited with the threshold met, OR an explicit one-line skip reason is recorded (bounded-vs-permanent per ADR-0098). An exit criterion or closure note worded around the harness mechanism ("the harness runs") SHALL NOT substitute for the threshold outcome: a green harness execution with a failing score FAILS this floor. IF the outcome is absent THEN classify the slice `not ready to close` and route to running the eval per `AI_EVAL_PLAN.md`. No-op when the task has no `AI_EVAL_PLAN.md` or the slice does not touch the evaluated feature.


---

## Integrity floor (v3 wave3 item S1)

### slice-closure variant

**Integrity floor (blocking; v3 wave3, item S1).** Run `bash scripts/verify-substrate-batch.sh <task-folder>` as part of the closure evidence. WHEN the wrapper exits non-zero the slice is not `ready to close` UNLESS an explicit waiver line is recorded in the closure notes: `integrity-waiver: N advisories unresolved (<one-line reason>)`, naming the failing validator(s) from the wrapper's summary line. A silent non-zero is never absorbed; a recorded waiver travels into the closure record. This floor consumes the wrapper's exit code and never re-implements the validators (wave-2 D-3 boundary); it keys on exit codes only, so the informational header-drift count (which never flips an exit code) cannot fire it. Checkpoint-eligible as a mechanical floor: the resume verdict is the re-run's exit code. This flips the v2 S1 finding (integrity advisories grew 13 to 23 while every validation reported OK).

### implement-approved-slice variant (inline-close)

None. This floor consumes a whole-task integrity wrapper and has one home, `slice-closure`.


---

## Layer-2 review floor (wos/gate-conditions.md, skip semantics per ADR-0098)

### implement-approved-slice variant (inline-close)

**Layer-2 review floor (inline-close; layering rule: `wos/gate-conditions.md` `## Verification layering`; skip semantics per ADR-0098).** A slice SHALL NOT close inline unless a Layer-2 risk review ran against the slice diff and its verdict is cited in the slice notes: `review-hard` (plus `security-review` when the slice has a security surface), or a named host-repo equivalent cited by name (for example a repo-local `/prove-it`), OR an explicit one-line skip reason. The inline exit-criteria checklist above is Layer 1 and SHALL NOT substitute for it. IF neither a cited verdict nor a skip reason is present THEN do NOT inline-close; route to `review-hard`. This floor matters most on the path that skips `slice-closure` entirely: LOW and MEDIUM slices are where an unreviewed defect travels furthest before anyone looks (mobile dogfood 2026-07-29: 5 LOW and 3 MEDIUM slices, zero Layer-2 reviews, and the first review returned 4 defects spanning two slices already treated as done).

### slice-closure variant

**Layer-2 review floor (layering rule: `wos/gate-conditions.md` `## Verification layering`; skip semantics per ADR-0098).** A slice is not `ready to close` unless a Layer-2 risk review ran against the slice diff and its verdict is cited in the closure notes: `review-hard` (plus `security-review` when the slice has a security surface), or a named host-repo equivalent cited by name (for example a repo-local `/prove-it`), OR an explicit one-line skip reason. Layer 1 green SHALL NOT substitute: a passing typecheck, lint and test run satisfies the layer below this one and says nothing about risk. IF neither a cited verdict nor a skip reason is present THEN classify the slice `not ready to close` and route to `review-hard`. Reviewing while the slice is small and fresh is what keeps a defect from surfacing later inside a slice already marked done (mobile dogfood 2026-07-29: 4 closures against 8 floors, zero Layer-2 reviews, and the first review returned 4 defects spanning two closed slices).


---

## Rollout-constraint reconcile (mobile dogfood 2026-07-29)

### implement-approved-slice variant (inline-close)

**Rollout-constraint reconcile (inline-close, mobile dogfood 2026-07-29).** WHEN `IMPLEMENTATION_PLAN.md` carries a `## Rollout and rollback notes` section, check each constraint stated there against this slice's declared Scope before closing inline. A constraint naming a file, config key, or release track inside that Scope is reconciled when the slice notes state it is satisfied, or record it as a deferral naming what satisfies it and when. IF a constraint in Scope is unchecked THEN do NOT inline-close. The plan writes its rollout constraints before the code exists: on the source run the plan named the exact OTA-versus-native ordering hazard on day one, and it surfaced as the run's only CRITICAL 30 hours later.

### slice-closure variant

**Rollout-constraint reconcile (mobile dogfood 2026-07-29).** WHEN `IMPLEMENTATION_PLAN.md` carries a `## Rollout and rollback notes` section, check each constraint stated there against the closing slice's declared Scope. A constraint naming a file, config key, or release track inside that Scope is reconciled when the closure notes state it is satisfied, or record it as a deferral naming what satisfies it and when. IF a constraint in Scope is unchecked THEN classify the slice `not ready to close`. This joins the reconcile family below (deliverable-reconcile per ADR-0056, references-reconcile per X2). The plan writes its rollout constraints before the code exists, which makes closure the cheapest place to catch a release-track defect: on the source run the plan named the exact ordering hazard on day one and the review found it as the only CRITICAL 30 hours later.
