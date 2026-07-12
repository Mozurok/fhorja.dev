# ADR-0100: Bounded deferral at the commit-evidence floor (a waiver covers only discardable work)

- **Status**: Accepted
- **Date**: 2026-07-12
- **Tags**: closure-enforcement, commit-evidence, slice-closure, task-close, bounded-deferral, refines-adr-0084, extends-adr-0098, dogfood-driven, theme-dogfood-wave

## Context

The ADR-0084 commit-evidence floor at `slice-closure` and `task-close` accepted either a commit reference or ANY explicit recorded waiver of committing, and eval scenario 95 pinned that reading. The 2026-07-11 theme dogfood wave (ten parallel, unattended vertical-slice builds, task `2026-07-11_theme-dogfood-wave2-triage`) had git operations forbidden by ground rules; all five paths that reached closure found the same gap independently: their real, working, test-passing product code was neither committable (forbidden) nor a throwaway, yet the floor's letter allowed closing it with a one-line waiver, and offered no sanctioned vocabulary for the honest middle state ("real work pending a human commit"). ADR-0098 had already drawn exactly this bounded-vs-permanent line for the sibling feel-verdict and experience-verdict floors, but the commit floor never received it.

## Decision

Mirror the ADR-0098 shape onto the commit-evidence floor at both homes (`commands/slice-closure.md`, `commands/task-close.md`): a committing-waiver covers ONLY genuinely discardable work (a deliberate throwaway, a spike whose value was the learning). Real work awaiting a human commit, including an unattended session where git is unavailable or forbidden, is a BOUNDED DEFERRAL recorded as `deferred: pending human commit (<one-line context>)`; it keeps the slice or task OPEN for the next human session and is the correct, honest outcome, not a failure. At `task-close` one escape remains: the user may explicitly authorize an archive-with-waiver that names the preserved uncommitted work (the audit-purpose dogfood-folder case, per the godot-wave D-3 precedent); silence or a bare waiver line on real work never satisfies the floor. Eval scenario 95 is updated in the same change to pin the new reading.

## Consequences

### Positive

- An unattended or autonomous run can no longer close real uncommitted work by writing a waiver line; it stalls honestly at the bounded deferral, which is what all five dogfood paths already did by judgment against the floor's letter.
- The three human-gated closure floors (feel-verdict, experience-verdict, commit-evidence) now share one doctrine (ADR-0098's bounded-vs-permanent line) instead of two of three.

### Negative

- Fully unattended runs touching real deliverables always end open pending a human commit. Intended: the human merge/commit gate is the WOS's core premise (ADR-0044).

### Neutral

- The genuine throwaway waiver is unchanged at its existing ceremony. No new command.

## References

- Refines ADR-0084 (closure commit gate); extends ADR-0098 (bounded-vs-permanent doctrine).
- Dogfood evidence: 5 of 10 unattended paths, 2026-07-11 theme dogfood wave (`projects/bmazurok__my-work-tasks/active/2026-07-11_theme-dogfood-wave2-triage/IMPACT_ANALYSIS.md`, TF-34).
- Eval scenario 95 (closure commit gate) updated with the bounded-deferral criterion.
