# ADR-0045: Feature-library research cluster (a new additive WOS cluster)

- **Status**: Accepted
- **Date**: 2026-06-20
- **Tags**: research, additive-track, external-web-access, authorized-fetch-set, adoption-signals, fleet-orchestration, stack-recommend-boundary, reference-grounding

## Context

The WOS already has stack-research commands, but they stop one level above where the maintainer keeps getting hurt. `stack-recommend` picks the stack by layer (frontend framework, UI, backend, database, auth, hosting) with an AAA-company-usage step and version pinning. `stack-currency-check` verifies that a framework's patterns are current. `external-research` and `external-research-fleet` synthesize from sources already captured in `REFERENCES.md`.

None of them answers the question that actually bites: given a chosen stack and a product's feature set, what is the community-vetted best-in-class library for each concrete feature problem, ranked by adoption signal? The maintainer kept discovering the answer by hand, after the fact, and having to redirect work toward libraries the research should have surfaced: react-native-safe-area-context, react-native-keyboard-controller, @gorhom/react-native-bottom-sheet, @expo/react-native-action-sheet, @shopify/flash-list for large lists, react-native-vision-camera for camera. None of these is a stack layer. Each is the canonical answer to a specific feature problem (lists, camera, forms, keyboard, sheets), and `stack-recommend`, organized by layer, does not surface them and has no adoption-signal layer (npm downloads, dependents, release cadence, last-publish date, GitHub stars and trend, maintenance health, Expo and New Architecture compatibility).

The gap is a distinct granularity (per feature problem, not per stack layer) plus a distinct vetting dimension (community adoption signals), informed by what reference repos and AAA apps actually ship. Three of the five research angles the maintainer wants are net-new to the WOS: npm registry signals, a product-repo feature and dependency scan, and reference-repo dependency mining.

The decisions that shape the cluster were locked in a `decision-interview` run on 2026-06-20 (full EARS text in the task `DECISIONS.md`).

## Decision

Add a new additive command cluster, the feature-library research cluster, parallel to the existing stack-research commands. It does not modify the behavior of any existing command. Two commands:

- `feature-library-scout` (single command): given the stack and the product's feature set, it researches across five angles (internet, product repository, npm registry, AAA-company practices, reference repos solving the same problem) and writes a `FEATURE_LIBRARIES.md` artifact with a per-problem table of vetted picks, each ranked by adoption signal, each grounded in a `REFERENCES.md` source, framed as optional guidance.
- `feature-library-scout-fleet` (orchestrator-workers variant): the orchestrator derives the feature-problem list, dispatches one worker per feature problem (each worker covers the five angles for its problem and returns a structured, source-grounded payload), then merges into a single `FEATURE_LIBRARIES.md` as the sole writer, with the ADR-0038 orphan-scan gate.

Load-bearing constraints from the locked decisions:

- Additive only (D-A). The cluster does not pivot, re-route, or remove any existing command.
- Boundary (D-Boundary). `stack-recommend` owns stack-layer selection; this cluster owns per-feature library and technique discovery vetted by adoption signal. No granularity overlap, stated in both command bodies to prevent sprawl.
- Authorized web-fetch (D-B). Both commands join the WOS authorized web-fetch set (the closed set previously holding only `capture-references`, `stack-recommend`, `stack-currency-check`), and each funnels every fetched source into `REFERENCES.md` in capture-references format, deduplicated by URL, so a fetch by either command is indistinguishable in the audit trail from a `capture-references` run.
- Adoption signals (D-Signals). Ranking uses adoption signals relative to the project's ecosystem: package-registry download or install volume (npm, PyPI, crates.io, the Go module index, Maven Central, etc.), dependent count, release cadence, last-release date, source-host stars and star trend, maintenance and issue health, and framework/platform fit on the axis that matters for the stack (React Native: Expo and New Architecture; web: SSR / RSC / edge and bundle size; backend: runtime version range). The signals are ecosystem-relative, never JavaScript-only; the cluster is stack-agnostic.
- Output artifact (D-D). A dedicated `FEATURE_LIBRARIES.md` artifact, separate from `STACK_RECOMMENDATION.md`.
- Trigger points (D-E). Runnable on-demand, and routed from `project-bootstrap`, from `task-init` on an existing project, and from `impact-analysis` when greenfield feature areas are detected (the same routing idiom used for `stack-currency-check`).
- Recommendation posture (D-F). Recommendations are optional guidance, never mandatory.
- Acceptance (D-Accept). An eval scenario treats the golden-set libraries above as the acceptance check for a React Native plus Expo product with lists, camera, forms, and keyboard needs.

