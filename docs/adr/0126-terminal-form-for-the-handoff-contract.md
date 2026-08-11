# ADR-0126: The handoff contract gains a terminal form

- **Status**: Accepted
- **Date**: 2026-08-05
- **Tags**: handoff, global-output-contract, routing-integrity, unattended, dogfood-driven, extends-adr-0050

## Context

Every `### Handoff` block ends with a `Run now` line, and `## Global output contract` requires that line to name the basename of a real file in `commands/`. The rule is deliberate and it earns its keep: it is what stops a model from inventing `finish`, `close-task`, or `execute-task` and sending a reader after a command that does not exist.

The rule has no exit. There is no contracted way for a command to say that the chain is over.

That gap stayed theoretical while a human read the handoff, because a human reads `Reason:` and stops. It stopped being theoretical when a driver started reading the line instead. On 2026-08-05 an unattended run walked six commands (`task-init`, `impact-analysis`, `implementation-plan`, `self-critique-and-revise`, `decision-interview`, `sync-task-state`) and then reached a state the contract cannot express: three decisions waiting on a maintainer, plus environment requirements the session could not supply. Continuing would have been motion without progress, and the agent said so in prose.

Then it had to fill in the block. It wrote:

```text
Run now: none
Mode: Ask, when a maintainer is present
```

Neither line is valid. The driver refused the unknown command name and aborted, which was the correct response to output it must not act on. But the agent had not made a mistake. It was handed a form with no field for the state it was actually in, and it did the most honest thing the form allowed.

Two details from that run shaped this decision.

**Two fields were unfillable, not one.** `Mode` is exactly `Ask | Plan | Agent | Debug`, and none of them describes a chain that has stopped. The agent wrote a sentence into the field. A terminal state needs somewhere to put the mode as much as it needs somewhere to put the route.

**The agent reached for `none` unprompted.** Nothing in the specification, the command bodies, or the driver's own instructions uses that spelling. It is what an unbiased reader of the contract produced when it needed the meaning, which is the strongest available evidence about which form is discoverable.

## Decision

Add `Run now: none` to `## Global output contract` as the single value on that line that does not name a `commands/` basename, paired with `Mode: N/A`.

- **It is an exception, stated as one.** The rule that `Run now` names a real command is unchanged for every other case, and the exception lives directly beneath it under `### Official command names (routing integrity)` so a reader meets both together.
- **`Reason:` carries the unblock.** A terminal block is not an empty one. It says what would let the work continue: which decision needs a human, which capability the environment lacks.
- **`Mode: N/A` is valid only in this pairing.** It is not a general escape from mode selection.
- **It does not replace a queued question.** A block that still routes somewhere routes there; `none` is for when nothing honest remains.

## Alternatives considered

**A separate `Chain: terminal` field.** Keeps `Run now` uniformly parseable as a command name, which is a real advantage for every consumer of the line. Rejected on cost distribution: it adds a field to every handoff every one of the 97 commands emits, so every run pays permanently to serve the terminal one. The exception concentrates the cost in the case that needs it.

**Leave the specification alone and fix only the driver**, treating a well-formed block with an unknown command as a governed stop rather than an abort. Cheapest option, and it does address the crash. Rejected because it leaves the agent with no honest way to end a chain: the next run reaches the same dead end and invents a value again, and the driver silently accepts whatever it invents. That trades a loud wrong answer for a quiet one.

**Route terminal states to an existing command** such as `task-close` or `where-we-at`. Zero specification change. Rejected because it is the failure mode this ADR exists to prevent: naming a command that is not really the next step is exactly what the routing-integrity rule forbids, and it would make every genuine stop indistinguishable from a real route.

## Consequences

`Run now` stops being uniformly parseable as a command name. Every consumer grows one branch, and that branch is the point: a driver can now tell a finished chain from a crash, and an operator chaining invocations can tell a finish from a stall.

The risk is overuse. `none` is easier to write than working out the real next command, and a command that reaches for it whenever the route is unclear would quietly convert routing failures into declared endings. The specification names this directly ("Do not use it to end a chain that has a real next step"), and the check is a run that ends terminal while work plainly remained.

This ADR changes the contract that all 97 commands inherit.

**Correction, 2026-08-05, same day.** This section originally read: "but requires no edit to any command body: they all reference `## Global output contract` rather than restating the format." That was wrong, and a `review-hard` pass over the shipping commit found it by checking the claim instead of trusting it. Two consumers restate the rule and both had to change:

- `commands/_shared/mandatory-context-bootstrap.md` says the `Run now` line "MUST be the basename of an existing `commands/<name>.md` file... Never invent names," and that shared block sits in 82 of the 97 command bodies. As first shipped, every command carried an instruction forbidding the form this ADR had just made valid, so the terminal form was reachable by a driver and unreachable by a command following its own body. The block now carries the exception.
- `scripts/validate-transcript.sh` resolved the basename against `commands/<name>.md` with no reserved-word branch, and failed a conforming terminal transcript (exit 1, "Run now basename does not resolve to a real command: none") where an otherwise byte-identical routing transcript passed silently. It now branches on the reserved word and enforces the `Mode: N/A` pairing in both directions, with three self-test fixtures.

The original wording is preserved above rather than rewritten, because the mistake is the useful part: this ADR predicted that "every consumer grows one branch" and then asserted no consumer needed one. Writing the prediction and the denial in the same document is how the gap survived to the commit.

## Provenance

The run behind this decision is preserved at `projects/bmazurok__fhorja-full-cycle/active/2026-07-30_driver-loop-to-draft-pr/DOGFOOD/run-13/` (gitignored, local), including the driver report and the agent's task memory. The corresponding locked decision is D-72 in that task's `DECISIONS.md`.
