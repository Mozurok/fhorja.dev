# Eval scenario 94: the mechanic contract is forced before implementation and the playtest loop is routed, not improvised

- **Tags**: ADR-0084, godot-cluster, image-to-spec, godot-scene-plan, godot-runtime-verify, review-hard, pr-feedback-ingest, mechanic-contract, playtest-loop
- **Last reviewed**: 2026-07-06
- **Status**: active

## Goal

Validates **ADR-0084** G1 and G4: a 2D-game mechanic is never implemented from an assumed default, and human playtest feedback reaches task memory through a designed path rather than whatever command is open. `image-to-spec --gameplay` turns references into a `MECHANICS_SPEC.md` whose rules are EARS-form and tagged observed, assumed, or open; `godot-scene-plan` refuses to design a scene around a mechanic that is assumed, open, or absent, routing it to `decision-interview`; `godot-runtime-verify` emits a `PLAYTEST_RUNBOOK.md` and routes human notes to `pr-feedback-ingest --playtest`; and `review-hard` routes playtest-shaped args to `pr-feedback-ingest --playtest` instead of absorbing them.

This exercises:

- Gameplay-mode producer: `--gameplay` emits `MECHANICS_SPEC.md`, every rule EARS-form and tagged observed / assumed / open, with win and lose conditions each present and an `## Unresolved mechanics` list; a lose condition not shown in the references is `open`, never an assumed default. When video frames are mined the ffmpeg sampling rate is stated.
- Scene-plan consumer gate: `godot-scene-plan` cites the spec rules its scene realizes, and logs any assumed, open, or missing rule as an open question routed to `decision-interview`; a scene designed around an undocumented mechanic is invalid output.
- Playtest runbook: `godot-runtime-verify` writes `PLAYTEST_RUNBOOK.md` (how to run, what to exercise including feel and fidelity, where notes go) and routes returned human notes to `pr-feedback-ingest --playtest`.
- review-hard triage: playtest-shaped args ("the game runs but the ball behaves wrong") are routed to `pr-feedback-ingest --playtest`, not reviewed as code risk; a mixed payload is split.
- No new command and MCP-agnostic: the flow uses the existing two commands plus modes; no MCP server is named.

## Setup

An active Godot 2D task with reference screenshots and a gameplay video in `docs/`, a `MECHANICS_SPEC.md` not yet produced, and the four command files carrying the ADR-0084 additions. No engine needs to run; the scenario tests the contract the commands state and follow.

## Input prompt

```text
1) From these screenshots and the gameplay video, produce the mechanic spec (use gameplay mode). 2) Plan the core-loop scene from it. 3) I ran the build and the ball escapes the ring even when the hole is on the far side, and it feels too fast. Here is my feedback.
```

## Expected response shape

- Step 1: `image-to-spec --gameplay` produces `MECHANICS_SPEC.md` with EARS rules tagged observed / assumed / open; the lose condition, if not visible in a still, is `open`; the video-frame mining states its sampling rate; unresolved win/lose/core rules are listed under `## Unresolved mechanics` and routed to `decision-interview`.
- Step 2: `godot-scene-plan` cites the observed rules its scene realizes and, for any assumed or open rule the scene depends on, logs an open question to `decision-interview` rather than designing around a default; a mandatory Mechanic contract section is present.
- Step 3: the ball-escape-and-feel feedback is playtest-shaped, so the response routes it to `pr-feedback-ingest --playtest` (via `godot-runtime-verify`'s runbook handoff, or `review-hard`'s triage if that command was reached), not absorbed as a code-risk review; a `PLAYTEST_RUNBOOK.md` exists or is written.
- Response ends with a `### Handoff` block routing forward.

## Pass criteria

1. `MECHANICS_SPEC.md` is EARS-form, every rule tagged observed / assumed / open, with a win and a lose condition each present; an undetermined lose condition is `open`, never an assumed default.
2. `godot-scene-plan` refuses to design a scene around an assumed, open, or missing mechanic; it routes the gap to `decision-interview` and carries the mandatory Mechanic contract section.
3. The playtest feedback is routed to `pr-feedback-ingest --playtest`, not treated as a code-risk review; a mixed payload is split.
4. A `PLAYTEST_RUNBOOK.md` is present or written by `godot-runtime-verify`, naming how to run, what to exercise, and where notes go.
5. No MCP server is named in normative text; no new command is introduced (the flow is modes plus the existing two commands).
6. When video frames are mined, the ffmpeg sampling rate is stated and a mechanic a low rate could miss is tagged `open`.

## Failure modes to watch

- **Assumed mechanic**: a scene plan (or spec) that fills a missing win/lose or interaction rule with a plausible default instead of tagging it open and routing to `decision-interview`. This is the exact dogfood failure ADR-0084 exists to prevent.
- **Absorbed playtest**: `review-hard` reviewing "it feels too fast" as a code risk instead of routing it to `pr-feedback-ingest --playtest`.
- **Missing runbook**: an improvised one-off run instruction instead of a persistent `PLAYTEST_RUNBOOK.md`.
- **Silent sampling**: mining video frames without stating the rate, or guessing a time-based mechanic a low rate would miss.
- **Scope creep**: proposing a new command instead of using the gameplay mode and the existing commands, or naming a specific MCP server.

## Notes

- Related ADRs: [ADR-0084](../../docs/adr/0084-godot-flow-completeness-wave.md), [ADR-0069](../../docs/adr/0069-godot-2d-mobile-cluster.md), [ADR-0078](../../docs/adr/0078-godot-2d-mobile-cluster-deepening.md), [ADR-0031](../../docs/adr/0031-ears-for-decisions-and-exit-criteria.md), [ADR-0043](../../docs/adr/0043-reference-grounding-execution-gate.md).
- Related files: `commands/image-to-spec.md`, `commands/godot-scene-plan.md`, `commands/godot-runtime-verify.md`, `commands/review-hard.md`, `commands/pr-feedback-ingest.md`, `wos/godot-2d-audio.md`, `wos/godot-2d-asset-pipeline.md`.
- Known issues: none yet (first run pending).

## History

- 2026-07-06: created with the ADR-0084 Godot flow-completeness wave (task `2026-07-06_godot-2d-flow-dogfood-gaps`, slice 07).
