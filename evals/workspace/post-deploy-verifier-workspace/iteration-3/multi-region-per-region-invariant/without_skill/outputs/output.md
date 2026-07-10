# Post-Deploy Verification Plan -- Slice 31: /search latency optimization

**Deploy:** production, sha `9a8b7c6`, started 2026-06-05T17:00:00Z, rolling across 4 regions (~30 min)
**Regions:** `us-east-1`, `us-west-2`, `eu-west-1`, `ap-southeast-1`
**On-call:** `@bruno`
**Verification window:** T+0 (17:00 UTC, deploy start) through T+90min (18:30 UTC) -- 60 min for full rollout + 30 min steady-state observation post-last-region.

---

## 1. Per-AC signal mapping

| AC | Statement | Primary signal | Source | Aggregation | Pass threshold | Window |
|---|---|---|---|---|---|---|
| AC-1 | p99 latency on `/search` drops below 200ms in **each** region post-deploy | `trace.http.request.duration` p99, filtered to `service:search resource_name:/search`, **grouped by `region`** (NOT aggregated) | Datadog APM | `p99` per `region` tag, 5-min rolling | **All 4 regions** < 200ms simultaneously for ≥ 15 min of steady-state post-deploy-complete | T+30 to T+90 min |
| AC-2 | Total `/search` request volume does not drop (routing not broken) | `trace.http.request.hits` count, sum across all regions | Datadog APM | `sum:hits` per 5-min bucket | Post-deploy 15-min avg ≥ 90% of pre-deploy 60-min avg (baseline = 16:00–17:00 UTC same day) | T+30 to T+90 min |
| AC-2 (per-region guard) | No single region's traffic collapses (partial routing break) | Same `hits` metric, **grouped by `region`** | Datadog APM | `sum:hits` per `region`, 5-min bucket | No region drops below 70% of its own pre-deploy baseline | T+30 to T+90 min |

**Critical note on existing SLO:** the configured Datadog SLO `p99 < 200ms aggregate` is **NOT a valid signal for AC-1** and MUST NOT be relied on for sign-off. The AC is a per-region invariant; the aggregate SLO can mask single-region failure (see §3). Treat the SLO widget as informational only.

---

## 2. Per-region disaggregation for AC-1 (explicit)

The default Datadog panel aggregates across regions and will hide the failure mode in the hidden-failure scenario. Verification MUST disaggregate.

**Required query (Datadog APM, paste-ready):**

```
p99:trace.http.request.duration{service:search,resource_name:/search,env:production} by {region}
```

**Required panel:** 4 separate time-series lines (one per region), shared y-axis 0–1000ms, horizontal threshold line at 200ms.

**Per-region pass table -- must be filled in at T+90min before sign-off:**

| Region | Pre-deploy p99 (16:00–17:00 UTC) | Post-deploy p99 (T+30 to T+90 steady) | < 200ms? | Notes |
|---|---|---|---|---|
| `us-east-1` | ___ ms | ___ ms | Y / N | |
| `us-west-2` | ___ ms | ___ ms | Y / N | |
| `eu-west-1` | ___ ms | ___ ms | Y / N | |
| `ap-southeast-1` | ___ ms | ___ ms | Y / N | |

**Decision rule:** AC-1 passes **only if all 4 cells are Y**. Three-of-four is a FAIL, not a partial pass.

**Why this matters (worked example of the hidden failure):** if us-east, us-west, eu-west land at ~120ms each and ap-southeast-1 stays at ~800ms, traffic-weighted aggregate p99 lands around ~250ms. The aggregate SLO widget shows "barely breached" -- easy to dismiss as noise. The per-region view shows one region at 4x threshold. The per-region view is the source of truth for AC-1.

---

## 3. Negative checks (catch hidden per-region failures)

These are explicit "if I see X, AC-1 has failed even if the aggregate looks fine" checks. Each must be evaluated before sign-off.

**NC-1: Per-region threshold breach (primary)**
- Query: `p99:trace.http.request.duration{service:search,resource_name:/search} by {region}`
- Trigger: any region's p99 > 200ms for ≥ 10 consecutive minutes during the T+30 to T+90 window.
- Action: AC-1 FAIL. Do not sign off. Proceed to §4 rollback decision.

**NC-2: Region-spread anomaly**
- Query: `(max:trace.http.request.duration.p99{...} by {region}) - (min:trace.http.request.duration.p99{...} by {region})`
- Trigger: spread > 300ms between worst and best region.
- Rationale: even if all 4 regions are < 200ms, a large spread suggests config drift in one region and is worth investigating before sign-off.
- Action: investigate before sign-off; not an automatic FAIL but a hold.

