---
name: over-mocked-test
category: testing
default-severity: P2
cwe: []
languages: [typescript, javascript, python]
file-patterns: ["**/*.test.*", "**/*.spec.*", "**/tests/**", "**/__tests__/**"]
perspectives: [maintainer]
reversibility-check: false
---

# over-mocked-test

## Trigger

A test mocks so many dependencies that it effectively tests the mock wiring rather than the real behavior. The function under test is surrounded by mocks for its DB client, HTTP client, logger, and config; the test verifies that the mocks were called with the right arguments, but never exercises the real logic, error handling, or edge cases of the function itself.

## Detection

Look for test files where:
- More than 3 `vi.mock(...)` / `jest.mock(...)` / `unittest.mock.patch(...)` calls exist for a single test
- The test assertions are exclusively `expect(mockFn).toHaveBeenCalledWith(...)` with no assertions on the function's return value or side effects
- The function under test is essentially a thin orchestrator and the test verifies orchestration order, not behavior

## Retrieval

- The test file (full test case)
- The source function being tested (to assess how much real logic exists)

## Analysis prompt

Given the test and its mocks:
1. How many dependencies are mocked? List them.
2. What does the test actually assert? (mock call arguments? return value? error thrown? state change?)
3. If the real function's logic had a bug (wrong calculation, missing validation), would this test catch it?
4. If the answer to #3 is no: recommend either (a) reducing mocks and testing with real deps where feasible, or (b) adding assertions on the function's output, not just mock interactions.

## Severity rubric

- P1: test covers a security-critical or data-integrity function and provides false confidence
- P2: test covers general business logic with excessive mocking

## Confidence factors

- HIGH: 4+ mocks for a single test; assertions are exclusively `toHaveBeenCalledWith`
- MEDIUM: 2-3 mocks; mix of mock assertions and return-value assertions
- LOW: mocks are for I/O boundaries only (DB, HTTP) and the function has minimal logic

## Examples

### Positive (over-mocked)

```typescript
vi.mock("@/lib/supabase");
vi.mock("@/lib/redis");
vi.mock("@/lib/logger");
vi.mock("@/lib/share-token");

it("creates share", async () => {
  mockSupabase.from.mockReturnValue({ insert: vi.fn().mockResolvedValue({ data: { id: "1" } }) });
  await createShare(mockReq, mockRes);
  expect(mockSupabase.from).toHaveBeenCalledWith("verification_run_claims");
  // Tests that supabase was called, not that the share logic is correct
});
```

### Negative (meaningful despite mocks)

```typescript
vi.mock("@/lib/supabase"); // mock DB only

it("rejects non-COMPLETED runs", async () => {
  mockSupabase.from.mockReturnValue({ select: vi.fn().mockResolvedValue({ data: { status: "IN_PROGRESS" } }) });
  await expect(createShare(mockReq, mockRes)).rejects.toThrow("Only COMPLETED");
  // Tests real validation logic, not just mock wiring
});
```
