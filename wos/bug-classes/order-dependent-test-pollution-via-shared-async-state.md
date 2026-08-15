---
name: order-dependent-test-pollution-via-shared-async-state
category: testing
default-severity: P1
cwe: [CWE-362, CWE-668]
languages: [typescript, javascript]
file-patterns: ["**/*.test.ts", "**/*.test.tsx", "**/*.spec.ts", "**/*.spec.tsx", "**/__tests__/**", "**/jest.setup.*", "**/test/setup.*"]
perspectives: [maintainer]
reversibility-check: false
---

# order-dependent-test-pollution-via-shared-async-state

## Trigger

A test passes alone and fails in the full suite, or fails only in a particular file order, because state leaks across test boundaries through an async or module-level surface that teardown never resets. A client or store built once at module scope carries a cache, an in-flight promise, or a retry timer into the next test; a timer scheduled by one test fires during another; an unmounted effect resolves after the test that started it has ended.

The cost is not the failing test, it is what the suite stops meaning. The same commit passes or fails depending on shard order, parallelism, or which tests were filtered, so a green run no longer certifies anything and a red one rarely points at the code that broke. Debugging time goes disproportionate because the failing test is almost never the test at fault. In a fleet or CI context it compounds: a worker can burn many full-suite reruns bisecting a failure that has nothing to do with the slice it was implementing.

CWE-362 (Concurrent Execution using Shared Resource with Improper Synchronization): async work scheduled by one test mutates shared state during another. CWE-668 (Exposure of Resource to Wrong Sphere): state scoped to one test leaks into the next through module-level retention.

## Detection

Three leak surfaces, and they need different fixes:

1. **Module-scope singletons.** A query client, a store, an API client, or a service instantiated once at the top of a test file or an imported module. Every test in the file shares its cache and its pending work.
2. **Timers that outlive their test.** A retry policy, a poll, or a debounce schedules work that fires after the test that started it completed. Retry-enabled queries tested without controlled time are the common instance.
3. **Effects and subscriptions that are never torn down.** A pending state update resolves after teardown and lands in the next render.

The tell is the gap between isolated and full-suite results, usually accompanied by warnings about updates outside the test-rendering wrapper or about updating an unmounted component. A representative shape:

```text
- renders the day timeline                     (passes alone)
x hides the current-time indicator on other days
  -> passes in isolation, fails in full-suite order
  -> "an update was not wrapped in act(...)" warnings
  -> a retry timer from the error-state test fired during this test
```

Reproduce the order dependency rather than inferring it:

```bash
# 1. Does it pass alone but fail in the suite?
npx jest path/to/file.test.tsx -t "the failing test"   # likely green
npx jest                                                # likely red

# 2. Force order variation to expose cross-test leakage
npx jest --runInBand --testSequencer ./reverseSequencer.js
npx jest --seed=12345 --randomize    # framework-dependent flag
```

Static greps for the two leak surfaces, which find the mechanism before a reorder finds it for you:

```bash
# module-scope clients/stores created once and reused across tests
grep -rnE 'new QueryClient\(|configureStore\(|create\(\(set' --include='*.ts*' src | grep -v beforeEach
# retry/poll paths that schedule timers without fake timers in tests
grep -rnE 'retry:\s*[1-9]|setInterval|setTimeout' --include='*.ts*' src
```

## Retrieval

- The failing test AND the tests that run before it in the failing order. The fault is upstream by definition, so retrieving only the failing test retrieves the symptom and none of the cause.
- The test file's module scope and every setup file the runner loads, read as a unit. A singleton in a shared setup file pollutes files that never mention it.
- The runner configuration: sequencer, parallelism, shard count, and any global setup or teardown. The order is part of the reproduction, and it lives here.
- The teardown blocks for every test in the file, plus what they do not reset. This class is defined by omission, so enumerate what is reset and derive the rest.
- The production module the tests exercise, specifically any retry, poll, debounce, or subscription it starts. The timer that fires late is created by the code under test, not by the test.
- Both runs of the suite, isolated and full, as actual output rather than as a claim. The gap between them is the evidence.

