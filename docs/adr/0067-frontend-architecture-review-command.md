# ADR-0067: frontend-architecture-review command (architecture review and micro-frontend gate)

- **Status**: Accepted
- **Date**: 2026-06-29
- **Tags**: frontend, architecture, micro-frontends, design-time-review, adopt-gate, discovery-and-scoping, ecosystem-adoption, additive

## Context

The 2026-06-29 staff-frontend role-fit research scored frontend architecture at scale and micro-frontend adoption as gaps: no WOS command reviewed a frontend architecture for scale or decided whether micro-frontends were warranted at all. The external benchmark (EXTERNAL_RESEARCH.md Angle 1, micro-frontends, and Angle 4, frontend architecture at scale) returned both a concrete architecture-review checklist (team-and-domain boundaries, independent deployability, governed shared dependencies, design-system sharing, runtime isolation, cross-app communication, routing and composition tier, performance budget across the composition, governance and failure handling) and a strong caution that micro-frontends are usually unnecessary. This is the third build item of decision D-1 and the second of the three deferred review commands; the frontend system-design RFC (ADR-0065) and the GraphQL/BFF contract review (ADR-0066) shipped first.

## Decision

Add `frontend-architecture-review`, a capability-routed design-time review of a frontend architecture at scale. Its first and most consequential step is a micro-frontend adopt-or-don't-adopt gate that defaults against adoption: it recommends them only when 3 or more teams genuinely need independent deploys, real cross-team coordination pain exists, and boundaries fall on business domains. When micro-frontends are not warranted, the command says so, recommends a modular monolith, and marks the federation-specific checks not applicable. It emits findings inline (no artifact file, no template), mirroring `api-contract-review` and `graphql-contract-review`, and is placed in the discovery-and-scoping cluster.

The command is named by capability, not by stack, honoring the charter Non-goal of staying stack-agnostic. A stack-locked name was rejected for that reason.

## Consequences

- `count:commands` rises 86 -> 87; the command is registered in all four registries (WOS `## Command categories` cluster, WOS `## Command roles` index, `wos/command-roles.md`, `COMMAND_PROMPT_STUBS.md`). `count:adrs` rises 65 -> 66.
- The adopt-or-don't-adopt gate prevents the command from over-prescribing micro-frontends; it is the load-bearing differentiator from a generic architecture checklist.
- Distinct from `frontend-system-design` (designs one system), the contract reviews (`api-contract-review`, `graphql-contract-review`), and `review-hard` (post-implementation engineering risk). It composes with `performance-budget` for the numeric budget rather than re-deriving it.
- The checklist is grounded in captured sources under `REFERENCES.md ## Staff frontend role benchmark (2026-06-29)` (Zalando, Martin Fowler, Luca Mezzalira, the Module Federation docs, AWS server-side micro-frontends, Amex, and frontendatscale) rather than asserted from memory.
- Additive and opt-in. One deferred review remains for a future task: a React Native performance-budget mode that extends `performance-budget`.
