# Service Role Tenant Isolation Audit -- `list-org-docs`

## TL;DR

The migration is fine. The Edge Function `list-org-docs` is a **critical tenant isolation break**. It uses the `service_role` key (which **bypasses RLS, including `FORCE ROW LEVEL SECURITY`**) and then trusts a caller-supplied `org_id` from the request body with **zero server-side validation** of who the caller is or what orgs they belong to. The clean RLS policy on `documents` is never evaluated, so it provides no protection here.

### Attack scenario answer

U1 (member of org A only) calls the endpoint with `{ org_id: 'org_B' }`. U1 receives **every row in `documents` where `org_id = 'org_B'`** -- full title and body. The RLS `docs_select` policy is bypassed because the Edge Function uses the service_role key. There is also **no authentication check at all** on the function -- even an unauthenticated attacker who can reach the endpoint can enumerate any org by guessing/iterating `org_id` UUIDs (or harvesting them from other endpoints, logs, support tickets, invite links, etc.). This is an **IDOR / horizontal privilege escalation across tenants**, severity Critical.

---

## Per-callsite verdict

### Callsite 1 -- `createClient(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)` (module scope)

**Verdict: UNJUSTIFIED.**

There is no operational reason this endpoint needs `service_role`. It performs a single tenant-scoped `SELECT` on `documents`, which is exactly what RLS was designed for. `service_role` is reserved for genuinely admin-shaped operations (cross-tenant aggregations, system jobs, webhooks that legitimately need to read across orgs, migrations, etc.). Listing a user's own org's documents is the textbook anti-use-case for `service_role`.

A second, subtler problem: the admin client is created at module scope and reused for every request. Even if some operations on this function needed elevated privileges in the future, mixing them with user-context reads on the same client is dangerous -- every query on this client silently runs as `service_role`.

### Callsite 2 -- `supabaseAdmin.from('documents').select('*').eq('org_id', org_id)`

**Verdict: UNJUSTIFIED -- Critical.**

This query:

1. Runs as `service_role`, so RLS is **bypassed entirely** (and `FORCE ROW LEVEL SECURITY` on the table does not save you -- `FORCE` only prevents the table owner from being exempt; the `service_role` JWT maps to a role that has the `bypassrls` attribute, which is a different mechanism).
2. Filters by an `org_id` value **taken directly from the request body** with no validation that the caller is authenticated, no validation that the caller is a member of that org, and no validation that the value is even a UUID.
3. Returns `*`, including any sensitive columns (`body`, and any columns added later -- schema drift will silently widen exposure).

---

## Concrete failure mode

**Class:** Authorization bypass via service_role + unvalidated tenant identifier (IDOR across tenants). Maps to CWE-639 (Authorization Bypass Through User-Controlled Key) and CWE-285 (Improper Authorization).

**Step-by-step exploitation for the given scenario:**

1. U1 authenticates to the app and is a member of org A only.
2. U1 (or any caller, even unauthenticated -- the function never reads `Authorization`) sends:
   ```
   POST /functions/v1/list-org-docs
   { "org_id": "org_B" }
   ```
3. The Edge Function constructs a query as `service_role`. RLS does not apply.
4. Postgres returns every row in `documents` where `org_id = 'org_B'`.
5. The function returns the full result set to U1.

**Blast radius:**

- **Read exposure of every tenant.** Any `org_id` known or guessable to an attacker yields full document contents (`title`, `body`). UUIDs are not secrets -- they leak through invite links, error messages, support emails, screenshots, browser history, analytics, and other endpoints. Treating them as a security boundary is itself a bug.
- **Unauthenticated abuse.** The handler never validates a JWT. A scraper hitting the function URL with arbitrary `org_id` values harvests data with no audit trail attributable to a user.
- **Silent and undetectable.** Because the query runs as `service_role`, there is no RLS denial, no Postgres error, nothing to alarm on. Detection requires application-layer logging that this function does not emit.
- **No write path here, but the same pattern in any sibling function (`update-doc`, `delete-doc`) would allow cross-tenant write / destroy.** Audit those next.

**Why the migration does not save you:** `ENABLE ROW LEVEL SECURITY` + `FORCE ROW LEVEL SECURITY` + `docs_select` are all correct, and they would protect the table if accessed via the **anon** key or a **user JWT**. `service_role` is exempt by design. The defense exists; this function declines to use it.

---

## Remediation

The correct fix is **code-shaped**, not migration-shaped. The schema and policy are already correct -- the function just needs to stop using `service_role` and let RLS do its job. Below is the recommended fix, plus a secondary defense-in-depth migration that makes the failure mode harder to reintroduce.

### Primary fix (code-shaped) -- use the caller's JWT, let RLS enforce isolation

Replace the handler so that:

