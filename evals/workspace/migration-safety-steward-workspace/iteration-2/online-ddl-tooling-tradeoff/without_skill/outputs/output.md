# Migration Audit: `20260606140006_index_orders_by_user.sql`

## 1. Per-Statement Verdict

### Statement: `CREATE INDEX idx_orders_user_id ON orders(user_id);`

**Verdict: BLOCK / DO NOT MERGE AS WRITTEN.**

A plain `CREATE INDEX` takes an `ACCESS EXCLUSIVE`-equivalent for the index build window -- concretely it takes a `SHARE` lock on `orders` that blocks all `INSERT`, `UPDATE`, `DELETE` (and any DDL) for the entire duration of the build. On a ~200M-row table with ~15k writes/min sustained and 3x peaks at hour boundaries, this is unambiguously unsafe under a rolling deploy with no maintenance window:

- Estimated build wall-clock: tens of minutes to a few hours depending on disk / `maintenance_work_mem` / row width. Even at the optimistic end, the writer-blocking window is far longer than any acceptable rolling-deploy stall.
- During the build, the write queue (5k inserts/min + 10k updates/min) will back up against the `SHARE` lock. Connection pools (PgBouncer / app-side) will saturate, then the app surfaces as a full outage even though Postgres is "up".
- At hour boundaries (3x peak) the queue grows ~45k writes/min while blocked -- connection exhaustion is essentially guaranteed.

Additional issues independent of the locking problem:

- **Missing `IF NOT EXISTS`**: if the migration is retried (and it will be retried on a 200M-row table), the second run fails with `relation "idx_orders_user_id" already exists` rather than no-op'ing. For an online index build that may have *partially* succeeded, retry safety matters.
- **No explicit `lock_timeout` / `statement_timeout`**: under the `CONCURRENTLY` variant (see §3), absence of a `lock_timeout` means the build can wedge waiting for the brief `ShareUpdateExclusive` lock and block writers behind it indefinitely.
- **No tablespace / fillfactor consideration**: not blocking, but worth noting -- on a write-hot table, a fresh btree at default fillfactor (90) will quickly bloat under the update load. Not changing this now, but flag for the index-maintenance runbook.

---

## 2. Explicit Comparison: `CREATE INDEX CONCURRENTLY` vs `pg_repack --only-indexes` for THIS Table Profile

The standard reflexive answer here is "use `CONCURRENTLY`". On this specific table that answer is wrong, and the context block already documents why. Comparing the two variants on the dimensions that matter for this workload:

