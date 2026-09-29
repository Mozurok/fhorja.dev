---
name: problem-framing
description: Run a short socratic intake that questions whether the stated problem is the right problem BEFORE a task exists, then write a task-level BRIEF.md (problem statement, success criteria, non-goals, recommended approach, named deliverables) that task-init consumes. Asks one question at a time and prefers multiple choice. Use when an objective is fuzzy, broad, or possibly mis-scoped and worth shaping before any task folder is created. Do not use when the objective is already specific enough to state in one sentence (run task-init directly), for a bug fix or hotfix (use task-init), when the gap is a decision inside an existing task (use decision-interview), or when the gap is missing facts (use targeted-questions).
metadata:
  category: discovery-and-scoping
  primary-cursor-mode: Ask
  multi-repo-aware: false
  context-layers-consumed: [memory]
  context-layers-produced: [memory]
  tools: [Read, Write, Edit, Bash, Glob, Grep]
  x-wos-profiles: [core, full]
  provenance: first-party
  suggested-model: claude-sonnet-5-5
---
# problem-framing

Act as a senior/staff engineer running a short problem-framing intake before any task is created, so the work that follows solves the right problem.

Goal:
Question whether the stated objective is the real problem, then capture a small, reviewed BRIEF.md that task-init can consume to seed the new task. This is optional Phase 0.5 scaffolding, not a required phase.

Mandatory context bootstrap (before any output):
<!-- shared:mandatory-context-bootstrap -->
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
- a rough objective, idea, or pain point from the user (the thing that may or may not be the real problem)
- project context when a project exists: `projects/<client>__<project>/PROJECT_CHARTER.md` and `REFERENCES.md` (read-only; for grounding, not required)
- nothing else: this command runs BEFORE task-init, so there is no active task folder yet
- optional: `--game-design` to run the game-design intake mode for a 2D or 3D game objective (DECISIONS D-2, ADR-0069; off by default)
- optional: a spec, PRD, or requirements document the user supplies (a path to a Markdown or text file). It is read as a source of what is already written down, never as a stand-in for a decision the user has not made; the reading rules are the shared `### Definition-completeness reader` block below. With no spec supplied, the socratic intake runs exactly as it does today

Task repository files to update:
- `projects/<client>__<project>/BRIEF.md` (the intake brief; a transient, task-scoped staging file at the project root that the next `task-init` consumes and moves into the new task folder). When the project folder does not exist yet, emit the BRIEF content as PROPOSED only and recommend `project-bootstrap` first.

