---
name: sibling-controller-divergence
category: convention-drift
default-severity: P2
cwe: []
languages: [typescript, javascript, python, go]
file-patterns: ["controllers/**", "handlers/**", "api/**"]
perspectives: [maintainer]
reversibility-check: false
---

# sibling-controller-divergence

## Trigger

A newly added or modified controller method handles cross-cutting concerns (error handling, logging, validation, auth checks, response shape) differently from sibling methods in the same file or same controller directory. The divergence is not justified by different business requirements but appears to be an oversight or copy-paste drift.

## Detection

Compare the new/modified method against other methods in the same file or directory:
- Error handling pattern: does it use the same error wrapper (`HttpError.fromDataBaseError`, try/catch shape, error response format)?
- Logging: does it log at the same points (entry, exit, error) with the same structured fields?
- Validation: does it validate inputs the same way (manual checks vs library, same response codes)?
- Auth checks: does it use the same middleware stack and ownership validation pattern?
- Response shape: does it return `{ success, data }` like siblings, or a bare object?

## Retrieval

- The new/modified method (full body)
- Up to 3 sibling methods in the same file or directory (for convention baseline)

## Analysis prompt

Given the new method and its siblings:
1. List the cross-cutting patterns siblings share (error handling, logging, validation, auth, response shape).
2. For each pattern, does the new method follow the same convention?
3. If it diverges: is the divergence justified by different business requirements, or is it an oversight?
4. What specific lines should change to align with the sibling convention?

## Severity rubric

- P0: never (convention drift is not a correctness bug)
- P1: divergence in auth/security handling (e.g., siblings check ownership, new method skips it)
- P2: divergence in error handling, logging, validation, or response shape (consistency concern, not security)

## Confidence factors

- HIGH: 3+ siblings follow the same pattern; the new method clearly diverges on the same concern
- MEDIUM: 2 siblings follow a pattern; new method diverges but the codebase is inconsistent generally
- LOW: only 1 sibling for comparison; divergence may be intentional

## Examples

### Positive (real bug)

```typescript
// Sibling methods all use HttpError.fromDataBaseError:
static getUser = asyncHandler(async (req, res) => {
  const { data, error } = await db.from("users").select("*").eq("id", id).single();
  if (error) throw HttpError.fromDataBaseError(error); // convention
  res.json(data);
});

// New method uses raw throw:
static createShare = asyncHandler(async (req, res) => {
  const { data, error } = await db.from("shares").insert({...}).single();
  if (error) throw new Error(error.message); // diverges from sibling convention
  res.json(data);
});
```

### Negative (not a bug)

Both methods use the same error handling but return different response shapes because they serve different API contracts (one is internal, one is public).
