# ADR-0009: Task shape system

- **Status**: Accepted
- **Date**: 2026-05-08
- **Tags**: task-shapes, recommended-workflows, sequencing, re-classification

## Context

Engineering tasks are not all the same shape. A typo fix is not the same kind of work as an auth change is not the same kind of work as a refactor. The workflow's value lies in disciplined phase sequencing, but applying the **same** sequence to every task is wrong:

- Typical unclear engineering tasks need full discovery (`impact-analysis`, `invariants-and-non-goals`, `decision-interview`).
- Contract-sensitive tasks need explicit `resolve-contract-gaps` and `contract-signoff` before planning.
- Small bounded tasks can skip discovery and go straight to planning.
- Docs-only tasks do not need impact analysis or test strategy.
- Test-only tasks need test-strategy as the central driver, with no other discovery commands.
- Refactors must mandate test-strategy (the test suite is the only proof of behavior preservation) and review-hard (refactors hide subtle bugs).
- Resuming a task uses `resume-from-state` first, not `task-init`.
- Recovery from confusion uses `im-stuck`, then domain-specific recovery.
- Production incidents use `incident-triage`, with branching paths based on the recommended fix size.
- PR review feedback (corrective) uses `pr-feedback-ingest`, then implement-style commands.
- PR review feedback (pivot) uses `post-review-pivot`, then re-planning.

The workflow needed a way to express these distinct **shapes** so that users (and the model when routing) could pick the right sequence for the work at hand.

A second, harder force: **tasks shift shape mid-flight**. A test-only task might surface a real bug while writing the test; the work is no longer test-only. A docs-only change might turn out to redefine a workflow contract; the work is no longer docs-only. Without explicit re-classification rules, tasks would silently drift across shapes, and the original sequence would no longer match the actual work.

## Decision

The workflow defines a **task shape system** as `WOS ## Recommended workflows by task shape`. Each shape is a named, sequenced flow of commands. Shapes shipped in v0.1.x:

- **Typical unclear engineering task** (the default; full discovery and planning).
- **Contract-sensitive task** (with explicit `resolve-contract-gaps` and `contract-signoff` gates).
- **Small but disciplined task** (skip broad discovery; one slice; close cleanly).
- **Docs-only task** (no production code change; skip impact-analysis, invariants, test-strategy).
- **Test-only task** (test additions or improvements; mandatory test-strategy; no behavior change).
- **Refactor task** (behavior preservation under structural change; mandatory test-strategy and review-hard).
- **Resume task after interruption** (start with resume-from-state).
- **Recovery from confusion or loop** (start with im-stuck).
- **Concrete observed failure** (start with incident-triage; branch on recommended fix size).
- **Near delivery** (where-we-at, review-hard, pr-package).
- **After PR review (corrective)** (pr-feedback-ingest, implement, pr-package again).
- **After review requests a meaningful pivot** (post-review-pivot, re-plan, implement, pr-package).

Each shape declares:

- The sequence of commands.
- Which commands are mandatory (vs optional or skipped).
- A skip rationale (what the shape avoids and why).
- An **explicit re-classification rule** (when to abandon the shape and switch to a different one).

The re-classification rules are the load-bearing part. Examples:

- **Test-only**: "If a test discovers a real bug while being written (test fails against current code, and the bug needs fixing), stop the test-only flow and re-classify as a small disciplined task or an incident-triage flow; do not let a test-only task drift into a behavior change."
- **Docs-only**: "Changes to `WORKFLOW_OPERATING_SYSTEM.md`, `commands/*.md`, or `wos/<topic>.md` are NOT docs-only because they redefine workflow contracts; use the disciplined flow."
- **Refactor**: "If `test-strategy` reveals that adequate behavior coverage cannot be added in scope, stop the refactor: it must be preceded by a separate task that adds the missing test infrastructure. Refactoring without behavior coverage is a known anti-pattern and is not a permitted shortcut even under deadline pressure."

The re-classification rules turn task shapes from a static taxonomy into a **dynamic discipline**: the user picks an initial shape, but the workflow has explicit guidance for when to switch.

## Consequences

### Positive

