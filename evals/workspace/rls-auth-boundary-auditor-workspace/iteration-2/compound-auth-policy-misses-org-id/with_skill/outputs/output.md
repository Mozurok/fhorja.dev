# rls-auth-boundary-auditor -- Compound auth audit (tasks + org_members)

Auth model: `auth.uid()` (Supabase).
Tenant scope shape: **compound** -- per-user-within-org (user identity scoped by org membership in `org_members`).
Migration audited: `migrations/20260606140001_tasks_with_org_scope.sql`.
Concrete data scenario verified against: U1 ∈ {org_A, org_B}; U2 ∈ {org_B}; tasks (org_A, U1) and (org_B, U1) exist.
Driver question: **Can U1 leak a task across orgs through this policy set?** **Yes -- multiple paths.** Details below.

---

## 1) Tenant-scoped table inventory

Every table touched by the migration set, with tenant scope annotation:

- `org_members` -- **compound (per-org-per-user)**. Authoritative tenancy mapping. Without correct policies on this table, every other policy that joins through it is unsound.
- `tasks` -- **compound (per-org-per-user)**. Rows carry both `org_id` and `user_id` and are jointly scoped: a row belongs to user U *within* org O. The migration treats it as per-user only (single-column predicate) -- that is the central defect.

No table from the migration diff is omitted.

---

## 2) Per-table policy posture table

| table | RLS enabled | FORCE applied | SELECT policy | INSERT policy (USING + WITH CHECK) | UPDATE policy (USING + WITH CHECK) | DELETE policy | tenant predicate present | verdict |
|---|---|---|---|---|---|---|---|---|
| `org_members` | yes | yes | yes -- `user_id = auth.uid()` (self-rows only; cannot see co-members) | **MISSING** | **MISSING** | **MISSING** | partial -- only user identity, no org-side check at all | **FAIL** |
| `tasks` | yes | yes | **INVALID DDL** -- `FOR SELECT … WITH CHECK (…)`; PostgreSQL rejects `WITH CHECK` on SELECT policies, so this migration will not even apply | `WITH CHECK (user_id = auth.uid())` -- **no `org_id` check**; cross-org INSERT possible | `USING (user_id = auth.uid()) WITH CHECK (user_id = auth.uid())` -- **no `org_id` check on either clause**; row can pivot orgs | `USING (user_id = auth.uid())` -- **no `org_id` check** | only `user_id`, never `org_id`, never membership join | **FAIL** |

Verdict legend: PASS = all checks satisfied; GAP = only P2/P3; FAIL = at least one P1.

---

## 3) Gaps and severities (concrete failure modes, not vague hedging)

**G1 -- P0 (migration will not apply): invalid DDL on `tasks_user_select`.**
`CREATE POLICY tasks_user_select ON tasks FOR SELECT USING (...) WITH CHECK (...)` is rejected by PostgreSQL -- `WITH CHECK` is allowed only on `INSERT`, `UPDATE`, and `ALL` policies. The migration aborts before any policy lands, leaving the table either unprotected (if a prior partial transaction state existed) or with no SELECT policy at all (RLS denies all reads, breaking the app). This is the highest-priority issue because it blocks deploy and masks every other finding until fixed.

**G2 -- P1 (cross-org leak via `tasks_user_select`): no `org_id` predicate on SELECT.**
Concrete failure mode using the supplied scenario: U1 belongs to both org_A and org_B. The app authenticates U1 with `auth.uid() = U1` while the user is "active" in org_A (e.g., the URL is `/orgs/org_A/tasks`). A query `SELECT * FROM tasks WHERE org_id = $current_org` is filtered server-side by RLS using `user_id = auth.uid()` -- but RLS happily returns the row (org_B, U1, "Resignation letter draft") because U1 owns it. If the app's `$current_org` filter is ever bypassed, omitted, mistyped, or attacker-controlled (e.g., a route that forgot the WHERE), org_B private data ships to a session active under org_A. **Compound tenancy is enforced only at the app layer; RLS provides zero defense in depth.** This is the exact class of leak the SOC2 "least-privilege at DB" control exists to catch.

