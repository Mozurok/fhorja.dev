# Shared canonical blocks

This directory holds the canonical body of sections that are shared verbatim across multiple `commands/*.md` files. It exists so a change to a shared section only has to be made in one place, with `scripts/sync-shared-blocks.sh` propagating the change and `scripts/lint-commands.sh` failing on drift.

## Files

| File | What it is | Consumers (verified at last edit) |
|---|---|---|
| `mandatory-context-bootstrap.md` | The block under `Mandatory context bootstrap (before any output):` | 48 commands; the rest (e.g. `task-init`, `task-close`) use command-specific bootstrap extensions instead of the marker |
| `standard-output-layout.md` | The 1-line body under `### Standard output layout (required)` | All 53 commands |
| `artifact-changes-default.md` | The 3-line generic body under `### Artifact changes` (includes the no-nest rule per ADR-0024) | 44 commands; the 9 commands with command-specific artifact-changes rules opt out by not declaring the marker |
| `command-transcript-standard.md` | The 4-bullet body under `### Command transcript` (Balanced/Deep depth) | 47 commands; commands with a command-specific 4th bullet opt out |
| `command-transcript-lean.md` | The 3-bullet body under `### Command transcript` (Lean depth) | `capture-observation` (1 command) |
| `handoff-body.md` | The fenced ending-format block under `### Handoff` | All 53 commands |
| `xml-review-scaffold.md` | The optional labeled instructions/context/constraints scaffold under `### Review prompt scaffold (optional)` (W-21) | 3 commands: review-hard, repo-consistency-sweep, verify-against-rubric |

Consumer counts are point-in-time at the last edit of this README. Verify current values with `for b in mandatory-context-bootstrap standard-output-layout artifact-changes-default handoff-body command-transcript-standard command-transcript-lean; do echo "$b: $(grep -l "shared:$b" ../*.md | wc -l)"; done`. `scripts/lint-commands.sh` reports the same numbers under its `Shared:` line.

## Marker convention

Each command file declares which canonical block it uses by placing an HTML comment marker on its own line, immediately after the section header. Example inside a command:

```markdown
### Standard output layout (required)
<!-- shared:standard-output-layout -->
Produce the command output using this structure (English only):

### Artifact changes
<!-- shared:artifact-changes-default -->
- List files in `my_work_tasks/` that would change, or `None`.
- For each file, mark `APPLIED` / `PROPOSED` / `SKIP` and follow the task-memory write policy in `WORKFLOW_OPERATING_SYSTEM.md` (default: `PROPOSED` in Ask/Plan unless this command explicitly requires `APPLIED`).
```

The lint reads each marker, looks up the corresponding `_shared/<name>.md`, and verifies that the section body (the lines from the marker to the next `### ` heading or the next plain-text section header) matches the canonical content byte-for-byte.

A section without a marker is treated as command-specific and is not validated against any canonical block. This is the explicit opt-out mechanism for legitimate variations.

## Workflows

### Editing a canonical block
1. Edit the relevant file under `commands/_shared/<name>.md`.
2. Run `./scripts/sync-shared-blocks.sh` to propagate the change to every command file that declares the corresponding marker.
3. Run `./scripts/lint-commands.sh` to confirm zero drift.
4. Commit the change to the canonical file plus the auto-propagated edits in commands.

### Editing a command-specific section
1. Edit the section body inside the command file directly.
2. Make sure no marker pointing at a canonical block sits above the section (or remove it if the section is now command-specific).
3. Run `./scripts/lint-commands.sh` to confirm validation behaves as expected.

### Adding a new canonical block
1. Add `commands/_shared/<new-name>.md` with the canonical body (no heading, no marker, body only).
2. Add `<!-- shared:<new-name> -->` markers in every command that should use it.
3. Update this README's table.
4. Run `./scripts/sync-shared-blocks.sh` and `./scripts/lint-commands.sh` to verify.

## Dual layout (K.3, 2026-06-04)

Commands live in two equally-valid layouts:

| Layout | Path | Used by |
|---|---|---|
| Flat | `commands/<name>.md` | All 62 existing commands (no migration planned) |
| Folder-shaped | `commands/<name>/SKILL.md` | K.8 personas (`templates/PERSONA_SKILL.template.md` is the starting point); also valid for any command that ships sidecar assets (rubrics, example traces, MCP refs) |

The three discovery scripts (`build-agent-skills.sh`, `lint-commands.sh`, `sync-shared-blocks.sh`) handle both layouts. The canonical name is the basename without `.md` for flat, the parent directory name for folder-shaped. Shared-block markers in folder-shaped `SKILL.md` files are propagated by `sync-shared-blocks.sh` identically to flat. The `_shared/` directory itself is skipped by all three scripts so its canonical-block files are not treated as commands.

## Why not use a build step

A more aggressive design would assemble each `commands/<name>.md` from sources at build time. We do not do that here because:
- Cursor and Claude Code consume command files directly from the repo via `scripts/sync-workflow-slash-commands.sh`. Inline self-contained command files are required for those pools to work without a build step.
- Inline files are also faster to read for reviewers and for LLMs that traverse the repo without running tooling.

The marker plus lint plus codemod combination delivers the same anti-drift guarantee while preserving inline self-contained command files.
