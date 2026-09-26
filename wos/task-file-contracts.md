---
activation: model_decision
description: Required and optional task files: purpose and structure. Load when the file structure is in question.
---

# Task file contracts

Defines the required and optional task-memory files under each `projects/<client>__<project>/active/YYYY-MM-DD_<task-slug>/` folder.

## Required task files

Every task must start with these files:

- `README.md`
- `TASK_STATE.md`
- `SOURCE_OF_TRUTH.md`
- `DECISIONS.md`
- `IMPLEMENTATION_PLAN.md`

### README.md
Purpose:
- short human summary of the task

Should contain:
- task name
- project name
- short summary
- objective
- current status

### TASK_STATE.md
Purpose:
- operational memory of the task
- current workflow truth
- resumability anchor

Must reflect:
- current phase
- current known facts
- canonical decisions
- blockers
- last completed step
- active files in scope
- risks to watch
- recommended next step
- **work complexity** for the next execution step (`LOW` | `MEDIUM` | `HIGH` | `N/A`) when applicable (see **Work complexity (capability routing)**)
- current closure target

### SOURCE_OF_TRUTH.md
Purpose:
- explicit list of the sources that should drive decisions

Should include when relevant:
- active codebase / repo
- active branch
- main files in scope
- tickets / docs / Figma / links
- official external docs if relevant
- optional `## Repositories` section for multi-repo tasks (only when 2 or more product repositories are in scope; see `## Multi-repo support (v1)` for the schema). Single-repo tasks omit this section and continue using the existing `active codebase / repo` field unchanged.

### DECISIONS.md
Purpose:
- normative record of approved decisions only

Do not use it for:
- discarded alternatives
- brainstorming
- long historical discussion

Structure:
- `## Locked decisions`: `### D-N` entries, the maintainer's own input. This is the only section a review reads as authorization.
- `## Provisional decisions` (P-1): `### P-N: <title>` entries the agent chose from evidence when the request left a needed decision open, never recorded as the maintainer's input. Each entry carries an `Evidence:` line (a file and line on the task branch, or a quote from the request), an `Impact:` line (`high` when it touches data, security, payments or cost, else `normal`), and `Status: provisional`. A P-N is never edited or moved. The maintainer confirms it with a new `### D-N` under `## Locked decisions` carrying `Confirms: P-N`, or replaces it with a new `### D-N` there carrying `Supersedes: P-N`. WHILE a P-N is not yet confirmed or superseded by the maintainer, the agent SHALL correct it only by appending a new `### P-N` that carries a `Replaces: P-M` line and the reason, and SHALL leave P-M exactly as written (ADR-0235). Plans SHALL cite only the newest entry of a replacement chain. `Replaces:` links two P-Ns only, and the maintainer's `Confirms:` and `Supersedes:` paths are unchanged. Merging the draft PR that lists a P-N does not confirm it; the P-N stays provisional until the maintainer confirms it that way.

### IMPLEMENTATION_PLAN.md
Purpose:
- official incremental plan for the task

Should include:
- target behavior
- current gaps
- constraints
- slices or phases (each slice should record **work complexity** `LOW` | `MEDIUM` | `HIGH` when execution risk differs across slices)
- validation expectations
- risks and mitigations

## Optional task files

Create these only when the phase actually requires them.

### IMPACT_ANALYSIS.md
Create when:
- the task starts unclear
- blast radius is not yet known
- contracts/schema/runtime risk is present

### INVARIANTS_AND_NON_GOALS.md
Create when:
- implementation boundaries need to be locked
- what must not change needs to be explicit
- scope creep risk is real

### TEST_STRATEGY.md
Create when:
- the task has meaningful regression risk
- validation choices matter enough to justify a dedicated artifact

### PR_PACKAGE.md
Create when:
- the task is ready for delivery
- the diff is stable enough to summarize
- PR packaging is useful

To start faster, copy repo-root `templates/PR_PACKAGE.md` into the task folder and fill placeholders before running `pr-package`.

### DB_CONTEXT.md
Create when:
- the task touches a database (currently `db-context-supabase` for Supabase projects and `db-context-postgres` for raw Postgres; additional providers ship as new `db-context-*` commands) and grounded, point-in-time schema is needed for planning, implementation, or review
- a `db-context-*` command was run for this task; the snapshot is fully owned by that command (auto-generated; user notes belong in `DECISIONS.md` or `TASK_STATE.md`, not here)
- Filename remains `DB_CONTEXT.md` regardless of which `db-context-*` variant produced it; the snapshot header identifies the source provider.

### SLICES/

Lifecycle (v3 wave3, item G): a slice note is born as a skeleton BEFORE the first in-scope edit (goal, approved scope, complexity, Status: in progress) and FILLED at close, never rewritten; see the slice-note-first floor in `commands/implement-approved-slice.md` and its mirror in `commands/slice-closure.md`. SLICES/*.md is outside the substrate protocol and excluded from SHA batches.
Create when:
- the task is being executed in meaningful slices
- slice-level traceability helps implementation or resumption

### LEARNINGS.md
Create when:
- a slice involved a failed attempt or surprising blocker worth recording
- a `post-review-pivot` happened (a pivot is a learning by definition)
- an `incident-triage` HOTFIX or ESCALATE produced a root cause future tasks should avoid

Task-scoped reflexion-style log per ADR-0017. Bootstrap from `templates/LEARNINGS.md`. Each entry is 5 required bullets, `Anchor:`, `Tried:`, `Failed because:`, `Next time:`, `Cross-project promotion:`, plus an optional `Tags:` bullet that `scripts/rank-learnings.sh` scores for retrieval (ADR-0071). Manual promotion path to `/USER_MEMORY.md ## Cross-project learnings` for durable cross-project lessons (slice 05 / ADR-0016).
