# WORKFLOW_OPERATING_SYSTEM

Fhorja is a workflow operating system for AI-assisted engineering. This document is its normative specification.

## LLM execution contract

Primary audience:
- the executing model inside Cursor

Human-facing policy:
- normative behavior belongs here in compact, enforceable rules
- longer explanatory prose should live in command outputs and task artifacts under `projects/`

Precedence order:
1. this file (`WORKFLOW_OPERATING_SYSTEM.md`)
2. specific command file under `commands/*.md`
3. `README.md` onboarding guidance

Conflict rule:
- if this file and command files disagree on command-specific behavior, follow the most recent command file and flag the mismatch explicitly

Minimum read map for execution:
- always read before routing or output shaping:
  - `## Editor mode policy`
  - `## Global output contract`
  - `## Cross-cutting workflow guardrails`
- read when needed by context:
  - naming/path disputes: `## Naming conventions`, `## Repository structure`
  - artifact requirements: `## Required task files`, `## Optional task files`, `## TASK_STATE policy`
  - multi-artifact drift or stale `TASK_STATE.md` after heavy edits: `## Command roles` index (`state-reconcile`)
  - PR review feedback under the same contract (Greptile, CI, inline comments): `## Command roles` index (`pr-feedback-ingest`)
  - PR or team feedback changes direction after packaging: `## Command roles` index (`post-review-pivot`)
  - phase/entry ambiguity: `## Command roles` index, `## Entry points`, `## Gate conditions`
  - command distinctness, guard rails, multi-repo nuance, or routing disputes the index does not resolve: load `wos/command-roles.md` (full per-command detail; not loaded by default)
  - phase-by-phase command sequencing across multiple phases when `## Command roles` index plus `## Default workflow` are insufficient: load `wos/cross-cutting-workflow-guardrails.md` (heuristics + external-web motivation; not loaded by default)
  - multi-repo task schema, locked decisions, invariants, non-goals, decision table, or implementation notes: load `wos/multi-repo-support.md` (single-repo tasks do not need this; not loaded by default)
  - full directory tree or governance files inventory (LICENSE, CONTRIBUTING.md, `.github/*`, etc.): load `wos/repository-structure.md` (compact path index in the spec suffices for day-to-day execution; not loaded by default)
  - project-level memory lifecycle (per-command behavior over time), rationale, and edge cases (retroactive bootstrap, multi-repo charter schema, gitignore policy, dedup policy), or the three-tier memory pyramid (task / project / user) and layered precedence rule (specific overrides general): load `wos/project-level-memory.md` (the Files inventory and Decision table in `## Project-level memory` are inline and suffice for routing; the `## Relationship to user-level memory` subsection covers the three-tier model per ADR-0016)
  - choosing `context-layers-consumed:` / `context-layers-produced:` values for a new command, debugging context overruns by layer, or designing a new lazy-loaded topic: load `wos/context-budget.md` (the six canonical layer names, frontmatter convention, and universal baseline rule in `## Context budget` are inline and suffice for routing)
  - deciding whether to delegate a sub-task to a tool-provided sub-agent (Claude Code Explore/Plan/general-purpose; Cursor agent mode; Codex agents; etc.) or stay inline: load `wos/sub-agent-orchestration.md` (orchestrator-workers pattern; four-question checklist; per-tool primitives table; pattern relationships)
  - design system work (foundations, components, tokens, Storybook, screen documentation, Figma extraction, design-to-code alignment): load `wos/design-system-conventions.md` (atomic hierarchy, **docs split (research vs app)**, **granular foundations**, semantic token naming, W3C DTCG target format, states-as-first-class, Figma-first derivation, traceability rule, **personas + screen organization**, **audit cadence (ATOM_AUDIT + COMPONENT_GUIDELINES + inventory)**, a11y floor, versioning convention)
  - depth control: load `wos/output-depth-policy.md` (Lean / Balanced / Deep per-command assignment and transcript brevity rule)
  - calibrating **Work complexity** or comparing risk across sessions: load `wos/global-output-contract.md` → `## Calibration examples (non-normative)` (the inline `### Work complexity (capability routing)` definitions remain inline; only the vignette set is lazy)
  - writing or reviewing human-facing prose (PR descriptions, commits, team updates, delivery assets, docs) or auditing text for AI tells: load `wos/natural-voice.md` (the normative core is inline in `## Global output contract` → `### Natural voice (no AI tells)`; this file is the full catalog with rewrites)
  - validating command output shape against phase gates: `## Definition of done (command outputs)`
  - handoff format or mode selection: `## Global output contract` → `### Adaptive handoff`
  - task file contracts (required/optional files, purpose, structure): load `wos/task-file-contracts.md`
  - entry point selection (which command to start with): load `wos/entry-points.md`
  - phase gate checklists: load `wos/gate-conditions.md`
  - workflow anti-patterns: load `wos/anti-patterns.md`
  - task shape selection (which workflow flow for this type of task): load `wos/workflow-shapes.md`
  - operating modes (minimal / strict / teaching): load `wos/operating-modes.md`
  - editor mode translation to non-Claude-Code tools (Cursor, Copilot, Codex, Gemini CLI equivalents): load `wos/editor-mode-mappings.md` (only when working in a tool other than Claude Code)
  - designing, building, or running the autonomous delivery track (the autonomy cluster: two human gates, runtime governor, mid-run escalation, run protocol): load `wos/autonomous-track.md` (built per ADR-0044; not loaded by default)
  - Godot 2D-mobile game development (scene architecture, save/state and the mobile lifecycle, 2D rendering performance, touch input and game-feel, audio, the asset pipeline, headless testing and CI): load `wos/godot-2d-architecture.md`, `wos/godot-2d-mobile-rendering-performance.md`, `wos/godot-mobile-interaction-and-feel.md`, `wos/godot-2d-audio.md`, `wos/godot-2d-asset-pipeline.md`, `wos/godot-testing-and-ci.md` (the Godot cluster reference layer per ADR-0078 and ADR-0084; capability-scoped, not loaded by default)

---

## Purpose

Human onboarding stub:
- this document defines the operating system for the engineering command library inside Cursor IDE
- it is a workflow control system (not just a prompt library), optimized for low ambiguity and resumable execution

---

## Scope

This workflow is designed for a single developer operating inside Cursor with a strict, evidence-driven, low-assumption working style.

Primary priorities:
- minimize ambiguity
- minimize incorrect assumptions
- keep task memory persistent outside chat state
- plan before implementation
- implement in approved slices
- preserve quality and predictability
- reduce context waste and unnecessary token usage
- make the next step operationally obvious

This workflow is optimized for:
- multi-project work
- tasks that often start nebulous
- fullstack engineering work
- repo-grounded analysis
- high-discipline execution

---

## Core principles

1. Do not implement before the scope is narrow enough.
2. Do not let Cursor infer undocumented business rules.
3. Use the real codebase as the primary source of truth.
4. Ask targeted questions before making correctness-affecting assumptions.
5. Separate discovery, decision-making, planning, implementation, closure, and delivery.
6. Prefer small approved slices over broad implementation.
7. Keep TASK_STATE.md updated as operational memory.
8. Do not confuse slice completion with task completion.
9. Prefer boring, safe, reviewable work over clever or wide-ranging work.
10. Use the safest editor mode for the current phase.
11. Every command should make the next step obvious.
12. Prefer fewer workflow hops when the task is small and already well-bounded.

---

## Repository structure

The workflow operates on a separate task-memory repository. Compact path index (the folders and files commands actually create or read):

- `commands/<name>.md`: command files (source of truth for which commands exist; carry Agent Skills frontmatter validated by `lint-commands.sh`).
- `commands/_shared/<name>.md`: canonical shared blocks propagated by `sync-shared-blocks.sh` into commands that declare the marker.
- `.claude/skills/<name>/SKILL.md`: **generated** Agent Skills artifacts produced by `scripts/build-agent-skills.sh` from each canonical `commands/<name>.md`. Drop-in for the 35+ tools that read `.claude/skills/` natively (Cursor 2.4+, Claude Code, Copilot, Codex, Gemini CLI, etc.). Never edit by hand; lint fails on drift.
- `wos/<topic>.md`: lazy-loaded reference files (<!-- count:wos-topics -->35<!-- /count --> topics; e.g. `command-roles.md`, `cross-cutting-workflow-guardrails.md`, `global-output-contract.md`; see the Minimum read map for the full set). Loaded only when explicitly needed.
- `templates/`: starting points for task artifacts (`PR_PACKAGE.md`, `review-hard-checklist.md`).
- `scripts/`: automation (`lint-commands.sh`, `sync-shared-blocks.sh`, `sync-workflow-slash-commands.sh`, `build-agent-skills.sh`, `check-doc-sync.sh`, `check-natural-voice.sh`, `monitor-fleet-progress.sh`, `scan-substrate-orphans.py`, `measure-tokens.py`, `measure-task-cost.py`).
- `evals/scenarios/<NN>-*.md`: manual eval harness exercising load-bearing workflow contracts (project-bootstrap to task-init wiring, multi-repo schema, slice execution and closure scope discipline, pr-package diff grounding, state-reconcile minimum patch). `evals/scripts/run-evals.sh` walks through them.
- `docs/`: contributor and user-facing reference (`FAQ.md`, `MIGRATION.md`, `adr/` Architecture Decision Records).
- `.github/`: issue/PR templates and CI (`workflows/lint.yml`).
- `projects/<client>__<project>/`: project-level memory. Required when the project is bootstrapped: `PROJECT_CHARTER.md`, `REFERENCES.md`, plus `active/` and `archive/` (or legacy `done/`) subfolders.
- `projects/<client>__<project>/active/YYYY-MM-DD_<task-slug>/`: active task folder. Required base files: `README.md`, `TASK_STATE.md`, `SOURCE_OF_TRUTH.md`, `DECISIONS.md`, `IMPLEMENTATION_PLAN.md`. Optional: `IMPACT_ANALYSIS.md`, `INVARIANTS_AND_NON_GOALS.md`, `TEST_STRATEGY.md`, `PR_PACKAGE.md`, `DB_CONTEXT.md`, `SLICES/NN_<slice-slug>.md`.

For the full directory tree (with file-level annotations) and the inventory of repository governance files (LICENSE, CONTRIBUTING.md, SECURITY.md, CODE_OF_CONDUCT.md, CHANGELOG.md, ROADMAP.md, CLAUDE.md, `.github/*`), load `wos/repository-structure.md`.

Command inventory source of truth:
- `commands/` directory contents (not this index)

---

## Naming conventions

### Project folder
Format:

```text
<client>__<project>
```

Examples:
- `petvet__platform`
- `coinbase__wallet-web`
- `zipdev__purecars`

Rules:
- lowercase
- use hyphens if needed
- avoid vague names
- keep it stable across tasks

### Task folder
Format:

```text
YYYY-MM-DD_<task-slug>
```

Example:
- `2026-04-11_fix-contentful-domain-routing`

Rules:
- English
- lowercase
- hyphenated slug
- specific enough to distinguish the work
- avoid vague slugs such as `fix-bug`, `cleanup`, `updates`

### Slice files
Format:

```text
01_<slice-slug>.md
02_<slice-slug>.md
03_<slice-slug>.md
```

Examples:
- `01_contract-lock.md`
- `02_domain-resolution.md`
- `03_test-update.md`

Rules:
- two-digit numeric prefix
- short explicit slug
- one file per meaningful slice

---

## Task files

Required: `README.md`, `TASK_STATE.md`, `SOURCE_OF_TRUTH.md`, `DECISIONS.md`, `IMPLEMENTATION_PLAN.md`. Optional: `IMPACT_ANALYSIS.md`, `INVARIANTS_AND_NON_GOALS.md`, `TEST_STRATEGY.md`, `PR_PACKAGE.md`, `DB_CONTEXT.md`, `SLICES/`, `LEARNINGS.md`. For the full contract per file (purpose, structure, create-when rules), load `wos/task-file-contracts.md`.

---

## Multi-repo support (v1)

This section defines opt-in multi-repo support for tasks that legitimately span multiple product repositories (typical fullstack work crossing backend and frontend repos). Multi-repo support is **additive only**: single-repo tasks continue working unchanged. The discriminator is the presence of an optional `## Repositories` section in `SOURCE_OF_TRUTH.md`; tasks without that section (the default) behave as single-repo across all <!-- count:commands -->94<!-- /count --> commands and do not pay any multi-repo overhead.

For the schema (identifier, path, base branch, role), example, locked decisions D1-D7, invariants I1-I4, non-goals NG1-NG5, runtime decision table, and implementation notes, load `wos/multi-repo-support.md`.

### Command coverage (G4 v1)

This taxonomy covers the product lifecycle commands. The `*-fleet` orchestrators (`implement-fleet`, `task-init-fleet`) and the CUSTOM personas inherit multi-repo behavior from the per-repo loop they run and are not enumerated here.

