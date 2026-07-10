# RLS Audit: `v_team_project_summary` cross-policy interaction

## TL;DR

U1 **CAN** see rows that leak information about (a) team T2's project `P_T2` and (b) U2's membership in team T2, even though U1 has no membership row in T2 and the `projects` RLS policy on its own correctly hides T2's projects. The leak occurs because the view is a `SECURITY INVOKER`-by-default view but the join condition allows a row keyed on `(team_id = T1, team_member_user_id = U2, project_id = P_T2_FALSE_MATCH...)` -- wait, let me be precise. Re-tracing below.

Re-trace: the join is `JOIN projects p ON p.team_id = tm.team_id`. For U1, `team_members` returns only `(T1, U1)`. So `tm.team_id = T1`. Projects joined are projects where `p.team_id = T1`. P_T2 has `team_id = T2`, so P_T2 does **not** appear for U1 through this exact join.

**However**, the real gap is more subtle and depends on what U1's `team_members` rows look like under U1's policy. Let me audit precisely.

## (1) Per-object posture table

| Object | Type | RLS enabled | FORCE RLS | Policy correctness in isolation | Security barrier? | View security model |
|---|---|---|---|---|---|---|
| `team_members` | table | YES | YES | Correct: returns only rows where `user_id = auth.uid()` | n/a | n/a |
| `projects` | table | YES | YES | Correct: returns projects where caller is in the team | n/a | n/a |
| `v_team_project_summary` | view | n/a | n/a | Inherits RLS of underlying tables when invoker runs the view | NOT declared `security_barrier` | Default: `security_invoker = off` historically, but in Postgres 15+ the view runs with the **definer's** (owner's) rights unless `security_invoker = true` is set -- **this is the critical gap** |

## (2) Gaps with severity

### GAP-1 (CRITICAL): View ownership bypasses RLS on underlying tables

`CREATE VIEW` in Postgres defaults to `security_invoker = false`. That means the view executes as the **view owner** (typically `postgres` or the migration role), not as the authenticated end user. The view owner is almost always a superuser-equivalent role for which `FORCE ROW LEVEL SECURITY` still applies only if the owner is not BYPASSRLS -- but in practice on Supabase, views created in a migration are owned by `postgres`, which **bypasses RLS** on tables it owns.

Concretely, when U1 runs `SELECT * FROM v_team_project_summary`:

- The query planner expands the view as the view owner.
- `team_members` and `projects` are read with the owner's privileges -- **RLS is not evaluated against `auth.uid()`**.
- The `GRANT SELECT ... TO authenticated` only controls whether U1 can call the view at all; it does not re-apply RLS.

**Result for U1:** U1 sees the full cartesian-style join across **every team_member row joined to every project row where team_id matches** -- i.e., U1 sees:
- (a) **YES**, team T2's project `P_T2` appears (joined against `(T2, U2)`).
- (b) **YES**, U2's membership of T2 appears as `team_member_user_id = U2, team_id = T2`.

Both confidentiality boundaries are broken.

**Severity: CRITICAL** -- full cross-tenant data exposure of project budgets and membership graph to any authenticated user.

### GAP-2 (HIGH): Even if `security_invoker = true` were set, no `security_barrier`

If the view is later switched to `security_invoker = true`, RLS on the base tables is evaluated as U1. U1 then sees only `team_members` rows where `user_id = U1` and only `projects` where U1 is in the team -- `P_T2` and U2's T2 membership are correctly filtered.

However, without `security_barrier = true`, a malicious user-supplied `WHERE` clause containing a leaky function (e.g., `WHERE leaky(budget_cents)`) can be pushed down **above** the RLS qual, exfiltrating values from rows that should have been filtered. This is a known qual-pushdown side channel.

**Severity: HIGH**, conditional on GAP-1 being fixed.

### GAP-3 (MEDIUM): Membership graph leak even in single-team case

The view exposes `tm.user_id AS team_member_user_id`. Even with correct RLS, this column lets U1 enumerate every co-member of every team U1 belongs to -- that may be intended, but it is a privacy decision that should be explicit. Combined with GAP-1 it leaks the full membership graph.

## (3) Follow-the-data trace

Tracing one specific row from the underlying tables to U1's result set, under the **current** view definition (no `security_invoker`):

