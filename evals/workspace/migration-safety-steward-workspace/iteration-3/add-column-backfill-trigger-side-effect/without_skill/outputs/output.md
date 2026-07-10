# Audit: `add_user_signup_source` migration + backfill

## 1. Per-statement verdict

### Statement A -- `ALTER TABLE users ADD COLUMN signup_source text DEFAULT NULL;`

**Verdict: SAFE (with caveats).**

- In Postgres 11+, adding a nullable column with `DEFAULT NULL` (or no default at all) is a metadata-only change. It does **not** rewrite the table and holds `ACCESS EXCLUSIVE` only for the brief catalog update.
- Risk is mostly lock contention: `ACCESS EXCLUSIVE` will queue behind any long-running transaction/`SELECT` and will then block all readers/writers until it acquires. On a 50M-row hot table, recommend running with `lock_timeout` set (e.g. `SET lock_timeout = '2s'`) and retrying, to avoid wedging the queue behind a long-running query.
- `DEFAULT NULL` is redundant (NULL is already the implicit default), but harmless.

### Statement B -- The batched `UPDATE … WHERE id IN (SELECT … LIMIT 10000)`

**Verdict: UNSAFE as written.** The batching shape is fine on its own, but it ignores the AFTER UPDATE trigger. See §2.

Mechanical issues with the batch query itself, independent of the trigger:
- `ORDER BY id … LIMIT 10000` inside the subquery without keyset pagination means each batch re-scans/seeks from the start of the "NULL" set. With a partial index on `WHERE signup_source IS NULL` it stays cheap; without one, cost grows. Recommend keyset pagination (`WHERE id > :last_id AND signup_source IS NULL ORDER BY id LIMIT 10000 RETURNING id`) and capture the max id per batch.
- No `COMMIT` shown between batches -- each batch must be its own transaction, otherwise XID/locks/bloat pile up.
- No inter-batch sleep / pacing.
- No autovacuum consideration: 50M row updates produce 50M dead tuples → table bloat + index bloat. Plan for a `VACUUM (ANALYZE) users` after, and consider lowering `autovacuum_vacuum_scale_factor` on this table during the backfill.

## 2. The hidden cost -- trigger fires + Kafka pressure

This is the load-bearing finding. The plan as written **will breach the Kafka consumer SLO and likely cause a production incident.**

The trigger is `AFTER UPDATE FOR EACH ROW`. Every row touched by the backfill emits one event:

- Rows to update: **~50,000,000**
- Trigger fires: **50,000,000 extra Kafka publishes** (one per row).
- Trigger cost: ~80 ms per event of *bridge* work. That cost is largely outside the UPDATE's critical path (it's the bridge → Kafka hop), but the row-level trigger function itself still executes inside the UPDATE transaction. Even if the publish is async, the per-row overhead (function call + queueing) is non-trivial at 50M rows.
- Steady-state Kafka write rate: ~3,500 events/sec. Consumer sized for ~5,000/sec peak. Headroom: ~1,500/sec.
- Backfill adds "~10× normal write rate" → on the order of **~35,000 events/sec** of additional emission while batches run.
- Result: producer rate ≈ 38,500/sec vs consumer ceiling 5,000/sec. **Consumer lag will grow by ~33,500 events/sec**, i.e. ~2M events/minute of backlog. The 60-second processing SLO will be violated within the first second of the first batch and will stay violated for hours after the backfill stops while the consumer drains.
- Secondary effects: Kafka topic disk pressure, downstream consumers (analytics, notifications, anything subscribed to `user_changed`) getting flooded with spurious "signup_source changed from NULL to 'organic'" events that don't represent a real user-facing change.

**The trigger turns a 50M-row metadata backfill into a 50M-event domain-event storm.** The slice author treated the column backfill as an isolated DDL+DML change; in reality it is also a **producer-side load test of the Kafka pipeline**, and the pipeline is not sized for it.

## 3. Recommended backfill strategy

Pick **one** of the following. Listed in order of preference for this situation.

### Option A (preferred) -- Suppress the trigger for the backfill path, using `session_replication_role`

The cleanest "don't fire side-effects for a backfill" pattern when you don't want to drop/recreate the trigger globally.

Per backfill worker session:

```sql
BEGIN;
SET LOCAL session_replication_role = 'replica';   -- skips non-REPLICA triggers in this txn only
UPDATE users
   SET signup_source = 'organic'
 WHERE id > :last_id
   AND signup_source IS NULL
 ORDER BY id
 LIMIT 10000
RETURNING id;
COMMIT;
```

Why this is good:
- `SET LOCAL` scopes the suppression to that transaction only -- no global window where *real* writes lose their event.
- The base trigger remains `ENABLED` (its default firing mode is `ORIGIN`), so application traffic on other connections continues to publish events normally during the backfill.
- Requires the backfill role to have permission to set `session_replication_role` (superuser or sufficiently privileged role; on managed Postgres like RDS this is typically allowed for the `rds_superuser`-equivalent).

