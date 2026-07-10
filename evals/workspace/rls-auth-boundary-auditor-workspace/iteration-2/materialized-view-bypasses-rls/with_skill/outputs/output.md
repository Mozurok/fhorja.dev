# RLS + Auth Boundary Audit -- `20260606140002_notes_summary_view.sql`

**Auditor:** `rls-auth-boundary-auditor`
**Migration under audit:** `migrations/20260606140002_notes_summary_view.sql`
**Auth model:** `auth.uid()` (Supabase default; JWT-derived)
**Tenant scope shape:** per-user
**Aggregate verdict:** **FAIL** (1 × P1 confirmed tenant leakage via materialized view; 1 × P1 grant on bypass surface; 1 × P2 missing FOR UPDATE/DELETE coverage; 1 × P2 schema exposure)
**Concrete scenario answer (U1 issues `SELECT * FROM mv_notes_summary;` from supabase-js with `authenticated` role):** **U1 sees the (user_id, note_count, last_note_at) row for EVERY user in the system -- not just their own.** The materialized view stores its result set physically; RLS on `notes` is never re-evaluated when the view is read. The view has no RLS of its own, and `GRANT SELECT ... TO authenticated` opens it to every signed-in user. This is a cross-tenant leak of per-user activity metadata (count + last-active timestamp), which is also a behavioural-analytics PII fingerprint.

---

## 1. Tenant-scoped table inventory

Every object touched by this migration, annotated with tenant scope:

- `public.notes` -- base table -- **per-user** (column `user_id` references `auth.uid()`).
- `public.mv_notes_summary` -- **materialized view derived from `notes`** -- **per-user logically, but materialized views are NOT tables and do NOT inherit RLS from their source.** This is the primary failure surface.
- `public.mv_notes_summary_pkey` -- unique index on `mv_notes_summary(user_id)` -- not itself a security boundary, but its existence enables `REFRESH MATERIALIZED VIEW CONCURRENTLY`, which is relevant to remediation choice.

No table from the migration diff is omitted. The materialized view is included as a first-class object in the posture table below because -- per the persona's follow-the-data discipline -- an object derived from an RLS-protected table inherits NONE of that protection by default and must be audited independently.

---

## 2. Per-object policy posture table

| object | kind | RLS enabled | FORCE applied | SELECT policy | INSERT policy (USING + WITH CHECK) | UPDATE policy (USING + WITH CHECK) | DELETE policy | tenant predicate present | verdict |
|---|---|---|---|---|---|---|---|---|---|
| `public.notes` | table | YES | YES | `notes_select_own` USING `user_id = auth.uid()` | `notes_insert_own` WITH CHECK `user_id = auth.uid()` (no USING needed for INSERT) | **MISSING** | **MISSING** | YES (on existing policies) | **GAP** (P2: no UPDATE/DELETE policies → both operations denied-by-default under FORCE, which is safe-by-default but almost certainly unintended for a notes app; explicit deny is fine, silent deny is a footgun) |
| `public.mv_notes_summary` | materialized view | **N/A -- RLS CANNOT be enabled on a materialized view** | **N/A** | **N/A -- MVs do not support `CREATE POLICY`** | **N/A** | **N/A** | **N/A** | **NO -- no tenant predicate enforced at read time; the MV is a flat snapshot that exposes ALL users' rows to anyone with SELECT** | **FAIL** (P1) |

Posture summary:
- `notes` is correctly hardened at the base-table layer (RLS + FORCE + SELECT/INSERT with tenant predicate and proper WITH CHECK on INSERT). The only base-table gaps are the missing UPDATE and DELETE policies.
- `mv_notes_summary` is the load-bearing failure. **Postgres materialized views do not support row-level security policies.** They are not regular views (which can use `security_invoker=true` to inherit caller identity for RLS evaluation against the underlying table). A materialized view is a stored relation populated by the owner role at `REFRESH` time, and `SELECT` against it does not re-execute the defining query against base tables -- it reads the stored rows. Therefore RLS on `notes` is bypassed by construction whenever a client queries the MV.

