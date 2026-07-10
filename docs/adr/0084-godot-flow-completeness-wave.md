# ADR-0084: Godot 2D flow-completeness wave (mechanic contract, screen graph, audio and asset topics, playtest loop, closure commit gate)

- **Status**: Accepted
- **Date**: 2026-07-06
- **Tags**: godot-cluster, mechanic-contract, screen-graph, audio, asset-pipeline, playtest-loop, closure-commit-gate, forcing-function, dogfood-driven, extends-adr-0069, extends-adr-0078

## Context

A full dogfood built a complete Godot 4.7 mobile 2D idle game through the WOS (project `bmazurok__wow-2d-test`: two archived tasks, one active ring-rework task, one ~4881-line session transcript). Mining that evidence surfaced six confirmed gaps in the Godot 2D flow, one of them the root of the others:

- **G1 (root): no mechanic contract.** The core ring mechanic shipped wrong. The reference game's ring has a hole the ball escapes through, the hole closes over time, and a too-closed ring crushes the ball (lose condition); the build used HP/DPS depletion with no hole, no closing, no lose state. The gameplay video WAS mined, but ad hoc (ffmpeg at 1 frame per 5 seconds, the center number read as ring HP through a DPS lens), and no behavior fact was ever persisted: `REFERENCES.md` held only Godot API docs. `decision-interview` locked movement, damage-application, and language, then declared "no open mechanic decision", never asking win or lose conditions. Two full builds shipped on the wrong contract before a human playtest caught it. The WOS had no artifact type where observed gameplay behavior lands as a contract, so a visual reference silently stood in for a behavior spec.
- **G2: no screen-graph owner.** Screens M1 to M4 were each planned in isolation, each correctly disowning "the core loop", with entry points punted to the menu nav bar. Nothing owned the win/lose game states or the cross-screen transitions (stage end, score, chest, retry). The connecting flow simply did not exist until the playtest surfaced it, then was patched ad hoc as untracked slices "N3 to N6" with no slice files. HUD anatomy itself was fine: specified in the scene plans, built to spec, zero rework. The gap is the flow, not the HUD.
- **G3: audio was a decision-forcing gap, not a missing-guidance gap.** `godot-scene-plan` already prompted for an audio manager autoload and audio feedback; the plans YAGNI'd the autoload and demoted audio to "polimento" prose. Audio entered no `DECISIONS.md`, so nobody ever consciously accepted shipping silent. The game shipped Sound and Music toggles that persist a bool and control nothing (no `AudioStreamPlayer` exists). Soft guidance is exactly what failed.
- **G4: the playtest loop was ad hoc.** `godot-runtime-verify` ran once in the whole session, gated only the Godot error taxonomy, and PASSED the wrong mechanic (it verifies acceptance criteria derived from the contract; it cannot question the contract). The two later builds skipped the runtime gate. The playtest runbook was improvised twice. Both mechanic corrections entered through `review-hard` command-args; `pr-feedback-ingest --playtest` exists for exactly that payload and was never discovered.
- **G5: zero asset-pipeline coverage.** The game has no art (default icon only); placeholder colors were locked only after playtest. The cluster surface had no asset, sprite, texture, or import guidance.
- **G6: closure without commit evidence.** Two tasks archived as "done" with 24 closed slices and 41 uncommitted files over a single commit; the post-playtest patches also bypassed the slice protocol. Task memory said done and archived while the repo could lose everything to one bad checkout.

What worked and must not change: HUD-anatomy planning, the headless probe verification pattern (closed 24 slices with real evidence), `stack-currency-check` (caught the Godot 4.7 `Vector2.reflect` trap), and the MCP-agnostic scene-plan contract.

## Decision

Extend the Godot 2D-mobile cluster (ADR-0069, deepened by ADR-0078) with a completeness wave. Per ADR-0078's precedent the wave adds no new command: it lands as one new mode, gates on existing commands, two reference topics, and a cross-project lifecycle tightening. Two cross-cutting principles govern it:

- **D-1 (scope guard).** The evidenced-working surfaces stay unchanged: HUD-anatomy guidance, the headless probe pattern, `stack-currency-check`'s role, and the MCP-agnostic scene-plan contract.
- **D-2 (forcing functions, not advice).** Every G1 and G3 guardrail lands as a gate, a required artifact section, or a recorded decision. A guardrail that lands only as advisory prose is treated as not done. Rationale: G3 proves soft guidance does not force outcomes.

