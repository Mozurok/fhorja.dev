---
name: auth-boundary-test-bypass
category: testing
default-severity: P1
cwe: [CWE-287]
languages: [typescript, javascript, python, go]
file-patterns: ["**/*.test.*", "**/*.spec.*", "**/tests/**", "**/__tests__/**", "**/test-server.*", "**/test-setup.*", "**/test-utils.*"]
perspectives: [security, maintainer]
reversibility-check: false
---

# auth-boundary-test-bypass

## Trigger

A test harness or shared setup utility for route/integration tests injects the POST-AUTHENTICATION request state directly (e.g. `req.auth = {...}`, `req.user = {...}`, pre-decoded JWT claims) instead of letting a real request flow through the actual authentication/authorization middleware. Every test built on that harness is structurally incapable of exercising the real header-parsing, token-validation, or credential-checking code, no matter how many tests exist or how business-logic-correct they are. This is most dangerous on endpoints that accept credentials from an external, un-controlled caller (an inbound webhook, a partner API-key integration, a public callback URL), where the real caller's request shape may never match what the team assumes.

## Detection

Look for:
- A shared test-server/test-app factory function that sets `req.auth`, `req.user`, `req.session`, or similar post-auth state directly in a middleware stub, before any route handlers run (grep for patterns like `req.auth =`, `req.user =` inside `tests/setup/**`, `test/helpers/**`, or similarly named shared test infrastructure).
- Route/integration test files for that surface that never set a real `Authorization`, `X-API-Key`, `Cookie`, or other credential-bearing header via the HTTP client (`.set("Authorization", ...)`, `.set("X-API-Key", ...)`, `.headers({...})`) -- i.e. a route test suite with zero occurrences of the literal header names the real middleware reads.
- Cross-reference: read the real authentication middleware's header-extraction functions (what header name, what format, what validation) and confirm the test suite's coverage report or "N/N passing" status is being cited as evidence that specific format is exercised, when it structurally cannot be.

## Retrieval

- The shared test-server/test-harness setup file (the mock middleware)
- The real authentication/authorization middleware it stubs past (to know what header/format/validation it actually implements)
- The route/integration test file(s) for the endpoint in question

## Analysis prompt

Given the test harness and the real middleware:
1. Does the harness inject `req.auth`/`req.user`/decoded-claims state directly, bypassing a call into the real middleware function?
2. Grep the corresponding route/integration test file(s) for the literal header-setting calls (`.set("Authorization"`, `.set("X-API-Key"`, etc.) that the real middleware reads. Zero matches means the real auth code path has zero automated coverage from this suite, regardless of how many tests pass.
3. Is this endpoint reachable by an external, un-controlled caller (an inbound webhook, a partner integration, a public API)? If so, is the auth format that caller will actually send confirmed by a live capture or vendor documentation, or only assumed to match what the mocked tests exercise?
4. If the answer to #2 is "zero coverage" and #3 is "external caller, format unconfirmed or unverified," this is a real, currently-broken-or-open gap, not a theoretical one: recommend either (a) adding at least one test that drives a real request through the actual middleware with the real (or best-known-real) header shape, or (b) explicitly documenting the auth boundary as untested in the PR/task memory so it cannot be silently treated as covered.

## Severity rubric

- P0: the endpoint accepts credentials from an external, un-controlled vendor/partner and the real auth format is unconfirmed against live vendor behavior (the boundary may already be completely broken or completely open)
- P1: the endpoint is internal-only or the auth format is otherwise confirmed, but the test suite still gives zero coverage of the real middleware code path

## Confidence factors

- HIGH: shared test harness sets `req.auth`/`req.user` directly with no call into the real middleware AND a grep of the route test file(s) for the real header name(s) returns zero matches
- MEDIUM: the harness bypasses the middleware but at least one test in the suite does set a real credential header for a positive-path check
- LOW: the harness only stubs a non-auth-adjacent dependency (DB, logger) and the auth middleware itself does run for real in tests

## Examples

### Positive (auth boundary bypassed)

```typescript
// tests/setup/test-server.ts
app.use((req, _res, next) => {
  if (authContext) {
    req.auth = authContext; // injects post-auth state directly
  }
  next();
});
```

```typescript
// tests/routes/integrations-vendor.test.ts
it("ingests a shipment", async () => {
  const res = await request(app).post("/integrations/vendor/shipments").send(payload);
  // never calls .set("Authorization", ...) or .set("X-API-Key", ...) anywhere in this file
  expect(res.status).toBe(201);
});
```

### Negative (real boundary exercised)

```typescript
// tests/routes/integrations-vendor.test.ts
it("authenticates with the vendor's real header shape", async () => {
  const res = await request(app)
    .post("/integrations/vendor/shipments")
    .set("Authorization", rawVendorApiKey) // no Bearer prefix, matches the vendor's documented delivery
    .send(payload);
  expect(res.status).toBe(201); // exercises the REAL middleware's header parsing, not a stub
});
```
