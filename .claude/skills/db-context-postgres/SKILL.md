---
name: db-context-postgres
description: |-
  Validate that a generic Postgres database (Cloud SQL, GKE Autopilot, RDS, self-hosted) is reachable via psql or pg_dump, introspect a user-scoped subset of the schema (extensions, tables, columns, indexes, foreign keys, optionally RLS policies and functions), and persist it as DB_CONTEXT.md with one cross-link in SOURCE_OF_TRUTH.md. Read-only introspection, never destructive SQL. Opt-in. Use when the task touches a non-Supabase Postgres and planning needs verified rather than assumed schema, or when an existing DB_CONTEXT.md is stale. Do not use without an active task folder (run task-init first), when the task touches no database, when the target is Supabase (use db-context-supabase), or to record a schema decision (use decision-interview).
metadata:
  category: "database-context"
  primary-cursor-mode: "Ask"
  multi-repo-aware: "false"
  context-layers-consumed: "memory, retrieved"
  context-layers-produced: "memory"
  tools: "Read, Write, Edit, Bash, Glob, Grep"
  x-wos-profiles: "full"
  provenance: "first-party"
  suggested-model: "claude-sonnet-5"
---

Act as a senior/staff engineering database context capture for the active task, scoped to a generic Postgres deployment (GCP Cloud SQL, GKE Autopilot Postgres, self-hosted, AWS RDS, etc.) accessed via `psql` or `pg_dump`.

Goal:
Validate that connection params resolve to a reachable Postgres instance, introspect a user-scoped subset of the schema (extensions, tables, columns, indexes, foreign keys, and optionally RLS policies and functions), and persist the result as `DB_CONTEXT.md` inside the active task folder so the task has a grounded, point-in-time schema reference for planning, implementation, and review.

This command is opt-in. It is not part of the default task initialization flow; run it after `task-init` only when the task actually touches Postgres data, schema, or RLS.

Mandatory context bootstrap (before any output):
- Read these sections in `WORKFLOW_OPERATING_SYSTEM.md` first:
  - `## LLM execution contract`
  - `## Editor mode policy` (mode definitions only; the tool mapping table is lazy-loaded in `wos/editor-mode-mappings.md` and needed only for non-Claude-Code tools)
  - `## Global output contract` (including **Adaptive handoff** and **Mode selection rule**)
  - `## Cross-cutting workflow guardrails`
