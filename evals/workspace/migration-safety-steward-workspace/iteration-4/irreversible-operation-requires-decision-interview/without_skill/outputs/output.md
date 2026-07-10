# Migration Audit: `20260608120001_drop_legacy_columns.sql`

## Summary verdict

**DO NOT RUN this migration as written.** All three statements are `DROP COLUMN` operations against a ~10M row `users` table on Postgres 15 with no backup of the column data. Every one of them is structurally irreversible once committed. One of them (`legacy_marketing_consent`) has a known active compliance dependency (LGPD audit). This needs a decision before any implementation plan or approval.

---

## (1) Per-statement verdict

### Statement 1
```sql
ALTER TABLE users DROP COLUMN legacy_signup_referrer;
```
- **Verdict:** BLOCK as-written. Column is unread in app for 6+ months, but "unread by app" is not the same as "unused" -- analytics, BI, exports, or compliance queries outside the app may still read it. No backup exists. Drop is structurally irreversible.
- **Operational risk on 10M rows:** `DROP COLUMN` in Postgres is metadata-only and fast (it does not rewrite the table), so the lock duration itself is short. The risk is data loss, not lock time.

### Statement 2
```sql
ALTER TABLE users DROP COLUMN legacy_acquisition_channel;
```
- **Verdict:** BLOCK as-written. Same reasoning as Statement 1. Marketing/attribution data is the kind of thing finance, growth, and BI typically still consult even when the product code has moved on. Confirm no downstream consumer (warehouse sync, dbt model, CSV export, attribution report) reads it before any drop.

### Statement 3
```sql
ALTER TABLE users DROP COLUMN legacy_marketing_consent;
```
- **Verdict:** HARD BLOCK. This column has a **named, current dependency**: compliance team uses it for LGPD audit responses, referenced in the most recent quarterly audit. Dropping LGPD-relevant consent state without a documented retention/migration path is both a data-loss risk and a regulatory risk (LGPD has data subject access and accountability obligations; you may need to answer "what was this user's consent state on date X" for years).

---

## (2) IRREVERSIBLE flag per statement

| Statement | Irreversible? | Why |
|---|---|---|
| `DROP COLUMN legacy_signup_referrer` | **IRREVERSIBLE** | `DROP COLUMN` discards all values. No backup of the column data exists. Recreating the column gives you `NULL`s, not the original values. |
| `DROP COLUMN legacy_acquisition_channel` | **IRREVERSIBLE** | Same as above. |
| `DROP COLUMN legacy_marketing_consent` | **IRREVERSIBLE + COMPLIANCE-CRITICAL** | Same data-loss reason, plus active LGPD audit dependency. Loss of this column may also prevent answering future regulator or data-subject requests about historical consent state. |

All three should be flagged `IRREVERSIBLE` in the migration review record. The third should additionally be flagged `COMPLIANCE-CRITICAL`.

---

## (3) Rollback per statement

Honest answer: **there is no real rollback for any of these once committed.** Postgres `DROP COLUMN` does not support `ROLLBACK` outside of the same transaction, and once the migration transaction commits, the column values are gone.

What you *can* do per statement:

### Statement 1 -- `legacy_signup_referrer`
- **In-transaction rollback (only window):** wrap migration in `BEGIN; ... ROLLBACK;` during a dry run. Once committed, no rollback.
- **Post-commit "rollback":** `ALTER TABLE users ADD COLUMN legacy_signup_referrer <original_type>;` -- this restores the schema shape only. All values are permanently `NULL`. This is a schema-shaped placeholder, not a real rollback.
- **Only real recovery path:** PITR (point-in-time recovery) of the database to just before the migration, then forward-replay of subsequent writes. Expensive, disruptive, and only viable if WAL retention covers the window.

### Statement 2 -- `legacy_acquisition_channel`
- Same options as Statement 1. Same caveat: re-adding the column restores schema, not data.

### Statement 3 -- `legacy_marketing_consent`
- Same mechanical options as above, but with an added compliance concern: even a successful PITR recovery may not satisfy LGPD if there's a gap window where the data was unavailable to answer a request. Treat this column as having no acceptable rollback at all without prior data preservation.

**Implication:** because rollback is not real, the safety has to come *before* the drop, not after.

---

## (4) Recommended next command

**`decision-interview`** -- not `implementation-plan`, not `approve-proposed`.

Reasoning:
- This is not a plan-shape problem (we know mechanically how to drop a column).
- It is not an approval-shape problem (the migration as written would cause permanent data loss in a compliance-sensitive column).
- It is a decision-shape problem: several policy choices must be made and recorded *before* any safe plan can be written. Different answers change behavior, data integrity, and rollout safety, which is exactly the decision-interview trigger.

### Questions that need answers before this migration can move forward
1. **LGPD retention:** What is the documented retention period for `legacy_marketing_consent`? Is the compliance team aware this drop is proposed, and have they signed off?
2. **Preservation strategy for compliance column:** Before any drop, do we (a) snapshot `users(id, legacy_marketing_consent, updated_at)` into a `users_consent_archive` table with the same retention as audit logs, (b) export to cold storage (S3 + checksum) with documented retrieval SLA, or (c) both?
3. **Confirmed non-use of the other two columns:** Has anyone confirmed `legacy_signup_referrer` and `legacy_acquisition_channel` are unused by *all* downstream consumers (warehouse, BI, dbt, ad-hoc exports, scheduled reports), not just the application code?
4. **Reversibility window:** Are we willing to ship a 2-phase migration -- Phase 1: stop writes / mark deprecated / archive; Phase 2 (weeks later, after observation): actual drop -- instead of a single irreversible step?
5. **Deploy model:** Rolling deploy with no maintenance window means old pods may still reference the columns mid-rollout. Has the application code been verified to not `SELECT *` or otherwise reference these columns in any code path still in production?
6. **Backup posture:** Why does no backup of this data exist, and is that itself an LGPD finding we should fix before doing anything else?

### Safer migration shape to propose after the interview
Once decisions are recorded, a safe plan would typically look like:

1. Archive `legacy_marketing_consent` (and ideally the other two) into a retention-aligned archive table or cold storage, with checksums and a documented restore procedure.
2. Get explicit written sign-off from compliance on (1).
3. Confirm no downstream consumer reads the columns (warehouse + BI + reports + code search).
4. In a first migration, *rename* the columns (e.g. `_deprecated_legacy_marketing_consent`) rather than drop, so any forgotten consumer fails loudly and recoverably.
5. Observe for an agreed window (e.g. 2–4 weeks) across at least one audit cycle.
6. Only then ship the `DROP COLUMN` migration, each statement in its own transaction, after the archive has been verified.

---

## TL;DR

- All three statements: **IRREVERSIBLE**.
- Statement 3 additionally **COMPLIANCE-CRITICAL** (LGPD).
- No real rollback exists once committed; re-adding the column restores shape, not values.
- **Next command: `decision-interview`.** Do not advance to `implementation-plan` or `approve-proposed` until retention, archival, downstream-consumer, and compliance sign-off questions are answered and recorded.