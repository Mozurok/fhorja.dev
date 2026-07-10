# MIGRATION_SAFETY.md -- Audit

**Migration file:** `migrations/20260608120001_drop_legacy_columns.sql`
**Postgres version:** 15
**Deployment strategy:** Rolling deploy, no maintenance window
**Row count assumption:** `users` ~10M rows (`1M-100M` bucket)
**Backup posture:** NO backup of column data exists
**Application read posture:** Columns UNREAD by app for 6+ months
**External consumer posture:** Compliance team consumes `legacy_marketing_consent` for LGPD audit responses (last quarterly audit referenced it)

---

## Per-statement verdict table

| # | Statement | File:line | Classification | Lock level | Rows bucket | Verdict | IRREVERSIBLE | Rollback |
|---|-----------|-----------|----------------|------------|-------------|---------|--------------|----------|
| S1 | `ALTER TABLE users DROP COLUMN legacy_signup_referrer;` | line 2 | DROP-COLUMN | AccessExclusiveLock (brief; metadata-only on PG15 -- column logically dropped, storage reclaimed on later rewrite) | 1M-100M | NEEDS-PHASING | **YES -- IRREVERSIBLE** | No safe reverse: data is unrecoverable (no backup). Recreating the column yields an empty column, NOT a restore. |
| S2 | `ALTER TABLE users DROP COLUMN legacy_acquisition_channel;` | line 3 | DROP-COLUMN | AccessExclusiveLock (brief; metadata-only on PG15) | 1M-100M | NEEDS-PHASING | **YES -- IRREVERSIBLE** | No safe reverse: data is unrecoverable (no backup). |
| S3 | `ALTER TABLE users DROP COLUMN legacy_marketing_consent;` | line 4 | DROP-COLUMN | AccessExclusiveLock (brief; metadata-only on PG15) | 1M-100M | **UNSAFE** | **YES -- IRREVERSIBLE** | No safe reverse AND active external consumer (compliance / LGPD). Dropping destroys evidence relied upon by the last quarterly audit. |

Notes on lock duration:
- On PG15, `ALTER TABLE … DROP COLUMN` is a catalog-only operation -- the lock is held briefly (milliseconds), not the multi-minute table-rewrite seen in `ALTER TYPE`. The production risk here is NOT lock duration; it is **irreversibility + compliance exposure**.
- Three sequential `ALTER TABLE` statements take three separate AccessExclusiveLocks. Acceptable on a rolling deploy from a locking standpoint.

---

## IRREVERSIBLE flag per statement (Step 5 requirement)

| Statement | IRREVERSIBLE? | Why no safe reverse exists |
|-----------|---------------|----------------------------|
| S1 `DROP COLUMN legacy_signup_referrer` | **YES** | Column data is destroyed at drop. No backup of column data exists. `ALTER TABLE users ADD COLUMN legacy_signup_referrer …` only re-creates an empty column -- the historical signup-referrer values for ~10M users are gone permanently. |
| S2 `DROP COLUMN legacy_acquisition_channel` | **YES** | Same as S1. No backup, no source of truth elsewhere -- value is unrecoverable. |
| S3 `DROP COLUMN legacy_marketing_consent` | **YES -- and load-bearing** | Same physical irreversibility as S1/S2 **plus** an active downstream consumer (compliance / LGPD audits). The "unread by app for 6+ months" signal is misleading: the app is not the only reader. Destruction here may also breach LGPD record-keeping obligations (consent provenance must remain demonstrable). |

Per persona Step 5: all three statements have no safe reverse and **MUST be routed via Handoff to `decision-interview` for explicit user confirmation**, not silently remediated.

---

## Rollback plan per statement

| Statement | Rollback op | Safety profile |
|-----------|-------------|----------------|
| S1 | `ALTER TABLE users ADD COLUMN legacy_signup_referrer <type>;` | **Structurally reversible, semantically irreversible.** Schema restored; data lost forever. |
| S2 | `ALTER TABLE users ADD COLUMN legacy_acquisition_channel <type>;` | Same as S1. Structure-only rollback. |
| S3 | `ALTER TABLE users ADD COLUMN legacy_marketing_consent <type>;` | Same as S1/S2 -- **and** the rollback does not restore LGPD audit evidence. Compliance posture cannot be rolled back. |

There is no operationally meaningful rollback for any of the three statements. A `pg_dump` of the three columns **before** drop is the only mechanism that converts these from IRREVERSIBLE to recoverable.

