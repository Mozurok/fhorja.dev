# ADR-0068: mobile and React Native surface in performance-budget (a mode, not a new command)

- **Status**: Accepted
- **Date**: 2026-06-29
- **Tags**: performance-budget, mobile, react-native, mode, planning-and-validation, ecosystem-adoption, additive

## Context

The 2026-06-29 staff-frontend role-fit research scored mobile runtime performance as a PARTIAL gap: `performance-budget` declared numeric budgets for web (Core Web Vitals), API, DB, and job surfaces, but not for a React Native app, whose metric set is genuinely different. The external benchmark (EXTERNAL_RESEARCH.md Angle 3, React Native performance at scale) returned that metric set: native time-to-interactive measured with a marker view (not a JS timestamp), a frame budget anchored to the 16.67ms physical constant with the JS thread and the UI thread tracked separately, list performance via a recycling list (FlashList) on a low-end device, bundle and memory, and a CI render-regression gate (Reassure). The benchmark also flagged that the circulating "3000ms launch, 500ms render, 55 FPS" defaults are secondary, not an official spec. This is the last of the three deferred review items from decision D-1.

## Decision

Add the mobile and React Native surface to `performance-budget` as a mode and surface extension, not a new command. The precedent is ADR-0061 (the `--spec` mode of `implementation-plan`) and ADR-0063 (the `--tdd` mode of `implement-approved-slice`): a mode of an existing command warrants an ADR but needs no `count:commands` bump and no four-registry registration. Step 2 (pick metrics per surface) gains a `Mobile (React Native, via a named mobile surface or --mobile)` entry, and a dedicated mobile budget block specifies the metric set above. The block keeps the persona honest: it marks the circulating RN defaults `PROPOSED-pending-baseline`, tiers budgets by device class, and anchors the frame budget to 16.67ms rather than a recalled number.

## Consequences

- No `count:commands` change (it stays 87): this is a mode of an existing folder-shaped command, edited in `commands/performance-budget/SKILL.md` and regenerated to `.claude/skills/performance-budget/SKILL.md`. `count:adrs` rises 66 -> 67.
- `performance-budget` now covers web, API, DB, job, and mobile/React Native surfaces in one command, picking the metric set per surface rather than fragmenting into per-platform commands.
- The mobile block composes with the existing Step 5 budget table (the same columns hold a mobile surface row) and the Step 6 route-do-not-run rule (the persona still never runs a profiler; it declares the budget and routes execution to the CI gate and `post-deploy-verifier`).
- The metric set is grounded in captured sources under `REFERENCES.md ## Staff frontend role benchmark (2026-06-29)` (the React Native New Architecture and Performance docs, React Native DevTools, Shopify FlashList, and Callstack Reassure) rather than asserted from memory.
- This completes the D-1 frontend cluster: 4 of 4 build items shipped (frontend-system-design ADR-0065, graphql-contract-review ADR-0066, frontend-architecture-review ADR-0067, and this mode ADR-0068).