**G3 -- P1 (cross-org write via `tasks_user_insert`): `WITH CHECK` lacks `org_id` membership check.**
U1 can `INSERT INTO tasks (org_id, user_id, title) VALUES ('org_C_uuid', U1, 'planted')` where U1 is **not a member of org_C**. `WITH CHECK (user_id = auth.uid())` passes. The row is now visible to anyone in org_C whose code naively does `SELECT * FROM tasks WHERE org_id = 'org_C'` -- and if/when org_C's own SELECT policy is later corrected to use membership, the malicious row is still there. This is a **write-side tenant escape**: U1 plants a row in a tenant they do not belong to. Severity is P1 even if no current code reads `tasks` for org_C, because policy DDL is a long-lived contract.

**G4 -- P1 (org pivot via `tasks_user_update`): row can change `org_id` mid-life.**
U1 owns task `(org_A, U1)`. U1 issues `UPDATE tasks SET org_id = 'org_B_uuid' WHERE id = $task_id`. `USING (user_id = auth.uid())` passes (U1 owns the row). `WITH CHECK (user_id = auth.uid())` passes (still U1). The row silently moves from org_A's tenancy to org_B's tenancy. A task containing org_A-private content (customer names, contract numbers, salaries) is now visible to org_B members the moment their SELECT policy is tightened to include membership joins. **This is the canonical compound-tenancy bug: USING and WITH CHECK both forget the column that defines the second tenancy dimension.**

**G5 -- P1 (`org_members` is the authoritative tenancy table and is unwritable through RLS): no INSERT/UPDATE/DELETE policies under FORCE RLS.**
`FORCE ROW LEVEL SECURITY` is on, no `INSERT`/`UPDATE`/`DELETE` policies exist, so even the table owner cannot mutate `org_members` through a normal connection. The migration provides **no documented path to add a member**, which silently forces every membership write to use `service_role` (full bypass). That is a privilege-escalation magnet: every callsite that adds members has root-level blast radius, and the audit trail conflates legitimate admin actions with potential abuse. Even worse, if a developer "fixes" this by adding a permissive INSERT policy (e.g., `WITH CHECK (user_id = auth.uid())`), any authenticated user can grant themselves membership to any org. The membership table is the **tenancy root**; it requires explicit admin-only write policies (e.g., `EXISTS (SELECT 1 FROM org_members om WHERE om.org_id = NEW.org_id AND om.user_id = auth.uid() AND om.role IN ('owner','admin'))`).

**G6 -- P1 (no membership join on `tasks` policies): predicate references `auth.uid()` but never asserts membership in `tasks.org_id`.**
Every `tasks` policy boils down to "you own the row." Combined with G3/G4, the correct predicate **must** be: `user_id = auth.uid() AND EXISTS (SELECT 1 FROM org_members WHERE org_id = tasks.org_id AND user_id = auth.uid())`. Without the membership join, the compound tenancy claim is false advertising.

**G7 -- P2 (data integrity -- no FKs): orphaned rows possible.**
`tasks.org_id`, `tasks.user_id`, `org_members.user_id`, `org_members.org_id` have **no foreign-key constraints**. Deleting an org leaves `tasks` rows pointing at a vanished tenancy. Worse, RLS policies that join `tasks → org_members` will quietly drop rows for vanished orgs, masking dangling data from observability. Add `REFERENCES auth.users(id) ON DELETE CASCADE` and `REFERENCES orgs(id) ON DELETE CASCADE` (assuming an `orgs` table exists or will).

**G8 -- P2 (`org_members.role` is `text` with no CHECK constraint): privilege strings are unvalidated.**
`role text DEFAULT 'member'` accepts any string. A typo (`'admin '` with trailing space) or accidental write (`role = 'OWNER'` instead of `'owner'`) creates a row that fails policy comparisons silently. Introduce a CHECK constraint or an enum: `role text NOT NULL DEFAULT 'member' CHECK (role IN ('owner','admin','member'))`.

**G9 -- P2 (no indexes on policy predicate columns): every RLS check becomes a seq scan.**
Once policies are corrected to use `EXISTS (SELECT 1 FROM org_members WHERE org_id = ? AND user_id = ?)`, that lookup needs an index. `org_members` PK is `(org_id, user_id)` -- that supports lookups by both, good. But `tasks` needs an index on `(org_id, user_id)` to scale once policies fan out. Without it, every query against `tasks` triggers a full scan to validate RLS.

