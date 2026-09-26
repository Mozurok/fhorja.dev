# ADR-0173: One fan-out floor, and a check that keeps it one

- **Status**: Accepted; sets the floor the spec and the fleet commands share. Does not edit ADR-0039, whose number governs a different unit.
- **Tags**: fleet, fan-out, thresholds, consistency, structural-evals, adr-0039, adr-0042
- **Date**: 2026-08-30

## Context

Three numbers claimed to be the fan-out floor and none of them agreed.

The spec said five, in two places: "5 or more independent items of the same shape" under when to use a fleet, and "Fewer than 5 items" under when not to. Neither sentence cited a source, and nothing in the repository derives five from anything.

ADR-0039 said ten: "Below 10 agents per batch, the orchestration overhead dominates."

The commands said neither. Measured on disk 2026-08-29: `task-init-fleet`, `external-research-fleet` and `feature-library-scout-fleet` fan out at 3 or more; `verify-against-rubric-fleet` at 4; `atom-audit-fleet` and `screen-spec-fleet` at 6; `implement-fleet` at a wave of 2.

A reader trying to decide whether to dispatch had three answers and no way to pick. A reader writing a new fleet command had no floor at all, because the two written-down numbers were both above every command that actually existed.

One correction to the audit that produced this: there is no `N >= 1` threshold anywhere. The occurrence recorded as one is a section-presence rule, not a dispatch floor.

## Decision

The fan-out floor is 3. Per-command thresholds may be higher, never lower, and an exception below the floor is registered in `wos/workflow-patterns.md` rather than left in a command file for someone to find.

Three is derived, not picked. It is the mode of what the commands already declare, and it is the only value that leaves no command to rewrite: everything sits at the floor or above it, and `implement-fleet` at a wave of 2 becomes the single registered exception. That exception has a reason worth writing down: a worker's payload there is a whole slice, so dispatch overhead is negligible against it, unlike a fleet whose worker reads one file.

The spec's five had no source and is replaced.

ADR-0039's ten is not overruled, because it never governed this unit. It measures agents per invocation in a read-only documentary sweep, against a declared default of 15 to 25 agents. That is a different question from how many independent items justify a fleet at all. ADR-0039 is not edited; this ADR records the scope reading so the next reader does not have to redo it.

`check_fanout_floor_consistency` in `evals/scripts/structural-evals.py` enforces the shape rather than the prose. It reads the floor from `wos/workflow-patterns.md`, requires the spec to name the same number in both of its sentences, and fails when a fleet command declares a threshold below the floor without being in the exception register, or declares none at all.

## Consequences

### Positive

- A reader deciding whether to fan out gets one answer.
- A new fleet command has a floor to sit at, and a check that says so before review does.
- The next drift fails the build instead of accumulating for months across three files.

### Negative

- The check parses thresholds out of prose with a regex, so a command that phrases its threshold in a shape the regex does not know reads as having none and fails. That is the intended direction: an unparseable threshold is one nobody can verify either.
- Exceptions live in a register, which is one more place to keep honest. There is one entry.

### Neutral

- No command file changes. All seven already sit at or above 3.
- ADR-0039 and ADR-0042 keep their contracts. The wave-of-2 trigger of `implement-fleet` is untouched.

## Alternatives considered

### Alternative 1: keep 5 and raise the three commands that sit at 3

- Make the spec's number true by editing the commands under it.
- Rejected: five has no source, and the change would narrow three working commands to satisfy a sentence nobody derived.

### Alternative 2: adopt ADR-0039's 10

- Treat the empirical batch number as the floor.
- Rejected: it measures a different unit, and applying it would disable every fleet command in the repository.

### Alternative 3: delete the floor and let each command decide

- No global number; each fleet declares its own.
- Rejected: that is the state that produced the drift. Without a floor a new command has nothing to sit at, and the reader is back to three answers.

## References

- [ADR-0039](./0039-workflow-batch-dispatch-empirical.md): agents per invocation in a read-only sweep; a different unit, not edited here.
- [ADR-0042](./0042-waves-aware-routing-and-progress-visibility.md): the wave contract `implement-fleet` follows; untouched.
- `wos/workflow-patterns.md` `## Fan-out floor`: the floor and the exception register.
- `WORKFLOW_OPERATING_SYSTEM.md` `### When to use` and `### When NOT to use`: the two sentences the check keeps in agreement.

## Notes

The floor is about dispatch overhead against payload size, so it moves if worker payloads change shape, not on a calendar. Moving it means editing one sentence in the topic and letting the check find whatever no longer agrees.
