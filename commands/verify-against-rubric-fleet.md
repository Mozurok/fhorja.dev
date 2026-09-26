---
name: verify-against-rubric-fleet
description: Orchestrator-workers generalization of verify-against-rubric to N=many artifacts against ONE locked rubric. Dispatches N stateless Sonnet sub-agents in parallel; each receives ONE artifact + the SAME rubric with read-only input access and one assigned JSON return-file write (no TASK_STATE, no DECISIONS, no prior history); returns structured per-criterion verdict. Orchestrator merges into VERIFICATION_LOG.md with aggregate pass/fail counts + failure clustering (which criteria fail most often across the cohort -> likely system-level signal). Use when N >= 4 artifacts share one rubric (multi-slice retrospective, batch PR review, cohort spec audit). Do not use for single artifacts (use verify-against-rubric), when rubrics differ per artifact (run separately or refactor the rubric first), or on LOW/MEDIUM complexity slices (use self-critique-and-revise).
metadata:
  category: planning-and-validation
  primary-cursor-mode: Plan
  multi-repo-aware: false
  context-layers-consumed: [memory]
  context-layers-produced: [memory]
  tools: [Read, Write, Edit, Bash, Glob, Grep, Agent]
  x-wos-profiles: [full]
  provenance: first-party
  suggested-model: claude-sonnet-5
  orchestrator: true
  workers:
    - role: rubric-verifier
      tier: claude-sonnet-5
      contract_ref: commands/_shared/worker-contract.md
  max_fanout: 16
  convergence:
    pattern: barrier
    timeout_ms: 600000
    partial_ok: true
  merge_strategy: union
  worker_input_schema: |
    {
      "type": "object",
      "required": ["artifact_id", "artifact_path", "rubric", "criteria"],
      "properties": {
        "artifact_id": {"type": "string", "pattern": "^[a-z0-9-]+$"},
        "artifact_path": {"type": "string"},
        "rubric": {"type": "string"},
        "rubric_source": {"type": "string"},
        "criteria": {
          "type": "array",
          "minItems": 1,
          "items": {
            "type": "object",
            "required": ["criterion_id", "criterion"],
            "properties": {
              "criterion_id": {"type": "string"},
              "criterion": {"type": "string"},
              "threshold": {"type": "string"}
            }
          }
        }
      }
    }
  worker_output_schema: |
    {
      "type": "object",
      "required": ["status", "artifact_id", "overall_verdict", "per_criterion"],
      "properties": {
        "status": {"enum": ["satisfied", "needs_revision", "max_iterations_reached", "failed", "interrupted"]},
        "artifact_id": {"type": "string"},
        "overall_verdict": {"enum": ["satisfied", "needs_revision", "failed"]},
        "per_criterion": {
          "type": "array",
          "minItems": 1,
          "items": {
            "type": "object",
            "required": ["criterion_id", "verdict", "reason"],
            "properties": {
              "criterion_id": {"type": "string"},
              "verdict": {"enum": ["satisfied", "needs_revision", "failed", "n/a"]},
              "reason": {"type": "string", "maxLength": 240}
            }
          }
        },
        "subagent_identifier": {"type": "string"}
      }
    }
---
# verify-against-rubric-fleet

Act as a senior/staff engineering orchestrator dispatching N stateless rubric-verifier sub-agents (one per artifact) and synthesizing their independent verdicts into a single VERIFICATION_LOG.md cohort entry with failure clustering.

Goal:
For cohorts of N >= 4 artifacts that share ONE locked rubric (multi-slice retrospective, batch PR package review, design system spec audit), dispatch N stateless Sonnet workers in parallel. Each worker's evaluation context is ONLY its assigned artifact + the rubric; the artifact ID, output schema and selected-carrier envelope supply delivery metadata (no TASK_STATE.md, no DECISIONS.md, no sibling artifacts, no prior conversation). Workers return structured per-criterion verdicts independently. The orchestrator merges into one VERIFICATION_LOG.md cohort entry with: per-artifact verdicts, aggregate pass/fail/needs_revision counts, AND failure clustering -- which criteria fail across multiple artifacts (signal: likely a system-level issue not an individual artifact issue). Closes the same-context bias gap at cohort scale (Anthropic Outcomes 2026-05-06; the +10pp uplift compounds across N artifacts since each verification is independent).

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
- task folder path
- artifact manifest: array of `{artifact_id, artifact_path}` per artifact (caller pre-enumerates; orchestrator does NOT auto-discover artifacts)
- rubric source: EITHER inline rubric (verbatim) OR reference to a section in IMPLEMENTATION_PLAN.md or DECISIONS.md (path + section anchor)
- optional: explicit criteria list (overrides the criteria extracted from rubric; useful when rubric prose mixes criteria with prologue)
- optional: explicit max_fanout override (defaults to 16; absolute ceiling 20)
- optional: cohort_label (string used in VERIFICATION_LOG.md entry header; defaults to date + N artifacts)

