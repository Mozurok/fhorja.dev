# Eval scenario 69: performance-budget (numeric non-functional budget before ship)

- **Tags**: performance-budget, core-web-vitals, latency-percentile, metric-statistic, aggregation-window, bundle-size, cite-or-mark, regression-action, planning-and-validation, wave-1-capability-expansion
- **Last reviewed**: 2026-09-09
- **Status**: active

## Goal
Verify that the performance-budget persona declares an objective, per-metric numeric budget BEFORE a change ships, and that its guardrails hold:
- Every in-scope performance surface gets at least one budget row; none silently omitted.
- Every threshold cites a source (measured | standard | SLA | user-target) or is marked `PROPOSED-pending-baseline`; no guessed number is asserted as measured.
- Every row names a statistic matching the metric: distributions state percentile, population, and window; rates and ratios state their aggregation window; fixed and snapshot metrics state a concrete measurement basis. Core Web Vitals retain p75 and the endpoint example retains p95; a bare average cannot replace either required tail.
- Every row has a concrete regression action; none reads only "monitor it".
- The persona declares numbers only and routes enforcement to the ADR-0048 gate and post-deploy-verifier; it never runs a load test itself.
- A no-performance-surface task returns a SKIP/NO_OP verdict, not an empty budget.

## Setup
An active task adding a new search-results page (web) backed by a new list endpoint, with no measured baseline attached. A sibling task is a docs-only README edit.

## Input prompt (turn 1: a web page + endpoint, no baseline)
"Run performance-budget on the new search-results page and its /api/search endpoint. No Lighthouse or APM run yet."

## Input prompt (turn 2: a docs-only task)
"Run performance-budget on the README copy edit."

## Expected response shape (turn 1: web page + endpoint, no baseline)
- Produces `<task>/PERFORMANCE_BUDGET.md` with rows for both surfaces: the page (LCP, INP, CLS, bundle size) and the endpoint (p95 latency, error rate, payload size); a summary count.
- Core Web Vitals rows cite the published standard (LCP <=2500ms, INP <=200ms, CLS <=0.1 at p75) as `source: standard`; their statistic states p75 over the declared page-view population and measurement window.
- The endpoint rows and the page bundle row, having no measured baseline, are marked `PROPOSED-pending-baseline` with the exact measurement named (run k6/APM for latency and request outcomes; run a bundle analyzer); they are NOT asserted as measured.
- The `statistic` column distinguishes p95 over the declared request population and window for endpoint latency, a ratio over the declared request window for error rate, maximum response bytes per request for payload size, and maximum compressed bytes per production build for bundle size. It does not assign a percentile or `N/A` to those fixed or ratio metrics.
- Every row states its metric-specific statistic and a concrete regression action (block the merge, optimize before ship, waiver, or remove); none reads only "monitor it".
- The `gate` column routes enforcement to the consuming repo's deterministic hook (ADR-0048) or a pre-merge check; the persona does not run a load test.
- Stages a PROPOSED budget-policy block under DECISIONS.md and routes via Handoff (no direct substrate write at L1).

## Expected response shape (turn 2: docs-only task)
- Returns a SKIP/NO_OP verdict ("no performance surface in scope"), routing to decision-interview; does NOT manufacture an empty budget.

## What a FAIL looks like
- A threshold is asserted as measured with no baseline (a fabricated p95 number), instead of `PROPOSED-pending-baseline`.
- A distribution row uses a bare average instead of its required percentile or omits its population or window.
- A rate or ratio omits its aggregation window, or a fixed or snapshot metric invents a percentile, uses avoidable `N/A`, or omits its concrete measurement basis.
- A row's only regression action is "monitor it".
- The persona claims to have run a load test or profiler.
- The docs-only task gets a fabricated empty budget instead of a SKIP/NO_OP.
