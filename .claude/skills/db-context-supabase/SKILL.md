---
name: db-context-supabase
description: |-
  Validate that a Supabase MCP server is reachable, introspect a user-scoped subset of the database (tables, columns, types, RLS policies, optionally functions and recent migrations), and persist it as DB_CONTEXT.md with one cross-link in SOURCE_OF_TRUTH.md. Read-only introspection, never destructive SQL. Falls back to the local Supabase CLI when no MCP server is reachable, and never records supabase status output into an artifact because it prints the service_role key. Opt-in. Use when the task touches Supabase data, schema or RLS and planning needs verified rather than assumed schema. Do not use without an active task folder (run task-init first), when the database is not Supabase, or to record a schema decision (use decision-interview).
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
> **Output contract, in brief.** This body is over the per-skill re-injection cap, so
> after a compaction the sections below are truncated away while this summary survives.
> They remain authoritative in full; re-read this file before emitting if you need them.
>
> - `Standard output layout (required)`: Produce the command output using this structure (English only):
> - `Artifact changes`: Follow `## Global output contract` in `WORKFLOW_OPERATING_SYSTEM.md` for `APPLIED` / `PROPOSED` / `SKIP` rules. Every listed file...
> - `Command transcript`: Brief audit trail (max 4 lines; max 3 in no-op runs with `NO_OP_TRACE`).
> - `Handoff`: Use the adaptive ending format from `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full per...
> - `Definition of done (command output)`: The MCP precondition check is performed first and its result is reported. When it fails, the local CLI path is checked next; when...


Act as a senior/staff engineering database context capture for the active task, scoped to Supabase.

Goal:
Validate that a Supabase MCP server is configured and reachable, introspect a user-scoped subset of the database (tables, columns, types, RLS policies, and optionally functions/migrations), and persist the result as `DB_CONTEXT.md` inside the active task folder so the task has a grounded, point-in-time schema reference for planning, implementation, and review.

When no MCP server is reachable, the command falls back to the local Supabase CLI and produces the same snapshot from CLI output. Only when neither path is available does it end in a no-op.

This command is opt-in. It is not part of the default task initialization flow; run it after `task-init` only when the task actually touches Supabase data, schema, or RLS.

Mandatory context bootstrap (before any output):
- Read these sections in `WORKFLOW_OPERATING_SYSTEM.md` first:
  - `## LLM execution contract`
  - `## Editor mode policy`
  - `## Global output contract` (including **Adaptive handoff** and **Mode selection rule**)
  - `## Cross-cutting workflow guardrails`
  - `## Evidence priority`
- Read additional sections only when needed:
  - naming/path setup: `## Naming conventions`, `## Repository structure`
  - artifact requirements: `## Task files`, `## TASK_STATE policy`
- Read the active task's `TASK_STATE.md` to confirm there is an active task to attach the DB context to and to align the requested table/schema scope with the task objective.
- Read the active task's `SOURCE_OF_TRUTH.md` to detect any prior `## DB context` link before proposing a new one.
- Read the `commands/` directory command inventory to ensure routing recommendations are current.

Required inputs:
- active task path (or enough context to resolve `projects/<client>__<project>/active/YYYY-MM-DD_<task-slug>/`)
- scope of introspection, supplied by the user as one or more of:
  - list of table names (qualified `schema.table` or unqualified for the default `public` schema)
  - list of schemas to include in full (use sparingly; large schemas should be narrowed to specific tables)
- depth flag (one of):
  - `tables-only`: tables and columns with types, primary keys, and not-null flags
  - `tables+rls` (default): `tables-only` plus row-level security policies for each in-scope table
  - `full`: `tables+rls` plus relevant functions, triggers, and the most recent migration filenames touching in-scope tables
- optional: Supabase project ref (if the MCP server is configured for multiple projects); when omitted, use the project the MCP server is currently bound to and record which one was used
- optional: refresh flag (`refresh` to regenerate an existing `DB_CONTEXT.md`; default is to fail with `NO_OP_TRACE` if a non-stale `DB_CONTEXT.md` already exists for the same scope)
- optional: path to the local Supabase project directory. Needed only on the local CLI path below, where every CLI form runs from that directory. When omitted and the MCP path is unavailable, ask for it once instead of guessing a directory.

