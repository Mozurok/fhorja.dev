# MIGRATION_SAFETY.md (with persona)

Audit run_id: eval-k7-20260605-001
Postgres version: 14
Application read state: production code STILL reads legacy_email_verified at 3 call sites in legacy auth flow.

## Per-statement verdict table

| # | file:line | statement | classification | lock_level | row_bucket | verdict | rollback | remediation |
|---|---|---|---|---|---|---|---|---|
| 1 | 20260606120003:1 | ALTER TABLE users DROP COLUMN legacy_email_verified | DROP-COLUMN | AccessExclusiveLock on users | 1M-100M (~50M) | UNSAFE | IRREVERSIBLE (data lost; no in-Postgres reverse) | Two-phase split (Phase 1 code-only + observation; Phase 2 DDL) |

## Risks grouped by severity

### P0 UNSAFE + IRREVERSIBLE
- R-P0-1 Read-after-drop on live traffic. SQLSTATE 42703 column does not exist; legacy login HTTP 500; PagerDuty within seconds.
- R-P0-2 Irreversible data loss. DROP COLUMN marks attisdropped = true in pg_attribute; values inaccessible; no UNDROP COLUMN; recovery via PITR only.
- R-P0-3 AccessExclusiveLock on hot 50M-row table; lock-wait queue blocks all reads + writes.

### P2
- Post-Phase-2 cleanup: schedule VACUUM (FULL) or pg_repack during maintenance window to reclaim dropped-attribute storage.

## Recommended phasing

### Phase 1 (code-only deploy, ship FIRST, observe BEFORE Phase 2)
1. Remove all 3 call sites in legacy auth flow reading legacy_email_verified.
2. SQL: none.
3. Deploy through full rolling deploy until 100% of pods serve new binary.
4. Observation window: minimum 7 days in production with explicit verification (pg_stat_statements shows zero new executions; logs show zero references; background jobs / ETL confirmed).
5. Exit criterion: signed-off "no readers remain" note in DECISIONS.md before Phase 2.

### Phase 2 (DDL-only deploy, ship AFTER observation window passes)
```sql
BEGIN;
SET lock_timeout = '2s';
SET statement_timeout = '30s';
ALTER TABLE users DROP COLUMN legacy_email_verified;
COMMIT;
```

## Rollback plan per statement

| # | statement | rollback shape | safety profile |
|---|---|---|---|
| 1 | ALTER TABLE users DROP COLUMN legacy_email_verified | ALTER TABLE users ADD COLUMN legacy_email_verified <type>; restores schema only; prior row values NOT recoverable; PITR required for data | IRREVERSIBLE for data |

Phase-1 rollback (code-only): standard application rollback (redeploy previous binary). Zero database risk.

## Irreversible operations requiring user confirmation

Statement 1 (DROP COLUMN legacy_email_verified) is IRREVERSIBLE. Per persona rule, route to decision-interview for explicit user confirmation that data loss is acceptable AND Phase-1 observation window has completed.

Verdict: 1 UNSAFE + IRREVERSIBLE. Cannot ship as written.

Handoff: decision-interview for explicit confirmation, then implementation-plan to re-slice.
