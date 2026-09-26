# ADR-0224: Shipped helpers name what they did not scan

- **Status**: Accepted
- **Date**: 2026-09-23
- **Supersedes**: nothing. It extends ADR-0218 from `ingest-scan.py` to every helper the install payload ships, and adds eleven entries to the ADR-0214 shipping list.
- **Tags**: install-payload, workflow-root, d-3, shipped-scripts, integrity-floor, sha-scope, adr-0214, adr-0217, adr-0218, b31

## Context

Backlog B31 asks, for every script a command runs, whether it ships in the install payload or the
command names its absence. On 2026-09-22 four shipped. A measurement pass on 2026-09-23 ran each of
the rest as an installed copy, from outside this repository, against an empty target, the two tests
D-3 of the retro wave-1 task set and ADR-0214 adopted.

Most failed the second test the same way `ingest-scan.py` had: they read nothing and printed the
line a clean run prints, with exit 0.

- `scan-substrate-headers.sh` printed `substrate_header_drift_count: 0` for a folder with no
  substrate file. Its `--verbose` path died on a bad substitution whenever there was drift to show.
  Outside a git repository it exited 2, which once shipped would fail the integrity floor on every
  close in a task repository that is not a git repository.
- `verify-log-validator.py` printed `lines: 0` and OK for an empty log. Its `--task` mode looked for
  tasks beside its own file. And it had no notion of digest scope: the only substrate fallback an
  installed user gets, a whole-file digest marked `"sha_scope":"file"`
  (`commands/_shared/substrate-digest-fallback.md`), was recomputed as a section digest and reported
  as content-vs-log drift. The integrity floor runs it with `--check-deletes`, so every close that
  used the fallback would have failed.
- `emit-substrate-write.sh` created `<task-root>/.wos/` under any root it was given, so a wrong
  `--task-root` grew a stray log no validator reads.
- `check-live-markers.sh` printed `Live-markers: none` for a folder holding none of the three files
  it reads. `approve-plan` reads that as permission to continue.
- `check-plan-coverage.sh` and `portfolio-review.sh` located their data from their own path, so an
  installed copy read the docs directory. `portfolio-review.sh` is the script D-3 was written from.
- `plan-adherence.py` reported `VERDICT: CONFORMANT` for an empty folder.
- `memory-lint.sh`, given a folder that does not exist, said it had looked under `./projects` and
  printed `MEMORY-LINT: 0 finding(s)`.
- `secret-scan-gate.sh`, with no scanner on PATH, exited 0 with no output at all.

`rank-references.sh` passed both tests as it was.

## Decision

A helper that ships says so when it scanned nothing, and exits non-zero unless its exit is advisory by
a documented contract. Each defect above is fixed in the script, with a test that fails on the old
code. The eleven scripts then join `SHIPPED_SCRIPTS`, and every command that runs one resolves it
against the workflow root and names, in `### Command transcript`, the case where it is in neither the
clone nor the installed docs directory, rather than reading the absence as a pass.

The four substrate scripts ship as one unit: `verify-substrate-batch.sh` is the closure integrity floor
and runs the other two validators and the orphan scan from its own directory. Shipping the validators
without the emitter, or without the file-scope reading, would fail that floor on every installed close.
The install test allows a script to locate itself only to reach a sibling that ships beside it.

When `verify-substrate-batch.sh` is not installed, the closure records
`integrity: not checked (verify-substrate-batch not installed)`. That line is neither a pass nor a
waiver, so the floor holds as it does for a non-zero exit (`wos/closure-floors.md`).

Exit codes that changed:

| Script | Case | Was | Now |
| --- | --- | --- | --- |
| `scan-substrate-headers.sh` | no substrate file found | 0, count 0 | 2, `not scanned` |
| `scan-substrate-headers.sh` | task folder outside git | 2 | scanned, 0 |
| `scan-substrate-headers.sh` | `--verbose` with drift | 1 | 0 |
| `verify-log-validator.py` | log with no lines | 0, OK | 2, `NOT CHECKED` |
| `verify-log-validator.py` | file-scope line matching the file, under `--check-deletes` | 1 | 0 |
| `emit-substrate-write.sh` | `emit`, `batch`, `apply` with no `TASK_STATE.md` in the root | 0, stray log | 1, nothing written |
| `check-live-markers.sh` | none of the three files present | 0, `none` | 2, `not scanned` |
| `check-plan-coverage.sh` | one folder, no plan or no `## Slices` | 0 | 2 (0 under `--advisory`) |
| `check-plan-coverage.sh` | `--all`, nothing measured | 0 | 2 (0 under `--advisory`) |
| `plan-adherence.py` | no `IMPLEMENTATION_PLAN.md` | 0, CONFORMANT | 2, no verdict |
| `secret-scan-gate.sh` | no gitleaks, trufflehog or rg | 0, silent | 3, `NOT scanned` |
| `portfolio-review.sh` | no `projects/` in the working directory | 0, empty board | 2, refused |

`memory-lint.sh` keeps exit 0, its advisory contract; its trailer says `not scanned` instead of a count.
`scan-substrate-headers.sh` keeps exit 0 when it finds drift: ADR-0034 makes a header-less section
valid, and the integrity floor states it keys on exit codes so that the drift count cannot fire it.

## Consequences

### Positive

- The integrity floor, the plan gates and the secret gate run on an install, and a run that could not
  check says so.
- The digest fallback no longer fails the floor it was written to keep working.
- Every caller in the tree was checked. The lint passes `--root` and `--advisory`, which still exits 0.
  `build-portfolio-board.py` and the audit scripts already run `portfolio-review.sh` from the
  repository root. A real task folder always holds `TASK_STATE.md`, so the batch wrapper's new
  `headers=2` fires only on a folder that is not a task, which is correct.

### Negative

- `verify-substrate-batch.sh` still reports `log=0` for a task with no log. A task predating K.1 is
  valid by ADR-0034, and the wrapper prints that it found none; turning that into a failure would fail
  every legacy close. The line is named, not counted.
- The command sentences assert the instruction, not the obedience. Only a run shows a model writing
  `not checked` instead of a pass.
- A file-scope digest cannot say which section moved. That reduction was declared when the fallback
  was written, and the validator now reads it as declared rather than as drift.

### Neutral

- The install test probes each shipped script with its own argument shape, and treats a clean line on
  an empty target as a failure for each script's own clean shape, not only `OK` and `VERDICT: CLEAN`.

## Alternatives considered

### Alternative 1: ship the validators and keep the emitter out

- Rejected on measurement: the wrapper then fails every installed close on the stray-log and
  section-digest cases, and the one fallback an install has is the file-scope digest.

### Alternative 2: make header drift exit non-zero

- Rejected. ADR-0034 made header-less sections valid, and the integrity floor keys on exit codes so the
  informational count cannot fire it. Changing that is a separate decision about the protocol, not a
  shipping question.

### Alternative 3: leave the no-scanner case of the secret gate at exit 0 with a warning line

- Rejected: `code-context-map` reads the exit code to decide what the map says. A distinct code lets it
  write the map, as the no-install posture wants, while stating the source was not scanned.

## References

- [ADR-0214](./0214-wire-the-memory-consume-path.md): the D-3 tests and the first shipped script.
- [ADR-0217](./0217-the-outcome-ledger-is-written-not-computed.md): the second.
- [ADR-0218](./0218-the-ingest-scan-ships-and-names-what-it-did-not-scan.md): the rule this extends.
- [ADR-0034](./0034-substrate-peers-and-worker-contract.md): header-less sections are valid.
- [ADR-0110](./0110-substrate-write-apply-subcommand.md): the batch wrapper.
- `scripts/tests/test-verify-log-scope.sh`, `scripts/tests/test-scan-substrate-headers.sh`,
  `scripts/tests/test-shipped-helpers-absence.sh`, and the D-3 loop in
  `scripts/tests/test-install-payload.sh`.
