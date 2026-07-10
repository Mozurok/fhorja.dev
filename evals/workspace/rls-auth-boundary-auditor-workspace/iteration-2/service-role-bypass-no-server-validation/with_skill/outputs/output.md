# RLS + Auth Boundary Audit -- `documents` migration + `list-org-docs` Edge Function

Scope:
- Migration: `migrations/20260606140003_documents.sql` (single table: `documents`)
- Backend code: `supabase/functions/list-org-docs/index.ts` (Edge Function using `SUPABASE_SERVICE_ROLE_KEY`)
- Auth model: default Supabase (`auth.uid()`); tenant shape: per-org (compound user-within-org via `org_members`)

Headline verdict: **FAIL**. The migration itself is policy-clean for the SELECT path, but the Edge Function holds a **service_role client** and uses a **caller-supplied `org_id`** as the only filter. RLS is bypassed entirely. Any authenticated (or unauthenticated, depending on function gating) caller can read every row in `documents` for any `org_id` they name. The clean migration is load-bearing only if the SELECT path actually goes through RLS; this call site is the bypass.

---

## 1. Tenant-scoped table inventory

- `documents` -- **per-org** (rows are scoped by `org_id`; secondary `user_id` is informational, not the tenant boundary). Touched directly by the migration and by the Edge Function.
- `org_members` -- **per-org membership join table** (referenced by the SELECT policy; assumed to exist from a prior migration). Tenant scope: compound (user within org). NOT in this migration diff; flagged for follow-the-data confirmation that it has its own RLS posture.

No other tables are introduced by `20260606140003_documents.sql`.

---

## 2. Per-table policy posture table

| table | RLS enabled | FORCE applied | SELECT policy | INSERT policy (USING + WITH CHECK) | UPDATE policy (USING + WITH CHECK) | DELETE policy | tenant predicate present | verdict |
|---|---|---|---|---|---|---|---|---|
| `documents` | YES | YES | `docs_select`: `USING (org_id IN (SELECT org_id FROM org_members WHERE user_id = auth.uid()))` | **MISSING** | **MISSING** | **MISSING** | YES (SELECT only) | **FAIL** |
| `org_members` (referenced, not in diff) | UNKNOWN (not in this migration) | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | n/a here | **GAP -- verify** |

Notes:
- `documents` correctly enables RLS and applies `FORCE ROW LEVEL SECURITY` (covers the table-owner bypass class). The SELECT policy has a real tenant predicate via `org_members` membership lookup. **For an anon-key or user-JWT caller, the SELECT policy would correctly isolate tenants.**
- However, no INSERT / UPDATE / DELETE policies are declared. With `FORCE ROW LEVEL SECURITY`, the default for missing policies on those operations is **deny**, so the migration itself is safe (writes are blocked) -- but this is an availability gap if the application ever needs to write through user JWTs. Severity P2 (operational, not leakage).
- The **dominant finding is not in the migration; it is in the Edge Function**. See §3, §7.

---

## 3. Gaps and severities

1. **P1 -- service_role bypass with caller-supplied tenant identifier (`list-org-docs/index.ts`).**
   The Edge Function instantiates a Supabase client with `SUPABASE_SERVICE_ROLE_KEY`. The service role bypasses RLS unconditionally. The function then reads `org_id` directly from the request body and uses it as the only filter on `documents`. There is no server-side validation that the calling user (a) is authenticated at all, (b) is a member of the requested `org_id`. Concrete failure mode: user U1, a member of org A only, calls the endpoint with `{ "org_id": "org_B" }`. The query becomes `SELECT * FROM documents WHERE org_id = 'org_B'` executed as service_role. RLS does not apply. The function returns **every document in org B** to U1. This is full cross-tenant read leakage of the entire table. The clean SELECT policy in the migration is bypassed and provides zero protection along this call path.

2. **P1 -- no authentication check in the Edge Function.**
   The function does not read or verify the caller's JWT (no `Authorization` header check, no `supabase.auth.getUser(jwt)`). Combined with finding 1, this means an unauthenticated request body of `{ "org_id": "<any uuid>" }` exfiltrates documents for any org. Even if Supabase Functions ingress is configured to require a Bearer token, that token is not bound to the query, so a token for any user still grants access to any org.

