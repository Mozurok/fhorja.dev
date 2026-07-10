---
name: branch-commit
description: |-
  Return a branch name and a concise commit message (at most 2 lines) for the current task, grounded in the real `git diff` rather than a paraphrase of the task summary. Use when the user only needs quick branch and commit naming right before committing, full PR packaging is unnecessary, and there is a real inspectable diff (staged or unstaged changes, or a branch diff vs an integration base). Do not use when the task needs a complete PR package (use pr-package), there is no diff yet (naming a branch from a task summary alone is the failure mode this command exists to avoid; ask the user to stage at least one change first), or the diff is still too unclear to summarize safely.
metadata:
  category: delivery-and-communication
  primary-cursor-mode: Ask
  multi-repo-aware: false
  context-layers-consumed:
    - memory
  context-layers-produced:
    - memory
  tools:
    - Read
    - Write
    - Edit
    - Bash
    - Glob
    - Grep
  x-wos-profiles:
    - core
    - full
  provenance: first-party
  token-budget: 2200
  suggested-model: claude-haiku-4-5
---

Act as a concise engineering delivery assistant.

Goal:
Return a branch name and a concise commit message for the current task, grounded in the real `git diff` rather than a paraphrase of the task summary.

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
- current task summary (for orientation only, never the primary source for the commit message)
- explicit diff source, exactly one of:
  - `git diff` (unstaged), `git diff --staged` (staged), or `git diff <base>...HEAD` (branch ahead of base)
- the actual diff output (paths and hunks, not the stat summary alone) so the commit message can name the real change
- current branch name (from `git branch --show-current`) so the branch suggestion only proposes a rename when the existing name is generic
- last completed step from TASK_STATE.md (command + summary), if available

Operating rules:
- Return in English.
- **Handoff:** end with the adaptive `### Handoff` block per `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full).
- Summarize from the **real diff**, not from the task summary. The commit subject must name a path or behavior visible in the diff; generic phrasings like "update task" or "improve flow" are invalid output unless that is literally what the diff shows.
- Return one suggested branch name (or explicitly say "keep current branch: `<name>`" when the existing name already reflects the diff scope).
- Return one commit message with a subject line ≤ 72 characters and an optional body of at most 2 short lines, for a total of max 3 lines. Prefer Conventional Commits style (`feat:`, `fix:`, `docs:`, `chore:`, etc.) when it fits the diff.
- If the diff spans multiple unrelated concerns, do not paper over it: flag the split and recommend either staging the commits separately or running `pr-package` for a structured delivery.
- If naming would not materially improve clarity versus the last recorded branch/commit guidance, return a no-op and route forward instead of inventing new names.
- **Auto-deliver on full completion:** when the diff covers all remaining slices in IMPLEMENTATION_PLAN.md (i.e., the task is fully implemented), update TASK_STATE.md phase to "delivered" as part of this command's output. This eliminates the need for a separate `sync-task-state` call after commit just to mark the task as delivered.

Required output:
1. Diff source actually used (one of `git diff`, `git diff --staged`, `git diff <base>...HEAD`), verbatim, for auditability
2. One-line summary of what the diff changes (paths + behavior)
3. Suggested branch name (or `keep current branch: <name>` with reason)
4. Suggested commit message (subject ≤ 72 chars, optional ≤ 2-line body, total ≤ 3 lines)
5. Multi-concern flag if the diff covers unrelated scopes, with recommended split

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
- Output names the exact diff source used (`git diff`, `git diff --staged`, or `git diff <base>...HEAD`); paraphrasing from the task summary without citing a diff is invalid output.
- Commit subject line names a path or behavior visible in the diff; generic phrasings like "update task" or "improve flow" are invalid unless the diff really is just that.
- Branch name is specific, stable, and matches repo conventions; reuse of an already-correct branch is preferred over a fresh rename.
- Commit message is ≤ 3 lines total (subject + optional 2-line body); body is omitted when the subject is sufficient.
- Multi-concern diffs are flagged explicitly with a recommended split (smaller commits or `pr-package`); silently merging unrelated concerns into one commit is invalid output.
- `### Artifact changes` is `None`.
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
Optimize for clarity and brevity.

<!-- cache-breakpoint -->
