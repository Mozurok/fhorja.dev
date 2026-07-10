# ADR-0026: APPLIED-by-default for implement-approved-slice in Agent mode

Status: Accepted (2026-05-26)

Addendum to: ADR-0001 (PROPOSED-by-default)

## Context

Transcript analysis of the Fhorja development session showed 76 APPLIED artifact changes, 5 PROPOSED, and 0 rejections. The `/approve-proposed` command was never invoked. The PROPOSED review cycle for slice execution notes added ~3,000-4,000 tokens of inline markdown content that was never reviewed or rejected.

ADR-0001 established PROPOSED-by-default as a safety mechanism to prevent surprise writes. This was the correct default for discovery and planning commands in Ask/Plan mode, where the user reviews output before authorizing persistence. However, `implement-approved-slice` in Agent mode represents a fundamentally different authorization model: the user already authorized the execution by pasting the handoff block and invoking the command in Agent mode. The authorization signal is the invocation itself.

## Decision

`implement-approved-slice` running in Agent mode uses **APPLIED** by default for slice execution notes (slice files under SLICES/, TASK_STATE.md phase/status updates).

This exception is scoped to:
- Command: `implement-approved-slice` only
- Mode: Agent mode only
- Artifacts: slice execution notes and TASK_STATE.md updates only
- Product code: unchanged (follows repo reality, not the write policy)

All other commands retain PROPOSED-by-default per ADR-0001. `implement-approved-slice` in Ask/Plan mode also retains PROPOSED-by-default.

## Consequences

### Positive
- Eliminates ~3,000-4,000 tokens of PROPOSED review overhead per session with zero observed corrective value
- Aligns the write policy with the actual authorization model (handoff invocation = authorization)
- Reduces the need for `/approve-proposed` or re-run-in-Agent-mode ceremony for slice notes

### Negative
- Slice notes are written without explicit review. If the notes are wrong, the user must edit them manually (mitigated: notes are operational metadata, not behavioral contracts)
- Reduces the "pause and review" moment between slices (mitigated: inline exit criteria check in Slice 2 of the wos-friction-reduction task provides the review moment)

### Neutral
- ADR-0001's core principle ("the cost of surprise writes is asymmetric") remains valid for all other commands
- The 3 valid paths to turn PROPOSED into APPLIED (re-run in Agent, /approve-proposed, manual copy) remain available for all other commands

## References
- ADR-0001 (PROPOSED-by-default): the global default this ADR creates an exception to
- ADR-0024 (approve-proposed idiom): the batch-persist shortcut that this ADR makes unnecessary for implement-approved-slice
- Fhorja transcript analysis: Category B findings (B3: 0% rejection rate, /approve-proposed never used)
