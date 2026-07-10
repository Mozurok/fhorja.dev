---
name: documentation-drift
category: quality
default-severity: P2
cwe: []
languages: [typescript, javascript, python, go]
file-patterns: ["**/*.ts", "**/*.js", "**/*.py", "**/*.go", "**/*.md"]
perspectives: [maintainer, api-consumer]
reversibility-check: false
---

# documentation-drift

## Trigger

A function signature, API endpoint, or configuration schema was changed in the diff, but the corresponding documentation (inline docstring, README section, OpenAPI spec, or adjacent .md file) was not updated. The stale documentation will mislead future developers or API consumers.

## Detection

For each function or endpoint modified in the diff:
- Did the parameter list change (added, removed, renamed, type changed)?
- Did the return type or response shape change?
- Did the error codes or error messages change?
- If yes to any: is there a docstring, JSDoc, or adjacent documentation file that describes the old signature?
- Was that documentation also modified in the diff?

Grep patterns:
- Modified function declarations (`function X(`, `static X =`, `def X(`) where parameter names changed
- Modified route registrations (`router.post(`, `app.get(`) where path or middleware changed
- Look for JSDoc/docstring blocks above the modified function that still reference old parameter names

## Retrieval

- The modified function (old and new signatures from the diff)
- The docstring or JSDoc block above it (if any)
- Adjacent README or API documentation files in the same directory

## Analysis prompt

Given the modified function and its documentation:
1. What changed in the function signature (parameters, return type, error codes)?
2. Does the existing documentation reference the OLD signature?
3. If yes: which specific lines of documentation need updating?
4. If no documentation exists: should there be? (Use judgment: trivial helpers need no docs; public API endpoints do.)

## Severity rubric

- P0: never
- P1: public API endpoint documentation is stale (external consumers will build against wrong contract)
- P2: internal function docstring is stale (maintainability concern)

## Confidence factors

- HIGH: function parameters were renamed or removed AND the docstring explicitly references the old names
- MEDIUM: function return type changed but docstring describes behavior generically (may still be accurate)
- LOW: function body changed but signature is identical (docstring may still be correct)

## Examples

### Positive (drift)

```typescript
/**
 * @param ttl_hours - TTL in hours (1, 24, or 168)
 * @returns { share_id, share_url }
 */
async function createShare(req, res) {
  // Function now also accepts `recipient_phone` parameter
  // and returns `expires_at` in the response
  // But the JSDoc above still describes the old signature
}
```

### Negative (up-to-date)

```typescript
/**
 * @param ttl_hours - TTL in hours (1, 24, or 168)
 * @param recipient_email - email of the share recipient
 * @returns { share_id, share_url, expires_at }
 */
async function createShare(req, res) { ... }
```
