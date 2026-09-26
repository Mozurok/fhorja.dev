# ADR-0209: Floors do what they declare

- **Status**: Accepted
- **Date**: 2026-09-16
- **Supersedes**: ADR-0119 in part. The Godot tier-declaration floor no longer fails closed and a
  malformed declaration block is no longer unwaivable; both are now recorded and closure proceeds.
  ADR-0119's canonical-form rules (one fenced block, the two permitted keys, the exact tier strings)
  are unchanged.
- **Completes**: ADR-0203, which declared three behaviors per floor and did not rewrite the normative
  bodies those declarations govern.
- **Tags**: closure-floors, adr-0203, adr-0119, record, reconcile, refuse, blinded-verification

## Context

ADR-0203 gave every closure floor an `On missing evidence:` line reading record, refuse or reconcile,
and stated which floors were which. It did not rewrite the variant bodies underneath those lines.

For one day the result was a corpus that announced one behavior and mandated another. Eleven of the
fifteen floors declared record or reconcile and then instructed a consumer to hold the slice, across
57 phrases: `SHALL NOT close inline`, `classify the slice not ready to close`, `do NOT archive`,
`SHALL BLOCK`, `FAILS CLOSED`. A reader following the declaration recorded. A reader following the
normative sentence blocked. Both readings were supported by the same file.

The task that shipped ADR-0203 recorded in its own closure that nine floors now record. They declared
it. Eleven of them did not do it.

It was found by reading rather than by searching. A corpus sweep over `wos/` read all 55 files one at
a time, specifically because a pattern pass had already cleared four of them. No grep tried against
this defect found it, and several narrower ones reported the corpus clean while it was not.

## Decision

A floor's normative body carries the behavior its own declaration line names.

Where a floor declares `record`, an absent evidence writes `unverified: <reason>` and closure
proceeds. Where it declares `reconcile`, the unsatisfied constraint becomes a named deferral and
closure proceeds. Where it declares `refuse`, nothing changes.

Each clause keeps the command it already routes to. The verdict moves; the remedy does not. Two
clauses inside one floor can route differently, and the Layer-2 review floor and the Godot
runtime-gate floor both do.

A recorded skip stays a distinct outcome from an `unverified` record. A skip says a person considered
the check and it does not apply. An `unverified` record says nobody performed it. The final report is
where that difference is read, so collapsing the two would lose the only signal separating a
deliberate exemption from an omission.

The Godot tier-declaration floor is the one case where a body argued for itself rather than reading
as an oversight, and ADR-0119 decided that argument. It is overridden here on that floor's own
declaration rationale, which states ADR-0203's refuse test in the negative: a missing tier declaration
is a missing statement, not lost work. A floor that records has nothing left to waive, so the
unwaivable-malformed rule goes with it. The floor now names what it replaces rather than deleting it,
because a reader who knows that history would otherwise read the change as an accident.

## Consequences

The three refuse floors (commit-evidence, integrity, unresolved-revision) and the Godot feel-verdict
floor are untouched, and `scripts/tests/test-closure-floor-ledger.sh` check 12 now asserts they still
block. That check is not decoration: a rewrite that turned every floor into a recorder would have
passed the check asserting no floor contradicts itself, while removing the four gates that prevent
losing work rather than adding friction.

Check 12 also produced this decision's sharpest correction. It failed at 3 of 4, because the integrity
floor says `SHALL NOT be archived` and ``is not `ready to close` ``, and neither form was in the
pattern. Widening it to the idioms the corpus actually uses then showed the Godot tier-declaration
floor still contradicting in three places, one of them a verbatim quotation of the superseded rule
that a checker cannot distinguish from a live one. Both checks now read a single idiom list
enumerated from the corpus rather than guessed.

The plan for this work was approved with no human turn, on three blinded review rounds. Every round
returned every slice authorized and found feasibility defects instead: an intermediate state lint
exits 1 on, a dependency naming a folded slice, a count-marker carrier missing from a scope, and this
supersession, which nothing had recorded until the third round read ADR-0119 and matched its Decision
against what the work removes.

## Alternatives considered

Rewrite the declaration lines to match the bodies instead, making eleven floors refuse again. Rejected:
ADR-0203 chose those behaviors deliberately and on evidence, and the bodies are what was left behind.

Leave it and document the discrepancy. Rejected: in `wos/` the normative text IS the behavior, so a
documented discrepancy is two contracts rather than one explained.

## References

- ADR-0203 (the decision this completes), ADR-0119 (superseded in part), ADR-0205 (the final report
  that makes recording safe), ADR-0206 (a rule with no checker drifts back), ADR-0208 (the blinded
  review that found the supersession).
