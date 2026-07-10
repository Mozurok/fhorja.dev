---
name: missing-csrf-protection
category: security
default-severity: P1
cwe: [CWE-352]
languages: [typescript, javascript, python, go]
file-patterns: ["routes/**", "api/**", "handlers/**", "middleware/**"]
perspectives: [security]
reversibility-check: false
---

# missing-csrf-protection

## Trigger

A state-changing endpoint (POST, PUT, PATCH, DELETE) that is callable from a browser session (cookie-based auth, session tokens) does not validate a CSRF token or use an alternative mitigation (SameSite cookies, custom request headers). An attacker can craft a page that tricks a logged-in user's browser into making an unintended request.

## Detection

Look for:
- POST/PUT/PATCH/DELETE routes that authenticate via cookies or session tokens (not API keys or Bearer tokens from localStorage)
- No CSRF middleware in the route's middleware chain (e.g., `csurf`, `csrf-csrf`, Django's `@csrf_protect`, Go's `gorilla/csrf`)
- No `SameSite=Strict` or `SameSite=Lax` on the session cookie

Exclude:
- Endpoints authenticated via Bearer token in the Authorization header (not vulnerable to CSRF because browsers do not auto-attach Authorization headers)
- Endpoints authenticated via API key in a custom header (same reason)
- Public/unauthenticated endpoints (no session to hijack)

## Retrieval

- The route registration and its middleware chain
- The auth middleware (to determine if auth is cookie-based or header-based)
- The cookie configuration (to check SameSite attribute)

## Analysis prompt

Given the route and its auth mechanism:
1. Is the endpoint authenticated via cookies or session tokens that the browser automatically attaches?
2. If yes: is there a CSRF token validation middleware in the chain?
3. If no CSRF middleware: are the cookies set with `SameSite=Strict` or `SameSite=Lax`?
4. If neither CSRF token nor SameSite: the endpoint is vulnerable. Recommend adding CSRF middleware or switching to SameSite cookies.
5. If auth is via Bearer token in Authorization header: not vulnerable (browsers do not auto-attach this header from cross-origin requests).

## Severity rubric

- P0: state-changing endpoint with cookie auth, no CSRF protection, and the action is destructive (delete, payment, admin privilege change)
- P1: state-changing endpoint with cookie auth, no CSRF protection, and the action is non-destructive but modifies user data
- P2: endpoint uses cookie auth but SameSite=Lax mitigates most CSRF vectors (only top-level navigations are vulnerable)

## Confidence factors

- HIGH: route uses cookie auth; no CSRF middleware; action is state-changing
- MEDIUM: route uses cookie auth with SameSite=Lax; most vectors mitigated but not all
- LOW: route uses Bearer token auth (not vulnerable); or endpoint is read-only despite being POST

## Examples

### Positive (vulnerable)

```typescript
// Cookie-based session auth, no CSRF protection
app.post("/account/delete", sessionAuth, ctrl.deleteAccount);
// Attacker's page: <form action="https://app.example.com/account/delete" method="POST"><button>Click me</button></form>
```

### Negative (not vulnerable)

```typescript
// Bearer token auth (not auto-attached by browser)
router.post("/:id/share", requireWriteAccess, ctrl.createShare);
// Authorization: Bearer <token> must be explicitly set by client JS; not vulnerable to CSRF
```