---

## 3. Gaps and severities

1. **P1 -- Materialized view bypasses RLS on `notes`.** `mv_notes_summary` is built from `notes` (which is RLS-FORCE protected with `user_id = auth.uid()`), but the MV stores the aggregated result set physically. At `SELECT` time Postgres does not re-evaluate the defining query, so the `notes_select_own` policy is never consulted. **Concrete failure mode:** U1 runs `SELECT * FROM mv_notes_summary;` from the `authenticated` role; U1 receives one row per user in the system, exposing `user_id`, `note_count`, and `last_note_at` for every user. This is cross-tenant data leakage of per-user activity metadata (a behavioural fingerprint and a tenant-enumeration vector). Affected: `mv_notes_summary`. Severity: **P1**.

2. **P1 -- `GRANT SELECT ON mv_notes_summary TO authenticated` opens the bypass surface to every signed-in user.** Even if remediation #1 wraps the MV behind a `security_invoker` view, the raw grant on the MV itself remains a direct read path that any authenticated client can target by name (`from('mv_notes_summary')` in supabase-js). **Concrete failure mode:** a single forgotten `REVOKE` keeps the leak alive after the wrapper view is introduced. Affected: `mv_notes_summary`. Severity: **P1**.

3. **P2 -- `notes` has no UPDATE policy and no DELETE policy under `FORCE ROW LEVEL SECURITY`.** Under FORCE, the absence of a policy for an operation means **all** non-superuser callers (including the table owner role used by the migration) are denied that operation. **Concrete failure mode:** U1 calls `supabase.from('notes').update({ body: 'edit' }).eq('id', noteId)` and silently gets zero rows updated, with no error, because no policy permits the operation. Mirror failure for DELETE. This is a denial-of-functionality bug, not a leakage bug, but it is P2 because it ships broken CRUD that fails open at the API layer (PostgREST returns `[]` rather than 403, so callers cannot distinguish "not yours" from "no rows match"). Affected: `notes`. Severity: **P2**.

4. **P2 -- Materialized view is in the `public` schema and exposed to PostgREST.** By default Supabase exposes the `public` schema via PostgREST. Combined with finding #1, this means the bypass is reachable from any browser-side supabase-js client without any backend route. Even after remediation, the MV should live in a non-exposed schema (e.g. `private`) so that the only read path is the wrapper view. Affected: `mv_notes_summary`. Severity: **P2**.

5. **P3 -- `notes.created_at` is `DEFAULT now()` but not `NOT NULL`.** Not a security gap; flagged for completeness because the MV's `MAX(created_at)` will silently return `NULL` for users whose rows have null timestamps. Affected: `notes`. Severity: **P3** (data-integrity hygiene, not RLS).

---

## 4. Remediation per gap (migration-shaped)

A single follow-up migration. Suggested filename: `migrations/20260606140003_notes_summary_view_rls_fix.sql`.

