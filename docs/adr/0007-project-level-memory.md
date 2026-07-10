# ADR-0007: Project-level memory layer

- **Status**: Accepted
- **Date**: 2026-05-08
- **Tags**: memory-layers, project-charter, references, task-init, gitignore-policy

## Context

Before this layer existed, the workflow had two memory layers:

1. **Repository memory**: the WOS, command files, templates, and scripts. Stable across all tasks and projects; this is the "operating system" itself.
2. **Task memory**: artifacts under `projects/<client>__<project>/active/YYYY-MM-DD_<task-slug>/` (`TASK_STATE.md`, `SOURCE_OF_TRUTH.md`, `DECISIONS.md`, etc.). Scoped to one task; born and archived together.

Two failure modes recurred when project context lived only at the task layer:

1. **Re-asking the same questions per task**. Without a persistent project context, every new `task-init` had to re-elicit stack, planned repositories, regulatory or compliance constraints, primary stakeholders, and durable external references. For projects with multiple tasks (most non-trivial work), this was both slow and a source of accidental drift between tasks.
2. **Research orphaned to a single task**. External references captured during exploration (vendor docs, regulatory text, framework upgrade notes) would die with the task folder when it moved to `archive/`. The next task on the same project had to re-find the same sources, often without knowing they had already been read.

The workflow needed a memory layer that **outlives any single task** but is still scoped to a specific project (so the open-source distribution does not carry one user's project specifics into another user's checkout).

A second design force was the **gitignore policy**. The repo is open source under AGPL-3.0; project memory is per-user and per-machine. It should not enter the public distribution. The natural placement (`projects/<client>__<project>/`) needed to be gitignored without breaking task-init or capture-references workflows.

## Decision

The workflow adds a third memory layer between repository and task: **project-level memory**, stored under `projects/<client>__<project>/` with two canonical files:

- **`PROJECT_CHARTER.md`**: high-level project context. Created by `project-bootstrap` (a dedicated zero-state command). Carries: project name, status, objective, stack, planned repositories (with multi-repo schema when N >= 2), default workspace, constraints, non-goals, stakeholders, and references pointer. Read by `task-init` to seed each new task's `SOURCE_OF_TRUTH.md` automatically.
- **`REFERENCES.md`**: external references with freshness metadata. Seeded by `project-bootstrap` if the user pre-supplies references; appended to by `capture-references` (the canonical command for adding entries). Each entry: URL, accessed date, summary, optional verbatim key points, tags. Deduplicated by URL.

Lifecycle rules (enforced by command-level `Operating rules:` and the WOS decision table):

- `project-bootstrap` is the **only** command that creates these files, and only when the project folder did not exist before the run.
- `capture-references` is the **only** command that appends to `REFERENCES.md`. No task-scoped command may append.
- `task-init` reads both files when present and links to them from the task's `SOURCE_OF_TRUTH.md` under a `## Project-level memory` section. When the project was not bootstrapped, `task-init` warns the user with a one-line note ("project not bootstrapped: recommended to run `project-bootstrap` first to capture project-level context") and proceeds with placeholders. The task is never blocked.
- Project-level memory is **never modified by task-scoped commands**. Tasks reference but do not mutate `PROJECT_CHARTER.md` or `REFERENCES.md`.

The entire `projects/` directory is gitignored. Project-level memory is per-user; it is not part of the open-source distribution. It persists locally so future Claude Code sessions on the same machine recover full project context without re-asking.

## Consequences

### Positive

- **Stack and constraint context is captured once per project**. New tasks under the same project inherit it automatically. The user is not asked the same setup questions on every task-init.
- **External research outlives the task**. References captured during one task remain available for all subsequent tasks under the same project. Deduplication by URL prevents accumulating duplicates as exploration revisits the same sources.
- **Per-user privacy**. The gitignore policy means commercial or sensitive project context never enters the open-source repo. Contributors can fork and use the workflow on their own private projects without polluting upstream.
- **Multi-repo at the project layer**. Projects that touch 2+ repositories (frontend + backend + shared, etc.) record the multi-repo schema once in `PROJECT_CHARTER.md`. Each task's `SOURCE_OF_TRUTH.md` mirrors that schema via task-init. The WOS multi-repo support v1 schema lives at the project layer naturally.
- **Retroactive bootstrap is safe**. A project folder that exists ad-hoc (a task was created before a charter) can have `project-bootstrap` run later to add the charter without disturbing existing tasks.

### Negative

- **One more layer to learn**. New users have to internalize three memory layers (repo / project / task) instead of two. The CLAUDE.md and README.md document the layers explicitly, but the cognitive load is real.
- **Local-only persistence**. Because `projects/` is gitignored, project-level memory does not sync between machines unless the user manually copies it (e.g., via dotfile sync, a private repo, or rsync). Multi-machine workflows have to handle that themselves.
- **No team-share path**. A team that wants to share `PROJECT_CHARTER.md` across maintainers cannot do so through this repo's distribution; they need a separate private repo or document store. The workflow does not currently provide guidance on that pattern.

### Neutral

- The `projects/` directory must remain gitignored even when this repo is mirrored or forked. Forks that accidentally commit project memory leak per-user context. The gitignore is checked into the repo, so accidental commits are blocked at the source.

## Alternatives considered

### Alternative 1: Project context inline in every task

- Each task's `SOURCE_OF_TRUTH.md` carries the full stack, repos, constraints. No separate project layer.
- Rejected: re-asks the user every task-init; no shared place for project-wide references; references die with the task.

### Alternative 2: Project context in a single global file

- `~/.my-work-tasks/projects.md` aggregates all projects.
- Rejected: a single global file does not scale across many concurrent projects; cross-project context bleed; deletion of a project requires editing a shared file.

### Alternative 3: Project context committed to the repo

- `PROJECT_CHARTER.md` lives under `projects/<client>__<project>/` and is **not** gitignored; users fork to maintain their own.
- Rejected: leaks per-user context into the open-source distribution; private clients (regulatory, commercial) cannot adopt the workflow without leaking their project names; conflicts with the AGPL-3.0 distribution model where the upstream repo carries no user data.

## References

- `WORKFLOW_OPERATING_SYSTEM.md` → `## Project-level memory` (definition, files, decision table; routing-critical content stays inline).
- `wos/project-level-memory.md` (lifecycle narrative, motivation, edge cases; lazy-loaded).
- `commands/project-bootstrap.md` (creates `PROJECT_CHARTER.md` and `REFERENCES.md`).
- `commands/capture-references.md` (canonical append to `REFERENCES.md`).
- `commands/task-init.md` (reads both files; seeds `SOURCE_OF_TRUTH.md`).
- `.gitignore` (line ignoring `projects/`).

## Notes

This ADR was written after retroactively bootstrapping the meta-project `bmazurok__my-work-tasks` (the my_work_tasks repo using its own workflow on itself). That bootstrap surfaced the "project folder existed but charter was missing" edge case explicitly; resolution was to allow `project-bootstrap` against a partially-populated folder. The retroactive bootstrap is documented in the project's own `PROJECT_CHARTER.md` notes section.
