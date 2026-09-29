---
name: godot-runtime-verify
description: Verify a built Godot 2D or 3D scene at runtime: run the scene (press-play or headless), read the captured debugger output, classify any runtime errors against a Godot-specific taxonomy, and decide a PASS/FAIL runtime gate for the slice's acceptance behavior. The run's real output IS the Layer-1 runtime evidence (ADR-0048); a claimed-but-not-shown run is unverified. MCP-agnostic about how the scene is run; it verifies and routes fixes, it does not apply them. Use after a Godot slice is implemented to gate runtime behavior the static checks (lint, typecheck) cannot catch. Do not use to plan a scene (use godot-scene-plan), to write or fix the code (use implement-approved-slice or implement-slice-complement), to triage a failure into a fix size (use incident-triage), or with no implemented scene to run.
metadata:
  category: game-and-engine
  primary-cursor-mode: Agent
  multi-repo-aware: false
  context-layers-consumed: [memory]
  context-layers-produced: [memory]
  tools: [Read, Write, Edit, Bash, Glob, Grep]
  x-wos-profiles: [full]
  provenance: first-party
  suggested-model: claude-sonnet-5-5
---
# godot-runtime-verify

Act as a senior Godot engineer running a built 2D or 3D scene and verifying its runtime behavior before the slice is closed.

Goal:
Run the implemented Godot scene (press-play in the editor or a headless run), capture and read the debugger output, classify any runtime errors against a Godot-specific taxonomy, and decide a PASS or FAIL runtime gate for the slice's acceptance behavior. This is the "feedback edge" that the static checks cannot cover: most Godot bugs are runtime bugs a linter never catches (EXTERNAL_RESEARCH.md A2). The command's verdict is a Layer-1 runtime gate per the three-layer model (`wos/gate-conditions.md`, ADR-0048): the run's actual output is the evidence, and it feeds Layer 2 (`review-hard`) and Layer 3 (human approval), never replacing them. The command verifies and routes; it does not write or fix code.

Mandatory context bootstrap (before any output):
<!-- shared:mandatory-context-bootstrap -->
- Read these sections in `WORKFLOW_OPERATING_SYSTEM.md` first:
  - `## LLM execution contract`
  - `## Editor mode policy` (mode definitions only; the tool mapping table is lazy-loaded in `wos/editor-mode-mappings.md` and needed only for non-Claude-Code tools)
  - `## Global output contract` (including **Adaptive handoff** and **Mode selection rule**)
  - `## Cross-cutting workflow guardrails`
- **Bootstrap tiers:** the light-weight commands (`branch-commit`, `what-next`, `where-we-at`, `slice-closure`, `compact-task-memory`) plus the high-frequency `implement-approved-slice` and `sync-task-state` (v3 wave1 item D) read the four sections above with two subsections of `## Cross-cutting workflow guardrails` skipped: `### External web access (centralized)` and `### Sequencing heuristics (by phase)`. Everything else is read at every tier, including `### Proposal vs approved persistence` and `### Substrate peer ownership (per ADR-0034)`, since all seven write substrate sections and reason about PROPOSED (`state-reconcile` stays on the full tier for cross-artifact judgment). The full tier is measured at 12109 tokens, the four always-read sections combined; the two skipped subsections are 1,034 of those (measured 2026-09-28), so the reduced tier is about 11,074. The leaf-reviewer tier (`verify-against-rubric`, ADR-0226) reads only `## Global output contract`, measured at 5215 tokens, plus its rubric.
- **Session bootstrap reuse (skip-if-unchanged; v3 wave1 item D):** WHEN this conversation already read the bootstrap sections in an earlier turn still VISIBLE in the context window AND `WORKFLOW_OPERATING_SYSTEM.md` has not changed since, the command MAY skip the re-read and cite the earlier one, emitting one Command transcript line: `Bootstrap: reusing turn <N> read, WOS unchanged`. Scoped exception to the context-budget re-fetch rule (`wos/context-budget.md`, "The re-fetch rule"), because these sections are one large, static, byte-identical read repeated every turn; every other tool result still re-fetches. VISIBLE means the section text itself is still present and quotable now, not merely that a record of the earlier read exists: a harness that clears a tool result while the record survives (ADR-0114) has not satisfied VISIBLE, and self-declared memory after a compaction never qualifies. A stateless-per-turn harness is excluded. The transcript line is mandatory; a silent skip is invalid output.
- **Resolving `WORKFLOW_OPERATING_SYSTEM.md` and a relative `wos/<topic>.md`.** Both resolve the same way: try the canonical workflow repository root FIRST, then the installed docs directory (`~/.claude/workflow-docs/` or `~/.cursor/workflow-docs/`, the spec at that root and topics under its `wos/`). Repository first, because the installed copy is a snapshot no sync prunes; preferring it would hide a `wos/` edit from every command until a reinstall. Name the resolved root in `### Command transcript`, and say so explicitly when NEITHER resolved rather than continuing silently, since several of these loads are MANDATORY.
- Read additional sections only when relevant to this command's role.
- Align all routing recommendations and next-command suggestions with the current command set.
- **Official next-command names only:** every recommended next command (including the handoff `Run now` line) MUST be the basename of an existing `commands/<name>.md` file in this workflow repository. Never invent names. One exception: `Run now: none` with `Mode: N/A` declares the chain ended with no honest next step, defined under `### Official command names (routing integrity)` (ADR-0126); use it only then, never to end a chain that has a real next step.

