# Slice 8 Post-Deploy Verification Plan: Send user-signup welcome email

**Deploy:** production, sha=`c1b2a3d`, ts=2026-06-05T09:00:00Z
**Window:** 2026-06-05T09:00:00Z → 2026-06-05T10:00:00Z
**On-call:** @bruno
**Feature flag:** none (full rollout)

---

## Verification approach

Three ACs → three (or four) signals, each traceable to one AC. The on-call must be able to walk this in under 15 minutes. If a signal does not directly prove or disprove an AC (or a named risk), it is excluded below.

### Named risks (used to justify signal inclusion)
- **R-1:** Email queueing silently fails (no errors, no emails) → covers AC-1 failure mode invisible to user.
- **R-2:** Signup endpoint latency regresses because email send accidentally became synchronous → covers AC-3 "does NOT block".
- **R-3:** Dead-letter queue grows unbounded after retry exhaustion → covers AC-3 retry-then-DLQ contract.

---

## Per-AC signal mapping

| AC / Risk | Signal | Where | Query / Check | Pass criterion |
|---|---|---|---|---|
| **AC-1** + R-1: welcome email is queued to Resend | Datadog Logs: structured log `event=welcome_email.queued` correlated with each new signup in window | Datadog Logs (`https://app.datadoghq.com/logs`) | `service:api env:prod event:welcome_email.queued @deploy.sha:c1b2a3d` between 09:00–10:00Z; cross-reference count vs. `event:user.signed_up` in same window | Count(`welcome_email.queued`) == Count(`user.signed_up`) within ±1 (race at window edge) |
| **AC-2**: display name OR 'there' fallback | Datadog Logs: sample 5 most recent `welcome_email.queued` events and inspect `@email.greeting_name` field | Datadog Logs | Same query as AC-1 + `| head 5`; visually confirm one signup with `display_name` present resolves to that name; one signup with null/empty `display_name` resolves to `there` | At least one of each branch observed and rendered correctly; zero events where `greeting_name` is null/empty/`undefined` |
| **AC-3** + R-2: user flow does NOT block on email send | Datadog APM: p95 latency of `POST /auth/signup` endpoint during deploy window vs. prior 24h baseline | Datadog APM (signup endpoint trace) | `service:api resource_name:POST /auth/signup`, compare p95 09:00–10:00Z vs. 08:00–09:00Z baseline | p95 delta ≤ +50ms; no span where `welcome_email.send` is a synchronous child of the signup transaction |
| **AC-3** + R-3: retry 3x then DLQ | Sentry: any `welcome_email.send` errors during window, and count of messages that reached the dead-letter queue | Sentry (`https://sentry.io/myorg`, project: api, tag `email_type:welcome`) | Filter `tag:email_type=welcome`, time range = deploy window | If errors observed: each error event must show ≤3 retry attempts in breadcrumbs before DLQ; no event with `retry.count > 3`. If zero errors: pass by absence (acceptable). |

**Total signals: 4** (one per AC, with AC-3 covered by two complementary signals because it has two distinct contract clauses: "does NOT block" and "retried 3 times then dead-lettered").

---

## Negative check

In the same window, confirm that users who **did not** sign up did **not** receive a welcome email:

- Datadog Logs: `event:welcome_email.queued -@trigger:user_signup` over the deploy window.
- **Pass:** zero results. Any hit indicates the email is being queued from an unintended code path (signup-adjacent flow, replay, test harness leak).

---

## Rollback

**Trigger:**
- AC-1 fails: queued count diverges from signup count by >5% over any 10-minute sub-window, OR
- AC-3 fails: signup p95 regression > +200ms, OR
- AC-3 fails: any single signup transaction shows a synchronous `welcome_email.send` child span.

**Action:**
1. `@bruno` initiates rollback to prior sha via standard deploy pipeline (revert + redeploy; no DB migration in this slice so no schema rollback needed).
2. Drain any in-flight retry queue items before rollback completes (let in-flight retries finish to avoid duplicate sends on redeploy of new sha).
3. Inspect DLQ post-rollback; manually re-queue any messages that were dead-lettered due to the bug, not due to genuine Resend failures.
4. Post-mortem in Sentry issue + Datadog incident, link sha `c1b2a3d`.

**Time budget for rollback decision:** within deploy window (by 10:00Z).

---

## Trimmed signals (why excluded)

The shotgun baseline would have added one signal per available observability system. The following were considered and **excluded** because they do not trace to AC-1, AC-2, AC-3, or a named risk:

| Excluded signal | Where it came from | Why trimmed |
|---|---|---|
| PostgreSQL: query latency on `users` insert | PG monitoring | Does not trace to any AC. Signup write path is unchanged by this slice (email is post-insert side effect). Would only matter if AC-3 fails *and* root cause is DB contention -- covered transitively by APM signup p95. |
| PostHog: funnel conversion rate `signup → email_opened` | PostHog analytics | "Email opened" is a Resend-side / recipient-side event, not part of any AC. AC-1 says queued, not delivered or opened. Belongs to a product metrics dashboard, not a deploy verification runbook. |
| Grafana: queue depth dashboard (general worker queue) | Grafana | Redundant with the Sentry retry/DLQ check for AC-3. Queue depth is meaningful over hours/days, not within a 60-minute deploy window. Would create noise. |
| CloudWatch: Lambda / container CPU + memory for the email worker | CloudWatch | No AC mentions resource utilization. A resource spike would only matter if it caused failures, which would already surface via Sentry (AC-3) or queued-vs-signed-up divergence (AC-1). Pure duplication. |
| Datadog SLO: monthly availability SLO for signup endpoint | Datadog SLOs | SLOs are 28-day rolling. A 60-minute deploy window cannot meaningfully move a 28-day SLO; checking it during deploy verification gives false confidence (will always read "green"). Belongs to weekly review, not deploy gate. |
| Datadog Logs: every `email.*` event across the platform | Datadog Logs (broader query) | The narrow `event:welcome_email.queued` query already covers AC-1. Broader log queries pull in transactional, marketing, password-reset emails -- none of which are in this slice's scope. Noise. |
| Sentry: all errors in `api` service during window | Sentry (broader query) | Already covered for the email path by the tagged `email_type:welcome` query. A broad Sentry sweep catches unrelated regressions and dilutes the deploy verification into a generic health check. If we want a generic health check, that lives in a separate always-on dashboard, not in this slice's runbook. |
| Grafana: Resend provider response time | Grafana / Resend webhook | Third-party provider latency is outside our deploy's blast radius. If Resend is slow, our retry logic (AC-3) handles it; we do not roll back our deploy because Resend is slow. |

**Rule applied:** every signal in the included table maps to exactly one of `{AC-1, AC-2, AC-3, R-1, R-2, R-3}`. Every excluded signal failed that test and was named here so the on-call understands the *deliberate* omission rather than an oversight.

---

## On-call execution checklist (15-minute walk)

1. (2 min) Open Datadog Logs, run AC-1 query, eyeball counts. → AC-1
2. (3 min) Sample 5 events from same query, verify greeting branch. → AC-2
3. (3 min) Open APM, compare signup p95 window vs. baseline; inspect one trace for sync email span. → AC-3 / R-2
4. (3 min) Open Sentry filtered by `email_type:welcome`, check retry counts on any errors. → AC-3 / R-3
5. (2 min) Run negative-check query. → guards against over-triggering.
6. (2 min) Decision: pass, monitor, or rollback per criteria above.
