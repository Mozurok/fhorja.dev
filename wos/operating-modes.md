---
activation: model_decision
description: Operating modes (minimal / strict / teaching). Load when the task posture needs to change.
---

# Operating modes

A per-task posture that changes how strictly the workflow's commands enforce ceremony. Operating mode is **orthogonal** to:

- **Editor mode** (`Ask` / `Plan` / `Agent` / `Debug`; per-command intent; see `## Editor mode policy`).
- **Output depth** (`Lean` / `Balanced` / `Deep`; per-command verbosity; see `## Output depth policy` or load `wos/output-depth-policy.md`).

Operating mode applies to the task as a whole and is declared at `task-init` time. When no operating mode is declared, the workflow operates under its standard rules (implicit "balanced" posture; no override).

## Modes

### minimal
For XS tasks where ceremony adds friction without reducing risk. Examples: typo fixes, copy edits, single-file test additions where the contract is obvious from surrounding tests, log-line additions to a path already covered by integration tests.

Effects:
- Output depth defaults to `Lean` regardless of the command's category in `## Output depth policy`.
- Long-form `Why this mode:` and `### Definition of done` blocks may be summarized to one line each in the response (the full content lives in `commands/<name>.md` and is not re-quoted).
- Optional task files (`IMPACT_ANALYSIS.md`, `INVARIANTS_AND_NON_GOALS.md`, `TEST_STRATEGY.md` when not already mandated by the task shape) are never created.
- The `### Handoff` block remains mandatory and full per `## Global output contract` (ADR-0002 in `docs/adr/`); minimal does not skip the contract.

When to use: Work complexity = `LOW`; blast radius is contained; no contract or invariant is at risk.

When NOT to use: blast radius unclear; contract not yet hardened; the user is asking for ceremony reduction to bypass a real risk signal. Minimal mode trims friction; it does not remove safety.

### strict
For high-risk tasks where additional ceremony is required: high blast radius, contract sensitivity, payment / auth / compliance work, production incidents with rollback considerations.

Effects:
- Output depth defaults to `Deep`.
- `invariants-and-non-goals` is **mandatory** (not optional), even on the Typical or Small flows.
- `test-strategy` is **mandatory**.
- `review-hard` is **required** before `pr-package`; `pr-package` runs in this mode are expected to follow a clean `review-hard` pass and to reference its conclusions.
- Decisions in `DECISIONS.md` include an explicit "rollback / unwind" note alongside the rationale.

When to use: Work complexity = `HIGH`; auth / cryptography / payments / compliance / multi-tenant isolation; production incidents where a wrong assumption creates safety or compliance exposure.

When NOT to use: small bounded changes; test-only or doc-only tasks. Strict mode adds friction; misuse means the friction is wasted.

### teaching
For users learning the workflow (first ~5 sessions, onboarding a teammate, demoing the system).

Effects:
- Output depth defaults to `Balanced`.
- Each command's response prefaces its work with a 2-3 line explanation: what phase this command serves, why this command was chosen now, what to expect next.
- Routing emphasizes `workflow-guide` rather than `what-next` when ambiguity arises.
- Anti-patterns from `wos/anti-patterns.md` are surfaced inline when they would otherwise apply, with a one-line "this is anti-pattern X; the safer alternative is Y" note.

When to use: first few sessions for a new user; onboarding a teammate; producing a demo run for documentation.

When NOT to use: production incident response; deadline-pressured work where pedagogical preface is friction. Teaching mode is intentionally heavier; it is not the default.

## Declaring the mode

The user declares the operating mode at `task-init` time, either in the task description or as an explicit `Operating mode: <minimal|strict|teaching>` line in the input. If declared, `task-init` records it in the new task's `TASK_STATE.md` `## Resume notes` field with the format `Operating mode: <name>`. Subsequent commands read it from there and adapt.

**Auto-suggestion (ADR-0025):** `task-init` may auto-suggest an operating mode based on its complexity assessment:
- Express tier -> suggests `minimal`
- Strict tier -> suggests `strict`
The suggestion appears in the `## Recommended pipeline` section of TASK_STATE.md. The user can accept or override. Auto-suggestion does not auto-activate; the user must confirm or the mode remains undeclared (standard behavior).

Switching modes mid-task is allowed but explicit: run `sync-task-state` (or `state-reconcile` if other artifacts also drifted) and update the `## Resume notes` line. The transition itself is a `D-N: mid-task adjustment` entry in `DECISIONS.md` if the mode change reflects a re-evaluation of risk; routine switches (a teaching task graduating to the standard posture once the user is fluent) do not need a decision entry.

## Default

When no operating mode is declared, every command operates under its native rules with output depth determined by its category in `wos/output-depth-policy.md`. This is "balanced" in spirit but unnamed; it is simply the workflow's normal behavior.


## Parallel dispatch (orthogonal mode)

Parallel dispatch is a tooling-level capability (fan-out workers via the Task tool or equivalent batch primitive), not a ceremony level. It changes *how* a single phase of work is executed, not *which* artifacts or reviews the workflow demands. Because of that, it composes with the three ceremony modes (minimal / strict / teaching) along an independent axis: a task can be `minimal + parallel`, `strict + parallel`, or `teaching + parallel` and the ceremony rules above still apply unchanged. The only thing parallel dispatch decides is whether a batch of independent sub-steps runs sequentially or concurrently; safety and reviewability are still governed by the ceremony mode in effect.

Compatibility:

| Ceremony mode | With parallel dispatch | Notes |
| --- | --- | --- |
| minimal | OK -- recommended | Ideal for read-only mega-batches (audits, inventories, fleet scans) where each worker returns evidence and no worker mutates state. |
| strict | OK with guardrails | Every batch MUST stay reviewable: workers default to PROPOSED, and the batch is gated by a single apply-step commit per batch so the diff is inspectable as one reviewable unit. |
| teaching | AVOID | Teaching mode is single-step learning by design; parallel dispatch hides the trace the learner is supposed to watch. Run sequentially until the user is fluent, then graduate. |

References: ADR-0038, ADR-0039, `wos/workflow-patterns.md`.
