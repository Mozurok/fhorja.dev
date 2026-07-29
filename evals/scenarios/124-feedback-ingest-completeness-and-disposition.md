# Eval scenario 124: feedback ingest requires a complete input set and carries an already-addressed disposition

- **Tags**: ADR-0121, pr-feedback-ingest, completeness-precondition, already-addressed, absorption, greptile
- **Last reviewed**: 2026-07-29
- **Status**: active

## Goal

Validates the two `pr-feedback-ingest` folds from the 2026-07-29 absorption wave: the command does not build its feedback matrix until the ingested set is complete (D-5), and an item a later commit already resolved is tagged `already-addressed` and never enters the corrective backlog (D-6).

This exercises:

- Completeness across all three input modes, with completeness ESTABLISHED rather than assumed.
- The operator's assertion path, which is the load-bearing positive case: a legitimate pasted payload must be able to proceed.
- The already-addressed disposition, and its distinction from the pre-existing dedup rule.

## Setup

An active task with an open PR.

Variation (a), the negative: `--mcp-pull` where the Greptile review check is still running and two linter checks have not reported.

Variation (b), the load-bearing positive: a pasted payload of six review comments, where the operator states the review is finished.

Variation (c): `--playtest` with a tester's notes and no statement about whether the session ended.

Variation (d): a pasted payload of four comments where two were already fixed by a commit pushed after the review.

## Input prompt

```text
(a) /pr-feedback-ingest --mcp-pull
(b) /pr-feedback-ingest
    [six pasted comments] Review is done, that is all of them.
(c) /pr-feedback-ingest --playtest
    [tester notes about jump feel and a stuck camera]
(d) /pr-feedback-ingest
    [four pasted comments] Review is complete. Note commits abc123 and def456
    landed after the review.
```

## Expected

Variation (a):

- No feedback matrix is built. The command names which checks are still pending and stops.
- The stop is not a refusal to ever proceed: it states what would make the set complete.

Variation (b) is the load-bearing case:

- The matrix IS built. The operator's statement that the review is finished satisfies the precondition.
- An output that refuses here, demanding machine-detected terminality on a pasted payload, is a FAIL. The rule requires completeness to be established, not machine-detected, and over-firing makes the command unusable in its most common mode.

Variation (c):

- The command asks whether the playtest session is finished, or accepts an operator statement that it is. It does NOT look for CI checks, which do not exist in this mode.

Variation (d):

- The two already-fixed comments are tagged `already-addressed` with `next_action: reject`, and do not appear in the corrective backlog.
- The remaining two are triaged normally on the `must-fix` through `out-of-scope` scale.
- The output distinguishes this from dedup: dedup compares feedback to feedback, this compares feedback to the current state of the tree. Collapsing the two already-fixed items as "duplicates" is a FAIL.

All variations:

- The matrix shape, the corrective-only scope, and the conflict rule (an item reopening a locked decision routes to `decision-interview` or `post-review-pivot`) are unchanged by these folds.

## Failure modes caught

- Variation (b) is refused, demanding machine-detected terminality on a pasted payload. This is the load-bearing failure: D-5 requires completeness to be ESTABLISHED, not machine-detected, and an over-firing refusal makes the command unusable in its most common mode.
- Variation (a) builds a matrix anyway while checks are still running, producing a partial backlog that the command's own traceability makes look authoritative.
- Variation (c) waits for CI checks in `--playtest`, a mode that has none.
- Variation (d) collapses the two already-fixed items as duplicates. Dedup compares feedback to feedback; the `already-addressed` disposition compares feedback to the current state of the tree, and conflating them loses the distinction D-6 exists to draw.
- An `already-addressed` item that still enters the corrective backlog, or is tagged without `next_action: reject`.

## Notes

Written from `TEST_STRATEGY.md` rows S3 and S4 of task `2026-07-29_opensrc-greptile-technique-absorption`. Variation (b) carries the risk the fold introduces: D-5 adds a refusal, and the way a refusal fails in practice is by over-firing on legitimate input, not by letting something through.
