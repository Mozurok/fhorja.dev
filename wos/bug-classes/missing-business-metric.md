---
name: missing-business-metric
category: observability
default-severity: P2
cwe: []
languages: [typescript, javascript, python, go]
file-patterns: ["controllers/**", "services/**", "consumers/**", "handlers/**", "api/**"]
perspectives: [operator]
reversibility-check: false
---

# missing-business-metric

## Trigger

A business-critical operation (share created, verification completed, payment processed, user signed up) executes without emitting a counter, histogram, or gauge metric. Without business metrics, the team cannot build dashboards, set SLOs, or create alerts for business health; they only discover problems when users report them.

## Detection

Look for handlers or service functions that perform a meaningful business action where:
- No metric increment/record call is present (e.g., `metrics.increment("shares.created")`, `statsd.count(...)`, `prometheus.counter(...)`)
- No analytics event is emitted (e.g., `analytics.track("share_created")`)
- The operation changes state that the business cares about (not just internal bookkeeping)

## Retrieval

- The function body performing the business operation
- The metrics/analytics library (to verify available primitives)

## Analysis prompt

Given the business operation:
1. What is the business-significant event? (share created, verification completed, email sent)
2. Is there a metric or analytics event emitted?
3. What metric would be most useful? (counter for rate, histogram for latency, gauge for active count)
4. If no metrics library exists in the project: note as informational, not a code fix.

## Severity rubric

- P1: high-value business operation (payment, signup, verification) with no metric
- P2: secondary operation (share created, notification sent) with no metric

## Confidence factors

- HIGH: handler performs a clear business action; project has a metrics library but this handler does not use it
- MEDIUM: handler performs a business action; no metrics library visible in the project
- LOW: internal operation (cleanup job, cache refresh) where business metrics are less critical

## Examples

### Positive (no metric)

```typescript
await db.from("shares").insert({ ... });
res.status(201).json({ share_id: claim.id });
// No metric: operations team cannot track share creation rate or set alerts
```

### Negative (with metric)

```typescript
await db.from("shares").insert({ ... });
metrics.increment("verification_shares.created", { company_id: auth.companyId });
res.status(201).json({ share_id: claim.id });
```
