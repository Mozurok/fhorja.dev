# Eval scenario 31: scan-substrate-orphans detects bullets emitted between H2 sections

- **Tags**: scan-substrate-orphans, substrate-bullet-orphan, adr-0038, post-batch-invariant, section-routing
- **Last reviewed**: 2026-06-05
- **Status**: active

## Goal

Validates `scripts/scan-substrate-orphans.py`, the post-batch invariant checker for ADR-0038 Rule 3 (every substrate bullet must live under a canonical H2 section). The script reads a TASK_STATE.md, scans every list-item bullet, and flags any bullet whose nearest preceding ancestor is not a recognized H2 substrate section. This is the executable backstop for the `substrate-bullet-orphan` bug class: bullets that get appended between sections (after section A closes, before section B opens) are invisible to downstream Fhorja commands and silently drop work.

Two sub-scenarios cover the clean and dirty cases.

## Setup

### Clean fixture

`TASK_STATE.fixtures/clean.md` contains canonical sections with bullets correctly nested:

```text
# TASK_STATE
## Current phase
- implementation (slice 3 of 5)
## Canonical decisions
- D-1: Tier read from customer record.
- D-2: Discounts apply to unit_price only.
## Open questions / blockers
- (none active)
## Recommended next step
- implement-approved-slice for SLICES/03-promotions.md
```

Every bullet sits directly under an H2 header.

### Dirty fixture

`TASK_STATE.fixtures/dirty.md` has two orphan bullets emitted between sections (between `## Canonical decisions` closing and `## Open questions / blockers` opening, and again after the last H2):

```text
# TASK_STATE
## Current phase
- implementation (slice 3 of 5)
## Canonical decisions
- D-1: Tier read from customer record.
- captured-observation: stripe key rotation upcoming   <-- ORPHAN (line 7)
## Open questions / blockers
- (none active)
## Recommended next step
- implement-approved-slice for SLICES/03-promotions.md
- followup: confirm B2B carve-out scope with sales     <-- ORPHAN (line 13)
```

Both stray bullets are valid Markdown list items, but neither is scoped to a recognized H2 section per ADR-0038.

## Input prompt (clean case)

```text
$ python3 scripts/scan-substrate-orphans.py TASK_STATE.fixtures/clean.md
```

## Input prompt (dirty case)

```text
$ python3 scripts/scan-substrate-orphans.py TASK_STATE.fixtures/dirty.md
```

## Expected response shape (clean case)

- Exit code `0`.
- Stdout reports `0 orphans` (or equivalent unambiguous wording, e.g. `OK: 0 orphan bullets found`).
- No stderr output.
- Suitable to wire into a pre-commit hook or CI step without noise.

## Expected response shape (dirty case)

- Exit code non-zero (`1` is conventional).
- Stdout (or stderr) lists each orphan bullet with: the file path, the 1-indexed line number, the offending bullet text (truncated if long), and the nearest preceding H2 header (or `<no H2 yet>` if the orphan precedes the first H2).
- At minimum the two orphans at lines 7 and 13 are surfaced; the script does not stop at the first orphan.
- A final summary line states the total orphan count (e.g. `2 orphan bullets found`).

## Pass criteria

1. **Clean exits 0**: running against the clean fixture exits `0` with a `0 orphans` confirmation; no false positives on correctly-nested bullets.
2. **Dirty exits non-zero**: running against the dirty fixture exits with a non-zero code so CI and hooks can treat it as a failure signal.
3. **Each orphan reported**: both the line 7 and line 13 orphans are listed; the scanner does not short-circuit after the first hit.
4. **Line numbers correct**: reported line numbers match the actual 1-indexed source location, so a human can jump directly to the offending bullet.
5. **Nearest H2 cited**: each orphan report names the nearest preceding H2 (e.g. `## Canonical decisions` for the line 7 orphan, `## Recommended next step` for line 13) so the reviewer can see where the bullet drifted from.
6. **Total count summary**: a single summary line states the orphan count, so CI logs are scannable without parsing per-orphan lines.
7. **No false positives on nested bullets**: bullets that are sub-items of a parent bullet (indented list children) under a valid H2 are NOT reported as orphans; only top-level list items outside any H2 trigger the check.
8. **Stable output**: re-running on the same fixture produces byte-identical stdout, so the script can be diffed in CI without flake.

## Failure modes to watch

- **False clean pass on dirty fixture**: scanner exits `0` despite orphans present (most dangerous; the invariant silently fails).
- **First-orphan short-circuit**: scanner reports only the line 7 orphan and misses line 13, letting one of two real defects ship.
- **Wrong line numbers**: off-by-one from 0-indexing vs 1-indexing, breaking the jump-to-line affordance.
- **Treats nested list children as orphans**: indented sub-bullets under a valid H2 get flagged, producing review-noise that trains operators to ignore the script.

## Notes

- Related ADR: [ADR-0038 Rule 3](../../docs/adr/0038-workflow-tool-as-parallel-orchestration-primitive.md) -- every substrate bullet must live under a canonical H2 section; bullets emitted between sections are defects, not stylistic choices.
- Related bug class: [`wos/bug-classes/substrate-bullet-orphan.md`](../../wos/bug-classes/substrate-bullet-orphan.md) -- documents the failure pattern this script defends against.
- This script is the executable post-batch invariant for the Fhorja substrate discipline; it complements the human reviewer rule but does not replace it.

## History

- 2026-06-05: scenario authored alongside scripts/scan-substrate-orphans.py to lock in the ADR-0038 Rule 3 executable check.
