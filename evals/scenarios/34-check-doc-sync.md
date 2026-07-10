# Eval Scenario 34: scripts/check-doc-sync.sh

## Scope

Verifies that `scripts/check-doc-sync.sh` correctly detects whether curated documentation references (command names, ADR IDs, wos topic references) map to real artifacts on disk. The script is the runtime guard against doc drift introduced by the doc-sync-validator proposal.

Targets the canonical curated doc set:
- `packages/wos-engine/internal/docs/FAQ.md`
- `packages/wos-engine/internal/docs/MIGRATION.md`
- `packages/wos-engine/internal/docs/adr/README.md`
- `packages/wos-engine/internal/wos/*.md` (curated topic files)
- `README.md` at repo root (if it references commands)

## Inputs

- A working tree of the Fhorja engine repo.
- Either:
  - (A) clean state -- every referenced command exists under `packages/wos-engine/internal/commands/`, every `ADR-####` reference resolves to a file under `packages/wos-engine/internal/docs/adr/`, every wos topic reference resolves to a `.md` file under `packages/wos-engine/internal/wos/`.
  - (B) deliberately broken state -- one or more invalid references injected for the negative test.

## Setup

1. Snapshot current working tree (`git stash -u` or a temp branch) before running negative cases.
2. For the positive case: run on a clean checkout with no local edits to curated docs.
3. For the negative case: inject one broken reference, for example:
   - Add the line `See the bogus-command command for details.` to `README.md`.
   - Add `Refer to ADR-9999 for rationale.` to `packages/wos-engine/internal/docs/FAQ.md`.
   - Add `See wos/nonexistent-topic.md.` to `packages/wos-engine/internal/docs/MIGRATION.md`.

## Steps

1. Run `bash scripts/check-doc-sync.sh` from repo root with the clean tree.
2. Capture exit code and stdout/stderr.
3. Inject a single broken reference (one of the three forms above).
4. Re-run `bash scripts/check-doc-sync.sh`.
5. Capture exit code and stdout/stderr.
6. Restore the working tree (`git checkout -- <files>` or `git stash pop`).

## Pass criteria

1. Clean-state run exits with code `0`.
2. Clean-state stdout contains a single summary line of the form `doc-sync: N refs verified, 0 broken` where `N` matches the number of references actually scanned (non-zero).
3. Broken-state run exits with code `1`.
4. Broken-state stdout contains at least one line identifying the broken reference, the source file path, and the line number, for example:
   `BROKEN: README.md:42 -- command 'bogus-command' not found under packages/wos-engine/internal/commands/`
5. Broken-state stdout still includes the summary line, with `broken` count >= 1, for example:
   `doc-sync: 187 refs verified, 1 broken`
6. The script does not modify any files (verify with `git status --porcelain` showing only the injected edit, nothing more).
7. The script completes in under 10 seconds on a typical laptop (no network calls, no LLM calls).
8. Re-running after restoring the tree returns to exit `0` and the original verified count, confirming the broken state was the sole cause.

## Failure modes

- Script exits `0` on the broken-state run -- false negative, the validator is not actually checking the reference class that was broken.
- Script exits `1` on the clean-state run -- false positive, the regex or path resolution is too strict and is flagging legitimate references.
- Broken-state output lacks file path or line number, making the break un-actionable for the author who has to fix it.
- Script mutates the working tree (rewrites docs, creates temp files in tracked paths) instead of running read-only.

## Notes

Anchor doc: `docs/proposals/doc-sync-validator.md` (proposal that introduced this script and its expected reference classes -- commands, ADRs, wos topics).

This scenario should be re-run whenever:
- A new reference class is added to the validator (e.g. bug-class refs, template refs).
- The curated doc set under `packages/wos-engine/internal/` is restructured.
- A new ADR is added or an existing ADR is renumbered.

Negative-case injection should rotate across all three reference classes over time (command ref, ADR ref, wos topic ref) so each branch of the validator gets exercised.
