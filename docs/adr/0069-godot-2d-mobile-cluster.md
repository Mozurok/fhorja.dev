# ADR-0069: a Godot 2D-mobile game-dev cluster (two net-new commands plus four modes)

- **Status**: Accepted
- **Date**: 2026-06-30
- **Tags**: godot, game-dev, 2d-mobile, cluster, mcp-agnostic, capability-routed, ecosystem-adoption, additive

## Context

The WOS covered general engineering work but had no path for game development. A research round (task `2026-06-29_godot-2d-mobile-game-dev-cluster`) captured eleven grounded sources into `REFERENCES.md` (six Godot MCP/builder repos named in the brief plus five swept: a seventh MIT MCP server `hi-godot/godot-ai`, the official Godot Android and iOS export docs, the April 2026 mobile update, and an independent framing of the agentic Godot loop) and synthesized them in `EXTERNAL_RESEARCH.md` across four angles (MCP-server landscape, AI-builder flow patterns, mobile platform requirements, licensing and trust) with zero cross-angle contradictions.

Two findings shaped the decision. First, the reuse map (`IMPACT_ANALYSIS.md`) showed most of a Godot 2D-mobile flow is already served by existing WOS commands (problem-framing, impact-analysis, code-context-map, implementation-plan, implement-approved-slice, review-hard, security-review, skill-vet, performance-budget, a11y-audit, incident-triage, the delivery and state commands). Second, the one pattern with no WOS analogue is the live press-play runtime gate (the "feedback edge"): WOS Layer-1 evidence (ADR-0048) assumes deterministic linter/test gates, while the captured tooling and framing agree that most Godot bugs are runtime bugs a linter cannot catch. The closest prior art, `HubDev-AI/godot-ai-builder` (MIT, a six-phase build with per-phase quality gates and checkpoint/resume "in the style of my_work_tasks"), confirmed the flow shape maps onto the WOS phase/gate/state model.

## Decision

Add a thin, additive, capability-routed Godot 2D-mobile game-dev cluster. The decisions (locked in the task's `DECISIONS.md`, D-1 to D-6) are:

- D-1 MCP-agnostic: command contracts name no specific MCP server; docs recommend the MIT servers (`mkdevkit/godot-mcp` for the mobile path because it is the only captured server with adb APK export-and-deploy, `hi-godot/godot-ai` as the general default for breadth of client support, `Coding-Solo/godot-mcp` as the minimal transport). The proprietary `3ddelano/gdai` and the paid `Godot MCP Pro` are reference-only and never bundled.
- D-2 Two net-new commands (`godot-scene-plan` for scene and node planning; `godot-runtime-verify`, the live press-play runtime gate), plus four modes of existing commands: game-design framing in `problem-framing`, mobile export-and-ship in `release-plan`, playtest-feedback ingest in `pr-feedback-ingest`, and a Godot 2D-mobile performance profile in `performance-budget`.
- D-3 The new commands map onto existing `metadata.category` values; no new game-development category.
- D-4 Godot-first and capability-named where natural; no speculative multi-engine abstraction.
- D-5 Godot-version-flexible, documenting Godot 4.6+ as the floor for editor-driven on-device testing (Android device mirroring) and 4.4+ as the baseline the recommended servers assume.
- D-6 GDScript as the default language; surface the experimental C# iOS export caveat (experimental since Godot 4.2) wherever mobile export is in scope.

The precedent is the Frontend cluster (ADR-0065 to 0068) and the Autonomous track (ADR-0044): an additive, capability-routed cluster, grouped for humans by a README section and a single cluster ADR rather than by a taxonomy change. Modes follow the ADR-0061 (`--spec`), ADR-0063 (`--tdd`), and ADR-0068 (mobile performance surface) precedent: a mode of an existing command warrants a mention in this ADR but needs no `count:commands` bump and no four-registry registration.

## Consequences

- `count:adrs` rises 67 to 68 with this ADR. `count:commands` will rise by 2 when the two net-new commands land (`godot-scene-plan`, `godot-runtime-verify`), each registered in all four registries with a generated skill and an eval scenario.
- The cluster reuses the WOS lifecycle end to end; it validates that the WOS fits game development rather than forking a parallel flow.
- `godot-runtime-verify` is the novel piece: its acceptance contract is designed from scratch against the ADR-0048 evidence model (what a passing runtime check is, how runtime errors are classified, how the result becomes slice evidence), MCP-agnostic about how the scene is actually run.
- The four modes extend their host commands without changing default behavior, gated and off by default.
- Mobile delivery is modeled as two asymmetric paths: Android is host-OS-flexible with first-class editor device mirroring on 4.6+; iOS is gated behind a macOS-plus-Xcode preflight with the experimental-C# and simulator-renderer caveats.
- The README gains a GameDevelopment / Godot section. Before it recommends any server by name, the MIT-into-AGPL attribution obligation for that server is verified against its on-disk LICENSE.

## Alternatives considered

- A full opinionated builder (a dedicated orchestrator command mirroring HubDev's seven-phase build plus several supporting commands). Rejected: it duplicates the WOS lifecycle and reads as a stack-locked vertical, against the WOS additive, capability-routed, non-stack-locked design.
- Docs-only (a README section and a recommended-MCP guide, no new commands). Rejected as the end state: it does not satisfy the user-named deliverable of new game-dev commands, though the README section it implies is kept as the cluster's last slice.
- Pinning one MCP server as the supported default. Rejected (D-1): it bets the cluster on one community project and conflicts with the WOS multi-tool stance.
- Adding a new game-development category. Rejected (D-3): it widens the lint canonical category set and the category count marker for no routing benefit; the README section and this ADR group the cluster for humans instead.
