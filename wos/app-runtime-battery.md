---
activation: model_decision
description: The per-adapter runtime battery and taxonomy that app-runtime-verify classifies against: the RN/Expo code set, the Unity mobile code set, the clean-persisted-state confirmation, the video-frame extraction rule, the cold-start requirement, the capture adapter and its run directory, the golden-baseline rule, and the static mechanical-versus-judgment split. Load when running the app runtime gate; the command keeps the eight-step skeleton and this topic carries the adapter layer.
---

# App runtime battery (RN/Expo and Unity mobile adapters)

Lazy-loaded reference for `app-runtime-verify`. It carries the per-adapter
battery this gate runs and the taxonomy it classifies against, so the command
itself keeps only the eight-step skeleton. Loaded when the command runs, never
inlined into the command. Capability-routed: whatever ran the app (an MCP run
tool, an emulator or simulator, a physical device, a headless run) is the
operator's choice; this topic defines what must be observed, not the runner.
Capture recipes stay in `wos/rn-expo-runtime-evidence.md` and
`wos/unity-runtime-evidence.md`; this topic consumes them and never restates them.

## Clean persisted state (ADR-0148)

WHEN a device pass is offered as evidence for a slice whose acceptance behavior can be MASKED by state that survives an app uninstall, this command SHALL request explicit confirmation of clean state for that store (a yes/no answer from the tester) before treating the pass as valid evidence, or accept a stated N/A; a device uninstall alone is not proof of clean state (`wos/rn-expo-runtime-evidence.md`). The leading cases are Keychain and SecureStore on an auth or biometric slice, which survive uninstall on both platforms and are why this gate exists; the same masking applies to a token cache, a local database, a persisted store key, a cached feature flag, and a completed-onboarding marker. The sharpest excluded case the old auth-only trigger let through: a first-run or onboarding slice verified on a device that has already run the app, where the pass observes the returning-user path and reports it as the first-run path. A one-line tester confirmation is sufficient; this is not a mandatory uninstall-reinstall-wipe cycle before every pass, and a slice whose behavior no persisted state can mask states N/A and moves on.

## Video evidence extraction (ADR-0107)

WHEN a screen recording is supplied as evidence, this command SHALL extract and review a minimum frame set (every distinct on-screen state transition, plus the frame immediately before and immediately after each reported symptom) before ruling any reported symptom in or out, and SHALL NOT classify an observed symptom as an environment artifact (a "simulator-only" or "flaky" dismissal) without citing the specific frame(s) reviewed that support that classification (`wos/rn-expo-runtime-evidence.md`).

## Evidence capture (the run directory)

Capture the platform log in this run rather than asking a human to paste it. Every artifact goes under the task folder in a per-slice run directory, `<task-folder>/evidence/<slice-id>/`, and every path written there is cited in the slice notes and in the report this command writes. The run directory lives in the task folder because it has to survive the session, which the session scratchpad does not.

The capture mechanism is platform log capture, and the exact commands stay in `wos/rn-expo-runtime-evidence.md` and `wos/unity-runtime-evidence.md`; this topic names which capture is required, never how to type it.

- Android: the process-scoped `adb logcat` capture, written as `logcat.txt` under the run directory. A full-buffer dump belongs there too when the scoped capture comes back silent.
- iOS: the device log through `xcrun simctl launch --console` for a simulator, or `devicectl` for a physical device, written as `device.log` under the run directory.
- The JS or managed console, when the run produced one, written as `console.log` under the run directory. For a Unity target both the managed and the native stream are captured, because a managed-only read shows a clean log for a run that crashed natively.
- The screen: `adb exec-out screencap` or `screenrecord` on Android, `xcrun simctl io booted screenshot` or the equivalent recording on iOS, written under the run directory.
- The view hierarchy, which is what makes a screen check mechanical instead of a picture someone reads. An accessibility-snapshot MCP is the mechanism: Maestro MCP's `inspect_screen`, the callstack `agent-device` server, or `mobile-next/mobile-mcp`. Write it as `hierarchy.txt` under the run directory. Any server exposing the same read is an equal substitute, and the report names whichever one ran.

WHEN no platform log capture is reachable for the target, the verdict is BLOCKED naming the missing capability (`no platform log capture reachable: no adb, no devicectl and no simctl for this target`), and that BLOCKED routes to `incident-triage` as a CONFIG failure so the capability is installed and this gate re-run. It is never a silent PASS, and it is never a stop that waits for a human to paste a log. A device a human is physically holding is the one case where the run itself needs that person: batch the device-only set per the command's own batching rule, capture whatever the session CAN capture, and record the remainder as `unverified: device-held run pending` rather than treating the whole gate as unrunnable.

## Golden baseline (visual checks)

A screenshot with no bug-free reference to compare it against is an artifact, not a check. Measured: median precision of 34 to 50 per cent with no reference screenshot, against 100 per cent with one. So a visual criterion needs a declared golden baseline, stored at `<task-folder>/evidence/baseline/<screen-slug>.png` and named in the report, and the check is the comparison against that file, never the screenshot on its own.

