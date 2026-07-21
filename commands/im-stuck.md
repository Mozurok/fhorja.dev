---
name: im-stuck
description: Break the task out of a loop, confusion state, or false-progress state, and determine the fastest safe path forward. Diagnoses whether the issue is technical, workflow-related, or scope-related, then routes to the right recovery command and editor mode (Ask by default; Debug if the stuckness is a concrete technical failure; Plan if it is a phase or contract or sequence issue). Use when progress is looping or stalling, the same questions or reviews are being repeated, the wrong command or wrong editor mode may be in use, or when the user is unsure whether the problem is technical, workflow-related, or scope-related. Do not use when the next step is already clear, the task only needs normal routing via what-next, or when the task is brand-new and should start with task-init. When the real blocker is a vague prompt, use prompt-shape.
metadata:
  category: state-and-navigation
  primary-cursor-mode: Ask
  multi-repo-aware: false
  context-layers-consumed: [memory, history]
  context-layers-produced: [memory]
  tools: [Read, Write, Edit, Bash, Glob, Grep]
  x-wos-profiles: [core, full]
  provenance: first-party
  token-budget: 2300
  suggested-model: claude-haiku-4-5
---
# im-stuck

Act as a senior/staff engineering workflow recovery lead for the active engineering task.

Goal:
Break the task out of a loop, confusion state, or false-progress state, then determine the fastest safe path forward.

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
- TASK_STATE.md
- SOURCE_OF_TRUTH.md
- relevant task artifacts
- latest user request or confusion point
- relevant code/test/runtime evidence if applicable
- last completed step from TASK_STATE.md (command + summary)

Operating rules:
- Do not implement code unless explicitly asked in a later step.
- **Handoff:** end with the adaptive `### Handoff` block per `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full).
- Diagnose why progress is stuck.
- Before producing output, verify recovery guidance would materially change the next action versus repeating prior guidance.
- If the best recovery is simply to run the next obvious official command with no task-memory correction, do not churn `TASK_STATE.md`.
- No-op rule for artifacts:
  - If `TASK_STATE.md` would not materially change, do not rewrite it.
  - Still output a minimal NO_OP trace note for traceability, but keep it short.
- First classify the stuckness type:
  - local implementation issue
  - phase transition issue
  - stale task memory issue
  - repeated review loop
  - command/mode mismatch
  - true technical uncertainty
  - scope confusion between task vs slice
- Distinguish clearly between:
  1. what is actually blocked
  2. what is already decided and should stop being reopened
  3. what is missing and truly needs resolution
  4. what is noise or repeated discussion
  5. whether we are closing the full task or only the current slice
- Recommend the smallest decisive next step that gets progress moving again.
- **Cheap check before expensive research.** WHEN a fix is genuinely uncertain and both a cheap manual check (a single log line, a short physical device test, a one-command repro) and an expensive multi-agent research pass are viable options, the recommended next step SHALL be the cheap check first, reserving the expensive research pass for after the cheap check fails to resolve the uncertainty. Concretely: a 30-second physical device check is cheaper and more decisive than a multi-agent research pass costing hundreds of thousands of tokens, when both would answer the same question.
- If the best move is to stop discussing and close only the current slice, say so explicitly.
- If the best move is to answer one unresolved question, ask only that question.
- If the best move is to correct task memory, include the exact TASK_STATE.md update block.
- Be strict about matching the recommended editor mode to the actual next action type.

Required output:
1. Why we are stuck
2. Stuckness classification
3. What is already settled
4. What is still truly open
5. What should stop being revisited
6. Are we closing the task or only the current slice?
7. Best recovery action now
8. Best next command
9. Best editor mode
10. Exact TASK_STATE.md update block, or explicit `TASK_STATE: NO_CHANGE`
11. What should not be done yet

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
- Classifies the stuckness type and names what should stop being reopened.
- Recovery action is the smallest decisive step (not a new initiative).
- `TASK_STATE.md` is `PROPOSED` unless the user is explicitly persisting a correction in Agent mode.
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
Optimize for decisiveness, momentum recovery, correct phase routing, and low ambiguity.

<!-- cache-breakpoint -->