```sql
-- =====================================================================
-- Remediation for P1 #1 + P1 #2 + P2 #4: replace the directly-queryable
-- materialized view with a security_invoker wrapper view that re-evaluates
-- RLS against `notes` for every caller.
--
-- Strategy:
--   (a) Move the materialized view into a private schema not exposed by
--       PostgREST, and revoke all grants on it from PUBLIC/authenticated.
--   (b) Create a `security_invoker = true` view in `public` whose defining
--       query re-aggregates from `notes`. Because security_invoker views
--       execute their query with the caller's privileges, the underlying
--       `notes_select_own` RLS policy is enforced and each caller sees
--       exactly one row (their own).
--   (c) Optionally keep the materialized view for server-side analytics
--       jobs that run as service_role; service_role bypasses RLS, which is
--       the justified usage path here.
-- =====================================================================

-- (a) Private schema + relocate the MV.
CREATE SCHEMA IF NOT EXISTS private;
REVOKE ALL ON SCHEMA private FROM PUBLIC, anon, authenticated;

REVOKE ALL ON public.mv_notes_summary FROM PUBLIC, anon, authenticated;
ALTER MATERIALIZED VIEW public.mv_notes_summary SET SCHEMA private;
-- mv_notes_summary_pkey moves with the MV automatically.

-- (b) security_invoker wrapper view in public. Each caller's SELECT against
--     this view re-runs the aggregation against `notes` under their identity,
--     so RLS on `notes` filters rows BEFORE aggregation: each caller sees at
--     most one row, scoped to their own user_id.
CREATE OR REPLACE VIEW public.notes_summary
WITH (security_invoker = true) AS
SELECT user_id,
       COUNT(*)        AS note_count,
       MAX(created_at) AS last_note_at
FROM   public.notes
WHERE  user_id = auth.uid()  -- defensive predicate; RLS already enforces this
GROUP BY user_id;

GRANT SELECT ON public.notes_summary TO authenticated;

-- =====================================================================
-- Remediation for P2 #3: add explicit UPDATE and DELETE policies on notes
-- so authenticated users can modify and delete their own rows. Under
-- FORCE ROW LEVEL SECURITY these must be declared explicitly; otherwise
-- writes silently no-op.
-- =====================================================================

CREATE POLICY notes_update_own
  ON public.notes
  FOR UPDATE
  USING      (user_id = auth.uid())   -- which rows can be targeted
  WITH CHECK (user_id = auth.uid());  -- prevents re-homing a row to another user

CREATE POLICY notes_delete_own
  ON public.notes
  FOR DELETE
  USING (user_id = auth.uid());

-- =====================================================================
-- Optional hardening (P3 hygiene + defence in depth)
-- =====================================================================

-- Ensure created_at is never null so MAX(created_at) is meaningful.
ALTER TABLE public.notes
  ALTER COLUMN created_at SET NOT NULL;

-- Ensure notes.user_id always references a real auth.users row so the MV
-- and wrapper view cannot accumulate dangling user_ids.
ALTER TABLE public.notes
  ADD CONSTRAINT notes_user_id_fkey
  FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;

-- If the materialized view is kept for analytics, schedule REFRESH from a
-- service_role context (e.g. pg_cron / Supabase scheduled function) and
-- document it in DECISIONS.md. Example:
-- SELECT cron.schedule('refresh_notes_summary', '*/15 * * * *',
--   $$ REFRESH MATERIALIZED VIEW CONCURRENTLY private.mv_notes_summary $$);
```

**Why `security_invoker = true` is the load-bearing fix.** Regular Postgres views default to `security_definer` semantics (the view's defining query runs with the view owner's privileges, so the owner's view of the underlying tables is what's returned). `security_invoker = true` (Postgres 15+, supported on Supabase) flips this so the defining query runs with the **caller's** privileges, which means RLS policies on the underlying tables are evaluated against the caller. This is the canonical Supabase pattern for exposing aggregates over RLS-protected tables. Materialized views do NOT support `security_invoker` because their data is precomputed; they must be hidden behind a wrapper view or behind a server-only path.

---

## 5. Follow-the-data trace

For each object derived from or referencing an RLS-protected table:

- `notes` → `mv_notes_summary` (defining query `SELECT user_id, COUNT(*), MAX(created_at) FROM notes GROUP BY user_id`): **FAIL.** Materialized view stores rows physically; RLS on `notes` is not re-evaluated at read time. GRANT to `authenticated` exposes every user's aggregate row to every authenticated caller. **This is the primary leak.**
- `notes` → `mv_notes_summary_pkey` (unique index on `(user_id)`): not a security boundary on its own, but its existence on a per-user-keyed MV confirms one stored row per user -- i.e. enumerating the MV enumerates the user base.
- `notes` → `auth.users` (implicit; no FK declared in the migration): **GAP (P3).** The migration declares `user_id uuid NOT NULL` without an FK to `auth.users(id)`. Orphan `user_id` values can accumulate; not an RLS bypass, but a data-integrity smell that compounds the MV leak by exposing stale identifiers. Remediation adds the FK with `ON DELETE CASCADE`.
- `notes` → no join tables, no audit/log tables, no soft-delete shadow tables declared in this migration: PASS by absence.
- `notes` → triggers / functions: none declared in this migration. See §6.

