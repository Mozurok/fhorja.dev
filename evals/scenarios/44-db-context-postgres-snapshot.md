# Eval scenario 44: db-context-postgres snapshot and no-op on re-run

- **Tags**: db-context-postgres, ADR-0010, centralized-external-access, DB_CONTEXT, snapshot, no-op-trace, postgres
- **Last reviewed**: 2026-06-05
- **Status**: active

## Goal

Validates that `commands/db-context-postgres.md` produces a deterministic structural snapshot of a live Postgres database (GCP Cloud SQL or local) into `DB_CONTEXT.md` using the `templates/DB_CONTEXT_POSTGRES.template.md` shape, and that a second run against the same database with no schema changes terminates as a NO_OP_TRACE rather than rewriting the file. This proves the snapshot is idempotent and that the command honors ADR-0010 centralized external access: the only network surface is the documented `DATABASE_URL`-bound read path, with no out-of-band probes.

This exercises:

- The introspection contract in `commands/db-context-postgres.md` (which schemas, tables, indexes, FKs, extensions, and server version to capture).
- The template shape in `templates/DB_CONTEXT_POSTGRES.template.md` (section order, required fields, normalization rules).
- ADR-0010 (centralized external access): only the configured DATABASE_URL is used; secrets are not echoed; no implicit fallback to alternate connections.
- The shared no-op contract: when the new snapshot is byte-identical (post-normalization) to the existing `DB_CONTEXT.md`, the command emits a NO_OP_TRACE and exits without a write.

## Setup

A bootstrapped project `projects/acme__billing/` with an active task folder. A reachable Postgres instance is exposed via `DATABASE_URL` (GCP Cloud SQL via proxy, or a local Postgres). The database contains at least two non-system schemas, several tables with primary keys, secondary indexes, at least one foreign key, and one extension (e.g. `pgcrypto` or `uuid-ossp`). No `DB_CONTEXT.md` exists yet under the active task folder for turn 1; it exists and is current for turn 2.

## Input prompt (turn 1: first snapshot)

```text
Run @commands/db-context-postgres.md

Project: acme__billing
Task: active/2026-06-05_billing-schema-map
DATABASE_URL: (resolved from env)
```

## Input prompt (turn 2: re-run with no schema changes)

```text
Run @commands/db-context-postgres.md

Project: acme__billing
Task: active/2026-06-05_billing-schema-map
DATABASE_URL: (resolved from env)
```

## Expected response shape (turn 1: first snapshot)

- Command connects via the resolved DATABASE_URL only, with no secondary connection strings probed.
- `DB_CONTEXT.md` is written under the active task folder, structured per `templates/DB_CONTEXT_POSTGRES.template.md`.
- The file includes: server version, enabled extensions, per-schema table list, per-table columns with types and nullability, primary keys, secondary indexes, and foreign keys with referenced table and column.
- Response lists the artifact as PROPOSED (write surface change) and cites ADR-0010 as the access-path justification. No raw DATABASE_URL or password is echoed in the response or the artifact.

## Expected response shape (turn 2: no-op re-run)

- Command reconnects, re-introspects, and computes the candidate snapshot.
- Candidate snapshot is compared against the existing `DB_CONTEXT.md` under the documented normalization rules (stable section order, deterministic sort of tables and indexes, ignored timestamp metadata).
- Response is a NO_OP_TRACE: no write, no PROPOSED entry, explicit statement that the snapshot is identical to the on-disk version.
- ADR-0010 is cited as the access path; the NO_OP_TRACE explicitly names the comparison basis (template-normalized diff).

## Pass criteria

1. **Turn 1 -- template shape honored**: `DB_CONTEXT.md` matches the section order and required fields of `templates/DB_CONTEXT_POSTGRES.template.md`; no sections are dropped, renamed, or reordered.
2. **Turn 1 -- complete inventory**: Output contains server version, extensions list, all non-system schemas, all tables per schema with columns and types, primary keys, secondary indexes, and foreign keys.
3. **Turn 1 -- ADR-0010 cited and respected**: The response names ADR-0010 and confirms the only external access was through the resolved DATABASE_URL; no DATABASE_URL value, password, or host secret is leaked into the artifact or response.
4. **Turn 1 -- deterministic ordering**: Schemas, tables, columns, indexes, and FKs are emitted in a stable, documented sort order so re-runs are diff-friendly.
5. **Turn 2 -- NO_OP_TRACE emitted**: When schema is unchanged, the command emits an explicit NO_OP_TRACE and does not write `DB_CONTEXT.md`; no PROPOSED entry appears.
6. **Turn 2 -- comparison basis named**: The NO_OP_TRACE states that the candidate snapshot was compared to the existing file under template-normalized form, not a raw byte compare of unsorted SQL output.
7. **Turn 2 -- access path unchanged**: Turn 2 still routes through the same centralized DATABASE_URL; no fallback connection, no off-template probe, no schema mutation.
8. **Both turns -- no secret leakage**: Neither turn echoes the DATABASE_URL value, password, host, or any credential string into the response, artifact, or trace logs.

## Failure modes to watch

- **Spurious rewrite on identical schema**: Turn 2 rewrites `DB_CONTEXT.md` instead of emitting NO_OP_TRACE, typically because the snapshot includes a timestamp or non-deterministic order that defeats the comparison.
- **Partial introspection**: Turn 1 omits foreign keys, indexes, or extensions, producing a snapshot that looks complete but is not faithful to the live database.
- **ADR-0010 bypass**: Command opens a second connection, reads from an alternate env var, or probes the host directly, violating centralized external access.
- **Credential leakage**: DATABASE_URL value or password is echoed into the artifact, the response, or a debug trace, leaving secrets in repo memory or chat history.

## Notes

- The normalization rules (stable sort keys, ignored fields) must be documented in `commands/db-context-postgres.md` so the no-op behavior is testable and auditable, not implicit.
- Local Postgres and GCP Cloud SQL must both satisfy the same contract; the only difference is the resolved DATABASE_URL.
- When the database schema does change between runs, the command is expected to write a new `DB_CONTEXT.md`; that path is covered by a separate scenario and is not in scope here.

## History

- 2026-06-05: Scenario created to cover initial snapshot plus no-op re-run for `db-context-postgres`.

## References

- `internal/commands/db-context-postgres.md` (command under test)
- `internal/templates/DB_CONTEXT_POSTGRES.template.md` (artifact shape)
- `internal/docs/adr/0010-centralized-external-access.md` (access-path invariant)
