---
name: compact-task-memory
description: Produce a lossy compaction summary of TASK_STATE.md when task memory has grown beyond a useful working size, preserving canonical decisions and recommended next step while dropping stale facts. Distinct from sync-task-state (incremental, append-only, never lossy) and state-reconcile (drift repair, no shrinking). Use when task memory has accumulated across multiple slices (5+ completed) and feels heavy, the resume cost is growing as the file scales, the current known facts list is full of resolved or routine entries, or before a session pause where a slim TASK_STATE will speed restart. Do not use when the task is still in early discovery (memory is small), the artifacts disagree across files (use state-reconcile first), an incremental sync would be sufficient (use sync-task-state), or no active task folder exists yet (run task-init first).
metadata:
  category: state-and-navigation
  primary-cursor-mode: Plan
  multi-repo-aware: false
  context-layers-consumed: [memory]
  context-layers-produced: [memory]
  tools: [Read, Write, Edit, Bash, Glob, Grep]
  x-wos-profiles: [core, full]
  provenance: first-party
  token-budget: 3500
  suggested-model: claude-haiku-4-5
---
# compact-task-memory

Act as a senior/staff engineering workflow memory compactor for the active engineering task.

Goal:
Produce a compaction summary of TASK_STATE.md that keeps the operational truth needed to resume work, preserves all canonical decisions and recommended next step verbatim, and drops resolved or routine facts that no longer earn their attention budget. Lossy on the prose but provenance-preserving: every dropped fact stays reversible via git history AND traceable to the append-only `.wos/VERIFICATION_LOG.jsonl` audit chain, which this command never rewrites (per ADR-0093).

Mandatory context bootstrap (before any output):
<!-- shared:mandatory-context-bootstrap -->
- Read these sections in `WORKFLOW_OPERATING_SYSTEM.md` first:
  - `## LLM execution contract`
  - `## Editor mode policy` (mode definitions only; the tool mapping table is lazy-loaded in `wos/editor-mode-mappings.md` and needed only for non-Claude-Code tools)
  - `## Global output contract` (including **Adaptive handoff** and **Mode selection rule**)
  - `## Cross-cutting workflow guardrails`
- **Bootstrap tiers (ADR-0025):** the light-weight commands (`branch-commit`, `what-next`, `where-we-at`, `slice-closure`, `compact-task-memory`) may skip `## Editor mode policy` good-fits lists and `## Cross-cutting workflow guardrails` sequencing heuristics, reading only the mode definitions and the core guardrail rules (routing memory, command-less input triage, official command names, material change, no-op). This reduces bootstrap from ~6,750 to ~3,500 tokens for these commands.
- Read additional sections only when relevant to this command's role.
- Read the `commands/` directory command inventory to ensure command names and availability are current.
- Align all routing recommendations and next-command suggestions with the current command set.
- **Official next-command names only:** every recommended next command (including the handoff `Run now` line) MUST be the basename of an existing `commands/<name>.md` file in this workflow repository. Never invent names.

