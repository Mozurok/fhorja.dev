# Post-Deploy Verification Plan -- Slice 31: Checkout v2 (behind flag)

**Deploy:** production, sha `5e4d3c2`, ts `2026-06-05T16:00:00Z`
**Feature flag:** `checkout_v2_enabled` (LaunchDarkly project `fhorja-prod`)
**Rollout target:** 10% of authenticated users in `us-east` segment
**On-call:** `@bruno`
**Verification window:** T+0 to T+24h after deploy

---

## 0. Core risk being verified

This slice is gated by a feature flag. Two things must both be true for the deploy to be considered "shipped":

1. The new code path is **present** in the running production binary (sha `5e4d3c2` is live).
2. The flag `checkout_v2_enabled` is actually **evaluating to true for ~10% of the target segment**.

If only (1) is true and (2) is not, the deploy is a **silent no-op**: the PR is merged, the runtime is unchanged, error rates look flat, and "everything looks green" -- but the change has not actually shipped. Baseline error-rate dashboards will not catch this. The verification below treats the flag-evaluation signal as a first-class artifact, not an assumption.

---

## 1. Per-AC signal mapping

For each acceptance criterion: the source of truth, the exact query/check, the pass threshold, the timing window, and who runs it.

### AC-1 -- Flagged users (`checkout_v2_enabled=true`) see the new 3-step form

| Field | Value |
|---|---|
| Primary signal | PostHog event `checkout_step_viewed` with property `flow_version="v2"` and `step` in `{1,2,3}` |
| Secondary signal | Datadog APM: route `/checkout` with tag `flow_version:v2` shows non-zero RPM |
| Tertiary signal (proof of flag evaluation) | LaunchDarkly "Flag insights" tab for `checkout_v2_enabled`: served-true count > 0 in last 1h, and matches ~10% of total evaluations |
| Pass threshold | (a) ≥1 distinct user_id emits `step=2` AND `step=3` events within T+30min (proves the multi-step flow rendered, not just the entry page); (b) LaunchDarkly served-true ratio is between 8% and 12% over 1h |
| Window | T+0 to T+1h (initial), then re-checked at T+24h |
| Owner | `@bruno` |
| Failure mode this catches | Code shipped, flag never lit up → no `v2` events ever appear (the silent no-op case) |

### AC-2 -- Non-flagged users (`checkout_v2_enabled=false`) see the legacy 1-step form (no regression for the 90%)

| Field | Value |
|---|---|
| Primary signal | PostHog event `checkout_completed` segmented by `flag_state` property (sent on every `/checkout` view); `flag_state="control"` cohort conversion rate vs. trailing 7-day baseline |
| Secondary signal | Datadog APM: route `/checkout` with tag `flow_version:v1` -- p50/p95 latency and error rate within ±10% of trailing 7-day baseline |
| Tertiary signal | Sentry: no new issue fingerprints on `/checkout` tagged `flow_version:v1` since deploy |
| Pass threshold | Control cohort conversion within ±3% of baseline; v1 error rate < 1% (matching pre-deploy); zero new Sentry issues on v1 path |
| Window | T+0 to T+24h, sampled at T+1h, T+6h, T+24h |
| Owner | `@bruno` |
| Failure mode this catches | Shared code path (cart, pricing, auth) accidentally broken by v2 refactor and regresses the 90% who are still on v1 |

### AC-3 -- Conversion in flagged cohort ≥ 95% of baseline over 24h window

