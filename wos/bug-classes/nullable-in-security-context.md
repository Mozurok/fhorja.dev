---
name: nullable-in-security-context
category: type-safety
default-severity: P0
cwe: [CWE-476, CWE-862]
languages: [typescript, javascript, python, go]
file-patterns: ["controllers/**", "middleware/**", "handlers/**", "api/**", "auth/**"]
perspectives: [security]
reversibility-check: false
---

# nullable-in-security-context

## Trigger

A value that can be null, undefined, or absent at runtime is used directly in a security-critical comparison (authorization check, scope filter, ownership validation) without an explicit null guard. When the value is nullish, the comparison produces an unexpected result that silently grants access.

## Detection

Look for patterns where:
- A variable from an external source (DB query, request param, JWT claim, config) is used in `!==`, `===`, `!=`, `==` within 5 lines of a throw/return that gates access
- The variable's type signature or origin allows null/undefined
- There is no explicit `if (!value)` or `value == null` guard before the comparison

## Retrieval

- The function body containing the comparison
- The source of the variable (query, request, config) to verify nullability
- Up to 2 sibling functions that perform similar checks (to see if they guard correctly)

## Analysis prompt

Given the comparison:
1. Can the left-hand value be null or undefined at runtime? What source produces it?
2. If nullish: does `null !== expectedValue` evaluate to true (granting access) or false (denying)?
3. What is the concrete consequence if access is silently granted? (e.g., cross-tenant data access, privilege escalation)
4. Is adding `if (!value) throw ForbiddenError()` before the comparison the correct fix, or is the nullability itself the bug (should the source guarantee non-null)?

## Severity rubric

- P0: nullish value silently passes an authorization or ownership check, granting cross-tenant or cross-user access
- P1: nullish value causes wrong data to be returned but no privilege escalation
- P2: nullish value in a non-security comparison (display, logging)

## Confidence factors

- HIGH: the value comes from a DB join or external API that can return null; the comparison gates authorization
- MEDIUM: the value comes from a validated source but the type allows null (defensive check recommended)
- LOW: the value's nullability is theoretical; the upstream guarantees non-null in practice

## Examples

### Positive (real bug)

```typescript
const companyId = claim.verification_runs?.company_id; // can be undefined if join fails
if (companyId !== req.auth.companyId) {
  throw new ForbiddenError();
}
// undefined !== "real-company-id" is TRUE: ForbiddenError thrown (accidental denial)
// undefined !== undefined is FALSE: check passes (accidental access if both are undefined)
```

### Negative (safe pattern)

```typescript
const companyId = claim.verification_runs?.company_id;
if (!companyId || companyId !== req.auth.companyId) {
  throw new ForbiddenError();
}
// Explicit null guard: if companyId is undefined, access is denied regardless
```
