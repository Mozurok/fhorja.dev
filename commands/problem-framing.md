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
- **Bootstrap tiers (ADR-0025):** the light-weight commands (`branch-commit`, `what-next`, `where-we-at`, `slice-closure`, `compact-task-memory`) may skip `## Editor mode policy` good-fits lists and `## Cross-cutting workflow guardrails` sequencing heuristics, reading only the mode definitions and the core guardrail rules (routing memory, command-less input triage, official command names, material change, no-op). This reduces bootstrap from ~6,750 to ~3,500 tokens for these commands.
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
