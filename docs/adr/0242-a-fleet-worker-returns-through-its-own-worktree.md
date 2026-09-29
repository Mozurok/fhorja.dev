# ADR-0242: A fleet worker is dispatched with harness isolation and returns through its own worktree

- **Status**: Accepted. The mechanism rests on provisional decisions of the 2026-09-29 fleet-dispatch-fixes task (P-1 to P-5), listed under `## Notes`, which await the maintainer's confirmation.
- **Date**: 2026-09-29
- **Supersedes**: in part, [ADR-0158](./0158-the-fleet-return-transport-is-the-file.md) D-2: a worker dispatched with worktree isolation writes its return file inside its own worktree, not into `fleet-inbox/<run_id>/`. ADR-0158's D-1 carrier (a typed `.json` file on the `Agent` path) and its D-3 to D-5 stand.
- **Tags**: fleet, implement-fleet, worker-contract, worktree, isolation, transport, adr-0041, adr-0158, measured

## Context

On 2026-09-29 a background session ran `implement-fleet` end to end in a sandbox repository, on a
harness whose worktree guard confines each agent's writes to its own worktree. Four slices, two
waves, seven workers dispatched, four succeeded.

Wave 1 failed on its first dispatch. `implement-fleet` Step 6 told the orchestrator to "create an
isolated git worktree off that same committed `base_ref` and dispatch one worker bound to that
worktree", and in a later sentence called isolation "an option on the per-agent call". The driver
read the first sentence as the instruction: it ran `git worktree add` itself, to control the base
SHA, and dispatched without the harness option. Every worker inherited the driver's own sandbox,
and every write outside it was refused.

The second dispatch passed with the harness option. Two more things had to be improvised for it to
pass. The harness worktree started from the default branch head, not from `base_ref`, so each
worker ran `git reset --hard` to `base_ref` before editing. And Step 7 told the worker to write its
slice note and its return file into the orchestrator's task folder, outside its own worktree, which
the same guard refused; the workers left both under `.fleet-out/` in their worktrees and the driver
copied them in.

ADR-0158 D-2 is where the second problem is written down. It admitted the return file as the one
write a worker may make and scoped it to `fleet-inbox/<run_id>/` "and nowhere else". Under
worktree isolation that directory is outside the only tree the worker can write.

## Decision

**D-1. Dispatch uses the harness's per-agent isolation, and the orchestrator makes no slice worktree
by hand.** Each worker is dispatched with the isolation option on the per-agent call (`isolation` on
the `Agent` tool, `agent(prompt, {isolation: 'worktree'})` in a workflow script). A worktree the
orchestrator creates carries the orchestrator's write sandbox to the worker, which is the failure
above. A harness with no per-agent isolation option does not dispatch the wave: its slices run one
after another through `implement-approved-slice`, the degradation `## Parallel workflow` already
names for tools without the primitive.

**D-2. The worker's first act is to move its worktree to `base_ref` and prove it.** It runs
`git reset --hard <base_ref>` and checks that `git rev-parse HEAD` prints `base_ref` before any other
read or edit. On a mismatch it edits nothing and returns `failed` with `error_class: missing-input`.
It commits only its `scope_files`, by explicit path, on its worktree branch.

**D-3. The return goes into a fixed folder inside the worker's own worktree.** A worktree-isolated
worker writes its typed payload to `.fleet-out/<worker_id>.json` and, for `implement-fleet`, its
slice note to `.fleet-out/<NN>_<slug>.md`. The folder sits at the worktree root, outside
`scope_files`, and is never staged or committed. This replaces ADR-0158 D-2's directory for these
workers and keeps its reason: one folder, keyed to one worker, and nothing else outside
`scope_files`.

**D-4. The orchestrator stays the single writer of the task folder.** After the barrier it copies
each `.fleet-out/<worker_id>.json` into `.wos/fleet-inbox/<run_id>/` and each slice note into
`SLICES/`, before any worktree is removed. It merges each worker's commit, or that worker's
`scope_files` diff against `base_ref`, and never the return folder.

## Consequences

### Positive

- A fleet run on a harness with a worktree guard dispatches on the first try, with no step left to
  improvise.
- The task folder has one writer again. Before this, every worker wrote into it.
- `scripts/monitor-fleet-progress.sh` can watch the return folders directly, since that is where the
  returns now live during a wave, and the installer ships it.

### Negative

- The worker contract now names two carrier locations, the run inbox and the in-worktree folder,
  depending on how the worker was dispatched.
- A product repository that does not ignore `.fleet-out/` shows it as untracked in each worker
  worktree. The explicit-path commit keeps it out of history, and the merge takes only the worker's
  commit or its `scope_files` diff, but it is one more rule a worker can break.

### Neutral

- ADR-0041's five conditions are unchanged. Condition 4, each worker in its own worktree, is now met
  by the harness rather than by the orchestrator.
- `structural-evals.py` `fleet-dispatch-isolation` fails when the old Step 6 or Step 7 wording comes
  back or the new anchors go, and `command-scripts-shipped` fails when a script a command runs is
  neither shipped nor on the named not-shipped list.

## Notes

- Evidence: the E4 simulation's Results and Defects found, 2026-09-29 (a local, gitignored task
  record), quoted in the fleet-dispatch-fixes task README.
- The four decisions above rest on provisional P-1 (the folder name), P-2 (harness isolation, no
  hand-made worktree), P-3 (reset and verify, explicit-path commit, merge rule), P-4 (this ADR) and
  P-5 (the monitor). They await the maintainer's confirmation on the draft pull request.
