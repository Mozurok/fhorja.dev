# Post-Deploy Verification Plan -- Slice 22: Stripe Webhook Idempotency

**Deploy SHA:** `9f8e7d6`
**Service:** `webhook-api`
**Route:** `POST /api/v1/webhooks/stripe`
**Deploy window:** `2026-06-05T14:30:00Z` → `2026-06-05T15:30:00Z` (1h smoke)
**On-call:** `@bruno`
**Feature flag:** none (cannot disable via flag; rollback = redeploy previous SHA)

---

## 1. Per-AC Signal Mapping

| AC | What we are proving | Primary signal | Secondary signal | Pass threshold |
|----|---------------------|----------------|------------------|----------------|
| AC-1 | First receipt of `customer.subscription.created` → 200 | Datadog Logs: `service:webhook-api route:/api/v1/webhooks/stripe status:200 stripe_event_type:customer.subscription.created deploy_sha:9f8e7d6` | Postgres: new row in `subscriptions` matching `stripe_subscription_id` from event payload | ≥1 log line with `status:200` AND row exists in `subscriptions` AND `webhook_events.processed_at IS NOT NULL` |
| AC-2 | Duplicate `event.id` → 200 but no re-execution | Datadog Logs: `service:webhook-api route:/api/v1/webhooks/stripe deploy_sha:9f8e7d6 idempotency_hit:true` AND `status:200` | Postgres: `SELECT COUNT(*) FROM subscriptions WHERE stripe_subscription_id = '<sub_id>'` must equal `1`; `SELECT COUNT(*) FROM outbound_emails WHERE template='subscription_created' AND stripe_event_id='<event_id>'` must equal `1` | Log line with `idempotency_hit:true status:200` AND both counts = 1 |
| AC-3 | Unsigned request → 400 | Datadog Logs: `service:webhook-api route:/api/v1/webhooks/stripe status:400 signature_verification:failed deploy_sha:9f8e7d6` | Sentry: no `SignatureVerificationError` raised to Sentry (these should be logged at WARN, not error) | Log line with `status:400 signature_verification:failed` AND zero Sentry events with `error.type:SignatureVerificationError` |

**Required structured log fields on every webhook log line (contract):**
`service`, `route`, `status`, `deploy_sha`, `stripe_event_id`, `stripe_event_type`, `idempotency_hit` (bool), `signature_verification` (`ok`|`failed`|`missing`), `duration_ms`, `trace_id`.

---

## 2. Datadog Log Queries (exact field syntax)

All queries scoped to the deploy window via the `from_ts` / `to_ts` parameters.

**Time window (UTC, ms epoch):**
- `from_ts=1780324200000` (2026-06-05T14:30:00Z)
- `to_ts=1780327800000` (2026-06-05T15:30:00Z)

### Q1 -- AC-1: First-receipt 200s
```
service:webhook-api env:production route:"/api/v1/webhooks/stripe" status:200 stripe_event_type:customer.subscription.created idempotency_hit:false deploy_sha:9f8e7d6
```
URL: `https://app.datadoghq.com/logs?query=service%3Awebhook-api%20env%3Aproduction%20route%3A%22%2Fapi%2Fv1%2Fwebhooks%2Fstripe%22%20status%3A200%20stripe_event_type%3Acustomer.subscription.created%20idempotency_hit%3Afalse%20deploy_sha%3A9f8e7d6&from_ts=1780324200000&to_ts=1780327800000&live=false`

### Q2 -- AC-2: Idempotency hits
```
service:webhook-api env:production route:"/api/v1/webhooks/stripe" status:200 idempotency_hit:true deploy_sha:9f8e7d6
```
URL: `https://app.datadoghq.com/logs?query=service%3Awebhook-api%20env%3Aproduction%20route%3A%22%2Fapi%2Fv1%2Fwebhooks%2Fstripe%22%20status%3A200%20idempotency_hit%3Atrue%20deploy_sha%3A9f8e7d6&from_ts=1780324200000&to_ts=1780327800000&live=false`

