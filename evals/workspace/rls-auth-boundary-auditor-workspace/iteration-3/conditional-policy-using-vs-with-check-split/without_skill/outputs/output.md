# RLS Audit: `invoices` -- USING vs WITH CHECK claim split

## 1. Per-policy posture

| Policy | Command | USING | WITH CHECK | Posture |
|---|---|---|---|---|
| `invoices_select_active_org` | SELECT | `org_id = (auth.jwt() ->> 'active_org_id')::uuid` | n/a (SELECT has no WITH CHECK) | Tenant-scoped to the **active org claim**, not to membership. Visibility flips whenever the user switches orgs. |
| `invoices_insert_self` | INSERT | n/a (INSERT has no USING) | `created_by = auth.uid()` | **User-scoped only.** No `org_id` constraint at all. Any authenticated user can write a row with an arbitrary `org_id`, including orgs they do not belong to. |
| `invoices_update_self` | UPDATE | `created_by = auth.uid()` | `created_by = auth.uid()` | Internally consistent (same predicate on both sides), but still **user-scoped only** -- a user can move/relabel `org_id` on their own rows freely. |

RLS is `ENABLE` + `FORCE`, which is correct. `org_id` and `created_by` are `NOT NULL`, which is good. But there is no FK to `auth.users`, no FK from `org_id` to an `orgs` table, and no membership check anywhere.

## 2. Gap -- the USING vs WITH CHECK claim split

The SELECT path and the write path key off **different identity facts**:

- **SELECT** trusts `auth.jwt() ->> 'active_org_id'` -- a *session-scoped, user-controllable* claim re-issued by a custom Edge Function whenever the user switches active org.
- **INSERT / UPDATE** trust `auth.uid()` -- a *stable* identity, but never cross-checked against `org_id` on the row being written.

This split has three consequences:

1. **Write side ignores tenancy entirely.** `WITH CHECK (created_by = auth.uid())` lets U1 insert a row with `org_id = <any uuid>` -- even an org they are not a member of, even a random uuid that does not exist. There is no `EXISTS (SELECT 1 FROM org_members WHERE user_id = auth.uid() AND org_id = NEW.org_id)` predicate.
2. **Read side can hide what the write side accepts.** Because SELECT filters by the *active* org claim, a row the user just wrote into a *different* org becomes invisible to them on the next `SELECT` from the same session. Classic insert-then-cannot-read footgun, and worse: it can be exploited to plant rows in orgs the attacker has no business writing to.
3. **Active-org claim is the wrong primitive for authorization.** `active_org_id` reflects *UI focus*, not *membership*. Even on SELECT, the policy is permissive in the wrong direction: if the Edge Function that mints the JWT ever sets `active_org_id` without re-verifying membership at mint time, the user can read invoices for any org they can name in the claim. The DB has no defense-in-depth against a malformed claim because the policy *only* checks the claim.

## 3. Follow-the-data: U1 inserts `(org_id = B, created_by = U1, …)` while JWT has `active_org_id = A`

### INSERT path

- Policy evaluated: `invoices_insert_self`.
- Predicate: `WITH CHECK (created_by = auth.uid())`.
- `created_by = U1` and `auth.uid() = U1` → predicate is **TRUE**.
- `org_id` is not referenced anywhere in WITH CHECK. The value `B` is accepted as-is.
- **Result: INSERT succeeds.** The row `(org_id = B, created_by = U1, amount_cents = 5_000_000, status = 'draft')` is persisted.

Note: this would succeed even if U1 were *not* a member of B, and even if `B` were a uuid for an org that does not exist. The DB has no FK and no membership predicate to stop it.

### SELECT path (same session, same JWT, `active_org_id = A`)

- Policy evaluated: `invoices_select_active_org`.
- Predicate: `USING (org_id = (auth.jwt() ->> 'active_org_id')::uuid)` → `org_id = A`.
- The row just inserted has `org_id = B`. `B = A` is **FALSE**.
- **Result: the row is not returned.** U1 cannot see the invoice they just wrote.

### What U1 *can* do to read it back

Switch active org to B via the Edge Function so a new JWT is minted with `active_org_id = B`. On the next request, USING evaluates `org_id = B` → TRUE → the row is visible. If the Edge Function does not re-verify membership when minting, U1 (or any caller who can influence the claim) can also flip `active_org_id` to *any* org id and read invoices for it. The DB does not guard against this.

### Net behavior

