# ADR-0171: An advisory either can fail the build or leaves the lint

- **Status**: Accepted
- **Date**: 2026-08-30
Supersedes, in part: ADR-0147 (D-2's `Gate-provenance:` lint line, not the trigger rule it measured)
- **Tags**: lint, advisory, warn-only, signal-to-noise, removal, tooling

## Context

`scripts/lint-commands.sh` grew a tail of warn-only delegates. Each was added for a good reason: surface a measurement, do not block anyone, decide later whether to enforce it. Later never came for some of them.

A 2026-08-29 audit measured what those lines actually produced. Three had never caused a change to anything. `Natural-voice` reported hits that have been on disk since 2026-05-25 and survived hundreds of commits. `Gate-provenance` reported uncited gates that nobody cited afterwards. `Clarify` counted inline markers inside task folders, and paid for it with a recursive scan over a 1.4 GB directory on every single lint run.

A number that never changes a decision is not information, it is furniture. Worse, it teaches the reader that the tail of the lint output is skippable, which is the habit that hides the lines that do matter.

The rule is not "advisories are bad". Several earn their line: `Mirror-guard` refuses a leaking tree, `Instruction-budget` watches files loaded into every session, `Substrate-ownership` measures a surface other work depends on, `Skill-triggers` measures an open roadmap item.

## Decision

A checker earns a line in the lint output if it either can fail the build, or reports a number someone is going to act on. A checker that can do neither leaves the lint and stays on disk as a standalone measurement tool.

Applied now: `Natural-voice`, `Gate-provenance` and the `Clarify` marker count leave the lint output. `scripts/check-natural-voice.sh` and `scripts/check-gate-provenance.sh` stay in the repository and are run by hand, the way `scripts/check-mcp-pins.sh` and `scripts/check-substrate-retention.sh` already are.

`Skill-triggers` stays. It is the only measurement of a roadmap item that is still open, and deleting the gauge for open work is worse than the noise it makes.

The normative natural-voice rule is untouched. What leaves is the sentence promising a lint line, not the rule the line was measuring. The rule lives in the spec and the catalog lives in `wos/natural-voice.md`, and both stay exactly as they are.

Removing a checker's lint line is not a decision to stop caring about what it measured. It is a decision to stop pretending a number nobody reads is enforcement.

## Consequences

### Positive

- The lint tail is short enough that a reader reaches the end of it.
- One lint run stops walking a 1.4 GB directory to produce a number nobody acted on.
- The remaining advisory lines mean something, so a change in one is worth looking at.

### Negative

- Natural-voice drift and uncited gates now need someone to run a script on purpose. Nothing reminds them.
- A future reader may read the removal as the repository not caring about natural voice. This ADR is the answer to that, and the spec rule is the other one.

### Neutral

- Both scripts keep working and keep their flags. Only the lint's call site goes.
- The count of advisory lines is not a target. Adding one back is fine when it meets the rule.

## Alternatives considered

### Alternative 1: promote the three to FAIL tier

- Make natural-voice hits and uncited gates fail the build.
- Rejected: natural-voice is a judgement call with false positives by design, and the gate-provenance heuristic is narrower than the mechanism it describes. Failing a build on either would produce cosmetic edits to silence a checker, which is the failure mode the repository already refuses elsewhere.

### Alternative 2: keep them and add a "last acted on" date

- Track when each advisory last changed a decision, and revisit.
- Rejected: it adds bookkeeping to defer a decision the audit already has the data for. Three of them had never acted, across months.

### Alternative 3: keep the Clarify line and make the scan cheap

- Cache the marker count, or scan only changed folders.
- Rejected: the cost was the visible symptom, not the reason. The number changed nothing even when it was free to compute.

## References

- `scripts/lint-commands.sh`: where the three call sites were.
- `scripts/check-natural-voice.sh` and `scripts/check-gate-provenance.sh`: kept, standalone.
- `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` and `wos/natural-voice.md`: the normative rule and its catalog, untouched.
- [ADR-0147](./0147-triggers-come-from-the-mechanism.md): the gate-provenance advisory this retires from the lint.

## Notes

Revisit any of the three the day someone wants to act on what it reports. Adding a line back is cheap; the rule is about whether a reader has a reason to read it.
