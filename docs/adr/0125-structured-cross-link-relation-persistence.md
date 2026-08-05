# ADR-0125: Cross-link relations persist typed, and the reader scopes to the column

- **Status**: Accepted
- **Date**: 2026-08-04
- **Tags**: task-init-fleet, portfolio-review, initiative, dependency-dag, initiative-index, shell, completes-adr-0062, absorption-beads

## Context

`task-init-fleet` computes a typed cross-link relation for every sub-task pair. Its `worker_input_schema` declares `cross_links[].relation` as an enum of five values (`shares-contract`, `shares-data-model`, `blocks`, `blocked-by`, `cosmetic-sibling`), and Step 2 validates that those links form a DAG before any worker is dispatched. The type is therefore known, checked, and trustworthy at generation time.

Step 8 then threw it away. The `INITIATIVE_INDEX.md` row it built carried `<cross_links summary>`, a free-text cell, so the relation degraded to prose the moment it was persisted. A real row reads "consumed html-dashboard (runs feed) and outcome-telemetry (outcome record) as shipped interfaces".

`portfolio-review --initiative` (ADR-0062) then had to recover the blocking subset by regex. It matched `blocked-by[: ]+[a-z0-9_,. -]+` against the lowercased WHOLE ROW, which meant a `blocked-by` string appearing anywhere (an Objective describing a dependency that was considered and rejected, a Next-command cell) was read as a real graph edge. This is the same defect class ADR-0062's own follow-up note anticipated: "a follow-up could formalize a structured `blocked-by: slug1,slug2` convention in `task-init-fleet` for stricter parsing".

It is also the same defect class the 2026-07-06 Status-column masking bug already had, fixed then by a header-derived column parse and pinned by `scripts/tests/test-initiative-classifier.sh`. The Cross-links column simply never received the same treatment.

The occasion for fixing it now was a comparative read of an external project whose dependency model splits edges into a blocking set that gates ready-work and a non-blocking set that only annotates the graph. That read found Fhorja already had the distinction and was discarding it at the persistence boundary. The mechanism is Fhorja's own; nothing was imported.

## Decision

Two changes, one on each side of the boundary.

**Write side.** `task-init-fleet` Step 8 persists the relation instead of summarizing it. The Cross-links cell carries one labelled group per relation present, groups separated by `; `, slugs within a group separated by `,`:

```
blocked-by: 2026-01-01_alpha,2026-01-03_gamma; shares-contract: 2026-01-02_beta
```

A sub-task with no cross-links gets `none`. The `blocks` relation is normalized into the blocked-by direction on the row of the sub-task that IS blocked, so a reader never inverts an edge. The four non-blocking relations carry their own labels and are never read as dependencies.

**Read side.** `scripts/portfolio-review.sh` learns the Cross-links column index from the header row, alongside the Status, Objective, and Next-command indexes it already learns, and scopes the `blocked-by` match to that column. A table with no header row has no column to scope to and keeps the historical whole-row match.

The fallback is what makes this safe to ship without a migration: every row written before this decision holds prose, and the whole-row match still reads it. The structured form is a superset the old regex already matched, so the two formats coexist indefinitely.

## Consequences

- A `blocked-by` string in any non-Cross-links cell no longer produces a phantom dependency, so `portfolio-review --initiative` stops reporting a startable task as blocked.
- The non-blocking relations survive persistence for the first time. Nothing reads them yet; the point is that a future reader can, without re-deriving them from prose.
- No migration and no rewrite of existing rows. Old prose rows parse through the fallback; new rows parse through the column.
- Pinned by `scripts/tests/test-initiative-blocked-by-column.sh`, the sibling of the Status-column test, including the same red-proof affordance (pass an older `portfolio-review.sh` as the first argument and the test fails).
- A pre-existing latent defect surfaced while implementing this and is fixed in the same change: `initiative_summary` read the parser's TSV with `IFS=$'\t' read -r slug status bb ...`, and because tab is IFS whitespace, bash collapses consecutive tabs, so an EMPTY blocked-by field shifted the Objective into the `bb` variable. It was invisible while the whole-row match rarely produced an empty field, and column-scoping produces empty fields constantly, so the two are coupled: without this fix the column-scoped parse would have been defeated by the reader. The loop now splits on tab explicitly. The JSON emitter path was never affected (`awk -F'\t'` and Python `str.split` both keep empty fields).
- This ADR completes the follow-up ADR-0062 recorded rather than reversing anything in it. ADR-0062's best-effort framing still holds for headerless tables.
