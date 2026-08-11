# Autonomous delivery track ("Fhorja for autonomy")

The autonomous delivery track is a new additive cluster (ADR-0044), parallel to the engineering and design tracks. It lets the maintainer hand a well-specified, approved, waved plan to agents and review the result, while two human gates and a runtime governor keep a faulty run from reaching anything irreversible on its own. It does not modify any existing command. The human-in-the-loop is moved and bounded, not removed.

Load this topic when designing, building, or running the autonomy cluster. The normative decisions are ADR-0044 and the source task `DECISIONS.md` (D1-D12).

## What it is, in one paragraph

A thin code-orchestrated dispatcher over the primitives that already exist. An approved waved `IMPLEMENTATION_PLAN` feeds a controller. The controller drives the Workflow tool (ADR-0038) wave by wave, runs `implement-approved-slice` as the single writer per slice (ADR-0040), applies a runtime governor and a boundary/test classifier between slices, and emits PROPOSED slice diffs for review. It never merges on its own. This is not an LLM swarm and not an unattended runner; it is a bounded loop with the human at two gates.

## The two gates plus mid-run escalation (D6)

- Plan-approval gate (entry): a human approves the waved plan before any execution. The track reuses `approve-plan`; it does not re-implement approval.
- Draft-diff merge gate (exit): a human approves the merged PROPOSED diff before any irreversible step (commit to an integration branch, merge, deploy). The track reuses `approve-proposed` and `review-hard`.
  - Commit-evidence is a separate question from this gate, and ADR-0133 answers it: an unattended run satisfies the commit-evidence floor by routing to `ref-attested`, where the RUNNER points a quarantine ref at a git object holding the run's work, under `refs/fhorja/attested/<run-id>/<invocation-id>`. That ref is not an integration branch, and reaching it is not an irreversible step: `git update-ref -d <ref>` removes it, and nothing is merged, pushed or deployed. This gate is otherwise unchanged, and merge, push and draft-PR stay human-gated.

## The autonomous commit route (driver-owned branch)

`ref-attested` preserves an unattended run's work; it does not give that run the ordinary developer act of committing. Written down here because the omission had a cost: through 2026-08-10 the closure floors read as "an unattended run cannot commit", so a driver that committed was violating a floor while a driver that produced files and left them untracked was compliant, and the compliant outcome is the one a maintainer reads as failure.

**The rule.** An unattended run MAY commit, and ONLY onto a branch it owns:

1. The branch SHALL NOT be a default or integration branch. WHEN the target is on one, the runner SHALL create an owned branch from it and switch before the first invocation, so the run's work never lands on the default branch. WHERE the working tree is dirty the runner SHALL instead REFUSE to start, because switching would carry or strand changes the operator wrote and did not commit, and a run is never worth touching those.
2. The runner SHALL create the branch when the target is not already on an owned one, naming it by convention (`fhorja/<run-id>`), and SHALL record the name it created. Where the target is already on a non-default branch the runner SHALL leave it alone: that branch is the operator's choice and is already outside condition 1's prohibition.

   Written as a correction rather than silently: the first draft of this rule said a run on a default branch "SHALL refuse to start rather than switch away from it", which preserved the driver's existing refusal and contradicted condition 2 in the same breath, leaving it reachable only in an odd narrow case. Refusing does protect the default branch, and it protects it by making the operator do the work by hand; creating the branch protects it better. The refusal survives only where it is the safer act, which is a dirty tree.
3. The run SHALL NOT merge, SHALL NOT push, SHALL NOT force-push, and SHALL NOT open or mark ready a pull request. Every one of those stays human-gated exactly as the exit gate above states.
4. Commits SHALL name their paths explicitly. `git add -A` and `git commit -a` stage work nobody wrote down, which is the same objection the `branch-commit` conditions raise for a human turn and it does not weaken when the human is absent.

With those four in place `commit-ref` becomes reachable unattended, and the slice notes cite the commit the same way a human turn would.

**Why this is not a loosening.** The reversibility argument is the one this file already makes for the quarantine ref, with one verb changed: `git branch -D <branch>` removes the branch and everything on it, and nothing was merged, pushed or deployed. A commit on a branch no other work depends on is as recoverable as a ref under `refs/fhorja/attested/`, and strictly more useful, because it carries a tree, a message and a parent instead of a bare object.

What makes it safe is condition 1, and that is enforcement rather than intention: the run refuses to start on a default branch, so an admitted commit has nowhere to land except a branch the run owns. A track that admitted commits without that refusal WOULD be a loosening, and this rule does not authorize one.

**What stays exactly as it was.** The two gates. Merge, push and draft-PR as human acts. The bounded deferral for a run that can reach neither class. And `branch-commit --apply` as the only path for a HUMAN turn, with its confirmation-after-display conditions unchanged; this route does not relax that command, it names a second route that a human turn never uses.
- Mid-run escalation: any boundary slice (schema, contract, migration, security) or any slice the classifier cannot prove safe escalates to the human mid-run. The wave stops at that slice; the run does not silently push past a boundary.

