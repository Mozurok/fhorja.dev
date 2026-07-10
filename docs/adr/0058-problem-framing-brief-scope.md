# ADR-0058: problem-framing front door and task-level BRIEF.md scope

- **Status**: Accepted
- **Date**: 2026-06-26
- **Tags**: command, problem-framing, intake, brief, spec-first, onboarding, superpowers-prior-art, additive

## Context

The 2026-06-26 vibe-coding ecosystem research found that the WOS asserts a spec-first principle but does not enforce it at the top of the funnel: the pipeline enters through `task-init` and `impact-analysis`, both of which assume the stated objective is the right one. `decision-interview` fires downstream and addresses decision ambiguity inside an existing task, not whether the problem itself is correctly framed. Superpowers (obra/superpowers) showed concrete prior art: a brainstorming skill that steps back and questions the goal before any work, asking one question at a time, exploring alternatives, and presenting a design in sections for approval before writing a design doc.

A new command for this is the one top-of-funnel gap the research flagged as worth closing now. The open design question was where its output should live, given the command runs before any task folder exists.

## Decision

Add `problem-framing`, an optional Phase 0.5 command that runs before `task-init`. It runs a short socratic intake (one question per message, prefer multiple choice, explore the goal before proposing a solution, present in sections with approval gates), proposes two or three approaches with trade-offs, and writes a five-field `BRIEF.md`: problem statement, success criteria, non-goals, recommended approach, and named deliverables. Its only terminal route is `task-init` (or `project-bootstrap` when the project is not yet bootstrapped); it never routes to an implementation, planning, or design command.

`BRIEF.md` is **task-level**, not project-level. `PROJECT_CHARTER.md` already owns durable project-level intake; the brief is transient and scoped to one task. Because the command runs before the task folder exists, it stages `BRIEF.md` at the project root (`projects/<client>__<project>/BRIEF.md`); `task-init` reads it, seeds `SOURCE_OF_TRUTH.md` and the `## Requested deliverables` ledger (ADR-0056) from it, and moves it into the new task folder so no stale brief lingers at the root.

The command carries a strong do-not-use-when gate to prevent ceremony: it returns a NO_OP and routes straight to `task-init` when the objective is already specific enough to state in one sentence, when it is a bug fix or hotfix, or when an active task already exists.

## Consequences

- The spec-first principle gains a top-of-funnel enforcement point without forcing ceremony on clear asks (the gate is explicit).
- The command count goes from 82 to 83; it is registered in all four registries with an eval scenario (ADR-0029 drift guards) and carries the three frontmatter fields from ADR-0059 (tools, x-wos-profiles, provenance).
- `task-init` gains a small consume step: read `BRIEF.md` when present, seed from it, and move it into the task folder.
- This ADR is additive. It does not supersede `decision-interview` (which stays the in-task decision-locking command) or `task-init` (which stays the task-creation command); `problem-framing` precedes both.
