## RLS Audit: `invoices` table (migration `20260606150002_invited_member_invoices.sql`)

Aggregate verdict: **FAIL (P1 tenant-isolation break via USING vs WITH CHECK claim split).**

---

### 1. Tenant-scoped table inventory

- `invoices` -- **compound tenant scope** (per-org via `org_id`, per-user via `created_by`). Touched by this migration; every row belongs to an org AND to an authoring user. Both axes are load-bearing for isolation.

No other tables touched. No join/audit/log tables defined alongside `invoices` in this migration set.

### 2. Per-table policy posture

| table | RLS enabled | FORCE applied | SELECT policy | INSERT policy (USING + WITH CHECK) | UPDATE policy (USING + WITH CHECK) | DELETE policy | tenant predicate present | verdict |
|---|---|---|---|---|---|---|---|---|
| `invoices` | YES | YES | `org_id = (auth.jwt() ->> 'active_org_id')::uuid` (predicate: **active org JWT claim**) | INSERT: no USING (correct for INSERT); WITH CHECK `created_by = auth.uid()` (predicate: **user identity only -- no org scope**) | USING `created_by = auth.uid()`; WITH CHECK `created_by = auth.uid()` (predicate: **user identity only -- no org scope**) | **MISSING** | partial -- SELECT is org-scoped, INSERT/UPDATE are only user-scoped; the two axes never meet | **FAIL** |

### 3. Gaps and severities

1. **P1 -- USING/WITH CHECK claim split between SELECT (`active_org_id` JWT claim) and INSERT/UPDATE (`auth.uid()` only).** The INSERT policy `invoices_insert_self` accepts ANY `org_id` value the client sends as long as `created_by = auth.uid()`. The SELECT policy `invoices_select_active_org` only returns rows where `org_id` matches the JWT's current `active_org_id`. A user who is a member of org A and org B, with `active_org_id = A`, can insert `(org_id = B, created_by = self)`. The write succeeds. The row is immediately unreadable to that same session (SELECT filters it out: `B != A`). This is the classic write-then-can't-read phantom-orphan footprint AND a cross-tenant write vector: the INSERT path performs no membership check against `org_id = B` at all. If U1 is in fact a member of B, the row is a legitimate-looking invoice in B's books authored from an A-context session, bypassing the org-switch ceremony that the rest of the app presumably relies on for audit trails. If U1 is NOT a member of B, the INSERT still succeeds -- there is no policy or FK guarding `org_id` against an org-membership table. This is the textbook USING-vs-WITH-CHECK claim-split failure mode.
2. **P1 -- INSERT WITH CHECK has no `org_id` tenant predicate at all.** Independent of the JWT split, `invoices_insert_self` lets any authenticated user write any `org_id` value, including a UUID for an org they are not a member of, an org that does not exist, or `NULL`-shaped garbage (the column is `NOT NULL` but no FK exists to constrain it to real orgs). The "self-as-author" predicate is necessary but not sufficient for a multi-tenant invoice table.
3. **P1 -- UPDATE policy has no `org_id` tenant predicate.** `invoices_update_self` lets the author re-home their own invoice into a different `org_id` after the fact (USING and WITH CHECK both only check `created_by`). Combined with finding #1, an author can insert under org A and then UPDATE the row to set `org_id = C` for any C -- including orgs they have no membership in.
4. **P1 -- No DELETE policy.** With RLS enabled and FORCE applied, the absence of a DELETE policy means DELETE is denied for every non-owner role, which is restrictive-by-default (good) but the audit MUST flag it because the application likely expects authors to be able to void their own drafts; the silent denial will surface as a user-facing bug rather than a security finding. Classified P1 because operability gaps on FORCE-RLS tables are indistinguishable from data-loss bugs at runtime.
5. **P2 -- `org_id` has no foreign key.** Even after policy fixes, an unconstrained `org_id uuid NOT NULL` permits orphaned tenancy. A row with `org_id = <random uuid>` is unreachable by any org-scoped SELECT but persists in storage and skews aggregate reporting (cost dashboards, totals, audit exports that scan with elevated roles).
6. **P2 -- No membership table referenced.** The audit cannot verify "is U1 a member of org B" because the migration set in scope contains no `org_memberships` / `org_members` table. The remediation below assumes one exists at `org_members(user_id uuid, org_id uuid, PRIMARY KEY (user_id, org_id))`; if it does not, that table is a prerequisite and the persona flags it as a blocking dependency for any correct fix.
7. **P3 -- `active_org_id` JWT claim is a session-mutable bearer of authority.** The SELECT policy trusts a claim that a custom Edge Function re-issues on org switch. If that Edge Function does not re-verify membership at re-issuance time (e.g. the user was removed from org A between login and switch), the SELECT path silently leaks. Out of scope for this migration but flagged for the Edge Function audit.

