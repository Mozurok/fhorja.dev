# FAQ

Common questions about Fhorja, a workflow operating system. If your question is not here, check [`README.md`](../README.md) for the user-facing entry point or [`WORKFLOW_OPERATING_SYSTEM.md`](../WORKFLOW_OPERATING_SYSTEM.md) for the normative spec.

## What is this repo?

A **markdown plus bash specification** of an AI-assisted engineering workflow for solo and small-team developers. The deliverables are documents (the workflow operating system spec, command files, templates) and small scripts (lint, sync, build adapters). There is no application runtime, no server, no persistence, no hosted service.

The workflow's job is to make AI-assisted engineering **resumable, auditable, and disciplined**: every step produces grounded artifacts, every command ends with a runnable next step, every plan is reviewable before it is applied.

## Why is the repo called `fhorja.dev` when the project is called Fhorja?

The repository takes its name from the project's site. Fhorja is the workflow; `fhorja.dev` is where
it is published and documented. Cloning `Mozurok/fhorja.dev` gives you the workflow, not the website
source. There is no second workflow repository to look for.

## When does a task get the short pipeline?

By default, every task does. `task-init` starts from the short path, `implementation-plan -> approve-plan -> implement-approved-slice -> branch-commit`, which on an attended run with a configured remote continues on into `pr-package --apply` and the draft PR (ADR-0233), and adds a command only when a named condition fires. It writes the condition into `## Recommended pipeline`, as `Escalations: impact-analysis (scope > 1 sentence)` or `Escalations: none` (ADR-0184, ADR-0207). A scope that needs more than one sentence, or 5 or more files, adds `impact-analysis`. A decision the prompt does not contain, several packages, or a new external service adds `decision-interview`. An auth, payments, compliance, PII or multi-tenant surface adds `invariants-and-non-goals`, `test-strategy` and `review-hard`. Uncertainty is not a condition: "I am not sure" leaves a task on the short path.

This used to be called Express. ADR-0207 retired the name because it did no routing work; the conditions did. `approve-plan` runs on every plan and does not wait for you (ADR-0208), except on the one-slice route, where a one-sentence change to at most two named files with every decision in the prompt and no provisional decision gets its approved slice from `task-init` and a `check-doc-sync.sh --against HEAD` run in place of the review (ADR-0225), and the task files are written in every mode, Ask included (ADR-0199). `--apply` creates the local commit after the staged diff is shown. On an attended run with a configured remote, `pr-package --apply` then pushes the branch and opens the draft PR on its own (ADR-0233). Without a remote, or in a declared assisted mode, the chain ends at the local commit; in assisted mode you run `pr-package --apply` or ask for it. Marking that PR ready for review and merging stay yours. A declared `Operating mode: strict` in `TASK_STATE.md ## Resume notes` runs invariants and tests before `approve-plan`. Unattended, background and fleet runs do not create the commit. Generated skills are already model-invocable.

## Why markdown plus bash, not a runtime tool?

Three reasons:

1. **Tool portability**. Markdown and bash run anywhere. The workflow targets Cursor, Claude Code, GitHub Copilot, OpenAI Codex, Gemini CLI, OpenHands, Goose, Junie, and 35+ others without per-tool integration. A runtime would need plugins per tool.
2. **Open-source-friendly distribution**. Static markdown is trivially open-source-compatible. The repo can be cloned, forked, and adapted with no installation step.
3. **Explicit over magical**. The workflow's value is its discipline (mandatory phases, review gates, Handoffs that name the next command). Wrapping that discipline in code would hide it; markdown surfaces it where contributors can audit and refine it.

A future hosted SaaS layer (exploratory, not committed) might wrap the workflow with server-side execution, sandboxing, and persistence. That is a separate product, not a replacement for the markdown layer.

## Does this work offline?

Cloning the repo and reading task memory needs no network access at all; the markdown files and scripts are entirely local. Running a command does need whatever your AI coding tool needs (most require a live connection to their model provider), so Fhorja is only as offline-capable as the underlying tool. A few individual commands additionally reach out on their own: `capture-references` fetches URLs, `external-research` synthesizes already captured sources and does not fetch, and the Figma commands need their MCP server reachable. `db-context-supabase` needs either the Supabase MCP server or the local Supabase CLI it falls back to, and `db-context-postgres` needs no MCP, only the database itself, reached through `psql` or `pg_dump`. Every other command works against local files only.

## Which AI tools work with this?