1. It requires an `Authorization: Bearer <user JWT>` header.
2. It constructs a Supabase client scoped to that user (anon key + the user's access token), so queries run as `authenticated` with the user's `auth.uid()`.
3. RLS (`docs_select`) handles the tenant check.
4. `service_role` is not imported into this function at all.

```typescript
// supabase/functions/list-org-docs/index.ts
import { createClient } from '@supabase/supabase-js';

const SUPABASE_URL = Deno.env.get('SUPABASE_URL')!;
const SUPABASE_ANON_KEY = Deno.env.get('SUPABASE_ANON_KEY')!;

export default async (req: Request) => {
  const authHeader = req.headers.get('Authorization') ?? '';
  if (!authHeader.startsWith('Bearer ')) {
    return new Response(JSON.stringify({ error: 'unauthorized' }), { status: 401 });
  }

  // Per-request client, scoped to the caller's JWT.
  // Queries run as `authenticated` with the caller's auth.uid().
  const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY, {
    global: { headers: { Authorization: authHeader } },
    auth: { persistSession: false, autoRefreshToken: false },
  });

  // Validate the JWT actually resolves to a user.
  const { data: userRes, error: userErr } = await supabase.auth.getUser();
  if (userErr || !userRes?.user) {
    return new Response(JSON.stringify({ error: 'unauthorized' }), { status: 401 });
  }

  let body: { org_id?: string };
  try {
    body = await req.json();
  } catch {
    return new Response(JSON.stringify({ error: 'bad_request' }), { status: 400 });
  }

  const orgId = body.org_id;
  if (typeof orgId !== 'string' || !/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(orgId)) {
    return new Response(JSON.stringify({ error: 'bad_request' }), { status: 400 });
  }

  // Project explicit columns -- never SELECT * across a tenant boundary.
  const { data, error } = await supabase
    .from('documents')
    .select('id, org_id, user_id, title, body')
    .eq('org_id', orgId);

  if (error) {
    return new Response(JSON.stringify({ error: 'query_failed' }), { status: 500 });
  }

  return new Response(JSON.stringify({ data }), {
    headers: { 'content-type': 'application/json' },
  });
};
```

Key properties of this fix:

- `service_role` is gone from this function. RLS now runs.
- A user who passes `org_id = 'org_B'` while only being a member of `org_A` gets an **empty array**, because `docs_select` filters by `org_id IN (SELECT org_id FROM org_members WHERE user_id = auth.uid())`.
- Unauthenticated callers get `401` before any query.
- The client is per-request, so there is no cross-request JWT bleed.
- `select('*')` is replaced with an explicit column list so future schema additions don't silently widen exposure.

### Optional belt-and-suspenders (code-shaped)

Even with RLS doing the right thing, **explicitly verify the caller is a member of the requested org** before querying. This makes the intent visible in code review and means a future regression in RLS does not silently re-open the hole:

```typescript
const userId = userRes.user.id;
const { data: membership, error: memErr } = await supabase
  .from('org_members')
  .select('org_id')
  .eq('user_id', userId)
  .eq('org_id', orgId)
  .maybeSingle();

if (memErr || !membership) {
  return new Response(JSON.stringify({ error: 'forbidden' }), { status: 403 });
}
```

This also returns the right status code (`403`) instead of an empty list, which is better UX and better for monitoring.

### Migration-shaped hardening (defense in depth)

The current schema cannot prevent a future engineer from reintroducing the same bug by reaching for `service_role` again. A few migration-level guardrails reduce that risk:

1. **Make `org_id` membership check a SQL function and reuse it everywhere.** Centralizes the predicate, makes it auditable, and reduces drift between SELECT/UPDATE/DELETE/INSERT policies.

   ```sql
   CREATE OR REPLACE FUNCTION public.is_org_member(target_org uuid)
   RETURNS boolean
   LANGUAGE sql
   STABLE
   SECURITY INVOKER
   SET search_path = public
   AS $$
     SELECT EXISTS (
       SELECT 1 FROM public.org_members
       WHERE org_id = target_org AND user_id = auth.uid()
     );
   $$;

   DROP POLICY IF EXISTS docs_select ON public.documents;
   CREATE POLICY docs_select ON public.documents
     FOR SELECT USING (public.is_org_member(org_id));
   ```

2. **Add policies for the other verbs** so a future `INSERT/UPDATE/DELETE` path is automatically protected if it ever uses a user-JWT client:

   ```sql
   CREATE POLICY docs_insert ON public.documents
     FOR INSERT WITH CHECK (public.is_org_member(org_id) AND user_id = auth.uid());

   CREATE POLICY docs_update ON public.documents
     FOR UPDATE
     USING (public.is_org_member(org_id))
     WITH CHECK (public.is_org_member(org_id));

   CREATE POLICY docs_delete ON public.documents
     FOR DELETE USING (public.is_org_member(org_id));
   ```

3. **Revoke unnecessary table grants from `anon`** so even a misconfigured client can't read without going through RLS-aware grants:

   ```sql
   REVOKE ALL ON public.documents FROM anon;
   GRANT SELECT, INSERT, UPDATE, DELETE ON public.documents TO authenticated;
   ```

4. **Operational guardrail (not SQL): lint for `SERVICE_ROLE_KEY` usage in `supabase/functions/**`.** Add a CI grep that fails the build if a function imports the service_role key without an allowlist comment explaining why. This is the single highest-leverage prevention against this bug class.

---

## Summary table

| Item | Verdict | Failure mode | Fix |
|---|---|---|---|
| `createClient(..., SERVICE_ROLE_KEY)` at module scope | UNJUSTIFIED | Bypasses RLS for every query in this function; shared across requests | Remove `service_role`; create a per-request anon client bound to the caller's JWT |
| `.from('documents').select('*').eq('org_id', org_id)` | UNJUSTIFIED -- Critical | Cross-tenant read: any caller (even unauthenticated) reads any org's documents by supplying its `org_id` (CWE-639 / CWE-285) | Run as caller's JWT so `docs_select` filters by membership; require `Authorization`; validate `org_id` is a UUID; project explicit columns; optionally pre-check `org_members` for a 403 |
| Schema / RLS policy | Already correct | n/a -- bypassed by `service_role` | Optional hardening: factor predicate into `is_org_member()`, add policies for INSERT/UPDATE/DELETE, tighten grants, add CI lint against `SERVICE_ROLE_KEY` in Edge Functions |

**Bottom line:** The clean migration is doing its job. The Edge Function is the entire problem. Stop using `service_role` here, run the query as the caller, and the attack scenario collapses to an empty array.
