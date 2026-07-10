---
name: flaky-test-signal
category: testing
default-severity: P2
cwe: []
languages: [typescript, javascript, python]
file-patterns: ["**/*.test.*", "**/*.spec.*", "**/tests/**", "**/__tests__/**"]
perspectives: [maintainer]
reversibility-check: false
---

# flaky-test-signal

## Trigger

A test contains patterns that make it likely to pass sometimes and fail others: dependency on wall-clock time, sleep/delay-based synchronization, reliance on insertion order from unordered collections, reading from shared mutable state, or network calls to real external services without mocking.

## Detection

Look for:
- `Date.now()`, `new Date()`, `time.time()` in assertions without freezing time
- `setTimeout`, `sleep`, `time.sleep` used for synchronization instead of event-driven waits
- `toEqual([...])` on results from `Set`, `Map.values()`, or unordered DB queries without `ORDER BY`
- `fetch(`, `axios.get(` to real external URLs (not mocked) in test code
- Assertions on auto-generated IDs (UUIDs, timestamps) without regex/range matching

## Retrieval

- The test file containing the suspect pattern
- The test configuration (to check if time mocking or network stubbing is available)

## Analysis prompt

Given the test:
1. Does it depend on wall-clock time? (Use `vi.useFakeTimers()` or `freezegun` instead.)
2. Does it use sleep/delay for synchronization? (Use event-based waits or polling with timeout.)
3. Does it assert on unordered collections? (Sort before comparing, or use `toContain`/set equality.)
4. Does it make real network calls? (Mock the HTTP layer or use a test server.)

## Severity rubric

- P1: flaky test on CI that causes spurious failures blocking merges
- P2: flaky test in local dev that occasionally fails but does not block CI

## Confidence factors

- HIGH: `Date.now()` in an assertion without time mocking; real HTTP call in test body
- MEDIUM: `setTimeout` used for sync; may work reliably on fast machines but fail on slow CI
- LOW: assertion on unordered data that happens to be consistently ordered in practice

## Examples

### Positive (flaky)

```typescript
it("should expire after 1 hour", async () => {
  const share = await createShare({ ttl_hours: 1 });
  await sleep(3600_000); // waits 1 real hour (!)
  expect(share.isExpired()).toBe(true);
});
```

### Negative (stable)

```typescript
it("should expire after 1 hour", () => {
  vi.useFakeTimers();
  const share = createShare({ ttl_hours: 1 });
  vi.advanceTimersByTime(3600_000);
  expect(share.isExpired()).toBe(true);
  vi.useRealTimers();
});
```
