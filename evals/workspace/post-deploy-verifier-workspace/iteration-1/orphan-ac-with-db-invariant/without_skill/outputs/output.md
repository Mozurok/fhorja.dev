# Post-Deploy Verification Plan -- Slice 14: Subscription Uniqueness Invariant

**Deploy:** production, sha=`a1b2c3d`, deployed 2026-06-05T10:00:00Z
**Verification window:** T+0 (smoke), T+1h (early signal), T+24h (SLO close-out)
**Owner on-call:** `@bruno`
**Feature flag:** none (unconditional ship -- rollback = revert + redeploy)

---

## 1. Per-AC signal mapping

Every AC maps to at least one concrete signal. No AC is orphaned.

| AC | Claim | Primary signal | Secondary / corroborating signal | Window |
|----|-------|---------------|----------------------------------|--------|
| AC-1 | `POST /api/v1/subscriptions` returns 409 when caller has active sub | Datadog Logs query on API access logs (status:409 + route filter) | Synthetic smoke test (curl, see §2.1) | T+0, T+1h |
| AC-2 | `/account/subscriptions` shows error banner instead of CTA | Manual browser smoke (see §2.2) + Sentry frontend events for banner render | Datadog RUM page-view + custom event `subscription.banner.shown` | T+0 |
| AC-3 | Stripe webhook `customer.subscription.created` is idempotent | Datadog Logs query on webhook handler (see §2.3) -- duplicate events should log `webhook.duplicate.ignored` | SQL row-count check before/after replay (see §2.3) | T+0 (replay test), T+24h (passive) |
| AC-4 | DB invariant: no user has >1 row in `subscriptions` with `status='active'` | **SQL invariant query against Postgres** (see §2.4) -- the load-bearing check, no log equivalent exists | Postgres unique partial index `subscriptions_one_active_per_user_idx` existence check | T+0, T+1h, T+24h (cron) |
| AC-5 | Datadog SLO `subscription_creation_p99_latency_ms` did not regress (<800ms p99 over 24h) | Datadog SLO dashboard widget (URL in §2.5) | APM service latency comparison vs prior 24h baseline | T+24h |

---

## 2. Exact queries, URLs, and smoke inputs

### 2.1 AC-1 -- 409 Conflict on duplicate subscription create

**Datadog Logs query (paste into Datadog Logs explorer):**

```
service:fhorja-api env:production @http.url_details.path:"/api/v1/subscriptions" @http.method:POST @http.status_code:409
```

Time range: `now-1h` initially, then `now-24h` at T+24h.

Expected: non-zero count once real duplicate-create traffic arrives. Zero is acceptable in the first 15 minutes only if no organic duplicate attempts have happened -- verify with the synthetic call below.

**Synthetic smoke test (run from on-call laptop):**

```bash
# Create a test user with an existing active subscription via fixture
# (use staging-mirror user id known to have status='active')
USER_TOKEN="<token for user_id=00000000-0000-0000-0000-000000000001>"

# First call should 409 (the user already has an active sub)
curl -i -X POST https://api.fhorja.com/api/v1/subscriptions \
  -H "Authorization: Bearer $USER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"plan_id":"plan_pro_monthly"}'

# Expect: HTTP/1.1 409 Conflict
# Expect body: {"error":"already_subscribed","message":"..."}
```

**Pass criterion:** response code is exactly `409`, body contains `already_subscribed`.
**Fail criterion:** any 2xx response, or 5xx.

---

### 2.2 AC-2 -- Subscription-list page banner

**Manual smoke (on-call performs at T+0):**

1. Log in as the same fixture user (`user_id=00000000-0000-0000-0000-000000000001`) at https://app.fhorja.com/account/subscriptions
2. Confirm visible banner copy contains: *"You already have an active subscription"*
3. Confirm the "Start a subscription" CTA is **not** rendered
4. Take screenshot, attach to deploy ticket

**Datadog Logs corroboration (frontend telemetry):**

```
service:fhorja-web env:production @event.name:"subscription.banner.shown" @user.has_active_subscription:true
```

**Sentry check:** https://sentry.io/organizations/fhorja/issues/?project=fhorja-web&query=is%3Aunresolved+url%3A%22%2Faccount%2Fsubscriptions%22&statsPeriod=24h

Expected: no new unresolved issues on `/account/subscriptions` route since deploy time `2026-06-05T10:00:00Z`.

**Pass criterion:** banner visible, CTA hidden, no new Sentry frontend issues on that route.
**Fail criterion:** CTA still rendered, banner absent, or new TypeError/render errors.

---

### 2.3 AC-3 -- Webhook idempotency

**Datadog Logs query (verify duplicate-detection log line exists):**