**G10 -- P3 (perf -- `auth.uid()` STABLE re-evaluation in joined predicates): wrap in subselect.**
When policies grow to include `EXISTS (... WHERE user_id = auth.uid())`, PostgREST + RLS pattern recommends wrapping as `(SELECT auth.uid())` to let the planner cache the value once per query. Cosmetic but documented Supabase performance guidance.

---

## 4) Remediation per gap (migration-shaped SQL -- paste-ready)

A new migration file (suggested name `migrations/20260606150000_rls_compound_auth_fix.sql`) MUST replace the broken policies. Snippets below are syntactically valid and use the actual column names from the audited migration.

```sql
-- ============================================================================
-- migrations/20260606150000_rls_compound_auth_fix.sql
-- Replaces compound-auth policies on org_members and tasks.
-- Fixes G1 (invalid DDL), G2/G3/G4/G6 (missing org_id + membership checks),
-- G5 (org_members write policies), G7 (FKs), G8 (role CHECK), G9 (indexes).
-- ============================================================================

BEGIN;

-- G1: drop the invalid SELECT-with-WITH-CHECK policy and all the
-- single-dimension tasks policies so we can re-create them correctly.
DROP POLICY IF EXISTS tasks_user_select ON tasks;
DROP POLICY IF EXISTS tasks_user_insert ON tasks;
DROP POLICY IF EXISTS tasks_user_update ON tasks;
DROP POLICY IF EXISTS tasks_user_delete ON tasks;
DROP POLICY IF EXISTS org_members_select ON org_members;

-- G7: add foreign keys so deletes cascade and orphans become impossible.
-- (Assumes an `orgs` table exists. If not, create it in an earlier migration.)
ALTER TABLE org_members
  ADD CONSTRAINT org_members_user_id_fkey
    FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE,
  ADD CONSTRAINT org_members_org_id_fkey
    FOREIGN KEY (org_id) REFERENCES orgs(id) ON DELETE CASCADE;

ALTER TABLE tasks
  ADD CONSTRAINT tasks_user_id_fkey
    FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE,
  ADD CONSTRAINT tasks_org_id_fkey
    FOREIGN KEY (org_id) REFERENCES orgs(id) ON DELETE CASCADE;

-- G8: constrain role to a known vocabulary.
ALTER TABLE org_members
  ADD CONSTRAINT org_members_role_check
    CHECK (role IN ('owner', 'admin', 'member'));

-- G9: index the predicate columns RLS will hit on every tasks query.
CREATE INDEX IF NOT EXISTS tasks_org_user_idx ON tasks (org_id, user_id);

-- ============================================================================
-- org_members policies (G5): admin-gated writes; self-or-co-member reads.
-- The membership table is the tenancy root, so writes must be explicitly
-- gated on owner/admin role within the target org.
-- ============================================================================

-- SELECT: a user can see their own membership rows AND the membership rows
-- of orgs they belong to (so the UI can render co-members). Co-member visibility
-- is intentional; tighten to self-only if your product requires it.
CREATE POLICY org_members_select ON org_members
  FOR SELECT
  USING (
    user_id = (SELECT auth.uid())
    OR EXISTS (
      SELECT 1 FROM org_members self
      WHERE self.org_id = org_members.org_id
        AND self.user_id = (SELECT auth.uid())
    )
  );

-- INSERT: only owner/admin of the target org may add members.
-- This deliberately prevents a user from self-granting membership.
CREATE POLICY org_members_insert ON org_members
  FOR INSERT
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM org_members admin
      WHERE admin.org_id = org_members.org_id
        AND admin.user_id = (SELECT auth.uid())
        AND admin.role IN ('owner', 'admin')
    )
  );

-- UPDATE: only owner/admin may change a member's role; must remain in same org.
CREATE POLICY org_members_update ON org_members
  FOR UPDATE
  USING (
    EXISTS (
      SELECT 1 FROM org_members admin
      WHERE admin.org_id = org_members.org_id
        AND admin.user_id = (SELECT auth.uid())
        AND admin.role IN ('owner', 'admin')
    )
  )
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM org_members admin
      WHERE admin.org_id = org_members.org_id
        AND admin.user_id = (SELECT auth.uid())
        AND admin.role IN ('owner', 'admin')
    )
  );

-- DELETE: only owner/admin may remove members; users may remove themselves.
CREATE POLICY org_members_delete ON org_members
  FOR DELETE
  USING (
    user_id = (SELECT auth.uid())
    OR EXISTS (
      SELECT 1 FROM org_members admin
      WHERE admin.org_id = org_members.org_id
        AND admin.user_id = (SELECT auth.uid())
        AND admin.role IN ('owner', 'admin')
    )
  );

-- ============================================================================
-- tasks policies (G2, G3, G4, G6): EVERY clause checks BOTH user_id AND
-- org membership via org_members. SELECT/DELETE use USING only (G1 fix).
-- INSERT/UPDATE check membership in WITH CHECK so neither inserts into a
-- foreign org nor pivots an existing row across orgs.
-- ============================================================================

-- SELECT: own the row AND be a current member of the row's org.
-- Closes G2: U1 active in org_A cannot SELECT (org_B, U1) rows in the same
-- session unless they explicitly query as org_B; combined with the app's
-- org-context filter this becomes defense-in-depth, not the only line.
CREATE POLICY tasks_select ON tasks
  FOR SELECT
  USING (
    user_id = (SELECT auth.uid())
    AND EXISTS (
      SELECT 1 FROM org_members
      WHERE org_members.org_id = tasks.org_id
        AND org_members.user_id = (SELECT auth.uid())
    )
  );

-- INSERT: closes G3. user_id must be self AND target org must be one the
-- user is currently a member of. U1 inserting (org_C, U1, ...) is rejected.
CREATE POLICY tasks_insert ON tasks
  FOR INSERT
  WITH CHECK (
    user_id = (SELECT auth.uid())
    AND EXISTS (
      SELECT 1 FROM org_members
      WHERE org_members.org_id = tasks.org_id
        AND org_members.user_id = (SELECT auth.uid())
    )
  );

-- UPDATE: closes G4. Both old row (USING) and new row (WITH CHECK) must
-- satisfy ownership AND current-org membership. U1 cannot pivot a row from
-- org_A to org_B because WITH CHECK is evaluated against the *new* org_id
-- and would also need org membership in the new org. If U1 belongs to both
-- orgs the pivot would technically pass -- if that is undesirable, add a
-- column-level guard:
--   AND tasks.org_id = (SELECT org_id FROM tasks WHERE id = NEW.id)
-- or move org_id to immutable via a BEFORE UPDATE trigger.
CREATE POLICY tasks_update ON tasks
  FOR UPDATE
  USING (
    user_id = (SELECT auth.uid())
    AND EXISTS (
      SELECT 1 FROM org_members
      WHERE org_members.org_id = tasks.org_id
        AND org_members.user_id = (SELECT auth.uid())
    )
  )
  WITH CHECK (
    user_id = (SELECT auth.uid())
    AND EXISTS (
      SELECT 1 FROM org_members
      WHERE org_members.org_id = tasks.org_id
        AND org_members.user_id = (SELECT auth.uid())
    )
  );

-- DELETE: own the row AND be a current member of the row's org.
CREATE POLICY tasks_delete ON tasks
  FOR DELETE
  USING (
    user_id = (SELECT auth.uid())
    AND EXISTS (
      SELECT 1 FROM org_members
      WHERE org_members.org_id = tasks.org_id
        AND org_members.user_id = (SELECT auth.uid())
    )
  );

COMMIT;
```

