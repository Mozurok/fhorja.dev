# MIGRATION_SAFETY.md -- `add-column-backfill-trigger-side-effect`

- **Audit run_id:** mss-2026-06-05-001
- **Migration files audited:** `migrations/20260607130002_add_user_signup_source.sql` + inline backfill loop in the same slice
- **Postgres version:** 15
- **Deployment strategy:** rolling deploy + oncall-driven backfill script
- **Row count assumptions:** `users` ≈ 50M (bucket `1M-100M`)
- **Side-effect context:** `AFTER UPDATE FOR EACH ROW EXECUTE FUNCTION publish_user_changed_event()` → postgres-kafka-bridge. Baseline ~3,500 events/sec; consumer SLO ≤60s lag, sized for 5,000 events/sec peak.

---

## Per-statement verdict table

| # | Statement (file:line) | Classification | Lock level | Est. rows | Verdict | Rollback | Remediation |
|---|---|---|---|---|---|---|---|
| 1 | `ALTER TABLE users ADD COLUMN signup_source text DEFAULT NULL` (migration:1) | `ADD-COLUMN-NULLABLE` | `AccessExclusiveLock` (held only briefly -- metadata-only on PG15 because default is NULL, no rewrite) | 50M | **SAFE** | `ALTER TABLE users DROP COLUMN signup_source` -- reversible while no reader depends on column | None -- ships as-is |
| 2 | `UPDATE users SET signup_source='organic' WHERE signup_source IS NULL AND id IN (SELECT id FROM users WHERE signup_source IS NULL ORDER BY id LIMIT 10000)` (slice backfill, loop ×~5,000) | `OTHER-DDL` → reclassified `BULK-DML-WITH-TRIGGER-FANOUT` | `RowExclusiveLock` on `users`; per-row `AFTER UPDATE` trigger fires `publish_user_changed_event()` for every row | 50M updates × 1 event each = 50M Kafka emissions | **UNSAFE** | `UPDATE users SET signup_source=NULL WHERE signup_source='organic'` -- *also* fires the trigger 50M more times; rollback is itself unsafe under the same Kafka pressure. Flag `IRREVERSIBLE-IN-PRACTICE` | See `## Recommended phasing` below |

---

## Risks grouped by severity

### P0 -- UNSAFE / IRREVERSIBLE-in-practice

- **R1: AFTER UPDATE trigger fan-out floods Kafka and breaches consumer SLO.**
  - Failure mode: every batched `UPDATE` row fires `publish_user_changed_event()`. With 10,000 rows/batch and the trigger's measured ~80ms cost, a naive sequential batch is ~13 minutes of wall-clock per batch *if the bridge is synchronous in the trigger function*; even if the bridge is async, the trigger still **enqueues 10,000 events into Kafka per batch**.
  - Steady-state Kafka rate during backfill: baseline 3,500 events/sec + backfill emission. If the oncall paces batches at "as fast as possible," peak emission rate easily hits **10–20× the 5,000 events/sec consumer ceiling**.
  - Production symptom: consumer lag breaches the 60s SLO within minutes; downstream consumers (analytics, notifications, search index, anything reading `user.changed`) fall behind by hours; on-call paged for consumer lag; potential Kafka broker disk pressure if retention is short; potential trigger-induced lock contention on `users` because every row's trigger executes inside the same transaction as the `UPDATE`, extending row-lock hold time per batch.
  - Secondary failure: if the postgres-kafka-bridge is *synchronous* inside the trigger function (the 80ms is in-transaction), each 10k batch holds row locks for ~13 minutes → **online write contention on `users` for the duration of every batch**, blocking real user signups and profile edits behind the backfill's row locks.

- **R2: Rollback is not actually a rollback.**
  - The proposed reverse (`UPDATE users SET signup_source=NULL WHERE signup_source='organic'`) fires the trigger another 50M times and re-floods Kafka. There is **no zero-side-effect rollback** for the backfill once it runs through the trigger.
  - Additionally, downstream consumers will have already processed 50M `user.changed` events with a semantic that *did not actually change* (signup_source is a derived/imputed value, not a real user action). Any consumer that treats `user.changed` as "user did something" is now wrong.

### P1 -- NEEDS-PHASING

- **R3: Backfill is bundled into the same slice as the DDL.** The `ADD COLUMN` is safe; the backfill is not. Co-shipping them forces oncall to run the dangerous half right after the safe half, with no observation window.

### P2 -- SAFE but worth noting