```
service:fhorja-api env:production @logger.name:"stripe.webhook" @event.type:"customer.subscription.created" @webhook.outcome:"duplicate_ignored"
```

**Active idempotency probe (run once at T+0):**

```bash
# Replay a known webhook payload twice. Use the Stripe CLI against the
# production webhook endpoint with a fixed event id.
EVENT_ID="evt_test_idempotency_slice14"

# First delivery -- should insert one row
stripe events resend $EVENT_ID --webhook-endpoint we_prod_subscription_handler

# Second delivery -- should be ignored (no new row)
stripe events resend $EVENT_ID --webhook-endpoint we_prod_subscription_handler
```

**Verify with SQL (run before and after the second replay):**

```sql
-- Count active subscription rows for the test customer before / after the replay
SELECT COUNT(*) AS active_rows
FROM public.subscriptions
WHERE stripe_customer_id = 'cus_test_idempotency_slice14'
  AND status = 'active';
-- Pass: same count before and after the second replay (no increase)
```

**Pass criterion:** row count unchanged after the duplicate webhook; Datadog log shows `duplicate_ignored`.
**Fail criterion:** row count increments on the second delivery, or no idempotency log line is emitted.

---

### 2.4 AC-4 -- DB INVARIANT (load-bearing) -- SQL check

**This claim has no log or dashboard equivalent. It must be verified directly in Postgres.**

Connection: `db.fhorja.supabase.co` (Supabase project `fhorja-prod`), use the `app_readonly` role from the Supabase SQL editor or `psql` with the production read-only DSN stored in 1Password (`Supabase / fhorja-prod / readonly DSN`).

**Primary invariant query:**

```sql
-- AC-4: No user may have more than one row in subscriptions with status='active'.
-- Pass: zero rows returned. Any row returned = invariant violated = ROLLBACK trigger.
SELECT user_id, COUNT(*) AS active_count
FROM public.subscriptions
WHERE status = 'active'
GROUP BY user_id
HAVING COUNT(*) > 1
ORDER BY active_count DESC;
```

**Confirm enforcing index is present (defense in depth):**

```sql
-- The slice should have shipped a unique partial index. Verify it exists and is valid.
SELECT
  i.indexname,
  i.indexdef,
  ix.indisvalid,
  ix.indisready
FROM pg_indexes i
JOIN pg_class c   ON c.relname = i.indexname
JOIN pg_index ix  ON ix.indexrelid = c.oid
WHERE i.schemaname = 'public'
  AND i.tablename  = 'subscriptions'
  AND i.indexdef ILIKE '%UNIQUE%'
  AND i.indexdef ILIKE '%status%active%';
-- Pass: exactly one row, indisvalid=t, indisready=t.
```

**Cadence:**

- T+0 (immediately after deploy): run both queries from Supabase SQL editor, paste result into deploy ticket.
- T+1h: re-run primary invariant query.
- T+24h: re-run primary invariant query.
- Ongoing: schedule the primary query as a Supabase scheduled function (cron `*/15 * * * *`) for the first 7 days; alert `@bruno` via Slack webhook if it ever returns a non-empty result.

**Pass criterion:** primary query returns zero rows at every checkpoint, enforcing index is valid.
**Fail criterion:** any row returned by the primary query → immediate rollback trigger (see §4).

---

### 2.5 AC-5 -- Latency SLO did not regress

**Datadog SLO dashboard URL:**

```
https://app.datadoghq.com/slo?slo_id=subscription_creation_p99_latency_ms&from_ts=1717495200000&to_ts=1717581600000
```

(Adjust `to_ts` at T+24h to the 24h-post-deploy timestamp.)

**Datadog APM metric query (paste in Metrics Explorer):**

```
p99:trace.http.request.duration{service:fhorja-api,resource_name:POST_/api/v1/subscriptions,env:production}.rollup(avg, 3600)
```

**Comparison query (24h before vs 24h after deploy):**

```
p99:trace.http.request.duration{service:fhorja-api,resource_name:POST_/api/v1/subscriptions,env:production}
- hour_before(p99:trace.http.request.duration{service:fhorja-api,resource_name:POST_/api/v1/subscriptions,env:production})
```

**Pass criterion:** p99 < 800ms across the full 24h window; no SLO burn-rate alert fired.
**Fail criterion:** p99 ≥ 800ms for any rolling 1h window, or SLO burn rate > 1.0 for >15 minutes.

---

## 3. Negative checks

These confirm we haven't broken adjacent behavior or masked real failures.