3. **P1 -- no server-side authorization check binding caller to `org_id`.**
   Even if a JWT were verified, the function does not verify that `auth.uid()` (the verified caller) is a member of the requested `org_id`. This is the membership predicate the SELECT policy embodies; the Edge Function must replicate it before the service_role query, or stop using service_role.

4. **P2 -- service_role client is module-scoped and used for a user-facing read path.**
   The pattern of constructing a service_role client at module load (`const supabaseAdmin = createClient(...)`) and using it for a user-facing endpoint maximizes blast radius: every code path in this function inherits RLS bypass. Even if findings 1-3 are fixed, the architectural choice is unjustified -- this endpoint should use a per-request user-scoped client so RLS does the isolation work.

5. **P2 -- missing INSERT / UPDATE / DELETE policies on `documents`.**
   With `FORCE ROW LEVEL SECURITY` and no write policies, writes through a user JWT are denied. This is safe-by-default but means the application cannot write through RLS; any write path will be forced to use service_role, which compounds the risk class in finding 1. If the product needs user-driven writes, declare the policies now.

6. **P2 -- `org_members` RLS posture is referenced but unverified in this audit scope.**
   The SELECT policy on `documents` depends on `org_members`. If `org_members` lacks its own RLS / does not restrict reads to the calling user's own membership rows, the policy still works for `documents` (the subquery runs in the policy's security context), but any direct read of `org_members` could leak the org graph. Out of scope for this migration, but flagged for the follow-up audit.

7. **P3 -- no input validation on `org_id` shape.**
   `req.json()` is consumed without checking that `org_id` is a UUID. Malformed input yields a 500 rather than a clean 400. Operability, not security.

---

## 4. Remediation per gap

The remediation is **code-shaped** for findings 1-4 (the migration is not the bug) and **migration-shaped** for findings 5-6. Both are required to close the gap.

### Code-shaped fix (findings 1, 2, 3, 4) -- replace the Edge Function

```typescript
// supabase/functions/list-org-docs/index.ts
import { createClient } from '@supabase/supabase-js';

export default async (req: Request) => {
  // 1. Require an Authorization header (caller JWT).
  const authHeader = req.headers.get('Authorization');
  if (!authHeader?.startsWith('Bearer ')) {
    return new Response(JSON.stringify({ error: 'unauthenticated' }), { status: 401 });
  }

  // 2. Build a per-request user-scoped client that forwards the caller JWT.
  //    This client respects RLS; service_role is NOT used on the read path.
  const supabase = createClient(
    Deno.env.get('SUPABASE_URL')!,
    Deno.env.get('SUPABASE_ANON_KEY')!,
    { global: { headers: { Authorization: authHeader } } }
  );

  // 3. Verify the JWT server-side (defense in depth -- do not trust headers).
  const { data: userData, error: userErr } = await supabase.auth.getUser();
  if (userErr || !userData?.user) {
    return new Response(JSON.stringify({ error: 'unauthenticated' }), { status: 401 });
  }

  // 4. Validate input shape.
  let body: { org_id?: unknown };
  try { body = await req.json(); } catch { 
    return new Response(JSON.stringify({ error: 'invalid_json' }), { status: 400 });
  }
  const orgId = typeof body.org_id === 'string' ? body.org_id : null;
  if (!orgId || !/^[0-9a-f-]{36}$/i.test(orgId)) {
    return new Response(JSON.stringify({ error: 'invalid_org_id' }), { status: 400 });
  }

  // 5. Issue the query through the user-scoped client.
  //    The docs_select RLS policy enforces tenant membership; cross-tenant
  //    requests return an empty set, never another org's rows.
  const { data, error } = await supabase
    .from('documents')
    .select('*')
    .eq('org_id', orgId);

  if (error) {
    return new Response(JSON.stringify({ error: error.message }), { status: 400 });
  }
  return new Response(JSON.stringify({ data }), { status: 200 });
};
```

