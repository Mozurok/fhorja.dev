# ADR-0194: The ignored-path waiver closes work that cannot be committed

- **Status**: Accepted
- **Date**: 2026-09-03
- **Tags**: commit-evidence, closure-enforcement, slice-closure, gitignored-scope, extends-adr-0084, beside-adr-0128, answers-adr-0133, measurement-driven

## Context

The commit-evidence floor admits four routes: `commit-ref`, `ref-attested`, a committing-waiver for
genuinely discardable work, and the three-condition no-VCS waiver of ADR-0128. Where none reaches,
the answer is the ADR-0100 bounded deferral, recorded as `deferred: pending human commit`.

There is a case none of the five expresses: a deliverable whose only home is a path the repository
deliberately and permanently ignores. Task memory under `projects/` is the standing example, made
gitignored on purpose by ADR-0007.

Measured 2026-09-03 in this repository:

- `git rev-parse --is-inside-work-tree` inside `projects/` returns **true**, so condition 1 of the
  no-VCS waiver, which requires that call to FAIL, cannot hold.
- `git check-ignore -v projects/` returns `.gitignore:27:projects/`, so `commit-ref` needs `-f`.
- `ref-attested` is routed as the answer for an external execution layer with no human turn; an
  attended session and direct-use `autonomous-run` are not sent there (ADR-0197).
- The committing-waiver covers only genuinely discardable work, which task memory is not.
- The bounded deferral therefore records `pending human commit` for a commit that is never coming.
  It does not terminate.

That last line is the defect. ADR-0128 already stated the principle for its own case: the fourth
route exists because `deferred: pending human commit` is FALSE in a workspace that will never have
a repository, and writing it there is the permanent-skip-disguised-as-bounded that ADR-0098 rules
out. The identical falsehood holds for a path that will never receive a commit. ADR-0128 drew its
condition 1 at the workspace when the property it needed was about the deliverable.

Five independent recurrences are on the record, by four different authors of it: the live block in
`acme__landing/2026-08-13_pt-br-three-language-compositions`; the 2026-08-08
`task-init-load-stage-headroom` task, which named it in these exact terms across slices 02, 04 and
05 and carried it into its `## Recommended next step` as item 2 of a fix program; the 2026-08-08
`fhorja-landscape-rescan-and-full-audit` task; and two tasks that worked around it by writing that
the deferral wording would be false rather than recording one.

ADR-0133 saw the question and declined it deliberately: it "does not name the gitignored-Scope
structural exemption as a further route", because whether work is committable at all is a different
question from who may attest it, and bundling them would produce one ADR that cannot be reverted
without reverting both. This is that separate ADR.

## Decision

A fifth route, the **ignored-path waiver**, recorded as
`ignored-path waiver: <deliverable path> (<ignore file>:<line> <pattern>)`. All three conditions
must hold:

1. **The path is provably ignored and the ignoring pattern is committed.** `git check-ignore -v`
   succeeds on the deliverable path and its output is cited verbatim, and the matching pattern is
   present in the ignore file at HEAD rather than in an uncommitted working-tree edit. Both halves
   are facts the command CHECKS. The second exists so a run cannot write its own exemption into
   `.gitignore` and then invoke this route.
2. **The ignored path is the deliverable's only home, and the deliverable is not derived from
   anything committable.** Build output fails: `dist/bundle.js` is ignored, but it is produced from
   a committable source, so the slice's work IS committable and this route does not apply. The
   question is never whether the artifact is ignored; it is whether a committable form of the work
   exists anywhere.
3. **The preserved work is named**, so a later reader can find it. Verbatim from ADR-0128.

It carries no verbatim user decision, which is the one place it departs from the shape of ADR-0128,
and the departure is the point rather than an omission. That condition exists there to disambiguate
a missing `.git`, which reads equally as "never" and as "not yet". A committed ignore pattern has no
such ambiguity: it is the decision already written down, and condition 1 makes the command read it.
Requiring the user to restate it in session would either block the route or invite a fabricated
quote.

**What does not change.** The route never fires because the operator is absent, forbidden, or
unattended; each of those stays on the bounded deferral, which is ADR-0100's case and is not
reopened. It does not travel to `task-close`, exactly as ADR-0128's does not: it is evidence that
home reads, never a route that satisfies it, so the archive-with-waiver authorization is still
required there. ADR-0128 is untouched and keeps its own three conditions.

## Consequences

### Positive

- A slice whose deliverable cannot be committed can now close honestly instead of recording a
  deferral that asserts a commit is coming.
- The floor stops producing a state with no exit, which is what five separate task records
  worked around by hand.
- Condition 2 is the load-bearing one and it is checkable by asking a single question about the
  work rather than about the artifact.

### Negative

- Condition 2 is a judgment where conditions 1 and 3 are facts. A slice that mislabels derived
  output as its only deliverable reaches a route it should not. Bounded by condition 1 being
  mechanical, by the named-paths requirement making the claim inspectable, and by the route not
  travelling to `task-close`.
- A fifth route is more surface on a floor whose value comes from being hard to satisfy. The
  honest reading is that the floor had a hole rather than four sufficient routes.

### Neutral

- No command file changes. The floor text lives in `wos/closure-floors.md` and reaches the three
  homes through the generated views.
- Per-home routing prose is untouched, so `check_commit_evidence_routes_to_apply` still sees both
  required routes in every home.

## Alternatives considered

### Alternative 1: widen ADR-0128's condition 1 from the workspace to the deliverable path

- Rejected. It puts two different fact patterns under one set of three conditions, and condition 2
  does not fit the second: there is no user decision to record for a repository-level ignore, so
  the widened rule would either block or invite an invented quote. ADR-0133 also read this as a
  separate question on its own terms.

### Alternative 2: leave it and keep recording bounded deferrals

- Rejected on measurement. Five recurrences and one still-live block, plus two records that
  declined to write the deferral because it would be false. The workaround is already the practice;
  this writes down what people were doing anyway.

### Alternative 3: commit the deliverable with `git add -f`

- Rejected. It defeats an ignore the repository set on purpose, and for `projects/` it would put
  per-user task memory into a distribution tree that ADR-0007 keeps it out of.

## References

- [ADR-0084](./0084-godot-flow-completeness-wave.md): the commit-evidence floor this extends.
- [ADR-0100](./0100-commit-evidence-floor-bounded-deferral.md): the bounded deferral, unchanged.
- [ADR-0128](./0128-no-vcs-workspace-waiver-at-the-slice-level.md): the sibling waiver, untouched.
- [ADR-0133](./0133-ref-attested-commit-evidence-for-the-autonomous-track.md): named this question and left it open.
- [ADR-0098](./0098-feel-experience-verdict-bounded-vs-permanent-skip.md): permanent-skip-disguised-as-bounded.
- `wos/closure-floors.md`: the rule.