**Multi-repo aware (7 commands)**:
- `task-init`: writes the `## Repositories` schema into `SOURCE_OF_TRUTH.md` when 2+ repos are provided (the schema producer; the others are consumers).
- `code-locate`: accepts `target repo` input when multi-repo; restricts search to that repo's workspace path.
- `impact-analysis`: produces per-repo blast radius assessment when multi-repo; per-repo subsections in `IMPACT_ANALYSIS.md`.
- `pr-package`: runs once per repo with explicit `repo` and `base branch` inputs; produces `PR_PACKAGE.<repo>.md` per repo.
- `implement-approved-slice`: produces per-repo execution subsections (files touched, validation evidence) when `SOURCE_OF_TRUTH.md` has a `## Repositories` section (D.4 v2).
- `slice-closure`: per-repo closure evidence when multi-repo (D.4 v2).
- `where-we-at`: per-repo progress assessment when multi-repo (D.4 v2).

**Single-repo by default (4 commands, deferred to G4 v2)**:
- `targeted-questions`
- `implement-slice-complement`
- `pr-feedback-ingest`
- `post-review-pivot`

These commands consume `SOURCE_OF_TRUTH.md` but ignore the `Repositories` section. They operate as if the task is single-repo (typically targeting the first listed repo or whichever workspace path was passed in directly). Multi-repo users coordinate manually for these commands until G4 v2 expands coverage.

### Per-task worktree isolation (opt-in, v1)

Opt-in, git-gated isolation lets several tasks run in parallel on one repository without colliding on a single working tree (ADR-0074). It is additive: when isolation is not requested, or the project is not a git repository, every command behaves as today (single working tree, single branch, no overhead). When a task opts in, the `task-workspace` command provisions one durable git worktree and a `task/<task-slug>` branch off the base, and records them in `SOURCE_OF_TRUTH.md` under an optional `## Workspace` section (worktree path, task branch, base branch; schema in `wos/multi-repo-support.md`). `task-init` routes to `task-workspace` when isolation is requested rather than provisioning itself; `task-close` tears the worktree down (`git worktree remove` then `prune`) and halts on an unclean or unmerged tree. These per-task worktrees are distinct from the ephemeral slice-level worktrees `implement-fleet` creates: when a task worktree is active, fleet slice worktrees branch off the task branch. Multi-repo worktree provisioning is out of scope for v1.

---

## Project-level memory

This section defines memory artifacts that live at the project level (`projects/<client>__<project>/`), shared across all tasks under that project. Project-level memory is created once by `project-bootstrap` and grown over time by `capture-references` (and other commands when explicitly authorized).

For lifecycle narrative (per-command behavior over time), the rationale ("why project-scoped at all"), the human knowledge layer (the `knowledge/` folder), and edge cases (retroactive bootstrap, multi-repo charter schema, gitignore policy, dedup policy), load `wos/project-level-memory.md`. The Files inventory and the Decision table below are the routing-critical stubs and stay inline.

### Files

- `PROJECT_CHARTER.md`: high-level project context (objective, stack, planned repositories, default workspace, constraints, non-goals, stakeholders). Created by `project-bootstrap`. Read by `task-init` to seed `SOURCE_OF_TRUTH.md` for new tasks under the same project.
- `REFERENCES.md`: external references (URL, accessed date, summary, optional verbatim key points, tags). Seeded by `project-bootstrap` when the user pre-supplies references; appended to by `capture-references`. Deduplicated by URL.
- `knowledge/` folder: human-first knowledge layer (project evolution, history, and the learnings that mattered), organized as a navigable, Obsidian-compatible set of linked notes (ADR-0054, ADR-0055). One note per closed task (`knowledge/<task-slug>.md`) plus an `index.md` map of content, wikilinked in plain Markdown. Written by `task-close` only (D-11): it creates the note, updates the index, writes deterministic links, and proposes topic links for the human to confirm. **Never auto-loaded**: no command reads the folder at task start, and `task-init` never seeds from it; the AI receives its content only when a human pastes an excerpt into a task prompt. Two generated views accompany it: the project timeline (`scripts/build-activity-timeline.py --project`) and the knowledge HTML view (`scripts/build-knowledge-view.py`). See `wos/project-level-memory.md` for the full convention; the note template is `templates/knowledge-layer-entry.template.md` and the index template is `templates/knowledge-index.template.md`.

### Decision table (runtime behavior)

| Input condition | Action | Expected effect |
|---|---|---|
| `projects/<client>__<project>/` does not exist | Recommend `project-bootstrap`; refuse to silently create project-level files from another command | New project starts with explicit charter + references skeleton |
| `projects/<client>__<project>/PROJECT_CHARTER.md` exists at `task-init` time | `task-init` seeds `SOURCE_OF_TRUTH.md` from it (stack, repos, constraints) | New tasks inherit project context without re-asking |
| `projects/<client>__<project>/PROJECT_CHARTER.md` missing at `task-init` time | `task-init` warns "project not bootstrapped" and proceeds with placeholders | Task continues; user can bootstrap later via `project-bootstrap` if appropriate |
| `projects/<client>__<project>/REFERENCES.md` exists at `task-init` time | `task-init` adds a `## Project-level memory` pointer to it from `SOURCE_OF_TRUTH.md` | Task can consume external references without duplication |
| `capture-references` invoked with a URL already present in `REFERENCES.md` | Skip with `NO_OP_TRACE`; do not append a duplicate entry | Frescor metadata stays consistent; no churn |
| Any task-scoped command tries to append to `REFERENCES.md` | Refuse and route to `capture-references` | Project-level memory only mutated through its canonical command |
| `projects/<client>__<project>/knowledge/` exists at `task-init` time | Do NOT read or seed from it; the layer is human-read and re-entered only by explicit human paste | The knowledge layer never re-couples to the AI automatically (ADR-0054, ADR-0055, D-3/D-5) |
| A task is closed via `task-close` | Create one `knowledge/<task-slug>.md` note, update `knowledge/index.md`, write deterministic links, and propose topic links for the human to confirm (idempotent; no second note on re-run; no silent unverified links) | Project history and learnings accumulate as a navigable vault without a per-slice tax (ADR-0055, D-9/D-11) |

---

## Context budget

This section names the six context layers every command implicitly operates on. Naming them turns context engineering from an implicit pattern into a falsifiable contract: lint can validate that each command declares which layers it touches, downstream slices (token budgets, cache structure, working-memory compaction) measure cost per layer, and new-command authors have a checklist instead of a judgment call.

For the layer-by-layer narrative, examples, the per-layer compaction guidance, the cache breakpoint convention foreshadow, and edge cases, load `wos/context-budget.md`. The six canonical layer names, the frontmatter convention, and the universal baseline rule below are the routing-critical stubs and stay inline.

### The six canonical layers

1. `system`: system-prompt rules, command personas, output contracts.
2. `memory`: persisted state (task memory, project memory, user memory).
3. `retrieved`: external sources brought in by retrieval rather than persisted as memory (capture-references entries, external-research syntheses).
4. `tools`: tool and command definitions exposed to the model (Agent Skills surface).
5. `history`: recent conversation turns within the active session.
6. `task`: the immediate user request being processed.

Names are locked (ADR-0012). Future renames require a new ADR superseding it.

### Frontmatter convention

Every `commands/<name>.md` declares two YAML lists:

```yaml
context-layers-consumed: [memory, retrieved]
context-layers-produced: [memory]
```

`consumed:` lists the non-baseline layers a command actively reads. `produced:` lists the layers a command writes to via runtime artifacts.

Every command also declares three additional `metadata` fields (ADR-0059), all rule-derived and lint-enforced:

```yaml
tools: [Read, Write, Edit, Bash, Glob, Grep]
x-wos-profiles: [minimal, core, full]
provenance: first-party
```

`tools:` is the command's tool surface from the canonical vocabulary (Read, Write, Edit, Bash, Glob, Grep, WebFetch, WebSearch, Task). A read-only command (`context-layers-produced: []`) MUST NOT declare Write or Edit (Bash is exempt: read-only commands still run git, grep, and lint); lint fails on violation. `x-wos-profiles:` is the install-tier membership (a subset of `minimal`, `core`, `full`; minimal commands also list core and full); `sync-workflow-slash-commands.sh --profile <tier>` filters by it. `provenance:` is the trust origin (`first-party` for every command; `vetted-third-party` and `sandbox` are reserved for external skills a human approved via `skill-vet`). Lint validates all three; the canonical `tools` vocabulary lives in the `VALID_TOOLS` array in `scripts/lint-commands.sh`.

### Universal baseline rule

`system`, `tools`, and `task` are universal baseline. Every command consumes them by definition. They are NOT listed in `consumed:` to keep the signal discriminating. Valid non-baseline values for `consumed:` are `memory`, `retrieved`, `history`. Empty lists are valid: a command may consume nothing beyond baseline (`project-bootstrap`) or produce nothing material (pure routing such as `what-next`).

Lint enforces presence of both fields and validates values against the canonical six.

### Cache breakpoint marker

Every `commands/<name>.md` ends with a single `<!-- cache-breakpoint -->` HTML comment marker as the LAST non-blank line of the body. The marker delimits the static cacheable prefix (the command file content) from the runtime-dynamic content that follows in the conversation (user invocation, task state, paste content). Lint validates presence (exactly one), count, and position (after `### Definition of done`) with hard FAIL on drift. See `wos/context-budget.md ## Cache breakpoint convention` for the full rationale and tool-integration notes; ADR-0014 records the decision.

---

## Task lifecycle

There are only two task states at the repository level:

- `active`
- `done`

### When a task is created
A new task is created whenever a new work item starts through the official workflow.

Rules:
- new work item = new task
- follow-up = new task
- post-review correction can be a new task if it becomes a new work cycle

### When a task stays in `active`
A task remains active while:
- implementation is still in progress
- review is not complete
- the team has not approved it yet
- the PR has not been merged into staging or the target integration branch for that project

### When a task moves to `done`
A task moves to `done` only when:
- the implementation is complete
- review is complete
- team approval happened
- merge into the target integration branch happened
- `TASK_STATE.md` was updated to final state

The `task-close` command performs this transition: it gates on the conditions above (each one met with evidence or explicitly waived in solo / Phase-1 contexts), writes the final `TASK_STATE.md`, and moves the task folder from `active/` to `archive/` (preserving the record; `archive/` canonical, `done/` legacy alias). It is the symmetric counterpart to `task-init` and is distinct from `slice-closure`, which closes a single slice. See ADR-0028.

Commit-evidence floor (ADR-0084): even when merge (condition 4) is waived in a solo or Phase-1 context, closure requires either a commit reference covering the closed work or an explicit recorded waiver of committing it (a deliberate throwaway). Archiving a task whose work is neither committed nor waived is the failure ADR-0084 closes: the dogfood archived two "done" tasks with the work uncommitted. `slice-closure` applies the same floor to a single slice.

---

## Editor mode policy

The workflow's canonical editor-mode vocabulary is **`Ask` / `Plan` / `Agent` / `Debug`**. These names originate from Cursor but are adopted as the workflow's tool-neutral mode taxonomy: every command's `Primary editor mode:` field uses one of these four values, and every `### Handoff` block's `Mode:` line uses one of them. Other AI tools have similar mode taxonomies under different names; the table below maps the workflow's modes to common tool equivalents.

### Mapping to other tools

The mode-to-tool mapping table lives in `wos/editor-mode-mappings.md` (lazy-loaded). Load it only when the user is working in a non-Claude-Code tool and needs to translate mode names. The mode names are about the agent's intent, not the tool's UI.

### Ask
Use Ask when the goal is:
- understanding
- impact analysis
- review
- routing
- phase detection
- ambiguity reduction
- closure judgment
- progress assessment
- prompt shaping
- delivery packaging
- lightweight communication

Good fits:
- `project-bootstrap` when drafting or validating project-level artifacts
- `capture-references` when researching and persisting external references
- `task-init` when drafting or validating task artifacts only
- `code-locate`
- `impact-analysis`
- `invariants-and-non-goals`
- `targeted-questions`
- `decision-interview`
- `problem-framing`
- `what-next`
- `workflow-guide`
- `im-stuck`
- `capture-observation`
- `direction-adjust`
- `review-hard`
- `where-we-at`
- `slice-closure`
- `resume-from-state`
- `pr-package`
- `branch-commit`
- `team-update`
- `prompt-shape`
- `sync-task-state`
- `state-reconcile`
- `pr-feedback-ingest`
- `post-review-pivot`

Do not use Ask as disguised implementation.

### Plan
Use Plan when the goal is:
- sequencing work
- converging contract decisions
- hardening implementation rules
- defining test strategy

Good fits:
- `resolve-contract-gaps`
- `contract-signoff`
- `implementation-plan`
- `test-strategy`
- `compact-task-memory`
- `self-critique-and-revise`

Do not use Plan to pretend implementation is already done.

