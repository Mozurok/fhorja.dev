# Migration Safety Audit: `ADD COLUMN ... NOT NULL DEFAULT 'unknown'`

## Statement under review

```sql
ALTER TABLE users
  ADD COLUMN signup_source text NOT NULL DEFAULT 'unknown';
```

Target table: `users`, ~50M rows, rolling deploy.

---

## Step 1 -- Per-statement verdict (per scenario)

| Scenario | PG version | Verdict |
|---|---|---|
| A | PostgreSQL 15 | **SAFE** (with caveats -- see Step 2) |
| B | PostgreSQL 10  | **UNSAFE -- NEEDS PHASING** |

The verdict differs even though the SQL text is identical. The difference is entirely a function of how each major version implements `ADD COLUMN ... DEFAULT <constant>` under the hood.

---

## Step 2 -- Why the verdict differs by PG version

### PostgreSQL 11 and later (covers Scenario A / PG15)

Since PG11 (commit `16828d5c`, the "fast default" feature), `ALTER TABLE ... ADD COLUMN ... DEFAULT <non-volatile expression>` is a **metadata-only** operation:

- The default value is stored in `pg_attribute.attmissingval` and `atthasmissing` is set.
- Existing rows are **not** rewritten. Reads synthesize the default on the fly when a row pre-dates the column.
- Subsequent `UPDATE`s/inserts materialize the column normally.
- The whole `ALTER TABLE` finishes in milliseconds regardless of table size.

Adding `NOT NULL` in the same statement is also cheap in PG11+:
- The planner knows every existing row will logically have `'unknown'` (the missing value), so it does not need to scan the heap to validate the constraint.
- The `NOT NULL` is recorded in catalog and enforced for future writes.

Lock held: `ACCESS EXCLUSIVE` on `users`, but only for the catalog flip -- duration is independent of row count. On a healthy 50M-row table this is typically <100ms.

Caveats that still apply on PG15:
1. `ACCESS EXCLUSIVE` conflicts with **every** other lock mode, including the `ACCESS SHARE` that any `SELECT` takes. If a long-running query or an idle-in-transaction session is holding `users`, the `ALTER` will queue behind it and **everything else queues behind the `ALTER`** (lock-queue head-of-line blocking). Mitigation: `SET lock_timeout = '2s';` and retry, plus monitor `pg_stat_activity` for `state = 'idle in transaction'` before running.
2. The default must be a constant / non-volatile expression. `'unknown'::text` qualifies. (If it were `now()` or `gen_random_uuid()`, the fast-default path would not apply and PG would rewrite the table.)
3. Rolling deploy contract: old app code does not know about `signup_source`. As long as old code uses `INSERT INTO users (...) VALUES (...)` without listing the new column, the default applies and the `NOT NULL` is satisfied. Old code that does `SELECT *` will see an extra column -- usually fine, but verify ORM/codegen does not blow up on schema drift.

### PostgreSQL 10 and earlier (covers Scenario B / PG10)

Fast default does not exist. `ADD COLUMN ... DEFAULT <constant>` **rewrites the entire table**:

- PG10 takes `ACCESS EXCLUSIVE` on `users` and walks every heap page, writing a new tuple version for every row with the default materialized.
- All indexes on `users` are rebuilt as part of the same operation.
- Lock is held for the **entire duration of the rewrite**, not milliseconds.
- For 50M rows, this is typically tens of minutes to multiple hours depending on row width, indexes, and disk throughput. Rough order of magnitude: 10M–20M rows/minute on decent SSD, so plan for 30–90 minutes minimum, longer with heavy indexes.
- During this window: no reads, no writes, no schema introspection on `users`. Connections pile up, the connection pool saturates, the app degrades to outage.
- Replication: WAL volume for the rewrite is enormous (essentially the size of the table + indexes). Replicas may fall behind; rolling deploy across replicas becomes a problem.
- Adding `NOT NULL` on PG10 in the same statement is fine *because* the rewrite materializes every row with the default, so the constraint is trivially satisfied at the end of the rewrite. The cost is in the rewrite itself, not the constraint.

So: identical SQL, but PG10 = full-table rewrite under `ACCESS EXCLUSIVE` = outage. PG15 = catalog flip = safe.

---

## Step 3 -- Phased SQL where NEEDS-PHASING applies

### Scenario A (PG15) -- no phasing required

Ship as-is, with operational guardrails:

```sql
-- Run during a low-traffic window. Bound lock wait to avoid head-of-line blocking.
SET lock_timeout = '2s';
SET statement_timeout = '10s';

ALTER TABLE users
  ADD COLUMN signup_source text NOT NULL DEFAULT 'unknown';
```

If `lock_timeout` fires, sleep and retry; investigate the blocker (long transaction, autovacuum on `users` in `(to prevent wraparound)` mode which cannot be cancelled, etc.) before retrying further.

Optional refinement: split the default and the `NOT NULL` only if you want belt-and-suspenders behavior and you do not fully trust the fast-default path (e.g., partitioned tables, foreign tables in the inheritance tree, or extensions that rewrite tuples). The four-phase pattern in Scenario B works on PG15 too and costs nothing.

