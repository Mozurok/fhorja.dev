# Audit: NOT VALID + VALIDATE Split Migration

## Summary

**No, this is NOT the safe variant the team thinks it is.** Putting both statements in a single migration file defeats the entire purpose of the NOT VALID/VALIDATE split. The team gets the syntactic pattern but loses the operational benefit -- the migration still blocks on the full table scan, with the additional cost of two ALTER TABLE statements taking AccessExclusiveLock back-to-back inside the same transaction (or successive transactions in the same deploy).

---

## 1. Per-Statement Verdict

### Statement 1: `ALTER TABLE invoices ADD CONSTRAINT ... NOT VALID`

**Verdict: SAFE on its own.**

- **Lock acquired**: `AccessExclusiveLock` on `invoices`.
- **Duration**: Near-instant (milliseconds). NOT VALID skips the table scan -- it only updates `pg_constraint` metadata.
- **Effect**: From this point on, all new INSERTs and UPDATEs are checked against the constraint. Existing rows are NOT checked.
- **Risk**: The lock is brief but exclusive. On a hot 80M-row `invoices` table, even a sub-second AccessExclusiveLock can stack behind / block in-flight transactions (lock queue head-of-line blocking). Acceptable with a reasonable `lock_timeout` (e.g., `SET lock_timeout = '2s'`) and retry.

### Statement 2: `ALTER TABLE invoices VALIDATE CONSTRAINT ...`

**Verdict: UNSAFE as written in this migration context.**

- **Lock acquired**: `ShareUpdateExclusiveLock` on `invoices` (Postgres 9.4+ relaxed this from AccessExclusive -- good).
- **What it allows**: Concurrent SELECT, INSERT, UPDATE, DELETE.
- **What it blocks**: Other DDL, VACUUM FULL, CREATE INDEX (non-concurrent), other ALTER TABLE, ANALYZE in some paths, autovacuum on this table.
- **Duration**: This is the real problem -- it performs a **full sequential scan of all 80M rows** to verify the predicate. See section 2.
- **Critical issue**: Running this immediately after Statement 1 in the same migration means the deploy pipeline blocks for the entire scan duration. If the team's mental model is "NOT VALID is the safe cheap part, VALIDATE is the deferred expensive part" -- they wrote the code as if VALIDATE were also cheap. It isn't.

### Compounded issue: same migration file

If both statements run inside a single implicit transaction (depends on the migration runner -- many wrap each file in BEGIN/COMMIT), the AccessExclusiveLock from Statement 1 is held until Statement 2 commits, which means **the entire 80M-row scan runs under AccessExclusiveLock**, not ShareUpdateExclusiveLock. This would block all reads and writes for the duration. Even if the runner does not wrap in a transaction, the two statements run back-to-back with no operational pause for monitoring.

---

## 2. Actual Lock Level + Duration Estimate for VALIDATE on 80M Rows