The whole middle, the work between the two gates that is verifiable and low blast radius, runs with little supervision. The gates are where the human stays.

## Runtime governor and kill switch (D11)

A run is bounded by deterministic limits so an unattended loop cannot run away:

- A per-task token and cost ceiling (bound to the Workflow tool's budget where the run executes).
- A maximum-iteration count.
- An identical-command loop detector (the same command repeating is a runaway signal).
- A wall-clock timeout.
- A kill switch as a STOP sentinel file located outside the agent writable scope. The controller checks it between slices; the agent provably cannot clear it.

Honest limit: a markdown-plus-bash system cannot meter arbitrary harness token spend by itself. The token and cost ceiling lean on the executing harness (the Workflow tool's budget and agent caps). The bash side covers max-iteration, wall-clock, loop detection, and the STOP file.

## Test policy (D12)

The autonomous agent writes and modifies tests freely (there is no deny-write on verifiers). The trust comes from a gate, not a restriction:

- Any slice that writes or modifies a test or eval file is a boundary slice that escalates to the human gate.
- The test and eval changes are flagged separately in the PROPOSED diff so a reviewer sees them plainly.
- The loop never auto-advances a slice on a test result the agent changed within that same slice. A loop cannot weaken its own verification and march on.

## What is out of scope, by construction (D9)

Recorded here so the cluster cannot drift toward removing the gate:

- Permissive headless autonomy (acceptEdits, bypassPermissions, skip-permissions, yolo modes).
- Default-no-approval auto-run.
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
- `approve-proposed` and `review-hard`: the exit merge gate.
- The Workflow tool (ADR-0038) and waves (ADR-0042): the execution substrate.
- The substrate-write protocol (ADR-0034): every artifact write stays audited.

## Command surface (provisional)

The exact cluster shape is pinned during the build. The working proposal is one controller command (working name `autonomous-run`) that takes an approved waved plan and drives the loop, plus an optional read-only board view. The controller is backed by deterministic helpers under `scripts/autonomy/` (the STOP-file checker, the governor counters, the boundary/test classifier). When the surface is finalized, register each new command in all four registries and add its eval scenario, the same as any other command.

## Background runs (the detachment layer)

An approved run MAY execute detached from the interactive terminal, in an isolated worktree, driven by the maintainer's configured agent CLI. This is a thin layer over the unchanged controller contract (D-1..D-4 of the 2026-07-03 background-run task); nothing about the gates, the governor, or the classifier changes.

- Launch: `scripts/autonomy/launch-background-run.sh <task-folder>` reads the CLI invocation from `WOS_AGENT_CMD`; when unset it prints the manual detached-launch steps and exits cleanly. It refuses to start while any runs-feed file has a heartbeat fresher than the staleness threshold (one background run at a time).
- Progress: the run is the PRODUCER of the ADR-0080 runs feed (`.wos/runs/<run_id>.json`): start on entry, a fresh-heartbeat update with the current slice between slices (alongside the existing governor calls), `state=escalated` plus `scripts/autonomy/notify.sh` on ANY halt or escalation, and removal on clean exit. The portfolio board and `autonomous-board` render the feed; a file whose `last_update_ts` is older than the staleness threshold reads as dead, not running.
- Permissions: pre-approved repository allowlists ONLY; the D9 skip list applies unchanged and the mode accepts no permissive flag. A permission prompt that would block the detached session stalls the run until the governor's wall-clock timeout produces a clean stop at a slice boundary, recorded as an escalation with the stall named. On a harness whose sandbox escalates per action (Codex CLI), front-load the actions known to require escalated approval to the start of the run while a human is still present, per `wos/editor-mode-mappings.md ## Harness operational quirks`.
- Kill switch: the STOP sentinel path is ABSOLUTE in the main repository; a path inside the worktree would be agent-writable and is invalid.
- Worktree layering: the background run occupies the task's ADR-0074 worktree (reused when `SOURCE_OF_TRUTH.md` has a `## Workspace` section, provisioned otherwise); `implement-fleet` slice worktrees branch off the task branch as usual. Two runs never share a worktree because two runs never coexist.
- Notification: the feed plus the boards plus the contract-mandated `TASK_STATE.md` writes are the canonical channel; the presence-gated local notifier is best-effort extra and its absence changes nothing.

## Known open risk

Durable resume of a long autonomous run across sessions (restarting and re-attaching a stopped run) is unproven in a markdown-plus-bash system and stays out of scope. A DETACHED background run is one continuous session and does not touch this boundary. v1 scopes a run to a single session, foreground or detached, with the governor and the STOP file as the safety net. Cross-session resume is a later spike and a new decision if pursued.
