---
name: info-disclosure-via-status-code
category: security
default-severity: P2
cwe: [CWE-209]
languages: [typescript, javascript, python, go]
file-patterns: ["controllers/**", "handlers/**", "routes/**", "api/**"]
perspectives: [security]
reversibility-check: false
---

# info-disclosure-via-status-code

## Trigger

An endpoint returns different HTTP status codes or error body shapes for different internal states of the same entity, enabling an attacker to infer whether a resource exists, is expired, is revoked, or belongs to a different tenant. The differentiation leaks state information that should be opaque to the caller.

## Detection

Look for branching logic in the same handler that returns distinct status codes or error codes based on entity state:
- 404 for "not found" vs 410 for "expired" vs 403 for "wrong tenant"
- Error body includes state-specific codes like `SHARE_EXPIRED`, `SHARE_REVOKED`, `TOKEN_INVALID`

The risk increases when the endpoint is unauthenticated (public-facing) and the entity identifier is guessable or enumerable.

## Retrieval

- The full handler function body
- The route definition (to verify if authenticated or public)
- Sibling handlers (to check if the codebase convention is uniform errors or differentiated)

## Analysis prompt

Given the handler:
1. How many distinct status codes or error shapes does it return for different states of the same entity?
2. Can an attacker use the differences to probe entity state (exists vs expired vs revoked)?
3. Is the endpoint authenticated or public? (Public endpoints have higher risk from probing.)
4. Would collapsing all error cases into a single generic response (e.g., 404 "unavailable") reduce information leak without harming legitimate UX?

## Severity rubric

- P0: differentiated codes on a public endpoint with enumerable identifiers (attacker can map valid vs expired tokens at scale)
- P1: differentiated codes on an authenticated endpoint (attacker needs credentials but can probe internal state)
- P2: differentiated codes but identifiers are UUIDs or high-entropy tokens (probing is infeasible at scale)

## Confidence factors

- HIGH: public endpoint returns 3+ distinct status codes for the same entity; identifiers are low-entropy or sequential
- MEDIUM: 2 distinct codes on a public endpoint; identifiers are UUIDs (probing impractical but state leak is real if ID is known)
- LOW: authenticated endpoint with differentiated codes; attacker already has credentials and can access the entity directly

## Examples

### Positive (information leak)

```typescript
if (!claim) return res.status(404).json({ code: "NOT_FOUND" });
if (claim.revoked_at) return res.status(410).json({ code: "REVOKED" });
if (claim.expired) return res.status(410).json({ code: "EXPIRED" });
// Attacker with a known token can distinguish invalid vs revoked vs expired
```

### Negative (uniform response)

```typescript
if (!claim || claim.revoked_at || claim.expired) {
  return res.status(404).json({ error: { message: "Link unavailable" } });
}
// All failure cases return the same status and body; no state leak
```