### Q3 -- AC-3: Signature rejections
```
service:webhook-api env:production route:"/api/v1/webhooks/stripe" status:400 signature_verification:(failed OR missing) deploy_sha:9f8e7d6
```
URL: `https://app.datadoghq.com/logs?query=service%3Awebhook-api%20env%3Aproduction%20route%3A%22%2Fapi%2Fv1%2Fwebhooks%2Fstripe%22%20status%3A400%20signature_verification%3A%28failed%20OR%20missing%29%20deploy_sha%3A9f8e7d6&from_ts=1780324200000&to_ts=1780327800000&live=false`

### Q4 -- Regression sentinel: 5xx on this route
```
service:webhook-api env:production route:"/api/v1/webhooks/stripe" status:>=500 deploy_sha:9f8e7d6
```
URL: `https://app.datadoghq.com/logs?query=service%3Awebhook-api%20env%3Aproduction%20route%3A%22%2Fapi%2Fv1%2Fwebhooks%2Fstripe%22%20status%3A%3E%3D500%20deploy_sha%3A9f8e7d6&from_ts=1780324200000&to_ts=1780327800000&live=false`
**Pass threshold:** zero results.

### Q5 -- Duplicate side-effect detector (would indicate AC-2 broken)
```
service:webhook-api env:production deploy_sha:9f8e7d6 (log_event:subscription_created OR log_event:billing_email_sent) @stripe_event_id:*
```
Group by `@stripe_event_id`, alert if any group `count > 1`.
URL: `https://app.datadoghq.com/logs/analytics?query=service%3Awebhook-api%20env%3Aproduction%20deploy_sha%3A9f8e7d6%20%28log_event%3Asubscription_created%20OR%20log_event%3Abilling_email_sent%29&agg_m=count&agg_t=count&agg_q=%40stripe_event_id&from_ts=1780324200000&to_ts=1780327800000`

