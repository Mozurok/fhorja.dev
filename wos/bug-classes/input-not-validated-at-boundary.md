---
name: input-not-validated-at-boundary
category: data-integrity
default-severity: P1
cwe: [CWE-20]
languages: [typescript, javascript, python, go]
file-patterns: ["controllers/**", "handlers/**", "api/**", "routes/**", "consumers/**"]
perspectives: [security, operator]
reversibility-check: false
---

# input-not-validated-at-boundary

## Trigger

User-supplied input (request body, query params, path params, headers, webhook payload, file upload metadata) reaches business logic or database operations without validation or sanitization at the system boundary. Invalid or malicious input can cause unexpected behavior, data corruption, or security vulnerabilities downstream.

## Detection

Look for controller/handler functions where:
- `req.body`, `req.params`, `req.query`, or equivalent is destructured and used directly in DB queries or business logic
- No validation library (zod, joi, yup, class-validator, pydantic) is applied before use
- No manual type/format/range checks exist before the value reaches a query or function call
- The value is used in a `.eq()`, `.insert()`, `.update()`, or raw SQL without prior validation

Exclude:
- Values validated by middleware before reaching the handler (e.g., request schema validation middleware)
- Internal function parameters that come from trusted upstream code (not from the request boundary)

## Retrieval

- The handler function body (to see where input is consumed)
- The route middleware chain (to check if validation middleware exists upstream)
- The database query or business function that receives the input

## Analysis prompt

Given the input consumption:
1. Where does the input come from? (req.body, req.params, req.query, webhook payload)
2. Is there any validation before it reaches business logic or DB? (zod schema, manual check, middleware)
3. What happens if the input is: (a) wrong type (string instead of number), (b) out of range, (c) missing, (d) maliciously crafted?
4. What is the blast radius of invalid input? (DB constraint error, silent data corruption, crash, security bypass)
5. Recommended fix: add zod/joi schema validation at the handler entry point before destructuring.

## Severity rubric

- P0: unvalidated input feeds a security-critical operation (auth, ownership check, financial amount)
- P1: unvalidated input feeds a DB write or business rule (data corruption risk)
- P2: unvalidated input feeds a read query or display (wrong results but no mutation)

## Confidence factors

- HIGH: `const { X } = req.body` followed directly by `db.insert({ X })` with no validation in between
- MEDIUM: input is partially validated (type check but not range/format) before use
- LOW: validation may exist in middleware not visible in the handler file

## Examples

### Positive (no validation)

```typescript
const { recipient_email, ttl_hours } = req.body;
await db.from("shares").insert({ recipient_email, ttl_hours });
// No check that ttl_hours is a number, is in allowed set, or that email is valid format
```

### Negative (validated)

```typescript
const { recipient_email, ttl_hours } = req.body;
if (typeof recipient_email !== "string" || !EMAIL_REGEX.test(recipient_email)) {
  throw HttpError.badRequest("Invalid email");
}
if (!ALLOWED_TTL.includes(ttl_hours)) {
  throw HttpError.validation("Invalid TTL");
}
await db.from("shares").insert({ recipient_email, ttl_hours });
```
