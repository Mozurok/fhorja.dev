---
activation: model_decision
description: Project-level memory lifecycle, retroactive bootstrap, multi-repo charter schema, three-tier memory pyramid. Load for project memory edge cases.
---

# wos/project-level-memory.md

Lazy reference for `## Project-level memory` in the spec. The compact stub in `WORKFLOW_OPERATING_SYSTEM.md` keeps the lead definition, the file inventory (`PROJECT_CHARTER.md`, `REFERENCES.md`), and the runtime decision table (which is routing-critical at every `task-init` and `capture-references` invocation). This file holds the lifecycle narrative and the motivational rationale that agents only need when explaining the design or onboarding a new contributor.

Load this file when:
- a contributor or new user asks "why does project-level memory exist as a separate layer?"
- writing or updating commands that touch `PROJECT_CHARTER.md` or `REFERENCES.md` lifecycle rules
- the compact stub in the spec is not enough to resolve a routing nuance about project-vs-task ownership

Single-task day-to-day execution does not need this file: `task-init` and `capture-references` already encode the lifecycle rules in their own `Operating rules:` sections, and the spec decision table covers the routing.

---

## Lifecycle

- `project-bootstrap` is the only command that creates `PROJECT_CHARTER.md` and `REFERENCES.md`, and only when `projects/<client>__<project>/` did not exist before the run. Subsequent `project-bootstrap` invocations against an existing folder return `NO_OP_TRACE` and route the user to `task-init` or `capture-references`.
- `capture-references` is the canonical way to append entries to `REFERENCES.md`. No other command appends to it. The append is deduplicated by URL, with freshness metadata (accessed date, summary, optional verbatim key points, tags).
- `task-init` reads both files when present and links to them from the new task's `SOURCE_OF_TRUTH.md` under a `## Project-level memory` section. When the project was not bootstrapped, `task-init` warns the user with a one-line note ("project not bootstrapped: recommended to run `project-bootstrap` first to capture project-level context") and proceeds with placeholders. The task is never blocked by missing project-level memory; the warning is informational.
- Project-level memory is never modified by task-scoped commands. Tasks may reference but never mutate `PROJECT_CHARTER.md` or `REFERENCES.md`. This is enforced both by command-level `Operating rules:` and by the spec decision table.

## Human knowledge layer (the `knowledge/` folder)

The `knowledge/` folder is the third project-level memory artifact (ADR-0054, ADR-0055). It is a human-first record of how a project evolved, what was decided, and the learnings that actually mattered, organized as a navigable, Obsidian-compatible set of linked notes rather than a flat log (D-8, D-9).

Shape (D-9): `projects/<client>__<project>/knowledge/` holds one note per closed task (`<task-slug>.md`) plus an `index.md` (the map of content). Plain Markdown, gitignored. Notes carry Obsidian-flavored wikilinks (`[[...]]`) to the task, its decisions, and topics; the index links to every note (D-8). The note template is `templates/knowledge-layer-entry.template.md` and the index template is `templates/knowledge-index.template.md`.

It exists to keep a durable, readable project history for a human without re-coupling the AI to every past learning. The AI is deliberately kept out of the read path: an always-on cross-task lessons rollup was the scope-creep failure mode this design avoids (ADR-0054 resolves the deferred D-5 from the 2026-06-25 claude-obsidian analysis).

Rules:

