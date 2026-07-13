# FAQ

Common questions about Fhorja, a workflow operating system. If your question is not here, check [`README.md`](../README.md) for the user-facing entry point or [`WORKFLOW_OPERATING_SYSTEM.md`](../WORKFLOW_OPERATING_SYSTEM.md) for the normative spec.

## What is this repo?

A **markdown plus bash specification** of an AI-assisted engineering workflow for solo and small-team developers. The deliverables are documents (the workflow operating system spec, command files, templates) and small scripts (lint, sync, build adapters). There is no application runtime, no server, no persistence, no hosted service.

The workflow's job is to make AI-assisted engineering **resumable, auditable, and disciplined**: every step produces grounded artifacts, every command ends with a runnable next step, every plan is reviewable before it is applied.

## Why markdown plus bash, not a runtime tool?

Three reasons:

1. **Tool portability**. Markdown and bash run anywhere. The workflow targets Cursor, Claude Code, GitHub Copilot, OpenAI Codex, Gemini CLI, OpenHands, Goose, Junie, and 35+ others without per-tool integration. A runtime would need plugins per tool.
2. **Open-source-friendly distribution**. Static markdown is trivially open-source-compatible. The repo can be cloned, forked, and adapted with no installation step.
3. **Explicit over magical**. The workflow's value is its discipline (mandatory phases, review gates, copy-paste handoffs). Wrapping that discipline in code would hide it; markdown surfaces it where contributors can audit and refine it.

A future hosted SaaS layer (exploratory, not committed) might wrap the workflow with server-side execution, sandboxing, and persistence. That is a separate product, not a replacement for the markdown layer.

## Does this work offline?

Cloning the repo and reading task memory needs no network access at all; the markdown files and scripts are entirely local. Running a command does need whatever your AI coding tool needs (most require a live connection to their model provider), so Fhorja is only as offline-capable as the underlying tool. A few individual commands additionally reach out on their own: `capture-references` and `external-research` fetch URLs, and any MCP-backed command (Figma, Supabase, database context) needs its server reachable. Every other command works against local files only.

## Which AI tools work with this?

Any tool that reads `.claude/skills/<name>/SKILL.md` natively works as a drop-in. As of mid-2026 that includes (but is not limited to) Cursor 2.4+, Claude Code, GitHub Copilot, OpenAI Codex, Gemini CLI, OpenHands, Goose, Junie, Roo Code, Mistral Vibe, Snowflake Cortex, Databricks Genie. The skills are generated from `commands/*.md` by `scripts/build-agent-skills.sh` and committed to the repo, so cloning is sufficient.

For tools that only read legacy `.claude/commands/` or `.cursor/commands/`, the same `commands/*.md` files are mirrored to those directories by `scripts/sync-workflow-slash-commands.sh`.

For tools without either pattern, the canonical command files are still readable as plain markdown; users can `@`-mention them or paste their content into the tool.

## How do I install it?

```bash
git clone https://github.com/Mozurok/fhorja.dev.git
cd fhorja.dev
```

That is the install, and you do it once, in its own directory, not once per product project. This repo never becomes your working directory while you code; your product repo stays separate and keeps its own git history. To use it:

- **In an editor that reads `.claude/skills/`** (Cursor 2.4+, Claude Code, etc.), the fastest path is `--with-skills` below: it mirrors the commands to your user-level directories once, so any product repo you open in that editor picks them up automatically, no per-project step.
- **For user-level slash commands in Cursor and Claude Code**: run `./scripts/sync-workflow-slash-commands.sh`. Defaults: `~/.cursor/commands/`, `~/.claude/commands/`. Override paths with `--cursor-dir=` and `--claude-dir=` or via env vars.
- **For user-level skills mirroring** (so skills are available in every project you open, not just this one): run `./scripts/sync-workflow-slash-commands.sh --with-skills`. Defaults: `~/.claude/skills/`, `~/.cursor/skills/`, `~/.codex/skills/`.
- **To install into one specific product repo instead (or in addition)**: run `./scripts/sync-workflow-slash-commands.sh --project /path/to/your/repo`.