### Scenario B (PG10) -- phasing required

Goal: never hold `ACCESS EXCLUSIVE` on `users` for longer than a catalog flip. Backfill in batches under normal row locks.

**Phase 1 -- Add nullable column with no default (catalog-only, fast)**

```sql
-- Deploy 1: schema change only. Old app code unaffected (column is nullable, no default required).
SET lock_timeout = '2s';

ALTER TABLE users
  ADD COLUMN signup_source text;
```

This is metadata-only even on PG10 because there is no default and no `NOT NULL` -- no rewrite, no per-row work.

**Phase 2 -- Deploy application code that writes `signup_source` on all new inserts/updates**

No SQL. App code now always populates `signup_source` (falling back to `'unknown'` in application logic when the source is genuinely unknown). After this deploy, all *new* rows have the column populated.

**Phase 3 -- Backfill existing rows in batches**

Run from a job / script outside the migration runner so it can be paused, throttled, and resumed. Each batch is a short transaction holding only row locks.

```sql
-- Repeat until 0 rows updated. Tune batch size to your I/O and replication lag tolerance.
WITH batch AS (
  SELECT id
  FROM users
  WHERE signup_source IS NULL
  ORDER BY id
  LIMIT 10000
  FOR UPDATE SKIP LOCKED
)
UPDATE users u
SET signup_source = 'unknown'
FROM batch
WHERE u.id = batch.id;
```

Between batches: short sleep (e.g., 200ms), monitor replication lag, throttle if lag grows. For 50M rows at 10k/batch and ~1 batch/sec, expect ~90 minutes of backfill -- but the cluster stays online the whole time.

If `users.id` is not the natural ordering key, use whatever indexed column gives a sargable range scan. Add a partial index temporarily if needed:

```sql
-- Optional: speed up the WHERE signup_source IS NULL scan. Create CONCURRENTLY to avoid locks.
CREATE INDEX CONCURRENTLY users_signup_source_null_idx
  ON users (id)
  WHERE signup_source IS NULL;

-- Drop after backfill completes:
DROP INDEX CONCURRENTLY users_signup_source_null_idx;
```

**Phase 4 -- Verify zero NULLs, then add the `NOT NULL` constraint**

PG10 does not support `NOT NULL NOT VALID` / `VALIDATE CONSTRAINT` for `NOT NULL` directly. The standard PG10 workaround is to add a `CHECK (signup_source IS NOT NULL) NOT VALID`, validate it (which only takes `SHARE UPDATE EXCLUSIVE`, not `ACCESS EXCLUSIVE`), then convert.

```sql
-- 4a: verification gate. Must return 0 before continuing.
SELECT count(*) FROM users WHERE signup_source IS NULL;

-- 4b: add CHECK constraint without scanning the table.
SET lock_timeout = '2s';
ALTER TABLE users
  ADD CONSTRAINT users_signup_source_not_null
  CHECK (signup_source IS NOT NULL) NOT VALID;

-- 4c: validate the constraint. Takes SHARE UPDATE EXCLUSIVE, allows concurrent DML.
ALTER TABLE users
  VALIDATE CONSTRAINT users_signup_source_not_null;
```

You can stop here -- the `CHECK` constraint enforces the invariant. If you specifically need a catalog-level `attnotnull` (some tooling cares), then on PG10 the only way to set it is `ALTER TABLE users ALTER COLUMN signup_source SET NOT NULL`, which **does** require an `ACCESS EXCLUSIVE` full-table scan to verify. Because Phase 3 + the validated `CHECK` guarantee no NULLs, the scan finds no violators, but it still scans every row under `ACCESS EXCLUSIVE`. Run only in a maintenance window:

```sql
-- 4d (optional, maintenance window): promote CHECK to true NOT NULL.
SET lock_timeout = '5s';
ALTER TABLE users
  ALTER COLUMN signup_source SET NOT NULL;

-- Optional cleanup: drop the redundant CHECK once attnotnull is set.
ALTER TABLE users
  DROP CONSTRAINT users_signup_source_not_null;
```

**Phase 5 -- Set the column default for future writers that omit it**

```sql
SET lock_timeout = '2s';
ALTER TABLE users
  ALTER COLUMN signup_source SET DEFAULT 'unknown';
```

`SET DEFAULT` is a catalog-only change on every supported PG version -- no rewrite, fast.

Note: I deliberately put `SET DEFAULT` *after* backfill rather than before, so that the existence of the default cannot mask an application bug where new inserts should have provided a real `signup_source` and silently got `'unknown'` instead. If your app contract is "default is fine when source is unknown," you can move `SET DEFAULT` to Phase 1 with no safety penalty.

---

## Step 4 -- Lock duration risk (cross-reference of lock × rows × version)

