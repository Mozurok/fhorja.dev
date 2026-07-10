---
name: task-workspace
description: Provision, report, or attach a dedicated git worktree and branch for the active task on a git-backed project, so multiple tasks run in parallel on one repository without colliding on a single working tree. Opt-in and git-gated: a non-git project or an un-opted task is a no-op. Records the worktree path and task branch in SOURCE_OF_TRUTH.md and runs standalone to retrofit a task already in progress. Use when a task needs an isolated working tree and branch, or to attach one to an in-flight task. Do not use for the ephemeral slice-level worktrees implement-fleet already manages, for a non-git project, or to close the whole task (task-close owns teardown).
metadata:
  category: state-and-navigation
  primary-cursor-mode: Agent
  multi-repo-aware: false
  context-layers-consumed: [memory]
  context-layers-produced: [memory]
  tools: [Read, Write, Edit, Bash, Glob, Grep]
  x-wos-profiles: [full]
  provenance: first-party
  token-budget: 3400
  suggested-model: claude-opus-4-7
---
# task-workspace

Act as a senior/staff engineering workflow workspace operator.

Goal:
Provision a dedicated git worktree and branch for the active task on a git-backed project (or report the current one, or attach one to a task already in progress), so several tasks run in parallel on the same repository without colliding on one working tree or one checked-out branch. This is opt-in, git-gated, and additive: when isolation is not requested or the project is not a git repo, this command is a no-op and every other command behaves exactly as today.

This command is distinct from:
- `implement-fleet`: which creates ephemeral, slice-level worktrees for parallel slices inside one task and tears them down at the wave merge. task-workspace creates one durable worktree for the whole task. When a task worktree is active, fleet slice worktrees branch from the task branch, not the repo base (ADR-0074 D-3).
- `task-init`: which creates the task memory folder and can invoke this command during initialization when isolation is requested. task-workspace owns only the git worktree lifecycle, not the task-memory files.
- `task-close`: which owns teardown. task-workspace never removes a worktree; `task-close` runs `git worktree remove` plus `git worktree prune` with an unclean-tree guard (ADR-0074 D-5, D-6).

See ADR-0074 for the contract this command implements.

Mandatory context bootstrap (before any output):
- Read these sections in `WORKFLOW_OPERATING_SYSTEM.md` first:
  - `## LLM execution contract`
  - `## Editor mode policy` (mode definitions only; the tool mapping table is lazy-loaded in `wos/editor-mode-mappings.md` and needed only for non-Claude-Code tools)
  - `## Global output contract` (including **Adaptive handoff** and **Mode selection rule**)
  - `## Cross-cutting workflow guardrails`
- Read additional sections only when relevant to this command's role:
  - `## Multi-repo support (v1)` (the SOURCE_OF_TRUTH workspace schema this command reads and writes; full detail in `wos/multi-repo-support.md`)
- Read the active task's memory:
  - `SOURCE_OF_TRUTH.md` (active codebase path, active or base branch, and any existing `## Workspace` section)
  - `TASK_STATE.md` (task slug, current phase, whether isolation was requested)
- Read the `commands/` directory command inventory to ensure command names and availability are current.
- Align all routing recommendations and next-command suggestions with the current command set.
- **Official next-command names only:** every recommended next command (including the handoff `Run now` line) MUST be the basename of an existing `commands/<name>.md` file in this workflow repository. Never invent names (invalid: `worktree-add`, `task-worktree`, `provision`).

Required inputs:
- active task folder path (`projects/<client>__<project>/active/YYYY-MM-DD_<task-slug>/`)
- SOURCE_OF_TRUTH.md (the target codebase path and its base branch)
- TASK_STATE.md (the task slug, used to derive the branch and worktree names)
- the requested action: `provision` (default), `status`, or `attach` (retrofit a worktree onto an in-flight task)
- intended editor mode (Agent to actually run git and persist the SOURCE_OF_TRUTH write; Ask or Plan to dry-run the proposed commands without touching the filesystem)

