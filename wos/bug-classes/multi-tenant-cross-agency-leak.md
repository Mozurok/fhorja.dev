---
name: multi-tenant-cross-agency-leak
category: multi-tenant
default-severity: P0
cwe: [CWE-639]
languages: [typescript, ruby, python, sql]
file-patterns: ["**/db/**", "**/models/**", "**/repositories/**", "**/queries/**", "**/server/**/routes/**", "**/api/**", "supabase/migrations/**"]
perspectives: [security-auditor, operator, maintainer]
reversibility-check: true
---

# multi-tenant-cross-agency-leak

## Trigger

In a multi-tenant application, a query against a tenant-scoped table (agents, customers, leads, policies, quotes) omits the tenant filter from its WHERE clause, OR reads the tenant id from the request body or query string instead of the authenticated session. An agent authenticated at tenant A can then read, list, or mutate rows owned by tenant B.

The class is written from a brokerage and carrier-appointment domain, where per-tenant isolation is a regulatory requirement rather than a product preference, but it applies to any application where one tenant's rows must never be visible to another.

CWE-639 (Authorization Bypass Through User-Controlled Key). The "key" here is the tenant id that the server should derive from the session but instead reads from a client-controlled field, or an object id filtered without re-checking tenant ownership.

## Detection

Static and grep heuristics:

```
# Queries on tenant-scoped tables that lack a tenant filter
rg -nP "from\\s+(agents|customers|leads|policies|quotes)" --type ts --type sql \
  | rg -v "tenant_id|agency_id"

# Routes that accept tenant id from the wire instead of the session
rg -nP "req\\.body\\.(tenant_id|agency_id)|req\\.query\\.(tenant_id|agency_id)" apps/
```

Shapes to look for by reading:

- A repository method `findCustomerById(id)` that filters only by `id` and not by `(id, tenant_id)`.
- An API route that accepts `agency_id` or `tenant_id` in the request body or query string and trusts it instead of deriving it from the session or JWT claims.
- ORM scopes where tenant scoping is opt-in (`.where(tenant_id: ...)`) instead of default-on; one developer forgets the scope and the leak ships.
- A "list all" endpoint (`GET /api/agents`) that returns rows from every tenant because the controller never narrows by tenant.
- A SQL view or RPC that joins across tenants for admin reporting and then gets exposed to a non-admin role.
- Supabase tables without RLS policies, or with a policy that uses `USING (true)` while the developer assumed the app layer would filter.

Dynamic and test-level checks:

- Integration test: seed two tenants (A, B). Authenticate as a user in A. Hit every read endpoint with B's row ids. Assert 404 or zero rows for every case.
- ORM scope coverage report: enumerate every model touching a tenant-scoped table; assert each one has a default tenant scope applied at the base class.
- Database audit: list every table that has a `tenant_id` or `agency_id` column and confirm a matching RLS policy exists and is non-trivial.

## Retrieval

- The ORM base class or model superclass where a default tenant scope would live, plus the repository or query layer for any tenant-scoped table (`**/models/**`, `**/repositories/**`, `**/queries/**`).
- The route handlers in the diff that read a tenant identifier, so the source of that identifier can be traced to the session rather than to the request.
- The session or JWT claim extraction code, to establish what the trusted tenant id actually is.
- Migration and policy DDL for the tenant-scoped tables in scope (`supabase/migrations/**`, `**/db/**`), to check whether RLS is the floor or the app layer is carrying the invariant alone.
- Any SQL view, RPC, or reporting query that joins across tenants, plus the role that can reach it.

## Analysis prompt

Given the retrieved query layer, route handlers, and policy DDL:

