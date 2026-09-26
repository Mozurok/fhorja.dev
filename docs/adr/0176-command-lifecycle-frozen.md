# ADR-0176: A command can be frozen, and freezing is not deprecating

- **Status**: Accepted; the mechanism only. Which commands are frozen is a separate decision.
- **Date**: 2026-08-30
- **Tags**: lifecycle, commands, frozen, catalog, maturity-ladder, frontmatter

## Context

The catalog has four states a command can be in, and none of them is "this works and we are done with it".

A command is active, or it is being extended in a capability wave, or it is being cut, or nobody has looked at it in a year. The fourth is not a state, it is the absence of one, and it is where a working command goes to be quietly re-litigated every time someone audits the catalog.

The cost shows up as repeated work. A surface that shipped, ran, and has had no demand since comes back in every review as a question: extend it, cut it, or leave it? Answering "leave it" costs the same as answering it the first time, because nothing recorded that the answer was already given.

The 2026-08-26 planning notes had already reached four such verdicts and written them into a table: the `scripts/autonomy/` cluster, the `knowledge/` auto-load of ADR-0054, hooks authorized but not wired, and `scripts/s3-thin-skills.py`. Those verdicts lived in planning notes with no tracked home, which is the same problem one level up.

## Decision

A command may carry an optional `lifecycle` field inside its frontmatter `metadata:`, with the value `active` or `frozen`. Absence means active.

A frozen command works and stays installed. It receives no further investment: an issue about it closes as wontfix, it is not extended in a capability wave, and its documentation is corrected only when it is wrong, never expanded.

Frozen is not deprecated, and the distinction is the point of the field. Removing a command needs an ADR of its own and this field does not authorize one. Freezing says the answer to "should we invest here" is recorded; it says nothing about removal.

The field is optional so that freezing costs one line and unfreezing costs deleting it. Making it required would add a line to 98 commands to express a state that 98 of them do not have.

Three things enforce it. The lint validates the enum as a hard failure, not an advisory, because a lifecycle field with a typo is worse than none: it reads as a state nobody set. The lint prints a `Lifecycle:` summary line. The count of frozen surfaces is a count marker in `wos/maturity-ladder.md`, so it cannot drift from disk.

The surfaces that are frozen and are NOT commands are recorded in the same place, in a table, because the reader asking "what has this repository stopped investing in" should get one answer rather than two lists. `scripts/s3-thin-skills.py` appears there under a different label: not frozen, but a path this repository decided not to walk twice. A frozen thing may thaw. That one is a decision about direction, and flattening the two into one word would lose it.

This ADR installs the mechanism empty. No command is frozen by it. Which commands carry the field is a separate decision, applied by a later slice.

## Consequences

### Positive

- "This works and we are done with it" becomes a state a reader can see, instead of a verdict that has to be re-derived each audit.
- The four verdicts already reached in 2026-08-26 planning notes get a tracked home before those notes are archived.
- A typo in the field fails the build rather than silently meaning nothing.

### Negative

- One more frontmatter field, on a surface whose per-invocation load is already watched. It is optional and one line, and it travels into the generated skill as a plain string, so it costs nothing on the commands that do not carry it.
- A frozen command can still rot. Freezing records a decision about investment, not a promise that the command keeps working. That is what the eval corpus is for.

### Neutral

- The generator copies frontmatter verbatim, so the field reaches `.claude/skills/`. It is a plain string, so the metadata type check stays green.
- The mechanism ships with zero frozen commands, which is what the count marker will say.

## Alternatives considered

### Alternative 1: a required lifecycle field on every command

- Every command declares `active` or `frozen` explicitly.
- Rejected: 98 commands gain a line to state the default. The information is in the absence, and requiring it buys nothing but diff noise.

### Alternative 2: a separate registry file listing frozen commands

- One file naming the frozen ones, no frontmatter change.
- Rejected: the state belongs beside the command, where someone editing it will see it. A separate list is one more thing to keep in sync, and this repository already measures how often that fails.

### Alternative 3: reuse the maturity ladder's levels

- Express frozen as a level on the existing L1 to L5 ladder.
- Rejected: the ladder measures how much autonomy a persona has earned. Frozen is orthogonal: a command at any level can stop receiving investment, and overloading the ladder would make both harder to read.

## References

- `wos/maturity-ladder.md` `## Lifecycle: frozen`: the normative text and the register of non-command frozen surfaces.
- [ADR-0046](./0046-no-auto-install-skill-trust.md): the `metadata.provenance` field whose enum validation this mirrors.
- [ADR-0054](./0054-human-knowledge-layer.md): the `knowledge/` auto-load recorded as frozen in that register.
- `scripts/lint-commands.sh` and `scripts/reconcile-counts.sh`: the enum check, the summary line, and the `frozen-commands` count kind.

## Notes

The two scripts mirror each other's `disk_count()`, so the new kind goes into both or the second fails with an unknown-kind error. That coupling is not new and is worth stating where the next person adding a kind will read it.
