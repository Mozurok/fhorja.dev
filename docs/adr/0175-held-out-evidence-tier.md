# ADR-0175: The evidence rule is grounded in measurement, and gains a held-out tier

- **Status**: Accepted; superseded in part by [ADR-0231](./0231-the-held-out-tier-is-withdrawn.md): D-2, the held-out tier, is withdrawn before it was wired, and D-3 rests on D-1 instead of D-2. D-1 stands. Supersedes the grounding of ADR-0048 on the evidence-tier question and keeps its deterministic-gate rule intact.
- **Date**: 2026-08-30
- **Tags**: evidence, gate-conditions, held-out, measurement, adr-0048, adr-0146, layer-1

## Context

ADR-0048 decided that a passing deterministic gate satisfies Layer 1. The decision holds. What it rested on does not.

Its `## Context` grounds the rule this way: "The research (W-20, grounded in the Claude Code best-practices source) recommended deterministic Stop/PostToolUse hooks as the strongest verification surface." That is an appeal to a source. A source can be right and still be the wrong kind of reason to write into a repository's own contract, because it tells a later reader what someone recommended rather than what this tree actually does.

This ADR replaces that grounding with two measurements. Both are recorded, because they answer different questions and neither substitutes for the other.

### The external measurement

Source: the Claude Code best-practices material captured under W-20, read 2026-06-21 and recorded in that task's `REFERENCES.md`. What it supports is narrow and worth stating narrowly: a deterministic hook that runs on a tool event is a stronger verification surface than a model's self-report, because the hook runs whether or not the model chooses to mention it. It says nothing about how well any particular repository adheres to that, which is the question the rule actually turns on.

### The disk measurement

Measured in this repository on 2026-08-30, with the command pasted so the number can be re-derived rather than trusted:

```
python3 -c "import glob,re;ns=glob.glob('projects/*/*/*/SLICES/*.md');V=re.compile(r'^#{2,4}\s*validation',re.I|re.M);w=[n for n in ns if V.search(open(n,errors='replace').read())];print('notes',len(ns),'with-validation',len(w),'without-fenced-block',sum(1 for n in w if '```' not in open(n,errors='replace').read()))"
```

Result: 1961 slice notes, 1525 carrying a validation section, and 851 of those carrying no fenced block at all. A second command:

```
python3 -c "import glob,re;ns=glob.glob('projects/*/*/*/SLICES/*.md');print(sum(1 for n in ns if re.search(r'tests? pass', open(n,errors='replace').read(), re.I)))"
```

Result: 75 notes containing a bare "tests pass" phrase.

So more than half the notes that claim to have validated something show no command output while claiming it. That is the reason the shown-evidence rule exists in this tree, and it is a fact about this tree rather than a recommendation about repositories in general.

Recording the plan's own reference numbers alongside, because they differed and the divergence is the point: the plan measured 1588 with-validation and 908 without-fenced-block on 2026-08-29, against 1525 and 851 today. The ADR records what was measured on the day it was written, never the number a plan predicted.

## Decision

### D-1: the evidence rule is grounded in measurement, not in a source

The requirement that Layer 1 evidence be shown output rather than a claim about output stands on the disk measurement above. The external source is cited for what it supports and no further. Any future revision of this rule re-runs the pasted commands and records the new numbers; a revision that argues from a source alone does not meet the bar this ADR sets.

### D-2: a held-out assertion tier

Layer 1 today accepts exactly the tests the agent saw. `TEST_STRATEGY.md` is written before implementation and the agent reads it, so a passing suite proves the agent satisfied a target it was shown. That is worth having and it is not the same as evidence the behavior is right.

The held-out tier requires at least one assertion that was NOT in `TEST_STRATEGY.md` when implementation began. It is proved by the mechanism this repository already uses for absent precedent under ADR-0146: the exact search command pasted, with its verbatim zero-result output. Prose saying "this assertion is new" is a referent-free status, read as UNKNOWN, exactly as a prose "no precedent found" already is in `commands/implement-approved-slice.md`.

The tier is defined here and applied where a later slice wires it. This ADR does not itself add a gate to any command.

### D-3: a per-slice evidence file

Evidence lives in a file per slice rather than inline in prose, with one writer, a fixed path and a stated lifecycle. Format, path, writer and lifecycle are settled by the slice that implements it. The reason it belongs in this decision rather than in that slice: the held-out tier of D-2 needs somewhere to put a pasted command and its output that a reviewer can find without reading the whole note.

## Consequences

### Positive

- A reader of the evidence rule can re-run two commands and see why it exists, instead of following a citation to a document about other repositories.
- The held-out tier names the gap between "the agent satisfied the target it was given" and "the behavior is right", which no current tier distinguishes.
- The proof mechanism for D-2 is one the repository already runs, so there is nothing new to learn or to enforce separately.

### Negative

- The disk numbers age. Anyone revising this rule has to re-measure, which is the intended cost and is cheap: the commands are in the file.
- A held-out assertion is real extra work per slice, and the tier is defined before anything requires it. Defining it without wiring it risks it sitting unused; the wiring slice is what prevents that.

### Neutral

- ADR-0048's decision is unchanged. A passing deterministic gate still satisfies Layer 1.
- ADR-0048's body is not edited. Only its Status line is marked, which is the pattern this repository already uses for supersession.

## Alternatives considered

### Alternative 1: leave ADR-0048's grounding as it is

- The decision is right, so the reasoning underneath it does not matter.
- Rejected: the reasoning is what a later reader uses to decide whether the rule still applies. Grounded in a source, the honest answer to "does this still hold?" is "go read that source". Grounded in measurement, it is "re-run this command".

### Alternative 2: make the held-out assertion mandatory now, in the same decision

- Define the tier and gate on it immediately.
- Rejected: a tier that nothing produces yet would fail every slice on the day it lands. The definition and the wiring are separate because the wiring needs the evidence file of D-3 to exist first.

### Alternative 3: rewrite ADR-0048 in place

- Edit its Context section to carry the measurement.
- Rejected: an accepted ADR records what was decided and why, at the time. Rewriting the why erases that the grounding ever changed, which is exactly the fact a later reader needs.

## References

- [ADR-0048](./0048-deterministic-gate-evidence.md): the decision this keeps and the grounding it replaces.
- [ADR-0146](./0146-internal-claim-keyed-grounding.md): the pasted-command, verbatim-zero-result mechanism D-2 reuses.
- `commands/implement-approved-slice.md`: where that mechanism already runs for absent precedent.
- `wos/gate-conditions.md`: the three-layer gate this tier sits inside.

## Notes

The two measurements answer different questions and the ADR keeps both on purpose. The external one says a deterministic surface beats a self-report. The disk one says this tree needs the rule. Dropping either leaves the next reader with half an argument.