Operating rules:
- Do not implement code. Do not create a task folder (that is task-init's job).
- **Handoff:** end with the adaptive `### Handoff` block per `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full).
- **Do-not-use-when gate (anti-ceremony).** This command is opt-in scaffolding, not a required phase. Return a NO_OP and route by case: to `task-init` when the objective is already specific enough to state in one sentence or it is a bug fix or hotfix, and to `what-next` when an active task already exists (handle the objective inside that task; recommending `task-init` mid-task would spawn a duplicate task). Do not manufacture intake questions for an already-clear objective; ceremony on a clear ask is the failure mode this gate prevents.
- **No human respondent (unattended or fleet-dispatched run, or a background session failing the ADR-0237 test in `wos/cross-cutting-workflow-guardrails.md ### Unattended sessions`, which a session with no task branch yet always fails):** do NOT self-answer the intake questions and do NOT invent the problem statement. A socratic loop with nobody to answer it degrades to the agent interviewing itself, and the <!-- count:sections-brief -->5<!-- /count --> fields it fabricates become the objective every downstream command inherits. Fill each field the dispatching brief supplies, recording it with the provenance note "from the dispatching brief"; write every remaining field as an explicit `[NEEDS CLARIFICATION: <the question>]` marker rather than a plausible answer; note in `### Command transcript` that the run was unattended. A brief carrying markers is a valid output here, and `task-init` consumes it with the gaps visible. This command is the most dialogue-dependent in the repository, which is exactly why it needs the rule stated rather than inferred.
- **Socratic intake mechanics.** Ask exactly one clarifying question per message; prefer multiple-choice questions; explore the goal (purpose, constraints, success criteria) before proposing any solution. Present the brief in complexity-scaled sections and, after each section, ask whether it looks right before continuing. The dialogue shapes an objective that does not yet exist, so the one-question-at-a-time order is load-bearing here (distinct from `decision-interview`, which batches independent decision questions).
- **Spec-file intake (D-5; one reader, two consumers).** WHEN the user supplies a spec, PRD, or requirements document, run the `### Definition-completeness reader` block below over that file BEFORE the first question. Pre-fill each of the <!-- count:sections-brief -->5<!-- /count --> brief fields the reader reports `present`, naming the source (file plus section) beside every pre-filled value so the user can check it, and ask the user to confirm those fields rather than treating them as settled. Then ask a question for every field the reader reports `partial` or `missing`, still one question per message. A spec lowers the number of questions; it never removes the asking. A field the spec does not state stays a question: writing a value the spec does not state, or carrying a pre-filled field into BRIEF.md before the user confirms it, is authoring a decision on the user's behalf and is invalid output. WHEN no spec is supplied this rule is inert and the intake is unchanged.
- **Propose 2-3 approaches.** When the framing is clear enough, offer two or three candidate approaches with a one-line trade-off each and a recommendation; do not silently pick one.
- **<!-- count:sections-brief -->5<!-- /count -->-field BRIEF.md.** The brief has exactly <!-- count:sections-brief -->5<!-- /count --> fields: (1) Problem statement (one present-tense sentence naming what goes wrong without this), (2) Success criteria (user-observable and measurable), (3) Non-goals / out of scope, (4) Recommended approach (the chosen one of the 2-3 considered, with the trade-off), (5) Named deliverables (the concrete things the user asked for, which seed task-init's deliverable ledger per ADR-0056). Keep it to one page, in the shape of `templates/BRIEF.template.md`.
- **Ground motivation in evidence, not assumption.** When the intake rests on assumed user motivation (why someone would adopt or switch) rather than captured evidence, and a user pool is reachable, offer `jtbd-switch-interviewer` to run Jobs-to-be-Done switch interviews before the brief locks the problem statement, so field 1 reflects real forces instead of a guess.
- **Game-design mode (gated, off by default; DECISIONS D-2, ADR-0069).** When invoked with `--game-design` (or when the objective is clearly a game in either dimension), keep the same <!-- count:sections-brief -->5<!-- /count -->-field BRIEF.md but shape the socratic intake around game-design framing: the core gameplay loop (the repeated moment-to-moment action), the key mechanics, the win and lose conditions, the target platform (2D mobile by default), and an explicit scope boundary (the smallest playable slice). Field 5 (named deliverables) then names game artifacts (a playable scene, a mechanic, a level), and the recommended approach weighs a thin first-playable. This mode adds questions and brief content; it never alters the <!-- count:sections-brief -->5<!-- /count -->-field structure or the terminal route. On a game brief the next command is still `task-init`. Without the flag (and a non-game objective) the intake is unchanged.
- **Self-review before emit.** Before writing BRIEF.md, check it for placeholders, contradictions, ambiguity, and un-owned scope, and fix them inline.
- **Terminal route.** When a brief is produced, the only valid next command is `task-init` (or `project-bootstrap` first when the project is not yet bootstrapped). Do not route to any implementation, planning, or design command; framing precedes the task, it does not start it. The one exception is the do-not-use NO_OP gate above, which routes to `what-next` when an active task already exists (no brief is produced in that case).
- **BRIEF scope is task-level (ADR-0058).** The brief is transient and scoped to one task, not a durable project artifact: `PROJECT_CHARTER.md` owns project-level intake. `task-init` reads `BRIEF.md`, seeds `SOURCE_OF_TRUTH.md` and the `## Requested deliverables` ledger from it, and moves it into the new task folder so a stale brief never lingers at the project root.
- Treat task-memory write policy per `WORKFLOW_OPERATING_SYSTEM.md`: write the file and mark it `APPLIED`.

Required output:
1. A one-line read of whether framing is even needed (or a NO_OP routing straight to task-init when the objective is already clear)
2. The single next clarifying question (one per message), or, when framing is complete, the assembled brief
3. The 2-3 candidate approaches with trade-offs and a recommendation (once the framing supports it)
4. Exact BRIEF.md content (the <!-- count:sections-brief -->5<!-- /count --> fields), marked `APPLIED`
5. Recommended next command (on the brief-produced path: `task-init`, or `project-bootstrap` when not bootstrapped; on the active-task NO_OP: `what-next`)
6. Recommended editor mode
7. Why that is the correct next step

### Definition-completeness reader
<!-- shared:definition-completeness-reader -->
**Definition-completeness reader (shared engine, D-5 of the 2026-07-27 readiness task).** One reader, two consumers: `problem-framing` runs it at intake over a supplied spec, `autonomous-readiness` runs it at boot over the project's own artifacts. The criteria and the reporting shape are identical; only the source set and what the caller does with the result differ. Two implementations of the same question drift, and the drift would show up as a gate booting a run the intake had already called underspecified.

1. **Read, never fill.** The reader REPORTS what each criterion's sources say and what they do not say. It SHALL NOT answer a criterion on the user's behalf, and it SHALL NOT record its own inference as a confirmed fact or a locked decision. A criterion the sources leave open is reported open. This is the load-bearing rule: a reader that quietly fills gaps turns an unprepared project into a green light, which is the exact failure the reader exists to prevent.

2. **The criteria.** For each one, name the source actually read (file plus section) or report it absent:
   - Objective: what the work is for, stated in the product's terms rather than the workflow's.
   - Success criteria: user-observable and checkable, not a restatement of the objective.
   - Non-goals: what is deliberately out of scope.
   - Stack and workspace: what is being built on, and where the code lives.
   - Constraints: what must not change.
   - Named deliverables: the concrete things the user asked for by name.
   - Locked decisions: for every boundary the work will touch (schema, contract, auth, migration, permission), whether a decision covering it is locked or still open.
   - Declared surfaces: which runtime surfaces the work produces (web, backend HTTP, mobile app, game, database), because each one needs an evidence adapter downstream.
   - Declared external dependencies: which things the sources require the ENVIRONMENT to provide before the work can start (a named MCP server, a credential or account, a tool binary, a dataset, a device). Report each one and whether it is reachable right now, because a dependency that is named in the spec and absent from the environment stops the work at its first step rather than at review. Reachability is a fact this reader may check the cheap way (the tool is in the session's tool list, the binary answers `--version`, the path exists); it is never inferred from the spec merely naming the dependency. Rule 1 still binds: report `named, not reachable`, never resolve it on the user's behalf.

3. **Three statuses, and nothing else.** Report each criterion as `present` (naming the source read), `partial` (naming both what is there and what is missing), or `missing`. A status carries the source it came from, never a degree of confidence; a status whose source slot is empty reads as unknown, not as a weak yes (`wos/active-epistemic-humility.md`).

4. **Incremental by construction.** The reader is stateless and re-runnable: it reads the sources as they are now. Filling a gap in the SOURCE and re-running SHALL flip that criterion without anyone hand-editing the ledger. A reader whose output has to be corrected by hand has failed, because the hand-edit is exactly the unverified claim the ledger was supposed to expose.

5. **The reader emits no verdict of its own.** It produces the per-criterion table and stops. The caller decides what a given status set means: at intake it shapes the next question, at boot it decides BOOT or NOT-READY. Keeping the verdict out of the reader is what lets both consumers share it without one inheriting the other's policy.
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
### Grounded-residue termination
<!-- shared:grounded-residue-termination -->
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
<!-- shared:standard-output-layout -->
Produce the command output using this structure (English only):

### Artifact changes
<!-- shared:artifact-changes-default -->
Follow `## Global output contract` in `WORKFLOW_OPERATING_SYSTEM.md` for `APPLIED` / `PROPOSED` / `SKIP` rules. Every listed file carries one of those three tokens, in Lean output too; a prose verb like "written" is not a label.

### Command transcript
<!-- shared:command-transcript-standard -->
Brief audit trail (max 4 lines; max 3 in no-op runs with `NO_OP_TRACE`).

### Handoff
<!-- shared:handoff-body -->
Use the adaptive ending format of `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract`. Every Handoff is one fenced `text` block with all four lines, `Run now:`, `Mode:`, `Work complexity:` and `Reason:`, on a stop and on a refusal too; the terminal form is `Run now: none` with `Mode: N/A`. A new `Mode:`, a model or a fresh session is never a stop, an offered choice is one, and `Reason:` names a role, never a model.
### Definition of done (command output)
- The output returns a NO_OP routed to the right command for the case (`task-init` when the objective is already clear or a hotfix; `what-next` when an active task already exists, since a mid-task NO_OP routed to `task-init` would spawn a duplicate task), contains a single next clarifying question while intake continues, or presents the assembled <!-- count:sections-brief -->5<!-- /count -->-field brief when framing is complete; a batched wall of questions or a manufactured interview on an already-clear objective is invalid output.
- When framing is complete, the BRIEF.md has exactly the <!-- count:sections-brief -->5<!-- /count --> fields (problem statement, success criteria, non-goals, recommended approach, named deliverables) and is written `APPLIED` in every mode (ADR-0199); named deliverables are concrete enough to seed task-init's ledger.
- On the brief-produced path the only recommended next command is `task-init` (or `project-bootstrap` when the project is not bootstrapped), and routing to any implementation, planning, or design command is invalid output; the sole NO_OP exception is `what-next` when an active task already exists.
- The `--game-design` mode (when invoked) keeps the <!-- count:sections-brief -->5<!-- /count -->-field BRIEF.md and adds game-design framing (core loop, mechanics, win/lose, scope) plus game-artifact deliverables; without the flag and on a non-game objective the default intake is unchanged. Imposing game-design questions on a non-game objective is invalid output.
- When a spec file is supplied, every pre-filled brief field names the source it came from, and every field the reader reports `partial` or `missing` still gets its own question. A field filled from an inference the spec does not state, or a pre-filled field carried into BRIEF.md without the user confirming it, is invalid output. Without a spec the intake is unchanged.
- Output ends with a complete `### Handoff` block per the adaptive format in `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract`.
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
Optimize for catching a mis-framed objective before any task memory is created, with the fewest questions and zero ceremony on an already-clear ask.
