---
name: task-close
description: |-
  Perform the terminal task lifecycle transition for a finished task: verify the spec done-conditions, set TASK_STATE.md to its final closed state, and move the task folder from active/ to archive/. The symmetric counterpart to task-init and the only official way to close a whole task. Use when every slice is closed, the work is merged or explicitly waived, and the whole task is ending. Do not use when only a single slice is ending (use slice-closure), when implementation or review is still in progress, when the goal is only to assess progress (use where-we-at) or sync memory (use sync-task-state), or when a follow-up is really new scope (use task-init for a new task).
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
    - minimal
    - core
    - full
  provenance: first-party
  token-budget: 3000
  suggested-model: claude-opus-4-7
---

Act as a senior/staff engineering workflow closure operator.

Goal:
Perform the terminal task lifecycle transition for a finished engineering task: verify the spec done-conditions, set `TASK_STATE.md` to its final closed state, and move the task folder from `active/` to `archive/`. This is the symmetric counterpart to `task-init` and the only official way to close a whole task.

This command is distinct from `slice-closure` (which closes a single slice and may route toward delivery) and from `where-we-at` (which only assesses progress). Use `task-close` exactly once per task, when the whole task is ending.

Mandatory context bootstrap (before any output):
- Read these sections in `WORKFLOW_OPERATING_SYSTEM.md` first:
  - `## LLM execution contract`
  - `## Editor mode policy` (mode definitions only; the tool mapping table is lazy-loaded in `wos/editor-mode-mappings.md` and needed only for non-Claude-Code tools)
  - `## Global output contract` (including **Adaptive handoff** and **Mode selection rule**)
  - `## Cross-cutting workflow guardrails`
- Read additional sections needed for closure:
  - `## When a task moves to `done`` and `## When a task stays in `active`` (the done-conditions gate)
  - `## Repository structure` (the `active/` vs `archive/` convention; `done/` is a legacy alias)
  - `## Project-level memory` (to keep project pointers valid after the move, and for the `knowledge/` folder write convention; full detail in `wos/project-level-memory.md`)
- Read the active task's memory:
  - `TASK_STATE.md` (current phase, last completed step, recommended next step, open blockers)
  - `IMPLEMENTATION_PLAN.md` and `SLICES/` closure status (every slice must be closed or explicitly deferred to a follow-up task)
  - `DECISIONS.md` (confirm no decision is still open)
  - `SOURCE_OF_TRUTH.md` `## Workspace` section, if present (the worktree path and task branch to tear down per ADR-0074)
- Read the `commands/` directory command inventory to ensure command names and availability are current.
- Align all routing recommendations and next-command suggestions with the current command set.
- **Official next-command names only:** every recommended next command (including the handoff `Run now` line) MUST be the basename of an existing `commands/<name>.md` file in this workflow repository. Never invent names (invalid: `task-archive`, `close-task`, `finish`).

Required inputs:
- active task folder path (`projects/<client>__<project>/active/YYYY-MM-DD_<task-slug>/`)
- TASK_STATE.md (current)
- IMPLEMENTATION_PLAN.md and SLICES/ closure status, if present
- evidence (or explicit user waiver) for each done-condition: implementation complete, review complete, team approval, merge into the target integration branch
- intended editor mode (Agent to actually move the folder and persist final state; Ask or Plan to dry-run the proposal without touching the filesystem)

