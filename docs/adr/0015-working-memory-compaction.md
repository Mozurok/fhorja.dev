# ADR-0015: Working-memory compaction via `compact-task-memory`

- **Status**: Accepted
- **Date**: 2026-05-15
- **Tags**: context-engineering, working-memory, compaction, memory-layer, command-introduction

## Context

Slice 01 of the 2026-05-15 context-engineering uplift named the six context layers (ADR-0012). Slice 02 quantified per-command cost with `token-budget:` (ADR-0013). Slice 03 surfaced cache boundaries with the cache-breakpoint marker (ADR-0014). Wave 1 closed with the qualitative + quantitative + cache halves of the context-budget contract in place.

Wave 2 opens with the memory layer. The `memory` layer (per ADR-0012's six-layer model) is the persistent state that survives across turns: task memory (`TASK_STATE.md`, `DECISIONS.md`, `SLICES/*`, etc.), project memory (`PROJECT_CHARTER.md`, `REFERENCES.md`), and the planned user memory (slice 05).

Task memory grows monotonically by design. Each closed slice adds entries to `## Current known facts`, may add risks, may resolve open questions, and updates the recommended next step. After 5+ slices a typical TASK_STATE.md is heavy: many of the entries are routine (resolved questions, mitigated risks, files in scope that only matter to closed slices). The Chroma `Context-Rot` report (2024-2025) shows that all models degrade as input length grows regardless of stated context window size; even when the context fits, the model's attention dilutes.

Three failure modes the absence of compaction creates:

1. **Resume cost grows linearly with task age**. A new session resuming a 10-slice task has to scan a long TASK_STATE.md plus 10 slice notes. The model's first move is essentially "summarize what I just read"; compaction does this once and persists the summary.
2. **Cache invalidation on every TASK_STATE edit propagates**. The `memory` layer is dynamic; cache-control directives ahead of it remain valid, but the layer itself is re-read each turn. Concentrating dynamic edits in one compacted body reduces the working surface.
3. **Stale facts compete for attention**. `## Current known facts` filled with entries that were once load-bearing but are now routine (e.g., "tier values silver / gold / platinum match the customer record" once D-1 is locked) dilute the model's focus on what is actually pending.

Existing commands cover incremental update (`sync-task-state`) and drift repair (`state-reconcile`), but neither shrinks memory. Compaction needs to be a distinct command with explicit lossy semantics and an audit trail.

## Decision

The WOS introduces a new command `commands/compact-task-memory.md`:

1. **Lossy by design, audit-trail required**. Compaction drops resolved facts, mitigated risks, and resolved questions. The dropped categories are listed verbatim in a new `## Compaction history` entry at the bottom of `TASK_STATE.md` so the user can audit (and challenge via git) any over-eager filtering.
2. **Preserved verbatim, never paraphrased**: canonical decisions (DECISIONS.md unchanged; the TASK_STATE.md cross-references stay verbatim), recommended next step, current phase, objective, invariants, source of truth pointers, constraints, last completed step, resume notes, task scope level, current closure target, work complexity.
3. **Filtered**: current known facts (drop entries not load-bearing for the recommended next step or any active risk), open questions / blockers (keep unresolved; move resolved to history), active files in scope (drop closed-slice-only files), risks (keep active; move mitigated to history).
4. **Reversible via git only**. Compaction is a one-way edit at the file level; the prior TASK_STATE.md content is recoverable via `git show <SHA>:TASK_STATE.md`. The Compaction history entry records the SHA.
5. **No side effects on other artifacts**. SLICES/*, DECISIONS.md, INVARIANTS_AND_NON_GOALS.md, SOURCE_OF_TRUTH.md, README.md are NOT touched. The command operates only on TASK_STATE.md.
6. **NO_OP semantics**. The command returns `NO_OP_TRACE` when (a) the task is too young (memory not yet heavy), (b) artifacts disagree (route to `state-reconcile` first), or (c) the model cannot identify which facts are stale vs load-bearing.
7. **Primary editor mode: Plan**. Compaction is a structural rewrite that benefits from PROPOSED-by-default review (the user verifies the slimmed body before APPLIED).
8. **Distinct from existing commands**. `sync-task-state` is incremental and never lossy; `state-reconcile` repairs drift but does not shrink; `resume-from-state` reconstructs from existing memory. Compaction is the only command that shrinks.

## Consequences

### Positive

- **Resume cost stays bounded**. Even for long-running tasks (10+ slices), the post-compaction TASK_STATE.md fits a small fraction of the context window. The Chroma `Context-Rot` finding (degradation with length) is materially mitigated.
- **Cache hit ratio improves**. The `memory` layer's volatile portion is concentrated in one compacted body; cache-control directives ahead of it benefit from a slimmer dynamic surface.
- **Audit trail makes lossy edits reversible**. The Compaction history entry plus git SHA pointer mean a user can recover any dropped fact within minutes. Lossy compaction without audit is what most teams refuse to adopt; the audit removes that friction.
- **One-way edit discipline**. The command is genuinely lossy: this prevents drift between "what we compacted" and "what's still active". Reversibility is via git, not via a parallel uncompacted file.
- **Distinct from siblings, easy to choose**. The decision tree (incremental? -> sync-task-state; disagreement? -> state-reconcile; heavy? -> compact-task-memory) is mechanical.

### Negative

- **One more command to know**. The WOS surface grows from 35 to 36 commands. The category (state-and-navigation) is unchanged.
- **Lossy compaction risks**. If the model under-filters, the compaction does nothing useful; if it over-filters, the user has to restore via git. Mitigation: PROPOSED-by-default in Plan mode (user reviews before APPLIED); audit entry lists drops explicitly; conservative rule ("when uncertain, KEEP").
- **Threshold for auto-trigger is deferred to slice 13**. For now, the command is user-invoked. Some tasks may accumulate stale facts that the user does not notice; auto-trigger via context-rot guardrails closes this loop.
- **Token cost of the command file itself**. `compact-task-memory.md` is ~3-4k tokens (a full canonical command). Per ADR-0013's per-command budget, this is within the typical cluster.

### Neutral

- The compaction does not change the SLICES/ contents; closed slice notes are commit-correlated history and stay durable. Only the working TASK_STATE.md is rewritten.
- The Compaction history section grows as a task ages. Multiple compactions in a long-running task each add an entry; this is intentional (the history of compactions is itself memory).

## Alternatives considered

### Alternative 1: auto-compact on threshold (no user invocation)

- The model auto-compacts when TASK_STATE.md crosses a token threshold; user never invokes manually.
- **Rejected for this slice; partially adopted in slice 13**. Auto-trigger without user awareness is opaque; a slimmed TASK_STATE that the user did not approve is a trust violation. Slice 13 will add a WARNING when the threshold is crossed, recommending the user run `compact-task-memory`. Auto-execution without explicit consent is not planned.

### Alternative 2: never compact, just archive closed slices and add new ones

- Append-only memory; old facts archive when the slice closes but never get filtered.
- **Rejected**: archiving moves bytes but does not shrink the working set. The user still has to scan archived content to know what is and is not active. Compaction's value is exactly the active vs archived filter.

### Alternative 3: compact via state-reconcile extension

- Extend `state-reconcile` with a `--compact` mode that includes shrinking.
- **Rejected**: conflates two different intents. Reconcile fixes disagreement (which assumes correctness can be recovered from cross-checking artifacts); compaction fixes growth (which assumes artifacts agree). Mixing them produces a command no one can reason about.

### Alternative 4: keep TASK_STATE.md small from the start (no compaction needed)

- Be strict during `sync-task-state` runs about not appending non-essential entries.
- **Rejected**: requires every contributor to predict what will be load-bearing later. Compaction is a deferred decision (we know what was load-bearing AFTER the slice closed, not during); a strict append-time rule cannot know.

## References

- `commands/compact-task-memory.md` (the canonical command).
- `wos/context-budget.md ## When to compact each layer` (the lazy-loaded narrative; mentions this command).
- `WORKFLOW_OPERATING_SYSTEM.md ## Command roles` (compact-task-memory row).
- `commands/sync-task-state.md` (sibling; incremental, never lossy).
- `commands/state-reconcile.md` (sibling; drift repair, no shrinking).
- ADR-0006 (lazy-load WOS pattern; the system-layer analogue of memory-layer compaction).
- ADR-0012 (context budget as explicit contract; names the `memory` layer this slice operates on).
- ADR-0013 (per-command token budget; tells us when memory is heavy).
- ADR-0023 (`context-rot guardrails`; the per-phase warnings that recommend running `compact-task-memory` when `TASK_STATE.md` exceeds the phase threshold).
- Anthropic, "Effective context engineering for AI agents" (Sep 2025): compaction and sub-agent strategies for long-running tasks.
- Chroma Research, "Context-Rot" (2024-2025): empirical evidence that degradation depends on input length, not just window size.
- Mem0, "Building Production-Ready AI Agents with Scalable Long-Term Memory" (ECAI 2025): working memory layer in the memory pyramid.

## Notes

The command is the first new command introduced by the 2026-05-15 context-engineering uplift (slices 01-03 modified existing commands; slice 04 introduces compact-task-memory). Slice 05 (USER_MEMORY.md) does NOT introduce a new command; it introduces a new memory artifact and updates existing commands to consume it. Slice 10 (self-critique-and-revise) and slice 12 (reflexion-style learnings template) bring the new-command count for this uplift to 2-3 by closure.

The "lossy by design + audit trail + git reversibility" pattern may be reusable for future memory-shrinking commands (e.g., a future `compact-references` if `REFERENCES.md` ever grows past a useful size). For now, no other compaction command is planned; the precedent is the pattern.
