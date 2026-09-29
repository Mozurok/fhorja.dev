# ADR-0158: The fleet worker return transport is the file on the Agent path

- **Status**: Accepted; D-2 superseded in part by [ADR-0242](./0242-a-fleet-worker-returns-through-its-own-worktree.md): a worker dispatched with worktree isolation writes its return file to `.fleet-out/` inside its own worktree, which the orchestrator copies into `fleet-inbox/<run_id>/`.
- **Date**: 2026-08-22
Supersedes, in part: ADR-0038 (Rule 1's return mechanism, not its typed-return invariant)
- **Tags**: fleet, orchestration, worker-contract, adr-0038, transport, open-decision, measured

## Context

ADR-0038 Rule 1 made a typed return mandatory and named the mechanism: the worker
invokes `StructuredOutput` once with `artifact=fleet-inbox/<run_id>/<worker_id>`.
`commands/_shared/worker-contract.md` carried that verbatim and declared prose
returns and `.partial.md` file writes FORBIDDEN. Seven fleet commands repeat it.

That tool is not reachable from the path those commands dispatch on. It exists
inside the dynamic-workflow runtime, where the SCRIPT declares the shape via
`agent(prompt, {schema})` and the runtime performs the call; the worker is never
told about it, and no `artifact=` key exists in that API. The `Agent` tool takes
`{description, isolation, model, prompt, subagent_type}` and no schema at all.

The measured consequence, counted on disk 2026-08-21 and again 2026-08-22:

| artifact under `.wos/fleet-inbox/` | count |
|---|---|
| `.json` | 46 |
| `.md` (the shape ADR-0038 forbade) | 27 |
| `.tar`, `.patch`, `.list` | 6 |
| total files | 79 |
| distinct run ids | 27 |
| run ids in the platform's generated `wf_<hex>` form | 4 |

The 27 markdown returns were written between 2026-06-11 and 2026-06-26. ADR-0038
is dated 2026-06-05. So the forbidden transport was used for three weeks after it
was forbidden, and 23 of 27 run ids were hand-invented (`wave1`, `fleet-w1`,
`flt260702161236`, `wf-wave11` imitating the prefix with a hyphen, two raw UUIDs),
which means most fleet runs never went through the workflow runtime at all.

The fleets ran. They ran by writing files, because the mandated tool was not on
the path they took.

A separate finding bears on the same decision. ADR-0092 found every fleet variant
except `implement-fleet` to be a zero-inbound orphan in the command graph, and a
2026-08-21 measurement over 386 task logs found 26 commands never invoked at all.

## The decision that is open

The command files have been corrected to state what is true today: which
transport belongs to which path, and that a command mandating `StructuredOutput`
must name the workflow path it depends on. That correction is factual and needed
no ADR. What it deliberately did NOT do is decide the contract.

**Option A. Legitimize the file transport on the `Agent` path.** Keep prose
returns forbidden, keep the typed payload mandatory, and admit two carriers: the
runtime's `StructuredOutput` on the workflow path, and a `.json` file written by
the worker into `fleet-inbox/<run_id>/<worker_id>.json` on the `Agent` path, with
the orchestrator reading it. This is what 46 of the 79 files on disk already are.

- For: it describes what happens, it keeps ADR-0038's real invariant (typed, not
  parsed prose), and it costs one contract edit.
- Against: a file the worker writes is a substrate write by a process the same
  contract says must not write substrate, and `worker-contract.md` now records
  that a background sub-agent retains `Edit` and `Write`, so the refusal is the
  only thing holding that line. Admitting one file write weakens the rule that
  keeps workers out of everything else.

**Option B. Route all fleets through the workflow runtime.** Make the workflow
path the only sanctioned dispatch, so `StructuredOutput` is genuinely available
and the mandate becomes true rather than aspirational.

- For: the mandate stops being a instruction to call an absent tool, and the
  run-id convention becomes the platform's rather than hand-invented.
- Against: 23 of 27 recorded runs did not take that path, so this is a change to
  how the fleets are invoked and not only to what they return. It also inherits
  the workflow runtime's constraint that a run cannot pause for human input,
  which ADR-0044's never-auto-merge rule leans on.

**Option C. Delete the orphan fleets and repair only what remains.** ADR-0092
found every fleet variant except `implement-fleet` orphaned, and the telemetry
shows most never invoked. Repairing a contract for commands nobody calls spends
review budget on surface rather than behavior.

- For: it removes the largest block of unexercised doctrine in the repository and
  shrinks the Advertise stage by 4,167 chars, about 1,042 tokens per session.
