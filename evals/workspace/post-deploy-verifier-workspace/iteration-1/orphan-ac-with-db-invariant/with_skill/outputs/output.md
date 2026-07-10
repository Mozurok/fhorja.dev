# POST_DEPLOY_PLAN.md -- Slice 14: Subscription uniqueness invariant

Deploy under verification:
- Environment: `production`
- Git SHA: `a1b2c3d`
- Deploy timestamp (UTC): `2026-06-05T10:00:00Z`
- Verification window: `[2026-06-05T10:00:00Z, 2026-06-06T10:00:00Z]` (24h, bounded by AC-5 SLO window)
- Feature flag: none (ships unconditionally -- no flag-flip rollback path; rollback = deploy revert)
- Named on-call human: `@bruno`

Observability stack inventory:
- Logs: Datadog Logs (`https://app.datadoghq.com/logs`)
- APM / dashboards: Datadog APM (`https://app.datadoghq.com/apm`)
- Errors: Sentry (`https://sentry.io/organizations/fhorja/issues/`)
- Database: Postgres on Supabase (`db.fhorja.supabase.co`, prod project)
- Feature flags: NONE

---

## Step 1 -- Acceptance criteria enumeration (zero orphan ACs)

Every AC in `SLICES/14_subscription_uniqueness.md` is enumerated below as a separately verifiable claim. Every AC maps to at least one signal in Step 3.

- AC-1: `POST /api/v1/subscriptions` returns HTTP 409 Conflict when the caller already has an active subscription (was 200 before this slice).
- AC-2: `/account/subscriptions` page renders the banner text "You already have an active subscription" instead of the empty-state "Start a subscription" CTA when the user has an active row.
- AC-3: Stripe webhook `customer.subscription.created` is idempotent -- a duplicate delivery does NOT create a second active row.
- AC-4: DB INVARIANT -- no user has more than one row in `subscriptions` where `status = 'active'`. (Load-bearing claim.)
- AC-5: Datadog SLO `subscription_creation_p99_latency_ms` does not regress: p99 stays under 800ms over the 24h post-deploy window.

---

## Step 3 -- Per-AC signal mapping table (one signal class per AC; orphan ACs forbidden)

| AC   | Claim (short)                                       | Signal class                          | Exact query / URL / inputs                                                                                                                                                                                                                                                                                                                                                                                                                                              | Expected result                                                                                                                       | Owner-of-check |
|------|-----------------------------------------------------|---------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------|----------------|
| AC-1 | API returns 409 on duplicate create                 | Datadog log query + smoke test        | Log query: `service:subscriptions-api env:production deploy_sha:a1b2c3d route:"/api/v1/subscriptions" method:POST @http.status_code:409` over `2026-06-05T10:00:00Z..2026-06-06T10:00:00Z`. Smoke test: see Step 4 §A.                                                                                                                                                                                                                                                  | ≥1 hit on the log query within 24h; smoke test returns `409 Conflict` with body `{"error":"already_subscribed"}`.                     | `@bruno`       |
| AC-2 | UI banner renders for users with active sub         | Smoke test (browser) + Sentry         | Smoke test: see Step 4 §B (login as `qa+active-sub@fhorja.dev`, visit `/account/subscriptions`, assert visible text "You already have an active subscription"). Sentry query: `https://sentry.io/organizations/fhorja/issues/?project=frontend&environment=production&query=release%3Aa1b2c3d+url%3A%22%2Faccount%2Fsubscriptions%22&statsPeriod=24h`.                                                                                                                  | Banner text present in DOM; Sentry shows zero new client-side errors on `/account/subscriptions` post-deploy.                         | `@bruno`       |
| AC-3 | Stripe webhook idempotent on duplicate delivery     | Datadog log query + smoke test (curl) | Log query: `service:webhooks-api env:production deploy_sha:a1b2c3d route:"/api/v1/webhooks/stripe" @stripe.event_type:"customer.subscription.created" @idempotency.outcome:("inserted" OR "deduped")` over deploy window. Smoke test: see Step 4 §C (replay the same `evt_test_*` twice via Stripe CLI to staging-mirrored prod endpoint or use `stripe events resend evt_<id> --live`).                                                                                  | Replay yields one `inserted` then one `deduped`; no second `INSERT` recorded; DB count for that customer's active rows = 1.           | `@bruno`       |
| AC-4 | DB INVARIANT: ≤1 active row per user                | **SQL invariant query (load-bearing)**| See Step 4 §D. Run against `db.fhorja.supabase.co` (prod, read replica) as role `verifier_ro`.                                                                                                                                                                                                                                                                                                                                                                          | Query returns **zero rows**. Any row returned = AC-4 FAILED = rollback trigger (see Step 6).                                          | `@bruno`       |
| AC-5 | p99 latency does not regress (<800ms over 24h)      | Datadog APM dashboard panel           | Panel URL: `https://app.datadoghq.com/apm/services/subscriptions-api/operations/POST_/api/v1/subscriptions?env=production&start=1748080800000&end=1748167200000` (24h window). SLO board: `https://app.datadoghq.com/slo?slo_id=subscription_creation_p99_latency_ms`.                                                                                                                                                                                                  | p99 line stays below the 800ms threshold line for the entire 24h window; SLO board shows `Healthy` status, error budget not consumed. | `@bruno`       |

