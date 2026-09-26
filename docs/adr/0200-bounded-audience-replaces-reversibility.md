# ADR-0200: An act is gated on bounded audience, not on reversibility

- **Status**: Accepted
- **Date**: 2026-09-16
- **Tags**: stop-reasons, egress, confirmation, draft-pr, mcp
- **Supersedes**: None

## Context

This corrects the stated criterion in reason 1 of the four allowed stop reasons without changing which acts gate.

ADR-0186 lists an outward OR irreversible act as the first reason a chain stops. A 2026-09-16 pass
reclassified a local commit, a task-branch push and a draft PR as un-gated, and argued it from
reversibility.

That inference does not follow from the rule as written. A push under the maintainer's identity to a
shared host is outward whether or not it can be undone. External research the same day found the
conclusion survives and the reason does not: a published wiki page is reversible and does not clear,
while an unrecoverable local commit reached nobody.

## Decision

An act clears and the command proceeds when the set of people it reaches is BOUNDED. It gates when
that set is open.

Bounded: a local commit, a push to a task branch, a draft PR that notifies nobody. Open: marking a
draft ready for review, MCP egress, publishing a page.

Undo decides nothing, in either direction.

A draft PR clears ONLY where the target repository fires no publishing workflow on
`pull_request: opened`. Checking that is the command's duty, not an assumption it may make.

MCP egress keeps its same-turn confirmation, and the confirmation displays the RAW payload and the
exact destination rather than the agent's summary of them.

## Consequences

Positive. The remaining PR stop moves from opening the PR to marking it ready, which is where the
audience boundary actually sits: GitHub does not request code-owner review on a draft.

Negative. The per-repo workflow check is a real cost on every draft-PR decision, and it was verified
for no repository when this was written.

Neutral. The set of gated acts is nearly unchanged; what changed is the reason, which is what a future
reviewer would have challenged.

## Alternatives considered

Gate on irreversibility alone. Rejected: it clears a published page, because pages can be deleted.

Gate on both, requiring either. Rejected: that is the current text, and it is what let a reversibility
argument clear an outward act.

## References

- ADR-0186: reason 1, whose stated criterion this corrects.
- The 2026-09-16 external research synthesis, contradictions 3 and 5.
