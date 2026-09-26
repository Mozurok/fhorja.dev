# ADR-0191: Condition 4 is checked, and solo governance is declared rather than inferred from infrastructure

- **Status**: Accepted
- **Date**: 2026-09-01
Supersedes, in part: the P0/D-2 solo/local auto-waiver of 2026-07-18 (its signal set and its coverage of condition 4; the waiver itself, its verbatim recording, and its exclusions all stand)
- **Tags**: task-close, closure-gate, solo-maintainer, done-conditions, friction, third-recurrence

## Context

Running `task-close` on 2026-09-01 blocked, and the block was correct under the rule as written. The
rule was wrong.

The solo/local auto-waiver dispenses conditions 3 (team approval) and 4 (merge into the integration
branch) when all three of its signals hold: no configured git remote, no integration branch, and an
untracked task folder. Measured on this repository the same day, only the third holds. `origin` is
the maintainer's staging remote and `main` exists.

The first signal proxies "solo" as "no remote". A solo maintainer who publishes has a remote, so
this repository can never reach its own auto-waiver, in the repository where the rule was written.

This is the third time. The project's knowledge index carries the same note on the 2026-08-13
closure, verbatim: "Closed with condition 3 waived verbatim (a remote exists, so the solo/local
auto-waiver did not fire)". Two prior closures recorded the defect as an observation and neither
turned it into a change, which is how a rule keeps costing the same waiver every time.

The same run surfaced a second defect, larger than the first. Condition 4 was in the waiver bundle,
and it did not need to be: all five commits the task cited are ancestors of `main`, verified with
`git merge-base --is-ancestor`. The condition was answerable, and the rule offered to waive it.

## Decision

**Condition 4 leaves the auto-waiver and becomes a check.** Where an integration branch exists, ask
whether the cited commits are ancestors of it. They are, and the condition is MET, on the
direct-to-branch pattern as much as on a merged pull request. Push is a separate act and this
condition does not ask about it. Where no integration branch exists, the condition is
not-applicable and says so.

A waiver for an answerable condition throws away the answer. That is the general form, and it is
why this is a decision rather than a wording fix.

**Condition 3's waiver gains a second route, and neither is inferred from commit history.**

- Route A, unchanged in substance: no configured git remote AND an untracked task folder. A purely
  local tree, with nothing to approve through.
- Route B, new: the project's `CONTRIBUTING.md` or equivalent governance file states a
  single-maintainer model. A declaration is stronger evidence than an inference from
  infrastructure, and it is the thing the condition is actually about.

Commit history is explicitly NOT a signal. Measured here, `git log --format='%ae' | sort -u` returns
two addresses for one person, so an author count would read this project as a team.

Everything else about the waiver stands: it is recorded verbatim in the final `TASK_STATE.md`, it
never covers the experience-verdict or commit-evidence floors, and when neither route holds the
fallback is still an explicit maintainer waiver.

## Consequences

### Positive

- A solo maintainer who publishes can reach the waiver. That is one closure's friction removed
  permanently, on a rule that had already charged it three times.
- Condition 4 stops being a ceremony and becomes an answer. `git merge-base --is-ancestor` is
  cheap, and the verdict it produces is auditable in a way "waived" never was.
- The signal that failed is replaced by one that says what it means, rather than by a second proxy.

### Negative

- Route B trusts a file the project writes about itself. A repository could declare solo governance
  and have a team. That is a weaker guarantee than infrastructure, and it is accepted because the
  infrastructure signal was not measuring governance at all.
- A consuming project with no `CONTRIBUTING.md` and a remote still falls through to the explicit
  waiver. The fallback is unchanged and is the safe direction.

### Neutral

- The waiver's exclusions, its verbatim recording and the knowledge-note confirmation it collapses
  are untouched.
- `wos/sub-agent-orchestration.md` cites this waiver as precedent for harness degradation and listed
  merge among the administrative gates; its parenthetical is corrected so the citation stays true.
  The degradation rule itself is not changed here.

## Alternatives considered

### Alternative 1: infer solo from the commit history

- Rejected on measurement. Two author addresses for one person on this repository, so the inference
  reads a solo project as a team. Recorded in the command text so a later author does not retry it.

### Alternative 2: keep condition 4 in the waiver and only fix the signals

- Rejected. It leaves a condition that a one-line git command answers being settled by a human
  sentence, which is the friction this arc exists to remove, and it discards evidence the closure
  already has in hand.

### Alternative 3: drop conditions 3 and 4 for solo projects entirely

- Rejected. Condition 4 is meaningful even alone: work that was never merged anywhere is exactly
  what a closure should catch, and on a solo project it is the only reader that will.

## References

- [ADR-0084](./0084-godot-flow-completeness-wave.md): the commit-evidence floor this leaves alone.
- `commands/task-close.md`: the rule.
- `projects/bmazurok__my-work-tasks/knowledge/index.md`: the 2026-08-13 entry recording the same
  defect as an observation, one closure before this one.
