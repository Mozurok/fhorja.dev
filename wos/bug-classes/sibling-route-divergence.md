---
name: sibling-route-divergence
category: convention-drift
default-severity: P2
cwe: []
languages: [typescript, javascript, python, go]
file-patterns: ["routes/**", "api/**"]
perspectives: [maintainer]
reversibility-check: false
---

# sibling-route-divergence

## Trigger

Routes registered in the same file or router use different middleware stacks for the same class of operation. For example, one POST route has rate limiting and another POST route in the same file does not, or one route applies an auth middleware that a sibling skips.

## Detection

Within a single route file, compare the middleware chains of all route registrations:
- List all `router.post`, `router.put`, `router.patch`, `router.delete` calls
- For each, extract the middleware chain (functions between the path and the handler)
- Flag routes where the middleware set diverges from the majority pattern for the same HTTP method

## Retrieval

- The full route file (to see all registrations side by side)
- The middleware definitions (to confirm what each middleware does)

## Analysis prompt

Given the route file:
1. List all route registrations with their middleware chains.
2. Group by HTTP method (POST, GET, etc.).
3. Within each group: is the middleware chain consistent? Which routes diverge?
4. For each divergence: is it intentional (e.g., one route is internal-only, another is public) or an oversight?
5. If oversight: which middleware is missing and on which route?

## Severity rubric

- P0: never (convention drift is a consistency concern)
- P1: divergence involves auth or rate-limiting middleware (security-adjacent)
- P2: divergence involves logging, validation, or response formatting middleware

## Confidence factors

- HIGH: 3+ sibling routes share a middleware; 1 route omits it; no documented reason for the difference
- MEDIUM: 2 routes with different middleware; may be intentional (internal vs public)
- LOW: routes serve clearly different purposes (e.g., health check vs business endpoint)

## Examples

### Positive (divergence)

```typescript
router.post("/:id/share", requireWriteAccess, createShareRateLimit, ctrl.createShare);
router.post("/:id/share/:shareId/revoke", requireWriteAccess, ctrl.revokeShare);
// revokeShare missing rate limit that createShare has
```

### Negative (consistent)

```typescript
router.post("/:id/share", requireWriteAccess, createShareRateLimit, ctrl.createShare);
router.post("/:id/share/:shareId/revoke", requireWriteAccess, createShareRateLimit, ctrl.revokeShare);
// Both routes share the same middleware chain
```
