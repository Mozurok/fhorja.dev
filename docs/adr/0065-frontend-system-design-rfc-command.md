# ADR-0065: frontend-system-design command (capability-routed frontend RFC)

- **Status**: Accepted
- **Date**: 2026-06-29
- **Tags**: frontend, system-design, rfc, interview-prep, capability-routed, discovery-and-scoping, ecosystem-adoption, additive

## Context

A 2026-06-29 research task (`2026-06-29_wos-staff-frontend-role-fit`) assessed whether the WOS covers a Staff Frontend Engineer role (Wellhub BASE: React, React Native, BFF, micro-frontends, REST and GraphQL, web and mobile at scale). The internal coverage map (IMPACT_ANALYSIS.md) scored 16 role demands: 5 covered, 8 partial, 3 missing. An external AAA benchmark (EXTERNAL_RESEARCH.md, 31 grounded sources across four angles) confirmed the gaps are real staff-frontend practice and returned, for the architecture-and-leadership angle, a stable 12-section frontend system-design document structure that maps onto the GreatFrontEnd RADIO framework (Requirements, Architecture, Data, Interface, Optimizations). The WOS had no command that produces a frontend system-design document: `problem-framing` frames the problem, `impact-analysis` maps blast radius, `implementation-plan` slices the build, and `api-contract-review` reviews one API contract, but none designs a frontend system. The role's mentoring and cross-team-reference demands are human acts; the honest WOS contribution is the artifact-leverage path (a written design doc), not a command that simulates leadership.

## Decision

Add `frontend-system-design`, a capability-routed command that produces a 12-section frontend system-design RFC for the active task (problem and context, requirements, high-level architecture, data model, API and interface contract, rendering and delivery, state management, performance budget, accessibility and i18n, security, rollout and migration, trade-offs and alternatives), covering web and mobile, persisted as `FRONTEND_SYSTEM_DESIGN.md`. A default RFC mode writes the design document for real work; an `--interview` mode reframes the same structure as a RADIO-aligned, time-boxed answer for a frontend system-design interview round (persisted as `FRONTEND_SYSTEM_DESIGN_INTERVIEW.md`), so one command serves both performing in the role and preparing to land it.

The command is named by capability, not by stack: it designs on whatever stack the task uses and never assumes React or React Native. This honors the charter Non-goal of staying stack-agnostic and capability-routed. A stack-locked React/React Native vertical was rejected for exactly that reason. It is placed in the discovery-and-scoping cluster, following the `api-contract-review` precedent (a design-time artifact produced before planning).

This command is the first build item of decision D-1 (GO on a thin, capability-routed frontend cluster). Three review commands surfaced by the same research (a GraphQL/BFF contract review, a frontend/micro-frontend architecture review, and a React Native performance-budget mode) are deferred, not cancelled; a future task revisits them when a project needs them.

## Consequences

- `count:commands` rises 84 -> 85; the command is registered in all four registries (WOS `## Command categories` cluster, WOS `## Command roles` index, `wos/command-roles.md`, `COMMAND_PROMPT_STUBS.md`). `count:adrs` rises 63 -> 64.
- The command composes rather than duplicates: section 8 (performance) references `performance-budget` and section 9 (accessibility) references `a11y-audit` instead of re-deriving them; it produces a design artifact, not a slice plan, so `implementation-plan` still owns slicing.
- The `--interview` mode reuses the same 12 sections, so the WOS serves both the day-to-day design need and the interview-prep need without a second command.
- Additive and opt-in: no existing command changes; the command is inert until invoked. The three deferred review commands remain parked.
- Grounding: the RFC structure is grounded in captured sources under `REFERENCES.md ## Staff frontend role benchmark (2026-06-29)` (RADIO / GreatFrontEnd, StaffEng) rather than asserted from memory.
