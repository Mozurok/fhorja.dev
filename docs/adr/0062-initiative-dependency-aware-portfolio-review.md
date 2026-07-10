# ADR-0062: Dependency-aware initiative view in portfolio-review (--initiative)

- **Status**: Accepted
- **Date**: 2026-06-27
- **Tags**: portfolio-review, initiative, dependency-dag, next-task, shell, read-only, ecosystem-adoption, additive

## Context

The 2026-06-26 ecosystem research (round 1 rank 9, round 2 rank 4, round 4 planning cluster) flagged that Taskmaster's `next` walks the dependency graph to recommend the highest-priority unblocked task, while the WOS has `INITIATIVE_INDEX.md` (written by `task-init-fleet`) as flat markdown whose `cross-links` column records `blocked-by` relations, but nothing resolves which sub-task is startable next across a multi-task initiative. `portfolio-review` is the read-only cross-task board; `what-next` routes within one task. Neither answers "which sub-task am I allowed to start next across this initiative".

## Decision

Add an opt-in `--initiative` mode to `scripts/portfolio-review.sh` (surfaced as the `--initiative` input on the `portfolio-review` command). It parses each `projects/*/INITIATIVE_INDEX.md` row for slug, status, and any `blocked-by:` cross-link, builds the blocked-by DAG deterministically in the shell (not the LLM), and reports each sub-task as done / ready / blocked, plus one `start now` recommendation (the first unblocked not-done task) and two warning classes: dangling refs (a `blocked-by` slug not present in the index) and a possible-cycle/deadlock warning (work remains but nothing is unblocked).

Parsing is best-effort: the cross-link column is free text, so the helper warns rather than fails on a row it cannot parse, and never invents a dependency. The mode is read-only like the board and never writes `INITIATIVE_INDEX.md` (the orchestrator is its sole writer per ADR-0040). With no index present it prints a graceful no-op pointing at `task-init-fleet`.

## Consequences

- Multi-task initiatives gain a deterministic "what is startable next" answer without an LLM pass, complementing `what-next` (single task) and the `portfolio-review` board (all tasks).
- The deterministic DAG lives in the shell, so the routing is reproducible and cheap; verified against ready+dangling, cycle/deadlock, and no-index fixtures.
- Because the cross-link column is free text, parsing is best-effort; a follow-up could formalize a structured `blocked-by: slug1,slug2` convention in `task-init-fleet` for stricter parsing (noted in the round-4 residual questions).
- This ADR is additive; it does not change the default board behavior and adds no new command.