| # | Check | How | Pass criterion |
|---|-------|-----|----------------|
| N-1 | First-time subscribers still succeed (we didn't blanket-reject everyone) | Create a user with zero subscription rows, call `POST /api/v1/subscriptions` | Returns `201 Created`, row appears with `status='active'` |
| N-2 | Existing active subscribers' page load doesn't 500 | Datadog Logs: `service:fhorja-web env:production @http.url_details.path:"/account/subscriptions" @http.status_code:[500 TO 599]` | Zero results since deploy time |
| N-3 | The 409 is not being silently swallowed (i.e. logged but client gets 200) | `service:fhorja-api env:production @http.url_details.path:"/api/v1/subscriptions" @http.method:POST @http.status_code:200 @user.had_active_subscription:true` | Zero results -- a 200 to a user who already had active = bug |
| N-4 | Webhook handler doesn't 500 on duplicates (idempotency != crash) | `service:fhorja-api @logger.name:"stripe.webhook" status:error` over T+0 to T+24h | Zero new errors attributable to slice |
| N-5 | No spike in subscription-create error rate masking the AC-1 path | APM: error_rate on `POST /api/v1/subscriptions` resource | <1% errors excluding the intended 409s |

---

## 4. Rollback trigger checklist

**Single named on-call:** `@bruno` (oncall@example.com)

### Triggers (any one fires → rollback)

- [ ] **R-1 (AC-4 invariant violation):** the primary SQL in §2.4 returns ≥1 row at any checkpoint. **This is the highest-severity trigger** -- duplicate-active rows mean billing / entitlement risk.
- [ ] **R-2 (AC-1 regression):** Datadog query in §2.1 shows 0 results AND smoke curl returns 2xx for a user known to have an active subscription (i.e. the 409 path is dead).
- [ ] **R-3 (AC-3 webhook regression):** §2.3 SQL row count increments after a duplicate webhook replay.
- [ ] **R-4 (AC-5 SLO regression):** p99 ≥ 800ms sustained > 1 rolling hour, or SLO burn rate > 1.0 for >15 min.
- [ ] **R-5 (Sentry surge):** new unresolved Sentry issue on `/api/v1/subscriptions` or `/account/subscriptions` with > 25 events in 1h.
- [ ] **R-6 (N-1 negative check fail):** first-time subscribers cannot create -- slice has over-rejected.

### Rollback commands (run by `@bruno`)

```bash
# 1. Acknowledge / page yourself in PagerDuty (so the incident is tracked)
pd-cli incident create \
  --title "Slice 14 rollback: subscription uniqueness regression" \
  --service fhorja-api \
  --urgency high \
  --assignee bruno

# 2. Revert the deploy commit on main
git fetch origin
git checkout main
git revert --no-edit a1b2c3d
git push origin main

# 3. Trigger production redeploy (Vercel for web, Railway for API -- adjust as appropriate)
vercel --prod                              # apps/web
railway up --service fhorja-api --env prod # API

# 4. If R-1 fired (invariant violated): also run reconciliation in Supabase SQL editor
#    BEFORE letting any new subscription writes through.
psql "$SUPABASE_PROD_DSN" -f scripts/reconcile_duplicate_active_subscriptions.sql

# 5. Post in #fhorja-ops: "Slice 14 rolled back at <ts>; trigger=<R-x>; invariant query result attached."
```

### Post-rollback verification (re-run the same checks)

- [ ] §2.4 primary invariant SQL returns zero rows.
- [ ] §2.1 Datadog query shows 409s have stopped (because the new code is gone -- confirms rollback landed).
- [ ] §2.5 p99 back under 800ms within 1h.
- [ ] Sentry shows no new issues post-rollback.
- [ ] `@bruno` writes incident note in deploy ticket linking the rollback commit SHA.

---

## 5. Verification schedule summary

| Time | Action | Owner |
|------|--------|-------|
| T+0 (10:00 UTC) | §2.1 smoke curl, §2.2 manual browser, §2.3 webhook replay, §2.4 SQL invariant, §2.4 index check | `@bruno` |
| T+1h (11:00 UTC) | §2.1 Datadog log query, §2.4 SQL invariant re-run, scan Sentry | `@bruno` |
| T+24h (2026-06-06 10:00 UTC) | §2.4 SQL invariant final, §2.5 SLO dashboard, §3 negative checks N-1..N-5 | `@bruno` |
| T+24h..T+7d | Scheduled 15-min cron of §2.4 invariant query with Slack alert | Automated → `@bruno` |

---

## 6. Sign-off

Slice 14 is considered verified when:

- All five AC checks above are green at T+24h.
- All five negative checks (N-1..N-5) are green.
- No rollback trigger fired during the 24h window.
- `@bruno` records the final §2.4 SQL result (expected: zero rows) in the deploy ticket.
