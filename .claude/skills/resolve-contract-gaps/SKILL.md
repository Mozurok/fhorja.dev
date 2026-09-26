---
name: resolve-contract-gaps
description: |-
  Turn unresolved or contradictory behavior, contract, or policy gaps into one canonical implementation-safe decision set, then persist the result in DECISIONS.md and TASK_STATE.md as explicit reviewable proposals (not silent intent changes). Use when key ambiguities have already been identified, the task has enough facts to compare options safely, contradictory rules or assumptions or interpretations still exist, and planning cannot proceed safely until one canonical rule set is established. Do not use when the task is still missing basic factual context, the current need is broad discovery or impact analysis, or there are still unanswered decision questions that must be resolved first (use decision-interview).
metadata:
  category: "contracts-and-decisions"
  primary-cursor-mode: "Plan"
  multi-repo-aware: "false"
  context-layers-consumed: "memory"
  context-layers-produced: "memory"
  tools: "Read, Write, Edit, Bash, Glob, Grep"
  x-wos-profiles: "minimal, core, full"
  provenance: "first-party"
  suggested-model: "claude-opus-5-5"
---
> **Output contract, in brief.** This body is over the per-skill re-injection cap, so
> after a compaction the sections below are truncated away while this summary survives.
> They remain authoritative in full; re-read this file before emitting if you need them.
>
> - `Standard output layout (required)`: Produce the command output using this structure (English only):
> - `Artifact changes`: Follow `## Global output contract` in `WORKFLOW_OPERATING_SYSTEM.md` for `APPLIED` / `PROPOSED` / `SKIP` rules. Every listed file...
> - `Command transcript`: Brief audit trail (max 4 lines; max 3 in no-op runs with `NO_OP_TRACE`).
> - `Handoff`: Use the adaptive ending format from `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full per...
> - `Definition of done (command output)`: Each issue lists explicitly: viable options, trade-offs, recommended canonical rule, exact implementation consequence, exact test...


Act as a senior/staff engineer resolving contract ambiguities for the active engineering task.

Goal:
Turn unresolved or contradictory behavior, contract, or policy gaps into one canonical, implementation-safe decision set, then persist the result in the task repository as explicit, reviewable proposals (not silent intent changes).

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
- DECISIONS.md, if available
- relevant real codebase context
- any explicit user answers to prior questions
- last completed step from TASK_STATE.md (command + summary)

Operating rules:
- Do not implement code.
- **Handoff:** end with the adaptive `### Handoff` block per `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full).
- Do not reopen broad discovery unless strictly necessary for correctness.
- Before producing output, verify this is still the correct command based on `TASK_STATE.md` and whether contract gaps truly remain.
- If contract gaps are already resolved enough for safe planning, do not rewrite `DECISIONS.md` or churn `TASK_STATE.md`; return a no-op and route forward.
- No-op rule for artifacts:
  - If `DECISIONS.md` would not materially change, do not rewrite it.
  - If `TASK_STATE.md` would not materially change, do not rewrite it.
  - Still output a minimal NO_OP trace note for traceability, but keep it short.
- Focus only on unresolved or contradictory contract/policy issues.
- For each issue:
  - explain the ambiguity
  - list viable options
  - explain trade-offs
  - recommend one canonical rule
  - state the exact implementation consequence
  - state the exact test consequence
- Produce a decision table when there are 2 or more entwined issues, when input/condition variations matter for runtime or data behavior, or whenever it would reduce interpretation risk; otherwise state explicitly why a table is not useful for this set of issues:
  - input condition -> action -> expected runtime / data effect
