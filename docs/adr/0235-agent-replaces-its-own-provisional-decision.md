# ADR-0235: The agent replaces its own provisional decision with a new P-N

- **Status**: Accepted. The rule is provisional P-1 of its task, listed in the draft PR for the maintainer to confirm.
- **Date**: 2026-09-24
- **Tags**: provisional-decisions, decisions, replaces, pr-package, check-plan-coverage, adr-0233

## Context

- ADR-0233 lets an attended chain record a decision the request left open as a `### P-N` under `DECISIONS.md ## Provisional decisions`. The lifecycle in `wos/task-file-contracts.md` says a P-N is never edited or moved, and it names two paths out of the provisional state, both the maintainer's: a `### D-N` carrying `Confirms: P-N` or one carrying `Supersedes: P-N`.
- It names no path for the agent. Between the moment a P-N is written and the moment the maintainer reads the draft PR, the agent can learn that its own P-N is wrong, and the lifecycle does not say what to do then.
- On 2026-09-24 that happened. In task 2026-09-24_task-close-harvests-learnings, the blinded plan review in round 1 found that P-1 carried `Impact: normal` while the rule it recorded narrowed the maintainer's request. The agent could not edit P-1, so it wrote P-2 with the same rule, `Impact: high`, and an ad hoc line reading "Replaces P-1". Nothing read that line. `pr-package` lists every P-N that no `Confirms:` or `Supersedes:` names, so both P-1 and P-2 would have gone into "Decisions made without you", and the maintainer could have confirmed the mislabeled one. `scripts/check-plan-coverage.sh` would have accepted a slice still citing P-1.

## Decision

WHILE a P-N is not yet confirmed or superseded by the maintainer, the agent SHALL correct it only by appending a new `### P-N` that carries a `Replaces: P-M` line and the reason, and SHALL leave P-M exactly as written. Plans SHALL cite only the newest entry of a replacement chain. `Replaces:` links two P-Ns only, and the maintainer's `Confirms:` and `Supersedes:` paths are unchanged.

- The clause sits in the same words in `wos/task-file-contracts.md` (`## Provisional decisions`) and in `wos/substrate-peers.md` (its DECISIONS.md provisional-decisions note and write rule 6).
- `commands/pr-package.md` lists under "Decisions made without you" only a P-N that no later P-N's `Replaces:` line names, on top of the `Confirms:` and `Supersedes:` exclusion.
- `scripts/check-plan-coverage.sh` reads each P-N's `Replaces:` line and reports a slice whose `Decision-ref:` cites a replaced P-N, naming the slice, the replaced P-N, the P-N that replaces it and the newest entry of the chain. In single-task mode that finding exits 1. `scripts/tests/test-check-plan-coverage.sh` checks 30 and 31 hold it.

## Consequences

### Positive

- A correction a review forced leaves a trace: the wrong entry stays readable and the new one says why it replaced it.
- The maintainer sees one entry per open decision in the draft PR, the current one, so the confirmation lands on what the plan actually rests on.
- A plan that kept citing the replaced entry is caught by the checker `implementation-plan` already runs, not by a reader.

### Negative

- `DECISIONS.md` grows by one entry per correction, and a reader of the file has to follow `Replaces:` to find the live one.
- The checker reads only `Replaces:` with a colon. The ad hoc form written on 2026-09-24 ("Replaces P-1") would not be read.

### Neutral

- `decision-interview` is unchanged; it already defers to the lifecycle in `wos/task-file-contracts.md`.
- The "never edited" statements elsewhere (`wos/command-roles.md`, `commands/contract-signoff.md`) stay true and need no change.

## Alternatives considered

### Alternative 1: let the agent edit its P-N in place until the draft PR opens

- The agent rewrites P-1 directly while the task is still on its branch, and the rule "never edited" starts at the PR.
- Rejected: the correction a blinded review forced would leave no trace in the substrate, and "never edited" would gain an exception that depends on timing, which a reader cannot check from the file alone.

### Alternative 2: do nothing

- Keep the lifecycle as it is and let the agent write replacement lines however it likes.
- Rejected: `pr-package` would list the replaced P-N next to its replacement, and the maintainer could confirm the wrong one. The checker would accept a slice resting on it.

## References

- `wos/task-file-contracts.md` → `### DECISIONS.md` → `## Provisional decisions` (the lifecycle).
- `wos/substrate-peers.md` (the DECISIONS.md provisional-decisions note and write rule 6).
- `commands/pr-package.md` (the "Decisions made without you" list).
- `scripts/check-plan-coverage.sh` rule 4b and `scripts/tests/test-check-plan-coverage.sh` checks 30 and 31.
- ADR-0233 (provisional decisions and the draft PR).
