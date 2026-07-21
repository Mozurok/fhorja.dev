---
name: problem-framing
description: Run a short socratic intake that questions whether the stated problem is the right problem BEFORE a task exists, then write a task-level BRIEF.md (problem statement, success criteria, non-goals, recommended approach from 2-3 considered, named deliverables) that task-init consumes. Asks one question at a time, prefers multiple choice, and on producing a brief routes only to task-init. Use when an objective is fuzzy, broad, or possibly mis-scoped and worth shaping before any task folder is created. Do not use when the objective is already specific enough to state in one sentence (run task-init directly), for a bug fix or hotfix (use incident-triage or task-init), when the gap is a decision inside an existing task (use decision-interview), when the gap is missing facts (use targeted-questions), or when an active task already exists (the brief belongs at intake, not mid-task). A gated --game-design mode (ADR-0069) frames a 2D-game intake into the same five-field brief, off by default.
metadata:
  category: discovery-and-scoping
  primary-cursor-mode: Ask
  multi-repo-aware: false
  context-layers-consumed: [memory]
  context-layers-produced: [memory]
  tools: [Read, Write, Edit, Bash, Glob, Grep]
  x-wos-profiles: [core, full]
  provenance: first-party
  token-budget: 2800
  suggested-model: claude-sonnet-4-6
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
- **Bootstrap tiers (ADR-0025):** the light-weight commands (`branch-commit`, `what-next`, `where-we-at`, `slice-closure`, `compact-task-memory`) may skip `## Editor mode policy` good-fits lists and `## Cross-cutting workflow guardrails` sequencing heuristics, reading only the mode definitions and the core guardrail rules (routing memory, command-less input triage, official command names, material change, no-op). This reduces bootstrap from ~6,750 to ~3,500 tokens for these commands. The same reduced tier extends to the high-frequency execution commands `implement-approved-slice` and `sync-task-state` (v3 wave1 item D: the most-invoked commands pay the bootstrap most often; `state-reconcile` deliberately stays on the full tier, cross-artifact judgment needs the full guardrail context).
- **Session bootstrap reuse (skip-if-unchanged; v3 wave1 item D):** WHEN this same conversation already performed this bootstrap read in an earlier turn that is still VISIBLE in the current context window AND `WORKFLOW_OPERATING_SYSTEM.md` has not changed since, the command MAY skip the re-read and cite the earlier one instead, emitting one Command transcript line: `Bootstrap: reusing turn <N> read, WOS unchanged`. Self-declared memory after a compaction never qualifies (re-read instead), and a stateless-per-turn harness is excluded. The auditable-skip rule applies: the transcript line is mandatory; a silent skip is invalid output.
- Read additional sections only when relevant to this command's role.
- Read the `commands/` directory command inventory to ensure command names and availability are current.
- Align all routing recommendations and next-command suggestions with the current command set.
- **Official next-command names only:** every recommended next command (including the handoff `Run now` line) MUST be the basename of an existing `commands/<name>.md` file in this workflow repository. Never invent names.

Required inputs:
- a rough objective, idea, or pain point from the user (the thing that may or may not be the real problem)
- project context when a project exists: `projects/<client>__<project>/PROJECT_CHARTER.md` and `REFERENCES.md` (read-only; for grounding, not required)
- nothing else: this command runs BEFORE task-init, so there is no active task folder yet
- optional: `--game-design` to run the game-design intake mode for a 2D game objective (DECISIONS D-2, ADR-0069; off by default)

Task repository files to update:
- `projects/<client>__<project>/BRIEF.md` (the intake brief; a transient, task-scoped staging file at the project root that the next `task-init` consumes and moves into the new task folder). When the project folder does not exist yet, emit the BRIEF content as PROPOSED only and recommend `project-bootstrap` first.

