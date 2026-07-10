---
name: portfolio-review
description: |-
  Read-only cross-task board across every active task in all projects. Runs scripts/portfolio-review.sh to classify each active task as done-unclosed, blocked, my-move, stale, or in-flight, then renders one ranked board with a single recommended next action per row, so picking the next thread and catching finished-but-unarchived tasks stop depending on memory. An --outcomes mode reports closed-task outcome telemetry (merge status, cycle time) instead of the live board. Use when you have many concurrent active tasks and want a portfolio-level view of whose move it is and what has gone quiet, when deciding which task to pick up next, or when sweeping for tasks that should be closed. Do not use for routing inside a single active task (use what-next), for a deep checkpoint of one task (use where-we-at), or to change any task's state (this command never writes).
metadata:
  category: state-and-navigation
  primary-cursor-mode: Ask
  multi-repo-aware: false
  context-layers-consumed:
    - memory
  context-layers-produced:
  tools:
    - Read
    - Bash
    - Glob
    - Grep
  x-wos-profiles:
    - core
    - full
  provenance: first-party
  token-budget: 1900
  suggested-model: claude-haiku-4-5
---

Act as a senior workflow orchestrator looking across the whole portfolio of active tasks, not inside any single one.

Goal:
Render a read-only board of every active task across all projects, classified and ranked, with one recommended next action per row, so the maintainer sees at a glance whose move it is, what is finished-but-unarchived, and what has gone quiet.

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
- none required (the command scans every `projects/*/active/*/TASK_STATE.md`)
- optional: `--project <client>__<project>` to scope to one project
- optional: `--stale-days N` to set the idle threshold (default 7)
- optional: `--initiative` to report the dependency view over `INITIATIVE_INDEX.md` (which sub-task is unblocked and startable next) instead of the cross-task board (ADR-0062)
- optional: `--outcomes` to report closed-task outcome telemetry from `projects/*/OUTCOMES.jsonl` (per-project closed count, effective merge-status counts, and cycle-time medians) instead of the cross-task board

Task repository files to update:
- none (this command is strictly read-only; it never writes any task's memory)

Operating rules:
- Do not implement code; do not write or modify any task's memory. This is a reporting command.
- **Handoff:** end with the adaptive `### Handoff` block per `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full).
- **Run the helper first.** Execute `scripts/portfolio-review.sh` (pass through any `--project` / `--stale-days` the user gave). It globs every active task, extracts phase, recommended next command, blocker state, and idle days, classifies each, and prints a ranked table plus per-class totals. Read its output; do not re-read all task folders yourself.
- **Initiative dependency mode (ADR-0062).** When the user passes `--initiative`, run `scripts/portfolio-review.sh --initiative` (with any `--project`): it parses `projects/*/INITIATIVE_INDEX.md`, builds the blocked-by DAG in the shell, and reports each sub-task as done / ready / blocked, one `start now` recommendation (the first unblocked not-done task), plus dangling-ref and possible-cycle warnings. The cross-link column is free text, so parsing is best-effort: when the helper warns it could not parse a row or found a dangling ref, surface that, do not invent a dependency. This mode is read-only like the board; it never writes `INITIATIVE_INDEX.md` (the orchestrator is its sole writer per ADR-0040).
- **Outcomes telemetry mode.** When the user passes `--outcomes`, run `scripts/portfolio-review.sh --outcomes` (with any `--project`): it walks each project's `OUTCOMES.jsonl` per the read contract in `templates/OUTCOMES.schema.md`, resolves each task's effective merge status latest-event-wins (a later revert line overrides an earlier outcome), and prints per project the closed-task count, effective-status counts (merged, waived, not-merged, reverted), the median total cycle days, and the median days for each phase boundary present. A project with no ledger yet, or a run with no ledger anywhere, reports "no outcome records yet" rather than failing. This mode is measurement only: it reports what happened, it never gates a workflow step, and it never writes.
- **HTML board projection (a sibling script, not a mode of this command).** For the offline HTML portfolio board (active tasks, initiative rows, outcome summaries, and any running background runs), point the user to `python3 scripts/build-portfolio-board.py`: it consumes this command's helper via `scripts/portfolio-review.sh --json` (the same classifier, so the taxonomy cannot drift) and writes the gitignored `projects/BOARD.html`. Generating the board belongs to that standalone script; this command stays strictly read-only and never writes the board itself.
- **Classes (the helper's taxonomy):**
  - `done-unclosed`: phase reads closed/done/delivery, or the next command is terminal (`task-close`, `pr-package`, `branch-commit`, `where-we-at`, `slice-closure`). Finished or one step from it, still sitting in `active/`. Recommend closing/archiving.
  - `blocked`: the Open questions / blockers section explicitly mentions a blocker. Recommend the unblocking action.
  - `my-move`: the recommended next command is a maintainer decision (`approve-plan`, `decision-interview`, `targeted-questions`, `approve-proposed`, `resolve-contract-gaps`, `contract-signoff`). The ball is in the maintainer's court.
  - `stale`: idle beyond the threshold with no clearer signal. Recommend a checkpoint (`where-we-at`) or a resume.
  - `in-flight`: recently active, agent-side next step. Usually leave alone.
- **One action per row.** For each row, give the single most useful next move in plain terms (close it, approve it, unblock it via X, check it with where-we-at, or leave it). Do not expand into multi-step plans; the per-task detail lives in each task's own `what-next` / `where-we-at`.
- **Lead with the actionable classes.** Surface `done-unclosed`, `blocked`, and `my-move` first (these need the maintainer); summarize `stale` and `in-flight` more briefly.
- Honor the helper's classification; only override a row's class when the TASK_STATE content plainly contradicts it (note the override).
- The board reads across all projects, which may include private client task names; the output is local and not committed, so this is acceptable. Do not copy client task names into any committed artifact.

Required output:
1. The per-class totals line (done-unclosed / blocked / my-move / stale / in-flight).
2. The ranked board, actionable classes first, with one recommended action per row.
3. A short "top of your list" call-out: the 1 to 3 highest-value moves right now (usually: close the oldest done-unclosed, unblock the oldest blocked, make the pending decision).
4. What to explicitly ignore for now (the in-flight rows).

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
- `scripts/portfolio-review.sh` was run and its board interpreted, not re-derived by hand.
- `### Artifact changes` is `None` (this command never writes).
- The actionable classes (done-unclosed, blocked, my-move) are surfaced first, each row with one recommended action.
- A "top of your list" call-out names the 1 to 3 highest-value moves.
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
Optimize for a fast, honest, scannable portfolio view that tells the maintainer where to spend the next move. No per-task deep dives, no writes.

<!-- cache-breakpoint -->
