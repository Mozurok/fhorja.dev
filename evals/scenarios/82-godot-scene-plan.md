# Eval scenario 82: godot-scene-plan produces an MCP-agnostic Godot scene plan

- **Tags**: ADR-0069, godot, game-dev, 2d-mobile, scene-plan, mcp-agnostic, capability-routed, discovery-and-scoping
- **Last reviewed**: 2026-06-30
- **Status**: active

## Goal

Validates **ADR-0069** (the Godot 2D-mobile game-dev cluster): `godot-scene-plan` plans the Godot scene and node architecture for a 2D feature before any GDScript, producing `GODOT_SCENE_PLAN.md` with a node-typed scene tree, autoloads, signal wiring, an input map, and resources/sub-scenes, while staying MCP-agnostic (names no specific server, per DECISIONS D-1) and inventing no device-specific performance numbers (deferred to `performance-budget`).

This exercises:

- Scene-tree fidelity: every node carries a Godot built-in type and a one-line responsibility, and the tree is the smallest that satisfies the feature.
- The four structural pillars are all addressed: autoloads, signals, input map, resources/sub-scenes.
- MCP-agnostic contract: the plan recommends no MCP server by name; the design is the output, not the tool that applies it.
- 2D-mobile fit: touch input mapping is explicit, and device-specific budgets are marked `[to confirm]` rather than fabricated.
- No code: the command plans the scene, it does not write GDScript or create `.tscn` files.

## Setup

A fixture task folder with an approved plan that includes `godot-scene-plan` as a slice, and DECISIONS D-1 to D-6 from ADR-0069. Paste a one-line feature brief (for example "a player character for a 2D platformer: run, jump, take damage").

## Input prompt

```text
Run @commands/godot-scene-plan.md for projects/acme__game/active/2026-06-30_player-feature/. Feature: a player character for a 2D platformer (run, jump, take damage, die). Game-design context: side-scrolling platformer, keyboard plus touch. Target Godot: 4.x (mobile, 4.6+ for on-device testing). Greenfield feature.
```

## Expected response shape

- Response includes a `### Artifact changes` section listing `GODOT_SCENE_PLAN.md` (APPLIED in Agent mode, PROPOSED in Ask/Plan).
- The plan contains a scene tree where each node has a Godot type (for example `CharacterBody2D`, `AnimatedSprite2D`, `CollisionShape2D`, `Camera2D`) and a one-line responsibility.
- The plan has an autoloads section, a signals section (emitter, signal, listener, payload), an input map section (with touch mapping), and a resources/sub-scenes section.
- Response includes a `### Handoff` block with a fenced region containing `Run now:`, `Mode:`, `Work complexity:`, `Reason:`, routing to `implementation-plan`, `decision-interview`, or `targeted-questions`.

## Pass criteria

1. Every node in the scene tree names a Godot built-in node type and a responsibility; no untyped placeholder nodes.
2. Autoloads, signals, input map, and resources/sub-scenes are each present and non-empty.
3. The plan names no specific MCP server anywhere (MCP-agnostic, DECISIONS D-1).
4. Touch input is mapped explicitly (not keyboard-only), and any device-specific performance number is marked `[to confirm]` rather than asserted.
5. No GDScript and no `.tscn` files are written; the output is the plan doc only.
6. The handoff routes to an official command that exists in `commands/`.

## Failure modes to watch

- **MCP leakage**: the plan recommends mkdevkit, hi-godot, Godot MCP Pro, or any server by name in the contract (it may only appear as a doc-level recommendation elsewhere, never in the plan itself).
- **Fabricated budgets**: invented FPS, draw-call, or memory thresholds instead of `[to confirm]` and a deferral to `performance-budget`.
- **Code leakage**: the response writes GDScript or creates scene files instead of planning.
- **Over-built tree**: nodes added that no stated responsibility requires (YAGNI violation).

## Notes

- Related ADRs: [ADR-0069](../../docs/adr/0069-godot-2d-mobile-cluster.md), [ADR-0031](../../docs/adr/0031-ears-for-decisions-and-exit-criteria.md) (EARS exit criteria for the slice that builds from the plan).
- Related commands: `commands/godot-scene-plan.md`; the cluster peer `godot-runtime-verify` (verifies the built scene at runtime).
- Known issues: none yet (first run pending).

## History

(Pending first run.)
