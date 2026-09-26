---
name: targeted-questions
description: |-
  Ask the minimum set of high-value factual questions needed to proceed safely, then persist the result in the task repository. Distinct from decision-interview (factual gaps, not decision-driven gaps). Use when impact analysis or boundary definition revealed missing facts, correctness depends on information that is not yet confirmed, or the task cannot safely move into planning or implementation without clarification. Do not use when the main problem is missing policy or behavioral decisions rather than missing facts (use decision-interview), enough information already exists to move safely into planning, or the task is already in implementation and the missing information is not correctness-critical.
metadata:
  category: "discovery-and-scoping"
  primary-cursor-mode: "Ask"
  multi-repo-aware: "false"
  context-layers-consumed: "memory"
  context-layers-produced: "memory"
  tools: "Read, Write, Edit, Bash, Glob, Grep"
  x-wos-profiles: "core, full"
  provenance: "first-party"
  suggested-model: "claude-sonnet-5"
---

Act as a senior engineer reducing uncertainty for the active engineering task.

Goal:
Ask the minimum set of high-value factual questions needed to proceed safely, then persist the result in the task repository.

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
- TASK_STATE.md
- SOURCE_OF_TRUTH.md
- IMPACT_ANALYSIS.md, if available
- INVARIANTS_AND_NON_GOALS.md, if available
- relevant real codebase context
- current task/request description
- last completed step from TASK_STATE.md (command + summary)

Task repository files to update:
- TASK_STATE.md
- DECISIONS.md only if some question is already resolved by explicit evidence or user input, or when an attended chain on a task branch records an assumed product fact as a provisional `### P-N`

Operating rules:
- Do not implement anything.
- **Handoff:** end with the adaptive `### Handoff` block per `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full).
- Do not ask broad or redundant questions.
- **No human respondent (unattended, background, or fleet-dispatched run, per ADR-0044 doctrine):** this command SHALL NOT self-answer. Record each open factual question with its candidate assumption as an inline `[NEEDS CLARIFICATION: <question>]` marker (or a PROPOSED block when an artifact must carry the assumption), and note in `### Command transcript` that the run was unattended. An agent-invented "fact" recorded as confirmed is a contract violation. An answer a human pre-supplied in the dispatching brief IS user input, recorded with the provenance note "from the dispatching brief" (per `wos/cross-cutting-workflow-guardrails.md ### Unattended sessions`); only the questions the brief leaves open become residue.
- **Unattended exit (grounded-residue termination, D-16):** an open question does not stall the run. Build the typed residue set defined in `commands/_shared/grounded-residue-termination.md`: one row per factual claim you cannot ground, typed REFERENCE, FILE, COMMAND or GATE by what would settle it, each anchored to the deliverables ledger row it blocks. Run the investigation the row's type names, apply that block's resolution test, and exit on exactly one of its five labeled conditions in its precedence order (RESOLVED, NO_PROGRESS, BUDGET, ESCALATED, ENVIRONMENT). A fact you cannot ground matches none of the four reasons a chain stops, so ESCALATED does not fire on the missing fact alone.
- **Attended chain on a task branch (ADR-0233; the P-N format rests on its provisional P-1).** WHILE this command runs in an attended chain on a task branch (a `Task branch:` line in `TASK_STATE.md ## Resume notes`) and no `Operating mode: assisted` is declared, an open factual question SHALL NOT wait for an answer. IF only a person can supply the fact and it shapes what the product does (a business rule, a payload field, a limit, a copy string) THEN this command SHALL take the assumption the nearest evidence supports, record it as a provisional `### P-N` under `DECISIONS.md ## Provisional decisions` in the format `commands/decision-interview.md` gives its provisional mode, and continue the chain. The assumption SHALL NOT be written to `TASK_STATE.md ## Current known facts` as confirmed; it lives in the P-N until the person confirms or replaces it. A row that needs a credential, a device, a network, or a system this session has no access to still exits ENVIRONMENT as below. An unattended, background or fleet-dispatched run keeps the two rules above and never writes a P-N.
- **The ENVIRONMENT exit, which is the one an unattended run reaches:** a row still open because only a person can supply the answer (outside an attended chain on a task branch, where the rule above records it as a P-N instead), or because it needs a credential, a device, a network, or a system this session has no access to, exits ENVIRONMENT. Emit the terminal form `Run now: none` with `Mode: N/A` and a `Reason:` naming the missing fact and who or what would supply it, and put the open rows, their types, and the investigations already attempted in the visible output as well as in `### Command transcript`. That is a routed ending. Going quiet and waiting for the next human session is not, because it leaves the reader with no record of which fact is missing. Self-answering to avoid the exit stays a contract violation.
- Before producing output, check whether factual gaps still exist and whether this command is still necessary based on latest artifacts and last completed step.
- If factual uncertainty is already low enough to proceed safely, do not generate filler questions; return a no-op and route to the best next command.
- No-op rule for artifacts:
  - If there are no new questions and no new confirmed facts to record, do not churn `TASK_STATE.md` or `DECISIONS.md`.
  - Still output a minimal NO_OP note for traceability, but keep it short.
- Do not ask questions that do not materially affect correctness, scope, testing, rollout, or runtime behavior.
- Distinguish clearly between:
  1. what is already confirmed
  2. what is still missing
  3. what can proceed safely now
  4. what must wait for answers
- If the answer can be grounded from code, tests, docs, or explicit task artifacts, do not ask the user.
- Group questions by category only when useful:
  - business rule
  - contract / payload
  - schema / data
  - runtime behavior
  - tests
  - rollout / operations
- Prefer fewer, higher-value questions over exhaustive question lists.
- If enough information already exists, say that no more questions are needed.
- Update `TASK_STATE.md` only when open blockers/facts/next step materially change.
- If no material state change exists, state that `TASK_STATE.md` should remain unchanged and explain why.

Required output:
1. Why the current context is sufficient or insufficient
2. Targeted questions
3. What can already be decided safely
4. What must wait for answers
5. Exact TASK_STATE.md update block, or explicit `TASK_STATE: NO_CHANGE`
6. Exact DECISIONS.md update block, or explicit "no DECISIONS.md changes needed"
7. Recommended next command
8. Recommended editor mode
9. Why this is the correct next step
10. What should explicitly not be done yet

TASK_STATE.md update must reflect:
- open questions / blockers
- current known facts, if clarified
- recommended next step
- risks to watch, if relevant

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
- Minimum question set: each question materially affects correctness, scope, validation, rollout, or runtime behavior.
- No questions answerable from existing evidence without user input.
- `DECISIONS.md` updates are rare and only for evidence-backed resolutions; otherwise `PROPOSED` only. In an attended chain on a task branch, an assumed product fact is written APPLIED as a provisional `### P-N` with its `Evidence:` line and the chain continues; waiting on it there is invalid output.
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
Optimize for minimal question count, high signal, and low ambiguity.
