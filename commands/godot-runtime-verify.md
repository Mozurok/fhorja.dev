---
name: godot-runtime-verify
description: Verify a built Godot 2D scene at runtime: run the scene (press-play or headless), read the captured debugger output, classify any runtime errors against a Godot-specific taxonomy, and decide a PASS/FAIL runtime gate for the slice's acceptance behavior. The run's real output IS the Layer-1 runtime evidence (ADR-0048); a claimed-but-not-shown run is unverified. MCP-agnostic about how the scene is run; it verifies and routes fixes, it does not apply them. Use after a Godot slice is implemented to gate runtime behavior the static checks (lint, typecheck) cannot catch. Do not use to plan a scene (use godot-scene-plan), to write or fix the code (use implement-approved-slice or implement-slice-complement), to triage a failure into a fix size (use incident-triage), or with no implemented scene to run.
metadata:
  category: execution-and-closure
  primary-cursor-mode: Agent
  multi-repo-aware: false
  context-layers-consumed: [memory]
  context-layers-produced: [memory]
  tools: [Read, Write, Edit, Bash, Glob, Grep]
  x-wos-profiles: [full]
  provenance: first-party
  token-budget: 2400
  suggested-model: claude-sonnet-4-6
---
# godot-runtime-verify

Act as a senior Godot engineer running a built 2D scene and verifying its runtime behavior before the slice is closed.

Goal:
Run the implemented Godot scene (press-play in the editor or a headless run), capture and read the debugger output, classify any runtime errors against a Godot-specific taxonomy, and decide a PASS or FAIL runtime gate for the slice's acceptance behavior. This is the "feedback edge" that the static checks cannot cover: most Godot bugs are runtime bugs a linter never catches (EXTERNAL_RESEARCH.md A2). The command's verdict is a Layer-1 runtime gate per the three-layer model (`wos/gate-conditions.md`, ADR-0048): the run's actual output is the evidence, and it feeds Layer 2 (`review-hard`) and Layer 3 (human approval), never replacing them. The command verifies and routes; it does not write or fix code.

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
- how the scene was run and the real captured output: the run mechanism (an MCP server run tool, the Godot CLI headless run, or a human pressing play) plus the actual debugger or console output from that run. When the output is not yet captured, this command STOPS and asks for it rather than asserting a result.
- the target Godot version, when relevant to interpreting an error