The cluster reuses existing primitives: the Workflow tool for the fleet variant (ADR-0038), the single-writer merge and orphan-scan gate (ADR-0038, ADR-0040), the reference-grounding execution gate (ADR-0043), and the cross-source reconciliation taxonomy for fleet merge (ADR-0018).

## Consequences

### Positive

- The maintainer gets the community-vetted feature libraries surfaced early, with adoption evidence, instead of discovering them by hand after the fact.
- The new surface is small because it reuses audited primitives (the Workflow tool, single-writer merge, the funnel-to-REFERENCES rule, reference grounding).
- The boundary with `stack-recommend` is recorded here and stated in both command bodies, so the cluster cannot quietly drift into re-doing layer selection.

### Negative

- A new cluster is two more commands to maintain, register in four places, and cover with an eval scenario.
- It widens the authorized web-fetch set from three commands to five. The funnel-to-REFERENCES rule keeps the audit trail single-sourced, but the fetch surface is larger and the maintainer accepts that tradeoff for the npm and reference-repo angles, which cannot run without live fetch.
- Adoption signals drift fast (downloads and stars change weekly), so the artifact is a dated snapshot, not durable truth, and rate-limit truncation must be logged rather than silently dropped.

### Neutral

- The existing stack-research commands are unchanged. This cluster sits one granularity below `stack-recommend` and calls none of its internals.
- The output is a new task artifact (`FEATURE_LIBRARIES.md`); there is no new persistence layer.

## Alternatives considered

### Alternative 1: deepen `stack-recommend` with a feature-library mode instead of a new cluster

- Rejected (D-A, D-Boundary). `stack-recommend` is organized by stack layer, version-pinned, and budget-bounded. Folding a per-feature-problem mode plus an adoption-signal layer into it mixes two granularities in one command and strains a fixed canonical format. A separate cluster keeps each command coherent.

### Alternative 2: no guardrail change; consume only via `capture-references`

- Rejected (D-B). The npm-signals and reference-repo angles need live, structured fetch of the npm registry and GitHub. Routing every discovery through `capture-references` by hand defeats the automation the maintainer asked for and produces weaker, slower signal gathering. There is precedent for a scoped research peer in the authorized set, so joining it is the cleaner path.

### Alternative 3: ship the single command first and add the fleet variant later

- Rejected for this build (D-A). The maintainer explicitly wanted the aggressive multi-agent depth from day one, so both commands are built together. The fleet variant follows the `external-research-fleet` template, so the marginal cost over the single command is bounded.

## References

- `projects/<client>__<project>/active/2026-06-20_deep-stack-research/` (this ADR's source task: `DECISIONS.md` D-A through D-Accept, `IMPACT_ANALYSIS.md`, `IMPLEMENTATION_PLAN.md`).
- WORKFLOW_OPERATING_SYSTEM.md `## Cross-cutting workflow guardrails` -> `### External web access (centralized)` (the authorized web-fetch set this ADR expands).
- ADR-0010 (centralized external web access), ADR-0029 (lint drift guards: registry membership + count markers), ADR-0038 (Workflow tool as the parallel-orchestration primitive), ADR-0040 (single-writer-per-folder), ADR-0043 (reference grounding execution gate), ADR-0018 (cross-source context in REFERENCES, used at fleet merge).
- `commands/stack-recommend.md` and `commands/stack-currency-check.md` (the adjacent stack-research commands this cluster sits below).

## Notes

The decisions were locked in a `decision-interview` run on 2026-06-20 and approved via `approve-plan` the same day. The command names (`feature-library-scout`, `feature-library-scout-fleet`), the one-worker-per-feature-problem decomposition, and the `FEATURE_LIBRARIES.md` filename were pinned at plan approval. This ADR is the first build slice; the WOS authorized-set edit and both command files cite it. Revisit the fetch-surface tradeoff (negative consequence) if the audit trail shows the funnel-to-REFERENCES rule being bypassed; that would be a new decision, not a patch to this ADR.

D-Signals was refined the same day (2026-06-20), before commit, from a JavaScript and React-Native-specific phrasing (npm downloads; Expo and New Architecture support) to the ecosystem-relative form in the Decision section above, after the maintainer confirmed the WOS must be stack-agnostic. The substance of the decision (rank by adoption signal) is unchanged; only the signal sources were generalized, so this is a same-session correction rather than a superseding ADR.
