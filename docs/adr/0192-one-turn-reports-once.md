# ADR-0192: A turn that runs several commands reports once

- **Status**: Accepted
- **Date**: 2026-09-02
Supersedes, in part: ADR-0186 (its implicit assumption that a chained turn emits one Handoff per command; the continuation rule and the four stop reasons stand)
- **Tags**: handoff, global-output-contract, chaining, adr-0186, express, measured

## Context

ADR-0186 made an attended session continue into its own `Run now:` in the same turn. It did not say
what the output contract means once four commands run inside one turn, and the contract it inherited
was written for one command per turn.

The ambiguity had a grader. `evals/scenarios/137` criterion 5 read "Four-field Handoff on every
command", and it would fail a correct run.

Measured 2026-09-02, three models on that one scenario, transcripts flattened so every intermediate
message reached the record:

- codex ran the chain and past it, to `slice-closure` and `task-close`: six `Run now:` lines, six
  complete four-field blocks.
- grok ran the same chain and emitted ONE block, `Run now: none`. Its narration names every hop, and
  its output carries the five genesis files, the Express plan with its Approval log, the closed
  slice, the emitted substrate batch and its verification, and the full `--apply` proof with
  `T_shown`, `HEAD_before`, `HEAD_after` and the tree match. It committed and stopped, saying merge
  needs a human.
- claude ran `task-init` only and emitted one block pointing forward to `implementation-plan`.

The record survived in both runs that chained. What varied was only how many times it was announced.

## Decision

When one turn runs several commands, `### Artifact changes` and `### Handoff` are emitted once for
the turn, not once per command. The per-command record is the substrate each command writes, and the
turn's single Handoff reports where the chain actually stopped.

One block per command is not wrong, only more verbose. Neither shape is graded against the other.

This resolves an ambiguity ADR-0186 created rather than changing what it decided. The continuation
rule and the four stop reasons are untouched, and so is the requirement that a turn end with a
complete four-field block.

The spec already reasoned this way for one section: `### Artifact changes` is described there as
"the single proposal surface per turn". This extends the same reading to the Handoff, which is the
only other per-command block.

## Consequences

### Positive

- A correct run stops being gradeable as a failure. Scenario 137's criterion 5 would have failed
  grok's run, which did the work, wrote the record, committed, and stopped at the right place.
- The thing worth grading is named: the substrate, which is durable and machine-readable, rather
  than a block count, which is neither.

### Negative

- A reader of a chained turn sees one Handoff and has to open the substrate to reconstruct the hops.
  That is a real loss of at-a-glance auditability, accepted because the substrate is the record and
  a repeated block was never the record.
- "Emitted once for the turn" says nothing about how much narration the turn should carry between
  commands. Left open on purpose; it is a verbosity question and the output-depth policy owns it.

### Neutral

- Nothing changes for a turn that runs one command, which is still the common shape.
- Net cost inside the four bootstrap sections is +331 characters, measured. A first draft was +525
  and pushed the declared floor 7 tokens past its tolerance; the guard refused it and the
  measurement sentence moved here, which is where it belonged.

## What this ADR does NOT decide

Chaining itself is not uniform, and this decision does not make it so. On the same prompt with the
same directive, one model ran four commands, one ran four and reported once, and one stopped after
the first. claude chained in a 2026-09-01 A/B and stopped after `task-init` here, so the variance is
within one model as well as across models.

That is a fact about models, not a contract defect, and no wording in this repository fixes it. It
is recorded so a later reader does not mistake ADR-0186 plus ADR-0189 for a guarantee. What they buy
is that the chain CAN run and that nothing structural stops it; they do not buy that it always will.

## Alternatives considered

### Alternative 1: require one Handoff per command

- Rejected on measurement. It fails a run that did everything right, and it grades an announcement
  rather than a record. The substrate already carries what a per-command block would restate.

### Alternative 2: leave the ambiguity and fix only the eval criterion

- Rejected. The criterion was wrong because the contract was silent, and fixing the grader while
  leaving the contract silent means the next grader gets it wrong the same way.

## References

- [ADR-0186](./0186-the-handoff-continues-the-chain.md): the continuation rule that created the
  multi-command turn.
- [ADR-0189](./0189-the-directive-is-the-missing-install-step.md): what makes a chain start.
- `evals/scenarios/137-express-one-human-stop.md`: criterion 5, corrected in the same commit.
