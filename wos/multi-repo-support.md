---
activation: model_decision
description: Multi-repo task schema, locked decisions, invariants, decision table. Load when SOURCE_OF_TRUTH.md contains a ## Repositories section.
---

# wos/multi-repo-support.md

Lazy reference for `## Multi-repo support (v1)` in the spec. The header, opt-in discriminator paragraph, and the `### Command coverage (G4 v1)` lists (multi-repo-aware vs deferred commands) remain in `WORKFLOW_OPERATING_SYSTEM.md` because they are routing-relevant. This file holds the schema, locked decisions, invariants, non-goals, runtime decision table, and implementation notes.

Load this file when:
- a task is using or about to use multi-repo mode and the schema or runtime behavior is needed
- a contributor is reviewing locked decisions, invariants, or non-goals of the multi-repo design
- the spec stub for `## Multi-repo support (v1)` is not enough to resolve a multi-repo question (rare for single-repo tasks)

Single-repo tasks (the default, no `## Repositories` section in `SOURCE_OF_TRUTH.md`) do not need this file. The 7 deferred commands listed in the spec stub also do not need it: they ignore the `## Repositories` section in v1.

---

### When to use multi-repo mode

A task is multi-repo when it touches code or configuration in two or more product repositories that ship coordinated. Typical examples:
- a feature requiring backend API change plus frontend client call
- an infrastructure change touching service plus IaC repos
- a shared library bump propagated across multiple consuming repos

Single-repo tasks (the default) do not use this mode and continue with the existing single-repo schema.

### Schema: `## Repositories` section in SOURCE_OF_TRUTH.md

When a task is multi-repo, `SOURCE_OF_TRUTH.md` includes an optional `## Repositories` section with N (where N is at least 2) entries. Each entry has:

- **identifier**: short repo tag, lowercase, hyphenated (e.g., `backend`, `frontend`, `web-app`, `mobile-ios`). Must be unique within the task and must match the convention used in slice filenames (see D5).
- **path**: local product workspace path (e.g., `~/code/acme-platform-backend`).
- **base branch**: integration branch this repo's PRs target (e.g., `origin/main`, `origin/staging`).
- **role tag**: one of `backend` / `frontend` / `shared` / `infra` / `mobile` / `other`. Documentation-only; helps future readers.

Example:

```yaml
## Repositories

- identifier: backend
  path: ~/code/acme-platform-backend
  base branch: origin/main
  role: backend

- identifier: frontend
  path: ~/code/acme-platform-frontend
  base branch: origin/main
  role: frontend
```

The presence of this section is the discriminator between single-repo and multi-repo task modes. Commands that support multi-repo branch their behavior on it; commands that do not support multi-repo (the 7 deferred commands listed in the spec stub) ignore it and operate single-repo-default.

### Schema: `## Workspace` section in SOURCE_OF_TRUTH.md (opt-in, ADR-0074)

Per-task worktree isolation is opt-in and git-gated. When a task opts in on a git-backed project, `task-workspace` provisions one git worktree plus a task branch and records them in an optional `## Workspace` section in `SOURCE_OF_TRUTH.md`. Each field:

- **worktree path**: the linked working tree's path (e.g., `../myrepo-worktrees/2026-07-01_my-task`).
- **task branch**: the branch checked out in that worktree (e.g., `task/2026-07-01_my-task`).
- **base branch**: the branch the worktree was cut from (e.g., `main`).

Example:

```yaml
## Workspace

worktree path: ../myrepo-worktrees/2026-07-01_my-task
task branch: task/2026-07-01_my-task
base branch: main
```

The presence of this section marks a task as worktree-isolated. It is written by `task-workspace`, read by `task-close` for teardown, and read by `implement-fleet` (fleet slice worktrees branch off the task branch when it is present). A task without this section behaves as today (single working tree). Multi-repo tasks (a `## Repositories` section) are out of scope for v1 worktree provisioning: only the single active repo is provisioned, and the command says so.

### Locked decisions (D1 to D7)

