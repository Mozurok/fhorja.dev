---
name: verify-against-rubric
description: |-
  Spawn a stateless sub-agent (Claude Code Task tool, Cursor agent mode, or equivalent) with ONLY the artifact path plus the locked rubric plus read-only tools. Sub-agent returns a structured verdict (satisfied, needs_revision, or failed) plus per-criterion feedback. Distinct from self-critique-and-revise (same-context; rewrites in place). Use after pr-package, contract-signoff, or implement-approved-slice on HIGH-complexity slices when independent verification matters more than throughput. Do not use on LOW or MEDIUM complexity slices (self-critique-and-revise covers those at lower cost), when no locked rubric exists yet or the rubric is vague (run resolve-contract-gaps first), or when no active task folder exists yet (run task-init first). For 4 or more artifacts against one rubric, use verify-against-rubric-fleet.
metadata:
  category: planning-and-validation
  primary-cursor-mode: Plan
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
  token-budget: 2200
  suggested-model: claude-sonnet-4-6
---

Act as a senior/staff engineer dispatching an independent stateless verification sub-agent against a locked rubric.

Goal:
Verify a task artifact (PR package, signed-off contract, executed slice) against a locked rubric using an isolated sub-agent context. The sub-agent sees only the artifact + the rubric (no TASK_STATE.md, no DECISIONS.md, no prior conversation). Sub-agent returns a structured verdict; main thread persists it to `VERIFICATION_LOG.md` and emits the next-step handoff. Closes the same-context bias gap that `self-critique-and-revise` (in-thread) inherits. Per ADR-0033 and Anthropic Outcomes (2026-05-06; +10pp success vs same-context critique).

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
- artifact path (PR_PACKAGE.md, contract document, slice file, etc.)
- rubric source: EITHER inline rubric (criteria list with verdict thresholds) OR reference to a section in IMPLEMENTATION_PLAN.md or DECISIONS.md (path + section anchor)
- task folder path
- optional: prior verdict id (for delta check vs previous run)

Task repository files to update:
- VERIFICATION_LOG.md (new optional task file; append-only)
- TASK_STATE.md (`## Last completed step` references the new verdict id)

Operating rules:
- **Handoff:** end with the adaptive `### Handoff` block per `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact, Mode B full, or Mode C parallel-fanout when triggered).
- **Step 1: Lock the rubric.** Either accept the inline rubric as-is or extract the referenced section from IMPLEMENTATION_PLAN.md / DECISIONS.md. The rubric MUST list discrete criteria (each verifiable independently). Refuse with NO_OP_TRACE if the rubric is vague ("looks good", "feature works") -- route to `resolve-contract-gaps` first.
- **Step 2: Spawn sub-agent (the load-bearing step).** Invoke the host's stateless sub-agent primitive (Claude Code `Task` tool with `subagent_type: general-purpose`; Cursor agent mode subagent; Codex agents). The sub-agent receives ONLY:
  - The artifact file path (read-only)
  - The rubric (verbatim)
  - Instruction: "Verify the artifact against each criterion. Return a structured verdict: per criterion, mark satisfied / needs_revision / failed with a 1-2 line reason. Then an overall verdict."
  - NO TASK_STATE.md, NO DECISIONS.md, NO prior conversation history.
- **Step 3: Receive verdict.** Sub-agent returns the verdict in the agreed structured format. Main thread does NOT re-evaluate or override the verdict; it persists it.
- **Step 4: Persist to VERIFICATION_LOG.md.** Append a new entry with: verdict id (auto-incremented), date, artifact path, rubric source, per-criterion verdict, overall verdict, sub-agent identifier (Claude Code Task ID or equivalent), and the timestamp.
- **Step 5: Update TASK_STATE.md.** Per the canonical 5-section write pattern in `commands/_shared/task-state-slice-closure-pattern.md`, update `## Last completed step` to reference the new verdict id.
- **Step 6: Emit handoff.** If verdict = satisfied: route to the next planned step (often `pr-package` submission or the next slice). If needs_revision: route to `implement-slice-complement` (with verdict feedback inline). If failed: route to `direction-adjust` or `decision-interview` based on the failure type.
- Do NOT use this command on LOW or MEDIUM complexity slices: `self-critique-and-revise` is the cheaper in-thread alternative.
- Do NOT spawn sub-agent without an explicit locked rubric. Vague rubrics produce vague verdicts.

Required output:
1. Rubric source (inline or referenced section)
2. Number of criteria evaluated
3. Per-criterion verdict (table)
4. Overall verdict (satisfied / needs_revision / failed)
5. Sub-agent identifier (Task ID or equivalent)
6. Verdict id in VERIFICATION_LOG.md
7. Recommended next command based on verdict

### Review prompt scaffold (optional)
<!-- shared:xml-review-scaffold -->
When the review directives in this command are ambiguous, parse them in three labeled parts: Instructions (what to do), Context (background, not a rule), and Constraints (hard limits that override the rest). This separation is optional and adds signal only where reviewers report ambiguity; do not tag mechanically or let it bloat the prompt.
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
- Rubric is locked and discrete (criteria are independently verifiable).
- Sub-agent invoked with isolated context (no TASK_STATE.md, no DECISIONS.md, no prior history).
- Verdict returned with per-criterion breakdown and overall classification.
- VERIFICATION_LOG.md updated with the verdict entry.
- TASK_STATE.md `## Last completed step` references the verdict id.
- Handoff routes based on verdict: satisfied -> next step, needs_revision -> implement-slice-complement, failed -> direction-adjust or decision-interview.
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
The verdict is only as good as the rubric. If the rubric is vague, the verdict is vague. Refuse vague rubrics. The sub-agent isolation is the load-bearing differentiator vs `self-critique-and-revise`; do not collapse them.

<!-- cache-breakpoint -->
