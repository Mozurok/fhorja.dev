---
activation: model_decision
description: Patterns for realtime AI overlays (audio capture + transcribe + LLM recommend + UI overlay). Load when designing or auditing a Peach-Live-style realtime coaching layer.
---

# Realtime Overlay Patterns

Operational patterns for building sub-second AI coaching overlays that ingest live audio, transcribe it, run an LLM recommendation, and render guidance into a UI overlay while the user is still talking. Grounded in the Peach-Live shape: a sales/support agent gets next-best-action prompts while on a live call.

## When this applies (sub-second coaching overlay; audio-driven AI)

Use these patterns when the system has all of the following properties:

- Continuous audio input (microphone, WebRTC, telephony bridge) rather than file upload.
- An overlay UI that surfaces AI guidance while the audio source is still active, not after the call ends.
- A user-perceptible latency budget under ~1.5s from spoken phrase to rendered suggestion.
- Multiple cooperating services on the request path (capture, transcribe, LLM, UI) where any single stall stalls the entire surface.

Do NOT use these patterns for batch post-call summarization, async coaching emails, or any flow where the user reads the AI output minutes after the audio. Those are batch shapes and live in a different design family.

## Canonical pipeline (Capture LiveKit -> Transcribe Deepgram -> Recommend Groq -> Overlay)

Reference shape, vendor names are illustrative:

1. **Capture** -- LiveKit (or equivalent WebRTC SFU) ingests the agent's mic and the customer's stream, exposes both as server-side audio tracks.
2. **Transcribe** -- Deepgram (or equivalent realtime STT) consumes the audio stream over a persistent socket, emits interim and final transcript tokens.
3. **Recommend** -- Groq (or any low-latency LLM endpoint) consumes streaming transcript tokens, emits streaming recommendation tokens.
4. **Overlay** -- the agent's browser subscribes to the recommendation stream and renders tokens into a non-blocking overlay component.

Every hop is a stream. The pipeline never materializes a full transcript or a full recommendation in memory before passing it forward.

## Pattern 1: stream-of-stream (don't await full transcript; stream tokens to recommend)

Do not await the STT "final" event before invoking the LLM. Treat the transcript itself as a token stream and pipe interim tokens into the recommend stage with a debounce window (e.g. 200-400ms of silence, or a punctuation boundary).

Why:
- Waiting for "final" adds 800ms-1500ms because most STT engines only finalize on long pauses.
- The LLM can produce useful partial guidance from a partial phrase ("the customer just said they're worried about pricing...").
- Tokens-in, tokens-out keeps the overlay perceptually live.

Implementation hint: keep a rolling window (last N seconds of transcript) as the LLM prompt context, not the full call transcript. Re-fire the LLM on each meaningful interim, cancel the previous in-flight LLM call if it has not yet emitted.

## Pattern 2: decouple via queue (audio source + transcript sink + recommend sink)

Put a bounded in-memory queue (or Redis stream) between each stage. The capture stage writes audio frames into a queue; the transcribe worker reads from it. The transcribe worker writes transcript tokens into a second queue; the recommend worker reads from it.

Why decouple:
- A slow LLM should not exert backpressure on the audio capture path; dropping LLM calls is fine, dropping audio frames is not.
- Each stage can be scaled, retried, or replaced independently.
- Failure of one stage degrades the overlay without killing the call.

Bound every queue. An unbounded queue under load turns into a memory leak and a tail-latency disaster.

## Pattern 3: SLO + graceful degradation (hide overlay rather than stale)

Define an explicit per-stage SLO (e.g. transcribe p95 < 400ms, recommend p95 < 700ms, end-to-end p95 < 1.5s). When the SLO is breached:

- Hide the overlay or render a neutral "listening..." state.
- Do NOT render a stale recommendation from 8 seconds ago; it is worse than no recommendation because the user trusts it and acts on it.
- Emit a structured telemetry event so the breach is visible in dashboards, not silently swallowed.

Stale guidance in a live conversation is a correctness bug, not a UX nit. Treat it like serving stale data from a cache: prefer empty over wrong.

## Pattern 4: per-tenant model/cost caps

Each tenant gets a per-minute token cap and a per-minute LLM-call cap. Enforce at the recommend-stage gateway, not at the UI. Reasons:

- A single noisy tenant should never starve the shared LLM quota.
- Per-tenant caps let pricing tiers be real (free vs paid maps to different caps).
- Caps make incident response cheap: throttle the offender, do not page on global LLM bill spikes.

Pair caps with a per-tenant model selector so cheaper tiers can be routed to a smaller/faster model without code changes.

## Related bug-classes

- `streaming-overlay-latency-leak` -- end-to-end p95 silently drifts upward as transcript windows grow; mitigation is rolling-window context, not full-call context.
- `sync-blocking-io-on-request-path` -- any synchronous DB write or remote call inside the recommend stream collapses the latency budget; push side effects to a background queue.
- `rate-limit-no-backoff` -- the recommend stage hits the LLM rate limit, retries without jitter, and amplifies the spike; always implement exponential backoff with jitter at the gateway.

## References

- Anthropic streaming API -- Messages API with `stream: true`, server-sent events with `content_block_delta` for token-by-token output.
- OpenAI streaming API -- Chat Completions with `stream: true`, deltas surfaced via SSE; same shape for the Responses API.
- Deepgram realtime docs -- websocket streaming STT, interim vs final results, endpointing/utterance-end events for boundary detection.
