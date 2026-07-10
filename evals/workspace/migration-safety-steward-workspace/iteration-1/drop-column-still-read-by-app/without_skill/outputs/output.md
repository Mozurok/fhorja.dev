# Migration Audit: 20260606120003_drop_legacy_email.sql

## 1. Per-Statement Verdict

Statement: ALTER TABLE users DROP COLUMN legacy_email_verified
Verdict: BLOCK / DO NOT SHIP / P0

Three independent failure modes:
1. Backward-incompatibility with running code (3 call sites still read the column).
2. AccessExclusiveLock profile on a 50M-row table (lock queue stampede).
3. IRREVERSIBLE data loss.

## 2. Reversibility Classification

IRREVERSIBLE (data-destructive). The DDL itself is logically reversible (ADD COLUMN restores schema), but the data is permanently lost from the live database. Recovery requires PITR from backups.

## 3. Phased Remediation (NEEDS-PHASING)

Phase 0 -- Snapshot. CREATE TABLE users_legacy_email_archive AS SELECT id, legacy_email_verified FROM users;
Phase 1 -- Code removal. Ship a backend release that no longer reads legacy_email_verified at the 3 call sites.
Phase 2 -- Soak. Leave the column in place for at least the rollback window (typically 7-14 days). Verify and observe.
Phase 3 -- DROP. Run the ALTER TABLE ... DROP COLUMN wrapped with SET lock_timeout = '2s'.

## 4. Two-Phase Deploy Strategy

| Phase | App version | Schema | Reads legacy_email_verified? |
|-------|-------------|--------|-------------------------------|
| P1    | N           | column present | yes (legacy flow) |
| P2    | N+1         | column present | no (call sites removed) |
| P3    | N+1 (soak)  | column present | no |
| P4    | N+1         | column dropped | no |

## 5. Rollback Plan & Data-Recovery

Rolling back P4 (post-drop):
- DDL: ALTER TABLE users ADD COLUMN legacy_email_verified boolean; (instant)
- Data: must be repopulated from users_legacy_email_archive via batched UPDATE FROM (10k-row chunks).

No archive table = no recovery path. Refuse to ship without verifying archive exists.
