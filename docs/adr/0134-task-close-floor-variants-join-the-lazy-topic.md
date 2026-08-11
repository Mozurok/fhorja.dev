# ADR-0134: task-close's whole-task floor variants join the lazy topic

- **Status**: Accepted
- **Date**: 2026-08-09
- **Tags**: closure-floors, context-budget, lazy-loading, task-close, supersedes-part-of-adr-0124, extends-adr-0116

## Context

ADR-0124 moved the generalized closure floors into `wos/closure-floors.md` for `slice-closure` and `implement-approved-slice`, and deliberately left `task-close`'s whole-task backstops inline. Its `## Decision` gave three reasons for that exclusion:

1. the whole-task backstops "read recorded evidence across every slice rather than gating one";
2. `task-close` "sits at 8521 tokens with headroom";
3. moving them "would widen the change past the two files that needed it".

Reason 2 was exact when written. At ADR-0124's own implementation commit `81891f3` (2026-07-29) `.claude/skills/task-close/SKILL.md` measured 34,087 chars, which is 8,521 tokens at the repository's standing 4-chars-per-token rule. It is now 38,656 chars, 9,664 tokens, a margin of 336 tokens against the ADR-0116 ceiling, and the tightest skill in the corpus. The premise decayed; it was not wrong.

Reason 3 was a scope statement about ADR-0124's own change, not a property of `task-close`.

Reason 1 still holds and this ADR does not contest it.

The decay has a mechanism, and it is the excluded content itself. ADR-0128 and ADR-0133 each added a route to the commit-evidence floor, which is now a single 3,405-char line, 8.8 percent of the file. The most recent commit touching the file is "regenerate task-close after the ref-attested floor edit". ADR-0124 already recorded that the closure commands "attract every new closure floor"; that dynamic has reached `task-close`, and every future closure doctrine will land on the same lines.

## Decision

`task-close`'s whole-task floor clause bodies move into `wos/closure-floors.md` as a THIRD variant family, alongside the two ADR-0124 created. This supersedes the `task-close` bullet of ADR-0124 and nothing else in it.

Reason 1 of ADR-0124 is preserved and is why this is a distinct variant family rather than a fold into an existing one: a whole-task backstop reads recorded evidence across every slice, and a `### task-close variant` section says so under each floor rather than pretending the three homes assert the same thing.

Constraints on the move, each load-bearing:

- **Every floor stays NAMED inline** in `commands/task-close.md` with its trigger and its routing. Only clause bodies move. A floor whose existence is discoverable only by loading a topic is a gate-if-read, and this is the command that decides whether a task archives.
- **Three floors additionally keep inline the exact string their runner must emit.** Commit-evidence keeps `deferred: pending human commit (<one-line context>)`, Integrity keeps `integrity-waiver: N advisories unresolved (<one-line reason>)`, and Unresolved-revision keeps `[WAIVED: <reason>]`. Naming a floor and its route is not enough when the outcome is a recorded waiver rather than a route: a reader who skips the load would have to reconstruct a closed string from memory, and the next grep looking for the exact form would miss the approximation.
- **The solo/local auto-waiver does not move.** It is not a floor. It waives conditions 3 and 4 of the done-conditions gate rather than blocking on its own, and a topic organised by floor has no correct heading for it. Six items move, not seven.
- **The existing 15 variant sections are not edited.** The change is additive; `slice-closure` and `implement-approved-slice` read exactly what they read before.
- **The `Definition of done` block stays inline and is extended** to name all six moved floors. It already named five of the six; only Unresolved-revision was missing. An earlier figure of three, produced during this task by a grep whose pattern required a bullet to end in the word `floor`, silently excluded the `Experience gates` bullet that covers two of the six. The correction is recorded here rather than left in task memory, because the wrong figure was in this ADR's first draft.
- The ADR-0116 ceiling does not change, and `Operating rules:` is not trimmed.

## Consequences

### Positive

- `task-close` regains headroom on the same mechanism it already uses one line above, where the platform runtime floors have pointed at `wos/platform-runtime-floors.md` since 2026-07-29.
- Future closure doctrine lands in one topic with three variants instead of in two topics plus one command body, so the next ADR that adds a route to a floor edits one file.
- The three homes become symmetric, which makes a floor written to only one of them visible as an omission rather than as a formatting difference.

### Negative

- One more gate sits behind a lazy load, and nothing verifies that a referenced topic is actually read. The naming constraint bounds the damage rather than removing it: a reader who skips the load still knows every floor exists, what fires it, where it routes, and which string to write. That exposure already exists for the platform floors in this file and for the two commands ADR-0124 moved; this ADR extends it rather than introducing it.
- The `Definition of done` now names floors whose bodies live elsewhere, which is a second place that can drift from the first.

### Neutral

- ADR-0124 stays Accepted. Only its `task-close` bullet is superseded, and its reason 1 is carried forward here rather than discarded.

## Alternatives considered

**Trim the clause prose in place.** This was the route the task was seeded with, before measurement found a destination. Rejected because it is the documented silent-rule-loss mode (a 2026-08-06 budget-driven trim deleted a rule older than the task while lint, count markers and natural-voice were all green on the wrong draft), applied to the one file that gates every closure, while the destination, the mechanism and the sibling family all already exist here.

**Move the ADR-0116 ceiling.** Rejected on the reasoning the predecessor task recorded when it declined the same route for `task-init`: a ceiling moved to clear a floor fits the ruler to the result. Nothing in this task's measurement argues the ceiling is wrong.

**Leave it inline and accept the 336-token margin.** Rejected because the margin is not stable. The floors are the growth vector, and two ADRs in the last eleven days each added a route to the same line.
