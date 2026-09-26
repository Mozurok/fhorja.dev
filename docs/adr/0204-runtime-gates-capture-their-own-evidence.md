# ADR-0204: A runtime gate captures its own evidence, or returns BLOCKED

- **Status**: Accepted
- **Date**: 2026-09-16
- **Tags**: runtime-verify, evidence-capture, golden-baseline, adr-0048, adr-0085
- **Supersedes**: None. It changes how the four runtime-verify commands obtain evidence, not what counts as evidence.

## Context

The four `*-runtime-verify` commands stopped and asked the human to paste the real run output,
because a claimed-but-not-shown run is unverified. The rule was right and the mechanism made the
person a transport for a log.

Capture tooling exists per surface: browser automation for the web, request and response recording
plus schema conformance for an API, platform log capture for mobile. Godot is the exception and was
measured as such.

## Decision

WHERE a capable tool is available for the surface, the command captures the evidence itself, writes it
under `<task-folder>/evidence/<slice-id>/`, and cites the artifact path.

IF no capable tool is reachable THEN it returns BLOCKED naming the missing capability, and routes. It
does NOT record a PASS. A BLOCKED verdict here is an honest statement about missing evidence, not a
human gate.

WHERE the check is visual, a GOLDEN BASELINE is required. A screenshot with no bug-free reference
yields 34 to 50 per cent median precision against 100 per cent with one, so capture without a
reference produces an artifact rather than a check.

The split between mechanically-checkable and judgment criteria is declared STATICALLY per battery
rule. An agent classifying its own criteria per run is self-assessing its own capability at a
decision boundary, which ADR-0202 rules out.

An API probe runs only against a local or development instance; a non-local target is recorded
`unverified: non-local target` and not probed.

## Consequences

Positive. The evidence the closure floors want is now producible by the run, which is what makes
ADR-0203's `record` behavior honest rather than a quiet skip.

Negative. Godot has no mature capture path: headless uses a dummy display server and renders no real
frame, so its visual half is BLOCKED by default pending one measured attempt. That is recorded on the
floor itself rather than hidden.

Neutral. The evidence lives in the task folder, which is gitignored, so it is available to the person
who ran the task and not to a reviewer elsewhere.

## Alternatives considered

Keep asking the human to paste the output. Rejected: it is the stop this arc removes, and the human
adds nothing to a log they are copying.

Capture and treat a missing tool as a pass. Rejected: that is the silent-pass failure the BLOCKED
route exists to prevent.

## References

- ADR-0048: evidence layering, unchanged by this.
- ADR-0085, ADR-0106, ADR-0127: the platform runtime floors this feeds.
- ADR-0203: the closure behavior that depends on this capture existing.
