# Eval scenario 99: the debug loop, instrument-first locus gate, ruled-out ledger, and review-hard runtime-debug triage

- **Tags**: ADR-0088, incident-triage, review-hard, debug-loop, instrument-first, reference-grounding, ruled-out-ledger, rn-dogfood-audit
- **Last reviewed**: 2026-07-07
- **Status**: active

## Goal

Validates **ADR-0088** (the debug loop with no new command): `incident-triage` refuses to propose a fix on an INFERRED failing locus until runtime evidence confirms it (ADR-0043 applied to the runtime locus), maintains an append-only `## Ruled-out hypotheses` ledger in TASK_STATE.md that it reads first and appends on each disproof; and `review-hard` routes a runtime-debug payload (pasted logs plus a still-failing symptom) to incident-triage instead of absorbing it, mirroring the ADR-0084 playtest triage. No new command; the loop is incident-triage plus app-runtime-verify.

This exercises:

- Instrument-first locus gate: when the failing component is inferred from a symptom rather than confirmed by a stack trace / crash view-tree / isolating repro, the next step is to instrument and confirm, NOT to route to a fix; a locus confirmed by the signal in hand clears the gate.
- Ruled-out ledger: incident-triage reads the `## Ruled-out hypotheses` section first, does not re-propose a disproven lever, and appends a new disproof with its evidence.
- review-hard runtime-debug triage: pasted logs plus "still happening" route to incident-triage; a mixed code-risk-plus-log payload is split; a normal review is unaffected.
- No new command: the loop is emergent from incident-triage and app-runtime-verify; incident-triage keeps its six-way classification.

## Setup

Two variations: (a) a bug report describing a symptom ("crashes when I submit the login") with no stack trace, and a TASK_STATE.md whose `## Ruled-out hypotheses` already lists `enableScreens(false) -> no-op`; (b) a review-hard invocation whose args are a pasted adb logcat block plus "still crashing".

## Input prompt

```text
(a) It crashes when I submit the login form. Fix it. (No stack trace; TASK_STATE ## Ruled-out hypotheses already has "enableScreens(false) -> no-op".)
(b) review-hard: [pasted adb logcat with a crash] still crashing after the last change.
```

## Expected response shape

- (a) incident-triage does NOT propose a code edit on the inferred locus; the smallest next step is to instrument/confirm the locus (add a diagnostic log, read the crash view-tree, or reproduce with the isolating input); it reads the ledger first and does not re-propose `enableScreens(false)`; any new disproof is appended to `## Ruled-out hypotheses` with its evidence.
- (b) review-hard recognizes the runtime-debug payload and routes it to incident-triage (the debug-loop entry), rather than absorbing it into a code-risk review; a mixed payload is split.
- No new command is introduced; incident-triage stays single-shot with its existing classification.
- Response ends with a `### Handoff` block routing forward.

## Pass criteria

1. incident-triage refuses to propose a fix on an inferred locus and routes to instrumentation first; a locus confirmed by the signal in hand clears the gate.
2. incident-triage reads `## Ruled-out hypotheses` first, does not re-propose a disproven lever, and appends new disproofs with their evidence.
3. review-hard routes a runtime-debug payload (pasted logs plus a still-failing symptom) to incident-triage and splits a mixed payload; a normal review is unaffected.
4. No new command is introduced; the loop is incident-triage plus app-runtime-verify.

## Failure modes to watch

- **Inferred-locus edit**: proposing a code fix on a component the failure signal never named.
- **Dead-end re-try**: re-proposing a lever already recorded as disproven in the ledger.
- **Payload absorption**: review-hard treating a pasted-log debug payload as a code-risk review input.
- **New command**: inventing a debug-iterate command instead of using incident-triage plus app-runtime-verify.
- **Gate over-fire**: blocking a fix whose locus the failure signal already confirmed, or routing a normal review to incident-triage.

## Notes

- Related ADRs: [ADR-0088](../../docs/adr/0088-debug-loop-instrument-first-and-ruled-out-ledger.md), [ADR-0043](../../docs/adr/0043-reference-grounding-execution-gate.md), [ADR-0084](../../docs/adr/0084-godot-flow-completeness-wave.md), [ADR-0087](../../docs/adr/0087-app-runtime-verify.md).
- Related files: `commands/incident-triage.md`, `commands/review-hard.md`, `commands/app-runtime-verify.md`.
- Known issues: none yet (first run pending).

## History

- 2026-07-07: created with ADR-0088 (task `2026-07-07_wos-rn-dogfood-punchlist`, slice D).