See [`README.md`](../README.md) -> `## Quickstart` and `## Tool support` for the full distribution story.

## Does it create a git worktree per task, or does it use one working tree at a time?

One working tree at a time, by default. `task-init` never creates a git worktree unless you ask for it. If you want a task to run on its own worktree and branch, so a second task on the same repo does not collide with it, request isolation when you run `task-init`, or run `task-workspace` standalone on a task already in progress. That command creates one durable worktree at `../<repo-basename>-worktrees/<task-dir>` and a `task/<task-dir>` branch off your base branch, records the path in `SOURCE_OF_TRUTH.md`, and `task-close` tears it down when the task closes. Skipping it is never wrong: working one task at a time on the single default working tree is the common case. See `commands/task-workspace.md` and ADR-0074 for the full contract. (This is a different mechanism from `implement-fleet`'s per-slice worktrees, which exist only inside one task's parallel execution wave and are merged back automatically; see `WORKFLOW_DEMO.md`.)

## How do I give the AI a map of an unfamiliar codebase?

Run `code-context-map` against the target repo. By default (`digest`) it writes a ranked, gitignored Markdown map of modules, imports, and db/http/queue boundaries to `<repo>/.code-context-map/MAP.md`. For a specific area use `module:<glob>`; to trace one file's wiring use `chain:<seed-file>`, which walks the import chain by direction up to `max-hops` (or `all` for the whole reachable graph) with a cycle guard. Add the `html` flag for a self-contained interactive `MAP.html` you can open in a browser. Extraction is ripgrep by default and uses a parser only if one is already present in the repo; a ripgrep-only chain is labeled `grep-seed (non-authoritative)` so the map never overclaims. The map orients you; it is a seed for `grep`, not a replacement for reading the code (ADR-0027, ADR-0057).

## Why are commands user-invoked instead of model-invoked?

The workflow is a **deliberate, phase-aware** discipline. Commands like `task-init`, `implementation-plan`, `pr-package` are meant to be invoked when the user has decided that phase is the right next step. Auto-invoking them based on description matching could short-circuit the user's review of whether the phase is actually right.

The Agent Skills standard supports a `disable-model-invocation` flag for exactly this case, but it is a Claude-Code-specific extension and not part of the open spec. The repo does not declare that flag (so the skills pass open-spec validation), but the per-command friction (each command requires explicit inputs and emits a copy-paste Handoff) means accidental auto-invocation has limited blast radius. ADR-0002 documents the Handoff contract that absorbs the risk.

## What happens if the AI gets something wrong, and how do I undo it?

Two different safety nets, depending on when it happens. Before code is written: everything is `PROPOSED` by default (ADR-0001). You see the full content of a plan, a decision, or a file inline before anything is written to disk; a wrong proposal is discarded by not approving it. After code is written: Fhorja never commits or pushes on your behalf. `implement-approved-slice` edits files in your working tree the same way you would by hand, so normal git is your undo button: `git diff` to see what changed, `git checkout -- <file>` or `git restore <file>` to discard one file, `git reset` for the whole working tree. Nothing in the default task loop force-pushes, merges, or deletes branches for you. `autonomous-run`, the one command that runs with less supervision, still never auto-merges and stops at a STOP file or the runtime governor's limits; a human always performs the merge.

## Does it send my code anywhere?

Fhorja itself does not. It is markdown files and local shell scripts: no server, no telemetry, no analytics call, nothing phoned home. Whatever your AI coding tool already sends to its model provider when you chat with it is unchanged by installing Fhorja; the commands are prompts that tool reads, not a new data path. The one place data leaves your machine through Fhorja's own doing is a command you explicitly ran that fetches something (`capture-references` and `external-research` fetch URLs you gave them; a connected MCP server, like Figma or Supabase, can read what you scoped it to). `mcp-server-vet` exists specifically so you can inspect a third-party MCP server's declared access before you trust it.

## Why so many commands? What is the difference between them?

The workflow has <!-- count:commands -->94<!-- /count --> commands organized in <!-- count:command-categories -->9<!-- /count --> categories, mapped to the engineering task lifecycle:

