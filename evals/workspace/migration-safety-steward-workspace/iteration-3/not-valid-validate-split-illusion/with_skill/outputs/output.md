# MIGRATION_SAFETY.md -- `add_invoice_amount_check`

**Audit run_id:** mss-2026-06-05-not-valid-validate-split-illusion
**Migration file:** `migrations/20260607130001_add_invoice_amount_check.sql`
**Postgres version:** 14
**Deployment strategy:** single migration, rolling deploy, no maintenance window
**Row count assumptions:** `invoices` ≈ 80M rows (bucket: `1M-100M`, top of bucket)
**Online-DDL tooling:** none in scope
**Pre-flight data audit:** zero existing rows have `amount_cents <= 0` (so the VALIDATE will not raise; it will still scan)

---

## TL;DR -- the split is a comforting illusion as written

The team wrote the canonical `NOT VALID` + `VALIDATE` pattern, but then **packed both statements into a single migration file**. On a rolling deploy with no maintenance window, that collapses the two phases back into one apply window. The `ADD CONSTRAINT ... NOT VALID` is genuinely cheap (≈ ms, metadata-only). The `VALIDATE CONSTRAINT` is NOT cheap on 80M rows: it takes a `ShareUpdateExclusiveLock` on `invoices` for the entire duration of a full table scan -- minutes, not milliseconds -- and during that window **any other `AccessExclusiveLock`-taking DDL on `invoices` is blocked, and itself blocks all reads/writes behind it (lock queue head-of-line blocking)**. The "we're safe because we used NOT VALID + VALIDATE" mental model is wrong unless the two statements live in separate migrations applied at separate times.

**Net verdict: NEEDS-PHASING.** Re-slice into two migrations.

---

## Per-statement verdict table

| # | file:line | statement (abbrev) | classification | lock level | est rows | verdict | rollback | remediation |
|---|---|---|---|---|---|---|---|---|
| S1 | `20260607130001_add_invoice_amount_check.sql:1` | `ALTER TABLE invoices ADD CONSTRAINT invoices_amount_positive CHECK (amount_cents > 0) NOT VALID` | `ADD-CHECK` (NOT VALID variant) | `AccessExclusiveLock` on `invoices`, held for **metadata update only** (sub-second on PG14) | 80M | **SAFE in isolation** | `ALTER TABLE invoices DROP CONSTRAINT invoices_amount_positive;` (metadata-only, safe) | Ship as-is **in its own migration**; see Phase 1 below |
| S2 | `20260607130001_add_invoice_amount_check.sql:2` | `ALTER TABLE invoices VALIDATE CONSTRAINT invoices_amount_positive` | `ADD-CHECK` (VALIDATE phase) | `ShareUpdateExclusiveLock` on `invoices`, held for **full sequential scan of 80M rows** | 80M | **NEEDS-PHASING** when shipped in the same migration as S1; **SAFE** when shipped in a separately scheduled migration during low-traffic window | `ALTER TABLE invoices ALTER CONSTRAINT invoices_amount_positive NOT VALID;` is **not supported for CHECK**; effective rollback is `DROP CONSTRAINT` + re-add `NOT VALID` (metadata-only, safe) | Move to its own migration; see Phase 2 below |

### Why S2 is NEEDS-PHASING and not SAFE

Per persona Step 4 (lock duration risk on 80M rows), the lock-level math the team is implicitly relying on is incomplete. Three independent failure modes co-exist on S2:

1. **Scan duration is not free.** `VALIDATE CONSTRAINT` performs a sequential scan of every live row to prove the predicate holds. On 80M rows of typical `invoices` width, expect **roughly 3–15 minutes** of scan time on commodity Postgres hardware (heavily dependent on row width, fillfactor, cache state, IO budget, autovacuum contention). Pre-flight audit guaranteeing zero violations does NOT shorten the scan -- Postgres still reads every row to prove the negative.
2. **`ShareUpdateExclusiveLock` ≠ "no impact".** Yes, it permits concurrent reads and concurrent DML. It does NOT permit concurrent `ShareUpdateExclusiveLock` or stronger lock acquisitions on the same table -- meaning autovacuum on `invoices` is blocked for the duration, **and any other DDL queued behind it (including a fast `ADD COLUMN`) becomes head-of-line-blocked and in turn blocks the entire read/write path** until the VALIDATE completes. This is the canonical "the migration looked safe in staging and brought down production" failure mode.
3. **Single-migration framing eliminates the abort lever.** Because S1 and S2 are in the same file applied in the same transaction window (or at least the same `migrate` invocation), an operator who notices VALIDATE has been running for 8 minutes and the lock queue is growing has no clean way to abort S2 while keeping S1 -- cancelling the migration may roll back the `NOT VALID` add as well, which is the one piece of value that should be preserved. Splitting the file is what makes the abort lever real.

