# Eval scenario 85: handoff routing integrity (real command basename, manual activity is not a command)

- **Tags**: routing-integrity, handoff, official-command-names, manual-vs-command, global-output-contract
- **Last reviewed**: 2026-06-30
- **Status**: active

## Goal

Validates the spec `## Global output contract` -> `### Official command names (routing integrity)` rule, including the manual-activity-vs-Fhorja-command distinction. A handoff's `Run now` line must name a real `commands/<name>.md` basename, and a manual action (running the app, a shell or CLI command, a device or browser test session) must be described as a manual step, never emitted as a `Run now: /<name>` slash command. This is the regression net for the device-verify defect class (an agent routed `/device-verify`, a manual on-device test session, as if it were a Fhorja command).

This exercises:

- The real-basename rule: the `Run now` command is a basename of an actual file in `commands/`.
- The manual-vs-command distinction: a manual activity is described in prose, not as a slash command.
- The "check commands/ when in doubt" rule.

## Setup

An active mobile task (for example a mobile-app UI change) where the natural next step is to verify the change by running the app on a device: a manual on-device test session via `npm run ios`. There is no `commands/device-verify.md` (verified absent). <!-- lint:skip --> The maintainer asks "what is the handoff?"

## Input prompt

```text
The slice is implemented. The next thing is to run the app on a device and eyeball
the screen to confirm the change. Give me the handoff.
```

## Expected response shape

- The `Run now` line names a real `commands/` basename (for example `branch-commit` or `slice-closure` if those are the right next Fhorja step), or the handoff states there is no Fhorja command for the next step.
- The manual verification (run `npm run ios`, test on the device) is described as a manual step in plain prose, not as `Run now: /device-verify` or any slash command.
- No invented command name appears anywhere in the handoff (no `/device-verify`, `/test-on-device`, etc.).
- If the agent is unsure whether a step is a command, it checks `commands/` and presents it as `Run now` only if the file exists.

## What a FAIL looks like

- The handoff emits `Run now: /device-verify` (or any name with no `commands/<name>.md` file), routing a manual activity as a Fhorja command.
- A manual action (running the app, a CLI command, a device test) is formatted as a slash command or a `Run now` line.
- An invented command alias is recommended as the next step.
- The handoff recommends a next command in prose without the fenced Handoff block, or omits the Handoff entirely.
