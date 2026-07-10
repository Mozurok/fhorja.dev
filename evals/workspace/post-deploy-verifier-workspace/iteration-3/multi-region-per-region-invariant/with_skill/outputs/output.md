# POST_DEPLOY_PLAN.md -- Slice 31: Latency optimization for /search endpoint

Deploy: `production` sha=`9a8b7c6` ts=`2026-06-05T17:00:00Z` (rolling complete ~17:30 UTC)
Regions: `us-east-1`, `us-west-2`, `eu-west-1`, `ap-southeast-1`
On-call: `@bruno`
Verification window: `17:30Z -> 18:30Z` (30 min post-rollout buffer; AC-1 measured over `17:30Z -> 18:30Z`)

---

## 0. Critical framing (load-bearing for this slice)

AC-1 is a **per-region invariant**: "p99 < 200ms in EACH region". The observability stack defaults to **aggregate** views (Datadog APM default-view; Datadog SLO `p99 < 200ms aggregate`). A naive aggregate read can show ~250ms and **still hide a single-region blowout** (e.g. three regions at ~120ms, one at ~800ms). Therefore:

- Every AC-1 signal below is authored as **four scoped panels / queries, one per region**, NOT one aggregate.
- The aggregate SLO is downgraded to a **negative-check signal only**, not the AC-1 pass/fail signal.
- Pass criterion for AC-1 = `max(p99_by_region) < 200ms`, NOT `aggregate_p99 < 200ms`.

If you only check the SLO panel, this plan has failed. Read §2 before §1.

---

## 1. Per-AC signal mapping

| AC   | Claim                                                                 | Signal class      | Exact query / URL / inputs                                                                                                                                                                                                                                                          | Expected result                                                                                                  | Owner    |
|------|-----------------------------------------------------------------------|-------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------|----------|
| AC-1a | p99 on `/search` < 200ms in `us-east-1` post-deploy                  | Dashboard panel   | Datadog APM service:`search-api` resource_name:`/search` env:`prod` `region:us-east-1`, metric `trace.http.request.p99`, time range `2026-06-05T17:30:00Z -> 2026-06-05T18:30:00Z`. Panel: `Search Latency by Region` -> filter `region:us-east-1`.                                  | p99 < 200ms sustained across the full 60-min window (no >2-min spike above 200ms).                              | `@bruno` |
| AC-1b | p99 on `/search` < 200ms in `us-west-2` post-deploy                  | Dashboard panel   | Same panel as AC-1a with `region:us-west-2`.                                                                                                                                                                                                                                        | p99 < 200ms sustained.                                                                                          | `@bruno` |
| AC-1c | p99 on `/search` < 200ms in `eu-west-1` post-deploy                  | Dashboard panel   | Same panel with `region:eu-west-1`.                                                                                                                                                                                                                                                 | p99 < 200ms sustained.                                                                                          | `@bruno` |
| AC-1d | p99 on `/search` < 200ms in `ap-southeast-1` post-deploy             | Dashboard panel   | Same panel with `region:ap-southeast-1`. **This is the scenario most likely to silently fail given AP is last in the rolling deploy order.**                                                                                                                                        | p99 < 200ms sustained.                                                                                          | `@bruno` |
| AC-1e | Cross-region disaggregation check (catches single-region blowout)    | Log/metric query  | Datadog metrics query: `max:trace.http.request.p99{service:search-api,resource_name:/search,env:prod} by {region}` over `17:30Z -> 18:30Z`. Equivalent log-based query: `service:search-api @http.url_details.path:/search env:prod @duration:>200000000` faceted by `@region`, count by region. | Four rows returned, one per region, each with `max(p99) < 200ms`. **If any row > 200ms, AC-1 fails for that region even if aggregate passes.** | `@bruno` |
| AC-1f | Deploy actually reached every region (not a no-op in any one)        | Log query         | `service:search-api env:prod @deploy.sha:9a8b7c6` faceted by `@region`, time range `17:00Z -> 18:30Z`.                                                                                                                                                                              | Exactly four region values returned, each with non-zero count. Missing region => deploy did not land there.      | `@bruno` |
| AC-2  | Total `/search` request volume does not drop (routing not broken)     | Dashboard panel   | Datadog APM `trace.http.request.hits{service:search-api,resource_name:/search,env:prod}` summed across regions, compare `2026-06-05T16:00Z -> 17:00Z` (pre-deploy 1h baseline) vs `2026-06-05T17:30Z -> 18:30Z` (post-deploy 1h).                                                    | Post-deploy hits within ±10% of baseline. A drop >10% suggests routing broke (LB, DNS, edge).                   | `@bruno` |
| AC-2-per-region | Per-region volume sanity (catches one-region routing break) | Metric query      | `sum:trace.http.request.hits{service:search-api,resource_name:/search,env:prod} by {region}.as_rate()` for both baseline and post-deploy windows.                                                                                                                                  | Each region within ±15% of its own baseline. A single region dropping to 0 while aggregate looks fine = routing failure isolated to that region. | `@bruno` |

