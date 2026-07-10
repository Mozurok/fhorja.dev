# MIGRATION_SAFETY.md -- add_org_member_fk

- **Audit run_id:** mss-2026-06-05-add-org-member-fk
- **Migration files audited:** `migrations/20260607130003_add_org_member_fk.sql`
- **Postgres version:** Supabase managed PG15
- **Deployment strategy:** cloud-push, rolling deploy, no maintenance window
- **Row-count assumptions:** `org_members` ~200k, `auth.users` ~150k (both bucket `10k–1M`)
- **Workload assumptions:** sustained ~50 signups/min, peaks ~200/min against `auth.users` (writes: INSERT into `auth.users`, plus dependent inserts in `auth.identities`, `auth.sessions`, `auth.refresh_tokens`; reads on login)
- **Online-DDL tooling:** none

---

## Per-statement verdict table

| # | file:line | Statement | Classification | Lock on `org_members` | Lock on `auth.users` (REFERENCED) | Est rows | Verdict | Rollback | Remediation |
|---|---|---|---|---|---|---|---|---|---|
| 1 | `20260607130003_add_org_member_fk.sql:1-4` | `ALTER TABLE org_members ADD CONSTRAINT … FOREIGN KEY (user_id) REFERENCES auth.users(id) NOT VALID` | ADD-FK (declare phase) | `AccessExclusiveLock` on `org_members` (brief, catalog-only -- no scan) | `ShareRowExclusiveLock` on `auth.users` (brief, taken to register the FK referencing it) | 200k / 150k | SAFE | `ALTER TABLE org_members DROP CONSTRAINT org_members_user_id_fk;` (cheap, reversible) | Keep as-is. Ship in its own transaction; do NOT bundle with VALIDATE. |
| 2 | `20260607130003_add_org_member_fk.sql:6-7` | `ALTER TABLE org_members VALIDATE CONSTRAINT org_members_user_id_fk` | ADD-FK (validate phase) | `ShareUpdateExclusiveLock` on `org_members` (blocks DDL + other VALIDATE, allows reads/writes) | **`RowShareLock` on `auth.users`** for the duration of the scan (blocks `ALTER TABLE auth.users` and explicit `LOCK auth.users IN SHARE / EXCLUSIVE / ACCESS EXCLUSIVE`, but does NOT block INSERT/UPDATE/DELETE) | 200k / 150k | SAFE (with caveats below) | `ALTER TABLE org_members ALTER CONSTRAINT … NOT VALID` is NOT supported on FKs; rollback = `DROP CONSTRAINT` then re-add `NOT VALID`. Cheap. | Keep as-is, ship in a separate transaction from statement 1, run during a low-write window, set `statement_timeout` + `lock_timeout` guard rails (see Remediation §). |

---

## Direct answer to the audited question

> **What lock does `VALIDATE CONSTRAINT` take on the REFERENCED `auth.users` table, and does that block concurrent signups?**

- On the **referencing** table (`org_members`): `ShareUpdateExclusiveLock` -- concurrent reads and concurrent DML (INSERT/UPDATE/DELETE on `org_members`) continue to work. Only concurrent DDL / VACUUM FULL / other VALIDATE on `org_members` is blocked.
- On the **referenced** table (`auth.users`): **`RowShareLock`** -- the same lock class an ordinary `SELECT … FOR KEY SHARE` row-lock probe takes at the table level. This is required because PG must guarantee that every `user_id` in `org_members` continues to reference a live row in `auth.users` for the duration of the scan; the table-level `RowShareLock` prevents anyone else from concurrently taking `ShareLock` / `ShareRowExclusiveLock` / `ExclusiveLock` / `AccessExclusiveLock` on `auth.users` (i.e. it blocks DDL on `auth.users`), but **it does NOT block `RowExclusiveLock`**, which is what every `INSERT`, `UPDATE`, and `DELETE` on `auth.users` acquires.
- **Concurrent signups: NOT BLOCKED.** Supabase `auth.users` INSERTs (and the trailing `auth.identities` / `auth.sessions` / `auth.refresh_tokens` writes that GoTrue performs on signup) take `RowExclusiveLock` on those tables, which is compatible with the `RowShareLock` that `VALIDATE` holds on `auth.users`. The PG lock conflict matrix confirms `RowShareLock` ↔ `RowExclusiveLock` do **not** conflict.

**Caveats that can still degrade signups even though the lock matrix says "compatible":**

