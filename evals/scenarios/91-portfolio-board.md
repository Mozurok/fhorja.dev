# Eval scenario 91: the portfolio board renders four sections with graceful degradation, render-never-mutate

- **Tags**: ADR-0080, portfolio-board, build-portfolio-board, html-projection, runs-feed, json-emitter, measurement-only
- **Last reviewed**: 2026-07-04
- **Status**: active

## Goal

Validates **ADR-0080** (the portfolio board): `scripts/build-portfolio-board.py` renders `projects/BOARD.html` with four sections (running background runs, active tasks, initiatives, outcomes), consumes the active-task rows from `scripts/portfolio-review.sh --json` (one classifier, D-2), degrades visibly on every absent or malformed optional source, and never mutates anything but its own output file.

This exercises:

- One classifier: the active-task section comes from the `--json` emitter, never from a reimplemented taxonomy; row count matches the text board.
- Runs-feed contract (D-4): a `.wos/runs/*.json` file renders task, state, and current_step; an absent or empty directory renders the explicit no-running-runs state.
- Degradation: no OUTCOMES.jsonl renders "no outcome records yet"; an unparseable INITIATIVE_INDEX row becomes a visible warning, never a crash; a failed `--json` call renders a warning section with exit 0.
- Render-never-mutate: the only write is `projects/BOARD.html`; `--stdout` writes nothing at all.
- Measurement only: no wording anywhere gates or blocks a workflow step.

## Setup

A repo with at least one active task, one `INITIATIVE_INDEX.md` containing one well-formed row and one deliberately malformed row, one project with a two-line OUTCOMES.jsonl (an outcome plus a later revert for the same task), and no `.wos/runs/` directory. A second pass adds `.wos/runs/fixture.json` per the D-4 v1 contract.

## Input prompt

```text
Generate the portfolio board with python3 scripts/build-portfolio-board.py --verbose, then add a .wos/runs/fixture.json (schema_version 1, state "executing", current_step "slice 02 in worktree") and regenerate. Show me what changed.
```

## Expected response shape

- First run: BOARD.html written with all four section headers; the active-task count matches `portfolio-review.sh --json` row count; the malformed initiative row appears as a visible warning; the outcomes section shows the reverted task via latest-event-wins; the runs section shows the explicit empty state.
- Second run: the runs section renders the fixture's task, state badge, and current_step.
- No file other than projects/BOARD.html is written in either run; the response never proposes a server, a daemon, or an auto-refresh process.
- Response ends with a `### Handoff` block routing forward.

## Pass criteria

1. All four sections render, and the active-task rows come from the `--json` emitter (stated or evidenced), not from a second classifier.
2. The runs empty state renders when `.wos/runs/` is absent, and the fixture run renders task, state, and current_step when present.
3. The reverted task's effective status is reverted (latest event wins) in the outcomes section.
4. The malformed initiative row degrades to a visible warning; the generator exits 0 on every degradation path.
5. `--stdout` produces the page on stdout and writes no file.
6. All interpolated task-memory text is HTML-escaped (no raw markup injection from task names or objectives).

## Failure modes to watch

- **Second classifier**: the generator parses TASK_STATE files and re-derives the five classes itself, reintroducing the taxonomy-drift risk D-2 eliminated.
- **Crash on absence**: a missing OUTCOMES.jsonl, runs dir, or initiative index raises instead of rendering the empty state.
- **Mutation**: the generator writes anything besides projects/BOARD.html (or writes INITIATIVE_INDEX.md, which is orchestrator-owned).
- **Server drift**: proposing a live server, websocket, or daemon for refresh (the no-server constraint is hard).
- **Contract drift**: reading runs-feed fields not in the v1 contract as required, or failing on unknown extra fields (additive extension must keep working).

## Notes

- Related ADRs: [ADR-0080](../../docs/adr/0080-portfolio-board.md), [ADR-0079](../../docs/adr/0079-outcome-ledger.md) (the ledger the outcomes section reads), [ADR-0049](../../docs/adr/0049-activity-timeline-html-view.md), [ADR-0055](../../docs/adr/0055-knowledge-layer-visual-organization.md) (the generator precedents).
- Related files: `scripts/build-portfolio-board.py`, `scripts/portfolio-review.sh`, `commands/portfolio-review.md`, `templates/OUTCOMES.schema.md`.
- Known issues: none yet (first run pending).

## History
