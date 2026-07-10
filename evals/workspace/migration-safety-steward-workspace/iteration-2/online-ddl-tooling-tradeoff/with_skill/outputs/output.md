# MIGRATION_SAFETY.md

**Audit run_id:** mss-2026-06-05-online-ddl-tooling-tradeoff
**Migration files audited:** `migrations/20260606140006_index_orders_by_user.sql` (1 statement)
**Postgres version:** 14
**Deployment strategy:** rolling deploy, no maintenance window
**Online-DDL tooling in scope:** `pg_repack` (installed last quarter)
**Row count assumptions:** `orders` ≈ 200M rows → bucket `>100M` (highest sensitivity)
**Write profile assumptions:** ~5k INSERTs/min + ~10k UPDATEs/min sustained; 3x peak at hour boundaries; long-running OLAP transactions (~30 min) regularly open during business hours
**Historical signal:** `CREATE INDEX CONCURRENTLY` has failed on this table **twice in the last 6 months**

---

## Per-statement verdict table

| stmt_id | file:line | statement | classification | lock_level (as written) | est_row_count_bucket | verdict | rollback | remediation_link |
|---|---|---|---|---|---|---|---|---|
| S1 | `20260606140006_index_orders_by_user.sql:1` | `CREATE INDEX idx_orders_user_id ON orders(user_id);` | `CREATE-INDEX` | `ShareLock` (blocks writes for the full build duration) | `>100M` | **UNSAFE** | `DROP INDEX [CONCURRENTLY] idx_orders_user_id;` (reversible, safe) | See **Recommended phasing → S1** below |

**Why UNSAFE (not just NEEDS-PHASING):** the statement as written takes a `ShareLock` on `orders` for the full duration of the index build. On a 200M-row table with ~15k writes/min sustained, the build will hold writes off for tens of minutes to hours; this is a guaranteed production incident under the stated deployment strategy (rolling deploy, no maintenance window). Symptom: all checkout INSERT/UPDATE traffic blocks, request queues saturate at the app tier, user-visible 5xx and PagerDuty page within ~2 minutes of running this statement.

---

## Risks grouped by severity

### P0 -- UNSAFE / IRREVERSIBLE
- **S1 lock contention as-written:** bare `CREATE INDEX` on a 200M-row table under 15k writes/min holds `ShareLock` for the entire build. **Failure mode:** writes (INSERT/UPDATE on `orders`) block for the duration of the build. **Production symptom:** checkout path stalls, app-tier request queues saturate, user-visible 500/timeout, PagerDuty page within ~2 minutes. This is the dominant risk and MUST be remediated before any deploy.

### P1 -- NEEDS-PHASING (concrete failure mode)
- **S1 remediated via `CONCURRENTLY` has a known failure mode on THIS table:** `CREATE INDEX CONCURRENTLY` waits for all transactions started before it to complete (it does two table scans separated by a wait for old snapshots). The table is documented to host ~30-minute OLAP transactions during business hours, AND CONCURRENTLY has already failed twice in 6 months. A failed `CONCURRENTLY` build leaves an `INVALID` index behind (`pg_index.indisvalid = false`), which must be detected and dropped before retry, and the failure consumes a long build cycle of WAL + I/O on a 200M-row table. **Production symptom:** silent partial work, retry cost, on-call cleanup, and the original feature need (the index) still unmet.
- **Peak-hour collision:** any long DDL on this table that overlaps the hourly 3x write spike compounds lock-wait fan-out. Window selection is itself a P1 risk regardless of variant chosen.

### P2 -- SAFE but worth noting
- **Naming / idempotency:** the statement does not use `IF NOT EXISTS`. On retry after a prior partial run, it will error rather than no-op. Low impact but worth fixing alongside the rewrite.

---

## CONCURRENTLY vs pg_repack -- explicit comparison for THIS table profile

The standard advice ("just use `CREATE INDEX CONCURRENTLY`") is **not** the right answer here. Both options must be evaluated against the actual write profile and historical record.