**Zero orphan ACs.** AC-1 maps to 1a–1f (per-region + disaggregation + deploy-landing check). AC-2 maps to aggregate-volume + per-region-volume.

---

## 2. Explicit per-region disaggregation procedure for AC-1

This is the load-bearing section. Execute it in this order.

**Step 1 -- Open the per-region panel, not the aggregate panel.**
- Dashboard: `Search Latency by Region` (Datadog APM, dashboard ID to be linked from `CODE_CONTEXT_MAP.md ## Observability`).
- If the default-view is aggregate, switch to the "Split by `region`" view OR add the filter `region:*` with `group_by:region`.
- Time range: `2026-06-05T17:30:00Z -> 2026-06-05T18:30:00Z` (hard-coded, NOT "last 1h" -- relative time drifts as the page sits open).

**Step 2 -- Run the disaggregation query (AC-1e).**

```
max:trace.http.request.p99{service:search-api,resource_name:/search,env:prod} by {region}
```

Expected output shape:

```
region:us-east-1     -> max p99 = <value>ms
region:us-west-2     -> max p99 = <value>ms
region:eu-west-1     -> max p99 = <value>ms
region:ap-southeast-1 -> max p99 = <value>ms
```

**Pass criterion:** ALL four values < 200ms.
**Fail criterion (and the scenario this plan is designed to catch):** any one value >= 200ms, even if the aggregate p99 sits at ~250ms and the SLO panel reads "barely breached". A 3-good / 1-bad distribution with values `[120, 120, 120, 800]` produces an aggregate p99 around `250ms` that LOOKS like a global mild regression but is actually a total failure in one region. **Do not interpret aggregate as per-region.**

**Step 3 -- Confirm the deploy landed in every region (AC-1f).**

```
service:search-api env:prod @deploy.sha:9a8b7c6
```

Facet by `@region`. Expect four non-empty regions. If `ap-southeast-1` is missing or shows zero hits, AC-1 cannot even be evaluated in that region (a no-op deploy in one region masquerading as healthy because no new code is running there to be slow).

**Step 4 -- Record per-region values in the verification log.**
Write all four `max p99` values into `POST_DEPLOY_PLAN.md ## Verification log` (this file). A single "AC-1 PASS" line is forbidden; only "AC-1 PASS in [list of four regions with values]" is acceptable closure language.

---

## 3. Smoke-test walkthrough (one synthetic request per region)

Run from a workstation with `curl` and ability to set the geo-routing header / hit per-region endpoints. If the LB does not expose per-region endpoints, run via the Datadog Synthetics suite `search-api-per-region-smoke` (one test per region).

For each region in `[us-east-1, us-west-2, eu-west-1, ap-southeast-1]`:

```
curl -sS -o /dev/null -w "%{http_code} %{time_total}\n" \
  -H "X-Region-Pin: <region>" \
  "https://search-api.prod.fhorja.com/search?q=test&limit=10"
```

Expected: `200` status, `time_total < 0.20` (200ms) for each of the four invocations.
Failure signal: any region returning `time_total > 0.20` confirms AC-1 fails for that region; cross-check against the per-region panel from §2 to rule out single-request noise (require >=3 out of 5 consecutive smoke invocations > 200ms before treating as confirmed failure).