Operating rules:
- Do not implement production code. This command manages the git worktree lifecycle and writes one SOURCE_OF_TRUTH section; it changes no product code.
- **Handoff:** end with the adaptive `### Handoff` block per `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full).
- **Git-gate first (ADR-0074 D-2).** Run `git rev-parse --is-inside-work-tree` on the target codebase path. IF it is not a git repository, return a short `NO_OP_TRACE` naming the gate and stop: this command does nothing on non-git projects, and the task continues on the single working tree unchanged.
- **Opt-in (ADR-0074 D-2).** Provision only when isolation is explicitly requested (the `provision` or `attach` action, or an opt-in signal from `task-init`). Never provision a worktree as a side effect of another action. When isolation is not requested, this command is a no-op.
- **Naming conventions (ADR-0074).** Let `<task-dir>` be the full task-folder name (`YYYY-MM-DD_<task-slug>`, the `active/` directory name, not the bare slug) so branch names stay unique across dates. Derive the task branch as `task/<task-dir>` and the worktree path as `../<repo-basename>-worktrees/<task-dir>`. Keep the worktree outside the main working tree so it is never nested inside the tracked repo.
- **Provision action.** In Agent mode, create the worktree and branch off the base branch: `git worktree add -b task/<task-dir> ../<repo-basename>-worktrees/<task-dir> <base-branch>`. The new worktree's HEAD comes from the base branch's committed HEAD, so uncommitted work in the main tree is not carried over (git-scm behavior; see `REFERENCES.md`). In Ask or Plan mode, emit the exact command as a `PROPOSED` step and do not run it.
- **Branch-collision handling (git one-checkout-per-branch rule).** A branch checks out in only one worktree at a time. Before `add`, check `git worktree list` and `git branch --list task/<task-dir>`. IF `task/<task-dir>` already exists and is checked out in another worktree, do NOT `--force`; stop and surface the collision so the user renames or reuses it. IF the branch exists but is not checked out anywhere, attach it with `git worktree add ../<repo-basename>-worktrees/<task-dir> task/<task-dir>` (no `-b`).
- **Attach action (retrofit).** For a task already in progress, run the same provisioning against the current base branch and record the result, without touching any task-memory file other than the SOURCE_OF_TRUTH `## Workspace` write below. This is the path that adopts a running task.
- **Status action.** Report the task's worktree path, branch, and `git worktree list` state read-only; write nothing.
- **Record the workspace (substrate write).** On a successful provision or attach, write a `## Workspace` section into `SOURCE_OF_TRUTH.md` with the worktree path, the task branch, and the base branch it was cut from. This is a substrate write: follow `commands/_shared/substrate-write-protocol.md` (transaction header above the section, one audit line in `.wos/VERIFICATION_LOG.jsonl`). This is the only file this command writes.
- **Distinct from fleet (ADR-0074 D-3).** Do not create, merge, or remove any `implement-fleet` slice worktree. When a task worktree is active, `implement-fleet` branches its slice worktrees off `task/<task-dir>`; that behavior lives in `implement-fleet`, not here.
- **Never tear down.** This command does not remove worktrees or delete branches. Teardown is `task-close`'s responsibility (ADR-0074 D-5, D-6). If the user asks to remove a worktree, route to `task-close`.
- **Idempotency and no-op.** IF the task already has a `## Workspace` section pointing at a live worktree (present in `git worktree list`), return a short `NO_OP_TRACE`; do not re-add or rewrite.
- Multi-repo tasks (a `## Repositories` section in `SOURCE_OF_TRUTH.md`) are out of scope for this version: do NOT provision. Return a short refusal naming multi-repo worktree provisioning as unsupported in v1, and ask the user to name the single repo to isolate (or to run `git worktree` per repo by hand). Never silently pick one repo out of several.

Required output:
1. Git-gate result (git repo confirmed, or `NO_OP_TRACE` for a non-git project)
2. Requested action (`provision`, `status`, or `attach`) and the derived branch and worktree path
3. Collision check result (branch free, attached to an existing branch, or blocked on a checked-out branch)
4. The exact git command run (Agent) or proposed (Ask or Plan), with its real output when run
5. The `## Workspace` section written to `SOURCE_OF_TRUTH.md` (or `PROPOSED` in Ask or Plan mode), or a `NO_OP_TRACE` when already provisioned
6. Recommended next command
7. Recommended editor mode
8. Why that is the correct next step
9. What should explicitly not be done yet

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
- The git-gate ran first: a non-git project returns `NO_OP_TRACE` and no worktree is created.
- Provisioning is opt-in: a worktree is created only for an explicit `provision` or `attach` action, never as a side effect.
- The derived branch (`task/<task-dir>`) and worktree path (`../<repo-basename>-worktrees/<task-dir>`) follow the ADR-0074 conventions, and the branch-collision check ran before any `add` (no `--force`).
- On a successful provision or attach in Agent mode, `SOURCE_OF_TRUTH.md` has a `## Workspace` section with the worktree path, task branch, and base branch, written per the substrate write protocol with one audit line; in Ask or Plan mode the same content is `PROPOSED`.
- The command never removes a worktree or deletes a branch (teardown is `task-close`), and never touches an `implement-fleet` slice worktree.
- An already-provisioned task returns `NO_OP_TRACE` instead of re-adding.
- Output ends with a complete `### Handoff` block per the adaptive format in `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract`.
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
Optimize for a safe, opt-in, git-gated provision that never forces a branch, never tears down, and records exactly one workspace section so downstream commands and `task-close` can find the worktree.

<!-- cache-breakpoint -->
