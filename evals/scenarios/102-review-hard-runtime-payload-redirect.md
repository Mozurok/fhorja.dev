# Eval scenario 102: review-hard routes a runtime-debug payload to incident-triage before any review step

- **Tags**: ADR-0088, F-3, D-3, review-hard, incident-triage, runtime-debug-payload, routing-integrity, connector-dogfood
- **Last reviewed**: 2026-07-10
- **Status**: active

## Goal

Validates the ADR-0088 runtime-debug-payload triage in `review-hard`, moved to the first operating rule after the 2026-07-10 connector dogfood showed the clause failing to fire when it sat mid-list: a runtime-debug payload pasted into `review-hard`'s invocation args is classified and routed to `incident-triage` before any review step runs, never absorbed into an inline diagnosis. This exercises the enforcement fix named directly in `commands/review-hard.md` Operating rules (first-position clause plus this scenario).

## Setup

An active task mid-testing a database-backed connector: a slice implementing an async database client is implemented and under test; the last `TASK_STATE.md` step recorded is "implement-approved-slice: async db client wired". No `incident-triage` run has happened yet this session. Real code changes exist (the connector slice), and the task folder has `TASK_STATE.md`, `DECISIONS.md`, `IMPLEMENTATION_PLAN.md` in place.

## Input prompt

Pure runtime-debug payload:

```text
/review-hard Erro dessa vez: a conexao com o banco caiu (asyncpg.exceptions.InterfaceError: connection is closed) ... quer que eu tente de novo?
```

Mixed payload, for the split-rule check:

```text
/review-hard Also while you're at it, the retry helper in db/client.py catches Exception too broadly and swallows the original traceback. Erro dessa vez: a conexao com o banco caiu (asyncpg.exceptions.InterfaceError: connection is closed) ... quer que eu tente de novo?
```

## Expected behavior

- Pure runtime-debug payload: the first action in the response classifies the pasted text as a runtime-debug payload (a crash signature plus a got-the-error-again symptom), not a code-risk finding. The response routes to `incident-triage` and performs no review step: no Must-fix, Should-fix, or Test-gaps content is populated from the payload, and no inline root-cause diagnosis of the `asyncpg.exceptions.InterfaceError` is attempted. The response does not ask the user whether to retry the failing database operation; that call belongs to `incident-triage`, not `review-hard`.
- Mixed payload: the response splits the two parts. The code-risk observation (the retry helper's overly broad `except Exception` swallowing the original traceback) is reviewed here and listed as a must-fix or should-fix finding. The runtime-debug part (the `asyncpg` connection error) is routed to `incident-triage`, not reviewed or diagnosed inline.
- In both variants, the routed-to command is `incident-triage`, named as a real `commands/incident-triage.md` basename, and the routing happens before any review content is produced, not after or as an aside.

## FAIL conditions

A FAIL is: the command absorbs the payload and starts diagnosing the `asyncpg.exceptions.InterfaceError` inline (root-causing the failure, proposing a fix, or offering to retry) instead of routing it, the historical failure this scenario exists to catch; the command produces review output first and only routes to `incident-triage` afterward; the command asks the user whether to retry the failing database connection itself instead of deferring that decision to `incident-triage`; the mixed-payload variant drops the code-risk finding or reviews the runtime-debug part instead of routing it; or the routed command name is not a real `commands/<name>.md` basename.
