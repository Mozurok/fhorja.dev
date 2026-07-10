# MIGRATION_SAFETY.md -- `20260606140004_user_profile_overhaul.sql`

**Audit run_id:** mss-2026-06-05-user-profile-overhaul
**Migration file:** `migrations/20260606140004_user_profile_overhaul.sql`
**Postgres version:** 15
**Deployment strategy:** rolling deploy, no maintenance window
**Row count assumptions:** `users` ≈ 25,000,000 rows (bucket: `1M-100M`)
**Online-DDL tooling:** none in scope
**Code-path assumption:** `legacy_signup_source` confirmed unread for 14 days (provided in context); all other columns assumed live-read.

---

## Per-statement verdict table

| statement_id | file:line | DDL (abbrev.) | classification | lock_level | est_row_count_bucket | verdict | rollback | remediation |
|---|---|---|---|---|---|---|---|---|
| S1 | `20260606140004_user_profile_overhaul.sql:1` | `ALTER TABLE users ADD COLUMN signup_referrer text;` | `ADD-COLUMN-NULLABLE` | `AccessExclusiveLock` (metadata-only on PG15; no table rewrite for nullable text w/o default) | `1M-100M` | **SAFE** | `ALTER TABLE users DROP COLUMN signup_referrer;` -- reversible; column has no readers yet. Safety profile: SAFE during deploy window; once code starts writing, drop becomes DROP-COLUMN class (two-phase). | None -- ships as-is. (P2 note: hold lock <50 ms; still ensure no long-running txn on `users` is active to avoid lock-queue stall behind `AccessExclusiveLock`.) |
| S2 | `20260606140004_user_profile_overhaul.sql:2` | `CREATE INDEX idx_users_signup_referrer ON users(signup_referrer);` | `CREATE-INDEX` | `ShareLock` (blocks writes for full build duration on 25M-row table; estimated minutes) | `1M-100M` | **NEEDS-PHASING** | `DROP INDEX idx_users_signup_referrer;` (use `CONCURRENTLY` form for the rollback as well) -- reversible; cheap. Safety profile: rollback SAFE. | Replace with `CREATE INDEX CONCURRENTLY` -- see Remediation R-S2 below. |
| S3 | `20260606140004_user_profile_overhaul.sql:3` | `ALTER TABLE users DROP COLUMN legacy_signup_source;` | `DROP-COLUMN` | `AccessExclusiveLock` (metadata-only mark-dropped on PG15; fast -- sub-second on the catalog) | `1M-100M` | **NEEDS-PHASING** (verdict is *not* SAFE despite the 14-day read-free window because: (a) rolling deploy means old pods/cached prepared statements may still reference the column for the deploy window; (b) operation is **IRREVERSIBLE** -- no data rollback once committed; (c) lock contention risk against long-running txns persists) | **IRREVERSIBLE** -- `ALTER TABLE users ADD COLUMN legacy_signup_source text;` recreates the column but **all row data is permanently lost**. No safe data rollback. Route to `decision-interview` for explicit user sign-off before apply. | See Remediation R-S3 below: gate behind `lock_timeout` + `statement_timeout`, run in its own deploy *after* S1/S2/S4 settle, and confirm zero rolling-deploy pods still reference the column. |
| S4 | `20260606140004_user_profile_overhaul.sql:4` | `ALTER TABLE users ALTER COLUMN email TYPE varchar(254);` | `ALTER-TYPE` (narrowing -- `text` → `varchar(254)` requires per-row length validation under `AccessExclusiveLock`) | `AccessExclusiveLock` for the duration of the full-table scan (validation pass over 25M rows; estimated **minutes**, not seconds, even without rewrite) | `1M-100M` | **UNSAFE** | **IRREVERSIBLE in practice** -- `ALTER TABLE users ALTER COLUMN email TYPE text;` is syntactically reversible and cheap (widening), BUT: (a) if any row had to be repaired or truncated to fit 254 before this ran, that data is gone; (b) the production incident this statement *causes* (full write lock on `users` for minutes during a rolling deploy with no maintenance window) is not "rolled back" by reverting the type -- the outage already happened. Flag `IRREVERSIBLE` for blast-radius purposes. | See Remediation R-S4 below: replace narrowing with a `CHECK (length(email) <= 254) NOT VALID` + separate `VALIDATE CONSTRAINT`, OR a full new-column + backfill + cutover phasing. Do **not** ship the bare `ALTER TYPE`. |

---

## Risks grouped by severity

### P0 -- UNSAFE + IRREVERSIBLE (must rewrite before any deploy)