| Scenario | Lock mode | Held for | Effective blast radius |
|---|---|---|---|
| A (PG15, 50M rows) | `ACCESS EXCLUSIVE` | Catalog flip only -- <100ms typical | Brief stall on `users`; safe under `lock_timeout=2s` with retry |
| B (PG10, 50M rows), one-shot | `ACCESS EXCLUSIVE` | Full table + index rewrite -- 30–90 min | Outage on `users`, connection pool exhaustion, replication lag spike |
| B (PG10, 50M rows), phased | `ACCESS EXCLUSIVE` only in Phase 1 (catalog), Phase 4d (optional, scan-only, maintenance window) | Each <few seconds for catalog; Phase 4d scan duration if used | Acceptable; backfill in Phase 3 uses only per-row locks |

This is the heart of the version split: lock *mode* is the same (`ACCESS EXCLUSIVE` for the top-level `ALTER`), but lock *duration* is bounded by catalog work on PG11+ and unbounded (proportional to row count) on PG10. Senior DB review must check both axes.

---

## Step 5 -- Rollback per scenario

### Scenario A (PG15)

Rollback is symmetric and cheap because the original `ALTER` was metadata-only:

```sql
SET lock_timeout = '2s';
ALTER TABLE users
  DROP COLUMN signup_source;
```

`DROP COLUMN` is catalog-only on all supported versions (the column is logically removed; physical storage is reclaimed lazily by future `VACUUM FULL` / table rewrites). Fast and safe.

Rolling-deploy ordering for rollback: revert app code first (so the app stops referencing `signup_source`), then drop the column. If you drop the column while old app code still references it, queries that name the column explicitly will error.

### Scenario B (PG10)

Rollback depends on which phase you are rolling back from.

- **From Phase 1 (column added, nullable, no default):**

  ```sql
  SET lock_timeout = '2s';
  ALTER TABLE users
    DROP COLUMN signup_source;
  ```

  Fast, catalog-only.

- **From Phase 2 (app writing the column):** redeploy previous app version. No SQL rollback needed; the column being populated for some rows is harmless because it is still nullable.

- **From Phase 3 (mid-backfill):** stop the backfill job. Leave the column. Either resume later or drop the column with the Phase 1 rollback above. Partially-backfilled state is safe because the column is still nullable.

- **From Phase 4 (`CHECK` or `NOT NULL` in place):**

  ```sql
  -- If you only added the CHECK (4a–4c):
  SET lock_timeout = '2s';
  ALTER TABLE users
    DROP CONSTRAINT users_signup_source_not_null;

  -- If you also promoted to attnotnull (4d):
  SET lock_timeout = '2s';
  ALTER TABLE users
    ALTER COLUMN signup_source DROP NOT NULL;
  ```

  Both are catalog-only and fast. The column itself can then be dropped if desired (Phase 1 rollback).

- **From Phase 5 (default set):**

  ```sql
  SET lock_timeout = '2s';
  ALTER TABLE users
    ALTER COLUMN signup_source DROP DEFAULT;
  ```

  Catalog-only.

What is *not* rollback-friendly on PG10 is the original one-shot statement. If someone runs the unphased `ALTER TABLE users ADD COLUMN signup_source text NOT NULL DEFAULT 'unknown'` on PG10 and it makes it through, the column is materialized in every heap tuple. `DROP COLUMN` only marks it dropped in the catalog; the storage is not reclaimed until a later table rewrite (`VACUUM FULL` or `CLUSTER`), which itself needs `ACCESS EXCLUSIVE` and is another outage. Plus, you've already taken the outage to add it. So the real rollback for "we ran the one-shot on PG10 and it's halfway through" is: cancel the statement (`pg_cancel_backend`), accept that the table is now bloated with partial rewrites, and schedule a maintenance window. Prevention (phasing) is materially cheaper than rollback.

---

## Step 6 -- Summary & ship/no-ship recommendation

- **Scenario A (PG15):** SHIP as-is with `SET lock_timeout = '2s'` and retry logic. Verify no long-running transactions on `users` immediately before running. Rolling deploy is fine because the column has a default and old code that omits it on insert will still satisfy `NOT NULL`.

- **Scenario B (PG10):** DO NOT SHIP the one-shot statement. Replace with the 5-phase plan above (add nullable → deploy app → batched backfill → `CHECK NOT VALID` + `VALIDATE` → optional `SET NOT NULL` in maintenance window → `SET DEFAULT`). The same logical end state is reached without ever holding `ACCESS EXCLUSIVE` for more than a catalog flip during business hours.

- **Cross-cutting recommendation:** the legacy PG10 cluster is the real risk here. PG10 has been EOL since November 2022, which means no security patches, no bug fixes, and -- relevant to this audit -- every schema change is more dangerous than the equivalent on a supported version. The migration off PG10 should be on the roadmap independently of this column addition. Until then, every migration touching `users` (or any other large table) must be reviewed against PG10 semantics, not PG15 intuition, even if the developer authored and tested it on a modern local PG. A pre-merge check that runs `EXPLAIN` / dry-run against a PG10 staging clone would catch this class of bug automatically.
