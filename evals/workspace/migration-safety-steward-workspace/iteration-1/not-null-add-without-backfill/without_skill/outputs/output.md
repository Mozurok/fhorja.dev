# Postgres Migration Audit -- 20260606120001_add_signup_source.sql

## 1. Per-Statement Verdict Table

| statement_id | classification | lock_level | est_row_count_bucket | verdict | rollback | remediation |
|---|---|---|---|---|---|---|
| S1: ALTER TABLE users ADD COLUMN signup_source text NOT NULL DEFAULT 'unknown' | DDL column add with NOT NULL + non-volatile DEFAULT | ACCESS EXCLUSIVE on users | XL (50M) | NEEDS-PHASING | ALTER TABLE users DROP COLUMN signup_source | Split into add-nullable / backfill / enforce NOT NULL |

## 2. Risks by Severity

CRITICAL -- Lock-queue stampede on users.
HIGH -- App/DB version skew during rolling deploy. Old pods omit signup_source.
HIGH -- Effectively irreversible once writes depend on the column.
MEDIUM -- 'unknown' default pollutes analytics; no CHECK; no length cap.
LOW -- No statement_timeout / lock_timeout set in the migration.

## 3. Recommended Phasing

### Phase 1: add nullable
```sql
SET lock_timeout = '2s';
ALTER TABLE users ADD COLUMN signup_source text NULL;
```
Deploy app code that writes signup_source on all new INSERTs.

### Phase 2: backfill in batches
```sql
UPDATE users SET signup_source = 'unknown'
WHERE id IN (SELECT id FROM users WHERE signup_source IS NULL LIMIT 10000);
```
Loop until 0 rows. Sleep between batches.

### Phase 3: enforce NOT NULL via NOT VALID CHECK then VALIDATE
```sql
ALTER TABLE users ADD CONSTRAINT users_signup_source_not_null CHECK (signup_source IS NOT NULL) NOT VALID;
ALTER TABLE users VALIDATE CONSTRAINT users_signup_source_not_null;
ALTER TABLE users ALTER COLUMN signup_source SET NOT NULL;
ALTER TABLE users DROP CONSTRAINT users_signup_source_not_null;
```

## 4. Rollback Plan

| Phase | Rollback |
|---|---|
| Phase 1 | ALTER TABLE users DROP COLUMN signup_source |
| Phase 2 | None (idempotent) |
| Phase 3 | ALTER TABLE users ALTER COLUMN signup_source DROP NOT NULL |