The categories span the engineering task lifecycle: project initialization, state and navigation, discovery and scoping, database context, contract and decision hardening, planning and validation, execution and closure, delivery and communication, and prompt tooling. The per-command breakdown (every command with its description, an example, and metadata, grouped by category) lives in the generated catalog, not in this FAQ.

The parallel `*-fleet` variants and the nine specialist persona commands round the catalog out to <!-- count:commands -->94<!-- /count -->. For the complete per-command list, see the generated catalog: open [`docs/command-catalog.html`](./command-catalog.html) (browsable, with examples and metadata) or the [README command catalog](../README.md#command-catalog). Both are generated from `commands/*.md` by `scripts/build-command-catalog.py`; this FAQ does not hand-maintain a command list.

Most tasks use only 4-6 of these in a typical run. The full count exists because each command captures a distinct **phase boundary** with explicit `Operating rules:` and a `### Definition of done`. Collapsing them into fewer commands would either lose the boundaries (one command does many phases poorly) or expand each command's responsibility surface (one command's `### Definition of done` becomes unreadable).

The `## Command roles` index gives a one-line role for each command and a `Next:` pointer.

## Can I use this in commercial work?

Yes, without restriction. The workflow is licensed under **MIT**. You can use it in commercial work, integrate it into a closed-source product or a proprietary SaaS, fork it, and adapt it, with no share-alike obligation and no separate commercial license to buy. The only requirement is keeping the copyright and license notice in copies. There is nothing to register and no one to email for permission.

Project-level memory (`PROJECT_CHARTER.md`, `REFERENCES.md`) is gitignored by design (see ADR-0007), so commercial or sensitive project context never enters the open-source repo even when you fork.

## How does this compare to other workflow tools?

This workflow is opinionated about:

- **Phase sequencing** (discovery -> contract -> planning -> execution -> review -> delivery, with explicit gates).
- **Reviewability** (PROPOSED-by-default writes; full artifact content emitted inline before any disk write; ADR-0001).
- **Resumability** (every command ends with a runnable Handoff; `TASK_STATE.md` is the operational memory; ADR-0002).
- **Capability routing without model SKUs** (LOW/MEDIUM/HIGH; ADR-0004).
- **Multi-tool distribution** (canonical commands generate per-tool skills; ADR-0005).

It is **not** a replacement for: external code review systems (use Greptile, GitHub PR review, etc.); a generic agent framework (the workflow is opinionated about phases); a model orchestrator (capability routing is intentional, but the user picks the model). It is also not a CI/CD or build tool; the only "build" it does is `scripts/build-agent-skills.sh`, which generates Agent Skills from canonical commands.

### Compared to spec-kit