- Against: deletion is irreversible in a way the other two are not, `implement-fleet`
  is genuinely used, and the ADR-0092 orphan finding is about inbound description
  edges rather than about value. A command with no inbound edge is unreachable by
  routing, which is a fixable defect and not a verdict on the command.


## Decision

**D-1. The typed payload stays mandatory and gains a second sanctioned carrier.**
Free-form prose returns remain FORBIDDEN. The payload matching
`worker_output_schema` is required either way. What changes is that the carrier
is named per dispatch path rather than assumed: the runtime's `StructuredOutput`
call on the dynamic-workflow path, and a `.json` file at
`fleet-inbox/<run_id>/<worker_id>.json` on the `Agent` path, which the
orchestrator reads. This is option A.

**D-2. The exception is scoped to `fleet-inbox/<run_id>/` and nowhere else.**
Admitting a worker file write cuts against the same contract's rule that workers
do not write substrate, and that rule is now known to rest on refusal alone,
since a background sub-agent retains `Edit` and `Write` and this repository ships
no agent definition withholding them. The exception names one directory, keyed to
the run, and grants nothing outside it.

**D-3. Option B is rejected on the measured practice, not on preference.** Across
all logged fleet activity: 155 runs, of which **6 carried the platform's
generated `wf_<hex>` run id and 149 did not**. Per command, `implement-fleet` ran
116 times with 4 through the runtime and `external-research-fleet` 35 times with
2. Routing every fleet through the workflow runtime is a change to how 96 per
cent of observed runs are invoked, and it inherits that runtime's inability to
pause for human input, which ADR-0044's never-auto-merge rule leans on.

**D-4. Option C is DEFERRED, and the evidence that was offered for it does not
hold.** The case for deleting the two never-run fleets was 0 runs and 0 log
writes, which is true: `screen-spec-fleet` and `verify-against-rubric-fleet` have
neither. But both are correctly wired. `screen-spec`'s own description names
`screen-spec-fleet` and `verify-against-rubric`'s names
`verify-against-rubric-fleet`, so each has exactly the Advertise-time routing
edge its design calls for: the parent routes to the variant when a stated
threshold is met (6 or more screens, 4 or more artifacts). They have not run
because the threshold has not been met, which is a statement about this
maintainer's workload and not about the commands. Deleting a correctly wired
command whose trigger has not fired is a different decision from deleting an
unreachable one, and ADR-0092's orphan finding is about inbound description edges,
which these two have.

Measured deletion cost, simulated in a `git clone --local` rather than estimated:
three registry files edit mechanically, `Registry` returns to 0 gaps, and
critically `Doc-sync` stays at 0 broken, so the ADR references to a deleted
command do not dangle. What remains is 2 broken scenario references, 12 stale
count markers, two routing-probe fixtures, and the description baseline. The cost
is real but modest; the reason to spend it is what dissolved.

**D-5. Usage, for the record.** Log writes per fleet command: `implement-fleet`
805, `external-research-fleet` 260, `atom-audit-fleet` 9, `task-init-fleet` 8,
`feature-library-scout-fleet` 7, `screen-spec-fleet` 0,
`verify-against-rubric-fleet` 0. Two commands carry 97.8 per cent of the traffic.
An earlier report predicted `implement-fleet` would account for nearly all of it
and the audit fleets for none; `external-research-fleet` at 260 refutes that.

## Why the decision was held open until now

The choice is a scope and value judgement about what Fhorja should be, and the
first draft of this ADR recorded the three options without picking one. The
maintainer chose A plus C. C then failed on inspection for the reason in D-4: the
two commands proposed for deletion turned out to carry the routing edge their
design calls for, so the evidence offered for deleting them was 0 runs with an
innocent explanation. A is adopted, C is deferred with its reason, and the
reversal is recorded here rather than smoothed away.

A decision here supersedes ADR-0038 Rule 1's mechanism (not its invariant) and,
under option C, retires commands ADR-0092 already flagged. Both are load-bearing
enough that patching the old ADRs would be wrong; this one records the choice
when it is made.

## Consequences (all conditional on the choice)

- Under A: one edit to `worker-contract.md`, and a stated exception to the
  no-substrate-writes rule scoped to `fleet-inbox/` only.
- Under B: seven dispatch steps change, and the fleets acquire the workflow
  runtime's no-mid-run-input constraint.
- Under C: five commands leave four registries each, the Advertise stage drops
  about 1,042 tokens, and `implement-fleet` still needs A or B.
- Under none of them: the contract stays factually correct and behaviourally
  unenforced, which is the state this ADR was written from.
