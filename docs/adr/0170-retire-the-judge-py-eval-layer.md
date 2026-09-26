# ADR-0170: Retire the judge.py eval layer

- **Status**: Accepted; supersedes the mechanism of ADR-0019, which stays as the historical record of why it was built.
- **Date**: 2026-08-30
- **Tags**: evals, deprecation, removal, adr-0019, adr-0033, spine-evals

## Context

ADR-0019 added an optional second pass over a scenario's `## Pass criteria`: a script that formatted the criteria as a rubric, piped it to a configured tool, and parsed per-criterion verdicts. ADR-0033 then made a stateless verify-against-rubric sub-agent the canonical evaluator, and the eval README has said so, in its own opening line, since 2026-06-04.

Two years of drift followed from leaving the script in place. No command invoked it. The `--judge` flag in the manual walker reached it and nothing else did. A 2026-08-29 audit found it still advertised in eight live surfaces: the root README, CLAUDE.md, the FAQ, the eval README in a full section plus a table row plus two loose mentions, the walker's usage text and argument parsing, the repository-structure tree, and three comments in an unrelated script that cited its `call_tool()` as the example of how to invoke a tool.

Advertising a superseded mechanism in eight places is worse than having no mechanism. A reader who follows any of those pointers arrives at a script the repository stopped standing behind, and there is nothing at the destination that says so.

Scenario 15 tested the script's own rubric extraction and verdict parsing. It tested no command contract, so with the script gone it has no subject.

## Decision

`evals/scripts/judge.py` and `evals/scenarios/15-llm-as-judge-self-check.md` are deleted, together with the `--judge` and `--tool` flags of `evals/scripts/run-evals.sh` and every live pointer to any of them.

Scenario number 15 becomes a gap. The numbering guard requires uniqueness, not density, so a gap costs nothing and renumbering the corpus to close it would break every reference into it.

ADR-0019 is not edited. It records a decision that was true when it was made, and this ADR supersedes its mechanism rather than rewriting its text. The FAQ keeps its historical mention of ADR-0019 and marks it retired, pointing here.

Rubric grading still exists: `evals/scripts/run-spine-evals.py` extracts the criteria, sends them to a vendor-agnostic command, parses per-criterion verdicts, and computes the overall verdict itself. That is why this removal lands after the runner and not before. Deleting the only grader in the repository at the moment the harness started to need one would have been a hole, not a cleanup.

`CHANGELOG.md`, `ROADMAP.md` and the ADR corpus keep their mentions. They are the historical record, and rewriting them would be the same mistake in the opposite direction.

## Consequences

### Positive

- A reader following any live pointer about eval grading arrives at the mechanism the repository actually stands behind.
- The manual walker is smaller and does one thing: print a scenario and wait for a human.
- One fewer script to keep working, in a repository whose CI cannot exercise it.

### Negative

- The `--judge` flag disappears without a deprecation window. It reached a script marked DEPRECATED since 2026-06-04, so the window already ran.
- Anyone whose local notes name `judge.py` finds it gone. The ADR is the pointer they land on.

### Neutral

- Scenario count drops by one, and the corpus keeps a numbering gap at 15.
- `scripts/mine-learnings-patterns.sh` still describes the same tool-calling pattern; only the citation of a deleted file goes.

## Alternatives considered

### Alternative 1: keep the script and fix the pointers

- Leave `judge.py` in place, update the surfaces to say it is optional and superseded.
- Rejected: it stays unreachable from any command and unexercised by CI, and a second grader whose verdicts nobody reads is a maintenance cost with no reader.

### Alternative 2: migrate scenario 15 to the new runner

- Rewrite it as a meta-test of `run-spine-evals.py`.
- Rejected: the runner's rubric extraction and verdict computation are covered by two script suites that run in CI on every push. A manual scenario would restate what a test already asserts, and less precisely.

### Alternative 3: delete the script first, add the runner later

- Cut the dead code immediately and build the replacement afterwards.
- Rejected: it leaves an interval with no rubric grading at all, in the exact stretch where the spine eval work needs one.

## References

- [ADR-0019](./0019-llm-as-judge-eval-layer.md): the decision this supersedes; not edited.
- [ADR-0033](./0033-verify-against-rubric-stateless-subagent.md): made the stateless sub-agent canonical, which is when the script became superseded.
- `evals/scripts/run-spine-evals.py`: the rubric grading that exists now.
- `scripts/tests/test-run-spine-evals.sh` and `scripts/tests/test-spine-eval-extract.sh`: what covers it in CI.

## Notes

The removal and the replacement are two commits, in that order, and the dependency is one way. Reversing them would leave the repository without a grader.
