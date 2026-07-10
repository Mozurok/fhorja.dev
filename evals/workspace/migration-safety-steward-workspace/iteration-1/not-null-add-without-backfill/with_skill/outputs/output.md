# MIGRATION_SAFETY.md (with persona)

Audit run_id: msa-2026-06-05-001
Postgres version: 14
Deployment strategy: Rolling deploy, no maintenance window

## Per-statement verdict table

| stmt_id | file:line | statement | classification | lock_level | est_rows | verdict | rollback | remediation |
|---|---|---|---|---|---|---|---|---|
| S1 | 20260606120001:1 | ALTER TABLE users ADD COLUMN signup_source text NOT NULL DEFAULT 'unknown' | ADD-COLUMN-NOT-NULL | AccessExclusiveLock (NOT NULL validation triggers full scan on PG14) | 1M-100M (~50M) | NEEDS-PHASING | ALTER TABLE users DROP COLUMN signup_source | Split into 4 phases below |

## Risks grouped by severity

### P1
- R1 AccessExclusiveLock on users for NOT NULL validation; 3-10 minute window blocks all SELECT/INSERT/UPDATE/DELETE. PagerDuty within 2 minutes.
- R2 Rolling deploy ordering. Subtle data quality if migration runs after new pods are live.

### P2
- R3 'unknown' default permanently baked into 50M rows. Route to decision-interview for product review before Phase 2.

## Recommended phasing

### Phase 1 add nullable column
```sql
ALTER TABLE users ADD COLUMN signup_source text DEFAULT 'unknown';
```

### Phase 1 code change
Deploy app code that writes signup_source on all INSERTs.

### Phase 2 backfill in batches
```sql
UPDATE users SET signup_source = 'unknown'
WHERE signup_source IS NULL
  AND id IN (SELECT id FROM users WHERE signup_source IS NULL ORDER BY id LIMIT 10000);
```

### Phase 3 NOT NULL without full-table validation
```sql
ALTER TABLE users ADD CONSTRAINT users_signup_source_not_null CHECK (signup_source IS NOT NULL) NOT VALID;
ALTER TABLE users VALIDATE CONSTRAINT users_signup_source_not_null;
```

### Phase 4 promote CHECK to NOT NULL
```sql
ALTER TABLE users ALTER COLUMN signup_source SET NOT NULL;
ALTER TABLE users DROP CONSTRAINT users_signup_source_not_null;
```

## Rollback plan per statement

| stmt | rollback SQL | safety |
|---|---|---|
| Phase 1 | ALTER TABLE users DROP COLUMN signup_source | Safe until app reads start |
| Phase 2 backfill | idempotent re-run | Safe |
| Phase 3a/3b | ALTER TABLE users DROP CONSTRAINT users_signup_source_not_null | Safe |
| Phase 4 | ALTER TABLE users ALTER COLUMN signup_source DROP NOT NULL | Safe |

Verdict distribution: 0 SAFE / 1 NEEDS-PHASING / 0 UNSAFE.