Any tool that reads `.claude/skills/<name>/SKILL.md` natively works as a drop-in. As of 2026-09-17 that includes (but is not limited to) Claude Code, Cursor, GitHub Copilot, OpenAI Codex, Gemini CLI, OpenHands, Goose, Junie, Mistral Vibe, Snowflake Cortex, Databricks Genie, Kimi Code CLI. Version numbers are deliberately absent: they age and the capability does not. Cursor's own documentation states it "also loads skills from Claude and Codex directories: `.claude/skills/`, `.codex/skills/`, `~/.claude/skills/`, and `~/.codex/skills/`" (cursor.com/docs/skills, read 2026-09-17), which is the checkable fact. Zed and Factory read the vendor-neutral `.agents/skills/` and deliberately do not read `.claude/skills/`, which is why the installer writes both. The skills are generated from `commands/*.md` by `scripts/build-agent-skills.sh` and committed to the repo, so cloning is sufficient.

For tools that only read legacy `.claude/commands/` or `.cursor/commands/`, the same `commands/*.md` files are mirrored to those directories by `scripts/sync-workflow-slash-commands.sh`.

For tools without either pattern, the canonical command files are still readable as plain markdown; users can `@`-mention them or paste their content into the tool.

## How do I install it?

```bash
git clone https://github.com/Mozurok/fhorja.dev.git
cd fhorja.dev
```

That is the install, and you do it once, in its own directory, not once per product project. This repo never becomes your working directory while you code; your product repo stays separate and keeps its own git history. To use it:

- **Run `./scripts/sync-workflow-slash-commands.sh` once.** Skills sync by default to your user-level directories, so any product repo you open in an editor that reads Agent Skills (Claude Code, Cursor, Copilot, Codex) picks them up automatically, with no per-project step. Pass `--no-skills` to skip them.
- **Bare on a terminal, it opens a setup wizard**; pick **Sync everything** on a first run. Pass any flag, or run it in CI or a pipe, and it runs non-interactively: it covers Cursor, Claude Code, Codex, and Kimi Code, copies the `minimal` command files, and mirrors every skill. `--profile core` or `--profile full` copies more command files. Command defaults: `~/.cursor/commands/`, `~/.claude/commands/`, `~/.codex/prompts/`. Override paths with `--cursor-dir=` and `--claude-dir=` or via env vars.
- **Skill destinations** (so skills reach every project you open, not only this one): <!-- skill-roots -->`~/.claude/skills/` and `~/.agents/skills/`<!-- /skill-roots -->. Claude Code reads the first and does not read `~/.agents/skills/` (checked 2026-09-23 against its skills documentation and issue tracker). Codex and Kimi Code read the second, and so does Cursor from 3.17.8, the release that fixed loading it; on an older Cursor, update it or pass `--cursor-skills`.
- **`~/.cursor/skills/` is opt-in.** `--cursor-skills` writes it as well, which only Cursor Cloud Agents sync needs, since that is the one root it syncs; Cursor then lists each skill twice. An install from before ADR-0228 left the skills there; `--clean-orphans` removes the Fhorja ones after asking, and leaves any other skill in that directory alone.
- **What is not measured yet.** The sync also writes command files to `~/.claude/commands/`, which Claude Code reads beside `~/.claude/skills/`, so a command installed both ways may be listed twice there. Whether Claude Code collapses the two by name has not been measured: it needs `/context` read inside and outside this repository. To shrink the listing Claude Code carries every turn, `--print-skill-overrides=core` (or `=minimal`) prints a `skillOverrides` object that keeps the names of the skills outside that tier and drops their descriptions. It writes nothing; merging it into `~/.claude/settings.json` is your call.
- **Before copying skills, the sync checks them.** It runs `scripts/build-agent-skills.sh --check` and refuses on drift, naming the fix (`./scripts/build-agent-skills.sh`). Without `python3` it prints `skills not checked: python3 absent` and continues. `--no-skills` skips both.
- **The legacy Codex root.** The default Codex sync removes matching Fhorja skills from the legacy `~/.codex/skills/` root to prevent duplicate names. Kimi Code CLI reads `~/.agents/skills/` natively, so the same run covers it; Kimi has no slash-command directory, so there the commands arrive as skills, invoked as `/skill:<name>`.
- **To install into one specific product repo instead (or in addition)**: run `./scripts/sync-workflow-slash-commands.sh --project /path/to/your/repo`.

See [`README.md`](../README.md) -> `## Quickstart` and `## Tool support` for the full distribution story.

