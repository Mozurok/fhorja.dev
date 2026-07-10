# Multi-tenant invariant prompt fragments

Reusable analysis prompts for multi-tenant safety checks. Referenced by bug-class templates via `<!-- shared:multi-tenant-invariant:tenant-scope-check -->`.

## tenant-scope-check

Read the query and its surrounding authorization context. Ask:

1. **Does this table have a tenant column?** Common names: `company_id`, `org_id`, `organization_id`, `workspace_id`, `tenant_id`, `account_id`. If the table has no tenant column, it may be a shared lookup table where cross-tenant access is by design (skip this check).

2. **Is the query filtered by the caller's tenant?** Look for:
   - Supabase: `.eq("company_id", req.auth.companyId)` or equivalent
   - SQL: `WHERE company_id = $1` with the parameter bound from auth context
   - ORM: `.filter(company_id=request.user.org_id)` or similar

3. **If using a service-role or admin client (bypasses RLS):** The application layer is the only protection. Is the tenant filter present in the query chain itself, or is there a post-query ownership check (`if (row.company_id !== auth.companyId) throw`)?

4. **Is the endpoint authenticated?** Unauthenticated endpoints that query tenant-scoped tables without RLS protection are P0 regardless of other factors.

5. **Sibling queries in the same file:** Do they include the tenant filter? If 3 out of 4 queries filter by `company_id` and 1 does not, the missing one is likely an oversight.

## tenant-mutation-check

For write operations (INSERT, UPDATE, DELETE):

1. **Does the INSERT set the tenant column explicitly?** If omitted and the column has no default trigger, the row may be unscoped (null tenant) and visible to all tenants.

2. **Does the UPDATE/DELETE filter by tenant?** A missing tenant filter on UPDATE could modify another tenant's rows. On DELETE, it could remove them.

3. **Is there a CHECK constraint or trigger ensuring tenant consistency?** If the application layer is the only enforcement, missing the filter is a single-point-of-failure.
