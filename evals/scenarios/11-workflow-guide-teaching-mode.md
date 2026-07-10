# Eval scenario 11: workflow-guide in teaching mode

- **Tags**: workflow-guide, teaching-operating-mode, onboarding, phase-explanation
- **Last reviewed**: 2026-05-08
- **Status**: active

## Goal

Validates that `workflow-guide` produces pedagogical responses appropriate for a user learning the workflow, especially under the `teaching` operating mode: each response prefaces work with a 2-3 line phase explanation, routes via `workflow-guide` rather than `what-next` on ambiguity, and surfaces relevant anti-patterns inline.

This exercises:

- The teaching operating mode (ADR-0008).
- The `workflow-guide` command's pedagogical positioning (vs `what-next` for fluent users).
- The "what phase, why this command, what next" preface format.

## Setup

Assume an active task at `projects/acme__widget-pricing/active/2026-05-08_first-time-user-task/` was just initialized with `Operating mode: teaching` recorded in `TASK_STATE.md` `## Resume notes`. The task is mid-discovery: `task-init` ran, `impact-analysis` ran, but the user is unsure what to do next. They are on session 2 with the workflow.

`TASK_STATE.md` (excerpt):

```text
# TASK_STATE
## Task summary
Add a feature toggle for the new pricing experiment.
## Current phase
discovery
## Last completed step
- Command: impact-analysis
- Mode: Ask
- Summary: Bounded the change to 3 files; identified the existing feature-toggle library in src/utils/featureFlags.ts.
## Recommended next step
- Command: (uncertain; user new to the workflow)
- Mode: Ask
- Why: Multiple plausible next steps; pedagogical guidance preferred over a single fast routing answer.
## Resume notes
Operating mode: teaching
```

## Input prompt

```text
Run @commands/workflow-guide.md

Active task: projects/acme__widget-pricing/active/2026-05-08_first-time-user-task/
Mode: Ask

I'm new to this workflow. I just ran impact-analysis but I'm not sure what comes next. Should I plan the implementation, or do I need more discovery first?
```

## Expected response shape

- Response begins with workflow-guide's persona line.
- Response opens with a 2-3 line phase explanation: "you are in discovery; impact-analysis completed; the next phase is either contract-hardening (if invariants are not yet locked) or planning (if the change is small enough to plan directly)".
- Response presents the next 2-3 candidate commands with rationale, not a single routing answer:
  - `invariants-and-non-goals` (recommended when the change touches behavior that needs explicit boundaries before planning)
  - `targeted-questions` (recommended when factual gaps remain)
  - `decision-interview` (recommended when policy or behavioral choices are still open)
  - `implementation-plan` (recommended when discovery is complete and the change is small)
- The recommendation is grounded in what `TASK_STATE.md` shows (impact-analysis bounded the change to 3 files; existing feature-toggle library identified). Concrete enough to act on, not generic.
- Response surfaces a relevant anti-pattern inline if applicable (e.g., "do not skip `invariants-and-non-goals` if the feature toggle changes default behavior; the safer path is to lock what must not change first").
- Response output depth is `Balanced` (the default for teaching mode); not as terse as `Lean`, not as exhaustive as `Deep`.
- `### Handoff` block at the end. `Run now:` is the recommended next command from the candidates above. `Mode:` is `Ask` or `Plan`. adaptive handoff block has the task path and links to the next command's required inputs.

## Pass criteria

1. **Phase explanation present**: response opens with a 2-3 line preface naming the current phase, the just-completed command, and the conceptual next phase.
2. **Multiple candidates ranked**: response presents at least 2 candidate next commands with rationale, not a single answer. (Distinguishes workflow-guide from what-next, which gives one answer.)
3. **Recommendation grounded in TASK_STATE**: the recommended next command references specific facts from `TASK_STATE.md` (the 3 files identified by impact-analysis; the feature-toggle library; the discovery phase). Generic "you should plan now" is not enough.
4. **Anti-pattern surfaced if applicable**: response surfaces a relevant anti-pattern when one applies. (Not always required; only when the user's likely next step has a known failure mode.)
5. **Output depth Balanced**: the response is fuller than Lean (no terse single-paragraph) but not Deep (no exhaustive Definition of done quote). Verifiable by length and structure.
6. **Operating mode read from TASK_STATE**: the response acknowledges (implicitly or explicitly) that teaching mode is active, e.g., by including the phase preface that minimal mode would skip.
7. **Handoff intact**: response ends with a complete Handoff. `Run now:` is one of the candidate next commands recommended in the body.

## Failure modes to watch

- **Single-answer routing**: response gives one next command without alternatives. That is `what-next` behavior; `workflow-guide` should rank candidates with rationale.
- **No phase explanation**: response skips the 2-3 line preface and dives into recommendations. Loses the pedagogical layer that teaching mode is supposed to provide.
- **Mode ignored**: response output is identical to what `what-next` would produce. Operating mode `teaching` recorded in `TASK_STATE.md` was not read or not honored.
- **Generic recommendation**: response says "consider impact-analysis or implementation-plan" without grounding in the specific facts of this task. A new user cannot tell which one applies to their case.
- **Routing to what-next**: response says "for ongoing work, run what-next next time". That is the right hint for a fluent user but contradicts the teaching mode posture (the user is learning; workflow-guide should remain the routing command for now).
- **Anti-pattern omitted when present**: a clear known failure mode applies (e.g., implementing without locking invariants on a feature-toggle change), and the response does not surface it.

## Notes

- Related ADRs: [ADR-0008](../../docs/adr/0008-operating-modes.md) (operating modes; teaching mode definition), [ADR-0009](../../docs/adr/0009-task-shape-system.md) (the task shape this is operating in).
- Related commands: `commands/workflow-guide.md` (this command), `commands/what-next.md` (the fast-routing alternative for fluent users), `commands/im-stuck.md` (the recovery alternative when the user is confused, not just learning).
- The teaching/learning distinction is a soft one: a new user might run `what-next` and be fine; a fluent user might run `workflow-guide` for context. The operating mode is the explicit declaration that shapes which is the default.
- This scenario is intentionally ambiguous about whether the right answer is `invariants-and-non-goals` or `implementation-plan`; the teaching response should rank both with grounded rationale rather than picking one for the user.

## History

- 2026-05-08: scenario authored. Initial pass criteria defined; not yet run against a model.