---

## 4. Log queries (exact)

**Q1 -- Per-region p99 disaggregation (AC-1e backing):**
```
service:search-api env:prod @http.url_details.path:/search @deploy.sha:9a8b7c6
| stats max(@duration) by @region
| time:[2026-06-05T17:30:00Z TO 2026-06-05T18:30:00Z]
```

**Q2 -- Deploy-landed-everywhere (AC-1f):**
```
service:search-api env:prod @deploy.sha:9a8b7c6
| facet @region
| time:[2026-06-05T17:00:00Z TO 2026-06-05T18:30:00Z]
```

**Q3 -- Per-region request volume (AC-2-per-region):**
```
service:search-api env:prod @http.url_details.path:/search
| stats count by @region
| time:[2026-06-05T17:30:00Z TO 2026-06-05T18:30:00Z]
```
Compare to:
```
service:search-api env:prod @http.url_details.path:/search
| stats count by @region
| time:[2026-06-05T16:00:00Z TO 2026-06-05T17:00:00Z]
```

**Q4 -- Error-rate per region (regression negative check):**
```
service:search-api env:prod @http.url_details.path:/search status:error
| stats count by @region
| time:[2026-06-05T17:30:00Z TO 2026-06-05T18:30:00Z]
```

---

## 5. Dashboard panel URLs / scoping

- **Panel A -- `Search Latency by Region`** (Datadog APM dashboard `search-api/latency-by-region`)
  - Query: `max:trace.http.request.p99{service:search-api,resource_name:/search,env:prod} by {region}`
  - Time: hard-coded `2026-06-05T17:30:00Z -> 2026-06-05T18:30:00Z`
  - This is the **only** panel that proves AC-1. The default aggregate panel is NOT acceptable.

- **Panel B -- `Search Volume by Region`** (same dashboard)
  - Query: `sum:trace.http.request.hits{service:search-api,resource_name:/search,env:prod} by {region}.as_rate()`
  - Time: `2026-06-05T16:00Z -> 18:30Z` (spans baseline + post-deploy so the eye can see the shape).

- **Panel C (NEGATIVE CHECK ONLY) -- Datadog SLO `p99 < 200ms aggregate`**
  - This SLO is aggregate-only and DOES NOT prove AC-1.
  - Use it only as the cross-check described in §6.

---

## 6. Negative checks (what would prove the change DID NOT ship, or hides a per-region failure)

1. **Aggregate-vs-per-region divergence (the headline check for this slice).** If Panel C (aggregate SLO) reads "burning ~250ms, slightly breached" but Panel A shows three regions at ~120ms and one region at ~800ms, the aggregate is masking a total per-region failure. Closure rule: **if `max_by_region(p99) - min_by_region(p99) > 300ms`, treat as AC-1 FAIL even if aggregate is below 200ms.** This is the catch for the hidden-failure scenario.
2. **Deploy did not reach a region.** Q2 returns fewer than 4 distinct `@region` values, or one region has zero hits for `@deploy.sha:9a8b7c6`. Implies the rolling deploy stalled in that region.
3. **Routing isolated to one region failed.** Q3 shows one region's volume dropped to ~0 while the other three are at baseline. AC-2 aggregate may still pass if the failed region was a small share of traffic.
4. **No error-rate regression introduced.** Q4 per-region error count for post-deploy window is within ±20% of the equivalent baseline window per region.
5. **No silent no-op.** Datadog metric `search-api.deploys.applied{env:prod,sha:9a8b7c6}` shows 4 region values, each `>=1`.

---

## 7. Rollback trigger checklist

Rollback is **per-region first, all-regions only on confirmed broad regression.**

