# RLS Tenant Isolation Audit -- `20260606140002_notes_summary_view.sql`

## Executive summary

This migration looks safe at a glance -- `notes` has RLS enabled, `FORCE`d, and policies scoped to `auth.uid()`. The problem is the **materialized view `mv_notes_summary` derived from `notes`**. PostgreSQL **does not apply RLS to materialized views**, and the view was granted `SELECT` directly to the `authenticated` role. The result is a full tenant-isolation bypass: any logged-in user can read every other user's note count and last-note timestamp.

**Concrete scenario answer (U1 issues `SELECT * FROM mv_notes_summary`):**
U1 sees one row per user in the system -- `(user_id, note_count, last_note_at)` for U1, U2, U3, …, U_N. Not just their own row. The `notes_select_own` policy on the base table is irrelevant here, because the materialized view's storage is a snapshot owned by the view's owner (typically `postgres`/superuser), and RLS is not consulted when reading from it.

---

## (1) Per-object posture table

| Object | Kind | RLS enabled? | FORCE RLS? | Policies | Grants (relevant) | Effective posture for `authenticated` |
|---|---|---|---|---|---|---|
| `public.notes` | TABLE | YES | YES | `notes_select_own` (SELECT, `user_id = auth.uid()`), `notes_insert_own` (INSERT, `user_id = auth.uid()`) | None granted in this migration (relies on default Supabase grants to `authenticated` for tables in `public`, mediated by RLS) | SELECT/INSERT restricted to rows where `user_id = auth.uid()`. **No UPDATE / DELETE policy** -- those operations are denied by default under RLS. OK for SELECT/INSERT, but missing posture for UPDATE/DELETE/ALL should be made explicit. |
| `public.mv_notes_summary` | MATERIALIZED VIEW | **N/A -- RLS does not apply to matviews** | N/A | None possible (Postgres doesn't honor RLS on matviews) | `GRANT SELECT ... TO authenticated` | **Every authenticated user can read every row.** Full cross-tenant disclosure of `(user_id, note_count, last_note_at)`. |
| `public.mv_notes_summary_pkey` | UNIQUE INDEX on matview | N/A | N/A | N/A | N/A | Enables `REFRESH MATERIALIZED VIEW CONCURRENTLY`, no isolation impact in itself. |

> Note on views vs. matviews: regular `VIEW`s in Postgres run with the **invoker's** privileges by default (since PG 15, `security_invoker=on` is the safe choice), and base-table RLS applies. **Materialized views do not** -- they are physical relations populated by the matview owner, and RLS on the source table is **bypassed** by every reader of the matview.

---

## (2) Gaps with severity and bypass mechanism

### GAP-1 -- Materialized view leaks all users' aggregates to every authenticated user -- **CRITICAL**

- **Object:** `public.mv_notes_summary`
- **Bypass mechanism:** Materialized views are physical relations populated under the **matview owner's** identity (typically `postgres`, a BYPASSRLS / superuser role). When `authenticated` queries the matview, Postgres consults grants on the matview itself, **not** the RLS policies on `notes`. The `GRANT SELECT ... TO authenticated` then exposes every aggregated row to every signed-in user.
- **Concrete impact:** User U1 running `SELECT * FROM mv_notes_summary` sees `(user_id, note_count, last_note_at)` for **all users** in the database. This discloses (a) the existence and `auth.users.id` of every other user that has notes, (b) how active they are (`note_count`), and (c) when they were last active (`last_note_at`). This is a PII / activity-pattern leak and a user-enumeration vector against `auth.users`.
- **CVSS-ish severity:** Critical. Unauthenticated → no, but **any** signed-in user can pull the entire table. No log signal differentiates malicious enumeration from normal use.
- **Why FORCE RLS on `notes` doesn't help:** `FORCE ROW LEVEL SECURITY` only forces policies to apply to the **table owner** when querying the table. It changes nothing about how matviews are read.

### GAP-2 -- Direct `GRANT SELECT TO authenticated` on a derived aggregate -- **HIGH (root cause of GAP-1)**

- **Object:** `GRANT SELECT ON mv_notes_summary TO authenticated;`
- **Bypass mechanism:** Bypasses the tenant model by giving the authenticated role broad read access to an object the role can never filter against `auth.uid()` itself (Postgres won't push the predicate into the matview's snapshot).
- **Impact:** Same as GAP-1. Listed separately because removing the grant is the *fastest* containment step, even before the architectural fix.

### GAP-3 -- `mv_notes_summary` is never `REFRESH`ed -- **MEDIUM (operability), but reduces leak window in practice only by accident**

- **Object:** `public.mv_notes_summary`
- **Issue:** No `REFRESH MATERIALIZED VIEW` job is defined. Data will be **empty** immediately after this migration (matview is created with `WITH DATA` by default, but `notes` is empty at create time). Over time staleness will mislead callers.
- **Security side-effect:** While the matview is empty, GAP-1 has no payload -- but this is incidental, not a control. The moment `REFRESH` runs (in a scheduled job, a Trigger.dev task, or by hand), the leak becomes real.

### GAP-4 -- `notes` has no UPDATE / DELETE policies, posture is implicit -- **LOW**

- **Object:** `public.notes`
- **Issue:** Under RLS, missing policies = deny. Functionally correct, but reviewers can't tell whether "no UPDATE policy" is intentional or an oversight. Make it explicit (either add `FOR UPDATE USING (user_id = auth.uid()) WITH CHECK (user_id = auth.uid())` or comment that updates are intentionally disallowed).

### GAP-5 -- `user_id` is not foreign-keyed to `auth.users` and has no index -- **LOW**

- **Object:** `public.notes.user_id`
- **Issue:** Two sub-issues:
  1. No `REFERENCES auth.users(id) ON DELETE CASCADE` -- orphan notes possible after user deletion. Not strictly an RLS gap, but cleaning up after a deleted user becomes manual.
  2. No index on `user_id`. Every RLS-filtered query (`WHERE user_id = auth.uid()`) and the matview's `GROUP BY user_id` will scan the table. Performance, not security, but worth fixing in the same migration.

---

## (3) Migration-shaped remediation

Two acceptable strategies. **Recommend Strategy A** (replace the matview with a security-invoker view) unless you have a measured aggregate-query performance need that justifies a snapshot. If you keep the matview, you must wrap reads in a `SECURITY INVOKER` function that filters by `auth.uid()` -- Strategy B.

### Strategy A -- Replace matview with a `security_invoker` view (recommended)

```sql
-- migrations/20260606140100_fix_notes_summary_view.sql

BEGIN;

-- 1. Containment first: revoke the dangerous grant.
REVOKE ALL ON public.mv_notes_summary FROM authenticated, anon, public;

-- 2. Drop the matview. It cannot be filtered by RLS and was the bypass.
DROP MATERIALIZED VIEW IF EXISTS public.mv_notes_summary;

-- 3. Replace with a regular view that runs with the invoker's privileges,
--    so RLS on `notes` is honored when the view is queried.
CREATE VIEW public.notes_summary
WITH (security_invoker = true)         -- Postgres 15+: ensures invoker-RLS
AS
SELECT user_id,
       COUNT(*)         AS note_count,
       MAX(created_at)  AS last_note_at
FROM public.notes
GROUP BY user_id;

-- 4. Grant SELECT to authenticated. RLS on `notes` will scope rows
--    such that each user only sees their own aggregate row.
GRANT SELECT ON public.notes_summary TO authenticated;

-- 5. While we're here: make the implicit deny on update/delete explicit
--    and close the lint gaps.
CREATE POLICY notes_update_own ON public.notes
  FOR UPDATE
  USING (user_id = auth.uid())
  WITH CHECK (user_id = auth.uid());

CREATE POLICY notes_delete_own ON public.notes
  FOR DELETE
  USING (user_id = auth.uid());

-- 6. Performance + integrity hygiene.
CREATE INDEX IF NOT EXISTS notes_user_id_idx ON public.notes (user_id);

-- Optional but recommended: tie notes to auth.users so deletes cascade.
-- Skip if you have application-level ownership semantics.
ALTER TABLE public.notes
  ADD CONSTRAINT notes_user_id_fkey
  FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;

COMMIT;
```

After this, U1's `SELECT * FROM public.notes_summary` returns **exactly one row** -- U1's own -- because the underlying scan of `notes` is filtered by `notes_select_own`.

### Strategy B -- Keep the matview but gate reads through a `SECURITY INVOKER` function

Use only if the aggregate is expensive enough to justify a snapshot and a stale-but-fast read is acceptable.

```sql
-- migrations/20260606140101_fix_notes_summary_matview.sql

BEGIN;

-- 1. Containment: no role outside the owner reads the matview directly.
REVOKE ALL ON public.mv_notes_summary FROM authenticated, anon, public;

-- 2. Gate access through a SECURITY INVOKER function that filters by auth.uid().
CREATE OR REPLACE FUNCTION public.get_my_notes_summary()
RETURNS TABLE (user_id uuid, note_count bigint, last_note_at timestamptz)
LANGUAGE sql
SECURITY INVOKER          -- run as the caller
STABLE
SET search_path = public, pg_temp
AS $$
  SELECT s.user_id, s.note_count, s.last_note_at
  FROM public.mv_notes_summary s
  WHERE s.user_id = auth.uid();
$$;

REVOKE ALL ON FUNCTION public.get_my_notes_summary() FROM public;
GRANT EXECUTE ON FUNCTION public.get_my_notes_summary() TO authenticated;

-- 3. Schedule a refresh (example: Trigger.dev scheduled task, or pg_cron).
--    Example pg_cron entry (if installed):
-- SELECT cron.schedule(
--   'refresh_notes_summary',
--   '*/5 * * * *',
--   $$REFRESH MATERIALIZED VIEW CONCURRENTLY public.mv_notes_summary$$
-- );

COMMIT;
```

Client code then calls `supabase.rpc('get_my_notes_summary')` instead of `from('mv_notes_summary').select()`. The `WHERE user_id = auth.uid()` predicate is the security boundary because the matview itself remains unreadable to `authenticated`.

> Important caveat for Strategy B: a `SECURITY INVOKER` function reading a matview **still does not enforce `notes` RLS** -- the matview is a snapshot, RLS isn't re-evaluated. The filter `user_id = auth.uid()` in the function body is doing all the isolation work. That's why the `REVOKE` in step 1 is non-negotiable: it's the only thing preventing a caller from skipping the function and reading the matview directly.

---

## Follow-the-data summary

| Data flow | Boundary type | Status before fix | Status after Strategy A | Status after Strategy B |
|---|---|---|---|---|
| Client → `notes` (SELECT/INSERT) | RLS policy | Enforced (own rows only) | Enforced + explicit UPDATE/DELETE | Enforced + explicit UPDATE/DELETE |
| Client → `mv_notes_summary` direct read | Grant + (no) RLS | **BYPASS -- all rows** | Object removed | Grant revoked, direct read denied |
| Client → aggregate of own notes | -- | Only via leaky matview | `notes_summary` view, RLS-filtered | `get_my_notes_summary()` RPC, `auth.uid()` filter inside function |
| Refresh path | Owner job | Undefined | N/A (view is live) | pg_cron / Trigger.dev scheduled task |

---

## Reviewer checklist for future RLS migrations touching derived objects

1. For every `CREATE VIEW`: add `WITH (security_invoker = true)` (PG15+). Confirm base tables have RLS.
2. For every `CREATE MATERIALIZED VIEW`: treat it as **public data** by default. Never `GRANT SELECT` to `authenticated`/`anon`. Wrap access in a `SECURITY INVOKER` function that re-applies the tenant predicate, or denormalize the snapshot into a regular table with its own RLS.
3. For every `GRANT` to `authenticated`/`anon` on an object derived from RLS-protected tables: justify in the migration comments why RLS still holds.
4. For every RLS-enabled table: ensure SELECT, INSERT, UPDATE, DELETE postures are all explicitly stated (policy or comment).
5. Index every column referenced by an RLS predicate (`user_id`, `tenant_id`, etc.).
