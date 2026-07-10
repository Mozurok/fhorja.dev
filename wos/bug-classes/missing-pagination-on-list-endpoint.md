---
name: missing-pagination-on-list-endpoint
category: performance
default-severity: P1
cwe: [CWE-770]
languages: [typescript, javascript, python, go]
file-patterns: ["controllers/**", "handlers/**", "api/**", "routes/**"]
perspectives: [operator, api-consumer]
reversibility-check: false
---

# missing-pagination-on-list-endpoint

## Trigger

A list endpoint (GET that returns an array of items) returns the full dataset without pagination parameters (limit/offset, cursor, page/pageSize). As data grows, the response payload inflates unboundedly, causing slow responses, high memory usage, client-side rendering issues, and potential timeouts.

## Detection

Look for GET handlers that:
- Query a transactional table (grows with usage) without `.limit()` or `LIMIT` clause
- Return `res.json(data)` where `data` is an array with no size cap
- Accept no pagination query params (`?page=`, `?limit=`, `?cursor=`, `?offset=`)
- The response shape has no `total`, `hasMore`, `nextCursor`, or `pagination` metadata

Exclude:
- Endpoints that return bounded data by nature (enum values, config, user's own profile)
- Endpoints with `.single()` or `.maybeSingle()` (return one item)
- Internal admin endpoints explicitly designed for bulk export

## Retrieval

- The handler function body
- The query (to check for LIMIT/pagination)
- The route definition (to check if pagination params are accepted)

## Analysis prompt

Given the list endpoint:
1. What table is being queried? Does it grow with usage?
2. Is there a LIMIT clause or pagination in the query?
3. Does the handler accept pagination params from the request?
4. At what data size does this become a problem? (100 rows? 10,000? 1M?)
5. Recommended pagination strategy: cursor-based (for real-time feeds) or offset-based (for stable lists).

## Severity rubric

- P0: public API endpoint without pagination on a high-growth table (partner consumers will hit timeouts)
- P1: internal endpoint without pagination on a moderately growing table
- P2: endpoint on a slow-growing table where the current size is manageable

## Confidence factors

- HIGH: GET endpoint returns array from a transactional table; no limit/offset/cursor in query or params
- MEDIUM: endpoint has a hardcoded limit (e.g., `.limit(1000)`) but no dynamic pagination params
- LOW: table growth is bounded by business rules (e.g., max 50 items per company)

## Examples

### Positive (no pagination)

```typescript
app.get("/drivers", async (req, res) => {
  const { data } = await db.from("drivers").select("*").eq("company_id", companyId);
  res.json(data); // returns ALL drivers; could be thousands
});
```

### Negative (paginated)

```typescript
app.get("/drivers", async (req, res) => {
  const limit = Math.min(Number(req.query.limit) || 50, 100);
  const offset = Number(req.query.offset) || 0;
  const { data, count } = await db.from("drivers").select("*", { count: "exact" })
    .eq("company_id", companyId).range(offset, offset + limit - 1);
  res.json({ data, total: count, limit, offset });
});
```
