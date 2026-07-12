# LEARNINGS

Task-scoped log of "we tried X, it failed because Y, next time try Z" entries. Reflexion-style learnings per ADR-0017.

Promotion path: durable cross-project lessons are manually promoted to `/USER_MEMORY.md ## Cross-project learnings`. Edit the entry to remove task-specific detail, then update the source entry's `Cross-project promotion:` line.

## Entry shape

Each entry is **anchored at the exact decision point that failed**, not retrospectively at slice end. Anchoring matters: a retro-summary at slice closure is easy to write but hard to use later; an anchor at the specific failure point lets a future slice that hits the same point find the lesson via grep on the anchor.

Each entry is 5 required bullets plus an optional 6th `Tags:` bullet. Empty required bullets disqualify the entry (better no learning than vague learning). `Tags:` is optional but recommended: it is what the retrieval ranker (`scripts/rank-learnings.sh`, ADR-0071) scores against, so a tagged entry is far easier for a future task to surface.

```
## YYYY-MM-DD task-slug source
- Anchor: <file:line OR slice file section header OR command name OR TASK_STATE.md timestamp>
- Tried: <attempted approach; one to two lines>
- Failed because: <root cause or blocking signal; one to two lines>
- Next time: <the lesson; what to try first or avoid next time>
- Cross-project promotion: <no | yes, copied to USER_MEMORY.md on YYYY-MM-DD>
- Tags: <optional; comma-separated keywords for retrieval, e.g. api-jobs, path-alias, tsx>
```

`Anchor` examples:
- `apps/web/components/Button.tsx:42` -- the exact line where the failed pattern lives
- `SLICES/03_auth-refactor.md ## Validation` -- the slice section where the failure was observed
- `decision-interview` -- the command whose output proved misleading
- `TASK_STATE.md 2026-06-04 implement-approved-slice` -- the timestamped state update where the wrong choice was made

`Tags` example: `Tags: api-jobs, path-alias, tsx` -- comma-separated keywords a future task can grep, and the fields `rank-learnings.sh` scores against.

`source` is one of:
- `slice-NN` (slice closure that surfaced the learning)
- `post-review-pivot` (pivot is a learning by definition)
- `incident-triage HOTFIX` (HOTFIX postmortem)
- `incident-triage ESCALATE` (escalated incident with identified root cause)
- `harvest-session-learnings` (session-wide harvest, ADR-0064; covers lessons whose origin is not a single slice or incident)

Adopted from Cursor Composer 2.5 RL evidence (2026): failure-point-anchored feedback materially outperforms retrospective summary at slice end (concrete reuse rate of anchored entries on subsequent slices ~3-5x higher than unanchored).

## Entries

(Add entries below as slices close, pivots happen, or HOTFIX incidents resolve. Newest first.)
