---
name: web-runtime-verify
description: |-
  Verify a built web or static frontend at runtime: serve the build on an ephemeral free port, assert page identity FIRST (automatic recovery on a collision or stale server), run the web battery (overflow 320 to 2560, keyboard and focus, console errors, Lighthouse and axe when available), and decide a PASS/FAIL/BLOCKED runtime gate. The run's real output IS the Layer-1 evidence (ADR-0048); a claimed-but-not-shown run is unverified. Capability-routed and MCP-agnostic; serving mechanics live in wos/frontend-preview-and-experience-verdict.md (ADR-0099), referenced never duplicated. It verifies and routes fixes, it does not apply them. Use after a web slice is implemented to gate runtime behavior the static checks cannot catch. Do not use to plan a page (implementation-plan), to write or fix code (implement-approved-slice), to record the HUMAN experience verdict (the ADR-0091 floor), for numeric perf budgets (performance-budget), for Godot or mobile (the sibling verify commands), or with no built frontend to serve.
metadata:
  category: execution-and-closure
  primary-cursor-mode: Agent
  multi-repo-aware: false
  context-layers-consumed:
    - memory
  context-layers-produced:
    - memory
  tools:
    - Read
    - Write
    - Edit
    - Bash
    - Glob
    - Grep
  x-wos-profiles:
    - full
  provenance: first-party
  token-budget: 2600
  suggested-model: claude-sonnet-4-6
---

Act as a senior web engineer serving a built frontend and verifying its runtime behavior before the slice is closed.

Goal:
Serve the implemented build, assert it is the RIGHT page before anything else, run the standard web battery, and decide a PASS, FAIL, or BLOCKED runtime gate for the slice's acceptance behavior. This is the feedback edge the static checks cannot cover: the wrong-page class (a stale server on a fixed port serving yesterday's build), the overflow that only appears at 320 px, the console error that only fires on load, the focus trap no linter sees. Before this command existed, every dogfooded session improvised this harness from scratch (preview server, readiness poll, teardown, width sweep, browser discovery, console capture); this command owns that gate. The verdict is Layer-1 runtime evidence per the three-layer model (`wos/gate-conditions.md`, ADR-0048): the run's actual output is the evidence, and it feeds Layer 2 (`review-hard`) and Layer 3 (the human experience verdict per ADR-0091), never replacing them. The command verifies and routes; it does not write or fix code.

Mandatory context bootstrap (before any output):
<!-- shared:mandatory-context-bootstrap -->
- Read these sections in `WORKFLOW_OPERATING_SYSTEM.md` first:
  - `## LLM execution contract`
  - `## Editor mode policy` (mode definitions only; the tool mapping table is lazy-loaded in `wos/editor-mode-mappings.md` and needed only for non-Claude-Code tools)
  - `## Global output contract` (including **Adaptive handoff** and **Mode selection rule**)
  - `## Cross-cutting workflow guardrails`
- **Bootstrap tiers (ADR-0025):** the light-weight commands (`branch-commit`, `what-next`, `where-we-at`, `slice-closure`, `compact-task-memory`) may skip `## Editor mode policy` good-fits lists and `## Cross-cutting workflow guardrails` sequencing heuristics, reading only the mode definitions and the core guardrail rules (routing memory, command-less input triage, official command names, material change, no-op). This reduces bootstrap from ~6,750 to ~3,500 tokens for these commands. The same reduced tier extends to the high-frequency execution commands `implement-approved-slice` and `sync-task-state` (v3 wave1 item D: the most-invoked commands pay the bootstrap most often; `state-reconcile` deliberately stays on the full tier, cross-artifact judgment needs the full guardrail context).
- **Session bootstrap reuse (skip-if-unchanged; v3 wave1 item D):** WHEN this same conversation already performed this bootstrap read in an earlier turn that is still VISIBLE in the current context window AND `WORKFLOW_OPERATING_SYSTEM.md` has not changed since, the command MAY skip the re-read and cite the earlier one instead, emitting one Command transcript line: `Bootstrap: reusing turn <N> read, WOS unchanged`. Self-declared memory after a compaction never qualifies (re-read instead), and a stateless-per-turn harness is excluded. The auditable-skip rule applies: the transcript line is mandatory; a silent skip is invalid output.
- Read additional sections only when relevant to this command's role.
- Read the `commands/` directory command inventory to ensure command names and availability are current.
- Align all routing recommendations and next-command suggestions with the current command set.
- **Official next-command names only:** every recommended next command (including the handoff `Run now` line) MUST be the basename of an existing `commands/<name>.md` file in this workflow repository. Never invent names.

