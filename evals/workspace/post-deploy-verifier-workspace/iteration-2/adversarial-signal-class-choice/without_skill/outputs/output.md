# Post-Deploy Verification Plan -- Slice 47: Org-quota enforcement

**Deploy:** production, sha `d4c5b6a`, window 2026-06-05T18:00:00Z → 2026-06-05T19:00:00Z
**On-call:** @bruno
**Feature flag:** none (no flag-flip rollback path; rollback = redeploy prior sha)

## Signal-class trap callouts (read before executing)

Three ACs in this slice look like one signal class but the load-bearing observable lives in a different one. Verifying the wrong surface will produce a green check on an unobserved invariant. Specifically:

- **AC-2 traded Datadog Logs → Postgres.** The audit log line *is* emitted to Datadog, but it is fire-and-forget without a `correlation_id` / `trace_id` join to the 429 response, so a log search proves "some quota_exceeded line existed" but not "*this* 429 produced *this* audit row for *this* org." The durable, queryable artifact is the audit row in Postgres. Verify there. Datadog Logs is kept only as a secondary sanity check.
- **AC-4 traded Datadog dashboard → per-tenant SQL.** The Datadog panel for "items per org" sums or averages across tenants, so a single offending org at 10,001 items can be hidden by 9,999 other orgs at low counts. The AC is a *per-tenant* invariant (`count(items) per org_id <= 10000`), which is a `GROUP BY org_id HAVING count(*) > 10000` shape -- that is a SQL-against-prod-replica check, not a dashboard check.
- **AC-6 traded SQL → PostHog.** The claim reads quantitative ("click-rate change") and tempts a DB query, but the "Upgrade plan" CTA click is a user-facing front-end event that is only instrumented in PostHog. There is no `cta_clicks` table. Verify in the analytics pipeline.

## Per-AC signal mapping

| AC | Claim (short) | Signal class chosen | Why this class is the smallest-resolution correct one |
|----|---------------|---------------------|--------------------------------------------------------|
| AC-1 | 429 when org has ≥10,000 active items | Datadog APM (route-level status code distribution) | Route-scoped HTTP status counts are exactly what APM exposes; smallest resolution to observe "429 appears post-deploy on this route." |
| AC-2 | Audit log entry on 429 | **Postgres (audit table)** -- TRAP, not Datadog Logs | Log line is fire-and-forget without correlation_id; cannot prove per-request linkage. Audit row in DB is the load-bearing artifact. |
| AC-3 | Datadog error-rate spike correlates with deploy | Datadog APM panel | Deploy-marker correlation is exactly what the APM error-rate panel renders. |
| AC-4 | Per-org invariant `count(items) ≤ 10000` | **Per-tenant SQL (replica)** -- TRAP, not Datadog dashboard | Dashboard aggregates across tenants and would mask a single violator; AC is per-tenant, so the query must be `GROUP BY org_id HAVING count(*) > 10000`. |
| AC-5 | Smoke: 9999 → 201, then → 429 | Smoke step (scripted curl against staging-mirror test org) | Behavioral end-to-end check; can only be confirmed by executing the calls. |
| AC-6 | "Upgrade plan" CTA shown on 429 and clicks route to /billing; click-rate change | **PostHog event filter** -- TRAP, not SQL | CTA click is a front-end event only emitted to PostHog; no DB table records it. |
| AC-7 | `/billing` reachable and renders upgrade flow | Smoke step (HTTP GET + DOM presence check) | Page-render reachability is a synthetic-check shape; APM alone cannot confirm the upgrade flow renders. |

---

## Per-AC exact query shapes, negative checks, and pass criteria

### AC-1 -- 429 on quota breach (Datadog APM)

**Signal class:** Datadog APM, route-scoped status-code breakdown.

**Query shape (Datadog APM search):**
```
service:items-api resource_name:"POST /api/v1/items" @http.status_code:429
env:prod
```
Timeframe: deploy_ts ± 60 min.

**Panel URL shape:** `https://app.datadoghq.com/apm/services/items-api/resources?env=prod&resource=POST%20/api/v1/items&from_ts=<deploy_ts-3600>&to_ts=<deploy_ts+3600>`

**Pass:** at least one 429 observed on this route post-deploy, attributable to a real org (not synthetic). For zero-traffic windows, AC-1 is confirmed instead by AC-5 smoke.

**Negative check:** confirm no 429s on this route in the 60 min *before* deploy (rules out pre-existing 429s from a different code path).

---

### AC-2 -- Audit row on 429 (Postgres) -- TRAP: NOT Datadog Logs

