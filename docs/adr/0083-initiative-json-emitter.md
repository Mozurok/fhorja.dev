# ADR-0083: The initiative rows get one parse point: an additive --initiative --json emitter

- **Status**: Accepted
- **Date**: 2026-07-06
- **Tags**: portfolio-board, initiative, json-emitter, single-source, amends-adr-0080, additive

## Context

INITIATIVE_INDEX.md was parsed by two independent implementations: the bash view (`portfolio-review.sh --initiative`) and the board generator's own python parser (`build-portfolio-board.py load_initiatives`). Commit 12435d2 fixed a first-keyword status-masking defect in the bash parser (a status keyword in an objective cell won over the Status column), and the first real autonomous run's dogfood immediately exposed the TWIN of that defect in the python parser: the board rendered the same row wrong next to the fixed text view. One table with two parsers is a standing drift class; ADR-0080 D-2 had already solved exactly this for the active-task taxonomy by making the board consume the `--json` emitter instead of re-implementing the classifier.

## Decision

Extend the single-source pattern to initiatives (D-1 of task `2026-07-06_board-initiative-parser-twin-fix`):

1. `portfolio-review.sh` gains an ADDITIVE emitter mode, `--initiative --json` (either flag order), emitting one JSON array of `{project, task, status, objective, next_command}`. The bare `--json` output is byte-compatible with its pre-change shape (proven by same-instant diff against the HEAD version).
2. The extraction is one function, `parse_initiative_rows()`, shared by the human view and the emitter: header-derived Status, Objective, and Next-command column indexes, with the historical whole-row match kept verbatim as the headerless fallback. The human view's downstream logic (ready, blocked, dependency warnings) is unchanged.
3. `build-portfolio-board.py` sources its Initiatives section from the emitter (the same subprocess pattern as its Active-tasks section) and its own table parser is retired; emitter absence or failure degrades to a visible warning with exit 0.
4. The regression test (`scripts/tests/test-initiative-classifier.sh`) asserts both surfaces against one fixture: the human view's classifications and the emitter's per-row status, including the masking case.

## Consequences

### Positive

- The drift class dies structurally: there is no second parser left to disagree.
- The board's Initiatives section now agrees with the text view by construction, and the masking defect cannot return unnoticed (the fixture pins it on both surfaces).

### Negative

- The board's initiative rendering now depends on the emitter being present and healthy; the visible-degradation path covers the failure mode, at the cost of one subprocess call per render.

### Neutral

- The emitter grows the ADR-0080 contract additively; the bare `--json` consumer surface is untouched.
- The TSV seam inside the parse function assumes no literal tabs inside table cells (a best-effort parser's stated limit).

## Alternatives considered

### Alternative 1: mirror the column-scoped parse in python plus a shared fixture

- Smaller diff; no contract growth.
- Rejected: keeps two parsers alive with a test as the only guard; the third copy of the bug remains possible, and the repo already owns the better pattern (D-2).

### Alternative 2: patch ADR-0080 in place

- Rejected: ADR immutability is a feature; contract growth gets its own record.

## References

- `scripts/portfolio-review.sh` (`parse_initiative_rows`, the `initiative-json` mode), `scripts/build-portfolio-board.py` (`load_initiatives` as consumer), `scripts/tests/test-initiative-classifier.sh` (both-surface regression).
- D-1 of `projects/bmazurok__my-work-tasks/active/2026-07-06_board-initiative-parser-twin-fix/DECISIONS.md` (locked 2026-07-06).
- ADR-0080 (the board and the D-2 single-source precedent this amends additively), ADR-0062 (the --initiative view), commit 12435d2 (the bash-side fix and the regression test this extends).

## Notes

Found by dogfood: the first real autonomous run (ADR-0081) rendered its live feed on the board next to a wrongly-classified initiative row, which is what surfaced the twin. The LEARNINGS entry of the sibling task names the general smell: when fixing a parser defect, grep for other consumers of the same artifact before scoping the slice.
