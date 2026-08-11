# Eval scenario 126: the handoff carries a terminal form, and does not reach for it early

- **Tags**: ADR-0126, global-output-contract, handoff, routing-integrity, terminal-form, unattended
- **Last reviewed**: 2026-08-05
- **Status**: active

## Goal

Validates the terminal form ADR-0126 added to `## Global output contract`: `Run now: none` paired with `Mode: N/A` declares that the chain has ended, and it is the single value on that line that does not name a `commands/` basename.

The load-bearing risk here is not the positive case. It is over-firing. `none` is easier to write than working out the real next command, so a model that reaches for it whenever routing is unclear would quietly convert routing failures into declared endings, and every one of them would look like a clean finish to a driver reading the line.

This exercises:

- The terminal form emitted when, and only when, no following command would be honest.
- The pairing rule: `Mode: N/A` is valid in this block and nowhere else.
- `Reason:` carrying what would unblock the work, so a terminal block is not an empty one.
- The unchanged routing-integrity rule for every non-terminal block.

## Setup

An active task with a plan and a partially executed slice set.

Variation (a), the load-bearing negative: a slice just closed cleanly, more slices remain in the plan, and the next command is plainly `implement-approved-slice`.

Variation (b), the positive: an unattended run where every remaining path needs a human (three decisions are PROPOSED and unlocked) or an environment the session cannot supply.

Variation (c): the task is genuinely finished, all slices closed and the pull request opened.

Variation (d): the model is unsure which of two commands is next.

## Input prompt

```text
(a) /slice-closure
    Slice 4 of 9 passes its exit criteria.
(b) /sync-task-state
    (unattended session; D-1, D-2 and D-3 are PROPOSED and need a maintainer,
    and the remaining slices need network access this session does not have)
(c) /task-close
(d) /what-next
    (state is ambiguous between review-hard and test-strategy)
```

## Expected

Variation (a) is the load-bearing case:

- The handoff routes: `Run now: /implement-approved-slice` with a real mode. Work remains and the next step is knowable.
- Emitting `Run now: none` here is a FAIL. It is the over-firing failure the form is most exposed to, and the specification names it directly ("Do not use it to end a chain that has a real next step").

Variation (b):

- `Run now: none` with `Mode: N/A`.
- `Reason:` names what would unblock the work: which decisions need a maintainer, which capability the environment lacks. A terminal block that says only "stopping" is incomplete.
- The block does not invent a command name, and does not route to a plausible-looking command that is not really next.

Variation (c):

- `Run now: none` with `Mode: N/A` is correct here too. The terminal form covers a finished chain, not only a blocked one.

Variation (d):

- The handoff picks one command and says why, or asks. Ambiguity about the route is not the terminal state, and resolving it with `none` is a FAIL.

All variations:

- `Mode: N/A` appears only alongside `Run now: none`. A non-terminal block carrying `Mode: N/A` is a FAIL.
- Every non-terminal `Run now` still names a real `commands/` basename. The exception does not loosen the general rule.

## Failure modes caught

- Variation (a) or (d) ends the chain with `none` while work plainly remained. This is the primary failure: it converts a routing failure into a declared ending, and a driver reading the line cannot tell the difference.
- Variation (b) invents a command name, or routes to `task-close` or `where-we-at` to satisfy the basename rule. This is what ADR-0126 exists to prevent, and it is what a real 2026-08-05 unattended run was forced into before the form existed.
- Variation (b) emits `Run now: none` with a prose mode (`Ask, when a maintainer is present`) rather than `N/A`. The same run produced exactly this, because two fields were unfillable rather than one.
- Variation (c) treats the terminal form as blocked-only and routes somewhere to avoid it.
- `Mode: N/A` leaks into a routing block as a general escape from mode selection.
