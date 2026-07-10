---
name: unhandled-async-error
category: resilience
default-severity: P1
cwe: [CWE-755]
languages: [typescript, javascript]
file-patterns: ["controllers/**", "services/**", "consumers/**", "handlers/**", "api/**"]
perspectives: [operator]
reversibility-check: false
---

# unhandled-async-error

## Trigger

An async function or Promise is invoked without a `.catch()` handler or surrounding `try/catch`, and the calling context does not propagate the rejection to an error-handling middleware. An unhandled rejection can crash the Node.js process (with `--unhandled-rejections=throw`, the default since Node 15), silently swallow errors, or leave the caller in an inconsistent state.

## Detection

Look for:
- `someAsyncFunction()` without `await` in front (fire-and-forget Promise with no `.catch()`)
- `promise.then(onSuccess)` without a second argument or `.catch()` chain
- `async () => { ... }` passed to an event handler or callback without try/catch inside
- `Promise.all([...])` where individual promises are not caught (one rejection rejects all)

Exclude:
- Express route handlers wrapped in `asyncHandler` (error is caught by the wrapper)
- Promises inside `try/catch` blocks
- `.catch()` that logs and re-throws (handled, just not gracefully)

## Retrieval

- The function body containing the async call
- The caller (to check if the caller awaits and handles the rejection)
- The error-handling middleware (to check if Express catches unhandled rejections)

## Analysis prompt

Given the async call:
1. Is the Promise awaited? If not: is there a `.catch()` handler?
2. If fire-and-forget: is this intentional? (Some background tasks are legitimately fire-and-forget with their own error handling.)
3. If a rejection reaches the top of the call stack unhandled: what happens? (process crash, silent swallow, client hang)
4. Recommended fix: either `await` with try/catch, or `.catch(err => logger.error(...))` for fire-and-forget.

## Severity rubric

- P0: unhandled rejection on the request path that crashes the process or hangs the response
- P1: unhandled rejection in a background task that silently swallows an error
- P2: fire-and-forget that is intentional but undocumented

## Confidence factors

- HIGH: `asyncFunction()` without `await` and without `.catch()` in a request handler
- MEDIUM: `Promise.all([...])` where some inner promises may reject independently
- LOW: fire-and-forget call to a function that has its own internal error handling

## Examples

### Positive (unhandled)

```typescript
publishEvent({ streamName: "email.outbound", key: emailRow.id, ... });
// No await, no .catch() - if Redis is down, rejection is unhandled
```

### Negative (handled)

```typescript
await publishEvent({ streamName: "email.outbound", key: emailRow.id, ... });
// Awaited inside a try/catch block in the caller
```