Then, after the backfill completes, emit **one** synthetic "bulk signup_source backfilled" event to the topic out-of-band (or document for downstream consumers that this column was populated by migration, no per-row event), so downstream systems know the state changed.

### Option B -- `ALTER TABLE users DISABLE TRIGGER publish_user_changed_event` for the duration of the backfill

Workable but **strictly worse than A**:
- It is global -- every connection's writes during the window also skip the event. Real user signups during the backfill window will silently fail to publish. For a multi-hour backfill this is unacceptable unless you also pause writes (you can't).
- Requires `ACCESS EXCLUSIVE` on the table to toggle, which contends with traffic.

Only viable if you can gate the backfill into a true maintenance window with writes paused. Given "rolling deploy + oncall script," that's not the case here.

### Option C -- Skip the per-row backfill entirely; treat NULL as "organic" at the read layer

If the semantic of `signup_source IS NULL` can be interpreted as `'organic'` by the application (and any reporting), then **don't backfill at all**. New rows get the correct value going forward (set the default on the column to `'organic'` and have the app write it explicitly), and old rows stay NULL with NULL meaning organic.

This is the cheapest, safest, zero-trigger-fire path. It is the right answer if and only if the downstream consumers of this column tolerate NULL.

### Option D -- Pace the backfill to stay under the Kafka consumer SLO

If for product/reporting reasons every row truly must be physically updated *and* every update truly must emit an event (rare, but possible), then pace:

- Consumer headroom is ~1,500 events/sec.
- Target ~1,000 events/sec from the backfill to leave margin.
- Batch size 10,000, sleep ~10 seconds between batches → ~1,000 rows/sec sustained.
- Wall-clock: 50M / 1,000 = **~50,000 seconds ≈ 14 hours**.
- Add monitoring: pause the backfill loop if consumer lag exceeds a threshold (e.g. lag > 30s).

This is the "honest" version of the original plan but it's slow and operationally fragile. Only choose this if A and C are both off the table.

### Recommended choice for this slice

**Option A**, with **Option C considered first** if the product team agrees NULL can mean organic. Avoid B. Use D only as a fallback.

### Other hardening regardless of option chosen

- Run the `ALTER TABLE` with `SET lock_timeout = '2s'` and retry on lock failure.
- Use keyset pagination (`WHERE id > :last_id`) instead of `LIMIT` over a re-scanned NULL set.
- One transaction per batch, with a small `pg_sleep` (200–500 ms) between batches even in A, to give autovacuum and replication room.
- After backfill: `VACUUM (ANALYZE) users;` and verify no remaining NULLs (`SELECT count(*) FROM users WHERE signup_source IS NULL;`) before the slice is considered closed.
- Pre-create a partial index `CREATE INDEX CONCURRENTLY ... ON users (id) WHERE signup_source IS NULL;` to keep the per-batch `WHERE … IS NULL` lookups cheap and drop it after backfill.
- Confirm replicas/replication: `session_replication_role = 'replica'` on the primary does **not** affect what physical replicas replay; logical replication is a separate consideration if any logical slot exists on this table.

## 4. Rollback

### Rolling back the column add

```sql
ALTER TABLE users DROP COLUMN signup_source;
```

- Takes `ACCESS EXCLUSIVE` briefly. Same lock-timeout precaution as the add.
- Safe at any time; no data dependency assumed yet by readers (slice 1 of a new column).
- Application code reading `signup_source` must be reverted/feature-flagged off **before** the drop.

### Rolling back the backfill

- If Option A or C was used: nothing to roll back data-wise (A produced no events; C wrote nothing). Just stop the script.
- If Option B was used and the trigger was globally disabled: re-enable immediately with `ALTER TABLE users ENABLE TRIGGER publish_user_changed_event;` and assume **all events emitted during the window are lost** -- surface this to downstream consumers and replay from the source-of-truth if any consumer depends on completeness.
- If Option D ran partially: the partial backfill is forward-compatible -- re-running the same batched UPDATE is idempotent (`WHERE signup_source IS NULL` guard). No special rollback needed unless product wants NULLs back, in which case `UPDATE users SET signup_source = NULL WHERE signup_source = 'organic';` -- but that re-fires the trigger another 50M times, so don't.

### Rollback of trigger state

- Verify the trigger is in its original state after the slice: `SELECT tgname, tgenabled FROM pg_trigger WHERE tgrelid = 'users'::regclass;` should show `tgenabled = 'O'` (origin / enabled).
- If `session_replication_role` was used: it's `SET LOCAL`, so it ends with the transaction; no cleanup needed. Confirm at the database level: `SHOW session_replication_role;` should return `origin` in fresh sessions.

---

**Bottom line.** The slice's batched UPDATE looks safe in isolation, but the AFTER UPDATE → Kafka trigger turns it into a 50M-event publish storm that will overrun a consumer sized for 5k/sec. The slice as written does **not** account for the trigger cost. Fix by suppressing the trigger for the backfill session (`session_replication_role = 'replica'`) -- or, better, skip the physical backfill entirely if NULL can mean `'organic'` at the read layer.