---

## Risks grouped by severity

### P0 -- UNSAFE + IRREVERSIBLE
- **S3 `DROP COLUMN legacy_marketing_consent`**
  - Failure mode: destruction of LGPD consent evidence relied upon by the compliance team's last quarterly audit.
  - Production symptom: next LGPD audit request cannot be answered; potential regulatory finding; "unread by app" was the wrong signal -- the reader is compliance, out-of-band.
  - No backup exists, so post-hoc reconstruction is impossible.

### P1 -- NEEDS-PHASING with concrete failure mode
- **S1 `DROP COLUMN legacy_signup_referrer`** and **S2 `DROP COLUMN legacy_acquisition_channel`**
  - Failure mode: irreversible data loss with no backup. App read-posture suggests safety, but the same "unread by app" reasoning that turned out to be wrong for S3 may also be wrong for S1/S2 (analytics, BI, finance, growth, legal, data team consumers were not surveyed in the brief).
  - Production symptom: silent loss of marketing-attribution history; downstream BI or attribution queries fail or return empty.

### P2 -- SAFE but worth noting
- (none -- all three statements share the IRREVERSIBLE class.)

---

## Recommended remediation (statement-shaped)

Do **not** ship as a single migration. Re-slice as follows, with `decision-interview` gating the destructive phase:

**Phase 0 -- preservation (mandatory before any DROP):**
```sql
-- Snapshot the three columns into a cold archive table BEFORE any DROP.
CREATE TABLE users_legacy_columns_archive_20260608 AS
SELECT
  id,
  legacy_signup_referrer,
  legacy_acquisition_channel,
  legacy_marketing_consent,
  now() AS archived_at
FROM users;

-- Verify row count parity.
SELECT
  (SELECT count(*) FROM users) AS users_count,
  (SELECT count(*) FROM users_legacy_columns_archive_20260608) AS archive_count;
```

**Phase 1 -- consumer survey + compliance sign-off (out-of-band, blocking):**
- Compliance owner confirms LGPD retention requirement and whether the archive table satisfies it (or whether export to a controlled compliance store is required).
- BI / analytics / data team confirms no downstream dependency on S1/S2.
- Outcome captured as a locked decision in `DECISIONS.md`.

**Phase 2 -- drops (only after Phase 0 + Phase 1 complete):**
```sql
ALTER TABLE users DROP COLUMN legacy_signup_referrer;
ALTER TABLE users DROP COLUMN legacy_acquisition_channel;
ALTER TABLE users DROP COLUMN legacy_marketing_consent;
```

Lock duration on PG15 is acceptable (metadata-only); the rolling deploy does not require a maintenance window for Phase 2 itself. The risk that gates this migration is **irreversibility**, not lock contention.

---

## Recommended next command

**`decision-interview`** -- not `implementation-plan`, not `approve-proposed`.

Rationale per persona Step 5 + Step 6: every statement is IRREVERSIBLE, one is UNSAFE due to a named external consumer (compliance / LGPD), and no backup exists. This is exactly the class of operation the persona requires to be routed for explicit user confirmation rather than silently remediated into a phasing plan. `implementation-plan` is premature until compliance has signed off on whether dropping `legacy_marketing_consent` is permitted at all, and `approve-proposed` is disqualified because the migration is not SAFE.

Decision-interview questions to put to the user:
1. Is the compliance team authorized to release `legacy_marketing_consent` for deletion, or must it be retained (and for how long) under LGPD?
2. Have BI / analytics / finance / data confirmed no downstream dependency on S1 and S2?
3. Is a `users_legacy_columns_archive_20260608` snapshot table an acceptable retention vehicle, or must the data move to a controlled compliance store?
4. Given no backup exists, is the team accepting that "rollback" for these statements means schema-only, not data?

### Handoff

**Verdict distribution:** 1 UNSAFE + 2 NEEDS-PHASING; 3/3 IRREVERSIBLE.
**Run now:** `decision-interview`
**Why:** IRREVERSIBLE operations with a named external consumer (compliance / LGPD) and no backup require explicit user confirmation before any phasing plan is drafted. Routing to `implementation-plan` now would lock in a destructive sequence the user has not authorized.
**Do not run yet:** `implementation-plan` (premature -- gated on decision-interview outcome), `approve-proposed` (disqualified -- not SAFE).