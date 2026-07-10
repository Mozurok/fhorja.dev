---
name: apply-sweep-triage
description: |-
  Persist the user's triage decisions (apply, decline, discuss) from a SWEEP snapshot into REVIEW_PREFERENCES.md so future sweeps suppress declined findings and track applied fixes. Use after the user has edited the triage values in a SWEEP snapshot file produced by repo-consistency-sweep. Do not use when no sweep snapshot exists or when the user has not yet set triage values.
metadata:
  category: execution-and-closure
  primary-cursor-mode: Agent
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
  token-budget: 1200
  suggested-model: claude-sonnet-4-6
---

Act as a workflow state updater that persists review-sweep triage decisions into project-level preferences.

Goal:
Read a SWEEP snapshot where the user has set `triage:` values (apply, decline, discuss) on each finding, and persist those decisions into `REVIEW_PREFERENCES.md` at the project level so future `repo-consistency-sweep` runs respect them.

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
- SWEEP snapshot path (or pointer from TASK_STATE.md under `## Latest sweep`)
- optional: REVIEW_PREFERENCES.md path (if not present, created from template)

Task repository files to update:
- REVIEW_PREFERENCES.md (create from `templates/REVIEW_PREFERENCES.template.md` if absent; append rows)
- TASK_STATE.md (update last completed step)

Operating rules:
- **Handoff:** end with the adaptive `### Handoff` block per `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full).
- **Step 1: Locate snapshot.** Read the SWEEP snapshot path from inputs or from TASK_STATE.md `## Latest sweep` pointer.
- **Step 2: Parse findings.** Extract each finding block from the snapshot. For each, read: bug_class, file_path, triage value (apply, decline, discuss, or unset).
- **Step 3: Skip unset.** Findings with `triage: unset` are skipped (user has not decided yet). If ALL findings are unset, return no-op.
- **Step 4: Compute file hashes.** For each triaged finding, run `git hash-object <file_path>` to capture the current file hash. This hash anchors the suppression: when the file changes, the declined entry ages out.
- **Step 5: Persist decisions.** Open or create REVIEW_PREFERENCES.md:
  - For `decline`: append a row to the `## Declined findings` table with date, bug_class, file_path, file_hash, and the user's reason (from the `reason:` line in the snapshot, or "no reason given" if absent).
  - For `apply`: append a row to the `## Applied findings` table with date, bug_class, file_path, and action_taken (from the `action:` line in the snapshot, or "acknowledged" if absent).
  - For `discuss`: append a row to the `## Discussed findings` table with date, bug_class, file_path, and the user's note (from the `note:` line in the snapshot, or empty).
- **Step 6: Deduplicate.** Before appending, check if an identical row (same bug_class + file_path) already exists in the target table. If yes, update the existing row's date, file_hash, and reason instead of appending a duplicate.
- **Step 7: Update TASK_STATE.** Set last completed step to this command with a summary of how many decisions were persisted (N declined, M applied, K discussed).
- Do not modify the SWEEP snapshot file itself (it is a read-only historical record).
- Do not implement code fixes. Persistence only.

Required output:
1. Summary: how many findings triaged (N declined, M applied, K discussed, J skipped as unset)
2. Rows added or updated in REVIEW_PREFERENCES.md
3. TASK_STATE.md update
4. Recommended next command

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
- All triaged findings (non-unset) are persisted into REVIEW_PREFERENCES.md.
- Declined rows include file_hash for suppression aging.
- No duplicate rows (deduplication by bug_class + file_path).
- TASK_STATE.md updated with triage summary.
- SWEEP snapshot is read-only (not modified).
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
Accurate persistence. Every triaged finding maps to exactly one row in REVIEW_PREFERENCES.md. No data loss, no silent overwrites.

<!-- cache-breakpoint -->