Operating rules:
- Do not implement code. Do not create a task folder (that is task-init's job).
- **Handoff:** end with the adaptive `### Handoff` block per `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full).
- **Do-not-use-when gate (anti-ceremony).** This command is opt-in scaffolding, not a required phase. Return a NO_OP and route by case: to `task-init` when the objective is already specific enough to state in one sentence or it is a bug fix or hotfix, and to `what-next` when an active task already exists (handle the objective inside that task; recommending `task-init` mid-task would spawn a duplicate task). Do not manufacture intake questions for an already-clear objective; ceremony on a clear ask is the failure mode this gate prevents.
- **Socratic intake mechanics.** Ask exactly one clarifying question per message; prefer multiple-choice questions; explore the goal (purpose, constraints, success criteria) before proposing any solution. Present the brief in complexity-scaled sections and, after each section, ask whether it looks right before continuing. The dialogue shapes an objective that does not yet exist, so the one-question-at-a-time order is load-bearing here (distinct from `decision-interview`, which batches independent decision questions).
- **Propose 2-3 approaches.** When the framing is clear enough, offer two or three candidate approaches with a one-line trade-off each and a recommendation; do not silently pick one.
- **Five-field BRIEF.md.** The brief has exactly five fields: (1) Problem statement (one present-tense sentence naming what goes wrong without this), (2) Success criteria (user-observable and measurable), (3) Non-goals / out of scope, (4) Recommended approach (the chosen one of the 2-3 considered, with the trade-off), (5) Named deliverables (the concrete things the user asked for, which seed task-init's deliverable ledger per ADR-0056). Keep it to one page.
- **Ground motivation in evidence, not assumption.** When the intake rests on assumed user motivation (why someone would adopt or switch) rather than captured evidence, and a user pool is reachable, offer `jtbd-switch-interviewer` to run Jobs-to-be-Done switch interviews before the brief locks the problem statement, so field 1 reflects real forces instead of a guess.
- **Game-design mode (gated, off by default; DECISIONS D-2, ADR-0069).** When invoked with `--game-design` (or when the objective is clearly a 2D game), keep the same five-field BRIEF.md but shape the socratic intake around game-design framing: the core gameplay loop (the repeated moment-to-moment action), the key mechanics, the win and lose conditions, the target platform (2D mobile by default), and an explicit scope boundary (the smallest playable slice). Field 5 (named deliverables) then names game artifacts (a playable scene, a mechanic, a level), and the recommended approach weighs a thin first-playable. This mode adds questions and brief content; it never alters the five-field structure or the terminal route. On a game brief the next command is still `task-init`, which then routes to `godot-scene-plan` for the scene architecture (Godot 2D-mobile cluster, ADR-0069). Without the flag (and a non-game objective) the intake is unchanged.
- **Self-review before emit.** Before writing BRIEF.md, check it for placeholders, contradictions, ambiguity, and un-owned scope, and fix them inline.
- **Terminal route.** When a brief is produced, the only valid next command is `task-init` (or `project-bootstrap` first when the project is not yet bootstrapped). Do not route to any implementation, planning, or design command; framing precedes the task, it does not start it. The one exception is the do-not-use NO_OP gate above, which routes to `what-next` when an active task already exists (no brief is produced in that case).
- **BRIEF scope is task-level (ADR-0058).** The brief is transient and scoped to one task, not a durable project artifact: `PROJECT_CHARTER.md` owns project-level intake. `task-init` reads `BRIEF.md`, seeds `SOURCE_OF_TRUTH.md` and the `## Requested deliverables` ledger from it, and moves it into the new task folder so a stale brief never lingers at the project root.
- Treat task-memory write policy per `WORKFLOW_OPERATING_SYSTEM.md`: `PROPOSED` in Ask mode, `APPLIED` only in Agent mode.

Required output:
1. A one-line read of whether framing is even needed (or a NO_OP routing straight to task-init when the objective is already clear)
2. The single next clarifying question (one per message), or, when framing is complete, the assembled brief
3. The 2-3 candidate approaches with trade-offs and a recommendation (once the framing supports it)
4. Exact BRIEF.md content (the five fields), marked PROPOSED or APPLIED per editor mode
5. Recommended next command (on the brief-produced path: `task-init`, or `project-bootstrap` when not bootstrapped; on the active-task NO_OP: `what-next`)
6. Recommended editor mode
7. Why that is the correct next step

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
- The output either returns a NO_OP routed to the right command for the case (`task-init` when the objective is already clear or a hotfix; `what-next` when an active task already exists, since a mid-task NO_OP routed to `task-init` would spawn a duplicate task) or contains a single next clarifying question; a batched wall of questions or a manufactured interview on an already-clear objective is invalid output.
- When framing is complete, the BRIEF.md has exactly the five fields (problem statement, success criteria, non-goals, recommended approach, named deliverables) and is marked PROPOSED (Ask) or APPLIED (Agent); named deliverables are concrete enough to seed task-init's ledger.
- On the brief-produced path the only recommended next command is `task-init` (or `project-bootstrap` when the project is not bootstrapped), and routing to any implementation, planning, or design command is invalid output; the sole NO_OP exception is `what-next` when an active task already exists.
- The `--game-design` mode (when invoked) keeps the five-field BRIEF.md and adds game-design framing (core loop, mechanics, win/lose, scope) plus game-artifact deliverables; without the flag and on a non-game objective the default intake is unchanged. Imposing game-design questions on a non-game objective is invalid output.
- Output ends with a complete `### Handoff` block per the adaptive format in `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract`.
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
Optimize for catching a mis-framed objective before any task memory is created, with the fewest questions and zero ceremony on an already-clear ask.

<!-- cache-breakpoint -->
