# WORKFLOW_OPERATING_SYSTEM

Fhorja is a workflow operating system for AI-assisted engineering. This document is its normative specification.

## LLM execution contract

Primary audience:
- the executing model in the editor or agent harness (Claude Code, Cursor, Codex, and others)

Human-facing policy:
- normative behavior belongs here in compact, enforceable rules
- longer explanatory prose should live in command outputs and task artifacts under `projects/`

Precedence order:
1. this file (`WORKFLOW_OPERATING_SYSTEM.md`)
2. specific command file under `commands/*.md`
3. `README.md` onboarding guidance

Conflict rule:
- this file governs cross-command behavior: the output contract, the guardrails, the lifecycle, the naming rules. A command file governs its own steps, preconditions and gates, and MAY be stricter there, never looser.
- when a command file contradicts a rule in this file instead of narrowing it, this file wins: follow this file, flag the mismatch in the output, and route the fix to the command file.

Minimum read map for execution:
- always read before routing or output shaping:
  - `## Editor mode policy`
  - `## Global output contract`
  - `## Cross-cutting workflow guardrails`
- read when needed by context:
  - naming/path disputes: `## Naming conventions`, `## Repository structure`
  - artifact requirements: `## Task files`, `## TASK_STATE policy` (per-file contract: load `wos/task-file-contracts.md`)
  - multi-artifact drift or stale `TASK_STATE.md` after heavy edits: `wos/command-roles.md` (`state-reconcile`)
  - PR review feedback under the same contract (Greptile, CI, inline comments): `wos/command-roles.md` (`pr-feedback-ingest`)
  - PR or team feedback changes direction after packaging: `wos/command-roles.md` (`post-review-pivot`)
  - phase/entry ambiguity: `wos/command-roles.md`, `## Entry points`, `## Gate conditions`
  - command distinctness, guard rails, multi-repo nuance, or routing disputes the index does not resolve: load `wos/command-roles.md` (full per-command detail; not loaded by default)
  - phase-by-phase command sequencing across multiple phases when `wos/command-roles.md` plus `## Default workflow` are insufficient: load `wos/cross-cutting-workflow-guardrails.md` (heuristics + external-web motivation; not loaded by default)
  - the session has NO human respondent (unattended, background, or fleet-dispatched) and the command is about to reach a question loop or a decision-bearing surface: load `wos/cross-cutting-workflow-guardrails.md` → `### Unattended sessions`. It is the rule for that situation and it is not discoverable from the sequencing trigger above, which is why four agents in one validation run improvised four incompatible behaviors at the same point
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
  - operating modes (minimal, strict, teaching, assisted): load `wos/operating-modes.md`
  - editor mode translation to non-Claude-Code tools (Cursor, Copilot, Codex, Gemini CLI equivalents) and per-harness operational quirks (sandbox write-root alignment, approval front-load, patch mechanics): load `wos/editor-mode-mappings.md` (only when working in a tool other than Claude Code)
  - designing, building, or running the autonomous delivery track (the autonomy cluster: two human gates, runtime governor, mid-run escalation, run protocol): load `wos/autonomous-track.md` (built per ADR-0044; not loaded by default)
  - Godot 2D-mobile game development (scene architecture, save/state and the mobile lifecycle, 2D rendering performance, touch input and game-feel, audio, the asset pipeline, headless testing and CI): load `wos/godot-2d-architecture.md`, `wos/godot-2d-mobile-rendering-performance.md`, `wos/godot-mobile-interaction-and-feel.md`, `wos/godot-2d-audio.md`, `wos/godot-2d-asset-pipeline.md`, `wos/godot-testing-and-ci.md` (the Godot cluster reference layer per ADR-0078 and ADR-0084; capability-scoped, not loaded by default)
  - Godot 3D development (renderer tiers and what each drops, the four limitation classes, the nine optimization techniques, GridMap and MeshLibrary level building, navigation meshes and agents, the physics body taxonomy, CC0 asset sourcing and the glTF import path): load `wos/godot-3d-rendering-and-performance.md`, `wos/godot-3d-architecture.md`, `wos/godot-3d-asset-pipeline.md` (the Godot 3D reference layer per ADR-0117; dimension-neutral content stays in the 2D topics and is cross-referenced, not duplicated; capability-scoped, not loaded by default)
  - running a runtime gate: load the battery for the surface under test, `wos/app-runtime-battery.md` for a mobile app, `wos/web-runtime-battery.md` for a browser, `wos/api-runtime-battery.md` for a backend, or `wos/godot-runtime-battery.md` for a game. Each is the adapter layer of the `*-runtime-verify` command for that surface, capability-scoped and not loaded by default, and each holds its own taxonomy, probes and evidence rules
  - Unity mobile development (capturing runtime evidence from an Android or iOS build, the managed-versus-native output split the taxonomy keys on, the Edit-versus-Play-mode test tiers, the test-assembly compile-unit requirement, the undocumented test exit-code contract, and the CI license-activation precondition): load `wos/unity-runtime-evidence.md`, `wos/unity-testing-and-ci.md` (the Unity reference layer per ADR-0130; Unity lands as an `app-runtime-verify` adapter plus contract widenings, with no net-new Unity command; capability-scoped, not loaded by default)
  - Unity multiplayer planning (topology and authority models with Unity's own trade-off table, what Netcode for GameObjects does NOT ship, per-NetworkObject ownership as the security boundary, the RPC-versus-NetworkVariable late-joiner test, and why physics determinism cannot be assumed): load `wos/unity-netcode-architecture.md` (per ADR-0131; grounded in Netcode for GameObjects only, with the framework comparison, CCU cost model, and anti-cheat design deliberately absent; capability-scoped, not loaded by default)
  - Unity mobile rendering (the three-way render-pipeline choice, HDRP's enumerated platform list and its compute-shader and OpenGL ES constraints, and the pipeline declaration a 3D plan carries): load `wos/unity-mobile-rendering-and-performance.md` (per ADR-0132; scoped to the pipeline decision only, with numeric budgets, batching, texture compression, shader stripping, Addressables, and Adaptive Performance deliberately absent; capability-scoped, not loaded by default)
  - deciding whether a slice closes, on ANY task (commit-evidence, experience-verdict, entry-path probe, eval-threshold, integrity, Layer-2 review, and rollout-constraint reconcile, each in its `slice-closure` and inline-close variant): load the per-consumer view named by that command's `unconditional-loads` frontmatter (`wos/closure-floors.<consumer>.md`, generated from `wos/closure-floors.md` per ADR-0138). Unlike the platform floors below this load is UNCONDITIONAL, because these floors fire on every slice: an unread floor here is a skipped gate, not a saved token.
  - platform runtime inline-close floors on a Godot or mobile task (runtime-gate, feel-verdict, and mobile-runtime-gate variants per closing command): load `wos/platform-runtime-floors.md` (moved out of the closing commands per v3 wave1 item D; capability-scoped, not loaded by default)
  - previewing a built frontend so a human can see it and record an experience verdict (serving the production build, the Vite/`astro preview` `allowedHosts` host-check gotcha and the static-server fallback, remote tunnel, recording the verdict): load `wos/frontend-preview-and-experience-verdict.md` (per ADR-0099; feeds the ADR-0091 experience-verdict floor and the release-plan pre-deploy gate; capability-scoped, not loaded by default)
  - authoring or reviewing a rule about what an agent may assert, when it must investigate instead of guessing, how a claim records its provenance, or how a persisted claim gets revised: load `wos/active-epistemic-humility.md` (per ADR-0109; the normative core is inline in `## Global output contract` → `### Claim status and abstention` and the shared block `commands/_shared/claim-grounding.md`; this topic is the full contract with rationale, not loaded by default)
  - recovering task context when the session transcript itself is lost (the `resume-from-state` `--lost-session` mode, per ADR-0113): load `wos/session-recovery.md` (per-harness session-file map and extraction rules; explicit trigger only, capability-scoped, not loaded by default)

---

## Purpose

Human onboarding stub:
- this document defines the operating system for the engineering command library, run in the editor or agent harness (Claude Code, Cursor, Codex, and others)
- it is a workflow control system (not just a prompt library), optimized for low ambiguity and resumable execution

---

## Scope

This workflow is designed for a single developer working in an editor or agent harness (Claude Code, Cursor, Codex, and others) with a strict, evidence-driven, low-assumption working style.

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
- `.claude/skills/<name>/SKILL.md`: **generated** Agent Skills artifacts produced by `scripts/build-agent-skills.sh` from each canonical `commands/<name>.md`. Drop-in for the 35+ tools that read `.claude/skills/` natively (Cursor, Claude Code, Copilot, Codex, Gemini CLI, etc.). Never edit by hand; lint fails on drift.
- `wos/<topic>.md`: lazy-loaded reference files (<!-- count:wos-topics -->55<!-- /count --> topics; e.g. `command-roles.md`, `cross-cutting-workflow-guardrails.md`, `global-output-contract.md`; see the Minimum read map for the full set). Loaded only when explicitly needed.
- `templates/`: starting points for task artifacts (`TASK_STATE.template.md`, `PR_PACKAGE.md`, `OUTCOMES.schema.md`), plus design-system and hook scaffolds.
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
- `globex__platform`
- `coinbase__wallet-web`
- `acme__storefront`

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

This section defines opt-in multi-repo support for tasks that legitimately span multiple product repositories (typical fullstack work crossing backend and frontend repos). Multi-repo support is **additive only**: single-repo tasks continue working unchanged. The discriminator is the presence of an optional `## Repositories` section in `SOURCE_OF_TRUTH.md`; tasks without that section (the default) behave as single-repo across all <!-- count:commands -->98<!-- /count --> commands and do not pay any multi-repo overhead.

For the schema (identifier, path, base branch, role), example, locked decisions D1-D7, invariants I1-I4, non-goals NG1-NG5, runtime decision table, and implementation notes, load `wos/multi-repo-support.md`.

### Command coverage (G4 v1)

This taxonomy covers the product lifecycle commands. The `*-fleet` orchestrators (`implement-fleet`, `task-init-fleet`) and the CUSTOM personas inherit multi-repo behavior from the per-repo loop they run and are not enumerated here.

**Multi-repo aware (<!-- count:commands-multi-repo -->7<!-- /count --> commands)**:
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

Opt-in, git-gated isolation lets several tasks run in parallel on one repository without colliding on a single working tree (ADR-0074). It is additive: when isolation is not requested, or the project is not a git repository, every command behaves as today (single working tree, single branch, no overhead). The task branch itself is no longer opt-in: WHEN `task-init` runs attended in a git repository with a configured remote while the default branch is checked out and isolation is not requested, it SHALL create `task/<task-dir>` in place and record it on a `Task branch:` line in `TASK_STATE.md ## Resume notes` (ADR-0233). When a task opts in, the `task-workspace` command provisions one durable git worktree and the `task/<task-dir>` branch off the base, and records them in `SOURCE_OF_TRUTH.md` under an optional `## Workspace` section (worktree path, task branch, base branch; schema in `wos/multi-repo-support.md`). `task-init` routes to `task-workspace` when isolation is requested rather than provisioning itself; `task-close` tears the worktree down (`git worktree remove` then `prune`) and halts on an unclean or unmerged tree. These per-task worktrees are distinct from the ephemeral slice-level worktrees `implement-fleet` creates: when a task worktree is active, fleet slice worktrees branch off the task branch. Multi-repo worktree provisioning is out of scope for v1.

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

`tools:` is the command's tool surface from the canonical vocabulary (Read, Write, Edit, Bash, Glob, Grep, WebFetch, WebSearch, Agent). `Task` is refused by lint. A read-only command (`context-layers-produced: []`) MUST NOT declare Write or Edit (Bash is exempt: read-only commands still run git, grep, and lint); lint fails on violation. `x-wos-profiles:` is the install-tier membership (a subset of `minimal`, `core`, `full`; minimal commands also list core and full); `sync-workflow-slash-commands.sh --profile <tier>` filters by it. `provenance:` is the trust origin (`first-party` for every command; `vetted-third-party` and `sandbox` are reserved for external skills a human approved via `skill-vet`). Lint validates all three; the canonical `tools` vocabulary lives in the `VALID_TOOLS` array in `scripts/lint-commands.sh`.

### Universal baseline rule

`system`, `tools`, and `task` are universal baseline. Every command consumes them by definition. They are NOT listed in `consumed:` to keep the signal discriminating. Valid non-baseline values for `consumed:` are `memory`, `retrieved`, `history`. Empty lists are valid: a command may consume nothing beyond baseline (`project-bootstrap`) or produce nothing material (pure routing such as `what-next`).

Lint enforces presence of both fields and validates values against the canonical six.

### Example classification (contract-fixing exemption)

Every example inside a `commands/*.md` file (or a `commands/_shared/*.md` block) is one of two classes. A contract-fixing example is one whose exact shape, the bytes, field order, or delimiters, is parsed by a script or validator elsewhere in the repository; `commands/_shared/substrate-write-protocol.md`'s transaction-header and JSONL example is the canonical case, read byte-exact by `scripts/emit-substrate-write.sh`. A judgment-illustrating example is everything else: a worked case that helps a reader calibrate tone, depth, or a borderline call, with no downstream parser depending on its literal text.

A contract-fixing example is exempt from any fold that reduces examples on context-engineering grounds. Removing or reshaping it does not just cost a reader's understanding; it breaks the script or validator that parses it. This is an exemption carved out for the one class where trimming has a mechanical failure mode, not a license to strip judgment-illustrating examples wherever they occur: those stay wherever they earn their keep, and a future fold judges each on its own merit. (D-2; ADR-0115.)

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

Which command fits which mode is per-command data: every command declares `metadata.primary-cursor-mode` in its own frontmatter and `docs/command-catalog.json` carries the same value as `mode`. This section defines the <!-- count:editor-modes -->4<!-- /count --> modes and nothing per-command.

The workflow's canonical editor-mode vocabulary is **`Ask` / `Plan` / `Agent` / `Debug`**. These names originate from Cursor but are adopted as the workflow's tool-neutral mode taxonomy: every command's `metadata.primary-cursor-mode` field uses one of these four values, and every `### Handoff` block's `Mode:` line uses one of them. Other AI tools have similar mode taxonomies under different names; the table below maps the workflow's modes to common tool equivalents.

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

Do not use Ask as disguised implementation.

### Plan
Use Plan when the goal is:
- sequencing work
- converging contract decisions
- hardening implementation rules
- defining test strategy

Do not use Plan to pretend implementation is already done.

### Agent
Use Agent only when:
- the slice is approved
- the scope is narrow enough
- the files in scope are known
- correctness-critical ambiguity is already resolved
- the next step is an actual code change

Writing task-memory files does not require Agent: it is `APPLIED` in every mode (ADR-0199).

Do not use Agent for discovery, policy decisions, or broad exploration.

### Debug
Use Debug only when:
- there is a concrete observed technical failure
- the problem is actual runtime behavior, broken output, or failing tests
- diagnosis is the main need

In this workflow, Debug is exceptional, not the default path. `incident-triage` exists so urgency-shaped tasks have a structured entry point that defends against bypassing the workflow entirely while keeping ceremony short for real hotfixes.

---

## Evidence priority

Across the workflow, use this evidence priority unless a command states otherwise:

1. real code and tests in the codebase
2. `TASK_STATE.md` and `SOURCE_OF_TRUTH.md`
3. other task artifacts in the task folder
4. project-level memory (`PROJECT_CHARTER.md`, `REFERENCES.md`)
5. internal project docs / tickets / local references
6. official framework or library docs, and a dependency's own published source when the docs are silent or unclear on the point (ADR-0121; cite it per `commands/_shared/reference-grounding.md` rule 3, and note the tier is additive: it never replaces capturing the contract via `capture-references`)
7. external web references, via `capture-references` only (never ad-hoc web fetches inside other commands; see `## Cross-cutting workflow guardrails` → `### External web access (centralized)`)

Rule:
- if correctness depends on something not grounded in code, docs, tests, or explicit user input, do not guess
- ask targeted questions instead
- a decision the request does not contain is not a fact to guess: in an attended chain on a task branch it becomes a provisional `P-N` chosen from that evidence and labeled as the agent's (`### Adaptive handoff`)
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
  - `APPLIED`: you are instructing a file write in this run. This is the default for task-memory files in every mode, per `### Task-memory write policy (default)` below.
  - `PROPOSED`: a block staged by a command that does not OWN the section, for the owner to promote (ADR-0034). It is not a mode gate. Adapt the verbosity of the staged block to file state:
    - **Create** (new file): full content inline -- there is no existing file to diff against
    - **Update-delta** (existing file, small change): semantic delta only -- name the section(s) changed, state what changed and why, include the changed lines or block. Do NOT repeat unchanged content.
  - `SKIP`: explicitly skipping an optional artifact with a one-line rationale (example: `TEST_STRATEGY.md`)
- A file labelled `APPLIED` is already on disk, so list it with a one-line summary of what changed, however large the rewrite.

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

The em-dash character stays a hard lint failure (use `--`, a colon, or parentheses). The rest is advisory: `scripts/check-natural-voice.sh` measures it, run by hand rather than from the lint (ADR-0171). Full catalog with rewrites: `wos/natural-voice.md`.

### Long-running execution visibility (per ADR-0042)

Any single execution step expected to exceed about 10 minutes MUST state its expected duration up front and emit interim status instead of going silent. Silence on a long step is indistinguishable from a hang and forces the operator to poll or interrupt.

- Announce up front: when a step (a fleet wave, a slow build or test suite, a large multi-file pass, a background task) is likely to run past ~10 minutes, say so and name what is running before starting it.
- Emit interim status: surface progress as it happens (file-completion ticks, per-wave dispatch lines, a background-task progress note, or the worker's last tool summary), not only a final result.
- Stall rule: when a long-running step surfaces no progress for the stall threshold, emit a status summary (what is running, elapsed time, last observable action) rather than waiting silently for a timeout. For fleets, `implement-fleet` references `scripts/monitor-fleet-progress.sh` and applies this rule during its convergence barrier; this is a reporting duty and does not weaken the integration gate.

This is the operator-visibility counterpart to the Handoff contract: the Handoff makes continuation legible between steps; this makes a single long step legible while it runs.

### Task-memory write policy (default)
Unless a command explicitly says otherwise:
- Write task-memory files directly and mark them **`APPLIED`**, in every mode. Writing five markdown files into a task folder is internal and reversible, and it matches none of the four reasons a chain stops, so it never waited on a human to begin with. This replaces the ADR-0001 PROPOSED-by-default write gate and the ADR-0026 exception that carved `implement-approved-slice` out of it; the exception is unnecessary once the rule it excepted is gone.
- `PROPOSED` keeps its OTHER meaning, which this change does not touch: a command that does not OWN a substrate section stages a `<!-- PROPOSED by <command>: ... -->` block inside it for the owner to promote (ADR-0034). That is a peer-ownership mechanism, not a mode gate, and it applies in Agent mode too.
- Prefer applying `TASK_STATE.md` updates via `sync-task-state` after meaningful progress (unless the command explicitly requires an immediate `TASK_STATE.md` patch).

### Claim status and abstention (per ADR-0109)
The active-epistemic-humility doctrine (`wos/active-epistemic-humility.md`, shared block `commands/_shared/claim-grounding.md`). This subsection is inert on any output whose claims are all grounded, so a normal output pays nothing:
- A load-bearing claim (one a downstream command or a human decision consumes) that a command persists into a task-memory artifact SHALL carry a provenance referent naming where it came from: a `REFERENCES.md` entry, a file path plus line, or a gate output. It SHALL NOT carry a confidence degree. A status with an empty referent reads as unknown. In a chat-only output the referent is required only on a claim that crosses the grounding boundary and triggers a route.
- WHEN a load-bearing claim cannot be traced to the grounded set (captured references, files read this session, command output seen, a passing deterministic gate), the command SHALL either investigate or abstain, and SHALL NOT assert it from model memory.
- Abstention is a routed continuation, never a bare refusal: it names the specific investigation that would settle the question and routes to the command that runs it. Abstention is distinct from `NO_OP` (no work to do); it means the grounding to proceed is missing.

### Every command should end with:
- the next command in the chain, which the same session then runs without being asked
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
- **Model selection for direct Claude Code usage** (no Cursor routing layer): `wos/model-routing.md` carries a recommended Claude SKU and Codex reasoning-effort ladder, from the default pipeline up to the most escalated one. Its rows are keyed on the escalations `TASK_STATE.md` records (ADR-0207). This is the user's per-task decision recorded in `TASK_STATE.md`; commands themselves still never emit SKU names in handoffs.
- **Harness primitive equivalence** (working in a non-Claude-Code harness): `wos/sub-agent-orchestration.md` → `## Harness equivalence` maps the Claude Code primitives commands assume (`SendMessage`, `Workflow` fleets, `AskUserQuestion`) to each harness's equivalent or explicit degradation, and `wos/model-routing.md` carries a `Codex reasoning-effort default` column. The vendor-neutral rule above is unchanged: commands never emit model or effort names in handoffs.
- Pipeline escalations and `Work complexity` (`LOW`/`MEDIUM`/`HIGH`/`N/A`) are orthogonal axes: an escalation adds a ceremony step because a named disqualifier fired, and Work complexity says *how hard the next single step is*. A task escalated on an auth surface may still have a `LOW` next step (a trivial typo fix in that file); a task with no escalation may have a `HIGH` next step (a tricky integration decision). Do not conflate them.

### Calibration examples (non-normative)

For the full `LOW` / `MEDIUM` / `HIGH` calibration vignettes (typo fixes, API plus migration changes, auth or cryptography changes, production incidents) and the "prefer the higher complexity if mistake cost is asymmetric" tiebreaker, load `wos/global-output-contract.md`. Capability-routing definitions themselves (`LOW` / `MEDIUM` / `HIGH` / `N/A`) remain inline above; only the supporting vignette set is lazy-loaded.

### Adaptive handoff

The `### Handoff` block adapts its verbosity based on session state.

`Run now:` names what happens next, and an attended session continues into it in the same turn rather than waiting to be asked. Stop and hand back only for a reason you can name: an act whose audience is not bounded, a decision that changes what the product is, a cost or loop ceiling, or a check of the work the agent cannot honestly run on itself. Say which one in `Reason:`.

An attended chain on a task branch is an attended session (ADR-0159) whose `TASK_STATE.md ## Resume notes` carry a `Task branch:` line and no declared `Operating mode: assisted`; every command that names it means this. In such a chain, reasons 2 and 4 are records, not stops (ADR-0233). WHEN such a chain needs a decision the request does not contain, the command SHALL pick the option the code and the request support, record it as a `### P-N` under `DECISIONS.md ## Provisional decisions` (`Evidence:`, `Impact:`, `Status: provisional`), and continue; WHEN a check it cannot honestly run on itself is pending, it SHALL record the check and continue. The draft pull request lists them under `Decisions made without you` (`Impact: high` first, to confirm before merge) and `Not verified`, and a named deliverable that needs a decision no evidence settles goes under `Not delivered, needs you`, never dropped. Short of a reason 3 ceiling, reason 1 is the one stop left: ready for review, merge, publish, outward egress. WHERE git or a configured remote is missing, reasons 2 and 4 stop as before. WHERE `Operating mode: assisted` is declared (`wos/operating-modes.md`, provisional P-8), every stop ADR-0233 removed comes back and nothing else: `task-init` creates no task branch, reasons 2 and 4 stop as before, and `branch-commit` does not hand on to `pr-package --apply`; the blinded plan review and the local commit on a named branch still run alone. Unattended, background and fleet-dispatched runs write no `P-N` and keep `wos/cross-cutting-workflow-guardrails.md` → `### Unattended sessions`.

Approving a plan is not an instance of reason 2. A plan is a route to decisions already locked in `DECISIONS.md`, not a decision itself, and `commands/implementation-plan.md` already requires a plan that would introduce a behavioral commitment those decisions do not support to be marked `PROPOSED` and routed to `decision-interview`, `targeted-questions`, `resolve-contract-gaps` or `contract-signoff` rather than approved; in an attended chain on a task branch that route ends in a provisional `P-N`, not a wait. What is left at approval is whether that routing rule held, which is a check against a rubric rather than a decision to make. So `approve-plan` runs its own check and continues, on the evidence of a review performed in a context that never saw the conversation that wrote the plan (ADR-0208). `## Locked decisions` stays the only authorization it reads: a slice resting on a `P-N` passes labeled "rests on provisional P-N", and the review asks whether that entry's evidence exists on the task branch. The autonomous delivery track keeps its own entry gate, because its premise is that nobody is watching: see `wos/autonomous-track.md` (ADR-0044).

Reason 1 turns on who can see the act, not on whether the act can be undone. An act clears, and the command proceeds without asking, when the set of people it reaches is bounded: a local commit, a push to a task branch, a draft pull request that notifies nobody. An act gates when that set is open: marking a draft pull request ready for review, sending produced content outward through a connected MCP server, publishing a page. Undo decides nothing here. A published page can be deleted and the people who already read it still read it, while a local commit that cannot be recovered still reached no one. One case has to be checked rather than assumed: a draft pull request clears only where the target repository fires no publishing workflow on `pull_request: opened`, and reading that repository's workflow triggers is the duty of the command doing the act. WHEN an act's audience is not bounded, the command SHALL obtain an explicit confirmation in that same turn, after displaying the raw payload and the exact destination rather than its own summary of them. One act takes one confirmation. No standing approval exists and consent is never carried across turns.

When one turn runs several commands, `### Artifact changes` and `### Handoff` are emitted ONCE for the turn, not once per command: the per-command record is the substrate each command writes, and the turn's single Handoff reports where the chain actually stopped. One block per command is not wrong, only more verbose (ADR-0192).

**Mode A -- Compact (default, intra-session)**

When the model has full conversation history (same session, no compaction boundary crossed):

```text
Run now: /<command>
Mode: <Ask | Plan | Agent | Debug>
Work complexity: <LOW | MEDIUM | HIGH | N/A>
Reason: <one line>
```

~50 tokens. No paste body needed because the context window already contains everything.

When the chain has ended and no following command would be honest, the same block carries the terminal form instead: `Run now: none` with `Mode: N/A`, defined under `### Official command names (routing integrity)`. `Mode: N/A` is valid only in that pairing.

**Mode B -- Full (cross-session or post-compaction)**

When context is actually lost (after auto-compaction, or when the next command is `resume-from-state`):

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
Mode: Plan (parent) + Explore (workers); use Claude Code `Agent` tool, Cursor /worktree, or equivalent
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
| Before implementation | `implementation-plan`, `approve-plan` (every plan but a one-slice route's), `test-strategy` |
| Before implementation (execution) | `implement-approved-slice`, `implement-slice-complement` |
| Before slice closure | `review-hard`, `slice-closure` |
| Local commit (after the last slice) | `branch-commit --apply` |
| Draft PR (after the local commit, attended, with a remote) | `pr-package --apply` |
| Before PR packaging | `where-we-at` (when used), `pr-package` |
| After PR review feedback (corrective) | `pr-feedback-ingest` |
| After PR review feedback (pivot) | `post-review-pivot` |
| Project-level memory init | `project-bootstrap`, `capture-references` |
| Entry / recovery / drift | `task-init`, `resume-from-state`, `what-next`, `workflow-guide`, `im-stuck`, `sync-task-state`, `state-reconcile` |
| Concrete observed failure | `incident-triage` |
| Communication / meta | `branch-commit` (naming only), `team-update`, `prompt-shape` |

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
- **Terminal form (the one exception).** `Run now: none` is the single value on that line that does not name a `commands/` basename. It declares that the chain has ended and no following command would be honest, either because the task is finished or because every remaining path needs a human or an environment this session cannot supply. A block carrying it sets `Mode: N/A`, and `Reason:` says what would unblock the work. It is how a continuing chain stops. Do not use it to end a chain that has a real next step, and do not use it in place of a queued question when the block still routes somewhere (ADR-0126).
- A manual activity is not a Fhorja command. When the next step is a manual action (running the app, a shell or CLI command like `npm run ios`, a device or browser test session, a dashboard check), describe it as a manual step in prose; never emit it as a `Run now: /<name>` line. The `Run now` line is reserved for real `commands/` basenames, so routing a manual activity through it (for example `Run now: /device-verify` when `device-verify` is a manual on-device test session, not a command) is invalid output. When in doubt whether the next step is a command, check `commands/` for that basename: present it as `Run now` only if the file exists, otherwise as a manual step.
- WHEN the next step depends on a human action outside the session (adding a connector, running a tunnel, pasting a credential, clicking through a flow), the manual-step handoff (F-4) SHALL hand over the exact current artifact that action needs (the URL, command, or value), verified as current immediately before the ask; asking for the outcome of a manual step before its inputs were delivered is invalid output. A mutable value (a tunnel URL, a port) has one source of truth in the handoff and is restated whenever it changes. This exists because a dogfooded session ran a tunnel in a background subshell and asked twice how the demo went while the user never had a usable URL.
- WHEN a turn is about to dispatch a fleet wave or a Workflow run (command-driven or command-less), the known-gotchas preflight (F-5) SHALL first consult the recorded operational gotchas for the tool being dispatched (scripts/rank-learnings.sh over the project LEARNINGS plus the user-level memory) and apply them to the dispatch, stating what it applied. A dispatch that repeats a recorded gotcha is a preventable failure, not bad luck: the consume side of ADR-0017/0071 extends from task-init to dispatch time because the 2026-07-10 dogfood re-hit a Workflow args gotcha recorded seven days earlier.

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
- **enumerate every unmet prerequisite, never just the first** (ADR-0148): WHEN the no-op is caused by unmet upstream prerequisites, the `NO_OP_TRACE` SHALL list EVERY one of them and name the single command that resolves the most at once. Stopping at the first blocker turns one unblock into a serial round-trip per blocker; the rule is unconditional and applies to any command that can no-op this way, not only to planning.

### Proposal vs approved persistence
- Do not silently change semantic intent in `DECISIONS.md` without explicit user approval in-chat or authoritative artifact approval.
- A provisional `### P-N` under `## Provisional decisions` is not such a change: it is labeled `Status: provisional`, never recorded as the user's input or under `## Locked decisions`, and listed in the draft pull request.
- When needed, label content as **PROPOSED** and route to explicit confirmation or the correct hardening command.
- A `PROPOSED` block staged by a non-owner is promoted by the section's OWNER, or by `/approve-proposed` when the user asks for it. That command is no longer part of any default chain: the ADR-0024 three-path rule described the mode gate, and the mode gate is gone. Commands MUST NOT pretend the user has already approved a DECISION when no signal was given, and MUST persist when a valid lock signal is given (e.g., `/decision-interview` recognizing `D<N> [LOCK]` picks per its Operating rules `LOCK-pick recognition`).
- `### Artifact changes` is the single proposal surface per turn. Never nest PROPOSED blocks (no `## PROPOSED X.md block` or `## PROPOSED X.md deltas` headers under `### Artifact changes`); inline content goes directly under each file's bullet.

### Substrate peer ownership (per ADR-0034)

Commands, personas (SKILL.md files), and Epic J fleet workers are peers sharing four canonical substrate files: `TASK_STATE.md`, `DECISIONS.md`, `IMPLEMENTATION_PLAN.md`, `SOURCE_OF_TRUTH.md`. Every H2 section has one conventional OWNER plus named CO-WRITERS, and ownership routes by convention (ADR-0232): a write outside the row is logged naming the owner, never refused; no silent last-write-wins. Workers dispatched by orchestrators MUST conform to the canonical worker contract in `commands/_shared/worker-contract.md`. Full ownership matrix, read/write contracts, conflict rules, and audit-trail schema in `wos/substrate-peers.md` (lazy-loaded; activation `model_decision`).

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

### Task-close-before-session-end guardrail

WHEN a task's `TASK_STATE.md` phase reads delivered or done and the current session is ending, the session SHALL prompt `task-close` before ending, rather than leaving the task open in `active/`. This is a session-end reminder, not a new mechanism: `portfolio-review`'s existing done-unclosed classification already exists as the safety-net sweep for anything missed.

### Sequencing heuristics (by phase)

Phase-grouped routing heuristics (Discovery → Contract → Planning → Execution → Delivery → Debug) live in `wos/cross-cutting-workflow-guardrails.md` → `### Sequencing heuristics (by phase)`. Most routing decisions are resolved by the `## Command roles` pointer plus `## Default workflow`; consult the lazy file when phase ordering across multiple commands is unclear.

---

## Command categories

Navigation note:
- this section is a grouping aid; authoritative command-level behavior lives in `## Command roles`
- one command sits in exactly one category. `README.md` `## Command clusters` groups the same commands
  editorially, where a command may appear in more than one family; the two axes answer different questions

### Project initialization
- `project-bootstrap`

### Research and sourcing
- `capture-references`
- `external-research`
- `external-research-fleet`
- `feature-library-scout`
- `feature-library-scout-fleet`
- `stack-currency-check`
- `stack-recommend`

### Discovery and scoping
- `backend-system-design`
- `code-context-map`
- `code-locate`
- `impact-analysis`
- `inventory-snapshot`
- `jtbd-switch-interviewer`
- `pattern-doc`
- `problem-framing`
- `targeted-questions`

### Design and UI
- `color-contrast-architect`
- `component-spec`
- `design-bootstrap`
- `design-spec-review`
- `extract-foundations-from-screens`
- `frontend-architecture-review`
- `frontend-system-design`
- `image-to-spec`
- `journey-map`
- `screen-spec`
- `screen-spec-fleet`

### Game and engine
- `godot-runtime-verify`
- `godot-scene-plan`
- `unity-scene-plan`

### Database context
- `db-context-postgres`
- `db-context-supabase`

### Contracts and decisions
- `api-contract-review`
- `contract-signoff`
- `decision-interview`
- `direction-adjust`
- `graphql-contract-review`
- `invariants-and-non-goals`
- `resolve-contract-gaps`

### Planning and validation
- `ai-feature-eval-harness`
- `approve-plan`
- `implementation-plan`
- `migration-safety-steward`
- `release-plan`
- `self-critique-and-revise`
- `slo-define`
- `test-strategy`
- `verify-against-rubric`
- `verify-against-rubric-fleet`

### Execution and closure
- `harvest-session-learnings`
- `implement-approved-slice`
- `implement-fleet`
- `implement-slice-complement`
- `postmortem-author`
- `review-hard`
- `slice-closure`
- `task-close`
- `where-we-at`

### Runtime verification
- `api-runtime-verify`
- `app-runtime-verify`
- `post-deploy-verifier`
- `web-runtime-verify`

### Audit and sweep
- `a11y-audit`
- `apply-sweep-triage`
- `atom-audit`
- `atom-audit-fleet`
- `foundation-audit`
- `mcp-server-vet`
- `performance-budget`
- `repo-consistency-sweep`
- `rls-auth-boundary-auditor`
- `security-review`
- `skill-vet`

### Autonomy
- `autonomous-board`
- `autonomous-readiness`
- `autonomous-run`

### Delivery and communication
- `branch-commit`
- `delivery-asset`
- `post-review-pivot`
- `pr-feedback-ingest`
- `pr-package`
- `team-update`

### State and navigation
- `approve-proposed`
- `capture-observation`
- `compact-task-memory`
- `im-stuck`
- `incident-triage`
- `portfolio-review`
- `resume-from-state`
- `state-reconcile`
- `sync-task-state`
- `task-init`
- `task-init-fleet`
- `task-workspace`
- `what-next`
- `workflow-guide`

### Prompt tooling
- `prompt-shape`

## Command roles

Per-command Role and Next lives in `wos/command-roles.md`. Load it when routing needs
command-level intent, distinctness between two candidates, or the next-command edge.

This file keeps no inline copy. The index duplicated data that every command paid for on
every invocation, and a dispute the command's own description does not settle is exactly the
case that should open the full file.

## Default workflow

Navigation note:
- this is a phase template; command-level intent still comes from `## Command roles`
- the default path is `task-init` -> `implementation-plan` -> `approve-plan` -> `implement-approved-slice` -> `branch-commit --apply` -> `pr-package --apply` (ADR-0184, ADR-0208, ADR-0233). Phases 2 and 3 run only when a named disqualifier fires, and `task-init` records it on the `Escalations:` line of `## Recommended pipeline`. The last step runs attended where the repository has a configured remote; after the draft pull request opens the chain ends with `Run now: none`, and ready for review and merge are the person's
- the one-slice route skips Phase 4: for an attended one-sentence change to at most two named files with every decision in the brief and no provisional `P-N`, `task-init` writes the approved slice and hands to `implement-approved-slice`, which runs `check-doc-sync.sh --against HEAD` at its inline close (ADR-0225)

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
- in an attended git repository with a configured remote, the task branch exists and `TASK_STATE.md` names it on a `Task branch:` line
- the decisions `task-init` expects to assume are listed, and the chain continues without waiting for answers

### Phase 2: understand the task
Only when a named disqualifier fires (recorded on `Escalations:`):
2. `impact-analysis` when the scope needs more than one sentence to state, or the change touches 5 or more files
3. `invariants-and-non-goals` when the surface is auth, payments, compliance, PII, or multi-tenant isolation

Expected result:
- blast radius is understood
- boundaries are explicit

### Phase 3: remove ambiguity
Only when a named disqualifier fires (recorded on `Escalations:`), or a missing fact blocks the plan:
4. `decision-interview` when a decision the prompt does not contain is required before the first line of code, or the change spans multiple packages or adds an external service dependency (in an attended chain on a task branch it records a provisional `P-N` and the chain continues); `targeted-questions` when the gap is a fact
5. `resolve-contract-gaps`
6. `contract-signoff` if needed

Expected result:
- correctness-critical ambiguity is resolved
- canonical decisions are explicit enough to plan safely

### Phase 4: plan safely
7. `implementation-plan`
8. `approve-plan`, for every plan `implementation-plan` writes: it runs the blinded review itself, and only an ESCALATED exit reaches the user (ADR-0208); in an attended chain on a task branch a missing product decision becomes a provisional `P-N` rather than an ESCALATED exit (ADR-0233)
9. `test-strategy` when the strict-surface disqualifier fired or the change carries regression risk
10. `sync-task-state` if useful

Expected result:
- safe incremental plan exists and is approved
- validation strategy is known
- task state is updated when needed

### Phase 5: execute slices
11. `implement-fleet` when the approved plan's `## Execution waves` show a remaining wave of size 2 or more with `Scope` and `Depends-on` declared; otherwise `implement-approved-slice` (waves-aware per ADR-0042)
12. `review-hard` when the strict-surface disqualifier fired, otherwise if useful
13. `slice-closure` when the slice does not close inline
14. `sync-task-state` if useful

Repeat this loop per slice. After the last slice, `branch-commit --apply` creates the local commit (ADR-0163). In an attended chain with a configured remote, `pr-package --apply` then pushes the task branch and opens the draft pull request, which closes the default pipeline (ADR-0233); without a remote the local commit closes it.

### Phase 6: checkpoint or deliver
15. `where-we-at` only if the task is large enough to justify a macro checkpoint
16. `repo-consistency-sweep` (optional; proactive defect-class detection before packaging; triage findings with `apply-sweep-triage` if any)
16b. `security-review` (optional; dedicated security assessment when the task touches auth, PII, public endpoints, or crypto; can run in parallel with step 16)
17. `pr-package`; the push and the draft PR happen only through `pr-package --apply` (ADR-0185), which an attended chain runs right after the last commit without waiting (ADR-0233); ready for review and merge stay human
18. `team-update` if useful
19. `task-close` once every slice is closed and the work is merged or explicitly waived

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

Scenario shortcuts for common task types (typical, contract-sensitive, greenfield POC, docs-only, test-only, refactor, incident, resume, delivery, post-review). Command-level authority remains in `## Command roles`. For the full catalog of <!-- count:task-shapes -->15<!-- /count --> task shapes with skip rationales, load `wos/workflow-shapes.md`.

---

## Output depth policy

Three tiers (`Lean`, `Balanced`, `Deep`) controlling how verbose each command's output should be. For the per-command assignment and the transcript brevity rule, load `wos/output-depth-policy.md`.

---

## Operating modes

Four per-task postures (`minimal`, `strict`, `teaching`, `assisted`) that change how strictly commands enforce ceremony. Orthogonal to editor mode and output depth. Declared at `task-init` time; recorded in `TASK_STATE.md ## Resume notes`. When undeclared, the workflow uses its standard rules.

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

Since ADR-0199 a command writes its task-memory files `APPLIED` in every mode, so whole files no longer pile up unpersisted. What can still accumulate is a `<!-- PROPOSED by <command>: ... -->` block a command stages inside a section it does not own, for the owner to promote (ADR-0034). Left unpromoted, those blocks let the section drift from what its owner would write.

Heuristic for the user (no command enforces this; it is a habit):

- When a section carries PROPOSED blocks from more than one command, or the same block has sat through several turns, run the owning command or `approve-proposed` (on request, ADR-0199) to promote or discard them, and `state-reconcile` when the section and the conversation have diverged.
- After meaningful progress that **was** applied (Agent mode commit, slice closure, decision update), run `sync-task-state` to keep `TASK_STATE.md` aligned. `sync-task-state` is the lighter alternative; `state-reconcile` is for cross-artifact drift detection.
- Before resuming a task in a new session, run `resume-from-state` first; if the artifacts seem inconsistent, route to `state-reconcile` immediately and only then to `what-next`.

The session-continuity hook (`scripts/session-continuity-hook.sh`, ADR-0052) nudges `sync-task-state` when `TASK_STATE.md` is stale, though it does not count unpromoted ownership blocks.

---

## Final rule

Use the smallest command that matches the real current need.
Use the safest editor mode for the current phase.
Do not move forward just because a next command exists.
Move forward only when the current phase is genuinely ready to close.
And when you finish a command, an attended session is already running the next one, or has stopped for a reason it named (ADR-0186); a next step left for the user to paste is the relay this replaced.


---

## Parallel workflow

Parallel batch execution dispatches independent subagents in a single tool call to compress wall-clock time on fan-out work. See ADR-0038 (Workflow tool primitive) for the dispatch mechanism, ADR-0039 (batch sweet spot) for the empirical sizing rationale, and ADR-0040 (single-writer-per-folder exception) for the disjoint-folder write carve-out used by `task-init-fleet`. For parallel execution of approved product-code slices, see ADR-0041 (file-scope disjointness gate, the `implement-fleet` orchestrator) and ADR-0042 (how the routing graph reaches it: `approve-plan` and `implement-approved-slice` route to `implement-fleet` when a remaining wave has size 2 or more). For empirical evidence and patterns see `wos/workflow-patterns.md`.

Tool support today: only Claude Code exposes the Workflow tool primitive. Other tools (Cursor, plain Claude.ai, Codex) degrade gracefully to sequential execution -- the orchestrator runs the same prompts back-to-back instead of in parallel. No correctness loss; only wall-clock loss.

### When to use

- 3 or more independent items of the same shape (file audits, per-route checks, per-component spec generation, per-slice verification).
- Read-only work, OR independent edits with no shared write target (each subagent touches a disjoint file set).
- Each item's output fits a stable structured shape the parent can merge mechanically.

### When NOT to use

- Shared-state writes (multiple subagents editing the same file -- last write wins, silent loss). Exception: ADR-0040 carves out disjoint-folder writes where each worker owns its own folder (e.g., `task-init-fleet`); those are allowed without an orchestrator merge step because there is no shared write target.
- Dependent steps (item N needs item N-1's output).
- Fewer than 3 items (dispatch overhead exceeds the savings; run sequentially). The fan-out floor is 3; per-command thresholds MAY be higher, never lower. Exceptions are registered in `wos/workflow-patterns.md`.
- Decisions or judgment calls the user owns -- parallelism amplifies wrong defaults.

### Per-batch checklist

- Per-subagent prompt: 300 to 500 words. Shorter loses grounding; longer wastes context across N workers.
- Typed-return reminder in every subagent prompt; the carrier depends on the dispatch path, per `commands/_shared/worker-contract.md`. Prose returns are forbidden.
- After the batch returns, run `scripts/scan-substrate-orphans.py` (or the project's equivalent post-apply scan) to catch any files the merge step missed.
- Persist the batch shape and outcome in the slice notes so future runs can replay or compare.