1. For every query against a tenant-scoped table in the diff, does the predicate include the tenant column? A filter on a primary key alone is not sufficient, because an object id from another tenant is still a valid id.
2. Where does the tenant identifier come from at each call site? Trace it to its origin. A tenant id read from the request body, query string, header, or a client-settable cookie is attacker-controlled and fails this class regardless of what the query looks like.
3. Is tenant scoping default-on at the ORM base class, or opt-in per query? Opt-in scoping is a latent leak: report it even when every current call site happens to be correct, because the failure arrives with the next query someone writes.
4. Is there a database-level floor? Check for RLS keyed to a session-scoped setting (for example a policy on `current_setting('app.tenant_id')::uuid`, set via a transaction-scoped `SET LOCAL`). App-layer scoping is defence in depth; RLS is the floor. A tenant-scoped table with no policy, or with `USING (true)`, has no floor.
5. For any cross-tenant path that exists deliberately (admin reporting, support impersonation), is it behind an explicit wrapper that logs the access and is gated by a separate role, or is it reachable by an ordinary authenticated user?
6. Recommend fixes in this order, because each one narrows the blast radius of the next being wrong: push tenant scoping down to the ORM base class so it is default-on; source the tenant only from the authenticated session; enforce at the database with RLS; add a deny-by-default integration test that fails the suite when any query returns a row whose tenant does not match the session, and run it in CI; require an explicit `withCrossTenant(reason)` wrapper for legitimate cross-tenant flows.
7. This class carries `reversibility-check: true`, so the reversibility prompt applies with a specific weight here: once tenant data has been read across the boundary, it is read. A confirmed leak is not rolled back by a deploy. Treat it as a P0 incident with PII rotation where possible, tenant notification, and breach disclosure per applicable law.

## Severity rubric

- **P0**: a query, route, view, or RPC reachable by an ordinary authenticated user can return or mutate another tenant's rows. Also P0 when a tenant-scoped table holding regulated personal data has no RLS policy and the app layer is the only control. Justification for the ceiling: in a regulated brokerage domain, cross-tenant visibility is a compliance violation rather than a UX defect; leaked personal data (government identifiers, dates of birth, health attestations on applications) triggers breach-notification statutes and direct civil exposure; and a single missing predicate can expose an entire table across every tenant in one query.
- **P1**: tenant scoping is opt-in rather than default-on, and every current call site is correctly scoped. The invariant holds today and depends on every future author remembering it.
- **P2**: a cross-tenant admin path exists and is correctly role-gated but does not log the access, so a legitimate cross-tenant read cannot be audited after the fact.

## Confidence factors

- **HIGH**: a query against a tenant-scoped table has no tenant predicate AND the tenant id at that call site is read from a client-controlled field; or a tenant-scoped table with regulated data has no RLS policy and the grep for the tenant column returns matches in the route layer.
- **MEDIUM**: the query lacks a tenant predicate but the tenant id is session-derived and a base-class scope may be applying it implicitly; reading the ORM base class settles it.
- **LOW**: the table name matches the tenant-scoped list but the query is in a migration, a seed, a fixture, or an admin task that runs with no user session, where the tenant predicate is legitimately absent.

## Examples

### Positive (cross-tenant leak)

```typescript
// repositories/customer.ts
export async function findCustomerById(id: string) {
  // filters on the primary key only: an id belonging to another tenant is
  // still a valid id, so this returns that tenant's row
  return db.selectFrom("customers").where("id", "=", id).executeTakeFirst();
}
```

```typescript
// server/routes/agents.ts
router.get("/api/agents", async (req, res) => {
  // tenant id read from the wire, not the session
  const agencyId = req.query.agency_id;
  res.json(await db.selectFrom("agents").where("agency_id", "=", agencyId).execute());
});
```

### Negative (tenant boundary enforced)

```typescript
// repositories/customer.ts
export async function findCustomerById(id: string, tenantId: string) {
  // composite predicate: an id from another tenant matches nothing
  return db
    .selectFrom("customers")
    .where("id", "=", id)
    .where("tenant_id", "=", tenantId) // tenantId comes from the session, never the request
    .executeTakeFirst();
}
```

```sql
-- supabase/migrations/..._customers_rls.sql
-- database floor: the app layer is defence in depth, this is the invariant
alter table customers enable row level security;
alter table customers force row level security;

create policy customers_tenant_isolation on customers
  using (tenant_id = current_setting('app.tenant_id')::uuid)
  with check (tenant_id = current_setting('app.tenant_id')::uuid);
```
