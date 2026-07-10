# Post-deploy verification plan -- Slice 24 (onboarding error budget)

Deploy: `production` @ sha=`e1f2a3b`, ts=`2026-06-05T15:00:00Z`
Deploy window: 15:00 -> 16:00 UTC (2026-06-05)
SLO observation horizon: 30 days post-deploy (deadline `2026-07-05T15:00:00Z`)
On-call: `@bruno`
Flag: none (unconditional ship)

## 1. Per-AC signal mapping

| AC | Claim | Signal class | Exact query / URL / inputs | Expected result | Owner | Retention risk |
|----|-------|--------------|----------------------------|-----------------|-------|----------------|
| AC-1 | Errors in `/onboarding` are tagged `slice=24` in Sentry | Error-tracker query | Sentry → project `fhorja-web` → Issues search: `tags["slice"]:24 url:"*/onboarding*" environment:production release:e1f2a3b` over `2026-06-05T15:00Z..16:00Z` | At least one captured event in the deploy window proves instrumentation is live; tag `slice=24` present on every event. If zero captured events, run negative-check NC-1 to disambiguate "no errors" vs "no instrumentation". | `@bruno` | **YES -- Sentry free tier 30-day retention.** Query returns empty after `2026-07-05T15:00Z` even if the instrumentation works perfectly. |
| AC-2 | `/onboarding` error rate ≤ 0.5% over deploy window AND 30 days post-deploy | (a) Deploy-window check: Datadog APM panel; (b) 30-day SLO check: Datadog APM panel | (a) Datadog APM → service `fhorja-web` → resource `GET /onboarding` panel `error_rate_5m`, time range `2026-06-05T15:00Z..16:00Z`, overlay deploy marker `e1f2a3b`. (b) Same panel, time range `2026-06-05T15:00Z..2026-07-05T15:00Z`, aggregation `error_rate = sum:trace.http.request.errors{service:fhorja-web,resource_name:GET_/onboarding} / sum:trace.http.request.hits{...}` | (a) error_rate ≤ 0.5% across deploy hour; (b) rolling 30-day error_rate ≤ 0.5% with no sustained breach > 1h. | `@bruno` | **NO -- Datadog 15-month retention covers both windows.** This is the authoritative SLO signal. |
| AC-3 | Datadog APM panel shows `/onboarding` error rate trend correlated with deploy marker | Dashboard panel (scoped) | Datadog dashboard `dash-fhorja-web-onboarding` panel `onboarding_error_rate_trend`, time range `2026-06-05T14:00Z..2026-06-05T18:00Z` (pre/post +/- 1h), deploy marker `e1f2a3b` annotated via `deploy_tags:e1f2a3b` | Deploy marker is visible on the trend; pre-deploy vs post-deploy band shape is comparable (no order-of-magnitude regression at the marker). | `@bruno` | NO -- Datadog. |

### Negative checks
- **NC-1 (catches silent no-op for AC-1):** Sentry query `tags["slice"]:24 environment:production release:e1f2a3b` over deploy window must return **at least one** event with `slice=24`. To exercise instrumentation deterministically, run the synthetic smoke step in §2 which deliberately triggers a captured error path. Zero events here AFTER the smoke step = instrumentation did not ship (PR merged, runtime unchanged).
- **NC-2 (catches AC-2 false-pass from low traffic):** Datadog query `sum:trace.http.request.hits{service:fhorja-web,resource_name:GET_/onboarding}` over deploy window must show non-zero traffic. A 0% error rate over 0 requests does not satisfy AC-2.
- **NC-3 (catches AC-3 dashboard staleness):** Confirm the deploy marker annotation `e1f2a3b` is actually present on the dash; absence = CI deploy-marker pipeline broke, not a code issue but invalidates AC-3.

## 2. Which AC's signal depends on Sentry retention?

