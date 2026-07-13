---
name: approve-proposed
description: |-
  Atomically persist every file marked PROPOSED in the most recent prior assistant turn's `### Artifact changes` block. Single-command idiom that closes the two-step latency in ADR-0001's PROPOSED-by-default contract; the user reviews proposals in Ask/Plan mode, then runs this once to write all of them. Use when the prior assistant turn ended with a `### Artifact changes` block containing one or more files marked PROPOSED and you have read and accepted the inline content for each. Do not use when the prior turn had no `### Artifact changes` block, every artifact is APPLIED or SKIP, you have not yet read the proposed content, or you want to approve only a subset (run the original command in Agent mode for partial approval).
metadata:
  category: state-and-navigation
  primary-cursor-mode: Agent
  multi-repo-aware: false
  context-layers-consumed:
    - history
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
  token-budget: 3000
  suggested-model: claude-haiku-4-5
---

Act as a senior/staff engineer executing a single batch-persist of every file the prior assistant turn proposed under `### Artifact changes`.

Goal:
Read the most recent prior assistant turn in the conversation history, identify every file marked `PROPOSED` in its `### Artifact changes` block, and write all of them atomically. Print a single recap line listing what landed.

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
- the conversation history containing the most recent prior assistant turn with an `### Artifact changes` block (already in context when the command runs)
- active task folder path (for resolving relative artifact paths)

Task repository files to update:
- every file listed in the prior turn's `### Artifact changes` block that is marked `PROPOSED` (full inline content or update-delta)

Operating rules:
- Do not propose anything. This command is for executing prior proposals, not creating new ones.
- **Source-of-truth turn**: the "prior assistant turn" means the MOST RECENT assistant message in the chat history that contains an `### Artifact changes` block. Skip intervening user messages, tool results, and assistant messages without an Artifact-changes block. Do NOT walk back across multiple Artifact-changes turns; only the latest counts.
- **Content required**: persist files that have either (a) full inline content or (b) an update-delta (semantic description of changes to an existing file). For full inline: write the content as-is. For update-delta: read the current file on disk, apply the described changes, and write the result. If a file is marked `PROPOSED` but its content is vague or unresolvable (e.g., "see content above", "same as last turn"), do NOT persist it; list it under `Skipped (incomplete inline)` in the recap.
- **Path resolution**: every file path in the prior block must resolve to a real path inside the active task folder OR inside `my_work_tasks/` (for workflow meta-edits). If a path resolves outside both, do NOT persist it; list it under `Skipped (path outside scope)` in the recap.
- **Atomic batch**: perform all qualifying writes in this single turn (one Write per file). Do not split across multiple turns. Do not interleave Write calls with conversational prose.
- **No partial mode**: this command is all-or-nothing for the qualifying subset. If the user wants partial approval, they re-run the source command in Agent mode or edit the proposals before running this command.
- **No-op cases**:
  - Prior turn has no `### Artifact changes` block: NO_OP with explicit explanation ("most recent assistant turn does not contain an Artifact changes block; nothing to approve").
  - Prior block contains no `PROPOSED` files (all `APPLIED` or `SKIP`): NO_OP with explicit explanation.
  - All PROPOSED files match on-disk content already: NO_OP with explicit explanation ("all proposed files are identical to current on-disk content; nothing to write").
- **No new proposals**: if the user input contains additional instructions beyond "approve", ignore them. This command does not accept new content; it only executes the prior batch. To propose new artifacts, re-run the source command.
- **Recap format (locked)**: the `### Command transcript` section MUST contain exactly one recap line per outcome class, in this order:
  1. `Persisted: <comma-separated-list-of-paths>` (omit line if empty)
  2. `Skipped (already current): <list>` (omit if empty)
  3. `Skipped (incomplete inline): <list>` (omit if empty)
  4. `Skipped (path outside scope): <list>` (omit if empty)
  5. `Skipped (no PROPOSED marker): <list>` (omit if empty)
- **Conflict-check rule**: before persisting any file, compare the proposed content's references to locked decisions in `TASK_STATE.md ## Canonical decisions`. If the proposal contradicts a locked decision, FAIL with a clear error naming the contradiction; do NOT persist anything in this turn (atomic rollback).
- **Substrate write protocol (per ADR-0034, K.2, ADR-0101).** WHEN a persisted file is a K.2 substrate file per `commands/_shared/substrate-write-protocol.md`, replace the proposer's mode=proposed transaction header with this run's `owner=approve-proposed ... mode=applied` header and append one `event=approve` JSONL line per applied file to `active/<task>/.wos/VERIFICATION_LOG.jsonl` with valid sha_before/sha_after (`bash scripts/emit-substrate-write.sh` is the invokable path); non-substrate files are unaffected.
- **Handoff:** end with the adaptive `### Handoff` block per `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full).

Required output:
1. The `### Artifact changes` block listing every persisted file as `APPLIED` (no inline content needed; the content already lived in the prior turn). Files that did not persist appear marked `SKIP` with a one-line reason.
2. The `### Command transcript` block with the recap lines per the format above.
3. A one-line summary stating how many files persisted vs how many were skipped.
4. Recommended next step, next command, editor mode, and why (typically routing back to whichever command produced the original proposals, OR to `sync-task-state` if the persisted files materially change task state).
5. What should explicitly not be done yet.

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
- Every file the prior turn marked `PROPOSED` (full inline or update-delta) is either persisted as `APPLIED` or explicitly skipped with a recap-line reason. Silent omission is invalid.
- The `### Command transcript` recap follows the locked five-line format (Persisted / Skipped already current / Skipped incomplete inline / Skipped path outside scope / Skipped no PROPOSED marker). Lines that have zero entries are omitted; lines that have entries appear in the locked order.
- No new artifacts are introduced beyond what the prior turn proposed. Adding files this command "thinks" should also be written is invalid output.
- No-op runs include `NO_OP_TRACE` and name the no-op cause (no Artifact-changes block / no PROPOSED files / all already current).
- Conflict-with-locked-decision runs do NOT persist anything; they emit a clear FAIL with the contradiction named.
- Output ends with a complete `### Handoff` block per the adaptive format in `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract`.
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
Optimize for: zero ambiguity about what landed on disk, atomic batch semantics, and recap clarity. The user must be able to read the recap and immediately know which files exist on disk now, which were skipped and why, and what to run next.

<!-- cache-breakpoint -->
