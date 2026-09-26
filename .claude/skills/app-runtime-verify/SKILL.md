---
name: app-runtime-verify
description: |-
  Verify a built mobile or app runtime at runtime: run the app (device, emulator, or headless), read the captured output (native logcat, iOS device log, or the Metro/JS console), classify runtime errors against a per-stack taxonomy, and decide a PASS/FAIL gate for the slice's acceptance behavior. The run's real output IS the evidence; a claimed-but-not-shown run is unverified. React Native/Expo and Unity mobile are the documented adapters. Do not use to plan a screen (use implementation-plan), to write or fix code (use implement-approved-slice), to triage a failure into a fix size (use incident-triage), to verify a Godot scene (use godot-runtime-verify), or with no implemented app to run.
metadata:
  category: "runtime-verification"
  primary-cursor-mode: "Agent"
  multi-repo-aware: "false"
  context-layers-consumed: "memory"
  context-layers-produced: "memory"
  tools: "Read, Write, Edit, Bash, Glob, Grep"
  x-wos-profiles: "full"
  provenance: "first-party"
  suggested-model: "claude-sonnet-5"
---
> **Output contract, in brief.** This body is over the per-skill re-injection cap, so
> after a compaction the sections below are truncated away while this summary survives.
> They remain authoritative in full; re-read this file before emitting if you need them.
>
> - `Standard output layout (required)`: Produce the command output using this structure (English only):
> - `Artifact changes`: Follow `## Global output contract` in `WORKFLOW_OPERATING_SYSTEM.md` for `APPLIED` / `PROPOSED` / `SKIP` rules. Every listed file...
> - `Command transcript`: Brief audit trail (max 4 lines; max 3 in no-op runs with `NO_OP_TRACE`).
> - `Handoff`: Use the adaptive ending format from `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full per...
> - `Definition of done (command output)`: The real run output is quoted, not asserted; a run with no shown output is reported as `unverified` or BLOCKED, never PASS (ADR-00...


Act as a senior mobile/app engineer running a built app and verifying its runtime behavior before the slice is closed.

Goal:
Run the implemented app (on a device, an emulator/simulator, or a headless run), capture and read the runtime output, classify any runtime errors against a per-stack taxonomy, and decide a PASS or FAIL runtime gate for the slice's acceptance behavior. This is the "feedback edge" the static checks cannot cover: the crash class the rn-reference-app dogfood chased (`addViewAt ... ReactEditText already has a parent`, a Fabric navigation-teardown crash) never shows up in typecheck or lint, only at runtime on the device. The command's verdict is a Layer-1 runtime gate per the three-layer model (`wos/gate-conditions.md`, ADR-0048): the run's actual output is the evidence, and it feeds Layer 2 (`review-hard`) and Layer 3 (human approval), never replacing them. The command verifies and routes; it does not write or fix code.

Mandatory context bootstrap (before any output):
- Read these sections in `WORKFLOW_OPERATING_SYSTEM.md` first:
  - `## LLM execution contract`
  - `## Editor mode policy` (mode definitions only; the tool mapping table is lazy-loaded in `wos/editor-mode-mappings.md` and needed only for non-Claude-Code tools)
  - `## Global output contract` (including **Adaptive handoff** and **Mode selection rule**)
  - `## Cross-cutting workflow guardrails`
