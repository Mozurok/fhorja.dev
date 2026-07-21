# ADR-0111: Compaction-proof Quick reanchor block in TASK_STATE

- **Status**: Accepted
- **Date**: 2026-07-21
- **Tags**: task-state, compaction, resume, sync-task-state, decision-interview, extends-adr-0023, v3-wave3

## Context

Context compaction is a normal event in long sessions, and TASK_STATE.md is the artifact a session reanchors from. The bv3 cross-model dogfood (2026-07-20/21) measured 7 compactions in one session; after each one the agent ran re-anchoring greps for decision IDs (D-2, D-3, D-9, D-11) across four artifacts before resuming the slice. The information needed to reanchor is small (active decisions, current slice, phase, next step) but was scattered mid-file and mid-plan, so every compaction paid a multi-file search.

The adversarially reviewed v3 spec bound two corrections: ownership of the block must be SHARED (a sole-owner design would leave the block stale on the most common path, a decision locked directly by decision-interview), and truncation must respect clause boundaries so EARS-form decisions are not decapitated to their WHEN-trigger.

## Decision

1. `## Quick reanchor` becomes the FIRST H2 of the TASK_STATE template (the structure grows from 19 to 20 sections): Active decisions (one clause-bounded line per non-superseded D-N, cap 10 with an explicit overflow line pointing at DECISIONS.md, `none locked yet` when empty), current slice (from IMPLEMENTATION_PLAN.md), phase, next step.
2. Ownership is shared: `sync-task-state` rebuilds the block mechanically on every sync; `decision-interview` co-writes the Active decisions line in the same turn it locks a D-N in persist mode. The ownership matrix carries the row.
3. `resume-from-state` reads the block first but trusts it only after a freshness cross-check: the highest D-N cited in the block must equal the highest locked D-N in DECISIONS.md; on mismatch or absence it falls back to the full re-read.
4. Truncation is by clause boundary (comma, semicolon), never a fixed word count.
5. Backfill follows the Work complexity precedent: a legacy task gains the block on its first sync, no mass migration.
6. Free riders in the same change: D-N prefixes on `## Canonical decisions` bullets, and the sync-task-state must-contain list corrected to the 20-section template order (adding the two rows that had drifted out: Requested deliverables, Recommended pipeline).

## Consequences

- A post-compaction resume reads one block instead of grepping four artifacts; the cross-check bounds the staleness risk to one detectable condition.
- Maintenance cost is one section write per sync; with the ADR-0110 apply path that is one call.
- Accepted residuals: the block can lag by at most one execution between syncs, and the cap can hide a D-N behind the overflow line (which never fails silently).
