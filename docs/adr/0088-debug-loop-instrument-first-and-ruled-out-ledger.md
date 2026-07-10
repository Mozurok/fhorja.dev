# ADR-0088: The debug loop, an instrument-first locus gate, a ruled-out-hypotheses ledger, and a runtime-debug payload triage

- **Status**: Accepted
- **Date**: 2026-07-07
- **Tags**: incident-triage, review-hard, debug-loop, instrument-first, reference-grounding, ruled-out-ledger, dogfood-driven, rn-dogfood-audit, no-new-command

## Context

The rn-reference-app dogfood exposed three related failures in how the WOS runs a live debugging loop:

1. **review-hard absorbed the debug loop.** In the audited session `review-hard` was invoked about ten times, mostly with pasted `adb logcat` output as args, functioning as the observe-hypothesize-instrument-rerun loop, while `incident-triage` (the actual failure command) ran only three times. `review-hard` is a code-risk review, not a debug-iterate loop; it landed there because it accepts free text and reasons about the situation. There was no first-class home for "here is new runtime output, still failing, iterate".

2. **Editing an inferred locus burned slices.** The session spent several slices editing an inferred locus (the login screen, the Input atom, the KeyboardController, `enableScreens`) without instrumenting to confirm which component actually failed. The maintainer had to inject skepticism ("are we even editing the right screen?") before a crash-view-tree read found the real trigger (the login screen torn down by a `router.replace` after 2FA), and `enableScreens(false)` turned out to be a no-op. The WOS has a reference-grounding execution gate (ADR-0043) that refuses to edit against an uncaptured external contract; it had no equivalent for the runtime locus.

3. **Dead-ends were not a fast-read ledger.** Across two context compactions, the disproven levers (feature-flag overrides, the config plugin, `enableScreens` as a no-op) were scattered in DECISIONS.md dead-end entries. A resumed context risked re-trying them.

The design (task `2026-07-07_wos-rn-dogfood-punchlist`, decisions D-3 and D-5): no new command (Direction C, D-1). The loop is `incident-triage` alternating with `app-runtime-verify` (ADR-0087); the three gaps become gates and a ledger on the existing commands.

## Decision

Three additions, one ADR, no new command:

1. **Instrument-first locus gate in `incident-triage` (P1-4).** WHEN the failing locus is INFERRED from a description or symptom rather than CONFIRMED by runtime evidence (a stack trace naming it, a crash view-tree, a diagnostic log, or an isolating reproduction), the smallest decisive next step is to instrument and confirm the locus BEFORE any code fix is proposed; do not route to a fix on an inferred locus. This applies the ADR-0043 reference-grounding principle to the runtime locus: editing an inferred locus is false progress. A locus already confirmed by the failure signal in hand clears the gate, so a normal fix pays no ceremony.

2. **Ruled-out-hypotheses ledger in `incident-triage` (P2-5).** `incident-triage` maintains a `## Ruled-out hypotheses` section in `TASK_STATE.md`: an append-only, one-line-per-entry list of levers and hypotheses already tried and disproven, each with the disproving evidence. It reads the ledger first on entry (so a long or resumed session does not re-try a dead end) and appends whenever it disproves a hypothesis. The ledger lives in `TASK_STATE.md` because that is the resumable memory `resume-from-state` already reads, so the dead-ends travel with the task across compaction with no new artifact type.

3. **Runtime-debug-payload triage in `review-hard` (P1-3).** Mirroring the ADR-0084 playtest-payload triage that `review-hard` already carries, a second payload-shape-conditional branch: WHEN the args are a runtime-debug payload (pasted logs, a stack trace or crash signature, plus a still-failing symptom) rather than a code-risk-review request, route it to `incident-triage` (the debug-loop entry) instead of absorbing it. A mixed payload is split: the code-risk part is reviewed here, the runtime-debug part routed onward. A normal review invocation is unaffected.

Together these make the debug loop first-class without a new command: a pasted-log payload routes into `incident-triage`, which confirms the locus before any edit, records what has been ruled out, and alternates with `app-runtime-verify` for the runtime gate.

## Consequences

### Positive

- The debug loop has a home. Pasted runtime logs plus "still happening" route to `incident-triage`, not into an ad-hoc `review-hard` pass, so the code-risk review stays a code-risk review.
- Edits stop landing on inferred loci: the instrument-first gate forces runtime confirmation of the failing component before a fix, the exact false-progress the audit hit.
- Dead-ends are a fast-read ledger in resumable memory, so a compacted or resumed session does not re-try a disproven lever.

### Negative

- `incident-triage` gains two conditional gates and a ledger, and `review-hard` a second triage branch. An over-broad trigger could add ceremony to a routine fix or a normal review. Mitigated by making each gate conditional (inferred-locus only; runtime-debug-payload-shape only) with an explicit clear-the-gate path.

### Neutral

- No new command (Direction C); the loop is emergent from `incident-triage` plus `app-runtime-verify`, not a new control structure. The ledger reuses `TASK_STATE.md` rather than adding an artifact type.