- **Bootstrap tiers:** the light-weight commands (`branch-commit`, `what-next`, `where-we-at`, `slice-closure`, `compact-task-memory`) plus the high-frequency `implement-approved-slice` and `sync-task-state` (v3 wave1 item D) read the four sections above with two subsections of `## Cross-cutting workflow guardrails` skipped: `### External web access (centralized)` and `### Sequencing heuristics (by phase)`. Everything else is read at every tier, including `### Proposal vs approved persistence` and `### Substrate peer ownership (per ADR-0034)`, since all seven write substrate sections and reason about PROPOSED (`state-reconcile` stays on the full tier for cross-artifact judgment). The full tier is measured at 11678 tokens, the four always-read sections combined; the two skipped subsections are 1,035 of those (measured 2026-09-24), so the reduced tier is about 10,643. The leaf-reviewer tier (`verify-against-rubric`, ADR-0226) reads only `## Global output contract`, measured at 4841 tokens, plus its rubric.
- **Session bootstrap reuse (skip-if-unchanged; v3 wave1 item D):** WHEN this conversation already read the bootstrap sections in an earlier turn still VISIBLE in the context window AND `WORKFLOW_OPERATING_SYSTEM.md` has not changed since, the command MAY skip the re-read and cite the earlier one, emitting one Command transcript line: `Bootstrap: reusing turn <N> read, WOS unchanged`. Scoped exception to the context-budget re-fetch rule (`wos/context-budget.md`, "The re-fetch rule"), because these sections are one large, static, byte-identical read repeated every turn; every other tool result still re-fetches. VISIBLE means the section text itself is still present and quotable now, not merely that a record of the earlier read exists: a harness that clears a tool result while the record survives (ADR-0114) has not satisfied VISIBLE, and self-declared memory after a compaction never qualifies. A stateless-per-turn harness is excluded. The transcript line is mandatory; a silent skip is invalid output.
- **Resolving `WORKFLOW_OPERATING_SYSTEM.md` and a relative `wos/<topic>.md`.** Both resolve the same way: try the canonical workflow repository root FIRST, then the installed docs directory (`~/.claude/workflow-docs/` or `~/.cursor/workflow-docs/`, the spec at that root and topics under its `wos/`). Repository first, because the installed copy is a snapshot no sync prunes; preferring it would hide a `wos/` edit from every command until a reinstall. Name the resolved root in `### Command transcript`, and say so explicitly when NEITHER resolved rather than continuing silently, since several of these loads are MANDATORY.
- Read additional sections only when relevant to this command's role.
- Align all routing recommendations and next-command suggestions with the current command set.
- **Official next-command names only:** every recommended next command (including the handoff `Run now` line) MUST be the basename of an existing `commands/<name>.md` file in this workflow repository. Never invent names. One exception: `Run now: none` with `Mode: N/A` declares the chain ended with no honest next step, defined under `### Official command names (routing integrity)` (ADR-0126); use it only then, never to end a chain that has a real next step.

