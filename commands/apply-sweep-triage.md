---
name: apply-sweep-triage
description: Persist the user's triage decisions (apply, decline, discuss) from a SWEEP snapshot into REVIEW_PREFERENCES.md so future sweeps suppress declined findings and track applied fixes. Use after the user has edited the triage values in a SWEEP snapshot file produced by repo-consistency-sweep. Do not use when no sweep snapshot exists or when the user has not yet set triage values.
metadata:
  category: execution-and-closure
  primary-cursor-mode: Agent
  multi-repo-aware: false
  context-layers-consumed: [memory]
  context-layers-produced: [memory]
  tools: [Read, Write, Edit, Bash, Glob, Grep]
  x-wos-profiles: [core, full]
  provenance: first-party
  token-budget: 1200
  suggested-model: claude-sonnet-4-6
---
# apply-sweep-triage

Act as a workflow state updater that persists review-sweep triage decisions into project-level preferences.

Goal:
Read a SWEEP snapshot where the user has set `triage:` values (apply, decline, discuss) on each finding, and persist those decisions into `REVIEW_PREFERENCES.md` at the project level so future `repo-consistency-sweep` runs respect them.

Mandatory context bootstrap (before any output):
<!-- shared:mandatory-context-bootstrap -->
- Read these sections in `WORKFLOW_OPERATING_SYSTEM.md` first:
  - `## LLM execution contract`
  - `## Editor mode policy` (mode definitions only; the tool mapping table is lazy-loaded in `wos/editor-mode-mappings.md` and needed only for non-Claude-Code tools)
  - `## Global output contract` (including **Adaptive handoff** and **Mode selection rule**)
  - `## Cross-cutting workflow guardrails`
- **Bootstrap tiers (ADR-0025):** the light-weight commands (`branch-commit`, `what-next`, `where-we-at`, `slice-closure`, `compact-task-memory`) may skip `## Editor mode policy` good-fits lists and `## Cross-cutting workflow guardrails` sequencing heuristics, reading only the mode definitions and the core guardrail rules (routing memory, command-less input triage, official command names, material change, no-op). This reduces bootstrap from ~6,750 to ~3,500 tokens for these commands. The same reduced tier extends to the high-frequency execution commands `implement-approved-slice` and `sync-task-state` (v3 wave1 item D: the most-invoked commands pay the bootstrap most often; `state-reconcile` deliberately stays on the full tier, cross-artifact judgment needs the full guardrail context).
- **Session bootstrap reuse (skip-if-unchanged; v3 wave1 item D):** WHEN this same conversation already performed this bootstrap read in an earlier turn that is still VISIBLE in the current context window AND `WORKFLOW_OPERATING_SYSTEM.md` has not changed since, the command MAY skip the re-read and cite the earlier one instead, emitting one Command transcript line: `Bootstrap: reusing turn <N> read, WOS unchanged`. Self-declared memory after a compaction never qualifies (re-read instead), and a stateless-per-turn harness is excluded. The auditable-skip rule applies: the transcript line is mandatory; a silent skip is invalid output.
- Read additional sections only when relevant to this command's role.
- Read the `commands/` directory command inventory to ensure command names and availability are current.
- Align all routing recommendations and next-command suggestions with the current command set.
- **Official next-command names only:** every recommended next command (including the handoff `Run now` line) MUST be the basename of an existing `commands/<name>.md` file in this workflow repository. Never invent names.

Required inputs:
- active task folder path
- SWEEP snapshot path (or pointer from TASK_STATE.md under `## Latest sweep`)
- optional: REVIEW_PREFERENCES.md path (if not present, created from template)

Task repository files to update:
- REVIEW_PREFERENCES.md (create from `templates/REVIEW_PREFERENCES.template.md` if absent; append rows)
- TASK_STATE.md (update last completed step)

Operating rules:
- **Handoff:** end with the adaptive `### Handoff` block per `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full).
- **Step 1: Locate snapshot.** Read the SWEEP snapshot path from inputs or from TASK_STATE.md `## Latest sweep` pointer.
- **Step 2: Parse findings.** Extract each finding block from the snapshot. For each, read: bug_class, file_path, triage value (apply, decline, discuss, or unset).
- **Step 3: Skip unset.** Findings with `triage: unset` are skipped (user has not decided yet). If ALL findings are unset, return no-op.
- **Step 4: Compute file hashes.** For each triaged finding, run `git hash-object <file_path>` to capture the current file hash. This hash anchors the suppression: when the file changes, the declined entry ages out.
- **Step 5: Persist decisions.** Open or create REVIEW_PREFERENCES.md:
  - For `decline`: append a row to the `## Declined findings` table with date, bug_class, file_path, file_hash, and the user's reason (from the `reason:` line in the snapshot, or "no reason given" if absent).
  - For `apply`: append a row to the `## Applied findings` table with date, bug_class, file_path, and action_taken (from the `action:` line in the snapshot, or "acknowledged" if absent).
  - For `discuss`: append a row to the `## Discussed findings` table with date, bug_class, file_path, and the user's note (from the `note:` line in the snapshot, or empty).
- **Step 6: Deduplicate.** Before appending, check if an identical row (same bug_class + file_path) already exists in the target table. If yes, update the existing row's date, file_hash, and reason instead of appending a duplicate.
- **Step 7: Update TASK_STATE.** Set last completed step to this command with a summary of how many decisions were persisted (N declined, M applied, K discussed).
- Do not modify the SWEEP snapshot file itself (it is a read-only historical record).
- Do not implement code fixes. Persistence only.

Required output:
1. Summary: how many findings triaged (N declined, M applied, K discussed, J skipped as unset)
2. Rows added or updated in REVIEW_PREFERENCES.md
3. TASK_STATE.md update
4. Recommended next command

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
Follow `## Global output contract` in `WORKFLOW_OPERATING_SYSTEM.md` for `APPLIED` / `PROPOSED` / `SKIP` rules.

### Command transcript
<!-- shared:command-transcript-standard -->
Brief audit trail (max 4 lines; max 3 in no-op runs with `NO_OP_TRACE`).

### Handoff
<!-- shared:handoff-body -->
Use the adaptive ending format from `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full per session state).

### Definition of done (command output)
- All triaged findings (non-unset) are persisted into REVIEW_PREFERENCES.md.
- Declined rows include file_hash for suppression aging.
- No duplicate rows (deduplication by bug_class + file_path).
- TASK_STATE.md updated with triage summary.
- SWEEP snapshot is read-only (not modified).
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
Accurate persistence. Every triaged finding maps to exactly one row in REVIEW_PREFERENCES.md. No data loss, no silent overwrites.

<!-- cache-breakpoint -->
