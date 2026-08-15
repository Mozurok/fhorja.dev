---
name: invariants-and-non-goals
description: |-
  Identify the invariants, non-goals, and forbidden changes for the active task, then persist them as INVARIANTS_AND_NON_GOALS.md so implementation boundaries are locked before planning or coding. Use when impact analysis is done or mostly clear, the task may touch sensitive behavior or contracts or schema or runtime paths, and implementation boundaries need to be locked before planning or coding. Do not use when the task is still too unclear to define safe boundaries, the current need is to ask missing factual questions first (use targeted-questions), or the task is already deep in implementation and boundaries are already locked.
metadata:
  category: discovery-and-scoping
  primary-cursor-mode: Ask
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
    - core
    - full
  provenance: first-party
  suggested-model: claude-sonnet-4-6
---

Act as a senior engineer defining change boundaries for the active engineering task.

Goal:
Identify the invariants, non-goals, and forbidden changes for the active task, then persist them in the task repository.

Mandatory context bootstrap (before any output):
<!-- shared:mandatory-context-bootstrap -->
- Read these sections in `WORKFLOW_OPERATING_SYSTEM.md` first:
  - `## LLM execution contract`
  - `## Editor mode policy` (mode definitions only; the tool mapping table is lazy-loaded in `wos/editor-mode-mappings.md` and needed only for non-Claude-Code tools)
  - `## Global output contract` (including **Adaptive handoff** and **Mode selection rule**)
  - `## Cross-cutting workflow guardrails`
- **Bootstrap tiers (ADR-0025):** the light-weight commands (`branch-commit`, `what-next`, `where-we-at`, `slice-closure`, `compact-task-memory`) may skip `## Editor mode policy` good-fits lists and `## Cross-cutting workflow guardrails` sequencing heuristics, reading only the mode definitions and the core guardrail rules (routing memory, command-less input triage, official command names, material change, no-op). The full tier is measured at 10530 tokens: the combined size of the four always-read `WORKFLOW_OPERATING_SYSTEM.md` sections listed above. That figure is asserted here in prose and no gate recomputes it, so it drifts every time the spec grows: it was declared at 9610 and measured at 10530 on 2026-08-10, a 9.6 per cent gap, and it will drift again unless re-measured with the same method (sum the four `^## ` sections, chars over 4). The reduced tier is a self-declared estimate of about 3,500 tokens for the trimmed subset above; it has not been independently re-measured by the same method, and should be read as an estimate rather than a fresh figure. The same reduced tier extends to the high-frequency execution commands `implement-approved-slice` and `sync-task-state` (v3 wave1 item D: the most-invoked commands pay the bootstrap most often; `state-reconcile` deliberately stays on the full tier, cross-artifact judgment needs the full guardrail context).
- **Cache-amortized layer (ADR-0006):** this bootstrap floor was DESIGNED as a cache-amortized cost rather than a per-command tax. ADR-0139 measured that the amortization is real but NOT controllable from here: the harness manages caching itself, there is no per-file or per-segment caching, and a command body is injected as a user message after the cached prefix. Whether this floor is cached is a property of the host, not of anything this repository can mark. Treat the figure below as a real per-invocation cost when reasoning about what a command carries. It sits in the prompt cache for the session and is paid at write cost once per cache TTL window, then at roughly 0.1x on cached reads inside that window. Account for it separately from any per-skill Load budget (the generated `.claude/skills/<name>/SKILL.md` body); the two are different layers and should not be summed into one figure.
- **Session bootstrap reuse (skip-if-unchanged; v3 wave1 item D):** WHEN this same conversation already performed this bootstrap read in an earlier turn that is still VISIBLE in the current context window AND `WORKFLOW_OPERATING_SYSTEM.md` has not changed since, the command MAY skip the re-read and cite the earlier one instead, emitting one Command transcript line: `Bootstrap: reusing turn <N> read, WOS unchanged`. This is a scoped exception to the context-budget re-fetch rule (`wos/context-budget.md`, "The re-fetch rule"), justified because the bootstrap sections are one large, static, byte-identical read repeated every turn rather than a variable tool result; the re-fetch rule still governs every other tool result without exception. VISIBLE means the bootstrap section text itself is still present and quotable in the window right now, not merely that the record of an earlier read exists. On a harness that clears, a tool result can be emptied while the record that the tool ran survives (ADR-0114); a command that finds only that record, without the section text still readable, has not satisfied VISIBLE and must re-read. Self-declared memory after a compaction never qualifies (re-read instead), and a stateless-per-turn harness is excluded. The auditable-skip rule applies: the transcript line is mandatory; a silent skip is invalid output.
- **Resolving a relative `wos/<topic>.md`.** Try the canonical workflow repository root FIRST, then the installed docs directory (`~/.claude/workflow-docs/wos/` or `~/.cursor/workflow-docs/wos/`). Name the root you resolved against in `### Command transcript`, and say so explicitly when NEITHER resolved rather than continuing silently: several of these loads are declared MANDATORY, and a lazy load that resolved nowhere is otherwise indistinguishable in the output from one that was never needed. Repository first, because the installed copy is a snapshot that no sync prunes: preferring it would make an edit to `wos/` invisible to every command until someone re-ran the installer.
- Read additional sections only when relevant to this command's role.
- Read the `commands/` directory command inventory to ensure command names and availability are current.
- Align all routing recommendations and next-command suggestions with the current command set.
- **Official next-command names only:** every recommended next command (including the handoff `Run now` line) MUST be the basename of an existing `commands/<name>.md` file in this workflow repository. Never invent names. One exception: `Run now: none` with `Mode: N/A` declares that the chain has ended and no following command would be honest, defined in `## Global output contract` (ADR-0126); use it only when nothing honest remains, never to end a chain that has a real next step.

