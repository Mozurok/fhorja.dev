# ADR-0003: NO_OP and NO_OP_TRACE semantics

- **Status**: Accepted
- **Date**: 2026-05-08
- **Tags**: no-op, idempotency, task-memory, churn-reduction

## Context

The workflow encourages calling the same command multiple times across a task's lifecycle: `sync-task-state` after every meaningful step, `state-reconcile` after heavy edits, `implementation-plan` after new evidence emerged, etc. Without explicit no-op semantics, two failure modes recurred:

1. **File churn**. A command run when nothing material had changed would still rewrite its target artifact (`IMPLEMENTATION_PLAN.md`, `TASK_STATE.md`, `PR_PACKAGE.md`). The `git diff` showed cosmetic edits (paragraph reordering, slight rewording) with no behavioral content. Reviewers had to read the diff to confirm there was nothing to review.
2. **Silent skips**. The opposite failure: when a command realized nothing material had changed, it would emit a short prose response ("nothing to do here") with no machine-readable trace. The next command in the chain had no signal that a no-op happened, so routing logic could not distinguish "ran and updated" from "ran and skipped".

The workflow needed two things:

- A way for any command to **decide it has nothing material to write** without breaking the response contract (Handoff still required, downstream routing still works).
- A way to **record that a no-op happened** so the audit trail in the conversation reflects every command that ran, even when it produced no diff.

## Decision

The workflow adopts two related markers, used inside the standard `### Command transcript` block:

- **`NO_OP`** is the conceptual state: the command ran and decided no material change is warranted.
- **`NO_OP_TRACE`** is the explicit 1-3 line transcript entry that records the decision. Format: a brief reason (one line is enough; "no material change vs current `IMPLEMENTATION_PLAN.md`"), and the routing forward (which command to run next, if different from the no-op'd one).

When any command's response is a no-op:

1. The `### Artifact changes` block lists `None` or marks every candidate file as `SKIP`.
2. The `### Command transcript` block contains `NO_OP_TRACE` followed by 1-3 lines.
3. The `### Handoff` block is still emitted in full (the contract from ADR-0002 is unconditional).
4. The `Reason:` line in the Handoff briefly notes the no-op (e.g., "plan unchanged; routing to slice execution").

The "material change" threshold is itself defined in the WOS `## Cross-cutting workflow guardrails` → `### Material change (definition)`. It is not a stylistic threshold; it is "would a reviewer's understanding of the task change if this rewrite were applied?".

Each `commands/*.md` that has artifact-write semantics declares its no-op rule explicitly in the `Operating rules:` section. Examples: `implementation-plan` (no rewrite if `IMPLEMENTATION_PLAN.md` matches current decisions), `pr-package` (no rewrite if PR package matches the current diff), `sync-task-state` (no rewrite if no meaningful progress occurred since the last sync).

## Consequences

### Positive

- The `git log` of any task folder reflects only meaningful changes. Reviewers do not waste attention on cosmetic diffs.
- The conversation transcript still records every command run, even no-ops. Audit completeness is preserved.
- Downstream routing has machine-readable signal: a `NO_OP_TRACE` in the transcript tells the next command (or the user reading the conversation) what happened and what to do next.
- The Handoff contract (ADR-0002) is preserved: every response, including no-ops, ends with a runnable next-step prompt.

### Negative

- Detecting "no material change" requires the model to compare the current artifact to what it would write. This is a non-trivial judgment, and a model that under-detects no-ops will still produce churn. The mitigation lives in each command's `### Definition of done` ("if the artifact would not materially change, do not rewrite it; emit `NO_OP_TRACE`").
- The vocabulary `NO_OP` / `NO_OP_TRACE` is workflow-specific. Users learning the workflow have to internalize it.

### Neutral

- The 1-3 line cap on `NO_OP_TRACE` is a soft rule; the exact length is judgment. Lint does not enforce it. Long `NO_OP_TRACE` blocks are worse than short ones but not incorrect.

## Alternatives considered

### Alternative 1: Always rewrite, always commit

- Every command always rewrites its target; the user reverts cosmetic diffs manually.
- Rejected: shifts churn cost to the user; reviewers stop reading task-folder diffs because most are noise; signal-to-noise ratio collapses.

### Alternative 2: Short-circuit no-ops with a separate command

- A `sync-if-changed` wrapper that decides whether to dispatch to `sync-task-state` based on a heuristic.
- Rejected: doubles the command count for a property that should be intrinsic to every write-emitting command. Also breaks symmetry: every command needs the no-op pattern, not just sync.

### Alternative 3: No-op without transcript marker

- A no-op response just emits `### Artifact changes: None` with a brief sentence in `### Command transcript`.
- Rejected: the explicit `NO_OP_TRACE` marker is searchable (`grep -r NO_OP_TRACE` across conversations) and machine-readable. Free-form prose is neither.

## References

- `WORKFLOW_OPERATING_SYSTEM.md` → `## Cross-cutting workflow guardrails` → `### No-op execution rule`, `### Material change (definition)`.
- `commands/_shared/command-transcript-standard.md` (canonical transcript shape, including the `NO_OP_TRACE` mention).
- `commands/_shared/command-transcript-lean.md` (lean variant for high-frequency commands like `capture-observation`).
- Every command file's `Operating rules:` and `### Definition of done (command output)` sections that mention no-op semantics.

## Notes

`NO_OP` and `NO_OP_TRACE` are workflow primitives, not Git or filesystem markers. They live in command output text, not in commit messages or file metadata. The decision to keep them as text-only (rather than encoding them as machine-readable JSON or YAML) is deliberate: the conversation is the audit surface, and humans should be able to read it without tooling.