- **Never auto-loaded.** No command reads the `knowledge/` folder at task start, and `task-init` never seeds from it. The AI receives its content only when a human pastes a chosen excerpt into a task prompt. This is the load-bearing invariant; a regression eval scenario guards it.
- **Written only at task-close (D-11).** `task-close` creates one note per task (`knowledge/<task-slug>.md`), updates `knowledge/index.md`, writes the deterministic links (to the task folder, the index, and that task's `DECISIONS.md`) automatically, and proposes candidate topic links and tags for the human to confirm or edit at close. No other command writes here, and there is no per-slice write. It is idempotent (no second note for the same task on re-run) and never silently inserts unverified topic links.
- **Human re-injection, not AI recall.** When a past learning is relevant to a new task, the human copies the relevant excerpt into the new task prompt. There is no flag and no recall command; the manual paste is the only re-entry path.
- **The mechanism ships, the content does not.** The templates, the `task-close` step, and the generators ship in the distribution; the generated per-project `knowledge/` content stays gitignored under `projects/` (per-user), exactly as ADR-0049's `ACTIVITY.html` does.

Two generated views accompany the folder:
- The per-project task timeline (`scripts/build-activity-timeline.py --project`): the chronological view over the audit log (ADR-0049, D-6).
- The navigable knowledge HTML view (`scripts/build-knowledge-view.py`, D-10): renders the index and the wikilinks for users without Obsidian. Opening the `projects/` folder in Obsidian gives the graph and Canvas for free (D-8, reinforces D-2).

## Why project-scoped

Some context outlives any single task: stack choices, planned repositories, regulatory or compliance constraints, primary stakeholders, durable external references (vendor docs, regulatory text, framework upgrade notes). Capturing this once at the project level prevents three failure modes that the workflow has historically hit when project memory was implicit:

1. **Re-asking the same questions per task**. Without `PROJECT_CHARTER.md`, every new `task-init` had to re-elicit stack, repositories, and constraints from the user. Slow, error-prone, and a source of accidental drift between tasks.
2. **Research orphaned to a single task**. External references captured during exploration would die with the task folder when it moved to `archive/`. The next task had to re-find the same vendor docs or regulatory text. `REFERENCES.md` keeps research alive at the project layer with deduplication.
3. **Implicit context that breaks under team handoff**. When a teammate or future-self resumes a project after months, knowing only the most recent task is not enough. The charter is the durable source of project intent that survives task churn.

These motivations live here rather than in the spec stub because they are explanatory: agents acting on the workflow only need the rules (decision table) and the inventory (file list), not the rationale. The rationale is for humans deciding whether to add a new layer or revise existing rules.

## Relationship to user-level memory

Slice 05 of the 2026-05-15 context-engineering uplift introduced a third memory tier above project memory: `/USER_MEMORY.md` at repo root (gitignored; bootstrap from `templates/USER_MEMORY.template.md`). ADR-0016 records the decision; this section documents how the three tiers compose.

### The three-tier memory pyramid

| Layer | Scope | Files | Lifetime |
|---|---|---|---|
| Task memory | active task only | `TASK_STATE.md`, `DECISIONS.md`, `SLICES/*`, etc. | until task closes / archives |
| Project memory | one client / project, all tasks under it | `PROJECT_CHARTER.md`, `REFERENCES.md`, `knowledge/` folder (human-read; never auto-loaded) | until the project is retired |
| User memory | one user, all projects, all tools | `USER_MEMORY.md` (repo root, gitignored) | until the user changes their preferences |

### Layered precedence

When the same fact appears at multiple layers, the more specific layer wins:

1. **Task memory** (most specific) overrides everything else.
2. **Project memory** overrides user memory.
3. **User memory** is the most general baseline.

Example: user prefers terse responses globally (USER_MEMORY.md `## Preferences`); project memory says "this project requires detailed PR descriptions" (PROJECT_CHARTER.md `## Constraints`); task memory says "for this slice, the user explicitly asked for an exhaustive review" (TASK_STATE.md). The task-level "exhaustive review" instruction wins for that slice only.

The rule is not lint-enforceable (the model cannot reliably detect cross-layer conflicts at static analysis time). It is consumed by commands at runtime; `task-init`, `what-next`, and `resume-from-state` are the primary consumers as of slice 05.

### When to write each layer

- **Task fact**: it matters only for the active task. Use `sync-task-state` or `capture-observation`.
- **Project fact**: it spans all tasks under the project (stack choice, regulatory constraint, key external reference). Use `project-bootstrap` (once) or `capture-references` (ongoing). Project memory is never mutated by task-scoped commands.
- **User fact**: it spans projects AND tools (style preference, recurring tool quirk, cross-project gotcha). Edit `USER_MEMORY.md` by hand; no command writes to it.

### Coexistence with Claude Code auto-memory

The Claude Code auto-memory system at `~/.claude/projects/<id>/memory/` is a Claude-Code-private convenience. It coexists with USER_MEMORY.md without overlap:

- Use USER_MEMORY.md for multi-tool facts (will matter when you switch to Cursor / Codex / Copilot / Gemini CLI).
- Use Claude Code auto-memory for Claude-Code-only quirks.

The two systems do not synchronize. The Fhorja contract is silent on auto-memory; it lives outside the workflow surface.

## Edge cases worth noting

- **Project folder exists but `PROJECT_CHARTER.md` is missing**: this is the retroactive-bootstrap case (the project was created ad-hoc by another command before `project-bootstrap` was run). Resolution: a later `project-bootstrap` run on a partially-populated folder is allowed and will create the missing charter without disturbing existing files. `task-init` warns but does not block when this state is encountered at task creation time.
- **Multi-repo projects**: `PROJECT_CHARTER.md` carries the multi-repo schema (identifier, path, base branch, role) once at the project level. Each task's `SOURCE_OF_TRUTH.md` mirrors that schema into a `## Repositories` section via `task-init`. Single-repo and zero-repo projects record what is known under `## Default workspace` instead and skip the `## Repositories` section entirely.
- **`projects/<client>__<project>/` itself is gitignored by design**: project-level memory is per-user and per-machine; it is not part of the open-source distribution. The charter and references files persist locally so future Claude Code sessions on the same machine recover full project context, but they never enter the public repo. Any structure or wording that would be valuable to share publicly belongs in `WORKFLOW_OPERATING_SYSTEM.md`, `commands/`, or `wos/` instead.
- **Reference deduplication policy**: `capture-references` deduplicates by URL only. The same URL accessed at two different dates does not produce two entries; it updates the existing entry's `Accessed:` field. Different URLs that point to the same logical document (mirrors, archive snapshots) are treated as distinct entries; the user is responsible for noting cross-references in the summary if they matter.
- **Cross-source context (ADR-0018)**: every new REFERENCES.md entry includes a `Context within project` field naming how the source relates to the project objective AND to other refs already captured (complements / contradicts / regulatory baseline / etc.). Pre-ADR-0018 entries are grandfathered. `external-research` consumes this field when synthesizing; the recommendation explicitly distinguishes reinforcing / contradicting / different-framing source relationships rather than inferring them at synthesis time.
