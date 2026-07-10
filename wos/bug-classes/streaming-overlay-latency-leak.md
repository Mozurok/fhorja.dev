---
name: streaming-overlay-latency-leak
category: performance
default-severity: P1
priority: P1
pillars: [performance, observability]
cwe: [CWE-405]
languages: [typescript, javascript]
file-patterns: ["apps/web/src/server/ai/**", "apps/web/src/server/realtime/**", "packages/**/overlay/**", "packages/**/transcribe/**", "packages/**/recommend/**"]
perspectives: [operator, maintainer]
reversibility-check: false
---

# streaming-overlay-latency-leak

A realtime AI overlay pipeline (audio capture -> transcribe -> recommend -> overlay render) has at least one stage that fully blocks the next stage, so cumulative latency grows past the sub-second target the product depends on. Coaching, captions, or suggestions arrive AFTER the agent has already moved on, breaking the "real-time" contract even when each stage looks correct in isolation.

## What it looks like

- Pipeline stages are chained as sequential awaits: `const transcript = await transcribe(audio); const reco = await recommend(transcript);`. The recommend stage cannot start until the full transcript is materialized.
- The overlay renders only after the final recommend call resolves, so users see coaching seconds after the relevant moment in the call has passed.
- No stream-of-stream pattern: transcribe does not emit incremental tokens into recommend, and recommend does not emit incremental tokens into the overlay.
- Latency dashboards track average end-to-end latency only -- p95 and p99 are missing, so tail latency leaks are invisible.
- No SLO is declared for "first overlay token visible" or "overlay update freshness", so regressions go unnoticed until users complain.
- Under load, the overlay shows stale coaching tied to an earlier turn instead of degrading gracefully (hiding or marking as stale).

## Why it matters

- This is the Peach Live shape (LiveKit capture + Deepgram transcribe + Groq recommend + browser overlay). The product value is "coaching arrives while the call is happening". Any blocking stage destroys that value even if every individual call is fast.
- Sub-second perceived latency is the threshold where overlay coaching feels live vs. feels like a delayed transcript. Once cumulative latency crosses ~1s, agents stop trusting the overlay and the feature is effectively dead.
- Sequential awaits also under-utilize the LLM provider's streaming capability -- you pay for streaming inference but consume it as a single blocking call.
- Missing p95/p99 + missing SLO means the leak is an observability failure too: the team cannot tell whether a deploy made things worse until users report it.

## How to detect

Code smells:

- Search for sequential `await transcribe(...)` followed by `await recommend(...)` in the same function body, with no intermediate stream or queue.
- Look for `await response.text()` / `await response.json()` on a streaming-capable transcribe or LLM response -- this drains the stream into a single blob and discards the streaming benefit.
- Check the overlay render path: does it accept incremental tokens, or does it only render on final payload?

Telemetry smells:

- Latency histogram exists but only reports average / p50. No p95, no p99, no max.
- No declared SLO for end-to-end overlay freshness (e.g., "p95 first-token < 800ms, p99 < 1500ms").
- No alert wired to p95 > 1s.

Grep heuristic:

```
rg -n "await\\s+transcribe\\(" apps/web/src/server -A 5 \
  | rg -B 1 "await\\s+(recommend|generate|complete)\\("
```

## How to fix

- Stream tokens from transcribe directly into recommend. Do not await the full transcript -- pipe partial transcripts (or interim results) into the recommender as they arrive.
- Decouple stages via an in-process queue or async iterator so transcribe and recommend run concurrently and back-pressure is explicit.
- Stream tokens from recommend into the overlay. The overlay should render incrementally as tokens arrive, not wait for the final payload.
- Declare an explicit SLO: e.g., p95 first-overlay-token < 800ms, p99 < 1500ms. Emit a histogram metric per stage AND end-to-end.
- Wire alerts at p95 > 1s and p99 > 2s. Page on sustained breach.
- Degrade gracefully: if the recommend stage falls behind (queue depth > N or stage latency > SLO), HIDE the overlay or mark it visibly stale. Never show coaching that is tied to a turn the agent has already left.
- Add a synthetic load test that replays a recorded call and asserts the p95/p99 SLO holds end-to-end.

## CWE / standard refs

- CWE-405: Asymmetric Resource Consumption (Amplification). A blocking stage in a streaming pipeline amplifies upstream latency: every millisecond spent waiting on the full transcript is a millisecond the overlay falls behind, and the gap is unrecoverable for that turn.

## See also

- `wos/bug-classes/sync-blocking-io-on-request-path.md` (sibling class for blocking I/O in request handlers)
- `wos/bug-classes/missing-business-metric.md` (sibling observability class -- missing SLO is a special case)
- ADR on realtime pipeline shape (LiveKit + Deepgram + Groq overlay contract)
- `wos/design-system-conventions.md` (overlay rendering + stale-state UX rules)
