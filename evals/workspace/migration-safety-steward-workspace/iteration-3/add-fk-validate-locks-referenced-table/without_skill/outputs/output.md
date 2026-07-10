# Migration Audit: `org_members_user_id_fk` → `auth.users`

## TL;DR

The NOT VALID + VALIDATE split is the right pattern for the *referencing* table (`org_members`), but it does **not** protect the *referenced* table. `VALIDATE CONSTRAINT` takes a `ShareUpdateExclusiveLock` on `org_members` **and** a `ShareRowExclusiveLock` on `auth.users`. The lock on `auth.users` blocks concurrent `INSERT`/`UPDATE`/`DELETE` -- i.e. **signups stall for the duration of VALIDATE**. With ~150k users that is typically seconds to tens of seconds, but at 50–200 signups/min on Supabase Auth that is enough to produce visible signup failures, timeouts, and queued auth retries.

---

## 1. Per-Statement Verdict

### Statement 1 -- `ADD CONSTRAINT ... NOT VALID`

```sql
ALTER TABLE org_members
  ADD CONSTRAINT org_members_user_id_fk
  FOREIGN KEY (user_id) REFERENCES auth.users(id)
  NOT VALID;
```

**Verdict: SAFE (with one caveat).**

- On `org_members`: brief `AccessExclusiveLock` to add the catalog entry. No table scan. Milliseconds.
- On `auth.users`: brief `AccessExclusiveLock` as well -- Postgres must attach the action triggers (`RI_FKey_noaction_del`, `RI_FKey_noaction_upd`) to the referenced table. This is fast (catalog-only, no scan) but it *does* momentarily block writes on `auth.users`. Under 50–200 signups/min this is normally invisible (sub-second), but it can deadlock with a long-running transaction on `auth.users`. **Set `lock_timeout` before running.**
- New `INSERT`/`UPDATE` on `org_members` are immediately enforced against the FK from this point on. Existing rows are *not* checked yet.

**Caveat:** if any pre-existing `org_members.user_id` does not exist in `auth.users` (orphans), Statement 2 will fail. You must clean orphans before VALIDATE.

### Statement 2 -- `VALIDATE CONSTRAINT`

```sql
ALTER TABLE org_members
  VALIDATE CONSTRAINT org_members_user_id_fk;
```

**Verdict: UNSAFE as written -- blocks signups on `auth.users`.**

This is the dangerous line in your migration. See lock analysis below.

---

## 2. Lock-Level Analysis During VALIDATE

`VALIDATE CONSTRAINT` for a foreign key is documented as "non-blocking" only with respect to the *referencing* table. The referenced side is a different story.

### On `org_members` (referencing table)

| Lock | Effect |
|---|---|
| `ShareUpdateExclusiveLock` | Blocks: VACUUM FULL, other ALTER TABLE, CREATE INDEX (non-concurrent), other VALIDATE. **Allows:** `SELECT`, `INSERT`, `UPDATE`, `DELETE`. |

Concurrent DML on `org_members` is fine. Good.

### On `auth.users` (referenced table) -- **the problem**

| Lock | Effect |
|---|---|
| `ShareRowExclusiveLock` (also called `RowShareExclusive` in some docs) | Acquired so Postgres can guarantee no row referenced by `org_members.user_id` is modified or deleted while VALIDATE scans. **Blocks `INSERT`, `UPDATE`, `DELETE` on `auth.users`.** Allows `SELECT` and `SELECT ... FOR SHARE`. Self-conflicts with itself, `ExclusiveLock`, `AccessExclusiveLock`, and `RowExclusiveLock` (the lock taken by every `INSERT`/`UPDATE`/`DELETE`). |

This is the exact mechanism: VALIDATE issues a single query of the form `SELECT fk.* FROM org_members fk LEFT JOIN auth.users pk ON fk.user_id = pk.id WHERE pk.id IS NULL` (conceptually), and to make that scan a correct constraint validation, it holds a lock on `auth.users` strong enough to prevent rows from being inserted/updated/deleted underneath it.

**Net result on `auth.users` during VALIDATE:**
- `SELECT` from `auth.users`: OK (logins that only read still work).
- `INSERT` into `auth.users` (**signup**): **BLOCKED -- waits for VALIDATE to finish.**
- `UPDATE` on `auth.users` (password reset, email confirm, last_sign_in_at, MFA enrollment, JWT refresh side effects): **BLOCKED.**
- `DELETE` from `auth.users`: **BLOCKED.**

This is the answer to your direct question: **yes, VALIDATE blocks concurrent signups.**

---

## 3. Signup Impact + Estimated VALIDATE Duration

### Duration estimate

`VALIDATE CONSTRAINT` performs a sequential scan of `org_members` (200k rows) with a lookup into `auth.users` (150k rows, hitting the PK index on `id`). On Supabase managed PG15 with a warm cache:

- **Best case (warm cache, no I/O contention):** 1–5 seconds.
- **Typical:** 5–20 seconds.
- **Worst case (cold cache, busy instance, bloat):** 30–90 seconds.

Whatever the number, it is *not* milliseconds, and the lock on `auth.users` is held the entire time.

### Signup impact at your traffic

- Sustained 50/min ≈ 0.83/sec. A 10-second VALIDATE → ~8 signups queued.
- Peak 200/min ≈ 3.3/sec. A 10-second VALIDATE → ~33 signups queued.
- Supabase GoTrue (Auth) has its own HTTP timeouts (often 10–30 s end-to-end). If VALIDATE runs longer than the GoTrue request timeout, signups don't just queue -- they **fail** with 5xx and bubble up to the client as "could not create user."
- Worse: password resets, email confirms, and refresh-token rotations also write to `auth.users`. So the blast radius is "everything Supabase Auth does that mutates a user row," not just new account creation.
- Rolling deploy + no maintenance window means this lands during live traffic. Expect a visible auth incident.

