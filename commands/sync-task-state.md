---
name: sync-task-state
description: Update TASK_STATE.md so it reflects the latest operational truth of the task and can be resumed safely in this or another session. Lighter-weight than state-reconcile (no cross-artifact drift detection); preferred when the update is incremental and trusted. Use when a meaningful planning, decision, implementation, or closure step just happened, a slice was completed or closed, canonical decisions changed, the task is about to be paused or handed off, or TASK_STATE.md is stale relative to current progress. Do not use when no meaningful progress or decision change occurred, the task should first be initialized with task-init, or the current need is broad discovery rather than state synchronization.
metadata:
  category: state-and-navigation
  primary-cursor-mode: Ask
  multi-repo-aware: false
  context-layers-consumed: [memory]
  context-layers-produced: [memory]
  tools: [Read, Write, Edit, Bash, Glob, Grep]
  x-wos-profiles: [minimal, core, full]
  provenance: first-party
  token-budget: 2300
  suggested-model: claude-haiku-4-5
---
# sync-task-state

Act as a senior/staff engineering workflow state manager for the active engineering task.

Goal:
Update TASK_STATE.md so it reflects the latest operational truth of the task and can be resumed safely in this or another session.

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
- DECISIONS.md
- IMPLEMENTATION_PLAN.md
- latest relevant task artifacts
- current known task status

Task repository files to update:
- TASK_STATE.md

Operating rules:
- Do not implement production code.
- **Handoff:** end with the adaptive `### Handoff` block per `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full).
- **Substrate write protocol (per ADR-0034, K.2 2026-06-04):** for every write to a substrate section (the 4 task-memory files plus the fleet-substrate files per `wos/substrate-peers.md ## Fleet-substrate files`), emit the transaction header AND append one `.wos/VERIFICATION_LOG.jsonl` line per `commands/_shared/substrate-write-protocol.md`. Shadow mode at launch -- writers emit, no reader enforces.
- **Bounded slice-status propagation (opt-in, Slice-08 P2).** DEFAULT = OFF: with no propagation scope declared, this command writes ONLY `TASK_STATE.md` (its stated update scope above) and nothing else changes. Propagation fires ONLY when the run declares the bounded scope `propagate-slice-status=<subset of {IMPLEMENTATION_PLAN, SOURCE_OF_TRUTH, README, TEST_STRATEGY}>`; it is a bounded set of named siblings, never a global flag. For each named target write the bounded slice-status field (closed enum: `in-progress | implemented-pending-closure | closed | closed-with-followups | not-ready`) honoring its write regime:
  - Regime 1 (SUBSTRATE -- inline `<!-- wos:write owner=sync-task-state ... -->` header + one `.wos/VERIFICATION_LOG.jsonl` line reusing THIS run's run_id/ts): `IMPLEMENTATION_PLAN.md` sets the field on the `### Slice N` `Status:` line and LOGS the H3-scoped co-write at the owning `## Slices` H2; `SOURCE_OF_TRUTH.md` writes/extends the `## Slice status` H2 pointer with a header above that H2 and one JSONL line naming `section='## Slice status'` (`sha_after` a real 64-hex, never null on the applied write).
  - Regime 2 (PLAIN -- direct Edit only, NO wos:write header, NO JSONL line): `README.md` and `TEST_STRATEGY.md` are outside the substrate set and outside `scan-substrate-headers.sh`; a header there would be pointless drift.
  G5 state-reconcile drift detection stays intact: every Regime-1 write still emits its header + JSONL line, and the Regime-2 files stay out of the substrate scan.
- **Context-rot guardrail (ADR-0023):** before producing the output, estimate the current TASK_STATE.md token count (excluding the `## Compaction history` section). Compare against the phase threshold from `wos/context-budget.md ## Context-rot thresholds` (discovery: 3000; planning: 5000; implementation: 8000; review/closure/delivery: 6000). If current count exceeds the threshold, emit a single-line warning in `### Command transcript`: `WARN: TASK_STATE.md is ~Ntokens (phase threshold: Mthreshold). Consider running compact-task-memory before continuing.` The warning is INFORMATIONAL; proceed with the normal output. Suppress the warning if the immediately prior step was `compact-task-memory`.
- Treat TASK_STATE.md as the operational memory for the current task.
- Keep it concise, structured, and implementation-oriented.
- Reflect the current workflow truth based on:
  - latest approved plan
  - latest canonical decisions
  - latest review or test-strategy outputs
  - latest completed implementation or slice-closure step
  - latest `repo-consistency-sweep` pointer (if a SWEEP snapshot was written, preserve the `## Latest sweep` line or inline pointer under `## Risks to watch`; do not strip it during sync)
- Do not restate broad historical analysis unless it still matters operationally.
- If TASK_STATE.md conflicts with newer approved artifacts, correct it explicitly.
- If the task state is unclear, say what evidence is missing instead of inventing it.
- Set **Work complexity** from current phase, blast radius, and the **next** recommended command (not from bravado). Use `N/A` only when the next step has no meaningful capability tradeoff. Never name model SKUs.
- **Post-commit delivery sync is handled by `branch-commit`:** when all slices are complete and committed, `branch-commit` auto-updates TASK_STATE.md phase to "delivered". A separate `sync-task-state` call solely to mark "delivered" after commit is unnecessary and should be skipped (see anti-pattern: redundant post-commit sync).
- If **Work complexity (for next execution step)** is missing from `TASK_STATE.md` (for example older tasks created before that subsection existed), add the full subsection in this run using the same structure as `task-init` (heading, `LOW | MEDIUM | HIGH | N/A` line, and one-line rationale).

TASK_STATE.md must contain:
1. Task summary
2. Current phase
3. Objective
4. Source of truth
5. Current known facts
6. Canonical decisions
7. Open questions / blockers
8. Last completed step
9. Current status
10. Active files in scope
11. Constraints / things that must not change
12. Risks to watch
13. Recommended next step
14. Resume notes
15. Task scope level
16. Current closure target
17. Work complexity (for next execution step): one of `LOW`, `MEDIUM`, `HIGH`, or `N/A`, plus a one-line rationale (definitions in `WORKFLOW_OPERATING_SYSTEM.md`)

Required output:
1. Whether TASK_STATE.md should be updated and why
2. Exact content for TASK_STATE.md
3. Recommended next command
4. Recommended editor mode
5. Why this is the correct next step
6. What should explicitly not be done yet

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
- `TASK_STATE.md` reflects the latest approved truth without inventing decisions.
- Any stale/contradictory state is called out explicitly with evidence pointers.
- `### Artifact changes` marks `TASK_STATE.md` as `APPLIED` only when persisting; otherwise `PROPOSED`.
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
Optimize for resumability, continuity, low ambiguity, and strict alignment with the latest approved task truth.

<!-- cache-breakpoint -->
