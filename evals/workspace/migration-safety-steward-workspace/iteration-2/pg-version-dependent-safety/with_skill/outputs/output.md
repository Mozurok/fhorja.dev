# MIGRATION_SAFETY.md -- PG-version-dependent audit

**Audit run_id:** mss-2026-06-05-pg-version-add-column-default
**Migration file audited:** `migrations/20260606140005_add_signup_source_with_default.sql`
**Statements parsed:** 1 (single `ALTER TABLE ... ADD COLUMN ... NOT NULL DEFAULT ...`)
**Deployment strategy:** rolling deploy (both scenarios)
**Row count assumption:** `users` ≈ 50M rows (bucket `1M-100M`)
**Scenarios audited:**
- **Scenario A** -- Postgres 15
- **Scenario B** -- Postgres 10 (EOL; legacy inherited cluster)

The audited DDL is **identical**:

```sql
ALTER TABLE users ADD COLUMN signup_source text NOT NULL DEFAULT 'unknown';
```

The verdict differs because PostgreSQL 11 introduced **fast default** semantics that changed this exact statement from a table-rewrite operation to a metadata-only operation. PG10 and PG15 execute the same SQL with materially different physical behavior, and the lock-duration risk on a 50M-row table flips from minutes-to-hours to milliseconds.

---

## Per-statement verdict table

| stmt_id | file:line | classification | scenario | PG version | lock_level | est_row_count | verdict | rollback | remediation |
|---|---|---|---|---|---|---|---|---|---|
| S1-A | `20260606140005_add_signup_source_with_default.sql:1` | `ADD-COLUMN-NOT-NULL` (with constant `DEFAULT`) | A | PG 15 | `AccessExclusiveLock` (very brief, metadata-only -- fast default path) | ~50M | **SAFE** | `ALTER TABLE users DROP COLUMN signup_source;` -- reversible, also metadata-only on PG11+ (no rewrite). | None required. Ship as-is; optionally drain writes for the sub-second metadata flip. See `## Recommended phasing → Scenario A`. |
| S1-B | `20260606140005_add_signup_source_with_default.sql:1` | `ADD-COLUMN-NOT-NULL` (with constant `DEFAULT`) | B | PG 10 | `AccessExclusiveLock` held for the **entire table rewrite** | ~50M | **UNSAFE** | `DROP COLUMN` is metadata-only and itself reversible-by-pattern, BUT cannot save you mid-rewrite -- a killed rewrite leaves bloat + a long recovery. Treat the forward op as effectively **non-roll-backable mid-flight**. | Re-slice into 4 phases (nullable add → backfill in batches → set DEFAULT + NOT NULL → cleanup). See `## Recommended phasing → Scenario B`. |

> **No silent grouping.** Same SQL line, two scenarios, two rows. The classification (`ADD-COLUMN-NOT-NULL`) is the same; the lock-level realization and the verdict are not.

---

## Why the verdict differs by PG version (Step 4 explanation)

### PG 11+ (covers Scenario A, PG 15) -- metadata-only ADD COLUMN with constant DEFAULT

PostgreSQL 11 introduced the **"fast default"** optimization (commit `16828d5c0`, feature: *"Fast ALTER TABLE ADD COLUMN with a non-NULL default"*). When the default expression is a **constant** (or a non-volatile expression that the planner can prove constant at DDL time), the server:

1. Records the default in `pg_attribute.atthasmissing` / `attmissingval`.
2. Does **not** rewrite existing heap tuples.
3. Returns the default value at read time for rows that physically lack the column.
4. Backfills lazily on subsequent row rewrites (UPDATE / VACUUM FULL / etc.).

Consequence for our statement on PG 15:
- `AccessExclusiveLock` is acquired but held only long enough to update the catalog (`pg_attribute`, `pg_attrdef`) -- **milliseconds**, independent of row count.
- The `NOT NULL` constraint is satisfied **logically** by the constant default; no per-row scan is needed because every existing row is treated as having `'unknown'` at read time.
- 50M rows do **not** matter for lock duration.

