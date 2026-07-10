---
name: autonomous-board
description: Read-only board-of-record view for an autonomous-run task (ADR-0044 D7, wos/autonomous-track.md). Renders the run as the spec, the IMPLEMENTATION_PLAN waves and slices, and the TASK_STATE phases mapped to to-do / in-progress / escalated / proposed / done columns, sourced only from the Fhorja task artifacts. No external work tracker; no writes. Use when the maintainer wants a single-glance status of an autonomous run without opening every artifact. Do not use to change state (use sync-task-state), to assess a normal multi-slice task (use where-we-at), or to route the next command (use what-next).
metadata:
  category: state-and-navigation
  primary-cursor-mode: Ask
  multi-repo-aware: false
  context-layers-consumed: [memory]
  context-layers-produced: []
  tools: [Read, Bash, Glob, Grep]
  x-wos-profiles: [full]
  provenance: first-party
  token-budget: 1800
  suggested-model: claude-haiku-4-5
---
# autonomous-board

Act as a read-only status renderer for an autonomous delivery run.

Goal:
Render the current state of an `autonomous-run` task as a board of record, sourced only from the Fhorja task artifacts (the spec, `IMPLEMENTATION_PLAN.md` waves and slices, `TASK_STATE.md` phases, and `SLICES/` notes). This is the Fhorja-internal substitute for an external tracker (ADR-0044 D7): the spec plus the plan plus the phases already model the work, so this command only reads and arranges them. It performs no writes.

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
- IMPLEMENTATION_PLAN.md (waves and slices), TASK_STATE.md (phase, last completed step), SLICES/ notes if present
- last completed step from TASK_STATE.md (command + summary)

Operating rules:
- Do not implement code. Do not write any artifact; this command is read-only (`context-layers-produced: []`).
- Map each slice to one column: to-do, in-progress, escalated (boundary or test/eval slice awaiting the human gate), proposed (PROPOSED diff awaiting the merge gate), done (closed slice).
- Derive every cell from the artifacts only. Do not infer status that the artifacts do not support; mark unknown cells as unknown.
- Do not integrate or read an external work tracker (D7).
- Read `.wos/runs/*.json` (the ADR-0080 runs-feed v1 contract) as an additional source: when a feed file for this task exists, render a live-run line above the artifact-derived columns showing state, current_step, and last_update_ts, with a staleness note when last_update_ts is older than 15 minutes; when no feed file exists this changes nothing. This command still performs no writes to the feed.
- **Handoff:** end with the adaptive `### Handoff` block per `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract`.

Required output:
1. Run header: task, current phase, governor status if recorded, wave count
2. The board: one row per slice with its column, work complexity, and the EARS exit-criterion status
3. What is at a gate now (escalated slices, PROPOSED diffs awaiting merge)
4. Best next command and editor mode toward finishing the run

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
- The board is sourced only from the Fhorja task artifacts; no external tracker is read (D7).
- `### Artifact changes` is `None` (read-only command); no writes occur.
- Every slice maps to exactly one column; unsupported cells are marked unknown rather than guessed.
- Output ends with a complete `### Handoff` block per the adaptive format in `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract`.
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
A glanceable, honest status. Show what the artifacts prove and nothing more.

<!-- cache-breakpoint -->