### Q6 -- Sentry filter (unexpected exceptions from this deploy)
Filter string (paste into Sentry issues search):
```
project:fhorja environment:production release:9f8e7d6 url:"*/api/v1/webhooks/stripe*" age:-1h
```
URL: `https://sentry.io/organizations/fhorja/issues/?project=fhorja&query=environment%3Aproduction+release%3A9f8e7d6+url%3A%22%2Fapi%2Fv1%2Fwebhooks%2Fstripe%2A%22&statsPeriod=1h&start=2026-06-05T14:30:00&end=2026-06-05T15:30:00`
**Pass threshold:** zero unresolved issues with `level:error` or `level:fatal`. Note: `SignatureVerificationError` should not appear (it's expected behavior, logged at WARN only).

---

## 3. Datadog Dashboards / APM Panels

All panel URLs pinned to the deploy window `from_ts=1780324200000&to_ts=1780327800000`.

### P1 -- APM service overview for `webhook-api`
URL: `https://app.datadoghq.com/apm/services/webhook-api?env=production&start=1780324200000&end=1780327800000&paused=true`
**Inspect:** request rate, p50/p95/p99 latency, error rate. Filter by `resource_name:POST /api/v1/webhooks/stripe`.
**Pass threshold:** error rate <1%, p95 < 500ms (idempotency lookup is a single indexed read, must not regress latency).

### P2 -- Endpoint resource view
URL: `https://app.datadoghq.com/apm/services/webhook-api/resources/POST_%2Fapi%2Fv1%2Fwebhooks%2Fstripe?env=production&start=1780324200000&end=1780327800000`
**Pass threshold:** hit count > 0 (Stripe is sending events), 4xx count matches signature-failure expectation, zero 5xx.

### P3 -- Postgres query latency for idempotency table
URL: `https://app.datadoghq.com/apm/services/postgres-fhorja?env=production&start=1780324200000&end=1780327800000&resource=SELECT_webhook_events`
**Pass threshold:** p95 < 20ms for `SELECT FROM webhook_events WHERE stripe_event_id = $1`. If higher, missing index -- block deploy promotion.

### P4 -- Trace search (full path of a duplicate)
URL: `https://app.datadoghq.com/apm/traces?query=service%3Awebhook-api%20resource_name%3A%22POST%20%2Fapi%2Fv1%2Fwebhooks%2Fstripe%22%20%40idempotency_hit%3Atrue&start=1780324200000&end=1780327800000&paused=true`
Open one trace; verify spans show: signature verification → idempotency check (HIT) → early return. No spans for `db.insert subscriptions` or `email.send`.

---

## 4. Smoke-Test Walkthrough (exact commands)

Test happens against production using a Stripe test-mode event replayed via Stripe CLI, OR a directly-crafted signed payload. The webhook secret is `whsec_test_9f8e7d6_smoke` (stored in 1Password item `stripe-webhook-secret-prod`).

### Step 0 -- Prep
```bash
export STRIPE_WEBHOOK_SECRET="$(op read 'op://Engineering/stripe-webhook-secret-prod/credential')"
export WEBHOOK_URL="https://api.fhorja.com/api/v1/webhooks/stripe"
export EVENT_ID="evt_smoke_${RANDOM}_$(date +%s)"
export SUB_ID="sub_smoke_${RANDOM}"
```

### Step 1 -- AC-1: First receipt (expect 200, side effects fire)

Fixture: `tests/fixtures/stripe/customer_subscription_created.json` rendered with `event_id=$EVENT_ID`, `subscription_id=$SUB_ID`.

```bash
PAYLOAD=$(cat <<JSON
{"id":"$EVENT_ID","object":"event","type":"customer.subscription.created","data":{"object":{"id":"$SUB_ID","object":"subscription","customer":"cus_smoke_test","status":"active","items":{"data":[{"price":{"id":"price_smoke_basic"}}]}}},"created":$(date +%s),"livemode":false,"api_version":"2024-06-20"}
JSON
)
TIMESTAMP=$(date +%s)
SIGNED_PAYLOAD="${TIMESTAMP}.${PAYLOAD}"
SIGNATURE=$(printf '%s' "$SIGNED_PAYLOAD" | openssl dgst -sha256 -hmac "${STRIPE_WEBHOOK_SECRET#whsec_}" -hex | awk '{print $2}')

curl -sS -X POST "$WEBHOOK_URL" \
  -H "Content-Type: application/json" \
  -H "Stripe-Signature: t=${TIMESTAMP},v1=${SIGNATURE}" \
  -d "$PAYLOAD" \
  -w "\nHTTP_STATUS=%{http_code}\n"
```

**Exact assertions:**
- `HTTP_STATUS=200` in curl output.
- Postgres: `SELECT COUNT(*) FROM webhook_events WHERE stripe_event_id = '<$EVENT_ID>';` returns `1`.
- Postgres: `SELECT COUNT(*) FROM subscriptions WHERE stripe_subscription_id = '<$SUB_ID>';` returns `1`.
- Postgres: `SELECT COUNT(*) FROM outbound_emails WHERE template='subscription_created' AND stripe_event_id='<$EVENT_ID>';` returns `1`.
- Datadog Q1 returns ≥1 matching log line with `stripe_event_id:<$EVENT_ID>`.

### Step 2 -- AC-2: Replay same event (expect 200, NO new side effects)

Re-run the exact same `curl` from Step 1 (same `$EVENT_ID`, same payload, same signature).

**Exact assertions:**
- `HTTP_STATUS=200`.
- Postgres: same three `COUNT(*)` queries above still return `1` (NOT `2`).
- Datadog Q2 returns ≥1 log with `idempotency_hit:true` and `stripe_event_id:<$EVENT_ID>`.
- Datadog trace (P4) for the second request shows NO `db.insert subscriptions` span and NO `email.send` span.

### Step 3 -- AC-3: Unsigned request (expect 400)

```bash
curl -sS -X POST "$WEBHOOK_URL" \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD" \
  -w "\nHTTP_STATUS=%{http_code}\n"
```
(Note: no `Stripe-Signature` header.)

**Exact assertions:**
- `HTTP_STATUS=400`.
- Datadog Q3 returns ≥1 log with `signature_verification:missing`.
- Sentry (Q6): no new issues raised.

### Step 4 -- AC-3b: Tampered signature (expect 400)

```bash
curl -sS -X POST "$WEBHOOK_URL" \
  -H "Content-Type: application/json" \
  -H "Stripe-Signature: t=${TIMESTAMP},v1=deadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef" \
  -d "$PAYLOAD" \
  -w "\nHTTP_STATUS=%{http_code}\n"
```

**Exact assertions:**
- `HTTP_STATUS=400`.
- Datadog Q3 returns matching log with `signature_verification:failed`.

### Step 5 -- Cleanup
```sql
DELETE FROM outbound_emails WHERE stripe_event_id LIKE 'evt_smoke_%';
DELETE FROM subscriptions WHERE stripe_subscription_id LIKE 'sub_smoke_%';
DELETE FROM webhook_events WHERE stripe_event_id LIKE 'evt_smoke_%';
```

---

## 5. Negative Check

**Goal:** prove the system actually rejects bad input AND that idempotency is keyed correctly (not too aggressive, not too loose).

### N1 -- Different `event.id`, same subscription data → MUST process (not idempotent on payload, only on `event.id`)
Re-run Step 1 with a fresh `$EVENT_ID` but the same `$SUB_ID` from Step 1.
**Expected:** `200`, AND `subscriptions` count for `$SUB_ID` is now `2` if our upsert allows it, OR a constraint-violation error path is logged. Either way: `idempotency_hit:false`, and the request did NOT silently dedupe on subscription id. (If business rule is "one sub per customer," this surfaces it now.)

### N2 -- Replay with stale timestamp (>5 min old) → MUST 400
```bash
OLD_TIMESTAMP=$(( $(date +%s) - 600 ))
# re-sign with $OLD_TIMESTAMP and POST
```
**Expected:** `400`, log `signature_verification:failed` with reason `timestamp_outside_tolerance`. Confirms Stripe's replay-attack window is enforced.

### N3 -- Wrong event type → MUST 200 (acknowledged, no-op)
POST a signed `payment_intent.created` event.
**Expected:** `200`, log with `stripe_event_type:payment_intent.created handler:no_op`. Confirms we acknowledge events we don't handle (Stripe requirement) without erroring.

---

## 6. Rollback Trigger Checklist

Rollback = redeploy SHA `<PREVIOUS_SHA>` (fill in from `git log --oneline -2 main` before deploy). No feature flag available -- rollback is the only mitigation.

**Trigger rollback IMMEDIATELY if ANY of the following is true within the 1h smoke window:**

- [ ] **R1 -- Duplicate side effects detected.** Q5 returns any `stripe_event_id` group with `count > 1` for `log_event:subscription_created` or `log_event:billing_email_sent`. Indicates AC-2 broken; risk of duplicate charges/emails to real customers. Page `@bruno`.
- [ ] **R2 -- 5xx rate on the route > 1% over any 5-min window.** Q4 returns >0, OR P2 shows error rate spike. Stripe will retry failed deliveries up to 3 days, so backlog will accumulate.
- [ ] **R3 -- Signature verification regression.** Q3 returns zero results across the whole window AND Q1 returns >0 results, i.e., we are accepting events but never rejecting any. Implies AC-3 broken; security regression.
- [ ] **R4 -- p95 latency on `POST /api/v1/webhooks/stripe` > 5s.** P2 panel. Stripe times out at ~30s but our SLO is 1s p95; 5s indicates the idempotency lookup is unindexed or there is lock contention on `webhook_events`.
- [ ] **R5 -- Postgres `webhook_events` write failures.** Datadog query `service:webhook-api env:production deploy_sha:9f8e7d6 @log_event:webhook_events_insert_failed` returns >0. Means we are processing without recording, breaking idempotency for future replays.
- [ ] **R6 -- Sentry issue with `level:fatal` matching Q6 filter.** Any unresolved fatal in this release.
- [ ] **R7 -- Stripe Dashboard webhook delivery success rate < 95%** at `https://dashboard.stripe.com/webhooks` for the endpoint, 1h view. External truth check.

**Rollback procedure:**
1. `@bruno` acknowledges in `#incidents`.
2. Identify previous deploy SHA: `git log --oneline 9f8e7d6^ -1`.
3. Trigger redeploy via CI: `gh workflow run deploy.yml -f sha=<previous_sha> -f env=production`.
4. Re-verify Q1/Q3/P2 against the rollback's deploy window.
5. File incident note in `projects/fhorja/incidents/2026-06-05_slice22_rollback.md` with the failing checklist item and links to the matching log query results.
6. Keep slice 22 PR open; do NOT close.

**No-action threshold (do NOT roll back, but flag for `@bruno`):**
- Sub-1% 4xx rate with `signature_verification:failed` from unknown IPs → likely scanner traffic, log and continue.
- Single Sentry warning-level issue with <5 occurrences → triage post-window.