Key invariants enforced:
- No `SUPABASE_SERVICE_ROLE_KEY` in this file. The service_role client is removed entirely from the read path.
- The caller's JWT is the source of authority. RLS evaluates `auth.uid()` against `org_members`, so U1 calling with `{ org_id: 'org_B' }` gets an empty array, not org B's documents.
- The `.eq('org_id', orgId)` is now defense-in-depth, not the authorization mechanism. Even if it were omitted, RLS would still scope rows to the caller's orgs.

### Migration-shaped fix (finding 5) -- write policies on `documents`

If the product needs user-driven writes, append to a new migration (do NOT edit the already-shipped one):

```sql
-- migrations/20260607000000_documents_write_policies.sql

CREATE POLICY docs_insert ON documents
  FOR INSERT
  WITH CHECK (
    user_id = auth.uid()
    AND org_id IN (SELECT org_id FROM org_members WHERE user_id = auth.uid())
  );

CREATE POLICY docs_update ON documents
  FOR UPDATE
  USING (
    org_id IN (SELECT org_id FROM org_members WHERE user_id = auth.uid())
  )
  WITH CHECK (
    org_id IN (SELECT org_id FROM org_members WHERE user_id = auth.uid())
    AND user_id = auth.uid()  -- adjust if non-author edits are intended
  );

CREATE POLICY docs_delete ON documents
  FOR DELETE
  USING (
    org_id IN (SELECT org_id FROM org_members WHERE user_id = auth.uid())
    AND user_id = auth.uid()  -- adjust if org-admin delete is intended
  );
```

Rationale:
- INSERT has only `WITH CHECK` (SELECT-back is governed by `docs_select`).
- UPDATE has both `USING` (which rows you can target) and `WITH CHECK` (what state you can leave behind); both reference the tenant predicate, preventing the "move row to another org" attack.
- DELETE binds to the caller's own rows by default. Adjust the `user_id = auth.uid()` clause for INSERT/UPDATE/DELETE if the product allows org-admin write on peer rows; in that case, replace with an `org_admins` lookup.

### Migration-shaped fix (finding 6) -- confirm `org_members` posture (follow-up audit)

Out of scope to write here, but the next audit MUST confirm `org_members` has:
```sql
ALTER TABLE org_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE org_members FORCE ROW LEVEL SECURITY;
CREATE POLICY org_members_self_select ON org_members
  FOR SELECT USING (user_id = auth.uid());
-- plus appropriate INSERT / UPDATE / DELETE policies for invites and removals.
```

---

## 5. Follow-the-data trace

- `documents.org_id` -> `org_members.org_id` (logical reference via SELECT policy subquery): **UNVERIFIED** -- `org_members` is not in this migration; flagged P2 for follow-up.
- `documents.user_id` -> `auth.users.id` (implicit Supabase auth FK): standard; no RLS gap, but ensure write policies enforce `user_id = auth.uid()` on INSERT so a user cannot impersonate another user's authorship within their own org.
- `documents` outgoing FKs: none declared in the migration. If `document_versions`, `document_comments`, or `document_audit_log` tables exist or will exist, each MUST receive its own RLS posture mirroring `documents` (P1 if added without policies).
- `documents` incoming FKs from external tables: none in scope.

No materialized views, no soft-delete shadow tables, no audit/log tables in this migration. Re-run the trace when subsequent migrations land.

---

## 6. SECURITY DEFINER function audit

No `SECURITY DEFINER` functions are declared in the migration under audit. No `pg_proc` enumeration available in this audit run. **Verdict: N/A for this scope.** Flag for re-audit if any RPC functions are added against `documents` (especially `create_document`, `share_document`, or `list_org_documents`-style RPCs that would centralize the SELECT through a definer function).

---

## 7. service_role usage audit

Call site: `supabase/functions/list-org-docs/index.ts`

