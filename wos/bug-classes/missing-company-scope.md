---
name: missing-company-scope
category: multi-tenant
default-severity: P0
cwe: [CWE-862, CWE-863]
languages: [typescript, javascript, python, go, sql]
file-patterns: ["controllers/**", "services/**", "handlers/**", "api/**", "routes/**"]
perspectives: [security]
reversibility-check: false
---

# missing-company-scope

## Trigger

A database query in a multi-tenant application reads or writes data without filtering by the caller's tenant identifier (company_id, org_id, workspace_id, or equivalent). The missing scope allows one tenant to access or modify another tenant's data.

This is a generic multi-tenant invariant. Project-specific overrides can customize the tenant column name and the method used to extract the caller's tenant from the request context (e.g., `req.auth.companyId`, `g.tenant_id`, `request.user.org_id`).

## Detection

For each DB query in the diff:
- Does the query filter by tenant ID? Look for `.eq("company_id", ...)` or `WHERE company_id = ...` or equivalent
- Does the controller extract tenant ID from the auth context? Look for `req.auth.companyId` or equivalent
- Is the query using an admin/service-role client that bypasses RLS? If so, the application-layer filter is the only protection

Grep patterns:
- `.from("table_name")` without `.eq("company_id",` in the same chain
- `SELECT ... FROM table_name` without `WHERE company_id` or `AND company_id`

## Retrieval

- The controller or service function containing the query
- The auth middleware (to verify how tenant ID is extracted)
- The DB schema or migration for the queried table (to confirm it has a tenant column)
- `wos/bug-classes/_shared/multi-tenant-invariant.md` for project-specific tenant conventions

## Analysis prompt

<!-- shared:multi-tenant-invariant:tenant-scope-check -->

Given the query and its auth context:
1. Does the queried table have a tenant-scoping column (company_id, org_id, etc.)?
2. Does the query filter by that column using the caller's tenant from the auth context?
3. If the query uses an admin client (bypasses RLS): is the application-layer filter present and correct?
4. If the filter is missing: what is the blast radius? Can tenant A see or modify tenant B's data?
5. Are there sibling queries in the same file that do include the scope filter? If so, the missing one is likely an oversight.

## Severity rubric

- P0: missing scope on a query that returns or modifies customer data (cross-tenant data exposure or mutation)
- P1: missing scope on a query that returns aggregate or non-sensitive data (cross-tenant information leak without PII)
- P2: missing scope on an internal or admin-only query where cross-tenant access is intentional and documented

## Confidence factors

- HIGH: table has a tenant column; sibling queries in the same file include the scope filter; this one does not
- MEDIUM: table has a tenant column; no sibling queries for comparison but the auth context is available
- LOW: table may not have a tenant column (shared lookup table, enum table); cross-tenant access may be by design

## Examples

### Positive (real bug)

```typescript
// Query fetches a verification run by ID without company_id filter:
const { data: run } = await supabase
  .from("verification_runs")
  .select("id, status, company_id")
  .eq("id", runId)
  .maybeSingle();
// Any authenticated user with a valid run ID can access any company's run
```

### Negative (safe pattern)

```typescript
const { data: run } = await supabase
  .from("verification_runs")
  .select("id, status, company_id")
  .eq("id", runId)
  .maybeSingle();

if (!run || run.company_id !== req.auth.companyId) {
  throw HttpError.notFound("Run not found");
}
// Post-query ownership check ensures cross-tenant access is denied
```