### Agent
Use Agent only when:
- the slice is approved
- the scope is narrow enough
- the files in scope are known
- correctness-critical ambiguity is already resolved
- the next step is an actual code change

Also use Agent when:
- a command is allowed to materialize or update files inside `my_work_tasks`
- and the intent is to write task-memory files, not product code

Good fits:
- `implement-approved-slice`
- `implement-fleet` (parallel execution of independent approved slices per ADR-0041; the orchestrator and its workers all run in Agent mode)
- `implement-slice-complement`
- `task-init` only when creating files in the task-memory repo
- `approve-proposed` (the canonical batch-persist idiom; writes every `PROPOSED` file from the prior assistant turn's `### Artifact changes` atomically; see ADR-0024 and `## Cross-cutting workflow guardrails ### Proposal vs approved persistence`)
- other commands only when explicitly persisting task-memory artifacts

Do not use Agent for discovery, policy decisions, or broad exploration.

### Debug
Use Debug only when:
- there is a concrete observed technical failure
- the problem is actual runtime behavior, broken output, or failing tests
- diagnosis is the main need

Good fits:
- `incident-triage` (the canonical Debug-mode use case in this workflow)

In this workflow, Debug is exceptional, not the default path. `incident-triage` exists so urgency-shaped tasks have a structured entry point that defends against bypassing the workflow entirely while keeping ceremony short for real hotfixes.

---

## Evidence priority

Across the workflow, use this evidence priority unless a command states otherwise:

1. real code and tests in the codebase
2. `TASK_STATE.md` and `SOURCE_OF_TRUTH.md`
3. other task artifacts in the task folder
4. project-level memory (`PROJECT_CHARTER.md`, `REFERENCES.md`)
5. internal project docs / tickets / local references
6. official framework or library docs
7. external web references, via `capture-references` only (never ad-hoc web fetches inside other commands; see `## Cross-cutting workflow guardrails` → `### External web access (centralized)`)

Rule:
- if correctness depends on something not grounded in code, docs, tests, or explicit user input, do not guess
- ask targeted questions instead
- when an answer requires an external web reference that is not yet in `REFERENCES.md`, route to `capture-references` rather than fetching ad-hoc

Greenfield clause (priority reordering for new code in established frameworks):
- when the existing codebase contains **no precedent** for the pattern about to be introduced (greenfield feature in an established framework, or new project bootstrap), **official framework docs (priority #6) supersede training-data defaults**
- the model MUST NOT fabricate patterns from training data when (a) no internal precedent exists AND (b) the framework has documented current best practices that may have shifted since the model's training cutoff
- in this case, route to `stack-currency-check` (or `capture-references` / `external-research` if more appropriate) to verify current patterns BEFORE planning or implementation
- specifically: deprecated APIs, replaced helper functions, new-recommended-defaults, and breaking-change migrations are the failure modes this clause exists to prevent (see anti-pattern: "gold-standard audit")

Execution consumption (reference grounding gate):
- ranking the references is not enough; an execution command MUST actively consume them. Before editing a slice that touches an external library, SDK, API, or documented protocol, the executor reads the matching `REFERENCES.md` entry and emits a `Grounded in:` cite, or refuses and routes to `capture-references` when the contract is uncaptured.
- the normative rule is the shared block `commands/_shared/reference-grounding.md`, consumed by every execution command (`implement-approved-slice`, `implement-slice-complement`, `implement-fleet`); the decision record is ADR-0043. This exists to prevent the NEVER-READ failure mode (references captured, then ignored during implementation).

---

## Global output contract

Every command must make continuation easy.

### Standard command output layout (required)
Every command output MUST be structured into these sections, in this order:

1) `### Artifact changes`
- List each task-memory file that would change (or `None`).
- For each file, label the change as one of:
  - `APPLIED`: you are explicitly instructing a file write in this run (typically only in Agent mode, and only when the command’s policy allows persistence)
  - `PROPOSED`: content the user should review before persisting. Adapt verbosity to file state:
    - **Create** (new file): full content inline -- there is no existing file to diff against
    - **Update-delta** (existing file, small change): semantic delta only -- name the section(s) changed, state what changed and why, include the changed lines or block. Do NOT repeat unchanged content.
    - **Update-rewrite** (existing file, large rewrite in Agent mode): write directly via tool call; list the file as `APPLIED` with a one-line summary of changes
  - `SKIP`: explicitly skipping an optional artifact with a one-line rationale (example: `TEST_STRATEGY.md`)

2) `### Command transcript`
- Short audit trail for reruns: what changed vs last step, why this command was/wasn’t a no-op, and any `NO_OP_TRACE` notes.

3) `### Handoff`
- Use the adaptive ending format (below). This is the only place for `Run now / Mode / Work complexity / Reason` (and `Resume context:` when applicable).
- Ending the message after `### Command transcript`, or after long prose inside `### Artifact changes`, **without** a complete `### Handoff`, is invalid command output.

### Tool-call placement contract

Applies to any assistant turn that emits tool calls (Bash, Read, Edit, Write, Grep, Glob, Task, etc.), structured-command and non-command alike:

- All tool calls in a single assistant message MUST be placed at the **end** of the message, after all user-facing prose.
- Immediately before the batched tool calls, emit a one-line `Why: <intent>` header naming what the batch is doing and why (example: `Why: reading three commands to compare frontmatter shape before editing`).
- Do not interleave prose between tool calls within a single turn. Either prose-then-tools, or pure tools, but never tool-prose-tool-prose.
- Exception: turns with zero tool calls are unaffected; structured-command output (`### Artifact changes` etc.) is unaffected because those sections are prose, not tool calls.

Rationale: makes transcripts readable; gives one logical interrupt point per turn; prevents context fragmentation in long sessions; pairs with `ADR-0023 context-rot guardrails` because grouped tool batches compress better. Adopted from Windsurf Cascade R1 leaked prompt (validated production pattern across Cursor, Windsurf, Replit).

### Vocabulary (English-only tokens)
Use these exact tokens when applicable:
- `NO_OP`: no material change; do not churn artifacts; still include `NO_OP_TRACE` in `### Command transcript`
- `NO_FILE_CHANGES`: no task-memory file writes in this run
- `NO_OP_TRACE`: 1-3 lines, human-readable, English only
- `Work complexity` handoff line: exactly one of `LOW`, `MEDIUM`, `HIGH`, or `N/A` (see **Work complexity (capability routing)** below)

### Natural voice (no AI tells)

All human-facing prose (PR descriptions, commit bodies, team and status updates, delivery assets, slice notes, docs) must read like a person wrote it. Avoid the common machine tells:

- Slash disjunctions in prose: write `Slack, Discord, or email`, not `Slack / Discord / email`. Code enums (`LOW/MEDIUM/HIGH`), paths, and pipe-separated token templates are exempt.
- `not just X, but Y` parallelism and the reflexive rule-of-three: state the point directly.
- Vocabulary cliches: prefer `use` over `leverage` or `utilize`; cut `seamless`, `robust`, `comprehensive`, `crucial`, `it's worth noting`.
- Decorative bold, emoji, and Title Case headers: bold only real emphasis, no emoji, sentence-case headers.

The em-dash character stays a hard lint failure (use `--`, a colon, or parentheses). The rest is advisory: `scripts/check-natural-voice.sh` surfaces hits on the lint `Natural-voice:` line without failing the build. Full catalog with rewrites: `wos/natural-voice.md`.

### Long-running execution visibility (per ADR-0042)

Any single execution step expected to exceed about 10 minutes MUST state its expected duration up front and emit interim status instead of going silent. Silence on a long step is indistinguishable from a hang and forces the operator to poll or interrupt.

