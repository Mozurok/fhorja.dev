# post-deploy-verifier -- Slice 31: Checkout v2 (behind flag)

Deploy: `production` @ sha `5e4d3c2`, 2026-06-05T16:00:00Z
Flag: `checkout_v2_enabled` in LaunchDarkly project `fhorja-prod` -- 10% authenticated users, segment `us-east`.
Observation window: T0 = 2026-06-05T16:00:00Z through T0+24h.

### Artifact changes

- PROPOSED `<task>/POST_DEPLOY_PLAN.md` (full plan below)
- PROPOSED `SLICES/31_checkout_v2_behind_flag.md` -- new `## Post-deploy checks` section (block at the end)
- PROPOSED `TASK_STATE.md ## Risks to watch` -- new risk row: "checkout_v2 flag rollout is a no-op until LD percentage > 0 in `us-east`; silent-ship class risk."

---

## 1. Per-AC signal mapping table

| AC | Claim | Signal class | Exact query / URL / inputs | Expected result | Owner of check |
|---|---|---|---|---|---|
| AC-1 | When `checkout_v2_enabled=true` for a user, `/checkout` renders the new 3-step form | Smoke-test walkthrough (browser, authenticated test user in flag cohort) + structured log query | Walkthrough §2.1 below; Datadog Logs: `service:checkout-web env:production version:5e4d3c2 @flag.checkout_v2_enabled:true @route:/checkout @event:render_form @form.variant:v2_step1` over `[T0, T0+24h]` | Smoke: DOM contains `data-testid="checkout-v2-step-1-of-3"` and step counter `Step 1 of 3`. Logs: > 0 events; `@form.variant:v2_step1` count ~= 10% of `@route:/checkout @event:render_form` total. | @bruno |
| AC-2 | When the flag is false, `/checkout` renders the legacy 1-step form (no regression for the 90%) | Smoke-test walkthrough (browser, authenticated test user NOT in cohort) + structured log query + Sentry baseline | Walkthrough §2.2 below; Datadog Logs: `service:checkout-web env:production version:5e4d3c2 @flag.checkout_v2_enabled:false @route:/checkout @event:render_form @form.variant:legacy_v1` over `[T0, T0+24h]`; Sentry: project `fhorja-web`, env `production`, release `5e4d3c2`, filter `url:/checkout flag.checkout_v2_enabled:false`, time `[T0, T0+24h]` | Smoke: DOM contains `data-testid="checkout-v1-single-step"` (no `v2` testids present). Logs: `@form.variant:legacy_v1` count ~= 90% of `@route:/checkout @event:render_form` total. Sentry: new-issue count for flag=false cohort = 0 above the pre-deploy 7-day baseline (`<= baseline + 0`). | @bruno |
| AC-3 | Conversion rate for the 10% flagged cohort >= 95% of baseline over 24h (no >5% drop) | PostHog funnel panel + DB invariant query (cross-check) | PostHog funnel: `https://app.posthog.com/project/fhorja-prod/insights/funnel?funnel_id=checkout_conversion&breakdown=feature_flag/checkout_v2_enabled&date_from=2026-06-05T16:00:00Z&date_to=2026-06-06T16:00:00Z` -- steps: `checkout_started` → `payment_submitted` → `order_confirmed`. DB invariant (Supabase, prod read replica): `select (sum(case when v.variant='v2' then 1 else 0 end)::float / nullif(sum(case when v.variant='v2' then 1 else 0 end_started),0)) as v2_conv, (sum(case when v.variant='legacy' then 1 else 0 end)::float / nullif(sum(case when v.variant='legacy' then 1 else 0 end_started),0)) as legacy_conv from analytics.checkout_attempts v where v.created_at between '2026-06-05T16:00:00Z' and '2026-06-06T16:00:00Z';` (replace with project's actual view if `analytics.checkout_attempts` differs -- verify in `CODE_CONTEXT_MAP.md`) | `v2_conv / legacy_conv >= 0.95` AND `v2_conv / pre_deploy_7d_baseline_conv >= 0.95`. PostHog funnel breakdown shows the v2 cohort within ±5% absolute of legacy across all three steps. | @bruno |

Each AC has at least one signal. No orphan ACs. AC-3 is intentionally double-instrumented (PostHog + DB) because conversion is the most expensive signal to be wrong about.

---

## 2. Smoke-test walkthrough script

### 2.1 AC-1 -- flagged user sees v2 (positive smoke)

Pre-req: a seed test account `qa+v2cohort@fhorja.test` that has been manually targeted in LaunchDarkly under `checkout_v2_enabled` → individual targeting → `on` (so we are not gambling on the 10% bucket hashing).

1. In a clean incognito Chrome window, navigate to `https://app.fhorja.com/login`.
2. Sign in as `qa+v2cohort@fhorja.test` / (vault: `1pw://fhorja-prod-qa/checkout-v2-cohort`).
3. Add SKU `SKU-TEST-001` to cart at `https://app.fhorja.com/p/SKU-TEST-001`, click `Add to cart`.
4. Navigate to `https://app.fhorja.com/checkout`.
5. Expected DOM:
   - Element `[data-testid="checkout-v2-step-1-of-3"]` is present.
   - Visible text `Step 1 of 3` appears in `<h1>` or `<header>`.
   - The legacy testid `[data-testid="checkout-v1-single-step"]` is ABSENT.
6. Fill Step 1 (shipping): name `QA V2`, address `1 Test St`, city `Brooklyn`, state `NY`, zip `11201`. Click `Continue`.
7. Step 2 (billing) renders, `[data-testid="checkout-v2-step-2-of-3"]` present. Fill test card `4242 4242 4242 4242`, exp `12/30`, cvc `123`. Click `Continue`.
8. Step 3 (review) renders, `[data-testid="checkout-v2-step-3-of-3"]` present. Click `Place order`.
9. Confirm redirect to `https://app.fhorja.com/order/confirmation?id=<uuid>` and that the resulting log line in Datadog matches the AC-1 query above with `@event:order_confirmed @form.variant:v2_step3`.

### 2.2 AC-2 -- non-flagged user sees legacy (negative-cohort smoke)

1. In a separate clean incognito window, sign in as `qa+legacycohort@fhorja.test` (this account is explicitly excluded from `checkout_v2_enabled` via LD individual targeting → `off`).
2. Repeat steps 3–4 above.
3. Expected DOM at `/checkout`:
   - `[data-testid="checkout-v1-single-step"]` is present.
   - No `[data-testid^="checkout-v2-"]` element exists in the document.
4. Complete the 1-step form (same shipping/billing/test card on one page). Click `Place order`.
5. Confirm redirect to `/order/confirmation` and that the log line carries `@form.variant:legacy_v1`.

---

## 3. Log queries (Datadog Logs)

Time window for every query unless stated: `from:2026-06-05T16:00:00Z to:2026-06-06T16:00:00Z`.

- **Q-render-v2** (AC-1, positive): `service:checkout-web env:production version:5e4d3c2 @flag.checkout_v2_enabled:true @route:/checkout @event:render_form @form.variant:v2_step1`
- **Q-render-legacy** (AC-2, positive): `service:checkout-web env:production version:5e4d3c2 @flag.checkout_v2_enabled:false @route:/checkout @event:render_form @form.variant:legacy_v1`
- **Q-errors-checkout** (AC-2 + AC-3 regression watch): `service:checkout-web env:production version:5e4d3c2 @route:/checkout status:error` -- group by `@flag.checkout_v2_enabled`. Compare each bucket to the 7-day pre-deploy rate.
- **Q-flag-evaluations** (negative check, see §5): `service:checkout-web env:production version:5e4d3c2 @flag.key:checkout_v2_enabled @event:flag_evaluated` -- group by `@flag.value`. The `true` bucket count divided by the total flag-evaluated count is the realized rollout percentage.
- **Q-legacy-codepath** (negative check, see §5): `service:checkout-web env:production version:5e4d3c2 @route:/checkout @event:render_form @form.variant:v2_step1` -- over the **5 minutes BEFORE T0** `[T0-5m, T0]`. If this returns > 0 events, the deploy is not actually new (the v2 code was already shipped earlier) and the AC mapping is unsafe.

---

## 4. Dashboard panel URLs

- **APM error rate, scoped to deploy**: `https://app.datadoghq.com/apm/services/checkout-web?env=production&version=5e4d3c2&panel=error_rate&from_ts=1780848000000&to_ts=1780934400000` (24h window from T0). Compare the post-deploy error rate against the saved 7-day baseline overlay.
- **PostHog conversion funnel (AC-3)**: `https://app.posthog.com/project/fhorja-prod/insights/funnel?funnel_id=checkout_conversion&breakdown=feature_flag/checkout_v2_enabled&date_from=2026-06-05T16:00:00Z&date_to=2026-06-06T16:00:00Z`
- **Sentry release health**: `https://sentry.io/organizations/fhorja/releases/5e4d3c2/?project=fhorja-web&environment=production&statsPeriod=24h`
- **LaunchDarkly flag dashboard (negative check anchor)**: `https://app.launchdarkly.com/projects/fhorja-prod/flags/checkout_v2_enabled/targeting?env=production`

---

## 5. Negative checks (prove the change actually SHIPPED -- not a silent no-op)

The flag-gated shape of this slice makes silent no-op the dominant failure mode: PR merges, sha `5e4d3c2` is live, but if the LD flag is at 0% rollout (or the `us-east` segment definition is empty), nobody sees v2 and casual error-rate watching shows nothing wrong because nothing changed.

- **N-1 (load-bearing flag check)**: At T0+15m and T0+1h, open the LD dashboard `https://app.launchdarkly.com/projects/fhorja-prod/flags/checkout_v2_enabled/targeting?env=production` and visually confirm: (a) flag toggle is `ON` in `production`, (b) rule "10% rollout to segment `us-east`" is present and active, (c) segment `us-east` evaluates to > 0 members (click `View segment` → member count must be > 0). Expected: all three are true. If any is false, the slice DID NOT actually ship to users -- escalate immediately.
- **N-2 (realized rollout %)**: Run `Q-flag-evaluations` for the window `[T0+30m, T0+90m]`. Expected: `count(@flag.value:true) / count(*) ` is between `0.07` and `0.13` (10% ± 30% of itself, allowing for cohort drift). If `< 0.05`, the flag is effectively off despite appearing on; if `> 0.30`, the rollout is mis-scoped and a bigger blast radius than agreed shipped.
- **N-3 (v2 render events exist at all)**: `Q-render-v2` over `[T0, T0+1h]`. Expected: > 0 events. If exactly 0, the v2 code path is unreachable in production -- the JS bundle may have tree-shaken it, or the flag SDK key may be wrong for prod.
- **N-4 (pre-deploy code path)**: `Q-legacy-codepath` over `[T0-5m, T0]`. Expected: 0 events (v2 testid was not present before deploy). > 0 events means we are not actually shipping anything new and the AC mapping is invalid.
- **N-5 (error-rate baseline)**: APM panel error rate on `service:checkout-web @route:/checkout` over `[T0, T0+24h]` should be within ±10% of the 7-day pre-deploy baseline. A FLAT error rate alongside N-1 through N-3 confirming traffic = the change shipped and is healthy. A FLAT error rate ALONGSIDE N-3 showing 0 v2 events = silent no-op (this is the failure mode this whole section exists to catch).

---

## 6. Rollback trigger checklist

Named owner: **@bruno** (sole on-call for `fhorja-prod`). Backup pager: none -- solo founder. If @bruno is unreachable, the rollback action is the same flag-flip and may be executed by any human with LD admin access.

Rollback strategy is flag-flip (no redeploy needed). The deploy stays at sha `5e4d3c2`; only the LD targeting changes.

### Trigger conditions and actions

| # | Observation (with exact panel/query) | Threshold | Page | Action |
|---|---|---|---|---|
| R-1 | PostHog funnel (URL §4) -- `v2_conv / legacy_conv` for `checkout_started → order_confirmed` | `< 0.80` sustained over any 60-min rolling window after T0+2h (gives early traffic time to stabilize) | Page `@bruno` via PagerDuty service `fhorja-checkout` | Execute R-A below |
| R-2 | Sentry release `5e4d3c2`, filter `url:/checkout` (URL §4) -- error rate | `> 2.0%` of `/checkout` sessions over any 10-min rolling window | Page `@bruno` via PagerDuty service `fhorja-checkout` | Execute R-A below |
| R-3 | Datadog APM `service:checkout-web @route:/checkout status:error` rate, breakdown by `@flag.checkout_v2_enabled` | v2 cohort error rate `> 2 * legacy cohort error rate` over any 15-min rolling window | Page `@bruno` | Execute R-A below |
| R-4 | Negative check N-1 fails (flag is off, rule missing, or segment empty) at T0+15m | Any of (a)(b)(c) in N-1 is false | Self-page (Bruno is the operator) | Execute R-B below (re-enable, not rollback) |

### R-A: Rollback (flag-flip to 0%)

1. Open `https://app.launchdarkly.com/projects/fhorja-prod/flags/checkout_v2_enabled/targeting?env=production`.
2. Edit the production rule: change "10% rollout to segment `us-east`" → `0%`. Save with comment `Rollback per R-1/R-2/R-3, ref slice 31, sha 5e4d3c2`.
3. CLI equivalent (preferred for auditability): `ldcli flags update checkout_v2_enabled --project fhorja-prod --env production --rule 'segment:us-east:rollout=0' --comment 'Rollback slice 31 sha 5e4d3c2'`.
4. Within 60s, re-run `Q-flag-evaluations` over `[now-2m, now]`. Expected: `@flag.value:true` count drops to 0. If it does not, fall back to the LD kill switch: toggle flag `OFF` entirely in `production`.
5. Re-run AC-2 smoke walkthrough (§2.2) against `qa+v2cohort@fhorja.test` -- they should now see legacy v1. Confirm.
6. Open a follow-up task via `direction-adjust` with the failed signal attached.

### R-B: Re-enable (the deploy shipped but the flag never took effect)

1. Open the LD URL above.
2. Confirm flag `ON` in `production`, add rule `10% rollout to segment us-east` if absent.
3. Confirm segment `us-east` has > 0 members; if empty, fix the segment definition (likely a missing `country=US AND region IN ('NY','NJ','MA',...)` clause).
4. Re-verify with N-1, N-2, N-3 over `[T0_reenable, T0_reenable+1h]`.

---

## 7. PROPOSED block -- `SLICES/31_checkout_v2_behind_flag.md` → append at end

```markdown
## Post-deploy checks

Deploy: production sha `5e4d3c2` @ 2026-06-05T16:00:00Z. Plan: `POST_DEPLOY_PLAN.md`.

- AC-1 → smoke §2.1 + Datadog `Q-render-v2`. Owner: @bruno.
- AC-2 → smoke §2.2 + Datadog `Q-render-legacy` + Sentry release `5e4d3c2`. Owner: @bruno.
- AC-3 → PostHog funnel (cohort-broken) + Supabase `analytics.checkout_attempts` query. Owner: @bruno.
- Silent-no-op guard: negative checks N-1 (LD dashboard) + N-2 (realized rollout %) + N-3 (v2 render events exist) + N-4 (pre-deploy code path absent). If any fails, slice did not actually ship.
- Rollback: R-1 (conv < 80% of legacy) | R-2 (Sentry `/checkout` errors > 2% / 10m) | R-3 (v2 error rate > 2× legacy / 15m) → page @bruno → flag-flip via `ldcli flags update checkout_v2_enabled --project fhorja-prod --env production --rule 'segment:us-east:rollout=0'`.

Verification window: T0 → T0+24h. Slice may not be closed by `slice-closure` until all three ACs have a green signal AND N-1 through N-3 have confirmed the change shipped.
```

---

## 8. PROPOSED block -- `TASK_STATE.md ## Risks to watch` → append row

```markdown
- **Silent no-op via flag misconfiguration** (slice 31, opened 2026-06-05): `checkout_v2_enabled` ships at sha `5e4d3c2` but is invisible unless LD `production` flag is ON + rule active + segment `us-east` non-empty. Mitigation: negative checks N-1/N-2/N-3 in `POST_DEPLOY_PLAN.md`. Cleanup deadline: flag must be either ramped to 100% or removed by T0+30d (2026-07-05) to avoid stale-flag debt.
```

---

### Command transcript

- Read slice file SLICES/31_checkout_v2_behind_flag.md and identified AC-1, AC-2, AC-3.
- Inventoried obs stack: Datadog Logs + APM, Sentry, PostHog, LaunchDarkly. All five mapped to AC + negative checks.
- Authored 5 negative checks (N-1 through N-5) anchored to LD dashboard + flag-evaluation log query -- silent-no-op is the dominant failure shape for flag-gated slices.
- Rollback checklist names @bruno explicitly and gives the exact `ldcli` command + GUI fallback + post-rollback verification step.

### Handoff

Mode A (compact).

Run now: `approve-proposed` to land `POST_DEPLOY_PLAN.md`, the slice `## Post-deploy checks` section, and the `TASK_STATE.md ## Risks to watch` row in one transaction.

Next: at T0+1h walk negative checks N-1 → N-3 first (catches silent-no-op before you spend time on AC signals); then AC-1 + AC-2 smoke (§2.1, §2.2); then at T0+24h run AC-3 PostHog funnel + DB invariant. If any rollback trigger fires before T0+24h, execute R-A. After the 24h window closes cleanly, route to `slice-closure` to close slice 31.

Why not `verify-against-rubric`: the slice does not yet have a frozen rubric and the verification needs human eyes on LD + PostHog rather than an automatable verdict. Author a rubric only if Checkout v3 reuses this shape.
