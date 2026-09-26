## Summary

<2-4 sentences describing what this PR changes.>

## Type of change

- [ ] New command (`commands/<name>.md`)
- [ ] Edit to existing command
- [ ] Shared block (`commands/_shared/`)
- [ ] Spec edit (`WORKFLOW_OPERATING_SYSTEM.md`)
- [ ] Documentation (README, FAQ, ROADMAP, etc.)
- [ ] Template (`templates/`)
- [ ] Script (`scripts/`)
- [ ] CI / GitHub Actions (`.github/workflows/`)
- [ ] Architecture Decision Record (`docs/adr/`)
- [ ] Eval scenario (`evals/scenarios/`)
- [ ] Other (specify)

## Related issue

Closes #<issue number>, or "no related issue" if standalone.

## Checklist

- [ ] I have read [CONTRIBUTING.md](../CONTRIBUTING.md).
- [ ] I signed off my commits with `git commit -s` (Developer Certificate of Origin; see CONTRIBUTING.md).
- [ ] I ran `./scripts/lint-commands.sh` locally and it passes.
- [ ] I followed the project's style guide (no em-dash, English for normative content, etc.).
- [ ] If I added a new command, I registered it in all three registries (lint fails on any gap):
  - [ ] the cluster bullet list under `## Command categories` in `WORKFLOW_OPERATING_SYSTEM.md`
  - [ ] `wos/command-roles.md`
  - [ ] the `COMMAND_PROMPT_STUBS.md` table (with a minimal prompt example)
- [ ] If I added or edited a command, I regenerated the derived artifacts (never hand-edited):
  - [ ] ran `python3 ./scripts/build-command-catalog.py` (regenerates `docs/command-catalog.html` and `docs/command-catalog.json`)
  - [ ] ran `./scripts/build-agent-skills.sh` (regenerates `.claude/skills/<name>/SKILL.md`)
- [ ] If I edited a `commands/_shared/<name>.md` block, I ran `./scripts/sync-shared-blocks.sh` to propagate it into every command that references it.
- [ ] If I added an ADR or an eval scenario, I added its index row (`docs/adr/README.md` for an ADR, `evals/README.md` for a scenario).
- [ ] If I changed an artifact count, I updated its `<!-- count:KIND -->N<!-- /count -->` marker to match the on-disk count.
- [ ] If I changed normative behavior (the spec or a command contract), I added an ADR under `docs/adr/` when `AGENTS.md` section 6 calls for one (a contract others rely on, a non-obvious tradeoff, a rejected alternative, or a change that is expensive to undo); otherwise the CHANGELOG entry and commit message record it.
- [ ] If this is a breaking change, I updated `CHANGELOG.md` under "Breaking changes" and bumped version per SemVer.
- [ ] I did not include any client names, absolute paths from my home directory, or other private information.

## Notes for the maintainer

<Anything the maintainer should know during review: design tradeoffs you considered, alternatives you rejected, follow-ups intentionally deferred, etc.>