- Announce up front: when a step (a fleet wave, a slow build or test suite, a large multi-file pass, a background task) is likely to run past ~10 minutes, say so and name what is running before starting it.
- Emit interim status: surface progress as it happens (file-completion ticks, per-wave dispatch lines, a background-task progress note, or the worker's last tool summary), not only a final result.
- Stall rule: when a long-running step surfaces no progress for the stall threshold, emit a status summary (what is running, elapsed time, last observable action) rather than waiting silently for a timeout. For fleets, `implement-fleet` references `scripts/monitor-fleet-progress.sh` and applies this rule during its convergence barrier; this is a reporting duty and does not weaken the integration gate.

This is the operator-visibility counterpart to the Handoff contract: the Handoff makes continuation legible between steps; this makes a single long step legible while it runs.

### Task-memory write policy (default)
Unless a command explicitly says otherwise:
- Treat task-memory updates as **`PROPOSED`** by default in Ask/Plan modes.
- Prefer applying `TASK_STATE.md` updates via `sync-task-state` after meaningful progress (unless the command explicitly requires an immediate `TASK_STATE.md` patch and the user is persisting in Agent mode).
- **Exception (ADR-0026):** `implement-approved-slice` running in Agent mode uses **`APPLIED`** by default for slice execution notes (slice files, TASK_STATE.md updates). Rationale: the user already authorized execution via the handoff; a PROPOSED cycle adds overhead with near-zero rejection rate (0% in Fhorja analysis). This exception does NOT extend to other commands or to Ask/Plan modes; the PROPOSED-by-default contract from ADR-0001 remains the global default.

### Every command should end with:
- recommended next command
- recommended editor mode
- **work complexity** for the immediate next step (`LOW`, `MEDIUM`, `HIGH`, or `N/A` when not applicable)
- one-line reason
- **adaptive context** per the handoff mode (see **Adaptive handoff** below)

### Work complexity (capability routing)

Purpose:
- Estimate how much **reasoning depth and carefulness** the **next** workflow step likely needs.
- Help you choose editor routing (for example Cursor **Auto** vs **Premium**, or manual model tier) **without naming vendors, families, or model SKUs**: those change too often to hardcode here.

Allowed values (exact tokens for the handoff line and for `TASK_STATE.md`):
- `LOW`: Narrow scope, localized edits, facts and contracts already tight, low blast radius if wrong.
- `MEDIUM`: Multi-step reasoning, several files or integration seams, moderate blast radius, or cross-boundary validation.
- `HIGH`: Correctness-critical ambiguity, security/safety, coordinated edits across many areas, long-horizon refactors, or fragile diagnosis where mistake cost is high.
- `N/A`: The recommended next step has no meaningful capability tradeoff (for example pure communication or trivial meta-routing).

Non-normative mapping to Cursor (user-controlled in the product UI; see [Cursor Models & Pricing](https://cursor.com/docs/models-and-pricing)):
- `LOW`: Everyday work: default routing is usually enough; **Auto + Composer** pool is designed for this class of task.
- `MEDIUM`: Prefer a **stronger** capability tier when a single pass must be unusually careful; often aligns with **API / Premium-style** routing or a manually pinned stronger model, still without naming SKUs here.
- `HIGH`: Treat like `MEDIUM` but with stricter expectations; additionally consider **larger context / Max-style** modes only when the **evidence footprint** (many files, large traces) truly warrants the extra cost.

Rules:
- Do **not** output model names, version numbers, or provider product strings in command outputs.
- Re-evaluate complexity when phase, risk, or slice changes; `sync-task-state` should keep the task-level line aligned with the next real step.
- **Model selection for direct Claude Code usage** (no Cursor routing layer): `ADR-0025` → `## Model selection by tier` provides a recommended Claude SKU per pipeline tier (Express → Haiku 4.5, Standard → Sonnet 4.6, Disciplined → Sonnet/Opus, Strict → Opus). This is the user's per-task decision recorded in `TASK_STATE.md`; commands themselves still never emit SKU names in handoffs.
- Pipeline tier (Express/Standard/Disciplined/Strict from `ADR-0025`) and `Work complexity` (`LOW`/`MEDIUM`/`HIGH`/`N/A`) are orthogonal axes: pipeline tier governs *which workflow shape* (how many ceremony steps); Work complexity governs *how hard the next single step is*. A Strict task may have a `LOW` next step (a trivial typo fix in an auth file); a Standard task may have a `HIGH` next step (a tricky integration decision). Do not conflate them.

### Calibration examples (non-normative)

For the full `LOW` / `MEDIUM` / `HIGH` calibration vignettes (typo fixes, API plus migration changes, auth or cryptography changes, production incidents) and the "prefer the higher complexity if mistake cost is asymmetric" tiebreaker, load `wos/global-output-contract.md`. Capability-routing definitions themselves (`LOW` / `MEDIUM` / `HIGH` / `N/A`) remain inline above; only the supporting vignette set is lazy-loaded.

### Adaptive handoff

The `### Handoff` block adapts its verbosity based on session state.

**Mode A -- Compact (default, intra-session)**

When the model has full conversation history (same session, no compaction boundary crossed):

```text
Run now: /<command>
Mode: <Ask | Plan | Agent | Debug>
Work complexity: <LOW | MEDIUM | HIGH | N/A>
Reason: <one line>
```

~50 tokens. No paste body needed because the context window already contains everything.

**Mode B -- Full (cross-session or post-compaction)**

When context loss is likely (new chat, `resume-from-state`, after auto-compaction, handoff to a different person):

```text
Run now: /<command>
Mode: <Ask | Plan | Agent | Debug>
Work complexity: <LOW | MEDIUM | HIGH | N/A>
Reason: <one line>
Resume context:
- Task: projects/<client>__<project>/active/YYYY-MM-DD_<task-slug>/
- Workspace: <product codebase path>
- Current slice: <slice id + name>
- Key decisions: <D-N references if relevant>
```

~150-250 tokens. Only include what cannot be re-derived from task files on disk.

**Mode C -- Parallel fanout (sub-agent dispatch)**

When the command would naturally fan out work across independent sub-agents to reduce parent-context inflation or cut latency through parallelism. Per ADR-0032.

Triggers (any one is sufficient):
- `code-locate` against a codebase with >1000 files
- `external-research` with >3 captured sources to compare
- `repo-consistency-sweep` with a diff touching >10 files
- multi-repo task where independent per-repo analysis can run in parallel

Format:

```text
Delegate now: <comma-separated sub-agent invocations or pattern descriptions>
Mode: Plan (parent) + Explore (workers); use Claude Code Task tool, Cursor /worktree, or equivalent
Work complexity: matches parent slice
Reason: <why fanout vs inline>
Merge back: <where the parent integrates the summarized results>
```

The parent emits the delegation; sub-agents run in isolated contexts. The parent waits, integrates the summarized results into its own output, then resumes the normal Mode A or Mode B handoff for the next step. Mode C is a within-turn directive, not a turn-ending handoff.

### Mode selection rule

- **Default: Mode A** within the same session.
- **Switch to Mode B** when:
  - The command explicitly targets a new session (`resume-from-state`).
  - Auto-compaction has occurred since the last handoff.
  - The user indicates they will continue in a different tool or chat.
  - The task is being handed to a different person.
- **Switch to Mode C** when:
  - The command body declares it triggers parallel-fanout (per ADR-0032) AND
  - One of the trigger conditions listed above is met AND
  - The sub-agents would do non-overlapping read-only work that can be summarized independently for the parent to consume.

### Why this is mandatory

The `### Handoff` block is the primary continuation interface; dropping or truncating it is a contract violation. **Never** truncate the response before a complete `### Handoff`. When token limits threaten the response, shorten earlier sections instead. For the full motivation, load `wos/global-output-contract.md` → `## Why the Handoff block is mandatory`.

---

## Definition of done (command outputs)

Shared contract for **every** command in `commands/*.md` (in addition to each file’s own `### Definition of done (command output)` bullets).

Before declaring any command's output done, you MUST load this section and confirm each of the following items applies to the run. A command's own closing `### Definition of done (command output)` bullet that points here means you have performed that confirmation, not merely that the contract exists.

1. **Section order**: Output uses `### Artifact changes`, then `### Command transcript`, then `### Handoff`, in that order, unless a command file explicitly documents an exception (none today).
2. **Handoff**: The `### Handoff` block uses the **adaptive ending format** (`Run now`, `Mode`, `Work complexity`, `Reason`, and `Resume context:` when Mode B applies). `Work complexity` is exactly one of `LOW`, `MEDIUM`, `HIGH`, `N/A`. Mode selection follows **Adaptive handoff** in `## Global output contract`.
3. **Routing integrity**: Recommended commands use **official basenames** only (files in `commands/`, without `.md`). No invented aliases.
4. **Material change and no-op**: Follow **Material change (definition)** and **No-op execution rule** in `## Cross-cutting workflow guardrails`. No-op runs still include a short `NO_OP_TRACE` in `### Command transcript`.
5. **Task-memory writes**: Follow **Task-memory write policy (default)** for `APPLIED` / `PROPOSED` / `SKIP` labels.
6. **Vocabulary**: Use English-only tokens from **Vocabulary (English-only tokens)** where applicable (`NO_OP`, `NO_FILE_CHANGES`, `NO_OP_TRACE`).
7. **No orphan routing**: Do not recommend a next command in prose without also emitting the full fenced Handoff block for that command.

### Phase gates (cross-reference)

Authoritative transition checks live in `## Gate conditions`. Use them to sanity-check whether a command’s conclusions are **safe for the current phase**. This table is a **hint**, not a replacement for `## Command roles`:

| Primary gate (most relevant) | Typical commands |
|------------------------------|------------------|
| Before planning | `code-locate`, `impact-analysis`, `invariants-and-non-goals`, `targeted-questions`, `decision-interview` |
| Before planning / contract hardening | `resolve-contract-gaps`, `contract-signoff` |
| Before implementation | `implementation-plan`, `test-strategy` |
| Before implementation (execution) | `implement-approved-slice`, `implement-slice-complement` |
| Before slice closure | `review-hard`, `slice-closure` |
| Before PR packaging | `where-we-at` (when used), `pr-package` |
| After PR review feedback (corrective) | `pr-feedback-ingest` |
| After PR review feedback (pivot) | `post-review-pivot` |
| Project-level memory init | `project-bootstrap`, `capture-references` |
| Entry / recovery / drift | `task-init`, `resume-from-state`, `what-next`, `workflow-guide`, `im-stuck`, `sync-task-state`, `state-reconcile` |
| Concrete observed failure | `incident-triage` |
| Communication / meta | `branch-commit`, `team-update`, `prompt-shape` |

---

## Cross-cutting workflow guardrails

These rules apply across commands unless a specific command explicitly overrides them.

### Routing memory (always consult)
Before running a command, use `TASK_STATE.md` as operational routing memory:
- read `Last completed step` (command + summary)
- read current blockers and the recommended next step
- confirm the command still matches the real current need

### Command-less input (triage before answering)
When the user's turn invoked no command (no `/<name>`, no `<command-name>` tag, no `# <name> ... Act as` command body), do not silently no-op. Default to answering plainly, and propose a command only when the intent clearly matches one bucket below. Propose exactly one, and defer to `what-next`'s single-best-command logic rather than restating it. The buckets resolve the three empty states explicitly so a proposed command never refuses on entry:
- No `projects/<client>__<project>/` folder yet, and the input is new-work intent: propose `project-bootstrap`.
- A project folder exists but no `active/` task, and the input is new-work intent: propose `task-init`.
- An active task exists and the input is a genuine observation, question, hypothesis, or concern: `capture-observation` is eligible. It requires an active task folder, so confirm the folder exists before proposing it.
- An active task exists and the input is a canonical decision or a course correction: propose `decision-interview` or `direction-adjust`.
- The input is a concrete observed failure such as a stack trace, a failing test, or an alert: propose `incident-triage`.
- The input is a navigation question (for example "what do I do now"): propose `what-next`.
- Pure chatter, one-line factual questions, and casual asides: answer plainly and propose nothing.

The last item is the default, not an exception. Propose only on a clear bucket match; everything else gets a plain answer with no proposal. This rule writes nothing on its own. Any capture happens one step later, only if the user accepts the proposed command, which then runs its normal substrate-write protocol. Command-less input is routed, not persisted (ADR-0050).

### Official command names (routing integrity)
- Valid command identifiers are exactly the basenames of files in the workflow repository `commands/` directory, **without** the `.md` suffix (example: `impact-analysis`, `implementation-plan`).
- Do not invent command names or aliases that do not match a file in `commands/` (invalid examples: `task-plan`, `plan`, `execute-task`).
- When recommending the next step, the `Run now` line must use that same basename after the slash (example: `Run now: /impact-analysis`).
- A manual activity is not a Fhorja command. When the next step is a manual action (running the app, a shell or CLI command like `npm run ios`, a device or browser test session, a dashboard check), describe it as a manual step in prose; never emit it as a `Run now: /<name>` line. The `Run now` line is reserved for real `commands/` basenames, so routing a manual activity through it (for example `Run now: /device-verify` when `device-verify` is a manual on-device test session, not a command) is invalid output. When in doubt whether the next step is a command, check `commands/` for that basename: present it as `Run now` only if the file exists, otherwise as a manual step.

### Material change (definition)
A command should only rewrite task-memory files when it produces a **material change**, meaning at least one of:
- new confirmed facts affecting correctness
- new or resolved blockers
- changed constraints/invariants
- new or clarified canonical decisions (when allowed by that command’s rules)
- changed plan/slices/validation intent
- changed risk posture or test/rollout consequences
- changed **work complexity** assessment for the next step (when `TASK_STATE.md` tracks it)
- changed recommended next step / closure target
- product code/test changes (for execution commands)

### No-op execution rule
If rerunning the command would **not** produce a material change:
- do not churn task-memory files
- return an explicit **no-op** outcome
- still emit a short **NO_OP trace note** in the command output (not necessarily a file rewrite) so reruns are auditable
- recommend the smallest next official command with the standard ending format

### Proposal vs approved persistence
- Do not silently change semantic intent in `DECISIONS.md` without explicit user approval in-chat or authoritative artifact approval.
- When needed, label content as **PROPOSED** and route to explicit confirmation or the correct hardening command.
- The user has three valid paths to turn `PROPOSED` artifacts into `APPLIED` writes (ADR-0024 adendum to ADR-0001): (a) re-run the source command in Agent mode; (b) run `/approve-proposed` once after any turn that emitted PROPOSED files, which reads the prior assistant turn and persists every PROPOSED file atomically with a locked five-line recap; or (c) copy-paste the proposed content manually. Commands MUST NOT pretend the user has already approved when no signal was given; commands MUST persist when a valid lock signal is given (e.g., `/decision-interview` recognizing `D<N> [LOCK]` picks per its Operating rules `LOCK-pick recognition`).
- `### Artifact changes` is the single proposal surface per turn. Never nest PROPOSED blocks (no `## PROPOSED X.md block` or `## PROPOSED X.md deltas` headers under `### Artifact changes`); inline content goes directly under each file's bullet. The shared block `commands/_shared/artifact-changes-default.md` is the canonical source.

### Substrate peer ownership (per ADR-0034)

Commands, personas (SKILL.md files), and Epic J fleet workers are peers sharing four canonical substrate files: `TASK_STATE.md`, `DECISIONS.md`, `IMPLEMENTATION_PLAN.md`, `SOURCE_OF_TRUTH.md`. Every H2 section has exactly one OWNER (writes via Edit/Write) plus explicit CO-WRITERS (propose-only via PROPOSED blocks). Conflict resolution: REFUSE + Handoff routing to owner; no silent last-write-wins. Workers dispatched by orchestrators MUST conform to the canonical worker contract in `commands/_shared/worker-contract.md`. Full ownership matrix, read/write contracts, conflict rules, and audit-trail schema in `wos/substrate-peers.md` (lazy-loaded; activation `model_decision`).

### External web access (centralized)

External web access is centralized. `capture-references` is the canonical entry point and the only general-purpose web-fetch command. A small, explicit set of scoped peers may also fetch the web, each for a narrow purpose and each required to funnel what it fetches into `REFERENCES.md` in `capture-references` format so the audit trail stays single-sourced.

Authorized-command set (the only commands that may fetch web pages or run web search):
- `capture-references`: the canonical entry point; general external research and reference capture. Its fetch mechanisms are web page fetch, web search, and (per ADR-0086) an issue-tracker CLI or host API (for example `gh issue view --comments`) for a deep read of a GitHub or GitLab issue or PR comment thread. This names a fetch mechanism on the existing authorized fetcher; it does not widen the authorized-command set, and the deep read funnels into `REFERENCES.md` in the same capture-references format.
- `stack-recommend`: stack and version research for a recommendation (official docs, release pages, AAA-company stack disclosures). Funnels every cited source into `REFERENCES.md`.
- `stack-currency-check`: verification of current framework patterns and version currency (the greenfield-clause verifier). Funnels verified sources into `REFERENCES.md` and the project-level `CURRENT_PATTERNS.md` cache.
- `feature-library-scout`: per-feature library discovery and adoption-signal gathering (the stack's package registry: npm, PyPI, crates.io, Go, Maven, etc.; plus source-host repos, official docs, AAA-company posts). Funnels every cited source into `REFERENCES.md` (ADR-0045).
- `feature-library-scout-fleet`: the orchestrator-workers variant of `feature-library-scout`. The orchestrator is the authorized fetcher and the sole writer; workers do not fetch (they read captured signals from `REFERENCES.md`). Funnels every cited source into `REFERENCES.md` (ADR-0045).

Rules:
- Commands outside the authorized set above MUST NOT perform ad-hoc web fetches or web searches. They consume external references through `projects/<client>__<project>/REFERENCES.md` (project-level memory). In particular `external-research` and `external-research-fleet` synthesize from sources already in `REFERENCES.md`; when new URLs must be discovered, they route that discovery through `capture-references` rather than fetching directly.
- Every authorized peer MUST persist the sources it fetches into `REFERENCES.md` (capture-references entry format, deduplicated by URL), so a fetch by a peer is indistinguishable in the audit trail from a `capture-references` run.
- When a command outside the set needs external context not yet present in `REFERENCES.md` and the missing context blocks safe progress, route the user to `capture-references` first via the standard Handoff, instead of fetching ad-hoc.
- When the missing external context is not blocking, capture it as a `concern` or `question` via `capture-observation` and continue.
- This rule applies even when the model has built-in web tools available; the workflow contract supersedes tool availability.
- Existing internal sources (framework manuals on disk, internal wikis available locally, repo-local READMEs, vendored docs) are NOT "external web" and continue to be read directly under the regular Evidence priority.

Motivation behind centralizing external web access (audit trail; no silent re-fetching; no research-fishing; codebase plus task memory plus project memory drive decisions; external findings become reusable project memory) is documented in `wos/cross-cutting-workflow-guardrails.md` → `### Why external web access is centralized`. The Rules above remain authoritative.

### Sequencing heuristics (by phase)

Phase-grouped routing heuristics (Discovery → Contract → Planning → Execution → Delivery → Debug) live in `wos/cross-cutting-workflow-guardrails.md` → `### Sequencing heuristics (by phase)`. Most routing decisions are resolved by the `## Command roles` index plus `## Default workflow`; consult the lazy file when phase ordering across multiple commands is unclear.

---

## Command categories

Navigation note:
- this section is a grouping aid; authoritative command-level behavior lives in `## Command roles`

### Project initialization
- `project-bootstrap`
- `capture-references`

### State and navigation
- `task-init`
- `task-init-fleet`
- `task-workspace`
- `sync-task-state`
- `state-reconcile`
- `resume-from-state`
- `what-next`
- `portfolio-review`
- `workflow-guide`
- `im-stuck`
- `incident-triage`
- `capture-observation`
- `compact-task-memory`
- `approve-proposed`
- `autonomous-board`

### Design system (WOS-UI)
- `design-bootstrap`
- `component-spec`
- `screen-spec`
- `image-to-spec`
- `journey-map`
- `pattern-doc`
- `design-spec-review`
- `foundation-audit`
- `extract-foundations-from-screens`
- `atom-audit`
- `atom-audit-fleet`
- `screen-spec-fleet`
- `inventory-snapshot`

### Discovery and scoping
- `code-locate`
- `code-context-map`
- `impact-analysis`
- `invariants-and-non-goals`
- `targeted-questions`
- `problem-framing`
- `decision-interview`
- `external-research`
- `external-research-fleet`
- `stack-recommend`
- `stack-currency-check`
- `feature-library-scout`
- `feature-library-scout-fleet`
- `api-contract-review`
- `graphql-contract-review`
- `frontend-architecture-review`
- `frontend-system-design`
- `backend-system-design`
- `jtbd-switch-interviewer`
- `color-contrast-architect`
- `godot-scene-plan`

### Database context
- `db-context-supabase`
- `db-context-postgres`

### Contract and decision hardening
- `resolve-contract-gaps`
- `contract-signoff`
- `direction-adjust`

### Planning and validation
- `implementation-plan`
- `approve-plan`
- `test-strategy`
- `self-critique-and-revise`
- `verify-against-rubric`
- `verify-against-rubric-fleet`
- `ai-feature-eval-harness`
- `slo-define`
- `release-plan`
- `rls-auth-boundary-auditor`
- `migration-safety-steward`
- `a11y-audit`
- `performance-budget`

### Execution and closure
- `implement-approved-slice`
- `implement-fleet`
- `post-deploy-verifier`
- `postmortem-author`
- `implement-slice-complement`
- `slice-closure`
- `task-close`
- `harvest-session-learnings`
- `review-hard`
- `repo-consistency-sweep`
- `apply-sweep-triage`
- `security-review`
- `skill-vet`
- `mcp-server-vet`
- `where-we-at`
- `autonomous-run`
- `godot-runtime-verify`
- `app-runtime-verify`

### Delivery and communication
- `pr-package`
- `pr-feedback-ingest`
- `post-review-pivot`
- `branch-commit`
- `team-update`
- `delivery-asset`

### Prompt tooling
- `prompt-shape`

---

## Command roles

Compact routing index with Role + Next for each of the <!-- count:commands -->94<!-- /count --> commands. For full per-command detail (distinctness rules, guard rails, multi-repo hints, edge-case routing), load `wos/command-roles.md`.

### project-bootstrap
Role: zero-state entry for a new project; creates `projects/<client>__<project>/` and project-level memory (`PROJECT_CHARTER.md`, `REFERENCES.md`).
Next: `task-init`, `capture-references`.

### task-init
Role: mandatory start of every task; creates task folder and required base files; seeds from `PROJECT_CHARTER.md` when present.
Next: `impact-analysis`.

### task-workspace
Role: opt-in, git-gated provisioning of a durable per-task git worktree and `task/<task-slug>` branch (ADR-0074); records the `## Workspace` section in `SOURCE_OF_TRUTH.md`; runs standalone to retrofit an in-flight task. Distinct from `implement-fleet` slice worktrees; teardown is `task-close`.
Next: `impact-analysis` (or the task's discovery step).

### task-init-fleet
Role: orchestrator-workers variant of `task-init` per ADR-0034 (J.8 PILOT). Opus orchestrator decomposes a multi-stream brief into N >= 3 independent sub-tasks; dispatches N Sonnet workers; each creates one task folder; orchestrator merges INITIATIVE_INDEX.md. Use when the brief contains N >= 3 logically independent work streams (multi-repo migrations, parallel feature kickoffs).
Next: per-sub-task `impact-analysis` or per declared complexity tier; overall `where-we-at`.

### code-locate
Role: read-only code search returning up to 10 candidate paths with `HIGH` / `MEDIUM` / `LOW` confidence and explicit search trail.
Next: `impact-analysis`, `targeted-questions`, `incident-triage`.

### code-context-map
Role: opt-in; generates a ranked, token-budgeted, layered Markdown structural map (imports, signatures, invoke edges, typed db/http/queue boundaries), or a seed-anchored import chain from one file (`chain:<seed-file>`, depth via `max-hops` or `all`, cycle-guarded), into a gitignored folder inside the target repo; optional self-contained `MAP.html` for humans; regenerate-on-invoke; ripgrep by default with parser augmentation only if already present, no embeddings; single-pass by default with a consent-gated fleet past a context-window threshold. A grep seed, not an authoritative index (ADR-0027, ADR-0057).
Next: `impact-analysis`, `code-locate`, `what-next`.

### impact-analysis
Role: bounded technical understanding and blast-radius assessment; per-repo subsections when multi-repo.
Next: `invariants-and-non-goals`, `targeted-questions`, `decision-interview`, `implementation-plan`.

### invariants-and-non-goals
Role: define what must not change; lock boundaries before planning or implementation.
Next: `targeted-questions`, `decision-interview`, `implementation-plan`.

### targeted-questions
Role: ask the minimum factual questions needed to proceed safely.
Next: `decision-interview`, `implementation-plan`, `resolve-contract-gaps`.

### decision-interview
Role: ask the minimum decision-level questions that affect behavior, data, or rollout safety.
Next: `resolve-contract-gaps`, `implementation-plan`.

### problem-framing
Role: optional pre-task intake (Phase 0.5); socratic one-question-at-a-time framing that questions whether the objective is the right problem and writes a task-level BRIEF.md.
Next: `task-init` (or `project-bootstrap` when the project is not yet bootstrapped).

### db-context-supabase
Role: opt-in Supabase schema snapshot via MCP; creates/regenerates `DB_CONTEXT.md`; read-only introspection.
Next: prior step's command; defaults to `impact-analysis` or `implementation-plan`.

### db-context-postgres
Role: opt-in generic Postgres schema snapshot via `psql`/`pg_dump` (GCP Cloud SQL, GKE Autopilot, self-hosted, RDS); creates/regenerates `DB_CONTEXT.md` with tables, indexes, FKs, RLS policies (optional), extensions, server version; read-only introspection only. Distinct from `db-context-supabase` (which uses Supabase MCP); use this when target is non-Supabase Postgres.
Next: prior step's command; defaults to `impact-analysis` or `implementation-plan`.

### resolve-contract-gaps
Role: turn ambiguity into canonical implementation-safe decisions.
Next: `contract-signoff`, `implementation-plan`.

### contract-signoff
Role: harden wording and remove interpretation risk from approved decisions.
Next: `implementation-plan`.

### direction-adjust
Role: record a mid-task course correction from the user's own work (not external review) as a numbered `D-N` entry in `DECISIONS.md`.
Next: `implement-approved-slice`, `implementation-plan`, `state-reconcile`, `decision-interview`.

### implementation-plan
Role: define safe phases or slices before any implementation; assign **work complexity** per slice; emit per-slice `Scope` + `Depends-on` and an `## Execution waves` section.
Next: `approve-plan` (default lock step when the plan is complete with no clarification markers), `test-strategy`, `sync-task-state`. Execution (`implement-fleet` / `implement-approved-slice`) is reached through the approval gate, routed waves-aware per ADR-0042.

### test-strategy
Role: define the smallest high-signal test plan.
Next: `sync-task-state`, `implement-approved-slice`.

### sync-task-state
Role: update operational memory after meaningful progress or decision changes; keep work complexity aligned. Incremental, append-only, never lossy.
Next: depends on the new state.

### compact-task-memory
Role: lossy compaction of `TASK_STATE.md` when task memory has grown beyond a useful working size; preserves canonical decisions and recommended next step verbatim while dropping stale facts, resolved questions, and mitigated risks. Writes a `## Compaction history` audit entry. Reversible only via git. Distinct from `sync-task-state` (incremental) and `state-reconcile` (drift repair, no shrinking).
Next: `sync-task-state`, `resume-from-state`, `what-next`; or the next planned slice.

### approve-proposed
Role: atomically persist every file marked `PROPOSED` in the most recent prior assistant turn's `### Artifact changes` block. Single-command batch-persist idiom that closes the two-step latency in ADR-0001. Agent mode (writes files by definition). Locked five-line recap (Persisted / Skipped already current / Skipped incomplete inline / Skipped path outside scope / Skipped no PROPOSED marker). Conflict-with-locked-decision rollback (FAILs the batch if any proposal contradicts `TASK_STATE.md ## Canonical decisions`). Three explicit no-op cases. Does NOT replace ADR-0001; users can still re-run source commands in Agent mode or copy-paste manually.
Next: `sync-task-state`, `where-we-at`, or whichever command produced the original proposals.

### approve-plan
Role: atomically lock IMPLEMENTATION_PLAN.md as the approved execution baseline. Symmetric counterpart to approve-proposed but plan-specific (not for arbitrary PROPOSED artifacts). Refuses with NO_OP_TRACE when the plan has `[NEEDS CLARIFICATION:]` markers, when it was not last touched by implementation-plan / self-critique-and-revise, or when already approved. Appends `## Approval log` entry and stamps TASK_STATE.md. Emits the execution handoff waves-aware per ADR-0042.
Next: `implement-fleet` when the first remaining wave has size 2 or more with `Scope` and `Depends-on` declared; otherwise `implement-approved-slice` for the first slice.

### state-reconcile
Role: cross-check `TASK_STATE.md` against other task artifacts; propose minimal patches when drift is material. Also runs an opt-in read-only memory-lint mode (ADR-0053) that reports memory-hygiene issues (dead relative cross-links, orphaned `SLICES/` files, stale facts) and writes nothing, backed by `scripts/memory-lint.sh` for the deterministic checks.
Next: `sync-task-state`, `what-next`, `resume-from-state`; upstream contract/plan commands when drift is `BLOCKING`.

### implement-approved-slice
Role: canonical single-slice execution path and the fleet fallback; minimal, bounded implementation of a single approved slice.
Next: waves-aware and terminal-safe per ADR-0042 -- `implement-fleet` when remaining `## Execution waves` show a wave of size 2 or more with `Scope` + `Depends-on`; `implement-approved-slice` for the next sequential slice; `sync-task-state` for the LOW/MEDIUM inline-close path; `slice-closure` (HIGH or unverifiable inline) or `review-hard`; `where-we-at` or `task-close` when this was the last slice.

### implement-fleet
Role: orchestrator-workers variant of `implement-approved-slice` per ADR-0041 (PILOT). Computes parallelizable waves from `IMPLEMENTATION_PLAN.md` `Scope` + `Depends-on`, validates file-scope disjointness, runs one worktree-isolated worker per slice per wave, and gates each wave on an integrated build + typecheck + test. Use when the slice DAG has a wave of size >= 2; falls back to `implement-approved-slice` when the DAG is a chain. When the active task is worktree-isolated (a `## Workspace` section per ADR-0074), slice worktrees branch off the task branch, not the repo base, so the two worktree layers stay consistent (D-3).
Next: `slice-closure`, `pr-package`, `implement-approved-slice` (for held or failed slices).

### implement-slice-complement
Role: bounded **micro-deltas** after slice work (polish, small fixes) still inside the same slice intent.
Next: `slice-closure`, `sync-task-state`, `review-hard`, `implement-approved-slice`.

### slice-closure
Role: determine whether the current slice is actually ready to close; for single-slice tasks may route directly to delivery.
Next: `sync-task-state`, next slice, `pr-package`, `where-we-at`, `task-close` (when the whole task is ending).

### task-close
Role: terminal task lifecycle transition; symmetric counterpart to `task-init`. Verifies the Fhorja done-conditions, sets `TASK_STATE.md` final, and moves the task folder `active/` -> `archive/`. Distinct from `slice-closure` (slice scope) and `where-we-at` (assessment only); the only official way to close a whole task.
Next: `delivery-asset`, `pr-package`, `task-init` (for a spun-off follow-up), or none.

### harvest-session-learnings
Role: on-demand, session-wide retrospective sweep; the produce-side of ADR-0017. Reads the session and task artifacts, judges what generalizes, and appends anchored, de-duplicated entries to the task's `LEARNINGS.md` (append-only; never edits history). Distinct from `capture-observation` (single verbatim note), `slice-closure` (per-slice inline learnings), and `task-close` (terminal move).
Next: `slice-closure`, `task-close`, `sync-task-state`, or the prior in-progress command.

### review-hard
Role: focused pre-PR engineering risk check; not a replacement for external review systems.
Next: `slice-closure`, `repo-consistency-sweep`, `where-we-at`, `pr-package`.

### repo-consistency-sweep
Role: proactive defect-class detection against a curated bug-class library; handles convention drift, ordering bugs, type-safety gaps, and CWE-grounded patterns before PR packaging. Distinct from `review-hard` (which does design/correctness/safety risk) and `pr-feedback-ingest` (which consumes external feedback after PR open).
Next: `pr-package`, `implement-slice-complement` (if P0 finding), `apply-sweep-triage` (for triage persistence).

### apply-sweep-triage
Role: persist user triage decisions (apply, decline, discuss) from a SWEEP snapshot into project-level `REVIEW_PREFERENCES.md` so future sweeps suppress declined findings.
Next: `pr-package`, `repo-consistency-sweep` (re-run after fixes).

### security-review
Role: dedicated security review covering threat modeling, OWASP ASVS L1 checklist, auth/authz flow tracing, and operational security reminders. Distinct from `review-hard` (general risk) and `repo-consistency-sweep` (pattern matching). Grounded in OWASP ASVS 5.0 (17 chapters, 350 requirements at L1).
Next: `implement-slice-complement` (if P0 security finding), `pr-package`, `repo-consistency-sweep`.

### skill-vet
Role: read-only safety inspection of a third-party agent skill or plugin before install; reads every file (not just SKILL.md), compares declared vs actual behavior, scans for exfiltration, secret access, out-of-directory and agent-config writes, shell execution, and hidden Unicode, and returns INSTALL / SANDBOX / DECLINE for a human to approve (ADR-0046). Distinct from `security-review` (own-code attack surface) and `repo-consistency-sweep` (first-party patterns).
Next: `capture-references` (if the source is a URL not yet captured), then human approval of the verdict.

### mcp-server-vet
Role: read-only safety inspection of a third-party MCP server before it is added to a config or trusted; enumerates the config entry and declared tool surface, compares declared vs actual, scans for tool-description poisoning, over-broad or undeclared scopes, egress and credential access, agent-config writes, shell execution, and hidden Unicode, and returns ADD / SANDBOX / DECLINE for a human to approve (ADR-0070). Distinct from `skill-vet` (third-party skill or plugin directories) and `security-review` (own-code attack surface).
Next: `capture-references` (if the source is a URL not yet captured), then human approval of the verdict.

### self-critique-and-revise
Role: evaluator-optimizer for draft artifacts (IMPLEMENTATION_PLAN.md, SLICES/*.md, PR_PACKAGE.md); runs a locked per-artifact-type rubric and emits both a critique and a revised draft. Distinct from `review-hard` (judges; no revision) and `direction-adjust` (records corrections; no artifact revision).
Next: artifact's downstream consumer (`implement-approved-slice` after revising a slice; `pr-package` after revising PR_PACKAGE.md; `decision-interview` if the critique surfaced a missing decision).

### verify-against-rubric
Role: spawn a stateless sub-agent (Claude Code Task tool or equivalent) with ONLY the artifact + locked rubric (no TASK_STATE.md, no DECISIONS.md, no prior history). Returns structured per-criterion verdict + overall classification (satisfied / needs_revision / failed). Distinct from `self-critique-and-revise` (same-context, in-thread) and `review-hard` (general risk review). Per ADR-0033; Anthropic Outcomes pattern (2026-05-06; +10pp success vs same-context critique). Persists to VERIFICATION_LOG.md.
Next: `pr-package` (on satisfied), `implement-slice-complement` (on needs_revision), `direction-adjust` or `decision-interview` (on failed).

### verify-against-rubric-fleet
Role: orchestrator-workers generalization of `verify-against-rubric` per ADR-0034 (J.10 PILOT). Sonnet orchestrator dispatches N >= 4 stateless Sonnet workers in parallel; each receives ONE artifact + the SAME locked rubric (no sibling artifacts, no shared context). Orchestrator merges per-artifact verdicts into one VERIFICATION_LOG.md cohort entry with aggregate counts AND failure clustering (criteria failing >= 50% are SYSTEMIC -> likely rubric/spec issue, not per-artifact). Closes same-context bias at cohort scale.
Next: `decision-interview` on rubric (when SYSTEMIC clusters present), `direction-adjust` on spec (when SYSTEMIC + upstream), `implement-slice-complement` per artifact (LOCALIZED).

### where-we-at
Role: macro checkpoint against the approved plan; broader than slice closure; for multi-slice or longer tasks.
Next: `what-next`, `implement-approved-slice`, `implement-slice-complement`, `pr-package`.

### autonomous-run
Role: controller for the autonomous delivery track (ADR-0044); drives an approved waved plan through bounded execution behind two human gates and a runtime governor; reuses `implement-approved-slice` as single writer; emits PROPOSED diffs only and never merges.
Next: `approve-proposed`, `review-hard`, `implement-approved-slice` (for an escalated slice the human approves).

### resume-from-state
Role: reconstruct task truth after context loss or new session start.
Next: `what-next`, command appropriate to the resumed phase.

### what-next
Role: fast routing answer; short and operational.
Next: depends on phase.

### portfolio-review
Role: read-only cross-task board across every active task in all projects; runs `scripts/portfolio-review.sh` to classify each task (done-unclosed / blocked / my-move / stale / in-flight) and recommends one action per row. Portfolio-level (no single active task); never writes. Distinct from `what-next` (routes one active task) and `where-we-at` (deep checkpoint of one task).
Next: per row, the recommended action (`task-close` / `where-we-at` / `approve-plan` / the unblocking command).

### workflow-guide
Role: pedagogical explanation of current phase and next 2-3 steps; for users learning the workflow.
Next: depends on phase.

### im-stuck
Role: recovery from loops, false progress, stale state, or phase confusion.
Next: depends on diagnosis.

### incident-triage
Role: triage a concrete observed technical failure; classify (`REGRESSION` / `NEW_BUG` / `CONFIG` / `EXTERNAL_DEPENDENCY` / `REPRODUCIBILITY` / `DIAGNOSTIC_INSUFFICIENT`) and recommend fix size (`HOTFIX` / `SLICE` / `INVESTIGATION` / `ESCALATE`).
Next: `branch-commit` + `pr-package` (HOTFIX); `implement-approved-slice` or `implementation-plan` (SLICE); `impact-analysis` or `targeted-questions` (INVESTIGATION); `capture-observation` + `team-update` (ESCALATE); `decision-interview` on locked-decision conflict.

### capture-references
Role: append external references to project-level `REFERENCES.md` with freshness metadata; deduplicates by URL.
Next: prior command; `task-init` after fresh bootstrap; `what-next` when uncertain.

### capture-observation
Role: lean append of a single observation, question, hypothesis, or concern to `TASK_STATE.md` without disrupting in-progress work.
Next: prior command; `what-next` fallback.

### autonomous-board
Role: read-only board-of-record view for an `autonomous-run` task (ADR-0044 D7); maps slices and waves to to-do / in-progress / escalated / proposed / done from the Fhorja artifacts only; no external tracker, no writes.
Next: `autonomous-run`, `approve-proposed`, `what-next`.

### pr-package
Role: prepare delivery artifacts based on the real diff vs an explicit base branch; per-repo when multi-repo.
Next: depends on review outcome.

### pr-feedback-ingest
Role: consolidate PR review signals (Greptile, CI, bots, humans) into a traceable matrix aligned with `DECISIONS.md`, `IMPLEMENTATION_PLAN.md`, `TASK_STATE.md`.
Next: `implement-approved-slice`, `implement-slice-complement`, `implementation-plan`, `sync-task-state`, `state-reconcile`, `post-review-pivot`, `decision-interview`, `pr-package`.

### post-review-pivot
Role: absorb PR or team feedback that changes direction while keeping the same task thread; produce pivot digest.
Next: `targeted-questions`, `decision-interview`, `resolve-contract-gaps`, `contract-signoff`, `implementation-plan`, `test-strategy`, `implement-approved-slice`, `state-reconcile`, `pr-package`.

### branch-commit
Role: lightweight naming support grounded in the real `git diff`; produces branch name + ≤3-line commit message.
Next: `pr-package`.

### team-update
Role: short status communication for any team channel (Slack, Discord, Teams, email, PR comment, standup); channel-portable.
Next: depends on context.

### delivery-asset
Role: outward-facing artifact (executive summary, release note, slack/email post, demo script, blog draft) per audience and per format; grounded in `TASK_STATE.md` / `DECISIONS.md` / `IMPLEMENTATION_PLAN.md` / `PR_PACKAGE.md`; never leaks workflow paths into the public surface.
Next: `team-update`, `pr-package`, or `state-reconcile` (when grounding revealed drift).

### external-research
Role: synthesize multiple external sources into a task-scoped `EXTERNAL_RESEARCH.md`; each source goes through `capture-references` first; every claim cites a `REFERENCES.md` entry; the model's recommendation is visually separated from the source-grounded analysis.
Next: `decision-interview` (when the synthesis surfaced new decision questions) or `implementation-plan` (when the synthesis closed the question and the path is clear).

### external-research-fleet
Role: orchestrator-workers variant of `external-research` per ADR-0034 (J.9 PILOT). Promotes inline Mode C delegation (ADR-0032) to a first-class orchestrator. Sonnet orchestrator dispatches N >= 3 Sonnet workers (one per angle or source-group); merges into one EXTERNAL_RESEARCH.md with explicit ADR-0018 reconciliation (REINFORCING / CONTRADICTING / DIFFERENT-FRAMING) and one consolidated recommendation.
Next: `decision-interview` (CONTRADICTING groups surfaced) or `implementation-plan` (path concluded).

### stack-recommend
Role: research and recommend a technology stack for the active project; consults official docs for latest stable versions, quality articles, and AAA company practices; accepts user-provided reference links; produces `STACK_RECOMMENDATION.md` with versioned picks, compatibility matrix, trade-offs, and confidence per layer; captures sources into `REFERENCES.md`.
Next: `implementation-plan` (stack decided), `decision-interview` (trade-offs need user input), `project-bootstrap` (feeding a new project initialization), `feature-library-scout` (per-feature library choices below the chosen layers, ADR-0045).

### stack-currency-check
Role: verify the patterns about to be used for a given framework+version are current per official docs; caches the result as project-level `CURRENT_PATTERNS.md`; prevents the "gold-standard audit" anti-pattern where training-data defaults ship outdated patterns. Distinct from `stack-recommend` (choosing the stack) and `capture-references` (arbitrary URL fetch).
Next: `implementation-plan`, `impact-analysis`, `decision-interview`.

### feature-library-scout
Role: discover and vet the community-validated best-in-class library for each per-feature problem in the product (lists, camera, forms, keyboard, sheets), ranked by adoption signal (registry downloads, dependents, last release, stars and trend, maintenance, framework/platform fit) relative to the stack's ecosystem, across five angles (internet, product repo, package registry, AAA-company practices, reference repos); writes `FEATURE_LIBRARIES.md`; funnels sources into `REFERENCES.md`. Stack-agnostic (any registry: npm, PyPI, crates.io, Go, Maven). One granularity below `stack-recommend` (layers); recommendations are optional guidance (ADR-0045).
Next: `decision-interview` (a pick needs the maintainer's ruling), `implementation-plan` (picks clear), `feature-library-scout-fleet` (deep multi-problem sweep).

### feature-library-scout-fleet
Role: orchestrator-workers variant of `feature-library-scout` per ADR-0038 and ADR-0045. Decomposes the product feature set into N >= 3 feature problems; the orchestrator (authorized fetcher, sole writer) captures adoption signals into `REFERENCES.md`, then dispatches one Sonnet worker per problem; each worker ranks candidates by adoption signal grounded in captured sources and returns a typed `StructuredOutput` payload; the orchestrator merges into one `FEATURE_LIBRARIES.md` and runs the orphan-scan gate. Workers never fetch or write.
Next: `decision-interview` (a pick needs the maintainer's ruling) or `implementation-plan` (picks clear).

### api-contract-review
Role: pre-implementation review of an API contract (endpoints, request/response shapes, error codes, auth model) for naming consistency, versioning, pagination, idempotency, and alignment with existing endpoints. Distinct from `review-hard` (post-implementation risk) and `repo-consistency-sweep` (pattern matching on written code).
Next: `implementation-plan`, `decision-interview`, `impact-analysis`.

### graphql-contract-review
Role: pre-implementation review of a GraphQL schema and BFF contract against a GraphQL-specific checklist (schema shape and nullability, errors-as-data unions, N+1 and DataLoader, query cost and depth, cursor connections, federation entity ownership, breaking-change gate, BFF token posture and thinness, partial-failure degradation). Distinct from `api-contract-review` (REST and HTTP), `review-hard` (post-implementation risk), and `repo-consistency-sweep` (pattern matching on written code).
Next: `implementation-plan`, `decision-interview`, `impact-analysis`.

### frontend-architecture-review
Role: design-time review of a frontend architecture at scale with a micro-frontend adopt/don't-adopt gate first (default: prefer a modular monolith). Checks team-and-domain boundaries, independent deployability, governed shared dependencies, design-system sharing, runtime isolation, cross-app communication, routing and composition tier, rendering strategy, state at scale, a performance budget across the composition, and governance and failure handling. Distinct from `frontend-system-design` (designs one system) and the contract reviews.
Next: `implementation-plan`, `decision-interview`, `impact-analysis`.

### frontend-system-design
Role: produce a staff-grade frontend system-design RFC (12 sections: problem, requirements, architecture, data model, API and interface contract, rendering and delivery, state management, performance, accessibility, security, rollout, trade-offs) for the active task, covering web and mobile; a default RFC mode plus an `--interview` mode (RADIO-aligned). Capability-routed, not React-specific. Distinct from `problem-framing` (frames the problem pre-task), `implementation-plan` (slices the build), and `api-contract-review` (reviews one API contract).
Next: `implementation-plan`, `decision-interview`, `approve-plan`.

### backend-system-design
Role: produce a staff-grade backend system-design RFC (12 sections: problem, requirements, architecture, data model and storage, API contract, caching, scaling and bottlenecks, reliability and SLOs, security, observability, rollout and migration, trade-offs) for a new service, endpoint, or backend feature. Capability-routed and scale-honest (no distributed-systems machinery without a stated requirement). The backend sibling of `frontend-system-design`; composes with `slo-define`, `performance-budget`, `api-contract-review`, `migration-safety-steward`, and `release-plan`. Distinct from `impact-analysis` (blast radius of an existing change) and `api-contract-review` (one API contract in isolation).
Next: `implementation-plan`, `decision-interview`, `approve-plan`.

### godot-scene-plan
Role: plan the Godot scene and node structure for a 2D game feature before any GDScript: the scene tree and node types, autoloads (singletons), signal wiring, the input map, and the resources and sub-scenes to create. Produces `GODOT_SCENE_PLAN.md`. Capability-routed and MCP-agnostic (names no server). Part of the Godot 2D-mobile game-dev cluster (ADR-0069). Distinct from `problem-framing` game-design mode (frames the game), `implementation-plan` (slices the build), `impact-analysis` (blast radius), and `godot-runtime-verify` (verifies a running scene).
Next: `implementation-plan`, `decision-interview`, `targeted-questions`.

### godot-runtime-verify
Role: verify a built Godot 2D scene at runtime; run it (press-play or headless), read the captured debugger output, classify runtime errors against a Godot taxonomy, and decide a PASS/FAIL runtime gate for the slice's acceptance behavior. The run's real output IS the Layer-1 runtime evidence (ADR-0048); MCP-agnostic about the runner; verifies and routes fixes, never writes code. Part of the Godot 2D-mobile cluster (ADR-0069). Distinct from `godot-scene-plan` (plans the scene), `implement-approved-slice` / `implement-slice-complement` (write or fix code), and `incident-triage` (sizes a fix from a failure).
Next: `slice-closure` / `review-hard` (on PASS), `incident-triage` / `implement-slice-complement` (on FAIL).

### app-runtime-verify
Role: verify a built mobile/app runtime; run it (device, emulator, or headless), read the captured runtime output (native logcat / device log and/or the Metro/JS console), classify against a per-stack taxonomy (RN/Expo first adapter: NATIVE_CRASH, NAVIGATION_TEARDOWN, JS_ERROR, and more), and decide a PASS/FAIL runtime gate for the slice's acceptance behavior. The run's real output IS the Layer-1 runtime evidence (ADR-0048); capability-routed and MCP-agnostic; verifies and routes fixes, never writes code. Reads `wos/rn-expo-runtime-evidence.md` for the capture path (ADR-0087). Distinct from `godot-runtime-verify` (Godot scenes), `implement-approved-slice` / `implement-slice-complement` (write or fix code), and `incident-triage` (sizes a fix from a failure).
Next: `slice-closure` / `review-hard` (on PASS), `incident-triage` / `implement-slice-complement` (on FAIL).

### design-bootstrap
Role: zero-state entry for design system work; reads Figma via MCP, extracts tokens, scaffolds foundation docs, creates component/screen inventories, bootstraps directory structure and OPEN_QUESTIONS.md.
Next: `component-spec`, `screen-spec`.

### component-spec
Role: generates a 15-section component spec from a Figma component using MCP tools (anatomy, variants, sizes, states, a11y, motion, haptics, platform, security, performance, API, usage, anti-patterns).
Next: next component from inventory, `screen-spec`, `journey-map`.

### screen-spec
Role: generates a 12-section screen spec from a Figma frame (layout sketch, components used, spacing, data deps, copy, a11y, interactions, error states).
Next: next screen from inventory, `journey-map`.

### image-to-spec
Role: generates a spec from a raw image (no Figma source) in `--component` (COMPONENT_SPEC-shaped) or `--screen` (SCREEN_SPEC-shaped) mode, auto-detecting when no flag is given; marks every observation `(proposed)` since there is no source of truth. Distinct from `component-spec` / `screen-spec` (Figma-sourced) and from `generate_figma_design` (image into Figma).
Next: `component-spec` / `screen-spec` (upgrade against Figma when available), `design-spec-review`, `implementation-plan`.

### journey-map
Role: documents a user journey across 3+ screens (outcome, flow diagram, critical states, a11y, security, performance).
Next: `pattern-doc`, `implementation-plan`.

### pattern-doc
Role: documents a reusable UX pattern (empty state, error handling, confirmation, loading skeleton) applicable across projects.
Next: `implementation-plan`, next pattern.

### design-spec-review
Role: verifies implementation against spec doc (10 checks: variants, sizes, states, a11y, tokens, motion, API, story, anti-patterns, platform). Distinct from `review-hard` (general risk) and `repo-consistency-sweep` (pattern matching).
Next: `implement-slice-complement` (if findings), `pr-package`.

### foundation-audit
Role: compares code tokens vs foundation docs vs optionally Figma variables; detects undocumented tokens, unimplemented tokens, and value drift.
Next: `implement-slice-complement` (to fix drift), `pr-package`.

### extract-foundations-from-screens
Role: extracts canonical foundations docs (`color.md`, `typography.md`, `spacing.md`, `radii.md`) from a batch of existing SCREEN_SPECs. Unions raw values, buckets into role tokens, routes conflicts to a `## Review queue` instead of silently resolving. Idempotent: re-runs preserve locked role mappings and only add new tokens. Distinct from `design-bootstrap` (which seeds foundations from Figma); use this when SCREEN_SPECs already carry raw values and you need cross-screen convergence.
Next: `foundation-audit` (verify extraction vs code), `component-spec` (start consuming role tokens).

### atom-audit
Role: tier-scoped audit of all atoms vs `COMPONENT_GUIDELINES.md` rules (memo, callbacks, inline styles, press anim, touch target, a11y, reduced motion). Produces `ATOM_AUDIT.md` table; fixes flow through normal slice pipeline. Single-agent variant.
Next: `task-init` (per fix grouping), `pr-package`.

### atom-audit-fleet
Role: orchestrator-workers variant of `atom-audit` per ADR-0034 (J.6 PILOT). Sonnet orchestrator dispatches N Haiku workers (3-5 atoms each); merges rows into ATOM_AUDIT.md table. Use when atom count >= 6. Eval baseline for K.7.
Next: `task-init` (per fix grouping), `pr-package`.

### screen-spec-fleet
Role: orchestrator-workers variant of `screen-spec` per ADR-0034 (J.7 PILOT, Bruno's primary scenario). Sonnet orchestrator dispatches N Sonnet workers (1 screen each) in parallel; each runs the 12-step screen-spec flow from a Figma frame; merges SCREEN_MAP.md rows + new routes. Use when screen count >= 6, one persona per run.
Next: `journey-map` (if fleet covered a complete journey), `task-init` (per screen group for implementation).

### inventory-snapshot
Role: snapshot the upstream Figma component library into `docs/research/_inventory/figma_components.md`; classify by tier; check WOS-UI traceability (spec/code/story); compute delta vs previous snapshot; refresh priority queue.
Next: `component-spec` (on the #1 priority entry).

### prompt-shape
Role: shape the exact next prompt when precision or handoff quality matters.
Next: target command.

### jtbd-switch-interviewer
Role: K.8 CUSTOM persona (L3 per ADR-0036 Path B; owns its declared section/report file, PROPOSED for non-owned substrate). Senior JTBD switch-interview researcher (Christensen / Moesta lineage) extracting the four forces (push, pull, anxiety, habit) and the trigger -> struggle -> switch timeline from real users. Replaces internal motivation assumptions with verbatim quote evidence. Owns its report file directly at L3; PROPOSED blocks for non-owned substrate; routes those via Pattern A handoff per `wos/substrate-peers.md`.
Next: `decision-interview` (promote D-N drafts), `capture-observation`, `implementation-plan` (when risks surfaced).

### ai-feature-eval-harness
Role: design a dataset-backed evaluation plan for a product AI feature (measurable success criteria, held-out labeled set, per-criterion grading code-then-LLM, pass threshold); produces `AI_EVAL_PLAN.md`. Code-graded tier composes with ADR-0048 (Layer-1 evidence); distinct from test-strategy (deterministic tests) and verify-against-rubric (internal artifact judging).
Next: `test-strategy` (deterministic half), `implementation-plan` (slice the harness build), `decision-interview` (lock the quality target), `implement-approved-slice`.

### slo-define
Role: K.8 CUSTOM persona (L1 at launch per `wos/maturity-ladder.md`; produces a report file, PROPOSED for non-owned substrate). Senior reliability engineer defining a service's reliability contract (SLIs, SLO target + window, error-budget math, error-budget policy); produces `SLO_SPEC.md`. Cites a baseline/SLA per target or marks PROPOSED-pending-baseline; SKIPs when no observability stack. post-deploy-verifier consumes the SLO threshold; incident-triage uses SLO burn to weight urgency (D-1/D-3).
Next: `decision-interview` (lock the SLO target), `post-deploy-verifier` (use the SLO in deploy negative checks), `incident-triage` (live budget burn), `implementation-plan` (slice instrumentation).

### postmortem-author
Role: K.8 CUSTOM persona (L1 at launch per `wos/maturity-ladder.md`; produces a report file, PROPOSED for non-owned substrate). Senior reliability engineer authoring a blameless postmortem for a resolved incident (timeline, contributing causes without fault, impact vs error budget, owned action items); produces `POSTMORTEM.md`. Distinct from incident-triage (live triage + inline `### Learnings`) and slo-define (the contract this measures impact against); incident-triage and task-close route into it for significant incidents.
Next: `task-init` (a follow-up fix task), `slo-define` (incident exposed a missing SLO), `decision-interview` (a policy action item), `task-close` (closes the incident task).

### release-plan
Role: design a pre-deploy release/rollout strategy for a change (pattern by risk + infra, exposure ramp, promotion metric + threshold, rollback trigger + mechanism); produces `RELEASE_PLAN.md`. Stack/infra-agnostic; designs the rollout, does not execute it. D-1 boundary: release-plan designs the per-change rollout, post-deploy-verifier consumes the promotion metric + rollback mechanism for the post-deploy watch, the standing-pipeline rollback audit is reserved for the future pipeline-gate-review.
Next: `post-deploy-verifier` (author the post-deploy checks that consume this plan), `decision-interview` (lock a rollout policy), `pr-package` (deliver), `slo-define` (promotion metric needs an SLO basis).

### a11y-audit
Role: K.8 CUSTOM persona (L1 at launch per `wos/maturity-ladder.md`; produces a report file, PROPOSED for non-owned substrate). Senior accessibility auditor mapping a UI surface to WCAG 2.2 at a named conformance level (A/AA/AAA); produces `ACCESSIBILITY_AUDIT.md`, a per-criterion ledger splitting machine-checkable rows from a manual-review queue, with severity and concrete remediation. Delegates contrast (1.4.3/1.4.11) to color-contrast-architect and single-component fidelity to design-spec-review.
Next: `color-contrast-architect` (contrast pending), `design-spec-review` (single-component), `implementation-plan` (slice remediation), `decision-interview` (lock target), `implement-slice-complement` (small fixes).

### performance-budget
Role: K.8 CUSTOM persona (L1 at launch per `wos/maturity-ladder.md`; produces a report file, PROPOSED for non-owned substrate). Senior performance-budget auditor declaring the numeric budgets a change must hold (Core Web Vitals, latency percentiles, payload/bundle size) and the regression action per metric, before the change ships; produces `PERFORMANCE_BUDGET.md`. Cites a source per threshold or marks PROPOSED-pending-baseline; declares numbers only and routes enforcement to the ADR-0048 gate and post-deploy-verifier.
Next: `test-strategy` (functional coverage), `post-deploy-verifier` (live signal post-ship), `implementation-plan` (slice optimization), `decision-interview` (lock budget policy), `implement-slice-complement` (small optimizations).

### color-contrast-architect
Role: K.8 CUSTOM persona (L3 per ADR-0036 Path B; owns its declared section/report file, PROPOSED for non-owned substrate). Senior design-system color contrast architect enforcing WCAG 2.2 AA/AAA per design context (normal text, large text, UI components, focus indicators). Pairwise audit across light/dark themes BEFORE visual choices lock; produces a token-level contrast matrix with concrete remediation. Owns `CONTRAST_AUDIT.md` directly at L3; PROPOSED blocks for non-owned substrate.
Next: `screen-spec` (audit cleared), `foundation-audit` (multi-token rework), `decision-interview` (contrast policy lock), `targeted-questions` (missing pairs).

### rls-auth-boundary-auditor
Role: K.8 CUSTOM persona (L3 per ADR-0036 Path B; owns its declared section/report file, PROPOSED for non-owned substrate). Senior Supabase RLS+Auth Boundary Auditor reviewing migrations and policy DDL for tenant isolation gaps BEFORE deploy. Catches USING-without-WITH-CHECK, RLS-without-FORCE, missing policies on join/audit tables, missing tenant predicates, SECURITY DEFINER unsafe functions, unjustified service_role bypass. Produces migration-shaped remediation (concrete CREATE POLICY / ALTER TABLE statements).
Next: `implementation-plan` (slice remediation), `decision-interview` (policy tradeoffs), `approve-proposed`.

### migration-safety-steward
Role: K.8 CUSTOM persona (L3 per ADR-0036 Path B; owns its declared section/report file, PROPOSED for non-owned substrate). Senior database migration safety steward auditing DDL for production-unsafe patterns BEFORE the migration is applied. Per-statement verdict table (SAFE / NEEDS-PHASING / UNSAFE) with concrete statement-shaped remediation; biases NEEDS-PHASING when row count or deploy strategy is unknown; flags IRREVERSIBLE operations for explicit user confirmation.
Next: `implementation-plan` (re-slice into phases), `decision-interview` (IRREVERSIBLE confirm), `approve-proposed`.

### post-deploy-verifier
Role: K.8 CUSTOM persona (L3 per ADR-0036 Path B; owns its declared section/report file, PROPOSED for non-owned substrate). Senior reliability engineer producing per-slice post-deploy verification plans mapping every acceptance criterion to a concrete live signal (exact log query, scoped dashboard panel, smoke-test walkthrough, feature-flag check, DB invariant query) plus negative checks + rollback trigger checklist with named humans. Distinct from `verify-against-rubric` (locked-rubric verdict on captured artifact); this persona produces the PLAN, not the verdict.
Next: `verify-against-rubric` (locked rubric authorable), `slice-closure` (apply ## Post-deploy checks), `direction-adjust` (follow-up needed), `approve-proposed`.

---

## Default workflow

Navigation note:
- this is a phase template; command-level intent still comes from `## Command roles`

### Phase 0: initialize the project (only when the project folder does not exist yet)
0a. `project-bootstrap`
0b. `capture-references` (optional; seed external references before opening the first task)

Expected result:
- `projects/<client>__<project>/` exists with `PROJECT_CHARTER.md`, `REFERENCES.md`, `active/`, `archive/`
- project-level memory is in place to be consumed by every future task under this project

Skip Phase 0 entirely when `projects/<client>__<project>/` already exists.

### Phase 1: initialize the task
1. `task-init`

Expected result:
- task folder exists
- required base files exist
- initial task state exists

### Phase 2: understand the task
2. `impact-analysis`
3. `invariants-and-non-goals`

Expected result:
- blast radius is understood
- boundaries are explicit

### Phase 3: remove ambiguity
4. `targeted-questions` or `decision-interview`
5. `resolve-contract-gaps`
6. `contract-signoff` if needed

Expected result:
- correctness-critical ambiguity is resolved
- canonical decisions are explicit enough to plan safely

### Phase 4: plan safely
7. `implementation-plan`
8. `test-strategy` if needed
9. `sync-task-state` if useful

Expected result:
- safe incremental plan exists
- validation strategy is known
- task state is updated when needed

### Phase 5: execute slices
10. `implement-fleet` when the approved plan's `## Execution waves` show a remaining wave of size 2 or more with `Scope` and `Depends-on` declared; otherwise `implement-approved-slice` (waves-aware per ADR-0042)
11. `review-hard` if useful
12. `slice-closure`
13. `sync-task-state` if useful

Repeat this loop per slice.

### Phase 6: checkpoint or deliver
14. `where-we-at` only if the task is large enough to justify a macro checkpoint
15. `repo-consistency-sweep` (optional; proactive defect-class detection before packaging; triage findings with `apply-sweep-triage` if any)
15b. `security-review` (optional; dedicated security assessment when the task touches auth, PII, public endpoints, or crypto; can run in parallel with step 15)
16. `pr-package`
17. `team-update` if useful

Optional when a PR is open and review returns under the same contract: `pr-feedback-ingest`, then repeat Phase 5 / `pr-package` as needed; use `post-review-pivot` when feedback changes direction.

---

---

## Entry points

Quick-start scenarios for choosing the first command (new project, new task, resume, stuck, incident, delivery, review). For the full <!-- count:entry-points -->21<!-- /count -->-scenario guide, load `wos/entry-points.md`.

---

## Gate conditions

Transition checks for 6 phase boundaries (before planning, before implementation, before slice closure, before PR packaging, after PR review, before done). If a command choice is ambiguous, resolve against `## Command roles` first. For the full checklist per gate, load `wos/gate-conditions.md`.

---

## TASK_STATE policy

`TASK_STATE.md` is mandatory and central.

### Create it
- at task start via `task-init`

### Update it
- after meaningful decisions
- after planning is stabilized
- after each slice closure when useful
- before pausing or handing off
- when stale relative to current truth

### Do not use it as
- a diary
- a long-form analysis dump
- a place for speculative ideas

### Use it as
- operational memory
- resumability anchor
- source of current phase and next step
- optional signal for **work complexity** (`LOW` / `MEDIUM` / `HIGH` / `N/A`) so resumption picks an appropriate editor capability tier without re-deriving risk from scratch

---

## Anti-patterns

<!-- count:anti-patterns -->29<!-- /count --> anti-patterns covering premature implementation, scope creep, skipped state sync, and missing handoffs. For the full list, load `wos/anti-patterns.md`.

---

## Recommended workflows by task shape

Scenario shortcuts for common task types (typical, contract-sensitive, greenfield POC, docs-only, test-only, refactor, incident, resume, delivery, post-review). Command-level authority remains in `## Command roles`. For the full catalog of 14 task shapes with skip rationales, load `wos/workflow-shapes.md`.

---

## Output depth policy

Three tiers (`Lean`, `Balanced`, `Deep`) controlling how verbose each command's output should be. For the per-command assignment and the transcript brevity rule, load `wos/output-depth-policy.md`.

---

## Operating modes

Three per-task postures (`minimal`, `strict`, `teaching`) that change how strictly commands enforce ceremony. Orthogonal to editor mode and output depth. Declared at `task-init` time; recorded in `TASK_STATE.md ## Resume notes`. When undeclared, the workflow uses its standard rules.

For mode definitions (effects, when to use, when NOT to use), declaring/switching mechanics, and the default posture, load `wos/operating-modes.md`.

---

## Operational discipline

This workflow is intentionally strict.

It is not optimized for:
- improvisation
- high-speed speculative coding
- loose task memory
- implicit assumptions

It is optimized for:
- correctness
- clarity
- continuity
- reviewability
- predictable execution
- grounded task handling across multiple projects
- low-friction handoff between commands

### Drift-prevention discipline (PROPOSED accumulation)

The PROPOSED-by-default write policy (Ask/Plan modes; see ADR-0001) means **artifact proposals can accumulate without ever being persisted to disk** if the user reads the conversation but never re-runs in Agent mode. Three or more consecutive PROPOSED-but-not-applied turns is a smell: `TASK_STATE.md` and the rest of the task-memory artifacts can drift away from the conversation's truth, breaking resumability across sessions.

Heuristic for the user (no command auto-enforces this; it is a habit):

- After **every 3 to 5 PROPOSED turns** that have not been applied, run `state-reconcile` against the active task folder. The command's job is exactly to surface and patch this kind of drift.
- After meaningful progress that **was** applied (Agent mode commit, slice closure, decision update), run `sync-task-state` to keep `TASK_STATE.md` aligned. `sync-task-state` is the lighter alternative; `state-reconcile` is for cross-artifact drift detection.
- Before resuming a task in a new session, run `resume-from-state` first; if the artifacts seem inconsistent, route to `state-reconcile` immediately and only then to `what-next`.

A future tool layer (a Claude Code hook, a Cursor pre-flight skill, etc.) could automate this counter and trigger the reconcile suggestion mechanically. The markdown layer cannot; documenting the discipline is the v0.1.x answer. A session-boundary hook now exists: the session-continuity hook (`scripts/session-continuity-hook.sh`, ADR-0052) nudges `sync-task-state` when `TASK_STATE.md` is stale, though it does not count PROPOSED-but-not-applied turns. See [ROADMAP](./ROADMAP.md) Wave 2 for the auto-trigger entry.

---

## Final rule

Use the smallest command that matches the real current need.
Use the safest editor mode for the current phase.
Do not move forward just because a next command exists.
Move forward only when the current phase is genuinely ready to close.
And when you finish a command, the next step should already be ready to paste.


---

## Parallel workflow

Parallel batch execution dispatches independent subagents in a single tool call to compress wall-clock time on fan-out work. See ADR-0038 (Workflow tool primitive) for the dispatch mechanism, ADR-0039 (batch sweet spot) for the empirical sizing rationale, and ADR-0040 (single-writer-per-folder exception) for the disjoint-folder write carve-out used by `task-init-fleet`. For parallel execution of approved product-code slices, see ADR-0041 (file-scope disjointness gate, the `implement-fleet` orchestrator) and ADR-0042 (how the routing graph reaches it: `approve-plan` and `implement-approved-slice` route to `implement-fleet` when a remaining wave has size 2 or more). For empirical evidence and patterns see `wos/workflow-patterns.md`.

Tool support today: only Claude Code exposes the Workflow tool primitive. Other tools (Cursor, plain Claude.ai, Codex) degrade gracefully to sequential execution -- the orchestrator runs the same prompts back-to-back instead of in parallel. No correctness loss; only wall-clock loss.

### When to use

- 5 or more independent items of the same shape (file audits, per-route checks, per-component spec generation, per-slice verification).
- Read-only work, OR independent edits with no shared write target (each subagent touches a disjoint file set).
- Each item's output fits a stable structured shape the parent can merge mechanically.

### When NOT to use

- Shared-state writes (multiple subagents editing the same file -- last write wins, silent loss). Exception: ADR-0040 carves out disjoint-folder writes where each worker owns its own folder (e.g., `task-init-fleet`); those are allowed without an orchestrator merge step because there is no shared write target.
- Dependent steps (item N needs item N-1's output).
- Fewer than 5 items (dispatch overhead exceeds the savings; run sequentially).
- Decisions or judgment calls the user owns -- parallelism amplifies wrong defaults.

### Per-batch checklist

- Per-subagent prompt: 300 to 500 words. Shorter loses grounding; longer wastes context across N workers.
- StructuredOutput reminder in every subagent prompt -- the parent reads only the tool call, not the text reply.
- After the batch returns, run `scripts/scan-substrate-orphans.py` (or the project's equivalent post-apply scan) to catch any files the merge step missed.
- Persist the batch shape and outcome in the slice notes so future runs can replay or compare.
