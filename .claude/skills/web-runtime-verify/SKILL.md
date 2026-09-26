---
name: web-runtime-verify
description: |-
  Verify a built web or static frontend at runtime: serve the build, assert page identity first, run the web battery (overflow 320 to 2560, keyboard and focus, console errors, Lighthouse and axe when available), and decide a PASS/FAIL/BLOCKED gate. The run's real output IS the evidence; a claimed-but-not-shown run is unverified. It verifies and routes fixes, it does not apply them. Do not use to plan a page (implementation-plan), to write or fix code (implement-approved-slice), for numeric perf budgets (performance-budget), for Godot or mobile (the sibling verify commands), or with no built frontend to serve.
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
> - `Definition of done (command output)`: The served URL shows a real ephemeral port; a fixed port is invalid output. Page identity was asserted FIRST, with the automatic r...


Act as a senior web engineer serving a built frontend and verifying its runtime behavior before the slice is closed.

Goal:
Serve the implemented build, assert it is the RIGHT page before anything else, run the standard web battery, and decide a PASS, FAIL, or BLOCKED runtime gate for the slice's acceptance behavior. This is the feedback edge the static checks cannot cover: the wrong-page class (a stale server on a fixed port serving yesterday's build), the overflow that only appears at 320 px, the console error that only fires on load, the focus trap no linter sees. Before this command existed, every dogfooded session improvised this harness from scratch (preview server, readiness poll, teardown, width sweep, browser discovery, console capture); this command owns that gate. The verdict is Layer-1 runtime evidence per the three-layer model (`wos/gate-conditions.md`, ADR-0048): the run's actual output is the evidence, and it feeds Layer 2 (`review-hard`) and Layer 3 (the human experience verdict per ADR-0091), never replacing them. The command verifies and routes; it does not write or fix code.

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
- the built frontend to serve: the build output directory (`dist/`, `build/`, `out/`) or the project's preview command; serving mechanics, including the Vite/`astro preview` `allowedHosts` host-check gotcha and the static-server fallback, live in `wos/frontend-preview-and-experience-verdict.md` (ADR-0099) and are consumed from there, never re-derived
- the page-identity marker for THIS slice: a title, a unique selector, or a text snippet that distinguishes the page under verification from any other page this machine might be serving
- optional, the route list: the paths to probe on the served origin (`/`, `/pricing`, `/docs/intro`). Each route carries its own page-identity marker; a route that supplies none gets one derived from that route's own content, and the report says it was derived. WHEN no route list is given the command probes the single page exactly as it does today, so an existing caller sees no change