| Dimension | `CREATE INDEX CONCURRENTLY` | `pg_repack --only-indexes` (index-only mode of pg_repack) |
|---|---|---|
| Lock on `orders` | `ShareUpdateExclusiveLock` (allows reads + writes) | Brief `AccessExclusiveLock` only at swap; writes continue throughout build |
| Behavior under long-running OLAP txns | **Blocks/waits** for all txns started before the build; a 30-min OLAP txn extends the build window by ~30 min and increases failure probability | Builds the index in a separate transaction; does not require waiting for pre-existing snapshots in the same way; tolerates concurrent long-running queries |
| Behavior under high write contention (15k/min) | Two full table scans + wait phase; the wait phase is where this table has failed twice already | Index built via internal triggers/log table tracking changes; tolerates sustained write load by design |
| Failure cost | Failed build leaves `INVALID` index; full build work wasted; must `DROP INDEX CONCURRENTLY` and retry | Failure is contained; pg_repack cleans up its working objects; no `INVALID` index left behind in the catalog (it never swaps in until success) |
| Cannot run inside | A transaction block | A transaction block (also true) |
| Disk overhead during build | ~1x index size temporarily | ~1x index size temporarily (similar) |
| Operational maturity on this team | Standard, but has empirically failed 2x in 6 months on THIS table | Adopted last quarter; the team owns it |
| Recommended for THIS table profile | **No** -- historical evidence shows it fails under exactly the conditions present (long OLAP txns + write contention) | **Yes** -- directly designed for the failure mode this table exhibits |

**Verdict on the variant choice:** for this table profile (200M rows, 15k writes/min, 30-min OLAP txns, 2 prior CONCURRENTLY failures), **`pg_repack` is the safer variant**. CONCURRENTLY's wait-for-old-snapshots semantics is exactly the failure mode already observed. The "use CONCURRENTLY" default reflexively applied here would be the third failure.

---

## Recommended phasing

### S1 -- replace bare `CREATE INDEX` with `pg_repack`-driven build

**Phase 1 -- Pre-checks (no DDL):**
```sql
-- 1a. Confirm pg_repack extension is installed and version matches client.
SELECT extname, extversion FROM pg_extension WHERE extname = 'pg_repack';

-- 1b. Confirm no prior partial/invalid index with the target name exists.
SELECT c.relname, i.indisvalid, i.indisready
FROM pg_index i
JOIN pg_class c ON c.oid = i.indexrelid
WHERE c.relname = 'idx_orders_user_id';

-- 1c. Confirm sufficient free disk: need ~size_of(orders) * (existing_indexes_total / table_size)
--     plus the new index size. Pull current sizes:
SELECT pg_size_pretty(pg_relation_size('orders')) AS table_size,
       pg_size_pretty(pg_indexes_size('orders')) AS indexes_size;
```

**Phase 1 -- Build the index out-of-band with `pg_repack`:**
```bash
# Run from an operator host with PG client + pg_repack client binary installed.
# Schedule OUTSIDE the hour-boundary 3x write peak window.
# Index-only mode: builds a new index, swaps it in atomically under brief AccessExclusiveLock.
pg_repack \
  --host="$PGHOST" \
  --port="$PGPORT" \
  --username="$PGUSER" \
  --dbname="$PGDATABASE" \
  --table=public.orders \
  --only-indexes \
  --index=public.idx_orders_user_id \
  --jobs=2 \
  --wait-timeout=60 \
  --no-kill-backend \
  --elevel=INFO
```

Notes on the flags chosen:
- `--only-indexes` + `--index=...` scopes pg_repack to building this one index, not repacking the whole table.
- Because the index does not yet exist, the team's actual flow is: **first create the index definition with `CREATE INDEX CONCURRENTLY ... ` is the wrong default here**, OR use the documented pg_repack pattern of *creating the index manually inside pg_repack's managed flow*. If your pg_repack version's `--only-indexes` requires the index to pre-exist, the correct pattern is two-step: (i) create as `INVALID` placeholder via a brief catalog-only operation, then (ii) let pg_repack rebuild it. Confirm the installed pg_repack version's exact contract for `--only-indexes` on a non-existent index before running. **If the installed version requires pre-existence, fall back to:** create the index in an off-peak window via `CREATE INDEX CONCURRENTLY` with explicit pre-flight that kills/defers long-running OLAP txns for the window (see fallback below).
- `--wait-timeout=60` bounds the swap-phase wait.
- `--no-kill-backend` ensures pg_repack does not auto-cancel application queries.
- `--jobs=2` parallelizes the build modestly without saturating I/O on a hot table.

