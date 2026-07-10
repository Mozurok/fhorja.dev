# ADR-0029: lint drift guards - registry membership and count markers

Status: Accepted (2026-06-02)

## Context

Two documentation-consistency sweeps (2026-06-01 and 2026-06-02, the second a multi-agent audit) found that the repo's hand-maintained documentation drifts from disk in two recurring ways:

1. **Shipped-but-unregistered commands.** `api-contract-review` and `stack-currency-check` had command files, frontmatter, and generated skills, but were absent from every discoverability registry (the WOS `### <cluster>` lists, the WOS `## Command roles` index, `wos/command-roles.md`, and `COMMAND_PROMPT_STUBS.md`), making them invisible to anyone navigating the workflow. `code-context-map` was missing its copy-paste stub.
2. **Stale prose counts.** Numbers like "49 commands", "16 anti-patterns", "23 scenarios", "24 ADRs", "16 entry-point scenarios" were scattered across WOS, README, FAQ, MIGRATION, CLAUDE.md, and the `wos/` topic files, disagreeing with disk and with each other (e.g. "49" vs "52" commands in the same document).

`lint-commands.sh` validated required sections, shared-block drift, frontmatter, forbidden bytes, and skills drift, but had **no guard** for registry membership or numeric counts. The drift was caught only by manual or multi-agent audit, after it had already shipped. Counts being hand-maintained made re-drift inevitable.

## Decision

Add two deterministic guards to `scripts/lint-commands.sh`. Both are commit-blocking (exit 1) like the existing checks.

### 1. Registry membership

Every `commands/<name>.md` must appear in all four discoverability surfaces:
- a WOS `### <cluster>` bullet (`- \`<name>\``)
- the WOS `## Command roles` index (`### <name>`)
- `wos/command-roles.md` (`### <name>`)
- the `COMMAND_PROMPT_STUBS.md` table (`| \`<name>\` |`)

And the reverse: every entry in those surfaces must map to a real command file (catches stale entries for renamed or removed commands). Deterministic; requires no annotations.

### 2. Count markers

Numbers that assert an on-disk quantity are wrapped in an HTML-comment marker:

```
<!-- count:KIND -->N<!-- /count -->
```

The lint extracts each `(KIND, N)`, computes the live on-disk count for `KIND`, and fails if `N` does not match. HTML comments do not render in Markdown, so the marker is invisible to readers (only the digit `N` shows). Supported `KIND` values and their disk sources:

| KIND | source of truth |
|------|-----------------|
| `commands` | `commands/*.md` |
| `skills` | `.claude/skills/*/SKILL.md` |
| `adrs` | `docs/adr/[0-9]*.md` |
| `scenarios` | `evals/scenarios/[0-9]*.md` |
| `wos-topics` | `wos/*.md` |
| `bug-templates` | `wos/bug-classes/*.md` minus `_index` |
| `bug-categories` | distinct `category:` in `wos/bug-classes/*.md` |
| `command-categories` | distinct `category:` in command frontmatter |
| `anti-patterns` | `^- ` bullets in `wos/anti-patterns.md` |
| `entry-points` | `^## ` headings in `wos/entry-points.md` |

The scan covers the root docs, all `wos/*.md`, `docs/FAQ.md`, `docs/MIGRATION.md`, `docs/adr/README.md`, and `evals/README.md`.

## Consequences

### Positive
- The "shipped but unregistered" class is now impossible to merge: adding a command without registering it in all four places fails CI.
- Marked counts can no longer drift; the next added command/ADR/scenario makes the stale marker fail lint until the number is corrected.
- The convention is idiomatic: it mirrors the existing `<!-- shared:<name> -->` marker pattern, and HTML comments keep the rendered docs clean.

### Negative
- A count is only guarded once wrapped in a marker; **un-marked count claims still drift undetected**. New count claims should be marked. The registry guard independently protects the command count regardless of markers.
- Adding a command now requires four registry edits (previously easy to forget). This is the intended cost; the alternative was undiscoverable commands.

### Neutral
- The guards run on every `lint-commands.sh` invocation (local pre-commit and CI). Cost is negligible (grep/awk over a few dozen files).

## Alternatives

### Alternative 1: regex-scan every number in prose
Scan all docs for `\d+ (commands|ADRs|...)` and compare to disk, no markers. Rejected: high false-positive rate (subset counts like "3 multi-repo aware", spelled-out numbers, numbers that legitimately are not disk counts) and false negatives (rewording). Markers are explicit and robust to rewording.

### Alternative 2: generate the docs from a manifest
Assemble the count-bearing and registry-bearing sections from a single source at build time. Rejected for the same reason ADR-0011 rejected a build step for shared blocks: the repo's design keeps `commands/*.md` and the docs inline and self-contained so tools (and reviewers) consume them directly without running tooling. The marker-plus-lint approach delivers the anti-drift guarantee while preserving inline files.

## References
- ADR-0011 (shared canonical blocks): the marker-and-lint anti-drift pattern this extends, and the "why not a build step" rationale
- The 2026-06-01 / 2026-06-02 doc-drift sweeps (commits 217ea17, 3679385) that motivated the guard
- `scripts/lint-commands.sh`: the implementation (Registry membership guard and Count-marker guard sections)

## Addendum (2026-06-02)

A third guard was added the same day, in the same spirit: **index-row membership**. Every `docs/adr/[0-9]*.md` file must have a row in `docs/adr/README.md`, and every `evals/scenarios/[0-9]*.md` file must have a row in `evals/README.md` (with the reverse check for orphan rows). This mirrors the command-registry guard for the two numbered-artifact indexes and catches the "ADR index stopped at 0024" / missing-scenario-row class the sweep found. It is a structural membership check (deterministic, no markers), reported on the lint `Indexes:` line; the `count:adrs` / `count:scenarios` markers still guard the numeric claim, while this guards the rows themselves.
