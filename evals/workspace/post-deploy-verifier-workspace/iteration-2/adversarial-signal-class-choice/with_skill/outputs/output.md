# POST_DEPLOY_PLAN -- Slice 47: Org-quota enforcement

Deploy: `production` @ sha `d4c5b6a`, window `2026-06-05T18:00:00Z → 2026-06-05T19:00:00Z`.
On-call: `@bruno`. Feature flag: none (unconditional ship; rollback = revert + redeploy).
Observability stack: Datadog Logs, Datadog APM, Postgres (psql), PostHog, Sentry.

---

## 1. Per-AC signal mapping

Three ACs traded their surface-obvious signal class for the correct smallest-resolution one:

- **AC-2: log-class TRAP → DB-class.** The audit-log line is fire-and-forget without a `correlation_id`, so Datadog Logs cannot bind a specific 429 to a specific `quota_exceeded` row. The load-bearing observable is the persisted `audit_events` row, not the log line. Signal: SQL against `audit_events`.
- **AC-4: dashboard-class TRAP → per-tenant SQL-class.** The Datadog APM panel sums `items.count` across tenants and would mask a per-org breach (one tenant at 12,000 hidden by 99 tenants at <10,000). The AC is a per-tenant invariant. Signal: SQL `GROUP BY org_id HAVING count(*) > 10000` (zero rows).
- **AC-6: SQL-class TRAP → PostHog-class.** The CTA click is a UI event not persisted to the DB; the analytics pipeline (PostHog) is the only system that records it. SQL would falsely return "no signal." Signal: PostHog event filter on `cta_clicked` with `cta_id = upgrade_plan_from_429`.

| AC | Claim | Signal class | Exact query / URL / inputs | Expected result | Owner |
|---|---|---|---|---|---|
| AC-1 | `POST /api/v1/items` returns 429 at org item-count >= 10,000 | Datadog Logs (structured log query) | `service:items-api route:/api/v1/items status:429 deploy_sha:d4c5b6a @timestamp:[2026-06-05T18:00:00Z TO 2026-06-05T19:00:00Z]` | At least 1 hit from a real org at quota; zero hits from orgs under quota during the same window | `@bruno` |
| AC-2 | Audit log entry `event:quota_exceeded org_id:<uuid> item_count:<int>` is emitted on each 429 -- **DB, not logs (TRAP)** | Postgres invariant query | `SELECT count(*) FROM audit_events WHERE event = 'quota_exceeded' AND created_at >= '2026-06-05T18:00:00Z' AND created_at < '2026-06-05T19:00:00Z';` cross-referenced with Datadog 429 count: `SELECT count(*) AS audit_rows FROM audit_events WHERE event='quota_exceeded' AND created_at BETWEEN '2026-06-05T18:00:00Z' AND '2026-06-05T19:00:00Z';` | `audit_rows` equals the Datadog 429 count for the same window (±0). Every row has non-null `org_id` (uuid) and `item_count` (int >= 10000). | `@bruno` |
| AC-3 | Datadog APM error-rate panel on `/api/v1/items` shows the 429 spike correlated with the deploy | Datadog APM dashboard panel | `https://app.datadoghq.com/apm/services/items-api/operations/POST_/api/v1/items?env=production&from_ts=1781020800000&to_ts=1781024400000&panel=error_rate_by_status&filter=status_code:429` | Visible step-up in 429 rate starting within 60s of deploy ts `2026-06-05T18:00:00Z`; 5xx rate flat (i.e., no spurious server errors) | `@bruno` |
| AC-4 | DB invariant `count(items) per org_id <= 10000` holds across all orgs -- **per-tenant SQL, not dashboard (TRAP)** | Postgres invariant query (per-tenant, not cross-tenant aggregate) | `SELECT org_id, count(*) AS n FROM items WHERE deleted_at IS NULL GROUP BY org_id HAVING count(*) > 10000;` | Zero rows. If any row returns, the enforcement gate has a bypass (race condition, RLS gap, or admin path skipped the check). | `@bruno` |
| AC-5 | Smoke: test org at 9999 items POSTs one more → 201; POSTs another → 429 | Smoke-test walkthrough | See §2 below | First call 201 with body `{ "item_id": "<uuid>" }`; second call 429 with body `{ "error": "quota_exceeded", "limit": 10000 }` | `@bruno` |
| AC-6 | 'Upgrade plan' CTA shown on 429; clicks route to `/billing`; click-rate observably increases -- **PostHog, not DB (TRAP)** | PostHog event filter | Event: `cta_clicked`, property filter: `cta_id = "upgrade_plan_from_429"`, time range `2026-06-05T18:00:00Z → 2026-06-05T19:00:00Z`; comparison panel against the prior 1h baseline. Companion event: `$pageview` where `$current_url` matches `/billing` and `$referrer` matches `/items` (any page that triggered the 429). URL: `https://app.posthog.com/insights/new?events=[{"id":"cta_clicked","properties":[{"key":"cta_id","value":"upgrade_plan_from_429"}]}]&date_from=2026-06-05T18:00:00Z&date_to=2026-06-05T19:00:00Z` | `cta_clicked[upgrade_plan_from_429]` count > 0 in the window; observable lift vs the prior-hour baseline; `$pageview` on `/billing` with referrer matching the 429-emitting page count > 0 | `@bruno` |
| AC-7 | `/billing` page is reachable and renders the upgrade flow | Smoke-test walkthrough | See §2 step 3 | HTTP 200; DOM contains the text `Upgrade your plan` and a button with `data-testid="upgrade-checkout-cta"` | `@bruno` |

