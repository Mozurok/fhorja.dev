---
name: non-transactional-multi-write
category: ordering-bug
default-severity: P1
cwe: []
languages: [typescript, javascript, python, go, sql]
file-patterns: ["controllers/**", "services/**", "handlers/**", "api/**"]
perspectives: [operator]
reversibility-check: true
---

# non-transactional-multi-write

## Trigger

Two or more write operations (INSERT, UPDATE, DELETE) against the same database that should succeed or fail atomically are executed as independent awaited calls without a transaction wrapper. If the second write fails, the first is already committed, leaving the data in an inconsistent state.

## Detection

Look for function bodies where:
- Two or more `.insert(`, `.update(`, `.delete(`, or raw SQL writes appear as independent `await` calls
- The operations touch related tables (same entity lifecycle, same FK chain, or same business event)
- No explicit transaction wrapper (`BEGIN`/`COMMIT`, `.transaction(`, or ORM equivalent) is present

## Retrieval

- The full function body containing the writes
- The database schema or migration for the tables involved (to verify FK relationships)

## Analysis prompt

Given the function body:
1. Are the writes semantically atomic (should both succeed or both fail)?
2. If the second write fails after the first commits, what inconsistent state results?
3. Is wrapping in a transaction feasible (same DB connection, same request lifecycle)?
4. If transactions are not available (e.g., cross-service writes), is there a compensating action or idempotent retry path?

## Severity rubric

- P0: inconsistent state causes data loss, security bypass, or financial impact with no self-recovery
- P1: inconsistent state causes degraded UX or requires manual intervention to fix
- P2: inconsistent state is detectable and auto-recoverable (e.g., background job cleans up)

## Confidence factors

- HIGH: both writes touch the same entity or FK-linked entities; no transaction wrapper visible
- MEDIUM: writes touch related entities but the relationship is indirect
- LOW: writes appear independent; atomicity may not be required

## Examples

### Positive (real bug)

```typescript
await db.from("orders").update({ status: "shipped" }).eq("id", orderId);
await db.from("inventory").update({ quantity: quantity - 1 }).eq("sku", sku);
// If inventory update fails, order is marked shipped but stock is unchanged
```

### Negative (safe pattern)

```typescript
await db.rpc("ship_order_and_decrement_inventory", {
  p_order_id: orderId,
  p_sku: sku,
  p_quantity: 1,
});
// Single RPC wraps both writes in a DB transaction
```