- **Bootstrap tiers:** the light-weight commands (`branch-commit`, `what-next`, `where-we-at`, `slice-closure`, `compact-task-memory`) plus the high-frequency `implement-approved-slice` and `sync-task-state` (v3 wave1 item D) read the four sections above with two subsections of `## Cross-cutting workflow guardrails` skipped: `### External web access (centralized)` and `### Sequencing heuristics (by phase)`. Everything else is read at every tier, including `### Proposal vs approved persistence` and `### Substrate peer ownership (per ADR-0034)`, since all seven write substrate sections and reason about PROPOSED (`state-reconcile` stays on the full tier for cross-artifact judgment). The full tier is measured at 11678 tokens, the four always-read sections combined; the two skipped subsections are 1,035 of those (measured 2026-09-24), so the reduced tier is about 10,643. The leaf-reviewer tier (`verify-against-rubric`, ADR-0226) reads only `## Global output contract`, measured at 4841 tokens, plus its rubric.
- **Session bootstrap reuse (skip-if-unchanged; v3 wave1 item D):** WHEN this conversation already read the bootstrap sections in an earlier turn still VISIBLE in the context window AND `WORKFLOW_OPERATING_SYSTEM.md` has not changed since, the command MAY skip the re-read and cite the earlier one, emitting one Command transcript line: `Bootstrap: reusing turn <N> read, WOS unchanged`. Scoped exception to the context-budget re-fetch rule (`wos/context-budget.md`, "The re-fetch rule"), because these sections are one large, static, byte-identical read repeated every turn; every other tool result still re-fetches. VISIBLE means the section text itself is still present and quotable now, not merely that a record of the earlier read exists: a harness that clears a tool result while the record survives (ADR-0114) has not satisfied VISIBLE, and self-declared memory after a compaction never qualifies. A stateless-per-turn harness is excluded. The transcript line is mandatory; a silent skip is invalid output.
- **Resolving `WORKFLOW_OPERATING_SYSTEM.md` and a relative `wos/<topic>.md`.** Both resolve the same way: try the canonical workflow repository root FIRST, then the installed docs directory (`~/.claude/workflow-docs/` or `~/.cursor/workflow-docs/`, the spec at that root and topics under its `wos/`). Repository first, because the installed copy is a snapshot no sync prunes; preferring it would hide a `wos/` edit from every command until a reinstall. Name the resolved root in `### Command transcript`, and say so explicitly when NEITHER resolved rather than continuing silently, since several of these loads are MANDATORY.
- Read additional sections only when relevant to this command's role.
- Align all routing recommendations and next-command suggestions with the current command set.
- **Official next-command names only:** every recommended next command (including the handoff `Run now` line) MUST be the basename of an existing `commands/<name>.md` file in this workflow repository. Never invent names. One exception: `Run now: none` with `Mode: N/A` declares the chain ended with no honest next step, defined under `### Official command names (routing integrity)` (ADR-0126); use it only then, never to end a chain that has a real next step.

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
- Do not invent tables, columns, types, indexes, foreign keys, policies, triggers, or functions. Every recorded field must come from the live introspection output or from explicit user-supplied scope.
- Always record `Last refreshed:` as today's date in `YYYY-MM-DD` format, the resolved host/database identifier, and the server version (`SELECT version()`). Stale snapshots without these fields are invalid.
- Never dump the entire database. If the target schema has more than 25 tables and the user provided no narrowing list, ask one targeted question to narrow scope before introspecting.
- Re-run policy: regeneration replaces `DB_CONTEXT.md` in full. Do not partial-merge. Handwritten notes belong in `DECISIONS.md` or `TASK_STATE.md`. State this explicitly when proposing a refresh that overwrites an existing file.
- Cross-link policy: `SOURCE_OF_TRUTH.md` gets at most one `## DB context` section with a single relative pointer to `./DB_CONTEXT.md`. Do not duplicate schema content into `SOURCE_OF_TRUTH.md`.
- Do not modify other task-scoped artifacts (`TASK_STATE.md`, `DECISIONS.md`, `IMPLEMENTATION_PLAN.md`, `IMPACT_ANALYSIS.md`, `INVARIANTS_AND_NON_GOALS.md`, `TEST_STRATEGY.md`, `PR_PACKAGE.md`, slice files).
- Treat task-memory write policy per `WORKFLOW_OPERATING_SYSTEM.md`: write the file and mark it `APPLIED`.
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

## Triggers (only when depth = full)
- <trigger_name> on <schema>.<table>: <trigger definition from live introspection>

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
7. Recommended next command (must exist as `commands/<name>.md` or `commands/<name>/SKILL.md`; verify against directory listing before output).
8. Recommended editor mode for that next command.
9. Why that is the correct next step.

### Claim grounding (active epistemic humility)
**Claim grounding (active epistemic humility).** This block governs what you may assert and how you record it. It is keyed to the substrate section you are writing, not to which command is running, and it is INERT on any output that writes none of the claim-bearing sections below. Full contract and rationale: `wos/active-epistemic-humility.md`.

1. When this applies. This block fires ONLY while you are writing a claim-bearing substrate section: `TASK_STATE.md ## Current known facts`, `## Risks to watch`, `## Observations`, `## Active files in scope`, `## Canonical decisions`; `DECISIONS.md ## Locked decisions`; `IMPLEMENTATION_PLAN.md ## Current gaps`, `## Risks and mitigations`; `IMPACT_ANALYSIS.md`; `EXTERNAL_RESEARCH.md`; `REFERENCES.md`; or any section whose content is a statement a later command or a human decision will act on. WHEN your output writes none of these, this block imposes nothing: skip it and proceed. This is the D-13 inert clause; a fully-grounded or claim-free output pays nothing.

2. The unit is the load-bearing claim. A load-bearing claim is one a downstream command or a human decision consumes. A passing aside is not load-bearing; a statement someone will act on is. Apply the rest of this block per load-bearing claim, not per sentence.