## Does it create a git worktree per task, or does it use one working tree at a time?

One working tree at a time, by default. `task-init` never creates a git worktree unless you ask for it; in an attended session on a git repository with a configured remote it does create a plain branch, `task/<task-dir>`, in place with `git switch -c`, and records it on a `Task branch:` line (ADR-0233). That branch is what lets the chain reach a pushed task branch and a draft PR on its own. If you want a task to run on its own worktree and branch, so a second task on the same repo does not collide with it, request isolation when you run `task-init`, or run `task-workspace` standalone on a task already in progress. That command creates one durable worktree at `../<repo-basename>-worktrees/<task-dir>` and a `task/<task-dir>` branch off your base branch, records the path in `SOURCE_OF_TRUTH.md`, and `task-close` tears it down when the task closes. Skipping it is never wrong: working one task at a time on the single default working tree is the common case. See `commands/task-workspace.md` and ADR-0074 for the full contract. (This is a different mechanism from `implement-fleet`'s per-slice worktrees, which exist only inside one task's parallel execution wave and are merged back automatically; see `WORKFLOW_DEMO.md`.)

## How do I give the AI a map of an unfamiliar codebase?

Run `code-context-map` against the target repo. By default (`digest`) it writes a ranked, gitignored Markdown map of modules, imports, and db/http/queue boundaries to `<repo>/.code-context-map/MAP.md`. For a specific area use `module:<glob>`; to trace one file's wiring use `chain:<seed-file>`, which walks the import chain by direction up to `max-hops` (or `all` for the whole reachable graph) with a cycle guard. Add the `html` flag for a self-contained interactive `MAP.html` you can open in a browser. Extraction is ripgrep by default and uses a parser only if one is already present in the repo; a ripgrep-only chain is labeled `grep-seed (non-authoritative)` so the map never overclaims. The map orients you; it is a seed for `grep`, not a replacement for reading the code (ADR-0027, ADR-0057).

## Who runs the next command, me or the session?

You decide what to work on. Once a chain starts, the session carries it.

Every command ends with a `Run now:` line naming the next one, and in an attended session the model continues into it in the same turn instead of waiting to be asked. You are not the transport. Stopping is the thing that needs a reason now. On a git repository with a configured remote, the reason has to be that the act's audience is not bounded, meaning it marks a PR ready for review, merges, publishes, or sends content outward. A decision the request did not settle, or a check the agent cannot honestly run on itself, no longer stop the run: they get recorded, labeled as the agent's, and carried into the draft PR for you to read (ADR-0233). A run that stops says why in `Reason:`. Without a remote, those two still stop and wait, as they always did. A declared `Operating mode: assisted` brings back every stop ADR-0233 removed: no task branch is created, the run asks you each product decision the request left open, stops on a check it cannot run on itself, and ends at the local commit, where the push and the draft PR are yours to start.

In practice that means a small task with a remote goes from your one-sentence brief through a local commit to a pushed task branch and a draft PR without you typing a command in between, and stops there, because marking that PR ready for review is the outward act nothing else in the chain does for you. The draft PR body opens with `Not delivered, needs you`, then the summary, then `Decisions made without you` and `Not verified`, in that order and in plain language, with no workflow ids or task paths in them.

One thing this does NOT do on its own: start. An agent handed a task in a repository that has the commands installed will usually just do the task, because nothing told it to open one. That is what the paste in [`templates/AGENT_DIRECTIVE.template.md`](../templates/AGENT_DIRECTIVE.template.md) is for, once per repository, and it is measured rather than assumed: without that paragraph the same model on the same brief edited the file and opened no task; with it, the same model ran the whole chain.

Chaining also is not uniform across models, or even across runs of one model. What the workflow guarantees is that nothing structural stops the chain and that every stop is named, not that every model always chains.

## What happens to a decision the chain made without me?

It gets recorded, not locked. A decision the request left open is chosen from the code and written as a `### P-N` under `DECISIONS.md ## Provisional decisions`, with an `Evidence:` line (a file and line on the task branch, or a quote from the request), an `Impact:` line (`high` for data, security, payments or cost, else `normal`), and `Status: provisional` (ADR-0233). Only `## Locked decisions` authorizes anything, so a P-N never counts as your input until you say so.

To confirm it, add a `### D-N` under `## Locked decisions` carrying `Confirms: P-N`. To choose something else instead, add one carrying `Supersedes: P-N`. The P-N itself is never edited or deleted.

