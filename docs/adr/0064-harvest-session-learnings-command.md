# ADR-0064: harvest-session-learnings command (produce-side of ADR-0017)

- **Status**: Accepted
- **Date**: 2026-06-27
- **Tags**: learnings, reflexion, knowledge-capture, retrospective, append-only, amends-adr-0017, ecosystem-adoption, additive

## Context

ADR-0017 established reflexion-style learnings. It wired the consume side (`task-init` scans prior `LEARNINGS.md` and surfaces a capped "relevant prior lessons" block) and one produce path (`slice-closure` captures an inline `### Learnings` block as a slice closes). The 2026-06-26 ecosystem research (Superpowers' lesson-capture habit, Taskmaster's reflection notes) flagged a gap: the WOS had no on-demand, session-wide harvest. A long session that produced hard-won lessons outside a slice boundary (a failed approach abandoned mid-task, a tool gotcha discovered during debugging) could lose them, because the only produce path fired at slice closure and was scoped to that slice. There was no single verb to sweep the whole session before the context was compacted.

## Decision

Add `harvest-session-learnings`, a new command that is the explicit, session-wide produce-side counterpart to ADR-0017. It reads the working session plus the active task's artifacts, judges which lessons generalize beyond this task, and appends anchored, de-duplicated entries to the active task's `LEARNINGS.md`. It is append-only and read-only on existing entries (ADR-0017 item 6: LEARNINGS compaction is out of scope for every command), and it touches no other task-memory file.

This ADR amends ADR-0017 by adding a dedicated produce path. It does not change or supersede ADR-0017's consume side or the inline `slice-closure` path, so per the immutability convention (`docs/adr/README.md`) ADR-0017 itself is not edited; this record documents the extension.

A new command was chosen over folding the behavior into `slice-closure` because `slice-closure` is slice-scoped and fires only at slice boundaries, while the harvest is session-wide and runnable mid-task or at the end. Keeping them distinct preserves `slice-closure`'s bounded scope and gives the user an explicit "sweep the session now" verb. The command judges durability before writing (rejecting one-off task trivia and decisions already in `DECISIONS.md`) and returns a NO_OP when nothing generalizes, so it adds no ceremony to a session that learned nothing reusable.

## Consequences

- `count:commands` rises 83 -> 84; the command is registered in all four registries (WOS `## Command categories` cluster, WOS `## Command roles` index, `wos/command-roles.md`, `COMMAND_PROMPT_STUBS.md`) and covered by eval scenario 80.
- The produce-side of ADR-0017 now has a dedicated, judged, session-wide path, not only the per-slice inline path; `task-init`'s consume side reads the result unchanged.
- `LEARNINGS.md` stays append-only and freeform (it is not a substrate-matrix section per `wos/substrate-peers.md`), so no transaction-header protocol applies; the anchor rule (`templates/LEARNINGS.md` `## Entry shape`) plus de-duplication is the quality gate.
- Additive: the existing closure flow is unchanged and the command is opt-in. Cross-project lessons are flagged as a pointer to `USER_MEMORY.md` (ADR-0016), not written by this command.
