# ADR-0228: Skills install where each tool reads them, and ~/.cursor/skills is opt-in

- **Status**: Accepted
- **Date**: 2026-09-23
- **Supersedes**: in part, [ADR-0005](./0005-multi-tool-architecture.md), its sentence naming `~/.cursor/skills/` among the user-level mirror destinations. The rest of ADR-0005 stands.
- **Tags**: installer, agent-skills, cursor, codex, claude-code, skill-listing, clean-orphans, skilloverrides, b19, b23

## Context

`scripts/sync-workflow-slash-commands.sh` copied every generated skill to three user-level roots:
`~/.claude/skills`, `~/.cursor/skills` and `~/.agents/skills`. Which tool reads which root was
checked on 2026-09-23 against each tool's own documentation:

- Claude Code reads `~/.claude/skills` and a repository's `.claude/skills`. Its skills page lists no
  `.agents` location, issue 31005 on anthropics/claude-code closed as a duplicate on 2026-09-18
  with later comments confirming `.agents/skills` is unsupported, issue 16345 is still open, and the
  release notes from 2.1.277 to 2.1.281 carry no entry for it. Two skills that exist only in the
  maintainer's `~/.agents/skills` do not appear in a Claude Code session's listing.
- Codex reads `~/.agents/skills` as its user root and nothing under `~/.cursor`.
- Cursor reads `.agents/skills`, `.cursor/skills`, `~/.agents/skills` and `~/.cursor/skills` natively,
  and loads `~/.claude/skills` for compatibility. Only `~/.cursor/skills` syncs to Cursor Cloud
  Agents. Cursor builds before 3.17.8 did not inject `.agents/skills` (a forum thread against 3.3.27,
  fixed by 3.17.8 in August 2026). How Cursor handles one name found in two roots is not documented.

So a default install gave Cursor every Fhorja skill twice, once from each of the two roots it reads
natively, and gave Claude Code and Codex one copy each.

Backlog B19 had proposed dropping `~/.cursor/skills` and was closed without building on 2026-09-17,
for two reasons. First, the redundancy it relied on was Cursor's compatibility load of
`.claude/skills`, which a user can switch off. Second, removing the destination would delete nothing
already installed, and the one removal path in the installer, `--clean-orphans`, would have been the
wrong tool: on the maintainer's machine `~/.cursor/skills` held 11 skills that are not Fhorja's
beside the 98 that are.

Two smaller facts came out of the same research. The wizard's everyday option read "all skills + the
everyday spine commands" while its branch calls `set_profile minimal`, which has filtered the skills
since 2026-08-30. And the Claude Code lever on the per-turn listing is the profile or a
`skillOverrides` entry, which no Fhorja command produced.

## Decision

A default sync writes the skills to `~/.claude/skills` and `~/.agents/skills`, one root per reader,
and stops writing `~/.cursor/skills`. Cursor 3.17.8 is the stated minimum. The rest follows from
that:

- `--cursor-skills` writes `~/.cursor/skills` as well (`CURSOR_SKILLS_DIR` still moves it), for Cursor
  Cloud Agents sync. Before this, the only override was the environment variable; no flag existed.
- `--project PATH` follows the same default: `PATH/.claude/skills` and `PATH/.agents/skills`, and
  `PATH/.cursor/skills` only under `--cursor-skills`.
- `--clean-orphans` also removes the Fhorja skills an earlier install left in `~/.cursor/skills`,
  unless `--cursor-skills` keeps that root a destination. It asks on a terminal, needs `--yes`
  otherwise, and deletes nothing under `--dry-run`. A skill there counts as Fhorja's only when its
  name is one of the repository's skills and its `SKILL.md` frontmatter carries `x-wos-profiles`;
  a name match alone is not enough, and the check is repeated at the moment of deletion.
- `--print-skill-overrides=<minimal|core>` prints a Claude Code `skillOverrides` object that sets every
  Fhorja skill outside the tier to `name-only`, then exits. It writes nothing: which skills a machine
  demotes is the operator's call and lives in their own settings file.
