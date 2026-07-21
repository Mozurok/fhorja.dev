# ADR-0113: lost-session recovery as a capped, read-only mode of resume-from-state

- **Status**: Accepted
- **Date**: 2026-07-21
- **Tags**: resume-from-state, lost-session, session-recovery, read-only, tool-call-cap, extends-adr-0053, v3-wave4

## Context

When a session dies without a Handoff (a crash, a dropped connection, a closed terminal), the task substrate on disk may lag what actually happened, and the only record of the tail is the harness's own session transcript. The bv3 dogfood opened exactly there: turn 0 spent an uncapped archaeology sweep over transcript files with no doctrine for where they live, what to extract, or when to stop. Fhorja had commands for resuming FROM state (`resume-from-state`) and for reconciling drifted state (`state-reconcile`), but nothing owned the step before either: recovering enough context to know which task was even active.

Two constraints shaped the design. First, the common path must pay nothing: session loss is rare, and `resume-from-state`'s normal flow stays untouched. Second, recovery must not become an unbounded research project or a silent state writer: transcript mining is inference over partial evidence, so its output is proposals, never resolved state.

## Decision

1. Lost-session recovery is a MODE of `commands/resume-from-state.md` (`--lost-session`), not a new command, per the ADR-0053 mode precedent; count:commands stays 95.
2. The trigger is EXPLICIT only: the flag or an unequivocal user ask. A missing `TASK_STATE.md` alone never fires it.
3. A hard cap of 6 tool calls PREVAILS over any per-step budget. Before any tool call, the mode asks one targeted question for a date window and the harness. Candidates found but not read are reported as unconfirmed leads (G1: the shortcut is auditable, never silent).
4. Every extraction is PROPOSED with provenance (source file plus line or event). The mode is read-only by construction (mirrored in `wos/substrate-peers.md`), and it never resolves state on its own: a found task folder routes to `state-reconcile`, none found routes to `task-init`. Unattended runs with an unknown project slug stall as PROPOSED rather than guessing.
5. The per-harness session-file map lives in the new lazy topic `wos/session-recovery.md` (activation model_decision; wos-topics 39), entries restricted to layouts verified in a real forensics or recovery session, each naming its verification date; the same evidence bar as the harness quirks section.

## Consequences

- The rare lost-session case gets a bounded, routable entry point (at most 6 calls plus one question) instead of an improvised sweep; the common resume path pays zero.
- Storage layouts date as vendors ship: the topic carries verification dates and refuses speculative entries, accepting that an outdated entry degrades to a reported dead end, never a fabricated recovery.
- Accepted residual: 6 calls cannot always find the session (multi-machine setups, purged transcripts); the mode's honest failure is a routed `task-init` with the leads listed.