**Optional hardening (recommended) -- immutable `tasks.org_id`:**

If product semantics say a task must never move between orgs, lock the column:

```sql
CREATE OR REPLACE FUNCTION prevent_tasks_org_pivot()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  IF NEW.org_id IS DISTINCT FROM OLD.org_id THEN
    RAISE EXCEPTION 'tasks.org_id is immutable (attempted pivot from % to %)',
      OLD.org_id, NEW.org_id;
  END IF;
  RETURN NEW;
END;
$$;

CREATE TRIGGER tasks_no_org_pivot
  BEFORE UPDATE ON tasks
  FOR EACH ROW
  EXECUTE FUNCTION prevent_tasks_org_pivot();
```

This closes G4 unambiguously even for users who belong to both source and destination orgs (the WITH CHECK approach above passes that edge case).

---

## 5) Follow-the-data trace

For each tenant-scoped table touched by the migration, trace every relationship and confirm the policy chain is unbroken.

- `org_members.user_id` → **auth.users.id**: no FK declared in migration; not RLS-leaky but integrity-leaky (orphan on user delete). **FLAG → G7 remediation adds the FK.**
- `org_members.org_id` → **orgs.id**: no FK declared; assumes `orgs` exists elsewhere. **FLAG → G7 remediation adds the FK; if no `orgs` table exists, that is a separate P1 omission.**
- `tasks.user_id` → **auth.users.id**: no FK declared. **FLAG → G7.**
- `tasks.org_id` → **orgs.id**: no FK declared. **FLAG → G7.**
- `tasks.org_id` ↔ `tasks.user_id` joint scope → **org_members(org_id, user_id)**: the membership table is the tenancy join. Current `tasks` policies never reference it. **FLAG → G6 remediation adds the EXISTS join.**
- Join/audit/log tables introduced by this migration: **none.** If a future migration adds `task_audit_log`, `task_versions`, `task_comments`, or any materialized view over `tasks`, each MUST receive identical compound-scope policies (same `user_id = auth.uid() AND EXISTS … org_members …` shape) or the leak reappears.
- Soft-delete shadow tables: **none.** If introduced, same policy shape applies.
- Realtime publication (`supabase_realtime`): not declared here, but if `tasks` is later added to the publication, the RLS policies above govern realtime row delivery -- re-verify the SELECT policy in that context.

