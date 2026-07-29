# ADR-0117: Godot 3D ships as a dimension-routed widening of the existing surface, not a new cluster

- **Status**: Accepted
- **Date**: 2026-07-26
- **Tags**: godot, 3d, game-dev, capability-routed, dimension-routing, no-new-command, reference-layer, extends-adr-0069

## Context

ADR-0069 added a Godot 2D-mobile game-dev cluster: two net-new commands (`godot-scene-plan`, `godot-runtime-verify`) plus four gated modes, backed by a six-file reference layer under `wos/godot-*.md`, later hardened by ADR-0078, ADR-0084, ADR-0085, and ADR-0089. The obvious next question was whether 3D deserves the same treatment. A research round (task `2026-07-26_godot-3d-cluster-research`) answered it, mirroring ADR-0069's own order: capture sources, synthesize, build a reuse map, then decide.

Twelve sources were captured across four groups (official Godot 3D documentation, real open-source 3D projects, free asset sources with licenses, genre and market data). Eleven already-captured sources from the 2026-06-29 and 2026-07-09 rounds were added after checking `REFERENCES.md` for entries no synthesis had consumed against a 3D question: the seven AI-tooling and MCP-server entries, the agentic-loop framing, and the three mobile export docs. That check cost nothing and produced the sharpest constraint in the round. Twenty-three sources were then synthesized across five angles by an `external-research-fleet` run, with two cross-angle conflicts surfaced rather than smoothed.

Two findings shaped the decision, and the first is an absence.

**No angle produced positive demand evidence for a 3D surface.** Four of the five said so outright: the asset angle can say licensing is not a blocker but cannot say what surface shape that implies; the market angle found no source that classifies any genre as 2D or 3D, so every dimensionality inference rests on an association none of the sources supplies; the corpus angle found exactly four 3D games in a curated list of roughly twenty, genre-scattered and license-unreliable outside the official MIT demos; the tooling angle found no confirmed 3D capability gap. What the market data does show cuts the other way for mobile: the genres that grew in 2025 (strategy, puzzle, hypercasual) skew 2D, while action, RPG, and racing led the download declines.

**3D does introduce concerns the 2D reference layer genuinely lacks.** Godot 4 3D is a three-way renderer choice, not one target, and the tiers differ by removed features, so a feature written against Forward+ is not portable by default. The iOS simulator supports only the Compatibility renderer, so a 3D scene verified there is not evidence for the tier the shipped build uses. The mobile performance path is mechanically different rather than numerically scaled (bake instead of realtime; no Forward+ auto-instancing on Mobile). Four of the nine documented 3D optimization techniques (LOD, occlusion culling, baked lighting, MultiMesh) have no equivalent in the existing 2D performance topic, and transparency sorting by node position rather than vertex position is a correctness-shaped defect class a 2D checklist does not contain.

The reuse map settled the shape question on internal evidence. Measured against the real command surface: zero of the 95 command files mention 3D anywhere, exactly seven are 2D-bound by text, and five Godot-aware commands (`implement-approved-slice`, `slice-closure`, `task-close`, `pr-feedback-ingest`, `app-runtime-verify`) carry no 2D binding at all because they route by task signature rather than dimension. Applying the strict gap rule (a gap counts only when a named 3D-specific need has no existing command) produced **zero command-shaped gaps**: every 3D need maps onto an existing 2D-bound command, onto reference content, or onto a gate inside `godot-scene-plan`.

## Decision