---

## 2. Smoke-test walkthrough (AC-5, AC-7)

Preconditions: a seeded test org `org_smoke_quota_47` exists in production with exactly 9,999 active items (`deleted_at IS NULL`). API token: `$SMOKE_TOKEN` (read from 1Password `prod/smoke/quota-47`).

**Step 1 -- Confirm starting count (AC-5 baseline).**
`psql "$PROD_DSN" -c "SELECT count(*) FROM items WHERE org_id = 'org_smoke_quota_47' AND deleted_at IS NULL;"`
Expect: `9999`.

**Step 2 -- POST item #10000 (AC-5, expect 201).**
```
curl -sS -X POST https://api.fhorja.com/api/v1/items \
  -H "Authorization: Bearer $SMOKE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"smoke-47-10000","payload":{"k":"v"}}' -i
```
Expect: `HTTP/1.1 201 Created`, body `{ "item_id": "<uuid>" }`.

**Step 3 -- POST item #10001 (AC-5, expect 429).**
Same curl with `"name":"smoke-47-10001"`.
Expect: `HTTP/1.1 429 Too Many Requests`, body `{ "error": "quota_exceeded", "limit": 10000, "current": 10000, "upgrade_url": "/billing" }`.

**Step 4 -- Audit row landed (AC-2 cross-check).**
`psql "$PROD_DSN" -c "SELECT event, org_id, item_count, created_at FROM audit_events WHERE org_id = 'org_smoke_quota_47' AND event = 'quota_exceeded' ORDER BY created_at DESC LIMIT 1;"`
Expect: exactly one row, `item_count = 10000`, `created_at` within last 60s.

**Step 5 -- Click the CTA in browser (AC-6, AC-7).**
Open Chrome (logged in as a `org_smoke_quota_47` user). Navigate to `/items/new`, submit the form. Expect a banner: `You've hit your plan limit (10,000 items).` with a button labeled `Upgrade plan`. Click it. Expect: navigation to `/billing`; DOM contains text `Upgrade your plan`; PostHog network call to `/e/` with `event=cta_clicked, cta_id=upgrade_plan_from_429`.

**Cleanup.** `psql "$PROD_DSN" -c "DELETE FROM items WHERE org_id = 'org_smoke_quota_47' AND name = 'smoke-47-10000';"` to restore the test org to 9,999 for the next smoke.

---

## 3. Log queries (consolidated)

- **AC-1 (Datadog Logs):** `service:items-api route:/api/v1/items status:429 deploy_sha:d4c5b6a @timestamp:[2026-06-05T18:00:00Z TO 2026-06-05T19:00:00Z]`
- **Sentry sanity (negative for AC-3):** project `items-api`, search `release:d4c5b6a level:error` over the deploy window. Expect zero new issue groups tagged `route:/api/v1/items` other than expected `quota_exceeded`-derived warnings (which should be `level:warning`, not `error`).

