---
name: missing-timeout-config
category: resilience
default-severity: P1
cwe: [CWE-400]
languages: [typescript, javascript, python, go]
file-patterns: ["controllers/**", "services/**", "consumers/**", "lib/**", "api/**"]
perspectives: [operator]
reversibility-check: false
---

# missing-timeout-config

## Trigger

An HTTP request to an external service or a database query is made without an explicit timeout. If the remote service hangs or is slow, the calling process blocks indefinitely, tying up a connection, a worker thread, or an event-loop slot. Under load, this cascades into connection pool exhaustion or request queue saturation.

## Detection

Look for:
- `fetch(url)` without `signal: AbortSignal.timeout(ms)` or a wrapper timeout
- `axios.get/post(url)` without `{ timeout: ms }` in config
- `new HttpClient({ ... })` without `timeout` in constructor options
- Database queries without statement timeout or connection timeout
- `await externalSdk.call(...)` without SDK-level timeout configuration

## Retrieval

- The function body containing the call
- The HTTP client or SDK initialization (to check if a default timeout is set)

## Analysis prompt

Given the call:
1. Is there an explicit timeout at the call level or at the client/SDK initialization level?
2. If no timeout: what is the default behavior? (fetch: no timeout; axios: no timeout; node-postgres: no timeout)
3. What is a reasonable timeout for this call? (API calls: 5-30s; file uploads: 60-120s; health checks: 3-5s)
4. What happens if the call hangs for 5 minutes without timeout? (blocked worker, connection leak, user-visible hang)

## Severity rubric

- P0: no timeout on a request-handling path (user request blocks indefinitely)
- P1: no timeout on a background job or consumer (worker hangs, queue backs up)
- P2: no timeout but the call is to a highly reliable internal service with sub-second SLA

## Confidence factors

- HIGH: `fetch(url)` with no timeout and no AbortController; on a request-handling path
- MEDIUM: SDK call without explicit timeout; SDK may have a built-in default
- LOW: internal service call where network is reliable and latency is bounded

## Examples

### Positive (no timeout)

```typescript
const response = await fetch("https://api.carrier-details.com/vin/" + vin);
// If the API hangs, this request blocks forever
```

### Negative (with timeout)

```typescript
const controller = new AbortController();
setTimeout(() => controller.abort(), 15000);
const response = await fetch("https://api.carrier-details.com/vin/" + vin, {
  signal: controller.signal,
});
```
