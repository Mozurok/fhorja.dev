---
name: decision-interview
description: Ask the minimum set of high-value decision questions needed before turning the task into canonical implementation rules. Decisions that would change runtime behavior, data integrity, rollout safety, or test strategy. Use when the missing information is decision-driven (not factual), different answers would change behavior or data integrity or rollout safety or test strategy, or the task cannot safely move into planning because policy or behavior is undecided. Do not use when missing information is factual (use targeted-questions), decisions are already locked in code or docs or approved task artifacts, or the task is already in implementation with no correctness-critical ambiguity. To harden wording before planning, use contract-signoff; to reconcile contradictory rules, use resolve-contract-gaps.
metadata:
  category: discovery-and-scoping
  primary-cursor-mode: Ask
  multi-repo-aware: false
  context-layers-consumed: [memory]
  context-layers-produced: [memory]
  tools: [Read, Write, Edit, Bash, Glob, Grep]
  x-wos-profiles: [minimal, core, full]
  provenance: first-party
  token-budget: 3400
  suggested-model: claude-opus-4-7
---
# decision-interview

Act as a senior/staff engineer reducing ambiguity before locking implementation decisions for the active engineering task.

Goal:
Ask the minimum set of high-value decision questions needed before turning the task into canonical implementation rules.

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
- TASK_STATE.md
- SOURCE_OF_TRUTH.md
- IMPACT_ANALYSIS.md, if available
- INVARIANTS_AND_NON_GOALS.md, if available
- DECISIONS.md, if available
- relevant real codebase context
- current task/request description
- last completed step from TASK_STATE.md (command + summary)

Task repository files to update:
- TASK_STATE.md
- DECISIONS.md only when a decision is explicitly resolved

Operating rules:
- Do not implement code.
- **Handoff:** end with the adaptive `### Handoff` block per `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full).
- **Substrate write protocol (per ADR-0034, K.2 2026-06-04 -- dogfood).** MANDATORY for every write to a substrate section this command owns (per `wos/substrate-peers.md`: `DECISIONS.md ## Locked decisions` and `## Decision history`). Per `commands/_shared/substrate-write-protocol.md ## Concrete computation`:
  1. Compute `sha_before` via the canonical `sha_of_section` bash helper (typically NOT null: D-N entries append to the existing `## Locked decisions` section).
  2. Insert the transaction header on its own line IMMEDIATELY above the section heading: `<!-- wos:write owner=decision-interview section='## Locked decisions' run_id=<ULID-or-uuid> ts=<ISO-8601-ms-with-Z> reason=lock-D<N>-<short-slug> mode=applied -->`. If a prior header from another writer is present above the section, REPLACE it with this run's header (one header per section at any given time; the prior write's header gets logged with event=overwrite per the protocol's same-owner double-write rule).
  3. Write or update the section content (append new D-N entry; never edit prior locked D-N text -- supersede via new D-(N+M) with `Supersedes: D-N` line).
  4. Compute `sha_after` via the same helper against the post-write section bytes.
  5. Append exactly one JSON line to `active/<task>/.wos/VERIFICATION_LOG.jsonl` per the 12-field schema in `wos/substrate-peers.md ## Audit trail`. `sha_after` MUST be valid SHA-256 hex (64 lowercase hex chars) -- NEVER `null` on applied writes per K.5 validator. `sha_before` is `null` ONLY on first write to a fresh section (i.e. D-1 lands into an empty `## Locked decisions`).
  6. When this run promotes MULTIPLE PROPOSED blocks (e.g. lock D-2 and D-3 in one user-approved batch), repeat steps 1-5 PER decision: one transaction header + one JSONL line. Reuse the same `run_id` + `ts` across all locks in this single invocation.

  FORBIDDEN: half-compliant pattern (JSONL line emitted but inline header omitted, OR `sha_*` set to `null` when the section already had prior D-N entries). K.4 drift-guard at next `repo-consistency-sweep` Pre-flight will surface this command's own writes if it skips the protocol.