[spec-kit](https://github.com/github/spec-kit) is GitHub's spec-driven development toolkit, and it is strong at the start of a feature: you write a specification, and it drives the agent from that spec to a plan and then to code. Fhorja overlaps there, but its center of gravity is different. spec-kit answers "how do I get from a clean spec to working code in one focused pass." Fhorja answers "how does a task that spans several sessions and many small decisions stay coherent over days." The decisions, the task state, and the plan live in files a new session reads back, so the work survives a closed laptop, a context compaction, or a switch of editor. If your pain is getting a good spec into code, spec-kit is a fine fit. If your pain is that context and decisions evaporate between sessions, that is the gap Fhorja fills. The two are compatible: spec a feature however you like and still track it through Fhorja's task memory.

### Compared to BMAD

[BMAD-METHOD](https://github.com/bmad-code-org/BMAD-METHOD) models an agile team as a set of agent personas (analyst, PM, architect, scrum master, developer, QA) that hand work to each other. It is a rich planning-and-simulation approach, and if you want an AI "team" to role-play the software lifecycle, it does that well. Fhorja does not simulate roles. It keeps one disciplined lifecycle with explicit human gates and leans hard on evidence: a step counts as done only when the real command output proves it, and every decision is written once with its reasoning and read back later. Where BMAD invests in richer up-front planning personas, Fhorja invests in persistent state and proof of execution. Neither is a knock on the other; they optimize for different things.

If you are evaluating against another workflow tool, the differentiators are: discipline over freedom, audit trail in conversation transcripts, multi-tool drop-in via the open Agent Skills standard, and the ADR-driven design so tradeoffs are visible.

## What about my private projects?

`projects/<client>__<project>/` is gitignored. Anything you store there (`PROJECT_CHARTER.md`, `REFERENCES.md`, task folders, `DB_CONTEXT.md`, etc.) stays local. Forking this repo and running tasks against your own clients does not leak project context upstream.

If you want to share project context across machines, copy `projects/<client>__<project>/` separately (a private repo, dotfile sync, rsync). The workflow does not currently provide a sync path for project memory; it is intentionally local.

## What if two people use it on the same repo?

`projects/<client>__<project>/` is gitignored, so it is local to each person's machine, not shared through the product repo. Two teammates working on the same codebase each keep their own task folders, their own `TASK_STATE.md`, their own decisions; Fhorja does not sync or merge task memory between them. What is shared is the product repo itself and ordinary git: two people implementing different tasks still need the usual coordination (separate branches, normal PR review) that any team already does without Fhorja. If you want isolation while both of you are mid-task, `task-workspace` gives each task its own git worktree and branch so your working trees do not collide. There is currently no shared or synced view of two people's task memory; keep that in mind before relying on `projects/` as a team-visible record.

## Where do I report issues / contribute?

- **Bug reports**: open an issue using the [bug report template](../.github/ISSUE_TEMPLATE/bug_report.md).
- **Feature requests**: open an issue using the [feature request template](../.github/ISSUE_TEMPLATE/feature_request.md).
- **Pull requests**: see [`CONTRIBUTING.md`](../CONTRIBUTING.md) for the contribution flow, CLA requirements, and style guide.
- **Security**: see [`SECURITY.md`](../SECURITY.md) for the reporting flow.
- **Code of conduct**: see [`CODE_OF_CONDUCT.md`](../CODE_OF_CONDUCT.md) (Contributor Covenant 2.1).
- **Roadmap and direction**: see [`ROADMAP.md`](../ROADMAP.md) for forward-looking plans.

The maintainer makes final decisions on roadmap priorities (BDFL governance). There is no SLA on changes or fulfillment of feature requests.

## Why is the spec called "WORKFLOW_OPERATING_SYSTEM"?

The metaphor is deliberate. An operating system multiplexes resources (CPU, memory, IO) across many processes; the workflow operating system multiplexes a developer's attention across many phases and tasks. The OS gives processes a stable contract (system calls, memory model); Fhorja gives commands a stable contract (mandatory context bootstrap, output layout, Handoff format).

The metaphor breaks down at scale (an OS isolates processes; Fhorja does not isolate tasks from each other). It is a teaching label, not a strict architectural claim.

## What is the context engineering framework? (ADRs 0012-0020)

The workflow adopts an explicit six-layer context model (`system`, `memory`, `retrieved`, `tools`, `history`, `task`) as a falsifiable contract. Every `commands/<name>.md` declares `metadata.context-layers-consumed` and `metadata.context-layers-produced` (ADR-0012), plus a `metadata.token-budget` (ADR-0013) and a `<!-- cache-breakpoint -->` marker (ADR-0014). Three composable layers extend the basic context model:

- **Memory pyramid** (task -> project -> user; specific overrides general): TASK_STATE.md and DECISIONS.md at the task layer; PROJECT_CHARTER.md and REFERENCES.md at the project layer (ADR-0007); USER_MEMORY.md at the user layer (ADR-0016; gitignored; bootstrap from `templates/USER_MEMORY.template.md`).
- **Working-memory compaction** (ADR-0015): `compact-task-memory` is a new command that produces a lossy summary of long TASK_STATE.md while preserving canonical decisions and the recommended next step verbatim; audit trail in a `## Compaction history` section.
- **Reflexion-style learnings** (ADR-0017): closed slices, post-review pivots, and HOTFIX incidents can optionally emit a 4-bullet `### Learnings` entry that lands in a task-scoped `LEARNINGS.md` (bootstrap from `templates/LEARNINGS.md`). Manual promotion path to user-level cross-project learnings.

Three additional ADRs extend retrieval (ADR-0018: `Context within project` field in every captured REFERENCES.md entry; reinforcing / contradicting / different-framing distinction in external-research synthesis), evaluation (ADR-0019: optional LLM-as-judge layer via `evals/scripts/judge.py`), and observability (ADR-0020: simulated end-to-end task cost via `scripts/measure-task-cost.py`).

The framework was introduced in the 2026-05-15 context-engineering uplift task (slices 01-09 of 13). All ADRs are independent enough to read separately; ADR-0012 is the entry point for the layer model itself.

## How do I keep TASK_STATE fresh across sessions, and lint task memory?

Two opt-in helpers, both shipped as advisory tooling Fhorja provides but does not force on you.

**Session-continuity hook (ADR-0052).** `scripts/session-continuity-hook.sh` is a Claude Code SessionStart and SessionStop hook you wire in the consuming repo's `.claude/settings.json` (the same way `scripts/typecheck-hook.sh` is wired; a copy-paste snippet lives in `templates/session-continuity-hook.template.md`). On session start it surfaces the active task's Resume notes and Recommended next step. On session stop it writes a bounded `.wos/SESSION_CONTINUITY.json` marker and, the next time you start, nudges you to run `sync-task-state` if `TASK_STATE.md` has not changed since. It is non-blocking and sidecar-only: it never rewrites the authored sections of `TASK_STATE.md`, and the real model-driven sync still happens when you run `sync-task-state`.

**memory-lint mode (ADR-0053).** `state-reconcile` has a read-only `memory-lint` mode (backed by `scripts/memory-lint.sh`) that reports memory hygiene issues: dead relative cross-links across task and project memory, orphaned `SLICES/` files, and stale `TASK_STATE.md` facts. It writes nothing; it only surfaces what to clean up, so you can run it any time without changing state.

Both came out of the 2026-06-25 analysis of the external claude-obsidian project, which absorbed its session hot-cache and vault-lint ideas while declining its heavier retrieval pipeline.

## What is the per-project knowledge layer, and how do I bring a past learning back?

The knowledge layer (ADR-0054, ADR-0055) is a human-first record of how a project evolved, organized as a navigable, Obsidian-compatible set of linked notes. It lives in `projects/<client>__<project>/knowledge/`: one note per closed task (`<task-slug>.md`) plus an `index.md` (the map of content). Plain Markdown, gitignored (per-user, like the rest of `projects/`). Notes carry Obsidian-flavored `[[wikilinks]]` to the task, its decisions, and topics. `task-close` writes here; nothing else does.

The point of difference from task memory: the AI never reads the `knowledge/` folder automatically. It is written for you, the human. This is deliberate. An AI that silently carries every past learning into every new task is the scope-creep failure mode the layer exists to avoid. To bring a past learning into a new task, you read the relevant note yourself and paste the excerpt into your `task-init` prompt. That keeps each task focused on exactly the prior context you chose, and leaves an auditable trail of what informed it.

When you close a task, `task-close` writes the safe links itself (to the task, the index, and the decisions) and proposes topic links and tags for you to confirm or edit; it never inserts unverified links silently. For a visual view, run `python3 scripts/build-knowledge-view.py projects/<client>__<project>/` to generate an offline, navigable `knowledge/KNOWLEDGE.html` where the wikilinks jump in-page, and `python3 scripts/build-activity-timeline.py projects/<client>__<project>/ --project` for the chronological `ACTIVITY.html` timeline. Because the notes are plain Markdown with wikilinks, opening the `projects/` folder in Obsidian gives you the graph and Canvas for free; Fhorja does not depend on Obsidian or any app.

## Where do the ADRs live?

[`docs/adr/`](./adr/). The [README](./adr/README.md) there has the full index and explains how to add new ADRs.



## When should I use parallel workflow dispatch vs sequential commands?

Use parallel dispatch only when the units of work are genuinely independent: they read disjoint inputs, write to disjoint substrate paths (substrate here means the task-memory files each command reads and writes, like TASK_STATE.md or IMPLEMENTATION_PLAN.md), and do not depend on each other's outputs. The default batch size is 15-25 workers per dispatch wave per ADR-0039 (`docs/adr/0039-workflow-batch-dispatch-empirical.md`); above that, scheduler contention and substrate-write interleaving start to dominate. Parallel dispatch currently requires Claude Code as the host, because the harness must support multiple concurrent subagent threads with isolated tool budgets -- single-thread tools (Cursor, Codex CLI) fall back to sequential. If you cannot prove independence in under a minute of inspection, run sequentially: the cost of one wasted serial pass is far smaller than one corrupted substrate write.

## What is the schema-skip failure mode and how do I avoid it?

Schema-skip is when a dispatched subagent finishes its work but returns prose instead of calling `StructuredOutput`, so the orchestrator gets no parseable artifact. The mitigation is the canonical worker contract in `commands/_shared/worker-contract.md` (ADR-0038 Rule 1), which requires every dispatched worker to return its result by invoking the `StructuredOutput` tool exactly once and names the `{artifact, mode, content}` shape; the `templates/ORCHESTRATOR_COMMAND.template.md` reinforces it on the dispatch side. Since adopting this contract in June 2026, observed skip rate is 0% across 47 sampled workers (previously 8-12%). If you write a custom dispatch prompt, copy the explicit StructuredOutput reminder verbatim; paraphrasing it has historically degraded compliance.

## How do I verify that my parallel batch didn't drop or corrupt substrate writes?

ADR-0040 (`docs/adr/0040-single-writer-per-folder-exception.md`) requires every parallel batch to honor single-writer-per-folder discipline; run `python3 scripts/scan-substrate-orphans.py --since <batch-start-timestamp>` after the batch settles to catch substrate-bullet-orphan instances (`wos/bug-classes/substrate-bullet-orphan.md`). The failure mode it catches is the `substrate-bullet-orphan` bug-class, where two workers race on the same parent and one bullet ends up dangling. If the scan reports any orphans, do not advance phases: re-dispatch the affected workers individually with the orphan IDs passed as input, and re-run the scan until it returns clean.

## Does using Fhorja cost more than prompting the AI directly?

Fhorja has no cost of its own (no subscription, no API key, no hosted service); you pay only for the AI coding tool and model you already use. It does use more of that tool's usage than a single freeform prompt, and here are measured numbers so you can judge for yourself (approximate, from `scripts/measure-tokens.py`, roughly 10% precision against the real tokenizer):

- **Per command**, the static context a command loads (the spec sections it needs plus its shared blocks) is about 41,000 tokens. With prompt caching, which Claude Code turns on by default, that block is written once and then read at about a tenth of the cost on every command after, so you pay the full amount roughly once per session, not once per command. The command file itself adds 2,000 to 7,400 tokens.
- **A real multi-command task** (the five-command flow from `task-init` through `pr-package`) costs about 102,000 token-equivalents with caching on, against about 238,000 if you open a fresh chat per command and lose the cache. Caching is worth roughly 57% here. An Express task is lighter still, because it skips the discovery commands.
- **The task's memory on disk** (`TASK_STATE.md`) averages about 11 KB, roughly 2,700 tokens, measured across 314 real task files (range 0.5 KB to 43 KB). That one file is the entire resumable state of a task: what is done, every decision, and the next step.

In exchange you get plan review before code is written and resumable state across sessions, which saves the tokens a freeform chat burns re-explaining context after a compaction or a new session. If you are on a metered budget, the `minimal` install profile (the twelve-command everyday loop) is now the default, so you skip specialist personas and fleet commands until a task actually needs them.

## How many MCP servers should I connect, and what does each cost?

Start with three and add more only when a real workflow needs it. Each connected MCP server injects its tool schema into every request, which costs roughly 2,000 to 5,000 tokens of context per server before you do any work, so an overloaded server list quietly eats the budget Fhorja spends on task memory. The community sweet spot is three to five servers. Fhorja itself stays MCP-agnostic: no command requires a specific server, and `mcp-server-vet` (ADR-0070) gives you a read-only pre-trust inspection of any third-party server before you add it to a config.
