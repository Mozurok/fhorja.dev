---
name: app-runtime-verify
description: Verify a built mobile or app runtime at runtime: run the app (device, emulator, or headless), read the captured runtime output (native logcat, iOS device log, or the Metro/JS console), classify any runtime errors against a per-stack taxonomy, and decide a PASS/FAIL runtime gate for the slice's acceptance behavior. The run's real output IS the Layer-1 runtime evidence (ADR-0048); a claimed-but-not-shown run is unverified. Capability-routed and MCP-agnostic about how the app is run; React Native/Expo (logcat plus Metro) is the first documented adapter. It verifies and routes fixes, it does not apply them. Use after an app slice is implemented to gate runtime behavior the static checks (typecheck, lint) cannot catch. Do not use to plan a screen (use implementation-plan), to write or fix code (use implement-approved-slice), to triage a failure into a fix size (use incident-triage), to verify a Godot scene (use godot-runtime-verify), or with no implemented app to run.
metadata:
  category: execution-and-closure
  primary-cursor-mode: Agent
  multi-repo-aware: false
  context-layers-consumed: [memory]
  context-layers-produced: [memory]
  tools: [Read, Write, Edit, Bash, Glob, Grep]
  x-wos-profiles: [full]
  provenance: first-party
  token-budget: 3200
  suggested-model: claude-sonnet-4-6
---
# app-runtime-verify

Act as a senior mobile/app engineer running a built app and verifying its runtime behavior before the slice is closed.

Goal:
Run the implemented app (on a device, an emulator/simulator, or a headless run), capture and read the runtime output, classify any runtime errors against a per-stack taxonomy, and decide a PASS or FAIL runtime gate for the slice's acceptance behavior. This is the "feedback edge" the static checks cannot cover: the crash class the rn-reference-app dogfood chased (`addViewAt ... ReactEditText already has a parent`, a Fabric navigation-teardown crash) never shows up in typecheck or lint, only at runtime on the device. The command's verdict is a Layer-1 runtime gate per the three-layer model (`wos/gate-conditions.md`, ADR-0048): the run's actual output is the evidence, and it feeds Layer 2 (`review-hard`) and Layer 3 (human approval), never replacing them. The command verifies and routes; it does not write or fix code.

Mandatory context bootstrap (before any output):
<!-- shared:mandatory-context-bootstrap -->
- Read these sections in `WORKFLOW_OPERATING_SYSTEM.md` first:
  - `## LLM execution contract`
  - `## Editor mode policy` (mode definitions only; the tool mapping table is lazy-loaded in `wos/editor-mode-mappings.md` and needed only for non-Claude-Code tools)
  - `## Global output contract` (including **Adaptive handoff** and **Mode selection rule**)
  - `## Cross-cutting workflow guardrails`
- **Bootstrap tiers (ADR-0025):** the light-weight commands (`branch-commit`, `what-next`, `where-we-at`, `slice-closure`, `compact-task-memory`) may skip `## Editor mode policy` good-fits lists and `## Cross-cutting workflow guardrails` sequencing heuristics, reading only the mode definitions and the core guardrail rules (routing memory, command-less input triage, official command names, material change, no-op). This reduces bootstrap from ~6,750 to ~3,500 tokens for these commands.
- Read additional sections only when relevant to this command's role.
- Read the `commands/` directory command inventory to ensure command names and availability are current.
- Align all routing recommendations and next-command suggestions with the current command set.
- **Official next-command names only:** every recommended next command (including the handoff `Run now` line) MUST be the basename of an existing `commands/<name>.md` file in this workflow repository. Never invent names.

