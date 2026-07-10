# ADR-0017: Reflexion-style learnings

- **Status**: Accepted
- **Date**: 2026-05-15
- **Tags**: context-engineering, working-memory, reflexion, post-mortem-light, manual-promotion

## Context

The Reflexion paper (Shinn et al., 2023) showed that language agents that record verbal lessons from failed attempts ("we tried X, it failed because Y, next time Z") materially improve performance on subsequent attempts within the same session. Mem0 and Zep extend the pattern to cross-session and cross-task scales.

The WOS already records two kinds of task memory:

1. **State and decisions** (via `sync-task-state`, `decision-interview`, `state-reconcile`): operational truth that is REQUIRED to continue work.
2. **External references** (via `capture-references`): durable knowledge captured from outside the task.

Three failure modes the absence of a learnings layer creates:

1. **Failed attempts leave no trace**. A slice that tried approach A, hit a wall, switched to approach B teaches nothing to future tasks. The wall is invisible to anyone reading the resulting diff (which shows only B). The same wall gets re-hit on the next similar task.
2. **Post-mortems are skipped because they feel like ceremony**. After an incident HOTFIX or PR pivot, the urgency that made the problem visible is gone; writing "what went wrong" requires summoning context that has already faded. A short optional section in the command that just resolved the issue captures the learning at the moment of greatest clarity.
3. **Cross-project lessons stay anecdotal**. Recurring gotchas ("validate RLS before pr-package on Supabase projects") survive as informal habit until something breaks. Project-level memory is project-scoped; user-level memory (slice 05) is the right home for cross-project lessons, but needs a feeder layer.

ADR-0016 (user-level memory) introduced `/USER_MEMORY.md ## Cross-project learnings` as the durable cross-project home. This ADR introduces the task-scoped feeder layer and the three commands that produce it.

## Decision

The WOS adopts a reflexion-style learnings pattern with three components:

1. **Task-scoped `LEARNINGS.md`** at the active task root (`projects/<client>__<project>/active/<task>/LEARNINGS.md`), bootstrapped from `templates/LEARNINGS.md`. Listed in WOS `## Optional task files`. Created on first emission; absent until then.
2. **Three commands optionally emit an `### Learnings` section**: `slice-closure` (when a slice involved a failed attempt or surprising finding), `post-review-pivot` (a pivot is a learning by definition; section is more often non-empty here), `incident-triage` (only on `HOTFIX` or `ESCALATE` paths where a root cause was identified). Other commands do NOT emit the section by default; the three are the natural producers.
3. **Locked entry shape (4 bullets, all required)**:
   ```
   ## YYYY-MM-DD task-slug source
   - Tried: <attempted approach; one to two lines>
   - Failed because: <root cause or blocking signal; one to two lines>
   - Next time: <the lesson; what to try first or avoid next time>
   - Cross-project promotion: <no | yes, copied to USER_MEMORY.md on YYYY-MM-DD>
   ```
   `source` is one of: `slice-NN`, `post-review-pivot`, `incident-triage HOTFIX`, `incident-triage ESCALATE`. Empty bullets disqualify the entry: better no learning than vague learning.
4. **Manual promotion only**. Cross-project lessons are lifted from task-scoped `LEARNINGS.md` to `/USER_MEMORY.md ## Cross-project learnings` BY THE USER. The promotion process: open source entry; copy `Next time:` plus enough context; paste into USER_MEMORY.md; update source entry's `Cross-project promotion:` line. No automated promotion.
5. **Optional in all three commands**. The section is skipped when:
   - `slice-closure`: the slice was routine (no failed attempt, no surprise).
   - `post-review-pivot`: the pivot has no transferable lesson (rare).
   - `incident-triage`: classification was `SLICE` or `INVESTIGATION` (the slice flow will produce its own learning at closure if relevant; the triage itself did not surface a durable lesson).
6. **Read-only from other commands**. `LEARNINGS.md` is consumed by `task-init` (next task may want to read prior learnings; not implemented in this slice; future-friendly) and is otherwise additive. No command compacts, prunes, or rewrites LEARNINGS.md entries; entries accumulate.

## Consequences

### Positive

- **Failed attempts leave a trace**. Future tasks (same or different) can scan LEARNINGS.md or USER_MEMORY.md `## Cross-project learnings` and avoid re-hitting the same wall. The Reflexion paper's verbal-reinforcement gain is captured at the human-readable layer.
- **Post-mortems happen at the moment of clarity**. The optional section is in the command that just resolved the issue (`slice-closure` after a failed slice, `post-review-pivot` after a pivot, `incident-triage` after a HOTFIX). The urgency is fresh; the section is short; the cost is low.
- **Cross-project lessons have a durable home**. The manual promotion path (LEARNINGS.md -> USER_MEMORY.md) is opt-in. Lessons that recur across projects get lifted; lessons that stay task-specific stay task-scoped.
- **No mandatory ceremony**. The section is OPTIONAL. Routine slices, vacuous pivots, and trivial incidents skip it. The lint does not enforce presence; the contract is "emit when there is a learning worth recording", not "always emit".