| Call site | Purpose | User-supplied identifier? | Server-side validation before bypass? | Verdict |
|---|---|---|---|---|
| `supabase/functions/list-org-docs/index.ts` -- module-scope `createClient(URL, SERVICE_ROLE_KEY)` used inside default request handler to read `documents` filtered by request-body `org_id` | User-facing read of org documents | **YES** -- `org_id` is read directly from `req.json()` | **NO** -- no JWT check, no membership check, no input validation | **UNJUSTIFIED** |

Concrete failure mode (the attack scenario explicitly asked for):
- U1 is a member of org A only.
- U1 POSTs to `list-org-docs` with body `{ "org_id": "org_B" }`.
- The function constructs the query as service_role; RLS is bypassed.
- Postgres executes `SELECT * FROM documents WHERE org_id = 'org_B'` with no tenant predicate.
- U1 receives **every row in `documents` for org B** in the response.
- The clean `docs_select` policy never runs. The migration's tenant isolation is defeated entirely at this code path.

Generalization: this is the canonical "service_role + user-supplied tenant id, no server validation" anti-pattern. Even one such call site nullifies the entire RLS posture for the affected table, regardless of how clean the DDL looks. The persona's rule (Step 7) treats this as **P1 when user input is the tenant filter and no server-side validation precedes the bypass** -- this is the P1 escalation case, not a routine P2.

Required disposition: **remove `SUPABASE_SERVICE_ROLE_KEY` from this function entirely** and replace with the user-scoped client pattern in §4. If a future endpoint genuinely needs service_role (e.g. a cron that aggregates across orgs), it MUST: (a) be inaccessible from the public ingress (internal-only invocation), (b) never accept tenant identifiers from request bodies, (c) document the justification inline.

Other call sites: none in scope for this audit. A full repo sweep with `rg -n 'SUPABASE_SERVICE_ROLE_KEY' supabase/functions/` should be run before merge to confirm no peer functions share this anti-pattern.

---

## 8. PROPOSED block draft for any policy decisions that need locking

```markdown
<!-- PROPOSED by rls-auth-boundary-auditor: -->
### D-N -- `documents` write policy authorship rule (per-author vs org-wide)

Context: §4 remediation drafts INSERT/UPDATE/DELETE policies for `documents` that bind to `user_id = auth.uid()` (the row's author). The product may instead want:

- Option A (drafted): only the author can update/delete their own document; any org member can insert documents authored by themselves.
- Option B: any org member can update/delete any document in their org (collaborative wiki shape).
- Option C: org admins can update/delete any document in their org; non-admins only their own (requires an `org_admins` lookup or role column in `org_members`).

Tradeoff: A is safest default; B fits collaborative editors; C requires the membership table to expose a role. Pick before declaring the write policies; the wrong choice locks the product into a less-flexible auth shape.

Recommended next: `decision-interview` to lock the authorship rule before `implementation-plan` slices the write-policy migration.
```

```markdown
<!-- PROPOSED by rls-auth-boundary-auditor: -->
### TASK_STATE.md ## Risks to watch -- service_role anti-pattern sweep

Risk: other Edge Functions in `supabase/functions/` may share the `list-org-docs` anti-pattern (service_role client + user-supplied tenant id, no server validation). One unaudited call site nullifies the entire RLS posture for the affected table. Mitigation: run `rg -n 'SUPABASE_SERVICE_ROLE_KEY' supabase/functions/` and audit every hit against the §7 criteria before merge.
```

```markdown
<!-- PROPOSED by rls-auth-boundary-auditor: -->
### IMPLEMENTATION_PLAN.md ## Risks and mitigations -- RLS bypass via service_role

Risk: any user-facing endpoint that holds a service_role client and consumes tenant identifiers from request bodies bypasses RLS regardless of policy quality. Mitigation: forbid module-scope service_role clients in user-facing functions; require per-request user-scoped clients; require `supabase.auth.getUser()` verification before any tenant-scoped query; reserve service_role for internal cron / webhook handlers with no user-supplied tenant identifiers.
```

---

## 9. `<task>/RLS_AUDIT.md` content draft

