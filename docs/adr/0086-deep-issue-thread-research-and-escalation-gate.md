# ADR-0086: Deep issue-thread research in capture-references plus a read-comments-before-escalation gate

- **Status**: Accepted
- **Date**: 2026-07-07
- **Tags**: capture-references, external-research, incident-triage, decision-interview, external-web-access, upstream-bugs, dogfood-driven, rn-dogfood-audit

## Context

A dogfooding session (the rn-reference-app Android Fabric `addViewAt ... ReactEditText already has a parent` crash, 2026-07-07) surfaced a repeatable failure in how the WOS researches upstream bugs. The web-fetch path read the top-level summary of the relevant GitHub issues and missed the actual fix, a community workaround (`requestAnimationFrame`/`setTimeout` to defer navigation one frame) buried in the comment threads of react-native-screens #2803 and #3249. The maintainer had to force a deep read via `gh issue view <n> --comments` before the workaround appeared. By then a full Expo SDK 56 to 54 downgrade (reanimated 4 to 3, both platforms re-tested) had already been locked as the plan; a 6-line change made it unnecessary. The session's own LEARNINGS L2 recorded the lesson: "read the full issue comment threads, not the summaries."

Two structural gaps: (1) `capture-references` (the only general-purpose web-fetch command; ADR: centralized external web access) summarizes a source; for a GitHub/GitLab issue it summarizes the issue body, not the comment thread where workarounds live. `external-research` never fetches (it synthesizes from `REFERENCES.md`), so the shallow read is produced at capture time. (2) Nothing forced reading the comments before escalating to a heavy, hard-to-reverse fix (a version downgrade or architecture change) to dodge the upstream bug.

## Decision

Two changes, landed together (task `2026-07-07_wos-rn-dogfood-punchlist`, decisions D-2 and D-6):

1. **Deep issue-thread read in `capture-references` (D-2).** WHEN `capture-references` is given a GitHub or GitLab issue or PR URL, it reads the full comment thread (via `gh issue view <n> --repo <r> --comments`, `gh pr view`, or the host API) and hunts for workaround markers (`workaround`, `setTimeout`, `requestAnimationFrame`, `InteractionManager`, `solved`, `fixed`, `patch`, `downgrade`), capturing the workaround-bearing comments verbatim with their commenter handles as Key points, not only the top-level issue summary. `external-research` consumes this richer capture; it still never fetches the web itself. The read is scoped to the authorized fetcher (`capture-references`); no other command gains a fetch capability, so the centralized-web-access guarantee is unchanged. The `gh`/host-API call is named in the WOS `### External web access (centralized)` `capture-references` bullet as one of its fetch mechanisms, alongside WebFetch and WebSearch.

2. **Read-comments-before-escalation gate (D-6).** WHEN `incident-triage` (on an INVESTIGATION or EXTERNAL_DEPENDENCY path) or `decision-interview` is about to escalate to a downgrade or heavy migration to dodge an upstream bug, the command requires the upstream issue's full comment thread to have been read for a community workaround (through the `capture-references` deep read) before that escalation is locked. If it has not been read, the command routes to `capture-references` first rather than locking the heavy fix. The gate is placed at both escalation points because the heavy fix can be reached either by triage routing or by a decision-interview lock.

This is Direction C (D-1): no new command. The change is a capture-time capability plus two gates on existing commands, recorded as one ADR.

## Consequences

### Positive

- The research path reads where the answers actually are for upstream bugs (the comment thread), so a cheap community workaround is found before an expensive downgrade is committed.
- The gate makes the escalation decision evidence-bound: a downgrade or architecture change to dodge an upstream bug cannot lock until the comments were read.
- No new command and no new fetcher: the centralized external-web-access audit trail is preserved (the deep read still funnels into `REFERENCES.md` in capture-references format).

### Negative

- `capture-references` gains conditional branch behavior (issue URL versus generic page) and a dependency on `gh` or a host API for the deep path. Mitigated by graceful degradation: with no `gh`/token available, it falls back to summary capture and says so.
- Two more commands (`incident-triage`, `decision-interview`) carry a conditional gate; an over-broad trigger could add ceremony to a routine fix. Mitigated by scoping the gate to the downgrade/heavy-migration-to-dodge-an-upstream-bug case only.

### Neutral

- The gate reads recorded evidence (was the thread captured); it does not itself fetch. The fetch stays in `capture-references`.
