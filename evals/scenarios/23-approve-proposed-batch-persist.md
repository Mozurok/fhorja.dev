# Eval scenario 23: /approve-proposed persists prior turn's PROPOSED files atomically

- **Tags**: approve-proposed, batch-persist, proposed-by-default, addendum-adr-0024, atomic-write
- **Last reviewed**: 2026-05-19
- **Status**: active

## Goal

Validate the canonical batch-persist idiom introduced in ADR-0024. The user reviews proposed artifacts in Ask/Plan mode, then runs `/approve-proposed` once; every PROPOSED file with fully inline content is written in a single turn, with a locked-format recap. Drift here breaks the "single command to close the proposed-mode loop" property that addresses the first real-world session friction.

## Setup

Fixture task folder under `projects/<test_client>__<test_project>/active/2026-05-19_test-fixture/`. The folder pre-exists with the following:

- `TASK_STATE.md` (current on-disk):

```markdown
# TASK_STATE

## Current phase
planning

## Canonical decisions
- D1: Use Postgres [LOCKED]

## Source of truth
- (placeholder)
```

- `IMPLEMENTATION_PLAN.md` (current on-disk):

```markdown
# IMPLEMENTATION_PLAN

(placeholder; needs first slice plan)
```

- `DECISIONS.md` (current on-disk):

```markdown
# DECISIONS

## Locked
- D1: Use Postgres
```

The conversation history ALREADY CONTAINS one prior assistant turn (the "source-of-truth turn") that emitted an `### Artifact changes` block with these contents:

```markdown
### Artifact changes
- `projects/<test_client>__<test_project>/active/2026-05-19_test-fixture/TASK_STATE.md` (PROPOSED):

  # TASK_STATE
  ## Current phase
  planning
  ## Canonical decisions
  - D1: Use Postgres [LOCKED]
  ## Source of truth
  - WORKFLOW_OPERATING_SYSTEM.md
  - real codebase
  ## Pending decisions
  - D2: Sync or async webhook processing?

- `projects/<test_client>__<test_project>/active/2026-05-19_test-fixture/IMPLEMENTATION_PLAN.md` (PROPOSED):

  # IMPLEMENTATION_PLAN
  ## Slice 1: scaffold service
  - create Postgres schema
  - boot the service
  ## Slice 2: webhook handler
  - depends on D2

- `projects/<test_client>__<test_project>/active/2026-05-19_test-fixture/DECISIONS.md` (PROPOSED):

  # DECISIONS
  ## Locked
  - D1: Use Postgres
  ## Pending
  - D2: Sync or async webhook processing? [PROPOSED: async]
```

## Input prompt

```text
Run @commands/approve-proposed.md against projects/<test_client>__<test_project>/active/2026-05-19_test-fixture/.
```

(The user types this AS THE NEXT TURN after the prior assistant turn shown above. No other input.)

## Expected response shape

- Response's `### Artifact changes` block lists exactly three files, each marked `APPLIED`:
  - `TASK_STATE.md` (APPLIED)
  - `IMPLEMENTATION_PLAN.md` (APPLIED)
  - `DECISIONS.md` (APPLIED)
- No inline content under each bullet (content already lived in the prior turn; restating it doubles tokens).
- `### Command transcript` block contains exactly one line: `Persisted: TASK_STATE.md, IMPLEMENTATION_PLAN.md, DECISIONS.md`. No other recap lines (none were skipped).
- Summary line stating "3 files persisted, 0 skipped" (or equivalent shape).
- `### Handoff` block with `Run now:`, `Mode:`, `Work complexity:`, `Reason:`, routing to the natural follow-up (typically `/where-we-at` or `/implement-approved-slice` since the plan now exists).
- No `### PROPOSED file updates` block, no nested `## PROPOSED X.md block` headers, no re-emission of the prior turn's inline content.
- After the turn, the on-disk files match the prior turn's proposed content exactly:
  - `TASK_STATE.md` now has the new `## Source of truth` and `## Pending decisions` sections (was placeholder before).
  - `IMPLEMENTATION_PLAN.md` now has Slices 1 and 2 (was placeholder before).
  - `DECISIONS.md` now has a `## Pending` section with D2 (had only `## Locked` before).

## Pass criteria

1. All three target files exist on disk after the turn with content matching the prior turn's proposal byte-for-byte (ignoring trailing newline).
2. `### Artifact changes` lists all three files with `APPLIED` (zero `PROPOSED`, zero `SKIP`).
3. `### Command transcript` contains exactly one `Persisted:` line naming all three files; no other recap lines.
4. Response body does NOT re-emit the inline file contents from the prior turn (verifiable via length: response should be < 1500 chars; if > 3000, content was almost certainly re-emitted).
5. Response does NOT propose new artifacts beyond what the prior turn proposed (no D3, no Slice 3, no IMPACT_ANALYSIS.md).
6. `### Handoff` block is present per the spec adaptive handoff contract (Mode A or Mode B).

## Failure modes to watch

- **Re-emit inline content (HIGH priority)**: response repeats the full proposed content of all three files in `### Artifact changes`. Wastes tokens and defeats the recap purpose. The point of `/approve-proposed` is to acknowledge what landed without re-emitting it.
- **Mark APPLIED but skip the write**: response says APPLIED in the block but no actual Write tool call fires. Files on disk stay placeholder. Detect by comparing pre/post file content.
- **Per-file separate turns**: model splits the persist across multiple turns or interleaves prose between Write calls. Should be one atomic batch.
- **Walk back to older Artifact-changes turns**: model finds an older PROPOSED block from earlier in the chat and persists THAT instead of (or in addition to) the most recent one. Source-of-truth turn rule must be "latest only".
- **Conflict-rollback skipped**: if the proposed `TASK_STATE.md` had contradicted the locked D1 (e.g., changed it to Postgres -> MySQL), the command should FAIL with a clear error and persist NOTHING. A scenario variant should test this; for this scenario, no conflict exists.
- **No-PROPOSED-block silent success**: if the prior turn happened to have all `APPLIED` (everything already persisted), the command must emit NO_OP_TRACE explaining "no PROPOSED files in prior block". Silent success is invalid.
- **Path resolution failure**: paths in the prior block must resolve to inside the active task folder OR `my_work_tasks/`. Persisting to absolute paths (`/Users/...`) or paths outside the workspace is forbidden.

## Notes

- Related ADRs: [ADR-0024](../../docs/adr/0024-approve-proposed-idiom.md) (the idiom this scenario validates), [ADR-0001](../../docs/adr/0001-proposed-by-default.md) (the contract this idiom complements), [ADR-0011](../../docs/adr/0011-shared-canonical-blocks.md) (the no-nest rule the parser depends on).
- Related commands: `commands/approve-proposed.md` (under test), `commands/_shared/artifact-changes-default.md` (no-nest rule).
- Origin: slice 2 of the 2026-05-19 proposed-mode-fixup task. The 2026-05-18 real-world session showed the absence of this idiom is the root cause of "I can't tell what's on disk" friction.

## History

(empty - scenario introduced 2026-05-19; should run during slice 2 closure and once more before tagging v0.2.1)
