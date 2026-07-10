# Migration Audit: `idx_orders_status`

## Migration under review

```sql
CREATE INDEX idx_orders_status ON orders(status);
```

This is a **blocking** `CREATE INDEX` (no `CONCURRENTLY`). On any non-trivial `orders` table, this will take an `ACCESS EXCLUSIVE`-incompatible share lock (`SHARE` lock) that blocks `INSERT`, `UPDATE`, `DELETE`, and `MERGE` against `orders` for the full duration of the build. Reads via `SELECT` continue, but any writer on `orders` (checkout, refund, webhook, status transition) will queue behind it.

For an `orders` table -- which in almost every commerce/SaaS system is a hot write path -- this is operationally risky by default.

---

## (1) Bias verdict

**NEEDS-PHASING.**

Rationale:
- Required inputs for a definitive verdict (PG version, row count, deployment strategy, online-DDL tooling) are missing.
- Per the audit rule "unknown row count = treat as >1M", we must assume this index build will run long enough to cause user-visible write stalls on `orders`.
- A blocking `CREATE INDEX` on a presumed >1M-row hot table is not safe to ship as-is. It needs to be phased into: (a) confirm context, (b) rewrite as `CREATE INDEX CONCURRENTLY` in its own migration/transaction, (c) plan rollout + monitoring.

Verdict is **not** APPROVE and **not** REJECT -- it is **NEEDS-PHASING** pending the missing inputs and a rewrite.

---

## (2) Missing context blocking a definitive audit

These items must be filled in before the audit can move from NEEDS-PHASING to APPROVE/REJECT:

1. **Postgres version**
   - `CREATE INDEX CONCURRENTLY` semantics, `REINDEX CONCURRENTLY`, partitioned-index handling, and `ON ONLY` behavior differ across PG 11 / 12 / 13+ / 14+ / 15+ / 16+.
   - Need to know if `orders` is on a managed PG (RDS/Aurora/Cloud SQL/Supabase) and which major version.

2. **Row count and table size**
   - Actual `n_live_tup` from `pg_stat_user_tables` and `pg_total_relation_size('orders')`.
   - Without this, we default to ">1M rows" and treat the build as long-running.

3. **Write rate / hot-path status**
   - Writes per second on `orders` (inserts + status updates).
   - Whether `status` is updated frequently (affects HOT updates and index maintenance cost post-creation).

4. **Cardinality and distribution of `status`**
   - How many distinct values, and skew (e.g., 90% `completed`).
   - Determines whether a plain B-tree on `status` is even the right index, vs. a **partial index** (e.g., `WHERE status IN ('pending','processing')`) which is typically what production systems actually want for an orders status column.

5. **Query patterns that justify the index**
   - The migration gives no evidence of the query this index serves. Need the actual `EXPLAIN` / slow query / access pattern.
   - Without this, we cannot confirm the index is needed at all, nor whether it should be composite (e.g., `(status, created_at)` or `(user_id, status)`).

6. **Partitioning**
   - Is `orders` partitioned? If yes, the migration is wrong -- you need `CREATE INDEX ... ON ONLY` + per-partition `CONCURRENTLY` builds + `ATTACH PARTITION`, not a single `CREATE INDEX`.

7. **Deployment strategy and tooling**
   - Migration runner (Prisma, Drizzle, Supabase CLI, Flyway, Liquibase, Sqitch, raw `psql`).
   - Whether the runner wraps each migration in a transaction -- critical, because `CREATE INDEX CONCURRENTLY` **cannot run inside a transaction block**. Several runners (notably Prisma's default behavior, Drizzle's default) will break this.
   - Whether there's a maintenance window, blue/green, or zero-downtime requirement.

8. **Lock-timeout / statement-timeout posture**
   - Current `lock_timeout` and `statement_timeout` defaults in the target environment.
   - Without a `lock_timeout`, a blocking `CREATE INDEX` that queues behind a long transaction can in turn block every writer behind it (lock-queue pileup) -- a well-known outage pattern.

9. **Replication topology**
   - Physical replicas / read replicas / logical replication subscribers.
   - Index build replays on replicas and can stall replication or cause replica lag.

10. **Rollback plan**
    - Is there a `DROP INDEX CONCURRENTLY idx_orders_status;` down-migration? The provided file has no down step.

---

## (3) Recommended next command

**`targeted-questions`.**

Reasoning:
- The blockers above are **factual**, not decision-driven. We need values (PG version, row count, runner behavior, partitioning, query pattern) before we can write a safe plan or even decide between APPROVE and REJECT.
- `decision-interview` is the wrong tool here -- there are no policy/behavior trade-offs to lock in yet. We don't have enough facts to even frame the decisions (e.g., partial vs full index, composite vs single-column) meaningfully.
- `implementation-plan` is premature -- planning a phased rollout on unknown PG version, unknown row count, unknown runner, and unknown partitioning status would be speculative and is exactly the failure mode the "STOP and Handoff" rule exists to prevent.

### Concrete questions to send into `targeted-questions`

1. What is the exact Postgres major version and host (RDS/Aurora/Cloud SQL/Supabase/self-managed)?
2. What is `n_live_tup` for `orders` and `pg_total_relation_size('orders')`?
3. What is the approximate write rate on `orders` (inserts/sec, status updates/sec)?
4. Is `orders` partitioned? If yes, by what key?
5. Which migration tool runs this file, and does it wrap each migration in a transaction by default?
6. What query/queries is `idx_orders_status` meant to accelerate? Can you share the `EXPLAIN`?
7. What is the cardinality and distribution of `status`?
8. Are there read replicas or logical replication subscribers downstream?
9. Is there a maintenance window available, or does this need to be fully online?
10. What are the environment's current `lock_timeout` and `statement_timeout` values?

Once those are answered, the audit can move to either:
- **APPROVE** (only if rows are tiny, no writers, dev/staging, etc. -- unlikely for `orders`), or
- **REJECT-and-rewrite** to:
  ```sql
  -- run outside any transaction block
  CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_orders_status
    ON orders (status);
  -- consider: partial index, composite index, or status-specific filter
  ```
  with a matching `DROP INDEX CONCURRENTLY IF EXISTS idx_orders_status;` down-migration, an explicit `lock_timeout`, and a phased rollout/monitoring plan.

---

## Summary

- **Verdict:** NEEDS-PHASING.
- **Why:** Required audit inputs are missing; default assumption (>1M rows, hot write path) makes a blocking `CREATE INDEX` unsafe.
- **Next command:** `targeted-questions` to collect the 10 factual inputs above before any plan or rewrite is proposed.
