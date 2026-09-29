# ADR-0241: A mode change, a model or a new session never stops the chain

- **Status**: Accepted. The mechanism rests on provisional decisions of the 2026-09-28 handoff-continues-across-mode task (P-1 to P-4), listed under `## Notes`, which await the maintainer's confirmation. Confirmed by the maintainer on 2026-09-28: each of those provisional decisions now has a locked D-N carrying `Confirms:` in the task's DECISIONS.md.
- **Date**: 2026-09-28
- **Supersedes**: in part, [ADR-0186](./0186-the-handoff-continues-the-chain.md): its four stop reasons stand, and the continuation rule now also names three things that are never a reason to stop and makes an offered choice a stop that has to name its reason. The rest of ADR-0186 stands.
- **Tags**: handoff, continuation, global-output-contract, editor-mode, model-routing, dispatch-role, attended, adr-0186, adr-0233, adr-0236

## Context

On 2026-09-28 a session on the maintainer's own project finished `approve-plan` and ended its turn
instead of continuing. Its Handoff read `Run now: test-strategy`, `Mode: Plan`, `Work complexity:
MEDIUM`, and a `Reason:` that ended by naming the next wave's model. It then asked the maintainer to
choose between running `test-strategy` now and opening a separate session on that model. Earlier the
same task had written an execution playbook telling the human to run each slice in a fresh session
on a named model by pasting a template.

The `Reason:` named none of the four stop reasons ADR-0186 lists. Three things in the rule let the
session read its own handoff as a stop anyway.

- `Mode: Plan` maps to Claude Code plan mode in `wos/editor-mode-mappings.md`, where files are not
  written. After an `Agent` step, a `Plan` label reads as a mode switch only the user can make. The
  spec already says the mode names are the agent's intent, not the tool's UI, and that task memory is
  written `APPLIED` in every mode (ADR-0199), but nothing said a `Mode:` change is not a stop.
  `approve-plan` itself writes `Mode: Plan` on its test-strategy route.
- A model and a new session were offered as the next step. ADR-0236 has the session drive the chain
  and dispatch sub-agents by role, so there is no case where the chain should go back to the human to
  be reopened on another model. The ADR-0236 lint reads command prose, never a Handoff a run emits,
  and `wos/model-routing.md` picks one model per task without saying what a chain already running on
  another model does.
- Offering the user a choice between continuing and something else is a stop. The rule said a stop
  names its reason and said nothing about a choice, so the choice went out with no reason at all.

## Decision

The continuation rule in `WORKFLOW_OPERATING_SYSTEM.md ### Adaptive handoff` names three things that
are never a reason to stop: a `Mode:` different from the current one, a suggested model, and a fresh
session. An attended session continues in the harness mode and model it is in and dispatches
sub-agents by role. Offering the user a choice between continuing and anything else is itself a stop,
so it names its stop reason in `Reason:` or it is not offered. In an attended chain on a task branch,
where ADR-0233 made reasons 2 and 4 records, that reason is 1 or 3. A Handoff's `Reason:` names a
role (`mechanical`, `judgment`), never a model.

- The rule lives in the spec (the continuation paragraph, the `### Work complexity (capability
  routing)` no-model rule, and `### Mapping to other tools`) and in `commands/_shared/handoff-body.md`,
  which every command carries. This ADR records why.
- `commands/approve-plan.md` says its `test-strategy` route with `Mode: Plan` continues in the same
  turn. `wos/editor-mode-mappings.md`, `wos/model-routing.md` and `wos/context-budget.md` lose the
  readings that pointed at a per-mode, per-model or per-session hand-back.
- `scripts/validate-transcript.sh` refuses a Handoff block that names a model: a `claude-` id, a
  `--model` flag, or a capitalized family name. `evals/scripts/structural-evals.py`
  `handoff-continues-across-mode` pins the rule text and refuses a `claude --model` or
  one-session-per-slice instruction in `commands/`, `templates/` and `wos/`. Scenario 147 grades the
  behavior a single transcript cannot show: a Mode change alone does not stop, and a stop names its
  reason.
- The four stop reasons, the ADR-0233 attended-chain rules and the Handoff block's shape are
  unchanged. Unattended and fleet-dispatched runs keep `### Unattended sessions`.

## Consequences

### Positive

- The failure above has a named rule against each of its three parts, and the model-naming part fails
  a check.
- The maintainer stops being the transport between models. Cheaper work reaches a cheaper model
  through a `mechanical` dispatch from the same session, which is what ADR-0236 built.
- A choice offered at the end of a turn now has to say why the chain could not continue, which is the
  question the maintainer would otherwise have to ask.

### Negative

- The validator reads the Handoff block only. A run that offers a model or a choice in prose after the
  block is caught by scenario 147, which needs a model run, not by the validator.
- Whether a turn stopped cannot be read from one transcript. That half of the rule stays behavioral.
- A user who wants a different model for the next step now has to say so; the chain will not suggest
  it.

### Neutral

- `wos/model-routing.md` keeps its per-task table. It is advice for the session a person starts, not
  a step in a running chain.
- `Mode:` keeps its four values and its meaning as the next step's intent.

## Alternatives considered

### Alternative 1: drop `Mode:` from the Handoff

- Remove the line so there is nothing to read as a switch.
- Rejected. The Handoff shape is an interface an external consumer parses, the line still tells a
  Cursor user which mode fits the step, and the defect was the missing sentence, not the field.

### Alternative 2: allow a model in `Reason:` as advice

- Keep model names legal in the Handoff when framed as a suggestion.
- Rejected for the reason ADR-0004 gave and ADR-0236 repeated: a model name in output ages with the
  lineup and means nothing to a harness that cannot select it, and here it was the thing that turned a
  continuation into a hand-back.

### Alternative 3: a lazy wos topic for the rule

- Put the non-reasons in a topic loaded on demand.
- Rejected. The continuation rule is what every command reads at the end of its run; a rule a command
  has to choose to load is the gap this ADR closes.

## References

- `WORKFLOW_OPERATING_SYSTEM.md` `### Adaptive handoff`, `### Work complexity (capability routing)`, `## Editor mode policy` `### Mapping to other tools`.
- `commands/_shared/handoff-body.md`; `commands/approve-plan.md`.
- `wos/editor-mode-mappings.md`, `wos/model-routing.md`, `wos/context-budget.md`.
- `scripts/validate-transcript.sh`; `evals/scripts/structural-evals.py` (`handoff-continues-across-mode`); `evals/scripts/guard-mutation.py`; `evals/scenarios/147-a-mode-change-or-a-model-does-not-stop-the-chain.md`.
- ADR-0186, ADR-0199, ADR-0233, ADR-0236.

## Notes

- Provisional decisions of the task, for the maintainer to confirm: the two-layer pin (P-1), what
  this ADR supersedes (P-2), how the shared-block sentence fits the Load ceiling (P-3), and which lines
  were corrected (P-4).
- A grep of `commands/`, `templates/` and `wos/` found no surface that tells the human to run slices
  session by session on a named model. The playbook in the failure was written by the session, not
  copied from the workflow.
