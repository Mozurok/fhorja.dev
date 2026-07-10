# POST_DEPLOY_PLAN.md -- Slice 22: Stripe webhook idempotency

Deploy: `production`, `sha=9f8e7d6`, deploy_ts=`2026-06-05T14:30:00Z`
Smoke window: `2026-06-05T14:30:00Z` → `2026-06-05T15:30:00Z` (1h)
Feature flag: none (unconditional ship per Bruno's no-premature-feature-flags rule)
Named on-call: `@bruno`
Observability inventory:
- Datadog Logs: `https://app.datadoghq.com/logs`
- Datadog APM (service `webhook-api`): `https://app.datadoghq.com/apm/services/webhook-api`
- Sentry project: `https://sentry.io/fhorja`
- Postgres: `db.fhorja.supabase.co` (read-only psql / Supabase SQL editor)
- Feature-flag system: NONE (no flag-toggle signal applicable for this slice)

---

## 1. Per-AC signal mapping table

| AC | Claim | Signal class | Exact query / URL / inputs | Expected result | Owner |
|---|---|---|---|---|---|
| AC-1 | `POST /api/v1/webhooks/stripe` returns 200 on first receipt of `customer.subscription.created` | Structured log query (Datadog Logs) | `service:webhook-api route:/api/v1/webhooks/stripe status:200 deploy_sha:9f8e7d6 @evt.type:customer.subscription.created @evt.first_receipt:true` over `from=2026-06-05T14:30:00Z to=2026-06-05T15:30:00Z` | ≥1 log line per first-receipt event; status field literally `200`; no `@evt.dedup_hit:true` on the same line | `@bruno` |
| AC-1 | Same claim, cross-check | DB invariant query (Postgres) | `SELECT COUNT(*) AS new_rows FROM public.subscriptions WHERE stripe_event_id IN (SELECT event_id FROM public.stripe_webhook_events WHERE received_at >= '2026-06-05T14:30:00Z' AND received_at < '2026-06-05T15:30:00Z' AND event_type = 'customer.subscription.created');` | `new_rows` equals COUNT(DISTINCT event_id) for first-receipts in window (1:1 mapping, no missing rows) | `@bruno` |
| AC-1 | Same claim, smoke | Smoke test (curl, signed payload) | See §4 Smoke Walkthrough -- Step A | HTTP `200`, body `{"received":true,"deduped":false}`, new row in `public.subscriptions` | `@bruno` |
| AC-2 | Duplicate of same `event.id` returns 200 but does NOT re-execute side effects | Structured log query (Datadog Logs) | `service:webhook-api route:/api/v1/webhooks/stripe status:200 deploy_sha:9f8e7d6 @evt.dedup_hit:true` over deploy window | ≥1 line for the duplicate replay; same line shows `@side_effects_executed:false`; correlated `@evt.id` matches first-receipt line | `@bruno` |
| AC-2 | Same claim, DB cross-check (no duplicate row) | DB invariant query | `SELECT stripe_event_id, COUNT(*) AS n FROM public.subscriptions WHERE created_at >= '2026-06-05T14:30:00Z' AND created_at < '2026-06-05T15:30:00Z' GROUP BY stripe_event_id HAVING COUNT(*) > 1;` | Empty result set (zero rows) -- no event_id appears more than once | `@bruno` |
| AC-2 | Same claim, billing email side effect | DB invariant query | `SELECT recipient, email_kind, COUNT(*) AS n FROM public.outbound_emails WHERE email_kind = 'subscription_created' AND created_at >= '2026-06-05T14:30:00Z' AND created_at < '2026-06-05T15:30:00Z' GROUP BY recipient, email_kind HAVING COUNT(*) > 1;` | Empty result set (no duplicate billing email per recipient) | `@bruno` |
| AC-2 | Same claim, smoke | Smoke test (curl, replay same signed payload) | See §4 Smoke Walkthrough -- Step B | HTTP `200`, body `{"received":true,"deduped":true}`, ZERO new rows in `public.subscriptions`, ZERO new rows in `public.outbound_emails` | `@bruno` |
| AC-3 | Webhook signature verification rejects unsigned requests with 400 | Structured log query (Datadog Logs) | `service:webhook-api route:/api/v1/webhooks/stripe status:400 deploy_sha:9f8e7d6 @err.code:stripe_signature_missing` over deploy window | ≥1 line for the negative smoke; `@err.code` literally `stripe_signature_missing` (or `stripe_signature_invalid` for the tampered variant) | `@bruno` |
| AC-3 | Same claim, smoke | Smoke test (curl, no `Stripe-Signature` header) | See §4 Smoke Walkthrough -- Step C | HTTP `400`, body matches `{"error":"missing_signature"}`; NO row inserted in `public.subscriptions`, `public.stripe_webhook_events`, or `public.outbound_emails` | `@bruno` |
| AC-3 | Same claim, security regression panel | Datadog APM panel | `https://app.datadoghq.com/apm/services/webhook-api?env=production&start=1780414200000&end=1780417800000&resources=POST%20%2Fapi%2Fv1%2Fwebhooks%2Fstripe` (filter `http.status_code:400` AND `error.type:StripeSignatureError`) | 4xx panel shows the smoke 400s only; no spurious 4xx spikes from real Stripe traffic (signed requests should not 400) | `@bruno` |

---

## 2. Log queries -- exact structured fields

All queries are scoped to `service:webhook-api`, the `route` field on the Express/Next handler, the `deploy_sha` tag set by the deploy pipeline (env var `DD_VERSION=9f8e7d6`), and the deploy window `from=2026-06-05T14:30:00Z to=2026-06-05T15:30:00Z`.

**Q1 -- AC-1 first-receipt 200s (Datadog Logs):**
```
service:webhook-api route:/api/v1/webhooks/stripe status:200 deploy_sha:9f8e7d6 @evt.type:customer.subscription.created @evt.first_receipt:true
```
URL: `https://app.datadoghq.com/logs?query=service%3Awebhook-api%20route%3A%2Fapi%2Fv1%2Fwebhooks%2Fstripe%20status%3A200%20deploy_sha%3A9f8e7d6%20%40evt.type%3Acustomer.subscription.created%20%40evt.first_receipt%3Atrue&from_ts=1780414200000&to_ts=1780417800000&live=false`

**Q2 -- AC-2 duplicate-replay dedup hits:**
```
service:webhook-api route:/api/v1/webhooks/stripe status:200 deploy_sha:9f8e7d6 @evt.dedup_hit:true @side_effects_executed:false
```
URL: `https://app.datadoghq.com/logs?query=service%3Awebhook-api%20route%3A%2Fapi%2Fv1%2Fwebhooks%2Fstripe%20status%3A200%20deploy_sha%3A9f8e7d6%20%40evt.dedup_hit%3Atrue%20%40side_effects_executed%3Afalse&from_ts=1780414200000&to_ts=1780417800000&live=false`

**Q3 -- AC-3 signature-rejection 400s:**
```
service:webhook-api route:/api/v1/webhooks/stripe status:400 deploy_sha:9f8e7d6 @err.code:(stripe_signature_missing OR stripe_signature_invalid)
```
URL: `https://app.datadoghq.com/logs?query=service%3Awebhook-api%20route%3A%2Fapi%2Fv1%2Fwebhooks%2Fstripe%20status%3A400%20deploy_sha%3A9f8e7d6%20%40err.code%3A%28stripe_signature_missing%20OR%20stripe_signature_invalid%29&from_ts=1780414200000&to_ts=1780417800000&live=false`

**Q4 -- Cross-cut: any unhandled exception on the route in the deploy window (Sentry):**
URL: `https://sentry.io/fhorja/issues/?project=webhook-api&query=is%3Aunresolved+release%3A9f8e7d6+url%3A%22%2Fapi%2Fv1%2Fwebhooks%2Fstripe%22&statsPeriod=1h&start=2026-06-05T14%3A30%3A00&end=2026-06-05T15%3A30%3A00`
Expected: ZERO new issues tagged `release:9f8e7d6` for this route (issues from earlier releases are allowed; new ones are not).

---

## 3. Dashboard panels -- bounded to deploy window

Epoch ms for deploy window: start=`1780414200000`, end=`1780417800000`.

**P1 -- APM service overview, webhook-api, throughput + error rate + p95 latency:**
`https://app.datadoghq.com/apm/services/webhook-api?env=production&start=1780414200000&end=1780417800000`
Expected: 200-rate ≥ pre-deploy 200-rate (visual sanity); 5xx-rate within 1σ of pre-deploy baseline; p95 latency on `POST /api/v1/webhooks/stripe` not regressed by >50% vs. preceding 1h.

**P2 -- Route-scoped resource panel for `POST /api/v1/webhooks/stripe`:**
`https://app.datadoghq.com/apm/services/webhook-api?env=production&start=1780414200000&end=1780417800000&resources=POST%20%2Fapi%2Fv1%2Fwebhooks%2Fstripe`
Expected: error rate ≤ 0.5% excluding the AC-3 smoke 400s; throughput shows the expected Stripe traffic shape (no flatline → see negative checks).

**P3 -- Sentry release health for `9f8e7d6`:**
`https://sentry.io/fhorja/releases/9f8e7d6/?project=webhook-api&statsPeriod=1h&start=2026-06-05T14%3A30%3A00&end=2026-06-05T15%3A30%3A00`
Expected: crash-free session rate ≥ 99.9%; zero new issues attributed to this release on the webhook route.

---

## 4. Smoke-test walkthrough -- exact inputs

Pre-req: shell env `STRIPE_WEBHOOK_SECRET` exported on a workstation with network access to `https://api.fhorja.com`. Use the Stripe CLI to produce a valid signature header against the exact payload bytes.

Fixture file: `apps/web/test/fixtures/stripe/customer_subscription_created.smoke.json`
Fixture `event.id` = `evt_smoke_9f8e7d6_001` (a slice-22 dedicated test id, guaranteed not to collide with real Stripe traffic).

**Step A -- AC-1: first receipt returns 200 and creates the subscription row**

```bash
# 1. Compute valid signature with Stripe CLI against the exact fixture bytes
PAYLOAD=$(cat apps/web/test/fixtures/stripe/customer_subscription_created.smoke.json)
TIMESTAMP=$(date +%s)
SIG=$(printf '%s.%s' "$TIMESTAMP" "$PAYLOAD" \
  | openssl dgst -sha256 -hmac "$STRIPE_WEBHOOK_SECRET" -hex \
  | awk '{print $2}')

# 2. POST to production webhook endpoint
curl -sS -X POST https://api.fhorja.com/api/v1/webhooks/stripe \
  -H "Content-Type: application/json" \
  -H "Stripe-Signature: t=${TIMESTAMP},v1=${SIG}" \
  --data-binary "$PAYLOAD" \
  -w "\nHTTP %{http_code}\n"
```
Expected response: `HTTP 200`, body exactly `{"received":true,"deduped":false}`.
Expected DB side effect (verify within 30s):
```sql
SELECT stripe_event_id, status, created_at
FROM public.subscriptions
WHERE stripe_event_id = 'evt_smoke_9f8e7d6_001';
```
→ exactly 1 row, `status='active'`, `created_at` within 60s of smoke.

**Step B -- AC-2: replay same signed payload, idempotency holds**

```bash
# Re-send the EXACT same payload + EXACT same signature header (do not recompute)
curl -sS -X POST https://api.fhorja.com/api/v1/webhooks/stripe \
  -H "Content-Type: application/json" \
  -H "Stripe-Signature: t=${TIMESTAMP},v1=${SIG}" \
  --data-binary "$PAYLOAD" \
  -w "\nHTTP %{http_code}\n"
```
Expected response: `HTTP 200`, body exactly `{"received":true,"deduped":true}`.
Expected DB invariants (re-run both):
```sql
SELECT COUNT(*) FROM public.subscriptions WHERE stripe_event_id = 'evt_smoke_9f8e7d6_001';
-- expect 1 (UNCHANGED from Step A; no new row)

SELECT COUNT(*) FROM public.outbound_emails
WHERE email_kind = 'subscription_created'
  AND payload->>'stripe_event_id' = 'evt_smoke_9f8e7d6_001';
-- expect 1 (UNCHANGED from Step A; no duplicate billing email queued)
```

**Step C -- AC-3: unsigned request is rejected with 400**

```bash
# Same payload bytes, intentionally OMIT the Stripe-Signature header
curl -sS -X POST https://api.fhorja.com/api/v1/webhooks/stripe \
  -H "Content-Type: application/json" \
  --data-binary "$PAYLOAD" \
  -w "\nHTTP %{http_code}\n"
```
Expected response: `HTTP 400`, body exactly `{"error":"missing_signature"}`.
Expected DB invariant (negative):
```sql
SELECT COUNT(*) FROM public.stripe_webhook_events
WHERE event_id = 'evt_smoke_9f8e7d6_001_unsigned';
-- expect 0
```

**Step C' -- AC-3 variant: tampered signature is rejected with 400**

```bash
# Reuse $PAYLOAD but flip the last hex char of the signature
TAMPERED_SIG="${SIG%?}0"
curl -sS -X POST https://api.fhorja.com/api/v1/webhooks/stripe \
  -H "Content-Type: application/json" \
  -H "Stripe-Signature: t=${TIMESTAMP},v1=${TAMPERED_SIG}" \
  --data-binary "$PAYLOAD" \
  -w "\nHTTP %{http_code}\n"
```
Expected response: `HTTP 400`, body matches `{"error":"invalid_signature"}`.

**Post-smoke cleanup (idempotent):**
```sql
DELETE FROM public.outbound_emails WHERE payload->>'stripe_event_id' = 'evt_smoke_9f8e7d6_001';
DELETE FROM public.subscriptions WHERE stripe_event_id = 'evt_smoke_9f8e7d6_001';
DELETE FROM public.stripe_webhook_events WHERE event_id = 'evt_smoke_9f8e7d6_001';
```

---

## 5. Negative checks (prove the change DID NOT silently no-op)

**N1 -- Code path actually executed at least once on the new SHA:**
```
service:webhook-api route:/api/v1/webhooks/stripe deploy_sha:9f8e7d6 @evt.idempotency_check:executed
```
Over deploy window. Expected: ≥1 hit. ZERO hits ⇒ the idempotency middleware did not load on the new SHA ⇒ silent no-op deploy ⇒ rollback.

**N2 -- Pre-deploy code path no longer fires:**
```
service:webhook-api route:/api/v1/webhooks/stripe -deploy_sha:9f8e7d6 @evt.type:customer.subscription.created
```
Over `from=2026-06-05T14:35:00Z to=2026-06-05T15:30:00Z` (5 min grace for in-flight requests). Expected: ZERO hits. Non-zero ⇒ the deploy did not replace all instances ⇒ partial rollout ⇒ investigate before closing the slice.

**N3 -- APM throughput on the webhook route is NOT flatlined:**
Panel P2 (above) -- expected non-zero requests/min across the deploy window. A flatline at zero would mean Stripe is not reaching the new SHA (DNS, load balancer, or routing regression).

**N4 -- Sentry release `9f8e7d6` is registered and has activity:**
`https://sentry.io/fhorja/releases/9f8e7d6/?project=webhook-api`
Expected: release exists, has ≥1 session attributed. Missing release ⇒ source-maps / release tagging broken ⇒ Sentry blindspot during smoke window.

**N5 -- DB write path is exercised (the idempotency dedupe table grew):**
```sql
SELECT COUNT(*) AS events_recorded
FROM public.stripe_webhook_events
WHERE received_at >= '2026-06-05T14:30:00Z'
  AND received_at <  '2026-06-05T15:30:00Z';
```
Expected: ≥1 (the smoke event plus any real Stripe traffic). Zero ⇒ either no Stripe traffic (unlikely in a 1h prod window) or the dedupe writer is silently failing ⇒ investigate.

---

## 6. Rollback trigger checklist

No feature flag exists for this slice; rollback = redeploy previous SHA. Previous production SHA: capture from `vercel ls api.fhorja.com --prod` immediately after deploy and record below before smoke begins.

Previous SHA: `<RECORD_BEFORE_SMOKE>` (placeholder -- fill from `vercel ls` output, e.g. `f70c3f3`).

| # | Observation (trigger) | Page | Exact rollback action |
|---|---|---|---|
| R1 | `5xx rate on POST /api/v1/webhooks/stripe` exceeds 2% over any 5-minute window in panel P2 | Page `@bruno` (PagerDuty service: `webhook-api-prod`) | `vercel rollback <previous-deployment-id> --token=$VERCEL_TOKEN` against the `api.fhorja.com` project; confirm new active deployment SHA in `vercel ls --prod` |
| R2 | AC-2 DB invariant query returns ≥1 row (duplicate subscription rows for same `stripe_event_id`) | Page `@bruno` | Same `vercel rollback` as R1 AND execute: `DELETE FROM public.subscriptions s1 USING public.subscriptions s2 WHERE s1.stripe_event_id = s2.stripe_event_id AND s1.created_at > s2.created_at AND s1.created_at >= '2026-06-05T14:30:00Z';` (dedupe; keep oldest) -- run in a transaction with `BEGIN; ... ; ROLLBACK;` first to inspect affected rows |
| R3 | AC-2 outbound-emails invariant query returns ≥1 row (duplicate `subscription_created` email per recipient) | Page `@bruno` | Rollback per R1 AND `UPDATE public.outbound_emails SET status='canceled' WHERE id IN (SELECT id FROM (SELECT id, row_number() OVER (PARTITION BY recipient, payload->>'stripe_event_id' ORDER BY created_at) AS rn FROM public.outbound_emails WHERE email_kind='subscription_created' AND created_at >= '2026-06-05T14:30:00Z') t WHERE rn > 1);` (cancel duplicates pre-send) |
| R4 | AC-3 smoke returns HTTP 200 (or any 2xx) instead of 400 on unsigned request | Page `@bruno` IMMEDIATELY (security regression: signature bypass) | Rollback per R1; do NOT wait for a second confirmation -- unsigned-request acceptance is a CRITICAL signature-bypass class regression |
| R5 | Negative check N1 returns ZERO hits 15 minutes into smoke window (idempotency middleware never executed on new SHA) | Page `@bruno` | Rollback per R1; investigate build-extension regression that may have stripped the middleware from the bundle |
| R6 | Sentry release `9f8e7d6` shows ≥3 unresolved issues tagged to this route within smoke window | Page `@bruno` | Rollback per R1 if any issue is a 500-class crash; otherwise capture issue IDs and route to `direction-adjust` for a follow-up slice |

Escalation: if `@bruno` is unreachable, there is no secondary on-call (solo founder). In that case, rollback is the default action -- do not wait.

---

## 7. PROPOSED block for `SLICES/22_stripe_webhook_idempotency.md`

To be appended at end of slice file under a new `## Post-deploy checks` section:

```markdown
## Post-deploy checks

Deploy: production, sha `9f8e7d6`, ts `2026-06-05T14:30:00Z`. Smoke window 1h. On-call: `@bruno`. No feature flag.

Verification authored in `POST_DEPLOY_PLAN.md`. Summary:
- AC-1 (first-receipt 200): Datadog log query Q1 + DB invariant on `public.subscriptions` + curl smoke Step A.
- AC-2 (duplicate replay, no side effects): Datadog log query Q2 + DB invariants on `public.subscriptions` and `public.outbound_emails` + curl smoke Step B.
- AC-3 (unsigned/tampered → 400): Datadog log query Q3 + APM 4xx panel + curl smoke Steps C and C'.
- Negative checks N1-N5 guard against silent no-op deploy.
- Rollback triggers R1-R6 named with `vercel rollback` command and explicit observation thresholds.

Owner of execution: `@bruno`. Pass criterion for slice closure: all three ACs green, all five negative checks green, zero R-triggers fired.
```

---

## Command transcript

1. Loaded persona SKILL.md and confirmed Step 1-8 protocol.
2. Enumerated AC-1, AC-2, AC-3 from slice file; mapped each to ≥1 query-shaped signal (log, DB, smoke); added 5 negative checks; authored 6 rollback triggers with named human and exact `vercel rollback` command.
3. No feature-flag signal applicable (none on this slice); no multi-repo split (webhook-api is backend-only).
4. PROPOSED block authored for the slice file's `## Post-deploy checks` section; `POST_DEPLOY_PLAN.md` produced inline above as the persona report.

## Handoff

Recommended next command: `slice-closure` (to apply the `## Post-deploy checks` PROPOSED block to `SLICES/22_stripe_webhook_idempotency.md` once the on-call has executed the plan and all ACs are green).

Run now: `slice-closure`

If any negative check (N1-N5) or rollback trigger (R1-R6) fires during execution, do NOT run `slice-closure`; route to `direction-adjust` instead with the failing signal as evidence.