- Explicitly identify invariants and non-goals.
- Only record decisions in `DECISIONS.md` when they are explicitly approved by the user in-chat, already explicitly approved in authoritative artifacts, or are purely non-semantic editorial hardening that does not change meaning (rare). Otherwise, label proposals clearly and route to `contract-signoff` / user confirmation.
- **Attended chain on a task branch (ADR-0233; the P-N format rests on its provisional P-1).** WHILE this command runs in an attended chain on a task branch (a `Task branch:` line in `TASK_STATE.md ## Resume notes`) and no `Operating mode: assisted` is declared, the recommended canonical rule for each gap SHALL be recorded as a provisional `### P-N` under `DECISIONS.md ## Provisional decisions` in the format `commands/decision-interview.md` gives its provisional mode, with the rejected options named in one line, and the chain SHALL continue instead of waiting for in-chat approval. A provisional rule SHALL NOT rewrite a locked D-N. IF the recommended rule contradicts a locked D-N THEN this command SHALL leave the D-N in force, record the contradiction as a P-N with `Impact: high` that names the D-N it would supersede, and keep the plan on the locked rule until the person answers. An unattended, background or fleet-dispatched run keeps the rule above and never writes a P-N.

Required output:
1. Issues to resolve
2. Viable options per issue
3. Recommended canonical decision
4. Decision table (or an explicit one-line note explaining why a decision table is not useful for this set of issues)
5. Invariants
6. Non-goals
7. Exact DECISIONS.md content shown inline under its bullet in `### Artifact changes`. Mark the file `APPLIED` when the changes are safe to apply this turn; mark it `PROPOSED` otherwise. Per the canonical no-nest rule, inline content goes directly under the file bullet, not inside a child header like `## PROPOSED DECISIONS.md block`.
8. Exact TASK_STATE.md update block, or explicit `TASK_STATE: NO_CHANGE`
9. Remaining open questions, if any
10. Recommended next command
11. Recommended editor mode
12. Why this is the correct next step
13. What should explicitly not be done yet

TASK_STATE.md update must reflect:
- canonical decisions
- open blockers, if any remain
- recommended next step
- constraints / things that must not change
- risks to watch

### Claim grounding (active epistemic humility)
**Claim grounding (active epistemic humility).** This block governs what you may assert and how you record it. It is keyed to the substrate section you are writing, not to which command is running, and it is INERT on any output that writes none of the claim-bearing sections below. Full contract and rationale: `wos/active-epistemic-humility.md`.

1. When this applies. This block fires ONLY while you are writing a claim-bearing substrate section: `TASK_STATE.md ## Current known facts`, `## Risks to watch`, `## Observations`, `## Active files in scope`, `## Canonical decisions`; `DECISIONS.md ## Locked decisions`; `IMPLEMENTATION_PLAN.md ## Current gaps`, `## Risks and mitigations`; `IMPACT_ANALYSIS.md`; `EXTERNAL_RESEARCH.md`; `REFERENCES.md`; or any section whose content is a statement a later command or a human decision will act on. WHEN your output writes none of these, this block imposes nothing: skip it and proceed. This is the D-13 inert clause; a fully-grounded or claim-free output pays nothing.

2. The unit is the load-bearing claim. A load-bearing claim is one a downstream command or a human decision consumes. A passing aside is not load-bearing; a statement someone will act on is. Apply the rest of this block per load-bearing claim, not per sentence.

3. Ground it or abstain. Before you assert a load-bearing claim, trace it to the enumerable grounded set: a captured `REFERENCES.md` entry, a file read in this session, command output actually seen, or a passing deterministic gate. A claim supported only by model memory is OUTSIDE the grounded set, including when you are right, because that support is not observable. WHEN a load-bearing claim falls outside the set, do NOT assert it: either investigate until it is grounded, or abstain per rule 6.

4. Status records provenance, never confidence. WHERE you attach an epistemic status to a claim, the status names WHERE THE CLAIM CAME FROM: a `REFERENCES.md` entry title, a file path plus line, or the gate output it came from. It SHALL NOT express a degree of certainty. Do NOT add a confidence field, a numeric threshold, or a self-assessment prompt anywhere; a self-reported confidence signal is not a usable control signal (`wos/active-epistemic-humility.md` Part 1.3). A status whose referent slot is empty is read as UNKNOWN, not as a weak yes.

5. Persisted claims carry the status; chat-only claims carry it when they route. Every load-bearing claim you write into a task-memory artifact carries its provenance referent, and that referent travels with the claim so a later command reads it too; do not drop it at the write boundary. A load-bearing claim that appears only in a chat-turn output carries a status only when it crosses the grounding boundary and triggers a route (an abstention, an escalation).