- **Write succeeded into an org context the SELECT policy refuses to acknowledge.** That is the split.
- **Tenancy is enforced on read but not on write**, which is the inverse of what you want -- write paths are where data integrity must be defended.
- **Forensics get worse**: if U1 wrote `org_id = B` by mistake or maliciously, org A admins will never see it via the app, and org B admins will see a foreign-looking row authored by a non-member.

## 4. Remediation -- close the split, anchor tenancy in membership

Two principles:

1. Both USING and WITH CHECK across **all** commands must reference the **same tenant fact**.
2. That tenant fact must be **membership in `org_id`**, verified server-side, not a self-asserted JWT claim.

```sql
-- migrations/20260606150003_invoices_tenant_scope_fix.sql

-- 1. Make org_id a real foreign key so bogus uuids are rejected at write time.
--    (Assumes an orgs table exists.)
ALTER TABLE invoices
  ADD CONSTRAINT invoices_org_id_fkey
  FOREIGN KEY (org_id) REFERENCES orgs(id) ON DELETE RESTRICT;

ALTER TABLE invoices
  ADD CONSTRAINT invoices_created_by_fkey
  FOREIGN KEY (created_by) REFERENCES auth.users(id) ON DELETE RESTRICT;

-- 2. Helper: is the current user a member of this org? SECURITY DEFINER so it
--    bypasses RLS on org_members while staying read-only and parameterized.
CREATE OR REPLACE FUNCTION public.is_org_member(target_org uuid)
RETURNS boolean
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
  SELECT EXISTS (
    SELECT 1
    FROM org_members om
    WHERE om.org_id  = target_org
      AND om.user_id = auth.uid()
  );
$$;
REVOKE ALL ON FUNCTION public.is_org_member(uuid) FROM public;
GRANT EXECUTE ON FUNCTION public.is_org_member(uuid) TO authenticated;

-- 3. Drop the split policies.
DROP POLICY IF EXISTS invoices_select_active_org ON invoices;
DROP POLICY IF EXISTS invoices_insert_self       ON invoices;
DROP POLICY IF EXISTS invoices_update_self       ON invoices;

-- 4. Re-issue policies that scope by membership on BOTH sides, consistently.

-- SELECT: any org the user is a member of. (active_org_id becomes a UI filter,
-- not an auth boundary -- apply it in the query, not in RLS.)
CREATE POLICY invoices_select_member ON invoices
  FOR SELECT
  USING ( public.is_org_member(org_id) );

-- INSERT: must be writing into an org the user belongs to, AND must self-author.
CREATE POLICY invoices_insert_member ON invoices
  FOR INSERT
  WITH CHECK (
    created_by = auth.uid()
    AND public.is_org_member(org_id)
  );

-- UPDATE: USING and WITH CHECK must agree, and both must require membership.
-- This also blocks moving a row to an org the user does not belong to.
CREATE POLICY invoices_update_member ON invoices
  FOR UPDATE
  USING (
    created_by = auth.uid()
    AND public.is_org_member(org_id)
  )
  WITH CHECK (
    created_by = auth.uid()
    AND public.is_org_member(org_id)
  );

-- 5. DELETE was implicitly denied (no policy). Make that explicit if intended,
--    or add a parallel membership-scoped DELETE policy.
-- CREATE POLICY invoices_delete_member ON invoices
--   FOR DELETE USING ( public.is_org_member(org_id) AND created_by = auth.uid() );
```

### Why this closes the split

- USING and WITH CHECK on UPDATE now reference the **same predicate** -- no insert-then-cannot-read, no update-then-cannot-read.
- INSERT now requires `is_org_member(org_id)`, so U1 cannot plant a row in org B unless they are actually a member of B. The U1 scenario above now **fails at WITH CHECK** with `new row violates row-level security policy`.
- SELECT is anchored in `org_members`, not in a session-controlled claim. `active_org_id` becomes a UI hint (`WHERE org_id = $active`) layered on top of RLS, not the only thing enforcing tenancy.
- FKs add defense in depth: a typo or forged `org_id` fails the FK before RLS even runs.

### Optional hardening

- Add `org_id` to a covering index for the membership lookup: `CREATE INDEX invoices_org_id_idx ON invoices(org_id);`.
- If `active_org_id` must remain in JWT for UX, keep it but **never** make it the sole authorization key. Treat any policy that references a JWT custom claim without a corroborating server-side membership check as a finding.
- Add a test (pgTAP or app-level) that asserts: user in orgs {A, B}, JWT `active_org_id = A`, INSERT with `org_id = C` (non-member) → denied; with `org_id = B` (member, non-active) → allowed and readable after the same insert under the same session, modulo any UI-level `active_org_id` filter applied at query time, not at policy time.