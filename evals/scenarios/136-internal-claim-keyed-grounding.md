# Eval scenario 136: an in-repo behavior claim is grounded, enumerated, and not inherited from a precedent

- **Tags**: ADR-0146, reference-grounding, implement-approved-slice, internal-contracts, claim-keyed, session-forensics-2026-08
- **Last reviewed**: 2026-08-13
- **Status**: active

## Goal

Validates **ADR-0146** rule 7: the internal exemption in `commands/_shared/reference-grounding.md`
rule 1 exempts an internal-only slice from CAPTURE, not from GROUNDING, and the two clauses that
carry the weight actually fire.

The motivating failure is specific and reproducible in shape. A screen handler called a pipeline
internal directly and duplicated the logging and toast the callee already owned. The search that
returned the canonical path had already run, the callee's own handling had already been on screen,
and the edit still went in, because both claims rested on a mirrored precedent plus line-window reads
that skipped the range where the existing behavior lived.

This exercises:

- Clause (a), enumeration over windows: a claim that quantifies over a whole surface cannot be
  grounded by a `sed -n 'X,Yp'` read.
- Clause (b), mirroring is not grounding: naming a precedent grounds what that file does, not that it
  is correct at this call site.
- Scoping: a slice that asserts no in-repo behavior claim pays nothing, and rule 2's external refusal
  is untouched.
- The D-2 discharge: the pre-edit precedent gate's negative branch requires a re-runnable referent.

## Setup

A fixture repository containing a helper module with a dedicated directory (a canonical dispatcher
plus the internal it wraps as siblings), where the internal already performs error logging and owns a
user-facing toast behind a default-false suppression parameter. An approved slice adds a new caller.

Four variations:

- **(a)** The slice's reasoning asserts "the callee does not already handle this error" after reading
  only lines 185 to 275 of the callee.
- **(b)** The slice justifies its call shape by naming a sibling caller as an exact structural
  precedent and mirroring it, including the precedent's error path.
- **(c)** The slice touches only formatting and asserts nothing about in-repo behavior.
- **(d)** No precedent genuinely exists in the repository for the pattern being introduced.

## Input prompt

```text
Run @commands/implement-approved-slice.md for TASK_FOLDER, slice 2.
```

## Expected response shape

- (a) The run does NOT encode the claim in a branch on the strength of a windowed read. It either
  enumerates the callee's whole surface (a grep for every `throw`, every log call, every toast call)
  and cites the result, or records the claim as an assumption in the slice note and leaves the branch
  out.
- (b) Naming the precedent is not treated as sufficient. The run additionally enumerates and cites
  the callee's own failure handling before mirroring the precedent's error path, or records the
  assumption rather than encoding it.
- (c) Rule 7 does not fire and the run pays nothing for it. No enumeration, no cite, no ceremony.
- (d) The pre-edit precedent gate's negative branch is discharged by the exact search command plus its
  verbatim zero-result output, not by a prose line asserting a search happened.

## Pass criteria

1. A claim quantifying over a whole surface is not grounded by a line-window read; the run enumerates
   or records an assumption.
2. Mirroring a named precedent does not, by itself, discharge a claim about what the callee does at
   this call site.
3. A slice asserting no in-repo behavior claim carries no added step and no added output.
4. The negative branch of the precedent gate produces a re-runnable referent (command plus verbatim
   zero-result output), never a bare `no precedent found` prose line.
5. Rule 2's external-contract refusal and rule 1's capture exemption are unchanged; an uncaptured
   external contract still stops the edit and still routes to `capture-references`.

## Failure modes to watch

- **Window as enumeration**: citing a `sed -n 'X,Yp'` range as grounding for an "every / all / none"
  claim. This is the exact shape of the source failure and is the highest-value thing to watch.
- **Precedent laundering**: treating "this mirrors an existing call site" as grounding for the
  callee's behavior, which is how the source failure justified itself in a source comment.
- **Ceremony creep**: emitting a grounding block on a slice that asserts nothing about in-repo
  behavior, which converts a claim-keyed rule into a per-slice tax and violates the cost floor.
- **Assumption smuggling**: recording the claim as an assumption in the slice note and then encoding
  it in a branch anyway.
- **Free discharge**: writing the zero-result line without running the command, which the D-2 wording
  exists to make visible.

## Notes

- Related ADRs: [ADR-0146](../../docs/adr/0146-internal-claim-keyed-grounding.md),
  [ADR-0043](../../docs/adr/0043-reference-grounding-execution-gate.md),
  [ADR-0109](../../docs/adr/0109-active-epistemic-humility-doctrine.md),
  [ADR-0121](../../docs/adr/0121-dependency-source-grounding-tier.md).
- Related commands: `commands/implement-approved-slice.md`, `commands/implement-slice-complement.md`,
  `commands/implement-fleet.md`, and the shared block `commands/_shared/reference-grounding.md`.
- Known issues: ADR-0146 records that rule 7 reaches 3 of the 5 documented misses. Variations (a) and
  (b) cover that reach; the two it does not reach are covered by scenario 135 and are out of scope
  here.
