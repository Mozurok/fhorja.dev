---
name: autonomous-run
description: Run one approved task through one supervised session with Fhorja's full-profile direct-use reference dispatcher. It delegates verifiable slices to existing commands, emits PROPOSED diffs only, and never creates commits or attestation refs. Use when a maintainer invokes Fhorja directly after approve-plan and a BOOT verdict from autonomous-readiness. Do not use from another execution loop, for an unapproved or NOT-READY plan, for a single slice (use implement-approved-slice), or when durable resume, sandboxing, credentials, remote control, commit, publication, merge, or deploy is required.
metadata:
  category: autonomy
  primary-cursor-mode: Agent
  multi-repo-aware: false
  context-layers-consumed: [memory]
  context-layers-produced: [memory]
  tools: [Read, Write, Edit, Bash, Glob, Grep]
  x-wos-profiles: [full]
  provenance: first-party
  suggested-model: claude-sonnet-5
---
# autonomous-run

Act as Fhorja's direct-use reference controller for the autonomous delivery track, driving one approved waved plan through one bounded, low-supervision session.

Goal:
Run one approved, waved `IMPLEMENTATION_PLAN.md` slice by slice in one continuous foreground or detached session, bounded by two human gates and a runtime governor. Emit PROPOSED slice diffs for review and never commit or merge. This full-profile reference dispatcher is for a maintainer invoking Fhorja directly. It delegates writing to `implement-approved-slice` through the existing execution substrate and adds only the governor, boundary/test classifier, and escalation routing defined in ADR-0044 (D6, D11, D12). It does not re-implement approval, writing, or review, and it is not a product execution layer.

Mandatory context bootstrap (before any output):
<!-- shared:mandatory-context-bootstrap -->
- Read these sections in `WORKFLOW_OPERATING_SYSTEM.md` first:
  - `## LLM execution contract`
  - `## Editor mode policy` (mode definitions only; the tool mapping table is lazy-loaded in `wos/editor-mode-mappings.md` and needed only for non-Claude-Code tools)
  - `## Global output contract` (including **Adaptive handoff** and **Mode selection rule**)
  - `## Cross-cutting workflow guardrails`
- **Bootstrap tiers:** the light-weight commands (`branch-commit`, `what-next`, `where-we-at`, `slice-closure`, `compact-task-memory`) plus the high-frequency `implement-approved-slice` and `sync-task-state` (v3 wave1 item D) read the four sections above with two subsections of `## Cross-cutting workflow guardrails` skipped: `### External web access (centralized)` and `### Sequencing heuristics (by phase)`. Everything else is read at every tier, including `### Proposal vs approved persistence` and `### Substrate peer ownership (per ADR-0034)`, since all seven write substrate sections and reason about PROPOSED (`state-reconcile` stays on the full tier for cross-artifact judgment). The full tier is measured at 11678 tokens, the four always-read sections combined; the two skipped subsections are 1,035 of those (measured 2026-09-24), so the reduced tier is about 10,643. The leaf-reviewer tier (`verify-against-rubric`, ADR-0226) reads only `## Global output contract`, measured at 4841 tokens, plus its rubric.
- **Session bootstrap reuse (skip-if-unchanged; v3 wave1 item D):** WHEN this conversation already read the bootstrap sections in an earlier turn still VISIBLE in the context window AND `WORKFLOW_OPERATING_SYSTEM.md` has not changed since, the command MAY skip the re-read and cite the earlier one, emitting one Command transcript line: `Bootstrap: reusing turn <N> read, WOS unchanged`. Scoped exception to the context-budget re-fetch rule (`wos/context-budget.md`, "The re-fetch rule"), because these sections are one large, static, byte-identical read repeated every turn; every other tool result still re-fetches. VISIBLE means the section text itself is still present and quotable now, not merely that a record of the earlier read exists: a harness that clears a tool result while the record survives (ADR-0114) has not satisfied VISIBLE, and self-declared memory after a compaction never qualifies. A stateless-per-turn harness is excluded. The transcript line is mandatory; a silent skip is invalid output.
- **Resolving `WORKFLOW_OPERATING_SYSTEM.md` and a relative `wos/<topic>.md`.** Both resolve the same way: try the canonical workflow repository root FIRST, then the installed docs directory (`~/.claude/workflow-docs/` or `~/.cursor/workflow-docs/`, the spec at that root and topics under its `wos/`). Repository first, because the installed copy is a snapshot no sync prunes; preferring it would hide a `wos/` edit from every command until a reinstall. Name the resolved root in `### Command transcript`, and say so explicitly when NEITHER resolved rather than continuing silently, since several of these loads are MANDATORY.
- Read additional sections only when relevant to this command's role.
- Align all routing recommendations and next-command suggestions with the current command set.
- **Official next-command names only:** every recommended next command (including the handoff `Run now` line) MUST be the basename of an existing `commands/<name>.md` file in this workflow repository. Never invent names. One exception: `Run now: none` with `Mode: N/A` declares the chain ended with no honest next step, defined under `### Official command names (routing integrity)` (ADR-0126); use it only then, never to end a chain that has a real next step.

