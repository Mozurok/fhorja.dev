# ADR-0214: Wire the memory consume path the August research concluded on

- **Status**: Accepted
- **Date**: 2026-09-22
- **Supersedes**: nothing. It answers the per-script question D-3 of the retro wave-1 task left open, for one script.
- **Tags**: memory, learnings, consume-path, task-init, impact-analysis, installer, adr-0017, adr-0054, adr-0071

## Context

Four rounds of research in August 2026, about 6.3M subagent tokens, asked how Fhorja should
remember across sessions. Embeddings, a vector database, sqlite-vec, fine-tuning and a
per-project accumulated memory layer were each measured and refuted. The conclusion that
survived was that the defect is the moment of CONSUMPTION, not storage, and that "the fix is
to wire what exists, not to build a new artifact". The round confirmed five concrete defects
by hand.

On 2026-09-22, a month later, one had been fixed (every bug-class template now carries its
`## Analysis prompt`) and four had not. Nothing in the tree measured any of them.

The question came back through a proposal to adopt Laya, a fast typed-decision engine, for
learnings. Laya classifies text; it neither stores nor retrieves, it needs PyTorch and a GPU,
and its distinguishing output is a calibrated probability, which ADR-0109 rules out ("Status
records provenance, never confidence"). It does not address consumption. Re-checking what
DOES address consumption is what found the four still open:

1. `task-init` told the agent to read the project's `REFERENCES.md`, and all it does with that
   file is write a pointer to it. This repository's own file had grown to 676 KB: about 79,000
   tokens in a default read of its first 2,000 lines, paid on every `task-init` to produce one
   link.
2. `task-init`'s LEARNINGS consume step runs `scripts/rank-learnings.sh`, and the installer
   ships no scripts (D-3). On every install that is not a clone of this repository the step
   had nothing to run, and it did not say so.
3. `impact-analysis` had no instruction to read prior analyses of the same code. 292
   `IMPACT_ANALYSIS.md` sat on disk; no command was told to consult them.
4. `scripts/memory-lint.sh` required a `Tags` line that ADR-0071 made optional, so it
   reported every entry predating the field as malformed.

## Decision

Each defect is fixed where it lives, and one check asserts all four stay fixed.

`task-init` checks that `REFERENCES.md` exists and links to it, and does not read it. A
command that grounds a claim reads the one entry it cites, which is the reading that was
always useful.

`rank-learnings.sh` ships in the installer's runtime payload, and `task-init` resolves it
against the workflow root rather than the task repository. When it is in neither, the command
names the absence in its transcript instead of skipping. This is the per-script answer D-3
asked for. A script ships only when an installed copy, run from outside this repository,
passes both of D-3's tests: it derives nothing from its own location and takes every input as
an argument, and on an empty input it names the absence rather than printing a well-formed
empty result. Measured: run from `/tmp` against a real project it returned ranked lessons;
against an empty one it printed "no LEARNINGS.md found under" and "0 ranked / 0 scanned". It
depends only on awk, find, grep, sed and sort.

`impact-analysis` greps the project's other `IMPACT_ANALYSIS.md` for the files in scope and
reads only those that match, newest first, at most three, recording which it read or that none
matched. Measured on this repository's 65 analyses: a file in scope matches 4 to 15 of them,
so the grep filters, and the cap bounds the worst case at roughly 9,000 tokens against about
195,000 to read all 65.

`memory-lint` checks `Tags` as `value-only`: absent is valid, present-and-empty is not.
Verified both ways with a fixture, and against the previous version, which reported the valid
entry.

`check_memory_consume_path` asserts the load-bearing clause of each, with one mutation per
clause.

## Consequences

### Positive

- The largest per-invocation cost found in this cycle leaves the most frequent entry command.
- LEARNINGS are consumed on an install, which is where every user outside this repository is.
- Prior analyses reach the command whose output they would have changed.

### Negative

- The check asserts wording. It bounds how each fix comes undone in the obvious phrasing and
  does not prove an agent follows the instruction; only a run measures that.
- The cap of three is a cost bound, not a relevance measure. The grep is literal, so an
  analysis that describes the same code in other words is missed.
- Shipping one script opens the door D-3 closed. The two tests above are the price of entry,
  and a script that fails either stays out.

### Neutral

- No artifact was added. Every change wires a file that already existed.

## Alternatives considered

### Alternative 1: adopt Laya, or any model, for learnings

- Rejected on what it is: a classifier, not a store or a retriever. The August research had
  already refuted the storage and retrieval side on measurement.

### Alternative 2: ship every script

- Rejected by D-3's own evidence. `portfolio-review.sh` derives its data root from its own
  location and, installed, prints a well-formed empty board with exit 0.

### Alternative 3: read every prior analysis

- Rejected on cost: up to 65 in one project, about 195,000 tokens.

## References

- [ADR-0017](./0017-reflexion-style-learnings.md): the LEARNINGS consume side.
- [ADR-0071](./0071-learnings-retrieval-tags-and-ranker.md): Tags optional, and the ranker.
- [ADR-0109](./0109-active-epistemic-humility-doctrine.md): provenance, never confidence.
