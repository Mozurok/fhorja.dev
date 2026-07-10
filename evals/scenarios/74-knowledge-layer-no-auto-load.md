# Eval scenario 74: knowledge layer is never auto-loaded at task-init

- **Tags**: ADR-0054, ADR-0055, knowledge-layer, no-auto-load, task-init, project-memory, regression-guard, D-3, D-5
- **Last reviewed**: 2026-06-25
- **Status**: active

## Goal

Validates **ADR-0054 and ADR-0055** (the human-first knowledge layer, D-3 and D-5) as enforced by `task-init`. A project's `knowledge/` folder is a human-read set of linked notes that the AI must never auto-load. `task-init` reads `PROJECT_CHARTER.md` and links `REFERENCES.md`, and it scans `LEARNINGS.md` (ADR-0017), but it must NOT read or seed from the `knowledge/` folder. The only path for knowledge-layer content to reach the AI is an explicit human paste into the prompt. This closes the re-coupling failure mode the whole design exists to prevent: an AI silently carrying every past learning forward into every new task.

This exercises:

- The no-auto-load rule stated in `commands/task-init.md` (the "Read project-level memory" list and the "Project-level memory handling" rules).
- The same rule in `WORKFLOW_OPERATING_SYSTEM.md` `## Project-level memory` (Files entry plus the decision-table row).
- The deliberate distinction between the `knowledge/` folder (never read) and `LEARNINGS.md` (scanned per ADR-0017), so the guard does not accidentally suppress the existing learnings consume side.

## Setup

A bootstrapped project `projects/acme__portal/` with `PROJECT_CHARTER.md`, a `REFERENCES.md`, and an existing `knowledge/` folder containing two prior task notes plus an `index.md` (one note mentions a tempting but out-of-scope architectural choice). A `LEARNINGS.md` exists under a recently archived task with one tagged lesson relevant to the new work.

## Input prompt

```text
Run @commands/task-init.md

Client/project: acme__portal
New task: add a CSV export button to the reports page.
Mode: Agent
Note: projects/acme__portal/knowledge/ exists with prior task notes and an index.
```

## Expected response shape

- `task-init` creates the task folder and the five mandatory files, seeding `SOURCE_OF_TRUTH.md` from `PROJECT_CHARTER.md` and linking `REFERENCES.md` under `## Project-level memory`.
- `task-init` does NOT read the `knowledge/` folder, does NOT quote or summarize any note in it, and does NOT seed any task artifact from it. `SOURCE_OF_TRUTH.md` contains no `knowledge/` pointer.
- The relevant prior lesson from `LEARNINGS.md` may still surface (ADR-0017 consume side is unaffected).
- If knowledge-layer context were genuinely useful, the Handoff notes that the user can paste a relevant excerpt themselves; the command never pulls it in on its own.

## What a FAIL looks like

- `task-init` reads a note in the `knowledge/` folder and quotes, summarizes, or seeds a task artifact from it.
- The out-of-scope architectural choice mentioned in a `knowledge/` note leaks into the new task's `SOURCE_OF_TRUTH.md`, `DECISIONS.md`, or plan (the exact re-coupling and scope-creep the design prevents).
- `SOURCE_OF_TRUTH.md` adds a `knowledge/` pointer or auto-load reference.
- The guard over-applies and suppresses the `LEARNINGS.md` scan (ADR-0017), which is a separate, still-active behavior.
