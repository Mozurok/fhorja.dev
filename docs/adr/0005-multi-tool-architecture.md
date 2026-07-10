# ADR-0005: Multi-tool architecture (canonical commands → generated skills)

- **Status**: Accepted
- **Date**: 2026-05-08
- **Tags**: multi-tool, agent-skills, canonical-source, code-generation, distribution

## Context

The workflow targets many tools at once: Cursor, Claude Code, GitHub Copilot, OpenAI Codex, Gemini CLI, OpenHands, Goose, Junie, Roo Code, Mistral Vibe, Snowflake Cortex, Databricks Genie, etc. Each tool reads commands from a different directory and (until recently) used a different file format.

Three options for distributing the same workflow across that ecosystem:

1. **Author once, distribute one format**. Pick a tool, author `.claude/commands/*.md`, expect users to convert if they want another tool. Lowest authoring cost but tightly couples the project to one vendor's lineage.
2. **Author per tool, hand-keep them in sync**. Maintain `commands/*.md` for tool A, parallel files for tool B, etc. High authoring cost; drift is inevitable.
3. **Author canonical, generate per-tool**. One source-of-truth tree; adapter scripts emit per-tool formats; lint detects drift.

A new force entered late in the design: the **open Agent Skills standard** (`agentskills.io`, 35+ tools as of mid-2026). Tools converged on a single format (`.claude/skills/<name>/SKILL.md` with YAML frontmatter) that any of them can consume. This collapsed the per-tool format problem: the **distribution** target is now one file shape, but the **canonical authoring surface** can still be different.

The canonical authoring surface in this repo is `commands/<name>.md`. It carries:

- An English title, "Act as ..." persona line, `Goal:`, `Mandatory context bootstrap:`, `Use when:` / `Do not use when:`, `Primary editor mode:`, `Required inputs:`, `Operating rules:`, the standard output layout (`### Standard output layout`, `### Artifact changes`, `### Command transcript`, `### Handoff`), and a `### Definition of done`.
- Shared canonical blocks (`commands/_shared/<name>.md`) inlined by `sync-shared-blocks.sh`, validated by `lint-commands.sh` for drift.
- Agent Skills frontmatter at the top (added in P11): `name`, `description` (≤1024 chars), `metadata` (category, primary-cursor-mode, multi-repo-aware).

The Agent Skills target is `.claude/skills/<name>/SKILL.md`. It is structurally a near-superset of the canonical command body (frontmatter is identical; the H1 line is redundant with the frontmatter `name` field).

## Decision

`commands/<name>.md` is the **single canonical source of truth** for every command. `.claude/skills/<name>/SKILL.md` is **generated** by `scripts/build-agent-skills.sh` from each canonical, and committed to the repo so any of the 35+ tools that read `.claude/skills/` natively gets drop-in compatibility without an install step.

Specifically:

- The adapter copies the YAML frontmatter verbatim, drops the redundant H1 line, copies the body verbatim. The result is byte-stable across runs (idempotent).
- Stale skill directories (whose canonical command was removed) are pruned by default; `--no-prune` opts out.
- `lint-commands.sh` invokes `build-agent-skills.sh --check` on every run; any drift between `commands/` and `.claude/skills/` fails the lint and blocks the commit.
- CI runs both the canonical-vs-generated drift check and `skills-ref validate` (the open Agent Skills spec validator, pinned to a known-good upstream SHA).
- README and WOS document the rule explicitly: **never edit `.claude/skills/*/SKILL.md` by hand; lint will fail on drift**.

Tool-specific user-level mirroring (for users who want skills available outside this repo's checkout) is handled by `scripts/sync-workflow-slash-commands.sh --with-skills`, which copies `.claude/skills/` to `~/.claude/skills/`, `~/.cursor/skills/`, and `~/.codex/skills/`.

## Consequences

### Positive

- **Single authoring surface**. Changes happen in `commands/<name>.md`. The 33 generated `SKILL.md` files refresh automatically.
- **Multi-tool drop-in**. Cloning the repo is sufficient; opening it in any of the 35+ tools that read `.claude/skills/` natively surfaces the workflow with no install step.
- **Open spec compliance**. `skills-ref validate` ensures the canonical schema is honored. The repo will not silently drift from the upstream spec.
- **Drift-resistant**. The lint enforces canonical-vs-generated equality; drift surfaces immediately on the next commit attempt.
- **Future-proof for new tools**. Any new tool that adopts the open Agent Skills standard works without changes here.

### Negative

- The repo carries duplicated content (canonical commands in `commands/`, generated mirrors in `.claude/skills/`). The duplication doubles the markdown footprint of those files in the repo, although markdown is small.
- Users who edit `.claude/skills/*/SKILL.md` directly (out of habit) lose their changes on the next `build-agent-skills.sh` run. The README warns explicitly; lint catches it; but the failure mode exists.
- Adding a new tool format (a non-Agent-Skills target) requires writing a new adapter. The adapter pattern scales linearly with tool format diversity, which is a real cost.

### Neutral

- The split between "canonical" (`commands/*.md`) and "generated" (`.claude/skills/`) is a project convention, not a Git or filesystem primitive. Newcomers to the repo have to internalize it.

## Alternatives considered

### Alternative 1: `.claude/skills/` as canonical; nothing in `commands/`

- Skip the canonical/generated split; treat `.claude/skills/<name>/SKILL.md` as the source of truth.
- Rejected: locks the canonical to one tool's directory convention (even though the format is open). Also makes shared-block propagation (`commands/_shared/`) awkward; it would need a new home under `.claude/`, breaking the established pattern.

### Alternative 2: Symlinks instead of generation

- `ln -s commands/task-init.md .claude/skills/task-init/SKILL.md`
- Rejected: the H1 line in `commands/task-init.md` is redundant with the frontmatter `name` field and would fail `skills-ref validate`. Also, symlinks do not commit well across platforms (Windows checkouts break).

### Alternative 3: Hand-author both; lint for drift

- Keep `commands/` as Cursor-style and `.claude/skills/` as Agent-Skills-style; lint that they describe the same intent.
- Rejected: doubles authoring effort; "describe the same intent" is not mechanically checkable; drift is inevitable.

## References

- `WORKFLOW_OPERATING_SYSTEM.md` → `## Repository structure` (lists `.claude/skills/` as generated).
- `README.md` → `## Multi-tool distribution (Agent Skills)` (full user-facing explanation).
- `scripts/build-agent-skills.sh` (the adapter; idempotent; supports `--check`, `--no-prune`, `--dry-run`).
- `scripts/lint-commands.sh` (invokes `build-agent-skills.sh --check`; fails on drift).
- `.github/workflows/lint.yml` → `validate-skills-spec` job (CI invokes `skills-ref validate`).
- [agentskills.io specification](https://agentskills.io/specification) (open standard, accessed 2026-05-08).
- [Cursor Skills docs](https://cursor.com/docs/context/skills) (confirms Cursor reads `.claude/skills/` automatically; accessed 2026-05-08).

## Notes

P11 (Agent Skills migration) was the architectural shift that operationalized this ADR. Phase 1 added frontmatter to all 33 commands; Phase 2 wrote the adapter and committed `.claude/skills/`; Phase 3 added open-spec compliance, `--with-skills` mirror, README/WOS docs, and CI integration. The rule "canonical commands; generated skills; lint enforces drift" is now load-bearing for the repo's distribution story.