```markdown
# RLS_AUDIT.md -- `documents` migration + `list-org-docs` Edge Function

Aggregate verdict: **FAIL** (one or more P1 findings).

## Migration files audited
- `migrations/20260606140003_documents.sql`

## Backend code audited
- `supabase/functions/list-org-docs/index.ts`

## Per-table posture
See output §2.

## Gaps (severity-ranked)
1. P1 -- service_role bypass with caller-supplied `org_id`, no JWT verification, no membership check (`list-org-docs/index.ts`). Cross-tenant read leakage of entire `documents` table.
2. P1 -- no authentication check in the Edge Function.
3. P1 -- no server-side authorization check binding caller to `org_id`.
4. P2 -- module-scope service_role client used on a user-facing read path; maximizes blast radius.
5. P2 -- missing INSERT/UPDATE/DELETE policies on `documents` (safe-by-default deny, but forces all writes to bypass RLS).
6. P2 -- `org_members` RLS posture not verified in this audit scope.
7. P3 -- no input validation on `org_id` shape.

## Remediation
- Code: replace `list-org-docs/index.ts` per output §4 (user-scoped client, JWT verification, input validation; remove `SUPABASE_SERVICE_ROLE_KEY`).
- Migration: add `docs_insert`, `docs_update`, `docs_delete` policies per output §4 (in a new migration file; do not edit `20260606140003_documents.sql`).
- Follow-up: audit `org_members` policies; sweep all other `supabase/functions/` for the same anti-pattern.

## service_role audit
- `supabase/functions/list-org-docs/index.ts` -- UNJUSTIFIED (P1).

## Follow-the-data trace
See output §5.

## SECURITY DEFINER functions
None in scope.

## Audit history
| timestamp | run_id | migrations | code paths | verdict |
|---|---|---|---|---|
| 2026-06-05 | rls-audit-001 | `20260606140003_documents.sql` | `supabase/functions/list-org-docs/index.ts` | FAIL |
```

---

## 10. Recommended next command

`decision-interview` -- the `documents` write-policy authorship rule (§8, Option A / B / C) is a real tradeoff that should be locked before the remediation migration is sliced. After the decision lands, route to `implementation-plan` to slice the two-part remediation (Edge Function rewrite + write-policy migration), then `implement-approved-slice` for the Edge Function fix first (closes the active P1 leak), then for the write-policy migration. `approve-proposed` is not appropriate here because the PROPOSED `D-N` block frames an unresolved tradeoff, not a settled decision.

### Artifact changes

- PROPOSED -- `DECISIONS.md ## Locked decisions` -- new `D-N` block per §8 (authorship rule for `documents` write policies).
- PROPOSED -- `TASK_STATE.md ## Risks to watch` -- service_role anti-pattern sweep entry per §8.
- PROPOSED -- `IMPLEMENTATION_PLAN.md ## Risks and mitigations` -- RLS bypass via service_role entry per §8.
- PROPOSED -- `<task>/RLS_AUDIT.md` -- full body per §9.

### Command transcript

- Parsed migration `20260606140003_documents.sql`: 1 table (`documents`), RLS + FORCE applied, SELECT policy with tenant predicate via `org_members`, no write policies.
- Audited `list-org-docs/index.ts`: identified module-scope service_role client + user-supplied `org_id` + no JWT verification + no membership check -- P1 cross-tenant read leakage.
- Generated code-shaped remediation (user-scoped client + auth.getUser + input validation) and migration-shaped remediation (write policies) plus PROPOSED `D-N` for authorship rule tradeoff.

### Handoff

Aggregate verdict: **FAIL** (P1 cross-tenant read leakage via service_role in `list-org-docs`).

Run now: `decision-interview` to lock the `documents` write-policy authorship rule (Option A / B / C in §8). After lock, `implementation-plan` to slice: (slice 1) rewrite `list-org-docs/index.ts` to remove service_role and adopt the user-scoped client pattern -- this closes the active leak; (slice 2) add `docs_insert` / `docs_update` / `docs_delete` policies per the locked authorship rule; (slice 3) sweep all other `supabase/functions/` for the same anti-pattern and audit `org_members` RLS posture. Do not ship the migration set until slice 1 is merged: the clean DDL provides zero protection while the Edge Function bypass exists.
