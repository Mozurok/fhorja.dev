# ADR-0077: System-design corpus mining: backend-system-design command plus two reference topics and an eval-harness rollout fold

- **Status**: Accepted
- **Date**: 2026-07-02
- **Tags**: system-design, backend-system-design, wos-topics, cache-strategies, architecture-tradeoffs, ai-feature-eval-harness, mining, additive, charter-bounded

## Context

A mining task (`2026-07-02_system-design-repos-wos-mining`) analyzed three well-known system-design corpora for mechanisms worth folding into the WOS: `donnemartin/system-design-primer` (356k stars), `ashishps1/awesome-system-design-resources` (39k stars, GPL-3.0), and `chiphuyen/machine-learning-systems-design` (thin, self-described as superseded by an O'Reilly book). The method mirrored the earlier `2026-07-01_llm-tooling-repos-absorption-analysis`: capture the sources into `REFERENCES.md`, run an `external-research-fleet` sweep (round 1: one worker per repo plus a WOS-surface census), verify load-bearing claims against the real command files (round 2), then a round-3 deep-dive on the borderline candidates. Full grounding is in the task's `EXTERNAL_RESEARCH.md`.

The corpora are educational and interview-oriented. The WOS charter non-goal is explicit: the WOS is an opinionated workflow for solo and small-team AI-assisted engineering, not a distributed-systems interview trainer. So the worth-it bar was whether a mechanism improves real engineering work for a solo or small-team builder, not whether it is a famous concept. The fleet produced 19 candidates: 3 worth-it, 5 maybe, 11 not-worth-it. The round-3 deep-dive resolved the 5 maybes to 1 build-now, 1 defer-with-trigger, 3 drop. The recurring meta-finding matched `2026-06-30_wos-ai-plan-mechanism-gaps`: famous external corpora mostly describe, in interview language, a rigor the WOS already operationalizes as persistent artifacts (the 4-step "lead the conversation" method is already `impact-analysis` plus `decision-interview` plus `invariants-and-non-goals` plus `implementation-plan`).

## Decision

Build the four accepted folds and nothing else.

- **`backend-system-design` command (net-new).** The strongest finding. `frontend-system-design` exists but had no backend sibling; `impact-analysis` presupposes an existing-code change and `api-contract-review` is endpoint-level, so component-level backend design had no home. A flat command mirroring `frontend-system-design`: a 12-section RFC (problem, requirements, architecture, data model and storage, API contract, caching, scaling and bottlenecks, reliability and SLOs, security, observability, rollout and migration, trade-offs) persisted as `BACKEND_SYSTEM_DESIGN.md`. Capability-routed and scale-honest: it forbids distributed-systems machinery (sharding, multi-region, message bus) without a stated requirement, so it stays inside the solo and small-team charter. Composes with `slo-define`, `performance-budget`, `api-contract-review`, `migration-safety-steward`, and `release-plan`; default-mode only (no `--interview` mode, to stay delivery-focused).
- **`wos/cache-update-strategies.md` (new reference topic).** Names cache-aside, write-through, write-behind, refresh-ahead with when-to-use and the failure mode each invites. A solo builder adds a cache in front of Postgres and gets staleness or stampede wrong; nothing in the repo named these strategies.
- **`wos/architecture-tradeoffs.md` (new reference topic).** The named architecture trade-off pairs as a shared vocabulary the `impact-analysis` "Viable implementation directions" table (and `api-contract-review`, `release-plan`, `backend-system-design`) can cite. Framed for decision capture, not interview recitation.
- **Offline-to-release-plan routing fold into `ai-feature-eval-harness`.** The one maybe promoted to build-now in round 3. Step 5 now states the offline eval pass as `release-plan`'s promotion-metric precondition and names a live proxy metric; `release-plan` is added to the next-command list. Closes a verified routing gap: `release-plan` cited only `SLO_SPEC.md` as a promotion-metric source, never `AI_EVAL_PLAN.md`.

## Consequences

- One net-new command (`backend-system-design`), so the full command blast radius applies: registered in all four registries, `count:commands` 92 to 93, ADR-0077 index row, `count:adrs` 75 to 76, eval scenario 88, `count:scenarios` 87 to 88, generated skill and command catalog regenerated, CHANGELOG entry.
- Two new reference topics, so `count:wos-topics` 26 to 28.
- The `ai-feature-eval-harness` edit regenerates its skill and the catalog; no registry or count change (an edit, not an add).
- GPL-3.0 on the awesome repo is not a licensing issue: the folds lift ideas and named-pair vocabulary, not verbatim text, into AGPL files.

## Alternatives considered

- **Fold the backend design arc into `impact-analysis` instead of a net-new command.** Rejected (D-2): `impact-analysis` is built for the blast radius of an existing change, and a greenfield design mode would mix two intents. A net-new command mirrors the established `frontend-system-design` pattern cleanly.
- **Build some of the five maybe folds.** Round-3 deep-dive verdict: one built (above), one deferred with a named trigger (a REST-vs-RPC transport check in `api-contract-review`, pulled in when the first task proposes a gRPC or tRPC contract; zero grpc/trpc hits in the repo today), and three dropped (a greenfield scale-quantification checklist in `impact-analysis`, a push-vs-pull fourth question in `wos/external-integration-patterns.md`, and a production model drift/retrain policy in `ai-feature-eval-harness`, all charter- or mechanism-mismatched).
- **Adopt the estimation kit, interview framework, FAANG case studies, or the SQL-vs-NoSQL and availability trade-off tables.** Rejected as interview trivia or already-embodied: `stack-recommend` already produces a per-project sourced comparison, and the design discipline is already the WOS's staged workflow.