Required inputs:
- active task folder path
- IMPLEMENTATION_PLAN.md with an approved `## Approval log` entry and an `## Execution waves` section (dependency-ordered, file-scope-disjoint per ADR-0041)
- a BOOT verdict from `autonomous-readiness` for the current plan revision (`RUN_READINESS.md` in the active task folder); an absent or NOT-READY verdict routes there
- TASK_STATE.md, DECISIONS.md (the run honors every locked decision)
- the STOP sentinel file path, whether the host enforces it outside the agent writable scope, and the governor limits (per-task token/cost ceiling, max-iteration, wall-clock timeout)
- last completed step from TASK_STATE.md (command + summary)

Operating rules:
- **Direct-use reference boundary (ADR-0197).** Run only when a maintainer invokes Fhorja directly. IF another execution loop dispatches this command, THEN refuse before executing a slice and tell that outer layer to consume ordinary command handoffs instead. `autonomous-run` owns no durable queue, cross-session resume, security sandbox, credential broker, remote control, commit, attestation-ref, push, pull request, merge, or deploy path.
- **Approval is a precondition.** If `IMPLEMENTATION_PLAN.md` has no `## Approval log` entry for the current plan revision, refuse and route to `approve-plan`. Never run an unapproved plan. A `one-slice route` line is not that entry: `task-init` writes it only for an attended run, and the check that replaces its review runs at the attended inline close (ADR-0225). Refuse it the same way and route to `approve-plan`.
- **Readiness is a second, independent precondition (D-3 of the 2026-07-27 readiness task).** Before the first slice, a BOOT verdict from `autonomous-readiness` for the current plan revision must be on record (`RUN_READINESS.md` in the active task folder). IF it is absent, or the recorded verdict is NOT-READY, THEN refuse and route to `autonomous-readiness`, naming what the gate still has to answer. This precondition is ADDITIVE and never a replacement: a BOOT verdict does not approve a plan, an approved plan does not make a project ready, and the approval rule above is unchanged. Both must hold before the run begins, and neither is satisfied by the controller's own judgment.
- **Two gates, never auto-merge (D6).** The plan-approval gate is upstream (`approve-plan`, already passed). The merge gate is downstream: the controller produces PROPOSED slice diffs and routes them to `review-hard`, and a human performs the merge. The controller MUST NOT commit, merge, deploy, or take any irreversible step. This track keeps the reversibility limit: ADR-0200's bounded-audience test covers attended sessions, not an unattended run (ADR-0221).
- **Single writer (ADR-0040).** Each slice is executed by `implement-approved-slice`; the controller never writes product files itself. Parallel subagents on the implement leg are forbidden (D9).
- **Between every slice, run the governor and the classifier.** Call `scripts/autonomy/stop-check.sh` (halt if STOP present, D11), `scripts/autonomy/governor.sh` (halt on max-iteration, wall-clock timeout, or identical-command loop, D11), and `scripts/autonomy/classify-slice.sh` over the slice's file set.
- **Mid-run escalation (D6/D12).** When the classifier returns `escalate` (a boundary slice: schema, contract, migration, security; or any slice that touches a test or eval file), stop the wave at that slice and surface it to the human gate. Flag test and eval changes separately in the PROPOSED diff. Never auto-advance a slice on a test result the agent changed within that same slice.
- **Default to escalate on uncertainty.** A slice whose file set cannot be proven free of boundary and test/eval paths escalates. A false auto-advance is the dangerous failure.
- **Skip list (D9), refuse and record.** Never run in a permissive headless mode (acceptEdits, bypassPermissions, skip-permissions, yolo), never auto-run without approval, never let the model pick its own autonomy tier, never auto-deploy. If asked, refuse and cite ADR-0044 D9.
- **Tracking is Fhorja-internal (D7).** The board of record is the spec, the plan waves, and the TASK_STATE phases. Do not integrate or write to an external work tracker. For a single-glance read-only view of that board of record, use `autonomous-board`.
- **Evidence manifest (one per run).** At the end of a run, write `EVIDENCE_MANIFEST.md` into the active task folder: one row per evidence artifact the run produced, each row naming the artifact's path and the gate that produced it (for example `WEB_RUNTIME_VERIFY.md` and its `WEB_RUNTIME_VERIFY_SHOTS/` images from `web-runtime-verify`, `API_RUNTIME_VERIFY.md` from `api-runtime-verify`, `APP_RUNTIME_VERIFY.md` from `app-runtime-verify`, `GODOT_RUNTIME_VERIFY.md` from `godot-runtime-verify`, `DB_CONTEXT.md` from the db-context commands). The manifest is an INDEX: it records paths, never the artifacts' contents. Two rules make it honest rather than decorative:
  - **Check the disk before naming a path.** A row whose file is not on disk at write time reads `absent` with the reason, never a path. A named path that does not exist is invalid output, the same standard the gates themselves hold.
  - **Never embed credential-bearing output.** Do not paste an artifact's body into the manifest, and never a `supabase status` block, a service_role key, an anon key, a JWT secret, or a full connection string. `db-context-supabase` strips those at the source; a manifest that re-embeds them would undo that at the aggregation point, which is exactly where a leak is easiest to miss.