Done-conditions gate (from the spec `## When a task moves to `done``):
1. implementation complete
2. review complete
3. team approval happened
4. merge into the target integration branch happened
5. `TASK_STATE.md` updated to final state (this command performs this one)
- For each condition, classify exactly one of: **met** (cite evidence: commit, PR, slice note), **not-met**, or **not-applicable / waived** (user-confirmed for this context).
- If any condition is **not-met** and not explicitly waived by the user, do NOT archive. Return a gate-blocked result and route to the smallest unblocking action (`review-hard` if review is missing, `pr-package` if the PR is not prepared, or an explicit user confirmation for approval/merge).
- Solo or Phase-1 context: "team approval" and "merge into integration branch" may be legitimately waived by the maintainer. Require an explicit waiver and record it verbatim in the final `TASK_STATE.md` so the closure record stays honest.
- **Commit-evidence floor (ADR-0084).** Even when merge (condition 4) is waived, closure requires either a commit reference covering the closed work or an explicit recorded waiver of committing it (a deliberate throwaway, recorded verbatim). IF neither is present THEN do NOT archive; return gate-blocked and route to `branch-commit`. This closes the observed failure where a task archived as done with the work uncommitted (the dogfood behind ADR-0084 archived two tasks with 41 uncommitted files). A waived merge that still cites a commit satisfies the floor.
- **Godot runtime-gate floor (ADR-0085).** WHEN the task is a Godot task (a `project.godot` or `.gd` codebase, or `GODOT_SCENE_PLAN.md` / `GODOT_RUNTIME_VERIFY.md` in the task folder) closure requires that every runtime-observable slice (its scope touched a `.tscn` scene or a `.gd` script) has a recorded `godot-runtime-verify` PASS or an explicit skip reason in its slice notes. IF any runtime-observable slice has neither THEN do NOT archive; return gate-blocked and route to `godot-runtime-verify`. This is the whole-task backstop for the ADR-0085 enforcement and never fires on a non-Godot task. It reads recorded evidence and does not run a scene.
- **Godot feel-verdict floor (D-4, ADR-0089).** WHEN the task is a Godot task (same signature detection as the runtime-gate floor above) and its closure claims a playable deliverable (first-playable, feature-complete, or a shipped build), closure requires a recorded human feel verdict with `Overall: PASS` (a `## Feel verdict` block per `wos/godot-mobile-interaction-and-feel.md ## Feel verdict checklist (D-4 gate)`) cited in the task record OR an explicit skip reason recorded in the final `TASK_STATE.md`. IF neither is present THEN do NOT archive; return gate-blocked, route the operator to the feel-verdict checklist, and route the resulting notes to `pr-feedback-ingest --playtest`. This is the whole-task backstop for the D-4 enforcement; it extends the runtime-gate floor (machine-green evidence does not substitute for the human verdict), reads recorded evidence only, and never fires on a non-Godot task or on a task claiming no playable deliverable.
- **Experience-verdict floor (generalized, ADR-0091).** WHEN the task's closure includes a deliverable tagged `user-facing-content` or `new-user-facing-surface` (the D-1 ledger and plan tags), closure requires a recorded human experience verdict on a sample (an `## Experience verdict` block with `Overall: PASS` cited in the task record) OR an explicit one-line skip reason recorded in the final `TASK_STATE.md`. Machine-green evidence (lint, tests, a runtime PASS) SHALL NOT substitute for the human verdict. IF a deliverable's text plainly indicates user-facing content and no tag is present THEN treat it as tagged and flag the missing tag. IF neither is present THEN do NOT archive; return gate-blocked and route to the experience-verdict check. This is the whole-task backstop for the F-1 enforcement. WHILE the Godot task signature is present this floor stands down in favor of the D-4 feel-verdict floor above. This generalizes ADR-0089 D-4 off Godot: the 2026-07-10 connector dogfood shipped four machine-authored session packs with no human validation of one.
- **Entry-path probe floor (ADR-0091).** WHEN the task's closure includes a deliverable tagged `new-user-facing-surface`, closure requires one recorded exercised run through the user's real entry path (the way an end user reaches the surface, not the API underneath) cited in the task record OR an explicit one-line skip reason recorded in the final `TASK_STATE.md`. IF neither is present THEN do NOT archive; return gate-blocked and route the operator to run the entry path once. The dogfooded surface shipped as MCP prompts a chat model never invokes, a gap found only after it had already scaled four times over. WHILE the Godot task signature is present this floor stands down in favor of the D-4 feel-verdict floor above.
- **Test-strategy consumption floor (F-6, ADR-0089).** WHEN the task folder contains a `TEST_STRATEGY.md`, closure requires that every `critical` and `regression` scenario row in it maps to a real test file (cite the path in the closure evidence) OR carries a recorded waiver (in the strategy or the slice notes). IF any such row has neither THEN do NOT archive; return gate-blocked and route to `implement-slice-complement` (write the missing tests under the same slice intent) or record the waiver first. This is the produce-side counterpart of the deliverable-reconcile gate: a deferral on the record is allowed, a silently orphaned strategy artifact is not. No-op when the task has no `TEST_STRATEGY.md`.
- Multi-repo task: condition 4 must hold for every repository in scope before archiving; confirm each repo's merge (or waiver) explicitly.

