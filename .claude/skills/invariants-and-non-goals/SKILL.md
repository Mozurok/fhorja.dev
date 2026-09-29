---
name: invariants-and-non-goals
description: |-
  Identify the invariants, non-goals, and forbidden changes for the active task, then persist them as INVARIANTS_AND_NON_GOALS.md so implementation boundaries are locked before planning or coding. Use when impact analysis is done or mostly clear, the task may touch sensitive behavior or contracts or schema or runtime paths, and implementation boundaries need to be locked before planning or coding. Do not use when the task is still too unclear to define safe boundaries, the current need is to ask missing factual questions first (use targeted-questions), or the task is already deep in implementation and boundaries are already locked.
metadata:
  category: "contracts-and-decisions"
  primary-cursor-mode: "Ask"
  multi-repo-aware: "false"
  context-layers-consumed: "memory"
  context-layers-produced: "memory"
  tools: "Read, Write, Edit, Bash, Glob, Grep"
  x-wos-profiles: "core, full"
  provenance: "first-party"
  suggested-model: "claude-sonnet-5-5"
---

Act as a senior engineer defining change boundaries for the active engineering task.

Goal:
Identify the invariants, non-goals, and forbidden changes for the active task, then persist them in the task repository.

Mandatory context bootstrap (before any output):
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
Use the adaptive ending format of `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract`. Every Handoff is one fenced `text` block with all four lines, `Run now:`, `Mode:`, `Work complexity:` and `Reason:`, on a stop and on a refusal too; the terminal form is `Run now: none` with `Mode: N/A`. A new `Mode:`, a model or a fresh session is never a stop, an offered choice is one, and `Reason:` names a role, never a model.
### Definition of done (command output)
- Invariants are concrete and testable; boundary questions are explicit when uncertain.
- Non-goals prevent scope creep without smuggling new product requirements.
- `INVARIANTS_AND_NON_GOALS.md` is `APPLIED`; `TASK_STATE.md` follows the global write policy.
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
Optimize for strict boundaries, low ambiguity, and safe downstream planning.