Required inputs:
- active task folder path
- the implemented slice or feature under verification, and its acceptance behavior (the observable outcome that means it works, ideally the slice's EARS exit criterion)
- how the scene was run and the real captured output: the run mechanism (an MCP server run tool, the Godot CLI headless run, or a human pressing play) plus the actual debugger or console output from that run. When the output is not yet captured, this command captures it itself per `wos/godot-runtime-battery.md` `## Evidence capture (the run directory)` rather than asserting a result or asking for a paste.
- the target Godot version, when relevant to interpreting an error

Operating rules:
- Do not write or fix code; this command runs and verifies, then routes a fix to the right command. Within-scope tidying of the report is allowed.
- **K.2 scope note (P2-8, dogfood-wave-2 2026-07-12):** this command's own artifact (`GODOT_RUNTIME_VERIFY.md`) is outside the K.2 11-file substrate scope (`commands/_shared/substrate-write-protocol.md`) and needs no transaction header. Update `TASK_STATE.md`'s `## Last completed step` afterward as ordinary operator hygiene.
- **Handoff:** end with the adaptive `### Handoff` block per `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full).
- MCP-agnostic (DECISIONS D-1): the command names no specific MCP server. Whatever ran the scene (an MCP run tool, the Godot CLI `--headless`, or a human) is the operator's choice; the command verifies the output, it does not prescribe the runner.
- No-op rule: if a current runtime verification already covers this slice with no material change (the scene and acceptance behavior are unchanged since the last PASS), return a short NO_OP note and route forward.
- **Adapter battery (lazy load, MANDATORY).** The binary preflight, the persistent `probes/` harness rules, the adversarial-probe requirement and the taxonomy for this command live in `wos/godot-runtime-battery.md` and are loaded when this command runs. A gate that ran only happy-path probes is incomplete evidence and MUST say so in its verdict. Resolve the path per the relative-`wos/` rule above and name the root you resolved against in `### Command transcript`. A battery that resolved nowhere makes the run BLOCKED, never a silent skip, and that BLOCKED verdict routes instead of halting: name the exact path that did not resolve (`wos/godot-runtime-battery.md`) and the roots you tried, then hand that path to `incident-triage` as a CONFIG failure so the battery is restored and this gate re-run. A missing in-repo file is none of the four stop reasons in `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` `### Adaptive handoff`, so do not end the chain waiting here.
- **Capture the probe output yourself.** This gate captures its own artifacts; it does not ask a human to transport a debugger log. Apply `wos/godot-runtime-battery.md` `## Evidence capture (the run directory)`: write every probe log under `<task-folder>/evidence/<slice-id>/`, record the resolved binary and the Godot version, and cite every written path in the slice notes. That capture is how this command satisfies the skeleton's step-1 requirement for real output. WHEN the preflight resolves no binary, the verdict is BLOCKED naming the missing capability and routing to `incident-triage` as a CONFIG failure; a BLOCKED that names its missing capability is the routed form of that stop, and it is never a silent PASS.
- **Frame capture on this surface is BLOCKED by default.** Apply `wos/godot-runtime-battery.md` `## Golden baseline (BLOCKED by default here)`. The headless run uses a dummy display server and renders no real frame, and no capture path has been measured against this workflow's own Godot surface yet, so a visual row reads `unverified: no measured Godot frame capture` and rides `PLAYTEST_RUNBOOK.md` to a human. Do not assert a capture capability nobody has named and nobody has run.
- **The mechanical and judgment split is static.** Read it from `wos/godot-runtime-battery.md` `## Mechanical and judgment criteria (static split)`; do not classify a criterion yourself at run time. A mechanical row is decided here from the captured probe output and gates. A judgment row rides the playtest runbook to a human and does not gate on its own.
- **Step 1: Confirm the run mechanism and the acceptance behavior.** Restate the slice under verification, its acceptance behavior (the EARS exit criterion when present), and how the scene was run. If the real run output is not yet captured, capture it per the rule above; do not proceed on an asserted result.
- **Step 2: Read the captured output.** Read the debugger or console log from the run. Quote the load-bearing lines (errors, warnings, the absence of expected output) verbatim in the report; do not paraphrase an error.
- **Step 3: Classify each runtime observation.** Tag every error or anomaly with exactly one taxonomy code from `wos/godot-runtime-battery.md` `## Taxonomy: Godot adapter`. One line per observation: the quoted symptom, the code, and the most likely cause.
- **Step 4: Verdict per acceptance criterion.** For each acceptance behavior, state `observed`, `not-observed`, or `unverified` (output not shown), grounded in the captured log.
- **Step 5: Gate decision.** PASS only when the scene ran, there is no unhandled runtime error, and every acceptance behavior is `observed`. Otherwise FAIL (one or more errors or a `not-observed` behavior) or BLOCKED (output `unverified`, or the bounded-retry cap was reached). State the decision in one line with its reason.
- **Step 6: Write the report.** Save as `GODOT_RUNTIME_VERIFY.md` (or `GODOT_RUNTIME_VERIFY_<slice>.md` when several slices are verified) in the active task folder: the run mechanism, the resolved binary and Godot version, the run directory path with every artifact it holds, the quoted output, the classification table, the per-criterion verdict, and the gate decision.
- **Step 7: Emit or update the playtest runbook (ADR-0084).** Write or update `PLAYTEST_RUNBOOK.md` per `wos/godot-runtime-battery.md` `## Playtest runbook (ADR-0084)`. An improvised one-off run instruction is not a runbook; the artifact is the point.
- **Route human playtest notes to `pr-feedback-ingest --playtest` (ADR-0084).** When the operator returns playtest feedback (the game runs but plays wrong, a mechanic is off, a screen flow is missing), the handoff routes it to `pr-feedback-ingest --playtest`, a first-class corrective ingestion path, not to a general review command. Do not absorb playtest feedback into an ad-hoc review.
- **Per-slice adoption (ADR-0084).** A Godot slice with runtime-observable behavior runs this gate, or records an explicit skip reason in the slice notes (for example a pure-data or config slice with nothing to run). A silently skipped runtime gate is the observed decay mode (the dogfood ran the gate once and dropped it for the two larger builds); the explicit skip line keeps the decision visible.

Required output:
1. Slice under verification and its acceptance behavior
2. Run mechanism + the quoted real output, plus the run directory path with every captured artifact listed (or BLOCKED naming the missing capture capability)
3. Classification table (symptom, taxonomy code, likely cause)
4. Verdict per acceptance criterion (observed | not-observed | unverified)
5. Gate decision (PASS | FAIL | BLOCKED) with reason
6. `PLAYTEST_RUNBOOK.md` written or updated (how to run, what to exercise including mechanic feel, where notes go)
7. Recommended next command (the fix route on FAIL, closure on PASS, or `pr-feedback-ingest --playtest` when the operator returns human playtest notes)
<!-- shared:runtime-verify-skeleton -->
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
Follow `## Global output contract` in `WORKFLOW_OPERATING_SYSTEM.md` for `APPLIED` / `PROPOSED` / `SKIP` rules. Every listed file carries one of those three tokens, in Lean output too; a prose verb like "written" is not a label.

### Command transcript
<!-- shared:command-transcript-standard -->
Brief audit trail (max 4 lines; max 3 in no-op runs with `NO_OP_TRACE`).

### Handoff
<!-- shared:handoff-body -->
Use the adaptive ending format of `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract`. Every Handoff is one fenced `text` block with all four lines, `Run now:`, `Mode:`, `Work complexity:` and `Reason:`, on a stop and on a refusal too; the terminal form is `Run now: none` with `Mode: N/A`. A new `Mode:`, a model or a fresh session is never a stop, an offered choice is one, and `Reason:` names a role, never a model.
### Definition of done (command output)
- The real run output is quoted, not asserted; a run with no shown output is reported as `unverified` or BLOCKED, never PASS (ADR-0048).
- The evidence this run captured is written under `<task-folder>/evidence/<slice-id>/` and every path is cited; no human was asked to paste a debugger log. WHERE the preflight resolved no binary, the verdict is BLOCKED naming that capability and routing, never PASS.
- Every visual row reads `unverified: no measured Godot frame capture` unless a capture attempt has been run and recorded; the mechanical and judgment split was read from the battery topic and not decided in this run.
- Every runtime observation carries a taxonomy code and a per-criterion verdict; the gate decision (PASS | FAIL | BLOCKED) is explicit with its reason.
- The command names no specific MCP server (MCP-agnostic, DECISIONS D-1) and writes no code (a FAIL routes the fix to `incident-triage` or `implement-slice-complement`).
- A hold-until-pass loop carries the bounded-retry cap; a PASS is Layer-1 runtime evidence that does not skip Layer 2 or Layer 3.
- `GODOT_RUNTIME_VERIFY.md` is written in Agent mode.
- `PLAYTEST_RUNBOOK.md` is written or updated with the run steps, the behaviors to exercise (including mechanic feel and fidelity the automated gate cannot judge), and where notes go; human playtest feedback is routed to `pr-feedback-ingest --playtest`, never absorbed into an ad-hoc review (ADR-0084).
- Output ends with a complete `### Handoff` block per the adaptive format in `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract`.
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
The verdict is only as good as the shown output. A real run with quoted errors and an honest FAIL is worth more than a confident PASS with nothing to read. Verify the runtime behavior the linter could never see, and route the fix rather than reaching for it.