## Analysis prompt

Given the failing test, the tests preceding it in the failing order, the setup files, and the runner configuration:

1. Reproduce both runs and report the two results: the isolated run and the full-suite run, with the commands used. If the isolated run also fails, this class does not apply and the finding is an ordinary failure; say so and stop.
2. Enumerate every object created at module scope in the test file and in every loaded setup file. For each, report whether it is rebuilt per test. Name the ones that are not.
3. Identify every timer-scheduling path the tests can reach: retry policies, polls, debounces, intervals. For each, report whether the test controls time or lets it run real.
4. List what the teardown resets, then list what it does not: timers, mocks, modules, mounted trees, subscriptions. The second list is the finding.
5. Trace which preceding test creates the state that reaches the failure. Name the test and the mechanism. A finding that names pollution without naming its source is not actionable, because the fix is in the source.
6. Report whether the suite runs in a varied order anywhere in CI. If every run uses one fixed order, this class is not merely present, it is undetectable by the current pipeline, which is a separate finding worth stating.
7. Recommend, in order: build clients and stores inside per-test setup rather than at module scope; disable retry in tests that do not exercise it, and control time explicitly in the tests that do; drain pending async and unmount the tree before the test ends so nothing resolves after teardown; clear timers, mocks, and cached modules in teardown, resetting modules where a singleton holds state; and make order-independence a gate by running the suite in a randomized or reversed order in CI, so the next leak fails immediately instead of waiting for a shard to reorder. When this class is hit mid-implementation, bound the debugging: return the failing test, the reproduction commands, and the hypothesis rather than rerunning the full suite indefinitely.

## Severity rubric

- **P1**: a reproducible order dependency in a suite that gates merges. Justification: the gate is non-deterministic, so it can pass a real regression and fail a correct change, and every consumer downstream of the gate inherits that. It sits below P0 because no production behavior is wrong and no data is at risk; the damage is to the signal, and to the time spent chasing it.
- **P1 also**: a suite that has never run in a varied order, where leakage would be invisible rather than absent. The pipeline cannot distinguish a clean suite from a lucky one.
- **P2**: module-scope shared state with no observed order dependency yet. The mechanism is present and the consequence is not, which is the state right before the next test is added.

## Confidence factors

- **HIGH**: the same test passes alone and fails in the suite, with both runs captured. Two observations, one comparison.
- **MEDIUM**: a module-scope client with retry enabled and no time control in tests, where the suite currently passes. The mechanism is established; the failure is latent.
- **LOW**: an update-after-unmount warning in a suite that passes, since that warning has other causes and does not by itself establish cross-test leakage.

## Examples

### Positive (one client for the file, retries live)

```ts
// top of the test file, outside every hook
const queryClient = new QueryClient();          // one cache for all tests
// retry left at its default, so failures schedule timers

it("shows the error state", async () => { /* triggers a retry timer */ });
it("hides the indicator on other days", async () => { /* the timer fires here */ });
```

The first test leaves a retry pending. It fires during the second, mutates the shared cache, and the second test fails with an assertion about state it never set. Run the second alone and it passes, which is what sends the next reader looking at the wrong file.

### Negative (fresh per test, time controlled, drained)

```ts
let queryClient: QueryClient;

beforeEach(() => {
  jest.useFakeTimers();
  queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
});

afterEach(async () => {
  await queryClient.cancelQueries();
  cleanup();                       // unmount before the test ends
  jest.clearAllTimers();
  jest.clearAllMocks();
  jest.useRealTimers();
});
```

The cache cannot cross a test boundary because it does not survive one, retries are off where they are not the subject, pending work is cancelled and the tree unmounted before teardown, and CI runs this suite in a reversed order so the next leak surfaces on the commit that introduces it.
