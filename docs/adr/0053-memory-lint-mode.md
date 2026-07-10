# ADR-0053: memory-lint is a read-only mode on state-reconcile, not a new command

- **Status**: Accepted
- **Date**: 2026-06-25
- **Tags**: memory, memory-lint, state-reconcile, read-only, command-surface, additive, claude-obsidian-prior-art

## Context

The 2026-06-25 analysis of `claude-obsidian` surfaced its `/wiki-lint` command: a vault health check that flags orphans, dead links, and stale claims. The WOS has no equivalent periodic hygiene check over its own memory artifacts. It has `state-reconcile` (drift repair between artifacts and reality) and `compact-task-memory` (lossy shrink), but neither scans for dead relative cross-links or orphaned `SLICES/` files, and neither runs as a cheap read-only pass.

The question was where this capability should live. The WOS command surface is already large (82 commands across flat and folder-shaped entries) and every new command must be registered in four places and kept lint-green, so adding commands has real maintenance cost. A memory-hygiene check is also conceptually adjacent to `state-reconcile`: both reason about whether task memory is trustworthy.

## Decision

Add memory-lint as a read-only mode on `state-reconcile` rather than a new command. The mode reports four classes of issue (stale `TASK_STATE` facts, broken relative cross-links across task and project memory, orphaned `SLICES/` files, LEARNINGS entry quality) and writes nothing. Deterministic detection (dead links, orphans) is handled by `scripts/memory-lint.sh`; the model-driven layer adds stale-fact judgment. The mode is strictly read-only and stays distinct from `state-reconcile`'s drift-repair behavior and from `compact-task-memory`'s shrink.

- Keeping it a mode avoids adding a command and the four-registry plus count-marker maintenance that a new command requires.
- The read-only boundary is explicit in the command file so the mode is never confused with drift repair.

## Consequences

### Positive

- Gives the WOS a periodic memory-hygiene check without growing the command surface.
- Reuses the `state-reconcile` mental model (memory trustworthiness) instead of introducing a parallel concept.
- The deterministic half (`scripts/memory-lint.sh`) is repeatable and usable out-of-band (CI, manual) independent of the command.

### Negative

- Overloads `state-reconcile` with a second behavior; the read-only boundary must be documented carefully so users do not expect repair from the lint mode.
- Link detection is heuristic (regex-based) and can miss unusual syntaxes.

### Neutral

- The stale-fact half stays model-driven and lives in the command, not the script (the deterministic/model split is deliberate).

## Alternatives considered

### Alternative 1: a new standalone `memory-lint` command

- A dedicated command mirroring `/wiki-lint`.
- Rejected: adds command-surface and four-registry maintenance for a capability that fits cleanly as a mode on an existing, conceptually-adjacent command.

### Alternative 2: fold it into `compact-task-memory`

- Run hygiene checks during compaction.
- Rejected: compaction is a lossy write; memory-lint is read-only and should run without mutating anything, including when no compaction is wanted.

## References

- `scripts/memory-lint.sh` (the deterministic detection backend).
- `commands/state-reconcile.md` (the command that hosts the mode).
- `commands/compact-task-memory.md` (the shrink behavior memory-lint stays distinct from).
- `projects/bmazurok__my-work-tasks/active/2026-06-25_claude-obsidian-memory-absorption-analysis/EXTERNAL_RESEARCH.md` (the analysis that recommended absorbing this; D-2).
- [claude-obsidian](https://github.com/AgriciDaniel/claude-obsidian) (prior art, `/wiki-lint`; accessed 2026-06-25).

## Notes

The deterministic helper landed first (slice S1) and is independently testable; the command-mode wiring (slice S2) consumes it. If link detection false-negatives become a problem, the regex backend can be hardened without changing the command contract.
