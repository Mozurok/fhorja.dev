# RLS + Auth Boundary Audit -- `20260606150001_team_projects.sql`

**Auth model:** `auth.uid()` (default Supabase JWT)
**Tenant scope:** per-team (compound via `team_members`)
**Aggregate verdict:** **FAIL** (one P1 in the view, one P1 latent in `projects` via the same join shape)

---

## 1. Tenant-scoped table / object inventory

- `team_members` -- compound tenant scope (per-team, per-user). Membership table.
- `projects` -- per-team tenant scope.
- `v_team_project_summary` -- VIEW joining the two; inherits the most permissive caller's policy chain, NOT the intersection.

No table from the migration diff is omitted. The VIEW is treated as a first-class object because it is the user-facing query surface (`GRANT SELECT ... TO authenticated`).

---

## 2. Per-object policy posture table

| Object | RLS enabled | FORCE applied | SELECT policy | INSERT (USING+CHECK) | UPDATE (USING+CHECK) | DELETE | Tenant predicate present | Verdict |
|---|---|---|---|---|---|---|---|---|
| `team_members` | Yes | Yes | `user_id = auth.uid()` | **missing** | **missing** | **missing** | Yes (self-row only) | **GAP** (missing write policies -- P2; locks table for writes via authenticated role but service_role bypass blast radius applies) |
| `projects` | Yes | Yes | `team_id IN (SELECT team_id FROM team_members WHERE user_id = auth.uid())` | **missing** | **missing** | **missing** | Yes (via subquery) | **FAIL** (P1 via VIEW join -- see §3) |
| `v_team_project_summary` | **N/A -- view has no `security_invoker`** | N/A | inherits view-owner privileges by default in PostgreSQL | N/A | N/A | N/A | **NO -- the JOIN side leaks** | **FAIL** (P1 -- see §3.1) |

---

## 3. Gaps and severities

### 3.1 GAP-1 (P1) -- VIEW created without `security_invoker = true`: view runs with OWNER's rights, bypassing RLS entirely

**Concrete failure mode.** In PostgreSQL ≤ 14, and in PG 15+ when `security_invoker` is NOT set on `CREATE VIEW`, a view executes with the privileges of the view's OWNER (here the migration runner -- typically `postgres` / table-owner role). The view owner is not subject to RLS on the underlying tables in their own session, and the policies on `team_members` and `projects` are evaluated AS THE OWNER, not as `auth.uid()`. Result: `auth.uid()` inside the underlying policy subqueries resolves to the OWNER's session (typically NULL or the role identity), the subquery `WHERE user_id = auth.uid()` returns zero rows, and on most Supabase installs the practical outcome is one of two equally bad states:

- **State A (policy returns empty):** the view returns no rows for any caller. Looks "safe," masks the second bug, fails silently in product.
- **State B (Supabase's typical postgres role with `bypassrls`):** the view returns **all rows from both tables**, fully unscoped. U1 sees every team's projects and every user's memberships. This is the realistic outcome on a default Supabase project where the migration role has `BYPASSRLS`.

Severity **P1**: tenant isolation is broken at the query surface that was explicitly granted to `authenticated`.

### 3.2 GAP-2 (P1, conditional on GAP-1 fix) -- Even with `security_invoker = true`, the JOIN leaks rows from `team_members` that the caller's own `team_members` policy would have hidden

**Concrete failure mode.** Assume GAP-1 is fixed (view marked `security_invoker = true`) so policies on the base tables ARE evaluated as the caller. Trace the row that materializes for U1:

The view body is `FROM team_members tm JOIN projects p ON p.team_id = tm.team_id`.

For each candidate row, two policy chains run:

1. `team_members tm` filtered by `team_members_select`: `tm.user_id = auth.uid()` -- i.e. `tm.user_id = U1`. So the LEFT side of the join only emits U1's own memberships. Good.
2. `projects p` filtered by `projects_select`: `p.team_id IN (SELECT team_id FROM team_members WHERE user_id = auth.uid())` -- i.e. p.team_id must be in U1's teams. So the RIGHT side only emits projects in U1's teams. Good.

So far the JOIN looks tight: U1 cannot see T2's projects, and U1 cannot see U2's membership in T2. This part is actually safe under `security_invoker = true`.

**But the subquery inside `projects_select` is the leak.** When PostgreSQL evaluates `team_id IN (SELECT team_id FROM team_members WHERE user_id = auth.uid())`, the inner `SELECT team_id FROM team_members` is filtered by `team_members_select` (USING `user_id = auth.uid()`) -- which restricts the inner read to U1's own memberships. That part is correct.

The real P1 surfaces when an attacker writes a sibling view, a `SECURITY DEFINER` helper, or even just a `SELECT ... FROM projects p JOIN team_members tm ON tm.team_id = p.team_id` directly from `authenticated`:

- `projects_select` admits `p` if `p.team_id` is in U1's teams.
- `team_members_select` independently filters `tm` to rows where `tm.user_id = U1`.
- So the JOIN result still respects isolation **for this exact view shape**.

The latent P1 is in `projects_select`'s **shape**, not this view's output: the policy decides project visibility based on a subquery over `team_members`, but `team_members` has NO `WITH CHECK` clause and NO write policies. An attacker with the ability to INSERT into `team_members` (which, because no INSERT policy exists and `FORCE ROW LEVEL SECURITY` blocks all writes from non-owners, currently fails closed) could promote themselves into any team and then read all that team's projects. The CURRENT migration locks writes by accident (no policy = deny under FORCE), but the next migration that adds `INSERT` policies must scope `WITH CHECK` to prevent self-promotion. Flagging now because the shape invites the bug.

**Net answer to the scenario question:** with GAP-1 unfixed (the realistic Supabase default), U1 sees **both** (a) T2's projects AND (b) U2's T2 membership -- full leak. With GAP-1 fixed (`security_invoker = true`), U1 sees neither (a) nor (b) for this view -- the join is safe -- but GAP-2 remains as a latent P1 against future write-policy additions.

### 3.3 GAP-3 (P2) -- `team_members` and `projects` have no `INSERT` / `UPDATE` / `DELETE` policies

Because `FORCE ROW LEVEL SECURITY` is on and no write policy exists, writes from `authenticated` and `anon` fail closed. This is safe today, but service_role bypass still applies, and any future migration that adds write policies must carry the tenant predicate in `WITH CHECK`. Severity **P2** (latent, not exploitable today).

### 3.4 GAP-4 (P2) -- `GRANT SELECT ... TO authenticated` on a view without `security_invoker` is the canonical Supabase footgun

This is the same bug as GAP-1 from the grant side. Calling it out separately because the remediation is in the GRANT/view DDL combination, not just the view body.

---

## 4. Follow-the-data trace

- `team_members` → `team_members_select` USING `user_id = auth.uid()`: row visible to U1 only when `user_id = U1`. **PASS** at the base table.
- `projects` → `projects_select` USING `team_id IN (SELECT team_id FROM team_members WHERE user_id = auth.uid())`: row visible to U1 only when U1 is in `p.team_id`. **PASS** at the base table (relies on `team_members_select` filtering the subquery -- confirmed).
- `team_members` → `v_team_project_summary` (left side of JOIN): under default `CREATE VIEW` semantics, RLS on `team_members` is evaluated as the view OWNER, not the caller. **FAIL -- P1 (GAP-1)**.
- `projects` → `v_team_project_summary` (right side of JOIN): same view-owner bypass. **FAIL -- P1 (GAP-1)**.
- `v_team_project_summary` → `GRANT SELECT ... TO authenticated`: surfaces the unprotected join to every logged-in user. **FAIL -- P1 (GAP-4, same root as GAP-1)**.
- Cross-row materialization trace for U1's `SELECT * FROM v_team_project_summary`:
  - Without `security_invoker`: the join is computed as OWNER → emits `(T1, U1, P_T1)`, `(T1, U2, P_T1)`, `(T2, U2, P_T2)`. U1 sees U2's T2 membership AND T2's project P_T2. **Leak confirmed.**
  - With `security_invoker = true`: `tm` filtered to `{(T1, U1)}` for caller U1, `p` filtered to T1's projects only. Join emits `(T1, U1, P_T1)` only. **Safe.**

No materialized views, audit tables, soft-delete shadow tables, or `SECURITY DEFINER` functions in the diff.

---

## 5. SECURITY DEFINER function audit

None present in this migration. Nothing to flag.

---

## 6. service_role usage audit

Out of scope of this single migration (no backend code in the diff). Flagging operationally: any service_role caller that hits `v_team_project_summary` after GAP-1 is fixed is fine; any caller that hits the underlying tables bypasses RLS by design and must validate the caller's `team_id` server-side before returning rows.

---

## 7. Migration-shaped remediation

```sql
-- Fix GAP-1 / GAP-4: recreate the view with security_invoker so RLS on
-- team_members and projects is evaluated as the calling user, not the view owner.
DROP VIEW IF EXISTS v_team_project_summary;

CREATE VIEW v_team_project_summary
WITH (security_invoker = true) AS
SELECT
  tm.team_id,
  tm.user_id AS team_member_user_id,
  p.id       AS project_id,
  p.name     AS project_name,
  p.budget_cents
FROM team_members tm
JOIN projects p ON p.team_id = tm.team_id;

GRANT SELECT ON v_team_project_summary TO authenticated;
REVOKE ALL ON v_team_project_summary FROM anon;

-- Fix GAP-3 (preemptive): add write policies that carry the tenant predicate
-- in WITH CHECK so future code paths cannot self-promote into teams or
-- create projects in teams the caller is not a member of.

CREATE POLICY team_members_insert ON team_members
  FOR INSERT TO authenticated
  WITH CHECK (
    -- Only an existing admin of the target team can add members.
    EXISTS (
      SELECT 1 FROM team_members existing
      WHERE existing.team_id = team_members.team_id
        AND existing.user_id = auth.uid()
        AND existing.role = 'admin'
    )
  );

CREATE POLICY team_members_update ON team_members
  FOR UPDATE TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM team_members existing
      WHERE existing.team_id = team_members.team_id
        AND existing.user_id = auth.uid()
        AND existing.role = 'admin'
    )
  )
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM team_members existing
      WHERE existing.team_id = team_members.team_id
        AND existing.user_id = auth.uid()
        AND existing.role = 'admin'
    )
  );

CREATE POLICY team_members_delete ON team_members
  FOR DELETE TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM team_members existing
      WHERE existing.team_id = team_members.team_id
        AND existing.user_id = auth.uid()
        AND existing.role = 'admin'
    )
    OR user_id = auth.uid()  -- a member can remove themselves
  );

CREATE POLICY projects_insert ON projects
  FOR INSERT TO authenticated
  WITH CHECK (
    team_id IN (SELECT team_id FROM team_members WHERE user_id = auth.uid())
  );

CREATE POLICY projects_update ON projects
  FOR UPDATE TO authenticated
  USING (
    team_id IN (SELECT team_id FROM team_members WHERE user_id = auth.uid())
  )
  WITH CHECK (
    team_id IN (SELECT team_id FROM team_members WHERE user_id = auth.uid())
  );

CREATE POLICY projects_delete ON projects
  FOR DELETE TO authenticated
  USING (
    team_id IN (SELECT team_id FROM team_members WHERE user_id = auth.uid())
  );
```

Notes on the remediation:

- `WITH (security_invoker = true)` requires PostgreSQL 15+. Supabase's hosted Postgres is ≥ 15. If you target an older base, use a `SECURITY INVOKER` function returning a TABLE instead, or wrap the join in a policy-bearing table rather than a view.
- The `team_members_insert` policy intentionally blocks self-insertion into a team the caller is not already an admin of -- that's the bootstrap problem to resolve via a separate `create_team` RPC that runs as `SECURITY DEFINER` with explicit `auth.uid()` validation. Flagging as a follow-up decision, not adding here.
- `REVOKE ALL ON ... FROM anon` is defensive; `authenticated` is the only role that should reach this view.

---

## 8. Direct answer to the posed scenario

U1 issues `SELECT * FROM v_team_project_summary` from a supabase-js client (which sends U1's JWT, so `auth.uid()` = U1 inside RLS-evaluated contexts):

- **As written (no `security_invoker`):** on a default Supabase install where the migration owner has `BYPASSRLS`, U1 sees **every row of the cartesian join** -- including `(T2, U2, P_T2, ...)`. U1 observes **(a) T2's projects YES** and **(b) U2's T2 membership YES**. Full cross-tenant leak through the view, even though each base-table policy is correct in isolation.
- **After remediation (`security_invoker = true`):** policies on `team_members` and `projects` evaluate as U1. The left side of the join emits only `(T1, U1)`. The right side emits only T1's projects. Result for U1: only rows about teams U1 is a member of, only projects in those teams. **(a) NO, (b) NO.** Safe.

The gap is in the **view's evaluation context**, not in either base policy. That is exactly the failure mode that base-table-only audits miss and that follow-the-data is designed to surface.

---

## 9. PROPOSED block for `DECISIONS.md`

```markdown
<!-- PROPOSED by rls-auth-boundary-auditor 2026-06-05 -->
### D-N -- View evaluation context for tenant-scoped joins

**Context.** `v_team_project_summary` joins two RLS-protected tables and is granted to `authenticated`. PostgreSQL's default view semantics evaluate base-table RLS as the view OWNER, not the caller, which silently bypasses RLS on Supabase (whose migration role typically has `BYPASSRLS`).

**Decision.** All views that read from RLS-protected tables and are granted to `authenticated` or `anon` MUST be created with `WITH (security_invoker = true)`. CI lint rule to follow.

**Alternatives considered.**
- Replace views with `SECURITY INVOKER` set-returning functions -- heavier, but works pre-PG15.
- Move the join into the application layer via two scoped reads -- loses the single-query ergonomics, costs a round trip.

**Status.** PROPOSED. Route to `decision-interview` if multi-policy tradeoff needs scoping.
```

---

## 10. Recommended next command

`decision-interview` -- to lock the `security_invoker` policy as a project-wide convention before the next view-bearing migration ships. If you'd rather just ship the fix and lock the convention later, `implementation-plan` to slice the remediation migration.

### Artifact changes

- PROPOSED: `<task>/RLS_AUDIT.md` (full body above; verdict FAIL; one P1 in view, one latent P1 in projects via shape, two P2s)
- PROPOSED: `DECISIONS.md` D-N draft (security_invoker convention)

### Command transcript

1. Enumerated objects in diff: 2 tables + 1 view, all tenant-scoped.
2. Per-object posture computed; FORCE RLS confirmed on both base tables; view has no security_invoker.
3. Followed the join: caller-context evaluation breaks at the view boundary → P1.
4. Emitted migration-shaped remediation + PROPOSED decision block.

### Handoff

**Run now:** `decision-interview` (to lock `security_invoker = true` as project-wide convention)
**Why:** the view-evaluation-context gap will recur on every future join-view migration unless the convention is locked.
**Mode:** Ask.