| Observation                                                                                                          | Page    | Action                                                                                                                                                                                                                          |
|----------------------------------------------------------------------------------------------------------------------|---------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Panel A shows ONE region with `max p99 > 200ms` sustained for 10+ minutes, other three < 200ms.                      | `@bruno` | Per-region rollback: `deploy rollback --service search-api --region <bad-region> --to-sha <previous-sha>`. Do NOT roll back the three healthy regions. Re-run §2 disaggregation 10 min after rollback completes.                |
| Panel A shows TWO OR MORE regions with `max p99 > 200ms` sustained for 10+ minutes.                                  | `@bruno` | All-region rollback: `deploy rollback --service search-api --all-regions --to-sha <previous-sha>`. Confirms broad regression, not a per-region config issue.                                                                    |
| Q4 error rate on `/search` exceeds +50% vs baseline in any region for 5+ minutes.                                    | `@bruno` | Per-region rollback for that region (command as above). Treat as higher priority than the latency trigger.                                                                                                                       |
| AC-2 aggregate volume drops >20% post-deploy vs baseline OR Q3 shows any region at <50% of its own baseline volume.  | `@bruno` | All-region rollback if aggregate; per-region rollback if isolated. Routing regressions tend to be edge/LB-level and full rollback is safer.                                                                                     |
| Q2 shows the deploy never landed in a region (zero hits for `@deploy.sha:9a8b7c6`).                                  | `@bruno` | Do NOT roll back. Re-trigger the regional deploy. Mark AC-1 unverified for that region until landed.                                                                                                                            |

Previous good SHA: to be filled in from `git log --oneline -2 production-deploy.log` at execution time (one line above `9a8b7c6`). Insert as `<previous-sha>` placeholder in commands above.

---

## 8. Verification log (filled at execution time)

```
2026-06-05T18:30:00Z AC-1 per-region results:
  us-east-1:      max p99 = ___ ms   PASS/FAIL
  us-west-2:      max p99 = ___ ms   PASS/FAIL
  eu-west-1:      max p99 = ___ ms   PASS/FAIL
  ap-southeast-1: max p99 = ___ ms   PASS/FAIL
  -> AC-1 verdict: PASS only if all four PASS.

AC-1f deploy landed in regions: [___, ___, ___, ___]
AC-2 aggregate volume delta vs baseline: ___% (PASS if within ±10%)
AC-2 per-region volume deltas: us-east-1 ___% / us-west-2 ___% / eu-west-1 ___% / ap-southeast-1 ___%
Aggregate-vs-per-region divergence: max - min = ___ ms (FAIL if >300ms)
```

---

## 9. Risks surfaced (PROPOSED for `TASK_STATE.md ## Risks to watch`)

- **R-31a (NEW):** Observability stack defaults to aggregate views and the only SLO is aggregate; AC-1 per-region invariant is not natively monitored. Mitigation: panel `Search Latency by Region` must be pinned to the on-call dashboard; consider adding a per-region SLO in a follow-up slice.
- **R-31b (NEW):** Rolling deploy order places `ap-southeast-1` last; any region-specific config issue tends to surface there first and is the most likely single-region failure mode for this slice.

---

### Artifact changes

- PROPOSED: `<task>/POST_DEPLOY_PLAN.md` -- this file (full per-AC signal mapping, per-region disaggregation procedure, negative checks, per-region rollback checklist).
- PROPOSED: `SLICES/31_search-latency.md ## Post-deploy checks` -- summary block (per-region AC-1 evaluation, four-region disaggregation required, link to `POST_DEPLOY_PLAN.md`, rollback per-region first).
- PROPOSED: `TASK_STATE.md ## Risks to watch` -- append R-31a (aggregate-only SLO blind spot) and R-31b (AP rollout-order risk).

### Command transcript

1. Read slice 31 ACs; flagged AC-1 as a per-region invariant against an aggregate-default stack.
2. Inventoried observability (Datadog APM tagged by `region`; SLO is aggregate); built per-region panel + disaggregation query as the load-bearing AC-1 signal.
3. Authored negative check for aggregate-masks-region-blowout (divergence rule `max - min > 300ms`) and per-region rollback ordering.

### Handoff

Next: `slice-closure` to apply the `## Post-deploy checks` PROPOSED block once the verification log in §8 is filled at `18:30Z`. If the divergence rule trips, route to `direction-adjust` for a follow-up slice adding a per-region SLO. Run now: `approve-proposed` to land the `POST_DEPLOY_PLAN.md` + risk entries before execution begins at `17:30Z`.
