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
| On an install from before 2026-09-23 | [Re-sync your install, and what `--apply` stages](#2026-09-22-re-sync-your-install-and-what---apply-stages) |
| Already mid-task when ADR-0233 to ADR-0235 landed | [task-close writes LEARNINGS.md, and a provisional decision can be replaced](#2026-09-24-task-close-writes-learningsmd-and-a-provisional-decision-can-be-replaced) |
| Moving from one-at-a-time commands to parallel fan-out | [Migrating to parallel workflow dispatch](#migrating-to-parallel-workflow-dispatch) |

---

## 2026-09-16: the chain stops asking for what it can do itself

If you have local commands or scripts that key off the old behavior, three changes matter.

**Task-memory writes.** Anything that expected `PROPOSED` in Ask or Plan now gets `APPLIED`. If you
wrote a check that asserts the old behavior, invert it: a `PROPOSED` mark justified by editor mode is
now the regression. `PROPOSED` still appears for the ADR-0034 case, where a non-owner stages a block
inside a section it does not own, and that is unchanged.

**approve-proposed.** Still there, still works, no longer in any default handoff. Invoke it when you
want a batch of ownership blocks promoted at once.

**Pipeline tiers.** `Tier: Standard` is gone from the templates. What replaces it is
`Escalations: impact-analysis (scope > 1 sentence)`, naming the disqualifier that fired. If you parse
the outcomes ledger, its `tier` field is now null for every task opened since; the fired
escalations live on the `Escalations:` line of each task's `TASK_STATE.md`, which carries more
information than the label did.

## 2026-09-22: re-sync your install, and what `--apply` stages

**Re-run the installer.** The install payload now ships four scripts next to `wos/`:
`rank-learnings.sh`, `compute-task-outcome.py`, `ingest-scan.py` and `scan-substrate-orphans.py`.
Before this, an install had none of the last three. The outcome ledger was never written, the
ingested-content poisoning scan was skipped without a word, and every fleet command's orphan gate
failed. Pull, then re-run `./scripts/sync-workflow-slash-commands.sh` the way you installed. Until
you do, your installed skills also carry the older command text. On the maintainer's machine they
were 98 bodies behind on the day this was written.

**On an install from before 2026-09-23, re-sync again.** Eleven more scripts ship (ADR-0224):
`rank-references.sh`, the four substrate scripts (`emit-substrate-write.sh`,
`scan-substrate-headers.sh`, `verify-log-validator.py`, `verify-substrate-batch.sh`),
`check-live-markers.sh`, `check-plan-coverage.sh`, `plan-adherence.py`, `memory-lint.sh`,
`secret-scan-gate.sh` and `portfolio-review.sh`. Before this, the closure integrity floor had no
script to run on an install. The commands that run these now write `not checked` or `not installed`
when one is missing, instead of reading the absence as a pass. Some exit codes changed: a helper that
found nothing to read says so and, unless its exit is advisory, exits non-zero. ADR-0224 has the
table. `portfolio-review.sh` and `check-plan-coverage.sh --all` read the directory you run them from,
so run them from the repository that holds `projects/`.

**`branch-commit --apply` respects what you staged.** If you staged part of a change before invoking
it, the commit is that staged set. Nothing is added to it, and the display names every unstaged edit
and untracked file left out. To include a new file, stage it first, or start with an empty index
(ADR-0219).

## 2026-09-23: check whether your product repository tracks `projects/`

Until today nothing kept `projects/` out of git in a product repository, so a `git add .` there could
commit your task memory. Now the command that creates `projects/` writes a `projects/.gitignore`
holding `*`, and `task-init` warns on every run while an existing project folder is not ignored
(ADR-0223). An install from before this change has no such file. Re-sync, then in each product
repository where you run tasks:

```bash
printf '*\n' > projects/.gitignore
git rm -r --cached --quiet projects 2>/dev/null   # only if task files were already committed
```

The second line removes the files from the index, not from disk, and it does not rewrite history:
a commit that already carried task memory still carries it.

## 2026-09-24: task-close writes LEARNINGS.md, and a provisional decision can be replaced

Two changes land the same day. Either can surprise a task that started before it.

**LEARNINGS.md appears at close.** `task-close` now runs a learnings pass before its archive move,
whenever the task recorded a signal: a review that asked for a revision, a check shown failing
before it passed, a fixed review finding, a refusal, a revert, a de-scope, or an unverified line
(ADR-0234). If a task you started before this change never had a `LEARNINGS.md`, this is why one
now shows up at close; the next `task-init` on the same project reads it automatically. A routine
close with no signal writes one line instead, `Learnings: none harvested (no signal recorded)`, and
nothing else changes.

**A provisional decision can carry a `Replaces:` line.** On an attended run with a remote, a
decision the request left open is recorded as a `### P-N` under `DECISIONS.md ## Provisional
decisions` (ADR-0233). If a later step in the same run finds that P-N wrong, it now corrects it by
appending a new `### P-N` carrying `Replaces: P-M` and the reason, rather than editing the old one
(ADR-0235). Reading `DECISIONS.md` on a task from before this change, you will only see single P-N
entries; from now on, follow `Replaces:` to the newest entry of a chain before you confirm or
replace one, since a plan cites only the newest entry and the draft PR lists only the current one.

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

### Step 3: run task-init with retroactive inputs already in the prompt

Put the current-state answers from Step 1 into the `task-init` prompt so the five files already reflect reality when they are written. They ARE written, in every mode, and marked `APPLIED` (ADR-0199); the mode no longer decides whether a task folder appears on disk. Choosing a mode here changes how much the run does around the write, not whether it happens.

```text
Run @commands/task-init.md

Project: <client>__<project>
Task slug: <YYYY-MM-DD>_<short-slug>
Description: <what the task is about, one paragraph>
Mode: Agent

Already true:
- Codebase and branch: <repo and branch>
- Files already touched and still expected: <paths>
- Decisions already locked: <plain statements>
- Implemented so far: <what exists, even partially>
- Still ahead: <what is uncertain or unimplemented>
- Tests / validation: <what has been tested, what has not>
```

`task-init` writes `README.md`, `TASK_STATE.md`, `SOURCE_OF_TRUTH.md`, `DECISIONS.md`, `IMPLEMENTATION_PLAN.md` into the task folder and marks them `APPLIED`, with placeholders only where those inputs still lack a fact. Read them before the next command.

### Step 4: correct the files on disk

The files are already on disk when `task-init` returns, so there is no block to persist and no window in which a later proposal could shadow an earlier one. This step used to say the opposite, at length: it told you not to hand-edit the proposed block in chat, and to run `approve-proposed` immediately with no command in between. That whole flow went with the write gate (ADR-0199). `approve-proposed` still exists for the case it was always right for, a command staging a block inside a section it does not own, and that case has nothing to do with editor mode. If a file is badly wrong, re-run `task-init` with the missing facts included; for smaller gaps, correct it as below.

Ground remaining corrections with `state-reconcile` rather than rewriting a file wholesale. Typical on-disk facts:

In **`SOURCE_OF_TRUTH.md`**:

- Replace leftover `[unknown yet]` placeholders with real codebase paths, the active branch, and the specific files you have already touched plus the ones you expect to touch.
- Add any tickets, internal docs, or links that are sources of truth for the work.

In **`DECISIONS.md`**:

- Convert decisions you have already made into numbered `D-1: <decision>` entries. Each entry should state the decision plainly and (briefly) the reasoning.
- If decisions are still in flight (you are 60% sure, but not committed), do not record them yet. They belong upstream in a `decision-interview` run, which on an attended run with a remote records the recommended option as a provisional decision under `## Provisional decisions` and continues, rather than waiting on you (ADR-0233).

In **`IMPLEMENTATION_PLAN.md`**:

- Record already-done work as entries under `## Slices` with `Status: closed` when `slice-closure` already ran, or `Status: implemented (pending closure)` if it has not. Those are the live values (`planned`, `approved`, `implemented (pending closure)`, `closed`). Include what was done, files touched, validation status, and remaining dependencies. Do not add a separate `## Completed slices` heading; planning and fleet commands consume `## Slices`.
- The remaining entries cover what is still ahead. If you do not yet know the slice structure, leave a `[to be planned]` placeholder; the next `implementation-plan` run will fill it.

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

`state-reconcile` cross-checks `TASK_STATE.md` against the other artifacts (and observable code, when relevant) and proposes the minimum set of updates so operational memory is internally consistent. Retroactive adoption is exactly the case where small inconsistencies appear. The files must already be on disk from Step 4; this command does not persist a chat proposal.

### What you should not do

- **Do not pretend you are starting over.** If you have already implemented half the work, do not write `IMPLEMENTATION_PLAN.md` as if everything is unimplemented; Fhorja does not score you on plan completeness, and accurate state matters more than plan elegance.
- **Do not skip `DECISIONS.md`.** If you have made decisions implicitly (in chat, in a Slack thread, in your head), record them now, as locked `D-N` entries, not provisional ones; a provisional entry is the agent's own choice, never a stand-in for yours. The next `decision-interview` or `resolve-contract-gaps` run uses `DECISIONS.md` as the canonical input.
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

The task-init files will be cleaner because there is no retroactive work to reconcile. Continue with the standard flow described in [`README.md`](../README.md) → `## The task loop`.

---

## Migrating from legacy slash commands to Agent Skills

If you have your own custom commands under `~/.cursor/commands/` or `~/.claude/commands/` from before adopting this workflow, you have three options for the **non-Fhorja commands** (the ones you wrote yourself, not the ones from this repo):

1. **Leave them as legacy commands**. Cursor and Claude Code still read `.claude/commands/` and `.cursor/commands/`; legacy commands continue to work. New commands you write should go to `.claude/skills/<name>/SKILL.md` so they work across all 35+ tools.
2. **Use Cursor's built-in `/migrate-to-skills`**. Cursor ships a built-in skill that converts legacy slash commands and rules into the Skills format (introduced in 2.4; the current stable line is far past that, so the version is noted as provenance rather than as a floor). Run it once on your own commands directory.
3. **Hand-convert**. For each legacy command file, create `.claude/skills/<name>/SKILL.md` with Agent Skills frontmatter (see the [open spec](https://agentskills.io/specification)) and the body. The frontmatter schema is in this repo's `commands/` files for reference.

For the **Fhorja commands themselves** (the <!-- count:commands -->98<!-- /count --> commands in this repo), there is no migration step. The Skills are generated by `scripts/build-agent-skills.sh` and committed to the repo. Cloning this repository is sufficient; the public repo's history starts fresh at v1.0.0 (docs/adr/0090-phase-3-public-release-transition.md), so there is no earlier tag to look for.

### Do NOT run `/migrate-to-skills` on this repo

The Cursor built-in `/migrate-to-skills` skill is designed for hand-authored commands that need to be converted. The Fhorja commands' canonical form **is** `commands/<name>.md`; the Skills are **generated** from them. Running `/migrate-to-skills` on this repo's `commands/` directory would produce hand-authored skill files that would then drift from the canonical commands. The lint would catch the drift, but it is wasted work.

The clean path: clone the repo, the Skills are already there. If you fork and customize commands, edit `commands/<name>.md` and run `./scripts/build-agent-skills.sh` to regenerate.

---

## Mirroring skills to user-level dirs

When you want Fhorja skills available **outside** this repo's checkout (for example, in another project's checkout, or in a global Cursor workspace), mirror them to user-level dirs:

```bash
./scripts/sync-workflow-slash-commands.sh
```

Skills sync by default; `--no-skills` skips them. The older `--with-skills` flag still parses, for backward compatibility, and changes nothing.

Default destinations: <!-- skill-roots -->`~/.claude/skills/` and `~/.agents/skills/`<!-- /skill-roots -->. Claude Code reads the first and not the second; Codex, Kimi Code and Cursor 3.17.8 or later read the second. `~/.cursor/skills/` is opt-in since ADR-0228: `--cursor-skills` writes it for Cursor Cloud Agents sync, and `--clean-orphans` removes the Fhorja skills an earlier install left there, after asking, without touching any other skill. The command files in `~/.claude/commands/` are read by Claude Code beside the skills, and whether its listing shows such a command twice is not measured yet. Override with `CLAUDE_SKILLS_DIR`, `CURSOR_SKILLS_DIR`, `CODEX_SKILLS_DIR`, `KIMI_SKILLS_DIR`, or the `--cursor-only`, `--claude-only`, `--codex-only`, and `--kimi-only` flags (which compose: pass two to select both tools). With the default Codex destination, the sync also removes matching Fhorja skills left in the legacy `~/.codex/skills/` root so Codex does not discover duplicate names.

Kimi Code CLI shares the `~/.agents/skills/` destination, which it scans natively, so the default run already covers it and the script skips the second write instead of registering every skill twice. Point `--kimi-dir=~/.kimi-code/skills` at Kimi's own home if you prefer a brand-owned copy. Kimi's runtime payload lands in `<kimi-home>/workflow-docs/` (`~/.kimi-code`, or `~/.kimi` for the older open-source `kimi-cli`, or wherever `KIMI_CODE_HOME` points).

Re-run the script after pulling upstream changes to refresh the user-level mirrors. The script is idempotent: re-running with no upstream changes does nothing.

---

## Forking and customizing

You forked the repo and want to add your own commands or change existing ones. Two rules keep your fork healthy:

1. **Edit `commands/<name>.md`, never `.claude/skills/<name>/SKILL.md` directly.** The skills are generated. Any direct edits will be overwritten by the next `build-agent-skills.sh` run, and the lint will fail on drift in the meantime.
2. **Run `./scripts/build-agent-skills.sh` after every command edit.** Or, run `./scripts/lint-commands.sh`, which invokes the build check internally and refuses to commit if the skills are out of date.

### Adding a new command

1. Create `commands/<new-name>.md` with the standard structure (look at any existing command for the shape: frontmatter `description:` stating what the command does plus its `Use when` and `Do not use when` cases, frontmatter `metadata.primary-cursor-mode:`, then the body sections `Goal:`, `Mandatory context bootstrap (before any output):`, `Required inputs:`, `Operating rules:`, `### Standard output layout (required)`, `### Artifact changes`, `### Command transcript`, `### Handoff`, `### Definition of done (command output)`).
2. Add Agent Skills frontmatter at the top (copy the frontmatter shape from any existing command).
3. Register the new command in all three registries (lint enforces this per ADR-0029): the `## Command categories` cluster list in `WORKFLOW_OPERATING_SYSTEM.md`, the per-command role detail in `wos/command-roles.md`, and the stub row in `COMMAND_PROMPT_STUBS.md`. Run `./scripts/reconcile-counts.sh` afterward: it resets the `<!-- count:commands -->` marker (and every other count marker across the scan-set) to the on-disk count in one pass, so nothing is hand-edited and `lint-commands.sh` stays clean.
4. Run `./scripts/build-agent-skills.sh` to generate `.claude/skills/<new-name>/SKILL.md`, then `python3 ./scripts/build-command-catalog.py` to regenerate the command catalog (`docs/command-catalog.html` and `docs/command-catalog.json`; the README's `## Command catalog` section is a pointer to them). Lint fails on catalog drift if you skip this.
5. Run `./scripts/lint-commands.sh` and fix any failures.
6. Commit. The skill is now available to any of the 35+ tools that read `.claude/skills/`.

### Modifying an existing command

1. Edit `commands/<name>.md`.
2. If your edit touches a shared block (`commands/_shared/<name>.md`), run `./scripts/sync-shared-blocks.sh` to propagate.
3. Run `./scripts/build-agent-skills.sh`, then `python3 ./scripts/build-command-catalog.py` if you changed any catalog input: command `description`, `metadata.category`, primary mode, suggested model, multi-repo awareness, lifecycle, prompt stubs in `COMMAND_PROMPT_STUBS.md`, or next-command roles in `wos/command-roles.md` (the catalog regenerates from those).
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

The project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html). It passed 1.0.0 on 2026-07-10 and 1.1.0 on 2026-07-21, and the current release is 2.0.0: see the `[2.0.0]` section of `CHANGELOG.md`. No git tag marks 2.0.0 yet; the note on tags at the top of the changelog explains why. Per `README.md`'s status line, breaking changes to command output or the `TASK_STATE.md` schema require a MAJOR bump, while MINOR and PATCH stay backward compatible.

### Patch (2.0.x → 2.0.y)

Drop-in for the central checkout. Pull. If you use user-level mirrors, re-run `./scripts/sync-workflow-slash-commands.sh` the same way you installed: pass `--profile TIER` only if you passed it then; if you used the wizard or omitted `--profile`, omit it again. If you also copied into a product repo, add `--project /path/to/your/repo`. Then run `./scripts/lint-commands.sh` to confirm clean state, and continue.

### Minor (2.0.x → 2.1.x)

Largely backward compatible, but **review the new release section of `CHANGELOG.md`** before pulling. Common minor-bump impact:

- New commands added (additive; ignore if you do not need them).
- New spec sections or lazy-loaded `wos/` topics (additive; cited where they are needed).
- Renames or splits in spec sections (the Minimum read map at the top of the spec lists current section names; update any of your own scripts that grep for old names).

If you have an in-flight task from an older minor release and the upgrade introduces new optional task files, your task continues to work without those files. They are optional by design.

### Major (1.x → 2.0.0)

2.0.0 is the second major jump; the first, 0.x.y to 1.0.0, shipped 2026-07-10 (see the `[1.0.0]` entry in `CHANGELOG.md`). The `[2.0.0]` section of `CHANGELOG.md` lists every change. What you do after pulling:

- **Re-sync your install.** Run `./scripts/sync-workflow-slash-commands.sh` the way you installed. Skills sync by default. Until you re-sync, your installed skills keep the 1.x command text, and nothing below reaches you.
- **Paste the directive into every repository you work in, once.** `templates/AGENT_DIRECTIVE.template.md` holds one paragraph for that repository's always-loaded instruction file (`CLAUDE.md`, `AGENTS.md`, or your editor's rules file). Installing the commands gives an agent the vocabulary; that paragraph is the instruction to use it. Measured, not assumed: with the commands installed and nothing else, a model handed a one-file task did the task and never opened one; with the paragraph, the same model on the same brief ran the whole chain. The installer does not write it for you, deliberately, because editing the file that governs an agent's behavior without being asked is the act the trust rules gate.
- **Read `Escalations:` where you read `Tier:`.** This is the `TASK_STATE.md` schema change that makes 2.0.0 a major release. The tier labels (Express, Standard, Disciplined, Strict) are retired (ADR-0207). `## Recommended pipeline` now records `Escalations: none`, or each added command with the disqualifier that added it, such as `Escalations: impact-analysis (scope > 1 sentence)`. A task opened under 1.x keeps working; a script of yours that parses `Tier:` needs the new line.

What changes in behavior, in short:

- **The default pipeline is short and has no name.** `task-init -> implementation-plan -> approve-plan -> implement-approved-slice -> branch-commit --apply`, which on an attended run with a configured remote continues into `pr-package --apply` and the draft PR (ADR-0184, ADR-0233). `task-init` adds a command only when it can name a disqualifier: a scope that needs more than one sentence, five or more files, a decision the prompt does not contain, a change that spans multiple packages or adds an external service, or an auth, payments, compliance, PII, or multi-tenant surface. "I am not sure" is explicitly not a disqualifier.
- **The chain runs itself, all the way to a draft PR when the repository has a remote.** A command's `Run now:` line is what an attended session does next, in the same turn. On a git repository with a configured remote, the chain runs from `task-init` to the pushed task branch and the draft PR, and stops only for a reason it names: an act whose audience is not bounded, meaning marking the PR ready for review, merging, publishing, or sending content outward. A decision the request did not settle, or a check the agent cannot honestly run on itself, no longer stop it; both get recorded and carried into the draft PR instead (ADR-0186, ADR-0233). Without a remote, those two still stop and wait. A declared `Operating mode: assisted` brings back every stop ADR-0233 removed: no task branch is created, open decisions and checks the agent cannot run on itself stop and wait, and the chain ends at the local commit, where you start the push and the draft PR. When one turn runs several commands you get ONE `### Handoff` for the turn (ADR-0192); the per-command record is the task folder on disk.
- **Task memory is written, not proposed.** Commands write their task files `APPLIED` in every editor mode (ADR-0199, ADR-0215). `PROPOSED` survives only as a block a command stages in a section another command owns (ADR-0034), and `approve-proposed` left the default chain.
- **`approve-plan` runs on every plan and approves itself** on a blinded review in an isolated context, with a second pass on a strict surface; only an ESCALATED exit reaches you (ADR-0208).
- **The one-slice route skips the plan.** An attended one-sentence change to at most two named files, with every decision in the prompt and no escalation, gets its approved slice from `task-init`; `implement-approved-slice` runs `scripts/check-doc-sync.sh --against HEAD` at inline close in place of the review (ADR-0225).
- **Commits and pushes.** `branch-commit --apply` creates the local commit after showing the staged diff, with no second confirmation (ADR-0163, ADR-0219). On an attended run with a configured remote, `pr-package --apply` then pushes the branch and opens the draft PR on its own, without waiting to be asked (ADR-0185, ADR-0233); without a remote, or in a declared assisted mode, the chain ends at the local commit. Marking the PR ready for review and merging stay human.
- **Closure floors record rather than wait.** A floor with no evidence records `unverified: <reason>` and the slice closes; `task-close` lists every such floor (ADR-0203, ADR-0205).

For anything not listed here, the `[2.0.0]` section of `CHANGELOG.md` is the full record. A future major will follow the same pattern: a migration section in `CHANGELOG.md` listing every breaking change, the symptom (what fails after the upgrade), and the fix (what to edit).

### How to know when an upgrade is safe

1. Read `CHANGELOG.md` for the version range you are crossing.
2. Run `./scripts/lint-commands.sh` after pulling. Lint failures are the most likely surface for upgrade-induced drift (especially shared-block mismatches and skills drift).
3. Run `python3 ./scripts/measure-tokens.py` and compare against the latest `scripts/baseline-*.md` snapshot to confirm the upgrade did not blow up the spec unexpectedly.
4. If you have active tasks, run `state-reconcile` against each one before resuming work; it will surface any artifact-level drift introduced by the upgrade.

---

## Migrating to parallel workflow dispatch

You have been running workflow commands one at a time (linear invocation: run `decision-interview`, wait, run `implementation-plan`, wait, run `implement-approved-slice`, wait). Two parallel paths exist, and they are not interchangeable.

- **Approved slice execution** uses `implement-fleet` when a remaining wave has size 2 or more with `Scope` and `Depends-on`. Each fleet command has its own `max_fanout` (8 for `implement-fleet`) under a platform ceiling of 20. The orchestrator names its dispatch path before dispatch; workers return the runtime's typed result on the dynamic-workflow path, or write `fleet-inbox/<run_id>/<worker_id>.json` on the `Agent` path.
- **Read-only Workflow research batches** (fleet audits, multi-component spec generation, isolated refactors) fan out 15 to 25 agents in a single Workflow tool batch per ADR-0039. The same host and independence rules apply; the return carrier is the one the orchestrator named, not a universal `StructuredOutput` call by the worker.

This is **opt-in additive**. Existing sequential workflows are unchanged; no slash command behavior shifts. Parallel dispatch is a new operating mode you reach for when the work shape fits.

### Prerequisites

- **AI tool: Claude Code.** Both paths need a host that can run concurrent subagent threads. Other tools (Cursor, Codex, Copilot) degrade gracefully: the underlying commands still run sequentially, you just lose the fan-out throughput. No code path breaks.
- **Independent work items.** No two agents may write to the same file. Read overlap is fine.
- **A structural scan.** `python3 scripts/scan-substrate-orphans.py <task-folder>` (or the named files the batch wrote) runs after the batch. It detects bullet lines that sit outside an H2-owned section. A nonzero result blocks the merge or phase until you correct the structure and the scan returns clean.
- **Single-writer-per-folder discipline.** Per ADR-0040, no two agents in a batch may write to the same folder (not just the same file). If two work items target the same folder, sequence them or merge.

### Before-state: linear command invocation

```text
Run @commands/atom-audit.md   (component A)   -- 4 min
Run @commands/atom-audit.md   (component B)   -- 4 min
Run @commands/atom-audit.md   (component C)   -- 4 min
... 20 more components, sequentially         -- ~90 min total
```

### After-state: research batches of 15 to 25, or an implement-fleet wave

```text
Approved slices (implement-fleet):
  remaining wave of size 2 or more, each command's max_fanout, ceiling 20
  named carrier: runtime typed result, or fleet-inbox/<run_id>/<worker_id>.json

Research batch (Workflow tool):
  Agent 1: atom-audit component A   ]
  Agent 2: atom-audit component B   ] dispatched together
  ...                                ] each returns through the named carrier
  Agent 23: atom-audit component W  ]
  total wall-clock: about 4-6 min for the slowest agent in the batch
```

### Migration steps

1. **Identify independent work items.** List the units of work. For each pair, confirm no shared file writes. If two items must touch the same file, keep them sequential or merge them into one agent.
2. **Author focused 300-500 word prompts per agent.** Each prompt is self-contained: task summary, inputs, expected output shape, success criteria. Longer than 500 words signals the work item is too broad to parallelize cleanly; split it.
3. **Name the dispatch path, then end each prompt with the matching carrier line.** On the dynamic-workflow path the script declares `agent(prompt, {schema})` and the runtime performs the `StructuredOutput` call; end that worker prompt with `Return one payload matching worker_output_schema and nothing else`. On the `Agent` path the worker writes a schema-conforming JSON file; end that prompt with `Write one JSON payload matching worker_output_schema to fleet_inbox_artifact and nothing else`. Never instruct a worker to call `StructuredOutput`. The orchestrator reads only the named carrier.
4. **Wrap dispatch with `python3 scripts/scan-substrate-orphans.py` after the batch settles.** Invoke it on the task folder (`python3 scripts/scan-substrate-orphans.py <task-folder>`) or on the exact files the batch wrote. It detects bullet lines that sit outside an H2-owned section. If it reports any, correct the structure and re-run until it exits 0 before advancing the phase. It does not inventory unregistered files and it does not offer keep, move, or delete.
5. **(Optional) Use `scripts/monitor-fleet-progress.sh <run_id> <task_folder>` during dispatch.** The run inbox `<task_folder>/.wos/fleet-inbox/<run_id>/` must already exist. For long-running batches, this script tails per-agent progress so you can intervene early on a clearly-failing agent instead of waiting for the full batch to settle.

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

