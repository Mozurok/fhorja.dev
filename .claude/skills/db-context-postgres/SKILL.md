---
name: db-context-postgres
description: |-
  Validate that a generic Postgres database (GCP Cloud SQL, GKE Autopilot, self-hosted, etc.) is reachable via psql or pg_dump, introspect a user-scoped subset of the schema (extensions, tables, columns, indexes, foreign keys, and optionally RLS policies and functions), and persist the result as DB_CONTEXT.md inside the active task folder; adds a single ## DB context cross-link in SOURCE_OF_TRUTH.md. Read-only introspection only; never destructive SQL. Opt-in, not part of default task init. Use when the active task touches a non-Supabase Postgres database (Cloud SQL, GKE Autopilot Postgres, self-hosted Postgres, RDS, etc.), when planning or implementation needs verified schema rather than assumed schema, or when an existing DB_CONTEXT.md is stale. Do not use without an active task folder (run task-init first), when the task does not touch a database, when the target is Supabase (use db-context-supabase), or when the user wants to record a schema decision (use decision-interview).
metadata:
  category: database-context
  primary-cursor-mode: Ask
  multi-repo-aware: false
  context-layers-consumed:
    - memory
    - retrieved
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
    - full
  provenance: first-party
  token-budget: 3200
  suggested-model: claude-sonnet-4-6
---

Act as a senior/staff engineering database context capture for the active task, scoped to a generic Postgres deployment (GCP Cloud SQL, GKE Autopilot Postgres, self-hosted, AWS RDS, etc.) accessed via `psql` or `pg_dump`.

Goal:
Validate that connection params resolve to a reachable Postgres instance, introspect a user-scoped subset of the schema (extensions, tables, columns, indexes, foreign keys, and optionally RLS policies and functions), and persist the result as `DB_CONTEXT.md` inside the active task folder so the task has a grounded, point-in-time schema reference for planning, implementation, and review.

This command is opt-in. It is not part of the default task initialization flow; run it after `task-init` only when the task actually touches Postgres data, schema, or RLS.

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
- active task path (or enough context to resolve `projects/<client>__<project>/active/YYYY-MM-DD_<task-slug>/`)
- connection params, provided via one of:
  - environment variables `PGHOST`, `PGPORT`, `PGUSER`, `PGDATABASE`, `PGPASSWORD` (or `PGSSLMODE`)
  - a `DATABASE_URL` (`postgres://user:pass@host:port/dbname?sslmode=...`)
  - a `~/.pgpass` entry plus host/db identifiers
- scope of introspection, supplied by the user as one or more of:
  - list of table names (qualified `schema.table` or unqualified for the default `public` schema)
  - list of schemas to include in full (use sparingly; large schemas should be narrowed)
- depth flag (one of):
  - `tables-only`: tables, columns with types, primary keys, not-null flags, indexes, foreign keys
  - `tables+rls` (default): `tables-only` plus row-level security policies for each in-scope table when RLS is in use
  - `full`: `tables+rls` plus relevant functions, triggers, extensions, and server version metadata
- optional: refresh flag (`refresh` to regenerate; default is to fail with `NO_OP_TRACE` if a non-stale `DB_CONTEXT.md` already exists for the same scope)

Project repository files to read:
- projects/<client>__<project>/active/YYYY-MM-DD_<task-slug>/TASK_STATE.md
- projects/<client>__<project>/active/YYYY-MM-DD_<task-slug>/SOURCE_OF_TRUTH.md
- projects/<client>__<project>/active/YYYY-MM-DD_<task-slug>/DB_CONTEXT.md (only if it already exists, for refresh comparison)

Project repository files to update:
- projects/<client>__<project>/active/YYYY-MM-DD_<task-slug>/DB_CONTEXT.md (create or fully regenerate; never partial-merge)
- projects/<client>__<project>/active/YYYY-MM-DD_<task-slug>/SOURCE_OF_TRUTH.md (append-only: add a single `## DB context` section pointing to `./DB_CONTEXT.md` if not already present)

Operating rules:
- Do not implement production code, migrations, or destructive SQL.
- Only issue read-only introspection via `psql` (e.g. `\dt`, `\d+`, queries against `information_schema` / `pg_catalog`) or `pg_dump --schema-only --no-owner --no-privileges`. Never run `INSERT` / `UPDATE` / `DELETE` / `DROP` / `ALTER` / `TRUNCATE` / `GRANT` / `REVOKE` for any reason; redirect the user to the appropriate implementation command and stop.
- Do not invent tables, columns, types, indexes, foreign keys, policies, or functions. Every recorded field must come from the live introspection output or from explicit user-supplied scope.
- Always record `Last refreshed:` as today's date in `YYYY-MM-DD` format, the resolved host/database identifier, and the server version (`SELECT version()`). Stale snapshots without these fields are invalid.
- Never dump the entire database. If the target schema has more than 25 tables and the user provided no narrowing list, ask one targeted question to narrow scope before introspecting.
- Re-run policy: regeneration replaces `DB_CONTEXT.md` in full. Do not partial-merge. Handwritten notes belong in `DECISIONS.md` or `TASK_STATE.md`. State this explicitly when proposing a refresh that overwrites an existing file.
- Cross-link policy: `SOURCE_OF_TRUTH.md` gets at most one `## DB context` section with a single relative pointer to `./DB_CONTEXT.md`. Do not duplicate schema content into `SOURCE_OF_TRUTH.md`.
- Do not modify other task-scoped artifacts (`TASK_STATE.md`, `DECISIONS.md`, `IMPLEMENTATION_PLAN.md`, `IMPACT_ANALYSIS.md`, `INVARIANTS_AND_NON_GOALS.md`, `TEST_STRATEGY.md`, `PR_PACKAGE.md`, slice files).
- Treat task-memory write policy per `WORKFLOW_OPERATING_SYSTEM.md`: `PROPOSED` in Ask/Plan mode, `APPLIED` only in Agent mode.
- Mark fields as `[unclear from psql output]` when the introspection returned ambiguous or partial data; never fill gaps with guesses.
- Output is intentionally bounded. Do not produce schema analysis, ER diagrams, or design recommendations beyond the snapshot itself; routing those follow-ups belongs in subsequent commands (`impact-analysis`, `decision-interview`, `implementation-plan`).
- Never log passwords or full `DATABASE_URL` values in the snapshot or transcript; record only host + database name + user (never the password component).
- **Handoff:** end with the adaptive `### Handoff` block per `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract`. Default `Run now`: read TASK_STATE.md `Last completed step`; if it was `task-init`, default to `impact-analysis`; if uncertain, default to `what-next`.

