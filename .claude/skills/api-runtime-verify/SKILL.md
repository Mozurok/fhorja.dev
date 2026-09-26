---
name: api-runtime-verify
description: |-
  Verify an implemented backend HTTP surface at runtime: per route, record the request actually made, the status, the content-type, and the observed body shape, assert each response against the slice's acceptance behavior, and decide a PASS/FAIL/BLOCKED gate. The probe's real output IS the evidence: a route whose output is not shown is unverified, never PASS. Capability-routed, and it routes fixes rather than applying them. Do not use to review a contract before implementation (use api-contract-review or graphql-contract-review), to write or fix code (use implement-approved-slice), to triage a failure into a fix size (use incident-triage), for a browser, app, or Godot surface, or with no running backend to probe.
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
> - `Definition of done (command output)`: Every probed route shows the request that was made, the HTTP status, the response content-type, and the observed body shape; a rou...


Act as a senior backend engineer probing an implemented HTTP surface and verifying its runtime behavior before the slice is closed.

Goal:
Probe the implemented routes, record what each request actually sent and what the service actually answered, and decide a PASS, FAIL, or BLOCKED runtime gate for the slice's acceptance behavior. This is the feedback edge the static checks cannot cover: the route that typechecks and returns 500 on the first real request, the handler that answers 200 with an HTML error page where the contract promised JSON, the write that reports success and persists nothing, the auth check that never runs on an anonymous request. It exists because no command in this workflow owned runtime HTTP behavior, so the backend half of a full-stack slice closed on static evidence alone while the frontend half had a runtime gate (DECISIONS D-6, 2026-07-27). The verdict is Layer-1 runtime evidence per the three-layer model (`wos/gate-conditions.md`, ADR-0048): the probe's actual output is the evidence, and it feeds Layer 2 (`review-hard`, `security-review`) and Layer 3 (human approval), never replacing them. The command verifies and routes; it does not write or fix code.

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
- the running backend under verification: its base URL, how it was started (a local dev server, a container, a preview deployment), and which build or revision is answering there, so the probe is known to reach the code under verification rather than a stale or shared instance
- the route set to probe: per route its method, its path, its auth posture (anonymous, authenticated, or a deliberately wrong tenant), and the request body shape when one is sent
- the declared contract for those routes when one exists (an OpenAPI or schema document, a captured `REFERENCES.md` entry for a third-party API, or the task's own `API_CONTRACT_REVIEW.md`), so an observed shape is compared against a declared one rather than against an assumption

Operating rules:
- Do not write or fix code; this command probes, verifies, and routes. Within-scope tidying of the report is allowed.
- **Handoff:** end with the adaptive `### Handoff` block per `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full).
- **An absent tool degrades honestly.** WHEN the mechanism that would issue a request is unavailable (no HTTP client on the machine, no test runner, no network path to the target), that route reports `n/a (tool absent)` with the reason and counts as `unverified`. A guessed status is invalid output.
- **Capability-routed and client-agnostic.** The command names no specific HTTP client, test runner, or MCP server. Whatever issued the request (a shell client, the project's own integration-test suite, a language HTTP library, or an MCP tool) is the operator's choice; the command verifies the recorded exchange, it does not prescribe the runner. Record which mechanism was used so a reader can repeat the probe.
- **Local or development targets only.** Apply `wos/api-runtime-battery.md` `## Target confirmation and blast radius` before any probe. A probe is a real request with real effects, so the blast radius is bounded by the target rather than by a confirmation question: probe a local or development instance, and WHEN the target is neither, do not probe it and do not stop to ask. Record every route on that target as `unverified: non-local target`, name the base URL that was rejected, and continue to the report.
- **Adapter battery (lazy load, MANDATORY).** The per-route battery and taxonomy for this command live in `wos/api-runtime-battery.md` and are loaded when this command runs. Resolve the path per the relative-`wos/` rule above and name the root you resolved against in `### Command transcript`. A battery that resolved nowhere makes the run BLOCKED, never a silent skip, and that BLOCKED verdict routes instead of halting: name the exact path that did not resolve (`wos/api-runtime-battery.md`) and the roots you tried, then hand that path to `incident-triage` as a CONFIG failure so the battery is restored and this gate re-run. A missing in-repo file is none of the four stop reasons in `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` `### Adaptive handoff`, so do not end the chain waiting here.
- **Capture the exchange yourself.** This gate records its own artifacts; it does not ask a human to paste a response body. Apply `wos/api-runtime-battery.md` `## Evidence capture (the run directory)`: write the recorded exchange and the conformance output under `<task-folder>/evidence/<slice-id>/`, redact secrets and personal data before writing, and cite every written path in the slice notes. That capture is how this command satisfies the skeleton's step-1 requirement for real output. WHEN no request recorder and no OpenAPI conformance checker are reachable, the verdict is BLOCKED naming the missing capability and routing to `incident-triage` as a CONFIG failure; a BLOCKED that names its missing capability is the routed form of that stop, and it is never a silent PASS.
- **The mechanical and judgment split is static.** Read it from `wos/api-runtime-battery.md` `## Mechanical and judgment criteria (static split)`; do not classify a criterion yourself at run time. Shape conformance against a declared OpenAPI document is mechanical because a tool that is not this agent decides it; shape with no declared document is the one judgment row, and it is reported with the recorded exchange cited rather than gating on its own.
- **Step 1: Confirm the target and the acceptance behavior.** Restate the slice under verification, its acceptance behavior (the EARS exit criterion when present), the base URL with how the target was started, and the route set with each route's auth posture. If the backend is not running, STOP and route to the step that starts it; if no route set was supplied, derive one from the slice's own scope and say so.
- **Step 2: Record the request actually made.** Record per route what `wos/api-runtime-battery.md` `## Recording the request and the response` requires. A result with no recorded request behind it is `unverified`.
- **Step 3: Record the response.** Record per route what the same section requires, quoting the load-bearing lines verbatim. Redact secrets and personal data; the shape is what this gate keeps.
- **Step 4: Assert each response against the acceptance behavior.** Compare the recorded status, content-type, and shape against what the slice says the route must do, and against the declared contract when one was supplied. State the comparison itself, not a summary of it. Run the probes in `wos/api-runtime-battery.md` `## Failure-path and write-confirmation probes`; a gate that exercised only the happy path is incomplete evidence and MUST say so in its verdict.
- **Step 5: Classify each observation.** Tag every finding with exactly one taxonomy code from `wos/api-runtime-battery.md` `## Taxonomy: API adapter`. One line per observation: the quoted symptom, the code, the most likely cause. For a non-HTTP backend surface, map to the nearest codes and say which adapter was used.
- **Step 6: Verdict per acceptance criterion.** For each acceptance behavior, state `observed`, `not-observed`, or `unverified` (output not shown), grounded in the recorded exchanges.
- **Step 7: Gate decision.** PASS only when every route in the set was actually reached, there is no `UNREACHABLE`, `STATUS_MISMATCH`, `CONTENT_TYPE_MISMATCH`, `SHAPE_MISMATCH`, `AUTH_BOUNDARY`, `ERROR_LEAK` or `EFFECT_NOT_OBSERVED`, and every acceptance behavior is `observed` (a `LATENCY_MEASUREMENT` is reported and routed but gates only when the slice's own exit criteria name it). Otherwise FAIL (a blocking finding or a `not-observed` behavior) or BLOCKED (any route `unverified`, or the bounded-retry cap reached). One line with the reason.
- **Step 8: Write the report.** Save as `API_RUNTIME_VERIFY.md` (or `API_RUNTIME_VERIFY_<slice>.md` when several slices are verified) in the active task folder: the confirmed target and whether it was local or development, the probe mechanism, the run directory path with every artifact it holds, the per-route record (request, status, content-type, observed shape, or the honest n/a), the classification table, the per-criterion verdict, and the gate decision.
- No-op rule: if a current verification already covers this slice with no material change (the target build, the route set, and the acceptance behavior unchanged since the last PASS), return a short NO_OP note and route forward.
- **Per-slice adoption.** A backend slice with runtime-observable route behavior runs this gate, or records an explicit skip reason in the slice notes (a pure-config or migration-only slice with no route to call). A silently skipped runtime gate is a decay mode; the explicit skip line keeps the decision visible.

Required output:
1. Slice under verification, acceptance behavior, and the confirmed target (base URL, how it was started, which build answers there, and whether it is local or development)
2. Per-route record: the request made, the HTTP status, the response content-type, and the observed body shape, or an honest `n/a (tool absent)`, plus the run directory path with every captured artifact listed
3. Classification table (symptom, taxonomy code, likely cause)
4. Verdict per acceptance criterion (observed | not-observed | unverified)
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
- Every probed route shows the request that was made, the HTTP status, the response content-type, and the observed body shape; a route with no shown output is `unverified` and never PASS (ADR-0048), and an absent tool reports `n/a (tool absent)` rather than a fabricated status.
- The target was confirmed before probing and was local or development; a non-local target was recorded as `unverified: non-local target` and never probed. Any non-idempotent route ran only against a target where its side effect was stated and acceptable.
- The exchange this run recorded is written under `<task-folder>/evidence/<slice-id>/` with secrets redacted, and every path is cited; no human was asked to paste a response body. WHERE neither a request recorder nor an OpenAPI conformance checker was reachable, the verdict is BLOCKED naming that capability and routing, never PASS.
- The mechanical and judgment split was read from the battery topic and not decided in this run; a shape verdict with no declared contract behind it says so.
- Every observation carries a taxonomy code and a per-criterion verdict; the gate decision (PASS | FAIL | BLOCKED) is explicit with its reason; the failure paths the acceptance behavior names were probed, or the verdict says they were not.
- Secrets and personal data are redacted; the report keeps the recorded shape, not a full payload dump.
- The command names no specific HTTP client and no specific MCP server (capability-routed) and writes no code (a FAIL routes to `incident-triage`, `implement-slice-complement`, `security-review`, or `api-contract-review`).
- A hold-until-pass loop carries the bounded-retry cap; a PASS is Layer-1 runtime evidence that does not skip Layer 2 or Layer 3.
- `API_RUNTIME_VERIFY.md` is written in Agent mode.
- Output ends with a complete `### Handoff` block per the adaptive format in `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract`.
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
The verdict is only as good as the exchange you can show. Record the request before judging the response, compare the observed shape against a declared contract instead of against what you expected, report the routes you could not reach as unverified, and route the fix rather than reaching for it.