Coverage check: AC-1 → row 1; AC-2 → row 2; AC-3 → row 3; AC-4 → row 4; AC-5 → row 5. Zero orphan ACs.

---

## Step 4 -- Signals at query-shaped resolution

### §A. AC-1 smoke test -- API 409 on duplicate create

1. Acquire a session token for the seeded prod QA user that already has an active subscription:
   - Email: `qa+active-sub@fhorja.dev`
   - Password: stored in 1Password vault `fhorja-prod-qa` → item `qa+active-sub`
   - Login route: `POST https://api.fhorja.com/api/v1/auth/login` with JSON `{"email":"qa+active-sub@fhorja.dev","password":"<from vault>"}` → returns `{ "access_token": "..." }`.
2. Attempt to create a second subscription:
   ```bash
   curl -i -X POST https://api.fhorja.com/api/v1/subscriptions \
     -H "Authorization: Bearer <access_token>" \
     -H "Content-Type: application/json" \
     -d '{"plan_id":"plan_basic_monthly","payment_method_id":"pm_card_visa"}'
   ```
3. Expected response:
   - Status: `HTTP/1.1 409 Conflict`
   - Body: `{"error":"already_subscribed","existing_subscription_id":"sub_<uuid>"}`
   - Header: `x-request-id: <uuid>` (record this id; paste into Datadog Logs as `@http.request_id:<uuid>` to confirm the request traversed `deploy_sha:a1b2c3d`).

### §B. AC-2 smoke test -- UI banner

1. Browser: Chromium (latest), incognito.
2. Navigate to `https://app.fhorja.com/login`.
3. Login as `qa+active-sub@fhorja.dev` (vault password).
4. Navigate to `https://app.fhorja.com/account/subscriptions`.
5. Expected DOM:
   - Visible text node containing exactly: `You already have an active subscription`
   - CSS selector `[data-testid="already-subscribed-banner"]` exists and is visible.
   - CSS selector `[data-testid="start-subscription-cta"]` does **not** exist (pre-slice empty-state CTA is gone for this user).
6. Sentry cross-check: open the Sentry URL in the AC-2 row above; confirm zero new unresolved issues tagged `release:a1b2c3d` on `url:"/account/subscriptions"`.

### §C. AC-3 smoke test -- Stripe webhook idempotency

1. Identify a recent real `customer.subscription.created` event for the QA customer:
   - Stripe Dashboard → Developers → Events → filter `type=customer.subscription.created customer=cus_QA_active_sub`.
   - Capture the event id, e.g. `evt_1QabcDEFghiJKL`.
2. Resend the event twice via Stripe CLI against the production webhook:
   ```bash
   stripe events resend evt_1QabcDEFghiJKL --live
   stripe events resend evt_1QabcDEFghiJKL --live
   ```
3. Datadog log query (paste into `https://app.datadoghq.com/logs`):
   ```
   service:webhooks-api env:production deploy_sha:a1b2c3d
   route:"/api/v1/webhooks/stripe"
   @stripe.event_id:"evt_1QabcDEFghiJKL"
   ```
   Time range: `2026-06-05T10:00:00Z..2026-06-06T10:00:00Z`.
