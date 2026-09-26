# ADR-0190: On the Ask path, task-init routes to the write, not to the plan

- **Status**: Accepted. Superseded by ADR-0199: the Ask path routed around the write gate.
- **Date**: 2026-09-01
Supersedes, in part: ADR-0159 (its Ask-mode handoff target only; the Express bind, the Agent-mode handoff and the unattended carve-out stand)
- **Tags**: task-init, ask-mode, approve-proposed, adr-0001, adr-0159, express, eval-found

## Context

Found by running the eval battery on 2026-09-01, not by reading. On scenario 01 turn 2, two
independent models ended `task-init` with `Run now: approve-proposed`. The scenario failed them
both, because no command file names that route and `task-init` says `implementation-plan`.

The first reading was that both models deviated. The measurement says otherwise.

`task-init` in Ask proposes five files and states "five files stay PROPOSED; do not claim the folder
is on disk". `implementation-plan` reads `TASK_STATE.md`. On the Ask path that file is not on disk,
so the command it was told to run has nothing to read.

Worse, the ordering is not merely inefficient, it is lossy. `approve-proposed` persists what is
marked PROPOSED in the MOST RECENT prior assistant turn and stops walking back at the first
intervening block carrying real decisions. Any command between `task-init` and the approval shadows
the block it was meant to apply. So the only turn at which those five files can be written is the
turn immediately after `task-init`, which is exactly where both models put it.

## Decision

On the Ask path, `task-init`'s Handoff is `Run now: approve-proposed`. `implementation-plan` follows
once the files exist.

The Agent path is unchanged and still routes straight to `implementation-plan`, because in Agent the
files are written rather than proposed and there is nothing to approve.

Nothing about the Express bind moves. The tier is still bound at `task-init` (ADR-0183), Express is
still the default (ADR-0184), and the unattended, background and fleet carve-out of ADR-0159 is
untouched. What changes is one handoff target on one mode.

## Consequences

### Positive

- The Ask path chains. Before this it named a command that could not run, and the ADR-0186 rule
  that a session continues into its own `Run now:` would have carried it into a file-not-found.
- The PROPOSED-by-default contract of ADR-0001 keeps its two-step shape on Ask and now names the
  second step at the only turn where it works.

### Negative

- One more command on the Ask path. That is the cost of PROPOSED-by-default and it was always being
  paid; it was just not written down, so a user reached `implementation-plan` and discovered it.
- `approve-proposed`'s own guard, that it never reaches past a block the user already acted on, is
  now load-bearing for the entry path rather than for an edge case. A change to that walk-back rule
  breaks task creation on Ask.

### Neutral

- Agent mode, the default in practice, is unaffected.
- `evals/scenarios/01-bootstrap-and-init.md` graded the old target. Its criterion was already
  rewritten in the same sitting for a different defect and now names the bound tier's route.

## Alternatives considered

### Alternative 1: `task-init` writes the five files in Ask and only the rest stays PROPOSED

- Rejected. It carves an exception into ADR-0001's PROPOSED-by-default contract for the one command
  that creates the most files at once, which is where a user most wants to read before anything
  lands.

### Alternative 2: leave it, and treat Ask as a preview that does not chain

- Rejected, though coherent. If Ask does not chain then `task-init` should not emit a `Run now:`
  naming a command at all, and it does. The contract would have to say Ask ends the chain, which is
  a larger claim than this defect supports.

### Alternative 3: accept `approve-proposed` in the eval and change nothing

- Rejected as teaching to the test. Two models agreeing is a reason to look, not a reason to bless.
  The look found a real gap, and this fixes the gap rather than the grader.

## References

- [ADR-0001](./0001-proposed-by-default.md): the two-step PROPOSED contract this keeps.
- [ADR-0159](./0159-express-binds-by-default.md): the Ask handoff target this supersedes in part.
- [ADR-0186](./0186-the-handoff-continues-the-chain.md): why naming an unrunnable command stopped
  being harmless.
- `projects/bmazurok__my-work-tasks/active/2026-08-31_express-as-behavior/BATTERY_2026-09-01.md`:
  the run that found it.