The `NOT VALID` + `VALIDATE` pattern is "safe" relative to the naïve `ADD CONSTRAINT CHECK` (which would hold `AccessExclusiveLock` for the duration of the full scan, blocking ALL reads and writes). It is NOT safe relative to "I can ship this in one migration on 80M rows during business hours and nothing will happen." The team has earned the weaker lock; they have not earned the right to skip phasing.

---

## Risks grouped by severity

### P0 -- UNSAFE + IRREVERSIBLE
None. The check predicate (`amount_cents > 0`) is non-data-destructive and the constraint is droppable.

### P1 -- NEEDS-PHASING with concrete failure mode
- **P1.1 (S2 head-of-line lock queue):** `VALIDATE CONSTRAINT` holds `ShareUpdateExclusiveLock` on `invoices` for ~3–15 min on 80M rows. **Production symptom:** any concurrent or subsequent DDL on `invoices` (autovacuum included) queues; any normal `SELECT`/`INSERT`/`UPDATE` arriving AFTER a queued `AccessExclusiveLock` waiter is blocked behind that waiter, even though VALIDATE itself would have permitted them. User-visible result: invoice reads and writes stall, latency p99 spikes, request timeouts, PagerDuty within 2–5 minutes depending on traffic shape.
- **P1.2 (autovacuum starvation):** autovacuum on `invoices` is blocked for the VALIDATE duration. **Production symptom:** if the VALIDATE coincides with a vacuum cycle that was already running, the rolling deploy is held until vacuum finishes; if VALIDATE runs first, vacuum is deferred, bloat accumulates, and the next vacuum is more expensive. Cumulative tax on a hot table.
- **P1.3 (no abort lever in single-migration form):** an operator cancelling mid-migration loses S1 as well. **Production symptom:** the team is forced to either let VALIDATE run to completion under load or abandon the constraint entirely; there is no "ship the cheap half, defer the expensive half" path.

### P2 -- SAFE but worth noting
- **P2.1 (S1 metadata lock):** `ADD CONSTRAINT ... NOT VALID` still acquires `AccessExclusiveLock` on `invoices` for the metadata update. Duration is sub-second on PG14 but is not literally zero -- if the table is currently being read by a long-running analytical query holding `AccessShareLock`, S1 will wait, and any newly arriving queries will queue behind S1. Standard mitigation: set `lock_timeout` on the migration session (e.g. `SET lock_timeout = '2s';`) so S1 fails fast and retries rather than head-of-line-blocking the read path.

---

## Recommended phasing

### Phase 1 -- Ship the NOT VALID constraint (migration A)

**File:** `migrations/20260607130001_add_invoice_amount_check_not_valid.sql`

```sql
-- Phase 1: add the constraint in NOT VALID form only.
-- New writes are immediately rejected if amount_cents <= 0.
-- Existing rows are NOT scanned; constraint is marked invalid until Phase 2.
SET lock_timeout = '2s';
ALTER TABLE invoices
  ADD CONSTRAINT invoices_amount_positive CHECK (amount_cents > 0) NOT VALID;
```

**Effect:** sub-second metadata change. New `INSERT`/`UPDATE` traffic is constraint-checked immediately. Existing 80M rows are untouched. `lock_timeout` ensures the migration aborts cleanly if it cannot acquire the brief `AccessExclusiveLock` within 2 seconds (preferable to head-of-line-blocking the read path).