Operating rules:
- Do not write or fix code; this command runs and verifies, then routes a fix to the right command. Within-scope tidying of the report is allowed.
- **Handoff:** end with the adaptive `### Handoff` block per `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full).
- Evidence, not trust (ADR-0048): the run's actual output (debugger or console log) MUST be shown. A run whose result is claimed but whose output is not shown is `unverified`, exactly like an asserted "tests pass". Do not fabricate runtime output; if it was not captured, STOP and ask for it.
- MCP-agnostic (DECISIONS D-1): the command names no specific MCP server. Whatever ran the scene (an MCP run tool, the Godot CLI `--headless`, or a human) is the operator's choice; the command verifies the output, it does not prescribe the runner.
- Verify, then route the fix; do not fix here. A FAIL routes to `incident-triage` (to size the fix when the cause is unclear) or `implement-slice-complement` (for a bounded known fix inside the slice intent). Reopening a signed-off decision routes to `post-review-pivot`.
- **Bounded retry (`wos/gate-conditions.md` interactive bounded retry).** When this gate is used in a hold-until-pass loop (re-run after each fix), cap consecutive failed runs at a small N (default 3 to 8). On reaching the cap, STOP and escalate to the human rather than looping; a hold-until-pass note without the cap reintroduces the infinite-retry loop.
- Layer placement: a PASS here is Layer-1 runtime evidence; it does not skip Layer 2 (`review-hard`, `repo-consistency-sweep`) or Layer 3 (human approval).
- No-op rule: if a current runtime verification already covers this slice with no material change (the scene and acceptance behavior are unchanged since the last PASS), return a short NO_OP note and route forward.
- **Environment preflight.** Before the gate runs, the command MUST resolve the Godot binary: try `godot --version` on PATH first; on macOS, fall back to the app bundle binary (`/Applications/Godot.app/Contents/MacOS/Godot`). Record the resolved path in the run evidence. If no binary resolves, STOP and ask the user where Godot lives rather than improvising a runner.
- **Persistent probe harness.** Probe scenes and scripts live under `probes/` in the game repo and are kept under version control, not written and deleted per slice. A probe MUST be self-terminating: call `get_tree().quit()` on PASS or FAIL, with a physics-frame backstop so a hung probe still exits. Drive behavior by calling handlers directly (for example `spawner._drop()`), never through simulated input timing or wall-clock waits.
- **Adversarial probe requirement.** The runtime gate for a mechanic acceptance MUST include at least one adversarial or stress probe (rapid repeated input, boundary states, spam of the core action) alongside the happy-path probe. A gate that ran only happy-path probes is incomplete evidence and MUST say so in its verdict.
- **Step 1: Confirm the run mechanism and the acceptance behavior.** Restate the slice under verification, its acceptance behavior (the EARS exit criterion when present), and how the scene was run. If the real run output is not provided, STOP and request it (do not proceed on an asserted result).
- **Step 2: Read the captured output.** Read the debugger or console log from the run. Quote the load-bearing lines (errors, warnings, the absence of expected output) verbatim in the report; do not paraphrase an error.
- **Step 3: Classify each runtime observation.** Tag every error or anomaly with one taxonomy code: `SCRIPT_ERROR` (a GDScript runtime error: nil method call, type mismatch, bad cast), `MISSING_NODE_OR_RESOURCE` (a node path not found or a resource that failed to load), `SIGNAL_NOT_CONNECTED` (an expected signal never fires or was never wired), `NULL_REFERENCE` (access to a freed or never-assigned node), `PHYSICS_OR_COLLISION` (a body that does not move, a collision layer/mask mismatch), `INPUT_NOT_MAPPED` (an action missing from the input map, or no touch binding on a mobile target), `PERFORMANCE_STALL` (frame drops or a hang; defer numeric budgets to `performance-budget`), or `CLEAN` (no runtime error and the acceptance behavior was observed). One line per observation: the quoted symptom, the code, and the most likely cause.
- **Step 4: Verdict per acceptance criterion.** For each acceptance behavior, state `observed`, `not-observed`, or `unverified` (output not shown), grounded in the captured log.
- **Step 5: Gate decision.** PASS only when the scene ran, there is no unhandled runtime error, and every acceptance behavior is `observed`. Otherwise FAIL (one or more errors or a `not-observed` behavior) or BLOCKED (output `unverified`, or the bounded-retry cap was reached). State the decision in one line with its reason.
- **Step 6: Write the report.** Save as `GODOT_RUNTIME_VERIFY.md` (or `GODOT_RUNTIME_VERIFY_<slice>.md` when several slices are verified) in the active task folder: the run mechanism, the quoted output, the classification table, the per-criterion verdict, and the gate decision.
- **Step 7: Emit or update the playtest runbook (ADR-0084).** Alongside the machine-run gate, write or update `PLAYTEST_RUNBOOK.md` in the active task folder: how a human launches the scene (the run command or the press-play steps and the main scene to set), the specific things to exercise (the acceptance behaviors plus what the automated gate cannot judge: feel, difficulty, pacing, and fidelity to the reference or the `MECHANICS_SPEC.md`), and where the playtester's notes go. The runbook is the durable, repeatable counterpart to the automated gate. This gate catches crashes and missing behaviors; the human playtest catches wrong-but-running mechanics the gate passes, which is the ADR-0084 failure: the runtime gate PASSED a core mechanic that was objectively wrong, because it verifies the contract and cannot question it. An improvised one-off run instruction is not a runbook; the artifact is the point.
- **Route human playtest notes to `pr-feedback-ingest --playtest` (ADR-0084).** When the operator returns playtest feedback (the game runs but plays wrong, a mechanic is off, a screen flow is missing), the handoff routes it to `pr-feedback-ingest --playtest`, a first-class corrective ingestion path, not to a general review command. Do not absorb playtest feedback into an ad-hoc review.
- **Per-slice adoption (ADR-0084).** A Godot slice with runtime-observable behavior runs this gate, or records an explicit skip reason in the slice notes (for example a pure-data or config slice with nothing to run). A silently skipped runtime gate is the observed decay mode (the dogfood ran the gate once and dropped it for the two larger builds); the explicit skip line keeps the decision visible.

Required output:
1. Slice under verification and its acceptance behavior
2. Run mechanism + the quoted real output (or a STOP requesting it)
3. Classification table (symptom, taxonomy code, likely cause)
4. Verdict per acceptance criterion (observed | not-observed | unverified)
5. Gate decision (PASS | FAIL | BLOCKED) with reason
6. `PLAYTEST_RUNBOOK.md` written or updated (how to run, what to exercise including mechanic feel, where notes go)
7. Recommended next command (the fix route on FAIL, closure on PASS, or `pr-feedback-ingest --playtest` when the operator returns human playtest notes)

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
- The real run output is quoted, not asserted; a run with no shown output is reported as `unverified`/BLOCKED, never PASS (ADR-0048).
- Every runtime observation carries a taxonomy code and a per-criterion verdict; the gate decision (PASS | FAIL | BLOCKED) is explicit with its reason.
- The command names no specific MCP server (MCP-agnostic, DECISIONS D-1) and writes no code (a FAIL routes the fix to `incident-triage` or `implement-slice-complement`).
- A hold-until-pass loop carries the bounded-retry cap; a PASS is Layer-1 runtime evidence that does not skip Layer 2 or Layer 3.
- `GODOT_RUNTIME_VERIFY.md` is written in Agent mode (or PROPOSED in Ask/Plan mode per ADR-0001).
- `PLAYTEST_RUNBOOK.md` is written or updated with the run steps, the behaviors to exercise (including mechanic feel and fidelity the automated gate cannot judge), and where notes go; human playtest feedback is routed to `pr-feedback-ingest --playtest`, never absorbed into an ad-hoc review (ADR-0084).
- Output ends with a complete `### Handoff` block per the adaptive format in `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract`.
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
The verdict is only as good as the shown output. A real run with quoted errors and an honest FAIL is worth more than a confident PASS with nothing to read. Verify the runtime behavior the linter could never see, and route the fix rather than reaching for it.

<!-- cache-breakpoint -->