4. Expected log shape:
   - Two log lines for the same `@stripe.event_id`.
   - First line: `@idempotency.outcome:"inserted"` + `@subscription.id:"sub_<uuid>"`.
   - Second line: `@idempotency.outcome:"deduped"` + same `@subscription.id:"sub_<uuid>"`.
   - Both return HTTP `200` to Stripe (so Stripe does not retry indefinitely).
5. DB cross-check (read replica):
   ```sql
   SELECT COUNT(*) AS active_rows
   FROM subscriptions
   WHERE user_id = (SELECT user_id FROM stripe_customers WHERE stripe_customer_id = 'cus_QA_active_sub')
     AND status = 'active';
   ```
   Expected: `active_rows = 1`.

### §D. AC-4 -- DB INVARIANT SQL query (load-bearing, no log/dashboard equivalent)

Run on `db.fhorja.supabase.co` (prod), role `verifier_ro`, via Supabase SQL editor or `psql`:

```sql
-- AC-4 invariant: no user may have more than one active subscription row.
-- Expected output: ZERO rows. Any row returned = invariant violated = rollback trigger.
SELECT
  user_id,
  COUNT(*)                          AS active_row_count,
  array_agg(id ORDER BY created_at) AS subscription_ids,
  array_agg(created_at ORDER BY created_at) AS created_ats
FROM public.subscriptions
WHERE status = 'active'
GROUP BY user_id
HAVING COUNT(*) > 1;
```

Also confirm the supporting partial unique index exists (this is what enforces the invariant at write time):

```sql
SELECT indexname, indexdef
FROM pg_indexes
WHERE schemaname = 'public'
  AND tablename  = 'subscriptions'
  AND indexdef ILIKE '%status%active%';
-- Expected: one row resembling
--   indexname: subscriptions_one_active_per_user
--   indexdef : CREATE UNIQUE INDEX subscriptions_one_active_per_user
--              ON public.subscriptions (user_id) WHERE (status = 'active');
```

Re-run the invariant query at:
- T0 = deploy + 5 min
- T0 + 1h
- T0 + 24h (end of verification window)

All three runs must return zero rows. If any run returns ≥1 row, halt and trigger rollback (Step 6).

### §E. AC-5 -- Datadog APM dashboard panel

- Service panel: `https://app.datadoghq.com/apm/services/subscriptions-api/operations/POST_/api/v1/subscriptions?env=production&start=1748080800000&end=1748167200000`
  - `start=1748080800000` = `2026-06-05T10:00:00Z`
  - `end=1748167200000`   = `2026-06-06T10:00:00Z`
- Scoped tags: `env:production service:subscriptions-api resource_name:"POST /api/v1/subscriptions"`.
- SLO board: `https://app.datadoghq.com/slo?slo_id=subscription_creation_p99_latency_ms`.
- Expected: p99 line below the 800ms threshold line for every 5-minute bucket in the window; SLO budget not consumed (Healthy).
- Baseline reference: 7-day pre-deploy p99 was ~640ms (compare the "Previous period" toggle on the panel; new p99 must be within +25% / under 800ms).

---

## Step 5 -- Negative checks (must prove the change actually shipped)

These catch the silent no-op deploy failure mode (PR merged, runtime unchanged).

- **N-1 (proves AC-1 code path is live):** Datadog log query
  ```
  service:subscriptions-api env:production deploy_sha:a1b2c3d
  route:"/api/v1/subscriptions" method:POST
  @http.status_code:409
  ```
  Time range: deploy window. Expected: ≥1 hit within 24h. **Zero hits = either no duplicate-create attempts occurred (run the §A smoke test to force one) OR the new code path is not deployed.** After running §A, expected: ≥1 hit including the `x-request-id` from §A step 3.

- **N-2 (proves pre-slice code path is dead):** Datadog log query for the old 200-on-duplicate path
  ```
  service:subscriptions-api env:production deploy_sha:a1b2c3d
  route:"/api/v1/subscriptions" method:POST
  @http.status_code:200 @subscription.created_for_existing_active_user:true
  ```
  Expected: **zero hits** over the 24h window. Any hit = old code path is still being served (deploy did not roll out to all instances) = rollback trigger.

- **N-3 (proves AC-3 idempotency branch is live):** Datadog log query
  ```
  service:webhooks-api env:production deploy_sha:a1b2c3d
  @stripe.event_type:"customer.subscription.created"
  @idempotency.outcome:"deduped"
  ```
  Expected: ≥1 hit within 24h (Stripe naturally retries some webhooks; if no organic hits, the §C smoke test forces one). Zero hits across 24h with the §C smoke test executed = idempotency branch is not deployed.