**Observe window between Phase 1 and Phase 2:** at minimum one full business cycle (≥ 24h, ideally ≥ 1 week) to:
- confirm no application code paths are emitting `amount_cents <= 0` (would surface as new write failures in app logs).
- confirm the pre-flight audit's "zero non-positive rows" claim holds against actual write traffic, not a point-in-time snapshot.
- give the operator a clean revert window before paying the scan cost.

### Phase 2 -- VALIDATE during scheduled low-traffic window (migration B)

**File:** `migrations/20260614020000_validate_invoice_amount_check.sql`

```sql
-- Phase 2: validate existing rows. Holds ShareUpdateExclusiveLock on invoices
-- for the duration of a full table scan (~3-15 min on 80M rows).
-- Run during scheduled low-traffic window. Reads/DML continue, but any other
-- DDL or autovacuum on invoices will queue behind this.
SET statement_timeout = '30min';  -- belt-and-braces upper bound
ALTER TABLE invoices VALIDATE CONSTRAINT invoices_amount_positive;
```

**Scheduling constraints:**
- Run during the lowest-traffic window for `invoices` (off-peak based on observed write rate, NOT just "weekend").
- Do not run concurrently with any other DDL on `invoices`, any pg_repack run, any logical replication snapshot, or any autovacuum-triggering bulk load.
- Pre-VALIDATE checklist: confirm no long-running transactions holding any lock on `invoices` (`SELECT pid, state, query_start FROM pg_stat_activity WHERE query ILIKE '%invoices%'`). A long-running `AccessShareLock` reader will not block VALIDATE itself, but it will prevent VALIDATE from completing the lock acquisition cleanly if the reader started before VALIDATE.
- `statement_timeout` is a backstop: if the scan exceeds 30 min the migration aborts and the constraint stays in NOT VALID form (still enforcing new writes -- operationally fine for another window).

**Effect on completion:** constraint flips to VALID. No further action needed; query planner can now use the constraint for predicate elimination.

---

## Rollback plan per statement

| phase | statement | rollback | safety profile |
|---|---|---|---|
| Phase 1 | `ADD CONSTRAINT ... NOT VALID` | `ALTER TABLE invoices DROP CONSTRAINT invoices_amount_positive;` | **Safe.** Metadata-only, sub-second, takes brief `AccessExclusiveLock`. Run with `SET lock_timeout = '2s';`. New writes immediately stop being constraint-checked; previously rejected writes are not retroactively repaired (app must handle). |
| Phase 2 | `VALIDATE CONSTRAINT` | **No direct reverse.** PostgreSQL has no `INVALIDATE CONSTRAINT`. Effective rollback is `DROP CONSTRAINT` + re-add `NOT VALID` -- which is metadata-only and safe, but loses the validated state and forces a future re-VALIDATE if the constraint is desired again. | **Safe but lossy.** Acceptable for incident response; not appropriate as a casual "undo". Flag this in the Phase 2 PR description so the on-call operator knows the cost of rollback before they invoke it. |

**Mid-migration abort:**
- Phase 1: `pg_cancel_backend(pid)` is safe; transaction rolls back cleanly.
- Phase 2: `pg_cancel_backend(pid)` mid-scan is safe (transaction rolls back, constraint stays NOT VALID, no data damage), but the lock queue that built up during the scan will release in dependency order -- expect a brief latency spike as queued writers drain. This is operationally acceptable and is one of the reasons Phase 2 belongs in its own migration with its own scheduled window.

---

## Irreversible operations requiring user confirmation

None. Both phases are reversible (Phase 2's rollback is lossy but safe). No `decision-interview` routing required on data-destructive grounds.

---

## Net recommendation

- **Re-slice the single migration into two migrations** (Phase 1 file + Phase 2 file).
- **Schedule Phase 2 explicitly** -- do not let it ride a normal rolling deploy.
- **Add `SET lock_timeout` to both** as a cheap insurance policy against head-of-line lock-queue incidents.
- **Update the team's mental model:** `NOT VALID` + `VALIDATE` in one file ≠ safe. The safety property comes from the *temporal* split, not the *syntactic* split. The pattern's value is that it *permits* phasing; if you don't take the phasing, you've paid the syntax cost without buying the safety.

Recommended next command: `implementation-plan` to re-slice into the two migrations above with explicit Phase 2 scheduling captured as a slice exit criterion.
