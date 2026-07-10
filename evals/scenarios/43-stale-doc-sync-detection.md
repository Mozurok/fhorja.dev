# Eval scenario 43: Stale doc-sync reference detection via check-doc-sync.sh

- **Tags**: bug-class, stale-doc-sync-reference, check-doc-sync, ADR-0029, drift-detection
- **Last reviewed**: 2026-06-05
- **Status**: active

## Goal

Validates the `stale-doc-sync-reference` bug-class detection path: `scripts/check-doc-sync.sh` must reliably distinguish a curated doc that references **real** commands and ADRs from one that references **non-existent** commands or ADRs, and must exit non-zero with a precise, file:line-anchored error message in the failing cases.

This exercises:

- The `wos/bug-classes/stale-doc-sync-reference.md` failure pattern (curated docs drifting out of sync with the canonical command and ADR sets).
- The detection script contract defined in ADR-0029 (deterministic exit codes, machine-parseable output, no false positives on backticked prose).
- The "verified reference" accounting so legitimate backtick command mentions in `CLAUDE.md` and similar curated docs do not get flagged.

## Setup

Run from the repository root of `my_work_tasks`. Assumes `scripts/check-doc-sync.sh` is executable and the canonical command set lives under `commands/` and the canonical ADR set under `docs/adr/`. Each sub-scenario below operates on a controlled fixture state of `CLAUDE.md` and `docs/FAQ.md`; revert between runs.

## Sub-scenario A: legitimate command reference passes

### Input state

`CLAUDE.md` contains the line:

```text
Use the `extract-foundations-from-screens` command after design handoff lands.
```

and `commands/extract-foundations-from-screens.md` exists.

### Command

```text
scripts/check-doc-sync.sh
```

### Expected outcome

- Exit code: `0`.
- Output includes a verified-references summary line such as `verified command refs: N` where `N >= 1`.
- `extract-foundations-from-screens` is counted in the verified bucket, not the broken bucket.
- No `BROKEN` lines are emitted.

## Sub-scenario B: bogus command reference fails

### Input state

`CLAUDE.md` contains the line:

```text
Then run `bogus-command-name` to finish the flow.
```

and **no** `commands/bogus-command-name.md` file exists. <!-- lint:skip -->

### Command

```text
scripts/check-doc-sync.sh
```

### Expected outcome

- Exit code: `1`.
- Output contains a line of the form:
  `BROKEN command ref 'bogus-command-name' in CLAUDE.md:<line>`
  where `<line>` is the actual 1-based line number of the offending backtick reference.
- The summary tallies at least 1 broken command reference.
- The script does not crash, does not require interactive input, and does not modify any file.

## Sub-scenario C: bogus ADR reference fails

### Input state

`docs/FAQ.md` contains a line such as:

```text
See ADR-9999 for the rationale on doc-sync enforcement.
```

and no `docs/adr/0029-*` style file for `9999` exists (the canonical ADR set tops out well below 9999).

### Command

```text
scripts/check-doc-sync.sh
```

### Expected outcome

- Exit code: `1`.
- Output contains a line of the form:
  `BROKEN ADR ref 'ADR-9999' in docs/FAQ.md:<line>`
  with the actual line number.
- The script still scans `CLAUDE.md` and any other curated docs in the same run; ADR and command checks do not short-circuit one another.

## Pass criteria

1. **Sub-scenario A exits 0**: the legitimate `extract-foundations-from-screens` backtick reference in `CLAUDE.md` does not trip the script.
2. **Verified accounting**: sub-scenario A's output explicitly attributes that reference to the verified bucket (numeric tally or per-ref line), proving the script is actually resolving against `commands/`.
3. **Sub-scenario B exits 1**: a single bogus command reference is enough to fail the run.
4. **Sub-scenario B message is anchored**: the broken-command line contains the literal token `bogus-command-name`, the literal path `CLAUDE.md`, and a real line number -- not a placeholder.
5. **Sub-scenario C exits 1**: a single bogus ADR reference is enough to fail the run.
6. **Sub-scenario C message is anchored**: the broken-ADR line contains the literal token `ADR-9999`, the literal path `docs/FAQ.md`, and a real line number.
7. **No false positives across runs**: when both bogus references are reverted, re-running the script returns exit 0 with zero `BROKEN` lines.
8. **Read-only**: across all three sub-scenarios, the script never writes to any tracked file (verifiable via `git status` being unchanged except for the deliberate fixture edits).

## Failure modes to watch

- **Silent pass on bogus command**: script exits 0 in sub-scenario B because backtick contents are treated as prose rather than command identifiers; this defeats the bug-class entirely.
- **Wrong line number**: broken-ref output reports `:0`, `:1`, or a hardcoded line; downstream sweeps cannot jump to the actual offense.
- **Path misattribution**: error message names the wrong file (e.g. blames `README.md` for a `CLAUDE.md` violation) because the script concatenates inputs before scanning.
- **ADR detection skipped when command check fires first**: short-circuiting after the first broken command means ADR-9999 in `docs/FAQ.md` is never reported in a single run, breaking the "scan everything, report everything" contract from ADR-0029.

## References

- `wos/bug-classes/stale-doc-sync-reference.md` -- the bug-class definition this scenario guards.
- `scripts/check-doc-sync.sh` -- the script under test.
- `docs/adr/0029-drift-guards-registry-and-count-markers.md` -- the ADR specifying exit codes, output shape, and scan coverage.
