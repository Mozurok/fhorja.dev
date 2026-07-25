# ADR-0115: contract-fixing examples are exempt from any example-reduction fold

- **Status**: Accepted
- **Date**: 2026-07-25
- **Tags**: context-engineering, examples, contract-fixing, judgment-illustrating, substrate-write-protocol, extends-adr-0093

## Context

The 2026-07-25 context-engineering frontier sweep's adversarial angle A2 tested the anchor post's claim that examples inside a system prompt narrow a model's exploration space and should generally be cut. The claim did not survive its own evidence base: the one controlled study cited found models tend to ignore chain-of-thought exemplars rather than being constrained by them, a different causal story from the anchor's; the second source is a secondhand, unverifiable opinion-piece number. Fhorja is already largely clear of the one concrete failure mode the weaker source names, since its canonical output templates use angle-bracket placeholder schemas rather than filled worked examples.

One place the general claim would be actively wrong: `commands/_shared/substrate-write-protocol.md` carries a byte-exact filled example of the transaction header and the JSONL audit line, read deterministically by `scripts/emit-substrate-write.sh` (its parsing logic spans lines 90-95 and 261-303 of that script). Applying an example-reduction fold to that block on context-engineering grounds, without a boundary, would break the audit chain the substrate write cycle depends on. The block exists to constrain the exploration space to exactly one shape; that is the entire point of it, not a defect to trim.

The exemption is not a Fhorja invention. The OpenAI GPT-5.6 prompting guidance, one of the sources this sweep drew on, names "instructions that encode product requirements" as a class worth preserving even under general terseness pressure. A machine-parsed template is a product requirement encoded as an example.

The simplest alternative, leaving the boundary implicit and judging each case at review time, was considered and rejected: the boundary would then live only in an archived task synthesis, invisible the next time a context-engineering fold is proposed, and nothing would stop that future fold from applying the general claim to `substrate-write-protocol.md` and quietly corrupting the one surface where an example's exact bytes are load-bearing.

## Decision

**(a) Classify every command-file example into one of two classes, stated in `WORKFLOW_OPERATING_SYSTEM.md`.** A contract-fixing example is one whose exact shape (bytes, field order, delimiters) is parsed by a script or validator elsewhere in the repository. A judgment-illustrating example is everything else: a worked case that helps a reader calibrate tone, depth, or a borderline decision, with no downstream parser depending on its literal text.

**(b) Exempt the contract-fixing class from any fold that reduces examples on context-engineering grounds.** A future pass that trims worked examples for token or attention-budget reasons applies to judgment-illustrating examples only. A contract-fixing example, `commands/_shared/substrate-write-protocol.md`'s transaction-header and JSONL example being the concrete instance on file today, is out of scope for that kind of fold; changing it is a protocol change, reviewed and coordinated with `scripts/emit-substrate-write.sh`, not a context-engineering trim.

**(c) State it as an exemption, not a mandate.** The rule does not instruct a future fold to cut every judgment-illustrating example it finds. It draws a boundary around the one class that breaks something mechanical when touched, leaving judgment-illustrating examples to be judged on their own merit each time, the same as before this ADR.

## Consequences

- `WORKFLOW_OPERATING_SYSTEM.md` gains a durable, inline classification rule that a future example-reduction fold can consult without re-deriving the boundary from an archived task's research.
- `commands/_shared/substrate-write-protocol.md`'s worked example is now explicitly protected by name in the decision record, not only by the accident that no fold has touched it yet.
- The rule composes with ADR-0093's four-operation context-engineering vocabulary (write, select, compress, isolate): an example-reduction fold is a form of `compress`, and this ADR narrows what `compress` is allowed to touch.
- Accepted residual: the rule names one concrete contract-fixing example today. Future command authors carry the burden of classifying new examples correctly as they write them; nothing in this ADR adds automated detection of which class a new example falls into.