- **R4: `ADD COLUMN` itself is metadata-only on PG15 when `DEFAULT NULL`** -- confirmed safe, sub-second `AccessExclusiveLock`. App must not read `signup_source` until backfill completes and the new code path ships (two-phase deploy ordering for the *reader*, not the DDL).

---

## Hidden cost summary (explicit answer to the question)

**No, the batched-backfill plan does NOT account for the trigger cost.** The plan reads as "small batches, gentle on the DB" -- that frame is incomplete. Per Step 4 (lock duration) and Step 5 (follow-the-data including triggers), the real cost surface is:

1. **Trigger fires per row, not per batch.** 10,000 rows = 10,000 trigger executions = 10,000 Kafka publishes per batch.
2. **Total Kafka emissions: ~50M extra events** stacked on top of baseline ~3,500 events/sec production traffic.
3. **Consumer SLO is the binding constraint, not Postgres.** Postgres can survive the writes; the Kafka consumer (sized 5,000 events/sec) cannot survive baseline + backfill emission.
4. **If the bridge is synchronous in the trigger**, row locks are held for the bridge round-trip × 10,000 per batch → online write blocking on `users`.
5. **Rollback also fires the trigger** → no safe reverse exists once the backfill runs as written.

---

## Recommended phasing

Three remediation paths, ranked by safety. Pick **Option A** unless `publish_user_changed_event()` has semantics that *require* downstream notification of backfill rows (it almost certainly does not -- `signup_source='organic'` is an imputed default, not a real user event).

### Option A (RECOMMENDED) -- Disable trigger for the backfill session, audit-log the bypass

Phase 1 -- DDL (safe, ships immediately):
```sql
ALTER TABLE users ADD COLUMN signup_source text DEFAULT NULL;
```

Phase 2 -- Backfill (separate slice, oncall-run, single session):
```sql
BEGIN;
-- Disable the trigger for THIS SESSION ONLY (PG15: session-scoped via session_replication_role)
SET LOCAL session_replication_role = 'replica';
-- ^ This causes row-level triggers marked as ORIGIN (the default) to NOT fire.
-- Verify publish_user_changed_event() is NOT marked ENABLE ALWAYS / ENABLE REPLICA
-- before relying on this; if it is ENABLE ALWAYS, use ALTER TABLE ... DISABLE TRIGGER instead
-- inside a maintenance window (DISABLE TRIGGER takes AccessExclusiveLock briefly).
COMMIT;

-- Then run the batched backfill in the same psql session (so session_replication_role persists):
-- Loop:
UPDATE users
SET signup_source = 'organic'
WHERE id IN (
  SELECT id FROM users
  WHERE signup_source IS NULL
  ORDER BY id
  LIMIT 10000
);
-- repeat until 0 rows affected
```

Phase 3 -- Re-verify trigger is firing for normal traffic after the session closes (sanity check via a no-op user update in staging mirror).

Phase 4 -- Optional: emit ONE synthetic `user.backfill_completed` event downstream so consumers that *did* want to know can react once, not 50M times.

Risk acknowledged: bypassing the trigger means downstream systems never see these 50M `user.changed` events. This is the correct behavior for an imputed default -- downstream consumers should not treat backfilled defaults as user-initiated changes. **Lock this in DECISIONS.md** before running.

### Option B -- Keep trigger firing, pace the backfill to stay under SLO

If downstream consumers MUST receive an event per row (rare; only if `signup_source` participates in real-time personalization or fraud signals):

Available headroom for backfill = 5,000 (consumer capacity) − 3,500 (baseline) = **1,500 events/sec safe budget**. To stay under, with a 30% safety margin: target ~1,000 events/sec from backfill.

```sql
-- Batch size 500, sleep 500ms between batches → ~1,000 events/sec
-- 50M rows / 1,000 events/sec ≈ 14 hours of wall-clock backfill
UPDATE users
SET signup_source = 'organic'
WHERE id IN (
  SELECT id FROM users
  WHERE signup_source IS NULL
  ORDER BY id
  LIMIT 500
);
SELECT pg_sleep(0.5);
-- loop, with a real-time check of consumer lag every N batches:
--   if lag > 30s, double the sleep; if lag < 5s, halve it (within bounds).
```

Plus: monitor `kafka_consumer_lag{topic="user.changed"}` and **auto-pause** the backfill script if lag > 45s (75% of SLO).

### Option C -- Different update path (no trigger fan-out at all)

If `signup_source` semantically should NOT participate in `user.changed` events at all, change the trigger function to skip rows where only `signup_source` changed:

```sql
CREATE OR REPLACE FUNCTION publish_user_changed_event() RETURNS trigger AS $$
BEGIN
  -- Skip backfill-only changes to signup_source
  IF (TG_OP = 'UPDATE'
      AND OLD.signup_source IS DISTINCT FROM NEW.signup_source
      AND OLD.* IS NOT DISTINCT FROM NEW.*::users) THEN
    -- Only signup_source changed; do not publish
    RETURN NEW;
  END IF;
  -- ... existing publish logic ...
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```

This is a `TRIGGER-CHANGE` itself and requires its own two-phase rollout (deploy the new trigger, verify no events lost for real updates, then run backfill).

---

## Rollback plan per statement

| # | Statement | Rollback | Safety profile |
|---|---|---|---|
| 1 | `ADD COLUMN signup_source` | `ALTER TABLE users DROP COLUMN signup_source` | SAFE if shipped before any app code reads the column; metadata-only `AccessExclusiveLock`, sub-second |
| 2 | Backfill `UPDATE` (Option A path) | Not applicable as a SQL reverse -- backfilled value is a default; if needed, set `signup_source=NULL` for affected rows ALSO with `SET LOCAL session_replication_role='replica'` to avoid re-firing the trigger | SAFE only with trigger bypass; UNSAFE without |
| 2 | Backfill `UPDATE` (Option B path, trigger fires) | `UPDATE users SET signup_source=NULL WHERE signup_source='organic'` | **UNSAFE** -- fires 50M trigger events on rollback; rollback re-creates the original problem |

---

## Irreversible operations requiring user confirmation

- **The backfill as currently written is IRREVERSIBLE-in-practice** because the rollback path triggers the same Kafka fan-out as the forward path. Route to `decision-interview` to lock in:
  1. Whether downstream `user.changed` consumers should receive these 50M backfill events (drives Option A vs Option B vs Option C).
  2. Whether the postgres-kafka-bridge inside `publish_user_changed_event()` is synchronous or async (drives whether row locks are held during the bridge round-trip -- this changes the Postgres-side risk profile materially).
  3. Whether `session_replication_role='replica'` is acceptable as the bypass mechanism, or whether the trigger should be modified (Option C) for a cleaner audit trail.

---

### Artifact changes

- `<task>/MIGRATION_SAFETY.md` -- **PROPOSED** (full body above; replaces prior audit if any; prior version archived under `<task>/.wos/migration-safety/mss-2026-06-05-001.md`)
- `DECISIONS.md ## Locked decisions` -- **PROPOSED** D-N: "Backfill of `users.signup_source` runs with `SET LOCAL session_replication_role='replica'` (Option A); downstream `user.changed` consumers are intentionally NOT notified of backfill rows because `signup_source='organic'` is an imputed default, not a user-initiated change. One synthetic `user.backfill_completed` event published at end of run."
- `TASK_STATE.md ## Risks to watch` -- **PROPOSED**: R1 (Kafka SLO breach via trigger fan-out, P0), R2 (no safe rollback once trigger fires, P0), R3 (DDL and backfill bundled in one slice, P1).
- `IMPLEMENTATION_PLAN.md ## Risks and mitigations` -- **PROPOSED**: mirror R1/R2/R3 with mitigation = re-slice into (a) DDL slice, (b) trigger-bypass decision slice routed through `decision-interview`, (c) backfill slice run by oncall in a single psql session with `session_replication_role='replica'`.

### Command transcript

1. Parsed 1 DDL statement + 1 looped DML statement; reclassified the DML as `BULK-DML-WITH-TRIGGER-FANOUT` after Step 5 trigger discovery.
2. Step 4 lock analysis: DDL safe (metadata-only on PG15); DML safe at row-lock level BUT trigger fan-out makes Kafka consumer SLO the binding constraint, not Postgres locks.
3. Step 5 follow-the-data: AFTER UPDATE trigger → postgres-kafka-bridge → 50M extra Kafka events; rollback path fires trigger again → IRREVERSIBLE-in-practice.
4. Verdict: statement 1 SAFE, statement 2 UNSAFE; recommended re-slice + Option A (session-scoped trigger bypass) as primary path.

### Handoff

**Next:** `decision-interview` -- three locked decisions required before any safe backfill path exists (bridge sync/async, downstream notification semantics, bypass mechanism). After that decision lands, run `implementation-plan` to re-slice into DDL / decision / backfill phases. Do NOT run `approve-proposed` until the decision-interview completes -- the proposed DECISIONS.md block above is the *recommended* decision, not a confirmed one.

**Run now:** `decision-interview`
