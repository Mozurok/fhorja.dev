---
activation: model_decision
description: Operating modes (minimal, strict, teaching, assisted). Load when the task posture needs to change.
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
- A long `### Definition of done` block may be summarized to one line in the response (the full content lives in `commands/<name>.md` and is not re-quoted).
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
- Under ambiguity, `what-next` itself produces the ranked form: it presents 2 or more candidate commands with a one-line rationale each, in recommended order, instead of a single answer.
- The same response names what would be premature right now and why, so the user learns the ordering rule rather than only the next click.
- Anti-patterns from `wos/anti-patterns.md` are surfaced inline when they would otherwise apply, with a one-line "this is anti-pattern X; the safer alternative is Y" note.

When to use: first few sessions for a new user; onboarding a teammate; producing a demo run for documentation.

When NOT to use: production incident response; deadline-pressured work where pedagogical preface is friction. Teaching mode is intentionally heavier; it is not the default.

### assisted
For a person who wants every stop ADR-0233 removed back, on an attended git-backed task. The behavior is provisional P-8 of the task that produced ADR-0233 (`Impact: high`); the maintainer confirms or replaces it.

Effects. A declared `Operating mode: assisted` restores every stop ADR-0233 removed, and nothing else:
- `task-init` SHALL NOT create a task branch and SHALL NOT write a `Task branch:` line. Without that line the run is not "an attended chain on a task branch" (`### Adaptive handoff`), so every rule keyed on that phrase falls back to its pre-ADR-0233 behavior. The phrase also excludes a declared assisted mode directly, for a task that already had the line when the mode was declared.
- A decision the request does not contain SHALL be asked, and the chain SHALL wait for the answer (reason 2). The question-asking commands skip their provisional path, so no `### P-N` is written; the answer is locked as a `D-N`.
- A check the agent cannot run on itself SHALL stop the chain as it did before ADR-0233 (reason 4): the Godot feel-verdict floor refuses, and `approve-plan`'s ENVIRONMENT exit ends on the terminal form. The closure floors that already recorded before ADR-0233 (ADR-0203) still record.
- `branch-commit --apply` SHALL NOT hand on to `pr-package --apply` after the commit. The person runs it, or asks for it.
- What ran alone before ADR-0233 keeps running: `approve-plan`'s blinded review and the local commit on a named branch (ADR-0163, ADR-0167). Reason 1 is unchanged: ready for review, merge, publish and outward egress stay the person's.

When to use: the maintainer wants to answer each product decision as it comes up and to start the push and the draft PR themselves, a decision is unusually costly to get wrong, or the task is being used to show someone the workflow's decision points.

When NOT to use: routine work where the draft PR's "Decisions made without you" section is enough review. Assisted mode trades throughput for a stop at every product decision and at the end; misuse means paying that cost where the default already covers it.

## Declaring the mode

The user declares the operating mode at `task-init` time, either in the task description or as an explicit `Operating mode: <minimal|strict|teaching|assisted>` line in the input. If declared, `task-init` records it in the new task's `TASK_STATE.md` `## Resume notes` field with the format `Operating mode: <name>`. Subsequent spine commands read that line and apply this file (ADR-0162). Auto-suggestion in `## Recommended pipeline` is not a declaration. A declared `strict` mode changes where `implementation-plan` hands off: to the next missing of `invariants-and-non-goals`, `test-strategy`, `approve-plan`, rather than straight to `approve-plan` (ADR-0162). It used to take precedence over the inline Approval log `implementation-plan` wrote on the no-escalation path; ADR-0208 removed that log, so every plan now reaches `approve-plan` and strict only decides what comes before it. A declared `strict` also rules out the one-slice route, which skips `approve-plan` (ADR-0225).

**Auto-suggestion (ADR-0025):** `task-init` may auto-suggest an operating mode based on its complexity assessment:
- `Escalations: none` -> suggests `minimal` (the signal that replaced the retired tier label, ADR-0207)
- an auth, payments, compliance, PII, or multi-tenant isolation surface -> suggests `strict` (the categorical trip condition that survived the retired Strict tier, ADR-0207)
The suggestion appears in the `## Recommended pipeline` section of TASK_STATE.md. The user can accept or override. Auto-suggestion does not auto-activate; the user must confirm or the mode remains undeclared (standard behavior).

Switching modes mid-task is allowed but explicit: run `sync-task-state` (or `state-reconcile` if other artifacts also drifted) and update the `## Resume notes` line. The transition itself is a `D-N: mid-task adjustment` entry in `DECISIONS.md` if the mode change reflects a re-evaluation of risk; routine switches (a teaching task graduating to the standard posture once the user is fluent) do not need a decision entry.

## Default

When no operating mode is declared, every command operates under its native rules with output depth determined by its category in `wos/output-depth-policy.md`. This is "balanced" in spirit but unnamed; it is simply the workflow's normal behavior.


## Parallel dispatch (orthogonal mode)

Parallel dispatch is a tooling-level capability (fan-out workers via the `Agent` tool or equivalent batch primitive), not a ceremony level. It changes *how* a single phase of work is executed, not *which* artifacts or reviews the workflow demands. Because of that, it composes with the three ceremony modes (minimal / strict / teaching) along an independent axis: a task can be `minimal + parallel`, `strict + parallel`, or `teaching + parallel` and the ceremony rules above still apply unchanged. The only thing parallel dispatch decides is whether a batch of independent sub-steps runs sequentially or concurrently; safety and reviewability are still governed by the ceremony mode in effect.

Compatibility:

| Ceremony mode | With parallel dispatch | Notes |
| --- | --- | --- |
| minimal | OK -- recommended | Ideal for read-only mega-batches (audits, inventories, fleet scans) where each worker returns evidence and no worker mutates state. |
| strict | OK with guardrails | Every batch MUST stay reviewable: workers return typed payloads (ADR-0158), the orchestrator is the sole writer (ADR-0038 Rule 2), and each batch lands as one reviewable commit so the diff is inspectable as one unit. |
| teaching | AVOID | Teaching mode is single-step learning by design; parallel dispatch hides the trace the learner is supposed to watch. Run sequentially until the user is fluent, then graduate. |

References: ADR-0038, ADR-0039, `wos/workflow-patterns.md`.