- **Right-sized ceremony per task**. A typo fix uses the docs-only or minimal flow; an auth change uses the contract-sensitive flow with strict operating mode. Each task gets the discipline it needs without the ceremony it does not.
- **Catalog is searchable**. Users (and the model) scan `## Recommended workflows by task shape` to find the closest match. The names are descriptive enough that "I am refactoring" maps to "Refactor task" without ambiguity.
- **Re-classification is built in**. When a task shifts shape mid-flight, the workflow has explicit guidance for what to do next. This is the difference between a static taxonomy (which fails when reality deviates) and a dynamic discipline (which absorbs deviation).
- **Composable with operating modes**. A "Refactor task" can run in `strict` operating mode (mandates rollback notes, deep output, review-hard before pr-package) or under standard rules. The shape and the mode are orthogonal axes.
- **Documents anti-patterns inline**. The "do not use this shape when..." paragraphs are themselves a form of WOS `## Anti-patterns`, applied at the shape boundary rather than scattered across command files.

### Negative

- **More taxonomy to learn**. New users see twelve task shapes plus three operating modes plus four editor modes plus three output depths. The orthogonality is real (each axis answers a different question), but the surface area is larger than a flat command catalog.
- **Shape selection requires judgment**. "Is this a small disciplined task or a contract-sensitive task?" is sometimes ambiguous. The wrong choice does not break the workflow (the user can re-classify), but the initial pick has friction.
- **Re-classification is opt-in**. The rules say "stop the test-only flow and re-classify"; nothing enforces it mechanically. A user who ignores the rule writes a behavior change under a test-only header. The mitigation is documentation plus the eventual `state-reconcile` pass that surfaces the drift.

### Neutral

- The list is open-ended: future shapes can be added without breaking existing ones. Each shape is independent of the others (no inheritance, no overrides).

## Alternatives considered

### Alternative 1: One workflow, all knobs adjust it

- Single canonical sequence; users adjust by skipping commands or adding flags.
- Rejected: turns every task into a configuration exercise. Users who do not configure correctly fall back to ceremony or under-disciplined work. Named shapes make the sequence the unit of choice, not the per-command flag set.

### Alternative 2: Tag-based composition

- Each task has tags (e.g., `tags: ["docs", "small"]`); the workflow composes the right sequence from tag rules.
- Rejected: tag composition is hard to reason about. "What is the sequence for `tags: ['docs', 'multi-repo']`?" requires running a composer. Named shapes are static and inspectable; the user reads the WOS section and knows what to expect.

### Alternative 3: Free-form workflow per task

- The user just declares which commands to run, in what order, with no shape system.
- Rejected: defeats the workflow's value. The discipline is in the **named** shapes, not in arbitrary sequences. The shape system embeds known-good sequences; free-form would lose that knowledge.

### Alternative 4: One shape per command category

- Map each WOS command category (`State and navigation`, `Discovery and scoping`, etc.) to a shape.
- Rejected: categories are about **what a command does**, not about **what kind of task uses it**. The same command (`task-init`) is the entry point of every shape; categorizing shapes by their commands inverts the relationship.

## References

- `WORKFLOW_OPERATING_SYSTEM.md` → `## Recommended workflows by task shape` (the normative section).
- `WORKFLOW_OPERATING_SYSTEM.md` → `## Anti-patterns` (related: shape rules embed anti-patterns at shape boundaries).
- [`docs/adr/0008-operating-modes.md`](./0008-operating-modes.md) (the orthogonal posture axis).
- Each shape's "re-classification" rule is a form of the boundary policing the WOS already does at command level via `Use when:` / `Do not use when:` blocks.

## Notes

The shape system grew incrementally. The first three shapes (Typical, Contract-sensitive, Small but disciplined) were inherited from earlier WOS iterations. Docs-only, Test-only, and Refactor were added in May 2026 as the v0.1.x release approached. The pattern of "explicit re-classification rule per shape" was crystallized when the docs-only shape needed to handle "WOS-spec changes look like docs but are contracts" - once that boundary was named, the same pattern was applied retroactively to test-only ("a test that finds a bug is no longer test-only") and refactor ("a refactor without coverage is not a permitted shortcut").

Future shapes (e.g., a `dependency-bump` shape, a `migration` shape, a `data-fix` shape) follow the same template: name, sequence, mandatory commands, skip rationale, explicit re-classification rule. The shape catalog is open by design.
