---
name: migration-risk-lock-or-irreversible
category: migration
default-severity: P0
cwe: []
languages: [sql]
file-patterns: ["migrations/**", "supabase/migrations/**", "db/migrations/**", "alembic/**"]
perspectives: [operator]
reversibility-check: true
---

# migration-risk-lock-or-irreversible

## Trigger

A database migration contains an operation that either acquires a heavy lock on a large table (blocking reads/writes during the migration) or is irreversible (data loss on rollback). In production with live traffic, this can cause downtime or permanent data loss.

## Detection

Scan migration files for high-risk SQL patterns:

Lock-acquiring operations:
- `ALTER TABLE ... ALTER COLUMN ... TYPE` (full table rewrite on large tables)
- `ALTER TABLE ... ADD COLUMN ... NOT NULL` without a DEFAULT (requires scanning all rows)
- `CREATE INDEX` without `CONCURRENTLY` (blocks writes)
- `ALTER TABLE ... ADD CONSTRAINT` (scans existing rows)
- `LOCK TABLE` explicit

Irreversible operations:
- `DROP TABLE` or `DROP COLUMN`
- `DELETE FROM` without a backup or soft-delete pattern
- `TRUNCATE`
- Data type narrowing (`VARCHAR(255)` to `VARCHAR(50)`) that may truncate existing data
- `ALTER TYPE ... RENAME VALUE` on enums (cannot be undone without recreating the type)

## Retrieval

- The full migration file
- The table definition (to assess row count and whether the table is actively written to)
- Previous migrations on the same table (to detect patterns like "added in migration N, dropped in N+1")

## Analysis prompt

Given the migration:
1. Does it acquire a heavy lock? On which table? Estimated row count?
2. Is the operation reversible by a follow-up migration, or is data permanently lost?
3. Is there a safer alternative? (e.g., `CREATE INDEX CONCURRENTLY`, add column as nullable then backfill, soft-delete instead of DROP)
4. Does the migration need to be split into multiple steps with deploy ordering? (e.g., add nullable column, deploy code, backfill, add NOT NULL constraint)

## Severity rubric

- P0: DROP COLUMN or DROP TABLE on a production table with live data; no backup or soft-delete
- P0: ALTER COLUMN TYPE on a table with 1M+ rows without concurrent/online DDL
- P1: CREATE INDEX without CONCURRENTLY on a table with significant write traffic
- P1: ADD COLUMN NOT NULL without DEFAULT on a non-empty table
- P2: reversible schema change (ADD nullable COLUMN, CREATE TABLE) with no lock risk

## Confidence factors

- HIGH: migration contains DROP COLUMN/TABLE or ALTER TYPE on a table known to have data
- MEDIUM: migration contains CREATE INDEX without CONCURRENTLY; table size unknown
- LOW: migration is additive only (ADD nullable COLUMN, CREATE TABLE); no risk

## Examples

### Positive (high risk)

```sql
ALTER TABLE public.verification_runs
DROP COLUMN IF EXISTS public_access_token_hash;
-- Irreversible: column data is permanently lost; no soft-delete
```

### Negative (safe)

```sql
ALTER TABLE public.verification_run_claims
ADD COLUMN share_type text NOT NULL DEFAULT 'driver_claim';
-- Additive, has DEFAULT, no lock on existing rows (Postgres 11+)
```