- **N-4 (proves deploy is actually live):** Datadog APM deployment marker
  - URL: `https://app.datadoghq.com/apm/services/subscriptions-api?env=production&deployments=true`
  - Expected: a deployment marker labeled `version:a1b2c3d` at or near `2026-06-05T10:00:00Z`, and post-marker traces carrying `version:a1b2c3d`. Absent marker or absent post-marker tagged traces = deploy did not register = treat all positive signals as suspect.

- **N-5 (error-rate sanity, no new spike):** Datadog APM panel
  - URL: `https://app.datadoghq.com/apm/services/subscriptions-api?env=production&start=1748080800000&end=1748167200000&panel=errors`
  - Expected: 5xx rate on `subscriptions-api` does not exceed the 7-day baseline by more than 1 percentage point. Any new spike correlated with `version:a1b2c3d` = rollback trigger.

---

## Step 6 -- Rollback trigger checklist (named human + exact command)

No feature flag exists for this slice -- rollback path is **deploy revert**. The named on-call human is `@bruno`. Escalation contact: `@bruno` (solo founder; no secondary on-call rotation).

| # | Observation (trigger condition)                                                                                                                                                                                              | Page                    | Exact action                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
|---|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| R-1 | **AC-4 invariant SQL (Step 4 §D) returns ≥1 row at any of the T0+5m / T0+1h / T0+24h checkpoints.**                                                                                                                          | Page `@bruno` immediately | 1. Revert deploy: `vercel rollback subscriptions-api --to <previous-deployment-id>` (previous id is in `https://vercel.com/fhorja/subscriptions-api/deployments`, the deployment immediately before SHA `a1b2c3d`). 2. Quarantine duplicates by flagging the newer row inactive (do NOT delete; preserve audit trail): `UPDATE public.subscriptions SET status = 'quarantined_dup', updated_at = now() WHERE id = ANY('<subscription_ids[2:]> from the §D query'::uuid[]);`. 3. Re-run §D query; must return zero rows. 4. Notify affected users via the script at `scripts/notify_quarantined_subs.ts` (input: list of `user_id` from §D query). |
| R-2 | 5xx rate on `POST /api/v1/subscriptions` exceeds 2% over any 5-minute window (Datadog monitor `monitor_id=sub_api_5xx_rate`).                                                                                                | Page `@bruno`            | 1. `vercel rollback subscriptions-api --to <previous-deployment-id>`. 2. Confirm rollback healthy via panel `https://app.datadoghq.com/apm/services/subscriptions-api?env=production&start=now-15m`. 3. Open Sentry release `a1b2c3d`, capture top error signature, file follow-up via `direction-adjust`.                                                                                                                                                                                                                                                                                                                                       |
| R-3 | AC-5 p99 exceeds 800ms for ≥3 consecutive 5-minute buckets, OR SLO board shows error budget burn ≥10% in any 1h window.                                                                                                       | Page `@bruno`            | 1. Confirm regression in panel (Step 4 §E URL). 2. `vercel rollback subscriptions-api --to <previous-deployment-id>`. 3. Confirm p99 returns to baseline within 30 min on the same panel. 4. Open `direction-adjust` to root-cause the regression (likely the new uniqueness index lookup; consider `CREATE INDEX CONCURRENTLY` follow-up).                                                                                                                                                                                                                                                                                                      |
| R-4 | Webhook duplicate observed: §C cross-check SQL returns `active_rows > 1` for the replayed customer, OR query `@idempotency.outcome:"inserted"` count > distinct `@stripe.event_id` count over 1h window.                      | Page `@bruno`            | 1. `vercel rollback webhooks-api --to <previous-deployment-id>`. 2. Run §D invariant query; if rows returned, follow R-1 quarantine step. 3. Capture failing event id; reproduce locally before redeploying.                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| R-5 | Negative check N-2 returns any hit (old 200-on-duplicate code path still serving) OR N-4 shows no `version:a1b2c3d` deployment marker.                                                                                       | Page `@bruno`            | 1. Re-run deploy: `vercel redeploy <build-id-for-a1b2c3d> --force`. 2. Re-check N-4 deployment marker present. 3. Re-run N-1 negative check to confirm new code path now serves. If still not serving after redeploy, `vercel rollback` to the previous green deployment and open `incident-triage`.                                                                                                                                                                                                                                                                                                                                            |

