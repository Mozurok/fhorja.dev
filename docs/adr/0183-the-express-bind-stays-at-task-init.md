# ADR-0183: The Express bind stays at task-init

- **Status**: Accepted; the Neutral note that ADR-0025's conservative default is untouched is superseded by [ADR-0184](./0184-express-is-the-default-tier.md), which inverts it: Express is the default and escalation names its disqualifier. The decision to keep the bind at `task-init` stands.
- **Date**: 2026-08-31
- **Tags**: express, complexity-routing, task-init, adr-0159, adr-0025

## Context

ADR-0159 binds Express at `task-init`, over the prompt, using the three ADR-0025 criteria: scope
in one sentence, all decisions given, fewer than five files. A planned slice (B3b) proposed moving
the bind to `implementation-plan`, where the same criteria become counts over the written plan
instead of judgments over a prompt. The question was recorded as open and reached the owner as one
letter: keep it where it is, or move it.

The argument for moving was concrete. Under the old floors, a plan that failed one count would
leave the closure floor standing down with no bind, because the floors keyed their stand-down on
the pipeline being attended Express.

## Decision

The bind stays at `task-init`. ADR-0159 is unchanged and B3b does not run.

Three measurements, read 2026-08-30 and 2026-08-31.

**The argument for moving is gone.** E2.C removed the Express stand-down from the closure floors.
All six remaining stand-down clauses in `wos/closure-floors.md` are the Godot task signature, and
zero are conditioned on Express. The failure mode the move was designed to prevent cannot occur.

**One of the five proposed counts is not a count.** B3b's fifth predicate reads "`DECISIONS.md`
carries no decision still open". The substrate matrix declares three DECISIONS.md sections with
owners, `## Locked decisions`, `## Decision history` and `## Open questions`, and none of them
represents an open DECISION: the first two hold what is locked and its history, the third holds
questions and has a different owner. Across 510 real `DECISIONS.md` files on disk the open state
appears in 71 distinct heading spellings. A criterion that exists to replace judgment with counting
would have reintroduced the judgment.

**The slice's scope is incomplete.** `commands/what-next.md` re-checks the Express bar on its own,
against the prompt, in the same three terms `task-init` uses, and can name Express even when the
tier field already names something heavier. B3b's scope does not list it. Moving the bind without
touching `what-next` leaves two commands deciding the tier by two different methods.

None of the three is fatal to the idea. Deciding the tier over an artifact rather than over a
prompt remains coherent, and this ADR does not close that door: it records that the version on the
table in 2026-08-31 was larger than "move one paragraph between two commands", and that its
motivating defect had already been fixed elsewhere.

## Consequences

### Positive

- No change to a routing rule that is working, and no new ADR superseding ADR-0159 on its binding
  site.
- The three defects are written down, so a later attempt starts from them instead of rediscovering
  them.

### Negative

- The Express criteria stay judgments over a prompt rather than counts over a file, which is the
  weaker form and remains the honest criticism of ADR-0159.

### Neutral

- ADR-0025's conservative default is untouched: when uncertain, Standard.

## Alternatives considered

### Alternative 1: move the bind to `implementation-plan` (B3b as written)

- Rejected on the three measurements above, not on principle.

### Alternative 2: move it and fix the two defects first

- Not rejected, deferred. It requires restating the fifth predicate against a section that exists
  and adding `what-next` to the scope. If that work is done, this ADR is the thing to supersede.

## References

- [ADR-0159](./0159-express-binds-by-default.md): the binding site this keeps.
- [ADR-0025](./0025-complexity-routing.md): the tiers and the conservative default.
- `wos/closure-floors.md`: six stand-down clauses, all Godot, none Express.