Project repository files to read:
- projects/<client>__<project>/active/YYYY-MM-DD_<task-slug>/TASK_STATE.md
- projects/<client>__<project>/active/YYYY-MM-DD_<task-slug>/SOURCE_OF_TRUTH.md
- projects/<client>__<project>/active/YYYY-MM-DD_<task-slug>/DB_CONTEXT.md (only if it already exists, for refresh comparison)

Project repository files to update:
- projects/<client>__<project>/active/YYYY-MM-DD_<task-slug>/DB_CONTEXT.md (create or fully regenerate; never partial-merge)
- projects/<client>__<project>/active/YYYY-MM-DD_<task-slug>/SOURCE_OF_TRUTH.md (append-only: add a single `## DB context` section pointing to `./DB_CONTEXT.md` if not already present)

Introspection path selection (MCP first, then the local CLI):
Choose the path before any introspection, in this order, and record which one was used.

1. Supabase MCP server. When the MCP server is configured, reachable, and exposes introspection tools, use it. Nothing about this path changes: same read-only rules, same scope and depth handling, same output.
2. Local Supabase CLI. WHEN no MCP server is reachable AND a local Supabase CLI is available, fall back to the CLI and produce `DB_CONTEXT.md` from its output under the local CLI branch rules below.
3. Neither. WHEN no MCP server is reachable and no local CLI is available, propose no `DB_CONTEXT.md` content and end with `NO_OP_TRACE` plus one actionable configuration line naming both paths (configure the Supabase MCP server, or bring the local stack up with `supabase start` in the local project directory and re-run). This is the existing no-op behavior and it is unchanged.

Local CLI branch (applies only when path 2 was selected):
- Availability check first. It reads the state of the local stack, not the database. Run `supabase status` from the local Supabase project directory. When it exits non-zero or reports the stack as not running, propose no `DB_CONTEXT.md` content and end with `NO_OP_TRACE` plus the actionable line naming `supabase start`. This command never starts, resets, seeds, or pushes to the stack; the user runs `supabase start` and re-runs this command.
- Secrets rule, non-negotiable. `supabase status` prints the JWT secret, the anon key, and the service_role key to stdout. That raw output is NEVER written into `DB_CONTEXT.md`, NEVER into `SOURCE_OF_TRUTH.md`, NEVER into the command transcript or any other task artifact, and NEVER echoed back in the chat output. Record three facts and nothing more: that the local stack is reachable, the DB host, and the DB port, the last two read off the `DB URL` line with the user and password components stripped (the captured example `postgresql://postgres:postgres@127.0.0.1:54322/postgres` becomes host `127.0.0.1` and port `54322`). Pasting a status block into an artifact leaks a service-role credential, which bypasses RLS, into task memory that outlives the run.
- Read-only, restated in full here because it must not live only on the MCP branch. On this branch, never run `INSERT` / `UPDATE` / `DELETE` / `DROP` / `ALTER` / `TRUNCATE` / `GRANT` / `REVOKE` through the CLI or through any connection the CLI reports. If the user requests one, redirect them to the appropriate implementation command and stop.
- The read-only set for this branch is exactly these forms, each cited to the captured Supabase CLI reference, and nothing outside it may be issued:
  - `supabase status` (availability only, subject to the secrets rule above)
  - `supabase db dump --local -f <path>` for the schema
  - `supabase db diff --local`
  - `supabase db lint --local`
  - `supabase inspect --local db <bloat|blocking|calls|locks|outliers>`
  - `supabase inspect --local report [--output-dir <string>]`
  Any subcommand outside this list is out of scope for this command, including anything that starts, resets, seeds, pushes, or applies migrations.
