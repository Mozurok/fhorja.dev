# ADR-0089: The Godot E2E completeness wave (feel verdict as evidence, user-supplied media, probe hardening, consumption gates, ship preflight)

- **Status**: Accepted
- **Date**: 2026-07-10
- **Tags**: godot-cluster, feel-gate, media-ingestion, probe-harness, performance-budget, store-ship, consumption-gate, dogfood-driven, e2e-audit, extends-adr-0084, extends-adr-0085

## Context

The 2026-07-09 Godot dogfood round (a Suika-style drop-merge POC, task `physics-launcher-first-playable`) ran the full cluster flow, intake through performance-budget, and its transcript was mined by the `2026-07-09_godot-2d-e2e-completeness-audit` task: 14 evidence-grounded findings (every claim cites a transcript line), a 19-stage complete-game map (8 stages covered and dogfooded, 6 partial, the rest uncovered or out of scope), and a 5-angle fleet research synthesis over 15 captured sources.

The central failure: the flow declared "first-playable complete" with every machine gate green (the ADR-0085 runtime gate caught two real physics bugs and passed), and the human's first press-play found the game unplayable: a square placeholder sprite contradicting circular physics, an invisible container, an invisible game-over line, and a false game over under rapid drops that happy-path probes never exercised. Secondary failures: no legal path to bring reference media into the flow (worked around with a hand-written curl, three recurrences), throwaway probe scaffolding rewritten per slice, a TEST_STRATEGY.md no test ever consumed, an unmeasurable performance budget, an un-versioned game repo, and two substrate emission bugs polluting audit validation.

## Decision

Eight decisions locked in the audit task (D-1..D-8), folded into existing commands and topics with no new command (the ADR-0084/0085 fold-first precedent), delivered as 8 slices:

1. **Feel verdict as Layer-1 evidence (D-4).** A recorded human press-play verdict (a `## Feel verdict` block: Swink's six dimensions, a content-stripped engagement test, feedback proportionality, `Overall: PASS | FAIL`) is required before any first-playable or feature-complete claim closes. The checklist lives in `wos/godot-mobile-interaction-and-feel.md ## Feel verdict checklist (D-4 gate)`; the floor is enforced at the same three homes as ADR-0085 (slice-closure, the implement-approved-slice inline-close path, task-close), claim-scoped (fires only on first-playable or feature-complete claims), with the explicit-skip escape. Machine-green gates do not substitute for the human verdict; the human is the measurement instrument. A FAIL verdict routes to `pr-feedback-ingest --playtest`, which accepts the verdict block as a first-class payload.
2. **Media ingestion is user-supplied-first (D-3).** `capture-references` ingests reference media only from user-supplied local files and direct-file URLs with stated rights, recording source and license per item; platform-page URLs are refused with the platform-terms rationale (the captured YouTube ToS clause is the baseline) and the compliant alternatives offered; platform downloaders (yt-dlp or similar) are out of scope this wave. `image-to-spec --gameplay` documents the ffmpeg frame-extraction contract and states that reference quality governs spec quality.
3. **Feel before perf, juice budgeted (D-5).** The feel gate runs before the on-device performance baseline; `performance-budget`'s Godot surface requires a named measurement source per metric row (editor-profiler run as shown evidence; on-device rows marked pending-baseline) and an explicit reserved juice share of the frame budget at design stage.
4. **Probe hardening.** `godot-runtime-verify` gains a binary-resolution preflight, a persistent `probes/` harness convention (self-terminating probes, kept and versioned), and a mandatory adversarial or stress probe per mechanic acceptance; the recurred headless gotchas (class_name cache, Area2D frozen-body, --quit-after semantics) are folded into `wos/godot-testing-and-ci.md`.
5. **Consumption gates.** A produced `TEST_STRATEGY.md` is a commitment: every critical and regression row maps to a real test file or a recorded waiver, checked by a `task-close` floor (the produce-side counterpart of the deliverable-reconcile gate). `godot-scene-plan` gains a git preflight (a non-git game directory blocks and routes to `git init` before slices).
6. **Ship preflight.** `release-plan --godot-mobile` gains the checkable export preflight (Android AAB plus the pinned toolchain from the dated capture, the signing-key uninstall gotcha, the macOS-plus-Xcode iOS gate) and the Play track ladder (Internal, Closed, Open, Production; staged rollout via Android vitals) bound to its promotion and rollback vocabulary; the iOS store-side (TestFlight, review) is a named capture gap.
7. **Substrate emission fixes (F-12).** `external-research-fleet` states the K.5 validator constraints as MUST rules and validates after emission; `direction-adjust` places the transaction header immediately above the section heading.
8. **CC0-default asset sourcing (D-2)** and the **complete-game bar (D-6)**: the cluster's bar is stages 1-17 (intake through store ship); post-launch (18) enters after the first real ship; localization and monetization build guidance (19) stay out this wave.

**Dogfood-front roadmap (D-7, D-8; the durable record of the audit's deliverable rows 3-4).** The gap map's uncovered and partial stages become POC fronts, in this order: Front 1 feel-and-assets (continues the `wos-angry-bird` task as its vehicle, then closes it via task-close), Front 3 ship (real Android device, on-device baseline, one real Play internal-track upload), Front 5 test-hardening (persistent harness plus GUT/gdUnit4 plus headless CI), Front 2 game-shell (menus, pause, settings wired to audio buses, save lifecycle), Front 4 content (level pipeline on a second mini-genre; TileMaps plus the ten-principle rubric).

**Considered and deferred.** F-10 (lock the genre before deep reference capture) would be advisory prose, which this cluster's own rule forbids (gates, not advice); it stays a LEARNINGS lesson. F-14 (a transcript-path affordance) fails the YAGNI ladder. **Known follow-up, recorded not folded:** F-15, `implement-fleet`'s command text names audit events (`wave-merge`, `integration-gate`) absent from the K.5 validator enum; until a fix slice lands, orchestrators emit the valid `fleet-merge` / `merge_include` events (as this wave's own fleet run did).

## Consequences

### Positive

- The failure that motivated the wave is structurally closed: a Godot first-playable cannot be declared done on machine evidence alone, and the human verdict has a recorded, checkable format.
- Reference media has a legal path with the terms baseline captured, ending the recurring curl workaround.
- Runtime evidence gets stronger and cheaper: persistent probes, mandatory stress paths, no re-derived scaffolding, no re-found gotchas.
- Budgets, strategies, and repos stop lying: every metric names its measurement source, every strategy row is consumed or waived on the record, every game repo is versioned from day one.

### Negative

- Lifecycle commands gain two more conditional floors (feel verdict, strategy consumption) on top of ADR-0084/0085; an over-broad trigger would add ceremony. Mitigated: both are claim- or artifact-scoped with cheap explicit escapes, mirroring the proven ADR-0085 shape.
- Several command token budgets (already over their soft targets) grow slightly; the budget check stays warn-only.
- The pinned Android toolchain versions in release-plan will go stale; the text carries its capture date and a re-verify rule rather than pretending to be timeless.
