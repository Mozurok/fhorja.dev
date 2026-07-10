# ADR-0080: Portfolio board: a generated HTML projection with the runs-feed v1 contract

- **Status**: Accepted
- **Date**: 2026-07-04
- **Tags**: portfolio-board, html-projection, visibility, runs-feed, outcome-telemetry, measurement-only, additive

## Context

WOS visibility lived entirely inside the active terminal session: the portfolio board, initiative view, and outcome summaries are text output of `scripts/portfolio-review.sh`, and nothing showed a human the cross-project state in a browser. The 2026-07-03 market-parity initiative named this gap as deliverable 3 (a generated static HTML board), and the `background-autonomous-run` sub-task declared the board as its progress surface, which made the board's data contract a cross-task interface that had to land first.

Two HTML-projection precedents already existed and defined the house pattern: `scripts/build-activity-timeline.py` (ADR-0049) and `scripts/build-knowledge-view.py` (ADR-0055): standalone python3 stdlib generators, one self-contained offline HTML file, render-never-mutate, `--stdout` and `--verbose`, gitignored output, each declaring itself "modeled on" the previous. A third fact bounded the design: `commands/portfolio-review.md` promises "this command is strictly read-only; it never writes any task's memory", so a board mode on the command would silently break its contract.

## Decision

Locked as D-1..D-4 of task `2026-07-03_html-dashboard`:

1. **Standalone generator plus a documented pointer (D-1).** The board is `scripts/build-portfolio-board.py`, the third link in the generator chain, and `commands/portfolio-review.md` carries only a body-only documented pointer to it. No command-contract change, no new command.
2. **One classifier, exposed via `--json` (D-2).** `scripts/portfolio-review.sh` gained a `--json` mode emitting the classified active-task rows (`{class, idle_days, project, task, next_command}`) from the SAME loop that renders the text board; the generator consumes it. The done-unclosed, blocked, my-move, stale, in-flight taxonomy exists in exactly one place.
3. **Output at `projects/BOARD.html` (D-3).** Gitignored by location, fully regenerated per invoke, self-contained (inline CSS, no external assets, `html.escape` on every interpolation).
4. **Runs-feed contract v1 (D-4).** The board reads `.wos/runs/*.json`; an absent or empty directory renders an explicit no-running-runs state. The `background-autonomous-run` task writes the feed and extends it additively (the `templates/OUTCOMES.schema.md` versioning pattern). The v1 contract:

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| schema_version | integer | yes | Contract version; this ADR defines version 1. |
| run_id | string | yes | The run's identifier, stable across updates. |
| task | string | yes | Task folder basename the run is executing. |
| state | string | yes | Producer-defined state label (for example queued, executing, escalated, finishing). |
| started_ts | string | yes | ISO 8601 with milliseconds and Z; when the run started. |
| last_update_ts | string | yes | ISO 8601 with milliseconds and Z; the producer's heartbeat. |
| current_step | string | yes | Short human-readable description of what the run is doing now. |

One file per run under `.wos/runs/`, rewritten in place by the producer as the run progresses; the producer removes the file when the run ends (a terminal outcome belongs in the outcome ledger, ADR-0079, not in the runs feed). Readers ignore unknown fields; breaking changes bump `schema_version`.

The board's four sections and their sources: active tasks (`--json`), initiative rows (`projects/*/INITIATIVE_INDEX.md`, best-effort with visible warnings), outcome summaries (`projects/*/OUTCOMES.jsonl` per ADR-0079, latest-event-wins), and running background runs (the contract above). Every optional source degrades visibly and exits 0; the board is measurement and visibility only and gates nothing.

## Consequences

### Positive

- Cross-project state is visible outside the terminal for the maintainer and beta testers, with zero server processes and zero new dependencies.
- The classification taxonomy cannot drift between the text board and the HTML board (one classifier, one emitter).
- The `background-autonomous-run` task plans against a published, versioned interface instead of inventing one, in the dependency direction both tasks declared at fleet decomposition.
- The generator chain now has three consistent links, reinforcing the projection pattern rather than fragmenting it.

### Negative

- The board is pull-based: a human regenerates and refreshes; there is no live push (accepted: no server is a hard initiative constraint).
- INITIATIVE_INDEX.md parsing stays best-effort over a free-text table; rows that defeat the parser appear as warnings, not data.
- One more standalone script to know about; discoverability rests on the command-doc pointer.

### Neutral

- Visual styling is deliberately minimal; polish is additive later without contract changes.
- The runs feed is empty until the sibling ships its writer; the board renders the designed empty state meanwhile.

## Alternatives considered

### Alternative 1: a --board mode on portfolio-review

- One entry point for all board views.
- Rejected: the command's contract says it never writes; a mode that writes HTML breaks that silently or forces a contract amendment for no functional gain over a sibling script.

### Alternative 2: a net-new command owning the board

- First-class routing and catalog discoverability.
- Rejected: full command blast radius (four registries, catalog, counts, eval) for what is one generator script; the precedent generators are not commands either.

### Alternative 3: reimplement the classifier in python

- No bash edit; the generator reads TASK_STATE files directly.
- Rejected: two copies of the five-class taxonomy to keep identical forever; the analysis named this the sharpest technical risk.

### Alternative 4: defer the runs-feed contract to the background-autonomous-run task

- Avoids speculative lock-in.
- Rejected: inverts the dependency both tasks declared (the sibling names this board as its progress surface), and would force a second pass over the board.

## References

- `scripts/build-portfolio-board.py` (the generator; four sections, degradation paths).
- `scripts/portfolio-review.sh` (`--json` emitter; the single classifier).
- `commands/portfolio-review.md` (the body-only pointer; contract unchanged).
- D-1..D-4 of `projects/bmazurok__my-work-tasks/active/2026-07-03_html-dashboard/DECISIONS.md` (locked 2026-07-04).
- ADR-0049, ADR-0055 (the generator precedents), ADR-0057 (the command-embedded HTML projection variant), ADR-0079 (the outcome ledger this board summarizes).
- `evals/scenarios/91-portfolio-board.md` (the regression scenario).

## Notes

The board was validated against the real repository at build time (113 active tasks, the market-parity initiative index, the first real outcome record) plus a runs-feed fixture proving the section renders and the empty state returns. The maintainer's browser look at the generated file is the honest final check for a human surface; the eval scenario protects the contract, not the aesthetics.
