---
name: unbounded-query
category: resource
default-severity: P2
cwe: [CWE-770]
languages: [typescript, javascript, python, go, sql]
file-patterns: ["controllers/**", "services/**", "handlers/**", "api/**"]
perspectives: [operator]
reversibility-check: false
---

# unbounded-query

## Trigger

A database query fetches rows without a `LIMIT` clause or pagination, and the result set could grow unbounded as data accumulates. On a table with millions of rows, this query can exhaust server memory, saturate the DB connection pool, or cause request timeouts.

## Detection

Look for queries where:
- `.select(...)` without `.limit(N)` or `.range(from, to)` on a table that grows over time
- `SELECT ... FROM <table>` without `LIMIT` in raw SQL
- The result is consumed as an array in memory (not streamed)
- The table is transactional (grows with usage) rather than a lookup/enum table

Exclude:
- Queries with `.single()` or `.maybeSingle()` (inherently bounded)
- Queries on small lookup tables (enum values, config rows, steps_catalog)
- Aggregate queries (`COUNT(*)`, `SUM(...)`) that return a single row

## Retrieval

- The function body containing the query
- The table definition or migration (to assess growth potential: transactional vs lookup)

## Analysis prompt

Given the query:
1. Can the result set grow unbounded over time? What is the growth driver? (users, events, orders, logs)
2. Is there a LIMIT or pagination clause? If not, should there be one?
3. What is the current table size and growth rate? (If unknown, assume it will grow.)
4. Does the consumer iterate the full result in memory, or is there early termination?
5. What LIMIT is appropriate? (Default recommendations: 100 for API responses, 1000 for internal batch jobs.)

## Severity rubric

- P0: unbounded query on a high-traffic endpoint serving external API consumers (can cause cascading failure)
- P1: unbounded query on an internal endpoint or background job (can cause OOM or timeout under load)
- P2: unbounded query on a low-traffic endpoint or small table (unlikely to cause issues in practice but should be bounded defensively)

## Confidence factors

- HIGH: query on a clearly transactional table (orders, events, verification_runs) without LIMIT; consumer loads full array into memory
- MEDIUM: query on a moderately growing table; may have external pagination (client-side limit)
- LOW: query on a small or static table; LIMIT would add no practical benefit

## Examples

### Positive (unbounded)

```typescript
const { data } = await db.from("verification_runs").select("*").eq("company_id", companyId);
// Returns ALL runs for a company; could be thousands
```

### Negative (bounded)

```typescript
const { data } = await db
  .from("verification_runs")
  .select("*")
  .eq("company_id", companyId)
  .order("created_at", { ascending: false })
  .limit(50);
// Bounded to 50 most recent
```
