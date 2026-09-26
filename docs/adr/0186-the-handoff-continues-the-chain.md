# ADR-0186: The handoff continues the chain; four named reasons stop it

- **Status**: Accepted The implicit assumption that a chained turn emits one Handoff per command is superseded by [ADR-0192](./0192-one-turn-reports-once.md): such a turn reports once. The continuation rule and the four stop reasons stand. Reason 1's wording is superseded by [ADR-0200](./0200-bounded-audience-replaces-reversibility.md): the test is whether an act's audience is bounded, not whether it can be undone. Reason 2 no longer covers plan approval, per [ADR-0208](./0208-plan-approval-self-runs.md). On attended runs reasons 2 and 4 are superseded in part by [ADR-0233](./0233-the-attended-chain-runs-to-the-draft-pr.md): a product decision becomes a provisional record and a check the agent cannot run on itself is listed in the draft PR, so the chain stops only for reason 1.
- **Date**: 2026-09-01
Supersedes, in part: ADR-0044 (the D9 skip-list entry "default-no-approval auto-run", narrowed to the unattended track it was measured on; the other four entries stand)
- **Tags**: express, handoff, global-output-contract, chaining, human-gate, adr-0044, adr-0126, adr-0184, friction

## Context

ADR-0184 made Express the default tier. A dogfood run the same day showed the Express chain
asks nothing across four commands. Both are true and neither one made the chain run.

The reason is in `## Global output contract`. It said every command ends with a "recommended next
command", and `wos/entry-points.md` told the reader to "follow the recommended next command from
the handoff". The handoff was a suggestion and the human was the transport. A tier that picks a
shorter pipeline still hands each step back to a person to retype.

The maintainer named this on 2026-08-31: the human should enter at the end to check the work, and
then ask for the push and the draft PR. Everywhere else the session should carry itself.

That is a change to what a handoff means, not to how it is written.

## Decision

`Run now:` names what the session does next. An attended session continues into it in the same
turn rather than waiting to be asked.

Four reasons stop it, and the block names which one in `Reason:`:

1. an outward or irreversible act
2. a decision that changes what the product is
3. a cost or loop ceiling
4. a check of the work the agent cannot honestly run on itself

The grammar does not move. `Run now:` still carries a `commands/` basename or `none`, so
`check_handoff_basenames`, `validate-transcript.sh` and its fixtures are untouched. What changes is
who acts on it.

Two consequential edits fall out of that.

**The terminal form becomes the stop.** `Run now: none` was written as an escape hatch for a
command with no honest next step (ADR-0126). Once the chain continues by default, it is the
mechanism by which a chain ends. Its rule is unchanged; its historical justification came out,
because it now describes ordinary behavior rather than a rare case.

**Mode B fires at two points, not four.** It was triggered by auto-compaction, by
`resume-from-state`, by the user saying they would continue elsewhere, and by a handoff to a
different person. The last two are human-coordination events, and under this decision the session
does not hand off between steps. The two that survive are the two where context is actually gone.

**D9 is narrowed, not ignored.** ADR-0044's skip list put "default-no-approval auto-run" out of
scope by construction. That entry was measured on the unattended track, where nobody is watching
and the run's own gates are the only ones. It is narrowed here to that track. An attended chain
advances without per-step approval, because the human is present, gave the prompt, can interrupt at
any point, and still holds the four stops. The other four skip-list entries stand untouched:
permissive headless autonomy, model-picked autonomy tiers, parallel subagents on the implement leg,
and fully autonomous deploy.

Naming the supersession rather than reading D9 narrowly is deliberate. The entry is broad enough
that a reader could apply it to this change, and a boundary that moved should say so.

## Consequences

### Positive

- The chain runs. Express picking a shorter pipeline now produces a shorter run rather than fewer
  prompts for a person to retype.
- A stop carries its reason, so a reader can check whether the workflow stopped for cause or out of
  habit. Under the old contract every step was a stop and none of them had to justify itself.
- The four reasons are a closed list, which makes a new stop an argued addition rather than an
  accretion.

### Negative

- A chain that should have stopped and did not now costs more than a chain that stopped and should
  not have. The exposure is real. It is bounded by the fourth reason, which keeps every verification
  of the work a separate act, and by the ceiling in the third.
- "A decision that changes what the product is" is a judgment, unlike the other three. It is the one
  a run can get wrong quietly.

### Neutral

- No command file changed. The contract reaches all 98 through
  `commands/_shared/handoff-body.md`, which every command carries.
- The `Run now:` grammar, the Mode A and Mode B formats, Mode C fanout, and `Work complexity` are
  unchanged.
- Net change inside the four bootstrap sections is +50 characters, measured, so the declared floor
  in `commands/_shared/mandatory-context-bootstrap.md` does not move.

## Alternatives considered

### Alternative 1: add an Express-only continuation rule and leave the general contract alone

- Rejected. It makes continuation a property of a tier, which is the framing the maintainer
  rejected: Express is how the workflow behaves, not a mode it can be put into. It would also leave
  two contracts to keep in step.

### Alternative 2: keep the recommend framing and add a wrapper that runs the recommendations

- Rejected. The contract would still say the human is the transport while something else quietly
  was one, and the wrapper would need its own copy of the stop rules.

### Alternative 3: leave D9 alone and argue this change sits outside it

- Rejected. It is the accretion the maintainer asked to stop: a rule that no longer fits, kept
  intact, with a reading layered on top to route around it.

## References

- [ADR-0002](./0002-paste-this-next-contract.md): the copy-paste contract the adaptive handoff
  replaced in v2.0.0-rc1. This removes the last thing that made a paste body make sense.
- [ADR-0044](./0044-autonomous-delivery-track.md): D9, whose first entry this narrows.
- [ADR-0126](./0126-terminal-form-for-the-handoff-contract.md): `Run now: none`, promoted from exception to the stop.
- [ADR-0184](./0184-express-is-the-default-tier.md): Express as the default tier, which this makes
  reach the run.
- `docs/DELETION_LEDGER.md`: the four stop reasons as a standing decision.