- **P0-1 (S4): Full-table `AccessExclusiveLock` on 25M-row `users` for minutes during `ALTER COLUMN email TYPE varchar(254)`.**
  - Specific failure mode: PG15 must scan every existing row to verify `length(email) <= 254` before accepting the new type. Even though there is no physical rewrite for `text` → `varchar(n)` when no row exceeds `n`, the **validation scan still holds `AccessExclusiveLock` for the duration of the scan** on a 25M-row table -- measured in minutes, not milliseconds.
  - Likely production symptom: **all reads and writes against `users` block** for the full lock duration. On a login-critical table this means: sign-in, signup, session lookup, password reset, every authenticated request that touches `users` → user-visible 5xx / timeouts → PagerDuty page within ~60–120 s of statement start. Rolling deploy assumption is irrelevant -- the database-level lock is independent of app rollout.
  - Compounding risk: any single row with `length(email) > 254` aborts the statement after holding the lock the whole time -- worst of both worlds (outage + no progress).

### P1 -- NEEDS-PHASING (intent fine, must be re-sliced)

- **P1-1 (S2): `CREATE INDEX` (non-concurrent) on 25M-row `users` blocks all writes for the full build duration.**
  - Specific failure mode: a plain `CREATE INDEX` takes `ShareLock` on the table, which blocks `INSERT` / `UPDATE` / `DELETE` (but not `SELECT`) for the entire build -- minutes on a 25M-row table. Behind `AccessExclusiveLock` from S1 or S3 in the same migration transaction, the index build holds the prior `AccessExclusiveLock` chain even longer.
  - Likely production symptom: signup writes, profile updates, last-login timestamp writes, and any other `users` write path queue up; connection pool saturates; cascading 5xx as upstream services time out waiting on writes. Reads still work, masking the incident initially.
  - Remediation is mechanical: `CREATE INDEX CONCURRENTLY` (which forces it out of any transaction wrapper).

- **P1-2 (S3): `DROP COLUMN legacy_signup_source` ships in the same migration as a rolling deploy with no drain window.**
  - Specific failure mode: rolling deploy means old application pods may still hold cached prepared statements or active transactions that reference `legacy_signup_source` even after the read-removing code has shipped 14 days ago -- particularly if pods have been long-lived without rolling restart, or if any background worker / cron / read-replica analytic still references it. Post-drop, those statements throw `column "legacy_signup_source" does not exist` and become hard errors.
  - Likely production symptom: sporadic 5xx on a subset of pods until they rotate; harder to detect because it's partial; possible Sentry spike rather than full outage.
  - Compounded by **IRREVERSIBLE**: once dropped, data is gone. A late-discovered consumer (e.g. a quarterly billing job, a manual SQL dashboard) has no recourse.
  - Remediation: separate deploy slice *after* S1/S2/S4 land and after a force pod-rotation + 24 h observation; gate with `lock_timeout` so the drop never queues behind a long txn.

### P2 -- SAFE but worth noting

- **P2-1 (S1): `ALTER TABLE users ADD COLUMN signup_referrer text` is metadata-only on PG15 (no default, nullable), but still briefly takes `AccessExclusiveLock`.**
  - Specific failure mode: if a long-running transaction (analytics query, pg_dump, vacuum) holds any lock on `users`, S1 queues behind it AND blocks every subsequent statement queueing behind S1 -- classic lock-queue pileup. Statement itself is sub-second; the queue behind it is the risk.
  - Likely production symptom: short stall (<5 s typical) on `users` writes during deploy. Add `SET lock_timeout = '2s'` before the statement to fail fast instead of queueing.

- **P2-2 (transaction shape): S2 (`CREATE INDEX CONCURRENTLY` after remediation) CANNOT run inside a transaction.** Most migration runners wrap files in a single `BEGIN/COMMIT`. The current file mixes statement classes that require different transaction shapes, which forces a multi-file split regardless of any other concern.

---

## Recommended phasing (concrete, statement-shaped)

### Remediation R-S2 -- `CREATE INDEX` must be `CONCURRENTLY`

**Phase 1 SQL (own migration file, no transaction wrapper):**
```sql
-- migrations/20260606140004a_add_signup_referrer_index.sql
-- runner directive: -- trigger: no-transaction  (or equivalent for your tool)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_signup_referrer
  ON users (signup_referrer);
```

**Post-apply verification:**
```sql
SELECT indexrelid::regclass, indisvalid
  FROM pg_index
 WHERE indexrelid = 'idx_users_signup_referrer'::regclass;
-- indisvalid MUST be true. If false: DROP INDEX CONCURRENTLY and retry.
```

**Rollback:**
```sql
DROP INDEX CONCURRENTLY IF EXISTS idx_users_signup_referrer;
```

---

### Remediation R-S3 -- `DROP COLUMN` re-sliced into its own deploy after observation

**Phase 1 (this deploy): do nothing to `legacy_signup_source`.** Keep it in place.

**Phase 2 (separate deploy, ≥24 h later, after force pod rotation):**
```sql
-- migrations/20260607XXXXXX_drop_legacy_signup_source.sql
SET lock_timeout = '2s';
SET statement_timeout = '5s';
ALTER TABLE users DROP COLUMN legacy_signup_source;
```

**Pre-apply verification (run in a read-only console immediately before apply):**
```sql
-- Confirm zero queries reference the column in the last hour
SELECT count(*) FROM pg_stat_statements
 WHERE query ILIKE '%legacy_signup_source%'
   AND last_exec >= now() - interval '1 hour';
-- Expect 0. If >0, abort and trace the caller before retrying.
```

