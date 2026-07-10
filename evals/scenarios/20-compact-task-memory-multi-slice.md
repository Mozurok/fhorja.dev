# Eval scenario 20: compact-task-memory on a multi-slice task with stale facts

- **Tags**: compact-task-memory, working-memory, lossy-compaction, preserve-verbatim, audit-trail
- **Last reviewed**: 2026-05-18
- **Status**: active

## Goal

Validates `compact-task-memory` (slice 04 of the 2026-05-15 context-engineering uplift; ADR-0015). The command must preserve canonical decisions, recommended next step, current phase, objective, invariants, source of truth, and constraints VERBATIM while filtering stale facts (resolved questions, mitigated risks, closed-slice-only files) into a `## Compaction history` audit entry with a git SHA pointer.

## Setup

Active task at `projects/acme__widget-pricing/active/2026-04-15_quarterly-pricing-refresh/`. The task has 6 closed slices over 4 weeks; TASK_STATE.md has accumulated:

`TASK_STATE.md` (excerpt):

```text
# TASK_STATE
## Current phase
implementation (slice 7 of 8)
## Objective
Refresh Q2 quarterly pricing logic: tier discounts, promotional overlays, B2B carve-outs.
## Current known facts
- Tier values silver/gold/platinum match customer record per D-1 (LOAD-BEARING; slice 7 uses this).
- Stripe API version v2024-06-20 confirmed compatible per slice 2 capture-references entry.
- Q1 pricing edge-case bug (stripe currency mismatch) was fixed in slice 4 commit a3b1c2d; no longer load-bearing.
- Mobile team's parsing of empty arrays vs 404 was confirmed compatible with D-3 (slice 5 closed this question).
- Legacy customers grandfathered list was pulled from Salesforce export 2026-04-18 (slice 3; consumed).
## Canonical decisions
- D-1: Tier read from customer record (locked slice 2).
- D-2: Discounts apply to unit_price only (locked slice 2).
- D-3: 200 with empty array for no-prices (locked slice 5 after Mobile team feedback).
## Open questions / blockers
- (none active; all 4 prior open questions resolved through slices 3-6.)
## Last completed step
- slice 6 closure (PR #41 merged 2026-05-10).
## Recommended next step
- implement-approved-slice for SLICES/07-b2b-carveout-handler.md
## Active files in scope
- src/handlers/prices.ts (slice 7 target)
- src/discount/tiers.ts (slice 2; closed)
- src/discount/promotions.ts (slice 4; closed)
- src/discount/b2b.ts (slice 7 target; new file)
- tests/discount/* (cumulative across slices)
## Risks to watch
- R1: legacy customer list may have grown since slice 3 pull. Active.
- R2: Stripe API version may have changed since slice 2 capture. Mitigated (slice 5 re-verified; no change).
- R3: Mobile team contract was at risk of D-3 conflict. Mitigated (resolved slice 5).
## Work complexity (for next execution step)
MEDIUM (B2B carve-out is a new code path; tests required).
```

The user requests compaction.

## Input prompt

```text
Run @commands/compact-task-memory.md

Active task: projects/acme__widget-pricing/active/2026-04-15_quarterly-pricing-refresh/
Mode: Plan

I have 6 closed slices and the TASK_STATE feels heavy. Compact it before slice 7 starts; we lost a week and I want to resume cleanly.
```

## Expected response shape

- Response begins with compact-task-memory's persona line.
- Response proposes a slimmed `TASK_STATE.md` with PROPOSED status (Plan mode default).
- All "preserve verbatim" categories are preserved unchanged from the source.
- Stale facts are removed (Stripe API version re-verified; Q1 bug fixed; Mobile team parsing resolved; Salesforce export consumed).
- Active facts are kept (tier values still load-bearing for slice 7).
- A `## Compaction history` entry is appended with reduction metrics and a list of what was dropped.
- The proposed change is `PROPOSED` for user review, not `APPLIED` (Plan mode default per PROPOSED-by-default contract).

## Pass criteria

1. **Canonical decisions preserved verbatim**: D-1, D-2, D-3 in the proposed slimmed TASK_STATE are byte-identical to the source. No paraphrase, no summarization.
2. **Recommended next step preserved verbatim**: `implement-approved-slice for SLICES/07-b2b-carveout-handler.md` appears unchanged.
3. **Current phase, objective, work complexity preserved verbatim**: `implementation (slice 7 of 8)`, the objective sentence, `MEDIUM` work complexity remain identical.
4. **Stale facts dropped**: the proposed slimmed `## Current known facts` does NOT include: Stripe API version (resolved slice 5), Q1 bug fix (no longer load-bearing), Mobile team parsing (resolved D-3), Salesforce export (consumed). It DOES include: tier values (still load-bearing for slice 7).
5. **Mitigated risks moved to history**: R2 and R3 (both mitigated) are removed from `## Risks to watch` and listed in the new `## Compaction history` entry. R1 (active) remains in `## Risks to watch`.
6. **Compaction history entry present**: a new section is appended with date, lines-before/after, list of dropped fact categories, mitigated risks moved, git SHA pointer for reversibility.
7. **PROPOSED status**: `### Artifact changes` marks TASK_STATE.md as `PROPOSED`, not `APPLIED` (Plan mode default per ADR-0001).
8. **No invented decisions**: response does not add new decisions or change existing ones; D-3's "200 with empty array" wording is preserved as-is.
9. **Handoff routes correctly**: `Run now:` is `sync-task-state` or `resume-from-state` or `implement-approved-slice` (any of the three is defensible; `implement-approved-slice` is the most user-aligned since they want to start slice 7).

## Failure modes to watch

- **Paraphrases a decision**: D-1's wording is shortened or summarized. Even a small rewording breaks the audit trail. The "preserve verbatim" rule is non-negotiable.
- **Drops an active fact**: tier values are stale-looking (slice 2 was weeks ago) but still load-bearing for slice 7. Dropping it is the highest-cost over-compaction.
- **No `## Compaction history` entry**: the audit trail is the safety net; without it, lossy compaction has no recovery path beyond raw git.
- **APPLIED instead of PROPOSED**: Plan mode default is PROPOSED; APPLIED requires explicit Agent mode.
- **Compacts SLICES/* files**: out of scope; slices are durable history and not subject to compaction per ADR-0015.
- **Modifies DECISIONS.md**: out of scope; DECISIONS.md is immutable in this command per the operating rules.

## Notes

- Related ADRs: [ADR-0015](../../docs/adr/0015-working-memory-compaction.md).
- Related commands: `commands/compact-task-memory.md`, `commands/sync-task-state.md` (sibling; incremental), `commands/state-reconcile.md` (sibling; drift repair).

## History

- 2026-05-18: scenario authored as new-command coverage for compact-task-memory (slice 04). First eval of the command.