WHEN no baseline exists for a screen, still capture the image and write it, then record that screen's visual row as `unverified: no golden baseline` and say in the report that this run's image is the candidate baseline a human can promote. An `unverified` visual row is never an observed acceptance behavior. This does not soften the video rule above: a supplied recording still gets its minimum frame set reviewed, and a frame reviewed with no baseline behind it is reported as what it is.

## Mechanical and judgment criteria (static split)

The split is declared here, per battery rule, and is never decided per run. A per-run classification would have the agent judging its own capability at the point where the verdict is decided, which is the self-assessment this workflow rules out everywhere else.

| battery rule | class | decided from |
|---|---|---|
| runtime error classification against either taxonomy | mechanical | the captured platform log |
| the app launched and stayed up | mechanical | the captured log and the process state |
| entry path, including the cold-start requirement | mechanical | the captured log of a run started from a killed process |
| a screen was reached and carries the expected elements | mechanical | the captured view hierarchy |
| clean persisted state | judgment | a tester's stated yes, no or N/A, which no capture can replace |
| screen appearance: layout, spacing, visual regression | judgment | a human reading the image against the golden baseline |
| feel, pacing and responsiveness | judgment | a human using the build |

A mechanical row is decided here with no human in the loop, and it gates. A judgment row is reported with its artifact path and routed to the human-bound experience verdict (ADR-0091); it does not gate on its own, and it is never recorded as observed. WHEN the slice's acceptance behavior IS a judgment row, that criterion is `unverified` and the gate is BLOCKED with that reason, because no mechanical evidence for it exists.

## Taxonomy: RN/Expo adapter

Tag every error or anomaly with one taxonomy code: `NATIVE_CRASH` (a fatal native exception in logcat or the device log: a Fabric/`SurfaceMountingManager` mounting crash, a JNI or native-module crash), `NAVIGATION_TEARDOWN` (a crash or error tied to a screen unmounting or re-parenting during navigation, the navigation-teardown class: `addViewAt`, `already has a parent`, screen-stack teardown races), `JS_ERROR` (a JS runtime error or red-box in Metro/console: undefined is not a function, unhandled promise rejection), `MISSING_NATIVE_MODULE` (a native module not linked or a config-plugin/prebuild mismatch), `STARTUP_CRASH` (a crash on launch or a hang on the splash screen), `LAUNCH_INTENT_LOST` (the app launches cleanly but the intent that launched it, a quick action, notification tap, deep link, widget, or universal link, never reaches its destination: the distinguishing mark is that there is no error line at all, so a log-only read finds nothing and only the observed destination reveals it), `ANR` (Android "app not responding" or a main-thread stall), `PERMISSION_OR_CONFIG` (a runtime failure from a missing permission, env, or app-config value; defer numeric budgets to `performance-budget`), or `CLEAN` (no runtime error and the acceptance behavior was observed). One line per observation: the quoted symptom, the code, and the most likely cause. For a non-RN stack, map to the nearest equivalent codes and say which adapter was used.

## Taxonomy: Unity mobile adapter (ADR-0130)

WHEN the target is a Unity mobile build, use this adapter instead of the RN/Expo one and say so in the report. Unity runtime output splits into a managed stream (C# script logs, which do not terminate the process) and a native stream (process-fatal failures, retrieved on iOS via `bt all` in the Xcode debugger console or an Organizer crash report). Read BOTH before deciding: a managed-only read shows a clean log for a run that crashed natively, and a native-only read misses a managed exception that silently disabled a feature. Reuse `NATIVE_CRASH`, `STARTUP_CRASH`, `ANR`, `MISSING_NATIVE_MODULE` (a native plugin absent, unlinked, or ABI-mismatched), `PERMISSION_OR_CONFIG`, and `CLEAN` with the Unity signatures in `wos/unity-runtime-evidence.md`; add `MANAGED_EXCEPTION` (a C# exception in the managed stream that does not terminate the process, so the app is still running and the log is the only evidence the feature failed). Android and iOS have no player-log file path, so the evidence comes from the device capture, never from a log read off disk. WHEN a shader or variant-stripping failure or an Addressables reference-count failure is observed, classify it under the nearest shared code and say so: neither has a captured log signature yet, and guessing one produces a confident wrong code. Do NOT assert a Unity-specific `adb logcat` tag filter; the Unity manual documents the bare command and no such filter, so name whatever filter was actually applied.

## Cold-start requirement

**Cold-start requirement:** WHEN the acceptance behavior is triggered at process launch (a quick action, a notification tap, a deep link, a widget, or a universal link), a `cold-start` observation is required for PASS; a warm-only or in-app-only run caps the verdict at BLOCKED with reason `warm-only`, never PASS, and a human PASS asserted over a warm-only run does not lift the cap. The paths differ in what exists when the intent arrives (no navigator mounted, no hydrated auth, no warmed cache), which is exactly where a launch intent is lost with no error line to show for it.
