# Migration Audit: `20260606140004_user_profile_overhaul.sql`

**Target:** Postgres 15, `users` table ~25M rows, rolling deploy (no maintenance window), no online-DDL tooling.

---

## 1. Per-Statement Verdict Table

| # | Statement | Classification | Lock Level | Est. Row Count Bucket | Verdict | Rollback | Remediation |
|---|-----------|----------------|------------|-----------------------|---------|----------|-------------|
| S1 | `ALTER TABLE users ADD COLUMN signup_referrer text;` | Schema add, nullable, no default | AccessExclusiveLock (brief, metadata-only in PG11+) | N/A (catalog-only) | **SAFE** | `ALTER TABLE users DROP COLUMN signup_referrer;` | None required. Lock is held only for catalog update; no table rewrite because column is nullable with no default. |
| S2 | `CREATE INDEX idx_users_signup_referrer ON users(signup_referrer);` | Index build (non-concurrent) | ShareLock on table (blocks writes for full build duration) | 25M rows | **NEEDS-PHASING** | `DROP INDEX idx_users_signup_referrer;` | Use `CREATE INDEX CONCURRENTLY` to avoid blocking writes on a 25M-row table. See §3. |
| S3 | `ALTER TABLE users DROP COLUMN legacy_signup_source;` | Schema drop | AccessExclusiveLock (brief, catalog-only; column logically dropped, physical removal deferred) | N/A (catalog-only) | **SAFE** *(but flagged IRREVERSIBLE -- see §4)* | **NONE** -- column data is logically lost the moment this commits. Restore requires PITR / backup restore. | None required for safety, but treat as one-way door. Consider gating behind a final go/no-go check. |
| S4 | `ALTER TABLE users ALTER COLUMN email TYPE varchar(254);` | Type change with length constraint | AccessExclusiveLock held for **full table scan + validation** on 25M rows | 25M rows | **UNSAFE** | `ALTER TABLE users ALTER COLUMN email TYPE text;` (only restores type; if any row was rejected mid-migration the migration would have failed atomically, so no data loss -- but extended downtime is the real risk) | Phase via CHECK constraint with `NOT VALID` → `VALIDATE CONSTRAINT` (online), avoiding the AccessExclusiveLock scan. See §3. |

---

## 2. Risks Grouped by Severity

### P0 -- Production-Blocking

- **S4 will lock `users` for writes AND reads for the entire duration of a 25M-row scan.** `ALTER COLUMN ... TYPE varchar(254)` from `text` requires Postgres to verify every existing row satisfies `length(email) <= 254`. This runs under `AccessExclusiveLock`, which blocks SELECTs, INSERTs, UPDATEs, and DELETEs. On 25M rows this is minutes of full table outage during a rolling deploy with no maintenance window. **This alone is a production incident.**
- **S2 (`CREATE INDEX` without `CONCURRENTLY`) blocks all writes to `users` for the duration of the index build.** On 25M rows this is typically several minutes of write outage. Reads continue, but any app path that writes to `users` (login updates, signups, profile edits) will hang or time out.

### P1 -- High Risk / Operational

- **S3 is irreversible at the DDL layer.** Although the column has been verified unused for 14 days, dropping it commits data destruction. Any rollback requires PITR or backup restore -- not a `DOWN` migration. The 14-day verification mitigates risk, but the irreversibility itself is a P1 operational concern (e.g., what if a forgotten analytics job or BI tool reads it?).
- **Transactional grouping risk.** If all four statements run in a single transaction (default for many migration tools), the AccessExclusiveLock from S4 is held from the moment S1 starts. Even the "safe" statements compound the outage window. Splitting into separate transactions / separate migration files is required.
- **S4 failure mode.** If even one of the 25M email rows exceeds 254 chars, the entire `ALTER TYPE` fails after potentially scanning most of the table -- wasting the lock window and leaving the deploy half-applied if statements are not transactional.

### P2 -- Medium / Hygiene

- **Index on low-cardinality / nullable column (S2).** `signup_referrer` is brand new and will be `NULL` for all 25M existing rows. A b-tree index on a mostly-NULL column has limited query value until backfilled. Consider whether the index is needed at all on day 1, or whether a partial index (`WHERE signup_referrer IS NOT NULL`) is more appropriate.
- **No explicit `lock_timeout` / `statement_timeout` set.** Best practice for any DDL on a hot table is `SET lock_timeout = '2s'` so a blocked DDL fails fast instead of queuing behind transactions and blocking every subsequent query in the lock queue (lock-queue pile-up is a common P0 amplifier).
- **`varchar(254)` vs `text` with CHECK constraint.** `varchar(n)` and `text` are functionally identical in Postgres except for the length check. A `CHECK (length(email) <= 254)` constraint expresses the same invariant and can be added/validated online. The `varchar` type offers no storage or performance benefit here.

