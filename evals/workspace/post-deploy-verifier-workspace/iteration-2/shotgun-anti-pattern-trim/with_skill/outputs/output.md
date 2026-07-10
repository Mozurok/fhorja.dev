# POST_DEPLOY_PLAN -- Slice 8: user-signup welcome email

Deploy: `production` @ sha `c1b2a3d`, window `2026-06-05T09:00:00Z -> 2026-06-05T10:00:00Z`
On-call: `@bruno`
Feature flag: none (unconditional ship)

## Acceptance criteria (enumerated)
- AC-1: New signup queues a welcome email to Resend.
- AC-2: Email body contains display name when present, else literal `there`.
- AC-3: Failed sends retry x3 then dead-letter; signup flow does NOT block on send.

## Per-AC signal mapping (trimmed)

| AC | Claim | Signal class | Exact query / URL / inputs | Expected result | Owner |
|----|-------|--------------|----------------------------|-----------------|-------|
| AC-1 | Signup enqueues a welcome email to Resend | Datadog Logs | `service:signup-api env:production deploy_sha:c1b2a3d event:email.enqueued provider:resend template:welcome` over `2026-06-05T09:00:00Z..10:00:00Z` -- URL: `https://app.datadoghq.com/logs?query=service%3Asignup-api%20env%3Aproduction%20deploy_sha%3Ac1b2a3d%20event%3Aemail.enqueued%20provider%3Aresend%20template%3Awelcome&from_ts=1780995600000&to_ts=1780999200000` | >=1 log line per signup in the window; field `to_email` matches the signup row | `@bruno` |
| AC-1 + AC-2 | Welcome email actually delivered to Resend with correct greeting body | Smoke test (live signup) | Browser: `POST https://fhorja.app/signup` with body `{ email: "bruno+pdv-c1b2a3d@fhorja.app", password: "Pdv!c1b2a3d", display_name: "Bruno" }`. Then repeat with body `{ email: "bruno+pdv-c1b2a3d-anon@fhorja.app", password: "Pdv!c1b2a3d", display_name: null }`. Open both inboxes within 2 min. | Named-case email subject `Welcome, Bruno` and body contains `Hi Bruno,`. Anonymous-case email body contains `Hi there,` (literal fallback string). Both arrive within 60s. | `@bruno` |
| AC-3 | Failures retry x3 then dead-letter AND user signup is not blocked | PostgreSQL invariant (dead-letter table + signup latency join) | Connect `db.prod.internal`, run: `SELECT s.id, s.created_at, q.attempts, q.status, q.dead_lettered_at, EXTRACT(EPOCH FROM (s.created_at_response - s.created_at_request)) AS signup_ms FROM users s LEFT JOIN email_queue q ON q.user_id = s.id AND q.template = 'welcome' WHERE s.created_at >= '2026-06-05T09:00:00Z' AND s.created_at < '2026-06-05T10:00:00Z' ORDER BY s.created_at DESC;` | (a) Every `q.status='dead_lettered'` row has `attempts = 3`; no rows with `attempts > 3`. (b) `signup_ms < 1500` for ALL rows, including those where `q.status IN ('failed','dead_lettered')` -- proves signup did not block on Resend. | `@bruno` |

Three signals cover three ACs with one duplicated user-flow smoke test for AC-1 and AC-2 (cheap to merge -- same browser session, two payloads). The DB invariant is load-bearing for AC-3 because it is the only signal that proves BOTH halves of the AC (retry-then-DLQ behavior AND non-blocking signup) in one query.

## Negative checks (would prove the change did NOT ship)

| Check | Query | Expected (proves shipped) | Failure (proves silent no-op) |
|-------|-------|---------------------------|-------------------------------|
| N-1: New code path is hit | Datadog Logs: `service:signup-api deploy_sha:c1b2a3d event:email.enqueued` window `09:00Z..10:00Z` | `count > 0` | `count == 0` AND signups occurred in the window -> code path dead, page `@bruno` immediately |

## Rollback trigger checklist

| Observation | Page | Command |
|-------------|------|---------|
| Negative check N-1 returns zero hits AND signups > 0 in window (silent no-op) | `@bruno` | Revert: `git revert c1b2a3d && git push origin main` (no flag to flip; unconditional ship) |
| AC-3 DB query shows ANY row with `signup_ms >= 1500` correlated to `q.status IN ('failed','dead_lettered')` (signup IS blocking on email) | `@bruno` | Revert: `git revert c1b2a3d && git push origin main`. Hot-fix path: wrap `resend.send()` in `setImmediate` / background queue, redeploy. |
| Datadog Logs shows `event:email.enqueued.error provider:resend` count > 1% of signup count over a rolling 10-minute window | `@bruno` | Do NOT revert (errors are expected to retry+DLQ per AC-3). Investigate Resend status page; if Resend outage, accept dead-letter accumulation and reprocess from DLQ post-incident. |

## Trimmed signals (why excluded)