**AC-1 depends on Sentry retention.** Its only signal is a Sentry query against tag `slice=24`. Sentry is on the FREE TIER with **30-day retention**, so events captured at `2026-06-05T15:00Z` are PURGED at `2026-07-05T15:00Z`. Any AC-1 retrospective verification after day 30 will return zero hits -- indistinguishable from "instrumentation never shipped".

AC-2 and AC-3 are not retention-fragile: they read from Datadog APM (15-month retention), which comfortably covers the 30-day SLO horizon plus 14 months of historical comparison.

## 3. What happens to AC-2's signal at day 31 post-deploy?

AC-2 is NOT retention-fragile, but it has a **subtle adjacent fragility** that must be called out so the plan does not silently mislead the on-call:

- **The Datadog signal at day 31 itself is intact.** Datadog retains 15 months, so the rolling 30-day error_rate query against `2026-06-05T15:00Z..2026-07-05T15:00Z` is fully answerable at day 31 and beyond. This is the authoritative SLO verdict for AC-2.
- **However, root-cause forensics for any AC-2 breach detected at day 30 are retention-impaired.** If the 30-day error_rate check at `2026-07-05T15:00Z` reveals a breach, the on-call's natural next step is to drill into per-event Sentry stack traces with tag `slice=24` to identify which exception class drove the breach. Sentry events from days 1–N of the window where N < (today − 30 days) are already purged. Concretely, a breach observed at day 30 can only be forensically investigated against the last ~30 days of underlying events, not the full 30-day SLO window.
- **At day 31, the AC-1 signal that anchors "instrumentation is alive" is dark.** This means: if Datadog shows AC-2 passed, the on-call cannot independently re-verify at day 31 that the events feeding any downstream Sentry-based dashboards (alerts, weekly reports) were actually being captured throughout the SLO window -- only that the Datadog-measured request error counts looked healthy. Datadog APM error_rate and Sentry-captured exceptions count different things (HTTP 5xx/4xx traces vs. instrumented thrown exceptions); the two signals diverging silently is a known failure mode.

**Net:** AC-2's primary signal survives. Its forensic depth and its cross-check against AC-1 do not.

## 4. Remediation -- handling the retention boundary

The plan MUST treat Sentry retention as a hard physical constraint and pre-stage the data the day-30 SLO check needs. Four remediations, ordered cheapest-first:

### R-1 (REQUIRED) -- Day-0 baseline snapshot of AC-1 evidence
At deploy +1h (`2026-06-05T16:00Z`), capture and persist to long-retention storage (Postgres `ops_verification_evidence` table or task folder `POST_DEPLOY_EVIDENCE/slice-24/`) a frozen artifact:
- Sentry CSV export of all events matching `tags["slice"]:24 environment:production release:e1f2a3b` over the deploy window.
- A signed assertion line in `.wos/VERIFICATION_LOG.jsonl`: `{slice:24, ac:AC-1, captured_events:N, sample_event_ids:[...], snapshot_ts:2026-06-05T16:00Z}`.
This locks AC-1 as VERIFIED at day 0, independent of Sentry retention. The day-30 closure check then re-reads the frozen snapshot, not Sentry directly.

### R-2 (REQUIRED) -- Mirror Sentry counts into Datadog as a derived metric
Configure Sentry → Datadog integration (or a lightweight cron in `apps/web` that runs every 5m and emits `statsd` count) to emit `fhorja.onboarding.sentry_events{slice:24,release:e1f2a3b}` into Datadog. Datadog's 15-month retention then carries the AC-1 signal across the full 30-day SLO window. The day-30 check queries Datadog, not Sentry. Cost: ~free (uses existing Datadog ingest). This is the durable fix.