After remediation:
- `notes` → `private.mv_notes_summary` (in non-exposed schema, no grants to `anon`/`authenticated`): PASS -- only reachable from `service_role` / `postgres`.
- `notes` → `public.notes_summary` (security_invoker view): PASS -- RLS on `notes` is enforced for every caller; aggregation runs against the RLS-filtered row set, so each caller sees at most one row.

---

## 6. SECURITY DEFINER function audit

The migration declares **zero** `SECURITY DEFINER` functions. No `CREATE FUNCTION` / `CREATE PROCEDURE` statements appear in the DDL.

Verdict per occurrence: **N/A -- no SECURITY DEFINER functions introduced by this migration.**

Caveat for the next audit run: if a future migration introduces a function to refresh `mv_notes_summary` from a non-superuser context, it will almost certainly need `SECURITY DEFINER` (because `REFRESH MATERIALIZED VIEW` requires ownership) and MUST then carry:
- `SET search_path = pg_catalog, public` (or `pg_catalog, private` once the MV is moved) to block search_path hijacking,
- an explicit caller-identity guard at function entry (e.g. `IF auth.role() <> 'service_role' THEN RAISE EXCEPTION ...`),
- no dynamic SQL built from caller input.

---

## 7. service_role usage audit

The migration is pure DDL; it contains no application code, so there are no `createClient(..., SUPABASE_SERVICE_ROLE_KEY)` call sites to audit in this diff.

Verdict per occurrence: **N/A -- no service_role call sites in this migration.**

Forward-looking note: the recommended remediation pattern (keep the materialized view in `private` for analytics, refresh on a schedule) implies a **future** service_role path -- either a scheduled `pg_cron` job (which runs as `postgres`, not `authenticated`, so it bypasses RLS by design -- **justified**) or a Supabase Edge Function refresh runner (which would use the service_role key -- **justified** if scoped to the refresh call only). Both are acceptable; both should be documented in `DECISIONS.md` when introduced.

---

## 8. PROPOSED block draft

```markdown
<!-- PROPOSED by rls-auth-boundary-auditor: append under DECISIONS.md ## Locked decisions -->
### D-N: Aggregates over RLS-protected tables use `security_invoker` views, not materialized views in `public`

**Context.** Migration `20260606140002_notes_summary_view.sql` introduced `public.mv_notes_summary` derived from the RLS-protected `notes` table and granted `SELECT` to the `authenticated` role. Materialized views in Postgres do NOT support row-level security policies and do NOT re-evaluate their defining query at SELECT time; they store the result set physically. Granting `SELECT` on such an MV to `authenticated` therefore bypasses RLS on the source table and leaks per-user aggregates to every signed-in user.

**Decision.** For any aggregate exposed to client roles (`anon`, `authenticated`) over an RLS-protected base table, the canonical pattern is a **`security_invoker = true` view in `public`**, whose defining query re-aggregates from the base table on every SELECT. Materialized views MAY exist for performance, but ONLY in a non-exposed schema (`private`), with all grants revoked from `anon` and `authenticated`, refreshed from a `service_role` / `postgres` context (`pg_cron`, scheduled Edge Function).

**Alternatives considered.**
- (a) Wrap MV behind a per-row WHERE-filtered view granted to `authenticated`. Rejected -- still relies on the MV's stored snapshot being trustworthy; one forgotten `REVOKE` on the MV reopens the bypass.
- (b) Add a `RULE` or `INSTEAD OF` trigger to the MV to filter at read time. Rejected -- not supported on materialized views and would not survive `REFRESH`.
- (c) Drop the MV entirely; compute aggregate inline in a `security_invoker` view. Acceptable for low-volume aggregates like `notes_summary`; chosen as the immediate remediation. MV becomes opt-in only when measured query latency justifies the operational cost.

**Consequences.** All future aggregate exposures on RLS-protected tables MUST follow this pattern. CI / repo-consistency-sweep gains a rule: any `CREATE MATERIALIZED VIEW` in a migration must either land in a non-`public` schema OR have an accompanying `REVOKE ... FROM authenticated, anon` and a wrapper view in `public`.
```