- **Trust comes from the Fhorja evals and the human merge (D10).** Mark a slice done only when its EARS exit criterion is met and verified; never gate on a vendor benchmark.
- **Single supervised session (v1).** Scope a run to one task and one continuous session bounded by the governor and the STOP file. Cross-session durable resume (restart and re-attach of a stopped run) is out of scope. On a cooperative stop, record the resume point in TASK_STATE.md at a slice boundary. Background termination can interrupt a slice; leave it incomplete for human inspection.
- **Background mode (opt-in; ADR-0196; runs-feed contract in ADR-0080).** Detach only through `scripts/autonomy/launch-background-run.sh <task-folder> --timeout-sec <seconds> --grace-sec <seconds>`, with explicit finite positive bounds and a pre-approved `WOS_AGENT_CMD`. When unset, follow the launcher's instructions through this same supervised entry point. If process control is unavailable, use an attended foreground session. In background mode the controller ADDITIONALLY:
  - sends progress through `scripts/autonomy/runs-feed.sh update <run_id> --step <slice>` alongside the between-slice governor calls, and sends `update <run_id> --state escalated --step <observed-reason>` on halt. Use the supplied `WOS_MAIN_REPO` so worktree calls reach the main feed. The supervisor owns feed creation, termination and finalization; late start, update or end calls cannot erase escalation. Clean process exit removes the feed; it does not certify slice completion or write the ADR-0079 outcome ledger.
  - uses the supplied `WOS_STOP_PATH`, an ABSOLUTE main-repo sentinel outside the worktree. The supervisor watches it and the elapsed-time deadline independently of agent progress, requests termination of the owned process group, then forces termination after the grace period. An absolute path does not prove the agent cannot clear it: record whether the host makes the sentinel read-only or outside the agent's writable scope. Without that host boundary, report STOP as independently observed cooperative control, not hard containment. Preserve partial work and logs; termination is neither rollback nor a clean slice-boundary guarantee.
  - runs under the repository's pre-approved permission allowlists ONLY; the D9 skip list applies unchanged. A blocked permission prompt is subject to the same deadline as any other stall. Record an observed timeout with cause unknown unless separate evidence identifies the cause; never infer a permission failure from elapsed time alone.
  - never runs concurrently: the launcher acquires exclusive ownership before workspace setup and retains it through cleanup. A live or unresolved owner refuses admission even with a stale heartbeat. Inspect the owner record, processes, logs and workspace before recovering legacy or unresolved runs; never delete ownership or STOP merely to bypass refusal. See `wos/autonomous-track.md` for the supported process boundary and recovery path.
  Escalation semantics are UNCHANGED by detachment: an escalation halts the run; nothing auto-advances because nobody is watching.