### R-3 (REQUIRED) -- Scheduled day-7, day-14, day-29 polling jobs
Add a Trigger.dev `schedules.task` `verify-slice-24-ac1` with `cron: "0 12 7,14,29 6,7 *"` (firing 2026-06-12, 2026-06-19, 2026-07-04 -- i.e. day 7, 14, 29, all comfortably inside Sentry's 30-day window). Each run:
1. Queries Sentry for `tags["slice"]:24 release:e1f2a3b` over the elapsed window.
2. Appends a row to `ops_verification_evidence(slice, ac, polled_at, event_count, sample_ids)`.
3. On day 29, emits a final "AC-1 evidence locked" event and pages `@bruno` if `event_count = 0` at any poll (silent regression in instrumentation between deploys).
This guarantees the day-30 SLO check has Postgres-persisted Sentry evidence even if R-2 was never wired up.

### R-4 (CONDITIONAL -- recommend if budget allows) -- Upgrade Sentry retention
The cheapest paid Sentry tier extends retention to 90 days, which would cover the 30-day SLO window with a 60-day margin and eliminate the cross-check forensics gap noted in §3. Flag this as a follow-up `direction-adjust` if Slice 24's error budget becomes load-bearing for other slices' SLOs.

### Rollback trigger checklist (retention-aware)

| Observation | Window | Page | Action |
|-------------|--------|------|--------|
| AC-1 NC-1 returns zero captured events after smoke step at deploy +1h | `2026-06-05T15:00Z..16:00Z` | `@bruno` | Re-deploy with instrumentation fix; do NOT close slice. Silent-no-op confirmed. |
| AC-2 error rate exceeds 0.5% sustained > 15min during deploy window | `2026-06-05T15:00Z..16:00Z` | `@bruno` | `vercel rollback <deployment-id-for-sha-e1f2a3b>` immediately; investigate Sentry events captured pre-purge. |
| AC-2 rolling 30-day error rate breaches 0.5% at any scheduled check (day 7, 14, 29) | rolling | `@bruno` | Do NOT auto-rollback; open `direction-adjust` slice. Pull Sentry forensics from `ops_verification_evidence` (R-1/R-3 ensures availability). |
| R-2 derived metric `fhorja.onboarding.sentry_events` stops emitting | any | `@bruno` | Sentry→Datadog bridge broken; restore before day-30 deadline or fall back to R-3 evidence. |
| Day 29 scheduled poll (R-3) fires and returns `event_count = 0` for any prior window | day 29 | `@bruno` | Instrumentation regressed silently; treat as Slice 24 partial-regression incident. |

## Plan summary (for slice file `## Post-deploy checks` PROPOSED block)

- AC-1 verified via Sentry tag query (retention-fragile: Sentry free tier 30-day purge).
- AC-2 verified via Datadog APM error_rate panel over deploy window AND rolling 30-day window.
- AC-3 verified via Datadog dashboard `dash-fhorja-web-onboarding` panel `onboarding_error_rate_trend` with deploy marker `e1f2a3b`.
- Three negative checks block silent no-op and low-traffic false-pass.
- Retention remediation: day-0 evidence snapshot (R-1) + Sentry→Datadog metric mirror (R-2) + Trigger.dev scheduled polling on day 7/14/29 (R-3) ensure the day-30 SLO check has the data it needs even after Sentry purge at `2026-07-05T15:00Z`.
- Rollback paging routed to `@bruno`; commands and observations are explicit per the table above.
- New risk added to `TASK_STATE.md ## Risks to watch`: "Sentry free-tier 30-day retention vs. 30-day SLO horizon -- verified via R-1/R-2/R-3; revisit if SLO horizon extends past 60 days, in which case escalate to R-4 (paid Sentry tier)."

### Recommended next command
`slice-closure` -- to apply the `## Post-deploy checks` PROPOSED block once R-1 (day-0 snapshot) and R-2 or R-3 (durable AC-1 evidence pipeline) are wired. If the user prefers to land the PROPOSED block immediately and wire R-2/R-3 in a follow-up slice, route to `approve-proposed` then `direction-adjust` to open the retention-bridge follow-up slice.