### Secondary risk: lock queue

Once VALIDATE is waiting (e.g. for an in-flight signup transaction to commit), every subsequent signup INSERT also queues *behind* VALIDATE because `RowExclusiveLock` (INSERT) conflicts with the `ShareRowExclusiveLock` VALIDATE is trying to acquire. This is the classic Postgres "lock queue pileup" -- a single slow transaction on `auth.users` can stretch VALIDATE wait time from seconds into minutes, and *all* signups queue behind it. This is how a "should be 5 seconds" migration becomes a 5-minute auth outage.

---

## 4. Remediation

### Step 0 -- Pre-flight (mandatory)

Check for orphaned `user_id` values before doing anything else, otherwise VALIDATE will fail mid-flight after blocking signups:

```sql
SELECT COUNT(*)
FROM org_members om
LEFT JOIN auth.users u ON u.id = om.user_id
WHERE om.user_id IS NOT NULL AND u.id IS NULL;
```

If non-zero, decide policy (delete orphans, nullify, or reassign) *before* validating.

### Step 1 -- Bound the blast radius with `lock_timeout` and `statement_timeout`

Never run VALIDATE against a hot referenced table without a guard:

```sql
SET lock_timeout = '2s';
SET statement_timeout = '30s';
ALTER TABLE org_members VALIDATE CONSTRAINT org_members_user_id_fk;
RESET statement_timeout;
RESET lock_timeout;
```

If VALIDATE can't acquire the lock within 2 s (something else is holding `auth.users`), it fails fast instead of queueing signups behind it. Retry during a quieter window. This converts a potential outage into a retryable migration error.

### Step 2 -- Run VALIDATE in the quietest window you have

Even without a maintenance window, signup traffic is rarely uniform. Pick the lowest-traffic 5-minute window (typically off-peak by timezone of your user base) and run VALIDATE then. Combined with `lock_timeout`, this is the realistic "no maintenance window" mitigation.

### Step 3 -- Pre-warm and verify duration in a staging clone

Before production:

1. Restore a recent `org_members` + `auth.users` snapshot to a staging Supabase project.
2. Run the exact two statements; measure VALIDATE wall time.
3. That number is your floor -- production will be at least that, usually more.

### Step 4 -- Confirm orphan cleanliness *under load*

Between Step 0 and the actual VALIDATE, new `org_members` rows are already FK-checked (NOT VALID still enforces forward). But you should re-run the orphan query immediately before VALIDATE in case an admin script or a pre-existing nightly job is still inserting unchecked rows from a different path.

### Step 5 -- Optional: drop and re-add as a deferrable constraint if you need rollback safety

Not necessary for correctness, but if you want to be able to "undo" the constraint quickly during the deploy window without another ALTER:

```sql
ALTER TABLE org_members
  ADD CONSTRAINT org_members_user_id_fk
  FOREIGN KEY (user_id) REFERENCES auth.users(id)
  DEFERRABLE INITIALLY IMMEDIATE
  NOT VALID;
```

Doesn't change the VALIDATE lock surface, but gives you a cleaner abort path.

### Step 6 -- Monitor during the run

- Watch `pg_stat_activity` for `wait_event_type = 'Lock'` on `auth.users` while VALIDATE runs.
- Watch your Supabase Auth (GoTrue) error rate and p95 latency in parallel.
- Have the rollback ready: `ALTER TABLE org_members DROP CONSTRAINT org_members_user_id_fk;` releases the lock immediately if you abort.

### What *not* to do

- Don't skip VALIDATE and leave the constraint `NOT VALID` forever -- it stops enforcing on existing rows and confuses the planner about FK-implied row counts. NOT VALID is a transitional state, not a destination.
- Don't try to "speed it up" with parallelism -- VALIDATE is single-process and you can't parallelize it.
- Don't run it inside a larger transaction with other DDL -- you'll hold the `auth.users` lock for the whole transaction, not just the VALIDATE.

---

## Recommended Final Migration

```sql
-- migrations/20260607130003_add_org_member_fk.sql

-- Phase 1: add NOT VALID (safe, near-instant)
ALTER TABLE org_members
  ADD CONSTRAINT org_members_user_id_fk
  FOREIGN KEY (user_id) REFERENCES auth.users(id)
  NOT VALID;

-- Phase 2: validate in a separate migration, with lock guards,
-- run during a low-signup-volume window.
-- Pre-check: confirm zero orphans first.
SET lock_timeout = '2s';
SET statement_timeout = '30s';
ALTER TABLE org_members
  VALIDATE CONSTRAINT org_members_user_id_fk;
RESET statement_timeout;
RESET lock_timeout;
```

Splitting into two separate migration files is recommended so the deploy pipeline can space them out and so a failed VALIDATE can be retried independently without re-running Phase 1.

---

## Summary Table

| Aspect | Statement 1 (ADD NOT VALID) | Statement 2 (VALIDATE) |
|---|---|---|
| Lock on `org_members` | AccessExclusive (brief) | ShareUpdateExclusive (duration of scan) |
| Lock on `auth.users` | AccessExclusive (brief, catalog only) | **ShareRowExclusive (duration of scan)** |
| Blocks signups? | Microseconds -- practically no | **Yes -- entire VALIDATE duration** |
| Duration | < 100 ms | 5–20 s typical, can be longer under load |
| Safe as written? | Yes, with `lock_timeout` | **No -- needs `lock_timeout`, low-traffic window, orphan pre-check** |
