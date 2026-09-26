# Eval Scenario 34: scripts/check-doc-sync.sh

## Scope

Verifies that `scripts/check-doc-sync.sh` correctly detects whether curated documentation references (ADR IDs, wos topic references, spec headings, AGENTS.md section numbers, and command names) map to real artifacts on disk. The script is the runtime guard against doc drift, and the lint runs it as a FAIL-tier delegate.

Targets the scan set the script declares in its `SURFACES` list:
- `CLAUDE.md`, `AGENTS.md`, `README.md`, `ROADMAP.md`, `WORKFLOW_OPERATING_SYSTEM.md`
- `docs/FAQ.md`, `docs/MIGRATION.md`
- `commands/*.md` and `commands/_shared/*.md`
- `wos/*.md` (curated topic files)
- `templates/*.md`

## Inputs

- A working tree of the Fhorja repo.
- Either:
  - (A) clean state: every `ADR-####` reference resolves to a file under `docs/adr/`, every wos topic reference resolves to a `.md` file under `wos/`, and every backticked command name resolves under `commands/`.
  - (B) deliberately broken state: one or more invalid references injected for the negative test.

## Setup

1. Snapshot current working tree (a temp branch, or `git stash push -u -m <tag>`) before running negative cases.
2. For the positive case: run on a clean checkout with no local edits to curated docs.
3. For the negative case: inject one broken reference, for example:
   - Add `Refer to ADR-9999 for rationale.` to `docs/FAQ.md`.
   - Add `See wos/nonexistent-topic.md.` to `docs/MIGRATION.md`.
   - Add the line ``See the `bogus-command` command for details.`` to `README.md`. An unknown backticked token is only a warning, and only under `--strict`, because it could be a shell command or a code symbol rather than a broken command reference.

## Steps

1. Run `bash scripts/check-doc-sync.sh` from repo root with the clean tree.
2. Capture exit code and stdout/stderr.
3. Inject a single broken reference (one of the three forms above).
4. Re-run `bash scripts/check-doc-sync.sh`, and for the command-token form also `bash scripts/check-doc-sync.sh --strict`.
5. Capture exit code and stdout/stderr.
6. Restore the working tree (`git checkout -- <files>`, or apply the stash entry you created).

## Pass criteria

1. Clean-state run exits with code `0`.
2. Clean-state stdout ends with a single summary line of the form `doc-sync: N refs verified, 0 broken`, where `N` is non-zero.
3. A broken ADR or wos-topic reference makes the run exit with code `1`.
4. Broken-state stdout contains a line naming the reference class, the broken reference, the source file and the line number, for example:
   `doc-sync: BROKEN ADR ref 'ADR-9999' in docs/FAQ.md:42`
5. Broken-state stdout still ends with the summary line, with the `broken` count at 1 or more, for example:
   `doc-sync: 7330 refs verified, 1 broken, 0 warnings`
6. The injected `bogus-command` token leaves the default run at exit `0`; under `--strict` a `doc-sync: WARN` line names it with its file and line. The strict exit code does not isolate it: the clean tree already carries hundreds of strict warnings (shell commands and code symbols in backticks), so strict exits `1` either way.
7. The script does not modify any files (verify with `git status --porcelain` showing only the injected edit, nothing more).
8. The script completes in under 10 seconds on a typical laptop (no network calls, no LLM calls).
9. Re-running after restoring the tree returns to exit `0` and the original verified count, confirming the broken state was the sole cause.

## Failure modes

- Script exits `0` on a broken ADR or wos-topic reference: a false negative, because the validator is not actually checking the reference class that was broken.
- Script exits `1` on the clean-state run: a false positive, because the regex or path resolution is too strict and is flagging legitimate references.
- Broken-state output lacks file path or line number, making the break un-actionable for the author who has to fix it.
- Script mutates the working tree (rewrites docs, creates temp files in tracked paths) instead of running read-only.

## Notes

Anchor: `scripts/check-doc-sync.sh` itself. Its header comments record each widening of the scan set and each reference class it gained. The proposal that introduced it was deleted in 2026-09 once the script had replaced it; it had proposed a `lint-commands.sh` mode, a fourth check for new-command coverage in the FAQ and the migration guide that was never built, and paths from an old layout.

This scenario should be re-run whenever:
- A new reference class is added to the validator (e.g. bug-class refs, template refs).
- The `SURFACES` scan set is widened or narrowed.
- A new ADR is added or an existing ADR is renumbered.

Negative-case injection should rotate across the reference classes over time (ADR ref, wos topic ref, spec heading, AGENTS.md section, command token under `--strict`) so each branch of the validator gets exercised.