```markdown
<!-- PROPOSED by rls-auth-boundary-auditor: append under TASK_STATE.md ## Risks to watch -->
- **R-MV-RLS-BYPASS** -- Materialized views derived from RLS-protected tables silently bypass RLS at read time. Any future `CREATE MATERIALIZED VIEW` in this codebase MUST be reviewed against D-N before grants are issued. Current incidence: `mv_notes_summary` (remediation migration `20260606140003_notes_summary_view_rls_fix.sql` proposed).
```

```markdown
<!-- PROPOSED by rls-auth-boundary-auditor: append under IMPLEMENTATION_PLAN.md ## Risks and mitigations -->
- **Risk:** Materialized views bypass RLS; the current `mv_notes_summary` leaks per-user aggregates to all authenticated callers.
- **Mitigation:** Ship remediation migration `20260606140003_notes_summary_view_rls_fix.sql` BEFORE `20260606140002_notes_summary_view.sql` is deployed to any non-local environment. Move the MV to schema `private`, replace with `security_invoker` view `public.notes_summary`, and add explicit UPDATE/DELETE policies on `notes`. Verify with the `mv_notes_summary` scenario test (U1 reads → exactly one row, theirs).
```

---

## 9. `<task>/RLS_AUDIT.md` content draft

```markdown
# RLS Audit -- notes + mv_notes_summary

**Status:** FAIL (block deploy until remediation migration ships)
**Migration(s) audited:** `migrations/20260606140002_notes_summary_view.sql`
**Auth model:** `auth.uid()` (Supabase default)
**Tenant scope:** per-user

## Headline finding
`public.mv_notes_summary` is a materialized view derived from the RLS-protected `public.notes` table and granted `SELECT` to the `authenticated` role. **Materialized views in Postgres do not honour RLS on their source tables**: they store the defining query's result set physically and serve it without re-evaluation. The `notes_select_own` policy is therefore never consulted when the MV is read, and any authenticated user can `SELECT * FROM mv_notes_summary` to obtain `(user_id, note_count, last_note_at)` for every user in the system. This is a P1 cross-tenant data leak and tenant-enumeration vector.

## Per-object posture
| object | kind | RLS | FORCE | SELECT | INSERT (U+WC) | UPDATE (U+WC) | DELETE | tenant pred | verdict |
|---|---|---|---|---|---|---|---|---|---|
| `public.notes` | table | yes | yes | own | own (WC) | MISSING | MISSING | yes | GAP (P2) |
| `public.mv_notes_summary` | matview | N/A | N/A | N/A | N/A | N/A | N/A | NO | FAIL (P1) |

## Gaps (severity-ordered)
1. **P1** -- `mv_notes_summary` bypasses RLS on `notes`; GRANT to `authenticated` exposes all users' aggregates to all signed-in users.
2. **P1** -- `GRANT SELECT ON mv_notes_summary TO authenticated` is the direct bypass surface and must be revoked.
3. **P2** -- `notes` lacks UPDATE and DELETE policies; under FORCE RLS, updates and deletes silently no-op (denial-of-functionality bug shipping as a green migration).
4. **P2** -- MV lives in `public` (PostgREST-exposed); even after wrapper-view fix, MV should move to `private` schema.
5. **P3** -- `notes.created_at` is nullable; `notes.user_id` lacks FK to `auth.users`.

## Remediation
See migration `20260606140003_notes_summary_view_rls_fix.sql` (sketched in the audit response §4). Net effect:
- MV moves to schema `private`, grants revoked from `authenticated` / `anon`.
- New `public.notes_summary` view with `security_invoker = true` re-aggregates from `notes` under caller identity; `notes_select_own` filters rows BEFORE aggregation, so each caller sees at most one row (their own).
- Explicit `notes_update_own` and `notes_delete_own` policies added with matching USING + WITH CHECK predicates.
- `notes.created_at NOT NULL`; `notes.user_id` FK to `auth.users(id) ON DELETE CASCADE`.

## Validation scenario (acceptance test)
As user U1 from supabase-js (`authenticated` role):
1. `SELECT * FROM public.notes_summary;` → returns exactly 1 row with `user_id = U1`, even if U2..Un have notes.
2. `SELECT * FROM private.mv_notes_summary;` → permission denied.
3. `UPDATE public.notes SET body='x' WHERE id=<own note id>;` → 1 row affected.
4. `UPDATE public.notes SET body='x' WHERE id=<U2's note id>;` → 0 rows affected (RLS filters target set).
5. `INSERT INTO public.notes(user_id, body) VALUES(<U2's uid>, 'gotcha');` → error (WITH CHECK violation).

