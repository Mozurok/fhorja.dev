# Autonomous delivery track

The autonomous delivery track is an additive cluster (ADR-0044), parallel to the engineering and design tracks. Its `autonomous-run` command is a full-profile reference dispatcher for a maintainer invoking Fhorja directly. It accepts one well-specified, approved, waved task for one continuous session and returns PROPOSED work for review. Two human gates and a runtime governor keep it from reaching anything irreversible on its own. The human-in-the-loop is moved and bounded, not removed.

Load this topic when designing, building, or running the autonomy cluster. The normative decisions are ADR-0044 and the source task `DECISIONS.md` (D1-D12).

## What it is, in one paragraph

A thin code-orchestrated reference dispatcher over the primitives that already exist. An approved waved `IMPLEMENTATION_PLAN` feeds a controller. The controller drives the execution substrate wave by wave, runs `implement-approved-slice` as the single writer per slice (ADR-0040), applies a runtime governor and a boundary/test classifier between slices, and emits PROPOSED slice diffs for review. It never commits, creates an attestation ref, or merges. It owns no durable queue, cross-session resume, security sandbox, credential broker, remote control, publication, or deploy path. An external execution layer may consume the ordinary command interface and implement its separately labeled obligations below, but it refuses to dispatch `autonomous-run` inside its own loop (ADR-0169, ADR-0197).

## The two gates plus mid-run escalation (D6)

- Plan-approval gate (entry): a human approves the waved plan before any execution. The track reuses `approve-plan`; it does not re-implement approval.
- Draft-diff merge gate (exit): a human approves the merged PROPOSED diff before any irreversible step (commit to an integration branch, merge, deploy). The PROPOSED slice diffs route to `review-hard`, and a human performs the merge (ADR-0221). This track keeps the reversibility limit: ADR-0200's bounded-audience test covers attended sessions, and ADR-0221 records why it does not reach an unattended run. ADR-0233 lets an attended chain push its own task branch and open the draft pull request; that reaches only attended sessions, and on this track the push and the draft pull request stay human-gated as before.
  - For an external execution layer, commit-evidence is a separate question from this gate, and ADR-0133 answers it: an unattended runner satisfies the commit-evidence floor by routing to `ref-attested`, where the RUNNER points a quarantine ref at a git object holding the run's work, under `refs/fhorja/attested/<run-id>/<invocation-id>`. That ref is not an integration branch, and reaching it is not an irreversible step: `git update-ref -d <ref>` removes it, and nothing is merged, pushed or deployed. This gate is otherwise unchanged, and merge, push and draft-PR stay human-gated.

## The autonomous commit route (external execution layer, driver-owned branch)

This section is an interface contract for an external execution layer under ADR-0169. It grants no commit authority to `autonomous-run`, which remains PROPOSED-only. For an external runner, `ref-attested` preserves an unattended run's work but does not give that run the ordinary developer act of committing. The route below makes `commit-ref` reachable only for an external runner that enforces every condition.

**The rule.** An external unattended runner MAY commit, and ONLY onto a branch it owns:

1. The branch SHALL NOT be a default or integration branch. WHEN the target is on one, the runner SHALL create an owned branch from it and switch before the first invocation, so the run's work never lands on the default branch. WHERE the working tree is dirty the runner SHALL instead REFUSE to start, because switching would carry or strand changes the operator wrote and did not commit, and a run is never worth touching those.
2. The runner SHALL create the branch when the target is not already on an owned one, naming it by convention (`fhorja/<run-id>`), and SHALL record the name it created. Where the target is already on a non-default branch the runner SHALL leave it alone: that branch is the operator's choice and is already outside condition 1's prohibition.

   Creating the branch protects the default branch better than refusing would; the refusal survives only where it is the safer act, which is a dirty tree.
3. The run SHALL NOT merge, SHALL NOT push, SHALL NOT force-push, and SHALL NOT open or mark ready a pull request. Every one of those stays human-gated exactly as the exit gate above states.
4. Staging SHALL name each path explicitly and the commit SHALL be bare. `git add -A` and `git commit -a` stage work nobody wrote down, and `git commit -- <path>...` rebuilds those paths from the working tree, committing content the run never recorded; the same objection the `branch-commit` conditions raise for a human turn does not weaken when the human is absent.

With those four in place `commit-ref` becomes reachable for the external unattended runner, and the slice notes cite the commit the same way a human turn would.