### 4. Concrete scenario trace (U1 member of A and B; JWT `active_org_id = A`; INSERTs `org_id = B`)

**INSERT path (write):**
- Postgres receives `INSERT INTO invoices (org_id, created_by, amount_cents, status) VALUES ('B', U1, 5000000, 'draft')`.
- RLS evaluates the INSERT policy `invoices_insert_self`. The check is `WITH CHECK (created_by = auth.uid())` → `U1 = U1` → **TRUE**.
- No other policy on this command. `org_id = B` is not examined. No FK to `org_members`. No FK to `orgs`. The row is written.
- **U1 successfully inserts an invoice into org B from an org-A session.** No error. No warning.

**SELECT path (read-back, same session, same JWT):**
- U1 issues `SELECT * FROM invoices WHERE id = <new id>` (or any list query).
- RLS evaluates `invoices_select_active_org`: `USING (org_id = (auth.jwt() ->> 'active_org_id')::uuid)` → `B = A` → **FALSE**.
- Zero rows returned. From U1's session, the invoice they just wrote **does not exist**.

**Net effect:**
- A real, persistent, $50,000 invoice exists in storage tagged to org B with `created_by = U1`.
- It is invisible to U1's current session (SELECT filters it).
- It is visible to any user in org B whose `active_org_id = B`, including org B admins, who will see an invoice authored by a member acting through a session they never authorized for B (no audit log entry that U1 switched to B).
- If U1 was in fact removed from B between the org-list snapshot the app uses and this INSERT, the row is fully cross-tenant: written by a non-member into another tenant's books.
- If U1 then runs UPDATE on the row (in another session with `active_org_id = B` so SELECT shows it, OR via any path that bypasses SELECT), `invoices_update_self` accepts ANY new `org_id` because UPDATE WITH CHECK only checks `created_by`. The row can be re-homed at will.

This is the exact failure mode the USING-vs-WITH-CHECK claim split produces: SELECT-side authority (org JWT claim) and INSERT/UPDATE-side authority (user identity only) disagree, and the INSERT/UPDATE side is weaker, so writes leak across the boundary the SELECT side appears to enforce.

### 5. Migration-shaped remediation (single migration closing the split)

