# ADR-0193: A rule that turns on a word must ask for that word, and a verdict must point at the response

- **Status**: Accepted
- **Date**: 2026-09-02
- **Tags**: slice-closure, routing, eval-harness, measured, friction

## Context

Two defects found by the 2026-09-01 battery, unrelated in surface and identical underneath: a
decision was being made from something nobody was asked to produce.

**The first.** `commands/slice-closure.md` routes a follow-up to `implement-slice-complement` for
explicit micro-deltas "unless the gap is material". The word "material" appears eleven times in that
file and "micro-delta" once, in the routing sentence itself. Nowhere does the command ask the output
to record which of the two the gap was. All three models faced that gap and none classified it. They
were not refusing; they were never asked.

**The second.** The eval runner prints a verdict and, beside each criterion, the grader's one-line
note. That note is the grader's reading of the response, not the response. On 2026-09-01 I read
those notes and drew two successive conclusions about scenario 03 criterion 3, and both were wrong:
first that a command's handoff target was underspecified, then that two of three models had missed a
lazy-loaded floor. Reading what the models actually wrote showed the command was specified, all
three had detected the floor, and what they had found was that the scenario's fixture did not exist.
Either wrong conclusion would have changed a command that did not need changing.

The response files were on disk the whole time, in a directory the runner names on stdout.

## Decision

**`slice-closure` asks for the word.** When the status is `ready to close with follow-ups`, the
output SHALL name the gap as `micro-delta` or as `material`, in those words. A follow-up left
unclassified is incomplete output rather than a judgment deferred. The routing is unchanged; what
changes is that the input the routing consumes is now required rather than assumed.

**The runner points at the response.** For every criterion that is not PASS, the run prints the path
to the response files and states that the notes are the grader's reading and not the model's words.
The pointer is emitted at the moment of reading, not left to be looked up.

## Why the second half is a mechanism and not a rule

The obvious response to reading a verdict badly is a rule saying read the response first. I proposed
exactly that and then declined to add it, for two reasons.

The rule already existed in my own head and I broke it three times in one afternoon. A rule an
operator already believes and does not follow is not a control.

And this repository's stated direction, set by the maintainer on 2026-08-31, is to stop adding a
rule on top of a rule. A line of output at the point of the mistake costs one print and cannot be
forgotten. A documented process rule costs a paragraph every reader pays and gets skipped by the
reader in a hurry, who is the one making the mistake.

## Consequences

### Positive

- The `slice-closure` routing becomes checkable. An eval criterion can now grade the classification,
  which is what `evals/scenarios/03` criterion 6 was already trying to do against a rule that never
  asked for it.
- The verdict stops being mistakable for evidence. The reader is told, at the moment of reading,
  which file holds the thing the verdict is about.

### Negative

- One more required field on a closure output. It is a word, and it is the word the next routing
  decision reads, so the cost is proportionate; but it is a new obligation on a command whose
  generated skill sits at 38607 of 40000.
- The runner's stdout is three lines longer on any non-PASS scenario. Accepted: those three lines
  are addressed at exactly the person about to draw a conclusion.

### Neutral

- No routing target changes. `implement-slice-complement` and `implement-approved-slice` keep the
  same conditions; only the record of which one applies becomes mandatory.
- The verdict JSON is unchanged. The pointer is stdout only, where the reading happens.

## Alternatives considered

### Alternative 1: infer the classification from the follow-up text

- Rejected. It reintroduces the judgment the classification exists to make explicit, and a reader
  cannot audit an inference that was never written down.

### Alternative 2: a documented rule requiring the response to be read before concluding

- Rejected, and the reasoning is above. It is the accretion the maintainer asked to stop, and it
  would have been a rule I already believed on the afternoon I broke it three times.

### Alternative 3: put the response excerpt inside the verdict JSON

- Rejected as the wrong surface. The JSON is read by machines and by anyone who already opened the
  directory. The mistake happens to someone reading stdout and stopping there.

## References

- `commands/slice-closure.md`: the routing sentence that now asks for its own input.
- `evals/scripts/run-spine-evals.py`: the pointer, asserted by check 22 in
  `scripts/tests/test-run-spine-evals.sh`.
- `projects/bmazurok__my-work-tasks/active/2026-08-31_express-as-behavior/BATTERY_2026-09-01.md`:
  the two wrong readings, recorded in the order they were made.