| Dimension | `CREATE INDEX CONCURRENTLY` | `pg_repack -i` (index-only mode) |
|---|---|---|
| **Writer-blocking window** | Brief `ShareUpdateExclusiveLock` at start and end; allows DML during the long middle phase. | Brief `AccessShareLock` + short `AccessExclusiveLock` at the swap step. Build itself happens on a shadow index without holding heavy locks. |
| **Sensitivity to long-running transactions** | **High.** Phase 2 (validation) waits for *all* transactions that were active when the build started to finish. With ~30-minute OLAP queries on this table during business hours, the build either stalls for ~30 min or -- more commonly -- gets cancelled / leaves an `INVALID` index. **This is exactly the failure mode that bit this table twice in 6 months.** | **Low.** `pg_repack` uses triggers to capture concurrent DML into a log table and replays it onto the shadow index, then does a short catch-up + swap. It does not need to wait for pre-existing snapshots to drain in the same blocking way. |
| **Failure mode** | Leaves an `INVALID` index that still consumes write amplification cost (planner won't use it, but every DML still updates it) until manually dropped and retried. Operator must `DROP INDEX CONCURRENTLY` and start over -- and the retry hits the same long-OLAP-transaction problem. | Failure cleans up the shadow object and triggers; original state is preserved. Safe to re-run. |
| **Total wall-clock** | One pass. Faster *if* it succeeds. | Slightly slower (shadow build + log replay) but bounded and predictable. |
| **Disk overhead** | 1x final index size during build. | ~1x final index size for the shadow + a log table that grows with concurrent write volume during the build. On 15k writes/min × (say) 60 min build = ~900k log rows -- easily handled, but plan disk headroom. |
| **Replication impact** | Logical: index build is replicated. Physical (streaming): replicated. | Same -- `pg_repack` operations are WAL-logged and replicate normally. |
| **Operability under rolling deploy** | Risky: if the migration step blocks, the deploy step blocks, and rollback is awkward because the partial index is real. | Safer: can be invoked from a maintenance host outside the deploy pipeline; deploy step becomes a no-op verification. |
| **Postgres 14 support** | Native. | `pg_repack` supports PG 14 fully; extension already installed per context. |

**Conclusion of the comparison:** for *this* table -- high sustained writes, hour-boundary 3x peaks, recurring ~30-minute OLAP transactions, and a documented history of `CONCURRENTLY` failing twice in 6 months on the same workload -- `pg_repack -i` is the safer variant. `CONCURRENTLY` would be the right default on a table without the long-OLAP-transaction problem; it is the wrong default here.

---

## 3. Recommended Variant + Concrete Invocation

**Recommendation: build the index using `pg_repack --only-indexes` from a maintenance host, then have the migration *register* the index as a no-op (`CREATE INDEX IF NOT EXISTS ... CONCURRENTLY`) so the migration history is consistent across environments.**

This split keeps the deployment pipeline honest (the migration file still names the index that production must have) while avoiding the failure mode that bit this table twice.

### Step A -- Pre-flight (before running anything)

```sql
-- Run on the primary, as a superuser or table owner.
-- 1. Confirm no existing index already covers (user_id) as a leftmost column.
SELECT indexname, indexdef
FROM   pg_indexes
WHERE  tablename = 'orders'
  AND  indexdef ILIKE '%(user_id%';

-- 2. Confirm pg_repack extension is installed in the target DB.
SELECT extname, extversion FROM pg_extension WHERE extname = 'pg_repack';

-- 3. Check current bloat / long-running transactions before kicking off.
SELECT pid, now() - xact_start AS xact_age, state, query
FROM   pg_stat_activity
WHERE  xact_start IS NOT NULL
  AND  now() - xact_start > interval '5 minutes'
ORDER  BY xact_age DESC;

-- 4. Disk headroom check: need at least 1x final index size plus log overhead.
SELECT pg_size_pretty(pg_relation_size('orders')) AS heap_size;
```

If step 3 shows OLAP transactions older than ~5 minutes, *wait for a quieter window* -- `pg_repack` tolerates concurrent writes far better than `CONCURRENTLY` does, but starting cleanly is still cheaper than recovering.

### Step B -- Build the index out-of-band with `pg_repack`

Because `pg_repack -i` operates on existing indexes, the typical pattern is:

1. Create a stub `INVALID` index definition that names the target, then have `pg_repack` rebuild it; or
2. Create the index with `CONCURRENTLY` *with a tight `lock_timeout` and a watchdog*, falling back to `pg_repack` on failure.

For this workload -- given the documented `CONCURRENTLY` failures -- the cleanest approach is to create an empty placeholder via a parallel-safe pattern and let `pg_repack` do the heavy lift, or to use `pg_repack`'s newer support directly. Concretely, from a maintenance host with `psql` access to the primary:

```bash
# Run from a maintenance host, NOT from the deploy pipeline.
# Detached / tmux'd so a disconnect does not kill the build.

# Tunables -- set BEFORE invoking pg_repack on a giant table.
export PGAPPNAME="pg_repack-idx-orders-user_id"

pg_repack \
  --host=primary.db.internal \
  --port=5432 \
  --username=repack_admin \
  --dbname=app_prod \
  --table=public.orders \
  --only-indexes \
  --index=idx_orders_user_id \
  --wait-timeout=60 \
  --jobs=2 \
  --no-superuser-check \
  --echo
```

Notes on the flags:

- `--only-indexes` + `--index=...` scopes the operation to building / rebuilding a single named index, *not* the whole heap. The heap on a 200M-row write-hot table is not what we want to rewrite right now.
- `--wait-timeout=60` bounds how long `pg_repack` waits for conflicting locks before giving up cleanly. With ~30-min OLAP transactions this matters: 60s is enough for normal contention, short enough that we fail fast and retry rather than block the writer queue.
- `--jobs=2` parallelizes the build modestly. Do **not** crank this up on a write-hot primary -- you will starve the write path of I/O.
- `--echo` so the operator sees the exact SQL being issued; useful for the incident channel.
- Because `pg_repack --index` requires the target index to already exist, the prerequisite SQL is:

```sql
-- One-shot, in its own session, with bounded lock wait.
SET lock_timeout = '2s';
SET statement_timeout = 0;
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_orders_user_id
  ON public.orders (user_id);
```

If that `CONCURRENTLY` build fails (which the context says is likely), the resulting `INVALID` index is exactly what `pg_repack -i --index=idx_orders_user_id` is designed to rebuild -- it will produce a valid replacement without re-entering the snapshot-wait failure mode.

Verify post-build:

```sql
SELECT indexname,
       indexdef,
       pg_size_pretty(pg_relation_size(indexname::regclass)) AS size,
       (SELECT indisvalid FROM pg_index WHERE indexrelid = indexname::regclass) AS is_valid
FROM   pg_indexes
WHERE  tablename = 'orders'
  AND  indexname = 'idx_orders_user_id';

-- Confirm planner picks it up for the canonical query.
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM orders WHERE user_id = $1 LIMIT 50;
```

### Step C -- Reconcile migration history

The migration file in source control should match what production has. Replace the original one-liner with this idempotent form so reruns and fresh environments converge to the same state:

```sql
-- migrations/20260606140006_index_orders_by_user.sql
--
-- NOTE: On the production primary this index was built out-of-band via
-- pg_repack --only-indexes on 2026-06-06 because CREATE INDEX CONCURRENTLY
-- on orders has failed twice in the last 6 months due to long-running
-- OLAP transactions holding open snapshots. See runbook RB-ORDERS-IDX.
-- This migration is idempotent and safe to re-run in any environment.

SET lock_timeout = '2s';
SET statement_timeout = 0;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_orders_user_id
  ON public.orders (user_id);
```

`CONCURRENTLY` + `IF NOT EXISTS` makes the production run a no-op (the index already exists) while smaller environments (dev / staging / fresh ephemeral DBs) can build it inline with `CONCURRENTLY` safely, since they do not have the long-OLAP-transaction problem.

---

## 4. Rollback

Rollback for an index addition is straightforward, but on a write-hot 200M-row table the rollback step itself must be online:

### Forward rollback (preferred): drop the index online

```sql
-- Do NOT use plain DROP INDEX -- it takes ACCESS EXCLUSIVE on orders
-- and will block writers for the duration of catalog cleanup.

SET lock_timeout = '2s';
DROP INDEX CONCURRENTLY IF EXISTS public.idx_orders_user_id;
```

`DROP INDEX CONCURRENTLY` exists for exactly this case in PG 14 and only takes a `ShareUpdateExclusive` lock. Bounded `lock_timeout` so the rollback cannot wedge behind the same long-OLAP transactions.

### If `pg_repack` was mid-build when we decided to roll back

`pg_repack` cleans up after itself on Ctrl-C, but if the process was killed uncleanly you may have leftover shadow objects and triggers in the `repack` schema:

```sql
-- Inspect.
SELECT n.nspname, c.relname
FROM   pg_class c
JOIN   pg_namespace n ON n.oid = c.relnamespace
WHERE  n.nspname = 'repack'
  AND  c.relname LIKE '%orders%';

-- pg_repack ships a cleanup helper; use it rather than dropping objects
-- by hand, because the trigger graph on orders must come off too.
```

```bash
pg_repack \
  --host=primary.db.internal \
  --dbname=app_prod \
  --table=public.orders \
  --error-on-invalid-index=false \
  --no-kill-backend \
  --dry-run    # inspect first
# then re-run without --dry-run if the plan looks right
```

### Application-side rollback

Independent of the DB rollback: any query plan that started using `idx_orders_user_id` will revert to its prior plan on `DROP INDEX CONCURRENTLY`. Confirm with `EXPLAIN` on the canonical `WHERE user_id = $1` query before declaring rollback complete, and watch p95 latency on the orders read path for ~15 minutes after -- that is where regression will surface if the prior plan was index-only on something correlated.

---

## Summary

- The migration as written is **unsafe** on a 200M-row, write-hot table under rolling deploy -- plain `CREATE INDEX` takes a writer-blocking lock for the entire build.
- The reflexive fix (`CONCURRENTLY`) is **also wrong for this specific table**, because the documented failure mode is exactly the one `CONCURRENTLY` is vulnerable to: long-running OLAP transactions prevent the validation phase from completing, leaving `INVALID` indexes (already happened twice in 6 months).
- The correct variant here is `pg_repack --only-indexes --index=idx_orders_user_id`, run out-of-band from a maintenance host with `--wait-timeout=60`, with the migration file rewritten as an idempotent `CREATE INDEX CONCURRENTLY IF NOT EXISTS` so production is a no-op and other environments stay consistent.
- Rollback is `DROP INDEX CONCURRENTLY IF EXISTS` with a bounded `lock_timeout`, plus the standard `pg_repack` cleanup path if a build was interrupted.