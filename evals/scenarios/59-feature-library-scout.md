# Eval scenario 59: feature-library-scout (per-feature library vetting)

- **Tags**: ADR-0045, feature-library-scout, feature-library-scout-fleet, adoption-signals, stack-recommend-boundary, optional-guidance, golden-set
- **Last reviewed**: 2026-06-20
- **Status**: active

## Goal

Validates **ADR-0045** (feature-library research cluster) as delivered by `feature-library-scout` and its fleet variant. Given a chosen stack and a product feature set, the command must surface the community-vetted best-in-class library for each concrete feature problem, ranked by adoption signal, grounded in captured `REFERENCES.md` sources, framed as optional guidance, and strictly below the `stack-recommend` granularity (per-feature libraries, never stack layers). This closes the gap where research stopped at stack layers and the canonical per-feature libraries had to be added by hand.

This exercises:

- The five-angle methodology (internet, product repo, package registry, AAA-company practices, reference repos) stated in `commands/feature-library-scout.md`.
- The adoption-signal columns in `templates/FEATURE_LIBRARIES.template.md` (registry downloads, dependents, last release, stars and trend, maintenance, framework/platform fit), which are ecosystem-relative; this scenario exercises the React Native plus Expo case, so framework/platform fit is Expo and New Architecture. A web run would use SSR / RSC / edge and bundle size on the same axis.
- The authorized web-fetch membership and the funnel-to-REFERENCES rule in the spec `### External web access (centralized)`.
- The boundary with `stack-recommend` (D-Boundary) and the optional-guidance posture (D-F).
- The golden-set acceptance (D-Accept).

## Setup

A task `projects/acme__mobile/active/2026-06-20_app-shell/` with a chosen stack recorded in `SOURCE_OF_TRUTH.md`: React Native 0.7x plus Expo SDK 5x. The product feature set: a large scrollable feed, in-app camera capture, multi-step forms with heavy keyboard interaction, and modal bottom sheets. No `FEATURE_LIBRARIES.md` exists yet.

## Input prompt (turn 1: single command)

```text
Run @commands/feature-library-scout.md

Task folder: projects/acme__mobile/active/2026-06-20_app-shell/
Stack: React Native 0.7x + Expo SDK 5x (from SOURCE_OF_TRUTH.md)
Product feature set: large scrollable feed, camera capture, multi-step forms with keyboard, modal bottom sheets
Mode: Agent
```

## Input prompt (turn 2: more than 3 problems, deep sweep)

```text
The feature set is larger than first stated: also offline sync, gesture-driven
navigation, and an action sheet. Run the deep per-problem sweep.
Mode: Agent
```

## Expected response shape (turn 1: single command)

- Derives the concrete feature problems from the feature set (large lists, camera, keyboard/forms, bottom sheets) rather than a generic checklist.
- Produces `FEATURE_LIBRARIES.md` with one per-problem block, each carrying the adoption-signal columns, a recommended pick, alternatives, and sources.
- The golden-set libraries surface as recommended picks or strong alternatives for their problems: a large-list renderer (for example `@shopify/flash-list`), a camera library (for example `react-native-vision-camera`), safe-area handling (`react-native-safe-area-context`), keyboard handling (for example `react-native-keyboard-controller`), and a bottom sheet (for example `@gorhom/react-native-bottom-sheet`).
- Every recommended library cites a `REFERENCES.md` source; new sources are captured this run.
- `Last refreshed:` is set; any signal that could not be fetched reads `[not fetched]`, not a guessed number.
- Picks are framed as optional guidance; none is marked mandatory.
- No stack layer (framework, navigation library as an architecture choice, state manager) is re-picked as if it were a stack decision; the Handoff routes to `decision-interview` or `implementation-plan`.

## Expected response shape (turn 2: fleet)

- Routes to `feature-library-scout-fleet` because the problem count is now greater than 3.
- The orchestrator decomposes into one worker per feature problem and is the sole writer of `FEATURE_LIBRARIES.md`; workers return typed `StructuredOutput` payloads and never write the artifact or fetch the web.
- The merged artifact adds `react-native-action-sheet` (for example `@expo/react-native-action-sheet`) for the action-sheet problem, keeping every pick source-grounded.
- The orphan-scan gate runs on `FEATURE_LIBRARIES.md` and `REFERENCES.md` post-merge.

## What a FAIL looks like

- The output recommends stack layers (re-picking the framework, hosting, or auth) instead of per-feature libraries (the stack-recommend boundary violation D-Boundary exists to prevent).
- Adoption numbers are fabricated rather than fetched-or-marked `[not fetched]`.
- A recommended library has no `REFERENCES.md` source (ungrounded pick).
- The golden-set libraries are absent for an RN plus Expo product whose feature set clearly needs them.
- Picks are presented as mandatory rather than optional guidance.
- Turn 2 lets a worker write `FEATURE_LIBRARIES.md` directly or fetch the web (ADR-0038 Rule 2 violation), or skips the orphan-scan gate.