| Field | Value |
|---|---|
| Primary signal | PostHog funnel: `checkout_started` → `checkout_completed`, filtered to `flag_state="treatment"` cohort, compared against trailing 7-day baseline of the same segment (authenticated, us-east) |
| Secondary signal | Stripe / payments backend: completed payment intents tagged with the user's flag-evaluation context (or matched via user_id join), treatment cohort vs. control |
| Tertiary signal | Datadog APM: 5xx rate on `POST /api/checkout/submit` for `flow_version:v2` vs `v1` (proxy for "did the submission actually go through") |
| Pass threshold | `treatment_conversion / baseline_conversion ≥ 0.95` over the rolling 24h window with n ≥ 200 attempts in the treatment cohort (below n=200 the signal is too noisy to call) |
| Window | Evaluated at T+6h (interim, advisory only), T+24h (canonical) |
| Owner | `@bruno` |
| Failure mode this catches | v2 form is rendering but is confusing/broken enough that users drop off without errors (no Sentry, no 5xx -- just lost revenue). This is the failure casual monitoring misses. |

---

## 2. Negative check: proof that the change DID ship (flag-eval signal)

This is the single most important check. The rest of this plan is meaningless if the flag is dark.

**The check:** within **T+30 minutes** of deploy completion, the following three things must all be true. If any one is false, the deploy is a no-op and must be treated as a flag-config incident even though nothing is "broken."

1. **LaunchDarkly is evaluating the flag in production.**
   - URL: `https://app.launchdarkly.com/projects/fhorja-prod/flags/checkout_v2_enabled/insights`
   - Required: "Evaluations in last 1h" > 0 for the `production` environment.
   - Required: `served: true` count > 0 AND falls between 8% and 12% of total evaluations.
   - If `served: true` count is 0 → flag is misconfigured (targeting rule, segment definition, or kill switch is off). The code shipped but no user is hitting it. **This is the silent no-op.**

