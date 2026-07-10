---
name: unsafe-type-assertion
category: type-safety
default-severity: P1
cwe: [CWE-476]
languages: [typescript]
file-patterns: ["**/*.ts"]
perspectives: [security, maintainer]
reversibility-check: false
---

# unsafe-type-assertion

## Trigger

A TypeScript `as unknown as T` (or equivalent double-cast) is used to narrow a value whose runtime shape may differ from the asserted type. The cast silences the type checker, but at runtime the value can be `undefined`, an array instead of an object, or a different shape entirely. When the cast result is used in a security-critical decision (authorization check, ownership validation, access control), `undefined` can silently pass equality checks and grant unauthorized access.

## Detection

Look for patterns in TypeScript files where:
- `as unknown as` appears (the canonical double-cast escape hatch)
- The cast result is used within 10 lines in a comparison (`!==`, `===`, `!=`, `==`) that gates an authorization or access-control decision
- The cast is applied to a value returned by an ORM, query builder, or API client that may return arrays for one-to-many relations or `null` for missing joins

Grep patterns:
- `as unknown as`
- `as any` followed by property access

## Retrieval

- The function body containing the cast
- The query or API call that produces the value being cast (to verify whether it can return array or null)
- Up to 2 other locations in the same file that use similar casts (to compare: does the sibling use a runtime narrowing check?)

## Analysis prompt

Given the cast and its usage:
1. What is the actual runtime shape of the value before the cast? Can it be an array (ORM one-to-many), null (missing join), or undefined (optional field)?
2. How is the cast result used? Is it in a security-critical decision (auth check, ownership validation, scope filter) or in data rendering (display, logging)?
3. If the runtime shape is an array when the cast asserts an object, what is the concrete consequence? Does `value?.property` return `undefined` and silently pass a `!==` check?
4. What is the recommended fix? Options: (a) Add `Array.isArray` narrowing before access. (b) Use a helper function like `firstRelation(rel)` that handles both shapes. (c) Validate the shape at the query layer (e.g., use `.single()` instead of `.maybeSingle()` if the relation is truly 1:1).

## Severity rubric

- P0: cast result feeds an authorization or access-control check; `undefined` from a mismatched shape would silently bypass the check
- P1: cast result feeds data rendering or business logic; `undefined` produces wrong output but no security bypass
- P2: cast result is used in non-critical context (logging, metrics, display-only fields)

## Confidence factors

- HIGH: cast is on a value from an ORM nested join AND the cast result is used in an auth/ownership check within 10 lines
- MEDIUM: cast is on an ORM value but used in data rendering; wrong shape causes wrong UI but no security issue
- LOW: cast exists but usage is unclear, or the query shape is verified elsewhere (e.g., integration test that would fail on wrong shape)

## Examples

### Positive (real bug)

```typescript
// Supabase returns nested joins as arrays for some relation types
const claim = await supabase.from("claims")
  .select("id, parent_table(company_id)")
  .eq("id", claimId)
  .maybeSingle();

// Unsafe: if parent_table is an array, .company_id is undefined
const companyId = (claim as unknown as { parent_table: { company_id: string } })
  .parent_table?.company_id;

// undefined !== req.auth.companyId evaluates to TRUE: authorization bypassed!
if (companyId !== req.auth.companyId) {
  throw new ForbiddenError();
}
```

### Negative (safe pattern)

```typescript
function firstRelation<T extends object>(rel: T | T[] | null | undefined): T | null {
  if (rel == null) return null;
  if (Array.isArray(rel)) return rel[0] ?? null;
  return rel;
}

const parentTable = firstRelation(
  (claim as unknown as { parent_table: unknown }).parent_table
);
const companyId = parentTable?.company_id;

// Explicitly reject if companyId could not be resolved
if (!companyId || companyId !== req.auth.companyId) {
  throw new ForbiddenError();
}
```
