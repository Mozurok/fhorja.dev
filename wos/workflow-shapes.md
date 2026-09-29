---
activation: model_decision
description: Task shape selection: which workflow flow for this type of task. Load when the task does not fit the default flow.
---

# Recommended workflows by task shape

Navigation note:
- these are scenario shortcuts; command-level authority remains in `## Command roles` (load `wos/command-roles.md` for detail)
- every shape starts from the default pipeline, `task-init` -> `implementation-plan` -> `approve-plan` -> `implement-approved-slice` -> `branch-commit --apply` -> `pr-package --apply` (ADR-0184, ADR-0233). The last step runs in an attended chain with a configured remote and no declared `Operating mode: assisted`, and ends at the draft pull request; ready for review and merge stay the person's. A step beyond it is added only when the disqualifier named beside it fires, and `task-init` writes each fired one on the `Escalations:` line (ADR-0207). Every plan `implementation-plan` writes passes through `approve-plan`, which runs its own blinded review (ADR-0208); the one-slice route below has no such plan (ADR-0225).

## Typical unclear engineering task
1. `task-init`
2. `code-locate` (only when files in scope are not yet known; populates `SOURCE_OF_TRUTH.md` so the next step can run with concrete files)
3. `impact-analysis` (added when the scope needs more than one sentence to state, or the change touches 5 or more files)
4. `invariants-and-non-goals` (added on a strict surface: auth, payments, compliance, PII, or multi-tenant isolation)
5. `targeted-questions` when facts are missing, or `decision-interview` when a decision the prompt does not contain is needed before the first line of code, or the change spans multiple packages or adds an external service dependency (in an attended chain on a task branch it records a provisional `P-N` and the chain continues)
6. `implementation-plan`
7. `test-strategy` (added on a strict surface, or when the plan names behavior worth pinning with tests)
8. `approve-plan`
9. `implement-fleet` when the plan's `## Execution waves` show a remaining wave of size 2 or more with `Scope` and `Depends-on` declared, on a harness with per-agent worktree isolation; otherwise `implement-approved-slice` (waves-aware per ADR-0042)

## Contract-sensitive task
1. `task-init`
2. `impact-analysis`
3. `invariants-and-non-goals`
4. `decision-interview`
5. `resolve-contract-gaps`
6. `contract-signoff`
7. `implementation-plan`
8. `approve-plan`

## Well-scoped task (no escalation fired; the retired Express label, ADR-0025)
For well-scoped tasks where the user provides all decisions upfront and the scope is describable in one sentence. Examples: add a single API endpoint with known schema, fix a bug with known root cause, add a component matching an existing pattern.
1. `task-init` (escalation assessment; `Escalations: none`, suggests `Operating mode: minimal`)
2. `implementation-plan` (lightweight; often single-slice)
3. `approve-plan`
4. `implement-approved-slice`
5. `branch-commit --apply` (then `pr-package --apply` in an attended chain with a configured remote, ADR-0233)

Skip rationale: `impact-analysis` is unnecessary when the blast radius is obvious from the task description. `decision-interview` is unnecessary when all decisions are provided upfront. `slice-closure` is handled inline by `implement-approved-slice` (see Slice completion check). This shape is what `task-init` produces when no disqualifier fires and its `Escalations:` line reads `none` (ADR-0184, ADR-0207); it is not a named tier and `task-init` emits the fired rule rather than a label.

## One-slice change (the one-slice route, ADR-0225)
For an attended change that fits one sentence, touches at most two files the brief names, and needs no locked decision beyond the brief (an open decision of `Impact: normal`, on a task branch, becomes a provisional `P-N` that `task-init` writes and the draft PR lists; an `Impact: high` one sends the task through `implementation-plan` and `approve-plan`, ADR-0239), with no escalation fired and no `Operating mode: strict` declared.
1. `task-init` (writes `Route: one-slice` with its evidence, the single approved slice, any normal-impact `P-N`, both lock signals, and runs `check-plan-coverage.sh`)
2. `implement-approved-slice` (runs `check-doc-sync.sh --against HEAD` at inline close; exit 1 goes to `implement-slice-complement`, a second to `implementation-plan`)
3. `branch-commit --apply` (then `pr-package --apply` in an attended chain with a configured remote, ADR-0233)

