# ADR-0044: The autonomous delivery track (a new additive WOS cluster)

- **Status**: Accepted
- **Date**: 2026-06-16
- **Tags**: autonomy, additive-track, human-in-the-loop, two-gates, mid-run-escalation, runtime-governor, kill-switch, fleet-orchestration, workflow-tool, single-writer

## Context

The WOS has the fan-out primitives for parallel work (the Workflow tool per ADR-0038, parallel slice execution per ADR-0041, waves-aware routing per ADR-0042) but no end-to-end unattended loop. `implement-fleet` runs slices in parallel, yet every wave is still human-gated, and nothing drives a whole task from an approved plan to a reviewable result on its own.

The maintainer asked for a way to hand a well-specified task to agents and come back to a finished result to refine, the pattern the frontier labs market as "autonomous". That ambition is in direct tension with the WOS core: PROPOSED-by-default, single-writer-per-folder (ADR-0040), verification gates, and "never go silent".

A focused fleet research sweep (8 angles, 73 sources, captured in the task folder's `EXTERNAL_RESEARCH.md` and project `REFERENCES.md`) resolved the tension empirically. Every production autonomous loop that was fetched (Anthropic harnesses, OpenAI Codex, Google Jules, GitHub Copilot coding agent, Cognition Devin) keeps a human merge gate. No fetched primary source showed an unattended spec-to-deploy loop that auto-merges to main. "Fully autonomous" is mostly framing; the real systems bound autonomy with sandboxes, verification, budgets, and a human merge gate. So the design question became where the human gate sits, not whether to keep it.

## Decision

Add a new additive command cluster, the autonomous delivery track ("WOS for autonomy"), parallel to the engineering and design tracks. It drives the existing fleet primitives between two human gates and does not modify any existing command. Twelve decisions (locked in a `decision-interview` run on 2026-06-16; full EARS text in the task `DECISIONS.md`) constrain it. The load-bearing ones:

- The track is a NEW ADDITIVE cluster (D5, D8). It does not pivot, re-route, or remove any existing command, direction, or behavior. The human-in-the-loop is not eliminated.
- Human gate model (D6): a human plan-approval gate before execution, a human draft-diff merge gate before any irreversible step, and mid-run escalation of any boundary slice (schema, contract, migration, security) or any unverifiable slice.
- Work tracking is WOS-internal (D7). The spec, the `IMPLEMENTATION_PLAN` slices and execution waves, and `TASK_STATE` phases are the board of record. No external work tracker (Jira, Linear) in v1.
- Skip list (D9): permissive headless autonomy, default-no-approval auto-run, model-picked autonomy tiers, parallel subagents on the implement leg, and fully autonomous deploy are out of scope by construction.
- Trust source (D10): trust is gated on the WOS eval scenarios and the human merge outcome, never on a vendor benchmark number.
- Runtime governor (D11): a per-task token and cost ceiling, a maximum-iteration count, an identical-command loop detector, and a wall-clock timeout, with the kill switch as a STOP sentinel file located outside the agent writable scope.
- Test policy (D12): the agent writes and modifies tests freely, but any slice that touches a test or eval file is treated as a boundary slice that escalates to the human gate, with the test changes flagged separately, and the loop never auto-advances a slice on a test result the agent changed in that same slice. The gate, not a deny-write, carries the trust.

The track is built as a thin code-orchestrated dispatcher over the existing primitives: an approved waved `IMPLEMENTATION_PLAN` feeds a controller that drives the Workflow tool (ADR-0038) wave by wave, runs `implement-approved-slice` as the single writer per slice, applies the governor and the boundary/test classifier between slices, and emits PROPOSED slice diffs for the merge gate. It never merges on its own.

The exact command surface (names, whether one controller command or a small set) is provisional at the time of this ADR and is pinned during the build. The enforcement is prompt-level plus deterministic bash helpers (the STOP file, the governor counters, the slice classifier), consistent with the rest of the WOS being markdown plus bash, not a runtime engine.

## Consequences

### Positive

- The maintainer can run most of a well-specified task hands-off while the two gates keep a faulty run from reaching main on its own.
- The autonomy reuses primitives that already exist and are audited (the Workflow tool, `implement-approved-slice`, single-writer-per-folder, the substrate-write protocol), so the new surface is small.
- The skip list (D9) is recorded, so the cluster cannot quietly drift toward removing the human gate; the failure data the field has produced (one-sided) backs that boundary.

### Negative

- A new cluster is more commands to maintain, register in four places, and cover with eval scenarios.
- A markdown plus bash WOS cannot truly meter arbitrary harness token spend; the governor leans on the Workflow tool's budget where the run executes and covers only max-iteration, wall-clock, loop detection, and the STOP file from bash.
- Durable resume of a long autonomous run across sessions is unproven here; v1 scopes a run to a single supervised session and treats cross-session resume as a later spike.

### Neutral

- The existing engineering commands are unchanged. The track calls `approve-plan` (up-front gate), `approve-proposed` and `review-hard` (merge gate), and `implement-approved-slice` (the writer), it does not edit them.
- The board-of-record is the WOS artifacts already in use, so there is no new persistence layer.

## Alternatives considered

### Alternative 1: a fully autonomous spec-to-deploy loop with no human gate

- Rejected. It violates PROPOSED-by-default, single-writer, and never-go-silent at once, and the research found no production system that actually does it. The failure data (Replit, the Devin 3/20 independent run) is one-sided.

### Alternative 2: extend `implement-fleet` with an autonomous mode

- Rejected per D5/D8. Editing an existing command pivots behavior the rest of the workflow depends on; an additive cluster keeps the boundary clean and the existing command untouched.

### Alternative 3: external work-tracker integration (Jira or Linear epics and sub-tickets) as the board

- Rejected per D7. A well-defined spec plus the WOS plan, waves, and TASK_STATE phases already model the work; an external tracker adds an auth and secrets surface and a context cost for no v1 benefit. An optional one-way status export stays a possible later spike.

## References

- `projects/<client>__<project>/active/2026-06-16_autonomous-agent-delivery-loop/` (this ADR's source task: `DECISIONS.md` D1-D12, `EXTERNAL_RESEARCH.md`, `IMPLEMENTATION_PLAN.md`).
- `wos/autonomous-track.md` (the lazy-loaded topic that describes the cluster, the gates, the governor, and the run protocol).
- ADR-0038 (Workflow tool as the parallel-orchestration primitive), ADR-0040 (single-writer-per-folder), ADR-0041 (parallel slice execution + file-scope disjointness), ADR-0042 (waves-aware routing), ADR-0043 (reference grounding execution gate), ADR-0034 (substrate-write protocol and the lived-substrate ladder).

## Notes

The twelve decisions were locked in a `decision-interview` run on 2026-06-16. D1-D5 framed the additive, human-in-the-loop scope; D6-D11 were chosen from the research synthesis; D12 was a maintainer pick ("write tests freely") reconciled with the loop-cannot-grade-itself floor by gating test-touching slices rather than denying writes. The command surface is provisional and is pinned during the build (the first build slice authors this ADR and `wos/autonomous-track.md`). Revisit the single-session scope (negative consequence) if durable cross-session resume proves necessary; that would be a new decision, not a patch to this ADR.
