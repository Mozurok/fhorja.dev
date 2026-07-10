---
name: missing-rate-limit-on-write
category: security
default-severity: P1
cwe: [CWE-770]
languages: [typescript, javascript, python, go]
file-patterns: ["routes/**", "api/**", "handlers/**"]
perspectives: [security, operator]
reversibility-check: false
---

# missing-rate-limit-on-write

## Trigger

A write endpoint (POST, PUT, PATCH, DELETE) that creates resources, sends notifications, or modifies state is registered without a rate-limiting middleware, while sibling write endpoints in the same file or service do have rate limiting. The unprotected endpoint can be abused for resource exhaustion, notification spam, or audit-log flooding.

## Detection

Compare route registrations in the same file:
- For each `router.post`, `router.put`, `router.patch`, `router.delete`: does it include a rate-limit middleware in its middleware chain?
- If some routes have rate limiting and others do not: flag the ones without
- Also flag write endpoints that trigger external side effects (email send, SMS, webhook) without any rate protection

Grep patterns:
- `router.post(` or `app.post(` without a rate-limit middleware in the same call
- `router.put(`, `router.patch(`, `router.delete(` without rate-limit

## Retrieval

- The route registration file (full file, to see all sibling routes)
- The controller method the route points to (to verify if it has side effects like email/SMS)

## Analysis prompt

Given the route registrations:
1. Which write routes have rate limiting? Which do not?
2. For unprotected routes: do they trigger side effects (email, SMS, webhook, audit writes)?
3. Is there a pattern: all public routes are rate-limited but internal-only routes are not? If so, is the flagged route truly internal-only?
4. What is the recommended rate limit (requests per minute per user/IP)?

## Severity rubric

- P0: unprotected endpoint sends external notifications (email, SMS) and can be used as a spam vector
- P1: unprotected endpoint writes to DB (creates resources, modifies state) and can cause DoS or audit flooding
- P2: unprotected endpoint is idempotent or internal-only with minimal abuse potential

## Confidence factors

- HIGH: sibling routes in the same file have rate limiting; this one does not; it triggers side effects
- MEDIUM: no sibling comparison (only route in file), but the endpoint has clear side effects
- LOW: endpoint is read-heavy (GET with side effects) or the rate limit may be applied at a higher layer (reverse proxy, WAF)

## Examples

### Positive (real bug)

```typescript
// Sibling route has rate limiting:
router.post("/:id/share", requireWriteAccess, createShareRateLimit, ctrl.createShare);
// New route missing it:
router.post("/:id/share/:shareId/revoke", requireWriteAccess, ctrl.revokeShare);
// An authenticated caller can loop over share IDs and flood the audit log
```

### Negative (safe pattern)

```typescript
router.post("/:id/share", requireWriteAccess, createShareRateLimit, ctrl.createShare);
router.post("/:id/share/:shareId/revoke", requireWriteAccess, createShareRateLimit, ctrl.revokeShare);
// Both routes share the same rate limiter
```