```sql
-- migrations/20260606150003_invoices_close_using_check_split.sql

-- Prerequisite (assumed to exist; create if not present):
-- CREATE TABLE org_members (
--   user_id uuid NOT NULL,
--   org_id uuid NOT NULL,
--   PRIMARY KEY (user_id, org_id)
-- );
-- ALTER TABLE org_members ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE org_members FORCE ROW LEVEL SECURITY;

-- 1. Constrain org_id at the schema level so policy logic cannot be undermined
--    by orphaned-tenant rows.
ALTER TABLE invoices
  ADD CONSTRAINT invoices_org_id_fkey
  FOREIGN KEY (org_id) REFERENCES orgs (id) ON DELETE RESTRICT;

ALTER TABLE invoices
  ADD CONSTRAINT invoices_created_by_fkey
  FOREIGN KEY (created_by) REFERENCES auth.users (id) ON DELETE RESTRICT;

-- 2. Drop the split policies.
DROP POLICY IF EXISTS invoices_select_active_org ON invoices;
DROP POLICY IF EXISTS invoices_insert_self        ON invoices;
DROP POLICY IF EXISTS invoices_update_self        ON invoices;

-- 3. SELECT: a row is visible if the caller is a member of the row's org.
--    Do NOT couple SELECT to the active_org_id JWT claim; couple it to
--    actual membership so the read side and write side share one authority.
CREATE POLICY invoices_select_member ON invoices
  FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM org_members m
      WHERE m.user_id = auth.uid()
        AND m.org_id  = invoices.org_id
    )
  );

-- 4. INSERT: the caller must be the author AND a member of the target org.
--    Both axes checked in WITH CHECK so the SELECT and INSERT authorities meet.
CREATE POLICY invoices_insert_member ON invoices
  FOR INSERT
  WITH CHECK (
    created_by = auth.uid()
    AND EXISTS (
      SELECT 1 FROM org_members m
      WHERE m.user_id = auth.uid()
        AND m.org_id  = invoices.org_id
    )
  );

-- 5. UPDATE: same predicate on USING and WITH CHECK so re-homing into a
--    foreign org is impossible. Author can only edit their own invoices in
--    orgs they are still a member of, and cannot mutate org_id to escape.
CREATE POLICY invoices_update_member ON invoices
  FOR UPDATE
  USING (
    created_by = auth.uid()
    AND EXISTS (
      SELECT 1 FROM org_members m
      WHERE m.user_id = auth.uid()
        AND m.org_id  = invoices.org_id
    )
  )
  WITH CHECK (
    created_by = auth.uid()
    AND EXISTS (
      SELECT 1 FROM org_members m
      WHERE m.user_id = auth.uid()
        AND m.org_id  = invoices.org_id
    )
  );

-- 6. DELETE: author can void their own drafts in orgs they belong to.
--    Restrict to status='draft' to prevent destruction of issued invoices;
--    issued-invoice voiding should go through a server-side function with
--    an audit trail, not a raw DELETE.
CREATE POLICY invoices_delete_own_draft ON invoices
  FOR DELETE
  USING (
    created_by = auth.uid()
    AND status = 'draft'
    AND EXISTS (
      SELECT 1 FROM org_members m
      WHERE m.user_id = auth.uid()
        AND m.org_id  = invoices.org_id
    )
  );
```

Key properties of the fix:

- USING and WITH CHECK are now grounded in the **same authority** (`org_members` membership join), so SELECT-side visibility and INSERT/UPDATE-side write authority can no longer disagree.
- The `active_org_id` JWT claim is removed from policy logic entirely. It remains useful as a **UI hint** (which org to default the view to) but is no longer load-bearing for isolation. JWT claims that the app re-issues outside Postgres should not be the sole authority on row visibility.
- INSERT now requires membership in the target `org_id`, closing the cross-tenant write vector regardless of which org the session is currently "active" in.
- UPDATE WITH CHECK enforces the org predicate, so the author cannot re-home an existing row into another org.
- The `org_id` FK eliminates orphan-org rows; the `status = 'draft'` guard on DELETE prevents accidental destruction of issued invoices via raw RLS-allowed deletes.

### 6. Follow-the-data trace

- `invoices.org_id` → (after fix) `orgs.id`: FK present, ON DELETE RESTRICT.
- `invoices.created_by` → (after fix) `auth.users.id`: FK present, ON DELETE RESTRICT.
- `invoices` ↔ `org_members`: read via EXISTS in every policy; `org_members` is assumed RLS-protected with its own membership predicate (verify in the membership-table migration).
- No join tables, materialized views, or audit/log tables defined alongside `invoices` in this migration. **Flag for next migration:** any future `invoice_line_items` or `invoice_audit_log` table MUST mirror the org-membership predicate; do not let line items become readable without their parent's tenant check.

### 7. SECURITY DEFINER function audit

