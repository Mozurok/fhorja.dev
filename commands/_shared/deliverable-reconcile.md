**Deliverable reconcile (per ADR-0056).** Reconcile the task's `## Requested deliverables` ledger in `TASK_STATE.md` against the delivered work. Hard-fails only when finalizing the whole task; reports without failing at a mid-task checkpoint.

1. Read `## Requested deliverables` in `TASK_STATE.md`. WHEN the section is absent (legacy task), OR its only row is the `- none named` sentinel, this gate is a no-op: skip it and proceed.

2. Classify the context. Finalization: `task-close`, or `review-hard` as the pre-PR final pass. Checkpoint: `where-we-at`, `slice-closure`, and any other `review-hard` run. At a checkpoint an `in-scope` row not yet done is normal remaining work.

3. Reconciled vs silent omission. A row is reconciled when it is `done` or `de-scoped:<reason>` with that reason recorded in `DECISIONS.md`. A deliverable named in the brief with NO ledger row, or a row dropped without a recorded de-scope, is a silent omission. You MUST cross-check the ledger against the brief: read the task's `README.md` (which `task-init` seeds from the brief, its `## Brief` section) and the original request when in context, and confirm every deliverable named there has a row. WHEN no brief artifact is available, reconcile the rows that exist and state that ledger-vs-brief completeness could not be re-verified (do not claim it was).

4. Apply the gate by context.
   - WHEN finalizing: IF any row is unreconciled (still `in-scope`, or a silent omission per step 3), THEN this command's output is invalid. Name each unreconciled deliverable, say whether it should be delivered or de-scoped, and route to `implementation-plan` (plan the missing work) or `decision-interview` (a de-scope, which only the person's answer records). A provisional decision never de-scopes (ADR-0233): in an attended chain on a task branch or under standing authorization (ADR-0244) the row stays `in-scope` and is listed as `Not delivered, needs you: <deliverable>: <what is undecided>` in `TASK_STATE.md ## Open questions / blockers`: `task-close` still holds it unreconciled, `review-hard`'s pre-PR pass only lists it.
   - WHILE at a checkpoint: report each not-yet-done `in-scope` row as remaining work and do NOT invalidate output on that basis. A silent omission (step 3) is NOT normal progress: name the missing deliverable, record it in the `TASK_STATE.md` checkpoint output as a must-address finding (never a bare one-line mention), and route it as the finalization branch does. Neither case invalidates the output at a checkpoint.

A de-scope is allowed; silence is not.