Paging mechanism: PagerDuty service `fhorja-prod-oncall` (single-member rotation: `@bruno`); SMS + phone call escalation policy `solo-founder-default`. Slack mirror: `#prod-incidents`.

---

## Step 8 -- Trim check

Every signal traces back to one AC or one rollback trigger:
- AC-1 → table row 1 + N-1 + N-2 + R-2
- AC-2 → table row 2
- AC-3 → table row 3 + N-3 + R-4
- AC-4 → table row 4 + R-1 (load-bearing)
- AC-5 → table row 5 + R-3
- Deploy-actually-shipped sanity → N-4, N-5

No shotgun signals included. No "check everything" rows.

---

### Artifact changes

- PROPOSED `<task>/POST_DEPLOY_PLAN.md` -- this file in full (content above).
- PROPOSED `SLICES/14_subscription_uniqueness.md` -- append the following `## Post-deploy checks` section:

  ```markdown
  ## Post-deploy checks

  Deploy: production, sha=`a1b2c3d`, ts=2026-06-05T10:00:00Z. Verification window 24h.
  Plan: see `POST_DEPLOY_PLAN.md`.

  Signals (one per AC; zero orphan ACs):
  - AC-1 → Datadog log query on `service:subscriptions-api ... @http.status_code:409 deploy_sha:a1b2c3d` + curl smoke §A. Owner: `@bruno`.
  - AC-2 → Browser smoke §B (`/account/subscriptions`, assert banner text "You already have an active subscription") + Sentry release `a1b2c3d`. Owner: `@bruno`.
  - AC-3 → Datadog log query on `@stripe.event_type:"customer.subscription.created" @idempotency.outcome:("inserted" OR "deduped")` + Stripe CLI replay smoke §C. Owner: `@bruno`.
  - AC-4 (load-bearing DB invariant) → SQL on `db.fhorja.supabase.co`: `SELECT user_id, COUNT(*) FROM subscriptions WHERE status='active' GROUP BY user_id HAVING COUNT(*) > 1;`. Expected zero rows. Run at T0+5m, T0+1h, T0+24h. Owner: `@bruno`.
  - AC-5 → Datadog APM panel for `POST /api/v1/subscriptions` p99 over deploy window; SLO `subscription_creation_p99_latency_ms` stays Healthy. Owner: `@bruno`.

  Negative checks: N-1 ≥1 hit on 409 path; N-2 zero hits on old 200-on-duplicate path; N-3 ≥1 hit on `deduped` outcome; N-4 deployment marker `version:a1b2c3d` present in APM; N-5 5xx rate no new spike.

  Rollback trigger: any of R-1..R-5 → page `@bruno` (PagerDuty `fhorja-prod-oncall`) → `vercel rollback <service> --to <previous-deployment-id>`; for R-1 also quarantine duplicates with `UPDATE subscriptions SET status='quarantined_dup' WHERE id = ANY(<ids>);`.
  ```

- PROPOSED `TASK_STATE.md` -- append to `## Risks to watch`:

  ```markdown
  - R14-obs: Slice 14 ships unconditionally (no feature flag). Rollback path is `vercel rollback` only; no flag-flip exists. Owner `@bruno`. Watch AC-4 invariant SQL at T0+5m, T0+1h, T0+24h.
  ```

### Command transcript

1. Read `commands/post-deploy-verifier/SKILL.md`; followed Steps 1-9.
2. Enumerated 5 ACs from `SLICES/14_subscription_uniqueness.md`; inventoried Datadog Logs, Datadog APM, Sentry, Supabase Postgres; flag system = NONE.
3. Mapped each AC to exactly one primary signal (table) + cross-checks; authored 5 negative checks; authored 5 rollback triggers naming `@bruno` with exact `vercel rollback` / SQL commands.
4. Single-repo task -- no multi-repo split needed.

### Handoff

Next command: `slice-closure` to apply the `## Post-deploy checks` PROPOSED block into `SLICES/14_subscription_uniqueness.md` and close the slice; or `approve-proposed` to land all three PROPOSED artifacts immediately. After closure, `verify-against-rubric` may be invoked at T0+24h to render a frozen-rubric verdict using the signals above as captured evidence.

Run now: `approve-proposed`
