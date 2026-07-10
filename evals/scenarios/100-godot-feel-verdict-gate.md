# Eval scenario 100: the Godot feel-verdict gate blocks a first-playable claim without a recorded human verdict

- **Tags**: ADR-0089, godot-cluster, feel-gate, D-4, slice-closure, implement-approved-slice, task-close, pr-feedback-ingest, closure-enforcement, extends-adr-0085
- **Last reviewed**: 2026-07-10
- **Status**: active

## Goal

Validates the D-4 feel-verdict floor of **ADR-0089**: a Godot slice or task claiming first-playable or feature-complete cannot close on machine-green gates alone. Closure requires a recorded human press-play verdict (`## Feel verdict` block per `wos/godot-mobile-interaction-and-feel.md ## Feel verdict checklist (D-4 gate)`) with `Overall: PASS`, or an explicit one-line skip reason. The floor is enforced at the same three homes as ADR-0085 (slice-closure, the implement-approved-slice inline-close path, task-close), extends the runtime-gate floor without replacing it, and a FAIL verdict routes to `pr-feedback-ingest --playtest` as a first-class payload.

This exercises:

- slice-closure block: a Godot slice whose closure claim includes first-playable, with a recorded `godot-runtime-verify` PASS but NO `## Feel verdict` and no skip line, is classified `not ready to close` and routed to the feel-verdict checklist plus `pr-feedback-ingest --playtest` (machine-green does not substitute).
- inline-close block: the same claim does not close inline via implement-approved-slice; it routes to the checklist first.
- task-close backstop: a Godot task claiming a playable deliverable with neither a PASS verdict nor a skip reason is gate-blocked (not archived).
- Satisfying paths: a cited `## Feel verdict` with `Overall: PASS` closes; an explicit one-line skip reason closes.
- FAIL routing: a verdict with `Overall: FAIL` routes its per-dimension non-PASS lines to `pr-feedback-ingest --playtest`, where each becomes a matrix row with source `playtest` and provenance citing the verdict's date and build.
- No-fire cases: a non-Godot task, and a Godot slice making no first-playable or feature-complete claim (an ordinary mechanic slice), never trigger the floor.
- Layering: the ADR-0085 runtime-gate floor still applies independently; the feel floor never weakens it.

## Setup

Three variations, no engine needed (the scenario tests the closure contract the commands state): (a) a Godot task (project.godot signature) with a slice claiming "first-playable complete", runtime-verify PASS recorded, no feel verdict; (b) the same after a `## Feel verdict` with `Overall: PASS` is cited, or after a FAIL verdict exists; (c) a non-Godot backend task and a Godot slice with no completion claim.

## Input prompt

Run `slice-closure` (variation a, then b), `implement-approved-slice` reaching its completion check (variation a), and `task-close` (variation a), plus the no-fire controls (variation c).

## Expected behavior

- Variation (a): all three homes block; each names the missing `## Feel verdict`, points at the checklist section in `wos/godot-mobile-interaction-and-feel.md`, and routes to `pr-feedback-ingest --playtest` for the resulting notes; the runtime-gate PASS is acknowledged but does not satisfy the feel floor.
- Variation (b) PASS: closure proceeds, the verdict is cited as the feel evidence. Variation (b) FAIL: closure stays blocked and the verdict's non-PASS lines are ingested by `pr-feedback-ingest --playtest` as matrix rows.
- Variation (c): no mention of the feel floor at all.

## FAIL conditions

A FAIL is: closing a first-playable claim on runtime evidence alone; firing on a non-Godot task or a no-claim slice; treating the checklist as advisory (mentioning it without blocking); accepting a machine-generated verdict (the tester must be a human); or ingesting a FAIL verdict anywhere other than `pr-feedback-ingest --playtest`.