No unprotected join paths exist *after the remediation migration* applies. Before it applies, the entire compound-tenancy chain is broken at every link.

---

## 6) SECURITY DEFINER function audit

The audited migration declares **no `SECURITY DEFINER` functions**, so there is nothing to verdict from this DDL.

Forward-looking guards (apply if the team later adds them):
- Every `SECURITY DEFINER` function added against this schema MUST begin with `SET search_path = pg_catalog, public` to prevent search_path hijacking.
- Every such function MUST validate `auth.uid()` and membership in the target org explicitly; the function runs as table owner and bypasses RLS by definition.
- The `prevent_tasks_org_pivot()` helper proposed in §4 is `SECURITY INVOKER` (default) -- correct, since it must run under the caller's RLS context.

---

## 7) service_role usage audit

No backend-repo paths are listed in this audit scope (single-repo migration eval), so the audit cannot enumerate `createClient(SUPABASE_SERVICE_ROLE_KEY)` callsites directly. Two forward-looking concerns from the migration itself:

- **Forced bypass for `org_members` writes (G5 side effect):** because no INSERT/UPDATE/DELETE policies exist on `org_members`, the only way to add a member today is through `service_role`. **Verdict: UNJUSTIFIED-by-default** -- the bypass exists because the policy is missing, not because the operation requires it. After G5 remediation, membership writes route through authenticated owner/admin sessions and `service_role` returns to admin/webhook/cron use only.
- **No documented service_role callsite for `tasks`:** if any backend code uses `service_role` to write to `tasks` (e.g., cron-imported tasks), each callsite MUST validate `(org_id, user_id)` tuple consistency server-side before insert. The migration cannot enforce this -- backend audit owns it.

Recommended follow-up: a `code-locate` pass over the backend repo for `SUPABASE_SERVICE_ROLE_KEY` / `createClient` / `createServiceClient` to produce an explicit justified/unjustified verdict per callsite. Multi-repo `SOURCE_OF_TRUTH.md ## Repositories` would normally name the backend repo; if missing, route to `task-init` or `state-reconcile` to add it.

---

## 8) PROPOSED block draft for any policy decisions that need locking

The audit surfaces one tradeoff that the team must lock before the remediation migration ships:

