---
name: destructive-before-constructive
category: ordering-bug
default-severity: P1
cwe: []
languages: [typescript, javascript, python, go, sql]
file-patterns: ["controllers/**", "services/**", "handlers/**", "routes/**", "api/**"]
perspectives: [operator]
reversibility-check: true
---

# destructive-before-constructive

## Trigger

Sequential awaited operations where a destructive write (delete, revoke, update-to-inactive) precedes a constructive write (insert, create) on the same logical entity. If the constructive operation fails (transient DB error, constraint violation, network timeout), the entity is left in a degraded state with no automatic recovery path.

## Detection

Look for sequences in the same function body where:
- An update/delete that sets a "revoked", "deleted", "inactive", or "expired" state is followed (within 30 lines) by an insert or create call on the same table or a related entity
- Both operations are awaited independently (not inside a single DB transaction)
- The destructive operation is NOT guarded by a rollback on insert failure

Grep patterns (approximate):
- `.update(` followed by `.insert(` in the same function
- `DELETE FROM` or `UPDATE ... SET deleted_at` followed by `INSERT INTO` in the same function
- `.revoke` or `.softDelete` followed by `.create` or `.insert`

## Retrieval

- The full function body containing both operations
- Up to 2 sibling functions in the same file (to check if the codebase convention is to use transactions elsewhere)

## Analysis prompt

Given the function body:
1. Identify the destructive operation and the subsequent constructive operation.
2. Assess: if the constructive operation fails (DB error, constraint violation, network timeout), what state does the user or entity end up in?
3. Is there a recovery path? Can the caller safely retry without admin intervention?
4. Is reordering feasible (construct first, then destroy the old one, excluding the new one from the destroy filter)?
5. Would wrapping both in a transaction be more appropriate than reordering?

## Severity rubric

- P0: destructive operation removes the user's only access path (auth token, share link, API key) AND no self-service recovery exists
- P1: destructive operation degrades access or data, but the caller can retry (still a poor UX, data may be inconsistent during the window)
- P2: ordering issue exists but the destructive operation is soft (reversible via admin action or automatic cleanup)

## Confidence factors

- HIGH: both operations are independently awaited (no transaction wrapper); they touch the same entity or closely related entities (same table, same FK chain)
- MEDIUM: operations are on related but distinct entities (different tables linked by FK); failure leaves an inconsistent cross-table state
- LOW: speculation; the destructive operation may be idempotent or conditionally skipped

## Examples

### Positive (real bug)

```typescript
// Revoke prior tokens FIRST
await db.update("tokens", { revoked_at: now() }).eq("user_id", uid);
// Then create new token
const { data, error } = await db.insert("tokens", { user_id: uid, ... });
if (error) throw error; // Prior tokens already revoked; user has no valid token
```

If the insert fails, the user's prior tokens are already revoked and they have no access.

### Negative (safe pattern)

```typescript
// Insert new token FIRST
const { data: newToken, error } = await db.insert("tokens", { user_id: uid, ... });
if (error) throw error;
// Then revoke prior tokens, excluding the one just created
await db.update("tokens", { revoked_at: now() })
  .eq("user_id", uid)
  .neq("id", newToken.id);
```

If the insert fails, prior tokens are untouched. User retains access.