**Signal class:** Postgres direct query against the audit table. The Datadog Logs entry exists but is unjoinable to the originating request because no `correlation_id` / `trace_id` is included in the log payload.

**Query shape (psql against prod read replica):**
```sql
SELECT id, event, org_id, item_count, created_at
FROM audit_log
WHERE event = 'quota_exceeded'
  AND created_at >= '2026-06-05T18:00:00Z'
  AND created_at <  '2026-06-05T19:00:00Z'
ORDER BY created_at DESC
LIMIT 50;
```

**Pass:** at least one row with `event = 'quota_exceeded'`, a real (non-test) `org_id`, and `item_count >= 10000`, within the deploy window. Row count should be ≥ the count of 429s observed in AC-1 for that same org (one audit row per 429 is the contract; allow ≥ in case retry-on-429 inflates 429 count above audit count).

**Secondary sanity check (Datadog Logs, not load-bearing):**
```
service:items-api "quota_exceeded" env:prod
```
This is only used to detect total absence of the log line, not to prove per-request linkage.

**Negative check:** confirm no `quota_exceeded` rows exist for orgs whose item count is < 10000 (no false-positive emissions).

---

### AC-3 -- Error-rate spike correlated with deploy (Datadog APM)

**Signal class:** Datadog APM error-rate panel with deploy marker overlay.

**Panel URL shape:** `https://app.datadoghq.com/apm/services/items-api?env=prod&panel=error_rate&deployment_marker=d4c5b6a&from_ts=<deploy_ts-3600>&to_ts=<deploy_ts+3600>`

**Pass:** error-rate panel shows a step-change in 4xx (specifically 429) timing-aligned with the `d4c5b6a` deploy marker. 5xx rate should be flat (a 5xx spike here would indicate the quota path is throwing instead of returning 429 cleanly).

**Negative check:** 5xx rate on `/api/v1/items` does not increase post-deploy (rules out the quota check causing exceptions instead of clean 429s).

---

### AC-4 -- Per-org invariant ≤ 10,000 items (Per-tenant SQL) -- TRAP: NOT dashboard

**Signal class:** Postgres direct query, grouped by tenant. The Datadog dashboard panel for "items per org" sums or averages across tenants and would silently hide a single violating org.

**Query shape (psql against prod read replica):**
```sql
SELECT org_id, count(*) AS item_count
FROM items
WHERE status = 'active'
GROUP BY org_id
HAVING count(*) > 10000
ORDER BY item_count DESC;
```

**Pass:** query returns zero rows. Any row returned is an invariant violation and is a P1 (the enforcement gate let a write through).

**Negative check:** also run with `status = 'active'` removed to confirm we're not hiding a violation behind a status filter:
```sql
SELECT org_id, count(*) AS total_items
FROM items
GROUP BY org_id
HAVING count(*) > 10000
ORDER BY total_items DESC LIMIT 10;
```
If this returns rows but the AC-4 query above does not, surface to @bruno -- it means the invariant is only being held by the `status` filter, which may or may not match the product intent.

**Why not the dashboard:** the cross-tenant aggregate panel will show "avg items/org = 312" even if one org has 50,000. A per-tenant invariant requires a per-tenant query.

---

### AC-5 -- Smoke (scripted)

**Signal class:** smoke step against a known test org seeded to 9,999 active items.

**Smoke step:**
```bash
# Pre-state: test org test-org-quota-47 has exactly 9999 active items (seeded).
TOKEN=$(<prod test-org API token>)
ORG=test-org-quota-47

# Expect 201
curl -sS -o /dev/null -w "%{http_code}\n" \
  -X POST https://api.fhorja.com/api/v1/items \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Org-Id: $ORG" \
  -H "Content-Type: application/json" \
  -d '{"name":"smoke-item-10000"}'
# -> 201

# Expect 429
curl -sS -o /dev/null -w "%{http_code}\n" \
  -X POST https://api.fhorja.com/api/v1/items \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Org-Id: $ORG" \
  -H "Content-Type: application/json" \
  -d '{"name":"smoke-item-10001"}'
# -> 429
```

**Pass:** first call returns 201, second returns 429. Both observations recorded in the verification log with timestamps.

**Negative check:** after the smoke, verify per-tenant SQL (AC-4 shape) for `org_id = test-org-quota-47` returns exactly 10000, not 10001 (confirms enforcement actually blocked the write rather than soft-warning).

**Cleanup:** delete the smoke-added item (or reset the test org to 9999) so the next run is repeatable.

---

### AC-6 -- Upgrade-plan CTA shown + click-rate (PostHog) -- TRAP: NOT SQL