```text
<!-- PROPOSED by rls-auth-boundary-auditor: -->
## Locked decisions

### D-N: tasks.org_id mutability under compound auth -- immutable vs membership-gated

Context:
Current `tasks` UPDATE policy (after remediation) checks ownership + membership
on both USING (old row) and WITH CHECK (new row). A user who belongs to BOTH
the source AND destination orgs can still move a row across orgs via UPDATE.

Options:
- A) Membership-gated only (current §4 remediation): allow org pivot if the
     user is a member of both old and new org. Simpler policy; preserves the
     "move task between my orgs" UX if that is a product feature.
- B) Immutable column (BEFORE UPDATE trigger from §4 optional hardening):
     `tasks.org_id` cannot change post-insert; pivots require delete+re-insert,
     creating an explicit audit event. Stronger isolation; rules out subtle
     leak vectors where a user mid-pivots a row to leak content into another
     org they joined later.

Trade-off:
- Option A: lighter, supports a possibly-useful UX, but policy reviewers must
  remember that compound-org users can pivot rows.
- Option B: stronger contract (a row's tenancy is set at creation, period),
  but forces an explicit data flow for the "move to another org" feature if
  it ever exists.

Recommendation: Option B unless product explicitly requires cross-org pivot.
Solo-founder default: Option B (simpler audit story, no realistic UX cost).

Status: PROPOSED -- requires explicit lock via `decision-interview` before the
remediation migration is committed.
<!-- /PROPOSED -->
```

Also PROPOSED for `TASK_STATE.md ## Risks to watch`:

```text
<!-- PROPOSED by rls-auth-boundary-auditor: -->
- RLS compound-auth gap on `tasks` and `org_members`: migration
  `20260606140001_tasks_with_org_scope.sql` ships per-user-only predicates
  that leak across orgs (G2/G3/G4/G6) AND contains invalid DDL on
  `tasks_user_select` (G1) that blocks the migration from applying. Blocking
  pre-deploy. Remediation migration drafted in RLS_AUDIT.md.
<!-- /PROPOSED -->
```

And PROPOSED for `IMPLEMENTATION_PLAN.md ## Risks and mitigations`:

```text
<!-- PROPOSED by rls-auth-boundary-auditor: -->
- Risk: shipping `20260606140001_tasks_with_org_scope.sql` as-is would either
  (a) fail to apply due to invalid SELECT-with-WITH-CHECK DDL, or (b) if
  patched naively, ship cross-org leak via missing org_id predicates.
  Mitigation: replace with the remediation migration drafted in RLS_AUDIT.md;
  add the org pivot decision (D-N above) to `decision-interview` queue.
<!-- /PROPOSED -->
```

---

## 9) `<task>/RLS_AUDIT.md` content draft

Full file body, ready for `approve-proposed` to write into the active task folder:

