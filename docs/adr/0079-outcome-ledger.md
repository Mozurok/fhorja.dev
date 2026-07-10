# ADR-0079: Outcome ledger: per-project outcome records written at task closure

- **Status**: Accepted
- **Date**: 2026-07-03
- **Tags**: outcome-telemetry, observability, measurement-only, append-only, task-close, portfolio-review, jsonl, additive

## Context

The WOS records process exhaustively (task memory, decisions, audit log) but records no outcomes: when a task archives, its merge verdict, cycle time, and review-triage results vanish into `archive/` where nothing reads them. `portfolio-review` shows only the current state of active tasks. The 2026-07-03 market analysis named outcome telemetry as one of the gaps against commercial and big-tech tooling, and the market-parity initiative brief (framed the same day via `problem-framing`) carried it as named deliverable 4: a file-based per-project outcome ledger plus `portfolio-review` consumption.

Constraints already locked upstream bounded the design: measurement only (enterprise governance was evaluated and dropped during the framing), file-based with no server, and the vendor-neutral no-API doctrine of ADR-0020 (no GitHub calls to detect merges or reverts). Three facts found at impact-analysis shaped it further: `task-close`'s done-conditions gate already records the merge signal as a human verdict with evidence (condition 4); per-phase timestamps already exist on disk in the `wos:write ts=` headers (ADR-0034); and `scripts/portfolio-review.sh` walks only `active/`, so a closed task's record must live at project level.

## Decision

A per-project, append-only outcome ledger, locked as D-1..D-3 of task `2026-07-03_outcome-telemetry`:

1. **The ledger** is `projects/<client>__<project>/OUTCOMES.jsonl`: one JSON object per line, append-only, single writer (`task-close` at gate decision archive, producing the line via `scripts/compute-task-outcome.py` with the condition-4 verdict). The append NEVER blocks archiving; a failure is reported and the archive proceeds. The file is gitignored by location (`projects/` is ignored wholesale).
2. **Revert is an append-only correction event** (`event=revert`), recorded when a human observes it, via the helper's `--revert` mode. Original records never mutate; readers resolve a task's effective merge status latest-event-wins.
3. **Five phase boundaries** (init, planning, implementation, delivery-prep, close) are derived at close from the existing `wos:write ts=` headers by mapping writer owners to phases. Tasks that predate ADR-0034 degrade to null fields and never fail a reader. `slice-closure` gains no write point.
4. **The read contract** is `templates/OUTCOMES.schema.md` (schema_version 1, additive-versioned). Consumers: `scripts/portfolio-review.sh --outcomes` (per-project summary: closed counts, effective statuses, median cycle days, per-phase medians) and any generated board surface.
5. **Optional enrichments**: sweep applied-vs-declined counts from `REVIEW_PREFERENCES.md` and deliverable done-vs-de-scoped counts from the ADR-0056 ledger, both null-degrading when absent.

## Consequences

### Positive

- Outcome signal exists per project with zero added ceremony during the task: the only write is one line at close, produced from data the workflow already emits.
- Append-only with correction events keeps the ledger trustworthy and trivially consumable (the property a mutable status field would have destroyed).
- The sibling initiative task building the HTML board plans against a stable, versioned schema doc instead of a guessed shape.
- Legacy-safe: pre-ADR-0034 tasks produce records with null phases rather than breaking the board.

### Negative

- Revert capture depends on human observation and can lag or be missed entirely; the ledger records what the maintainer knows, not ground truth from a forge API (accepted cost of the ADR-0020 doctrine).
- The owner-to-phase mapping is a heuristic over writer names; unusual command sequences can blur a boundary.
- Sweep attribution is a substring match on the task slug (REVIEW_PREFERENCES.md has no task column) and can overcount incidental mentions.

### Neutral

- The ledger is local project data, not shared telemetry; any future aggregate or team view consumes the same JSONL without a format change.
- One outcome line per task is the norm, but multiple are tolerated by the read rules (latest wins), which keeps re-closure after a reopened task representable.

## Alternatives considered

### Alternative 1: per-task outcome record aggregated at read time

- One `OUTCOME.md` per task folder; `portfolio-review` walks `archive/` and aggregates.
- Rejected: the read side pays an unbounded `archive/` walk on every invocation, and every consumer becomes an N-file reader; the brief's own wording ("per-project records") already pointed at one file per project.

### Alternative 2: derive everything at read time, no new write

- No ledger; readers parse headers, final TASK_STATE, and REVIEW_PREFERENCES per task on demand.
- Rejected: merge and sweep signals are not reliably parseable from prose across heterogeneous legacy tasks, and every board render re-pays the derivation cost.

### Alternative 3: mutable status field for revert

- One row per task; a revert edits the row in place.
- Rejected: editing archived data destroys the append-only property that makes the ledger trustworthy, the same reason ADRs and LEARNINGS are immutable here.

### Alternative 4: forge API integration for merge and revert detection

- Call the GitHub (or other forge) API at close and on a schedule to detect merges and reverts automatically.
- Rejected: violates the ADR-0020 vendor-neutral no-API doctrine; the done-conditions gate already captures the merge verdict as evidence-cited human input.

## References

- `templates/OUTCOMES.schema.md` (the versioned read contract).
- `scripts/compute-task-outcome.py` (the producer; outcome and revert modes, null-degrading).
- `commands/task-close.md` (the single write point at gate decision archive; never blocks archiving).
- `scripts/portfolio-review.sh` and `commands/portfolio-review.md` (the `--outcomes` read side).
- D-1..D-3 of `projects/bmazurok__my-work-tasks/active/2026-07-03_outcome-telemetry/DECISIONS.md` (locked 2026-07-03).
- ADR-0020 (no-API observability doctrine), ADR-0034 (the ts headers the phases derive from), ADR-0049 (generated reporting precedent), ADR-0056 (closure-ledger precedent).
- `evals/scenarios/90-outcome-ledger.md` (the regression scenario).

## Notes

Born from the market-parity initiative's first fleet-executed task. One operational lesson from the build is recorded for future fleet plans: editing any command's frontmatter desyncs the generated `docs/command-catalog.*`, so the catalog is a coupling artifact (ADR-0041 Rule 2) owned by the orchestrator at merge time, never by a parallel worker.
