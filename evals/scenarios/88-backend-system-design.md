# Eval scenario 88: backend-system-design produces a scale-honest 12-section backend RFC

- **Tags**: ADR-0077, backend-system-design, system-design, scale-honest, capability-routed, additive
- **Last reviewed**: 2026-07-02
- **Status**: active

## Goal

Validates **ADR-0077** as delivered by `backend-system-design`. Given an active task to design a new backend service or feature, the command must produce a 12-section backend system-design RFC (problem, requirements, high-level architecture, data model and storage, API and interface contract, caching and data access, scaling and bottlenecks, reliability and SLOs, security, observability, rollout and migration, trade-offs), persist it as `BACKEND_SYSTEM_DESIGN.md`, stay capability-routed (design for the stack the task actually uses, never assume one), stay scale-honest (no sharding, multi-region, or message-bus machinery without a stated requirement), assert no scale or SLO number without a source or a `PROPOSED-pending-baseline` mark, and write no product code. It is the backend sibling of `frontend-system-design` and composes with `slo-define`, `performance-budget`, `api-contract-review`, `migration-safety-steward`, and `release-plan` rather than duplicating them.

This exercises:

- The 12-section completeness rule: every section present, or marked `not applicable` with a reason.
- Scale-honesty: a solo-scale task (for example a small-team app on a single Postgres) does not get a sharded, multi-region, queue-heavy design; distributed-systems machinery appears only when a stated requirement forces it.
- No invented metrics: scale numbers, latency targets, and SLOs cite a source or are marked `PROPOSED-pending-baseline`.
- Composition, not duplication: reliability targets route to `slo-define`, the endpoint audit to `api-contract-review`, DDL safety to `migration-safety-steward`, and the rollout to `release-plan`; the cache choice cites `wos/cache-update-strategies.md` and the trade-offs cite `wos/architecture-tradeoffs.md`.
- Locked-decision respect: a decision the design needs but does not have is marked `PROPOSED` and routed to `decision-interview`, never asserted.
- The non-empty trade-offs section naming the rejected options.
- No product code is written; the output is a design document.

## Input prompt (representative)

Run `@commands/backend-system-design.md` for an active task designing a new "saved searches with email digest" backend feature on an existing Node plus Postgres app (small team, low thousands of users). Expected scale: unknown beyond the current user base. Produce `BACKEND_SYSTEM_DESIGN.md`.

## Expected response shape

- All 12 sections present; the expected-scale line in Requirements states the known user base and marks the rest `unknown` rather than inventing a peak.
- The design uses the existing Postgres (a periodic digest job or a lightweight queue at most), and explicitly does not introduce sharding, a multi-region topology, or a heavyweight message bus, because no requirement forces them.
- Any latency or SLO target cites a source or is marked `PROPOSED-pending-baseline`.
- Reliability routes to `slo-define`; the endpoint contract composes with `api-contract-review`; any schema change routes to `migration-safety-steward`; the rollout composes with `release-plan`.
- The trade-offs section names the rejected options (for example cron digest vs event-driven) citing `wos/architecture-tradeoffs.md`.
- The artifact is marked APPLIED (Agent) or PROPOSED (Ask); no product code is emitted; the response ends with a complete Handoff.

## Pass criteria

1. All 12 sections are present (or `not applicable` with a reason); the trade-offs section is non-empty and names rejected options.
2. The design is scale-honest: no sharding, multi-region, or message-bus machinery without a stated requirement; a solo or small-team scale gets a single-Postgres-shaped answer.
3. No scale, latency, or SLO number is asserted without a cited source or a `PROPOSED-pending-baseline` mark.
4. The command composes with (does not duplicate) `slo-define`, `api-contract-review`, `migration-safety-steward`, and `release-plan`, and cites the two new `wos/` topics where relevant.
5. No product code is written; `BACKEND_SYSTEM_DESIGN.md` is persisted per editor mode; the Handoff `Run now` line names a real `commands/<name>.md` basename.

## Fail signals

- A section is dropped without a `not applicable` reason, or the trade-offs section is empty.
- The design imports sharding, multi-region, or a message bus with no requirement forcing it (charter violation: interview-scale cargo-culting).
- A scale or SLO number is asserted with no source and no `PROPOSED-pending-baseline` mark.
- The command re-implements `slo-define`, `api-contract-review`, or `release-plan` instead of composing with them.
- Product code is written, or the Handoff is dropped or names a non-existent command.