- The wizard's everyday option says what it installs: "the everyday spine: skills and commands".
- The installer usage carries a `Default skill roots:` line. `check_default_skill_roots_agree` in
  `evals/scripts/structural-evals.py` asserts that README, FAQ and MIGRATION each name the same roots
  inside a `skill-roots` span and that none of them calls another root a default, with two mutations
  in `evals/scripts/guard-mutation.py`. `scripts/tests/test-install-destinations.sh` asserts that the
  usage line names the roots a default run actually writes.

This reverses backlog B19 on a new basis. The redundancy no longer rests on a compatibility setting:
Cursor reads `~/.agents/skills` natively, the same root Codex and Kimi read. And the removal now has a
path that cannot take a skill that is not Fhorja's, which is what stopped B19 from recommending
`--clean-orphans`.

## Consequences

### Positive

- Cursor sees one copy of each Fhorja skill on a default install, and `~/.agents/skills` is the single
  root three tools share.
- An operator who wants to shrink Claude Code's listing gets the exact object to paste, computed from
  the same profile metadata the installer filters on.
- Six places that promised `~/.cursor/skills` as a default now agree with the installer, and three of
  them are checked.

### Negative

- A Cursor Cloud Agents user who relied on the default install must now pass `--cursor-skills`; a
  default sync stops refreshing their root. The end-of-run summary and `check-installed-skills-drift.sh`
  both name the flag.
- A Cursor older than 3.17.8 sees no user-level Fhorja skill on a default install unless its Claude
  compatibility load picks up `~/.claude/skills`.
- Existing installs keep their `~/.cursor/skills` copies, and the duplicate listing with them, until
  the operator runs `--clean-orphans`. The installer says so in its summary rather than removing
  anything on its own.

### Neutral

- Dropping `~/.cursor/skills` does nothing for Claude Code's per-turn cost. The installer also writes
  command files to `~/.claude/commands`, which Claude Code reads beside `~/.claude/skills`; whether its
  listing collapses a name found in both is not measured, and the docs say so. It needs `/context`
  read inside and outside this repository, which only the maintainer can run.
- The same change prunes templates retired from the repository out of the `--with-docs` copy, the rule
  the runtime payload already applied to its topics, and adds a skills preflight
  (`build-agent-skills.sh --check` before any write, refusing on drift, skipped with a named line when
  `python3` is absent, not run under `--no-skills`). Neither is decided here; the CHANGELOG records
  both.

## Alternatives considered

### Keep all three roots

- No code change.
- Rejected: Cursor reads two of them natively, so every Fhorja skill is listed twice there, and the
  docs described a layout no tool needed.

### Keep `~/.cursor/skills` and drop `~/.agents/skills`

- Cursor would still get one copy, and Cloud Agents sync would keep working by default.
- Rejected: Codex reads only `~/.agents/skills`, and Kimi reads it natively. Dropping it removes the
  skills from two tools to spare an opt-in flag for a third.

### Symlink one root to another

- One copy on disk, so nothing can drift between roots.
- Rejected for now: Codex documents symlink support, but whether Cursor deduplicates a symlinked root
  is unproven, and a canary under the operator's home is the maintainer's to run.

### Remove Fhorja skills from `~/.cursor/skills` by name, as the legacy Codex cleanup does

- Simpler, and consistent with `cleanup_legacy_codex_skills`.
- Rejected: `~/.cursor/skills` is shared with skills from other sources, and a user's own skill can
  share a Fhorja name. The frontmatter key is what only a Fhorja skill carries.

### Write `skillOverrides` into `~/.claude/settings.json`

- One step less for the operator.
- Rejected: that file is machine-local configuration the operator owns, and a repository script that
  rewrites it is a trust problem out of proportion to the saving.

## References

- `scripts/sync-workflow-slash-commands.sh` (the destinations, `--cursor-skills`, `--clean-orphans`,
  `--print-skill-overrides`, the usage line).
- `scripts/tests/test-install-destinations.sh` and `scripts/tests/test-install-payload.sh`.
- `evals/scripts/structural-evals.py` → `check_default_skill_roots_agree`.
- Claude Code skills documentation, https://code.claude.com/docs/en/skills (read 2026-09-23).
- Codex skills documentation, https://developers.openai.com/codex/skills (read 2026-09-23).
- Cursor skills documentation, https://cursor.com/docs/skills (read 2026-09-23).
- anthropics/claude-code issues 31005 and 16345 (read 2026-09-23).