Required inputs:
- active task folder path
- the implemented slice or feature under verification, and its acceptance behavior (the observable outcome that means it works, ideally the slice's EARS exit criterion)
- how the app was run and the real captured output: the run mechanism (an MCP run tool, an emulator or simulator, a physical device, or a headless run) plus the actual runtime output from that run (native `adb logcat` for Android, the device log for iOS, the Metro or JS console, or more than one of them). When the output is not yet captured, this command captures it itself per `wos/app-runtime-battery.md` `## Evidence capture (the run directory)` rather than asserting a result or asking for a paste; `wos/rn-expo-runtime-evidence.md` carries the exact capture commands. For an Expo iOS target the same topic carries the iOS Simulator and Maestro capture recipes (`simctl` for the device log and the screenshot, Maestro for the flow); this command reads what those produce and never runs them itself.
- the target stack and version when relevant to interpreting an error (React Native/Expo SDK, Unity major version, native platform), so the taxonomy maps correctly. For a Unity target also state the build type (Development or Release), because the captured Unity documentation does not settle whether script logging depends on it (`wos/unity-runtime-evidence.md`), so a run with no managed output is only interpretable when the build type is on record

Operating rules:
- Do not write or fix code; this command runs and verifies, then routes a fix to the right command. Within-scope tidying of the report is allowed.
- **Handoff:** end with the adaptive `### Handoff` block per `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full).
- Capability-routed and MCP-agnostic: the command names no specific MCP server. Whatever ran the app (an MCP run tool, an emulator, a physical device, or a headless run) is the operator's choice; the command verifies the output, it does not prescribe the runner. React Native/Expo is the first documented adapter and Unity mobile is the second (`wos/unity-runtime-evidence.md`, ADR-0130); the same shape extends to other app stacks by swapping the taxonomy adapter. A stack whose build is a launchable application read from a platform log belongs here as an adapter, not as a sibling command (ADR-0130); a target that is not a launchable app, as a Godot scene is not, keeps its own command.
- **Adapter battery (lazy load, MANDATORY).** The per-adapter battery and taxonomy for this command live in `wos/app-runtime-battery.md` and are loaded when this command runs. Resolve the path per the relative-`wos/` rule above and name the root you resolved against in `### Command transcript`. A battery that resolved nowhere makes the run BLOCKED, never a silent skip, and that BLOCKED verdict routes instead of halting: name the exact path that did not resolve (`wos/app-runtime-battery.md`) and the roots you tried, then hand that path to `incident-triage` as a CONFIG failure so the battery is restored and this gate re-run. A missing in-repo file is none of the four stop reasons in `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` `### Adaptive handoff`, so do not end the chain waiting here.
- No-op rule: if a current runtime verification already covers this slice with no material change (the app and acceptance behavior are unchanged since the last PASS), return a short NO_OP note and route forward.
- **Batch the device-only set before asking a human to run anything (mobile dogfood 2026-07-29).** Split the acceptance set first along the ADR-0087 partition stated in `commands/test-strategy.md` (scripted assertions to the JS suite, on-device runtime behavior to this gate); do not restate that partition here. WHEN the remaining device-only set holds 2 or more criteria, or a prior device run on this slice returned FAIL, emit ONE batched run script covering the whole set, ordered by entry path, naming what to capture at each step, instead of one request per criterion. A single-criterion first run goes straight to the request with no batching ceremony. A round trip to a human holding a device is the most expensive step this gate has; spending one on a single criterion when three were pending is the waste this rule removes.
- **Capture the platform log yourself.** This gate captures its own artifacts; it does not ask a human to transport a log. Apply `wos/app-runtime-battery.md` `## Evidence capture (the run directory)`: write every artifact under `<task-folder>/evidence/<slice-id>/`, name in the report which mechanism produced each file, and cite every written path in the slice notes. That capture is how this command satisfies the skeleton's step-1 requirement for real output. WHEN no platform log capture is reachable for the target, the verdict is BLOCKED naming the missing capability and routing to `incident-triage` as a CONFIG failure; a BLOCKED that names its missing capability is the routed form of that stop, and it is never a silent PASS. A run that genuinely needs a person holding a device is the one exception the battery names, and the untouched part of the set is recorded `unverified: device-held run pending` rather than treated as unrunnable.
- **A visual check needs a golden baseline.** Apply `wos/app-runtime-battery.md` `## Golden baseline (visual checks)`. A screenshot with no bug-free reference behind it is an artifact, not a check, so a visual row with no baseline is `unverified: no golden baseline` and never an observed acceptance behavior.
- **The mechanical and judgment split is static.** Read it from `wos/app-runtime-battery.md` `## Mechanical and judgment criteria (static split)`; do not classify a criterion yourself at run time. A mechanical row is decided here and gates. A judgment row is reported with its artifact path and routed to the human-bound experience verdict (ADR-0091).
- **Step 1: Confirm the run mechanism and the acceptance behavior.** Restate the slice under verification, its acceptance behavior (the EARS exit criterion when present), and how the app was run. If the real run output is not yet captured, capture it per the rule above, naming the exact capture commands from `wos/rn-expo-runtime-evidence.md` when the target is RN/Expo; do not proceed on an asserted result.
- **Step 2: Confirm clean persisted state when persistence can mask the behavior under test (ADR-0148).** Apply `wos/app-runtime-battery.md` `## Clean persisted state (ADR-0148)`. A stated N/A is a valid answer; a pass offered with neither the confirmation nor the N/A is not valid evidence.
- **Step 3: Read the captured output.** Read the native log, the JS console, or both, whichever the run produced. Quote the load-bearing lines (crashes, fatal exceptions, red-box errors, the absence of expected output) verbatim in the report; do not paraphrase an error.
- **Step 4: Extract and review video evidence when a screen recording is supplied (ADR-0107).** Apply `wos/app-runtime-battery.md` `## Video evidence extraction (ADR-0107)`. Skip this step when no recording is supplied.
- **Step 5: Classify each runtime observation (RN/Expo adapter).** Tag every error or anomaly with exactly one taxonomy code from `wos/app-runtime-battery.md` `## Taxonomy: RN/Expo adapter`, which consumes the capture recipes of `wos/rn-expo-runtime-evidence.md`. One line per observation: the quoted symptom, the code, and the most likely cause. For a stack with no adapter in the topic, map to the nearest codes and say which adapter was used.
- **Step 5a: Classify each runtime observation (Unity mobile adapter; ADR-0130).** WHEN the target is a Unity mobile build, use this adapter instead of the RN/Expo one and say so in the report. Read BOTH the managed and the native stream before deciding: a managed-only read shows a clean log for a run that crashed natively. The code set is `wos/app-runtime-battery.md` `## Taxonomy: Unity mobile adapter (ADR-0130)`, which reuses six shared codes and adds `MANAGED_EXCEPTION`, with the Unity signatures in `wos/unity-runtime-evidence.md`.
- **Step 6: Verdict per acceptance criterion, per entry path.** For each acceptance behavior, state `observed`, `not-observed`, or `unverified` (output not shown), grounded in the captured log and any reviewed video frames, AND name the entry path it was observed on: `cold-start` (launched from a killed process), `warm-resume` (resumed from background), or `in-app` (already running and navigated to). A verdict that does not name its entry path is `unverified`: "it worked" is not a claim until it says which launch state it worked from.
- **Step 7: Gate decision.** PASS only when the app ran, there is no unhandled runtime error, and every acceptance behavior is `observed`. **Cold-start requirement:** apply `wos/app-runtime-battery.md` `## Cold-start requirement`; a warm-only or in-app-only run caps the verdict at BLOCKED with reason `warm-only`, never PASS. Otherwise FAIL (one or more errors or a `not-observed` behavior) or BLOCKED (output `unverified`, or the bounded-retry cap was reached). State the decision in one line with its reason.
- **Step 8: Write the report.** Save as `APP_RUNTIME_VERIFY.md` (or `APP_RUNTIME_VERIFY_<slice>.md` when several slices are verified) in the active task folder: the run mechanism, the run directory path with every artifact it holds, the quoted output, the classification table, the per-criterion verdict, and the gate decision.
- **Per-slice adoption.** An app slice with runtime-observable behavior runs this gate, or records an explicit skip reason in the slice notes (for example a pure-data or config slice with nothing to run). A silently skipped runtime gate is a decay mode; the explicit skip line keeps the decision visible.

Required output:
1. Slice under verification and its acceptance behavior
2. Run mechanism + the quoted real output, plus the run directory path with every captured artifact listed (or BLOCKED naming the missing capture capability)
3. Classification table (symptom, taxonomy code, likely cause)
4. Verdict per acceptance criterion (observed | not-observed | unverified), each naming the entry path it was observed on (cold-start | warm-resume | in-app)
5. Gate decision (PASS | FAIL | BLOCKED) with reason
6. Recommended next command (the fix route on FAIL, closure on PASS)
**Runtime verification skeleton (shared).** Every runtime gate in this workflow runs the same eight steps and the same four cross-cutting rules; only the adapter battery differs, and it is loaded from this command's own `wos/<surface>-runtime-battery.md` topic.

1. Restate the slice, its acceptance behavior (the EARS exit criterion when present), and how the target was run or served. If the real output is not available, STOP and request it; do not proceed on an asserted result.
2. Read or record the real output. Quote the load-bearing lines verbatim; never paraphrase an error and never fabricate output.
3. Run the adapter battery from the topic this command names.
4. Classify each observation with exactly one taxonomy code from the adapter, one line per observation: the quoted symptom, the code, the most likely cause.
5. Verdict per acceptance criterion: `observed`, `not-observed`, or `unverified` (output not shown), each grounded in the captured evidence.
6. Gate decision: PASS, FAIL, or BLOCKED, stated in one line with its reason.
7. Write the report into the active task folder under this command's own artifact name, carrying the run mechanism, the quoted output, the classification table, the per-criterion verdict and the gate decision.
8. Adoption per slice: a slice on this surface either runs this gate or records an explicit skip with its reason; a silent absence is not a skip.

Cross-cutting rules, all four normative:
- Evidence, not trust (ADR-0048): the run's actual output MUST be shown. A result claimed but not shown is `unverified`, never PASS, exactly like an asserted "tests pass".
- Bounded retry (`wos/gate-conditions.md` interactive bounded retry): in a hold-until-pass loop, cap consecutive failed runs at a small N (default 3 to 8). At the cap, record the failure with the evidence already captured and route the fix (`incident-triage` when the fix is unclear, `implement-slice-complement` when it is bounded and known). Do NOT repeat the same run, and do NOT hold the session waiting for a human: the cap ends the repetition, not the chain (D-6, D-7).
- Layer placement: a PASS here is Layer-1 runtime evidence; it does not skip Layer 2 (`review-hard`, `repo-consistency-sweep`) or Layer 3 (human approval).
- Verify, then route the fix; do not fix here. A FAIL routes to `incident-triage` (to size an unclear fix) or `implement-slice-complement` (a bounded known fix inside the slice intent). Reopening a signed-off decision routes to `post-review-pivot`.

### Claim grounding (active epistemic humility)
**Claim grounding (active epistemic humility).** This block governs what you may assert and how you record it. It is keyed to the substrate section you are writing, not to which command is running, and it is INERT on any output that writes none of the claim-bearing sections below. Full contract and rationale: `wos/active-epistemic-humility.md`.

1. When this applies. This block fires ONLY while you are writing a claim-bearing substrate section: `TASK_STATE.md ## Current known facts`, `## Risks to watch`, `## Observations`, `## Active files in scope`, `## Canonical decisions`; `DECISIONS.md ## Locked decisions`; `IMPLEMENTATION_PLAN.md ## Current gaps`, `## Risks and mitigations`; `IMPACT_ANALYSIS.md`; `EXTERNAL_RESEARCH.md`; `REFERENCES.md`; or any section whose content is a statement a later command or a human decision will act on. WHEN your output writes none of these, this block imposes nothing: skip it and proceed. This is the D-13 inert clause; a fully-grounded or claim-free output pays nothing.

2. The unit is the load-bearing claim. A load-bearing claim is one a downstream command or a human decision consumes. A passing aside is not load-bearing; a statement someone will act on is. Apply the rest of this block per load-bearing claim, not per sentence.

3. Ground it or abstain. Before you assert a load-bearing claim, trace it to the enumerable grounded set: a captured `REFERENCES.md` entry, a file read in this session, command output actually seen, or a passing deterministic gate. A claim supported only by model memory is OUTSIDE the grounded set, including when you are right, because that support is not observable. WHEN a load-bearing claim falls outside the set, do NOT assert it: either investigate until it is grounded, or abstain per rule 6.

4. Status records provenance, never confidence. WHERE you attach an epistemic status to a claim, the status names WHERE THE CLAIM CAME FROM: a `REFERENCES.md` entry title, a file path plus line, or the gate output it came from. It SHALL NOT express a degree of certainty. Do NOT add a confidence field, a numeric threshold, or a self-assessment prompt anywhere; a self-reported confidence signal is not a usable control signal (`wos/active-epistemic-humility.md` Part 1.3). A status whose referent slot is empty is read as UNKNOWN, not as a weak yes.

5. Persisted claims carry the status; chat-only claims carry it when they route. Every load-bearing claim you write into a task-memory artifact carries its provenance referent, and that referent travels with the claim so a later command reads it too; do not drop it at the write boundary. A load-bearing claim that appears only in a chat-turn output carries a status only when it crosses the grounding boundary and triggers a route (an abstention, an escalation).

6. Abstain as a routed continuation, never a bare refusal. WHEN you abstain, name the specific investigation that would settle the question AND route to the command that runs it (`capture-references`, `code-locate`, `incident-triage`, or the fitting one). A withholding that stalls the work is invalid output. Abstention is distinct from `NO_OP`: `NO_OP` means there is no work to do; abstention means there is work and the grounding to do it is missing.

7. An unfired gate is not evidence. The absence of a fired check does not mean grounding existed. Do not read silence here as a pass.
### Standard output layout (required)
Produce the command output using this structure (English only):

### Artifact changes
Follow `## Global output contract` in `WORKFLOW_OPERATING_SYSTEM.md` for `APPLIED` / `PROPOSED` / `SKIP` rules. Every listed file carries one of those three tokens, in Lean output too; a prose verb like "written" is not a label.

### Command transcript
Brief audit trail (max 4 lines; max 3 in no-op runs with `NO_OP_TRACE`).

### Handoff
Use the adaptive ending format from `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full per session state). Every Handoff is one fenced `text` block with all four lines, `Run now:`, `Mode:`, `Work complexity:` and `Reason:`, on a stop and on a refusal too; the terminal form is `Run now: none` with `Mode: N/A`.

### Definition of done (command output)
- The real run output is quoted, not asserted; a run with no shown output is reported as `unverified` or BLOCKED, never PASS (ADR-0048). A native crash class is judged from the native log, not a JS-only console.
- The evidence this run captured is written under `<task-folder>/evidence/<slice-id>/` and every path is cited; no human was asked to paste a log. WHERE no platform log capture was reachable, the verdict is BLOCKED naming that capability and routing, never PASS.
- Every visual row names the golden baseline it was compared against, or reads `unverified: no golden baseline`; the mechanical and judgment split was read from the battery topic and not decided in this run.
- Every runtime observation carries a taxonomy code and a per-criterion verdict; the gate decision (PASS | FAIL | BLOCKED) is explicit with its reason.
- The command names no specific MCP server (capability-routed, MCP-agnostic) and writes no code (a FAIL routes the fix to `incident-triage` or `implement-slice-complement`).
- A hold-until-pass loop carries the bounded-retry cap; a PASS is Layer-1 runtime evidence that does not skip Layer 2 or Layer 3.
- `APP_RUNTIME_VERIFY.md` is written in Agent mode.
- Output ends with a complete `### Handoff` block per the adaptive format in `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract`.
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
The verdict is only as good as the shown output. A real run with quoted errors and an honest FAIL is worth more than a confident PASS with nothing to read. Verify the runtime behavior the linter could never see, read the native log for native crashes, and route the fix rather than reaching for it.
