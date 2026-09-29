# ADR-0243: implement-fleet is the default for a wave of two or more slices

- **Status**: Accepted. The mechanism rests on provisional decisions of the 2026-09-29 fleet-default-and-install-gaps task (P-1 to P-3, P-6, P-7), listed under `## Notes`, which await the maintainer's confirmation.
- **Date**: 2026-09-29
- **Supersedes**: in part, [ADR-0041](./0041-parallel-slice-execution-file-scope-disjointness.md): its pilot status (the Status line) and the promotion criteria in its Notes, which the E4 rerun met. Its five conditions stand unchanged.
- **Extends**: the waves-aware rule of ADR-0042 by one condition; that rule is not replaced.
- **Tags**: fleet, implement-fleet, routing, default-path, minimal-profile, adr-0041, adr-0042, adr-0242, measured

## Context

ADR-0041 shipped `implement-fleet` as a pilot and named what would promote it: "a first lived run
with the realized wave width recorded and a passing integration gate on a wave of size two or
greater." ADR-0042 wired the routing graph to reach it: `approve-plan`, `implementation-plan`,
`what-next` and `implement-approved-slice` route a remaining wave of size 2 or more to it. The
parallel-work research of 2026-09-28 then locked D-6: "if E4 passes, it SHALL become the default
path for such waves."

E4 ran `implement-fleet` end to end in a sandbox repository on 2026-09-29. Its first run failed on
dispatch, which ADR-0242 repaired. The rerun, dispatching per ADR-0242, passed every line on the
first dispatch:

- Wave 1 (three slices) and wave 2 (one slice): 3 of 3 and 1 of 1 workers satisfied, no retry,
  no `needs_revision`, no scope violation, no timeout.
- Every worker moved its harness worktree to `base_ref` and showed HEAD equal to it; one worktree
  was born at the default branch head and the reset moved it, so the check did real work.
- Merge and gate: three cherry-picks and the test suite 24 of 24 on the first try; one cherry-pick
  and 35 of 35 on the first try. The log validator and the substrate batch check were clean.
- Wall-clock: the wave 1 barrier came about 62 s after dispatch, against 173.6 s for its three
  workers in sequence (47.9 + 69.6 + 56.1), 64 percent less. The whole wave, with merge, gate and
  records, took about 2 m 20 s; wave 2 about 1 m 30 s.
- Cost: 8.91 USD for the run (7.44 USD on the orchestrator's model, 1.47 USD on the workers'),
  against 11.41 USD for the first run with its failed dispatch.

That is the lived run ADR-0041's Notes asked for, with the realized wave width recorded (3) and a
passing integration gate on a wave of size two or greater.

Three things still stood between D-6 and a default. The routing rule named no harness condition,
so a session without per-agent worktree isolation would route to a command that then tells it to
run the slices in turn anyway. `implement-fleet` was tagged `[full]`, so an explicit
`--profile=minimal` or `core` install that reached the route had no such command. And the command
still called itself a pilot.

## Decision

**D-1. A wave of two or more slices goes to `implement-fleet` by default, on a harness that isolates
each sub-agent's worktree.** Every surface that routes execution keeps ADR-0042's rule and adds one
condition: route a remaining wave of 2 or more slices that declare `Scope` and `Depends-on` to
`implement-fleet` when the session's harness gives each sub-agent its own worktree (`isolation` on
the `Agent` tool, `agent(prompt, {isolation: 'worktree'})` in a workflow script). Everything else
goes to `implement-approved-slice`: a pure chain, a single slice, a harness without that isolation.
A wave that fails the disjointness check never reaches the route as a wave of two, because
`implementation-plan` splits it and `implement-fleet` Step 3 checks it again.

**D-2. `implement-fleet` ships in the minimal and core profiles.** A default the default install
does not carry is not a default. This is the ADR-0229 shape: `verify-against-rubric` joined minimal
and core because `approve-plan` dispatches it on every plan. The minimal profile goes from 23 to 24
commands and core from 51 to 52.

**D-3. The pilot label is retired.** `implement-fleet`'s quality bar, `wos/command-roles.md` and
ADR-0041's Status line stop calling it a pilot. `implement-approved-slice` stays the canonical
single-slice unit, the worker contract and the fallback.

**D-4. The fleet's own gaps from the rerun are closed in the command.** The orchestrator runs
`git worktree list` right after dispatch to find each worker's worktree while the wave runs, and
prefers the path the dispatch result or the worker's return names. Its `merge_include` lines name
`IMPLEMENTATION_PLAN.md` and `## Slices`, and its `fleet-merge` lines `## Execution waves`, because
`scripts/verify-log-validator.py` requires a `file` and a `## ` section on every line and the
rerun's first write failed it for lack of them.

## Consequences

### Positive

- A plan with independent slices runs them in parallel without anyone asking, which is what D-6
  asked for, on the harness where the rerun showed it works.
- The route and the command agree about the harness: a session that cannot isolate worktrees is
  sent straight to `implement-approved-slice` instead of through a command that would send it there.
- An explicit minimal or core install carries the command its default route names.

### Negative

- The gain was shown on slices of about a minute each. Each wave pays a fixed cost of about 45 s
  (worktree creation and dispatch latency), so a wave of short slices can come out close to even
  with the sequential run, and a wave of long slices gains the most. One measured run is the
  evidence; a second run on a different repository would firm it up.
- A parallel wave costs more model spend than the same slices in turn on one session, since each
  worker builds its own context. The rerun cost 8.91 USD; the sequential baseline on the same
  slices was not measured.
- An explicit minimal install gains one command and one skill description to advertise.

### Neutral

- ADR-0041's five conditions and ADR-0042's progress and closure rules are unchanged.
- A harness without per-agent isolation behaves exactly as before this ADR.

## Alternatives considered

### Alternative 1: route every multi-slice plan to implement-fleet and let it fall back

- `implement-fleet` already degrades to `implement-approved-slice` for a chain and for a harness
  without isolation, so the routing surfaces could have dropped their condition.
- Rejected: a chain or a harness without isolation would pay an extra command hop and the fleet's
  bootstrap for nothing, and the routing text would stop saying what actually runs.

### Alternative 2: keep implement-fleet in the full profile

- Fewer installed commands for a minimal user.
- Rejected: the default route would name a command an explicit minimal or core install does not
  have, the gap ADR-0229 closed for the plan reviewer.

## Notes

- Provisional decisions this rests on, from the fleet-default-and-install-gaps task: P-1 (the
  harness condition on the route), P-2 (the minimal and core retag), P-3 (this ADR and its scope),
  P-6 (how the orchestrator learns each worktree path), P-7 (the file and section of the fleet log
  lines). The maintainer confirms or replaces them on the draft pull request.
- The 45 s fixed cost per wave is the maintainer's reading of the rerun, from the task brief.

## References

- [ADR-0041](./0041-parallel-slice-execution-file-scope-disjointness.md): the disjointness gate and
  the pilot this retires.
- [ADR-0042](./0042-waves-aware-routing-and-progress-visibility.md): the waves-aware rule this
  extends.
- [ADR-0229](./0229-the-minimal-profile-reaches-its-reviewer.md): the retag precedent.
- [ADR-0242](./0242-a-fleet-worker-returns-through-its-own-worktree.md): the dispatch the rerun used.
- `commands/implement-fleet.md`, `commands/approve-plan.md`, `commands/what-next.md`,
  `commands/implementation-plan.md`, `commands/implement-approved-slice.md`.
