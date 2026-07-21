---
name: approve-proposed
description: Atomically persist every file marked PROPOSED in the most recent prior assistant turn's `### Artifact changes` block. Single-command idiom that closes the two-step latency in ADR-0001's PROPOSED-by-default contract; the user reviews proposals in Ask/Plan mode, then runs this once to write all of them. Use when the prior assistant turn ended with a `### Artifact changes` block containing one or more files marked PROPOSED and you have read and accepted the inline content for each. Do not use when the prior turn had no `### Artifact changes` block, every artifact is APPLIED or SKIP, you have not yet read the proposed content, or you want to approve only a subset (run the original command in Agent mode for partial approval).
metadata:
  category: state-and-navigation
  primary-cursor-mode: Agent
  multi-repo-aware: false
  context-layers-consumed: [history, memory]
  context-layers-produced: [memory]
  tools: [Read, Write, Edit, Bash, Glob, Grep]
  x-wos-profiles: [core, full]
  provenance: first-party
  token-budget: 3000
  suggested-model: claude-haiku-4-5
---
# approve-proposed

Act as a senior/staff engineer executing a single batch-persist of every file the prior assistant turn proposed under `### Artifact changes`.

Goal:
Read the most recent prior assistant turn in the conversation history, identify every file marked `PROPOSED` in its `### Artifact changes` block, and write all of them atomically. Print a single recap line listing what landed.

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
- the conversation history containing the most recent prior assistant turn with an `### Artifact changes` block (already in context when the command runs)
- active task folder path (for resolving relative artifact paths)

Task repository files to update:
- every file listed in the prior turn's `### Artifact changes` block that is marked `PROPOSED` (full inline content or update-delta)

Operating rules:
- Do not propose anything. This command is for executing prior proposals, not creating new ones.
- **Source-of-truth turn**: the "prior assistant turn" means the most recent assistant message whose `### Artifact changes` block is NON-EMPTY and carries at least one `PROPOSED` file. Skip intervening user messages, tool results, assistant messages with no Artifact-changes block, AND assistant messages whose Artifact-changes block is empty (a NO_OP `None` / `NO_FILE_CHANGES` block): an empty block does NOT shadow an earlier real proposal (D-4, 2026-07-18). STOP walking back at the first intervening block that carried real `APPLIED` or `SKIP` decisions: never reach past a block the user already acted on, so a superseded proposal is never resurrected. This preserves ADR-0024's rule that you never walk back across multiple *decision-bearing* Artifact-changes turns; it only skips empty NO_OP blocks that would otherwise hide the latest real proposal.
- **Content required**: persist files that have either (a) full inline content or (b) an update-delta (semantic description of changes to an existing file). For full inline: write the content as-is. For update-delta: read the current file on disk, apply the described changes, and write the result. If a file is marked `PROPOSED` but its content is vague or unresolvable (e.g., "see content above", "same as last turn"), do NOT persist it; list it under `Skipped (incomplete inline)` in the recap.
- **Path resolution**: every file path in the prior block must resolve to a real path inside the active task folder OR inside `my_work_tasks/` (for workflow meta-edits). If a path resolves outside both, do NOT persist it; list it under `Skipped (path outside scope)` in the recap.
- **Atomic batch**: perform all qualifying writes in this single turn (one Write per file). Do not split across multiple turns. Do not interleave Write calls with conversational prose.
- **No partial mode**: this command is all-or-nothing for the qualifying subset. If the user wants partial approval, they re-run the source command in Agent mode or edit the proposals before running this command.
- **No-op cases**:
  - Prior turn has no `### Artifact changes` block: NO_OP with explicit explanation ("most recent assistant turn does not contain an Artifact changes block; nothing to approve").
  - Prior block contains no `PROPOSED` files (all `APPLIED` or `SKIP`): NO_OP with explicit explanation.
  - All PROPOSED files match on-disk content already: NO_OP with explicit explanation ("all proposed files are identical to current on-disk content; nothing to write").
- **No new proposals**: if the user input contains additional instructions beyond "approve", ignore them. This command does not accept new content; it only executes the prior batch. To propose new artifacts, re-run the source command.
- **Recap format (locked)**: the `### Command transcript` section MUST contain exactly one recap line per outcome class, in this order:
  1. `Persisted: <comma-separated-list-of-paths>` (omit line if empty)
  2. `Skipped (already current): <list>` (omit if empty)
  3. `Skipped (incomplete inline): <list>` (omit if empty)
  4. `Skipped (path outside scope): <list>` (omit if empty)
  5. `Skipped (no PROPOSED marker): <list>` (omit if empty)
- **Conflict-check rule**: before persisting any file, compare the proposed content's references to locked decisions in `TASK_STATE.md ## Canonical decisions`. If the proposal contradicts a locked decision, FAIL with a clear error naming the contradiction; do NOT persist anything in this turn (atomic rollback).
- **Substrate write protocol (per ADR-0034, K.2, ADR-0101).** WHEN a persisted file is a K.2 substrate file per `commands/_shared/substrate-write-protocol.md`, replace the proposer's mode=proposed transaction header with this run's `owner=approve-proposed ... mode=applied` header and append one `event=approve` JSONL line per applied file to `active/<task>/.wos/VERIFICATION_LOG.jsonl` with valid sha_before/sha_after (`bash scripts/emit-substrate-write.sh` is the invokable path); non-substrate files are unaffected.
- **Handoff:** end with the adaptive `### Handoff` block per `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full).

Required output:
1. The `### Artifact changes` block listing every persisted file as `APPLIED` (no inline content needed; the content already lived in the prior turn). Files that did not persist appear marked `SKIP` with a one-line reason.
2. The `### Command transcript` block with the recap lines per the format above.
3. A one-line summary stating how many files persisted vs how many were skipped.
4. Recommended next step, next command, editor mode, and why (typically routing back to whichever command produced the original proposals, OR to `sync-task-state` if the persisted files materially change task state).
5. What should explicitly not be done yet.

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
- Every file the prior turn marked `PROPOSED` (full inline or update-delta) is either persisted as `APPLIED` or explicitly skipped with a recap-line reason. Silent omission is invalid.
- The `### Command transcript` recap follows the locked five-line format (Persisted / Skipped already current / Skipped incomplete inline / Skipped path outside scope / Skipped no PROPOSED marker). Lines that have zero entries are omitted; lines that have entries appear in the locked order.
- No new artifacts are introduced beyond what the prior turn proposed. Adding files this command "thinks" should also be written is invalid output.
- No-op runs include `NO_OP_TRACE` and name the no-op cause (no Artifact-changes block / no PROPOSED files / all already current).
- Conflict-with-locked-decision runs do NOT persist anything; they emit a clear FAIL with the contradiction named.
- Output ends with a complete `### Handoff` block per the adaptive format in `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract`.
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
Optimize for: zero ambiguity about what landed on disk, atomic batch semantics, and recap clarity. The user must be able to read the recap and immediately know which files exist on disk now, which were skipped and why, and what to run next.

<!-- cache-breakpoint -->
