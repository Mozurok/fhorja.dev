---
activation: model_decision
description: Named architecture trade-off pairs (scaling direction, consistency, sync vs async, and more) as a shared vocabulary for decision capture. Load when a task weighs one architectural decision and impact-analysis or a design command needs named dimensions to cite.
---

# wos/architecture-tradeoffs.md

Lazy reference for the recurring architecture trade-off pairs, one line each, as a shared vocabulary. Load this when a task weighs an architectural decision and you want to name the axis rather than reinvent it. This is a vocabulary to cite, not a decision engine: `impact-analysis`'s "Viable implementation directions" table, `api-contract-review`, `backend-system-design`, and `release-plan` can point here for the named dimension, and the actual per-task decision plus its rationale still lives in DECISIONS.md and any ADR.

The framing is deliberate. Each pair is a real axis a solo or small-team builder decides, not a distributed-systems exam topic. Pick the side that fits the task's actual scale and constraints, and record why in DECISIONS.md. "Everything is a trade-off" is only useful if the trade is named.

## The pairs

- Vertical vs horizontal scaling: a bigger box vs more boxes. Vertical is simpler and usually right first for small teams; horizontal buys headroom at the cost of statelessness and coordination.
- Strong vs eventual consistency: read-your-writes correctness vs availability and latency under partition. Default to strong within a single datastore; reach for eventual only where a real distributed need forces it.
- Stateful vs stateless services: in-process state (sticky, simpler locally) vs externalized state (scales and redeploys cleanly). Stateless plus an external store is the safer default for anything that will run more than one instance.
- Synchronous vs asynchronous communication: call-and-wait simplicity vs decoupled throughput and resilience. Start synchronous; add a queue when a slow or failure-prone step should not block the caller.
- Push vs pull: the source notifies (webhooks, subscriptions) vs the consumer polls. Prefer push when the vendor offers it and latency matters; pull when you need control over cadence or the source cannot push.
- Batch vs stream processing: periodic bulk jobs vs per-event handling. Batch is cheaper and simpler; stream only when freshness genuinely matters.
- Read-through vs write-through cache: populate on read-miss vs write to cache and store together. See `wos/cache-update-strategies.md` for the full set and failure modes.
- REST vs RPC: resource-oriented HTTP vs procedure calls (gRPC, tRPC). REST for public or cross-team contracts; RPC for tight internal, typed, low-latency calls.
- Latency vs throughput: fast per request vs high total volume. Optimizing one often costs the other; name which the feature actually needs.
- Concurrency vs parallelism: interleaving many tasks vs running them simultaneously. Concurrency handles I/O-bound waits; parallelism needs real cores and is for CPU-bound work.
- Long polling vs WebSockets: reuse plain HTTP for near-real-time vs a persistent bidirectional channel. Long polling is simpler to operate; WebSockets pay off for high-frequency or truly bidirectional flows.
- Normalization vs denormalization: no duplicated data (write-simple, join on read) vs duplicated data (read-fast, harder writes). Normalize first; denormalize a proven hot read path.
- Monolith vs services: one deployable vs many. A monolith is the correct default for a solo or small team; split only when a real team or scaling boundary forces it.

## How to use this in the workflow

- When a task has two or more viable directions, name the relevant pair in `impact-analysis`'s trade-off table and record the chosen side plus rationale in DECISIONS.md.
- Do not paste this list into a design doc; cite the axis and decide it for the task at hand.
- Related: `wos/cache-update-strategies.md`, `wos/external-integration-patterns.md`.
