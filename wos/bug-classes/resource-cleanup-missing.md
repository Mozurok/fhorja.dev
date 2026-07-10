---
name: resource-cleanup-missing
category: reliability
default-severity: P1
cwe: [CWE-404, CWE-772]
languages: [typescript, javascript, python, go]
file-patterns: ["controllers/**", "services/**", "consumers/**", "handlers/**", "api/**", "lib/**"]
perspectives: [operator]
reversibility-check: false
---

# resource-cleanup-missing

## Trigger

A function acquires a resource (database connection, file handle, stream, subscription, timer, temporary file) but does not release it on all exit paths (normal return, early return, exception). Over time, leaked resources cause connection pool exhaustion, file descriptor limits, memory leaks, or dangling event listeners.

## Detection

Look for:
- `open(`, `createReadStream(`, `createConnection(`, `connect(` without a corresponding `close(`, `end(`, `destroy(`, or `finally` block
- `setInterval(`, `setTimeout(` without `clearInterval(`, `clearTimeout(` on cleanup
- `subscribe(`, `addEventListener(`, `on(` without `unsubscribe(`, `removeEventListener(`, `off(` in a cleanup path
- Database clients or pools acquired inline (`new Pool()`, `createClient()`) without `pool.end()` or `client.release()` in a `finally` block
- `try` blocks that acquire resources in the `try` body but have no `finally` for cleanup

Exclude:
- Resources managed by a framework or connection pool that handles cleanup automatically (e.g., Supabase JS client, Express request/response lifecycle)
- Event listeners on long-lived objects that are intentionally never removed (server-level listeners)

## Retrieval

- The function body where the resource is acquired
- The error handling paths (catch, finally, early returns) to verify cleanup coverage

## Analysis prompt

Given the resource acquisition:
1. What resource is acquired? (connection, file, stream, timer, subscription)
2. Is there a corresponding release call on the normal exit path?
3. Is there a release call on the error path (catch or finally)?
4. Is there a release call on early-return paths?
5. If any exit path lacks cleanup: what is the consequence? (connection leak, file lock, memory growth)
6. Recommended fix: move cleanup to a `finally` block, use `using` (TS 5.2+), or use a wrapper that auto-cleans.

## Severity rubric

- P0: leaked resource is a database connection on a request-handling path (connection pool exhaustion under load)
- P1: leaked resource is a file handle, stream, or timer (gradual degradation)
- P2: leaked resource is a subscription or listener on a short-lived object (minor memory concern)

## Confidence factors

- HIGH: `open(` or `connect(` with no `close(` or `end(` on any path; no `finally` block
- MEDIUM: resource is acquired in a `try` but cleanup is only in the `try` body (not in `finally`)
- LOW: resource may be managed by the framework; cleanup may happen automatically

## Examples

### Positive (missing cleanup)

```typescript
const file = fs.createReadStream(path);
const data = await streamToBuffer(file);
return data;
// If streamToBuffer throws, the file stream is never closed
```

### Negative (proper cleanup)

```typescript
const file = fs.createReadStream(path);
try {
  const data = await streamToBuffer(file);
  return data;
} finally {
  file.destroy();
}
```