Skip rationale: the blinded plan review found one defect on a plan this small, a placement that renumbered a cited section, and that class now has a deterministic check. `implementation-plan` and `approve-plan` are skipped on this route only; a condition that stops holding sends the task back to `implementation-plan`.

## Greenfield POC (new project, stack not yet decided)
For starting a new product from an empty workspace where framework, libraries, and approach are genuinely open and shape every later task.
1. `project-bootstrap` (seed `PROJECT_CHARTER.md` and `REFERENCES.md` for the new project)
2. `capture-references` (when external UI/UX, API, or stack research is needed before deciding)
3. `task-init` (first task under the project)
4. `stack-recommend` (version-pinned stack for the empty workspace; this is the greenfield discovery step in place of `impact-analysis`, which has no blast radius to analyze on an empty repo)
5. `decision-interview` (lock the stack and the build-vs-buy and approach decisions)
6. `implementation-plan`
7. `approve-plan`
8. `implement-fleet` when the plan's `## Execution waves` show a remaining wave of size 2 or more with `Scope` and `Depends-on` declared, on a harness with per-agent worktree isolation; otherwise `implement-approved-slice`

Skip rationale: `impact-analysis` is replaced by `stack-recommend` because an empty workspace has no existing blast radius; the discovery that matters is choosing a current, compatible stack rather than analyzing impact on code that does not exist yet. The first real product task after scaffolding rejoins the Typical flow or the small task with impact-analysis. This is a documented sequence, not a single composite command.

## Small task with impact-analysis
1. `task-init`
2. `impact-analysis` (the scope needs more than one sentence, or the change touches 5 or more files)
3. `implementation-plan`
4. `approve-plan`
5. `implement-fleet` when the plan's `## Execution waves` show a remaining wave of size 2 or more with `Scope` and `Depends-on` declared, on a harness with per-agent worktree isolation; otherwise `implement-approved-slice` (waves-aware per ADR-0042)
6. `slice-closure` (opt-in for LOW/MEDIUM; see `commands/slice-closure.md`)
7. `branch-commit --apply` (then `pr-package --apply` in an attended chain with a configured remote, ADR-0233)

## Docs-only task (no production code change)
1. `task-init` (set `## Task scope level: full task`; `## Current closure target` names the doc set being updated)
2. `implementation-plan` (lighter; one slice covering the doc set, with explicit list of files to update; no test slices, no rollback notes)
3. `approve-plan`
4. `implement-approved-slice` (Agent mode against the docs)
5. `branch-commit --apply` (then `pr-package --apply` in an attended chain with a configured remote, ADR-0233)

Skip rationale: `impact-analysis`, `invariants-and-non-goals`, and `test-strategy` only apply when production behavior is at risk; doc updates do not change runtime behavior. If the doc set is large and cross-cutting (multiple READMEs across multiple repos, or normative spec changes that affect command contracts), treat it as a contract change, not a docs-only change, and let the disqualifiers decide what is added. Borderline call: changes to `WORKFLOW_OPERATING_SYSTEM.md`, `commands/*.md`, or `wos/<topic>.md` are **not** docs-only because they redefine workflow contracts. The file type alone adds nothing: a scope that needs more than one sentence or touches 5 or more files adds `impact-analysis`, and a decision the prompt does not contain adds `decision-interview`.