Verdict: **SAFE**. The only residual concern on a rolling deploy is that old-version app pods must tolerate the new column existing (a read-side `text NOT NULL` column with a default is universally tolerated by `SELECT *` consumers, but explicit-INSERT consumers that don't list the column will still be fine because the default supplies the value).

### PG 10 and earlier (covers Scenario B) -- full table rewrite

Before PG 11, `ADD COLUMN ... DEFAULT <const>` was implemented as:

1. Acquire `AccessExclusiveLock` on `users`.
2. **Rewrite every heap page** to physically add the new column populated with `'unknown'`.
3. **Rewrite every index** on the table (because the heap TIDs change during the rewrite).
4. Release the lock.

Consequence for our statement on PG 10 with 50M rows:
- `AccessExclusiveLock` blocks **all** reads and writes for the duration of the rewrite. With 50M rows of any non-trivial width, that is **minutes to hours** on commodity disk, plus index rebuild time.
- Every concurrent transaction touching `users` queues behind the lock; the lock queue itself then blocks unrelated queries that need a weaker lock on the same table (lock queueing).
- Production symptom: login/signup/auth traffic stalls → connection pool saturates → cascading 5xx → PagerDuty within ~60–120s.
- A mid-flight cancel (`pg_cancel_backend`) leaves a half-rewritten table + bloat; recovery requires `VACUUM FULL` (which itself takes `AccessExclusiveLock`).
- Adding `NOT NULL` is **not** the dominant cost here -- the **DEFAULT-driven rewrite** is. Even `ADD COLUMN ... DEFAULT 'unknown'` without `NOT NULL` would rewrite the table on PG10.

Verdict: **UNSAFE**. Must be re-sliced.

### Why classification stays the same but verdict flips

Step 2 classification (`ADD-COLUMN-NOT-NULL` with constant default) is a property of the SQL **shape**. Step 4 (lock duration) is where PG version semantics enter -- the same shape produces different lock-hold profiles. This is exactly the case the persona's Step 4 was designed to catch: classification alone is insufficient; lock-level × row count × PG version is the load-bearing cross-reference.

---

## Risks grouped by severity

### P0 -- UNSAFE, will cause production incident

- **[Scenario B / PG 10] S1-B full-table rewrite under AccessExclusiveLock on 50M-row `users` table.**
  Specific failure mode: `ALTER TABLE` rewrites every heap page and every index, holding `AccessExclusiveLock` for the entire rewrite (estimated **tens of minutes to hours** at 50M rows).
  Production symptom: all reads and writes against `users` block; downstream auth/session/profile services time out; connection pool saturates; cascading 5xx across the app; PagerDuty page within ~60–120 seconds of issuing the statement. Mid-flight cancel is worse than waiting it out (leaves bloat + requires `VACUUM FULL`).

### P1 -- NEEDS-PHASING with concrete failure mode

- *(none in this audit -- Scenario A is SAFE, Scenario B is UNSAFE-not-NEEDS-PHASING because the current shape will cause an outage, not merely an awkward deploy)*

### P2 -- SAFE but worth noting

- **[Scenario A / PG 15] S1-A metadata-only ADD COLUMN.**
  Specific note: even on PG 11+, the catalog update takes `AccessExclusiveLock` briefly and **queues behind any long-running transaction on `users`**. If a long-running `SELECT` or autovacuum is active, the `ALTER` will block until it completes, and **all subsequent queries on `users` queue behind the waiting ALTER** (lock queueing). Production symptom on a bad day: a 2-minute analytical query holds an `AccessShareLock`, the `ALTER` waits for it, and 10s of seconds of writes pile up behind the `ALTER`.
  Mitigation: set `lock_timeout` before running (e.g. `SET lock_timeout = '2s';`) and retry on failure; ideally run during a low-traffic window.

---

## Recommended phasing

### Scenario A (PG 15) -- no phasing required, defensive wrapper recommended

The migration is SAFE as written. Recommended **operational wrapper** (not a re-slice):

```sql
-- Run during low-traffic window. lock_timeout prevents the ALTER from
-- queueing behind a long-running reader and blocking all subsequent
-- writes on users.
SET lock_timeout = '2s';
SET statement_timeout = '10s';

ALTER TABLE users ADD COLUMN signup_source text NOT NULL DEFAULT 'unknown';

RESET lock_timeout;
RESET statement_timeout;
```

If the `ALTER` fails with `lock_timeout`, retry. Do **not** raise the timeout; the failure indicates a long-running transaction is in flight and forcing through would queue all writes behind the waiting ALTER.

**Rolling deploy ordering for Scenario A:**
- Phase 1 (single deploy): run the migration above. Old and new app pods both work -- old pods ignore the column; new pods read/write it; the constant default keeps `NOT NULL` satisfied for any old-pod INSERT that omits the column.

### Scenario B (PG 10) -- re-slice into 4 phases

The unsafe statement must be decomposed. The principle: never let PG10 see a single statement that requires a table rewrite while holding `AccessExclusiveLock`. Split DEFAULT from NOT NULL, and backfill in batches under a weaker lock.

**Phase 1 -- Add nullable column (no default).** Metadata-only on every PG version including PG 10.

```sql
-- migrations/20260606140005a_add_signup_source_nullable.sql
ALTER TABLE users ADD COLUMN signup_source text;
-- No DEFAULT, no NOT NULL. PG10 does NOT rewrite the table for this.
-- AccessExclusiveLock held for milliseconds (catalog update only).
```

**Phase 1 code change:** ship app code that **writes** `signup_source` on every new INSERT (defaulting to `'unknown'` in application code where the source is genuinely unknown) but does **not** assume the column is `NOT NULL` on read. Wait for full rollout + at least one full deploy cycle of observation.

**Phase 2 -- Backfill in batches.** Avoid a single 50M-row `UPDATE` (which takes a row-exclusive lock on every row and bloats WAL massively). Batch in chunks of e.g. 10k rows with brief pauses.

```sql
-- Run repeatedly from an external script until 0 rows affected.
-- Each batch is its own transaction; no long-held locks.
UPDATE users
SET signup_source = 'unknown'
WHERE ctid = ANY (ARRAY(
  SELECT ctid FROM users
  WHERE signup_source IS NULL
  LIMIT 10000
));
-- Sleep 100ms between batches to let replication / autovacuum catch up.
-- Monitor pg_stat_replication lag and bloat on users.
```

**Phase 3 -- Attach DEFAULT (metadata-only on every PG version).**

```sql
-- migrations/20260606140005b_set_signup_source_default.sql
ALTER TABLE users ALTER COLUMN signup_source SET DEFAULT 'unknown';
-- Metadata-only on PG10 too: SET DEFAULT does NOT rewrite the table.
-- Only affects future INSERTs.
```

**Phase 4 -- Add NOT NULL after backfill verification.** This is the only remaining risk: on PG10, `SET NOT NULL` performs a sequential scan to verify the constraint, holding `AccessExclusiveLock` for the duration of the scan. At 50M rows on modern hardware this is typically a few minutes (much faster than a rewrite -- no page writes, just a scan) but still risky.

Two options, in order of preference:

**Phase 4 option A (preferred on PG10 -- defer NOT NULL or accept a brief scan-only lock):**

```sql
-- migrations/20260606140005c_set_signup_source_not_null.sql
-- Verify 0 NULLs first (outside the ALTER) -- should return 0 after Phase 2:
-- SELECT count(*) FROM users WHERE signup_source IS NULL;

SET lock_timeout = '5s';
ALTER TABLE users ALTER COLUMN signup_source SET NOT NULL;
RESET lock_timeout;
-- Retry on lock_timeout. Run during low-traffic window.
```

**Phase 4 option B (safer on PG10 -- use a CHECK constraint validated separately):**

```sql
-- Step 4b.i: add the constraint as NOT VALID (instant, AccessExclusiveLock for ms).
ALTER TABLE users
  ADD CONSTRAINT users_signup_source_not_null
  CHECK (signup_source IS NOT NULL) NOT VALID;

-- Step 4b.ii: validate it under ShareUpdateExclusiveLock (does NOT block reads/writes).
ALTER TABLE users VALIDATE CONSTRAINT users_signup_source_not_null;
```

Option B avoids the `AccessExclusiveLock` scan entirely. The trade-off is that the column is technically `NULL`-able at the catalog level even though the CHECK enforces the same semantics; some ORMs introspect `is_nullable` and may model the column differently. Pick based on ORM behavior.

---

## Rollback plan per statement

### Scenario A (PG 15) rollback

| forward statement | reverse statement | safety profile |
|---|---|---|
| `ALTER TABLE users ADD COLUMN signup_source text NOT NULL DEFAULT 'unknown';` | `ALTER TABLE users DROP COLUMN signup_source;` | **Reversible.** Drop is metadata-only on PG11+; AccessExclusiveLock for milliseconds. Caveat: any app code already reading the new column will break -- roll back app code FIRST, then drop. |

### Scenario B (PG 10) rollback (per phase)

| phase | forward | reverse | safety profile |
|---|---|---|---|
| Phase 1 | `ALTER TABLE users ADD COLUMN signup_source text;` | `ALTER TABLE users DROP COLUMN signup_source;` | **Reversible.** DROP on PG10 of a column added without a rewrite is metadata-only (PG10 does mark `pg_attribute.attisdropped = true` and the column space stays in tuples until next rewrite, but the operation itself is fast and lock-brief). |
| Phase 2 | batched `UPDATE` | no clean reverse -- backfilled values overwrite prior NULLs; original NULLs cannot be distinguished from intentional `'unknown'` writes after the fact. | **EFFECTIVELY IRREVERSIBLE for data fidelity.** If rollback is needed, drop the column (Phase 1 reverse) -- accepts loss of the backfilled values, which is fine because they were synthesized `'unknown'` anyway. |
| Phase 3 | `SET DEFAULT 'unknown'` | `ALTER COLUMN signup_source DROP DEFAULT;` | **Reversible.** Metadata-only on every PG version. |
| Phase 4 (option A) | `SET NOT NULL` | `ALTER COLUMN signup_source DROP NOT NULL;` | **Reversible.** DROP NOT NULL is metadata-only and brief AccessExclusiveLock. |
| Phase 4 (option B) | `ADD CONSTRAINT ... CHECK ... NOT VALID; VALIDATE CONSTRAINT ...` | `ALTER TABLE users DROP CONSTRAINT users_signup_source_not_null;` | **Reversible.** DROP CONSTRAINT is metadata-only. |

### Scenario B rollback -- critical operational note

If the **original UNSAFE statement** (`ADD COLUMN ... NOT NULL DEFAULT ...`) is dispatched on PG10 and the team realizes mid-rewrite, **do not `pg_cancel_backend` or `pg_terminate_backend` casually**. The rewrite is transactional, so it will roll back cleanly, BUT:
- The rollback itself takes time (proportional to work done so far).
- The `AccessExclusiveLock` is held through the rollback.
- Concurrent queued queries continue piling up.

The least-bad path mid-incident is usually to wait for completion if >50% done, else terminate and accept the queued-query timeout cascade. This is why we classify the forward op as **effectively non-roll-backable mid-flight** for Scenario B.

---

## Irreversible operations requiring user confirmation

None at the SQL level -- both scenarios have catalog-level reverse operations.

**Operational irreversibility flag (Scenario B only):** the forward UNSAFE statement on PG10 cannot be safely cancelled mid-flight without operational pain. This is not "data irreversible" but is "incident irreversible." If the team chooses to ship the UNSAFE shape on PG10 anyway, route to `decision-interview` for explicit acknowledgement that the cluster will be effectively offline for the duration of the rewrite.

---

## Summary verdict

- **Scenario A (PG 15):** SAFE. Ship as written, ideally wrapped with `lock_timeout` for the queueing edge case.
- **Scenario B (PG 10):** UNSAFE. Must be re-sliced into the 4-phase plan above. The single-statement migration as written will cause an extended outage on a 50M-row `users` table.

The same SQL, two verdicts. PG version is load-bearing here, and any audit that didn't cross-reference PG version with the classification + row count would have shipped the PG10 variant and paged the on-call within two minutes.

---

### Artifact changes

- PROPOSED `<task>/MIGRATION_SAFETY.md` -- full audit body above.
- PROPOSED `DECISIONS.md ## Locked decisions` -- D-N (draft): "On PG 10 cluster, `ADD COLUMN NOT NULL DEFAULT` is always re-sliced into 4 phases (nullable add → batched backfill → SET DEFAULT → SET NOT NULL or CHECK NOT VALID + VALIDATE). On PG 11+, the single-statement form is permitted with `lock_timeout` wrapper."
- PROPOSED `TASK_STATE.md ## Risks to watch` -- P0: PG10 cluster will outage on single-statement form; P2: PG15 lock queueing risk during catalog update.
- PROPOSED `IMPLEMENTATION_PLAN.md ## Risks and mitigations` -- mirror P0/P2 with mitigation = 4-phase plan (PG10) / lock_timeout wrapper (PG15).

### Command transcript

1. Parsed 1 statement; produced 2 scenario rows (PG15, PG10) per Step 4 cross-reference rule.
2. Classified as `ADD-COLUMN-NOT-NULL` with constant DEFAULT in both scenarios.
3. Applied PG-version-aware lock duration analysis (Step 4): metadata-only on PG11+, full table rewrite on PG10-.
4. Verdict split: SAFE (A) / UNSAFE (B); produced 4-phase remediation for B.

### Handoff

**Next command:** `decision-interview` -- Scenario B has an operationally irreversible incident risk if shipped as-written; needs explicit user confirmation of the 4-phase plan AND confirmation that the legacy PG10 cluster timeline for upgrade is tracked separately. If only Scenario A is in scope for actual deploy, route to `approve-proposed` instead.

**Run now:** `decision-interview`
