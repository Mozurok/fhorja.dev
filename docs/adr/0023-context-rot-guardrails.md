# ADR-0023: Context-rot guardrails

- **Status**: Accepted
- **Date**: 2026-05-18
- **Tags**: context-engineering, context-rot, per-phase-thresholds, informational-warning, locked-thresholds

## Context

The Chroma `Context-Rot` report (2024-2025) showed that all models degrade as input length grows regardless of stated context window size; even when the context fits, the model's attention dilutes. Slice 02 of the 2026-05-15 context-engineering uplift (ADR-0013) made per-command token cost visible. Slice 04 (ADR-0015) introduced `compact-task-memory` for lossy working-memory compaction with audit trail. Together they gave the workflow the framework to ACT on context-rot, but the framework stayed passive: nothing told the user WHEN to act.

Three failure modes the passive framework creates:

1. **Working memory grows silently**. A user can let `TASK_STATE.md` grow to 10k+ tokens without realizing it; resume cost grows; degradation creeps in. The user has tools (`compact-task-memory`) but no signal of when to use them.
2. **Blanket thresholds are noisy**. A single "TASK_STATE > N tokens" warning ignores phase context. A task in implementation legitimately accumulates state across slices; a task in discovery should have a smaller working memory. The warning needs phase awareness to be useful.
3. **The Chroma finding wants action**. Empirical degradation grows with length; the WOS has the framework; the action is to surface the cost when it crosses phase-aware thresholds.

Slice 13 closes this loop. The thresholds are heuristic but locked at slice authoring; future revisions go through an ADR addendum.

## Decision

The WOS adopts per-phase context-rot guardrails:

1. **Five phases, five thresholds (locked at slice 13)**:
   - `discovery`: 3000 tokens
   - `planning`: 5000 tokens
   - `implementation`: 8000 tokens
   - `review` / `closure`: 6000 tokens
   - `delivery`: 6000 tokens
2. **Three commands warn**: `sync-task-state`, `where-we-at`, `resume-from-state`. These are the commands users invoke when they want to know operational state; surfacing the cost there is the right moment. Other commands (e.g., `task-init`, `implement-approved-slice`) do NOT warn; the cost surfaces during state interactions, not authoring.
3. **Warning text is a fixed template**: `WARN: TASK_STATE.md is ~Ntokens (phase threshold: Mthreshold). Consider running compact-task-memory before continuing.` Commands do not paraphrase.
4. **Informational, not blocking**. The warning is one line in `### Command transcript`; the command proceeds with its normal output. No NO_OP; no FAIL; just a surfaced cost.
5. **Compaction-history exclusion**. The token count for the threshold comparison EXCLUDES the `## Compaction history` section of TASK_STATE.md. That section grows monotonically as past compactions accumulate; counting it against the threshold would penalize tasks that have already done their part.
6. **Suppression after compact**. If the immediately prior step was `compact-task-memory`, the warning is suppressed for the current run. Double-noise avoided.
7. **Default-safe behavior for unknown phases**. If a command sees a phase value not in the table (a future phase added without updating this section), no warning is emitted. The threshold lookup is permissive; missing entries are treated as "no threshold".

## Consequences

### Positive

- **Visible context-rot cost**. The Chroma finding is now actionable: users see the cost during state interactions and can compact when ready.
- **Phase-aware noise reduction**. A discovery-phase task with 3500 tokens warns; an implementation-phase task with the same size does not. The warning is meaningful when it fires.
- **Closes the slice-02 / slice-04 loop**. The token-budget framework (slice 02) and the compaction command (slice 04) now have a trigger: warnings tell the user when to use them. The full discipline is in place.
- **Empirically grounded**. The Chroma report is the empirical motivation; the thresholds are heuristic but defensible per the phase rationale in `wos/context-budget.md`.

### Negative

- **Thresholds are heuristic**. The 3000 / 5000 / 8000 / 6000 / 6000 numbers are reasonable but not derived from per-task measurement. Mitigation: locked at slice 13; revisable via ADR addendum once usage data justifies adjustment.
- **3 commands' token budgets may need bumping** after the new Operating rule lands. Mitigation: re-measure post-edit; bump where needed per ADR-0013 process.
- **Warning is ignorable**. A user who wants to plow through a 10k-token TASK_STATE will see the warning every run and ignore it. Mitigation: warnings only; user retains control; future iteration could escalate to FAIL at extreme thresholds (e.g., 2x the phase threshold), but that decision lives in a future ADR.

