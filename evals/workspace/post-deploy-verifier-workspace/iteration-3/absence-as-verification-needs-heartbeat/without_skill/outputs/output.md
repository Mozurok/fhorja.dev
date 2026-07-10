# Slice 18 Post-Deploy Verification Plan

Deploy: production, sha=`b2c3d4e`, window 13:00 -> 14:00 UTC
On-call: `@bruno`
Flag: none (code-only behavior change)

---

## 1. Per-AC signal mapping

### AC-1 (positive): Premium users still receive `quota_exceeded` warning when over quota

- **Primary signal (Datadog Logs):**
  `service:quota-engine event:quota_exceeded user.tier:premium env:prod`
  Expected: count > 0 over the 60-minute window, at a rate roughly comparable to the trailing 7-day same-hour baseline (within +/- 50%).
- **Secondary signal (PostHog):**
  Event `quota_exceeded_warning_shown` filtered by `user_properties.tier = premium`.
  Expected: distinct_users > 0 in the window, comparable to baseline.
- **DB cross-check (Postgres):**
  ```sql
  select count(*)
  from quota_events
  where event_type = 'quota_exceeded'
    and tier = 'premium'
    and created_at >= '2026-06-05T13:00:00Z';
  ```
  Expected: > 0 and within baseline band.
- **Pass criterion:** all three sources show non-zero premium `quota_exceeded` activity in the window, and the Datadog count is within +/- 50% of the trailing 7-day same-hour median.

### AC-2 (absence): Non-premium users no longer receive `quota_exceeded` warning

- **Primary signal (Datadog Logs):**
  `service:quota-engine event:quota_exceeded user.tier:(free OR basic OR trial) env:prod`
  Expected: count == 0 over the 60-minute window.
- **Secondary signal (PostHog):**
  Event `quota_exceeded_warning_shown` filtered by `user_properties.tier != premium`.
  Expected: distinct_users == 0.
- **DB cross-check (Postgres):**
  ```sql
  select count(*)
  from quota_events
  where event_type = 'quota_exceeded'
    and tier <> 'premium'
    and created_at >= '2026-06-05T13:00:00Z';
  ```
  Expected: 0.
- **Pass criterion:** absence is observed AND the heartbeat below confirms the pipeline is alive (see section 2). Absence alone is not sufficient.

### AC-3 (still-works): /usage page renders for both tiers

- **Primary signal (Datadog APM / RUM):**
  `service:web route:/usage status:2xx` grouped by `user.tier`.
  Expected: 2xx rate >= 99% for both premium and non-premium cohorts, comparable to baseline. No spike in 5xx or `route:/usage error:*`.
- **Secondary signal (PostHog):**
  Pageview `$pageview` where `$pathname = '/usage'`, split by `tier`. Expected: non-zero pageviews for both tiers, no drop > 30% vs. baseline.
- **Synthetic check:** scripted login as one premium + one free test account, GET `/usage`, assert HTTP 200 and presence of usage table element. Run at T+5min and T+30min.

---

## 2. AC-2 heartbeat / canary: distinguishing "expected absence" from "broken log pipeline"

The hazard: AC-2 expects zero `quota_exceeded` events for non-premium users. A silently disabled log emitter (or broken Datadog forwarder, or a code path that no longer runs at all) would also yield zero events. We need a positive liveness signal from the same emission path to prove that "zero" means "correctly suppressed" rather than "nothing is being logged."

### Heartbeat signals (any one passing is necessary; ideally all three)

**H1. Emitter-level heartbeat log (same code path, same logger):**
The quota engine should emit a lightweight `quota_check_evaluated` log on every quota check, regardless of outcome, carrying fields `tier`, `over_quota: bool`, `warning_emitted: bool`.
- Query: `service:quota-engine event:quota_check_evaluated env:prod`
- Expected: count > 0 in the window, roughly proportional to non-premium request volume (cross-check against `service:web` traffic for the same period).
- This proves the logger and Datadog pipeline are alive for the exact codepath that gates `quota_exceeded`.

**H2. Sibling event from same emitter:**
Confirm a different event type emitted by the same logger module is flowing. e.g. `service:quota-engine event:quota_check_passed env:prod` should have non-zero volume from non-premium users.
- This rules out a logger-instance-level outage scoped to the quota engine.

