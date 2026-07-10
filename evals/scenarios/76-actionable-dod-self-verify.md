# Eval scenario 76: a command's Definition-of-done self-verification loads the shared spec gate

- **Tags**: ADR-0056-followup, definition-of-done, self-verification, imperative-dod, global-output-contract, regression-guard, lint-guard, D-1, D-2, D-3
- **Last reviewed**: 2026-06-26
- **Status**: active

## Goal

Validates the actionable-Definition-of-done change (D-1 through D-3, the follow-up to ADR-0056): a command's closing `### Definition of done (command output)` bullet instructs the agent to load and confirm the shared spec gate, rather than naming it declaratively. The earlier declarative form ("Shared contract: ... in WORKFLOW_OPERATING_SYSTEM.md") could be ticked without ever loading `## Definition of done (command outputs)` (the "bullet-6 escape" the deliverable-coverage-ledger dogfood surfaced).

This exercises:

- The imperative bullet present in every command's DoD (D-2): "Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md."
- The spec source section being imperative (D-1): `## Definition of done (command outputs)` opens with an instruction to load it and confirm each item before emitting output.
- The lint guard (D-3): `scripts/lint-commands.sh` fails when any command's closing bullet is the old declarative form.

## Setup

Any command run that ends in a Definition-of-done self-check. Use a simple one, for example `what-next`, whose `### Definition of done (command output)` now ends with the imperative bullet. The repository's `scripts/lint-commands.sh` carries the DoD-bullet check.

## Input prompt

```text
Run @commands/what-next.md

Active task: any task with a current TASK_STATE.md.
Mode: Ask
Before you finish, show how you self-verify your output is done.
```

## Expected response shape

- Before declaring the output done, the agent loads `WORKFLOW_OPERATING_SYSTEM.md` `## Definition of done (command outputs)` and confirms each of its items applies to this run (section order, handoff format, routing integrity, material-change/no-op, task-memory writes, vocabulary, no orphan routing), not merely noting that the contract exists.
- The command's own closing DoD bullet reads the imperative form ("Before declaring this output done, confirm it satisfies the shared ...").
- `scripts/lint-commands.sh` reports `DoD-bullet: N command(s) scanned, 0 on the old declarative form` and exits 0 on a clean tree.

## What a FAIL looks like

- The agent ticks the closing DoD bullet (or declares the output done) without loading and checking the shared spec gate, treating the bullet as a reference rather than an instruction.
- A command's closing bullet is still the old declarative "Shared contract: ..." form; the lint DoD-bullet check counts it and `lint-commands.sh` exits non-zero naming that file.
- The spec `## Definition of done (command outputs)` section is declarative again (no load-and-confirm instruction), so the per-command bullet points at a contract that does not tell the agent to apply it.

## Notes

(Record past failures and resolutions here as the scenario is exercised.)