The shotgun baseline would have authored one signal per observability system (8+ signals). Each was tested against Step 8: does it trace to AC-1, AC-2, AC-3, or a named risk? If not, deleted.

| Excluded signal | Obs system | Why trimmed |
|-----------------|------------|-------------|
| Datadog APM trace latency panel for `POST /signup` p95 | Datadog APM | Does not trace to AC-1/2/3. AC-3's non-blocking claim is already covered by the DB `signup_ms` column in the per-row invariant query, which is stronger (per-row, not aggregate) than an APM p95. Adding APM duplicates coverage and dilutes the runbook. |
| Datadog SLO burn-rate panel for signup availability | Datadog SLOs | No SLO is named in the slice or in `TASK_STATE.md ## Risks to watch` for this change. SLO burn is a standing dashboard the on-call watches anyway; not slice-specific. |
| Sentry issue search filtered to `release:c1b2a3d` | Sentry | Plausible but not required: errors in the email send path are EXPECTED per AC-3 (retry then DLQ is the success behavior). A Sentry spike would be noise unless it shows a stack outside the retry envelope. The existing standing Sentry alert routes to `@bruno` already; no slice-specific Sentry query adds confidence. |
| PostHog funnel `signup_started -> signup_completed -> welcome_email_opened` | PostHog | Open-rate is a product-analytics question, not a deploy-verification question. AC-1 is about ENQUEUE, not delivery-success-as-measured-by-open. Open-rate has hours-to-days latency and cannot be checked inside the 60-minute deploy window. |
| Grafana dashboard panel for queue depth on `email_queue` | Grafana | Queue depth would only matter if a backlog hypothesis was named in `## Risks to watch`. None is. The DB invariant query in AC-3 already inspects `attempts` and `status` per row, which subsumes a depth panel for this 60-minute window. |
| CloudWatch metric for Lambda cold-start / memory on the signup handler | CloudWatch | Infrastructure-level, not slice-level. No AC references handler runtime. Cold-start regression would surface in the APM panel that was itself trimmed; cascading reinstatement is unjustified. |
| Datadog Logs query for `event:email.sent` (delivery confirmation) | Datadog Logs | AC-1 is "queued to the Resend provider", not "delivered by Resend". Enqueue is the contract surface; delivery is Resend's responsibility behind their own SLA. Checking `email.sent` conflates two concerns and would create a false-negative if Resend is slow but healthy. |
| Sentry release-health session-crash-free rate | Sentry | Not slice-specific. This is a standing release-quality gauge, not a signal that proves AC-1/2/3. |

Eight plausible signals excluded. Three signals retained. Every retained signal traces to a named AC. Every excluded signal was rejected because it failed Step 8's tracing test, not because the obs system is unhealthy.

## Smoke-test walkthrough script (concrete inputs)

1. Open incognito browser, go to `https://fhorja.app/signup`.
2. Submit form: email `bruno+pdv-c1b2a3d@fhorja.app`, password `Pdv!c1b2a3d`, display name `Bruno`. Expect HTTP 200 within 1.5s, redirect to `/dashboard`.
3. Open new incognito tab, go to `https://fhorja.app/signup`.
4. Submit form: email `bruno+pdv-c1b2a3d-anon@fhorja.app`, password `Pdv!c1b2a3d`, leave display name BLANK. Expect HTTP 200 within 1.5s, redirect to `/dashboard`.
5. Open inbox for `bruno+pdv-c1b2a3d@fhorja.app`. Within 60s, expect email subject `Welcome, Bruno`, body starts with `Hi Bruno,`.
6. Open inbox for `bruno+pdv-c1b2a3d-anon@fhorja.app`. Within 60s, expect email body starts with `Hi there,` (literal fallback).
7. Run the AC-3 SQL query in the table above; confirm both new user rows have `signup_ms < 1500` and exactly one `email_queue` row each with `status='sent'` (or `status='pending'` with `attempts < 3`).

If step 5 or step 6 produces the wrong greeting -> AC-2 failed, page `@bruno`, revert.
If step 2 or step 4 exceeds 1.5s OR the SQL shows blocking on email -> AC-3 failed, page `@bruno`, revert.

## Definition of done

- 3 ACs, 3 retained signals, every AC mapped (zero orphans).
- All 3 signals are query-shaped (exact Datadog query string with deploy_sha and time window, exact SQL with bounded `created_at`, exact smoke-test inputs with concrete payloads and expected DOM/email text).
- 1 negative check (N-1) catches the silent no-op case.
- Rollback checklist names `@bruno` and gives the exact `git revert c1b2a3d && git push origin main` command (no flag because feature flag is none).
- 8 plausible-but-excluded signals listed with their trace-failure reason -- runbook stays inside the 15-minute execution budget.

### Handoff

**Next:** `slice-closure` to apply the `## Post-deploy checks` PROPOSED block to `SLICES/8_user_signup_email.md` and close the slice once the smoke walk passes.
**Run now:** `slice-closure`
