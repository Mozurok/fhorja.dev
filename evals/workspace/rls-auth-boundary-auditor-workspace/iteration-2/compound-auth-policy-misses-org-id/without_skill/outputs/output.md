# RLS Audit: `tasks` + `org_members` (compound auth, per-org-per-user)

## TL;DR

**Yes -- U1 can leak / cross-pollute data across orgs through this policy set.** The policies key entirely on `user_id = auth.uid()` and never reference `org_id`. The migration treats the tenant boundary as if it were single-axis (per-user), but the stated data model is **compound** (per-org-per-user). Every `tasks` policy is therefore under-constrained on the `org_id` axis.

Severity: **High** for data integrity and tenancy invariants; **Medium-to-High** for confidentiality depending on how `org_id` is selected by the application at insert / update time and how the data is later partitioned in the UI.

---

## 1. Per-table posture

| Table | RLS enabled | FORCED | SELECT | INSERT | UPDATE | DELETE | Compound (org_id) enforced? | Verdict |
|---|---|---|---|---|---|---|---|---|
| `org_members` | Yes | Yes | `user_id = auth.uid()` | None defined | None defined | None defined | N/A (this table *is* the membership oracle) | **Partial.** SELECT is correct (a user sees only their own membership rows). INSERT/UPDATE/DELETE have **no policy** -- combined with FORCE RLS, they are de-facto denied for non-owner roles, which is safe but probably not intended (no admin path defined). Also lacks FKs to `auth.users` and to `orgs`. |
| `tasks` | Yes | Yes | `user_id = auth.uid()` (USING + redundant WITH CHECK) | `user_id = auth.uid()` | USING `user_id = auth.uid()` / WITH CHECK `user_id = auth.uid()` | `user_id = auth.uid()` | **No.** `org_id` is never referenced in any policy. | **Broken w.r.t. stated model.** Org boundary is not enforced. User can write any `org_id` value (including an org they don't belong to), or move a row from one of their orgs to another. |

Structural issues independent of policies:

- No `FOREIGN KEY (org_id, user_id) REFERENCES org_members(org_id, user_id)` on `tasks` → DB will accept tasks for `(org, user)` pairs that don't exist as memberships.
- No FK from `tasks.user_id` to `auth.users(id)`, no FK from `tasks.org_id` to an `orgs` table (the `orgs` table isn't in this migration at all).
- No index on `org_members(user_id)` -- the membership lookup that should drive RLS will table-scan as the table grows. Indexes matter for RLS because the policy predicate runs on every row.
- No index on `tasks(org_id, user_id)` or `tasks(user_id, org_id)` -- once RLS is fixed, queries will need it.
- `org_members.role` is freeform `text` with a default; no CHECK constraint, no enum. Any future role-gated policy can be spoofed by inserting a typo'd role.
- Policies are not role-scoped (`TO authenticated`) -- they implicitly apply to `PUBLIC`, which on Supabase resolves to anon + authenticated. With FORCE RLS the predicate still gates access, but explicit `TO authenticated` is the standard.

---

## 2. Gaps & failure modes

### G1. `tasks` policies don't reference `org_id` at all -- **High**

The stated invariant is "each row belongs to ONE user WITHIN ONE org." The policies enforce only the user axis. Concrete failure modes:

- **Cross-org INSERT (writing into an org you don't belong to).**
  U1 belongs to org A and org B. U1 can `INSERT INTO tasks (org_id, user_id, title) VALUES ('<org_C_uuid>', U1, 'x')` and the WITH CHECK passes because `user_id = auth.uid()`. U1 is not a member of org C, yet a `tasks` row now exists tagged to org C. This is silent tenancy corruption. If org C ever runs an admin/service query that lists tasks where `org_id = org_C`, U1's task surfaces inside org C's data.

- **Cross-org UPDATE (re-parenting a row to a different org).**
  U1 owns `(org_A, U1, "salary plan")`. U1 issues `UPDATE tasks SET org_id = '<org_B_uuid>' WHERE id = '<task_id>'`. The USING clause matches (U1 is the user), the WITH CHECK clause matches (still U1). The row is now `(org_B, U1, "salary plan")` -- a private org A task has been migrated into org B's tenant scope. If org B's UI lists all `tasks` where `org_id = org_B`, every member of org B (including U2, who is **not** in org A) will see "salary plan." That is the direct confidentiality breach.

- **Cross-org SELECT via row-targeting (lateral leak).**
  Because SELECT keys only on `user_id = auth.uid()`, U1 can read **all** of their own tasks across **every** org they have ever been associated with, including:
  - orgs they have since been removed from (no enforcement that membership still exists at read time),
  - orgs they fabricated themselves via G1's INSERT path.
  In a UI scoped to "the currently selected org," the client is responsible for filtering by `org_id`. RLS gives no defence-in-depth here.

- **Phantom-org INSERT.**
  Nothing requires `org_id` to be a real org. With no FK, U1 can insert `(org_id = '00000000-...', user_id = U1)`. Harmless on its own, but it pollutes analytics, breaks `JOIN orgs` queries silently, and creates dangling rows that later schema work must clean up.

> Why "surface-correct SQL still leaks": `user_id = auth.uid()` looks like a sane ownership check, and it *is* sufficient for a single-axis (per-user) model. The breakage is the gap between the *stated* tenant model (compound) and the *enforced* tenant model (user-only). The SQL is internally consistent but models the wrong invariant.

### G2. INSERT does not verify membership -- **High**

There is no policy clause of the shape:

```sql
EXISTS (SELECT 1 FROM org_members m WHERE m.org_id = tasks.org_id AND m.user_id = auth.uid())
```

So even setting aside G1's "wrong org_id" issue, an INSERT can name any org -- real or fake -- that U1 isn't currently a member of. Membership revocation is also not enforced retroactively; if U1 is removed from org A, U1's existing org A tasks remain readable/writable by U1 (because the policy only checks `user_id`).

### G3. UPDATE allows `org_id` mutation -- **High**

The UPDATE policy doesn't pin `org_id`. A correct compound-auth UPDATE policy must either (a) forbid changing `org_id` outright, or (b) require membership in *both* the old and the new `org_id`. Right now neither is enforced. This is the single sharpest cross-org leak vector: re-parenting a row from a private org into a shared org silently exposes it.

### G4. SELECT scope ignores current membership -- **Medium**

A user removed from an org still sees their historical tasks in that org because SELECT only checks `user_id`. Whether that is acceptable is a product question, but it is *not* what "tenant isolation" usually means, and it is silently inconsistent with how server-side admin queries (scoped by `org_id`) will treat the same data.

### G5. `org_members` has no INSERT/UPDATE/DELETE policy + no admin path -- **Medium**

With FORCE RLS, write attempts from `authenticated` are denied. That means there is **no way for the application** (acting as the user) to create memberships, change roles, or remove members -- all of that has to happen via the `service_role` / a SECURITY DEFINER function. The migration doesn't ship one. Either intentional (admin path lives elsewhere) or oversight; flag it.

### G6. `org_members.role` is unconstrained -- **Low/Medium**

`role text DEFAULT 'member'` with no CHECK / enum. Any future policy like `role = 'admin'` is one typo away from being bypassable (`'Admin'`, `'admin '`, `'ADMIN'`). Lock the domain.

### G7. No `TO authenticated` clause -- **Low**

Policies default to `PUBLIC`. With FORCE RLS the predicates still apply, but Supabase convention (and clarity for reviewers) is to write `TO authenticated`. Anon should be denied explicitly by *not* having a matching policy.

### G8. WITH CHECK on SELECT is meaningless -- **Low (smell)**

`CREATE POLICY tasks_user_select ... FOR SELECT USING (...) WITH CHECK (...)` -- `WITH CHECK` doesn't apply to SELECT. It's dead syntax. Not a bug, but a strong signal the author was pattern-matching and not thinking about which clause runs when.

### G9. Missing structural integrity -- **Medium**

- No FK `(org_id, user_id) -> org_members(org_id, user_id)` on `tasks` means the DB itself does not enforce that a task's `(org, user)` pair is a real membership. RLS is *one* layer; constraints are another. Defence in depth requires both.
- No FK on `org_members.user_id -> auth.users(id) ON DELETE CASCADE` -- deleting a user leaves orphan membership rows.

### G10. No indexes supporting RLS predicates -- **Low (perf, but tenancy-adjacent)**

Once policies are tightened to use `EXISTS (SELECT 1 FROM org_members ...)`, every row visibility check joins through `org_members`. Without `org_members(user_id, org_id)` index (the PK is `(org_id, user_id)`, which is the wrong leading column for "find my orgs"), this becomes expensive fast. Slow RLS is its own incident class.

---

## 3. Remediation -- migration-shaped

```sql
-- migrations/20260606140002_tasks_compound_auth_fix.sql

BEGIN;

-- 3.1 Structural integrity: lock the role domain.
ALTER TABLE org_members
  ADD CONSTRAINT org_members_role_chk
  CHECK (role IN ('owner', 'admin', 'member'));

-- 3.2 Cascade on user deletion to avoid orphan memberships.
--     (Assumes auth.users is the source of truth; adjust if you have a public.users mirror.)
ALTER TABLE org_members
  ADD CONSTRAINT org_members_user_fk
  FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;

-- 3.3 Support index for RLS lookups by current user.
CREATE INDEX IF NOT EXISTS org_members_user_org_idx
  ON org_members (user_id, org_id);

-- 3.4 Tasks: enforce compound (org, user) integrity at the schema level.
ALTER TABLE tasks
  ADD CONSTRAINT tasks_membership_fk
  FOREIGN KEY (org_id, user_id) REFERENCES org_members (org_id, user_id)
  ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS tasks_org_user_idx ON tasks (org_id, user_id);
CREATE INDEX IF NOT EXISTS tasks_user_org_idx ON tasks (user_id, org_id);

-- 3.5 Helper: is the current user a member of this org? STABLE so the planner
--     can hoist it, SECURITY INVOKER (default) so it respects RLS on org_members.
CREATE OR REPLACE FUNCTION public.is_org_member(target_org uuid)
RETURNS boolean
LANGUAGE sql
STABLE
AS $$
  SELECT EXISTS (
    SELECT 1
    FROM org_members m
    WHERE m.org_id = target_org
      AND m.user_id = auth.uid()
  );
$$;

-- 3.6 Replace tasks policies with compound-auth versions.
DROP POLICY IF EXISTS tasks_user_select ON tasks;
DROP POLICY IF EXISTS tasks_user_insert ON tasks;
DROP POLICY IF EXISTS tasks_user_update ON tasks;
DROP POLICY IF EXISTS tasks_user_delete ON tasks;

-- SELECT: own row AND still a member of the org.
CREATE POLICY tasks_select
  ON tasks
  FOR SELECT
  TO authenticated
  USING (
    user_id = auth.uid()
    AND public.is_org_member(org_id)
  );

-- INSERT: row must be authored by caller AND caller must be a member of the target org.
CREATE POLICY tasks_insert
  ON tasks
  FOR INSERT
  TO authenticated
  WITH CHECK (
    user_id = auth.uid()
    AND public.is_org_member(org_id)
  );

-- UPDATE: caller owns the row in an org they belong to, AND cannot move the row
-- to a different org or to a different user.
CREATE POLICY tasks_update
  ON tasks
  FOR UPDATE
  TO authenticated
  USING (
    user_id = auth.uid()
    AND public.is_org_member(org_id)
  )
  WITH CHECK (
    user_id = auth.uid()
    AND public.is_org_member(org_id)
  );

-- Hard pin: forbid changing org_id or user_id post-creation. RLS WITH CHECK alone
-- is symmetric and would allow a swap to another org the user is also in
-- (e.g. U1 moving an org_A task into org_B). A trigger removes that vector.
CREATE OR REPLACE FUNCTION public.tasks_pin_tenancy()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  IF NEW.org_id IS DISTINCT FROM OLD.org_id THEN
    RAISE EXCEPTION 'tasks.org_id is immutable';
  END IF;
  IF NEW.user_id IS DISTINCT FROM OLD.user_id THEN
    RAISE EXCEPTION 'tasks.user_id is immutable';
  END IF;
  RETURN NEW;
END;
$$;

CREATE TRIGGER tasks_pin_tenancy_trg
BEFORE UPDATE ON tasks
FOR EACH ROW EXECUTE FUNCTION public.tasks_pin_tenancy();

-- DELETE: same gate as SELECT/UPDATE.
CREATE POLICY tasks_delete
  ON tasks
  FOR DELETE
  TO authenticated
  USING (
    user_id = auth.uid()
    AND public.is_org_member(org_id)
  );

-- 3.7 org_members: explicit admin-write path via SECURITY DEFINER.
-- Read stays as-is (a user sees their own memberships). Writes go through
-- a definer function that checks the caller's role in the target org.
CREATE OR REPLACE FUNCTION public.org_members_add(target_org uuid, target_user uuid, target_role text)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM org_members
    WHERE org_id = target_org
      AND user_id = auth.uid()
      AND role IN ('owner', 'admin')
  ) THEN
    RAISE EXCEPTION 'not authorized to manage org %', target_org USING ERRCODE = '42501';
  END IF;
  IF target_role NOT IN ('owner', 'admin', 'member') THEN
    RAISE EXCEPTION 'invalid role';
  END IF;
  INSERT INTO org_members (org_id, user_id, role)
  VALUES (target_org, target_user, target_role)
  ON CONFLICT (org_id, user_id) DO UPDATE SET role = EXCLUDED.role;
END;
$$;

REVOKE ALL ON FUNCTION public.org_members_add(uuid, uuid, text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.org_members_add(uuid, uuid, text) TO authenticated;

COMMIT;
```

Notes on the remediation:

- The **immutability trigger** is the load-bearing piece that closes the cross-org UPDATE leak. WITH CHECK alone is not sufficient: if U1 belongs to both org A and org B, both the USING and WITH CHECK predicates are satisfied for `org_A -> org_B` reparenting, because U1 is a valid member in both. RLS by itself cannot express "the org_id must equal what it was before."
- `public.is_org_member` is `STABLE` and `SECURITY INVOKER` so it respects RLS on `org_members` and is hoistable by the planner. Don't make it SECURITY DEFINER unless you want it to bypass `org_members` RLS, which here we don't.
- The compound FK `tasks(org_id, user_id) -> org_members(org_id, user_id)` is defence in depth: even if a future policy regresses, the DB will refuse a `(org, user)` pair that isn't a real membership. Pair it with `ON DELETE CASCADE` so revoking a membership removes the tasks (verify this is the desired product behavior -- if not, switch to `ON DELETE RESTRICT` and clean up explicitly).
- I deliberately left `org_members` SELECT alone (it was correct). I added a SECURITY DEFINER admin path because otherwise the application has no way to grow memberships.

---

## 4. Follow-the-data trace -- U1 across org A and org B

Setup: U1 ∈ {org A, org B}. U2 ∈ {org B}. U1 creates `(org_A, U1, "A-task")` and `(org_B, U1, "B-task")`.

### Under the original migration

1. **U1 SELECT `tasks`.** Policy: `user_id = auth.uid()`. U1 sees both `(org_A, U1, "A-task")` and `(org_B, U1, "B-task")` regardless of which org their UI is "in". A client bug that forgets to add `WHERE org_id = $current_org` leaks org-A data into an org-B view of U1's tasks. (Annoying, not a confidentiality breach against U2 yet.)
2. **U1 INSERT `(org_C, U1, "smuggled")`** where U1 is *not* a member of org C. Policy WITH CHECK: `user_id = auth.uid()` ✓. Row inserted. Org C's admin queries (server-side, scoped by `org_id = org_C`) will now show "smuggled" as if it belongs to org C.
3. **U1 UPDATE `(org_A, U1, "A-task")` SET org_id = org_B.** USING: `user_id = U1` ✓. WITH CHECK: `user_id = U1` ✓. Row becomes `(org_B, U1, "A-task")`. U2 (member of org B) now sees "A-task" via any org-B-scoped query -- including the standard server-rendered "team feed for org B." **This is the confidentiality breach.**
4. **U1 removed from org A.** `org_members` row deleted. U1's existing `(org_A, U1, *)` tasks are still readable, writable, and deletable by U1, because the `tasks` policies never consult `org_members`. Revocation is a no-op against the data.

### Under the remediated migration

1. **U1 SELECT `tasks`.** Predicate now requires `is_org_member(org_id)`. Removing U1 from org A immediately hides org-A tasks from U1's reads. SELECT is now genuinely compound-scoped.
2. **U1 INSERT `(org_C, U1, "smuggled")`.** WITH CHECK now calls `is_org_member(org_C)` → false. INSERT rejected with RLS violation. (Even if RLS were bypassed, the new `tasks_membership_fk` would reject it at the constraint layer.)
3. **U1 UPDATE org_id swap A→B.** The BEFORE UPDATE trigger raises `tasks.org_id is immutable`. The row stays put. U2 never sees U1's org-A task. **Leak closed.**
4. **U1 removed from org A.** `is_org_member(org_A)` becomes false for U1. U1 loses SELECT/UPDATE/DELETE on those rows. With `ON DELETE CASCADE` on `tasks_membership_fk`, the rows are removed when the membership is removed (confirm this is what the product wants; if not, swap to RESTRICT + an explicit archival step).

---

## Reviewer checklist before merge

- [ ] Every `tasks` policy references `org_id` via `is_org_member(org_id)`.
- [ ] `tasks.org_id` and `tasks.user_id` cannot be mutated (trigger present and tested).
- [ ] Compound FK from `tasks(org_id, user_id)` to `org_members(org_id, user_id)` exists and ON DELETE behavior is intentional.
- [ ] `org_members` write path is via SECURITY DEFINER function with role check; no broad INSERT/UPDATE/DELETE policy on the table.
- [ ] `role` domain is constrained (CHECK or enum).
- [ ] Indexes on `org_members(user_id, org_id)` and `tasks(org_id, user_id)` exist.
- [ ] All policies are `TO authenticated`; anon is denied by default.
- [ ] Tests:
  - U1 cannot INSERT into an org they don't belong to.
  - U1 cannot UPDATE `org_id` (even to another org they *do* belong to).
  - U2 cannot see U1's tasks in their shared org B unless those tasks were authored by U2 (or the product allows shared visibility -- if so, the SELECT policy needs an explicit broader rule, not a leak).
  - Removing U1 from org A hides org-A tasks from U1's reads immediately.
  - Anon role gets zero rows from both tables.
