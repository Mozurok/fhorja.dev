---
name: streaming-overlay-latency-leak
category: performance
default-severity: P1
cwe: [CWE-405]
languages: [typescript, javascript]
file-patterns: ["apps/web/src/server/ai/**", "apps/web/src/server/realtime/**", "packages/**/overlay/**", "packages/**/transcribe/**", "packages/**/recommend/**"]
perspectives: [operator, maintainer]
reversibility-check: false
---

# streaming-overlay-latency-leak

## Trigger

A realtime pipeline (capture, then transcribe, then recommend, then render an overlay) has at least one stage that fully blocks the next, so latency accumulates past the sub-second budget the product depends on. Coaching, captions, or suggestions arrive after the moment they described has passed, and the realtime contract breaks even though every individual stage is fast and correct.

The product value is that the output arrives while the conversation is still happening. Once cumulative latency crosses the budget, users stop trusting the overlay and the feature is effectively dead, no matter how good the content is. A second cost rides along: a pipeline that awaits complete responses pays for streaming inference and consumes it as a blocking call, so the capability is bought and discarded.

It is also an observability failure. Dashboards that report only an average hide exactly the tail this class lives in, and without a declared budget for first-token visibility there is nothing for a regression to violate. The team learns about the leak from users.

CWE-405 (Asymmetric Resource Consumption): a blocking stage amplifies upstream latency, and every millisecond spent waiting for a complete intermediate result is a millisecond the overlay falls behind, unrecoverable for that turn.

## Detection

Code shapes:

- Stages chained as sequential awaits in one function body, so the second cannot start until the first has fully materialized:
  `const transcript = await transcribe(audio); const reco = await recommend(transcript);`
- A complete-body read (`await response.text()`, `await response.json()`) on a streaming-capable response, which drains the stream into a blob and discards the incremental benefit.
- An overlay render path that accepts only a final payload rather than incremental tokens.
- No stream-into-stream anywhere: transcribe does not emit partials into recommend, and recommend does not emit partials into the overlay.
- Under load, the overlay shows content tied to an earlier turn rather than hiding or marking itself stale.

Telemetry shapes:

- A latency histogram that reports average or median and no p95, p99, or max.
- No declared budget for first-overlay-token or for overlay freshness.
- No alert wired to the tail.

```
rg -n "await\\s+transcribe\\(" apps/web/src/server -A 5 \
  | rg -B 1 "await\\s+(recommend|generate|complete)\\("
```

## Retrieval

- The whole pipeline in one read, from capture to render. Every stage in isolation looks fast, which is the property that makes this class survive stage-level review; only the composition shows the leak.
- The transport between each pair of stages: a direct await, a queue, an async iterator, an event emitter. The boundary is where the blocking lives, so the boundaries are the retrieval target.
- The response-consumption call for each network stage, specifically whether it reads incrementally or waits for a complete body. A streaming-capable client used with a blocking read is invisible in the client's own configuration.
- The overlay render path down to the component that draws, to establish whether it can render a partial at all. A fully streaming backend into a final-payload renderer leaks at the last hop.
- The metric definitions and any recorded budget, not the dashboard. Which percentiles are computed is a property of the instrumentation, and the dashboard only shows what someone chose to display.
- The cancellation and staleness path: what happens to in-flight work when a new turn starts. Its absence is the graceful-degradation half of this class.

## Analysis prompt

Given the retrieved pipeline, its stage boundaries, and its instrumentation:

1. Draw the stage graph and report, for each boundary, whether the downstream stage begins before the upstream one completes. Name each boundary that blocks. This is the finding; everything below characterizes it.
2. For each network stage, report how the response is consumed: incrementally or as a complete body. A complete-body read on a streaming-capable response is a blocking boundary even when the code around it looks asynchronous.
3. Report whether the renderer can draw a partial result. Trace it to the component that draws, not to the handler that receives.
4. Report which percentiles the instrumentation actually computes, per stage and end to end. Distinguish what is computed from what is displayed, and report the absence of p95 and p99 as its own finding rather than as part of the latency one.
5. Report whether a latency budget is declared anywhere in the repository, with its numbers. If none exists, say so plainly: without it there is no threshold a regression can cross, and every later step here is descriptive rather than actionable.
6. Report what happens when a stage falls behind: does the overlay hide, mark itself stale, or keep showing content from a turn that has ended? Showing stale content as current is a correctness finding, not only a latency one.
7. Report whether in-flight work is cancelled when a new turn starts. Uncancelled work competes with the turn that replaced it, which makes the leak worse under exactly the load that caused it.
8. Recommend, in order: stream partial results from each stage into the next rather than awaiting completion, decoupling stages with a queue or an async iterator so back pressure is explicit; render incrementally at the overlay; declare an explicit budget for first-token and for freshness, and emit a histogram per stage and end to end; alert on the tail rather than the average; degrade visibly by hiding or marking stale when a stage exceeds its budget, never by showing content tied to a turn the user has left; and add a replay-based load test that asserts the budget end to end so the next regression is caught before a user reports it.

## Severity rubric

- **P1**: a blocking boundary in a pipeline whose product promise is realtime delivery. Justification: the feature's value is time-bound, so latency past the budget is a functional failure rather than a slow success, and it is invisible to stage-level testing. It is not P0 because nothing is lost or corrupted and the pipeline recovers on the next turn; the damage is user trust, which erodes rather than breaks.
- **P1 also**: stale content displayed as current when a stage falls behind. The user acts on information about a moment that has passed, which is worse than an empty overlay.
- **P2**: a fully streaming pipeline instrumented with averages only, and no declared budget. Correct today, and a regression would reach users before it reached a dashboard.

## Confidence factors

- **HIGH**: two stages chained as sequential awaits in one function body, with a streaming-capable client on the upstream stage. The blocking boundary and the discarded capability are both on the page.
- **MEDIUM**: a streaming backend feeding a renderer whose props take a final payload. The leak is at the last hop and depends on how the component is fed at runtime.
- **LOW**: an average-only dashboard where the underlying metric may still record the full distribution, so the gap could be in the display rather than the instrumentation.

## Examples

### Positive (each stage waits for the whole of the previous one)

```ts
const audio = await captureTurn(session);              // waits for silence
const transcript = await transcribe(audio);            // waits for the full transcript
const reco = await recommend(transcript);              // waits for the full completion
overlay.render(reco);                                  // draws once, at the end
```

Four sequential waits, each correct and each fast on its own. The overlay appears after the turn it describes has finished, and the dashboard shows a healthy average because the average is dominated by the short turns.

### Negative (streamed through, budgeted, cancelled)

```ts
const turn = newTurn(session);                          // cancels the previous turn's work
for await (const partial of transcribe(turn.audio)) {   // partials, not a final transcript
  for await (const token of recommend(partial, { signal: turn.signal })) {
    overlay.append(token);                              // draws incrementally
    metrics.observe("overlay.first_token_ms", turn.sinceStart(), { stage: "e2e" });
  }
}
if (turn.behindBudget()) overlay.markStale();           // never shows a past turn as current
```

Nothing waits for a complete intermediate result, the previous turn's work is cancelled rather than left to compete, the metric is observed per turn so the tail is computable, and falling behind produces a visible stale marker instead of confident wrong content.
