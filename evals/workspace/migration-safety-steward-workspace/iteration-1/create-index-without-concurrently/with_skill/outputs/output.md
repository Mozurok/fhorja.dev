# MIGRATION_SAFETY.md (with persona)

Audit run_id: msa-2026-06-05-001
Postgres version: 14
Row count: orders ~120M (bucket >100M); high write concurrency

## Per-statement verdict table

| # | statement | classification | lock_level | est_row_count_bucket | verdict | rollback | remediation |
|---|-----------|----------------|------------|----------------------|---------|----------|-------------|
| S1 | CREATE INDEX idx_orders_user_id ON orders(user_id) | CREATE-INDEX | ShareLock on orders | >100M | UNSAFE | DROP INDEX CONCURRENTLY idx_orders_user_id | R1 (Phase A + Phase B) below |

## Risks grouped by severity

### P0 -- UNSAFE will cause incident
R-P0-1 CREATE INDEX without CONCURRENTLY on 120M-row write-heavy table. ShareLock incompatible with RowExclusiveLock (INSERT/UPDATE/DELETE). Build 20-60+ minutes; full write blocking; connection pool saturates; user-visible 5xx; PagerDuty within 2 minutes.

### P2
R-P2-1 Post-remediation: monitor for invalid index state (CONCURRENTLY can leave indisvalid = false on failure).

## Recommended phasing

### Phase A build the index concurrently (own migration file, no transaction)
```sql
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_orders_user_id ON orders(user_id);
```
Runner MUST be configured non-transactional for this file (sqitch --no-transaction, Flyway transactional=false, Supabase -- transaction: false).

### Phase B verify index validity
```sql
SELECT c.relname, i.indisvalid, i.indisready
FROM pg_index i JOIN pg_class c ON c.oid = i.indexrelid
WHERE c.relname = 'idx_orders_user_id';
```
If indisvalid = false: DROP INDEX CONCURRENTLY idx_orders_user_id; then re-run Phase A.

### Can remediation run inside a transaction block?
No. CREATE INDEX CONCURRENTLY is explicitly disallowed inside a transaction block by Postgres (ERROR: CREATE INDEX CONCURRENTLY cannot run inside a transaction block).

## Rollback plan per statement

| # | rollback statement | safety | reversible |
|---|---------------------|--------|-------------|
| S1 | DROP INDEX CONCURRENTLY IF EXISTS idx_orders_user_id | ShareUpdateExclusiveLock only; cannot run inside transaction | Yes |

## Irreversible operations requiring user confirmation
None.

Verdict: 1 UNSAFE / cannot ship as written.