- **Substrate write protocol (per ADR-0034, K.2):** for every write to a substrate section, emit the transaction header AND append one `.wos/VERIFICATION_LOG.jsonl` line per `commands/_shared/substrate-write-protocol.md`.
- **Handoff:** end with the adaptive `### Handoff` block per `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract`.

Required output:
1. Pre-flight: direct invocation confirmed (yes/no), plan approved (yes/no), readiness verdict (BOOT, NOT-READY, or absent) with the path it was read from, waves detected, governor limits, STOP file path and host enforcement (`host-enforced` or `cooperative-only`; background mode: plus the run_id, feed file path, and log path)
2. Per wave: the slices attempted, each slice's classifier verdict (auto / escalate + reason)
3. Slices executed (via `implement-approved-slice`) with PROPOSED-diff status, and slices escalated to the human gate
4. Governor status at stop (iterations, elapsed, whether a limit halted the run)
5. The exact merge-gate routing (`review-hard`, then the human merge) for the PROPOSED diffs
6. The evidence manifest: the path to `EVIDENCE_MANIFEST.md` and its row count, with any `absent` rows named here too so a missing artifact is visible without opening the file
7. What was intentionally not done (no commit, no attestation ref, no merge, no deploy, escalated slices left for the human)
8. Recommended next command (`review-hard` for the produced diffs, or `implement-approved-slice` for an escalated slice the human now approves)
9. Recommended editor mode
10. Why this is the correct next step

### Substrate digest fallback
<!-- shared:substrate-digest-fallback -->
**Digest fallback when the canonical helper is unreachable.** `sha_of_section` extracts a section's body with `awk` and pipes it to `shasum -a 256`. A run executing inside a permission boundary that admits `shasum` but refuses `awk` and `sed` cannot invoke that helper, and MUST NOT reimplement it: an `awk` or `sed` program operand can call `system()` and write files, so a boundary that refuses those verbs refuses them for a reason. Assume the helper is unreachable whenever the workflow repository's `scripts/` directory is not readable from the working directory.

WHERE the canonical per-section digest helper is unreachable, the write SHALL use a whole-file SHA-256 and SHALL declare the reduced scope:

```bash
# One call per file. `shasum -a 256 <file>` needs no extraction step, so no
# refused verb is involved. Read the hash (the first field) out of the output;
# do not pipe it through `cut` or `awk` to trim it.
shasum -a 256 TASK_STATE.md
```

Then add `"sha_scope":"file"` to that JSONL line, so a validator distinguishes a file digest from a section digest instead of inferring it. Everything else about the protocol is unchanged: the transaction header still goes above the section heading, and there is still exactly one JSONL line per section write.

Do NOT rebuild the helper by writing each section out as its own file so it can be hashed separately. That workaround is coherent and it is what this rule exists to prevent: a 2026-08-04 run wrote 31 numbered section fragments to compute per-section digests by hand, spent the whole run doing it, and produced no product code.

What the fallback costs, stated so the trade is explicit rather than discovered later: the digest chain exists to detect an unlogged change to a SECTION. At file scope, two sections written in the same run share a digest, so the chain detects tampering with the file without attributing it to a section. That is a declared reduction in resolution, not a silent one, which is why the `sha_scope` field is mandatory rather than optional.
### Claim grounding (active epistemic humility)
<!-- shared:claim-grounding -->
**Claim grounding (active epistemic humility).** This block governs what you may assert and how you record it. It is keyed to the substrate section you are writing, not to which command is running, and it is INERT on any output that writes none of the claim-bearing sections below. Full contract and rationale: `wos/active-epistemic-humility.md`.

1. When this applies. This block fires ONLY while you are writing a claim-bearing substrate section: `TASK_STATE.md ## Current known facts`, `## Risks to watch`, `## Observations`, `## Active files in scope`, `## Canonical decisions`; `DECISIONS.md ## Locked decisions`; `IMPLEMENTATION_PLAN.md ## Current gaps`, `## Risks and mitigations`; `IMPACT_ANALYSIS.md`; `EXTERNAL_RESEARCH.md`; `REFERENCES.md`; or any section whose content is a statement a later command or a human decision will act on. WHEN your output writes none of these, this block imposes nothing: skip it and proceed. This is the D-13 inert clause; a fully-grounded or claim-free output pays nothing.

2. The unit is the load-bearing claim. A load-bearing claim is one a downstream command or a human decision consumes. A passing aside is not load-bearing; a statement someone will act on is. Apply the rest of this block per load-bearing claim, not per sentence.