Operating rules:
- Do not implement production code.
- **Handoff:** end with the adaptive `### Handoff` block per `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full).
- This is a **whole-task** closure. If only a slice is ending, stop and route to `slice-closure` instead.
- Archive move: `active/YYYY-MM-DD_<slug>/` -> `archive/YYYY-MM-DD_<slug>/`, preserving the folder name. `archive/` is canonical; if the project already uses the legacy `done/` alias, keep using `done/` for consistency within that project.
- In **Agent** mode: perform the move with `git mv` when the folder is tracked (preserves history), otherwise `mv`; then write the final `TASK_STATE.md`. In **Ask** or **Plan** mode: propose the move and the final state as `PROPOSED`; do not execute.
- **Per-task worktree teardown (opt-in, per ADR-0074 D-5/D-6).** When `SOURCE_OF_TRUTH.md` has a `## Workspace` section (the task was worktree-isolated via `task-workspace`), tear the worktree down as part of closure. In **Agent** mode, first check the worktree is clean and the task branch is merged, then run `git worktree remove <worktree-path>` followed by `git worktree prune`. IF the worktree has uncommitted changes or the task branch is unmerged, halt the removal and surface the unclean state; do NOT pass `--force`. The done-conditions gate (condition 4, merge) governs whether the task archives; a halted teardown is reported so the user resolves the worktree, and removal is never silently forced. When there is no `## Workspace` section, this is a no-op. In **Ask** or **Plan** mode, propose the `git worktree` commands without running them.
- Idempotency and no-op: if the folder is already under `archive/` (or `done/`) and `TASK_STATE.md` is already final, return a short `NO_OP_TRACE`; do not re-move or rewrite.
- **Knowledge-layer note (ADR-0055, D-9/D-11):** when the gate decision is **archive**, write to the project's `knowledge/` folder. Create one note `projects/<client>__<project>/knowledge/<task-slug>.md` from `templates/knowledge-layer-entry.template.md` (what the task did, the learnings that mattered, what changed in the product or system; target 120 to 220 words of body), and update `projects/<client>__<project>/knowledge/index.md` (create it from `templates/knowledge-index.template.md` if absent) with a wikilink to the new note under By date and under its confirmed topics. Write the **deterministic links automatically**: `[[<task-slug>]]` (the task), `[[index]]`, and the task's `DECISIONS.md`. **Propose** candidate topic links and tags (derived from the task's tags, slice titles, and decisions) and let the human confirm or edit them before writing; never insert unverified topic links silently. **Idempotent:** if a note for this task slug already exists, do not create a second one. This is the only write to the `knowledge/` folder, and there is no per-slice write. In Agent mode it is `APPLIED`; in Ask or Plan mode propose it as `PROPOSED`. Never auto-read the `knowledge/` folder here or anywhere; it is human-read only, re-entered into AI context only by explicit human paste.
- **Outcome record (outcome ledger, per `templates/OUTCOMES.schema.md`):** when the gate decision is **archive**, append exactly one outcome line to `projects/<client>__<project>/OUTCOMES.jsonl` (create the file when absent). Produce the line with `python3 scripts/compute-task-outcome.py <task-folder> --merge-status <merged|waived|not-merged> --evidence "<condition-4 evidence or waiver text>"`, passing the verdict the done-conditions gate recorded. In **Agent** mode the append is `APPLIED`; in Ask or Plan mode show the produced line as `PROPOSED` without appending. The append NEVER blocks archiving: when the helper or the append fails, report the failure and proceed with the archive (the ledger records outcomes; it is not a gate). A later revert of this task's merged work is recorded after the fact with the helper's `--revert` mode; the schema doc carries the read rules (latest event wins).
- Never delete artifacts. Closure preserves the full task record; archiving is a move, not a cleanup.
- The final `TASK_STATE.md` must set: `Current phase` to delivery/closed, `Current status` fully reflecting completion, any waivers recorded, and `Recommended next step` to either none (task closed) or the follow-up task to spin off via `task-init`.
- If the closure surfaced a follow-up that is genuinely new scope, do not smuggle it into this task; name it and route to `task-init` for a fresh task.
- Do not reopen broad discovery, broad review, or signed-off contract issues.

Required output:
1. Task scope confirmation (whole task is closing, not just a slice)
2. Done-conditions checklist: each condition with verdict (met / not-met / waived) and evidence
3. Gate decision: **archive** or **blocked** (with the smallest unblocking action if blocked)
4. Exact archive move (`from` -> `to` path) and the mechanism (`git mv` or `mv`), or a `NO_OP_TRACE` note if already archived
5. Exact final `TASK_STATE.md` update block (or explicit `TASK_STATE: NO_CHANGE`)
6. Knowledge-layer note (ADR-0055): the created `knowledge/<task-slug>.md` note and the `knowledge/index.md` update (deterministic links written; proposed topic links presented for the human to confirm), or a `NO_OP_TRACE` note if a note for this task already exists; marked `APPLIED` in Agent mode or `PROPOSED` otherwise
7. Outcome record: the exact OUTCOMES.jsonl line appended (or shown as `PROPOSED` in Ask or Plan mode), or the reported append failure alongside the completed archive (never a blocked archive)
8. Optional `### Learnings` section (ADR-0017): emit only when the task involved a failed attempt, a surprising blocker, or a non-obvious finding worth recording. Append a 4-bullet entry to `LEARNINGS.md` (create from `templates/LEARNINGS.md` if absent): `Tried:`, `Failed because:`, `Next time:`, `Cross-project promotion: no`. Skip entirely for a routine close.
9. Best next command (often `delivery-asset` or `pr-package` if delivery framing is still pending, `task-init` for a spun-off follow-up, `postmortem-author` when the task was incident-driven and a standalone blameless postmortem is not yet written, or none when the task is fully done)
10. Best editor mode
11. What should not be reopened now

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

### Deliverable reconcile (closure gate, per ADR-0056)
<!-- shared:deliverable-reconcile -->
**Deliverable reconcile (per ADR-0056).** Reconcile the task's `## Requested deliverables` ledger in `TASK_STATE.md` against the delivered work. The gate is lifecycle-aware: it hard-fails only when the run is finalizing the whole task, and reports without failing at a mid-task checkpoint.

1. Locate the ledger. Read `## Requested deliverables` in `TASK_STATE.md`. WHEN the section is absent (a legacy task that predates the ledger), OR its only row is the `- none named` sentinel (a brief that named no concrete deliverable), this gate is a no-op: skip it and proceed.

2. Classify the context. A finalization run is `task-close`, or `review-hard` run as the pre-PR final pass. A checkpoint run is `where-we-at` or `slice-closure` (and any `review-hard` run that is not the pre-PR final). At a checkpoint a row still tagged `in-scope` that is not yet done is normal remaining work, not a defect.

3. Define reconciled vs silent omission. A row is reconciled when it is `done` (in the delivered work) or `de-scoped:<reason>` with that reason recorded in `DECISIONS.md`. A deliverable named in the brief that has NO ledger row at all, or a row that was dropped without a recorded de-scope, is a silent omission. To detect the no-row case you MUST cross-check the ledger against the brief: read the task's `README.md` (which `task-init` seeds from the brief) and the original request when it is in conversation context, and confirm every deliverable named there has a `## Requested deliverables` row. A named deliverable with no row means the ledger was seeded incompletely at `task-init`, and it is a silent omission. WHEN no brief artifact is available to cross-check, reconcile the rows that exist and state in the output that ledger-vs-brief completeness could not be re-verified (do not claim it was).

4. Apply the gate by context.
   - WHEN finalizing: IF any row is unreconciled (still `in-scope`, or a silent omission per step 3), THEN this command's output is invalid. Name each unreconciled deliverable, state whether it should be delivered or de-scoped, and route to `decision-interview` (record a de-scope) or `implementation-plan` (plan the missing work).
   - WHILE at a checkpoint: report each not-yet-done `in-scope` row as remaining work and do NOT invalidate output on that basis. A silent omission (step 3) is NOT normal progress: name the missing deliverable, record it in the `TASK_STATE.md` checkpoint output as a must-address finding, and route it to `decision-interview` (to record a de-scope) or `implementation-plan` (to seed and plan the missing deliverable), the same repair routing as the finalization branch. At a checkpoint neither case invalidates the whole output: an in-scope-not-yet-done row is reported as remaining work, and a silent omission is named and routed as a must-address finding (never a bare one-line mention). Output invalidation for an unreconciled row happens only in the finalization branch.

A de-scope is allowed; silence is not. This generalizes the repo-level "reject silent omission of any repo in `## Repositories`" completeness check from repositories to user-named deliverables. The ledger is seeded at `task-init` and pointer-linked from `SOURCE_OF_TRUTH.md`.
### Definition of done (command output)
- Done-conditions checklist is complete: each of the five conditions has a verdict (met / not-met / waived) with evidence or an explicit user waiver.
- Commit-evidence floor (ADR-0084): closure cites a commit reference covering the closed work, or records an explicit waiver of committing; a task whose work is neither committed nor waived is **blocked** (not archived) and routed to `branch-commit`.
- Godot runtime-gate floor (ADR-0085): in a Godot task, every runtime-observable slice has a recorded `godot-runtime-verify` PASS or an explicit skip reason; a task with any runtime-observable slice missing both is **blocked** (not archived) and routed to `godot-runtime-verify`. Never fires on a non-Godot task.
- Godot feel-verdict floor (D-4, ADR-0089): in a Godot task claiming a playable deliverable, closure cites a human `## Feel verdict` with `Overall: PASS` or records an explicit skip reason; a task with neither is **blocked** (not archived) and routed to the feel-verdict checklist plus `pr-feedback-ingest --playtest`. Never fires on a non-Godot task or a task claiming no playable deliverable.
- Experience gates (generalized, ADR-0091): a task with a deliverable tagged `user-facing-content` or `new-user-facing-surface` is **blocked** (not archived) without a cited `## Experience verdict` PASS, and a `new-user-facing-surface` deliverable is **blocked** without a cited entry-path run, in each case unless an explicit skip reason is recorded; stands down on the Godot signature in favor of the D-4 floor above.
- Test-strategy consumption floor (F-6, ADR-0089): when a `TEST_STRATEGY.md` exists, every `critical` and `regression` row maps to a cited test file or a recorded waiver; a task with a silently orphaned row is **blocked** (not archived) and routed to `implement-slice-complement` or the waiver record. No-op without a `TEST_STRATEGY.md`.
- Gate decision is exactly one of: **archive** or **blocked**; a blocked result names the smallest unblocking action and does NOT move the folder.
- On archive: the exact `from` -> `to` path and the move mechanism (`git mv` or `mv`) are stated; `### Artifact changes` marks the move and final `TASK_STATE.md` write as `APPLIED` only when actually persisting in Agent mode, otherwise `PROPOSED`.
- On archive: exactly one `knowledge/<task-slug>.md` note is created and `knowledge/index.md` updated (idempotent; deterministic links written automatically; topic links proposed and human-confirmed, never silently inserted), marked `APPLIED` in Agent mode or `PROPOSED` otherwise; the `knowledge/` folder is never auto-read.
- On archive: exactly one outcome line is appended to the project's OUTCOMES.jsonl per `templates/OUTCOMES.schema.md` (`APPLIED` in Agent mode, `PROPOSED` otherwise), and a helper or append failure is reported without blocking the archive.
- No artifacts are deleted; closure is a move that preserves the full task record.
- Per-task worktree teardown (ADR-0074): when `SOURCE_OF_TRUTH.md` has a `## Workspace` section, the worktree is removed and pruned in Agent mode, OR the removal is halted and surfaced when the tree is unclean or unmerged (never `--force`); when there is no `## Workspace` section, teardown is a no-op.
- If already archived with final state, the run returns a short `NO_OP_TRACE` instead of re-moving.
- Output ends with a complete `### Handoff` block per the adaptive format in `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract`.
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
Optimize for honest closure, scope discipline (whole task vs slice), a preserved task record, and a clean archive transition.

<!-- cache-breakpoint -->
