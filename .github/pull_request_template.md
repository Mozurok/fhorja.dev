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
- [ ] I have signed the CLA when prompted by CLA Assistant on this PR.
- [ ] I ran `./scripts/lint-commands.sh` locally and it passes.
- [ ] I followed the project's style guide (no em-dash, English for normative content, etc.).
- [ ] If I added a new command, I registered it in all four registries (lint fails on any gap):
  - [ ] the cluster bullet list under `## Command categories` in `WORKFLOW_OPERATING_SYSTEM.md`
  - [ ] the `## Command roles` index in `WORKFLOW_OPERATING_SYSTEM.md`
  - [ ] `wos/command-roles.md`
  - [ ] the `COMMAND_PROMPT_STUBS.md` table (with a minimal prompt example)
- [ ] If I added or edited a command, I regenerated the derived artifacts (never hand-edited):
  - [ ] ran `python3 ./scripts/build-command-catalog.py` (regenerates the README `## Command catalog` and `docs/command-catalog.*`)
  - [ ] ran `./scripts/build-agent-skills.sh` (regenerates `.claude/skills/<name>/SKILL.md`)
- [ ] If I edited a `commands/_shared/<name>.md` block, I ran `./scripts/sync-shared-blocks.sh` to propagate it into every command that references it.
- [ ] If I added an ADR or an eval scenario, I added its index row (`docs/adr/README.md` for an ADR, `evals/README.md` for a scenario).
- [ ] If I changed an artifact count, I updated its `<!-- count:KIND -->N<!-- /count -->` marker to match the on-disk count.
- [ ] If I changed normative behavior (the spec or command contract), I added an ADR under `docs/adr/`.
- [ ] If this is a breaking change, I updated `CHANGELOG.md` under "Breaking changes" and bumped version per SemVer.
- [ ] I did not include any client names, absolute paths from my home directory, or other private information.

## Notes for the maintainer

<Anything the maintainer should know during review: design tradeoffs you considered, alternatives you rejected, follow-ups intentionally deferred, etc.>