Required inputs:
- active task folder path
- the implemented slice or feature under verification, and its acceptance behavior (the observable outcome that means it works, ideally the slice's EARS exit criterion)
- the built frontend to serve: the build output directory (`dist/`, `build/`, `out/`) or the project's preview command; serving mechanics, including the Vite/`astro preview` `allowedHosts` host-check gotcha and the static-server fallback, live in `wos/frontend-preview-and-experience-verdict.md` (ADR-0099) and are consumed from there, never re-derived
- the page-identity marker for THIS slice: a title, a unique selector, or a text snippet that distinguishes the page under verification from any other page this machine might be serving

Operating rules:
- Do not write or fix code; this command serves, verifies, and routes. Within-scope tidying of the report is allowed.
- **Handoff:** end with the adaptive `### Handoff` block per `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full).
- Evidence, not trust (ADR-0048): the run's actual output (the HTTP response, the probe results, the console capture, the tool reports) MUST be shown. A check whose result is claimed but whose output is not shown is `unverified`, exactly like an asserted "tests pass". Never substitute a stored screenshot or fixture for a live capture (G3); when a capture cannot run, the check reports honestly and the verdict reflects it.
- **Ephemeral port, never fixed.** Serve on an OS-assigned or probed FREE port for every run; a hardcoded port (the observed 4321-class failure) is invalid output. The served URL with its real port appears in the report.
- **Step 1: Confirm the build and the acceptance behavior.** Restate the slice under verification, its acceptance behavior, the build directory or preview command, and the page-identity marker. If the build does not exist, STOP and route to the build step; if no identity marker was provided, derive one from the slice's own content and say so.
- **Step 2: Serve and poll.** Start the server per the ADR-0099 topic mechanics on an ephemeral free port; poll readiness (bounded, a few seconds); ALWAYS tear the server down at the end of the run, pass or fail. Under Codex CLI, fire this step as one of the FIRST actions of the turn while a human is present to approve escalations (`wos/editor-mode-mappings.md ## Harness operational quirks`; the 2h39 stall class).
- **Step 3: Page identity FIRST, with automatic recovery.** Before any other check, fetch the served page and assert the identity marker. WHEN the marker is absent or the port was already occupied (a stale server, another project), do NOT dry-fail: re-bind to a fresh free port, restart the serve, and re-run the identity check ONCE (the G2 recovery rule; a collision is an environment hazard, not a task blocker). A marker still absent after recovery is a real FAIL with the fetched evidence quoted: every later check would otherwise be verifying the wrong page, which is worse than no verification.
- **Step 4: The battery.** Run each check and capture its real output; a tool that is not installed reports `n/a (tool absent)` honestly, never a fabricated score:
  - overflow sweep: probe horizontal overflow at 320, 768, 1280 and 2560 px (a headless viewport probe or a scrollWidth-vs-clientWidth check); quote the failing width and element when found;
  - keyboard and focus walk: tab through the interactive elements; a focus trap, an unreachable control, or an invisible focus indicator is a finding;
  - console capture: collect errors and warnings emitted on load and during the walk; zero errors is the bar, warnings are reported;
  - Lighthouse and axe: run when available; report the scores and violations, or `n/a (tool absent)`; numeric thresholds belong to `performance-budget`, this gate reports the measurement.
- **Step 5: Classify each observation (web adapter).** Tag every finding with one taxonomy code: `PAGE_IDENTITY_MISMATCH` (wrong page after recovery), `SERVE_FAILURE` (build will not serve or never becomes ready), `CONSOLE_ERROR`, `OVERFLOW` (horizontal overflow at a probed width), `FOCUS_DEFECT` (trap, unreachable control, missing indicator), `A11Y_VIOLATION` (axe finding), `PERF_MEASUREMENT` (a Lighthouse metric worth surfacing; budget judgment stays with `performance-budget`), or `CLEAN`. One line per observation: the quoted symptom, the code, the most likely cause. For a non-standard stack, map to the nearest codes and say which adapter was used.
- **Step 6: Verdict per acceptance criterion.** For each acceptance behavior, state `observed`, `not-observed`, or `unverified` (output not shown), grounded in the captured evidence.
- **Step 7: Gate decision.** PASS only when the page identity held, there is no `CONSOLE_ERROR`, `OVERFLOW`, `FOCUS_DEFECT` or `SERVE_FAILURE`, and every acceptance behavior is `observed` (an `A11Y_VIOLATION` or `PERF_MEASUREMENT` is reported and routed but gates only when the slice's own exit criteria name it). Otherwise FAIL (a blocking finding or a `not-observed` behavior) or BLOCKED (evidence `unverified`, or the bounded-retry cap reached). One line with the reason.
- **Step 8: Write the report.** Save as `WEB_RUNTIME_VERIFY.md` (or `WEB_RUNTIME_VERIFY_<slice>.md`) in the active task folder: the served URL and real port, the identity assertion output, each battery check's real output or its honest n/a, the classification table, the per-criterion verdict, and the gate decision.
- **Bounded retry (`wos/gate-conditions.md` interactive bounded retry).** In a hold-until-pass loop, cap consecutive failed runs at a small N (default 3 to 8); on the cap, STOP and escalate rather than looping.
- Verify, then route the fix; do not fix here. A FAIL routes to `incident-triage` (unclear cause) or `implement-slice-complement` (bounded known fix inside the slice intent); an a11y cluster routes to `a11y-audit`; reopening a signed-off decision routes to `post-review-pivot`.
- Layer placement: a PASS here is Layer-1 machine evidence over the served build; the HUMAN experience verdict (ADR-0091) runs over the SAME served build per the ADR-0099 topic and is never replaced by this gate.
- No-op rule: if a current verification already covers this slice with no material change (build and acceptance behavior unchanged since the last PASS), return a short NO_OP note and route forward.
- **Per-slice adoption.** A web slice with runtime-observable behavior runs this gate, or records an explicit skip reason in the slice notes (a pure-data or config slice with nothing to serve). A silently skipped runtime gate is a decay mode; the explicit skip line keeps the decision visible.

Required output:
1. Slice under verification, acceptance behavior, and the page-identity marker
2. Served URL with its real ephemeral port + the identity assertion output (including any recovery re-bind)
3. Battery results with each check's real output or honest n/a
4. Classification table (symptom, taxonomy code, likely cause)
5. Verdict per acceptance criterion (observed | not-observed | unverified)
6. Gate decision (PASS | FAIL | BLOCKED) with reason
7. Recommended next command (the fix route on FAIL, closure on PASS)

### Claim grounding (active epistemic humility)
<!-- shared:claim-grounding -->
**Claim grounding (active epistemic humility).** This block governs what you may assert and how you record it. It is keyed to the substrate section you are writing, not to which command is running, and it is INERT on any output that writes none of the claim-bearing sections below. Full contract and rationale: `wos/active-epistemic-humility.md`.

1. When this applies. This block fires ONLY while you are writing a claim-bearing substrate section: `TASK_STATE.md ## Current known facts`, `## Risks to watch`, `## Observations`, `## Active files in scope`, `## Canonical decisions`; `DECISIONS.md ## Locked decisions`; `IMPLEMENTATION_PLAN.md ## Current gaps`, `## Risks and mitigations`; `IMPACT_ANALYSIS.md`; `EXTERNAL_RESEARCH.md`; `REFERENCES.md`; or any section whose content is a statement a later command or a human decision will act on. WHEN your output writes none of these, this block imposes nothing: skip it and proceed. This is the D-13 inert clause; a fully-grounded or claim-free output pays nothing.

2. The unit is the load-bearing claim. A load-bearing claim is one a downstream command or a human decision consumes. A passing aside is not load-bearing; a statement someone will act on is. Apply the rest of this block per load-bearing claim, not per sentence.

3. Ground it or abstain. Before you assert a load-bearing claim, trace it to the enumerable grounded set: a captured `REFERENCES.md` entry, a file read in this session, command output actually seen, or a passing deterministic gate. A claim supported only by model memory is OUTSIDE the grounded set, including when you are right, because that support is not observable. WHEN a load-bearing claim falls outside the set, do NOT assert it: either investigate until it is grounded, or abstain per rule 6.

4. Status records provenance, never confidence. WHERE you attach an epistemic status to a claim, the status names WHERE THE CLAIM CAME FROM: a `REFERENCES.md` entry title, a file path plus line, or the gate output it came from. It SHALL NOT express a degree of certainty. Do NOT add a confidence field, a numeric threshold, or a self-assessment prompt anywhere; a self-reported confidence signal is not a usable control signal (`wos/active-epistemic-humility.md` Part 1.3). A status whose referent slot is empty is read as UNKNOWN, not as a weak yes.

5. Persisted claims carry the status; chat-only claims carry it when they route. Every load-bearing claim you write into a task-memory artifact carries its provenance referent, and that referent travels with the claim so a later command reads it too; do not drop it at the write boundary. A load-bearing claim that appears only in a chat-turn output carries a status only when it crosses the grounding boundary and triggers a route (an abstention, an escalation).

6. Abstain as a routed continuation, never a bare refusal. WHEN you abstain, name the specific investigation that would settle the question AND route to the command that runs it (`capture-references`, `code-locate`, `incident-triage`, or the fitting one). A withholding that stalls the work is invalid output. Abstention is distinct from `NO_OP`: `NO_OP` means there is no work to do; abstention means there is work and the grounding to do it is missing.

7. An unfired gate is not evidence. The absence of a fired check does not mean grounding existed. Do not read silence here as a pass.
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
- The served URL shows a real ephemeral port; a fixed port is invalid output. Page identity was asserted FIRST, with the automatic re-bind recovery on a collision or mismatch before any FAIL (G2).
- Every check's real output is quoted or reported as honest `n/a (tool absent)`; nothing is asserted-not-shown (ADR-0048), and no live capture is replaced by a fixture (G3).
- Every observation carries a taxonomy code and a per-criterion verdict; the gate decision (PASS | FAIL | BLOCKED) is explicit with its reason; the server was torn down.
- Serving mechanics were consumed from `wos/frontend-preview-and-experience-verdict.md`, not re-derived (one serving doctrine, two consumers).
- The command names no specific MCP server and writes no code (a FAIL routes to `incident-triage`, `implement-slice-complement`, or `a11y-audit`).
- `WEB_RUNTIME_VERIFY.md` is written in Agent mode (or PROPOSED in Ask/Plan mode per ADR-0001).
- Output ends with a complete `### Handoff` block per the adaptive format in `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract`.
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
The verdict is only as good as the shown output, and the shown output is only as good as the page it came from. Assert the page identity before trusting anything else, recover from the environment instead of blaming the task, report what the tools really said (including that they were absent), and route the fix rather than reaching for it.

<!-- cache-breakpoint -->
