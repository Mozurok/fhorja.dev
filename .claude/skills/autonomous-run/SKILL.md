---
name: autonomous-run
description: |-
  Drive an approved, waved IMPLEMENTATION_PLAN through the autonomous delivery track. A thin code-orchestrated dispatcher over the existing fleet primitives (the Workflow tool, implement-approved-slice as single writer) bounded by two human gates and a runtime governor. Runs verifiable slices with little supervision and emits PROPOSED slice diffs only; it never merges. Use when the plan is approved (approve-plan), broken into dependency-ordered waves, and the maintainer wants the work between the two gates run hands-off in a single supervised session. Do not use when the plan is not yet approved (run approve-plan), the work is a single slice (use implement-approved-slice), the run would need to remove the human merge gate or auto-merge (never allowed; a human always performs the merge), or cross-session durable resume (restart and re-attach of a stopped run) is required (out of v1 scope; a detached single continuous background session is in scope via the opt-in background mode).
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
  token-budget: 3200
  suggested-model: claude-sonnet-4-6
---

Act as the controller for the autonomous delivery track, driving an approved waved plan through bounded, low-supervision execution.

Goal:
Run an approved, waved `IMPLEMENTATION_PLAN.md` slice by slice with little human supervision, bounded by two human gates and a runtime governor, emitting PROPOSED slice diffs for review and never merging on its own. The controller is a thin dispatcher over the existing primitives (the Workflow tool per ADR-0038, `implement-approved-slice` as the single writer per slice); it adds the governor, the boundary/test classifier, and the escalation routing defined in ADR-0044 (D6, D11, D12). It does not re-implement approval, writing, or review.

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
- IMPLEMENTATION_PLAN.md with an approved `## Approval log` entry and an `## Execution waves` section (dependency-ordered, file-scope-disjoint per ADR-0041)
- TASK_STATE.md, DECISIONS.md (the run honors every locked decision)
- the STOP sentinel file path (outside the agent writable scope) and the governor limits (per-task token/cost ceiling, max-iteration, wall-clock timeout)
- last completed step from TASK_STATE.md (command + summary)

Operating rules:
- **Approval is a precondition.** If `IMPLEMENTATION_PLAN.md` has no `## Approval log` entry for the current plan revision, refuse and route to `approve-plan`. Never run an unapproved plan.
- **Two gates, never auto-merge (D6).** The plan-approval gate is upstream (`approve-plan`, already passed). The merge gate is downstream: the controller produces PROPOSED slice diffs and routes the merge to `approve-proposed` and `review-hard`. The controller MUST NOT commit, merge, deploy, or take any irreversible step.
- **Single writer (ADR-0040).** Each slice is executed by `implement-approved-slice`; the controller never writes product files itself. Parallel subagents on the implement leg are forbidden (D9).
- **Between every slice, run the governor and the classifier.** Call `scripts/autonomy/stop-check.sh` (halt if STOP present, D11), `scripts/autonomy/governor.sh` (halt on max-iteration, wall-clock timeout, or identical-command loop, D11), and `scripts/autonomy/classify-slice.sh` over the slice's file set.
- **Mid-run escalation (D6/D12).** When the classifier returns `escalate` (a boundary slice: schema, contract, migration, security; or any slice that touches a test or eval file), stop the wave at that slice and surface it to the human gate. Flag test and eval changes separately in the PROPOSED diff. Never auto-advance a slice on a test result the agent changed within that same slice.
- **Default to escalate on uncertainty.** A slice whose file set cannot be proven free of boundary and test/eval paths escalates. A false auto-advance is the dangerous failure.
- **Skip list (D9), refuse and record.** Never run in a permissive headless mode (acceptEdits, bypassPermissions, skip-permissions, yolo), never auto-run without approval, never let the model pick its own autonomy tier, never auto-deploy. If asked, refuse and cite ADR-0044 D9.
- **Tracking is Fhorja-internal (D7).** The board of record is the spec, the plan waves, and the TASK_STATE phases. Do not integrate or write to an external work tracker. For a single-glance read-only view of that board of record, use `autonomous-board`.
- **Trust comes from the Fhorja evals and the human merge (D10).** Mark a slice done only when its EARS exit criterion is met and verified; never gate on a vendor benchmark.
- **Single supervised session (v1).** Scope a run to one session bounded by the governor and the STOP file. Cross-session durable resume (restart and re-attach of a stopped run) is out of scope; if the run cannot finish in-session, stop cleanly at a slice boundary and hand off with the resume point recorded in TASK_STATE.md. A detached background session (below) is still ONE continuous session and does not conflict with this rule.
- **Background mode (opt-in; D-1..D-4 of the 2026-07-03 background-run task; runs-feed contract in ADR-0080).** The run MAY execute detached in an isolated worktree, launched via `scripts/autonomy/launch-background-run.sh` (or the manual pattern it prints when `WOS_AGENT_CMD` is unset). In background mode the controller ADDITIONALLY:
  - produces the runs feed: `scripts/autonomy/runs-feed.sh start` on entry; `update` with a fresh heartbeat and the current slice as the step alongside the existing between-slice governor calls; `update --state escalated` plus `scripts/autonomy/notify.sh` on ANY halt or escalation; `end` on clean exit (a terminal outcome belongs in the outcome ledger per ADR-0079, never in the feed).
  - uses an ABSOLUTE main-repo STOP sentinel path (the launcher prints it); a path inside the worktree is invalid because the agent could write over it.
  - runs under the repository's pre-approved permission allowlists ONLY; the D9 skip list applies unchanged and no permissive flag exists that this mode accepts. IF a permission prompt would block the detached session THEN the run stalls until the governor's wall-clock timeout produces a clean stop at a slice boundary, recorded in the feed as state=escalated with the stall named as the reason (D-1).
  - never runs concurrently: the launcher refuses while any fresh-heartbeat feed file exists (D-4; staleness threshold in the background-mode ADR).
  Escalation semantics are UNCHANGED by detachment: an escalation halts the run; nothing auto-advances because nobody is watching.