Task repository files to update:
- VERIFICATION_LOG.md (orchestrator is the SOLE writer per `wos/substrate-peers.md`; one cohort entry appended per fleet run)
- TASK_STATE.md `## Last completed step` per the canonical <!-- count:closure-pattern-sections -->5<!-- /count -->-section write pattern in `commands/_shared/task-state-slice-closure-pattern.md`
- `.wos/fleet-inbox/<run_id>/` directory (gitignored; one JSON payload per worker: native return or orchestrator copy of the runtime result)
- `.wos/VERIFICATION_LOG.jsonl` (one line per merged section + one per per-worker classification event; distinct from VERIFICATION_LOG.md which holds human-readable verdicts)

Operating rules:
- **Handoff:** end with the adaptive `### Handoff` block per `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract`.
- **Step 1: Lock the rubric.** Either accept inline as-is OR extract referenced section. Rubric MUST decompose into discrete criteria (each verifiable independently). If criteria list not provided, parse the rubric: each bullet/numbered item -> one criterion with auto-generated `criterion_id` (`c1`, `c2`, ...). Refuse with NO_OP_TRACE if rubric is vague ("looks good", "feature works") -> route to `resolve-contract-gaps` first.
- **Step 2: Validate manifest.** Confirm N >= 4 (else NO_OP_TRACE: route to `verify-against-rubric` per-artifact). Confirm every `artifact_id` unique. Confirm every `artifact_path` exists. Confirm N <= `max_fanout` (else NO_OP_TRACE: list overflow; suggest splitting cohort by sub-topic).
- **Step 3: Verify prerequisites.** VERIFICATION_LOG.md exists (or create with header from convention); rubric has >= 2 criteria (single-criterion rubric collapses to a trivial pass/fail; route to `verify-against-rubric` instead).
- **Step 4: Verify tier guard.** Orchestrator runs Sonnet (`claude-sonnet-5`); workers run Sonnet (`claude-sonnet-5`). Per `wos/sub-agent-orchestration.md ## Tier-mapping per role`: per-target deep analysis (one artifact vs one rubric, judgment-heavy) -> Sonnet; cross-target synthesis (failure clustering, rule-based aggregation) -> Sonnet acceptable. Override-down from default Opus orchestrator: rationale = "clustering is mechanical (group by criterion_id), aggregation is counting; cost guard favors Sonnet". Tier guard PASS.
- **Step 5: Dispatch workers (the load-bearing step).** For each artifact, invoke a stateless sub-agent (Claude Code `Agent` tool with `subagent_type: general-purpose`). Each worker MUST receive ONLY: its artifact ID and path (read-only), the rubric verbatim, the criteria list, the output schema and selected-carrier delivery metadata. The assigned return file is its only write permission. NO TASK_STATE.md, NO DECISIONS.md, NO sibling artifacts, NO prior conversation history. Per ADR-0033 isolation rule. **Per ADR-0038 Rule 1 (structured output mandatory), the worker returns a typed payload matching `worker_output_schema` and never free-form prose.** Name the path you are on before dispatch (ADR-0158 D-1). Resolve `<task_root>/.wos/fleet-inbox/<run_id>/<worker_id>.json` for each worker and create the run inbox. On the dynamic-workflow path, declare `agent(prompt, {schema})` with `worker_output_schema`; consume the runtime's typed result and persist its JSON copy at that path. Never tell the worker to call StructuredOutput. On the `Agent` path, pass the resolved path as `fleet_inbox_artifact` in the existing worker-contract envelope, outside `task_input`; the worker writes one schema-conforming JSON payload there and the orchestrator reads it. This return-file permission grants no other writes (ADR-0158 D-2). Supply the output schema and selected-carrier instruction outside `task_input`. End the dynamic worker prompt with `Return one payload matching worker_output_schema and nothing else`; end the native worker prompt with `Write one JSON payload matching worker_output_schema to fleet_inbox_artifact and nothing else`. The orchestrator validates the selected payload against `worker_output_schema`; the native file or runtime copy remains available for audit/replay.
- **Step 6: Each worker (instruction template).** Worker reads the artifact; for each criterion, evaluates independently and assigns `satisfied | needs_revision | failed | n/a` with 1-2 line reason (<= 240 chars). Worker MUST NOT consult sibling artifacts, MUST NOT defer to "the cohort", MUST treat its artifact as if it were the only one. Worker assigns `overall_verdict`: `satisfied` (all criteria satisfied or n/a), `needs_revision` (one or more `needs_revision`, none `failed`), `failed` (one or more `failed`). **Final-instruction reminder (ADR-0038 Open follow-up mitigation against schema-skip): the worker prompt MUST end with the selected-carrier reminder from Step 5 to defeat the 10-of-12 schema-skip failure mode observed on 2026-06-05.** Worker returns `{status, artifact_id, overall_verdict, per_criterion: [{criterion_id, verdict, reason}, ...], subagent_identifier}` through the selected carrier. Free-form prose returns are CONTRACT VIOLATIONS and MUST be classified `interrupted` in `### Command transcript`.
- **Step 7: Wait for convergence.** Barrier pattern: wait for all N workers OR `timeout_ms` (10 min default). Read each expected worker's validated runtime result or assigned `<task_root>/.wos/fleet-inbox/<run_id>/<worker_id>.json` according to the selected carrier. Count that result once; unrelated files or replay copies cannot stand in for it. Classify per `commands/_shared/convergence-policy.md`.
- **Step 8: Aggregate verdicts.** Apply `union` merge: collect all per-artifact verdicts. Compute: count of artifacts `satisfied` / `needs_revision` / `failed`; cohort_overall_verdict (satisfied iff all N satisfied; otherwise needs_revision or failed by worst-of).
- **Step 9: Failure clustering (the novel deliverable).** For each criterion, count `needs_revision` and `failed` verdicts ACROSS the cohort. Sort criteria by failure-rate descending. Cluster criteria with failure-rate >= 50% as `SYSTEMIC` (signal: rubric criterion likely points at a system-level issue, not per-artifact). Criteria with failure-rate < 50% are `LOCALIZED`. Emit the clustering as a separate output section AND in the VERIFICATION_LOG.md cohort entry.
- **Step 10: Write VERIFICATION_LOG.md cohort entry.** Append a single entry with: cohort_label, date, rubric source, N, per-artifact verdict table, aggregate counts, failure clustering (SYSTEMIC vs LOCALIZED), recommended remediation routing per cluster. The orchestrator is the SOLE writer of this section. Every bullet MUST be anchored to an existing parent heading or list per ADR-0038 Rule 3.
- **Step 10.5: Scan substrate orphans (ADR-0038 Rule 3 enforcement).** Immediately after the merge in Step 10 and BEFORE updating TASK_STATE.md, run `scripts/scan-substrate-orphans.py VERIFICATION_LOG.md`, with `scripts/scan-substrate-orphans.py` (resolved against the WORKFLOW ROOT, ADR-0218); its exit 2 means a named file was absent, never a pass. If exit code != 0 (orphan bullets detected between sections), the apply step is NOT successful: emit `NO_OP_TRACE` listing the orphan offsets in `### Command transcript`, refuse to update TASK_STATE.md, and route to `state-reconcile` to repair the structural drift. Only on exit code 0 may the orchestrator proceed to Step 11. This closes the substrate-bullet-orphan failure class (`wos/bug-classes/substrate-bullet-orphan.md`, detector commit `5840755`).
- **Step 11: Emit VERIFICATION_LOG.jsonl.** One line per per-worker classification event plus one line for the merged cohort entry (`event=fleet-merge`, `partials=[worker_id, ...]`, `strategy=union`, `orphan_scan=passed`).
- **Step 12: Update TASK_STATE.md.** Per the canonical <!-- count:closure-pattern-sections -->5<!-- /count -->-section write pattern. Reference the cohort_label. Gated on Step 10.5 orphan-scan exit code 0.
- Workers MUST NOT consult each other or share context. The independence is the load-bearing property: if workers see each other's verdicts, the +10pp Anthropic Outcomes uplift collapses (groupthink).
- Failure clustering is INFORMATIONAL, not deterministic. A SYSTEMIC label is a hypothesis: the orchestrator MUST suggest a follow-up (typically `decision-interview` on the rubric itself or `direction-adjust` on the underlying spec) but MUST NOT auto-route.
- Mixed rubrics in one fleet run are FORBIDDEN. Re-run per rubric. (For multiple rubrics on the same artifact set, run the fleet N_rubrics times; the rubric is the load-bearing dimension, not the artifact.)