3. Ground it or abstain. Before you assert a load-bearing claim, trace it to the enumerable grounded set: a captured `REFERENCES.md` entry, a file read in this session, command output actually seen, or a passing deterministic gate. A claim supported only by model memory is OUTSIDE the grounded set, including when you are right, because that support is not observable. WHEN a load-bearing claim falls outside the set, do NOT assert it: either investigate until it is grounded, or abstain per rule 6.

4. Status records provenance, never confidence. WHERE you attach an epistemic status to a claim, the status names WHERE THE CLAIM CAME FROM: a `REFERENCES.md` entry title, a file path plus line, or the gate output it came from. It SHALL NOT express a degree of certainty. Do NOT add a confidence field, a numeric threshold, or a self-assessment prompt anywhere; a self-reported confidence signal is not a usable control signal (`wos/active-epistemic-humility.md` Part 1.3). A status whose referent slot is empty is read as UNKNOWN, not as a weak yes.

5. Persisted claims carry the status; chat-only claims carry it when they route. Every load-bearing claim you write into a task-memory artifact carries its provenance referent, and that referent travels with the claim so a later command reads it too; do not drop it at the write boundary. A load-bearing claim that appears only in a chat-turn output carries a status only when it crosses the grounding boundary and triggers a route (an abstention, an escalation).

6. Abstain as a routed continuation, never a bare refusal. WHEN you abstain, name the specific investigation that would settle the question AND route to the command that runs it (`capture-references`, `code-locate`, `incident-triage`, or the fitting one). A withholding that stalls the work is invalid output. Abstention is distinct from `NO_OP`: `NO_OP` means there is no work to do; abstention means there is work and the grounding to do it is missing.

7. An unfired gate is not evidence. The absence of a fired check does not mean grounding existed. Do not read silence here as a pass.
### Standard output layout (required)
<!-- shared:standard-output-layout -->
Produce the command output using this structure (English only):

### Artifact changes
<!-- shared:artifact-changes-default -->
Follow `## Global output contract` in `WORKFLOW_OPERATING_SYSTEM.md` for `APPLIED` / `PROPOSED` / `SKIP` rules. Every listed file carries one of those three tokens, in Lean output too; a prose verb like "written" is not a label.

### Command transcript
<!-- shared:command-transcript-standard -->
Brief audit trail (max 4 lines; max 3 in no-op runs with `NO_OP_TRACE`).

### Handoff
<!-- shared:handoff-body -->
Use the adaptive ending format from `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full per session state). Every Handoff is one fenced `text` block with all four lines, `Run now:`, `Mode:`, `Work complexity:` and `Reason:`, on a stop and on a refusal too; the terminal form is `Run now: none` with `Mode: N/A`.

### Definition of done (command output)
- The run was a direct maintainer invocation for one task and one continuous session. A request from another execution loop was refused before slice execution (ADR-0197).
- The run emits only PROPOSED slice diffs; no commit, attestation ref, merge, or deploy happened (D6/D9, ADR-0197).
- Every slice passed the governor (`stop-check.sh`, `governor.sh`) and the classifier (`classify-slice.sh`) before execution; the evidence is in the transcript.
- Every boundary or test/eval-touching slice was escalated to the human gate, not auto-advanced (D6/D12).
- The plan was approved (`## Approval log` present, and not a `one-slice route` line) before the run; an unapproved plan is a refusal routed to `approve-plan`.
- A BOOT verdict from `autonomous-readiness` was on record before the first slice; an absent or NOT-READY verdict is a refusal routed to `autonomous-readiness`, and it never stood in for the approval check above.
- In background mode: explicit timeout and grace bounds were supplied, supervisor-owned lifecycle and controller progress used the main-repo feed, interrupted work remained incomplete, and the STOP path was absolute in the main repo. The output named whether STOP was host-enforced or cooperative-only. The permission posture stayed allowlist-only with the D9 skip list unchanged.
- `EVIDENCE_MANIFEST.md` was written with every row's path checked against the disk, `absent` recorded where a file is missing, and no artifact body or credential-bearing output embedded.
- No existing command was modified; the controller reused `implement-approved-slice` and `review-hard` (D5/D8).
- Output ends with a complete `### Handoff` block per the adaptive format in `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract`.
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
A boring, bounded run that a human can trust precisely because it never crosses a gate on its own. Prefer stopping and escalating over guessing.