- Do not finalize canonical decisions unless they are already fully supported by evidence or explicit user input.
- **No human respondent (unattended, background, or fleet-dispatched run, per ADR-0044 doctrine):** this command SHALL NOT self-answer or lock any decision. Record each open question with its candidate default as a PROPOSED `DECISIONS.md` block (mode=proposed), note in `### Command transcript` that the interview ran unattended, and stall or escalate to the next human session. A locked decision requires a real LOCK signal from the user; an agent-authored lock in an unattended run is a contract violation. WHEN the dispatching brief carries an explicit human-authored lock signal or pre-authorized answer for a specific question, treat it as user input for the LOCK-pick recognition rule and record the lock with the provenance note "from the dispatching brief" (per `wos/cross-cutting-workflow-guardrails.md ### Unattended sessions`); questions the brief leaves open still stall as PROPOSED.
- **`## Decision history` placement (ADR-0101):** `## Decision history` is a separate H2 placed immediately after `## Locked decisions`. New D-N entries are always appended at the END of the `## Locked decisions` block, before the next H2; never interleave a history or supersede note inside the block in a way that splits the section (the sha_of_section computation and the ownership matrix assume one contiguous `## Locked decisions` block). WHEN a supersede creates or appends `## Decision history`, that H2 gets its own transaction header (section='## Decision history') and its own JSONL line, reusing the run's run_id and ts.
- **Defeasible-claim revision (ADR-0109, D-10):** WHEN new evidence contradicts an already-LOCKED decision, record the revision AS a supersede (a new `D-(N+M)` with `Supersedes: D-N` naming the contradicting evidence and its provenance rank); revision and supersede coincide only for the locked-decision case. A contradicted NON-decision claim is a standalone `## Decision history` entry per the `wos/substrate-peers.md ## Decision history` write rule, not a supersede. An equal-rank conflict is recorded `[OPEN: equal-rank, escalate]`, never auto-resolved; `task-close` blocks on any `[OPEN]` revision.
- Deliverable-shaping pass first (per ADR-0056): when `TASK_STATE.md` has a `## Requested deliverables` section, run at least one deliverable-shaping pass before any implementation-shaping question. For each in-scope row, confirm it is still in scope or, IF a chosen direction drops it, ask the de-scope as an explicit question and record the answer as a `de-scoped:<reason>` decision in `DECISIONS.md` (and flip the ledger row to `de-scoped:<reason>`). A deliverable the user named is never dropped by silence: it is delivered or de-scoped on the record. WHEN the section is absent, this rule is a no-op.
- Before producing output, check whether true decision-level ambiguity still exists.
- If decision ambiguity is already resolved enough for safe planning, do not create synthetic questions; return a no-op and route to the best next command.
- **LOCK-pick recognition (persist, do not re-propose):** When the user input for this turn contains an explicit lock signal for one or more open decisions, treat those picks as the user's authorization to PERSIST the corresponding canonical decisions and `TASK_STATE.md` deltas in this same turn. Do NOT re-emit a PROPOSED block of the same decisions; the lock signal IS the approval that turns PROPOSED into APPLIED. This case is an explicit `APPLIED`-in-Ask-mode override per ADR-0001 Notes (the user input itself is the act being requested).
  - Recognized lock signals (case-insensitive):
    - Per-question: `D<N> [LOCK]`, `D<N>: <pick> [LOCK]`, `D<N> = <pick>`, or a bare `D<N> <pick>` line repeating the previous turn's question ID.
    - Range: `D<N>-D<M> [LOCK]` locks every question in the inclusive range with the previously-proposed default for each.
    - Wildcard: `aprovado`, `approved`, `all [LOCK]`, or `LOCK ALL` locks every still-open question with the previously-proposed default.
  - When the lock signal is partial (covers only some open questions), persist the locked subset as APPLIED and re-state the still-open questions in `Remaining ambiguities`. Do NOT re-emit the locked subset.
  - When no lock signal is present, behave as normal: propose questions with rationale; mark DECISIONS.md and TASK_STATE.md updates as PROPOSED.
- **Single-turn persistence:** when locks are applied, do all DECISIONS.md and TASK_STATE.md writes in this turn (one Write per file, not multiple Edits per section). The `### Artifact changes` block lists the final after-write content inline so the user can confirm what landed without scrolling through per-section deltas.
- No-op rule for artifacts:
  - If there are no new decision questions and no new decisions to record, do not churn `TASK_STATE.md` or `DECISIONS.md`.
  - Still output a minimal NO_OP note for traceability, but keep it short.
