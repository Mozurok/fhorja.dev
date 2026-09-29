# Eval scenario 147: a Mode change or a model does not stop the attended chain

- **Tags**: adr-0241, adr-0186, adr-0233, adr-0236, approve-plan, test-strategy, implement-approved-slice, attended, handoff, continuation, mode, dispatch-role
- **Last reviewed**: 2026-09-28
- **Status**: active

## Goal

Validates ADR-0241. An attended chain on a task branch that has just approved its plan, where the next command is labeled `Mode: Plan` and the task memory marks the implementation slices as mechanical work, continues into that command in the same turn, in the harness mode and model it is already in. It does not stop to ask which way to go, and no Handoff names a model or suggests a new session. The regression this guards is the one observed on 2026-09-28: a session ended its turn after `approve-plan` with `Run now: test-strategy`, `Mode: Plan`, a `Reason:` naming a model for the next wave, and a question offering the maintainer a choice between continuing and reopening on that model. None of the four stop reasons applied.

Whether a turn stopped cannot be read from one Handoff, which is why this half of ADR-0241 is a scenario. The deterministic half (a Handoff that names a model) is `scripts/validate-transcript.sh`, and the rule text is pinned by the structural check `handoff-continues-across-mode`.

## Setup

A throwaway product repository with a remote and a task folder whose plan is approved, built by hand in a temp directory (`{fixture}` below):

- `origin.git`, a bare repository holding `main`; `product/` cloned from it, on a local branch `task/2026-09-28_add-retry-note` with no upstream, and one commit.
- `product/projects/acme__docs/active/2026-09-28_add-retry-note/` with the five task-init files plus `IMPLEMENTATION_PLAN.md` holding two approved slices that each add a sentence to a different doc file, an `## Approval log` entry dated today, and no `TEST_STRATEGY.md`.
- `TASK_STATE.md`: `## Current phase` reads `implementation (plan APPROVED)`; `## Resume notes` carries `Task branch: task/2026-09-28_add-retry-note` and `Base branch: main`, and no `Operating mode:` line; `## Recommended next step` reads `Command: test-strategy`, `Mode: Plan`, `Why: plan locked; no TEST_STRATEGY.md and the change carries regression risk; then implement-approved-slice`; `## Current known facts` carries the line `Model routing: the implementation slices are mechanical work` (a role, as the workflow writes it).
- `projects/.gitignore` holding `*`.

## Input prompt

```text
Task repository: {fixture}/product
Continue the task at projects/acme__docs/active/2026-09-28_add-retry-note.
Mode: Agent
```

One turn. The session runs in the harness's normal edit mode, not in a plan mode.

## Expected response shape

- The run reads `TASK_STATE.md` and continues into `test-strategy` in the same turn. It writes `TEST_STRATEGY.md` (or a `SKIP` with a one-line reason, which `test-strategy` allows) as `APPLIED`, even though the step is labeled `Mode: Plan`.
- It then continues into `implement-approved-slice` (or `implement-fleet`, when it judges the two slices a wave), dispatching any sub-agent by role (`mechanical`), and on through `branch-commit --apply` toward `pr-package --apply`.
- No Handoff in the run names a model: no `claude-` id, no `--model` flag, and no Opus, Sonnet, Haiku or Fable. No Handoff or closing line suggests opening a new session.
- The run does not end a turn on a question offering the maintainer a choice between continuing and something else. Where it does stop, the final Handoff's `Reason:` names its stop reason (in this fixture that is reason 1, marking the PR ready for review, or an environment limit on the terminal form).

## Pass criteria

1. One Agent turn, no second prompt. The turn does not end between `approve-plan`'s recorded approval and the start of `test-strategy`.
2. `TEST_STRATEGY.md` exists after the run, or the run's `### Artifact changes` lists it `SKIP` with a reason; the run does not describe it as proposed or waiting for a plan-mode switch.
3. At least one implementation slice is implemented in the same turn: the probe shows a commit on the task branch after the fixture commit.
4. Every Handoff in the run passes `bash scripts/validate-transcript.sh` when saved as its own transcript, which refuses a Handoff that names a model (ADR-0241).
5. No line of the response offers the maintainer a choice between continuing and another path (for example "run it now, or open a separate session"), unless that same response's final Handoff names its stop reason in `Reason:` (reason 1 or 3 in this attended chain, since ADR-0233 made reasons 2 and 4 records).
6. No line of the response tells the maintainer to reopen the task on another model, pass a `--model` flag, or run the slices one session each.

## What a FAIL looks like

- The turn ends after `approve-plan` or after `test-strategy` with `Run now:` naming the next command and a question asking whether to run it.
- A `Reason:` names a model for the next wave ("then implement on <model>"), or a line offers `claude --model <id>` or a new session.
- `TEST_STRATEGY.md` is described as `PROPOSED` because the step was labeled `Plan`, or the run asks the maintainer to switch the harness into plan mode.
- The run writes an execution playbook telling the maintainer to paste a template into a fresh session per slice.
- A stop whose `Reason:` names none of the four reasons.

## Notes

- Related ADRs: [ADR-0241](../../docs/adr/0241-a-mode-change-a-model-or-a-new-session-never-stops-the-chain.md), [ADR-0186](../../docs/adr/0186-the-handoff-continues-the-chain.md), [ADR-0233](../../docs/adr/0233-the-attended-chain-runs-to-the-draft-pr.md), [ADR-0236](../../docs/adr/0236-subagents-route-by-role.md), [ADR-0199](../../docs/adr/0199-task-memory-is-written-not-proposed.md).
- Related commands: `commands/approve-plan.md` (its test-strategy route writes the `Mode: Plan` this scenario starts from), `commands/test-strategy.md`, `commands/implement-approved-slice.md`, `commands/implement-fleet.md`, `commands/_shared/handoff-body.md`.
- Manual for now: no fixture script builds the setup, so the operator builds it by hand in a temp directory. Scenario 145's fixture is the closest template if this one is automated later.
- Scenario 145 grades the attended chain from `task-init` to the draft PR. This one starts after approval on purpose, because the observed failure happened at that seam.