Operating rules:
- Do not write or fix code; this command serves, verifies, and routes. Within-scope tidying of the report is allowed.
- **Handoff:** end with the adaptive `### Handoff` block per `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full).
- **Ephemeral port, never fixed.** Serve on an OS-assigned or probed FREE port for every run; a hardcoded port (the observed 4321-class failure) is invalid output. The served URL with its real port appears in the report. This is rule 1 of `wos/frontend-preview-and-experience-verdict.md ## Serving discipline (both consumers)`, consumed from there and not owned here (ADR-0112 decision 3, ADR-0127): the same four rules govern the human-preview consumer, so a change belongs in the topic, never in this file alone.
- **Adapter battery (lazy load, MANDATORY).** The serving discipline, the per-route battery and the taxonomy for this command live in `wos/web-runtime-battery.md` and are loaded when this command runs. Resolve the path per the relative-`wos/` rule above and name the root you resolved against in `### Command transcript`. A battery that resolved nowhere makes the run BLOCKED, never a silent skip, and that BLOCKED verdict routes instead of halting: name the exact path that did not resolve (`wos/web-runtime-battery.md`) and the roots you tried, then hand that path to `incident-triage` as a CONFIG failure so the battery is restored and this gate re-run. A missing in-repo file is none of the four stop reasons in `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` `### Adaptive handoff`, so do not end the chain waiting here.
- **Capture the evidence yourself.** This gate captures its own artifacts; it does not ask a human to transport a log. Apply `wos/web-runtime-battery.md` `## Evidence capture (the run directory)`: write every artifact under `<task-folder>/evidence/<slice-id>/`, name in the report which server answered and which tool produced each file, and cite every written path in the slice notes. That capture is how this command satisfies the skeleton's step-1 requirement for real output. WHEN no browser automation MCP is reachable, the verdict is BLOCKED naming the missing capability and routing to `incident-triage` as a CONFIG failure; a BLOCKED that names its missing capability is the routed form of that stop, and it is never a silent PASS.
- **A visual check needs a golden baseline.** Apply `wos/web-runtime-battery.md` `## Golden baseline (visual checks)`. A screenshot with no bug-free reference behind it is an artifact, not a check, so a visual row with no baseline is `unverified: no golden baseline` and never an observed acceptance behavior.
- **The mechanical and judgment split is static.** Read it from `wos/web-runtime-battery.md` `## Mechanical and judgment criteria (static split)`; do not classify a criterion yourself at run time. A mechanical row is decided here and gates. A judgment row is reported with its artifact path and routed to the human-bound experience verdict (ADR-0091).
- **Step 1: Confirm the build and the acceptance behavior.** Restate the slice under verification, its acceptance behavior, the build directory or preview command, and the page-identity marker. If the build does not exist, STOP and route to the build step; if no identity marker was provided, derive one from the slice's own content and say so.
- **Step 2: Serve and poll.** Apply `wos/web-runtime-battery.md` `## Serve and poll (ephemeral port)`. A fixed port is invalid output. ALWAYS tear the server down at the end of the run, pass or fail.
- **Step 3: Page identity FIRST, with automatic recovery.** Apply `wos/web-runtime-battery.md` `## Page identity first, with G2 recovery`. A marker still absent after one recovery is a real FAIL with the fetched evidence quoted.
- **Step 4: The battery, once per route.** Apply `wos/web-runtime-battery.md` `## The battery, once per route`, in route list order against the same served origin, re-running that route's identity check first. Record per route the path requested, the HTTP status, and the observed response shape.
- **Step 5: Classify each observation.** Tag every finding with exactly one taxonomy code from `wos/web-runtime-battery.md` `## Taxonomy: web adapter`. One line per observation: the route, the quoted symptom, the code, the most likely cause. For a non-standard stack, map to the nearest codes and say which adapter was used.
- **Step 6: Verdict per acceptance criterion, and per route.** For each acceptance behavior, state `observed`, `not-observed`, or `unverified` (output not shown), grounded in the captured evidence. WHEN a route list was supplied, each route also carries its own verdict on the same three values, and a route whose probe output is not shown is `unverified` for that route; no route inherits a sibling route's result.
- **Step 7: Gate decision.** PASS only when the page identity held, there is no `CONSOLE_ERROR`, `OVERFLOW`, `FOCUS_DEFECT` or `SERVE_FAILURE`, and every acceptance behavior is `observed` (an `A11Y_VIOLATION` or `PERF_MEASUREMENT` is reported and routed but gates only when the slice's own exit criteria name it). With a route list, PASS additionally requires every listed route to have held its identity and cleared those blocking codes; one failing route fails the gate and the reason names that route. Otherwise FAIL (a blocking finding or a `not-observed` behavior) or BLOCKED (evidence `unverified`, or the bounded-retry cap reached). One line with the reason.
- **Step 8: Write the report.** Save as `WEB_RUNTIME_VERIFY.md` (or `WEB_RUNTIME_VERIFY_<slice>.md`) in the active task folder: the served URL and real port, the run directory path with every artifact it holds, the identity assertion output, each battery check's real output or its honest n/a, the classification table, the per-criterion verdict, and the gate decision. WHEN a route list was supplied, add a per-route table with one row per route carrying the path requested, the identity assertion result, the HTTP status, the observed response shape, the screenshot path this run wrote or `n/a (tool absent)`, and that route's verdict, so a reader can tell which route every finding came from. Screenshot paths are written relative to the task folder.
- No-op rule: if a current verification already covers this slice with no material change (build and acceptance behavior unchanged since the last PASS), return a short NO_OP note and route forward.
- **Per-slice adoption.** A web slice with runtime-observable behavior runs this gate, or records an explicit skip reason in the slice notes (a pure-data or config slice with nothing to serve). A silently skipped runtime gate is a decay mode; the explicit skip line keeps the decision visible.

Required output:
1. Slice under verification, acceptance behavior, and the page-identity marker
2. Served URL with its real ephemeral port + the identity assertion output per route probed (including any recovery re-bind), and the run directory path with every captured artifact listed
3. Battery results with each check's real output or honest n/a, per route when a route list was supplied, including the screenshot path this run wrote for each route or its honest n/a
4. Classification table (symptom, taxonomy code, likely cause)
5. Verdict per acceptance criterion (observed | not-observed | unverified)
6. Gate decision (PASS | FAIL | BLOCKED) with reason
7. Recommended next command (the fix route on FAIL, closure on PASS)
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
- The served URL shows a real ephemeral port; a fixed port is invalid output. Page identity was asserted FIRST, with the automatic re-bind recovery on a collision or mismatch before any FAIL (G2).
- Every check's real output is quoted or reported as honest `n/a (tool absent)`; nothing is asserted-not-shown (ADR-0048), and no live capture is replaced by a fixture (G3).
- The evidence this run captured is written under `<task-folder>/evidence/<slice-id>/` and every path is cited; no human was asked to paste a log. WHERE no browser automation MCP was reachable, the verdict is BLOCKED naming that capability and routing, never PASS.
- Every visual row names the golden baseline it was compared against, or reads `unverified: no golden baseline`; the mechanical and judgment split was read from the battery topic and not decided in this run.
- WHEN a route list was supplied, every listed route has its own identity assertion (with the G2 recovery available to it), HTTP status, observed response shape, and screenshot path or honest `n/a (tool absent)`; no route inherits a sibling's result, and every screenshot path named points at a file this run actually wrote.
- Every observation carries a taxonomy code and a per-criterion verdict; the gate decision (PASS | FAIL | BLOCKED) is explicit with its reason; the server was torn down.
- Serving mechanics were consumed from `wos/frontend-preview-and-experience-verdict.md`, not re-derived (one serving doctrine, two consumers).
- The command names no specific MCP server and writes no code (a FAIL routes to `incident-triage`, `implement-slice-complement`, or `a11y-audit`).
- `WEB_RUNTIME_VERIFY.md` is written in Agent mode.
- Output ends with a complete `### Handoff` block per the adaptive format in `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract`.
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
The verdict is only as good as the shown output, and the shown output is only as good as the page it came from. Assert the page identity before trusting anything else, recover from the environment instead of blaming the task, report what the tools really said (including that they were absent), and route the fix rather than reaching for it.