- **D1**: Multi-repo support is additive only. Single-repo tasks continue working without changes to current `SOURCE_OF_TRUTH.md` schema or command contracts.
- **D2**: Each slice operates in exactly one repo's workspace. Slices spanning multiple repos are invalid; logical changes that touch backend plus frontend decompose into ordered slices, one per repo.
- **D3**: `branch-commit`, `team-update`, `capture-observation`, and `direction-adjust` require no schema change for multi-repo support. They operate per-repo or on `TASK_STATE.md` only.
- **D4**: Multi-repo information lives in `SOURCE_OF_TRUTH.md` as an internal `## Repositories` section (schema above).
- **D5**: Slice files use flat numbering with explicit repo identifier in the slug. Pattern: `SLICES/NN_<repo>-<slice-slug>.md`. The `<repo>` token must match an entry in the `Repositories` section. Cross-repo slice ordering is captured by the global `NN` numbering. Single-repo tasks keep the existing `SLICES/NN_<slice-slug>.md` pattern with no repo prefix.
- **D6**: `pr-package` produces one PR per repo. Output filename pattern in multi-repo mode: `PR_PACKAGE.<repo>.md`. Cross-repo coordination notes (rollout order, dependencies between PRs) live in `TASK_STATE.md` `Risks to watch` plus per-PR body cross-reference lines (`Related PR: <other-repo-PR-url>`).
- **D7**: For G4 v1, 4 commands were multi-repo aware: `task-init` writes the `## Repositories` schema, and 3 consumers read it (`code-locate`, `impact-analysis`, `pr-package`).
- **D7.v2 (2026-06-04, per D.4 of Fhorja improvement plan):** G4 v2 expanded coverage to 7 commands. Added: `implement-approved-slice` (per-repo file lists + validation evidence), `slice-closure` (per-repo exit-criteria validation), `where-we-at` (per-repo progress checkpoint). The 4 remaining deferred commands (`targeted-questions`, `implement-slice-complement`, `pr-feedback-ingest`, `post-review-pivot`) keep single-repo defaults; D.1 audit (2026-06-04) ranked them lower-priority based on Bruno's FE+BE workflow patterns. G4 v3 further expansion is contingent on new friction signals.

### Invariants (I1 to I4)

- **I1**: Single-repo task contract is preserved. Existing `SOURCE_OF_TRUTH.md` without a `Repositories` section continues working unchanged in all 53 commands.
- **I2**: Slice atomicity per workspace. `implement-approved-slice` operates on exactly one repo per invocation. No concurrent multi-workspace execution.
- **I3**: GitHub PR atomicity. One PR per repo. No cross-repo PR fiction.
- **I4**: One `TASK_STATE.md` per task folder, even when multi-repo. No per-repo TASK_STATE files. Same applies to `DECISIONS.md` and `IMPLEMENTATION_PLAN.md`.

### Non-goals (NG1 to NG5)

- **NG1**: Concurrent `implement-approved-slice` invocations across repos. Sequential per-repo execution only.
- **NG2**: Cross-repo refactor automation. The user coordinates manually.
- **NG3**: Repository discovery or auto-detection. The user explicitly lists repos in `SOURCE_OF_TRUTH.md`.
- **NG4**: Multi-repo support in the 7 deferred commands. Punted to G4 v2.
- **NG5**: Per-repo `TASK_STATE.md`, `DECISIONS.md`, or `IMPLEMENTATION_PLAN.md`. Task-level memory is shared.

### Decision table (runtime behavior)

| Input condition | Action | Expected effect |
|---|---|---|
| `SOURCE_OF_TRUTH.md` has no `## Repositories` section | Treat as single-repo; existing command behavior | Zero change for single-repo tasks (backwards-compat preserved) |
| `SOURCE_OF_TRUTH.md` has `## Repositories` with N (where N is at least 2) entries | Treat as multi-repo; updated commands consume the array | `code-locate` searches one repo per invocation; `impact-analysis` produces per-repo blast radius; `pr-package` runs once per repo |
| Slice file `SLICES/NN_<repo>-<slug>.md` where `<repo>` matches a `Repositories` entry | `implement-approved-slice` operates in that repo's workspace | Standard slice execution scoped to one workspace |
| Slice file `SLICES/NN_<slug>.md` (no repo prefix) | Treat as single-repo task slice (backwards-compat) | No change |
| `pr-package` invoked with explicit `repo` matching a `Repositories` entry | Generates `PR_PACKAGE.<repo>.md` for that repo | Single-repo PR produced |
| `pr-package` invoked without `repo` flag in a multi-repo task | Error: multi-repo task requires explicit repo input | Forces user to disambiguate |
| Repo identifier in slice filename does not match any `Repositories` entry | Error in `implement-approved-slice`: unknown repo identifier | Forces user to fix the filename or add the repo |

### Implementation notes

- Slice filename repo prefix (`<repo>-`) is enforced by `implement-approved-slice` only when the task has a `Repositories` section. For single-repo tasks, `<repo>-` prefix in slice filenames is ignored; existing slice naming continues to work.
- Repo identifiers must be lowercase, hyphenated, and unique within the task. Duplicate identifiers are invalid output for `task-init` and any subsequent edit to `SOURCE_OF_TRUTH.md`.
- Adding a repo mid-task (after some slices have already executed against a single-repo `SOURCE_OF_TRUTH.md`) is allowed but requires a `direction-adjust` to record the schema migration as a decision.