2. **PostHog has received at least one `v2` event from a real user.**
   - Query: `SELECT count(distinct distinct_id) FROM events WHERE event = 'checkout_step_viewed' AND properties.flow_version = 'v2' AND timestamp > '2026-06-05T16:00:00Z'`
   - Required: result ≥ 1 within T+30min, ≥ 10 within T+2h.
   - If result is 0 at T+30min while LaunchDarkly shows served-true > 0 → instrumentation gap (flag is on but we can't see it). Treat as observability incident, not a rollback.

3. **Datadog APM shows traffic on the new code path.**
   - Query: `service:fhorja-web resource_name:GET_/checkout @flow_version:v2`
   - Required: non-zero request count in last 30min.
   - If zero → either the flag is dark (cross-check with #1) or the APM tag isn't being emitted (instrumentation gap).

**What this negative check proves:** the deploy is not a silent no-op. The new code is reachable, the flag is evaluating, and users are actually hitting v2. Without this check, AC-2 will pass trivially (because everyone is on v1) and AC-3 will have an empty treatment cohort, and the team will believe the deploy succeeded when in fact nothing changed.

**Trap to avoid:** "no Sentry errors on `/checkout`" is NOT proof the change shipped. It is equally consistent with "the change shipped and is clean" and "the change did not ship at all." The only positive proof is the three signals above.

---

## 3. Rollback trigger checklist

### 3.1 Named humans

- **Primary on-call:** `@bruno` (decision authority + executor)
- **Backup / second pair of eyes:** none designated for this slice -- `@bruno` is solo. If unavailable for >30min during the verification window, the rollback authority defers to whoever has LaunchDarkly write access in the `fhorja-prod` project. Document this gap; do not let it block the rollback.

### 3.2 Rollback trigger thresholds (any one of these fires → rollback)

| # | Signal | Source | Threshold | Window |
|---|---|---|---|---|
| R1 | Treatment-cohort conversion drop | PostHog funnel `checkout_started → checkout_completed`, `flag_state="treatment"` | `treatment_conversion / baseline_conversion < 0.80` | rolling 1h, with n ≥ 50 attempts in window |
| R2 | Sentry error rate on `/checkout` (v2 path) | Sentry, filter `flow_version:v2` | error rate > 2% of requests | rolling 10min |
| R3 | Datadog APM 5xx rate on `/checkout` (v2 path) | Datadog APM, `service:fhorja-web resource:GET_/checkout @flow_version:v2` | 5xx rate > 2% | rolling 10min (cross-check on R2) |
| R4 | Unexpected expansion of blast radius | LaunchDarkly insights | `served: true` ratio > 20% (i.e. rollout is hitting more users than the intended 10%) | any 5min sample |

R1 is the canonical revenue-protection trigger. R2/R3 are the canonical error-protection triggers. R4 is a safety net against misconfigured targeting rules suddenly broadening exposure.

### 3.3 Exact rollback command (flag-flip)

Rollback is a flag-flip, not a redeploy. Two equivalent execution paths -- use whichever is faster:

**Path A -- LaunchDarkly UI (preferred, fastest):**
1. Open `https://app.launchdarkly.com/projects/fhorja-prod/flags/checkout_v2_enabled/targeting?env=production`
2. Under "Default rule" / the 10% rollout rule, set rollout to `0%` (or toggle the flag's kill switch to off).
3. Confirm the "Save changes" dialog.
4. Verify `served: true` count drops to 0 within 60 seconds on the Insights tab.

**Path B -- LaunchDarkly REST API (scriptable fallback if UI is degraded):**

```bash
curl -X PATCH \
  "https://app.launchdarkly.com/api/v2/flags/fhorja-prod/checkout_v2_enabled" \
  -H "Authorization: $LD_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "environmentKey": "production",
    "instructions": [
      { "kind": "turnFlagOff" }
    ],
    "comment": "Rollback Slice 31 -- triggered by <R1|R2|R3|R4> at <timestamp>"
  }'
```

Expected response: `200 OK`. Verify by re-running the negative check (Section 2) -- `served: true` should now be 0.

### 3.4 Post-rollback verification (within 10 min of flag-flip)

1. LaunchDarkly Insights: `served: true` count = 0 for `production`.
2. PostHog: no new `checkout_step_viewed` events with `flow_version=v2` after the flip timestamp.
3. Datadog APM: traffic on `@flow_version:v2` decays to 0 within ~5min (allowing for in-flight sessions).
4. Sentry: error rate on `/checkout` returns to baseline within 15min.
5. Confirm AC-2 path (legacy v1) is now serving 100% of traffic and conversion is at baseline.

### 3.5 What rollback does NOT require

- It does NOT require a code revert. Sha `5e4d3c2` stays in production; the dead-code path is dormant.
- It does NOT require a redeploy. The flag-flip is the rollback.
- A subsequent code revert is only needed if the dormant v2 code is somehow affecting the v1 path (which AC-2 is specifically testing for). If AC-2 is failing, escalate to a code revert, not just a flag-flip.

---

## 4. Verification timeline summary

| Time | Action | Owner |
|---|---|---|
| T+0 (deploy completes) | Confirm sha `5e4d3c2` is live in production | `@bruno` |
| T+15min | Run the negative check (Section 2, all 3 sub-checks) | `@bruno` |
| T+30min | If negative check fails → treat as flag-config or instrumentation incident, do NOT proceed to AC verification | `@bruno` |
| T+1h | First AC-1, AC-2 pass; first R1/R2/R3 trigger check | `@bruno` |
| T+6h | Interim AC-3 read (advisory only) | `@bruno` |
| T+24h | Canonical AC-3 read; close verification or extend window | `@bruno` |
| Anytime in window | If any R1–R4 fires → execute Section 3.3 rollback | `@bruno` |

---

## 5. Known gaps / things this plan does not cover

- **Solo on-call.** `@bruno` is the only named human. There is no escalation path if unavailable. This is an accepted risk for this slice but should be raised before the next gated rollout.
- **n-threshold on AC-3.** The n ≥ 200 floor is a judgment call. If 24h traffic is lower than expected, extend the window before declaring AC-3 a pass or fail -- do not declare on noisy data.
- **Stripe-side reconciliation.** The plan uses PostHog `checkout_completed` as the conversion source. A 24h post-window reconciliation against Stripe-completed payment intents is recommended to catch the case where PostHog fired but the payment never settled.
