# Shared canonical blocks

This directory holds the canonical body of sections that are shared verbatim across multiple `commands/*.md` files. It exists so a change to a shared section only has to be made in one place, with `scripts/sync-shared-blocks.sh` propagating the change and `scripts/lint-commands.sh` failing on drift.

## Files

| File | What it is | Consumers |
|---|---|---|
| `mandatory-context-bootstrap.md` | The block under `Mandatory context bootstrap (before any output):` | <!-- count:shared-mandatory-context-bootstrap -->92<!-- /count --> commands; the rest (e.g. `task-init`, `task-close`) use command-specific bootstrap extensions instead of the marker |
| `standard-output-layout.md` | The 1-line body under `### Standard output layout (required)` | <!-- count:shared-standard-output-layout -->98<!-- /count --> commands |
| `artifact-changes-default.md` | The 1-line pointer to the spec's `## Global output contract`, which is where the APPLIED / PROPOSED / SKIP rules and the no-nest rule live | <!-- count:shared-artifact-changes-default -->89<!-- /count --> commands; the commands with their own artifact-changes rules opt out by not declaring the marker |
| `command-transcript-standard.md` | The 4-bullet body under `### Command transcript` (Balanced/Deep depth) | <!-- count:shared-command-transcript-standard -->92<!-- /count --> commands; commands with a command-specific 4th bullet opt out |
| `command-transcript-lean.md` | The 3-bullet body under `### Command transcript` (Lean depth) | `capture-observation` (<!-- count:shared-command-transcript-lean -->1<!-- /count --> command) |
| `handoff-body.md` | The fenced ending-format block under `### Handoff` | <!-- count:shared-handoff-body -->98<!-- /count --> commands |
| `projects-ignore.md` | The body under `### Task memory stays out of git`: the command that creates `projects/` writes a self-ignoring `projects/.gitignore` (ADR-0223) | <!-- count:shared-projects-ignore -->2<!-- /count --> commands: task-init, project-bootstrap |
| `xml-review-scaffold.md` | The optional labeled instructions/context/constraints scaffold under `### Review prompt scaffold (optional)` (W-21) | <!-- count:shared-xml-review-scaffold -->3<!-- /count --> commands: review-hard, repo-consistency-sweep, verify-against-rubric |

Each consumer count is a `count:shared-<block>` marker, the number of command files (flat and folder-shaped) that declare `<!-- shared:<block> -->`. `scripts/reconcile-counts.sh` sets it from the tree and `scripts/lint-commands.sh` fails when one is stale, so the column cannot fall behind the way it did when it was typed by hand.

## Marker convention

Each command file declares which canonical block it uses by placing an HTML comment marker on its own line, immediately after the section header. Example inside a command:

```markdown
### Standard output layout (required)
<!-- shared:standard-output-layout -->
Produce the command output using this structure (English only):

### Artifact changes
<!-- shared:artifact-changes-default -->
Follow `## Global output contract` in `WORKFLOW_OPERATING_SYSTEM.md` for `APPLIED` / `PROPOSED` / `SKIP` rules. Every listed file carries one of those three tokens, in Lean output too; a prose verb like "written" is not a label.

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
| Flat | `commands/<name>.md` | <!-- count:commands-flat -->89<!-- /count --> commands (no migration planned) |
| Folder-shaped | `commands/<name>/SKILL.md` | K.8 personas (`templates/PERSONA_SKILL.template.md` is the starting point); also valid for any command that ships sidecar assets (rubrics, example traces, MCP refs) |

The three discovery scripts (`build-agent-skills.sh`, `lint-commands.sh`, `sync-shared-blocks.sh`) handle both layouts. The canonical name is the basename without `.md` for flat, the parent directory name for folder-shaped. Shared-block markers in folder-shaped `SKILL.md` files are propagated by `sync-shared-blocks.sh` identically to flat. The `_shared/` directory itself is skipped by all three scripts so its canonical-block files are not treated as commands.

## Why not use a build step

A more aggressive design would assemble each `commands/<name>.md` from sources at build time. We do not do that here because:
- Cursor and Claude Code consume command files directly from the repo via `scripts/sync-workflow-slash-commands.sh`. Inline self-contained command files are required for those pools to work without a build step.
- Inline files are also faster to read for reviewers and for LLMs that traverse the repo without running tooling.

The marker plus lint plus codemod combination delivers the same anti-drift guarantee while preserving inline self-contained command files.