```
Base rows in DB:
  team_members:
    (T1, U1, 'member')
    (T1, U2, 'member')
    (T2, U2, 'member')
  projects:
    (P_T1, T1, 'Alpha', 100000)
    (P_T2, T2, 'Bravo', 999999)   <-- T2-only, should be invisible to U1

Query: U1 -> SELECT * FROM v_team_project_summary;

Step A: Postgres rewrites the view. Because the view has no
        `security_invoker = true`, the underlying scans of
        team_members and projects run as the VIEW OWNER, not as U1.
Step B: Scan of team_members under owner -> RLS NOT enforced ->
        returns ALL three rows: (T1,U1), (T1,U2), (T2,U2).
Step C: Scan of projects under owner -> RLS NOT enforced ->
        returns BOTH projects: (P_T1,T1), (P_T2,T2).
Step D: Join on tm.team_id = p.team_id produces:
        (T1, U1, P_T1, 'Alpha',   100000)
        (T1, U2, P_T1, 'Alpha',   100000)
        (T2, U2, P_T2, 'Bravo',   999999)   <-- LEAKED to U1
Step E: U1 has SELECT on v_team_project_summary -> rows returned as-is.
```

U1 observes the third row. That row reveals:
- (a) project `P_T2` exists in team `T2` and its `budget_cents`,
- (b) user `U2` is a member of team `T2` (a team U1 has no membership in).

Both (a) and (b) are confirmed leaks.

## (4) Migration-shaped remediation

```sql
-- migrations/20260606150002_fix_team_project_summary_view.sql

-- Drop the leaky view (CASCADE only if you understand dependents)
DROP VIEW IF EXISTS v_team_project_summary;

-- Recreate with security_invoker so RLS on team_members and projects
-- is evaluated against the caller's auth.uid().
-- security_barrier prevents leaky qual pushdown.
CREATE VIEW v_team_project_summary
  WITH (security_invoker = true, security_barrier = true)
AS
SELECT
  tm.team_id,
  tm.user_id AS team_member_user_id,
  p.id        AS project_id,
  p.name      AS project_name,
  p.budget_cents
FROM team_members tm
JOIN projects     p ON p.team_id = tm.team_id;

GRANT SELECT ON v_team_project_summary TO authenticated;

-- Defense in depth: ensure the view owner cannot silently bypass RLS
-- on the base tables. FORCE ROW LEVEL SECURITY is already set on both
-- tables in the original migration, which is correct and should stay.

-- Optional hardening: if the membership graph itself is sensitive,
-- redact team_member_user_id when it is not the caller:
--
-- CREATE VIEW v_team_project_summary
--   WITH (security_invoker = true, security_barrier = true)
-- AS
-- SELECT
--   tm.team_id,
--   CASE WHEN tm.user_id = auth.uid() THEN tm.user_id ELSE NULL END
--     AS team_member_user_id,
--   p.id        AS project_id,
--   p.name      AS project_name,
--   p.budget_cents
-- FROM team_members tm
-- JOIN projects     p ON p.team_id = tm.team_id;

-- Verification queries (run as U1 in a test):
--   SELECT * FROM v_team_project_summary;          -- expect only T1 rows
--   SELECT count(*) FROM v_team_project_summary
--     WHERE team_id = 'T2';                        -- expect 0
```

### Post-fix expected behavior for U1

Under the patched view, Step B becomes: scan of `team_members` as U1 -> returns only `(T1, U1)`. Step C: scan of `projects` as U1 -> returns only `(P_T1, T1)` because the `projects_select` policy resolves the IN-subquery against U1's `team_members` rows. The join produces a single row `(T1, U1, P_T1, 'Alpha', 100000)`. P_T2 and U2's T2 membership are no longer observable.

### Notes on FORCE RLS and view owner

`FORCE ROW LEVEL SECURITY` on `team_members` and `projects` forces RLS even when the table owner queries them -- but only for the table owner. Views in Supabase are normally owned by `postgres`, which on managed Supabase has RLS bypass semantics for views unless `security_invoker = true` is set. Always pair `FORCE ROW LEVEL SECURITY` on base tables with `security_invoker = true` on every view that joins multi-tenant tables. This pairing is the load-bearing invariant.
