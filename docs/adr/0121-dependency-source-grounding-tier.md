# ADR-0121: A dependency's published source is an admissible grounding tier, cited locatably

- **Status**: Accepted
- **Date**: 2026-07-29
- **Tags**: grounding, evidence-priority, reference-grounding, epistemic-humility, absorption, extends-adr-0043, extends-adr-0109

## Context

Fhorja requires an executor to ground every external contract before editing, and enumerates what
counts. `commands/_shared/reference-grounding.md` rule 6 names the grounded set as "a captured
`REFERENCES.md` entry, a doc read this session, or a live capture per rule 5". Rule 2 makes the gate
refusing: an uncaptured contract means the executor must not edit, and routes to `capture-references`.

Every admissible item in that set is either a description of the library (documentation, or a captured
summary of documentation) or a runtime observation of it (a live capture per rule 5). The artifact that
actually defines the behavior, the library's own published source, is absent from the enumeration. Not
forbidden: absent. There was no mechanism to reach it, so there was nothing to enumerate.

The consequence is narrow and specific. When a captured entry marks a field `[unclear in source]`,
because the vendor's documentation does not state it, the executor has no next step short of rule 5's
live capture, which is expensive (real credentials, a webhook capture endpoint, or vendor confirmation)
and deliberately scoped to security-critical or fully-gating paths. A version number that the docs
simply omit does not warrant that machinery, and the executor is left inferring from model memory,
which ADR-0109 explicitly rules outside the grounded set.

The gap is self-demonstrating. Both external sources captured on 2026-07-29 for the task that produced
this ADR carry `Version: [unclear in source]`, because neither page states one.

The prompt was an outside tool (`opensrc`, vercel-labs) whose entire premise is fetching and caching a
package's real source so an agent can grep it. The tool itself is not adoptable here: locked decision
R-1 in the archived `2026-07-01_llm-tooling-repos-absorption-analysis` rejected six runtime cores on
the grounds of "no runtime services, no vector DB, no hosted backends, no new Python dependencies",
and a Rust CLI installed via npm sits squarely inside that reject set. The technique is separable from
the tool, and separating them is the whole content of this decision.

## Decision

A dependency's published source becomes an admissible grounding tier, recorded in both normative
surfaces, and every claim grounded in it carries a locatable cite.

1. `commands/_shared/reference-grounding.md` rule 6 gains the tier in its enumeration of the grounded
   set, and `WORKFLOW_OPERATING_SYSTEM.md ## Evidence priority` gains the matching entry. Both, not
   one. Editing rule 6 alone would leave the execution gate and the normative evidence ranking
   disagreeing about what counts as grounding, which is a contract conflict rather than a partial
   improvement.

2. The tier is ADDITIVE. Rule 2's refusal is unchanged: an external contract absent from
   `REFERENCES.md` still stops the edit and still routes to `capture-references`. Reading source is
   not a substitute for capture, and the rule text says so where an executor will read it.

3. A claim grounded in source carries a `Grounded in:` cite naming the file path, the line range, and
   the version read. Every other tier produces a checkable referent; this one must too. ADR-0109 holds
   that support which is not observable does not count even when the claim is correct, so a bare
   assertion of having read a library's source cannot satisfy the gate.

4. The rule is capability-routed and names no tool. How an operator obtains a dependency's source is
   unspecified, exactly as the workflow leaves every other capability unspecified.

## Consequences

The `[unclear in source]` case gains a cheap resolution path that did not exist, sitting between a
captured doc summary and rule 5's live capture in both cost and authority.

The cite requirement adds friction to the tier deliberately. An executor that cannot name a path, a
line range, and a version has not done the thing the tier describes, and the cite is what makes the
difference visible to a reviewer.

The grounded set is now enumerated in two files that must be kept in agreement. That is a maintenance
cost accepted knowingly, and the alternative (one canonical list, referenced from the other) was
rejected below.

Nothing about rule 2, rule 5, or the human gates changes. A reader who only cared about those is
unaffected.

## Alternatives considered

**Edit rule 6 alone, leave `## Evidence priority` untouched.** Smaller surface, one file, no ADR. It
was rejected because the two documents would then answer the same question differently, and the
execution gate is the one an executor reads under time pressure while the spec section is the one a
command author reads when writing a new rule. A disagreement between them is invisible until it
produces a wrong decision.

**Require the source excerpt be captured into `REFERENCES.md` before it counts.** This needs no new
verification concept, since the captured entry is already a checkable referent. It was rejected as the
primary form because it collapses the tier into the mechanism it was meant to supplement: the executor
would stop, run `capture-references`, and be back where the gap started. It remains available and is
strictly better when the same source fact will be needed by a later task, since a captured entry
outlives the session.

**Adopt the tool.** Rejected by R-1 without needing a fresh argument. Recorded here only so a future
reader does not mistake the omission for an oversight.

## References

- `commands/_shared/reference-grounding.md` (rules 2, 3, 5, 6)
- `WORKFLOW_OPERATING_SYSTEM.md ## Evidence priority`
- [ADR-0043](./0043-reference-grounding-execution-gate.md): the execution-time grounding gate this extends
- [ADR-0109](./0109-active-epistemic-humility-doctrine.md): ground-or-abstain, and provenance rather than confidence
- `projects/bmazurok__my-work-tasks/REFERENCES.md`, entry "opensrc: Give coding agents access to any package's source code" (captured 2026-07-29)
- Locked decision R-1, `archive/2026-07-01_llm-tooling-repos-absorption-analysis/DECISIONS.md`

## Notes

The prompting comparison also examined Greptile's Agent Skills in the same read. Its `greploop`
convergence mechanism was declined: three of its four properties already exist in
`commands/_shared/convergence-policy.md`, and the fourth (one artifact iterating against an external
grader, rather than many workers converging into one merge) belongs to the task already in discovery
on that axis. The two folds that did survive from that source are unrelated to this ADR and land in
`commands/pr-feedback-ingest.md`.