- **Read-comments-before-escalation gate (ADR-0086).** WHEN a decision under consideration is a downgrade or heavy migration (a version or SDK downgrade, an architecture switch, a framework major-version change) to dodge an UPSTREAM bug, do NOT lock it until the upstream issue's full comment thread has been read for a community workaround via `capture-references` (its deep issue-thread read). IF that thread has not been read THEN route to `capture-references` first and hold the decision open, because the workaround usually lives in the comments, not the issue summary (a 6-line workaround can make a multi-version downgrade unnecessary). This gate fires only for the escalate-to-dodge-an-upstream-bug case; ordinary product decisions are unaffected.
- WHEN decision-interview locks a security-relevant invariant (an auth, biometric, session, or permission-boundary decision), it SHALL enumerate and confirm the behavior for at least 3 adjacent flows (logout, app backgrounding, force-quit/kill) before the decision is marked locked; a decision that only covers the flow it was asked about is incomplete.
- WHEN a decision-interview D-N entry proposes new complexity not explicitly requested by the user (a new mechanism, a new state, a new UI element), that entry SHALL include a one-line "Simplest alternative considered:" note before it can be locked, naming the simpler option and why the proposed complexity is needed instead. This applies only to self-proposed complexity increases, not to complexity the user themselves asked for.
- **Fact vs decision filter:** Before proposing a question, verify it is a genuine decision (two or more viable alternatives with different tradeoffs). Do not record pre-existing facts (e.g. "Stripe account exists", "stack is Next.js") or product-spec duplicates (e.g. "pricing is $20/month") as decisions. Facts belong in SOURCE_OF_TRUTH.md, not DECISIONS.md. A good test: if only one answer is reasonable given the existing codebase, spec, and constraints, it is a fact, not a decision.
- Ask only questions that materially affect:
  - correctness
  - runtime behavior
  - data integrity
  - test strategy
  - rollout safety
- Prefer targeted, binary, or tightly scoped questions.
- For each question:
  - explain why it matters
  - state what is already known
  - state what changes depending on the answer
- Separate:
  - decisions already safe to lock
  - remaining ambiguities that still need input
- Update `TASK_STATE.md` only when canonical decisions, blockers, risks, or next step materially change.
- If no material state change exists, state that `TASK_STATE.md` should remain unchanged and explain why.

DECISIONS.md entries MUST use EARS template (per ADR-0031). One of five canonical forms:
- Ubiquitous: `The <system> SHALL <response>`
- Event-driven: `WHEN <trigger> the <system> SHALL <response>`
- State-driven: `WHILE <state> the <system> SHALL <response>`
- Optional feature: `WHERE <feature included> the <system> SHALL <response>`
- Unwanted behavior: `IF <trigger> THEN the <system> SHALL <response>`

Free-form prose for decision rationale is OK; the canonical sentence per entry MUST use SHALL keyword. Banned softeners in canonical sentences: should, may, appropriate, sensible, reasonable. Rationale: pre-empts ambiguity at the entry point rather than letting `resolve-contract-gaps` catch it later.

Required output (interview mode, no LOCK picks in this turn):
1. Decisions already safe to lock (each locked decision phrased in EARS)
2. Remaining ambiguities
3. Targeted questions
4. Why each question matters
5. What implementation/test behavior changes depending on each answer
6. Exact TASK_STATE.md update block (PROPOSED), or explicit `TASK_STATE: NO_CHANGE`
7. Exact DECISIONS.md update block (PROPOSED) with EARS-shaped entries, or explicit "no DECISIONS.md changes needed"
8. Recommended next step
9. Recommended next command
10. Recommended editor mode
11. Why this is the correct next step
12. What should explicitly not be done yet

Required output (persist mode, LOCK picks present in this turn):
1. Acknowledgement listing which question IDs were locked and with which picks (one line per locked decision; no re-rationale).
2. Final DECISIONS.md content after this turn's writes (APPLIED in `### Artifact changes`).
3. Final TASK_STATE.md content after this turn's writes (APPLIED in `### Artifact changes`), with `Canonical decisions` reflecting the new locks.
4. `Remaining ambiguities` ONLY if some open questions were not covered by the lock signal; otherwise the section is omitted.
5. Recommended next step, next command, editor mode, and why (same as interview mode).
6. Do NOT re-emit the locked questions or their per-question rationale; the locks already happened.

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
- **Interview mode (no LOCK picks)**: Output has three explicit, separated sections: `Decisions already safe to lock`, `Remaining ambiguities`, and `Targeted questions`. Collapsing these into a single prose block is invalid output.
- **Persist mode (LOCK picks present)**: Output acknowledges the locked picks by ID + value, lists DECISIONS.md and TASK_STATE.md as `APPLIED` in `### Artifact changes`, and does NOT re-emit the locked questions or their rationale. Re-proposing already-locked decisions is invalid output.
- Each question (interview mode only) states explicitly: why it matters / what is already known / what changes depending on the answer. Question lists without per-question rationale are invalid output.
- No premature canonicalization: in interview mode, `DECISIONS.md` changes are PROPOSED only. In persist mode, the LOCK signal in the user input authorizes APPLIED.
- Clear separation between `PROPOSED` decisions vs locked decisions in interview mode; persist mode does not mix PROPOSED and APPLIED for the same decision.
- Output ends with a complete `### Handoff` block per the adaptive format in `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract`. A response that ends without a complete Handoff is invalid output.
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
Optimize for minimal question count, decision quality, and low ambiguity.

<!-- cache-breakpoint -->