### Negative

- **Three commands updated in one slice**. Risk surface: if the canonical output contract regressed, 3 commands' behavior could shift. Mitigation: the new section is OPTIONAL and additive; existing eval scenarios that did not assert its presence pass unchanged. New scenarios for the section can be added in a future slice 08 (eval coverage to 30).
- **Lossy when the model writes vague learnings**. A `Tried: stuff` / `Failed because: it didn't work` entry is worse than no entry. Mitigation: locked entry shape requires concrete bullets; the rule "empty bullets disqualify the entry" is explicit.
- **Manual promotion may be skipped consistently**. Some users may never lift task-scoped lessons to USER_MEMORY.md. The lessons stay task-scoped and die when `archive/` happens. Mitigation: this is fine; manual promotion is intentionally low-friction-to-skip; the default state is recoverable (LEARNINGS.md survives in `archive/`).
- **One more optional artifact to know**. WOS `## Optional task files` grows by one. Documentation cost is small (~10 lines in WOS).

### Neutral

- The pattern reuses the same "task / project / user" three-tier structure as memory (ADR-0007, ADR-0016). Contributors who learned the precedence rule once apply it here too: task learnings start specific; user-promoted learnings are general.
- `LEARNINGS.md` may grow on long tasks. No compaction policy is defined in this ADR; a future slice (matching slice 04's compact-task-memory pattern) could add `compact-learnings` if friction shows up. Not planned.

## Alternatives considered

### Alternative 1: auto-promotion (LEARNINGS -> USER_MEMORY)

- A command or daemon promotes entries from task LEARNINGS to user USER_MEMORY automatically based on heuristics (e.g., entries with `Cross-project promotion: yes` flag).
- **Rejected**: which lessons are durable cross-project requires judgment the model cannot reliably make without seeing many tasks. Wrong promotions clutter USER_MEMORY.md (a long-term memory artifact). Manual promotion preserves user judgment.

### Alternative 2: mandatory `### Learnings` section on every slice close

- Every `slice-closure` MUST emit a Learnings section, even if "(none for this slice)".
- **Rejected**: ceremony for ceremony's sake. Routine slices have no learning worth recording; forcing the section produces noise. Optional with explicit emission criteria is better.

### Alternative 3: separate file per learning entry

- One file per learning under `LEARNINGS/<date>-<source>.md`.
- **Rejected**: multiplies files in the task folder without benefit. A single `LEARNINGS.md` with newest-first entries is easier to scan and aggregate.

### Alternative 4: do nothing; users record learnings in TASK_STATE.md `## Open questions`

- Use the existing memory infrastructure.
- **Rejected**: conflates active context with historical lessons. TASK_STATE.md should be slim and operational (slice 04 compact-task-memory removes resolved facts). Learnings are durable; they belong in their own artifact.

### Alternative 5: project-scoped LEARNINGS instead of task-scoped

- `projects/<client>__<project>/LEARNINGS.md` shared across tasks within a project.
- **Rejected for this slice**. Task-scoped is simpler (no cross-task write ordering); promotion from task to user is the durable path. A future slice could add project-scoped aggregation as a middle tier if friction shows up, but the three-tier model (task / project / user) is already crowded enough.

## References

- `templates/LEARNINGS.md` (committed template).
- `commands/slice-closure.md`, `commands/post-review-pivot.md`, `commands/incident-triage.md` (the three producers).
- `templates/USER_MEMORY.template.md ## Cross-project learnings` (the promotion target; slice 05).
- `WORKFLOW_OPERATING_SYSTEM.md ## Optional task files ### LEARNINGS.md` (where the file is listed).
- ADR-0007 (project-level memory; the memory pyramid this slice extends).
- ADR-0012 (context budget; names the `memory` layer).
- ADR-0016 (user-level memory; the cross-project promotion target).
- Shinn et al., 2023, "Reflexion: Language Agents with Verbal Reinforcement Learning" (the technique being adopted at the human-readable layer).
- Mem0, "Building Production-Ready AI Agents with Scalable Long-Term Memory" (ECAI 2025): the long-term memory tier promotion pattern.

## Notes

The "learnings as separate optional artifact" pattern may be reused in future slices. For example, slice 09 (cost/latency observability) could optionally emit a `### Cost surprise` section when a command's measured cost was materially different from its declared budget. The pattern: short, structured, optional, additive.

Slice 12 closes Wave 2 (memory layer) of the 2026-05-15 context-engineering uplift. The reassessment point D-1 follows: review whether slices 06-13 still feel load-bearing given what Wave 1+2 delivered, or whether priorities have shifted.