While you have not yet confirmed or replaced a P-N, the agent can also correct its own choice: it appends a new `### P-N` carrying a `Replaces: P-M` line and the reason, and leaves P-M exactly as written (ADR-0235). A plan cites only the newest entry of that chain, and the draft PR's `Decisions made without you` section lists only the current one, so you never see a decision the agent already walked back. Merging the draft PR does not confirm a P-N on its own; it stays provisional until you confirm it as described above.

## Which GitHub account opens the draft PR?

`pr-package --apply` checks whether the `gh` account you are currently logged into can see the target repository before it opens the PR. If it can, that account pushes the branch and opens it, same as always.

If it cannot, it tries the other accounts `gh auth status` lists for that host, the remote owner's first, and uses the first one that can see the repository, for that one PR call only. It never switches your active `gh` account and never prints or stores a token. If no logged-in account can see the repository, it stops right after pushing the branch, names the missing login, and points you to `gh auth login`; the pushed branch stays either way, so nothing is lost while you fix the login.

## Why do four commands produce one Handoff block?

Because a turn reports once, not once per command.

When a chain runs several commands inside one turn, `### Artifact changes` and `### Handoff` are emitted once for the whole turn. The per-command record is not the block; it is the substrate each command writes to disk, the task files, the plan, the slice notes, the evidence. A run that emits one block per command is not wrong either, only more verbose.

So do not count blocks to check whether the chain ran. Read the task folder.

## What happens if the AI gets something wrong, and how do I undo it?

Two different safety nets, depending on when it happens. Before code is written: every command writes its task files directly, in every editor mode, and lists each one under `### Artifact changes`, so you see what changed in the turn it changed (ADR-0199). A wrong decision or plan is undone by editing the file, and every plan passes `approve-plan`'s blinded review before any code is written (ADR-0208). After code is written: attended `--apply` can create a local commit after showing the staged diff. If that commit is still unpushed, `git reset --soft HEAD^` undoes it and keeps the worktree. If the commit is already on a shared branch, `git revert <sha>` instead. On an attended run with a configured remote, `pr-package --apply` runs on its own right after the last commit and pushes the task branch and opens a draft PR (ADR-0233); without a remote, or in a declared assisted mode, the chain ends at the local commit. It never force-pushes or merges. `implement-approved-slice` edits files in your working tree the same way you would by hand. Nothing in the default task loop force-pushes, merges, or deletes branches for you. `autonomous-run`, the one command that runs with less supervision, still never auto-merges and stops at a STOP file or the runtime governor's limits; a human always performs the merge.

## How do I know a `PASS` from a runtime-verify command is real?

<!-- count:runtime-verify-commands -->4<!-- /count --> commands probe an implemented surface and report what actually happened, per platform: `godot-runtime-verify` for a Godot scene, `app-runtime-verify` for a mobile or app build (ADR-0087), `web-runtime-verify` for a web or static frontend, which serves the build on an ephemeral port and checks page identity first (ADR-0112), and `api-runtime-verify` for a backend HTTP surface, which records the real status, content-type, and body per route (ADR-0120). None of them writes or fixes code; the run's captured output is the evidence, not a claim about what should happen (ADR-0048), so an unshown pass is never a pass.

For a task with a mobile signature, `slice-closure`, the `implement-approved-slice` inline-close path, and `task-close` all ask for a real `app-runtime-verify` PASS or an explicit recorded skip reason before a runtime-observable slice closes (ADR-0106). The same floor now covers web and backend HTTP surfaces, closed after a 2026-08 dogfood run found the check named in the plan but reimplemented by hand instead of actually invoked (ADR-0127). When neither exists, the floor records a verification debt, `unverified: <reason>`, and the slice still closes; `task-close` lists every such record in its final report (ADR-0203, ADR-0209). Among the runtime floors, only the Godot feel-verdict refuses to close without evidence.

## Does it send my code anywhere?

Fhorja itself does not. It is markdown files and local shell scripts: no server, no telemetry, no analytics call, nothing phoned home. Whatever your AI coding tool already sends to its model provider when you chat with it is unchanged by installing Fhorja; the commands are prompts that tool reads, not a new data path. The one place data leaves your machine through Fhorja's own doing is a command you explicitly ran that fetches something (`capture-references` fetches URLs you gave it; `external-research` reads already captured sources and does not fetch; a connected MCP server, like Figma or Supabase, can read what you scoped it to). `mcp-server-vet` exists specifically so you can inspect a third-party MCP server's declared access before you trust it.

