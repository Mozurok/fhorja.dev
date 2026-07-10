# ADR-0071: LEARNINGS retrieval via an optional Tags field and a recency-plus-overlap ranker

- **Status**: Accepted
- **Date**: 2026-07-01
- **Tags**: memory, learnings, reflexion, retrieval, task-init, adr-0017-amendment, read-only, ripgrep, additive

## Context

ADR-0017 gave the WOS a reflexion-style memory: producer commands (`slice-closure`, `post-review-pivot`, `incident-triage`, `harvest-session-learnings`) write anchored lessons to a task's `LEARNINGS.md`, and `task-init` reads prior LEARNINGS to seed a new task so it starts aware of past failed approaches. That is the intended loop.

The consume side was underspecified. `task-init` told the model to "match on tags, anchors, or topic" and surface a capped block, but there was no `Tags:` field to match on (the entry shape had none) and no mechanism to rank entries. In practice the retrieval step was a vague model instruction with nothing concrete to score against, so relevant prior lessons were captured but not reliably surfaced. This is the same captured-but-not-consumed failure the deliverable-coverage work (ADR-0056) targeted, here on the memory path.

## Decision

Make the retrieval path real with two small, additive pieces. This ADR **amends ADR-0017 by reference**; it does not edit ADR-0017.

1. Add an optional `Tags:` bullet to the `LEARNINGS.md` entry shape (`templates/LEARNINGS.md`): comma-separated keywords for retrieval, for example `Tags: api-jobs, path-alias, tsx`. Tags is optional, never a disqualifying bullet: an entry with no Tags line is still valid, it is just harder to retrieve. The four producer commands each gain a one-line instruction to emit the optional `Tags:` line when they write a lesson.

2. Add `scripts/rank-learnings.sh`, a read-only helper that scans a project's `LEARNINGS.md` files (or a single file), scores each entry by recency (parsed from the `## YYYY-MM-DD` header) plus tag and keyword overlap (the `Tags:` line and the Tried / Failed because / Next time bullets), and prints the top N (default 5) as a markdown block. `task-init` invokes it at the ADR-0017 consume step and drops the capped block inline into its handoff.

The ranker uses recency plus overlap only. There is no vector store and there are no embeddings: it is plain grep and bash arithmetic, matching the ripgrep-based, no-embedding posture already set for `code-context-map` (ADR-0057). It is advisory and always exits 0, mirroring `scripts/memory-lint.sh` (ADR-0053): an entry with no `Tags:` line is scored as low-relevance (body overlap only, no tag bonus), never a crash. It reads only; it never writes a `LEARNINGS.md`.

## Consequences

- The ADR-0017 consume side now has something concrete to match on and a deterministic ranker to surface it, closing the captured-but-not-consumed gap on the memory path.
- Tags being optional keeps the change backward compatible: every existing entry stays valid, and existing producers keep working without change until they adopt the one-line Tags instruction.
- No new dependency and no runtime component. The ranker is a repeatable, out-of-band helper (usable in CI or by hand) exactly like `memory-lint.sh`, and the recency score is reproducible via the `RANK_LEARNINGS_TODAY` env override since date is deterministic.
- This ADR is additive. It does not supersede ADR-0017; it makes its consume side executable. It also does not change the append-only, never-prune invariant on `LEARNINGS.md` (ADR-0017 item 6): the ranker only reads.

## References

- `templates/LEARNINGS.md` (the entry shape that gains the optional `Tags:` bullet).
- `scripts/rank-learnings.sh` (the recency-plus-overlap ranker).
- `commands/task-init.md` (the ADR-0017 consume step that invokes the ranker).
- `commands/slice-closure.md`, `commands/post-review-pivot.md`, `commands/harvest-session-learnings.md`, `commands/incident-triage.md` (the producers that emit the optional Tags line).
- ADR-0017 (the reflexion-style learnings loop this ADR amends by reference).
- ADR-0053 (`memory-lint.sh`, the read-only advisory helper whose conventions the ranker follows).
