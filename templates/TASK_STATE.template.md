<!-- Canonical TASK_STATE.md structure, emitted by task-init. The 20-section order is
     normative (ADR-0111). Extracted from commands/task-init.md on 2026-08-09; the command
     keeps the heading list inline and reads this file for the per-section annotation. -->

# TASK_STATE

## Quick reanchor
(Compaction-proof anchor, FIRST section by design, ADR-0111. Rebuilt mechanically by sync-task-state on every sync; decision-interview co-writes the Active decisions line in the same turn it locks a D-N in persist mode. Truncate each line at a clause boundary such as a comma or semicolon, never a fixed word count; cap Active decisions at 10 with an explicit overflow line pointing at DECISIONS.md; write `none locked yet` when empty.)
- Active decisions: [D-N: one clause each | none locked yet]
- Current slice: [from IMPLEMENTATION_PLAN.md ## Slices | none]
- Phase: [current phase]
- Next step: [command from ## Recommended next step]

## Task summary
[Short description of the task]

## Current phase
[discovery | planning | contract refinement | contract signoff | test design | implementation | review | debug | delivery]

## Objective
[What success looks like for this task]

## Requested deliverables
(One row per concrete deliverable the user named in the brief: an artifact to produce or an input to analyze, not every implied sub-task. Tag each: in-scope | de-scoped:<reason> | done; when the deliverable is user-facing product content or a new user-facing surface, also tag it user-facing-content or new-user-facing-surface (ADR-0091; tagging test per ADR-0103: the tag applies when a human end user experiences the content or reaches the surface through any client, visual or not, so an MCP prompt surface reached via chat tags and an MCP tool whose result a human end user consumes in the client tags, while a machine-to-machine API, a developer-facing CLI, or a tool consumed only by the model or another machine does not), for example `- session pack v2 [in-scope] [user-facing-content]`. Seeded here at task-init; reconciled at closure per ADR-0056. When the brief names no concrete deliverable, the single row is `- none named`.)
- [deliverable 1] [in-scope]
- [deliverable 2] [in-scope]

## Recommended pipeline
(Fired escalations + ordered command sequence per the scope assessment. The default pipeline has no name; every added command names the disqualifier that added it (ADR-0184). Owner: task-init; updated by what-next or sync-task-state as routing evolves.)
- Escalations: [none | <added command> (<disqualifier that fired>), ...]
- [Route: one-slice (<evidence for each condition>), only when task-init took that route (ADR-0225)]
- [ordered next commands]

## Source of truth
- [main plan markdown]
- [decision markdown, if any]
- [relevant code/docs/tickets]

## Current known facts
- [fact 1]
- [fact 2]

## Canonical decisions
- [decision 1]
- [decision 2]

## Open questions / blockers
- [open item 1]
- [open item 2]

## Last completed step
- Command:
- Mode:
- Summary:

## Current status
### Completed
- [completed item]

### In progress
- [current item]

### Not started
- [pending item]

## Active files in scope
- [file 1]
- [file 2]
- [file 3]

## Constraints / things that must not change
- [constraint 1]
- [constraint 2]

## Risks to watch
- [risk 1]
- [risk 2]

## Recommended next step
- Command: (official basename only, must match `commands/<name>.md` in this repo, e.g. `impact-analysis`, not `task-plan`)
- Mode:
- Why:

## Work complexity (for next execution step)
LOW | MEDIUM | HIGH | N/A
- Rationale (one line):

## Resume notes
[Short practical note explaining how to continue from here in a new chat]
<!-- ADR-0233: task-init, task-workspace or branch-commit adds the task-branch and base-branch lines here only when a task branch exists (an attended run on a git repository with a configured remote and no declared assisted mode). Write neither otherwise; a placeholder would read as a real task branch. -->

## Task scope level
[full task | current phase | current slice | hotfix]

## Current closure target
[exact thing we are trying to finish now]
