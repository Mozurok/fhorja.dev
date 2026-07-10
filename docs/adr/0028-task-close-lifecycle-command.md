# ADR-0028: task-close as the terminal task lifecycle command

Status: Accepted (2026-06-01)

## Context

The task lifecycle was asymmetric. `task-init` opens a task (creates `active/YYYY-MM-DD_<slug>/` and base memory), but no command closed one. `slice-closure` closes a single **slice** and (for single-slice tasks) may route toward delivery, but it explicitly scopes itself to the slice: "Treat this as a closure decision for the current slice only, unless the context explicitly says the whole task is ending." The WOS `## When a task moves to `done`` section described the terminal state (implementation complete, review complete, team approval, merge, TASK_STATE final) and the `active/` -> `archive/` convention, but assigned the transition to no command. It was a documented state with no operator.

This gap had a concrete failure mode. In the Fhorja development session, command handoffs repeatedly recommended running `/task-close` (5 occurrences) as the terminal step after re-smoke. `/task-close` did not exist. The model reached for the natural, symmetric counterpart to `task-init` to fill the unnamed slot, and the "official next-command names only" guardrail (WOS, present in every command's bootstrap) did not catch it at runtime. The hallucination was not random: it pointed exactly at a real missing command.

## Decision

Add `task-close` as the terminal task lifecycle command, the symmetric counterpart to `task-init`.

`task-close`:
- Verifies the five WOS done-conditions, classifying each as met (with evidence), not-met, or waived (user-confirmed for solo / Phase-1 contexts where team approval and merge may not apply).
- Blocks (does not archive) when any condition is not-met and not explicitly waived, routing to the smallest unblocking action.
- Sets `TASK_STATE.md` to its final closed state.
- Moves the task folder `active/YYYY-MM-DD_<slug>/` -> `archive/YYYY-MM-DD_<slug>/` (preferring `git mv` when tracked; `archive/` canonical, `done/` legacy alias).
- Is idempotent: returns `NO_OP_TRACE` when already archived with final state.
- Never deletes artifacts; closure is a move that preserves the full task record.

Category: `execution-and-closure`. Primary mode: Agent (it performs the move and the final persist). Multi-repo aware: false (it verifies per-repo merge via explicit confirmation rather than consuming the `## Repositories` schema, so it does not expand the v2-deferred multi-repo consumer set).

## Consequences

### Positive
- The lifecycle is symmetric: `task-init` opens, `task-close` closes. The unnamed slot that invited the `/task-close` hallucination now resolves to a real command.
- The WOS `## When a task moves to `done`` conditions become an executable gate instead of prose.
- The `active/` -> `archive/` transition has a single official operator with idempotency and a no-delete guarantee.

### Negative
- One more command to maintain (53 total). Mitigated: it reuses the standard shared blocks and the established closure-command shape.
- `slice-closure` and `task-close` must stay clearly distinct (slice vs whole task). Mitigated: both command files and `wos/command-roles.md` state the distinction explicitly, and `slice-closure`'s "next" routing now points to `task-close` for whole-task closure.

### Neutral
- Solo / Phase-1 maintainers still close tasks; the team-approval and merge conditions are waivable with an explicit, recorded waiver rather than silently skipped.

## Alternatives

### Alternative 1: documentation-only fix (no new command)
Make `slice-closure` point explicitly at the manual `active/` -> `archive/` step when scope is single-slice / whole-task. Rejected: the conceptual gap (a documented terminal state with no operator) remains, so the hallucination can recur; and the archive transition stays a manual, unguarded `mv` with no done-conditions gate or idempotency.

### Alternative 2: fold closure into slice-closure
Let `slice-closure` perform the archive move when it detects a single-slice task is fully done. Rejected: it overloads a slice-scoped command with task-scoped filesystem effects, blurring the slice-vs-task distinction the command was built to protect.

## References
- WOS `## When a task moves to `done`` / `## When a task stays in `active``: the done-conditions this command gates on
- WOS `## Repository structure`: the `active/` vs `archive/` (legacy `done/`) convention
- `commands/task-init.md`: the symmetric opening command whose shape this mirrors
- `commands/slice-closure.md`: the slice-scoped closure this command is distinct from
- ADR-0017 (reflexion-style learnings): the optional `### Learnings` section task-close may emit
- Fhorja transcript analysis: 5 `/task-close` hallucinations against a real missing command
