# ADR-0102: Reliability trio degrades with a floor instead of hard-stopping on missing observability

- **Status**: Accepted
- **Date**: 2026-07-12
- **Tags**: reliability, post-deploy-verifier, slo-define, release-plan, degrade-with-floor, l3-persona, amends-adr-0036-contract, dogfood-driven, theme-dogfood-wave

## Context

The pix-checkout dogfood path (2026-07-11 theme wave) chained `release-plan` into `post-deploy-verifier` as the two commands' own contracts design, and hit a verified internal contradiction: on the identical missing-infra condition (no observability stack), `release-plan` Step 2 degrades gracefully to a manual go/no-go while `post-deploy-verifier` Step 2 hard-STOPs and routes to `decision-interview`, dead-ending the chain even though the verifier's own signal-class list contains infra-free classes (smoke-test walkthrough, DB invariant query, feature-flag check) that need no observability stack at all. `slo-define` had the adjacent gap: its no-observability SKIP gate defined no floor between zero observability and the baseline a container runtime provides free (stdout logs plus a HEALTHCHECK), despite its own required-inputs line counting logs and uptime checks as valid SLI sources. The selfhosted-bookmarks path hit that one.

## Decision

The reliability trio adopts degrade-with-floor semantics. `post-deploy-verifier`: an empty observability inventory no longer stops the run; the plan is authored from the infra-free signal classes only, the observability gap is recorded as a PROPOSED `TASK_STATE.md ## Risks to watch` entry, and the STOP survives only when not even an infra-free signal exists for any acceptance criterion. Its registered do-not-use clause is reworded accordingly (this is the contract change that makes this an ADR: the persona is L3-promoted per ADR-0036 and its frontmatter description is registry-propagated). `slo-define`: process or stdout logs plus an uptime or health check count as a measurable stack for availability-class SLIs (aggregation and retention gaps marked PROPOSED-pending-baseline); SKIP fires only below that floor. `release-plan` is unchanged (it already degraded); the three commands now share one posture on the same condition.

## Consequences

### Positive

- The designed release-plan to post-deploy-verifier chain works on exactly the projects most likely to lack an observability stack (self-hosted, early-stage), which are also the projects where a concrete smoke-test plan has the highest marginal value.

### Negative

- A plan authored from infra-free signals only is weaker than one with real telemetry; the mandatory PROPOSED risk entry keeps that weakness on the record instead of implying full coverage.

### Neutral

- No new command; two Step edits, one description reword, one floor sentence.

## References

- Dogfood evidence: TF-32 (P0 at report time, confirmed as the release-chain contradiction) and TF-9 in `2026-07-11_theme-dogfood-wave2-triage/IMPACT_ANALYSIS.md`.
- Touches the ADR-0036 L3 persona contract for post-deploy-verifier; composes with ADR-0089's reliability folds.
