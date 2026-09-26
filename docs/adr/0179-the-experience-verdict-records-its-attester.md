# ADR-0179: the experience-verdict floor records who attested, instead of pretending a commit did

- **Status**: Accepted; supersedes in part the attester clause of [ADR-0161](./0161-express-experience-verdict-at-apply.md) and the human-bound attester of [ADR-0091](./0091-experience-gates-generalized.md). Does NOT supersede [ADR-0048](./0048-deterministic-gate-evidence.md).
- **Date**: 2026-08-30
- **Tags**: closure-floors, experience-verdict, attester, evidence, express, adr-0091, adr-0161

## Context

The experience-verdict floor contradicted itself inside a single paragraph, in all three of its
variants. It said machine-green evidence SHALL NOT substitute for the human verdict, and then, two
sentences later, that on attended Express the floor stands down in favor of the local commit
`branch-commit --apply` creates, because "that commit is the attester".

A commit the agent itself created is machine evidence. So the paragraph forbade the substitution
and performed it.

The owner named the cost of resolving it the other way. Requiring a person on every user-facing
slice means a text change or a button label needs someone to confirm the button is there. That is
not a gate, it is a toll. What the owner asked for instead: the run captures its own evidence,
evaluates it, records it, and continues; the human verdict becomes a complement the operator can
add when it is worth adding.

The floor's real requirement was never the person. It was that a reader can tell who attested. The
2026-07-10 connector dogfood, which ADR-0091 and ADR-0089 D-4 exist to prevent, shipped four
machine-authored session packs with no human validation of one AND nothing recording that. The
second half is the defect. A run that says plainly "I checked this myself, here is what I captured"
is honest; a run that lets a reader assume a person looked is not.

## Decision

The floor requires an attester to be RECORDED, not to be human.

1. **The false claim goes.** `that commit is the attester` is deleted from all three variants. The
   sentence it shared a paragraph with stays as written: machine-green evidence still does not
   substitute for a human verdict, because under this decision it no longer pretends to be one.

2. **`## Experience verdict` carries a mandatory `Attested by:` line**, valued `run` or `human`.
   `run` is valid only when the block cites the evidence the run itself captured: the screenshot
   path it wrote, the runtime output it quoted, the route it probed. That is the ADR-0048 contract
   applied to this floor, not an exception to it.

3. **`Attester class:` becomes `agnostic`.** The vocabulary already exists in
   `wos/gate-conditions.md`: agnostic means any attester satisfies the floor, provided it is
   recorded. `human-bound` was the wrong word for a floor whose point is the record.

4. **The Express special case disappears.** The three variants lose
   `WHILE the pipeline is attended Express ... this floor stands down`. The floor now applies on
   every path and is cheap on all of them, because the run can attest. Keying the requirement to
   the pipeline was always a proxy for keying it to risk, and a bad one.

5. **Human attestation never blocks.** It can be added before or after closure. A run does not wait
   for it.

The invariant that survives, and the one the check enforces: an artifact may never claim a human
verdict that did not happen. `Attested by:` is mandatory and machine-checkable, so `Overall: PASS`
without a valid attester is invalid output.

The Godot feel-verdict floor (ADR-0089 D-4, in `wos/platform-runtime-floors.md`) stays
`human-bound` and is not touched. Measured 2026-08-30: it is the only other `human-bound` floor on
disk. Whether a build FEELS right is not something a run can capture, and the owner's example was a
button's existence, not a game's feel.

## Consequences

### Positive

- The contradiction is gone, and it is gone by making the weaker claim true rather than by deleting
  the stronger one.
- The cost of the gate now scales with what the deliverable is, instead of with which pipeline ran.
- A reader of any closure artifact can tell who attested, which is what the 2026-07-10 failure
  actually lacked.

### Negative

- `Attested by: run` is a claim a run makes about itself. The check can verify the field is present
  and valid; it cannot verify the evidence cited is genuine. That is the same trust boundary
  ADR-0048 already lives on, not a new one.
- Three variants and one generated view set change together. The views are regenerated, never
  hand-edited.

### Neutral

- No command gains or loses a step. The floor's text changes and a field becomes mandatory.

## Alternatives considered

### Alternative 1: E2.A, the human attester comes back unconditionally

- Delete the stand-down, keep `human-bound`, require a person on every tagged slice.
- Rejected by the owner: it puts a human stop on a button-label change. The floor would be honest
  and unaffordable, and an unaffordable gate gets skipped, which is how decorative skips are born.

### Alternative 2: E2.B, split the floor and say in the README that Express has no attester

- Add an `Attester class:` line per variant and declare the gap publicly.
- Rejected: it records the absence of a human rather than the presence of an attester. The run DID
  look at something; refusing to name that is as inaccurate as pretending a person did.

### Alternative 3: keep the stand-down and reword the commit sentence

- Say the commit is "evidence" rather than "the attester".
- Rejected: it renames the problem. A commit created by the agent still attests nothing, and the
  floor would still key on pipeline rather than on what was verified.

## References

- [ADR-0091](./0091-experience-gates-generalized.md): the floor this qualifies.
- [ADR-0161](./0161-express-experience-verdict-at-apply.md): the stand-down this removes.
- [ADR-0048](./0048-deterministic-gate-evidence.md): evidence, not trust. Unchanged and relied on.
- [ADR-0089](./0089-godot-e2e-completeness-wave.md): D-4, the Godot feel-verdict floor, which stays human-bound.
- [ADR-0098](./0098-feel-experience-verdict-bounded-vs-permanent-skip.md): the bounded-versus-permanent skip rule, unchanged.
- `wos/gate-conditions.md`: the `Attester class:` vocabulary this uses.