- **Substrate write protocol (per ADR-0034, K.2):** for every write to a substrate section, emit the transaction header AND append one `.wos/VERIFICATION_LOG.jsonl` line per `commands/_shared/substrate-write-protocol.md`.
- **Handoff:** end with the adaptive `### Handoff` block per `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract`.

Required output:
1. Pre-flight: plan approved (yes/no), waves detected, governor limits, STOP file path (background mode: plus the run_id, feed file path, and log path)
2. Per wave: the slices attempted, each slice's classifier verdict (auto / escalate + reason)
3. Slices executed (via `implement-approved-slice`) with PROPOSED-diff status, and slices escalated to the human gate
4. Governor status at stop (iterations, elapsed, whether a limit halted the run)
5. The exact merge-gate routing (`approve-proposed` / `review-hard`) for the PROPOSED diffs
6. What was intentionally not done (no merge, no deploy, escalated slices left for the human)
7. Recommended next command (`approve-proposed` for the produced diffs, or `implement-approved-slice` for an escalated slice the human now approves)
8. Recommended editor mode
9. Why this is the correct next step

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
- The run emits only PROPOSED slice diffs; no commit, merge, or deploy happened (D6/D9).
- Every slice passed the governor (`stop-check.sh`, `governor.sh`) and the classifier (`classify-slice.sh`) before execution; the evidence is in the transcript.
- Every boundary or test/eval-touching slice was escalated to the human gate, not auto-advanced (D6/D12).
- The plan was approved (`## Approval log` present) before the run; an unapproved plan is a refusal routed to `approve-plan`.
- In background mode: the runs feed reflected every state transition (start, per-slice heartbeats, escalated on any halt, end on clean exit), the STOP path was absolute in the main repo, and the permission posture was allowlist-only with no permissive flag (the D9 skip list unchanged).
- No existing command was modified; the controller reused `implement-approved-slice`, `approve-proposed`, and `review-hard` (D5/D8).
- Output ends with a complete `### Handoff` block per the adaptive format in `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract`.
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
A boring, bounded run that a human can trust precisely because it never crosses a gate on its own. Prefer stopping and escalating over guessing.

<!-- cache-breakpoint -->