1. **Per-row `KEY SHARE` locks on `auth.users.id` during the scan.** `VALIDATE` of an FK to `auth.users(id)` internally does the equivalent of `SELECT 1 FROM auth.users WHERE id = $org_members.user_id FOR KEY SHARE` for every distinct referenced row. Those row-level `KEY SHARE` locks DO conflict with concurrent row-level `FOR UPDATE` / `FOR NO KEY UPDATE` taken by GoTrue when it mutates a referenced user (e.g. `UPDATE auth.users SET last_sign_in_at = …` during login, password reset, email confirmation). A login burst that hits the same `auth.users.id` rows the validator is currently scanning will see **transient lock waits**, not failures, but visible as elevated p95/p99 latency on the auth path for the duration of the scan.
2. **DDL on `auth.users` is blocked.** Any concurrent Supabase platform migration that does `ALTER TABLE auth.users …` (rare but real -- GoTrue ships schema changes occasionally) will queue behind the `RowShareLock` until VALIDATE finishes. On Supabase-managed PG you do not control GoTrue rollout timing.
3. **Estimated VALIDATE duration:** ~200k rows in `org_members`, one indexed `auth.users.id` lookup each. On Supabase shared-tier disk, expect **~1–6 seconds** wall clock under load, ~sub-second on an idle cluster. Not minutes -- `auth.users` is small and `id` is the PK so each probe is an index-only-ish lookup. The duration risk is in the queueing behind the `RowShareLock`, not the scan itself.
4. **Hidden full-table scan on `org_members`.** VALIDATE scans every row in `org_members` to confirm each `user_id` resolves. With 200k rows this is cheap, but it does sustained read I/O for the duration; if `org_members` is hot, expect minor read-side contention.

---

## Risks grouped by severity

### P0 (UNSAFE + IRREVERSIBLE)
- None. The migration uses the canonical `NOT VALID` + `VALIDATE` split, and the referenced-side lock is row-share (compatible with signup writes).

### P1 (NEEDS-PHASING with concrete failure mode)
- **R1 -- orphaned `org_members.user_id` rows will fail VALIDATE atomically.** `VALIDATE CONSTRAINT` is all-or-nothing: a single `org_members.user_id` that no longer exists in `auth.users` (e.g. a hard-deleted user; Supabase soft-deletes by default but admin SQL deletes are possible) aborts the entire VALIDATE with `ERROR: insert or update on table "org_members" violates foreign key constraint`. Production symptom: migration fails at the VALIDATE step, leaving the FK in `NOT VALID` state indefinitely; new INSERTs are already being checked (NOT VALID only skips the back-check, not the forward-check), so the FK is partially live and the operator may not notice until the next migration attempt.

### P2 (SAFE but worth noting)
- **R2 -- VALIDATE in the same transaction as the NOT VALID add.** The audited file ships both `ALTER TABLE` statements back-to-back without `BEGIN; COMMIT;` boundaries shown. Most migration runners (Supabase CLI, dbmate, sqitch) wrap each file in a single transaction by default. If VALIDATE fails (see R1) the NOT VALID add rolls back too -- the operator loses the partial progress and must re-run from scratch. Split into two migration files to make the failure mode survivable.
- **R3 -- auth-path p99 latency spike during VALIDATE.** Transient per-row lock waits between VALIDATE's `KEY SHARE` and GoTrue's `FOR NO KEY UPDATE` on hot `auth.users` rows will elevate signup/login p99 for the ~1–6s VALIDATE window. Not user-visible at 50/min; potentially user-visible at 200/min peak. Run VALIDATE during a known trough.

---

## Recommended phasing

**Phase 1 -- Pre-flight orphan check (read-only, no lock):**
```sql
-- run as a query, not a migration; abort phasing if rows returned
SELECT om.user_id, COUNT(*) AS orphan_count
FROM org_members om
LEFT JOIN auth.users u ON u.id = om.user_id
WHERE u.id IS NULL
GROUP BY om.user_id;
```
If this returns rows, remediate the orphans (delete or repoint) BEFORE attempting VALIDATE. This collapses R1 from "migration aborts in production" to "migration is known-good before it runs".

**Phase 2 -- Declare the FK (separate migration file):**
```sql
-- migrations/20260607130003_add_org_member_fk_declare.sql
BEGIN;
SET lock_timeout = '2s';
ALTER TABLE org_members
  ADD CONSTRAINT org_members_user_id_fk
  FOREIGN KEY (user_id) REFERENCES auth.users(id)
  NOT VALID;
COMMIT;
```
- `lock_timeout` bounds the brief `AccessExclusiveLock` on `org_members` so a stuck connection doesn't queue signup-adjacent writes (e.g. INSERTs into `org_members` itself) behind it.
- New INSERTs on `org_members` are FK-checked from this point forward.