- Write the schema dump to a scratch path outside the task folder, read it there, and do not add it as a task artifact. `DB_CONTEXT.md` plus the single `## DB context` cross-link stay the only files this command touches.
- Target selection is explicit. The [official CLI command reference](https://github.com/supabase/cli/blob/develop/apps/cli/docs/go-cli-reference.md) (checked 2026-09-07) documents `--local` for dump, diff, lint, and inspect; dump and inspect otherwise default to the linked project. Run every listed operation from the same project directory checked by `supabase status`, with `--local` as shown. `--linked` and `--db-url` are not allowed on this local branch. Help for these listed subcommands may be read to verify installed-version support; if the local selector is unsupported or the target cannot be established, stop with `NO_OP_TRACE` and name the missing CLI or target evidence instead of emitting a snapshot labeled local. Narrow to in-scope tables while reading the dump. Record the CLI version only from observed output, otherwise keep `[unclear in source]` for the version.
- Any field the CLI output does not answer (an RLS policy, a function body, a migration filename) is marked `[unclear from CLI output]`, never guessed.

Operating rules:
- Do not implement production code, migrations, or destructive SQL.
- Only issue read-only introspection: through the MCP server on the MCP path, and through the read-only CLI forms listed above on the local CLI path. Never run `INSERT` / `UPDATE` / `DELETE` / `DROP` / `ALTER` / `TRUNCATE` / `GRANT` / `REVOKE` for any reason on either path; if the user requests one, redirect them to the appropriate implementation command and stop.
- Never record a credential. No `supabase status` output block, no service_role key, no anon key, no JWT secret, and no full connection string appears in `DB_CONTEXT.md`, in `SOURCE_OF_TRUTH.md`, in the transcript, or in the chat output. Host and port are the only connection details worth recording.
- Do not invent tables, columns, types, policies, triggers, functions, or migrations. Every recorded field must come from the MCP server's response, from the CLI output on the local path, or from explicit user-supplied scope.
- Always record `Last refreshed:` as today's date in `YYYY-MM-DD` format, the introspection path used, and the resolved Supabase project identifier (`local` on the local CLI path). Stale snapshots without these fields are invalid.
- Never dump the entire database. If the user provides a schema with more than 25 tables and no narrowing list, ask one targeted question to narrow scope before introspecting.
- Re-run policy: regeneration replaces `DB_CONTEXT.md` in full. Do not partial-merge. If the user has handwritten notes that should survive refresh, those belong in `DECISIONS.md` or `TASK_STATE.md`, not in `DB_CONTEXT.md`. State this explicitly when proposing a refresh that overwrites an existing file.
- Cross-link policy: `SOURCE_OF_TRUTH.md` gets at most one `## DB context` section with a single relative pointer to `./DB_CONTEXT.md`. Do not duplicate schema content into `SOURCE_OF_TRUTH.md`.
- Do not modify other task-scoped artifacts (`TASK_STATE.md`, `DECISIONS.md`, `IMPLEMENTATION_PLAN.md`, `IMPACT_ANALYSIS.md`, `INVARIANTS_AND_NON_GOALS.md`, `TEST_STRATEGY.md`, `PR_PACKAGE.md`, slice files).
- Treat task-memory write policy per `WORKFLOW_OPERATING_SYSTEM.md`: write the file and mark it `APPLIED`.
- Mark fields as `[unclear from MCP response]` on the MCP path, or `[unclear from CLI output]` on the local CLI path, when the introspection returned ambiguous or partial data; never fill gaps with guesses.
- Output is intentionally bounded. Do not produce schema analysis, ER diagrams, or design recommendations beyond the snapshot itself; routing those follow-ups belongs in subsequent commands (`impact-analysis`, `decision-interview`, `implementation-plan`).
- **Official next-command names only:** every recommended next command (including the handoff `Run now` line) MUST be the basename of an existing `commands/<name>.md` file in this workflow repository. Never invent names. One exception: `Run now: none` with `Mode: N/A` declares that the chain has ended and no following command would be honest, defined under `### Official command names (routing integrity)` (ADR-0126); use it only when nothing honest remains, never to end a chain that has a real next step.
- **Handoff:** end with the adaptive `### Handoff` block per `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full). Default `Run now`: read TASK_STATE.md `Last completed step`; if it was `task-init`, default to `impact-analysis`; if uncertain, default to `what-next`.

Snapshot format (canonical):

```text
# DB_CONTEXT

## Snapshot metadata
- Provider: supabase
- Introspection path: mcp | local-cli
- Project ref: <resolved-project-ref-or-alias, or "local" on the local-cli path>
- Local stack: reachable (local-cli path only; never a key, a secret, or a connection string)
- DB host/port: <host>:<port> (local-cli path only; host and port only, no user, no password)
- CLI version: <version if the CLI output reported one, else [unclear in source]> (local-cli path only)
- Last refreshed: YYYY-MM-DD
- Depth: tables-only | tables+rls | full
- Scope: <comma-separated list of schema.table or schema.* entries actually introspected>

## Tables

### <schema>.<table>
- Columns:
  - <column_name> <type> [PK] [NOT NULL] [DEFAULT <expr>]
- Primary key: <column(s)>
- Foreign keys:
  - <column> -> <ref_schema>.<ref_table>(<ref_column>)
- Indexes (non-PK, non-unique-constraint):
  - <index_name> ON (<columns>)
- RLS enabled: yes | no
- RLS policies (only when depth >= tables+rls):
  - <policy_name> [<command: SELECT/INSERT/UPDATE/DELETE/ALL>] FOR <role>: <USING expression> / <WITH CHECK expression>

## Triggers (only when depth = full)
- <trigger_name> on <schema>.<table>: <trigger definition from the MCP response or CLI output>

## Functions (only when depth = full)
### <schema>.<function_name>(<args>)
- Returns: <return_type>
- Language: <plpgsql | sql | ...>
- Security: <DEFINER | INVOKER>
- One-line summary: <verbatim COMMENT ON FUNCTION if present, else "[no COMMENT in source]">

## Recent migrations touching in-scope tables (only when depth = full)
- <migration_filename_or_id>: <one-line description from migration metadata, or "[no description in source]">
```

Sections that have no content for the chosen depth must be omitted entirely rather than left empty.

Required output:
1. Resolved active task path.
2. Which introspection path was selected (`mcp`, `local-cli`, or none) and the result of its precondition check. For the MCP path: configured / reachable / introspection tools available, or the actionable failure line. For the local CLI path: whether the local stack is reachable, reported without any key, secret, or connection string.
3. Resolved Supabase project ref/alias used for introspection, or `local` plus the DB host and port on the local CLI path.
4. Resolved scope (tables/schemas) and depth flag.
5. Whether this is a `create` or a `refresh` of `DB_CONTEXT.md`, and (on refresh) a one-line drift summary versus the prior snapshot (e.g., "3 new columns, 1 dropped table, RLS toggled on `public.orders`").
6. Exact content for `DB_CONTEXT.md` using the canonical snapshot format.
7. Exact patch to `SOURCE_OF_TRUTH.md` adding the `## DB context` cross-link, or `SKIP` if the link is already present.
8. Recommended next command (must exist as `commands/<name>.md` or `commands/<name>/SKILL.md`; verify against directory listing before output).
9. Recommended editor mode for that next command.
10. Why that is the correct next step.

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
- The MCP precondition check is performed first and its result is reported. When it fails, the local CLI path is checked next; when neither path is available, no `DB_CONTEXT.md` content is proposed and the run ends with `NO_OP_TRACE` plus the actionable configuration line.
- The proposed `DB_CONTEXT.md` includes `Provider`, `Introspection path`, `Project ref`, `Last refreshed`, `Depth`, and `Scope` metadata, and at least one populated `## Tables` entry (or an explicit `NO_OP_TRACE` if the requested scope returned no tables).
- Every column type, policy, trigger, function, and migration entry is grounded in the MCP server's response or in the CLI output; no field is fabricated. Ambiguous fields are marked `[unclear from MCP response]` or `[unclear from CLI output]`.
- No destructive SQL was issued on either path. Only read-only introspection was used, and on the local CLI path only the command forms in that branch's read-only set.
- No credential escaped the local CLI path: no `supabase status` output block, no service_role key, no anon key, no JWT secret, and no full connection string appears in `DB_CONTEXT.md`, in `SOURCE_OF_TRUTH.md`, in the transcript, or in the chat output.
- No task-scoped artifact other than `DB_CONTEXT.md` and (at most) a single `## DB context` cross-link in `SOURCE_OF_TRUTH.md` is modified.
- On refresh, the prior `DB_CONTEXT.md` is fully replaced (no partial merge), and the drift summary in the required output makes the change auditable.
- `### Artifact changes` marks the patches as `APPLIED`.
- The basename in the `Run now:` line corresponds to a real file in `commands/<name>.md`.
- Output ends with a complete `### Handoff` block per the adaptive format in `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract`.
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
Optimize for fidelity to the live Supabase schema, point-in-time auditability, narrow scope (no full-DB dumps), credential hygiene (a service-role key never reaches a task artifact), and minimal disruption to whatever task-scoped work was in progress before this capture.