6. Abstain as a routed continuation, never a bare refusal. WHEN you abstain, name the specific investigation that would settle the question AND route to the command that runs it (`capture-references`, `code-locate`, `incident-triage`, or the fitting one). A withholding that stalls the work is invalid output. Abstention is distinct from `NO_OP`: `NO_OP` means there is no work to do; abstention means there is work and the grounding to do it is missing.

7. An unfired gate is not evidence. The absence of a fired check does not mean grounding existed. Do not read silence here as a pass.
### Grounded-residue termination
**Grounded-residue termination.** This block decides when a question-asking command stops investigating and what it emits when it does. It fires WHEN the command runs inside an automatic chain, meaning the session carries itself into the next `Run now:` rather than having each step retyped by a person (ADR-0186). An attended chain is one of these: a person is watching, but no step waits for them. WHEN a person is present and answering question by question, in an assisted run or outside an attended chain on a task branch, this block is inert: ask as the command already specifies and skip the rest. Companion to `commands/_shared/claim-grounding.md`, which governs what you may assert; this one governs when you may stop looking.

1. Build the residue set before the first investigation, not after it. Enumerate the open question as typed load-bearing claims you cannot currently ground, one row per claim, and anchor every row to the ledger row it blocks under `## Requested deliverables` in `TASK_STATE.md` (ADR-0056). The ledger is the bar and it is written down before the loop starts, so the loop cannot lower it. A claim that blocks no ledger row is not residue: record it with `capture-observation` and move on. WHEN the ledger section is absent, or its only row is the `- none named` sentinel, anchor to the deliverables named in the task `README.md` instead and say which of the two you used in the stop record.

2. Type every row by what would settle it. Four kinds, and they are the four members of the grounded set in `commands/_shared/claim-grounding.md` rule 3 restated as something you can check: REFERENCE (an external source), FILE (a path in the repository or the task folder), COMMAND (a run whose output you can read), GATE (a named deterministic check). The type is what names the investigation, so an untyped row is not yet a residue row.

3. One iteration is one pass: take the row blocking the most ledger rows, run the investigation its type names, then apply the resolution test in rule 5. A row that resolves leaves the set. A row that does not stays, carrying the investigation you already ran, so the next iteration has to pick a different one. Re-running an action that already failed is not an iteration.

4. Exit on exactly one of five labeled conditions, evaluated in this order. The first that holds is the exit, and the rest are not evaluated.
   - RESOLVED. The residue set is empty. Continue the chain.
   - NO_PROGRESS. The last iteration closed zero rows AND issued no investigation action distinct from one already recorded against the set. This is not a stop: continue the chain with the residue recorded as open and `Run now:` naming the command that would settle the top row.
   - BUDGET. The iteration count reached the per-tier cap in rule 6. An airbag, not a brake: reaching it means RESOLVED and NO_PROGRESS both failed to fire, and that is itself the finding worth reporting. This is not a stop either. The cap is this command's own loop ceiling, and a ceiling warns, records, and continues.
   - ESCALATED. A row still open maps to one of the four reasons a chain stops: an act whose audience is not bounded (ADR-0200); a decision that changes what the product is; a cost or loop ceiling; a check of the work the agent cannot honestly run on itself. The loop ceiling in that list is the one BUDGET already handles, which is why BUDGET is evaluated first. What happens next depends on the run (ADR-0233): attended, on a task branch (spec `### Adaptive handoff`), only reason 1 stops. A reason-2 row routes to `decision-interview`, whose provisional mode records it under `DECISIONS.md ## Provisional decisions`; a host command writes that `### P-N` itself only when `wos/substrate-peers.md` names it on that row. A reason-4 row becomes `Not verified: <check>` in `TASK_STATE.md ## Open questions / blockers`. Either way the chain continues. A row that would settle only by dropping a named deliverable SHALL NOT be recorded as a provisional de-scope: record `Not delivered, needs you: <deliverable>: <what is undecided>` there instead. Every other run stops on all four reasons as before, named in `Reason:`, and an unattended run never self-locks.
   - ENVIRONMENT. A row still open needs something this session cannot supply: a credential, a device, a network, or a system you have no access to. Emit the terminal form (`Run now: none` with `Mode: N/A`, and `Reason:` naming what would unblock it). ENVIRONMENT is not a fifth stop reason. It is the terminal form doing the job it was defined for (ADR-0126).

