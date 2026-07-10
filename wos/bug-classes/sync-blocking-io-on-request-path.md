---
name: sync-blocking-io-on-request-path
category: performance
default-severity: P1
cwe: [CWE-400]
languages: [typescript, javascript]
file-patterns: ["controllers/**", "handlers/**", "api/**", "routes/**", "middleware/**"]
perspectives: [operator]
reversibility-check: false
---

# sync-blocking-io-on-request-path

## Trigger

A synchronous I/O call (file read, crypto operation, DNS lookup) runs on the request-handling path, blocking the Node.js event loop. While the sync call executes, no other requests can be processed, causing latency spikes proportional to the I/O duration. Under load, this serializes all requests through a single-threaded bottleneck.

## Detection

Look for sync variants of I/O APIs on request paths:
- `fs.readFileSync`, `fs.writeFileSync`, `fs.existsSync` (use async variants)
- `crypto.pbkdf2Sync`, `crypto.scryptSync` (use async variants or worker threads)
- `child_process.execSync`, `child_process.spawnSync`
- `require()` at runtime (not at module top level)
- Any `*Sync` method from Node.js core modules inside a request handler

Exclude:
- Sync calls at module initialization (top-level `require`, one-time config read)
- Sync calls in CLI scripts or build tools (not request handlers)

## Retrieval

- The request handler or middleware containing the sync call
- The call site context (to verify it is on the request path, not initialization)

## Analysis prompt

Given the sync call:
1. Is it on the request-handling path (inside a route handler, middleware, or controller)?
2. How long does the operation typically take? (File read: 1-50ms; pbkdf2: 50-500ms; exec: variable)
3. At what concurrency does this become a problem? (10 concurrent requests each blocked 100ms = 1s total serialized delay)
4. Recommended fix: replace with async variant (`fs.promises.readFile`, `crypto.pbkdf2`, `child_process.exec`)

## Severity rubric

- P0: `crypto.pbkdf2Sync` or `child_process.execSync` on a public endpoint (100ms+ block per request)
- P1: `fs.readFileSync` on a request path (1-50ms block; noticeable at high concurrency)
- P2: sync call on a low-traffic internal endpoint where concurrency is bounded

## Confidence factors

- HIGH: `*Sync` method inside an `asyncHandler` or Express route handler; high-traffic endpoint
- MEDIUM: `*Sync` method in middleware that runs on every request
- LOW: `*Sync` method in a controller but the endpoint is internal/low-traffic

## Examples

### Positive (blocking)

```typescript
static getConfig = asyncHandler(async (req, res) => {
  const template = fs.readFileSync("templates/email.html", "utf-8"); // blocks event loop
  res.json({ template });
});
```

### Negative (non-blocking)

```typescript
static getConfig = asyncHandler(async (req, res) => {
  const template = await fs.promises.readFile("templates/email.html", "utf-8");
  res.json({ template });
});
```
