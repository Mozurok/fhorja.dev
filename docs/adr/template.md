# ADR-NNNN: Short title

- **Status**: Accepted | Proposed | Deprecated | Superseded by [ADR-XXXX](./NNNN-other.md)
- **Date**: YYYY-MM-DD
- **Tags**: comma, separated, keywords

## Context

The forces at play that prompted this decision: constraints, prior incidents, observed friction, conflicting goals. Describe the situation as it stood **before** the decision was made. Use bullets when listing multiple forces; use prose when telling the story of how the question arose.

This section should make a future maintainer (or a contributor reviewing a PR that touches this decision) understand the problem before reading the resolution. If the context is no longer valid (technology changed, constraints relaxed), the ADR may be a candidate for "Superseded" status.

## Decision

The single, clear statement of what was chosen. One paragraph maximum. Avoid hedging; if the decision had qualifications, list them as bullets after the paragraph.

Where applicable, reference the exact mechanism that enforces the decision in the codebase (a specific file path, a lint rule, a CI step, a command's `Operating rules:`).

## Consequences

### Positive

- The benefits this decision unlocks. One bullet per benefit; concrete enough that a future reader could verify it (or notice when it stops being true).

### Negative

- The costs this decision imposes. Be honest. If a tradeoff was accepted, name it.

### Neutral

- Side effects that are neither clear wins nor losses, but worth recording for future readers.

## Alternatives considered

### Alternative 1: [short label]

- What it would have looked like.
- Why it was rejected (specific, not "it felt wrong").

### Alternative 2: [short label]

- What it would have looked like.
- Why it was rejected.

(Add more as needed; aim for the 2-3 strongest competing options, not an exhaustive enumeration.)

## References

- `WORKFLOW_OPERATING_SYSTEM.md` → `## <section>` (where the decision is enforced as normative content).
- `commands/<name>.md` (where applicable; the command file that operationalizes the decision).
- External link (if the decision was informed by upstream prior art; include accessed date for freshness).

## Notes

(Optional. Anything that does not fit cleanly above. Examples: the exact incident that triggered this ADR, a link to the discussion thread, the maintainer's confidence level when accepting, "revisit if X changes" reminders.)
