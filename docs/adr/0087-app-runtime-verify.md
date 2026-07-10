# ADR-0087: app-runtime-verify, a capability-routed runtime gate for mobile/app stacks (RN/Expo first adapter)

- **Status**: Accepted
- **Date**: 2026-07-07
- **Tags**: app-runtime-verify, runtime-gate, layer-1-evidence, react-native, expo, mcp-agnostic, capability-routed, dogfood-driven, rn-dogfood-audit, mirrors-godot-runtime-verify

## Context

The rn-reference-app dogfood (the Android-only React Native Fabric `addViewAt ... ReactEditText already has a parent` crash, 2026-07-07) hinged entirely on runtime evidence that only a run on a device could produce. The crash never appears in typecheck or lint; it fires when a screen with a mounted `TextInput` is torn down during navigation. Throughout the session the maintainer was the runtime harness: they ran the app, ran `adb logcat`, and pasted the output by hand, and the assistant taught the `adb`/`expo` commands ad hoc each time. The WOS had no command that treats a mobile run's output as gated Layer-1 evidence.

The WOS already has exactly this shape for one stack: `godot-runtime-verify` (ADR-0069/0085) runs a Godot scene, classifies the debugger output against a Godot taxonomy, and decides a PASS/FAIL runtime gate where the run's real output IS the Layer-1 evidence (ADR-0048). Nothing analogous existed for React Native, Expo, or any other app stack. The audit's P0-2 finding: build that gate.

The design choice (task `2026-07-07_wos-rn-dogfood-punchlist`, decision D-4): one stack-specific `mobile-runtime-verify` (the Godot precedent) versus one capability-routed `app-runtime-verify` with per-stack taxonomy adapters. The WOS's dominant pattern is capability routing (backend-system-design, release-plan, performance-budget all route by capability, not stack), and the project rejects stack-locked verticals. Godot is the exception, a dedicated cluster that predates this. So a single capability-routed command with RN/Expo as the first documented adapter fits the WOS better than one command per stack.

## Decision

Add `app-runtime-verify`, one net-new command (the only new command in the punch-list; Direction C, D-1), cloned from `godot-runtime-verify`'s contract:

1. **Capability-routed, MCP-agnostic runtime gate.** It runs (or reads a run of) the built app, reads the captured runtime output, classifies each observation against a per-stack taxonomy, gives a per-acceptance-criterion verdict, and decides PASS / FAIL / BLOCKED. The run's real output IS the Layer-1 evidence (ADR-0048): a claimed-but-not-shown run is `unverified`/BLOCKED, never PASS. It names no MCP server; whatever ran the app is the operator's choice. It verifies and routes fixes (to `incident-triage` or `implement-slice-complement`); it never writes code. A hold-until-pass loop carries the bounded-retry cap (`wos/gate-conditions.md`).

2. **React Native / Expo is the first adapter.** The taxonomy codes are RN/Expo-grounded: `NATIVE_CRASH`, `NAVIGATION_TEARDOWN` (the navigation-teardown class), `JS_ERROR`, `MISSING_NATIVE_MODULE`, `STARTUP_CRASH`, `ANR`, `PERMISSION_OR_CONFIG`, `CLEAN`. A companion reference topic, `wos/rn-expo-runtime-evidence.md`, documents how to capture the evidence (clean prebuild rebuild, `expo run`, `adb logcat --pid`, the two-log-surface rule that a native crash is judged from the native log, not the JS console), grounded in the commands the maintainer actually ran. Other app stacks extend the same command by swapping the taxonomy adapter.

3. **Composition, not duplication.** `test-strategy` detects an RN/Expo target and routes the headless suite while treating this press-play-style gate as complementary (the same relationship it already has with `godot-runtime-verify`). `performance-budget` keeps the numeric frame/latency budgets; this gate is pass/fail on crashes and observed behavior, not numbers.

## Consequences

### Positive

- The runtime evidence the audit showed the human producing by hand is now a first-class gate: a mobile slice's acceptance behavior is verified against real, quoted run output, and the native-crash class is read from the native log.
- Capability routing keeps it one command for many app stacks, consistent with the WOS pattern and the no-stack-lock stance, rather than one command per stack.
- It reuses a proven contract (`godot-runtime-verify`), so the Layer-1/Layer-2/Layer-3 placement, the MCP-agnostic runner, and the bounded-retry cap are already validated.

### Negative

- A capability-routed gate risks a vague taxonomy if the adapter is thin. Mitigated by grounding the RN/Expo taxonomy in the audited crash classes and shipping the concrete evidence-capture topic with it.
- One net-new command carries the registration tax (4 registries, count markers, an eval scenario). Accepted as the single new command the punch-list allows.

### Neutral

- No WOS lifecycle change. The gate lives in execution/closure like `godot-runtime-verify`; it is opt-in per slice with an explicit-skip escape for no-runtime-surface slices.
