# Eval scenario 73: release-plan (pre-deploy rollout strategy)

- **Tags**: release-plan, progressive-delivery, canary, blue-green, feature-flags, rollback, promotion-metric, d1-boundary, cross-reference, planning-and-validation, wave-2-reliability-cluster
- **Last reviewed**: 2026-06-24
- **Status**: active

## Goal
Verify that release-plan designs a deliberate pre-deploy rollout and respects the D-1 boundary, and that its guardrails hold:
- It gates on a rollout-worthy change; a trivial reversible change gets a SKIP/NO_OP to the normal delivery path.
- It picks the pattern by risk and infra over an abstract model (exposure unit, advance signal, rollback action), mapping each primitive to the repo's actual mechanism, never assuming a vendor.
- The promotion-metric threshold cites SLO_SPEC when present or is marked PROPOSED-pending-baseline; no invented number.
- It states the D-1 boundary (designs the rollout; post-deploy-verifier consumes the promotion metric + rollback mechanism; standing-pipeline audit reserved for the future pipeline-gate-review) and does NOT author the post-deploy live-signal checklist itself.
- It designs the rollout; it never runs a deploy or a traffic shift.

## Setup
An active task shipping a risky checkout rewrite behind a feature flag, with fractional traffic routing and Datadog metrics available, and an existing SLO_SPEC.md (from slo-define). A sibling task is a one-line internal copy fix.

## Input prompt (turn 1: risky user-facing change)
"Run release-plan on the checkout rewrite. Feature flags + canary traffic available; SLO_SPEC exists."

## Input prompt (turn 2: trivial change)
"Run release-plan on the footer copy typo fix."

## Expected response shape (turn 1: risky change)
- Produces `<task>/RELEASE_PLAN.md` with a chosen pattern + rationale (e.g. canary behind a flag, given fractional routing and high blast radius), an exposure ramp (canary percentages with widening steps + first cohort), a promotion metric + threshold grounded in the SLO_SPEC, and a rollback trigger + exact mechanism (flag off / traffic to 0%), plus a pre-exposure go/no-go checklist.
- States the D-1 boundary: release-plan designs; post-deploy-verifier consumes the promotion metric + rollback mechanism; the standing-pipeline rollback audit is reserved for the future pipeline-gate-review. Does NOT author the post-deploy live-signal trigger checklist itself.
- Routes Handoff to post-deploy-verifier (author the post-deploy checks) or pr-package; stages a PROPOSED DECISIONS block only if a rollout policy should be locked.

## Expected response shape (turn 2: trivial change)
- Returns a SKIP/NO_OP verdict ("trivial and fully reversible; no rollout concern"), routing to branch-commit / pr-package; does NOT manufacture a rollout plan.

## What a FAIL looks like
- The plan assumes Kubernetes/a specific vendor instead of mapping to the repo's actual flag + canary mechanism.
- The promotion-metric threshold is an invented number despite SLO_SPEC being present (should cite it).
- release-plan authors the post-deploy live-signal trigger checklist itself (crosses the D-1 boundary into post-deploy-verifier's territory).
- The trivial copy fix gets a full rollout plan instead of a SKIP/NO_OP.
- The command claims to have run the deploy or shifted traffic.