## Why so many commands? What is the difference between them?

The workflow has <!-- count:commands -->98<!-- /count --> commands organized in <!-- count:command-categories -->15<!-- /count --> categories, mapped to the engineering task lifecycle: project initialization, research and sourcing, discovery and scoping, design and UI, game and engine, database context, contracts and decisions, planning and validation, execution and closure, runtime verification, audit and sweep, autonomy, delivery and communication, state and navigation, and prompt tooling (ADR-0211). The per-command breakdown (every command with its description, an example, and metadata, grouped by category) lives in the generated catalog, not in this FAQ.

The parallel `*-fleet` variants and the <!-- count:personas -->9<!-- /count --> specialist persona commands round the catalog out to <!-- count:commands -->98<!-- /count -->. For the complete per-command list, see the generated catalog: open [`docs/command-catalog.html`](./command-catalog.html) (browsable, with examples and metadata) or the machine-readable [`docs/command-catalog.json`](./command-catalog.json). Both are generated from `commands/*.md` by `scripts/build-command-catalog.py`; this FAQ does not hand-maintain a command list.

Most tasks use only 4-6 of these in a typical run. The full count exists because each command captures a distinct **phase boundary** with explicit `Operating rules:` and a `### Definition of done`. Collapsing them into fewer commands would either lose the boundaries (one command does many phases poorly) or expand each command's responsibility surface (one command's `### Definition of done` becomes unreadable).

[`wos/command-roles.md`](../wos/command-roles.md) gives a one-line role for each command and a `Next:` pointer.

## Can I use this in commercial work?

Yes, without restriction. The workflow is licensed under **MIT**. You can use it in commercial work, integrate it into a closed-source product or a proprietary SaaS, fork it, and adapt it, with no share-alike obligation and no separate commercial license to buy. The only requirement is keeping the copyright and license notice in copies. There is nothing to register and no one to email for permission.

Project-level memory (`PROJECT_CHARTER.md`, `REFERENCES.md`) is gitignored by design (see ADR-0007), so commercial or sensitive project context never enters the open-source repo even when you fork.

## How does this compare to other workflow tools?

This workflow is opinionated about:

- **Phase sequencing** that starts on a short default path and adds discovery, decision, and review steps only when a named condition fires. On a git repository with a configured remote the chain runs on to a draft PR, stopping only for an act whose audience is not bounded; without a remote it keeps the older, more cautious set of stops (ADR-0184, ADR-0186, ADR-0233).
- **Reviewability** (every command lists what it wrote under `### Artifact changes`, so a change is visible the turn it happens; task memory is written directly rather than proposed, ADR-0199, and a wrong write is undone by editing the file).
- **Resumability** (every command ends with a Handoff whose `Run now:` line continues the chain; `TASK_STATE.md` is the operational memory; ADR-0186).
- **Capability routing** (commands declare LOW/MEDIUM/HIGH work complexity, ADR-0004; a `suggested-model` frontmatter hint maps it to a model in `wos/model-routing.md`, and nothing requires that model).
- **Multi-tool distribution** (canonical commands generate per-tool skills; ADR-0005).

It is **not** a replacement for: external code review systems (use Greptile, GitHub PR review, etc.); a generic agent framework (the workflow is opinionated about phases); a model orchestrator (capability routing is intentional, but the user picks the model). It is also not a CI/CD or build tool; the only "build" it does is `scripts/build-agent-skills.sh`, which generates Agent Skills from canonical commands.

### Compared to spec-kit