**H3. Synthetic canary (active probe):**
Run a scripted canary as a non-premium test account that deliberately exceeds quota at T+10min and T+40min in the verification window. The canary user is on an allow-list that EXCLUDES it from the AC-2 zero count (tagged `synthetic:true`).
- Pre-deploy baseline: the canary previously emitted `quota_exceeded` with `synthetic:true`. Post-deploy: the canary should NOT emit `quota_exceeded` (since it's non-premium and the new behavior suppresses it) BUT should emit `quota_check_evaluated` with `over_quota:true, warning_emitted:false`.
- This is the strongest signal: it actively exercises the suppression path and verifies the decision is being made rather than the whole code path being dead.

### Decision rule for AC-2

```
AC-2 PASS  := (count(non_premium quota_exceeded) == 0)
              AND (count(quota_check_evaluated, non_premium) > 0)   // H1
              AND (canary emitted quota_check_evaluated with over_quota:true, warning_emitted:false)  // H3

AC-2 INCONCLUSIVE := absence observed but H1 or H3 also silent -> treat as FAIL, investigate logger health
```

If H1/H3 are silent, do NOT mark AC-2 green. Escalate to "logging pipeline suspected broken."

---

## 3. AC-1 + AC-2 pair correlation: catching the hidden broken-logger scenario

The specific failure described is: log emitter accidentally disabled in same commit. Both premium and non-premium `quota_exceeded` go to zero. AC-2 passes vacuously, AC-1 fails. The operator's attention is on AC-2 (the new behavior) and could miss AC-1's failure.

### Correlation rule (run as a single check, not two separate checks)

```
Hidden-broken-logger detector:

  let premium_count    = count(service:quota-engine event:quota_exceeded user.tier:premium, window=60min)
  let nonprem_count    = count(service:quota-engine event:quota_exceeded user.tier:!premium, window=60min)
  let evaluated_count  = count(service:quota-engine event:quota_check_evaluated, window=60min)
  let premium_baseline = trailing_7d_same_hour_median(premium_count)

  if premium_count == 0 AND premium_baseline > 0:
      -> AC-1 FAIL, page @bruno regardless of AC-2 state
  if nonprem_count == 0 AND evaluated_count == 0:
      -> logging pipeline suspected dead, AC-2 INCONCLUSIVE (not pass), page @bruno
  if nonprem_count == 0 AND evaluated_count > 0 AND premium_count > 0:
      -> AC-1 PASS, AC-2 PASS (genuine suppression)
```

### Operational guardrails

- **Datadog monitor "quota-engine emitter alive":** alert if `service:quota-engine event:quota_check_evaluated` rate drops > 75% vs. trailing 1h baseline. This fires within ~5 min of a logger outage independent of any tier logic.
- **Datadog monitor "premium quota_exceeded suspicious drop":** alert if premium `quota_exceeded` count drops > 80% vs. trailing 7d same-hour median for >= 15 min. This directly catches AC-1 regression and is what fires in the hidden-failure scenario.
- **Verification dashboard layout:** put AC-1 (premium count + baseline ribbon) and AC-2 (non-premium count + heartbeat overlay) side-by-side on one panel so the operator sees both at once. Force the eye to AC-1 by putting it on the left.
- **Checklist enforcement:** the verification checklist must require explicit sign-off on AC-1, AC-2, AC-3 individually. Marking AC-2 green requires pasting the heartbeat query result, not just "zero observed."

---

## 4. Rollback

### Rollback triggers (any single condition during 13:00 -> 14:00 UTC verification window)

- AC-1 FAIL: premium `quota_exceeded` count is 0 over a sustained 15-minute window while `quota_check_evaluated` for premium > 0 (proves suppression is wrong, not pipeline dead).
- AC-1 INCONCLUSIVE for >= 20 min due to logger heartbeat down AND premium baseline > 0: rollback as a safety move; we cannot prove the new behavior is safe.
- AC-2 FAIL: any non-premium `quota_exceeded` event observed in production (other than `synthetic:true` canary) within 30 min of deploy.
- AC-3 FAIL: /usage 5xx rate > 1% sustained 10 min for either tier, or synthetic check fails twice consecutively.
- Customer/support signal: any inbound report from a premium user that quota warning stopped working.

### Rollback procedure

1. `@bruno` declares rollback in the deploy channel, timestamp logged.
2. Revert sha `b2c3d4e` via the standard deploy pipeline (re-deploy previous green sha). No DB migration is involved in this slice, so the revert is code-only and safe.
3. While revert is in flight (~5 min), post a holding comms note: "Quota warning behavior reverted to prior version; investigating."
4. Re-run the same verification dashboard against the prior sha to confirm green: premium `quota_exceeded` non-zero, /usage 2xx healthy, heartbeat alive.
5. Open an incident doc, capture: which signal fired, why the pre-deploy verification missed it, what heartbeat/correlation gap (if any) should be added before re-attempt.

### Post-rollback follow-ups

- If the failure was the hidden-broken-logger scenario: add a pre-merge check that any change touching the quota engine must include or preserve the `quota_check_evaluated` heartbeat emission, and add a CI smoke test that runs the emitter against a local sink.
- If AC-2 failed (non-premium still warned): inspect the tier-check branch; likely a missed code path (e.g. background job or cached tier flag).
- Schedule re-deploy only after the gap is closed and the verification plan is updated.

---

## Verification checklist (operator-facing, 13:00 -> 14:00 UTC)

- [ ] T+5min: Datadog "quota-engine emitter alive" green (heartbeat H1 flowing).
- [ ] T+5min: Synthetic /usage check passes for premium + free test accounts.
- [ ] T+10min: Canary (non-premium, over-quota) emits `quota_check_evaluated` with `warning_emitted:false`, does NOT emit `quota_exceeded`.
- [ ] T+15min: Premium `quota_exceeded` count > 0 and within +/- 50% of 7d same-hour median. (AC-1)
- [ ] T+15min: Non-premium `quota_exceeded` count == 0 AND heartbeat H1 > 0. (AC-2)
- [ ] T+15min: /usage 2xx rate >= 99% for both tiers. (AC-3)
- [ ] T+30min: Repeat AC-1 / AC-2 / AC-3 checks, confirm stability.
- [ ] T+40min: Second canary run, same expectations as T+10min.
- [ ] T+60min: Final sign-off; paste Datadog queries + counts into deploy thread for each AC individually. No "looks good" -- show the numbers.