---

## 4. Dashboard scopes

- **AC-3 panel:** Datadog APM, service `items-api`, operation `POST /api/v1/items`. URL pattern: `https://app.datadoghq.com/apm/services/items-api/operations/POST_/api/v1/items?env=production&from_ts=1781020800000&to_ts=1781024400000`. Required widgets: error-rate by status code (must show 429 step), latency p50/p95/p99 (must NOT spike -- enforcement should be O(1) DB check), throughput (must be flat-to-slightly-down, not collapsed).
- **DO NOT use** the existing `Org quotas overview` panel for AC-4. It aggregates `SUM(item_count)` across all orgs and would mask a single-org breach. Use the SQL in the AC-4 row instead.

---

## 5. Negative checks (would prove the change DID NOT ship)

- **NC-1 (enforcement actually running).** Datadog Logs: `service:items-api route:/api/v1/items status:429 deploy_sha:d4c5b6a @timestamp:[2026-06-05T18:00:00Z TO 2026-06-05T19:00:00Z]`. If zero 429s land in the first hour AND at least one org sits at >=10,000 items per `SELECT count(*) FROM items WHERE org_id = (SELECT org_id FROM items GROUP BY org_id ORDER BY count(*) DESC LIMIT 1);`, the gate is a no-op -- the deploy shipped but the runtime check is bypassed.
- **NC-2 (pre-deploy code path is dead).** Datadog Logs: `service:items-api route:/api/v1/items @deploy_sha:-d4c5b6a status:201 @timestamp:[2026-06-05T18:05:00Z TO 2026-06-05T19:00:00Z]`. Expect zero hits after the deploy timestamp; non-zero = canary/old pods still serving.
- **NC-3 (audit pipeline alive).** `SELECT count(*) FROM audit_events WHERE created_at >= '2026-06-05T18:00:00Z';` must be > 0 in the deploy window; if zero, AC-2's "no rows" verdict is uninformative (audit pipeline broken, not "no quota events").
- **NC-4 (PostHog alive).** PostHog: `$pageview` count > 0 in the deploy window for the `items-web` project. Zero = PostHog SDK broken, AC-6's verdict is uninformative.
- **NC-5 (per-tenant invariant has actual subjects).** `SELECT count(DISTINCT org_id) FROM items WHERE deleted_at IS NULL;` > 0; otherwise AC-4's "zero rows over limit" is trivially true.

---

## 6. Rollback trigger checklist

No feature flag, so rollback = `vercel rollback` to the previous production deployment + `psql` cleanup if any audit-row schema migration ran (none in this slice -- confirmed by inspecting the diff).

