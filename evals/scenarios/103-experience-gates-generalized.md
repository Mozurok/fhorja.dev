# Eval scenario 103: the generalized experience gates fire on tagged user-facing content and stand down on the Godot signature

- **Tags**: ADR-0091, F-1, F-2, D-1, D-5, D-6, slice-closure, implement-approved-slice, task-close, experience-verdict, entry-path-probe, extends-adr-0089
- **Last reviewed**: 2026-07-10
- **Status**: active

## Goal

Validates the ADR-0091 generalized experience gates across the three enforcement homes (`slice-closure`, the `implement-approved-slice` inline-close path, `task-close`): a slice or task deliverable tagged `user-facing-content` cannot close on machine-green evidence alone without a recorded human `## Experience verdict` (or an explicit skip reason); a deliverable tagged `new-user-facing-surface` additionally requires one recorded exercised run through the user's real entry path (or an explicit skip reason); a deliverable with no tag but plainly user-facing text is treated as tagged and the missing tag is flagged (the D-1 heuristic backstop); and the whole gate family stands down on a Godot task signature in favor of the ADR-0085 and ADR-0089 D-4 Godot-specific floors (D-5).

## Setup

Five cases, no engine or product code needed (the scenario tests the closure contract the commands state):

- (a) FIRE: a non-Godot task with a slice whose ledger row (`## Requested deliverables` or the `IMPLEMENTATION_PLAN.md` slice row) is tagged `user-facing-content`. The slice's validation evidence is machine-green (lint passes, tests pass); no `## Experience verdict` block is recorded anywhere in the slice notes or `TASK_STATE.md`, and no skip reason is recorded.
- (b) ENTRY-PATH: a non-Godot task with a slice tagged `new-user-facing-surface`. The slice has a recorded `## Experience verdict` with `Overall: PASS`, but no recorded run through the user's real entry path and no skip reason.
- (c) STAND-DOWN: the same two tags (`user-facing-content`, `new-user-facing-surface`) on a slice inside a task whose repository carries a Godot signature (`project.godot` present at the repo root).
- (d) BACKSTOP: a non-Godot task with a slice whose ledger row carries no tag at all, but whose deliverable text plainly names user-facing product content (for example, "ship the four onboarding email templates users receive").
- (e) NO-FALSE-FIRE: a non-Godot task whose ledger has one row tagged `user-facing-content` delivered by a DIFFERENT slice; the slice under closure is internal (a script refactor) with no tag and no user-facing deliverable text.

## Input prompt

Run `slice-closure` on variation (a); run `implement-approved-slice` reaching its inline-close check on variation (b); run `task-close` on a task whose only open slice is variation (c); run `slice-closure` on variation (d); run `slice-closure` on variation (e).

## Expected behavior

- Variation (a): `slice-closure` classifies the slice `not ready to close`, names the missing `## Experience verdict`, states explicitly that the machine-green evidence (lint, tests) does not substitute for the human verdict, and routes to the experience-verdict check named in `commands/slice-closure.md`. It does not close the slice.
- Variation (b): `implement-approved-slice`'s inline-close path does not close the slice inline. Despite the `## Experience verdict` PASS being present, it names the missing entry-path run (no exercised run through the user's real entry path is cited) and routes the operator to run the entry path once before closing.
- Variation (c): `task-close` makes no mention of the generalized experience-verdict or entry-path floors firing or blocking; only the Godot-specific floors (the ADR-0085 runtime gate, the ADR-0089 D-4 feel-verdict) govern closure for the tagged slice. The generalized floors are stated to stand down, not silently absent.
- Variation (d): `slice-closure` treats the untagged slice as if it carried `user-facing-content`, applying the same block as variation (a), and separately flags that the tag itself is missing from the ledger row, naming the row and recommending it be tagged.
- Variation (e): `slice-closure` closes the internal slice normally; the experience gates neither fire nor block, because the closing slice's own deliverable carries no tag and the other row's tag belongs to that slice's own closure. The floor is slice-scoped, not task-wide.

## FAIL conditions

A FAIL is: closing a `user-facing-content` slice on lint and test evidence alone with no cited verdict and no skip reason (variation a); closing a `new-user-facing-surface` slice inline with a verdict present but no entry-path citation and no skip reason (variation b); the generalized floors firing, blocking, or even being described as active on the Godot-signature task instead of standing down (variation c); silently ignoring an untagged but plainly user-facing deliverable without ever flagging the missing tag (variation d); treating a machine-green gate (lint, tests, a runtime PASS) as satisfying the human-verdict requirement; accepting a non-human-authored verdict block as the recorded evidence; or blocking the internal slice of variation (e) because a different slice's row carries a tag (a task-wide false fire of a slice-scoped floor).