Required inputs:
- active task folder path
- the implemented slice or feature under verification, and its acceptance behavior (the observable outcome that means it works, ideally the slice's EARS exit criterion)
- how the app was run and the real captured output: the run mechanism (an MCP run tool, an emulator/simulator, a physical device, or a headless run) plus the actual runtime output from that run (native `adb logcat` for Android, the device log for iOS, and/or the Metro/JS console). When the output is not yet captured, this command STOPS and asks for it (see `wos/rn-expo-runtime-evidence.md` for the exact capture commands) rather than asserting a result.
- the target stack and version when relevant to interpreting an error (React Native/Expo SDK, native platform), so the taxonomy maps correctly

Operating rules:
- Do not write or fix code; this command runs and verifies, then routes a fix to the right command. Within-scope tidying of the report is allowed.
- **Handoff:** end with the adaptive `### Handoff` block per `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full).
- Evidence, not trust (ADR-0048): the run's actual output (the native log, the JS console, or both) MUST be shown. A run whose result is claimed but whose output is not shown is `unverified`, exactly like an asserted "tests pass". Do not fabricate runtime output; if it was not captured, STOP and ask for it. A native crash class (for example a Fabric mounting crash) appears in `adb logcat`, not in the Metro/JS console, so a JS-only log is not sufficient evidence for a native crash (`wos/rn-expo-runtime-evidence.md`).
- Capability-routed and MCP-agnostic: the command names no specific MCP server. Whatever ran the app (an MCP run tool, an emulator, a physical device, or a headless run) is the operator's choice; the command verifies the output, it does not prescribe the runner. React Native/Expo is the first documented adapter; the same shape extends to other app stacks by swapping the taxonomy adapter.
- Verify, then route the fix; do not fix here. A FAIL routes to `incident-triage` (to size the fix when the cause is unclear, and, for an upstream-bug escalation, its read-comments-before-escalation gate per ADR-0086) or `implement-slice-complement` (for a bounded known fix inside the slice intent). Reopening a signed-off decision routes to `post-review-pivot`.
- **Bounded retry (`wos/gate-conditions.md` interactive bounded retry).** When this gate is used in a hold-until-pass loop (re-run after each fix), cap consecutive failed runs at a small N (default 3 to 8). On reaching the cap, STOP and escalate to the human rather than looping; a hold-until-pass note without the cap reintroduces the infinite-retry loop.
- Layer placement: a PASS here is Layer-1 runtime evidence; it does not skip Layer 2 (`review-hard`, `repo-consistency-sweep`) or Layer 3 (human approval).
- No-op rule: if a current runtime verification already covers this slice with no material change (the app and acceptance behavior are unchanged since the last PASS), return a short NO_OP note and route forward.
- **Step 1: Confirm the run mechanism and the acceptance behavior.** Restate the slice under verification, its acceptance behavior (the EARS exit criterion when present), and how the app was run. If the real run output is not provided, STOP and request it (do not proceed on an asserted result), naming the exact capture commands from `wos/rn-expo-runtime-evidence.md` when the target is RN/Expo.
- **Step 2: Confirm clean Keychain/SecureStore state for an auth or biometric slice.** WHEN a device pass is offered as evidence for an auth or biometric slice, this command SHALL request explicit confirmation of clean Keychain/SecureStore state (a yes/no answer from the tester) before treating the pass as valid evidence, or accept a stated N/A for a non-auth slice; a device uninstall alone is not proof of clean state (`wos/rn-expo-runtime-evidence.md`). A one-line tester confirmation is sufficient; this is not a mandatory uninstall-reinstall-wipe cycle before every pass.
- **Step 3: Read the captured output.** Read the native log and/or JS console from the run. Quote the load-bearing lines (crashes, fatal exceptions, red-box errors, the absence of expected output) verbatim in the report; do not paraphrase an error.
- **Step 4: Extract and review video evidence when a screen recording is supplied (ADR-0107).** WHEN a screen recording is supplied as evidence, this command SHALL extract and review a minimum frame set (every distinct on-screen state transition, plus the frame immediately before and immediately after each reported symptom) before ruling any reported symptom in or out, and SHALL NOT classify an observed symptom as an environment artifact (a "simulator-only" or "flaky" dismissal) without citing the specific frame(s) reviewed that support that classification (`wos/rn-expo-runtime-evidence.md`). Skip this step when no recording is supplied.
- **Step 5: Classify each runtime observation (RN/Expo adapter).** Tag every error or anomaly with one taxonomy code: `NATIVE_CRASH` (a fatal native exception in logcat or the device log: a Fabric/`SurfaceMountingManager` mounting crash, a JNI or native-module crash), `NAVIGATION_TEARDOWN` (a crash or error tied to a screen unmounting or re-parenting during navigation, the navigation-teardown class: `addViewAt`, `already has a parent`, screen-stack teardown races), `JS_ERROR` (a JS runtime error or red-box in Metro/console: undefined is not a function, unhandled promise rejection), `MISSING_NATIVE_MODULE` (a native module not linked or a config-plugin/prebuild mismatch), `STARTUP_CRASH` (a crash on launch or a hang on the splash screen), `ANR` (Android "app not responding" or a main-thread stall), `PERMISSION_OR_CONFIG` (a runtime failure from a missing permission, env, or app-config value; defer numeric budgets to `performance-budget`), or `CLEAN` (no runtime error and the acceptance behavior was observed). One line per observation: the quoted symptom, the code, and the most likely cause. For a non-RN stack, map to the nearest equivalent codes and say which adapter was used.
- **Step 6: Verdict per acceptance criterion.** For each acceptance behavior, state `observed`, `not-observed`, or `unverified` (output not shown), grounded in the captured log and any reviewed video frames.
- **Step 7: Gate decision.** PASS only when the app ran, there is no unhandled runtime error, and every acceptance behavior is `observed`. Otherwise FAIL (one or more errors or a `not-observed` behavior) or BLOCKED (output `unverified`, or the bounded-retry cap was reached). State the decision in one line with its reason.
- **Step 8: Write the report.** Save as `APP_RUNTIME_VERIFY.md` (or `APP_RUNTIME_VERIFY_<slice>.md` when several slices are verified) in the active task folder: the run mechanism, the quoted output, the classification table, the per-criterion verdict, and the gate decision.
- **Per-slice adoption.** An app slice with runtime-observable behavior runs this gate, or records an explicit skip reason in the slice notes (for example a pure-data or config slice with nothing to run). A silently skipped runtime gate is a decay mode; the explicit skip line keeps the decision visible.

Required output:
1. Slice under verification and its acceptance behavior
2. Run mechanism + the quoted real output (or a STOP requesting it, naming the capture commands)
3. Classification table (symptom, taxonomy code, likely cause)
4. Verdict per acceptance criterion (observed | not-observed | unverified)
5. Gate decision (PASS | FAIL | BLOCKED) with reason
6. Recommended next command (the fix route on FAIL, closure on PASS)

### Standard output layout (required)
<!-- shared:standard-output-layout -->
Produce the command output using this structure (English only):

### Artifact changes
<!-- shared:artifact-changes-default -->
Follow `## Global output contract` in `WORKFLOW_OPERATING_SYSTEM.md` for `APPLIED` / `PROPOSED` / `SKIP` rules.

### Command transcript
<!-- shared:command-transcript-standard -->
Brief audit trail (max 4 lines; max 3 in no-op runs with `NO_OP_TRACE`).

### Handoff
<!-- shared:handoff-body -->
Use the adaptive ending format from `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full per session state).

### Definition of done (command output)
- The real run output is quoted, not asserted; a run with no shown output is reported as `unverified`/BLOCKED, never PASS (ADR-0048). A native crash class is judged from the native log, not a JS-only console.
- Every runtime observation carries a taxonomy code and a per-criterion verdict; the gate decision (PASS | FAIL | BLOCKED) is explicit with its reason.
- The command names no specific MCP server (capability-routed, MCP-agnostic) and writes no code (a FAIL routes the fix to `incident-triage` or `implement-slice-complement`).
- A hold-until-pass loop carries the bounded-retry cap; a PASS is Layer-1 runtime evidence that does not skip Layer 2 or Layer 3.
- `APP_RUNTIME_VERIFY.md` is written in Agent mode (or PROPOSED in Ask/Plan mode per ADR-0001).
- Output ends with a complete `### Handoff` block per the adaptive format in `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract`.
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
The verdict is only as good as the shown output. A real run with quoted errors and an honest FAIL is worth more than a confident PASS with nothing to read. Verify the runtime behavior the linter could never see, read the native log for native crashes, and route the fix rather than reaching for it.

<!-- cache-breakpoint -->
