---
activation: model_decision
description: Cache update strategies (cache-aside, write-through, write-behind, refresh-ahead) with when-to-use and the failure mode each invites. Load when a task adds or changes a cache layer in front of a datastore.
---

# wos/cache-update-strategies.md

Lazy reference for the four canonical cache update strategies. Load this when a task adds a cache (Redis, an in-memory layer, a CDN data cache) in front of a datastore, or when reviewing a slice that reads or writes through one. The point of naming the strategy is to make the staleness and consistency trade-off an explicit decision with a known failure mode, not a default that surfaces as a bug weeks later.

A solo or small-team builder most often reaches for a cache to take read load off Postgres or to hide a slow upstream. The mistake is not choosing a cache; it is choosing one of these strategies implicitly and inheriting its failure mode without noticing. Name the strategy in DECISIONS.md and the failure mode below tells you what to guard.

## Cache-aside (lazy loading)

The application reads from the cache; on a miss it reads the datastore, populates the cache, and returns. Writes go to the datastore and invalidate (or update) the cache entry.

- When to use: read-heavy data that tolerates brief staleness; the default for most app-level caching.
- Failure mode: stale reads between a write and the invalidation, and a cache stampede when a hot key expires and many requests miss at once. Guard with a short TTL plus a single-flight or lock on the repopulate, and invalidate on write rather than only relying on TTL.

## Write-through

Every write goes to the cache and the datastore synchronously, in the same operation, so the cache is always consistent with the store.

- When to use: data that is read soon after it is written and must not be stale; when a slightly slower write is acceptable.
- Failure mode: write latency is the sum of both writes, and the cache fills with data that may never be read (write amplification). Pair with a TTL so cold entries expire.

## Write-behind (write-back)

Writes go to the cache and are flushed to the datastore asynchronously after a delay or in batches.

- When to use: write-heavy workloads that can tolerate a small window of durability risk in exchange for fast writes and fewer datastore round trips.
- Failure mode: data loss if the cache node dies before the flush, and ordering or consistency bugs if two writers race the flush. Only use with a durable cache or an accepted, documented loss window; most small-team apps should not reach for this.

## Refresh-ahead

The cache proactively refreshes a soon-to-expire entry before it is requested, predicting that a hot key will be read again.

- When to use: a small set of predictably hot keys where a cache-miss latency spike is unacceptable.
- Failure mode: wasted refreshes on keys that were not going to be read, and complexity that rarely pays off below real scale. Usually premature for a solo or small-team build; prefer cache-aside with a sane TTL first.

## How to use this in the workflow

- Cite the chosen strategy by name in DECISIONS.md when a task adds a cache, and record the failure mode it guards against.
- `impact-analysis` and `stack-recommend` can reference this file when a task's plan introduces a cache layer, so the choice is a named pattern rather than a guess.
- Related: `wos/architecture-tradeoffs.md` for the strong-vs-eventual-consistency and read-through-vs-write-through pairs this sits inside.
