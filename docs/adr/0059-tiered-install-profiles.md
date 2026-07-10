# ADR-0059: Tiered install profiles, lint-enforced metadata.tools and provenance

- **Status**: Accepted
- **Date**: 2026-06-26
- **Tags**: install, onboarding, frontmatter, metadata-tools, x-wos-profiles, provenance, lint, ecosystem-adoption, additive

## Context

The 2026-06-26 vibe-coding ecosystem research (see `projects/bmazurok__my-work-tasks/active/2026-06-26_vibe-coding-ecosystem-research/EXTERNAL_RESEARCH.md`) surfaced three convergent, low-risk improvements drawn from the leading community repos, all of which sit inside the existing markdown-canonical, lint-enforced frontmatter contract:

- **Install friction.** `sync-workflow-slash-commands.sh` copied every command with no filtering, so a newcomer met the full corpus at once. ECC (Everything Claude Code) ships tiered install profiles (minimal / core / full); four repos independently pointed at the same onboarding barrier.
- **No machine-checked tool boundary.** Tool restrictions lived only as prose inside command bodies. The awesome-claude-code-subagents convention declares an explicit `tools:` list per agent; a read-only command could silently gain write tools and nothing would catch it.
- **No provenance signal.** ADR-0046 deferred a provenance/creator-tier field for trusted skills (DEF-09). The scale of external skills now makes the gap concrete: a vetted WOS skill and an anonymous third-party skill carry the same flat verdict.

These are additive metadata changes; they do not alter any command's behavior, only how the corpus is described, filtered, and lint-checked.

## Decision

Add three required `metadata` frontmatter fields to every command, all rule-derived from existing fields so no field is hand-assigned, and enforce each in `scripts/lint-commands.sh`:

1. **`tools`** (canonical vocabulary: Read, Write, Edit, Bash, Glob, Grep, WebFetch, WebSearch, Task). Derived: base `[Read, Grep, Glob, Bash]`; add `[Write, Edit]` unless the command is read-only (`context-layers-produced: []`); add `[Task]` for orchestrators; add `[WebFetch, WebSearch]` for the authorized web-fetch set. **Read-only guard:** lint fails when a `context-layers-produced: []` command declares Write or Edit (Bash is exempt; read-only commands still run git, grep, and lint). This is the rank-1 candidate from the research: it turns the read-only-versus-write boundary from prose into a CI-checked property.

2. **`x-wos-profiles`** (subset of `[minimal, core, full]`). Category-derived, not hand-picked: `minimal` is the lifecycle spine (task-init, impact-analysis, decision-interview, implementation-plan, approve-plan, implement-approved-slice, slice-closure, review-hard, pr-package, what-next, sync-task-state, task-close); `full` adds orchestrator fleets, the design-system set, database-context, and the specialist personas; `core` is everything else. A command lists every tier that ships it. `sync-workflow-slash-commands.sh --profile <tier>` copies only commands whose list contains the tier; with no `--profile`, it copies all (backwards-compatible).

3. **`provenance`** (enum: first-party, vetted-third-party, sandbox). Every WOS command is `first-party`. The other values are reserved for external skills a human approved via `skill-vet`, which gains a provenance line in its verdict. This is the concrete realization of ADR-0046 DEF-09.

The taxonomy and the tier-class labels are stated tech-agnostically: profiles are named by role tier, not by command count or model SKU, and `tools` is the host's built-in vocabulary, not a model-specific list.

## Consequences

- A read-only command that later declares a write tool fails lint, closing a drift class the WOS could not previously catch.
- New adopters can install a manageable surface (`--profile minimal`) and grow into the full corpus; this is primarily a Phase 3 onboarding lever.
- Every command frontmatter carries three more fields. They are generated into `.claude/skills/<name>/SKILL.md` by the existing verbatim copy in `build-agent-skills.sh`, so no generator change was needed.
- The canonical `tools` vocabulary must be kept in sync as the host adds or renames built-in tools; the `VALID_TOOLS` array in `lint-commands.sh` is the single owner.
- This ADR is additive and does not supersede any prior decision. It extends ADR-0046 (skill trust) with the provenance field and ADR-0013/ADR-0012 (frontmatter contract) with three fields.
