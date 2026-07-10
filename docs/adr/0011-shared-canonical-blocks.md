# ADR-0011: Shared canonical blocks

- **Status**: Accepted
- **Date**: 2026-05-09
- **Tags**: shared-blocks, dry, drift-detection, canonical-source

## Context

Many sections of `commands/<name>.md` files are identical across all 35 commands by design:

- The `### Standard output layout (required)` block (every command produces the same artifact-changes / transcript / handoff structure).
- The `### Handoff` body (the adaptive ending format with `Run now:` / `Mode:` / `Work complexity:` / `Reason:` / optional `Resume context:`).
- The `### Artifact changes` default rule (`PROPOSED` / `APPLIED` / `SKIP` mode policy).
- The `### Command transcript` brevity rules (max lines per category).
- The `Mandatory context bootstrap:` reading list (the WOS sections every command reads first).

When the workflow had ~10 commands and these blocks were copy-pasted, drift was annoying but tolerable. As the catalog grew (10 → 26 → 33 → 35), three failure modes became significant:

1. **Drift accumulates silently**. Edits to one command's `### Handoff` block (e.g., adding a new line to the canonical Handoff template) had to be replicated by hand across every other command. Inevitably, some commands lagged. The lint could not detect which version was canonical because every file was authoritative for its own copy.
2. **Refactor cost scaled with command count**. Changing the canonical Handoff format from one shape to another required N edits, where N was the command count at that moment. The refactor was discouraged just by friction.
3. **Reading the contract was harder, not easier**. A reviewer trying to understand "what does the Handoff block look like?" had to read several command files to confirm they all said the same thing, because there was no single source of truth.

The workflow needed a primitive that captured "this block is the same everywhere" and made the sameness mechanically enforceable.

## Decision

The workflow adopts a **canonical block + marker + sync** pattern:

1. **Canonical content lives in `commands/_shared/<name>.md`**. Each shared block is a single file with the canonical body. There is exactly one source of truth per block.
2. **Each command file declares an HTML-comment marker** (`<!-- shared:<name> -->`) at the start of the section that should carry the canonical content. The marker is invisible in rendered markdown but mechanically detectable.
3. **`scripts/sync-shared-blocks.sh` propagates** canonical content from `commands/_shared/<name>.md` into every command file that declares the corresponding marker. The script is idempotent: re-running on a clean repo produces no diff.
4. **`scripts/lint-commands.sh` detects drift**. Any command file whose post-marker body does not match the canonical block fails the lint. Drift is a hard failure, not a warning; commits cannot land with shared-block drift in the repo.

The shared blocks shipped in v0.1.x are seven files under `commands/_shared/`:

- `standard-output-layout.md` (the required artifact-changes / transcript / handoff structure).
- `artifact-changes-default.md` (the `PROPOSED` / `APPLIED` / `SKIP` mode policy).
- `command-transcript-standard.md` (max-line transcript brevity for normal commands).
- `command-transcript-lean.md` (lean variant for high-frequency commands like `capture-observation`).
- `handoff-body.md` (the canonical fenced Handoff format).
- `mandatory-context-bootstrap.md` (the WOS sections every command reads first).

Adding a new shared block requires:
- A new file under `commands/_shared/<name>.md`.
- An update to `scripts/lint-commands.sh` `shared_end_pattern` function (to tell the parser where the block body ends in command files, since that varies by block).
- Marker insertions in every command that should carry it.

## Consequences

### Positive

- **Single source of truth per block**. Editing the canonical Handoff format means editing one file. The sync script propagates; the lint enforces.
- **Drift is mechanically caught**. A reviewer landing a PR sees the lint result; no command file can silently fall behind the canonical block.
- **Refactors scale cleanly**. Changing the canonical block shape (e.g., adding a `Work complexity:` line to the Handoff fenced block) requires editing one file and running one script.
- **Per-block evolution is independent**. The transcript brevity rule can be tightened without touching the Handoff format; each canonical file has its own lifecycle.
- **Variants are explicit**. The `command-transcript-standard.md` vs `command-transcript-lean.md` split is encoded as two canonicals with two markers; commands declare which one they use. No ad-hoc "make this transcript shorter" judgment in command files.

### Negative

- **One more concept to learn**. New contributors editing a command file see HTML-comment markers and have to internalize what they mean. The marker is non-rendering but visually present in the source.
- **Shared blocks must be edited centrally**. A user who wants to deviate from the canonical Handoff for one command cannot just edit the command file; the lint will revert the deviation. The right path is to argue the canonical change applies everywhere, or split a new variant block.
- **Adding a new block has tooling cost**. The lint's `shared_end_pattern` function has to know where the block body ends in command files. Each new block adds a small amount of script complexity.

### Neutral

- The HTML-comment marker pattern is borrowed from documentation-generation tools and from include-style markdown processors. It is not a standard but is widely used. Markdown renderers ignore the marker; agents reading the file can act on it; humans skim past it.

## Alternatives considered

### Alternative 1: Hand-keep the blocks in sync

- Document the canonical block in WOS or in a contributor guide; rely on careful editing.
- Rejected: drift accumulates inevitably as the catalog grows; this is exactly what motivated the ADR.

### Alternative 2: Generated command files from a templating system

- Each command file is generated from a template plus a per-command overlay; canonical blocks live in the template.
- Rejected: the canonical command files become opaque (you read the generated file, not the source); editing becomes a build-step rather than a direct edit; the workflow's preference for direct-readable markdown is sacrificed.

### Alternative 3: Include syntax (e.g., `{% include "handoff-body.md" %}`)

- Use a markdown include processor to inline the shared block at render time.
- Rejected: requires a build step (the rendered markdown is what tools see, not the source); the source becomes harder to read in raw form; introduces a tooling dependency for a problem markdown can solve directly.

### Alternative 4: Symlinks instead of sync

- Link `commands/<name>.md` sections to `commands/_shared/<name>.md` via a filesystem mechanism.
- Rejected: markdown does not support partial-file symlinks; whole-file symlinks would lose the per-command surrounding content.

## References

- `commands/_shared/` (the canonical blocks; current count: seven files).
- `commands/_shared/README.md` (block-by-block table with which command uses which).
- `scripts/sync-shared-blocks.sh` (the propagation script; idempotent).
- `scripts/lint-commands.sh` (drift detection; `shared_end_pattern` function maps each block to where the body ends in command files).
- Any `commands/<name>.md` (search for `<!-- shared:` to see markers in context).

## Notes

The shared-block system shipped before the Agent Skills migration (P11). When P11 added frontmatter to every command, the pattern was retained: the frontmatter is per-command (each command's `description` and `metadata` are unique), but the body sections that should be uniform continued to use the marker-and-sync pattern.

The "drift is a hard failure" stance is deliberate. Earlier WOS iterations had soft warnings for shared-block drift; in practice, soft warnings were ignored and drift accumulated. Promoting drift to a lint failure (commit-blocking) made the rule self-enforcing.

Future blocks: if a new normative paragraph is added to every command (e.g., a privacy-or-security disclosure block in a future regulated-context release), it would be added as `commands/_shared/<new-name>.md` and propagated via the same pattern.

> Correction (2026-06-01): the body above says "seven files" but the list immediately below it enumerates six, and six `.md` blocks shipped in v0.1.x (the as-authored "seven" was a miscount; no block was later removed). Per the ADR immutability convention this is recorded as a dated footnote rather than a body edit. The canonical current count and per-block consumer table live in `commands/_shared/README.md`.
