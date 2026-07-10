---
name: order-dependent-test-pollution-via-shared-async-state
category: testing
priority: P1
pillars: [correctness, testing]
default-severity: P1
cwe: [CWE-362, CWE-668]
languages: [typescript, javascript]
file-patterns: ["**/*.test.ts", "**/*.test.tsx", "**/*.spec.ts", "**/*.spec.tsx", "**/__tests__/**", "**/jest.setup.*", "**/test/setup.*"]
perspectives: [maintainer]
reversibility-check: false
---

# order-dependent-test-pollution-via-shared-async-state

## What it looks like

A test passes when run in isolation (`-t "name"` or a single-file run) but fails when the whole suite runs, or fails only in a particular file order. The cause is state that leaks across test boundaries through an async or module-level surface that the test teardown does not reset:

- A shared client or store created once at module scope (a `QueryClient`, a Zustand or Redux store, an Apollo client, a singleton service) carries cached data, in-flight promises, or retry timers from one test into the next.
- A retry or refetch path (TanStack Query retries, a polling effect, a debounced callback) schedules a timer that fires after the test that started it has finished, mutating state during an unrelated test.
- An effect or subscription is not unmounted, so a pending `setState` resolves after teardown and bleeds into the next render.

A representative shape (the failure class observed in a React Native + TanStack Query timeline view):

```text
✓ renders the day timeline                     (passes alone)
✗ hides the current-time indicator on other days
  -> passes in isolation, fails in full-suite order
  -> "An update to X was not wrapped in act(...)" warnings
  -> a retry timer from the error-state test fired during this test
```

The tell is the gap between isolated and full-suite results, often accompanied by `act(...)` warnings or "can't perform a React state update on an unmounted component".

## Why it matters

Order-dependent pollution makes the suite non-deterministic: the same commit passes or fails depending on shard order, parallelism, or which tests were filtered. That destroys the test suite's value as a regression signal and burns disproportionate debugging time, because the failing test is rarely the test at fault. In a fleet or CI context the cost compounds: a worker can spend many full-suite reruns bisecting a failure that has nothing to do with the slice it is implementing (the exact spiral that produced a 73-minute silent fleet run in the 2026-06-12 session). The correctness pillar is hit because a real regression can hide behind, or be masked by, the noise; the testing pillar is hit because the suite no longer means what a green run claims.

## How to detect

Reproduce the order dependency deterministically:

```bash
# 1. Does it pass alone but fail in the suite?
npx jest path/to/file.test.tsx -t "the failing test"   # likely green
npx jest                                                # likely red

# 2. Force order variation to expose cross-test leakage
npx jest --runInBand --testSequencer ./reverseSequencer.js
npx jest --seed=12345 --randomize    # framework-dependent flag
```

Grep for the shared-state smells:

```bash
# module-scope clients/stores created once and reused across tests
grep -rnE 'new QueryClient\(|configureStore\(|create\(\(set' --include='*.ts*' src | grep -v beforeEach
# retry/poll paths that schedule timers without fake timers in tests
grep -rnE 'retry:\s*[1-9]|setInterval|setTimeout' --include='*.ts*' src
```

Review-side: a `QueryClient` or store instantiated at the top of a test file (not inside `beforeEach`), tests that share a `render` result, retry-enabled queries tested without `jest.useFakeTimers()`, and missing `cleanup`/`unmount` before assertions on teardown.

## How to fix

1. **Fresh state per test.** Construct the client or store inside `beforeEach` (or per `render`), never once at module scope. For TanStack Query, a new `QueryClient` per test with `defaultOptions: { queries: { retry: false } }` removes both the shared cache and the retry timers in one move.
2. **Disable or control time-based paths in tests.** Set `retry: false` for query tests; for code that must exercise retries or polling, use `jest.useFakeTimers()` and advance time explicitly, then restore real timers in teardown.
3. **Drain pending async before unmount.** Await the library's idle signal (for TanStack Query, await pending queries to settle) and unmount the tree before the test ends, so no `setState` resolves after teardown. With React Native Testing Library 14, `render(...)` is async: always `await render(...)` and `await` any interaction that triggers state.
4. **Reset global mocks and modules between tests.** `afterEach(() => { jest.clearAllTimers(); jest.clearAllMocks(); })` and, when a module holds singleton state, `jest.resetModules()` so the singleton is rebuilt.
5. **Make order-independence a gate, not a hope.** Run the suite in a randomized or reversed order in CI so cross-test leakage fails fast instead of hiding until a shard reorders.

When a worker hits this class mid-implementation, it should bound the debugging (stop after a few attempts, return the failing test, the reproduction command, and the hypothesis) rather than rerun the full suite indefinitely; see the worker stop-loss rule in `commands/_shared/worker-contract.md`.

## CWE / standard refs

- CWE-362: Concurrent Execution using Shared Resource with Improper Synchronization. Async work scheduled by one test mutates shared state during another.
- CWE-668: Exposure of Resource to Wrong Sphere. State scoped to one test (a client, store, or timer) leaks into the sphere of the next through module-level retention.

## See also

- bug-class: unsafe-parallel-slice-execution (sibling failure where a fleet run looks green but is broken; both are "the run looks green but is not").
- `commands/_shared/worker-contract.md`: the worker stop-loss and suite-cost-aware validation rule that bounds the debugging spiral this class triggers.
- `commands/implement-fleet.md`: per-wave integration gate; a flaky order-dependent suite makes the gate non-deterministic, so this class is a fleet hazard.
