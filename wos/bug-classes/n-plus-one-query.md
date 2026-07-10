---
name: n-plus-one-query
category: performance
default-severity: P1
cwe: [CWE-400]
languages: [typescript, javascript, python, go]
file-patterns: ["controllers/**", "services/**", "handlers/**", "api/**", "consumers/**"]
perspectives: [operator]
reversibility-check: false
---

# n-plus-one-query

## Trigger

A loop iterates over a collection and executes a database query on each iteration, resulting in N+1 total queries (1 to fetch the collection, N to fetch related data per item). This pattern degrades linearly with data size and can cause severe latency or connection pool exhaustion under load.

## Detection

Look for patterns where:
- A query returns an array of results, then a `for`/`forEach`/`map`/`for...of` loop runs a query per element
- `.select(...)` or `query(...)` appears inside a loop body or a `.map(async ...)` callback
- The inner query could be replaced with a batch query, a JOIN, or a single query with an `IN (...)` clause

Grep patterns:
- `for.*await.*from\(` or `forEach.*await.*select\(`
- `.map(async` followed by `.from(` or `.query(` within 10 lines
- `Promise.all(items.map(` followed by a query call per item

## Retrieval

- The function body containing the loop + inner query
- The database schema (to verify if a JOIN or batch query is feasible)

## Analysis prompt

Given the loop and inner query:
1. How many iterations does this loop typically run? (10? 100? 1000?)
2. Can the inner query be replaced with: (a) a JOIN in the outer query, (b) an `IN (...)` batch query, (c) a single RPC that handles the batch?
3. What is the performance impact at current scale? At 10x scale?
4. If batching is not feasible (different DBs, external API), is there a caching layer that mitigates?

## Severity rubric

- P0: N+1 on a user-facing API endpoint where N can exceed 100 (causes visible latency)
- P1: N+1 on a background job or internal endpoint where N is moderate (10-100) but grows with data
- P2: N+1 where N is inherently small (less than 10) and unlikely to grow

## Confidence factors

- HIGH: query call is visibly inside a loop body; the outer query returns a list that grows with usage
- MEDIUM: query is inside a `.map(async ...)` or `Promise.all(...)` that may or may not be a loop
- LOW: the "loop" is over a fixed small set (enum values, config entries) that does not grow

## Examples

### Positive (N+1)

```typescript
const drivers = await db.from("drivers").select("id, name");
for (const driver of drivers) {
  const license = await db.from("licenses").select("*").eq("driver_id", driver.id).single();
  results.push({ ...driver, license });
}
// 1 query for drivers + N queries for licenses = N+1
```

### Negative (batched)

```typescript
const drivers = await db.from("drivers").select("id, name, licenses(*)");
// Single query with JOIN; 0 extra queries
```
