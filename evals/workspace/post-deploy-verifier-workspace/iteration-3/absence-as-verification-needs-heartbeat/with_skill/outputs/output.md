## POST_DEPLOY_PLAN.md -- Slice 18: Tighten quota-exceeded scope to premium users only

**Deploy:** `production` @ sha `b2c3d4e` -- window `2026-06-05T13:00:00Z` -> `2026-06-05T14:00:00Z`
**Feature flag:** none (unconditional code-path narrowing)
**Named on-call:** `@bruno`
**Observability stack:** Datadog Logs, PostHog, Postgres

---

### 1. Per-AC signal mapping

| AC   | Claim                                                                                          | Signal class            | Exact query / URL / inputs                                                                                                                                                                                                                                                                                                | Expected result                                                                                                                                  | Owner    |
|------|-----------------------------------------------------------------------------------------------|-------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------|----------|
| AC-1 | Premium users still receive `quota_exceeded` warning when over quota.                          | Datadog log query (positive presence) | `service:quota-engine event:quota_exceeded user.tier:premium deploy_sha:b2c3d4e` over `[2026-06-05T13:00Z, 2026-06-05T14:00Z]`                                                                                                                                                                                          | `count > 0`. Floor: `>= 1 event per 5-min bucket` once the first premium over-quota lands. If `count == 0` after 30 min of traffic -> FAIL.       | `@bruno` |
| AC-1 | Premium emitter actually fires (heartbeat against silent no-op).                              | Postgres invariant (correlated truth) | `SELECT count(*) FROM usage_events WHERE tier='premium' AND used > quota AND ts >= '2026-06-05T13:00:00Z' AND ts < '2026-06-05T14:00:00Z';` (Datadog count for the same window MUST be `>=` 80% of this number -- accounting for sampling)                                                                                | DB count and Datadog count correlate (>= 80%). If DB shows over-quota premiums but Datadog shows zero `quota_exceeded`, the emitter is broken.    | `@bruno` |
| AC-2 | Non-premium users no longer receive `quota_exceeded` warning under any condition.             | Datadog log query (absence)           | `service:quota-engine event:quota_exceeded user.tier:(free OR trial OR basic) deploy_sha:b2c3d4e` over `[2026-06-05T13:00Z, 2026-06-05T14:00Z]`                                                                                                                                                                          | `count == 0`. **MUST be paired with AC-1 positive and the heartbeat signal below -- see §2.**                                                     | `@bruno` |
| AC-2 | Pipeline is alive (distinguishes "expected absence" from "broken log pipeline" -- see §2).     | Datadog log query (heartbeat / canary) | `service:quota-engine event:quota_check_evaluated deploy_sha:b2c3d4e` over `[2026-06-05T13:00Z, 2026-06-05T14:00Z]` -- this is the unconditional per-evaluation log emitted upstream of the tier branch                                                                                                                   | `count > 0` AND tracks pre-deploy 60-min baseline within +/- 30%. If `count == 0` or collapses, AC-2's `count == 0` is meaningless (vacuous).    | `@bruno` |
| AC-3 | /usage page still renders for both tiers.                                                      | PostHog + smoke walkthrough           | PostHog: insight `usage_page_viewed` filtered by `$current_url contains "/usage"`, breakdown by `user.tier`, time range `[13:00Z, 14:00Z]`. Smoke: see §3.                                                                                                                                                                | Both `premium` and `free` cohorts show `pageview` count within +/- 20% of the prior 24h same-hour baseline; no spike in `pageleave` <2s.         | `@bruno` |
| AC-3 | /usage page does not regress server-side.                                                     | Datadog log query (negative-as-health) | `service:web env:production route:/usage status:>=500 deploy_sha:b2c3d4e` over the deploy window                                                                                                                                                                                                                          | `count == 0`. Any 5xx -> page `@bruno`.                                                                                                          | `@bruno` |

---

### 2. AC-2 absence verification -- heartbeat / canary signal (load-bearing section)

**Why this section exists.** AC-2's success criterion is the *absence* of an event. Absence is indistinguishable from "the log pipeline is broken," "the emitter was removed," or "nobody triggered any quota check during the window." A naive verification of AC-2 alone (`count == 0` for non-premium `quota_exceeded`) passes vacuously in all four of those failure modes. The hidden-failure scenario in the brief is exactly this: the emitter was disabled in the same commit, so zero events fire for *anyone*, and the operator confirms AC-2 while AC-1 silently fails.

