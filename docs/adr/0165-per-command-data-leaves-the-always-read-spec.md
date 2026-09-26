# ADR-0165: Per-command data leaves the always-read spec

- **Status**: Accepted
- **Date**: 2026-08-30
- **Tags**: spec, context-budget, command-roles, registries, always-paid-surface, extends-adr-0006, extends-adr-0136

## Context

`WORKFLOW_OPERATING_SYSTEM.md` is read on every invocation of every command. Its
`## Command roles` section held one `### <name>` entry per command, with a Role line and a
Next line: 44086 chars of per-command data, about a third of the file, paid by every command
including the ones that never route. `wos/command-roles.md` already held the same data with
more detail, lazily.

ADR-0006 split the spec from the lazy topics on exactly this principle and the index survived
the split. ADR-0136 then set a non-regression ceiling on the file and recorded, as an open
item, that the check measures one file and says nothing about what is inside it.

## Decision

The `## Command roles` heading stays in the spec and its body becomes a pointer to
`wos/command-roles.md`. Per-command Role and Next live in one place.

Registry membership drops from four surfaces to three: the spec `## Command categories`
cluster list, `wos/command-roles.md`, and `COMMAND_PROMPT_STUBS.md`. `scripts/lint-commands.sh`
loses the forward check and the reverse walk that read the spec index. The reverse walk is
deleted rather than retargeted: over a section holding only a pointer it would emit zero names
and pass forever, which is a guard that has stopped guarding.

The heading is deliberately preserved. `scripts/check-doc-sync.sh` resolves a `## X` token on
any line naming the spec file against the spec's real headings, and three such citations are
live (`README.md`, `docs/MIGRATION.md`, `wos/command-roles.md`).

Before the deletion, the twelve commands whose next-command edge existed only in the spec are
ported into `wos/command-roles.md`, so no routing edge is lost. The plan for this change said
thirteen. Measured on 2026-08-30: twelve. `unity-scene-plan` is the only one of the spec's 98
entries with no `Next:` line at all, and it has no `Typical next` in the topic either, so there
was no thirteenth edge to move. `scripts/flow-audit.py` already lists it among the commands with
no outbound edge. That gap predates this ADR and giving it an edge is separate work.

## Consequences

The spec drops from 125307 to about 81600 chars. Adding a command now means three registrations,
not four, and every document that said four is corrected in the same wave.
