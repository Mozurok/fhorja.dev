# Eval scenario 78: problem-framing front door writes a task-level BRIEF and gates on ceremony

- **Tags**: ADR-0058, problem-framing, intake, brief, spec-first, task-init, do-not-use-when, anti-ceremony, regression-guard
- **Last reviewed**: 2026-06-26
- **Status**: active

## Goal

Validates **ADR-0058** (the problem-framing front door and task-level BRIEF.md scope): an optional Phase 0.5 command questions whether the stated objective is the right problem before any task exists, writes a five-field task-level `BRIEF.md` that `task-init` consumes, and routes only to `task-init`. The anti-ceremony gate keeps it from firing on an already-clear objective.

This exercises:

- The socratic intake: `problem-framing` asks one question per message, prefers multiple choice, and explores the goal before proposing a solution (Superpowers prior art).
- The five-field BRIEF: problem statement, success criteria, non-goals, recommended approach (one of 2-3 considered), named deliverables; the deliverables seed task-init's `## Requested deliverables` ledger (ADR-0056).
- The task-level scope: `BRIEF.md` is staged at the project root and `task-init` reads it, seeds `SOURCE_OF_TRUTH.md` and the ledger from it, and moves it into the new task folder; it is not a durable project artifact (PROJECT_CHARTER.md owns that).
- The terminal route: the only next command is `task-init` (or `project-bootstrap` when the project is not bootstrapped); never an implementation, planning, or design command.
- The do-not-use-when gate: a NO_OP routed by case, to `task-init` when the objective is already one-sentence-clear or it is a bug fix or hotfix, and to `what-next` when an active task already exists (routing that case to `task-init` would spawn a duplicate task).

## Setup

A user brings a fuzzy objective with no task folder yet, for example: "I think our onboarding is bad and we lose users somewhere, can we fix it?" The project `projects/<client>__<project>/` exists with a `PROJECT_CHARTER.md`.

## Expected behavior

- `problem-framing` does not jump to a task. It asks one clarifying question at a time (purpose, where the drop-off is, what success looks like), prefers multiple choice, and confirms each brief section before continuing.
- It proposes 2-3 candidate framings or approaches with a one-line trade-off each and a recommendation.
- It writes a five-field `BRIEF.md` (PROPOSED in Ask, APPLIED in Agent) at the project root, then recommends `task-init` as the only next command.
- A second run on an already-clear, one-sentence objective (or a hotfix) returns a NO_OP and routes straight to `task-init`, with no manufactured questions; a run while an active task already exists returns a NO_OP routed to `what-next` (not `task-init`, which would duplicate the task).

## Failure modes (a FAIL looks like)

- Batches a wall of questions, or manufactures an interview on an already-clear objective (ceremony the gate must prevent).
- Writes a brief with missing or extra fields, or treats `BRIEF.md` as a durable project artifact instead of a transient task-scoped one.
- On the brief-produced path, routes to an implementation, planning, or design command instead of `task-init` / `project-bootstrap`; or routes the active-task NO_OP to `task-init` (spawning a duplicate) instead of `what-next`.
- Creates a task folder itself (that is `task-init`'s job).