Snapshot format (canonical):

```text
# DB_CONTEXT

## Snapshot metadata
- Provider: postgres
- Deployment: <cloud-sql | gke-autopilot | self-hosted | rds | other>
- Host/database: <host>/<dbname> (user: <user>)
- Server version: <output of SELECT version()>
- Last refreshed: YYYY-MM-DD
- Depth: tables-only | tables+rls | full
- Scope: <comma-separated list of schema.table or schema.* entries actually introspected>

## Extensions (only when depth = full)
- <extension_name> <version>

## Tables

### <schema>.<table>
- Columns:
  - <column_name> <type> [PK] [NOT NULL] [DEFAULT <expr>]
- Primary key: <column(s)>
- Foreign keys:
  - <column> -> <ref_schema>.<ref_table>(<ref_column>) [ON DELETE <action>] [ON UPDATE <action>]
- Indexes (non-PK, non-unique-constraint):
  - <index_name> ON (<columns>) [UNIQUE] [WHERE <predicate>]
- RLS enabled: yes | no | n/a
- RLS policies (only when depth >= tables+rls and RLS enabled):
  - <policy_name> [<command: SELECT/INSERT/UPDATE/DELETE/ALL>] FOR <role>: <USING expression> / <WITH CHECK expression>

## Functions (only when depth = full)
### <schema>.<function_name>(<args>)
- Returns: <return_type>
- Language: <plpgsql | sql | c | ...>
- Security: <DEFINER | INVOKER>
- One-line summary: <verbatim COMMENT ON FUNCTION if present, else "[no COMMENT in source]">
```

Sections that have no content for the chosen depth must be omitted entirely rather than left empty.

Required output:
1. Resolved active task path.
2. Result of the connectivity precondition check (`psql -c "SELECT 1"` or equivalent succeeded / failed, plus resolved host/db/user; never the password).
3. Resolved scope (tables/schemas) and depth flag.
4. Whether this is a `create` or a `refresh` of `DB_CONTEXT.md`, and (on refresh) a one-line drift summary versus the prior snapshot (e.g., "3 new columns, 1 dropped table, RLS toggled on `public.orders`").
5. Exact content for `DB_CONTEXT.md` using the canonical snapshot format.
6. Exact patch to `SOURCE_OF_TRUTH.md` adding the `## DB context` cross-link, or `SKIP` if the link is already present.
7. Recommended next command (must exist in `commands/*.md`; verify against directory listing before output).
8. Recommended editor mode for that next command.
9. Why that is the correct next step.

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
- The connectivity precondition check is performed first and its result is reported; if it failed, no `DB_CONTEXT.md` content is proposed and the run ends with `NO_OP_TRACE` plus the actionable configuration line (missing env var, unreachable host, auth failure, etc.).
- The proposed `DB_CONTEXT.md` includes `Provider`, `Deployment`, `Host/database`, `Server version`, `Last refreshed`, `Depth`, and `Scope` metadata, and at least one populated `## Tables` entry (or an explicit `NO_OP_TRACE` if the requested scope returned no tables).
- Every column type, index, foreign key, policy, extension, and function entry is grounded in the live `psql` / `pg_dump` output; no field is fabricated. Ambiguous fields are marked `[unclear from psql output]`.
- No destructive SQL was issued. Only read-only introspection was used.
- No credentials are leaked: passwords and full `DATABASE_URL` values never appear in the snapshot or transcript.
- No task-scoped artifact other than `DB_CONTEXT.md` and (at most) a single `## DB context` cross-link in `SOURCE_OF_TRUTH.md` is modified.
- On refresh, the prior `DB_CONTEXT.md` is fully replaced (no partial merge), and the drift summary in the required output makes the change auditable.
- `### Artifact changes` marks the patches as `PROPOSED` in Ask mode or `APPLIED` only when the user explicitly authorized Agent persistence.
- The basename in the `Run now:` line corresponds to a real file in `commands/<name>.md`.
- Output ends with a complete `### Handoff` block per the adaptive format in `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract`.
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
Optimize for fidelity to the live Postgres schema, point-in-time auditability, narrow scope (no full-DB dumps), credential hygiene, and minimal disruption to whatever task-scoped work was in progress before this capture.

<!-- cache-breakpoint -->