The six concrete changes (locked as D-3 to D-7 in the task's DECISIONS.md):

1. **Mechanic contract (D-4, addresses G1).** `image-to-spec` gains a gated `--gameplay` mode: screenshots, extracted video frames, and playtest notes become `MECHANICS_SPEC.md`, every rule in EARS form tagged `observed`, `assumed`, or `open`; unresolved rules affecting win, lose, or core interactions route to `decision-interview`. `godot-scene-plan` gains a mandatory "Mechanic contract" section that cites the spec rules the scene builds on or logs each missing rule as an open question. Behavior neither observed in a reference nor stated by the user is an open question, never an implemented assumed default. This gives video-derived behavior a durable place to land without a new command.
2. **Screen-graph step (D-3, addresses G2).** The "HUD coverage" deliverable is reframed to a screen-graph / game-state flow step (the reframe was confirmed with the user, not applied silently, per ADR-0056). For a multi-screen game, `godot-scene-plan` requires a specification of the game states (win, lose) and the cross-screen transitions before per-screen scene plans are implemented. HUD anatomy is recorded as already covered; no HUD guidance is removed (D-1).
3. **Audio and asset topics plus forcing rulings (D-5, addresses G3 and G5).** Two new lazy-loaded reference topics: `wos/godot-2d-audio.md` (bus layout, `AudioStreamPlayer` patterns, SFX pooling, music layering, haptics wiring, the inert-toggle trap) and `wos/godot-2d-asset-pipeline.md` (import settings, atlases, placeholder-to-final policy, sourcing hygiene). By plan approval a Godot game task must have a recorded ship-with-or-without-audio decision and a recorded placeholder-asset policy in `DECISIONS.md`; "polish later" prose does not satisfy this.
4. **Playtest loop (D-6, addresses G4).** `godot-runtime-verify` emits a persistent playtest runbook artifact and routes human playtest notes to `pr-feedback-ingest --playtest`; a Godot slice with runtime-observable behavior runs the gate or records an explicit skip reason; `review-hard` routes playtest-shaped args to `pr-feedback-ingest --playtest` instead of absorbing them.
5. **Closure commit gate (D-7, addresses G6).** `slice-closure` and `task-close` require, at close time, either a commit reference covering the closed work or an explicit recorded waiver line; absent both, closure refuses. This tightens the existing "merged or explicitly waived" done-condition by forcing the record, and applies to every project, not only Godot.
6. **Regression coverage.** Two eval scenarios pin the mechanic-contract-plus-playtest loop and the closure commit gate.

## Consequences

### Positive

- The root failure is structurally addressed: observed behavior now has a durable, EARS-tagged home, and `godot-scene-plan` cannot proceed on an assumed mechanic.
- Audio and assets can no longer be silently demoted to polish; the ship decision is on the record either way.
- The playtest signal reaches task memory through a designed path rather than whatever command happens to be open.
- Closure across every project now leaves an auditable commit trail or an explicit waiver, closing the "done but uncommitted" class.

### Negative

- `review-hard`, `slice-closure`, and `task-close` are core commands used far beyond Godot; the D-6 and D-7 changes carry the widest blast radius in the wave. Mitigated by additive-only wording, declared STOP conditions on those slices, and in-slice checks that existing eval expectations still hold.
- The Godot planning surface grows: a scene plan for a multi-screen game now carries more required sections. The screen-graph step is gated on multi-screen games, not single features, to bound the cost.

### Neutral

- The wave adds one mode and two topics; the cluster stays at two commands, consistent with ADR-0078.
- `MECHANICS_SPEC.md` has no template file; the `--gameplay` mode defines its format inline (YAGNI).
- Video-frame mining in the gameplay mode is opt-in (a local ffmpeg prerequisite, documented in the mode) rather than a forced step.

## Alternatives considered

### Alternative 1: a new `godot-mechanics-spec` command

- A first-class primitive for behavior specs, more visible than a mode.
- Rejected: ADR-0078 deliberately keeps the cluster at two commands and deepens via modes and topics; a new command costs a 4-registry registration and an eval scenario without a capability the `image-to-spec --gameplay` mode cannot carry.

### Alternative 2: checklist and decision-prompt edits only, no structural artifact

- Cheapest; no new surface.
- Rejected on direct evidence: `godot-scene-plan` already prompted for audio as prose and the game still shipped silent (G3). Non-forcing guidance is the failure mode this wave exists to end (D-2).

### Alternative 3: scope the closure commit gate to the Godot cluster only

- Smaller blast radius; core lifecycle untouched.
- Rejected by the user: the "done but uncommitted" failure is general, not game-specific, so the gate applies to all projects (D-7).

## References

- Task `projects/bmazurok__my-work-tasks/active/2026-07-06_godot-2d-flow-dogfood-gaps/`: `IMPACT_ANALYSIS.md` (gap map G1 to G6 with transcript line refs), `DECISIONS.md` (D-1 to D-7, EARS), `IMPLEMENTATION_PLAN.md` (7 slices, 4 waves).
- Dogfood evidence: `projects/bmazurok__wow-2d-test/` (two archived tasks, one active ring-rework task) and the session transcript cut in the task's `inputs/`.
- ADR-0069 (the Godot 2D-mobile cluster) and ADR-0078 (the cluster deepening via modes, topics, and bug-classes) that this wave extends; ADR-0056 (the deliverable-coverage rule that forced the HUD reframe to be confirmed, not silent); ADR-0043 (reference grounding); ADR-0048 (deterministic gate as Layer 1 evidence); ADR-0031 (EARS); ADR-0029 (registry and count-marker drift guards).

## Notes

Found by dogfood, and single-rooted: because no command captured the mechanic contract from the reference video (G1), the only place the wrong mechanic could surface was a human playtest, and because there was no playtest-ingestion gate (G4), the correction arrived through `review-hard` args after two full builds had shipped on the wrong contract. The wave breaks that chain at the source (a durable behavior spec) and at every downstream link (screen graph, audio and asset rulings, playtest loop, commit gate).