**NC-3: Aggregate-vs-region disagreement**
- Manual check: compare aggregate p99 (existing SLO widget) against the worst per-region p99.
- Trigger: aggregate < 200ms BUT any single region > 200ms.
- Rationale: this is exactly the hidden failure mode in the scenario. The aggregate-only SLO is structurally blind to it.
- Action: AC-1 FAIL. The aggregate SLO is misleading; trust the per-region view.

**NC-4: Per-region traffic collapse (catches "p99 looks great because no one is hitting that region")**
- Query: `sum:trace.http.request.hits{service:search,resource_name:/search} by {region}` vs. same query 1h ago.
- Trigger: any region's request count drops > 30% vs. its own pre-deploy baseline.
- Rationale: a region with collapsed traffic will show artificially low p99. AC-1 "drops below 200ms" must be on real traffic, not on absence of traffic.
- Action: AC-2 FAIL (routing broken in that region). Investigate before signing AC-1.

**NC-5: Error rate per region**
- Query: `sum:trace.http.request.errors{service:search,resource_name:/search} by {region} / sum:trace.http.request.hits{...} by {region}`
- Trigger: any region's error rate > 2x its pre-deploy baseline.
- Rationale: a deploy can cut p99 by failing fast. Verify latency improvement is on successful requests.
- Action: investigate; latency win on errors is not a real win.

**Sign-off gate:** all five negative checks must be evaluated and recorded in the verification log. Default-view dashboards (cross-region aggregate) are explicitly insufficient.

---

## 4. Rollback plan -- per region OR all-regions

The deploy is rolling and per-region, so rollback can be scoped. Decision tree:

### 4a. Rollback decision matrix

| Failure scope | Action | Rationale |
|---|---|---|
| 1 region fails NC-1 or NC-3, other 3 healthy | **Per-region rollback** of failing region only | Minimize blast radius; preserve latency win in healthy regions; isolate to investigate config drift (likely cause given scenario) |
| 2 regions fail | **Per-region rollback** of both, hold deploy in remaining 2 pending RCA | Pattern suggests environmental/config issue, not code; partial rollback buys investigation time |
| 3 or 4 regions fail | **All-regions rollback** to prior sha | Code-level regression likely; full revert is safest |
| AC-2 fails (traffic collapse) in any region | **All-regions rollback** | Routing break is a correctness issue, not a performance issue; do not leave any users routed to a broken region |
| NC-5 fails (error spike) in any region | **All-regions rollback** | Error-rate regression takes precedence over latency wins |

### 4b. Per-region rollback procedure (scenario: `ap-southeast-1` only)

1. `@bruno` confirms failure in `#deploys` with the per-region panel screenshot and pre/post p99 numbers from the table in §2.
2. Trigger rollback for the failing region only (deploy tooling region scope: `--region ap-southeast-1 --sha <prior-sha>`).
3. Drain in-flight requests (~60s) before redeploying prior sha.
4. Verify the rolled-back region returns to its pre-deploy p99 baseline within 15 min.
5. Leave healthy regions on the new sha `9a8b7c6`.
6. Open an incident ticket for the failing region with: per-region p99 graph, config diff between healthy and failing region, deploy log from the failing region.
7. Do **not** declare the slice complete. Slice status: PARTIAL -- 3/4 regions on new sha, 1/4 reverted, awaiting RCA before re-attempting `ap-southeast-1`.

### 4c. All-regions rollback procedure

1. `@bruno` declares rollback in `#deploys` and `#incidents`.
2. Trigger rollback across all 4 regions in parallel (deploy tooling: `--all-regions --sha <prior-sha>`).
3. Verify each region returns to baseline p99 within 15 min -- same per-region disaggregation required (do not trust aggregate).
4. Slice status: REVERTED. Open RCA ticket before re-attempting the slice.

### 4d. Rollback verification (mirrors §2 and §3)

After any rollback, re-run the per-region p99 panel and NC-1 through NC-5. A rollback is not "done" until every affected region is back inside its pre-deploy baseline, verified per-region, not in aggregate.

---

## Sign-off checklist

- [ ] Per-region p99 table in §2 filled in, all 4 regions < 200ms
- [ ] NC-1 evaluated: no region breached 200ms for ≥ 10 min
- [ ] NC-2 evaluated: region spread < 300ms (or holds investigated)
- [ ] NC-3 evaluated: aggregate and worst-region agree on PASS
- [ ] NC-4 evaluated: no per-region traffic collapse
- [ ] NC-5 evaluated: no per-region error-rate regression
- [ ] AC-2 total volume check passed
- [ ] Verification window T+30 to T+90 fully observed
- [ ] Sign-off logged by `@bruno` with screenshots of the per-region panel (NOT the default aggregate panel)

**Hard rule:** the existing `p99 < 200ms aggregate` SLO is **not** an acceptable sign-off signal for this slice. AC-1 is a per-region invariant and must be verified per-region.