- No `SECURITY DEFINER` functions in this migration. The Edge Function that re-issues the JWT with `active_org_id` lives outside Postgres and is out of scope for this audit, but flagged: that function MUST re-verify org membership at re-issuance, otherwise revoked members keep reading via stale claims. Route to a separate Edge Function audit.

### 8. `service_role` usage audit

- Migration introduces no new `service_role` call sites. The split-policy gap is reachable by ordinary `authenticated` JWT requests; no `service_role` is needed to exploit it. Backend code search for `SUPABASE_SERVICE_ROLE_KEY` is out of scope for this migration but recommended as a follow-up sweep once the policy fix lands.

### 9. PROPOSED decisions to lock

```
<!-- PROPOSED by rls-auth-boundary-auditor:
D-N: Tenant authority for `invoices` row visibility and writes.

Context: Original migration coupled SELECT to JWT claim `active_org_id`
and INSERT/UPDATE to `auth.uid()` only, producing a USING vs WITH CHECK
split where writes succeed for org_id values the SELECT side then filters
out. Cross-tenant write vector confirmed.

Options:
  A. Couple all policies to `org_members` membership join (proposed).
     Pros: single authority, SELECT and INSERT/UPDATE cannot disagree,
     resilient to stale JWT claims, FK-enforceable.
     Cons: extra join in every policy evaluation; requires `org_members`
     table to exist and be RLS-protected.
  B. Couple all policies to JWT claim `active_org_id` (SELECT and
     WITH CHECK both).
     Pros: cheaper at query time (no join).
     Cons: trusts session-mutable claim re-issued by Edge Function;
     a user re-issuing the claim to an org they were just removed from
     still passes WITH CHECK; harder to audit; encourages claim-stuffing
     bugs in the auth layer.
  C. Hybrid: SELECT by JWT claim (cheap), INSERT/UPDATE by membership
     join (correct). Pros: perf on read path. Cons: re-introduces a
     coordinated authority across two layers; auditing the equivalence
     of the two predicates becomes a recurring task.

Recommendation: A. The cost of one EXISTS join per row is small relative
to the cost of a cross-tenant write incident. Route to decision-interview
if B or C is preferred for performance reasons; capture the perf budget
explicitly before locking.
-->
```

PROPOSED entries also belong under `TASK_STATE.md ## Risks to watch` ("invoices RLS USING/WITH CHECK split unresolved until D-N locked and remediation migration shipped") and under `IMPLEMENTATION_PLAN.md ## Risks and mitigations` (block any invoice-feature slice on the remediation migration landing first).

### 10. `RLS_AUDIT.md` content draft

```
# RLS Audit -- invoices (migration 20260606150002)

Audited: 2026-06-05
Auditor: rls-auth-boundary-auditor
Migrations in scope: supabase/migrations/20260606150002_invited_member_invoices.sql
Aggregate verdict: FAIL

## Tenant-scoped tables
- invoices: compound (per-org via org_id, per-user via created_by)

## Posture
[posture table from section 2]

## Gaps
P1 #1 USING/WITH CHECK claim split (active_org_id vs auth.uid())
P1 #2 INSERT WITH CHECK lacks org_id tenant predicate
P1 #3 UPDATE WITH CHECK lacks org_id tenant predicate (re-home vector)
P1 #4 No DELETE policy on FORCE RLS table
P2 #5 org_id has no FK
P2 #6 No org_members table referenced; assumed prerequisite
P3 #7 active_org_id JWT claim trusts Edge Function re-issuance

## Remediation
[SQL from section 5]

## Follow-the-data
[trace from section 6]

## SECURITY DEFINER audit
None in scope.

## service_role audit
None in scope.

## Audit history
| timestamp | run_id | migrations | verdict |
|---|---|---|---|
| 2026-06-05 | <run-id> | 20260606150002_invited_member_invoices.sql | FAIL |
```

### Recommended next command

`decision-interview` -- D-N has three real options with a perf/correctness tradeoff; do not lock unilaterally. After D-N is locked, route to `implementation-plan` to slice the remediation migration (plus the `org_members` prerequisite if it does not yet exist), then `implement-approved-slice`.