# ADR-0201: A cost or retry ceiling warns and continues

- **Status**: Accepted
- **Date**: 2026-09-16
- **Tags**: bounded-retry, max-fanout, cost-ceiling, stop-reasons
- **Supersedes**: None.

## Context

Four ceilings stopped the session and asked a human: the bounded retry in the runtime-verify
skeleton, the `max_fanout` overflow in the orchestrator bootstrap and in `atom-audit-fleet`, and the
token-estimate consent prompt in `code-context-map`.

Each exists for a real reason. The retry cap prevents an unbounded hold-until-pass loop; the fanout
cap bounds concurrency; the token estimate warns about cost. None of those reasons requires
interrupting the person.

## Decision

A ceiling records its state and proceeds. It SHALL NOT request human input.

The repetition guard survives, and it is what the cap now does: at the bounded-retry cap the command
records the failure with the evidence already captured and routes the fix, rather than repeating the
same run. Both fanout overflows split into sequential sub-batches. `code-context-map` produces the
bounded map by default and leaves the full fan-out as an explicit request.

## Consequences

Positive. A long chain no longer stops at a threshold whose only message is that a threshold was
reached.

Negative. A user who wanted the fan-out now has to ask for it, where before the prompt offered it.
That is a deliberate trade: the prompt was a stop, and the bounded map is useful output.

Neutral. Silent truncation stays forbidden everywhere it was forbidden before.

## Alternatives considered

Drop the ceilings entirely. Rejected: a hold-until-pass loop with no cap repeats the same failing
action indefinitely, which is a worse failure than an interruption.

Keep the ceilings and shorten the prompts. Rejected: a shorter stop is still a stop.

## References

- ADR-0186: reason 3, which this keeps while removing the interruption.
- `wos/gate-conditions.md`, interactive bounded retry.