```markdown
# RLS_AUDIT.md -- Compound-auth audit for tasks + org_members

Owner: rls-auth-boundary-auditor
Auth model: auth.uid() (Supabase)
Tenant scope shape: compound (per-user-within-org)
Migrations audited: migrations/20260606140001_tasks_with_org_scope.sql
Aggregate verdict: **FAIL** (P0 + multiple P1)

## Per-table posture

| table | RLS | FORCE | SELECT | INSERT | UPDATE | DELETE | tenant predicate | verdict |
|---|---|---|---|---|---|---|---|---|
| org_members | yes | yes | self-only | MISSING | MISSING | MISSING | user-only | FAIL |
| tasks | yes | yes | INVALID DDL | user-only WITH CHECK | user-only USING+CHECK | user-only USING | user-only | FAIL |

## Gaps (severity-ordered)

- G1 (P0): tasks_user_select uses FOR SELECT … WITH CHECK -- invalid in PostgreSQL; migration aborts on apply.
- G2 (P1): tasks SELECT lacks org_id predicate -- U1 can SELECT (org_B, U1) rows while session is "in" org_A; no DB-side compound enforcement.
- G3 (P1): tasks INSERT WITH CHECK lacks org_id membership -- U1 can plant rows in org_C they do not belong to.
- G4 (P1): tasks UPDATE allows org_id pivot -- owned row can be moved from org_A to org_B without re-validating membership.
- G5 (P1): org_members has no INSERT/UPDATE/DELETE policies under FORCE RLS -- forces service_role bypass for every membership write; tenancy root is unmanageable through normal auth.
- G6 (P1): tasks policies never join org_members -- compound tenancy is claimed but never enforced.
- G7 (P2): no foreign keys on org_members or tasks -- orphans possible; RLS joins silently mask dangling data.
- G8 (P2): org_members.role text is unconstrained -- silent role typos defeat policy comparisons.
- G9 (P2): no index supporting RLS predicate lookups on tasks (org_id, user_id).
- G10 (P3): auth.uid() not wrapped in (SELECT …) inside EXISTS -- minor planner caching loss.

## Remediation

Single migration: `migrations/20260606150000_rls_compound_auth_fix.sql`. See the
full DDL in the audit output (drops broken policies, adds FKs + CHECK +
indexes, re-creates org_members policies as admin-gated, re-creates tasks
policies with compound (user_id AND membership) predicate, optional immutable
org_id trigger).

## Follow-the-data trace

- org_members.user_id → auth.users.id: FK missing (G7).
- org_members.org_id → orgs.id: FK missing (G7).
- tasks.user_id → auth.users.id: FK missing (G7).
- tasks.org_id → orgs.id: FK missing (G7).
- tasks ↔ org_members compound scope: not joined in any policy (G6).
- No join/audit/log/materialized-view tables in migration scope.

## SECURITY DEFINER audit

None declared in migration. Forward guards documented for future additions.

## service_role audit

No backend-repo enumeration in this audit scope. G5 forces unjustified
service_role bypass until remediation lands.

## Decisions raised

- D-N (PROPOSED): tasks.org_id mutability -- immutable trigger vs membership-gated UPDATE. Awaits decision-interview lock.

## Audit history

| timestamp (UTC) | run_id | migrations audited | verdict |
|---|---|---|---|
| 2026-06-05 | rls-audit-001 | 20260606140001_tasks_with_org_scope.sql | FAIL |
```

---

## 10) Recommended next command

`decision-interview` -- the audit surfaced a genuine policy tradeoff (D-N: `tasks.org_id` mutability, Option A membership-gated vs Option B immutable trigger) that must be locked before the remediation migration is written. After D-N locks, route to `implementation-plan` to slice the remediation work (one slice for the remediation migration, one for backend service_role audit, one for an integration test that asserts U1 cannot leak across orgs). Then `approve-proposed` to persist the PROPOSED blocks above and the RLS_AUDIT.md draft.

Verified against `commands/` directory: `decision-interview.md`, `implementation-plan.md`, `approve-proposed.md` all exist.

---

### Artifact changes

- `<task>/RLS_AUDIT.md` -- **PROPOSED** (create). Full body in §9 above. L1 substrate access means this persona cannot write it directly; `approve-proposed` promotes it.
- `<task>/DECISIONS.md ## Locked decisions` -- **PROPOSED** (update-delta). Adds D-N draft per §8 first block. Awaits `decision-interview` to lock.
- `<task>/TASK_STATE.md ## Risks to watch` -- **PROPOSED** (update-delta). Adds one bullet per §8 second block.
- `<task>/IMPLEMENTATION_PLAN.md ## Risks and mitigations` -- **PROPOSED** (update-delta). Adds one bullet per §8 third block.

No APPLIED writes (L1 persona; PROPOSED-only).

### Command transcript

- Loaded SKILL.md + mandatory bootstrap (LLM execution contract, Editor mode policy, Global output contract, Cross-cutting guardrails).
- Parsed migration; identified P0 (invalid SELECT-with-WITH-CHECK DDL) before any policy analysis -- flagged so the team does not mistake "migration applied" for "policies working."
- Worked the supplied U1/U2 scenario through each policy clause; confirmed 4 distinct leak/pivot paths plus 1 tenancy-root management gap.
- Verified all recommended next commands exist in `commands/` directory.

### Handoff

```text
Run now: /decision-interview
Mode: Ask
Work complexity: HIGH
Reason: D-N (tasks.org_id mutability) must lock before the remediation migration is written; auth-boundary correctness is the bar.
```
