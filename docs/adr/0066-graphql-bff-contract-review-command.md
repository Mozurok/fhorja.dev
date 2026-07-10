# ADR-0066: graphql-contract-review command (GraphQL and BFF contract review)

- **Status**: Accepted
- **Date**: 2026-06-29
- **Tags**: graphql, bff, contract-review, federation, design-time-review, discovery-and-scoping, ecosystem-adoption, additive

## Context

The 2026-06-29 staff-frontend role-fit research (the lineage that produced ADR-0065) scored GraphQL and BFF contract review as a MISSING named demand: `api-contract-review` covers REST and HTTP only, with no path for a GraphQL schema, resolvers, federation, or a Backend-for-Frontend contract. The external benchmark (EXTERNAL_RESEARCH.md Angle 2, BFF + GraphQL federation) returned a concrete contract-review checklist explicitly distinct from a REST review: nullability and null-bubbling, errors-as-data unions, N+1 and DataLoader, query cost and depth limits, cursor connections, federation entity ownership, the breaking-change gate, BFF token posture and thinness, and partial-failure degradation. This is the second build item of decision D-1 (GO on a thin, capability-routed frontend cluster) and the first of the three deferred review commands; the frontend system-design RFC command shipped first (ADR-0065).

## Decision

Add `graphql-contract-review`, a capability-routed design-time review of a GraphQL schema and a BFF contract against a 12-step GraphQL-specific checklist (the benchmark items above). It is the GraphQL and BFF counterpart to `api-contract-review`, which owns REST and HTTP: the two share the design-time review role but check different things. It emits findings inline (no artifact file, no template), mirroring `api-contract-review`, and is placed in the discovery-and-scoping cluster.

The command is named by capability, not by stack: it reviews GraphQL on any framework and never assumes one, honoring the charter Non-goal of staying stack-agnostic. A stack-locked name was rejected for that reason.

## Consequences

- `count:commands` rises 85 -> 86; the command is registered in all four registries (WOS `## Command categories` cluster, WOS `## Command roles` index, `wos/command-roles.md`, `COMMAND_PROMPT_STUBS.md`). `count:adrs` rises 64 -> 65.
- Distinct from `api-contract-review` (REST and HTTP), `review-hard` (post-implementation engineering risk), and `repo-consistency-sweep` (pattern matching on already-written code). The command states the REST-versus-GraphQL distinction so the two reviews do not blur.
- The checklist is grounded in captured sources under `REFERENCES.md ## Staff frontend role benchmark (2026-06-29)` (Sam Newman and Phil Calcado on BFF, Apollo federation, Shopify query-cost, the Relay connection spec, errors-as-data, FusionAuth BFF auth) rather than asserted from memory.
- Additive and opt-in: no existing command changes; the command is inert until invoked. The two remaining deferred reviews (a frontend and micro-frontend architecture review, and a React Native performance-budget mode) remain parked for a future task.
