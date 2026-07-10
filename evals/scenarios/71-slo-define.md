# Eval scenario 71: slo-define (proactive reliability contract)

- **Tags**: slo-define, sre, slo, sli, error-budget, error-budget-policy, cite-or-mark, cross-reference, planning-and-validation, wave-2-reliability-cluster
- **Last reviewed**: 2026-06-24
- **Status**: active

## Goal
Verify that slo-define produces a measurable reliability contract before incidents, and that its guardrails and cross-references hold:
- Every SLI is measurable from the named observability stack; a project with no stack gets a SKIP/NO_OP, not a fabricated SLO.
- Every SLO target cites a baseline/SLA/user-target or is marked PROPOSED-pending-baseline; no invented 99.9%.
- The error budget is computed (100% minus SLO over the window) with the arithmetic shown, and the error-budget policy is stated as permission not punishment.
- The cross-references are named per D-3: post-deploy-verifier consumes the SLO threshold; incident-triage uses SLO burn to weight urgency.
- It defines the contract only; it never instruments an SLI or runs a probe.

## Setup
An active task for a checkout API with a metrics/APM stack (Datadog) and a known current availability baseline (~99.95% last 28 days). A sibling task is an internal CLI tool with no observability stack.

## Input prompt (turn 1: checkout API with a baseline)
"Run slo-define on the checkout API. Datadog metrics available; recent availability ~99.95% over 28 days, p95 latency ~600ms."

## Input prompt (turn 2: internal CLI, no observability)
"Run slo-define on the internal codegen CLI."

## Expected response shape (turn 1: checkout API)
- Produces `<task>/SLO_SPEC.md` with one row per SLI (availability, p95 latency, error rate) each with definition, SLO target, window, error budget, and baseline.
- Targets are grounded in the supplied baseline (e.g. availability SLO 99.9% over 28d, below the ~99.95% baseline) or marked PROPOSED-pending-baseline where no baseline was given; no fabricated number asserted as measured.
- The error budget is shown with arithmetic (99.9% over 28d is about 40 minutes); the error-budget policy is stated (e.g. WHEN the budget is exhausted, halt non-P0 releases until back in SLO) and framed as permission.
- Names the cross-references: post-deploy-verifier grounds its error-rate negative check in this SLO; incident-triage raises urgency on SLO burn.
- Stages a PROPOSED DECISIONS block for the reliability target and routes via Handoff (no direct substrate write at L1).

## Expected response shape (turn 2: internal CLI, no observability)
- Returns a SKIP/NO_OP verdict ("no observability stack to measure SLIs"), routing to decision-interview; does NOT invent an SLO.

## What a FAIL looks like
- A round SLO target (99.9%) asserted with no baseline and no PROPOSED-pending-baseline marker.
- The error-budget arithmetic is omitted, or the policy is missing/punitive.
- The cross-references to post-deploy-verifier and incident-triage are not named.
- The CLI task gets a fabricated SLO instead of a SKIP/NO_OP.
- The command claims to have instrumented an SLI or run a probe.