**Signal class:** PostHog event filter on the front-end click event. The CTA click is not persisted to Postgres; there is no `cta_clicks` table. The only durable record lives in the analytics pipeline.

**PostHog event filter shape:**

Event 1 -- CTA *shown* (impression):
```
event = "upgrade_cta_shown"
properties.context = "quota_exceeded_429"
properties.route = "/api/v1/items"
date_from = 2026-06-05T18:00:00Z
date_to   = 2026-06-05T19:00:00Z
```

Event 2 -- CTA *clicked*:
```
event = "upgrade_cta_clicked"
properties.context = "quota_exceeded_429"
properties.destination = "/billing"
date_from = 2026-06-05T18:00:00Z
date_to   = 2026-06-05T19:00:00Z
```

**Pass:**
1. Impression count > 0, and roughly tracks the 429 count from AC-1 (1:1 is ideal; >1:1 acceptable if a user sees the CTA multiple times in a session).
2. Click count > 0 (proves the CTA is interactive and the route to `/billing` fires).
3. Funnel `upgrade_cta_shown` → `upgrade_cta_clicked` shows non-zero conversion compared to the same time-of-day window the day prior.

**Negative check:** confirm `upgrade_cta_clicked` `properties.destination` is `/billing` for ≥99% of events (rules out a wiring bug that routes the click elsewhere).

**Why not SQL:** there is no DB-side click record. A SQL query would return zero rows and produce a false negative.

---

### AC-7 -- `/billing` reachable and upgrade flow renders

**Signal class:** synthetic smoke (HTTP + minimal DOM check).

**Smoke step:**
```bash
# Reachability
curl -sS -o /tmp/billing.html -w "%{http_code}\n" \
  https://app.fhorja.com/billing \
  -H "Cookie: <authenticated test-org-quota-47 session>"
# -> 200

# DOM-presence sanity (look for the upgrade-flow root marker, e.g. a data-testid)
grep -c 'data-testid="upgrade-flow-root"' /tmp/billing.html
# -> >= 1
```

**Pass:** HTTP 200 and the upgrade-flow root marker is present in the rendered HTML.

**Negative check:** Sentry filter `url:"/billing" level:error env:prod` over the deploy window returns zero new error groups. Any new `/billing` error group is a regression even if the smoke returns 200 (the test session may not exercise the failing code path).

---

## Cross-AC consistency checks

Run these after individual ACs pass. They cross-check the signals against each other and catch instrumentation drift that single-AC checks miss:

1. **429 count (AC-1, APM) ≈ audit row count (AC-2, Postgres)** for the deploy window, modulo retries. If APM 429s ≫ audit rows, the audit write is failing silently.
2. **429 count (AC-1, APM) ≈ `upgrade_cta_shown` event count (AC-6, PostHog)**. If 429s ≫ impressions, the UI is not rendering the CTA on 429.
3. **AC-4 invariant query returns zero rows** even after AC-5 smoke completes (smoke must not be able to push the test org over 10,000).

---

## Rollback

**Trigger conditions (any one fires rollback):**
- AC-4 invariant query returns any rows for non-test orgs (data integrity violation -- enforcement is letting writes through).
- 5xx rate on `/api/v1/items` rises measurably post-deploy (quota path throwing instead of returning clean 429s).
- AC-2 audit row count is materially less than AC-1 429 count over a sustained 15-min window (audit pipeline broken -- cannot meet compliance posture).
- Sentry error volume on the `/api/v1/items` route shows a new error group attributable to sha `d4c5b6a` with >10 occurrences in the deploy window.

**Rollback procedure:**
1. `@bruno` is paged.
2. Redeploy prior sha (the sha immediately before `d4c5b6a`). No feature flag exists, so flip-rollback is not available -- only redeploy.
3. After redeploy, re-run AC-1 and AC-4 query shapes to confirm: 429s on `/api/v1/items` return to pre-deploy baseline, and the per-tenant invariant query continues to return zero rows.
4. Leave AC-5 smoke org seeded; do not delete it during rollback (it is the fastest way to retest after fix-forward).
5. Open an incident note linking deploy `d4c5b6a`, the AC that failed, and the signal-class evidence (Postgres row sample / PostHog event sample / APM panel screenshot).

**Do not:**
- Do not rely on the Datadog Logs `quota_exceeded` line as evidence of correct enforcement during rollback decisioning -- it cannot be joined per-request to the 429.
- Do not rely on the cross-tenant items-per-org dashboard panel to confirm AC-4 health -- it averages and will mask a single-tenant violation.
- Do not rely on a SQL count for AC-6 outcomes -- the CTA click is PostHog-only.
