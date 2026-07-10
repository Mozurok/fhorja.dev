# Migration Audit: 20260606120002_index_orders_by_user.sql

## 1. Per-Statement Verdict

| # | Statement | Verdict | Lock Level |
|---|-----------|---------|------------|
| 1 | CREATE INDEX idx_orders_user_id ON orders(user_id) | REJECT | SHARE on orders (blocks all writes) |

The SHARE lock held by non-concurrent CREATE INDEX blocks INSERT/UPDATE/DELETE on orders for the entire build duration. 120M rows = full write outage.

## 2. Risks by Severity

Critical -- Write outage for the index build duration.
Critical -- Lock queue head-of-line blocking.
Critical -- Single-shot with no maintenance window.
High -- No IF NOT EXISTS.
High -- Migration runner likely wraps in BEGIN/COMMIT; CONCURRENTLY cannot run inside a transaction.
Medium -- No lock_timeout / statement_timeout.

## 3. Remediation

```sql
SET lock_timeout = '3s';
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_orders_user_id ON public.orders(user_id);
```

Post-build validation:
```sql
SELECT indexrelid::regclass AS index, indisvalid, indisready
FROM pg_index WHERE indexrelid = 'public.idx_orders_user_id'::regclass;
```

If indisvalid = false, drop and rebuild:
```sql
DROP INDEX CONCURRENTLY IF EXISTS public.idx_orders_user_id;
```

## 4. Transaction Block Compatibility

No. CREATE INDEX CONCURRENTLY cannot run inside a transaction block; the migration runner must execute this file in autocommit mode, one statement at a time, with no enclosing BEGIN/COMMIT.