**Why this is not a loosening.** On this track reversibility, not audience, is the test (ADR-0221). The argument is the one this file already makes for the quarantine ref, with one verb changed: `git branch -D <branch>` removes the branch and everything on it, and nothing was merged, pushed or deployed. A commit on a branch no other work depends on is as recoverable as a ref under `refs/fhorja/attested/`, and strictly more useful, because it carries a tree, a message and a parent instead of a bare object.

What makes it safe is condition 1, and that is enforcement rather than intention: the external runner refuses to start on a default branch, so an admitted commit has nowhere to land except a branch the run owns. An execution layer that admitted commits without that refusal WOULD be a loosening, and this rule does not authorize one.

**What stays exactly as it was.** The two gates for an externally driven unattended run. Merge stays a human act everywhere. The bounded deferral for a run that can reach neither class. And the two `--apply` routes, which belong to a HUMAN turn and not to the unattended execution layer: `branch-commit --apply` for the local commit with its display-then-commit conditions (ADR-0163), and `pr-package --apply` for the push and the draft PR with its display and its refusal conditions (ADR-0185). Neither lets unattended `--apply` through; they name routes an unattended run never takes.
- Mid-run escalation: any boundary slice (schema, contract, migration, security) or any slice the classifier cannot prove safe escalates to the human mid-run. The wave stops at that slice; the run does not silently push past a boundary.

The whole middle, the work between the two gates that is verifiable and low blast radius, runs with little supervision. The gates are where the human stays.

## Runtime governor and kill switch (D11)

A run is bounded by deterministic limits so an unattended loop cannot run away:

