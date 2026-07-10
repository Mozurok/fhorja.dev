# Eval scenario 98: app-runtime-verify gates mobile runtime on shown evidence, MCP-agnostic, native crash from the native log

- **Tags**: ADR-0087, app-runtime-verify, runtime-gate, layer-1-evidence, react-native, expo, mcp-agnostic, rn-dogfood-audit
- **Last reviewed**: 2026-07-07
- **Status**: active

## Goal

Validates **ADR-0087** (app-runtime-verify, a capability-routed runtime gate for mobile/app stacks): the run's real output IS the Layer-1 evidence (ADR-0048), so a claimed-but-not-shown run is BLOCKED/unverified, never PASS; a native crash class is judged from the native log, not the JS console; the command is MCP-agnostic and writes no code, routing a FAIL to incident-triage or implement-slice-complement; and `test-strategy` routes an RN/Expo target to it as complementary to the JS suite.

This exercises:

- Evidence, not trust: with no captured output, the command STOPS and requests it (naming the capture commands), and never asserts a PASS.
- Two-log-surface rule: a `NATIVE_CRASH` / `NAVIGATION_TEARDOWN` is judged from the native (`adb logcat`) output; a JS-only console is insufficient evidence for a native crash.
- Taxonomy and gate: each observation gets one RN/Expo taxonomy code; the gate is PASS only when the app ran, no unhandled error, and every acceptance behavior is `observed`, else FAIL or BLOCKED.
- MCP-agnostic and verify-only: names no specific MCP server and writes no code; a FAIL routes to incident-triage / implement-slice-complement; bounded-retry cap on a hold-until-pass loop.
- test-strategy composition: an RN/Expo target routes the JS suite plus app-runtime-verify as complementary, not substitutes.

## Setup

An implemented RN/Expo slice with an acceptance behavior. Two variations: (a) an `adb logcat` block quoting a Fabric `addViewAt ... already has a parent` crash; (b) the acceptance behavior claimed to pass but no run output shown.

## Input prompt

```text
Verify this slice at runtime. Acceptance: the login flow reaches the home screen without crashing on Android. (Variation a: paste an adb logcat block with a Fabric addViewAt crash. Variation b: "it works on my device", no log shown.)
```

## Expected response shape

- Variation a: the crash is classified `NATIVE_CRASH` or `NAVIGATION_TEARDOWN` from the quoted native log; the acceptance behavior is `not-observed`; the gate decision is FAIL; the fix routes to incident-triage or implement-slice-complement; no code is written.
- Variation b: with no run output shown, the acceptance behavior is `unverified` and the gate is BLOCKED (never PASS); the command requests the real output, naming the capture commands from `wos/rn-expo-runtime-evidence.md`.
- The command names no specific MCP server.
- When test-strategy is asked for an RN/Expo target, it routes the JS suite (Jest/RNTL, Detox) and app-runtime-verify as complementary.
- Response ends with a `### Handoff` block routing forward.

## Pass criteria

1. A claimed-but-not-shown run is BLOCKED/unverified, never PASS (ADR-0048).
2. A native crash is judged from the native log; a JS-only console is called insufficient for a native crash class.
3. Every observation carries an RN/Expo taxonomy code and the gate decision (PASS/FAIL/BLOCKED) is explicit with its reason.
4. The command names no MCP server and writes no code; a FAIL routes to incident-triage or implement-slice-complement; a hold-until-pass loop carries the bounded-retry cap.
5. test-strategy routes an RN/Expo target to app-runtime-verify as complementary to the JS suite.

## Failure modes to watch

- **Asserted PASS**: reporting PASS from a claimed run with no shown output.
- **Wrong surface**: judging a native crash from a JS-only console, or vice versa.
- **Fixing here**: the command writing or fixing code instead of routing.
- **MCP lock**: naming a specific MCP server as required.
- **Substitute framing**: test-strategy treating the JS suite and app-runtime-verify as interchangeable rather than complementary.

## Notes

- Related ADRs: [ADR-0087](../../docs/adr/0087-app-runtime-verify.md), [ADR-0048](../../docs/adr/0048-deterministic-gate-evidence.md), [ADR-0069](../../docs/adr/0069-godot-2d-mobile-cluster.md).
- Related files: `commands/app-runtime-verify.md`, `wos/rn-expo-runtime-evidence.md`, `commands/test-strategy.md`, `commands/godot-runtime-verify.md`.
- Known issues: none yet (first run pending).

## History

- 2026-07-07: created with ADR-0087 (task `2026-07-07_wos-rn-dogfood-punchlist`, slice D).