**Lock level**: `ShareUpdateExclusiveLock` (assuming statements run in separate transactions -- verify your migration runner's behavior).

**Duration estimate** for a full sequential scan of 80M rows:

| Factor | Assumption | Estimate |
|---|---|---|
| Row width | Typical invoice row ~200-500 bytes | 16-40 GB table size |
| Scan throughput | Warm cache, modern NVMe, no contention | ~500 MB/s - 1 GB/s |
| Scan throughput | Cold cache or shared cloud storage (RDS gp3, etc.) | 100-300 MB/s |
| **Realistic range** | | **3-7 minutes warm, 10-30 minutes cold** |

**Additional risks during the scan**:
- **Autovacuum blocked** on `invoices` for the entire duration. If autovacuum was midway through a vacuum cycle, it gets canceled.
- **Replication lag**: On a primary, the scan generates minimal WAL (VALIDATE writes only the `convalidated = true` flip), but the long-running transaction on the primary can pin replication slots and delay `hot_standby_feedback`-driven vacuum decisions on replicas.
- **Statement timeout**: If `statement_timeout` is set globally (e.g., 5 minutes for safety), VALIDATE will be killed mid-scan and rolled back, leaving the constraint NOT VALID. Worth a `SET LOCAL statement_timeout = 0` for this statement specifically.
- **Lock queue**: While ShareUpdateExclusive does not block DML, it does block any other DDL -- including emergency `CREATE INDEX CONCURRENTLY`, `ANALYZE`, or another deploy attempting to ALTER `invoices`. During a rolling deploy, a parallel hotfix could be stuck behind this.

---

## 3. Recommended Re-Slicing

### Phase 1 -- Ship NOT VALID immediately

```sql
-- migrations/20260607130001_add_invoice_amount_check_not_valid.sql
SET lock_timeout = '2s';
ALTER TABLE invoices
  ADD CONSTRAINT invoices_amount_positive CHECK (amount_cents > 0) NOT VALID;
```

- Ships with normal deploy. Sub-second.
- Immediately protects against NEW bad data -- the actual business-value half of the constraint.
- Retry with backoff if `lock_timeout` fires.

### Phase 2 -- Schedule VALIDATE separately

```sql
-- migrations/20260608020000_validate_invoice_amount_check.sql
-- DEPLOY DURING LOW-TRAFFIC WINDOW (e.g., 02:00-04:00 UTC)
SET lock_timeout = '5s';   -- short wait to acquire the lock
SET statement_timeout = 0; -- but allow the scan to run to completion
ALTER TABLE invoices VALIDATE CONSTRAINT invoices_amount_positive;
```

- Runs as a separate migration file, separate deploy, separate change ticket.
- Scheduled for a quiet window so the long ShareUpdateExclusiveLock does not collide with batch jobs, other deploys, or autovacuum maintenance.
- Pre-flight: confirm again that zero rows violate the predicate (`SELECT count(*) FROM invoices WHERE amount_cents <= 0`) -- the pre-flight audit may be stale by Phase 2 time.
- Monitor: track scan progress via `pg_stat_progress_cluster` is not applicable here; use `pg_stat_activity` for the backend pid and watch `wait_event` / query duration.

### Optional Phase 2.5 -- Batched verification before VALIDATE

To de-risk further, run a chunked SELECT scan (read-only, no locks) in the days before Phase 2 to confirm no violations exist, e.g., iterate by `id` ranges of 1M rows. This avoids the situation where VALIDATE runs for 20 minutes and then fails on row 79,999,000.

---

## 4. Rollback Per Phase

### Phase 1 rollback

```sql
ALTER TABLE invoices DROP CONSTRAINT invoices_amount_positive;
```

- Sub-second, AccessExclusiveLock briefly.
- Safe to run anytime. New writes stop being checked. No data loss.
- Application impact: any code path that started relying on the constraint being enforced server-side must be reviewed -- generally none for a CHECK that only rejects bad data.

### Phase 2 rollback

Two scenarios:

**A. VALIDATE failed or was canceled mid-scan**
- Constraint remains in `NOT VALID` state (the failed VALIDATE rolls back cleanly).
- No DDL needed. Investigate why (violating row found? statement_timeout? lock contention?) and re-run later.

**B. VALIDATE succeeded but you need to revert**
- Postgres has no "un-validate" -- the only way back is to DROP and re-ADD as NOT VALID:

```sql
BEGIN;
ALTER TABLE invoices DROP CONSTRAINT invoices_amount_positive;
ALTER TABLE invoices
  ADD CONSTRAINT invoices_amount_positive CHECK (amount_cents > 0) NOT VALID;
COMMIT;
```

- Both statements take AccessExclusiveLock briefly; wrap in a transaction so there is no window where the constraint is absent.
- This rollback is rare -- VALIDATE succeeding means the data is already clean, so reverting is almost always a no-op operationally.

---

## Bottom Line

The pattern (`NOT VALID` then `VALIDATE`) is correct. The **packaging** is wrong: bundling both into one migration file gives the team the worst of both worlds -- they pay the full table-scan cost during their normal deploy window, with the lock-stacking risk of two consecutive ALTERs, while believing they have decoupled the two phases. Split the file, schedule Phase 2 explicitly, set `statement_timeout = 0` on the VALIDATE, and gate Phase 2 on a fresh violation-count pre-flight.