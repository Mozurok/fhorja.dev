---
name: multi-tenant-cross-agency-leak
category: multi-tenant
default-severity: P0
priority: P0
pillars: [security, multi-tenancy]
cwe: [CWE-639]
languages: [typescript, ruby, python, sql]
file-patterns: ["**/db/**", "**/models/**", "**/repositories/**", "**/queries/**", "**/server/**/routes/**", "**/api/**", "supabase/migrations/**"]
perspectives: [security-auditor, operator, maintainer]
reversibility-check: true
---

# multi-tenant-cross-agency-leak

In a multi-tenant insurance app (Right Quote / SureLC-shaped domain), a query against a tenant-scoped table (agents, customers, leads, policies, quotes) omits the tenant filter from its WHERE clause, OR reads the tenant id from the request body / query string instead of the authenticated session. Result: an agent authenticated at Agency A can read, list, or mutate rows owned by Agency B. This is the hardest rule in the insurance carrier-appointment domain: no cross-agency visibility, ever.

## What it looks like

- A repository method `findCustomerById(id)` that filters only by `id` and not by `(id, tenant_id)`.
- An API route that accepts `agency_id` (or `tenant_id`) in the request body or query string and trusts it instead of deriving it from the session / JWT claims.
- ORM scopes where tenant scoping is opt-in (`.where(tenant_id: ...)`) instead of default-on; one developer forgets the scope and the leak ships.
- A "list all" endpoint (`GET /api/agents`) that returns rows from every tenant because the controller never narrows by tenant.
- A SQL view or RPC that joins across tenants for "admin reporting" and then gets accidentally exposed to a non-admin role.
- Supabase tables without RLS policies, or with a policy that uses `USING (true)` while the developer assumed the app layer would filter.

## Why it matters

- Insurance compliance: carrier appointments and BGA hierarchies (SureLC pattern) require strict per-agency data isolation. Cross-agency visibility is a regulatory violation, not just a UX bug.
- Customer trust: leaking a competing agency's lead list, commissions, or PII is an unrecoverable trust event for a small/solo broker tool.
- Civil liability: leaked PII (SSN, DOB, health attestations on life applications) triggers breach-notification statutes in most US states and direct civil exposure.
- Blast radius: a single missing WHERE clause can expose the entire customer table across all tenants in one query.

## How to detect

Static + grep heuristics:

```
# Queries on tenant-scoped tables that lack a tenant filter
rg -nP "from\\s+(agents|customers|leads|policies|quotes)" --type ts --type sql \
  | rg -v "tenant_id|agency_id"

# Routes that accept tenant id from the wire instead of the session
rg -nP "req\\.body\\.(tenant_id|agency_id)|req\\.query\\.(tenant_id|agency_id)" apps/
```

Dynamic / test-level:

- Integration test: seed two tenants (A, B). Authenticate as user in A. Hit every read endpoint with B's row ids. Assert 404 / 0 rows for every case.
- ORM scope coverage report: enumerate every model touching a tenant-scoped table; assert each one has a default tenant scope applied at the base class.
- DB-level audit: list every table that has a `tenant_id` / `agency_id` column and confirm a matching RLS policy exists and is non-trivial.

## How to fix

1. Push tenant scoping down to the ORM base class so it is default-on, not opt-in (ActsAsTenant-style pattern). Every query against a tenant-scoped model automatically filters by the current tenant.
2. Source the current tenant ONLY from the authenticated session / JWT claim, never from the request body, query string, header, or cookie that the client controls.
3. Enforce at the database layer with RLS (Supabase Postgres): policy keyed to `current_setting('app.tenant_id')::uuid`, set via a transaction-scoped `SET LOCAL` driven by the session. App-layer scope is defence-in-depth, RLS is the floor.
4. Add a deny-by-default integration test: any query that returns a row whose `tenant_id` does not match the session's tenant fails the suite. Run it in CI.
5. For admin / cross-tenant flows (reporting, support impersonation), require an explicit `withCrossTenant(reason)` wrapper that logs the access and is gated by a separate role.
6. Reversibility: once leaked, the data is leaked. Treat any confirmed cross-agency leak as a P0 incident: rotate exposed PII where possible, notify affected tenants, file breach disclosures per state law.

## CWE / standard refs

- CWE-639: Authorization Bypass Through User-Controlled Key. The "key" here is the tenant id (agency id) that the server should derive from the session but instead reads from a client-controlled field, or filters by an object id without re-checking tenant ownership.

## See also

- `wos/bug-classes/pii-encryption-boundary-leak.md` -- sibling class covering encrypted-PII boundaries within a single tenant.
- `wos/personas/rls-auth-boundary-auditor.md` -- persona that audits RLS + tenant-scope coverage end to end.
- `wos/multi-repo-support.md` -- where tenant scoping crosses repo boundaries (web app + workers + edge functions).