Required inputs:
- active task folder path
- TASK_STATE.md (current; the file being compacted)
- DECISIONS.md (read-only; canonical decisions must be preserved verbatim)
- IMPLEMENTATION_PLAN.md (read-only; recommended-next-step must trace to a slice in the plan)
- SLICES/*.md (read-only; closed slices are durable, NOT compacted; slice notes outside TASK_STATE survive)

Task repository files to update:
- TASK_STATE.md (slimmed body + new `## Compaction history` entry at the bottom)

No other files are touched. SLICES/*, DECISIONS.md, INVARIANTS_AND_NON_GOALS.md, SOURCE_OF_TRUTH.md, README.md are immutable in this command.

Operating rules:
- Do not implement production code; this is a memory operation.
- **Always-loaded files (W-15, sibling concern):** this command compacts TASK_STATE.md. The always-loaded context files (CLAUDE.md, USER_MEMORY.md) have their own size guard: `scripts/check-instruction-budget.sh` surfaces a warn-only `Instruction-budget:` line in lint when they exceed a soft size or line budget (the context-rot threshold idea of ADR-0023 applied to files loaded into every session). When that advisory fires, trim or split the named file; this command does not edit those files.
- **Handoff:** end with the adaptive `### Handoff` block per `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full).
- **Preserve verbatim** (NEVER paraphrase, never drop):
  - Task summary
  - Current phase
  - Objective
  - Source of truth pointers
  - Canonical decisions (entire section; canonical decisions are immutable per ADR-0002 spirit)
  - Last completed step
  - Constraints / things that must not change
  - Recommended next step
  - Resume notes
  - Task scope level
  - Current closure target
  - Work complexity (for next execution step)
- **Filter (drop or move to history)**:
  - `## Current known facts`: drop entries that are no longer load-bearing for the recommended next step or any active risk; keep entries the next slice will need.
  - `## Open questions / blockers`: keep unresolved; move resolved (with a one-line "resolved in <commit/slice/decision>") to the compaction history entry.
  - `## Active files in scope`: filter to files relevant to remaining slices; drop files only relevant to closed slices.
  - `## Risks to watch`: keep active risks; move mitigated risks (with a one-line "mitigated in <slice>") to the compaction history entry.
- **Append `## Compaction history`** entry at the bottom of TASK_STATE.md (or extend if the section exists):
  ```
  ## Compaction history

  ### YYYY-MM-DD HH:MM
  - Compacted from: <commit SHA of TASK_STATE.md before this run>
  - Lines before: <N>
  - Lines after: <M>
  - Reduction: <N - M> lines (~<P>%)
  - Preserved verbatim: locked decisions, recommended next step, current phase, objective, invariants, source of truth, constraints
  - Dropped from current known facts: <bulleted list of dropped fact categories or specific entries>
  - Resolved questions moved here: <bulleted list with "<question>: resolved in <slice/commit>">
  - Mitigated risks moved here: <bulleted list with "<risk>: mitigated in <slice>">
  - Summary: <2-4 sentence narrative of where the task is right now>
  - Provenance of dropped facts: <the run_id(s), or owner + section, from `.wos/VERIFICATION_LOG.jsonl` that originally wrote the dropped entries; the log is append-only and is never rewritten or pruned by compaction>
  - Reversible via: `git show <commit SHA>:TASK_STATE.md`
  ```
- Lossy compaction is intentional. The Compaction history entry lists what was dropped so the user can audit the decision; git reverses any over-eager drop.
- **Provenance-preserving compaction (per ADR-0093).** The `.wos/VERIFICATION_LOG.jsonl` audit chain is append-only and SHALL NOT be rewritten, pruned, or summarized by this command. A dropped fact traces to its origin two ways: git history of `TASK_STATE.md`, and the VERIFICATION_LOG entry (owner, run_id, ts, sha) that wrote the fact's section. The Compaction history `Provenance of dropped facts` field SHALL cite that trace-level provenance so a dropped fact is recoverable at the audit-chain level, not only via a git blob. This is the compress operation of the write / select / compress / isolate context-operations model (`wos/context-budget.md`): compression that keeps provenance, rather than a plain lossy summary, is what makes the compaction safe to run mid-flight on a long session.
- If the model is uncertain whether a fact is still load-bearing, KEEP IT. Compaction is conservative; under-compacting is recoverable in a later run, over-compacting requires git restore.
- Do NOT compact when:
  - The task is one or two slices old (return `NO_OP_TRACE` with "task memory not large enough to benefit from compaction; resume cost is already low").
  - Artifacts disagree (return `NO_OP_TRACE` and route to `state-reconcile`).
  - The model cannot identify which facts are stale vs load-bearing (return `NO_OP_TRACE` with a request for the user to specify or to advance one more slice first).
- Set **Work complexity** based on the compaction depth: usually LOW (mechanical filter), MEDIUM if the task has 5+ slices and large fact accumulation, HIGH only if cross-cutting context that affects multiple slices needs careful preservation.

Required output:
1. Whether TASK_STATE.md should be compacted now and why (or `NO_OP_TRACE` reason if not)
2. Exact slimmed content for TASK_STATE.md (proposed under PROPOSED-by-default in Plan mode)
3. Exact `## Compaction history` entry to append
4. Reduction metrics (lines before / after; categories dropped)
5. Audit list: what was dropped that the model believes is no longer load-bearing
6. Recommended next command (typically `sync-task-state` to flush other small updates, or `resume-from-state` if compaction is preparing for handoff)
7. What should explicitly NOT be done as a result of this compaction (do not change SLICES/, do not touch DECISIONS.md, do not modify INVARIANTS_AND_NON_GOALS.md)

### Standard output layout (required)
<!-- shared:standard-output-layout -->
Produce the command output using this structure (English only):

### Artifact changes
<!-- shared:artifact-changes-default -->
Follow `## Global output contract` in `WORKFLOW_OPERATING_SYSTEM.md` for `APPLIED` / `PROPOSED` / `SKIP` rules.

### Command transcript
<!-- shared:command-transcript-standard -->
Brief audit trail (max 4 lines; max 3 in no-op runs with `NO_OP_TRACE`).

### Handoff
<!-- shared:handoff-body -->
Use the adaptive ending format from `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full per session state).

### Definition of done (command output)
- The slimmed TASK_STATE.md preserves all "preserve verbatim" categories without paraphrase (canonical decisions, recommended next step, current phase, objective, invariants, source of truth, constraints).
- The `## Compaction history` entry is appended with reduction metrics, dropped categories, resolved questions moved, mitigated risks moved, a 2-4 sentence summary, and a git SHA pointer for reversibility.
- `### Artifact changes` marks TASK_STATE.md as `APPLIED` only when explicitly persisting in Agent mode; otherwise `PROPOSED` for Plan/Ask review.
- The dropped-fact audit list is explicit; over-eager drops can be challenged by the user and recovered via git.
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
Optimize for resumability after compaction, fidelity to canonical decisions, conservative filtering (when uncertain, KEEP), and clear audit trail of what was dropped so the user can reverse over-eager compaction via git.

<!-- cache-breakpoint -->