## Test-only task (test additions or improvements; no behavior change)
1. `task-init` (set `## Task scope level: full task`; `## Current closure target` names the test set being added or improved)
2. `test-strategy` (mandatory; defines what behavior the new tests pin down, what cases are covered, how regressions would surface)
3. `implementation-plan` (one slice per test set; no rollback notes)
4. `approve-plan`
5. `implement-approved-slice` (Agent mode adding the tests; existing tests are not modified unless they were measurably wrong)
6. `branch-commit --apply` (then `pr-package --apply` in an attended chain with a configured remote, ADR-0233)

Skip rationale: `impact-analysis` and `invariants-and-non-goals` only apply when product behavior changes; test-only tasks add coverage to behavior that is already locked. If a test discovers a real bug while being written (test fails against current code, and the bug needs fixing), **stop the test-only flow** and re-classify as a small task with impact-analysis or an incident-triage flow; do not let a test-only task drift into a behavior change.

## Refactor task (behavior preservation under structural change)
1. `task-init` (set `## Task scope level: full task`; `## Current closure target` names the refactor scope)
2. `impact-analysis` (refactors often have non-obvious blast radius; this step is not optional)
3. `invariants-and-non-goals` (the central invariant is "external behavior unchanged"; non-goals exclude opportunistic improvements)
4. `test-strategy` (**mandatory** for refactors; the test suite is the only proof that behavior is preserved. If the existing test coverage is too thin to anchor the refactor safely, the strategy adds the coverage **before** the refactor begins, as a separate slice or task)
5. `implementation-plan` (slices ordered to keep the codebase green at every step; behavior-preserving moves first, behavior-equivalent rewrites second)
6. `approve-plan`
7. `implement-approved-slice` (Agent mode; one slice at a time)
8. `review-hard` (refactors benefit from a focused engineering risk pass before delivery; the failure mode "refactor introduced a subtle behavior change" is exactly what review-hard catches)
9. `branch-commit --apply` (then `pr-package --apply` in an attended chain with a configured remote, ADR-0233)

Skip rationale: nothing is skipped versus the Typical flow; instead, `test-strategy` is upgraded from "if needed" to **mandatory**, and `review-hard` is upgraded from "if useful" to **expected**. The flow is a heavier sub-shape, not a shortcut.

If `test-strategy` reveals that adequate behavior coverage cannot be added in scope (the existing surface is untestable as-is), **stop the refactor**: the refactor is itself the right path forward, but it must be preceded by a separate task that adds the missing test infrastructure. Refactoring without behavior coverage is a known anti-pattern and is not a permitted shortcut even under deadline pressure.

## Resume task after interruption
1. `resume-from-state`
2. `what-next`

## Recovery from confusion or loop
1. `im-stuck`
2. do the smallest decisive recovery action
3. `state-reconcile` if multiple artifacts disagree with `TASK_STATE.md` or trust is low
4. `sync-task-state` if a single incremental `TASK_STATE.md` update is enough

## Concrete observed failure (incident triage)
1. `task-init` if no active task folder exists yet for this incident
2. `incident-triage`
3. then one of the following depending on the recommended fix size:
   - `HOTFIX`: `branch-commit` then `pr-package` (with explicit hotfix marker)
   - `SLICE`: `implement-approved-slice` (or `implementation-plan` first if no slice is approved yet)
   - `INVESTIGATION`: `impact-analysis` or `targeted-questions`, then back to `incident-triage` once diagnostic info is gathered
   - `ESCALATE`: `capture-observation` plus `team-update`

## Near delivery
1. `where-we-at` only if needed
2. `review-hard` if useful
3. `pr-package`

## After PR review (corrective, Greptile / CI / inline)
1. `pr-feedback-ingest`
2. `implement-approved-slice` or `implement-slice-complement` (or a small plan touch) as the matrix implies
3. `pr-package` again when the diff and narrative are stable

## After review requests a meaningful pivot
1. `post-review-pivot`
2. `decision-interview` / `resolve-contract-gaps` / `contract-signoff` as needed
3. `implementation-plan` (or slice updates) as needed
4. `implement-approved-slice`
5. `pr-package` again when the diff is stable
