# Contributing to Fhorja

Thanks for considering a contribution. This document covers how to report issues, propose changes, and submit pull requests for this repository.

## Project model: BDFL solo maintainer

This project is maintained by Bruno Mazurok as a personal open-source effort under a BDFL (Benevolent Dictator For Life) governance model. In practice:

- The maintainer makes all decisions about scope, design, and acceptance of contributions.
- There is no SLA for issue or PR response. Best effort, no guarantees.
- PRs are welcome but may be redirected, declined, or merged at maintainer discretion.
- For larger changes, please open a discussion or issue first to align on direction before investing time.
- If this model does not work for you, you are encouraged to fork under AGPL-3.0 terms.

## License and contributor agreement

This project is licensed under [AGPL-3.0](LICENSE).

By submitting a contribution, you agree that:

1. Your contribution is your original work or you have authority to submit it.
2. Your contribution is licensed under AGPL-3.0.
3. The maintainer may relicense your contribution under different open-source or commercial terms in the future, including dual licensing for commercial customers, without further notice or compensation.

A CLA bot ([CLA Assistant](https://cla-assistant.io/)) will be enabled at public launch to record your agreement once on your first PR; until it is wired, the maintainer confirms your agreement in the PR thread. Subsequent PRs are covered by the same agreement.

If you cannot agree to these terms, please do not submit a PR; you are welcome to fork instead.

## Reporting bugs

Use the [bug report template](.github/ISSUE_TEMPLATE/bug_report.md). Include:

- Editor used (Cursor version, Claude Code version, or other)
- Command that produced unexpected behavior
- Expected vs actual output
- Minimal reproduction steps

## Requesting features

Use the [feature request template](.github/ISSUE_TEMPLATE/feature_request.md). Describe:

- The concrete problem you encountered
- The use case context
- An initial proposal (optional)

Feature requests are evaluated against the project's design principles (see `WORKFLOW_OPERATING_SYSTEM.md`). Suggestions that conflict with the workflow's strict, evidence-driven philosophy may be declined with rationale.

## Proposing a new command

Adding a command to `commands/` requires more than a markdown file. New commands must:

1. Have a clear, non-redundant role distinct from existing commands.
2. Follow the standard structure documented in `WORKFLOW_OPERATING_SYSTEM.md` (`Goal`, `Required inputs`, `Operating rules`, `Required output`, `Standard output layout (required)` with its `### Artifact changes`, `### Command transcript`, and `### Handoff` sections, `Definition of done (command output)`). Include Agent Skills frontmatter with `name`, `description`, `metadata.category`, `metadata.primary-cursor-mode`, `metadata.context-layers-consumed`, `metadata.context-layers-produced`, `metadata.token-budget`, `metadata.tools`, `metadata.x-wos-profiles`, and `provenance`. `scripts/lint-commands.sh` is the normative checklist for structure and frontmatter; this list is a summary.
3. Pass `scripts/lint-commands.sh` validation.
4. Be referenced in:
   - `## Command categories` and `## Command roles` index in `WORKFLOW_OPERATING_SYSTEM.md`, plus full detail entry in `wos/command-roles.md`
   - `Command catalog` in `README.md` (generated: run `python3 scripts/build-command-catalog.py`; do not hand-edit that section)
   - `COMMAND_PROMPT_STUBS.md` with a minimal prompt example
5. Have a corresponding slot in `WORKFLOW_DEMO.md` if the command represents a new flow stage.

For commands that overlap heavily with existing ones, expect pushback or a request to merge instead of creating a new file.

## Proposing changes to the spec

`WORKFLOW_OPERATING_SYSTEM.md` is the normative spec. Changes to it should be accompanied by an Architecture Decision Record under `docs/adr/` (format: Michael Nygard simplified, see existing ADRs for reference).

For breaking changes (anything that invalidates existing task memory format or output contracts), expect:

1. Discussion or issue first.
2. Migration guide for users with active tasks under the old format.
3. Major version bump (per [SemVer](https://semver.org/) + [CHANGELOG.md](./CHANGELOG.md)).

## Style guide

### Markdown

- Use English for normative content (commands, the spec, output tokens like `NO_OP`, `NO_OP_TRACE`).
- Documentation prose can be in English or Portuguese depending on file purpose; be consistent within a file.
- No em-dash characters (Unicode U+2014); prefer colons, parentheses, or hyphens.
- Natural voice (no AI tells): human-facing prose must read like a person wrote it. Avoid slash disjunctions in prose (write `Slack, Discord, or email`, not `Slack / Discord / email`; code enums like `LOW/MEDIUM/HIGH` are exempt), `not just X, but Y` parallelism, vocabulary cliches (`leverage`, `utilize`, `seamless`, `robust`, `comprehensive`, `crucial`, `it's worth noting`), and decorative bold, emoji, or Title Case headers. Full catalog with rewrites: `wos/natural-voice.md`. Lint runs `scripts/check-natural-voice.sh` as an advisory (warn-only) check that never fails the build.
- Use fenced code blocks with language hint (`text`, `bash`, `yaml`, `markdown`) wherever applicable.
- Reference other files in the repo with relative paths.

### Bash scripts

- Use `set -euo pipefail` at the top.
- Add `--help` / `-h` flag with usage text.
- Add `--dry-run` flag for any script that writes files.
- Make scripts executable (`chmod +x`).

### YAML (GitHub Actions, etc.)

- Pin action versions explicitly (e.g., `actions/checkout@v4`, not `@main`).
- Add comments for non-obvious choices.

## Local development

```bash
# Sync commands to your editor (legacy slash commands)
./scripts/sync-workflow-slash-commands.sh --dry-run  # preview
./scripts/sync-workflow-slash-commands.sh             # apply

# Mirror generated Agent Skills to user-level dirs (multi-tool drop-in)
./scripts/sync-workflow-slash-commands.sh --with-skills

# Run command lint before opening PR (covers required sections, shared-block
# drift, frontmatter, em-dashes, natural-voice advisory, AND skills drift via build-agent-skills.sh --check)
./scripts/lint-commands.sh

# If you changed any commands/<name>.md, regenerate the Agent Skills artifacts
./scripts/build-agent-skills.sh             # build (idempotent)
./scripts/build-agent-skills.sh --check     # CI-style drift check; exits 1 on drift

# If you changed normative docs, sync the docs mirror too
./scripts/sync-workflow-slash-commands.sh --with-docs

# Re-baseline token footprint after structural changes
python3 ./scripts/measure-tokens.py > scripts/baseline-$(date +%Y-%m-%d).md
```

### Agent Skills (canonical → generated)

The command files under `commands/` (flat `<name>.md` plus folder-shaped persona commands at `commands/<name>/SKILL.md`) are the **canonical source of truth**. The generated `.claude/skills/<name>/SKILL.md` files are produced by `scripts/build-agent-skills.sh` and committed to the repo so any of the 35+ tools that read `.claude/skills/` natively (Cursor 2.4+, Claude Code, GitHub Copilot, OpenAI Codex, Gemini CLI, OpenHands, Goose, etc.) gets drop-in compatibility without an install step.

**Never edit `.claude/skills/<name>/SKILL.md` by hand.** The lint catches drift; the build adapter is idempotent. Edit `commands/<name>.md` and run `./scripts/build-agent-skills.sh`. See [`docs/MIGRATION.md`](./docs/MIGRATION.md) for the full forking and customization guide and [ADR-0005](./docs/adr/0005-multi-tool-architecture.md) for the why.

### Shared canonical blocks

Some sections of `commands/*.md` are identical across many commands (the
`### Standard output layout`, `### Handoff` body, `Mandatory context bootstrap`
block, etc.). Their canonical content lives in `commands/_shared/<name>.md` and
each command file declares a `<!-- shared:<name> -->` marker for the variants
it uses. See `commands/_shared/README.md` for the full table.

When editing one of those shared sections:

```bash
# 1. Edit the canonical body in commands/_shared/<name>.md.
# 2. Propagate to every command that declares the marker.
./scripts/sync-shared-blocks.sh --dry-run    # preview
./scripts/sync-shared-blocks.sh              # apply

# 3. Confirm zero drift.
./scripts/lint-commands.sh
```

The lint script reports drift between any marker and its canonical, and exits
non-zero if drift is present. The sync script is idempotent: running it on a
clean repo produces no diff.

## Pull request flow

1. Fork the repo.
2. Create a feature branch (`feat/your-change` or `fix/your-issue`).
3. Make your changes; commit with conventional commit messages (`feat:`, `fix:`, `docs:`, `chore:`, etc.).
4. Run `./scripts/lint-commands.sh` and ensure it passes.
5. Open a PR using the [PR template](.github/pull_request_template.md).
6. Sign the CLA when prompted (one-time per contributor).
7. Wait for review. Best-effort response time.

## Commercial licensing

If your organization needs to use this workflow under terms different from AGPL-3.0 (for example, integrating into a closed-source product or proprietary SaaS), a commercial license is planned but not yet available. Contact the maintainer by email to register interest.

## Questions

For usage questions, check [docs/FAQ.md](./docs/FAQ.md) or open a discussion. For workflow-specific guidance, the workflow itself is the answer: see `WORKFLOW_DEMO.md` and `COMMAND_PROMPT_STUBS.md`.