### Neutral

- The warning lives in `### Command transcript` (the standard place for operational notes). No new section; no contract change.
- The five-phase table covers all current phase values from `TASK_STATE.md ## Current phase`. If a future phase is added (e.g., "evaluation"), the table needs a new row; the default-safe behavior covers the gap.

## Alternatives considered

### Alternative 1: hard FAIL on threshold crossing

- Commands fail when TASK_STATE.md exceeds the phase threshold; the user must run `compact-task-memory` first.
- **Rejected**: too aggressive. Some legitimate tasks may exceed the threshold without needing compaction (e.g., a one-shot retrospective task with 30+ slices that genuinely needs full memory inline). Warnings preserve user agency; FAIL would force the user to fight the contract.

### Alternative 2: blanket threshold (no phase awareness)

- One number (e.g., 6000 tokens); warn when exceeded regardless of phase.
- **Rejected**: noisy in implementation; silent in discovery. Phase-aware thresholds are the same complexity (one extra lookup) with materially better signal.

### Alternative 3: warn on EVERY command, not just 3

- Every command emits the warning when applicable.
- **Rejected**: noise. The 3 state-and-navigation commands are where users naturally check state; warning there is the right moment. Warning during slice execution (`implement-approved-slice`) or PR prep (`pr-package`) is off-tempo.

### Alternative 4: lint-level threshold enforcement

- `scripts/lint-commands.sh --task-state-cost <path>` would emit the warning at lint time, not at command run time.
- **Rejected for this slice**: the WOS lint operates on `commands/*.md`, not per-task TASK_STATE.md. Adding task-level lint would require a new tool surface (per-task linter). Out of scope; commands surfacing the warning at runtime is the right placement.

### Alternative 5: auto-trigger `compact-task-memory`

- When the threshold is exceeded, automatically run compact-task-memory.
- **Rejected**: violates user agency. Compaction is lossy; user must approve. The warning surfaces the cost; the user decides when to act.

## References

- `wos/context-budget.md ## Context-rot thresholds` (the lazy-loaded locked table and warning policy).
- `commands/sync-task-state.md`, `commands/where-we-at.md`, `commands/resume-from-state.md` (the 3 commands implementing the warning guard).
- `commands/compact-task-memory.md` (the response action the warning recommends).
- ADR-0006 (lazy-load WOS pattern; the system-layer compaction technique).
- ADR-0012 (context budget; names the `memory` layer this slice operates on).
- ADR-0013 (per-command token budget; the per-command analogue at one tier below).
- ADR-0015 (working-memory compaction; the response action).
- ADR-0017 (reflexion-style learnings; the optional Learnings section that contributes to TASK_STATE growth).
- Chroma Research, "Context-Rot: How Increasing Input Tokens Impacts LLM Performance" (2024-2025): empirical evidence that motivates the warning.
- Anthropic, "Effective context engineering for AI agents" (Sep 2025): the broader framing of compaction as a context-engineering discipline.

## Notes

The locked thresholds (3000 / 5000 / 8000 / 6000 / 6000) are heuristic. They reflect a reasonable working assumption that:

- Discovery should converge; persistent high-volume facts mean the discovery phase is not converging (decisions undeferred; questions unresolved).
- Planning's volume comes from the plan structure itself (slices, dependencies, risks); 5000 is a defensible plateau.
- Implementation legitimately accumulates state per slice closure; 8000 accommodates ~6-8 closed slices before a compaction is recommended.
- Review and delivery should be slim; if state is heavy at these phases, un-closed slices or unresolved questions are likely accumulating.

Future revisions can adjust these numbers through an ADR addendum. The mechanism for adjustment: a contributor or eval surfaces a per-phase distribution where the current threshold either over-warns (discovery thresholds firing on legitimate state) or under-warns (implementation reaching 12k tokens without a warning). The ADR addendum updates both this Notes section AND `wos/context-budget.md ## Context-rot thresholds` in lockstep.

Slice 13 closes Wave 4 and closes the entire 2026-05-15 context-engineering uplift task. After this slice's commit, the task moves to closure: where-we-at macro checkpoint for the final retrospective, then archive.
