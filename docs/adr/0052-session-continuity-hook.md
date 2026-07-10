# ADR-0052: Session-continuity hook keeps task memory resumable, sidecar-only

- **Status**: Accepted
- **Date**: 2026-06-25
- **Tags**: memory, hooks, session-continuity, task-memory, sidecar, advisory, claude-code, additive, claude-obsidian-prior-art

## Context

A recurring failure mode in the WOS is `TASK_STATE.md` going stale because nobody ran `sync-task-state` before a session ended. The next session then resumes from outdated operational memory. The WOS already has the pieces to resume (`TASK_STATE.md` Resume notes, `resume-from-state`, `compact-task-memory`), but the refresh is command-driven: it depends on a human or agent remembering to invoke it.

The 2026-06-25 analysis of `claude-obsidian` (a Claude Code plugin implementing Karpathy's LLM Wiki pattern; see `projects/.../REFERENCES.md`) surfaced its `hot.md` pattern: a small recent-context cache refreshed automatically by a SessionStop hook and reloaded at SessionStart, so "the next session starts with full recent context, no recap needed." That automation on session boundaries is the part the WOS lacked. Claude Code supports `SessionStart` and `SessionStop` hooks natively, and the WOS already ships one advisory hook (`scripts/typecheck-hook.sh`), so the mechanism is on-brand.

A key technical constraint shaped the decision: a pure bash SessionStop hook cannot run the model-driven `sync-task-state`. So "auto-sync" in a hook can only be a bounded, deterministic write, not a full memory synthesis.

## Decision

Ship an optional, advisory `scripts/session-continuity-hook.sh` with two modes. On `stop` it writes a bounded continuity marker (session-end timestamp, session id, task name) to the active task's `.wos/SESSION_CONTINUITY.json` sidecar and never touches authored `TASK_STATE.md` sections. On `start` it prints the active task's Resume notes and Recommended next step and, when `TASK_STATE.md` has not changed since the last recorded session end, nudges the user to run `sync-task-state`. The hook is non-blocking (always exits 0), auto-detects the active task as the most-recently-modified `projects/*/active/*/TASK_STATE.md`, and is wired in the consuming repo's `.claude/settings.json` (the WOS repo ships the script and `templates/session-continuity-hook.template.md`, it does not enable the hook itself).

- Auto-write is sidecar-only and no-op-if-unchanged on its non-timestamp payload; authored memory is never rewritten by the hook.
- Full synthesis stays with `sync-task-state`; the hook records continuity and nudges, it does not replace the model-driven sync.

## Consequences

### Positive

- Closes the stale-`TASK_STATE` failure mode at the session boundary, matching the WOS's own "the system owns closure, never go silent" design principle.
- Stays inside the plain-markdown-plus-bash stance: no app dependency, no database, no embeddings; wired exactly like the existing typecheck hook.
- Resume context is surfaced automatically at session start, lowering restart cost.

### Negative

- Hook firing is host-dependent; a host that does not fire `SessionStop` reliably (very short sessions, hard kills) can miss the marker.
- Adds a second hook the maintainer must wire per consuming repo (opt-in, not automatic).

### Neutral

- Introduces a `.wos/SESSION_CONTINUITY.json` sidecar alongside the existing `.wos/VERIFICATION_LOG.jsonl`; both are gitignored task-local state.
- The staleness nudge is surfaced, not auto-cleared; it clears on the next start once `sync-task-state` has updated `TASK_STATE.md`.

## Alternatives considered

### Alternative 1: nudge-only hook (no write at all)

- The SessionStop hook would only print a reminder, writing nothing.
- Rejected: the maintainer chose auto-sync behavior so continuity is recorded even when the session ends abruptly. A pure nudge loses the session-end signal that drives the deterministic staleness check.

### Alternative 2: auto-write into TASK_STATE.md directly

- The hook would append a continuity block into `TASK_STATE.md` itself.
- Rejected: a bash hook writing into authored memory risks corrupting or churning curated sections. The sidecar keeps authored memory untouchable by the hook.

### Alternative 3: a full retrieval/index layer (the broader claude-obsidian pattern)

- Adopt claude-obsidian's hybrid retrieval (BM25 plus embeddings) for memory.
- Rejected as over-engineering at WOS scale and against the no-embeddings stance (declined as D-3 in the parent analysis).

## References

- `scripts/session-continuity-hook.sh` (the implementation).
- `templates/session-continuity-hook.template.md` (consuming-repo wiring).
- `scripts/typecheck-hook.sh` (the advisory-hook precedent this mirrors).
- `WORKFLOW_OPERATING_SYSTEM.md` → `## Project-level memory` and the TASK_STATE policy (the memory model this supports).
- `projects/bmazurok__my-work-tasks/active/2026-06-25_claude-obsidian-memory-absorption-analysis/EXTERNAL_RESEARCH.md` (the analysis that recommended absorbing this; D-1).
- [claude-obsidian](https://github.com/AgriciDaniel/claude-obsidian) (prior art; accessed 2026-06-25).

## Notes

A pure bash SessionStop hook cannot run model-driven `sync-task-state`; this is why "auto-sync" is scoped to a deterministic sidecar marker plus a start-side nudge, not a full synthesis. Revisit if Claude Code adds a way for a hook to trigger a model turn.