---

## 3. Safe Variants (per NEEDS-PHASING / UNSAFE statement)

### S2 -- Replace with `CREATE INDEX CONCURRENTLY`

```sql
-- Must run OUTSIDE a transaction block.
-- Does not block reads or writes; takes longer wall-clock but no outage.
CREATE INDEX CONCURRENTLY idx_users_signup_referrer
  ON users(signup_referrer);

-- Verify success (CONCURRENTLY can leave INVALID indexes on failure):
-- SELECT indexrelid::regclass, indisvalid
--   FROM pg_index
--  WHERE indexrelid = 'idx_users_signup_referrer'::regclass;
-- If indisvalid = false: DROP INDEX CONCURRENTLY idx_users_signup_referrer; then retry.
```

Optional improvement (partial index, since column is NULL for all 25M existing rows):

```sql
CREATE INDEX CONCURRENTLY idx_users_signup_referrer
  ON users(signup_referrer)
  WHERE signup_referrer IS NOT NULL;
```

### S4 -- Replace `ALTER TYPE varchar(254)` with phased CHECK constraint

The goal (enforce `length(email) <= 254`) can be achieved without an AccessExclusiveLock scan by using a CHECK constraint with `NOT VALID`, then validating online.

**Phase 4a -- Add constraint as NOT VALID (fast, catalog-only, brief lock):**

```sql
SET lock_timeout = '2s';
ALTER TABLE users
  ADD CONSTRAINT users_email_length_chk
  CHECK (length(email) <= 254) NOT VALID;
```

This immediately enforces the constraint on all new INSERTs and UPDATEs, with no table scan and no extended lock.

**Phase 4b -- Validate existing rows online (SHARE UPDATE EXCLUSIVE, does not block reads/writes):**

```sql
ALTER TABLE users
  VALIDATE CONSTRAINT users_email_length_chk;
```

`VALIDATE CONSTRAINT` takes only `ShareUpdateExclusiveLock` -- concurrent reads and writes continue. If validation fails, the offending rows can be identified and remediated without holding a global write lock.

**Phase 4c (optional, only if `varchar(254)` is required by an external contract):**

Once the CHECK is validated and you have verified zero rows exceed 254 chars over a stable window, the `ALTER COLUMN TYPE varchar(254)` becomes a much faster operation -- but in Postgres 15 it still re-scans. Generally, **keep the column as `text` and rely on the CHECK constraint**; this is the idiomatic Postgres pattern and avoids the rewrite/scan entirely.

---

## 4. IRREVERSIBLE Flags

- **S3 -- `ALTER TABLE users DROP COLUMN legacy_signup_source;` is IRREVERSIBLE.**
  Once committed, the column's data is unrecoverable through normal DDL. Recovery requires PITR or restoring from a backup taken before the migration. The 14-day no-read verification mitigates the *behavioral* risk but does not make the operation reversible. Recommend: confirm a recent verified backup exists, document the rollback path as "PITR to pre-migration LSN," and consider a final read-traffic check immediately before deploy.

---

## 5. Recommended Deploy Sequence

Split into separate migrations / transactions so the AccessExclusiveLock from any single statement does not amplify into a longer outage:

1. **Migration A (transactional, fast):**
   - `SET lock_timeout = '2s';`
   - S1: `ALTER TABLE users ADD COLUMN signup_referrer text;`
   - S4a: `ALTER TABLE users ADD CONSTRAINT users_email_length_chk CHECK (length(email) <= 254) NOT VALID;`
2. **Migration B (non-transactional, online, slow wall-clock but no outage):**
   - S2 (rewritten): `CREATE INDEX CONCURRENTLY idx_users_signup_referrer ON users(signup_referrer);`
   - S4b: `ALTER TABLE users VALIDATE CONSTRAINT users_email_length_chk;`
3. **Migration C (transactional, fast -- gated behind final go/no-go because IRREVERSIBLE):**
   - `SET lock_timeout = '2s';`
   - S3: `ALTER TABLE users DROP COLUMN legacy_signup_source;`

Every DDL session should run with `SET lock_timeout = '2s'` (or similar small value) to prevent lock-queue pile-ups that would turn a 200ms catalog lock into a multi-minute application stall.

---

## Summary

- **2 statements ship as-written** (S1, S3) -- though S3 is IRREVERSIBLE and should be gated.
- **1 statement needs phasing** (S2 → `CONCURRENTLY`).
- **1 statement is unsafe as written** (S4 → replace with `NOT VALID` CHECK + `VALIDATE`, or skip the type change entirely and rely on the CHECK).
- **Do not run this migration as a single transaction.** Split per the deploy sequence above.
