---
name: rate-limit-no-backoff
category: resilience
default-severity: P1
priority: P1
pillars: [resilience, observability]
cwe: [CWE-770]
languages: [typescript, javascript]
file-patterns: ["apps/web/src/server/**", "apps/web/src/lib/**", "packages/**/src/**", "**/integrations/**", "**/clients/**"]
perspectives: [operator, maintainer]
reversibility-check: false
---

# rate-limit-no-backoff

Code calls a rate-limited external API (e.g. CompuLife quoting API, Stripe, Twilio, a CRM webhook) without circuit-breaker, exponential backoff, jitter, or per-tenant quota. When the vendor throttles (HTTP 429 or 503), the client retries hard or in a tight loop, amplifying the load. The result is cascading failures, vendor account suspension, and customer-visible errors that should have been recoverable.

## What it looks like

- A `fetch` / `axios` / SDK call to a known rate-limited vendor wrapped in a naive `for` loop, `Promise.all` over a large batch, or a `while(!ok) retry` block.
- No `Retry-After` header inspection -- the code retries immediately on 429 instead of honoring the vendor's hint.
- No exponential backoff schedule and no jitter -- every tenant retries on the same wall-clock cadence, producing thundering-herd bursts against the vendor.
- No circuit breaker around the integration -- a vendor outage propagates to every tenant call until the vendor unbans the account.
- No per-tenant token bucket or leaky bucket -- one noisy tenant exhausts the shared quota, starving every other tenant.
- UI surfaces a generic "something went wrong" while the worker keeps retrying behind the scenes, hiding the real failure mode (vendor throttling) from operators and customers.

## Why it matters

- Vendor account bans: rate-limited APIs (CompuLife, Stripe, SendGrid) actively suspend accounts that ignore 429s. Recovery often requires a manual support ticket, hours to days of downtime.
- Cascading failures: a tight retry loop turns a transient 429 into a sustained DoS-against-self. Adjacent services (queues, DB connections, log pipelines) saturate.
- Customer-visible errors: quote requests time out, payments hang, notifications drop. The user sees a broken product even though the vendor would have served the request 30 seconds later.
- Observability gap: without circuit-breaker state and per-tenant counters, operators cannot tell "vendor is throttling us" from "vendor is down" from "one tenant is hammering". MTTR balloons.

## How to detect

Grep heuristics:

```
# Vendor SDK / fetch calls without retry config
rg -n "fetch\(|axios\.|got\(" apps/web/src packages -A 5 \
  | rg -B 1 -A 5 "retry|backoff|circuit" --files-without-match

# Known rate-limited vendors called without a wrapper
rg -n "compulife|stripe|twilio|sendgrid" apps/web/src packages -A 3 \
  | rg -B 1 -A 3 "Retry-After|exponential|jitter" --files-without-match
```

Code-review signals:

- Any new integration client lacking a shared `withRetry()` / `withCircuitBreaker()` wrapper.
- Absence of a token bucket or leaky bucket middleware in the request path.
- No per-tenant rate counter in Redis / KV / DB -- only a global counter, or none at all.
- 429 / 503 branches that `continue` or `return retry()` without delay.

## How to fix

1. Exponential backoff with jitter on 429 / 503 -- honor `Retry-After` when present; otherwise base delay * 2^attempt + random jitter, capped (e.g. 30s max, 5 attempts max).
2. Circuit breaker around the integration (e.g. `opossum`): open after N consecutive failures, half-open after a cooldown, surface "vendor unavailable" instead of retrying.
3. Per-tenant token bucket (Redis-backed) so one noisy tenant cannot starve others; reject or queue at the bucket boundary, not at the vendor.
4. Surface vendor throttling to the UI as a first-class state ("vendor is rate-limiting us, retrying in 12s") rather than a generic error or an infinite spinner.
5. Emit metrics: 429 count per vendor per tenant, circuit-breaker state transitions, bucket rejections. Alert on sustained open-circuit state.
6. Wrap the integration in a shared client module so every call site inherits the retry + breaker + bucket policy automatically.

## CWE / standard refs

- CWE-770: Allocation of Resources Without Limits or Throttling. The "resource" here is the vendor's per-account quota; the client allocates retry attempts without throttling itself, exhausting the quota and triggering vendor-side enforcement.

## See also

- `wos/bug-classes/missing-retry-on-external-call.md` (related but distinct: that class is "no retry at all"; this class is "too much retry, no backoff")
- `wos/bug-classes/stale-csv-cache-import.md` (sibling resilience class -- stale fallback when vendor is unavailable)
- `wos/bug-classes/unhandled-async-error.md` (often co-occurs: retry loop swallows the underlying error)