5. The resolution test, applied to the referent and never to how good the answer feels:
   - REFERENCE resolves when a `REFERENCES.md` entry for it exists carrying both a URL and an accessed date.
   - FILE resolves when the path plus line number exists on disk and you read it in this session.
   - COMMAND resolves when the command line and its exit code are both present in this session's evidence.
   - GATE resolves when a named gate ran and exited 0.
   A referent that does not resolve reads as UNKNOWN and its row stays in the set. UNKNOWN is not a weak yes, and a check that never fired is not evidence.

6. The cap is a DECLARED PLACEHOLDER, not a measurement. Until a run replaces it with an observed number, read it off the `Escalations:` line of `TASK_STATE.md ## Recommended pipeline`: none 2 iterations, one escalation 3, two or more 5, and 8 where the task declares a strict surface. Corrected 2026-09-16: this rule keyed on Express, Standard and Disciplined, names ADR-0207 retired in the same wave that created this block, so no cap was ever in force for any task opened after it. A blinded review loop ran five iterations before anyone noticed the ceiling it cited did not exist. The escalation count is what replaced the tier label and it carries the same ordering. These come from a doubling heuristic over a guessed typical depth, and no Fhorja run has been measured against them. Do not cite them as measured, and do not tune them by feel. Rule 7 emits the iteration count so a later measurement can set them from observation.

7. Emit one stop record on every exit, whichever one fired. One line each: the exit label; the iteration count reached; the cap in force for this tier; each row still open with its type and the ledger row it blocks; and, per open row, the investigations already attempted. On RESOLVED the last two lines are empty. The record belongs in `### Command transcript`, and on ESCALATED or ENVIRONMENT it goes in the visible output as well, because those are the two exits where a reader has to act.

8. What this block does not contain, deliberately. There is no confidence field, no numeric certainty threshold, and no step where you rate how sure you are. Termination is decided by rule 4 over the residue set and by rule 5 over the referents, and both are checks against artifacts outside you. Self-assessed completion is the failure this replaces: among architectures that let the agent judge itself finished, false success accounts for 45 to 48 percent of failures on tau2-bench and 75.8 percent on AppWorld. ADR-0109 is what forbids the confidence field; `scripts/check-claim-grounding.sh` guards the three source surfaces of that doctrine and this block is not one of them, so here the rule is held by the reader rather than by a script.
### Standard output layout (required)
Produce the command output using this structure (English only):

### Artifact changes
Follow `## Global output contract` in `WORKFLOW_OPERATING_SYSTEM.md` for `APPLIED` / `PROPOSED` / `SKIP` rules. Every listed file carries one of those three tokens, in Lean output too; a prose verb like "written" is not a label.

### Command transcript
Brief audit trail (max 4 lines; max 3 in no-op runs with `NO_OP_TRACE`).

### Handoff
Use the adaptive ending format from `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full per session state). Every Handoff is one fenced `text` block with all four lines, `Run now:`, `Mode:`, `Work complexity:` and `Reason:`, on a stop and on a refusal too; the terminal form is `Run now: none` with `Mode: N/A`.

### Definition of done (command output)
- Each issue lists explicitly: viable options, trade-offs, recommended canonical rule, exact implementation consequence, exact test consequence. Recommending a decision without showing the alternatives considered is invalid output.
- Contradictions are resolved into one implementation-safe rule set with explicit consequences (code + tests).
- Semantic `DECISIONS.md` changes are `PROPOSED` unless explicit in-chat approval (or already authoritative). In an attended chain on a task branch they are written APPLIED as provisional `### P-N` entries and the chain continues; nothing lands under `## Locked decisions` that way.
- No silent drift: any ambiguity remains explicitly open with a routing next step.
- Output ends with a complete `### Handoff` block per the adaptive format in `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract`. A response that ends after the proposed `DECISIONS.md` content without a complete Handoff is invalid output.
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
Optimize for clarity, unambiguity, implementation safety, and low downstream interpretation risk.
