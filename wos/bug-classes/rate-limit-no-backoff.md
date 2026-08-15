---
name: rate-limit-no-backoff
category: resilience
default-severity: P1
cwe: [CWE-770]
languages: [typescript, javascript]
file-patterns: ["apps/web/src/server/**", "apps/web/src/lib/**", "packages/**/src/**", "**/integrations/**", "**/clients/**"]
perspectives: [operator, maintainer]
reversibility-check: false
---

# rate-limit-no-backoff

## Trigger

Code calls a rate-limited external API without backoff, jitter, a circuit breaker, or a per-tenant quota. When the vendor throttles, the client retries hard or in a tight loop, so the response to being told to slow down is to speed up.

The damage runs in three directions at once. Vendors that enforce quotas suspend accounts that ignore throttling responses, and recovery usually means a support ticket and hours of downtime rather than a code change. A tight retry loop turns a transient throttle into a sustained denial of service against yourself, saturating the queues, database connections, and log pipelines around it. And the operator cannot tell which of three situations they are in, because without breaker state and per-tenant counters, "the vendor is throttling us", "the vendor is down", and "one tenant is hammering it" all present as the same wall of errors.

CWE-770 (Allocation of Resources Without Limits or Throttling): the resource is the vendor's per-account quota, and the client allocates retry attempts against it without throttling itself.

## Detection

- A vendor SDK or `fetch` call wrapped in a bare `for` loop, a `Promise.all` over a large batch, or a `while (!ok) retry` block.
- A 429 or 503 branch that retries immediately, with no read of the `Retry-After` header the vendor sent precisely to answer the question of when.
- A retry schedule with no jitter, so every tenant retries on the same wall-clock cadence and the herd arrives together.
- No circuit breaker around the integration, so a vendor outage propagates through every tenant call until the vendor lifts the block.
- No per-tenant bucket, only a global counter or none, so one noisy tenant exhausts the shared quota and starves the rest.
- A generic error in the UI while a worker retries behind it, which hides the actual state from both the customer and the operator.

Grep heuristics:

```
# Vendor SDK / fetch calls without retry config
rg -n "fetch\(|axios\.|got\(" apps/web/src packages -A 5 \
  | rg -B 1 -A 5 "retry|backoff|circuit" --files-without-match

# Known rate-limited vendors called without a wrapper
rg -n "<vendor-sdk>|stripe|twilio|sendgrid" apps/web/src packages -A 3 \
  | rg -B 1 -A 3 "Retry-After|exponential|jitter" --files-without-match
```

## Retrieval

- Every call site for the vendor, not one. This class is a property of the integration surface, and a single wrapped call site says nothing about the four unwrapped ones next to it.
- The shared client module if one exists, and its absence if it does not. Whether the policy lives in one place or is re-implemented per call site is the difference between one fix and twenty.
- The full response-handling branch for each call, down to what happens on 429 and 503 specifically. The retry decision is usually several lines below the request, and reading only the request misses it.
- Any rate-limiting middleware, token bucket, or quota check in the request path, along with where its state lives. A per-process counter and a shared-store counter behave differently under more than one instance, and only the storage location shows which one this is.
- The metrics and alerts that exist for this vendor. Their absence is the observability half of the class and should be recorded as an answer, not left as silence.
- Whatever the vendor's own documentation says about its limits and its throttling response, captured as a reference before any claim about that vendor's behavior is written down.

## Analysis prompt

Given the retrieved call sites, the response-handling branches, and the surrounding middleware:

1. Enumerate every call site for this vendor and report, per site, whether it goes through a shared client or issues its own request. Report the count both ways. A minority of unwrapped sites is still an unwrapped surface.
2. For each site, report what happens on a throttling response. Quote the branch. Report specifically whether the code reads the vendor's own retry hint from the response headers, and if it does not, say what it uses instead.
3. Report whether the retry schedule grows and whether it carries jitter. A fixed delay is better than none and still synchronizes the herd; report the two properties separately because they fail differently.
4. Report whether a maximum attempt count and a maximum total delay exist. An unbounded retry is the shape that turns a throttle into an outage.
5. Determine whether a circuit breaker wraps the integration, and if so where its state lives and what the caller sees when it is open. A breaker whose open state surfaces as the same generic error as everything else has not improved the operator's position.
6. Determine whether quota is tracked per tenant or globally, and name the store. Report what happens at the bucket boundary: rejection, queueing, or nothing.
7. Report which metrics exist: throttling responses per vendor and per tenant, breaker state transitions, bucket rejections. Name each one that is absent.
8. WHERE the analysis needs to state what this specific vendor does on throttling, cite the captured vendor documentation for that claim. Do not assert a vendor's enforcement behavior, suspension policy, or limit values from memory; if no reference was captured, report the claim as ungrounded and name the capture as the next step.
9. Recommend, in order: honor the vendor's own retry hint when present and otherwise back off exponentially with jitter, under an explicit attempt and total-delay cap; put a circuit breaker around the integration and give its open state a distinct, surfaced meaning; add a per-tenant bucket in a shared store and reject or queue at that boundary rather than at the vendor; show throttling in the UI as its own state rather than as a generic error; emit the three metrics above and alert on a sustained open circuit; and move every call site behind one shared client so the policy is inherited rather than remembered.

## Severity rubric

- **P1**: an unwrapped call site to a quota-enforcing vendor that retries without backoff. Justification: the failure amplifies under exactly the conditions that caused it, and the worst outcome is account suspension, which is recovered through a vendor support queue rather than a deploy. It stays below P0 because no data is lost or corrupted and the blast radius, while wide, is a temporary loss of one integration.
- **P1 also**: no per-tenant quota on a multi-tenant path, even where backoff is correct. One tenant can consume the shared allowance, and the tenants who lose access did nothing.
- **P2**: backoff, breaker, and bucket all present, with no metrics distinguishing throttling from outage. The system behaves correctly and the operator still cannot tell what is happening during an incident.

## Confidence factors

- **HIGH**: a retry branch with no delay between attempts, read directly off the call site. The loop is the finding.
- **MEDIUM**: a shared client with backoff exists and several call sites bypass it. The policy is right and its coverage is unestablished until each site is checked.
- **LOW**: a call to a vendor whose quota behavior is not documented in the captured references, where the risk is inferred from the vendor category rather than from that vendor's stated limits.

## Examples

### Positive (immediate retry, no cap, shared quota)

```ts
for (const lead of leads) {                    // batch of unknown size
  let ok = false;
  while (!ok) {                                // no attempt cap
    const res = await fetch(vendorUrl, { method: "POST", body: toBody(lead) });
    if (res.status === 429) continue;          // Retry-After ignored, no delay
    ok = res.ok;
  }
}
```

The vendor's throttle is answered with a tighter loop, there is no ceiling on attempts, and every tenant running this path competes for one undivided quota.

### Negative (hint honored, bounded, broken, bucketed)

```ts
await tenantBucket.consume(tenantId);          // rejects at our boundary, not the vendor's
await breaker.fire(() =>
  withRetry(() => vendor.quote(lead), {
    maxAttempts: 5,
    maxTotalMs: 30_000,
    delay: (attempt, res) =>
      retryAfterMs(res) ?? base * 2 ** attempt + jitter(),   // vendor's hint wins
    on429: () => metrics.increment("vendor.throttled", { tenantId }),
  }),
);
```

The vendor's own hint takes precedence over the local schedule, the retry is bounded in both attempts and wall-clock, the breaker gives an outage a distinct surfaced state, and the bucket makes one tenant's burst that tenant's problem.