[spec-kit](https://github.com/github/spec-kit) is GitHub's spec-driven development toolkit, and it is strong at the start of a feature: you write a specification, and it drives the agent from that spec to a plan and then to code. Fhorja overlaps there, but its center of gravity is different. spec-kit answers "how do I get from a clean spec to working code in one focused pass." Fhorja answers "how does a task that spans several sessions and many small decisions stay coherent over days." The decisions, the task state, and the plan live in files a new session reads back, so the work survives a closed laptop, a context compaction, or a switch of editor. If your pain is getting a good spec into code, spec-kit is a fine fit. If your pain is that context and decisions evaporate between sessions, that is the gap Fhorja fills. The two are compatible: spec a feature however you like and still track it through Fhorja's task memory.

### Compared to BMAD

[BMAD-METHOD](https://github.com/bmad-code-org/BMAD-METHOD) models an agile team as a set of agent personas (analyst, PM, architect, scrum master, developer, QA) that hand work to each other. It is a rich planning-and-simulation approach, and if you want an AI "team" to role-play the software lifecycle, it does that well. Fhorja does not simulate roles. It keeps one disciplined lifecycle, a merge gate that always stays human, and leans hard on evidence: a step counts as done only when the real command output proves it, and every decision is written once, whether locked by you or provisional and chosen by the agent, with its reasoning and read back later. Where BMAD invests in richer up-front planning personas, Fhorja invests in persistent state and proof of execution. Neither is a knock on the other; they optimize for different things.

### Compared to beads

[beads](https://github.com/gastownhall/beads) gives a coding agent a real task database: a dependency-aware graph stored in a version-controlled SQL engine, with hash-based issue IDs, a ready-work query that returns only unblocked items, and sync across machines. On the narrow question of holding task state while several agents write at once, beads is the stronger artifact, and it is worth saying so plainly rather than burying it. Its default embedded mode is single-writer, same as Fhorja, but it also ships a server mode built for multiple concurrent writers, plus a real cross-machine sync path, and it claims its hash-based IDs remove merge collisions across agents and branches. Fhorja has markdown files, a single-writer convention, no server mode, and no sync path. That is a deliberate trade for tool portability and human-diffable history rather than an oversight, but it is still the weaker answer to that particular question. Fhorja is answering a different one: how a piece of work gets framed, decided, sliced, verified, and closed, with explicit human gates where an agent should not proceed alone, and with the reasoning behind each decision written once and read back later. The two sit at different altitudes and compose rather than compete; tracking work in beads and still running it through Fhorja's phases is not a contradiction.

If you are evaluating against another workflow tool, the differentiators are: discipline over freedom, audit trail in persisted task artifacts and the verification log, multi-tool drop-in via the open Agent Skills standard, and the ADR-driven design so tradeoffs are visible.

## What about my private projects?

`projects/<client>__<project>/` stays out of git wherever it lives. In a clone of this repository the root `.gitignore` lists `projects/`. In your product repository, where an installed `task-init` creates the tree, the command that creates `projects/` writes a `projects/.gitignore` holding `*` (ADR-0223); it does not edit your own `.gitignore`. If `projects/` was already there and git would track it, `task-init` says so on every run and names the fix. Anything you store there (`PROJECT_CHARTER.md`, `REFERENCES.md`, task folders, `DB_CONTEXT.md`, etc.) stays local. Forking this repo and running tasks against your own clients does not leak project context upstream.

If you want to share project context across machines, copy `projects/<client>__<project>/` separately (a private repo, dotfile sync, rsync). The workflow does not currently provide a sync path for project memory; it is intentionally local.

## What if two people use it on the same repo?

`projects/<client>__<project>/` is ignored by git in the product repo too, through the `projects/.gitignore` described above, so it is local to each person's machine, not shared through the product repo. Two teammates working on the same codebase each keep their own task folders, their own `TASK_STATE.md`, their own decisions; Fhorja does not sync or merge task memory between them. What is shared is the product repo itself and ordinary git: two people implementing different tasks still need the usual coordination (separate branches, normal PR review) that any team already does without Fhorja. If you want isolation while both of you are mid-task, `task-workspace` gives each task its own git worktree and branch so your working trees do not collide. There is currently no shared or synced view of two people's task memory; keep that in mind before relying on `projects/` as a team-visible record. A team that wants the tree in git deletes `projects/.gitignore` and commits it; Fhorja still does nothing to merge two people's edits to the same task.

## Where do I report issues / contribute?

- **Bug reports**: open an issue using the [bug report template](../.github/ISSUE_TEMPLATE/bug_report.md).
- **Feature requests**: open an issue using the [feature request template](../.github/ISSUE_TEMPLATE/feature_request.md).
- **Pull requests**: see [`CONTRIBUTING.md`](../CONTRIBUTING.md) for the contribution flow, the DCO sign-off (`git commit -s`; there is no CLA), and the style guide.
- **Security**: see [`SECURITY.md`](../SECURITY.md) for the reporting flow.
- **Code of conduct**: see [`CODE_OF_CONDUCT.md`](../CODE_OF_CONDUCT.md) (Contributor Covenant 2.1).
- **Roadmap and direction**: see [`ROADMAP.md`](../ROADMAP.md) for forward-looking plans.

The maintainer makes final decisions on roadmap priorities (BDFL governance). There is no SLA on changes or fulfillment of feature requests.

## Why is the spec called "WORKFLOW_OPERATING_SYSTEM"?

The metaphor is deliberate. An operating system multiplexes resources (CPU, memory, IO) across many processes; the workflow operating system multiplexes a developer's attention across many phases and tasks. The OS gives processes a stable contract (system calls, memory model); Fhorja gives commands a stable contract (mandatory context bootstrap, output layout, Handoff format).

The metaphor breaks down at scale (an OS isolates processes; Fhorja does not isolate tasks from each other by default). Isolation is opt-in: `task-workspace` gives a task its own git worktree and branch, and `implement-fleet` uses per-slice worktrees. It is a teaching label, not a strict architectural claim.

## What is the context engineering framework? (ADRs 0012-0020)

The workflow treats context as six layers (`system`, `memory`, `retrieved`, `tools`, `history`, `task`), and every `commands/<name>.md` declares which layers it consumes and produces (ADR-0012). Memory stacks task, then project, then user, and the more specific layer wins (ADR-0007, ADR-0016). Several mechanisms from that May 2026 design round have since been retired or replaced, so start at ADR-0012 and read each later ADR's Status line for what still applies.

## How do I keep TASK_STATE fresh across sessions, and lint task memory?

Two opt-in helpers, both shipped as advisory tooling Fhorja provides but does not force on you.

**Session-continuity hook (ADR-0052).** `scripts/session-continuity-hook.sh` is a Claude Code SessionStart and Stop hook you wire in the consuming repo's `.claude/settings.json` (the same way `scripts/typecheck-hook.sh` is wired; a copy-paste snippet lives in `templates/session-continuity-hook.template.md`). On session start it surfaces the active task's Resume notes and Recommended next step. On session stop it writes a bounded `.wos/SESSION_CONTINUITY.json` marker and, the next time you start, nudges you to run `sync-task-state` if `TASK_STATE.md` has not changed since. It is non-blocking and sidecar-only: it never rewrites the authored sections of `TASK_STATE.md`, and the real model-driven sync still happens when you run `sync-task-state`.

**memory-lint mode (ADR-0053).** `state-reconcile` has a read-only `memory-lint` mode (backed by `scripts/memory-lint.sh`) that reports memory hygiene issues: dead relative cross-links across task and project memory, orphaned `SLICES/` files, and stale `TASK_STATE.md` facts. It writes nothing; it only surfaces what to clean up, so you can run it any time without changing state.

Both came out of the 2026-06-25 analysis of the external claude-obsidian project, which absorbed its session hot-cache and vault-lint ideas while declining its heavier retrieval pipeline.

## What is the per-project knowledge layer, and how do I bring a past learning back?

Two different mechanisms answer that second question, and they are not the same layer.
`LEARNINGS.md` is the task-scoped one: every `task-init` reads it automatically, ranked by
`rank-learnings.sh` (ADR-0017, ADR-0071), and since ADR-0234 `task-close` writes it automatically
too, appending entries when the task recorded a signal (a review that asked for a revision, a
check shown failing before it passed, a fixed review finding, a refusal, a revert, a de-scope, or
an unverified line). You do nothing for that path to work; a task that struggled hands its lessons
to the next one on its own. The knowledge layer below is the other, separate mechanism: a
human-only, cross-task record nothing reads for you.

The knowledge layer (ADR-0054, ADR-0055) is a human-first record of how a project evolved, organized as a navigable, Obsidian-compatible set of linked notes. It lives in `projects/<client>__<project>/knowledge/`: one note per closed task (`<task-slug>.md`) plus an `index.md` (the map of content). Plain Markdown, gitignored (per-user, like the rest of `projects/`). Notes carry Obsidian-flavored `[[wikilinks]]` to the task, its decisions, and topics. `task-close` writes here; nothing else does.

The point of difference from task memory: the AI never reads the `knowledge/` folder automatically. It is written for you, the human. This is deliberate. An AI that silently carries every past learning into every new task is the scope-creep failure mode the layer exists to avoid. To bring a past learning into a new task, you read the relevant note yourself and paste the excerpt into your `task-init` prompt. That keeps each task focused on exactly the prior context you chose, and leaves an auditable trail of what informed it.

When you close a task, `task-close` writes the safe links itself (to the task, the index, and the decisions) and proposes topic links and tags for you to confirm or edit; it never inserts unverified links silently. For a visual view, run `python3 scripts/build-knowledge-view.py projects/<client>__<project>/` to generate an offline, navigable `knowledge/KNOWLEDGE.html` where the wikilinks jump in-page, and `python3 scripts/build-activity-timeline.py projects/<client>__<project>/ --project` for the chronological `ACTIVITY.html` timeline. Because the notes are plain Markdown with wikilinks, opening the `projects/` folder in Obsidian gives you the graph and Canvas for free; Fhorja does not depend on Obsidian or any app.

## Where do the ADRs live?

[`docs/adr/`](./adr/). The [README](./adr/README.md) there has the full index and explains how to add new ADRs.



## When should I use parallel workflow dispatch vs sequential commands?

There are two parallel paths, and they are not the same mechanism.

**Approved slice execution.** Use `implement-fleet` when the approved plan's `## Execution waves` show a remaining wave of size 2 or more whose slices declare `Scope` and `Depends-on`. Each fleet command has its own `max_fanout` (8 for `implement-fleet`) under a platform ceiling of 20. Workers return through the carrier the orchestrator named before dispatch: the runtime's typed result on the dynamic-workflow path, or `fleet-inbox/<run_id>/<worker_id>.json` on the `Agent` path. Claude Code is the host that can run concurrent workers; single-thread tools (Cursor, Codex CLI) fall back to sequential `implement-approved-slice`.

**Read-only Workflow research batches.** Use parallel dispatch only when the units of work are genuinely independent: they read disjoint inputs, write to disjoint substrate paths (substrate here means the task-memory files each command reads and writes, like TASK_STATE.md or IMPLEMENTATION_PLAN.md), and do not depend on each other's outputs. The empirical batch size for that research path is 15 to 25 workers per dispatch wave per ADR-0039 (`docs/adr/0039-workflow-batch-dispatch-empirical.md`); above that, scheduler contention and substrate-write interleaving start to dominate. This path also currently requires Claude Code as the host. If you cannot prove independence in under a minute of inspection, run sequentially: the cost of one wasted serial pass is far smaller than one corrupted substrate write.

## What goes wrong in a parallel batch, and how do I check?

Two failures matter: a worker that answers in prose instead of the typed payload (schema-skip), and two workers racing on one section (a substrate orphan). Both, with the check to run after a batch, are in `wos/workflow-patterns.md` under `## Parallel dispatch failures: schema-skip and substrate orphans`.

## Does using Fhorja cost more than prompting the AI directly?

Fhorja has no cost of its own (no subscription, no API key, no hosted service); you pay only for the AI coding tool and model you already use. It does use more of that tool's usage than a single freeform prompt. The figures below are from repository scripts and dated snapshots, using the chars/4 approximation (about 10% precision against the real tokenizer). They are not live API measurements.

- **Per command**, the static context a command loads is the four always-read spec sections, about 11,678 tokens (the full bootstrap; `commands/_shared/mandatory-context-bootstrap.md` declares the measured figure and a structural eval checks it). With prompt caching, which Claude Code turns on by default, that block is written once and then read at about a tenth of the cost on every command after, so you pay the full amount roughly once per session, not once per command. Command files themselves add roughly 3,000 to 9,600 tokens each (run `python3 scripts/measure-tokens.py --per-command` for the current figures, chars/4 on `commands/*.md`).
- **A multi-command task** is a simulation, not a measured run. The checked-in snapshot `scripts/baseline-task-cost-2026-05-18.md` (from `python3 scripts/measure-task-cost.py`) models <!-- count:task-cost-phases -->9<!-- /count --> phases at 68,560 cached token-equivalents versus 206,888 uncached. A task with no escalations is lighter, because it skips the discovery commands.
- **The task's memory on disk** (`TASK_STATE.md`) is the resumable state of a task: what is done, every decision, and the next step. Size varies by task; this FAQ does not keep a corpus average.

In exchange you get plan review before code is written and resumable state across sessions, which saves the tokens a freeform chat burns re-explaining context after a compaction or a new session. If you are on a metered budget, pass `--profile minimal` so both command files and skills stay on the <!-- count:commands-minimal -->23<!-- /count -->-command profile, and skip specialist personas and fleet commands until a task actually needs them.

## How many MCP servers should I connect, and what does each cost?

Connect only the servers a real workflow needs. Each connected MCP server injects its tool schema into every request, so an overloaded server list quietly eats the budget Fhorja spends on task memory. Schema cost varies with the exposed tool set; this repository does not keep a per-server token range. Fhorja itself stays MCP-agnostic: no command requires a specific server, and `mcp-server-vet` (ADR-0070) gives you a read-only pre-trust inspection of any third-party server before you add it to a config.
