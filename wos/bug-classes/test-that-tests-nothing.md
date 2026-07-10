---
name: test-that-tests-nothing
category: testing
default-severity: P2
cwe: []
languages: [typescript, javascript, python, go]
file-patterns: ["**/*.test.*", "**/*.spec.*", "**/tests/**", "**/__tests__/**"]
perspectives: [maintainer]
reversibility-check: false
---

# test-that-tests-nothing

## Trigger

A test case exists in the diff but does not meaningfully verify behavior: it has no assertions, its assertions are tautological (always true), it mocks the thing it should be testing, or it catches and swallows errors that should cause failure.

## Detection

Look for test cases (`it(`, `test(`, `def test_`) where:
- No `expect(`, `assert`, `should`, `assertEqual`, or equivalent assertion appears in the body
- The only assertion is tautological: `expect(true).toBe(true)`, `assert 1 == 1`
- The function under test is fully mocked (the test verifies the mock, not real behavior)
- A `try/catch` wraps the test body and the catch does not re-throw or assert on the error
- The test is marked `.skip` or `@pytest.mark.skip` with no explanation

## Retrieval

- The test file (full test case body)
- The source file being tested (to verify what behavior should be asserted)

## Analysis prompt

Given the test case:
1. How many assertions does it contain? Are any of them tautological?
2. Is the function under test actually called with real inputs, or is it fully mocked?
3. If the function under test were broken (returned wrong value, threw unexpected error), would this test fail?
4. If the answer to #3 is no: the test provides false confidence. Recommend either adding meaningful assertions or removing the test entirely.

## Severity rubric

- P0: never
- P1: test covers a security-critical or data-integrity function and provides false confidence
- P2: test covers general business logic and provides false confidence

## Confidence factors

- HIGH: test body has zero assertion calls; or the only assertion is tautological
- MEDIUM: test has assertions but they verify mock behavior, not real function output
- LOW: test has assertions but they are weak (checking only truthy/falsy, not specific values)

## Examples

### Positive (tests nothing)

```typescript
it("should create a share", async () => {
  const result = await createShare(mockReq, mockRes);
  // No expect() call; test passes regardless of what createShare returns
});
```

### Negative (meaningful test)

```typescript
it("should create a share", async () => {
  const result = await createShare(mockReq, mockRes);
  expect(result.share_id).toBeDefined();
  expect(result.share_url).toMatch(/^https:\/\//);
  expect(result.expires_at).toBeTruthy();
});
```
