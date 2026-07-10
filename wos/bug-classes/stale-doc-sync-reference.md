---
name: stale-doc-sync-reference
category: meta
default-severity: P2
priority: P2
pillars: [maintainability, observability]
cwe: [CWE-1059]
languages: [markdown]
file-patterns: ["packages/wos-engine/internal/wos/**/*.md", "packages/wos-engine/internal/commands/**/*.md", "packages/wos-engine/internal/docs/**/*.md"]
perspectives: [maintainer, operator]
reversibility-check: false
---

# stale-doc-sync-reference

A curated doc references an artifact that no longer exists in the canonical shape the reference expects: a backticked command name that has been removed or renamed, an `ADR-NNNN` id that was never created (or was archived), or a `wos/<topic>.md` path that does not resolve on disk. The `scripts/check-doc-sync.sh` drift guard surfaces these as broken refs at `file:line` granularity. Each broken ref is a small navigation failure for any reader -- human or agent -- who tries to follow the link.

## What it looks like

- A doc paragraph mentions `` `some-command` `` but `some-command` is not in the live command registry (renamed, removed, or never existed).
- A doc cites `ADR-0042` but `internal/docs/adr/0042-*.md` does not exist (typo, future-dated reference, or archived without a redirect).
- A doc links to `wos/<topic>.md` but the file moved or was deleted in a refactor and the link was not updated.
- `bash scripts/check-doc-sync.sh` exits non-zero with one or more `path/to/file.md:42 -> broken-ref: <ref>` lines.

## Why it matters

- Navigation failure: a reader following the broken ref hits a dead end. For LLM agents that resolve refs as part of context-loading, the dead end becomes a silent context gap instead of a visible 404.
- User confusion: a backticked command name implies the command is callable. If it has been removed, the reader either tries it and fails, or treats the doc as still authoritative on stale behavior.
- Observability gap without the guard: drift accumulates silently across many small doc edits. The guard converts "drift that nobody notices" into "exit-non-zero on every check".
- Cumulative trust loss: even one stale ref in a high-traffic doc (e.g. `entry-points.md`, `command-roles.md`) erodes confidence in the rest of the curated surface.

## How to detect

```bash
bash scripts/check-doc-sync.sh
# Exit code: 0 = clean. Non-zero = broken refs.
# Output lines have the shape:
#   internal/wos/<file>.md:<line> -> broken-ref: <kind>=<value>
# where <kind> is one of: command, adr, topic
```

Run the script locally before pushing a doc-touching commit. CI runs it on every PR; a non-zero exit blocks merge.

## How to fix

For each broken ref, pick exactly one of three resolutions -- do not silently delete the surrounding text without a deliberate choice:

1. Update the doc to the current ref. The artifact still exists but was renamed or relocated. Replace the stale token with the live one and verify the surrounding sentence still reads correctly.
2. Restore the missing artifact. The ref is correct and the artifact should exist but has been deleted in error (e.g. an ADR was removed without an archive note, a command was renamed mid-refactor). Recreate or restore the artifact at the expected path.
3. Deliberately deprecate. The artifact is intentionally gone. Replace the bare ref with an explicit "removed" or "superseded" note (e.g. ``~~`old-command`~~ removed in ADR-0029; use `new-command` instead``). The drift guard treats explicit removal notes as resolved.

After fixing, re-run `bash scripts/check-doc-sync.sh` and confirm exit 0.

## CWE / standard refs

- CWE-1059: Insufficient Technical Documentation (advisory). The bug class covers the case where technical documentation references artifacts that no longer match the running system; the reader cannot rely on the documentation as a faithful map.

## See also

- `scripts/check-doc-sync.sh` -- the drift guard that surfaces this class
- `docs/proposals/doc-sync-validator.md` -- design rationale and ref-kind taxonomy
- ADR-0029 -- drift guards as a class (curated-surface integrity)
- `wos/bug-classes/documentation-drift.md` -- sibling class covering signature/behavior drift in inline docstrings