Godot 3D ships as a dimension-routed widening of the existing surface. The decisions (locked in the task's `DECISIONS.md`, D-1 through D-9) are:

- **D-9 (supersedes D-4) Surface shape.** Deliver 3D capability by widening the seven 2D-bound command files to dimension-routed contracts, adding 3D reference topics, and adding a REQUIRED renderer-tier declaration field to `godot-scene-plan` such that a 3D scene plan without a declared tier is incomplete. No net-new 3D command. A dimension-routed contract states which Godot dimension it applies to, or states that it applies to both, instead of naming 2D by default. The seven files are `godot-scene-plan`, `problem-framing`, `release-plan`, `image-to-spec`, `godot-runtime-verify`, `test-strategy`, and `performance-budget`.
- **D-1 No net-new 3D command**, stated as a standing constraint in its own right.
- **D-2 Platform posture** is desktop-leaning and asymmetric; no mobile-first default.
- **D-3 Asset sourcing** is CC0 only, with per-source license terms captured in `REFERENCES.md`, and acquisition stays a documented human step rather than an automated fetch.
- **D-5 Reference-layer shape** is parallel `wos/godot-3d-*.md` files, with dimension-neutral content left in the existing topics and cross-referenced rather than copied.
- **D-6 POC wave shape** is exactly two POCs on desktop Forward+ (one movement-and-camera scene, one GridMap-and-lighting scene), gated by the existing runtime-gate and human feel-verdict floors in `wos/platform-runtime-floors.md`, and not dispatched before the D-8 precondition is met.
- **D-8** defines that precondition: the two open 2D genre-dogfood audit tasks count as resolved only when both task folders have been archived via `task-close`.
- **D-7 Genre deliverable reframe.** The genre finding is recorded as demand by platform without a 2D-versus-3D dimensionality field and without desktop most-played data, because no captured source supplies either.

This extends ADR-0069 rather than paralleling it. ADR-0069 D-4 ("Godot-first and capability-named where natural; no speculative multi-engine abstraction") stands and was not reopened.

## Consequences

- `count:adrs` rises by one with this ADR. `count:commands` does not change, and no registry row is added: a widening touches no command name, so the four-registry rule (ADR-0029) and the generated-skills surface see no new entry.
- The seven widened commands carry a real risk this ADR names explicitly: a find-and-replace on the string "2D" would leave unstated 2D assumptions in prose, producing a surface that claims 3D support it does not deliver. No lint check catches a contract that says Godot but means 2D, so the widening pass reads each file line by line. Four of the five dimension-neutral commands were confirmed by text count only, not by a line-by-line read, and that verification belongs to the build task.
- The reference layer roughly doubles in file count. The drift risk between parallel 2D and 3D copies of dimension-neutral content is accepted rather than eliminated; cross-referencing rather than copying is the mitigation.
- `EXTERNAL_RESEARCH.md` conflict C-2 (whether any captured MCP server exposes a 3D-specific operation) is deliberately left open. Every capture records tool counts and category counts and never a category name, so project memory cannot settle it. The D-6 POC wave is the mechanism that will.
- Four research gaps stay open and are recorded rather than papered over: numeric 3D budgets per renderer tier, whether CC0 assets are mobile-viable (no poly counts or LOD data captured), the 2D-versus-3D split in demand data, and the desktop ship path (no source covers Windows, macOS, or Linux export).
- The round surfaced that the captured tooling entries reason about license fit against an AGPL-distributed workflow. That premise is stale since the 2026-07-12 MIT relicense. The direction of those license conclusions is unaffected (five MIT-adoptable, two proprietary reference-only), but the stated rationale is out of date, and `PROJECT_CHARTER.md` carries the same drift.

## Alternatives considered

- **A new 3D command cluster** (sibling `godot-3d-scene-plan` and `godot-3d-runtime-verify`), mirroring ADR-0069's own precedent. Rejected on the reuse map: zero command-shaped gaps were found, so there is nothing for a new command to do that widening an existing one does not. It would also add four registry rows, two generated skills, and two eval scenarios for no routing benefit.
- **No change at all.** Defensible purely on the demand evidence, since four of five angles could not justify a surface. Rejected because it leaves the seven 2D-bound contracts telling a 3D user the flow does not apply to them, while the engine-level findings show 3D genuinely needs guidance the 2D layer does not carry.
- **Reference topics only**, touching no command contract and no registry. Rejected as the end state for the same reason: the topics would exist while every command a 3D user reads first still says 2D. The topics it implies are kept as part of the chosen direction.
- **Refactoring the reference layer into a dimension-neutral core plus per-dimension deltas** instead of parallel files. Rejected because it churns a shipped layer already hardened by four ADRs and nine dogfood runs, and no third dimension or platform is currently expected.
- **A mobile-first or dimension-symmetric posture.** Rejected on three independent angles converging on desktop-leaning, and on the absence of any mobile 3D demand signal in the captured market data.