Required inputs:
- active task folder path
- TASK_STATE.md
- SOURCE_OF_TRUTH.md
- IMPACT_ANALYSIS.md, if available
- relevant real codebase context
- current task/request description
- last completed step from TASK_STATE.md (command + summary)

Task repository files to create or update:
- INVARIANTS_AND_NON_GOALS.md
- TASK_STATE.md

Operating rules:
- Do not implement anything.
- **Handoff:** end with the adaptive `### Handoff` block per `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full).
- Do not assume undocumented business rules.
- Before producing output, verify whether boundaries are already sufficiently locked for the current scope.
- If invariants/non-goals already exist and no material boundary gap is present, do not rewrite artifacts just to rephrase; return a no-op and route to the best next command.
- No-op rule for artifacts:
  - If `INVARIANTS_AND_NON_GOALS.md` would not materially change, do not rewrite it.
  - If `TASK_STATE.md` would not materially change, do not rewrite it.
  - Still output a minimal NO_OP note for traceability, but keep it short.
- Identify:
  - external behavior that must remain unchanged
  - contracts that must be preserved
  - data assumptions that cannot be broken
  - modules that should not be touched unless strictly necessary
  - tempting but out-of-scope refactors to avoid
- If any invariant is uncertain and affects correctness, surface it as an open boundary question instead of guessing.
- Keep the output strict, concrete, and implementation-oriented.
- Prefer precise guardrails over broad commentary.
- Update `TASK_STATE.md` only when constraints/risks/next step materially change.
- If no material state change exists, state that `TASK_STATE.md` should remain unchanged and explain why.
- WHEN a locked decision in scope governs state that more than one flow reads or writes, cross-check it against this document's own adjacent-flow list when one exists, so `decision-interview`'s per-decision enumeration (bounded by the state, per ADR-0150) and this file's boundary list do not silently diverge; for a security invariant (auth, biometric, session, or permission-boundary) that list is at minimum logout, backgrounding, and force-quit/kill. This is a light pointer, not a duplicated mechanism.

INVARIANTS_AND_NON_GOALS.md must include:
1. Invariants
2. Non-goals
3. Forbidden changes
4. Risky temptations to avoid
5. Open boundary questions
6. Recommended next command
7. Recommended editor mode
8. Why that is the correct next step

TASK_STATE.md update must reflect:
- constraints / things that must not change
- risks to watch
- open questions / blockers, if any
- recommended next step

Required output:
1. Whether INVARIANTS_AND_NON_GOALS.md should be created or updated
2. Exact content for INVARIANTS_AND_NON_GOALS.md (full document if create/update; otherwise a short NO_OP note)
3. Exact TASK_STATE.md update block, or explicit `TASK_STATE: NO_CHANGE`
4. Recommended next command
5. Recommended editor mode
6. Why this is the correct next step
7. What should explicitly not be done yet

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
- Invariants are concrete and testable; boundary questions are explicit when uncertain.
- Non-goals prevent scope creep without smuggling new product requirements.
- `INVARIANTS_AND_NON_GOALS.md` is `PROPOSED` unless persisting in Agent mode; `TASK_STATE.md` follows the global write policy.
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
Optimize for strict boundaries, low ambiguity, and safe downstream planning.