**Heartbeat construction.** The quota engine evaluates a check on every gated request. The check evaluation is logged *upstream* of the tier branch as `event:quota_check_evaluated` (verify this log line exists in the quota engine -- if it does not, file a follow-up slice to add it; this persona will not paper over its absence). This heartbeat fires regardless of tier and regardless of over/under quota state. It is the ground truth that the runtime path is alive.

**Three-state truth table for AC-2:**

| `quota_check_evaluated` count (heartbeat) | Non-premium `quota_exceeded` count | Premium `quota_exceeded` count | Interpretation                                                                                                       |
|-------------------------------------------|------------------------------------|-------------------------------|----------------------------------------------------------------------------------------------------------------------|
| `> 0` (within +/- 30% of baseline)        | `0`                                | `> 0` and correlates w/ DB    | **AC-2 PASS** -- pipeline alive, premium emitter alive, non-premium emitter correctly silenced.                       |
| `> 0` (within +/- 30% of baseline)        | `0`                                | `0` (DB shows over-quota)     | **HIDDEN FAILURE** -- emitter disabled. AC-2 vacuous, AC-1 broken. **Page `@bruno`, trigger rollback.**               |
| `0` or collapsed (<30% of baseline)       | `0`                                | `0`                           | **PIPELINE BROKEN** -- log shipper, Datadog ingest, or the upstream evaluator is down. AC-2 unverifiable. Page SRE.   |
| `> 0`                                     | `> 0`                              | (any)                         | **AC-2 FAIL** -- scope tightening regressed. Page `@bruno`, trigger rollback.                                         |

**Heartbeat baseline query (run before deploy or against the prior hour):**
```
service:quota-engine event:quota_check_evaluated
  | rollup count by 5-minute buckets over [2026-06-05T12:00Z, 2026-06-05T13:00Z]
```
Capture the per-bucket mean as `baseline_mean`. During the deploy window, the heartbeat MUST stay within `baseline_mean * [0.7, 1.3]`. Anything outside means AC-2 cannot be evaluated and the plan routes to the pipeline-broken row.

---

### 3. AC-1 + AC-2 pair correlation (catches the hidden-broken-logger scenario)

The hidden failure described in the brief -- emitter disabled, all `quota_exceeded` events suppressed -- passes AC-2 vacuously and silently fails AC-1. The plan defeats this by **never evaluating AC-2 in isolation.** The verification protocol is:

**Protocol (must execute as a single block, in order):**

1. **Heartbeat check first.** Run the `quota_check_evaluated` query. If count is zero or collapsed vs baseline -> stop, page `@bruno`, the plan is unverifiable, treat as deploy-suspect and prepare rollback.
2. **AC-1 positive check.** Run the premium `quota_exceeded` query AND the Postgres `usage_events` correlation query in §1 row 2. If DB shows premium over-quota users in the window but Datadog shows zero `quota_exceeded` logs (correlation < 80%), -> **hidden-failure detected.** Page `@bruno`, trigger rollback. Do not proceed to AC-2.
3. **AC-2 absence check, only if steps 1 and 2 PASS.** Run the non-premium `quota_exceeded` query. Now and only now does `count == 0` mean what it claims to mean: the pipeline is alive (step 1), the emitter is alive (step 2), and non-premium is correctly excluded.
4. **AC-3 render check.** PostHog cohort split + smoke walkthrough (§4).

**Smoke walkthrough script (AC-3 + secondary confirmation of AC-1/AC-2):**

| Step | Actor                        | Inputs                                                                                                                                            | Expected                                                                                                                                                  |
|------|------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------|
| 1    | Test premium user `qa_premium@fhorja.test` (over quota: `used=110 / quota=100`) | Navigate to `https://fhorja.app/usage`. Open browser devtools network tab.                                                                        | DOM contains the literal text "You're over your monthly quota". Network: GET `/api/usage` -> 200 with JSON `{ "warning": "quota_exceeded", "tier": "premium" }`. Datadog shows one new `event:quota_exceeded user.tier:premium` log within 30s. |
| 2    | Test free user `qa_free@fhorja.test` (over quota: `used=15 / quota=10`)         | Navigate to `https://fhorja.app/usage`. Open browser devtools network tab.                                                                        | DOM does NOT contain "You're over your monthly quota". Network: GET `/api/usage` -> 200 with JSON that does NOT contain `quota_exceeded`. Datadog shows zero new `event:quota_exceeded user.tier:free` logs and one new `event:quota_check_evaluated user.tier:free`. |
| 3    | Test free user under quota `qa_free_ok@fhorja.test` (`used=5 / quota=10`)       | Navigate to `https://fhorja.app/usage`.                                                                                                           | Page renders, no warning. Datadog shows one new `event:quota_check_evaluated user.tier:free`.                                                              |

