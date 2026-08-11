# ADR-0129: Operating from an installed tree (the spec is runtime payload, and the task repo is not the workflow root)

- **Status**: Accepted
- **Date**: 2026-08-06
- **Tags**: distribution, runtime-payload, sync-workflow-slash-commands, task-init, preflight, multi-tool, dogfood-driven, kimi-dogfood

## Context

Fhorja is developed in a checkout where `commands/`, `scripts/`, `wos/` and `projects/` all sit at one root. It is used from an installed tree where they do not: the skills land in the agent's skills directory, the reference docs land in a per-tool `workflow-docs/`, and the user's tasks live under a `projects/` tree inside whatever repository they are working in. Two rules were written against the development layout and fail against the installed one. A cross-model dogfood run (Kimi K3, 2026-08-06) hit both.

**The spec does not reach two of its four declared destinations.** `sync_runtime_payload` copies `wos/` to all four tool destinations on every sync, deliberately outside the `--with-docs` gate. The script's own comment states why: every command file cites at least one `wos/<topic>.md`, several of those loads are declared mandatory, and a session bootstrapping from an installed copy was resolving them against nothing. The comment is correct and the same argument applies, unchanged, to `WORKFLOW_OPERATING_SYSTEM.md`: the first item of every command's mandatory context bootstrap is four named sections of that file.

It was never applied. `sync_workflow_docs` is called for the Cursor and Claude destinations and for the project-scoped Cursor copy. `CODEX_WORKFLOW_DOCS_DIR` and `KIMI_WORKFLOW_DOCS_DIR` are declared in the help text as docs destinations and receive nothing, with or without `--with-docs`. Verified on disk during the audit: `~/.kimi-code/workflow-docs/` held `wos/` and nothing else. The run bootstrapped only because a Claude installation happened to exist on the same machine and its `Glob` found the spec there. On a machine with Kimi alone, the first mandatory read of every command resolves against nothing.

The classification is the underlying error. `--with-docs` describes its payload as optional reading material, which is true of `README.md`, `WORKFLOW_DEMO.md` and `COMMAND_PROMPT_STUBS.md`, and false of the spec.

**The task-repo preflight requires the workflow root.** `task-init`'s repository-path preflight resolves the target repository and then requires it to contain `commands/`, `scripts/` and `wos/`, stopping and asking the user when any is missing. Those three directories sit beside `projects/` only in the maintainer's checkout. In every installed setup the resolved task repository holds `projects/` and the workflow root is elsewhere, so the rule as written stops the product's main mode of use on its first command.

The audited run resolved a task repository holding `projects/` and nothing else, read the STOP instruction, reasoned about which repository the rule meant, and continued. The judgment was right and the rule it disobeyed was wrong. A rule that is only survivable by being ignored teaches that the rules are advisory, which is expensive on a system whose floors depend on being obeyed literally.

The preflight's actual purpose is sound and worth keeping: a resolved path can silently land on a stale mirror or a docs-only checkout, and creating a task folder against the wrong repository is a real failure. That purpose is served by checking the right thing about each of two roots, not by requiring one root to be both.

## Decision

**1. The spec is runtime payload.** `sync_runtime_payload` copies `WORKFLOW_OPERATING_SYSTEM.md` alongside `wos/`, to all four tool destinations, on every sync, outside the `--with-docs` gate, for the reason already written in that function's comment. `--with-docs` keeps carrying the genuinely optional material (`README.md`, `WORKFLOW_DEMO.md`, `COMMAND_PROMPT_STUBS.md`, `templates/`) and its help text stops implying the spec is part of it.

This changes nothing about scripts. The D-3 decision recorded in the same function stands: no helper scripts are distributed, because a helper that runs where it lands is a per-script question and `portfolio-review.sh` demonstrated that shipping the wrong subset produces confident wrong answers. That question keeps its own task.

**2. The preflight checks two roots, each for what it should hold.** `task-init` resolves and validates them separately:

- The **task repository** is where `projects/<client>__<project>/` lives. It is valid when that path exists or can be created; it is never required to contain `commands/`, `scripts/` or `wos/`.
- The **workflow root** is where the spec and the topics resolve from: the canonical checkout when the session is running inside it, otherwise the installed `workflow-docs/` directory the bootstrap already read the spec from.

The STOP is preserved and re-aimed: it fires when the WORKFLOW ROOT cannot be resolved at all, meaning neither `WORKFLOW_OPERATING_SYSTEM.md` nor `wos/` is reachable from anywhere, because no command can honor its mandatory bootstrap in that state. It also fires when the resolved task repository is a stale mirror of the workflow checkout, which is the original wrong-repo hazard: a path holding `commands/` and `wos/` but no `projects/` is a workflow checkout being mistaken for a task repository, and the task folder must not be created there.

When the workflow root resolves to an installed docs tree rather than a checkout, that is the normal installed mode and not a degradation, and the command records which root it used in one transcript line so a later reader can tell where the contract came from. When it resolves to an installed tree that carries no `scripts/`, the substrate digest fallback already documented in `commands/_shared/substrate-digest-fallback.md` applies as it does today, and the run says so rather than implying the helpers were available.

## Consequences

### Positive

- A single-tool install of Codex or Kimi bootstraps. Today it silently depends on a Claude or Cursor install existing beside it.
- The main mode of use stops being blocked by a rule written for the development layout, so the preflight can be obeyed literally instead of reasoned around.
- The original wrong-repo hazard is caught more precisely than before: a workflow checkout mistaken for a task repository now fails the check, which the old rule let through whenever both roots happened to coincide.

### Negative

- Each sync writes one more file (about 120 KB) to four destinations. Negligible next to `wos/`, which is already copied whole.

### Neutral

- No command is added or removed. `task-init` gains no new inputs; it splits a check it already performs.
- The scripts question is untouched and still open under its own task.

## References

- Applies to `WORKFLOW_OPERATING_SYSTEM.md` the runtime-dependency reasoning already recorded in `sync_runtime_payload` for `wos/`; leaves the D-3 no-scripts decision in the same function unchanged.
- Interacts with ADR-0025 (bootstrap tiers and the session-reuse rule): the reuse rule presumes the spec was readable in the first place.
- Consumes `commands/_shared/substrate-digest-fallback.md` for the no-scripts installed case.
- Dogfood evidence: Kimi K3 session `a6f1a135`, 2026-08-06, turn 0 (spec resolved from the Claude destination) and turn 2 (preflight disobeyed).