- A per-task token and cost ceiling (bound to the Workflow tool's budget where the run executes).
- A maximum-iteration count.
- An identical-command loop detector (the same command repeating is a runaway signal).
- A wall-clock timeout.
- A kill switch as a STOP sentinel file. For hard immutability, the host SHALL place or mount it outside the agent writable scope. The controller and supervisor observe it independently, but an absolute path alone does not prove host permissions. Without that host boundary, record the control as cooperative-only rather than claiming containment.

Honest limit: a markdown-plus-bash system cannot meter arbitrary harness token spend by itself. The token and cost ceiling lean on the executing harness (the Workflow tool's budget and agent caps). The bash side covers max-iteration, wall-clock, loop detection, and the STOP file.

## Test policy (D12)

The autonomous agent writes and modifies tests freely (there is no deny-write on verifiers). The trust comes from a gate, not a restriction:

- Any slice that writes or modifies a test or eval file is a boundary slice that escalates to the human gate.
- The test and eval changes are flagged separately in the PROPOSED diff so a reviewer sees them plainly.
- The loop never auto-advances a slice on a test result the agent changed within that same slice. A loop cannot weaken its own verification and march on.

## What is out of scope, by construction (D9)

Recorded here so the cluster cannot drift toward removing the gate:

- Permissive headless autonomy (acceptEdits, bypassPermissions, skip-permissions, yolo modes).
- Default-no-approval auto-run (narrowed to the unattended track by ADR-0186; an attended chain advances without per-step approval).
- Model-picked autonomy tiers (the model deciding how much approval to skip).
- Parallel subagents on the implement leg (conflicting implicit decisions threaten single-writer; parallel is fine for read-heavy research legs only).
- Fully autonomous deploy with no human gate.

Trust is gated on the Fhorja eval scenarios and the human merge outcome, never on a vendor benchmark number (D10).

## Tracking is Fhorja-internal (D7)

The board of record is the Fhorja artifacts already in use: the spec, the `IMPLEMENTATION_PLAN` slices and execution waves, and the `TASK_STATE` phases. There is no external work tracker (Jira, Linear) in v1; a well-defined spec is the in-Fhorja work model. An optional one-way status export is a possible later spike, not v1 scope.

## How it reuses existing primitives (no pivot, D5/D8)

The track calls these and does not edit them:

- `approve-plan`: the entry gate.
- `implement-approved-slice`: the single writer per slice.
- `review-hard`: the exit merge gate, followed by the human merge (ADR-0221).
- The Workflow tool (ADR-0038) and waves (ADR-0042): the execution substrate.
- The substrate-write protocol (ADR-0034): every artifact write stays audited.

## Command surface

The full profile includes `autonomous-run`, the direct-use reference dispatcher, plus `autonomous-readiness` and the read-only `autonomous-board`. Deterministic helpers under `scripts/autonomy/` provide STOP observation, governor counters, classification and the bounded background lifetime. An external execution layer consumes ordinary command handoffs and the readiness and board surfaces; it refuses nested `autonomous-run` dispatch. Fhorja neither depends on that consumer nor implements its product capabilities.

## Background runs (the detachment layer)

A direct-use approved run MAY execute detached in an isolated worktree using the maintainer's pre-approved agent CLI. This remains one continuous reference session, not a durable service. ADR-0196 adds an independent process supervisor; approval, readiness, the D6 merge gate, the D9 skip list, the classifier and cooperative governor checks remain required. Such a run stays unattended whoever launched it: condition 2 of the ADR-0237 test in `wos/cross-cutting-workflow-guardrails.md ### Unattended sessions` excludes it, so it never writes a provisional P-N and never runs `branch-commit --apply` or `pr-package --apply`. A background session a person launched to run the ordinary chain on a task branch is a different thing, and that test decides it.

- Launch: `scripts/autonomy/launch-background-run.sh <task-folder> --timeout-sec <seconds> --grace-sec <seconds>` requires finite positive values for both bounds when `WOS_AGENT_CMD` is configured. Configuration remains whitespace-split arguments, never shell evaluation. When unset, the launcher prints instructions for this same supervised entry point and exits 0 without spawning an agent. Unsupported process control refuses with an attended foreground route. A bounded startup handshake reports success only after owned agent creation; startup refusal names its log or cause.
- Lifetime: `scripts/autonomy/supervise-background-run.py` watches a monotonic deadline from agent creation and the main-repository STOP sentinel independently of agent calls. It sends termination to the owned process group, then forced termination after the supplied grace. The supported boundary includes ordinary child commands in that group; it does not contain descendants that create another session or process group. Use an attended session if the configured CLI cannot keep its work inside this boundary. No security sandbox, durable restart or cross-session resume is added.
- Progress: the supervisor creates and finalizes `.wos/runs/<run_id>.json`; the controller sends between-slice heartbeats and observed escalation through `runs-feed.sh update`, retaining `WOS_MAIN_REPO` when called from a worktree. Serialized writes preserve the seven required ADR-0080 v1 fields and additive fields. Escalation survives exit 0 and late start, update or end calls. Clean exit removes the feed without certifying task completion. Boards stay read-only; stale heartbeat indicates display freshness, never proven process death.
- Admission and recovery: an exclusive main-repo owner is acquired before workspace setup. `.wos/background-run.owner` and `.wos/background-runs/<run_id>.json` retain unresolved ownership after supervisor death or failed finalization. A live owner, nonempty unresolved owner record, or legacy feed without proven closure refuses another launch even when stale. Before adopting an old detached run or recovering a refusal, a human must inspect its log, owned processes and partial workspace, stop or account for remaining writers, then reconcile the owner and feed records. Never signal a saved PID merely because it appears in metadata, and never automatically delete records to permit reentry.
- Permissions and interruption: pre-approved repository allowlists ONLY; the D9 skip list is unchanged. A permission prompt that blocks is bounded by the same deadline as any other stall. Timeout records cause unknown unless separately observed evidence identifies it. STOP, timeout, nonzero exit or cleanup failure records escalation; preserve logs and partial work, leave the interrupted slice incomplete, and route inspection to the human gate. Forced termination can interrupt a slice and does not roll it back. On a harness whose sandbox escalates per action, front-load known approvals while a human is present, per `wos/editor-mode-mappings.md ## Harness operational quirks`.
- Kill switch: the STOP sentinel path is ABSOLUTE in the main repository; a path inside the worktree is invalid. The host supplies any read-only mount or permission boundary that prevents the agent from clearing it. The local launcher and supervisor validate and observe the path but cannot prove that boundary. Without it, describe STOP as independently observed cooperative control.
- Worktree layering: the background run occupies the task's ADR-0074 worktree (reused when `SOURCE_OF_TRUTH.md` has a `## Workspace` section, provisioned otherwise); `implement-fleet` slice worktrees branch off the task branch as usual. Two runs never share a worktree because two runs never coexist.
- Notification: the supervisor attempts the presence-gated notifier after process cleanup and lifecycle finalization, with its own bounded lifetime. Its failure or absence does not prevent termination. A feed-write failure retains ownership and writes the failure to the run log for human recovery. Interrupted agents may not reach their final TASK_STATE.md write; inspect the supervisor record, log and partial workspace before continuing.

## Known open risk

Durable resume of a long autonomous run across sessions (restarting and re-attaching a stopped run) is unproven in a markdown-plus-bash system and stays out of scope. A DETACHED background run is one continuous session and does not touch this boundary. v1 scopes a run to a single session, foreground or detached, with the governor and the STOP file as the safety net. Cross-session resume is a later spike and a new decision if pursued.
