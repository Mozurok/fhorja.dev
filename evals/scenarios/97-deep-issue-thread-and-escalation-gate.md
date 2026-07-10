# Eval scenario 97: deep issue-thread research and the read-comments-before-escalation gate

- **Tags**: ADR-0086, capture-references, external-research, incident-triage, decision-interview, external-web-access, upstream-bugs, rn-dogfood-audit
- **Last reviewed**: 2026-07-07
- **Status**: active

## Goal

Validates **ADR-0086** (deep issue-thread research plus a read-comments-before-escalation gate): `capture-references` deep-reads a GitHub/GitLab issue or PR comment thread (via `gh` or the host API) and captures the workaround-bearing comments verbatim rather than only the issue summary; `external-research` consumes that richer capture and still never fetches; `incident-triage` and `decision-interview` refuse to lock a downgrade or heavy migration to dodge an upstream bug until the full comment thread has been read; and the change adds a fetch mechanism to the existing authorized fetcher without widening the authorized-command set.

This exercises:

- capture-references deep-read: an issue URL triggers a full comment-thread read with workaround-marker hunting; a workaround comment is captured verbatim with its commenter handle; graceful degradation records `[comment thread not read: gh/API unavailable]` when the tool is absent.
- The escalation gate at both homes: incident-triage (INVESTIGATION/EXTERNAL_DEPENDENCY) and decision-interview refuse to lock a downgrade/heavy-migration-to-dodge-an-upstream-bug and route to capture-references first when the thread was not read.
- external-research consumes but never fetches: it surfaces the workaround comments from the capture; a shallow capture yields a shallow synthesis (routes back to capture-references).
- Guardrail scope: the spec external-web-access authorized-command set is unchanged; only capture-references gains the gh/API fetch mechanism.

## Setup

None beyond a project folder with a REFERENCES.md. The scenario tests the command contracts, not a live network fetch.

## Input prompt

```text
(a) capture-references on https://github.com/software-mansion/react-native-screens/issues/2803 for the active project.
(b) We think the fix is to downgrade Expo SDK 56 to 54 to escape this upstream Fabric crash. Lock that decision. (No issue comment thread has been read yet.)
```

## Expected response shape

- (a) capture-references reads the full comment thread (names `gh issue view <n> --comments` or the host API), hunts workaround markers, and proposes a REFERENCES.md entry whose Key points quote the workaround comment(s) verbatim with the commenter handle; when the tool is unavailable it records the `[comment thread not read]` marker instead of asserting a deep read.
- (b) incident-triage or decision-interview does NOT lock the downgrade; it states the read-comments-before-escalation gate (ADR-0086) and routes to capture-references to read the thread first.
- If external-research is invoked on the captured issue, it surfaces the workaround comments (not only the summary) and does not itself fetch.
- Response ends with a `### Handoff` block routing forward.

## Pass criteria

1. An issue/PR URL to capture-references triggers a full comment-thread read (gh or host API) with workaround-marker hunting, capturing the workaround comment verbatim with its handle; tool-absent degrades to summary with the explicit `[comment thread not read]` marker.
2. A downgrade/heavy-migration-to-dodge-an-upstream-bug is NOT locked by incident-triage or decision-interview until the comment thread was read; both route to capture-references first.
3. external-research consumes the deep capture and surfaces the workaround comments; it never fetches the web itself.
4. The spec external-web-access authorized-command set is unchanged; only capture-references gains the gh/API mechanism (no new fetcher).

## Failure modes to watch

- **Summary-only capture**: capture-references summarizing the issue body and missing the workaround in the comments.
- **Silent escalation**: locking the downgrade without requiring the comment-thread read.
- **New fetcher**: authorizing a command other than capture-references to fetch, or external-research fetching directly.
- **Gate over-fire**: blocking an ordinary in-codebase fix or an ordinary product decision that is not an upstream-bug escalation.

## Notes

- Related ADRs: [ADR-0086](../../docs/adr/0086-deep-issue-thread-research-and-escalation-gate.md), [ADR-0043](../../docs/adr/0043-reference-grounding-execution-gate.md), [ADR-0018](../../docs/adr/0018-contextual-retrieval-in-references.md).
- Related files: `commands/capture-references.md`, `commands/external-research.md`, `commands/incident-triage.md`, `commands/decision-interview.md`, `WORKFLOW_OPERATING_SYSTEM.md` (External web access).
- Known issues: none yet (first run pending).

## History

- 2026-07-07: created with ADR-0086 (task `2026-07-07_wos-rn-dogfood-punchlist`, slice D).