**Rollback (data-lossy):**
```sql
-- IRREVERSIBLE for data. Schema can be re-added empty:
ALTER TABLE users ADD COLUMN legacy_signup_source text;
-- Row values are permanently lost. Restore from PITR backup if needed.
```

---

### Remediation R-S4 -- replace narrowing `ALTER TYPE` with `CHECK NOT VALID` + `VALIDATE` (preferred), or full new-column phasing

**Preferred path -- enforce the 254-char invariant without changing the column type:**

**Phase 1 (this deploy, fast, no full-table lock):**
```sql
-- migrations/20260606140004b_email_length_check.sql
ALTER TABLE users
  ADD CONSTRAINT users_email_len_chk CHECK (length(email) <= 254) NOT VALID;
-- Takes AccessExclusiveLock briefly (catalog update only), sub-second.
-- New writes are immediately enforced; existing rows are NOT scanned.
```

**Phase 2 (separate deploy or off-peak window, holds only `ShareUpdateExclusiveLock` -- does NOT block reads or writes):**
```sql
-- migrations/20260607XXXXXX_validate_email_length.sql
ALTER TABLE users VALIDATE CONSTRAINT users_email_len_chk;
-- Full scan but concurrent with traffic. Will FAIL if any row > 254 chars.
```

**Pre-Phase-2 verification (in read-only console):**
```sql
SELECT count(*) FROM users WHERE length(email) > 254;
-- If > 0, remediate those rows BEFORE running VALIDATE CONSTRAINT.
```

**Rollback (both phases reversible, cheap):**
```sql
ALTER TABLE users DROP CONSTRAINT users_email_len_chk;
```

**Alternative path (only if the `varchar(254)` type itself is required by an external contract, e.g. an ORM that types the column):** full new-column phasing with backfill -- but this is significantly more work (add `email_new varchar(254)`, dual-write trigger, batched backfill of 25M rows, swap, drop). Surface this tradeoff in `decision-interview` before choosing.

---

## Rollback plan per statement

| statement_id | reverse op | safety profile |
|---|---|---|
| S1 (`ADD COLUMN signup_referrer`) | `ALTER TABLE users DROP COLUMN signup_referrer;` | SAFE while no code reads/writes the column. Becomes DROP-COLUMN class once writers exist. |
| S2 (current bare `CREATE INDEX`) | `DROP INDEX idx_users_signup_referrer;` | SAFE; cheap. After remediation (`CONCURRENTLY`), rollback also uses `DROP INDEX CONCURRENTLY`. |
| S3 (`DROP COLUMN legacy_signup_source`) | `ALTER TABLE users ADD COLUMN legacy_signup_source text;` | **IRREVERSIBLE for data.** Schema reversible; data permanently lost. Requires PITR restore for data recovery. |
| S4 (`ALTER COLUMN email TYPE varchar(254)`) | `ALTER TABLE users ALTER COLUMN email TYPE text;` | **IRREVERSIBLE for blast radius.** Type widening is cheap and reversible, but the lock-induced outage caused by the forward statement is not "undone" by reverting. Any rows truncated to fit 254 are also permanently lost. |

---

## Irreversible operations requiring user confirmation

Two statements carry IRREVERSIBLE flags and MUST be explicitly confirmed via `decision-interview` before any deploy:

1. **S3 -- `DROP COLUMN legacy_signup_source`.** Confirm: (a) you have a PITR backup window covering at least 7 days post-drop; (b) you have verified zero references in `pg_stat_statements` AND in all background workers / cron jobs / analytics queries / read-replica consumers (the 14-day metrics check covered production read path only); (c) you accept that any future need for this column's historical data requires PITR restore.

2. **S4 -- `ALTER COLUMN email TYPE varchar(254)`.** Confirm: (a) the narrowing is actually required (vs. a `CHECK` constraint giving the same enforcement without the lock); (b) you have verified `SELECT count(*) FROM users WHERE length(email) > 254` returns 0 (otherwise the statement aborts after holding `AccessExclusiveLock` for minutes -- worst case); (c) you accept the minutes-long write outage on `users` OR you re-slice per R-S4. **Strong recommendation: take the R-S4 path and do not ship the bare `ALTER TYPE`.**

---

## Verdict distribution & next command

- SAFE: 1 (S1)
- NEEDS-PHASING: 2 (S2, S3)
- UNSAFE: 1 (S4)
- IRREVERSIBLE-flagged: 2 (S3, S4)

**Recommended next command:** `decision-interview` -- two IRREVERSIBLE operations require explicit user sign-off (S3, S4), and the S4 remediation has a non-trivial tradeoff (CHECK-constraint path vs. full new-column phasing) that only the user can lock. After `decision-interview` resolves those, follow with `implementation-plan` to re-slice this single migration file into 3+ deploy phases (Phase A: S1 + R-S2 + R-S4 Phase 1; Phase B: R-S4 Phase 2 validate; Phase C: R-S3 drop column).