## Audit history
| timestamp (UTC) | run_id | migrations audited | aggregate verdict |
|---|---|---|---|
| 2026-06-05T00:00:00Z | rls-audit-2026-06-05-01 | `20260606140002_notes_summary_view.sql` | **FAIL** (1×P1 leakage, 1×P1 grant, 2×P2, 1×P3) |
```

---

## 10. Recommended next command

**`decision-interview`** -- because the audit surfaces a genuine policy-pattern tradeoff (proposed D-N: "aggregates over RLS-protected tables use `security_invoker` views, not materialized views in `public`") that should be locked before remediation ships, and because the choice between "drop the MV entirely" vs "keep the MV in `private` for analytics" is a real decision with operational and cost consequences that only Bruno can make.

If Bruno wants to skip the decision-locking step and accept the proposed pattern as-is, **`approve-proposed`** is the alternative -- it will write `RLS_AUDIT.md`, the D-N PROPOSED block in `DECISIONS.md`, and the risk entries in `TASK_STATE.md` / `IMPLEMENTATION_PLAN.md` in one atomic step. Then **`implementation-plan`** slices the remediation migration into a deployable unit.

Both `decision-interview`, `approve-proposed`, and `implementation-plan` are verified present in `commands/`.

---

### Artifact changes

- `PROPOSED` -- `DECISIONS.md ## Locked decisions` -- append D-N (aggregates pattern). Body in §8.
- `PROPOSED` -- `TASK_STATE.md ## Risks to watch` -- append R-MV-RLS-BYPASS. Body in §8.
- `PROPOSED` -- `IMPLEMENTATION_PLAN.md ## Risks and mitigations` -- append MV-bypass mitigation row. Body in §8.
- `PROPOSED` -- `<task>/RLS_AUDIT.md` -- full body in §9.
- `SKIP` -- no direct substrate writes at L1 per persona contract.

### Command transcript

1. Loaded `rls-auth-boundary-auditor/SKILL.md` and applied Steps 1–9 to the supplied migration.
2. Inventoried 1 base table (`notes`) + 1 derived object (`mv_notes_summary`); confirmed MV is the load-bearing failure surface because Postgres MVs do not honour source-table RLS and have no `CREATE POLICY` support.
3. Verified the U1 scenario answer analytically against Postgres semantics: MV stores rows physically, `GRANT SELECT ... TO authenticated` exposes the whole result set → U1 sees every user's aggregate.
4. Produced FAIL verdict, migration-shaped remediation using `security_invoker` wrapper view + schema relocation + missing UPDATE/DELETE policies, and 3 PROPOSED substrate blocks for owner-command promotion.

### Handoff

**Verdict:** FAIL -- do not deploy `20260606140002_notes_summary_view.sql` to any non-local environment until `20260606140003_notes_summary_view_rls_fix.sql` ships in the same deploy. The materialized view leaks every user's `(user_id, note_count, last_note_at)` to every signed-in user.

**Run now:** `decision-interview` to lock D-N (aggregates pattern), then `approve-proposed` to persist `RLS_AUDIT.md` + risk entries, then `implementation-plan` to slice the remediation migration.

**If skipping the decision-lock step:** `approve-proposed` directly, then `implementation-plan`.
