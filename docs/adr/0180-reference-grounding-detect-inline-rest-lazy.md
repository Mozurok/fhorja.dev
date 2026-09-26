# ADR-0180: Reference grounding keeps Detect inline and lazy-loads the rest

- **Status**: Accepted
- **Date**: 2026-08-30
- **Tags**: reference-grounding, lazy-load, adr-0116, skill-budget, execution-gate, shared-block

## Context

`commands/_shared/reference-grounding.md` was 8487 chars carried inline by four commands
(`implement-approved-slice`, `implement-fleet`, `implement-slice-complement`,
`api-runtime-verify`). Seven other commands carry a different block,
`reference-grounding-design` (ADR-0043 D-3), which marks instead of refusing and is untouched
here.

`.claude/skills/implement-approved-slice/SKILL.md` had reached 39996 of the 40000-char ADR-0116
ceiling, four characters of headroom, and `implement-fleet` sat at 2897. Measured 2026-08-30:
148 sentences over 60 chars in the first command's own body were compared pairwise and only two
pairs exceeded 0.72 similarity, both legitimate. There was no redundant text to reclaim, so the
next rule added to either command would have failed the build.

The repository had already answered the general question. `implement-approved-slice` line 97
replaces a 16604-char body with a 920-char pointer to
`wos/closure-floors.implement-approved-slice.md`, and closure floors are blocking gates. Whether a
gate may be lazy-loaded was settled; what was open was which part of this gate may move.

## Decision

The block splits by what the rules depend on, not by size.

Step 1, Detect, stays inline in every command that carries the block. It scans the slice's imports
and diff for external contracts, and its outcome is what decides whether anything else applies. A
detector behind a lazy load is a gate that never fires.

Rules 2 to 7 move to `wos/reference-grounding.md`: refuse when uncaptured, read and cite when
captured, design assets as contracts (ADR-0051), live-verify a security-critical or fully-gating
contract (ADR-0108), and the two claim-keyed tests (ADR-0109 D-9, ADR-0146). Every one of them
fires only on step 1's outcome.

The inline block becomes the gate header, step 1 verbatim, and a pointer. The pointer states that
the load is CONDITIONAL on step 1 and that a slice touching no external contract loads nothing. The
execution summary cites which rules were read and applied, the same G3 safeguard the closure-floors
pointer carries, so the lazy load cannot decay into a paraphrase.

The pointer's first draft explained the conditionality by contrasting it with the closure floors,
which do fire on every slice. `check_unconditional_load_declared` (ADR-0006) rejected it: the
contrast phrase sat on the same line as the topic name, so a line-scoped reader binds the two and
reads this load as unconditional. The guard was right, and the comparison came out.

The rule text is unchanged. Only where it is read changed.

Enforced by `commands/_shared/reference-grounding.md` plus `scripts/sync-shared-blocks.sh`, which
propagates the shortened block to the four carriers.

## Consequences

### Positive

- The inline block goes from 8487 to 1874 chars, freeing 6613 in each of the four carriers.
  `implement-approved-slice` goes from 4 chars of headroom to 6617 and `implement-fleet` from 2897
  to 9510.
- The two commands closest to the ceiling can take a rule again without a squeeze.
- One source: the rules live in one file rather than four inline copies.

### Negative

- A conditional load can be skipped by a model that decides step 1 found nothing when it did. The
  G3 citation requirement is the check on that, and it is the same exposure the platform runtime
  floors already carry.
- One more file to open on a slice that does touch an external contract.

### Neutral

- `reference-grounding-design` is a different block and is unchanged.
- The new topic is cited by commands and not by the spec's Minimum read map, which is the shape 10
  of the 54 topics already have, including the three closure-floors views.

## Alternatives considered

### Alternative 1: lazy-load the whole block including Detect

- Rejected. Detect is what decides whether the rest applies, so moving it makes the gate depend on
  a load that only its own outcome would justify.

### Alternative 2: move this command's own conditional floors instead

- Bootstrap tiers, session bootstrap reuse, the Express attended lock and the slice-note-first
  floor total 4559 chars, and behind one pointer would free about 3639 in one command.
- Rejected: it frees less, helps one command instead of four, and puts four unrelated subjects
  behind a single pointer, which is not what the closure-floors precedent does.

### Alternative 3: raise the ADR-0116 ceiling

- Rejected. ADR-0116 says the number comes down, never up. Raising it is reversing a decision
  rather than fixing a defect, and it makes every command cheaper to grow.

## References

- [ADR-0116](./0116-single-load-stage-size-budget.md): the 40000-char ceiling this relieves.
- [ADR-0043](./0043-reference-grounding-execution-gate.md): the gate itself. Its D-3 is the
  design-gate variant, a separate shared block, left untouched here.
- `wos/reference-grounding.md`: the lazy body.
- `commands/implement-approved-slice.md`: the closure-floors pointer whose form this copies.