Required output:
1. Rubric source + criteria count
2. Artifact count + manifest summary
3. Dispatch summary: N dispatched, M satisfied, K needs_revision, L failed, P interrupted, T timed out
4. Per-artifact verdict table (artifact_id, overall_verdict, count_failed, count_needs_revision)
5. Aggregate cohort verdict + counts
6. Failure clustering: SYSTEMIC criteria (>=50% failure rate) with affected artifacts; LOCALIZED criteria
7. Recommended remediation routing: SYSTEMIC -> `decision-interview` on rubric or `direction-adjust` on spec; LOCALIZED -> `implement-slice-complement` per artifact (one per artifact with non-satisfied verdict)
8. Path to updated VERIFICATION_LOG.md cohort entry + orphan-scan exit code (MUST be 0 to proceed)
9. Recommended next command (typically `decision-interview` if SYSTEMIC clusters present, else per-artifact follow-ups; `state-reconcile` if orphan-scan failed)

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
- Rubric is locked and discrete (>= 2 independently verifiable criteria).
- Every artifact in the manifest has exactly one verdict in the VERIFICATION_LOG.md cohort entry; missing artifacts explicitly classified per failure taxonomy.
- Per-criterion verdicts grounded in worker output; main thread did NOT re-evaluate or override worker verdicts.
- Failure clustering computed: SYSTEMIC (>=50% failure rate) and LOCALIZED (<50%) buckets emitted.
- Workers received only their artifact and rubric inputs plus the artifact ID, output schema and selected-carrier delivery metadata; no task memory, sibling artifacts or prior conversation leaked into worker context.
- Workers returned typed payloads through the selected ADR-0158 carrier; schema-skip (free-form prose) classified as `interrupted` and listed in `### Command transcript`.
- Per-worker structured payloads persisted in `.wos/fleet-inbox/<run_id>/<worker_id>.json` for audit/replay.
- VERIFICATION_LOG.md has one cohort entry appended (never partial-merged with prior entries).
- **Orphan scanner (`scripts/scan-substrate-orphans.py`) exit code is 0 on VERIFICATION_LOG.md after the merge in Step 10.5 (ADR-0038 Rule 3 enforcement); non-zero exit blocks TASK_STATE.md update and routes to `state-reconcile`.**
- VERIFICATION_LOG.jsonl has one line per classification event + one per merged section (with `orphan_scan=passed`).
- Worker contract violations (mid-flight writes to VERIFICATION_LOG.md, sibling-artifact reads, schema-skip) explicitly listed in `### Command transcript`.
- Substrate peer rule respected: VERIFICATION_LOG.md is owned by this command in fleet mode (single-artifact `verify-against-rubric` retains co-ownership for append-only sequential entries; mixed-mode is reconciled by `state-reconcile`).
- Recommended remediation routing distinguishes SYSTEMIC (rubric or spec issue) from LOCALIZED (per-artifact fix) and routes accordingly.
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
J.10 orchestrator pilot. The independence of workers is the load-bearing property: if the orchestrator inadvertently leaks the cohort's running tally into a worker prompt (e.g., "5 of the previous artifacts failed criterion C3; check C3 carefully"), the Anthropic Outcomes +10pp uplift collapses into groupthink. Workers are stateless against each other AND against the parent. Failure clustering is the novel deliverable -- it's the difference between "you have 20 artifacts to fix" (low value) and "criterion C3 fails on 14 of 20 artifacts; the rubric or the upstream spec is the root cause" (high value). When the clustering surfaces SYSTEMIC issues, the recommended remediation routes UPSTREAM (rubric, spec, decision), not downstream (per-artifact patches that would compound). Per **ADR-0038** (Workflow tool as canonical parallel-orchestration primitive): Rule 1 binds workers to typed payloads through the ADR-0158 carrier (schema-skip is the 10/12 failure mode observed on 2026-06-05), Rule 2 keeps substrate writes sequential through the orchestrator's apply step, and Rule 3 binds the apply step to `scripts/scan-substrate-orphans.py` to prevent the **substrate-bullet-orphan** failure class (`wos/bug-classes/substrate-bullet-orphan.md`, bug class commit `615c6bb`, detector commit `5840755`) where bullets appended near section boundaries land between sections with no semantic parent. Step 10.5 is the load-bearing enforcement point -- it MUST run before TASK_STATE.md is updated, and a non-zero exit code MUST block the apply, route to `state-reconcile`, and surface the orphan offsets in `### Command transcript`.