**Phase 3 -- Validate during a low-write window (separate migration file):**
```sql
-- migrations/20260607130004_add_org_member_fk_validate.sql
SET lock_timeout = '5s';
SET statement_timeout = '5min';
ALTER TABLE org_members VALIDATE CONSTRAINT org_members_user_id_fk;
```
- `lock_timeout = 5s` ensures we don't sit on `RowShareLock` on `auth.users` indefinitely if a concurrent Supabase platform DDL is queued.
- `statement_timeout = 5min` is a defensive ceiling; actual expected duration is 1–6 s.
- Schedule for the daily signup trough (use Trigger.dev `schedules.task` if a programmatic window is needed -- out of scope for this audit).
- Do NOT bundle this with other DDL in the same transaction -- keep it isolated so a retry is cheap.

**Why two files, not one:** if VALIDATE fails (R1), Phase 2's NOT VALID FK survives and continues to enforce forward inserts; the operator only re-runs Phase 3 after fixing orphans. A single file would roll the NOT VALID add back on VALIDATE failure.

---

## Rollback plan per statement

| # | Statement | Rollback | Safety profile |
|---|---|---|---|
| 1 | NOT VALID add | `ALTER TABLE org_members DROP CONSTRAINT org_members_user_id_fk;` | SAFE -- brief `AccessExclusiveLock` on `org_members`, no scan, no impact on `auth.users` |
| 2 | VALIDATE | Constraint cannot be reverted to NOT VALID in place. Rollback = `ALTER TABLE org_members DROP CONSTRAINT org_members_user_id_fk;` then re-issue Phase 2. | SAFE but lossy -- drops the validated state; re-VALIDATE will re-scan. No data loss. |

---

## Irreversible operations requiring user confirmation
- None. Both statements are fully reversible via `DROP CONSTRAINT`.

---

## Bottom line for the audited question

The lock `VALIDATE` takes on `auth.users` is **`RowShareLock` at the table level** plus **per-referenced-row `KEY SHARE` locks** during the scan. Per the Postgres lock matrix, this **does NOT block signups** (which take `RowExclusiveLock` on `auth.users` and `FOR NO KEY UPDATE` on individual rows, both compatible with `RowShareLock` / `KEY SHARE`). What it CAN do is (a) queue any concurrent `ALTER TABLE auth.users` from the Supabase platform behind it, and (b) cause brief per-row lock waits when GoTrue updates a hot `auth.users` row (e.g. `last_sign_in_at`) that the validator is currently probing -- visible as p99 latency, not errors. Estimated VALIDATE duration on a 200k-row referencing table against a 150k-row referenced PK is ~1–6 seconds. Verdict: **SAFE**, but ship as two separate migration files with `lock_timeout` / `statement_timeout` guards and a pre-flight orphan check, per the phasing above.

---

### Artifact changes
- `<task>/MIGRATION_SAFETY.md` -- PROPOSED (full content above)
- `<task>/DECISIONS.md` -- PROPOSED add under `## Locked decisions`:
  > **D-N (PROPOSED): FK add via two-file NOT VALID → VALIDATE split with pre-flight orphan check.** Phase 1 reads orphans; Phase 2 declares FK NOT VALID with `lock_timeout=2s`; Phase 3 validates with `lock_timeout=5s` + `statement_timeout=5min` during the daily signup trough. Rollback = `DROP CONSTRAINT`. Rationale: VALIDATE takes only `RowShareLock` on `auth.users` (signup-compatible) but transactional bundling of declare + validate makes orphan-induced failures non-survivable.
- `<task>/TASK_STATE.md ## Risks to watch` -- PROPOSED add:
  > **R1 (P1):** `org_members` may contain orphaned `user_id` rows; VALIDATE aborts atomically if any exist. Mitigation: pre-flight orphan query before Phase 3.
  > **R3 (P2):** auth-path p99 latency spike during the ~1–6s VALIDATE window from per-row `KEY SHARE` vs `FOR NO KEY UPDATE` contention on hot `auth.users` rows. Mitigation: run Phase 3 during signup trough.
- `<task>/IMPLEMENTATION_PLAN.md ## Risks and mitigations` -- PROPOSED mirror of R1 and R3 with mitigation = the three-phase plan above.

### Command transcript
1. Parsed 2 DDL statements from `20260607130003_add_org_member_fk.sql`.
2. Classified both as ADD-FK (declare + validate phases); cross-referenced PG15 lock matrix for referenced-side `RowShareLock`.
3. Verdict: SAFE on both, with P1 phasing recommendation (split into two files + pre-flight orphan check) to make the failure mode survivable.

### Handoff
**Run now:** `approve-proposed` to persist `MIGRATION_SAFETY.md` and the PROPOSED blocks in DECISIONS / TASK_STATE / IMPLEMENTATION_PLAN, then `implementation-plan` to re-slice the migration into the three-file phasing above.
**Mode:** Plan (no code yet -- re-slicing is plan-level).
**Why:** All statements verdict SAFE; the only required action is splitting the file boundary + adding the orphan pre-flight, which is a plan re-slice, not a rewrite.