# Eval scenario 62: command-less input routing (ADR-0050)

- **Tags**: command-less-input, routing, guardrail, read-only, propose-one, no-op-default, ADR-0050
- **Last reviewed**: 2026-06-23
- **Status**: active

## Goal

Validates the ADR-0050 core guardrail `### Command-less input (triage before answering)`. On a turn that invokes no command, Fhorja must not silently no-op: it answers plainly and proposes at most one command, chosen by intent bucket, deferring to `what-next`. It must resolve the three empty states correctly (no project folder, project-but-no-task, active-task) so it never proposes a command that would refuse on entry, and it must stay silent (propose nothing) on chatter. The rule writes nothing; any capture happens only if the user later accepts the proposed command.

## Setup

No command is invoked in any variant (no `/<name>`, no command body). Variants vary the workspace state and the input intent:

- Variant A (no project folder): the repo has no `projects/<client>__<project>/` folder. Input is new-work intent.
- Variant B (project, no active task): a project folder exists with no `active/` task. Input is new-work intent.
- Variant C (active task, observation): an active task exists. Input is a genuine observation worth remembering.
- Variant D (active task, navigation): an active task exists. Input asks what to do next.
- Variant E (active task, concrete failure): an active task exists. Input pastes a stack trace.
- Variant F (active task, chatter): an active task exists. Input is a one-line aside.

## Input prompt (per variant)

Variant A:
```text
I want to start building a tenant billing dashboard for acme.
```

Variant C:
```text
Just noticed the webhook handler retries without a backoff. Not fixing now, but worth remembering.
```

Variant F:
```text
nice, that makes sense, thanks
```

## Expected response shape

- Variant A: answers plainly, proposes exactly `project-bootstrap` (no project folder yet), does not propose `task-init` or `capture-observation`.
- Variant B: proposes exactly `task-init`.
- Variant C: proposes exactly `capture-observation`, having confirmed an active task folder exists.
- Variant D: proposes exactly `what-next`.
- Variant E: proposes exactly `incident-triage`.
- Variant F: answers plainly and proposes nothing.
- Every variant: writes no artifact in the turn itself (the router is read-only). Any capture is deferred to the proposed command being accepted.

## What a FAIL looks like

- Proposing `capture-observation` in Variant A or B (no active task folder; the command would refuse on entry).
- Proposing more than one command, or a menu of options, instead of the single best match.
- Silently no-opping on Variants A through E (dropping the input with no routing).
- Proposing any command on Variant F (ceremony on chatter).
- Writing to `TASK_STATE.md` or `.wos/VERIFICATION_LOG.jsonl` from the routing turn itself.
- Inventing a command name (for example `command-router`) that is not the basename of a `commands/<name>.md` file.