If step 2 fails to produce a `quota_check_evaluated` log for the free user, the heartbeat is broken for that tier specifically -> the entire AC-2 verification is invalid; rollback.

---

### 4. Negative checks (explicit, beyond the protocol above)

- `service:quota-engine event:quota_exceeded user.tier:(free OR trial OR basic) deploy_sha:b2c3d4e` over the deploy window -> MUST be zero. (AC-2 primary.)
- `service:quota-engine status:error deploy_sha:b2c3d4e` over the deploy window -> MUST be within +/- 50% of the 60-min pre-deploy baseline. New error class -> investigate.
- `service:web env:production route:/usage status:>=500 deploy_sha:b2c3d4e` -> MUST be zero. (AC-3 server health.)
- PostHog: `usage_page_viewed` total volume during the window MUST be within +/- 30% of the prior 24h same-hour bucket. A collapse implies the page is broken even if 5xx are zero (e.g. blank-page render).
- **Silent no-op deploy check:** `service:quota-engine deploy_sha:b2c3d4e` (any event, any level) over the window MUST be `> 0`. If this returns zero, the new build is not actually serving traffic -> investigate the deploy itself before any AC verdict.

---

### 5. Rollback trigger checklist

| Observation                                                                                                              | Action                                                                                                                                                                  | Who      |
|---|---|---|
| Heartbeat (`quota_check_evaluated`) drops to zero or <30% of baseline within the deploy window.                          | Page `@bruno`. Rollback: `vercel rollback <pre-b2c3d4e deployment-id>` (capture pre-deploy id at 12:55Z). Do NOT close slice.                                            | `@bruno` |
| DB shows premium over-quota users but Datadog shows zero premium `quota_exceeded` (correlation < 80%).                   | Page `@bruno`. **Hidden-failure scenario confirmed.** Rollback: `vercel rollback <pre-b2c3d4e deployment-id>`.                                                          | `@bruno` |
| Any non-premium `quota_exceeded` log during the window.                                                                  | Page `@bruno`. AC-2 regression. Rollback: `vercel rollback <pre-b2c3d4e deployment-id>`.                                                                                | `@bruno` |
| `/usage` 5xx rate > 0 OR PostHog `usage_page_viewed` collapses >30% vs baseline for either tier.                         | Page `@bruno`. AC-3 regression. Rollback: `vercel rollback <pre-b2c3d4e deployment-id>`.                                                                                | `@bruno` |
| Smoke walkthrough step 1 fails to render the premium warning OR step 2 renders the warning for a free user.              | Page `@bruno`. Rollback immediately; do not wait for log corroboration.                                                                                                 | `@bruno` |

No feature flag; rollback is the only mitigation lever. Capture the pre-deploy Vercel deployment id at 12:55Z and pin it in `@bruno`'s on-call note before 13:00Z.

---

### Artifact changes

- `<task>/POST_DEPLOY_PLAN.md` -- **PROPOSED** -- the full plan above.
- `SLICES/18_quota-scope-premium.md` `## Post-deploy checks` section -- **PROPOSED** -- three-line summary linking to `POST_DEPLOY_PLAN.md` and naming the heartbeat as the load-bearing signal for AC-2.
- `TASK_STATE.md ## Risks to watch` -- **PROPOSED** -- add risk: "AC-2 is an absence assertion; verification depends on the `quota_check_evaluated` heartbeat log existing in the quota engine. If that log line is ever removed or renamed, this slice's verification becomes vacuous."

### Command transcript

1. Read slice 18 ACs; classified AC-2 as absence-as-verification.
2. Identified hidden-failure scenario: emitter disabled -> AC-2 passes vacuously, AC-1 fails unobserved.
3. Designed heartbeat (`quota_check_evaluated`) + DB correlation as the two independent anchors that defeat the vacuous pass.
4. Authored protocol ordering AC-1 + heartbeat BEFORE AC-2, and a rollback row dedicated to the hidden-failure signature.

### Handoff

**Next:** `slice-closure` to apply the `## Post-deploy checks` PROPOSED block once the verification protocol has been walked at 13:00Z+.
**Run now:** `approve-proposed` if you want to land `POST_DEPLOY_PLAN.md` and the TASK_STATE risk row immediately.
**On-call:** `@bruno` for the deploy window; pin the pre-deploy Vercel deployment id at 12:55Z.