3. Ground it or abstain. Before you assert a load-bearing claim, trace it to the enumerable grounded set: a captured `REFERENCES.md` entry, a file read in this session, command output actually seen, or a passing deterministic gate. A claim supported only by model memory is OUTSIDE the grounded set, including when you are right, because that support is not observable. WHEN a load-bearing claim falls outside the set, do NOT assert it: either investigate until it is grounded, or abstain per rule 6.

4. Status records provenance, never confidence. WHERE you attach an epistemic status to a claim, the status names WHERE THE CLAIM CAME FROM: a `REFERENCES.md` entry title, a file path plus line, or the gate output it came from. It SHALL NOT express a degree of certainty. Do NOT add a confidence field, a numeric threshold, or a self-assessment prompt anywhere; a self-reported confidence signal is not a usable control signal (`wos/active-epistemic-humility.md` Part 1.3). A status whose referent slot is empty is read as UNKNOWN, not as a weak yes.

5. Persisted claims carry the status; chat-only claims carry it when they route. Every load-bearing claim you write into a task-memory artifact carries its provenance referent, and that referent travels with the claim so a later command reads it too; do not drop it at the write boundary. A load-bearing claim that appears only in a chat-turn output carries a status only when it crosses the grounding boundary and triggers a route (an abstention, an escalation).

6. Abstain as a routed continuation, never a bare refusal. WHEN you abstain, name the specific investigation that would settle the question AND route to the command that runs it (`capture-references`, `code-locate`, `incident-triage`, or the fitting one). A withholding that stalls the work is invalid output. Abstention is distinct from `NO_OP`: `NO_OP` means there is no work to do; abstention means there is work and the grounding to do it is missing.

7. An unfired gate is not evidence. The absence of a fired check does not mean grounding existed. Do not read silence here as a pass.
### Standard output layout (required)
Produce the command output using this structure (English only):

### Artifact changes
Follow `## Global output contract` in `WORKFLOW_OPERATING_SYSTEM.md` for `APPLIED` / `PROPOSED` / `SKIP` rules. Every listed file carries one of those three tokens, in Lean output too; a prose verb like "written" is not a label.

### Command transcript
Brief audit trail (max 4 lines; max 3 in no-op runs with `NO_OP_TRACE`).

### Handoff
Use the adaptive ending format from `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full per session state). Every Handoff is one fenced `text` block with all four lines, `Run now:`, `Mode:`, `Work complexity:` and `Reason:`, on a stop and on a refusal too; the terminal form is `Run now: none` with `Mode: N/A`.

### Definition of done (command output)
- The connectivity precondition check is performed first and its result is reported; if it failed, no `DB_CONTEXT.md` content is proposed and the run ends with `NO_OP_TRACE` plus the actionable configuration line (missing env var, unreachable host, auth failure, etc.).
- The proposed `DB_CONTEXT.md` includes `Provider`, `Deployment`, `Host/database`, `Server version`, `Last refreshed`, `Depth`, and `Scope` metadata, and at least one populated `## Tables` entry (or an explicit `NO_OP_TRACE` if the requested scope returned no tables).
- Every column type, index, foreign key, policy, extension, trigger, and function entry is grounded in the live `psql` / `pg_dump` output; no field is fabricated. Ambiguous fields are marked `[unclear from psql output]`.
- No destructive SQL was issued. Only read-only introspection was used.
- No credentials are leaked: passwords and full `DATABASE_URL` values never appear in the snapshot or transcript.
- No task-scoped artifact other than `DB_CONTEXT.md` and (at most) a single `## DB context` cross-link in `SOURCE_OF_TRUTH.md` is modified.
- On refresh, the prior `DB_CONTEXT.md` is fully replaced (no partial merge), and the drift summary in the required output makes the change auditable.
- `### Artifact changes` marks the patches as `APPLIED`.
- The basename in the `Run now:` line corresponds to a real file in `commands/<name>.md`.
- Output ends with a complete `### Handoff` block per the adaptive format in `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract`.
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
Optimize for fidelity to the live Postgres schema, point-in-time auditability, narrow scope (no full-DB dumps), credential hygiene, and minimal disruption to whatever task-scoped work was in progress before this capture.