| Observation | Page | Action |
|---|---|---|
| Datadog APM `/api/v1/items` 5xx rate > 1% over 5 min in deploy window | `@bruno` | `vercel rollback <prev_deployment_id>` (previous prod deployment id captured at deploy time in the slice file's `## Deploy log`). |
| Datadog APM `/api/v1/items` p95 latency > 2x pre-deploy baseline over 5 min | `@bruno` | Same `vercel rollback`. Capture a flamegraph from Datadog APM first if time allows. |
| AC-4 SQL returns any row (per-tenant invariant breached post-deploy) | `@bruno` | `vercel rollback` then run remediation SQL: `SELECT org_id, count(*) FROM items WHERE deleted_at IS NULL GROUP BY org_id HAVING count(*) > 10000;` and triage each org case-by-case (do not bulk-delete). |
| Sentry new error group on `items-api` release `d4c5b6a` with event count > 50 in first 30 min | `@bruno` | `vercel rollback`. |
| AC-2 audit-rows count diverges from Datadog 429 count by > 5% | `@bruno` (no rollback -- investigate) | Do not roll back; the user-facing behavior is correct. Open a follow-up slice to add `correlation_id` to both the log line and the audit row so the two sides can be joined. Track under `TASK_STATE.md ## Risks to watch`. |

---

## 7. PROPOSED block for slice file

To be inserted at the bottom of `SLICES/47_org_quota_enforcement.md` by `slice-closure`:

```markdown
## Post-deploy checks

Deploy: `production` @ `d4c5b6a`, window `2026-06-05T18:00:00Z → 2026-06-05T19:00:00Z`.
Full plan: `POST_DEPLOY_PLAN.md`.

- AC-1 → Datadog Logs `status:429 route:/api/v1/items deploy_sha:d4c5b6a` over deploy window.
- AC-2 → Postgres `audit_events` row count, cross-checked against Datadog 429 count (DB is the load-bearing observable; the log line is fire-and-forget with no correlation_id).
- AC-3 → Datadog APM panel `items-api POST /api/v1/items` over deploy window.
- AC-4 → `SELECT org_id, count(*) FROM items WHERE deleted_at IS NULL GROUP BY org_id HAVING count(*) > 10000;` (per-tenant; the existing Datadog panel sums across tenants and is unsafe here).
- AC-5 → smoke walkthrough §2 (steps 1–3) against seeded org `org_smoke_quota_47`.
- AC-6 → PostHog event `cta_clicked` with `cta_id=upgrade_plan_from_429` over deploy window, plus companion `$pageview /billing` with referrer (CTA click is a UI event; not persisted to the DB).
- AC-7 → smoke walkthrough §2 (step 5): `/billing` returns 200, renders `Upgrade your plan`.

Negative checks: NC-1 through NC-5 (see plan). Rollback: `vercel rollback` to previous deployment id, paged to `@bruno`.
```

## 8. PROPOSED block for `TASK_STATE.md ## Risks to watch`

```markdown
- AC-2 audit-row ↔ Datadog 429 reconciliation has no `correlation_id` join key. Current verification is "counts within 5%." Follow-up slice should add `correlation_id` to both the log line and the audit row so each 429 is provably bound to its audit event. Tracked: 2026-06-05.
- AC-4's existing `Org quotas overview` Datadog panel aggregates across tenants and is unsafe as a per-tenant invariant signal. Either retitle/scope the panel to a per-tenant breakdown or add a panel-level warning. Tracked: 2026-06-05.
```

---

### Artifact changes

- `POST_DEPLOY_PLAN.md` (active task folder) -- PROPOSED (full body above).
- `SLICES/47_org_quota_enforcement.md` -- PROPOSED `## Post-deploy checks` block (§7 above), to be applied by `slice-closure`.
- `TASK_STATE.md` `## Risks to watch` -- PROPOSED two new risk entries (§8 above).

### Command transcript

1. Read slice file: 7 ACs enumerated. Stack inventory confirmed: Datadog Logs/APM, Postgres, PostHog, Sentry. No feature-flag system.
2. Classified each AC by smallest-resolution correct signal; flagged AC-2 / AC-4 / AC-6 as TRAPs and routed each to the correct class (DB / per-tenant SQL / PostHog).
3. Authored query-shaped signals, smoke walkthrough with concrete inputs/expected bodies, 5 negative checks, rollback table with `@bruno` paged and exact `vercel rollback` command.
4. Built PROPOSED blocks for slice file and `TASK_STATE.md ## Risks to watch`.

### Handoff

Plan is ready. Three signal-class traps were rerouted: AC-2 to Postgres `audit_events` (the log line has no correlation id), AC-4 to a per-tenant `GROUP BY org_id HAVING count(*) > 10000` SQL (the existing Datadog panel sums across tenants and would mask a single-org breach), and AC-6 to a PostHog `cta_clicked` event filter (the CTA click only exists in the analytics pipeline, not the DB).

Run now: `approve-proposed` to land `POST_DEPLOY_PLAN.md` and the two PROPOSED blocks, then `slice-closure` to insert `## Post-deploy checks` into the slice and move the slice to closed.

Alternates:
- `verify-against-rubric` -- if you want a frozen-rubric verdict executed against the live signals before closing.
- `direction-adjust` -- to spin out the two new risks (correlation_id join key for AC-2; per-tenant scoping for the Datadog `Org quotas overview` panel) into their own slices.
