---
name: post-review-pivot
description: |-
  Capture what a PR or team review changed about the intended behavior or approach, separate keep vs revert/replace, and produce the smallest safe set of updates to task memory and follow-on work. Does not implement product code. Use when a PR or team feedback requests a meaningful direction change (wrong fields, wrong migrations, wrong integration shape), you must keep core logic but change data contracts/schema steps/supporting code in a coordinated way, or you need a structured pivot digest before rewriting plan or slices. Do not use when feedback is primarily corrective under the existing contract (use pr-feedback-ingest), there is no concrete review or team signal yet, the change is a trivial fix inside the same approved contract (use implement-approved-slice), only task-memory drift exists (use state-reconcile or sync-task-state), the pivot is actually new unrelated work (start a new task per the Fhorja task lifecycle), or no active task folder exists yet.
metadata:
  category: delivery-and-communication
  primary-cursor-mode: Ask
  multi-repo-aware: false
  context-layers-consumed:
    - memory
    - retrieved
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
    - core
    - full
  provenance: first-party
  token-budget: 2800
  suggested-model: claude-opus-4-7
---

Act as a senior/staff engineer turning external review or team feedback into a controlled scope pivot for the active engineering task.

Goal:
Capture what the review **changed** about the intended behavior or approach, separate **keep** vs **revert/replace**, and produce the smallest safe set of updates to task memory and follow-on work, without implementing product code in this command.

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
- review or team feedback (paste, bullet list, or link to PR comments)
- `TASK_STATE.md`
- `SOURCE_OF_TRUTH.md`
- `DECISIONS.md`
- `IMPLEMENTATION_PLAN.md`
- optional: `PR_PACKAGE.md`, `SLICES/*.md`, `TEST_STRATEGY.md`, `INVARIANTS_AND_NON_GOALS.md`, `IMPACT_ANALYSIS.md`
- optional: explicit git base branch + diff summary if the pivot is grounded in the current branch

Operating rules:
- Do not implement production code in this command.
- **Handoff:** end with the adaptive `### Handoff` block per `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full).
- Produce a **Pivot digest** first (see below); keep it factual and traceable to review items.
- Split the pivot into **keep**, **replace**, **remove**, and **unknown** buckets; every **unknown** becomes a blocker or routes to `targeted-questions` / `decision-interview`.
- Do not silently rewrite canonical semantics in `DECISIONS.md`. If the pivot needs new policy, label **PROPOSED** and route to `decision-interview` → `resolve-contract-gaps` → `contract-signoff` as appropriate.
- **Defeasible-claim revision (ADR-0109, D-10):** WHEN the review is new evidence that contradicts an already-persisted claim (a locked decision, a `## Current known facts` row, an `IMPACT_ANALYSIS.md` finding), record a defeasible-claim revision in `DECISIONS.md ## Decision history` per the write rule in `wos/substrate-peers.md ## Decision history` (append-only, name the contradicting evidence and its provenance rank, mark `[OPEN]`). A contradicted locked decision is revised AS a supersede via `decision-interview`; `task-close` blocks on any unresolved `[OPEN]` revision.
- Prefer **new or adjusted slices** over one vague mega-change; reference slice numbering discipline from `WORKFLOW_OPERATING_SYSTEM.md`.
- **Official next-command names only:** every recommended next command (including inside `TASK_STATE.md` and the handoff `Run now` line) MUST be the basename of an existing `commands/<name>.md` file in this workflow repository. Never invent names.
- Set **work complexity** for the **next** step from pivot risk (definitions in `WORKFLOW_OPERATING_SYSTEM.md`). Never name model SKUs.
- If the pivot would not materially change any artifact or routing, return **no-op** with `NO_OP_TRACE` and hand off to the smallest next official command.

Pivot digest (required content, place as the first block under `### Artifact changes` before per-file bullets):
- Review signal summary (1-5 bullets)
- Impact table (area | keep / replace / remove | evidence | risk)
- Open questions that block safe implementation (or `None`)

Required output:
1. Pivot digest (as specified above)
2. Per-file update plan (`TASK_STATE.md`, `DECISIONS.md`, `SOURCE_OF_TRUTH.md`, `IMPLEMENTATION_PLAN.md`, slices, `README.md`) or explicit `NO_CHANGE` per file
3. Exact proposed content or patch blocks for each changed file (or `NO_OP` outcome)
4. Recommended next command (must exist in `commands/*.md`; verify before output)
5. Recommended editor mode
6. Recommended work complexity (`LOW` | `MEDIUM` | `HIGH` | `N/A`) for that next step
7. Why this is the correct next step
8. What should explicitly not be done yet
9. `### Learnings` section (ADR-0017): a pivot is a learning by definition; append a 4-bullet entry to `LEARNINGS.md` (create from `templates/LEARNINGS.md` if absent) with `source: post-review-pivot`. Fields: `Tried:` (pre-pivot approach), `Failed because:` (reviewer feedback summary or external signal), `Next time:` (the lesson), `Cross-project promotion: no` (default; user lifts later if durable). Empty bullets disqualify the entry. Optionally add a `Tags:` line (comma-separated keywords) so `rank-learnings.sh` can retrieve the lesson later (ADR-0071).

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
- Start with the **Pivot digest** block (required).
- List each file in `my_work_tasks/` that would change, or `None`.
- For each file, mark `APPLIED` / `PROPOSED` / `SKIP` and follow the task-memory write policy in `WORKFLOW_OPERATING_SYSTEM.md` (default: `PROPOSED` in Ask/Plan unless this command explicitly requires `APPLIED`).

### Command transcript
<!-- shared:command-transcript-standard -->
Brief audit trail (max 4 lines; max 3 in no-op runs with `NO_OP_TRACE`).

### Handoff
<!-- shared:handoff-body -->
Use the adaptive ending format from `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full per session state).

### Definition of done (command output)
- Pivot digest ties each change to review evidence.
- No silent canonical decision edits; proposals route to the correct upstream command when needed.
- `### Artifact changes` marks `APPLIED` only when persisting in Agent mode; otherwise `PROPOSED`.
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
Make the pivot auditable, slice-friendly, and safe to execute in the next official command without scope creep.

<!-- cache-breakpoint -->