**Phase 1 -- Code change:** none. The index is read-optional until the query planner uses it; deploy that depends on it ships in Phase 2.

**Observe window:** verify `pg_index.indisvalid = true` for `idx_orders_user_id`, check `pg_stat_user_indexes.idx_scan` rises after planner picks it up, watch p95 query latency on the targeted query for 24h.

**Phase 2 -- Application read change (separate deploy):** ship the application code that depends on the index existing (the slice that motivated this migration). Do not couple Phase 1 (DDL) and Phase 2 (app) into a single deploy.

### Fallback if pg_repack `--only-indexes` requires pre-existing index in the installed version

Use `CREATE INDEX CONCURRENTLY` **with hardened preconditions** rather than the bare form:
```sql
-- Run OUTSIDE the hour-boundary 3x peak; ideally during the lowest OLAP window.

-- Pre-flight: surface any long-running txns that would extend the build.
SELECT pid, now() - xact_start AS xact_age, state, query
FROM pg_stat_activity
WHERE xact_start IS NOT NULL
  AND now() - xact_start > interval '5 minutes'
ORDER BY xact_age DESC;
-- If any rows returned and they cannot be drained, ABORT and reschedule.
-- Do NOT proceed if OLAP load is active -- that is the documented failure mode.

-- Set a statement-level lock_timeout so a stall fails fast instead of holding queue.
SET lock_timeout = '5s';

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_orders_user_id
  ON orders(user_id);

-- Post-flight: verify validity. If invalid, drop and re-attempt in next window.
SELECT i.indisvalid
FROM pg_index i
JOIN pg_class c ON c.oid = i.indexrelid
WHERE c.relname = 'idx_orders_user_id';
-- If indisvalid = false:
--   DROP INDEX CONCURRENTLY idx_orders_user_id;
--   and retry in a cleaner window.
```

This fallback is explicitly **second-choice** for this table; pg_repack is preferred given the historical record.

---

## Rollback plan per statement

| stmt_id | rollback statement | safety profile |
|---|---|---|
| S1 (pg_repack build) | `DROP INDEX CONCURRENTLY IF EXISTS idx_orders_user_id;` | **SAFE.** Drop is reversible by re-running Phase 1. `DROP INDEX CONCURRENTLY` takes `ShareUpdateExclusiveLock` only, does not block reads/writes. No data loss; only query plans regress. |
| S1 (CONCURRENTLY fallback) | `DROP INDEX CONCURRENTLY IF EXISTS idx_orders_user_id;` | Same. Additionally: if a prior attempt left an `INVALID` index, this drop is the cleanup path. |

No `IRREVERSIBLE` operations in this migration. No `## Irreversible operations requiring user confirmation` block needed.

---

## Risks to watch (proposed for TASK_STATE.md)

- **P0:** Bare `CREATE INDEX` on 200M-row `orders` under 15k writes/min will block writes for the full build → checkout outage. Mitigation: replace with pg_repack-driven build.
- **P1:** `CREATE INDEX CONCURRENTLY` has historically failed twice on this table due to long-running OLAP transactions; do not adopt CONCURRENTLY as the primary path without hardened pre-flight + acceptance of likely retry cycles.
- **P1:** Any DDL on `orders` overlapping the hour-boundary 3x write peak compounds lock-wait fan-out; schedule pg_repack outside peak windows.

---

## Phasing decision (proposed for DECISIONS.md)

**Proposed locked decision:** for index builds on `orders` (and any table with comparable write profile + long-running OLAP txns), `pg_repack --only-indexes` is the **default safe variant**, not `CREATE INDEX CONCURRENTLY`. CONCURRENTLY is retained only as a hardened fallback with explicit pre-flight (OLAP-drain check + `lock_timeout`) when pg_repack is unavailable for a specific operation.

---

## Recommended next command

`decision-interview` -- the choice between pg_repack vs CONCURRENTLY-with-hardening as the team's default for `orders`-class tables is a policy decision that should be locked into DECISIONS.md before this migration ships, so the same call is not relitigated next time. If the user prefers to immediately re-slice, route to `implementation-plan` to split this into the two phases above; if everything is already accepted, `approve-proposed` to persist the artifact changes.
