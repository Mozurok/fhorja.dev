---
name: harvest-session-learnings
description: Scan the current working session and the active task's artifacts for reusable, generalizable lessons (what was tried, what failed and why, what surprised us, what the next task should do differently) and propose anchored entries to append to the task's LEARNINGS.md, the produce-side counterpart to the ADR-0017 consume path that task-init already reads. Append-only and read-only on existing entries; de-duplicates against what is already captured; keeps durable lessons and drops one-off task trivia. Use on demand mid-task after a hard-won fix or a surprising failure, or at closure to sweep a long session before the context is lost. Do not use to rewrite or prune existing learnings (never edit prior entries), to capture a single in-flight observation (use capture-observation), to close a slice or the task (use slice-closure or task-close), or when nothing durable was learned (return a NO_OP rather than manufacturing a lesson).
metadata:
  category: execution-and-closure
  primary-cursor-mode: Ask
  multi-repo-aware: false
  context-layers-consumed: [memory]
  context-layers-produced: [memory]
  tools: [Read, Write, Edit, Bash, Glob, Grep]
  x-wos-profiles: [core, full]
  provenance: first-party
  token-budget: 2300
  suggested-model: claude-sonnet-4-6
---
# harvest-session-learnings

Act as a senior/staff engineer running a focused retrospective sweep over the current session, distilling only the lessons worth carrying into future tasks.

Goal:
Read the working session and the active task's artifacts, extract the reusable lessons (tried X, it failed because Y, next time Z), and propose anchored entries to append to the task's `LEARNINGS.md`. This is the produce-side counterpart to ADR-0017: `task-init` already reads prior LEARNINGS to seed a new task; this command is one explicit way those entries get written, complementing the inline `### Learnings` that `slice-closure` captures per slice.

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
- TASK_STATE.md (for the task arc: phase, last completed step, blockers, observations)
- the working session itself (what was attempted in this conversation, what failed, what was surprising, what was corrected)
- relevant task artifacts when present: `SLICES/*.md`, `DECISIONS.md`, `IMPLEMENTATION_PLAN.md`, `PR_PACKAGE.md`
- the existing `LEARNINGS.md` (read-only, for de-duplication; created from `templates/LEARNINGS.md` if absent)

Task repository files to update:
- `projects/<client>__<project>/active/<task>/LEARNINGS.md` (APPEND-ONLY; this command never edits or prunes existing entries, per ADR-0017 item 6)

Operating rules:
- Do not implement production code. Do not change any other task-memory file (no `TASK_STATE.md` edits here; route to `/sync-task-state` if state moved).
- **Handoff:** end with the adaptive `### Handoff` block per `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full).
- **Append-only, read-only on history (ADR-0017).** This command ONLY appends new entries. It MUST NOT edit, reword, reorder, compact, or prune any existing `LEARNINGS.md` entry. Compaction of LEARNINGS is out of scope for every command (ADR-0017 item 6); a harvest that rewrites history is invalid output. This command holds the `Edit` tool to append below the last entry, so the append-only invariant is enforced by this rule, not by tooling: before emitting, confirm no existing entry's bytes changed (only new lines were added at the end).
- **A learning is reusable, not a task log.** Admit an entry ONLY when the lesson generalizes beyond this one task: a failed approach and why it failed, a non-obvious constraint, a tool or environment gotcha, a sequence that worked when the obvious one did not. Reject one-off task status, decisions already recorded in `DECISIONS.md`, and restatements of the plan. When the session produced nothing durable, return a NO_OP rather than manufacturing a lesson (ceremony is the failure mode this rule prevents).
- **Anchor every entry.** Each proposed entry MUST anchor at the exact point it came from (`file:line`, a slice section header, a command name, or a timestamped `TASK_STATE.md` row) and follow `templates/LEARNINGS.md` `## Entry shape`. An entry that is a retrospective summary with no anchor is disqualified, not appended (same bar `slice-closure` applies to inline learnings). Emit an optional `Tags:` line (comma-separated keywords) on each entry so `rank-learnings.sh` can surface it for a future task (ADR-0071).
- **De-duplicate against existing entries.** Before proposing, read the current `LEARNINGS.md` and drop any candidate already captured (the same lesson at the same anchor, comparing anchors case-insensitively and with surrounding whitespace normalized so a trivially reformatted anchor is still caught). Surface near-duplicates as "already captured" in the transcript rather than re-appending; LEARNINGS is cumulative, not a changelog of re-discoveries.
- **Stay inside one task.** Write only to the active task's `LEARNINGS.md`. A lesson that is genuinely cross-project belongs in `USER_MEMORY.md` (ADR-0016); name it in the output as a pointer for the user to promote, but do not write `USER_MEMORY.md` yourself. Likewise, a lesson whose subject is the workflow system's own contract is flagged as a candidate workflow-repo dogfood finding for the user to file in the workflow repository (`problem-framing` or `task-init` there, or `capture-observation` in an already-active workflow task); this command never writes outside the active task.
- Treat task-memory write policy per `WORKFLOW_OPERATING_SYSTEM.md`: `PROPOSED` in Ask mode, `APPLIED` only in Agent mode.
- **Distinctness.** `capture-observation` captures a single in-flight note verbatim without judgment; `slice-closure` captures the learnings of one slice as it closes; `task-close` is the terminal lifecycle move. This command is an on-demand, session-wide harvest that can run mid-task or at the end, and it judges what is durable before writing.

Required output:
1. A one-line read of whether the session produced durable lessons (or a NO_OP routing back to the prior work when nothing generalizes)
2. The candidate lessons found, each with its anchor and a one-line reason it generalizes
3. Which candidates were dropped as duplicates or one-off trivia, and why
4. Exact `LEARNINGS.md` append block (the new entries only, in `templates/LEARNINGS.md` shape), marked PROPOSED or APPLIED per editor mode
5. Any cross-project lesson flagged as a pointer to `USER_MEMORY.md`, and any workflow-contract lesson flagged as a candidate workflow-repo dogfood finding for the user to file in the workflow repository (neither written here)
6. Recommended next command
7. Recommended editor mode
8. Why that is the correct next step

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
- Every appended entry is reusable beyond this task, anchored per `templates/LEARNINGS.md` `## Entry shape`, and new (de-duplicated against existing `LEARNINGS.md`); an unanchored or one-off entry is invalid output.
- The run is append-only: no existing `LEARNINGS.md` entry is edited, reordered, or pruned, and no other task-memory file is touched.
- `### Artifact changes` marks the `LEARNINGS.md` append as `PROPOSED` in Ask/Plan mode or `APPLIED` only in Agent mode; a session with nothing durable returns a NO_OP rather than a manufactured lesson.
- Output ends with a complete `### Handoff` block per the adaptive format in `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract`.
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
Optimize for a small number of high-signal, anchored, reusable lessons that make the next task start smarter, with zero rewriting of past entries and zero manufactured filler.

<!-- cache-breakpoint -->
