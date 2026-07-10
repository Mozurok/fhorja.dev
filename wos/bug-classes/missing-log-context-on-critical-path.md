---
name: missing-log-context-on-critical-path
category: observability
default-severity: P1
cwe: []
languages: [typescript, javascript, python, go]
file-patterns: ["controllers/**", "services/**", "handlers/**", "api/**", "consumers/**"]
perspectives: [operator]
reversibility-check: false
---

# missing-log-context-on-critical-path

## Trigger

A critical code path (write operation, auth decision, external API call, async job dispatch) executes without emitting a log entry that would help diagnose failures in production. When this path fails silently or produces unexpected results, there is no observability trail to reconstruct what happened.

## Detection

Look for functions that:
- Perform DB writes, external API calls, email/SMS dispatch, or auth decisions
- Have no `logger.info`, `logger.warn`, `logger.error`, or equivalent calls
- OR have log calls that are missing key contextual fields (entity IDs, operation outcome, caller identity)

Compare against sibling functions in the same file: if most log at entry and error, a function that does not is likely an oversight.

## Retrieval

- The full function body
- Up to 2 sibling functions (to establish the logging convention baseline)

## Analysis prompt

Given the function:
1. What critical operations does it perform? (DB write, API call, notification dispatch, auth check)
2. At what points should log entries exist? (minimum: on error; recommended: on entry with key params, on success with outcome)
3. What contextual fields should each log include? (entity ID, user/tenant ID, operation name, outcome)
4. Are sibling functions in the same file logging at the same points? If yes, this function should too.

## Severity rubric

- P0: never (missing logs are not correctness bugs)
- P1: critical path (auth, payment, data mutation, external notification) with zero log entries on the error branch
- P2: non-critical path, or logs exist but are missing some contextual fields

## Confidence factors

- HIGH: function performs a write + external side effect (email, webhook) with no logger calls; sibling functions log
- MEDIUM: function performs a DB write with a warn-level log on error but no info-level log on success
- LOW: function is a simple read or the logging may be handled at a higher middleware layer

## Examples

### Positive (missing context)

```typescript
static revokeShare = asyncHandler(async (req, res) => {
  // ... validation and DB update ...
  await db.from("claims").update({ revoked_at: now }).eq("id", shareId);
  // No log entry: if this silently fails (constraint, timeout), no trace exists
  res.json({ revoked: true });
});
```

### Negative (good observability)

```typescript
static revokeShare = asyncHandler(async (req, res) => {
  const { error } = await db.from("claims").update({ revoked_at: now }).eq("id", shareId);
  if (error) {
    logger.error("Failed to revoke share", { shareId, userId: req.auth.userId, error });
    throw HttpError.fromDataBaseError(error);
  }
  logger.info("Share revoked", { shareId, userId: req.auth.userId });
  res.json({ revoked: true });
});
```
