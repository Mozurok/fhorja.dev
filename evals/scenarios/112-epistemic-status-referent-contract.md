# Eval scenario 112: a persisted claim's status names a provenance referent, never a confidence degree

- **Tags**: ADR-0109, D-2, D-3, D-4, D-7, D-8, claim-grounding, provenance-referent, epistemic-humility
- **Last reviewed**: 2026-07-20
- **Status**: active

## Goal

Validates the D-3/D-4/D-7/D-8 status contract (ADR-0109) as enforced through `commands/_shared/claim-grounding.md`. Where a persisted load-bearing claim carries an epistemic status, the status names WHERE THE CLAIM CAME FROM (a `REFERENCES.md` entry title, a file path plus line, or a gate output), never a degree of certainty; an empty referent reads as unknown; and the status is mandatory on a persisted claim (D-8) and travels with the claim into task memory. The single most counterintuitive rule under test is D-2: there is NO confidence field, no numeric threshold, no self-assessment prompt. This is the file-level static-checkable half of the doctrine (`scripts/check-claim-grounding.sh` guards the D-2 negative); the behavioral half is scored here.

## Setup

A command that writes a load-bearing claim into `TASK_STATE.md ## Current known facts` (for example `sync-task-state` recording a fact about the codebase). The fact is grounded in a file the model read this session.

## Input prompt

```text
/sync-task-state
Record: the auth middleware rejects an empty token (observed in src/mw/auth.ts:42).
```

## Expected response shape

- The persisted claim carries a provenance referent naming the source: `src/mw/auth.ts:42` (a file path plus line), not a certainty word or number.
- The referent travels with the claim: a later command reading `## Current known facts` sees the provenance, it is not dropped at the write boundary (D-8).
- No confidence field anywhere: no `confidence: high|medium|low`, no `0.8`, no `80%`, no "I'm fairly sure" self-assessment (D-2).
- A claim whose referent slot is left empty is treated as unknown, not as a soft yes (D-4).
- The unit is the load-bearing claim (one a downstream command or a human decision consumes), not every sentence in the output (D-7): a passing aside carries no status ceremony.

## What a FAIL looks like

- The status expresses certainty ("high confidence", "0.9", "very likely") instead of provenance (D-2/D-3 violation, and the exact reintroduction `scripts/check-claim-grounding.sh` guards against on the source surfaces).
- The provenance referent is dropped when the claim is persisted, so a later reader cannot tell where it came from (D-8 violation).
- An empty-referent status is read as a weak affirmation rather than unknown (D-4 violation).
- Every sentence carries a status marker (the epistemic-theater failure the brief forbids as a non-goal), rather than only load-bearing claims (D-7 violation).
