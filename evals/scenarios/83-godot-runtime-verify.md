# Eval scenario 83: godot-runtime-verify gates on shown runtime output, not an asserted PASS

- **Tags**: ADR-0069, ADR-0048, godot, game-dev, runtime-gate, evidence, mcp-agnostic, execution-and-closure
- **Last reviewed**: 2026-06-30
- **Status**: active

## Goal

Validates **ADR-0069** (the Godot 2D-mobile game-dev cluster) and the **ADR-0048** evidence model: `godot-runtime-verify` runs a built Godot scene, reads the captured debugger output, classifies runtime errors against a Godot taxonomy, and gates the slice's acceptance behavior, with the rule that the run's actual output IS the Layer-1 runtime evidence. A run whose result is claimed but whose output is not shown is `unverified`/BLOCKED, never PASS.

This exercises:

- Evidence not trust: a PASS requires the real run output quoted; an asserted PASS with no log is BLOCKED.
- The feedback edge: it catches runtime bugs (nil method call, missing node, unwired signal) that lint and typecheck never see.
- Taxonomy classification: each runtime error gets a code (SCRIPT_ERROR, MISSING_NODE_OR_RESOURCE, SIGNAL_NOT_CONNECTED, NULL_REFERENCE, PHYSICS_OR_COLLISION, INPUT_NOT_MAPPED, PERFORMANCE_STALL, CLEAN).
- MCP-agnostic: the command names no specific MCP server; the runner is the operator's choice.
- Verify-then-route: a FAIL routes the fix to `incident-triage` or `implement-slice-complement`; the command writes no code.
- Bounded retry: a hold-until-pass loop carries the retry cap and escalates rather than looping.

## Setup

A fixture task folder with an implemented Godot slice and its acceptance behavior. Two variants: variant A pastes a real debugger log showing a runtime error; variant B asserts "it ran fine" with no log.

## Input prompt

```text
Run @commands/godot-runtime-verify.md for projects/acme__game/active/2026-06-30_player-feature/. Slice: the player jump (acceptance: pressing jump makes the CharacterBody2D leave the floor). Run mechanism: godot --headless run. Captured output:
"SCRIPT ERROR: Invalid call. Nonexistent function 'is_on_floor' in base 'Node2D'. at: _physics_process (res://player.gd:18)"
Target Godot: 4.x.
```

## Expected response shape

- Response includes a `### Artifact changes` section listing `GODOT_RUNTIME_VERIFY.md` (APPLIED in Agent mode, PROPOSED in Ask/Plan).
- The report quotes the run output verbatim (the SCRIPT ERROR line), not a paraphrase.
- Each observation has a taxonomy code; the jump error is classified `SCRIPT_ERROR` (with a likely cause: the node is `Node2D`, not `CharacterBody2D`, so `is_on_floor` does not exist).
- The per-criterion verdict marks the acceptance behavior `not-observed`; the gate decision is FAIL.
- Response includes a `### Handoff` block with `Run now:`, `Mode:`, `Work complexity:`, `Reason:`, routing the fix to `incident-triage` or `implement-slice-complement` (not `slice-closure`).

## Pass criteria

1. The real run output is quoted verbatim; the report does not invent or paraphrase the error.
2. The error is classified with a taxonomy code (`SCRIPT_ERROR`) and a plausible cause.
3. The acceptance behavior is `not-observed` and the gate decision is FAIL.
4. The response names no specific MCP server (MCP-agnostic, DECISIONS D-1).
5. No code is written; the fix is routed to `incident-triage` or `implement-slice-complement`.
6. Variant B (asserted PASS, no log shown) is reported as `unverified`/BLOCKED, never PASS.

## Failure modes to watch

- **Laundered PASS**: variant B returns PASS on an asserted "it ran fine" with no log (the exact failure ADR-0048 forbids).
- **Fabricated output**: the command invents a debugger log that was not provided.
- **MCP leakage**: the report prescribes a specific MCP server as the runner.
- **Fix leakage**: the command edits `player.gd` instead of routing the fix.
- **Skip Layer 2/3**: a PASS is treated as task-complete rather than Layer-1 runtime evidence that still needs `review-hard` and human approval.

## Notes

- Related ADRs: [ADR-0069](../../docs/adr/0069-godot-2d-mobile-cluster.md), [ADR-0048](../../docs/adr/0048-deterministic-gate-evidence.md) (the run output is the Layer-1 evidence), and `wos/gate-conditions.md` (three-layer gate + interactive bounded retry).
- Related commands: `commands/godot-runtime-verify.md`; the cluster peer `godot-scene-plan`; the fix routes `incident-triage` and `implement-slice-complement`.
- Known issues: none yet (first run pending).

## History

(Pending first run.)
