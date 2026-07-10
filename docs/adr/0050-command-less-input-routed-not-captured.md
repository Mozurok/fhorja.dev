# ADR-0050: Command-less input is routed, not captured

- **Status**: Accepted
- **Date**: 2026-06-23
- **Tags**: routing, command-less-input, guardrail, read-only, additive, portability, lean-memory, audit-log-non-goal

## Context

The WOS is command-driven. Every behavior contract lives in a `commands/<name>.md` file, and the user normally starts a turn by invoking one. But a large share of real turns invoke no command: the user types a free-form prompt, a question, a stray observation, or a one-line aside. Until now the WOS had no defined behavior for that case. `wos/entry-points.md` answers "which command do I start with" but assumes the user is choosing a command; nothing covered "the user typed raw text and picked nothing, what happens".

The maintainer's first proposal was to attach `capture-observation` to every command-less prompt so the system always records what was written. A research-and-design workflow (five grounding and research agents, three independent proposals, a synthesis, two adversarial verifiers) tested that idea against the repo and rejected it. Three symptoms were named for the gap (the input is not captured, not logged, not routed). Only one is real.

- Not routed: a real gap. The agent could silently no-op or guess a command that does not fit.
- Not captured: correct by design. `capture-observation` writes to `TASK_STATE.md`, the curated task memory, and requires an active task folder. Pouring every utterance there violates lean-memory (`wos/context-budget.md`) and the PROPOSED-by-default write policy (ADR-0001). Most command-less prompts are questions, navigation, or chatter, not observations worth resurfacing later.
- Not logged: a non-goal the audit-log validator actively rejects. `scripts/verify-log-validator.py` pins a closed `OWNER_TYPES` set (`command`, `persona`, `fleet-merger`) and a closed events set; a raw `user_prompt` line fails validation. ADR-0049 also scopes the activity timeline to state-changing commands on purpose.

The "always capture-observation" idea is a degenerate single-target router: it breaks for new-work, navigation, incident, and decision inputs, and it refuses outright when there is no active task folder.

## Decision

Command-less input is routed, not captured. On a turn that invoked no command, the WOS classifies intent and PROPOSES at most one command; it persists nothing on its own.

Add a core guardrail rule, `### Command-less input (triage before answering)`, to `WORKFLOW_OPERATING_SYSTEM.md` under `## Cross-cutting workflow guardrails`, next to Routing memory and Official command names. It is a CORE guardrail, not a sequencing heuristic. Placement is load-bearing: the ADR-0025 light bootstrap tier (which includes `what-next`) is allowed to skip the sequencing heuristics, and the rule defers to `what-next`. A heuristic-placed rule would be absent on exactly the command it delegates to. `commands/_shared/mandatory-context-bootstrap.md` is updated to name "command-less input triage" in the core-guardrail list the light tier must read.

The rule: on a command-less turn, do not silently no-op. Default to answering plainly. Propose a command only on a clear intent match, exactly one, and defer to `what-next`'s single-best-command logic. The buckets resolve the three empty states explicitly so the agent never proposes a command that will refuse:

- no project folder, new-work intent: `project-bootstrap`
- project folder but no active task, new-work intent: `task-init`
- active task plus a genuine observation, question, hypothesis, or concern: `capture-observation` (eligible only here, because it requires an active task folder)
- active task plus a canonical decision or course correction: `decision-interview` or `direction-adjust`
- concrete observed failure: `incident-triage`
- navigation question: `what-next`
- pure chatter, one-line factual questions, casual asides: answer plainly, propose nothing

The last item is the default, not a bucket. The router proposes only on a clear match; everything else gets a plain answer. Capture happens one step later, only if the user accepts the proposed command, which then runs its normal substrate-write protocol and logs as it does today.

Scope of this ADR (v1): the portable prose rule only. A Claude Code `UserPromptSubmit` trigger hook that fires the rule mechanically is a documented optional follow-up; it is `UserPromptSubmit`-only and degrades to the prose rule on Cursor and Codex, so it is not part of the contract. Raw-prompt logging is explicitly out of scope and out of intent.

## Consequences

### Positive

- The WOS stops silently dropping command-less input; the most common real turn now has a defined behavior.
- Curated task memory stays lean: nothing is written by the router, so it cannot pollute `TASK_STATE.md`.
- Fully additive and read-only: no new command (no 4-registry cost), no schema change (the audit-log validator and the ADR-0049 timeline scope are untouched), no new dependency.
- Portable across hosts: the rule is prose in the core guardrail set, so it loads on Claude Code, Cursor, and Codex alike.

### Negative

- A prose rule routes probabilistically, not deterministically. A cooperative agent follows it; a mechanical guarantee needs the optional hook, which is Claude Code only.
- The "pure chatter, propose nothing" default is a judgment boundary. Too strict and a real observation is missed; too eager and ceremony returns through the front door. Eval scenario 62 pins the boundary.

### Neutral

- Logging command-less prompts is recorded here as a non-goal. If a forensic need ever appears, it would ship later as a separate gitignored journal behind its own decision, never in `VERIFICATION_LOG.jsonl` and never in curated memory.

## Alternatives considered

### Alternative 1: always attach capture-observation (the maintainer's first idea)

Rejected. Degenerate single-target router. `capture-observation` requires an active task folder and is scoped to genuine observations, so it breaks for new-work, navigation, incident, and decision inputs, and writing every utterance into `TASK_STATE.md` violates lean-memory and ADR-0001.

### Alternative 2: a hook that appends every command-less prompt to the audit log

Rejected as designed. `scripts/verify-log-validator.py` rejects a `user_prompt` owner and event, and ADR-0049 deliberately keeps the timeline to state-changing commands. Logging would force a separate journal that nothing reads. The hook survives only as an optional trigger for the prose rule, not as a logging path.

### Alternative 3: a new command-router command

Deferred and unnecessary. `command-router` was already folded into `what-next` (see ROADMAP). A new command adds 4-registry membership, a count-marker bump, an eval scenario, and a skills rebuild. The core guardrail rule plus `what-next` meet the need without a new command.

## References

- ADR-0001: PROPOSED-by-default write policy (why the router persists nothing).
- ADR-0025: bootstrap tiers (why the rule must be a core guardrail, not a heuristic).
- ADR-0034: substrate-write protocol and the audit-log validator (why a user_prompt line fails).
- ADR-0049: activity timeline scope (state-changing commands only).
- `wos/context-budget.md`: the lean-memory principle.
- `commands/what-next.md`: the single-best-command logic the rule defers to.
