# Migration guide

How to adopt this workflow when you do not start from a clean slate. Each scenario below is self-contained; jump to the one that matches your situation.

| You are... | Go to |
|---|---|
| Mid-task on an engineering work item that did not use this workflow | [Adopting Fhorja on an in-progress task](#adopting-fhorja-on-an-in-progress-task) |
| Starting a brand-new project from zero | [Adopting Fhorja on a new project](#adopting-fhorja-on-a-new-project) |
| A Cursor or Claude Code user with existing `.cursor/commands/` or `.claude/commands/` | [Migrating from legacy slash commands to Agent Skills](#migrating-from-legacy-slash-commands-to-agent-skills) |
| Wanting Fhorja skills available outside this repo's checkout | [Mirroring skills to user-level dirs](#mirroring-skills-to-user-level-dirs) |
| Forking this repo to customize the workflow | [Forking and customizing](#forking-and-customizing) |
| Upgrading between Fhorja versions | [Upgrading between Fhorja versions](#upgrading-between-fhorja-versions) |
| Moving from one-at-a-time commands to parallel fan-out | [Migrating to parallel workflow dispatch](#migrating-to-parallel-workflow-dispatch) |

---

## Adopting Fhorja on an in-progress task

You are partway through an engineering task: maybe you have a branch with several commits, a draft PR, scattered notes, and a decision or two already made. You want to bring that work under Fhorja without restarting.

The key idea: **`task-init` is creation, not retrofitting**. It will write a fresh task folder, but the contents of `SOURCE_OF_TRUTH.md`, `DECISIONS.md`, and `IMPLEMENTATION_PLAN.md` should reflect what is **already true** about the work, not pretend you are starting over.

### Step 1: capture the current state of your work in your head

Before invoking any command, briefly answer these for yourself (you will paste them as inputs):

- **Codebase and branch**: which repo and branch is the work on?
- **Files in scope**: which files have you already touched, and which others do you expect to touch?
- **Decisions already made**: any decisions about behavior, contracts, schema, or rollout that are already locked? (Include the ones from chat history, internal docs, or PR descriptions.)
- **Implementation done so far**: what has been implemented, even partially?
- **Implementation still ahead**: what is still uncertain or unimplemented?
- **Tests / validation status**: what has been tested, what has not?

This is information you already have; Fhorja just wants it written down.

### Step 2: bootstrap the project (if it does not exist yet)

If `projects/<client>__<project>/` does not exist, create it first. Run `project-bootstrap`:

```text
Run @commands/project-bootstrap.md

Project: <client>__<project>
Objective: <one paragraph from your head>
Stack: <or [not decided yet]>
Repositories: <or [unknown yet]>
```

`project-bootstrap` only creates `PROJECT_CHARTER.md` and `REFERENCES.md`; it never creates a task folder. If the project folder already exists, skip this step.

### Step 3: run task-init with retroactive inputs

```text
Run @commands/task-init.md

Project: <client>__<project>
Task slug: <YYYY-MM-DD>_<short-slug>
Description: <what the task is about, one paragraph>
Mode: Ask (so the proposed files are PROPOSED, not APPLIED)
```

`task-init` will propose `README.md`, `TASK_STATE.md`, `SOURCE_OF_TRUTH.md`, `DECISIONS.md`, `IMPLEMENTATION_PLAN.md` for the task folder, with placeholders where it lacks information. Review the proposals.

### Step 4: hand-edit the proposed files to reflect reality

This is the retroactive part. The proposals from `task-init` assume you are starting fresh; you are not.

In **`SOURCE_OF_TRUTH.md`**:

- Replace `[unknown yet]` placeholders with real codebase paths, the active branch, and the specific files you have already touched plus the ones you expect to touch.
- Add any tickets, internal docs, or links that are sources of truth for the work.

In **`DECISIONS.md`**:

- Convert decisions you have already made into numbered `D-1: <decision>` entries. Each entry should state the decision plainly and (briefly) the reasoning.
- If decisions are still in flight (you are 60% sure, but not committed), do not record them yet. They belong upstream in a `decision-interview` run.

In **`IMPLEMENTATION_PLAN.md`**:

- Add a `## Completed slices` section listing what has already been implemented. Each entry: slice name, what was done, files touched, validation status.
- The main slice-by-slice plan covers what remains. If you do not yet know the slice structure, leave a `[to be planned]` placeholder; the next `implementation-plan` run will fill it.

In **`TASK_STATE.md`**:

- Set `## Current phase` to where you really are: probably `implementation` (you are mid-task) or `review` (you are nearly done).
- Set `## Last completed step` to the most recent meaningful step (a commit, a test pass, a PR review round).
- Fill `## Current known facts` and `## Canonical decisions` with the work already locked in.
- Set `## Recommended next step` to whichever command makes sense from where you are; common starting points after retroactive adoption:
  - `state-reconcile` if the artifacts you just wrote disagree with each other
  - `where-we-at` to checkpoint progress against the plan
  - `implement-slice-complement` if the remaining work is small and within an already-executed slice
  - `implementation-plan` if the remaining work needs slice planning before execution
  - `pr-package` if the work is essentially complete

### Step 5: confirm with state-reconcile (recommended)

```text
Run @commands/state-reconcile.md

projects/<client>__<project>/active/YYYY-MM-DD_<slug>/
```

`state-reconcile` cross-checks `TASK_STATE.md` against the other artifacts (and observable code, when relevant) and proposes the minimum set of updates so operational memory is internally consistent. Retroactive adoption is exactly the case where small inconsistencies appear.

### What you should not do

- **Do not pretend you are starting over.** If you have already implemented half the work, do not write `IMPLEMENTATION_PLAN.md` as if everything is unimplemented; Fhorja does not score you on plan completeness, and accurate state matters more than plan elegance.
- **Do not skip `DECISIONS.md`.** If you have made decisions implicitly (in chat, in a Slack thread, in your head), record them now. The next `decision-interview` or `resolve-contract-gaps` run uses `DECISIONS.md` as the canonical input.
- **Do not skip the warning if the project was not bootstrapped.** `task-init` will warn if `PROJECT_CHARTER.md` is missing; treat that warning seriously and run `project-bootstrap` retroactively if the project will have more than one task.

---

## Adopting Fhorja on a new project

Brand-new project, no existing work. This is the simplest path.

```text
Run @commands/project-bootstrap.md

Project: <client>__<project>
Objective: <one paragraph>
Stack: <languages, frameworks, runtime>
Repositories: <one entry per repo if multi-repo; otherwise a default workspace>
References: <URLs to seed REFERENCES.md, or "none yet">
Constraints: <regulatory, performance, deadlines, or "none yet">
Non-goals: <explicit, or "none yet">
Stakeholders: <names or roles, or "[not recorded yet]">
```

After `project-bootstrap`:

```text
Run @commands/task-init.md

Project: <client>__<project>
Task slug: <YYYY-MM-DD>_<short-slug>
Description: <task objective, one paragraph>
```

The task-init proposal will be cleaner because there is no retroactive work to reconcile. Continue with the standard flow described in [`README.md`](../README.md) → `## The task loop`.

---

## Migrating from legacy slash commands to Agent Skills

If you have your own custom commands under `~/.cursor/commands/` or `~/.claude/commands/` from before adopting this workflow, you have three options for the **non-Fhorja commands** (the ones you wrote yourself, not the ones from this repo):

1. **Leave them as legacy commands**. Cursor 2.4+ and Claude Code still read `.claude/commands/` and `.cursor/commands/`; legacy commands continue to work. New commands you write should go to `.claude/skills/<name>/SKILL.md` so they work across all 35+ tools.
2. **Use Cursor's built-in `/migrate-to-skills`**. Cursor 2.4+ ships a built-in skill that converts legacy slash commands and rules into the Skills format. Run it once on your own commands directory.
3. **Hand-convert**. For each legacy command file, create `.claude/skills/<name>/SKILL.md` with Agent Skills frontmatter (see the [open spec](https://agentskills.io/specification)) and the body. The frontmatter schema is in this repo's `commands/` files for reference.

For the **Fhorja commands themselves** (the <!-- count:commands -->94<!-- /count --> commands in this repo), there is no migration step. The Skills are generated by `scripts/build-agent-skills.sh` and committed to the repo. Cloning v0.1.0+ is sufficient.

### Do NOT run `/migrate-to-skills` on this repo

The Cursor built-in `/migrate-to-skills` skill is designed for hand-authored commands that need to be converted. The Fhorja commands' canonical form **is** `commands/<name>.md`; the Skills are **generated** from them. Running `/migrate-to-skills` on this repo's `commands/` directory would produce hand-authored skill files that would then drift from the canonical commands. The lint would catch the drift, but it is wasted work.

The clean path: clone v0.1.0+, the Skills are already there. If you fork and customize commands, edit `commands/<name>.md` and run `./scripts/build-agent-skills.sh` to regenerate.

---

## Mirroring skills to user-level dirs

When you want Fhorja skills available **outside** this repo's checkout (for example, in another project's checkout, or in a global Cursor workspace), mirror them to user-level dirs:

```bash
./scripts/sync-workflow-slash-commands.sh --with-skills
```

Default destinations: `~/.claude/skills/`, `~/.cursor/skills/`, `~/.codex/skills/`. Override with `CLAUDE_SKILLS_DIR`, `CURSOR_SKILLS_DIR`, `CODEX_SKILLS_DIR`, or `--cursor-only` / `--claude-only` flags.

Re-run the script after pulling upstream changes to refresh the user-level mirrors. The script is idempotent: re-running with no upstream changes does nothing.

---

## Forking and customizing

You forked the repo and want to add your own commands or change existing ones. Two rules keep your fork healthy:

1. **Edit `commands/<name>.md`, never `.claude/skills/<name>/SKILL.md` directly.** The skills are generated. Any direct edits will be overwritten by the next `build-agent-skills.sh` run, and the lint will fail on drift in the meantime.
2. **Run `./scripts/build-agent-skills.sh` after every command edit.** Or, run `./scripts/lint-commands.sh`, which invokes the build check internally and refuses to commit if the skills are out of date.

### Adding a new command

1. Create `commands/<new-name>.md` with the standard structure (look at any existing command for the shape: `Goal:`, `Mandatory context bootstrap:`, `Use when:` / `Do not use when:`, `Primary editor mode:`, `Required inputs:`, `Operating rules:`, `### Standard output layout`, `### Artifact changes`, `### Command transcript`, `### Handoff`, `### Definition of done`).
2. Add Agent Skills frontmatter at the top (copy the frontmatter shape from any existing command).
3. Register the new command in all four registries (lint enforces this per ADR-0029): the `## Command categories` cluster list and the `## Command roles` index in `WORKFLOW_OPERATING_SYSTEM.md`, the per-command role detail in `wos/command-roles.md`, and the stub row in `COMMAND_PROMPT_STUBS.md`. Bump the `<!-- count:commands -->` markers to match the on-disk count.
4. Run `./scripts/build-agent-skills.sh` to generate `.claude/skills/<new-name>/SKILL.md`, then `python3 ./scripts/build-command-catalog.py` to regenerate the command catalog (`docs/command-catalog.html` plus the README `## Command catalog` section). Lint fails on catalog drift if you skip this.
5. Run `./scripts/lint-commands.sh` and fix any failures.
6. Commit. The skill is now available to any of the 35+ tools that read `.claude/skills/`.

### Modifying an existing command

1. Edit `commands/<name>.md`.
2. If your edit touches a shared block (`commands/_shared/<name>.md`), run `./scripts/sync-shared-blocks.sh` to propagate.
3. Run `./scripts/build-agent-skills.sh`, then `python3 ./scripts/build-command-catalog.py` if you changed the `description` or `metadata.category` (the catalog and README section regenerate from those).
4. Run `./scripts/lint-commands.sh`.
5. Commit.

### Pulling upstream changes

Standard `git fetch upstream && git merge upstream/main` works. After merging:

1. Resolve any merge conflicts in `commands/<name>.md`.
2. Run `./scripts/sync-shared-blocks.sh` if shared blocks changed upstream.
3. Run `./scripts/build-agent-skills.sh` and `python3 ./scripts/build-command-catalog.py`.
4. Run `./scripts/lint-commands.sh` to catch drift introduced by the merge.
5. Commit the regenerated artifacts.

If your fork has diverged significantly (added several commands, restructured shared blocks, etc.), expect merge conflicts in `commands/_shared/`, the command index, and the lazy-loaded `wos/` files. The lint will catch most issues; manual review of the merged command index is still worth doing.

---

## Upgrading between Fhorja versions

The project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html). Until v1.0.0, MINOR bumps may include breaking changes; expect more stability after 1.0.0.

### Patch (0.1.x → 0.1.y)

Drop-in. Pull, run `./scripts/lint-commands.sh` to confirm clean state, continue.

### Minor (0.1.x → 0.2.x)

Largely backward compatible, but **review `CHANGELOG.md` `[Unreleased]` and the new release section** before pulling. Common minor-bump impact:

- New commands added (additive; ignore if you do not need them).
- New spec sections or lazy-loaded `wos/` topics (additive; cited where they are needed).
- Renames or splits in spec sections (the Minimum read map at the top of the spec lists current section names; update any of your own scripts that grep for old names).

If you have an in-flight task using v0.1.x and the upgrade introduces new optional task files, your task continues to work without those files. They are optional by design.

### Major (0.x.y → 1.0.0; future 1.x → 2.x)

Pre-1.0 majors are not yet planned but may include:

- `TASK_STATE.md` schema changes (new required fields, renamed sections).
- `commands/*.md` contract changes (new mandatory sections in the standard output layout).
- Breaking changes to lint rules or shared-block markers.

Each major release will ship with a dedicated migration section in `CHANGELOG.md` listing every breaking change, the symptom (what fails after the upgrade), and the fix (what to edit). For a 0.x → 1.0.0 jump, expect a migration script under `scripts/migrate-to-vX.sh` if the changes are mechanical, or hand-edit instructions if they require judgment.

### How to know when an upgrade is safe

1. Read `CHANGELOG.md` for the version range you are crossing.
2. Run `./scripts/lint-commands.sh` after pulling. Lint failures are the most likely surface for upgrade-induced drift (especially shared-block mismatches and skills drift).
3. Run `python3 ./scripts/measure-tokens.py` and compare against the latest `scripts/baseline-*.md` snapshot to confirm the upgrade did not blow up the spec unexpectedly.
4. If you have active tasks, run `state-reconcile` against each one before resuming work; it will surface any artifact-level drift introduced by the upgrade.

---

## Migrating to parallel workflow dispatch

You have been running workflow commands one at a time (linear invocation: run `decision-interview`, wait, run `implementation-plan`, wait, run `implement-approved-slice`, wait). For tasks where many independent work items exist (fleet audits, multi-component spec generation, broad refactors with isolated file scopes), parallel dispatch fans out 15-25 agents in a single Workflow tool batch, each producing a `StructuredOutput` result the orchestrator aggregates.

This is **opt-in additive**. Existing sequential workflows are unchanged; no slash command behavior shifts. Parallel dispatch is a new operating mode you reach for when the work shape fits.

### Prerequisites

- **AI tool: Claude Code.** Parallel dispatch leans on the Workflow tool batch primitive and `StructuredOutput` aggregation. Other tools (Cursor, Codex, Copilot) degrade gracefully: the underlying commands still run sequentially, you just lose the fan-out throughput. No code path breaks.
- **Independent work items.** No two agents may write to the same file. Read overlap is fine.
- **A scan/cleanup script.** `scripts/scan-substrate-orphans.py` runs after the batch to catch any orphaned artifacts produced by partial-failure agents.
- **Single-writer-per-folder discipline.** Per ADR-0040, no two agents in a batch may write to the same folder (not just the same file). If two work items target the same folder, sequence them or merge.

### Before-state: linear command invocation

```text
Run @commands/atom-audit.md   (component A)   -- 4 min
Run @commands/atom-audit.md   (component B)   -- 4 min
Run @commands/atom-audit.md   (component C)   -- 4 min
... 20 more components, sequentially         -- ~90 min total
```

### After-state: Workflow tool batches of 15-25 agents

```text
Workflow tool batch:
  Agent 1: atom-audit component A   ]
  Agent 2: atom-audit component B   ] all dispatched in one call
  ...                                ] each returns StructuredOutput
  Agent 23: atom-audit component W  ]
-- total wall-clock: ~4-6 min for the slowest agent in the batch
```

### Migration steps

1. **Identify independent work items.** List the units of work. For each pair, confirm no shared file writes. If two items must touch the same file, keep them sequential or merge them into one agent.
2. **Author focused 300-500 word prompts per agent.** Each prompt is self-contained: task summary, inputs, expected output shape, success criteria. Longer than 500 words signals the work item is too broad to parallelize cleanly; split it.
3. **Add explicit StructuredOutput reminder to each prompt.** Every prompt ends with a directive that the agent MUST call `StructuredOutput` exactly once with the agreed schema. The orchestrator reads only that tool call.
4. **Wrap dispatch with `scripts/scan-substrate-orphans.py` post-apply.** Run the scan after the batch settles. It surfaces artifacts an agent created but did not register, so the operator can decide whether to keep, move, or delete them.
5. **(Optional) Use `scripts/monitor-fleet-progress.sh` during dispatch.** For long-running batches, this script tails per-agent progress so you can intervene early on a clearly-failing agent instead of waiting for the full batch to settle.

### References

- [`docs/adr/0038-workflow-tool-as-parallel-orchestration-primitive.md`](./adr/0038-workflow-tool-as-parallel-orchestration-primitive.md): the decision to adopt the Workflow tool as canonical parallel-orchestration primitive.
- [`docs/adr/0039-workflow-batch-dispatch-empirical.md`](./adr/0039-workflow-batch-dispatch-empirical.md): empirical 15-25 batch-size sweet spot for parallel dispatch waves.
- [`wos/workflow-patterns.md`](../wos/workflow-patterns.md): the canonical patterns for fan-out, prompt sizing, and post-batch reconciliation.

### Note

Sequential workflows remain the default. Reach for parallel dispatch when the work shape (many independent items, isolated file scopes) makes the fan-out worth the prompt-authoring overhead.

---

## See also

- [`README.md`](../README.md): user-facing entry point with day-to-day quick start and full distribution story.
- [`WORKFLOW_OPERATING_SYSTEM.md`](../WORKFLOW_OPERATING_SYSTEM.md): the normative spec.
- [`docs/FAQ.md`](./FAQ.md): common questions about scope, install, multi-tool support, licensing.
- [`docs/adr/`](./adr/): Architecture Decision Records explaining the why behind load-bearing decisions.
- [`CHANGELOG.md`](../CHANGELOG.md): full release history.
- [`ROADMAP.md`](../ROADMAP.md): forward-looking direction.


