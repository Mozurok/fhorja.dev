---
name: task-close
description: |-
  Perform the terminal task lifecycle transition for a finished task: verify the spec done-conditions, set TASK_STATE.md to its final closed state, and move the task folder from active/ to archive/. The symmetric counterpart to task-init and the only official way to close a whole task. Use when every slice is closed, the work is merged or explicitly waived, and the whole task is ending. Do not use when only a single slice is ending (use slice-closure), when implementation or review is still in progress, when the goal is only to assess progress (use where-we-at) or sync memory (use sync-task-state), or when a follow-up is really new scope (use task-init for a new task). Before archiving a long session, use harvest-session-learnings to sweep durable lessons. For picking the next thread after archiving, use portfolio-review.
metadata:
  category: execution-and-closure
  primary-cursor-mode: Agent
  multi-repo-aware: false
  context-layers-consumed:
    - memory
  context-layers-produced:
    - memory
  unconditional-loads:
    - wos/closure-floors.task-close.md
  tools:
    - Read
    - Write
    - Edit
    - Bash
    - Glob
    - Grep
  x-wos-profiles:
    - minimal
    - core
    - full
  provenance: first-party
  suggested-model: claude-opus-4-7
---
> **Output contract, in brief.** This body is over the per-skill re-injection cap, so
> after a compaction the sections below are truncated away while this summary survives.
> They remain authoritative in full; re-read this file before emitting if you need them.
>
> - `Standard output layout (required)`: Produce the command output using this structure (English only):
> - `Artifact changes`: Follow `## Global output contract` in `WORKFLOW_OPERATING_SYSTEM.md` for `APPLIED` / `PROPOSED` / `SKIP` rules.
> - `Command transcript`: Brief audit trail (max 4 lines; max 3 in no-op runs with `NO_OP_TRACE`).
> - `Handoff`: Use the adaptive ending format from `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full per...
> - `Definition of done (command output)`: Done-conditions checklist is complete: each of the five conditions has a verdict (met / not-met / waived) with evidence or an expl...


Act as a senior/staff engineering workflow closure operator.

Goal:
Perform the terminal task lifecycle transition for a finished engineering task: verify the spec done-conditions, set `TASK_STATE.md` to its final closed state, and move the task folder from `active/` to `archive/`. This is the symmetric counterpart to `task-init` and the only official way to close a whole task.

This command is distinct from `slice-closure` (which closes a single slice and may route toward delivery) and from `where-we-at` (which only assesses progress). Use `task-close` exactly once per task, when the whole task is ending.

Mandatory context bootstrap (before any output):
- Read these sections in `WORKFLOW_OPERATING_SYSTEM.md` first:
  - `## LLM execution contract`
  - `## Editor mode policy` (mode definitions only; the tool mapping table is lazy-loaded in `wos/editor-mode-mappings.md` and needed only for non-Claude-Code tools)
  - `## Global output contract` (including **Adaptive handoff** and **Mode selection rule**)
  - `## Cross-cutting workflow guardrails`
- Read additional sections needed for closure:
  - `## When a task moves to `done`` and `## When a task stays in `active`` (the done-conditions gate)
  - `## Repository structure` (the `active/` vs `archive/` convention; `done/` is a legacy alias)
  - `## Project-level memory` (to keep project pointers valid after the move, and for the `knowledge/` folder write convention; full detail in `wos/project-level-memory.md`)
- Read the active task's memory:
  - `TASK_STATE.md` (current phase, last completed step, recommended next step, open blockers)
  - `IMPLEMENTATION_PLAN.md` and `SLICES/` closure status (every slice must be closed or explicitly deferred to a follow-up task)
  - `DECISIONS.md` (confirm no decision is still open)
  - `SOURCE_OF_TRUTH.md` `## Workspace` section, if present (the worktree path and task branch to tear down per ADR-0074)
- Read the `commands/` directory command inventory to ensure command names and availability are current.
- Align all routing recommendations and next-command suggestions with the current command set.
- **Official next-command names only:** every recommended next command (including the handoff `Run now` line) MUST be the basename of an existing `commands/<name>.md` file in this workflow repository. Never invent names (invalid: `task-archive`, `close-task`, `finish`).

Required inputs:
- active task folder path (`projects/<client>__<project>/active/YYYY-MM-DD_<task-slug>/`)
- TASK_STATE.md (current)
- IMPLEMENTATION_PLAN.md and SLICES/ closure status, if present
- evidence (or explicit user waiver) for each done-condition: implementation complete, review complete, team approval, merge into the target integration branch
- intended editor mode (Agent to actually move the folder and persist final state; Ask or Plan to dry-run the proposal without touching the filesystem)

Done-conditions gate (from the spec `## When a task moves to `done``):
1. implementation complete
2. review complete
3. team approval happened
4. merge into the target integration branch happened
5. `TASK_STATE.md` updated to final state (this command performs this one)
- For each condition, classify exactly one of: **met** (cite evidence: commit, PR, slice note), **not-met**, or **not-applicable / waived** (user-confirmed for this context).
- If any condition is **not-met** and not explicitly waived by the user, do NOT archive. Return a gate-blocked result and route to the smallest unblocking action (`review-hard` if review is missing, `pr-package` if the PR is not prepared, or an explicit user confirmation for approval/merge).
- **Solo/local auto-waiver (P0, D-2, 2026-07-18).** WHEN all three solo/local signals hold (the product repo has no configured git remote, there is no integration branch, and the task folder is not tracked by the workflow repository) THEN conditions 3 (team approval) and 4 (merge into integration branch) AND the knowledge-note topic/tag confirmation (see the Knowledge-layer note rule below) are AUTO-WAIVED and recorded verbatim in the final `TASK_STATE.md` as a solo-delivery auto-waiver, so a solo, local-only delivery does not stall on approvals that do not exist. This replaces the prior explicit-paste requirement for the solo case; WHEN any of the three signals is absent (a remote exists, an integration branch exists, or the folder is tracked), fall back to requiring an explicit maintainer waiver recorded verbatim. The auto-waiver NEVER covers the experience-verdict floor below (a `user-facing-content` / `new-user-facing-surface` deliverable still needs its recorded human PASS) nor the commit-evidence floor (uncommitted real work is still a bounded deferral, not auto-archived): it collapses only the team-approval, merge, and knowledge-note-confirmation ceremony.
- **Closure floors (lazy-loaded, UNCONDITIONAL; `wos/closure-floors.task-close.md`, per ADR-0134 and ADR-0138).** Load `wos/closure-floors.task-close.md` and apply every floor in it exactly as written there (a generated view: it already contains only this command's variants, and is rebuilt from the canonical floors file by `scripts/build-closure-floor-views.py`); the task record SHALL cite which subsections were read and applied (G3 safeguard: the lazy load never degrades into a paraphrase). The load is unconditional, not signature-gated: unlike the platform floors above, every floor below is evaluated on every task. The six, each with its trigger, its routing, and where the outcome is a recorded string rather than a route, that string:
  - **Commit-evidence floor** (ADR-0084, bounded deferral ADR-0100, no-VCS waiver ADR-0128, `ref-attested` route ADR-0133). Fires always, even when merge (condition 4) is waived. Satisfied by `commit-ref` or `ref-attested`. Routing has two branches and both are required: where a human turn is available it routes to `branch-commit --apply`, the only path in this repository that can create a commit; an unattended run SHALL route to `ref-attested`, the only one of the two it can reach. On a no-VCS workspace, ask for archive-with-waiver instead. Real work with neither class is a bounded deferral recorded verbatim as `deferred: pending human commit (<one-line context>)`.
  - **Experience-verdict floor** (ADR-0091). Fires WHEN the closure includes a deliverable tagged `user-facing-content` or `new-user-facing-surface`. Routes to the experience-verdict check; machine-green evidence SHALL NOT substitute for the human verdict. WHILE the Godot task signature is present this floor stands down in favor of the D-4 feel-verdict floor above.
  - **Entry-path probe floor** (ADR-0091). Fires WHEN the closure includes a deliverable tagged `new-user-facing-surface`. Routes the operator to run the real entry path once. WHILE the Godot task signature is present this floor stands down in favor of the D-4 feel-verdict floor above.
  - **Test-strategy consumption floor** (F-6, ADR-0089). Fires WHEN the task folder contains a `TEST_STRATEGY.md`. Routes to `implement-slice-complement`, or the waiver is recorded first.
  - **Integrity floor** (blocking; v3 wave3 item S1). Fires always: run `bash scripts/verify-substrate-batch.sh <task-folder>`. A non-zero exit blocks the archive unless the final `TASK_STATE.md` records `integrity-waiver: N advisories unresolved (<one-line reason>)`, naming the failing validator(s).
  - **Unresolved-revision floor** (ADR-0109, D-10). Fires WHEN `DECISIONS.md ## Decision history` holds a revision entry still marked `[OPEN]` (or `[OPEN: equal-rank, escalate]`). Routes to `decision-interview` or `direction-adjust`, or the entry is tagged `[WAIVED: <reason>]`.
- **Platform runtime floors (lazy-loaded; ADR-0085, ADR-0089, ADR-0106, ADR-0127).** WHEN the active task matches the Godot signature (a `project.godot` or `.gd` codebase, or `GODOT_SCENE_PLAN.md` / `GODOT_RUNTIME_VERIFY.md` in the task folder), the mobile signature (the `mobile-runtime-target` tag, or a `package.json` with an `expo` or `react-native` dependency plus a generated `android/` or `ios/` folder), the web signature (the `web-runtime-target` tag, or a slice scope touching a servable frontend surface in a project whose manifest declares a web build or preview script), or the backend HTTP signature (the `http-runtime-target` tag, or a slice scope touching an HTTP route handler, controller, or router definition), load `wos/platform-runtime-floors.md` and apply its **task-close variants** (whole-task backstops for Godot runtime-gate, Godot feel-verdict, Godot tier-declaration, mobile-runtime-gate, web-runtime-gate, backend-runtime-gate) exactly as written there; the task record SHALL cite which subsection was read and applied (G3 safeguard: the lazy load never degrades into a paraphrase). Inert on a task with no platform signature. The generalized closure floors in this file are unaffected.
- Multi-repo task: condition 4 must hold for every repository in scope before archiving; confirm each repo's merge (or waiver) explicitly.

Operating rules:
- Do not implement production code.
- **Handoff:** end with the adaptive `### Handoff` block per `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full).
- This is a **whole-task** closure. If only a slice is ending, stop and route to `slice-closure` instead.
- Archive move: `active/YYYY-MM-DD_<slug>/` -> `archive/YYYY-MM-DD_<slug>/`, preserving the folder name. `archive/` is canonical; if the project already uses the legacy `done/` alias, keep using `done/` for consistency within that project.
- In **Agent** mode: perform the move with `git mv` when the folder is tracked (preserves history), otherwise `mv`; then write the final `TASK_STATE.md`. In **Ask** or **Plan** mode: propose the move and the final state as `PROPOSED`; do not execute.
- **Per-task worktree teardown (opt-in, per ADR-0074 D-5/D-6).** When `SOURCE_OF_TRUTH.md` has a `## Workspace` section (the task was worktree-isolated via `task-workspace`), tear the worktree down as part of closure. In **Agent** mode, first check the worktree is clean and the task branch is merged, then run `git worktree remove <worktree-path>` followed by `git worktree prune`. IF the worktree has uncommitted changes or the task branch is unmerged, halt the removal and surface the unclean state; do NOT pass `--force`. The done-conditions gate (condition 4, merge) governs whether the task archives; a halted teardown is reported so the user resolves the worktree, and removal is never silently forced. When there is no `## Workspace` section, this is a no-op. In **Ask** or **Plan** mode, propose the `git worktree` commands without running them.
- Idempotency and no-op: if the folder is already under `archive/` (or `done/`) and `TASK_STATE.md` is already final, return a short `NO_OP_TRACE`; do not re-move or rewrite.
- **Reopen mode (ADR-0105).** The symmetric reverse of this command's own move, used when a recorded closure waiver authorizes reopening or the user asks for it. Move the folder from `archive/` (or the legacy `done/`) back to `active/` with the same mechanism (`git mv` when tracked, otherwise `mv`), reset the final `TASK_STATE.md` fields via the canonical 5-section pattern in `commands/_shared/task-state-slice-closure-pattern.md` (phase back from closed to the resumed working phase, recommended next step pointing at the work that reopened it), and append exactly one OUTCOMES.jsonl `reopen` event, read under the same latest-event-wins rule as `revert` (per `templates/OUTCOMES.schema.md`). In Ask or Plan mode propose the reverse move and updates as `PROPOSED` without executing.
- **Knowledge-layer note (ADR-0055, D-9/D-11):** when the gate decision is **archive**, write to the project's `knowledge/` folder. Create one note `projects/<client>__<project>/knowledge/<task-slug>.md` from `templates/knowledge-layer-entry.template.md` (what the task did, the learnings that mattered, what changed in the product or system; target 120 to 220 words of body), and update `projects/<client>__<project>/knowledge/index.md` (create it from `templates/knowledge-index.template.md` if absent) with a wikilink to the new note under By date and under its confirmed topics. Write the **deterministic links automatically**: `[[<task-slug>]]` (the task), `[[index]]`, and the task's `DECISIONS.md`. **Propose** candidate topic links and tags (derived from the task's tags, slice titles, and decisions) and let the human confirm or edit them before writing; never insert unverified topic links silently. Under the solo/local auto-waiver (in the done-conditions gate above) the proposed topics and tags are auto-accepted (recorded as auto-defaulted in the note) rather than blocking on human confirmation. **Idempotent:** if a note for this task slug already exists, do not create a second one. This is the only write to the `knowledge/` folder, and there is no per-slice write. In Agent mode it is `APPLIED`; in Ask or Plan mode propose it as `PROPOSED`. Never auto-read the `knowledge/` folder here or anywhere; it is human-read only, re-entered into AI context only by explicit human paste.
- **Outcome record (outcome ledger, per `templates/OUTCOMES.schema.md`):** when the gate decision is **archive**, append exactly one outcome line to `projects/<client>__<project>/OUTCOMES.jsonl` (create the file when absent). Produce the line with `python3 scripts/compute-task-outcome.py <task-folder> --merge-status <merged|waived|not-merged> --evidence "<condition-4 evidence or waiver text>"`, passing the verdict the done-conditions gate recorded. In **Agent** mode the append is `APPLIED`; in Ask or Plan mode show the produced line as `PROPOSED` without appending. The append NEVER blocks archiving: when the helper or the append fails, report the failure and proceed with the archive (the ledger records outcomes; it is not a gate). A later revert of this task's merged work is recorded after the fact with the helper's `--revert` mode; the schema doc carries the read rules (latest event wins).
- Never delete artifacts. Closure preserves the full task record; archiving is a move, not a cleanup.
- The final `TASK_STATE.md` must set: `Current phase` to delivery/closed, `Current status` fully reflecting completion, any waivers recorded, and `Recommended next step` to either none (task closed) or the follow-up task to spin off via `task-init`.
- **Substrate write protocol (per ADR-0034, K.2; terminal writes per ADR-0105).** The `## Closure record` H2 this command writes into the final `TASK_STATE.md` is owned by task-close (matrix row per ADR-0105) and carries its own `wos:write` transaction header plus one `.wos/VERIFICATION_LOG.jsonl` line per `commands/_shared/substrate-write-protocol.md`. The final phase and status update goes through the canonical 5-section pattern in `commands/_shared/task-state-slice-closure-pattern.md`.
- If the closure surfaced a follow-up that is genuinely new scope, do not smuggle it into this task; name it and route to `task-init` for a fresh task.
- Do not reopen broad discovery, broad review, or signed-off contract issues.

Required output:
1. Task scope confirmation (whole task is closing, not just a slice)
2. Done-conditions checklist: each condition with verdict (met / not-met / waived) and evidence
3. Gate decision: **archive** or **blocked** (with the smallest unblocking action if blocked)
4. Exact archive move (`from` -> `to` path) and the mechanism (`git mv` or `mv`), or a `NO_OP_TRACE` note if already archived
5. Exact final `TASK_STATE.md` update block (or explicit `TASK_STATE: NO_CHANGE`)
6. Knowledge-layer note (ADR-0055): the created `knowledge/<task-slug>.md` note and the `knowledge/index.md` update (deterministic links written; proposed topic links presented for the human to confirm), or a `NO_OP_TRACE` note if a note for this task already exists; marked `APPLIED` in Agent mode or `PROPOSED` otherwise
7. Outcome record: the exact OUTCOMES.jsonl line appended (or shown as `PROPOSED` in Ask or Plan mode), or the reported append failure alongside the completed archive (never a blocked archive)
8. Optional `### Learnings` section (ADR-0017): emit only when the task involved a failed attempt, a surprising blocker, or a non-obvious finding worth recording. Append a 4-bullet entry to `LEARNINGS.md` (create from `templates/LEARNINGS.md` if absent): `Tried:`, `Failed because:`, `Next time:`, `Cross-project promotion: no`. Skip entirely for a routine close.
9. Best next command (often `delivery-asset` or `pr-package` if delivery framing is still pending, `task-init` for a spun-off follow-up, `postmortem-author` when the task was incident-driven and a standalone blameless postmortem is not yet written, or none when the task is fully done)
10. Best editor mode
11. What should not be reopened now

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
Follow `## Global output contract` in `WORKFLOW_OPERATING_SYSTEM.md` for `APPLIED` / `PROPOSED` / `SKIP` rules.

### Command transcript
<!-- shared:command-transcript-standard -->
Brief audit trail (max 4 lines; max 3 in no-op runs with `NO_OP_TRACE`).

### Handoff
<!-- shared:handoff-body -->
Use the adaptive ending format from `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full per session state).

### Deliverable reconcile (closure gate, per ADR-0056)
<!-- shared:deliverable-reconcile -->
**Deliverable reconcile (per ADR-0056).** Reconcile the task's `## Requested deliverables` ledger in `TASK_STATE.md` against the delivered work. The gate is lifecycle-aware: it hard-fails only when the run is finalizing the whole task, and reports without failing at a mid-task checkpoint.

1. Locate the ledger. Read `## Requested deliverables` in `TASK_STATE.md`. WHEN the section is absent (a legacy task that predates the ledger), OR its only row is the `- none named` sentinel (a brief that named no concrete deliverable), this gate is a no-op: skip it and proceed.

2. Classify the context. A finalization run is `task-close`, or `review-hard` run as the pre-PR final pass. A checkpoint run is `where-we-at` or `slice-closure` (and any `review-hard` run that is not the pre-PR final). At a checkpoint a row still tagged `in-scope` that is not yet done is normal remaining work, not a defect.

3. Define reconciled vs silent omission. A row is reconciled when it is `done` (in the delivered work) or `de-scoped:<reason>` with that reason recorded in `DECISIONS.md`. A deliverable named in the brief that has NO ledger row at all, or a row that was dropped without a recorded de-scope, is a silent omission. To detect the no-row case you MUST cross-check the ledger against the brief: read the task's `README.md` (which `task-init` seeds from the brief) and the original request when it is in conversation context, and confirm every deliverable named there has a `## Requested deliverables` row. A named deliverable with no row means the ledger was seeded incompletely at `task-init`, and it is a silent omission. WHEN no brief artifact is available to cross-check, reconcile the rows that exist and state in the output that ledger-vs-brief completeness could not be re-verified (do not claim it was).

4. Apply the gate by context.
   - WHEN finalizing: IF any row is unreconciled (still `in-scope`, or a silent omission per step 3), THEN this command's output is invalid. Name each unreconciled deliverable, state whether it should be delivered or de-scoped, and route to `decision-interview` (record a de-scope) or `implementation-plan` (plan the missing work).
   - WHILE at a checkpoint: report each not-yet-done `in-scope` row as remaining work and do NOT invalidate output on that basis. A silent omission (step 3) is NOT normal progress: name the missing deliverable, record it in the `TASK_STATE.md` checkpoint output as a must-address finding, and route it to `decision-interview` (to record a de-scope) or `implementation-plan` (to seed and plan the missing deliverable), the same repair routing as the finalization branch. At a checkpoint neither case invalidates the whole output: an in-scope-not-yet-done row is reported as remaining work, and a silent omission is named and routed as a must-address finding (never a bare one-line mention). Output invalidation for an unreconciled row happens only in the finalization branch.

A de-scope is allowed; silence is not. This generalizes the repo-level "reject silent omission of any repo in `## Repositories`" completeness check from repositories to user-named deliverables. The ledger is seeded at `task-init` and pointer-linked from `SOURCE_OF_TRUTH.md`.
### References status (finalization gate, X2)
Dedup: WHEN this same closure already carries a review-hard References status verdict (the pre-PR final pass), cite that recorded verdict here instead of re-running the reconcile.
<!-- shared:references-reconcile -->
**References reconcile (X2, 2026-07-18).** Reconcile the references a task cited (its `REFERENCES.md` deliverable, an `EXTERNAL_RESEARCH.md`, or the project-level references it grounded in) against what the task actually shipped, enforcing "cite only what you used." Lifecycle-aware: it reports at a mid-task checkpoint and hard-fails only when finalizing the whole task.

1. Gate on presence. This sub-check fires only WHEN the task produced or cited references: a `REFERENCES.md` or `EXTERNAL_RESEARCH.md` in the task folder, or a `Grounded in:` citation in the shipped work. WHEN none is present, it is a no-op: skip and proceed.

2. Classify the context. A finalization run is `task-close` (or `review-hard` as the pre-PR final pass). A checkpoint run is `slice-closure` or `where-we-at`. At a checkpoint a cited reference not yet reflected is normal in-progress work, not a defect.

3. Reconcile cited vs reflected. For each reference the task cited, confirm the shipped work materially reflects it (a real layout, behavior, or decision traceable to that reference), not merely a name-drop. A reference cited with no material trace in the shipped work is a cited-but-unused reference: this is the failure the brief names ("if the final result does not reflect the references you cited, the REFERENCES.md is wrong").

4. Apply the gate by context.
   - WHEN finalizing: IF any cited reference is unused (no material trace) THEN name it and require either removing the citation or pointing to where it is reflected, and route to `implement-slice-complement` (fix the citation) before closing.
   - WHILE at a checkpoint: report each cited-but-unused reference as a must-address finding (name it, route to `implement-slice-complement`), and do NOT invalidate the whole output on that basis.

"Cite only what you used" is the invariant. This is the produce-side gate for the `capture-references` and `external-research` artifacts, the design-and-research analog of the deliverable-reconcile completeness check.
### Definition of done (command output)
- Done-conditions checklist is complete: each of the five conditions has a verdict (met / not-met / waived) with evidence or an explicit user waiver.
- Commit-evidence floor (ADR-0084, ADR-0100): closure cites a commit reference covering the closed work, or records an explicit waiver covering only genuinely discardable work, or the user explicitly authorized an archive-with-waiver naming the preserved uncommitted work; real work pending a human commit is a bounded deferral that keeps the task open, and a task with none of these is **blocked** (not archived) and routed to `branch-commit --apply`.
- Platform runtime floors (lazy; ADR-0085, ADR-0089, ADR-0106, ADR-0127): on a Godot-, mobile-, web-, or backend-HTTP-signature task, the task-close variants in `wos/platform-runtime-floors.md` were applied and the task record cites which subsection was read; a task failing a floor is blocked (not archived) and routed per that file. Inert on tasks with no platform signature.
- Experience gates (generalized, ADR-0091): a task with a deliverable tagged `user-facing-content` or `new-user-facing-surface` is **blocked** (not archived) without a cited `## Experience verdict` PASS, and a `new-user-facing-surface` deliverable is **blocked** without a cited entry-path run, in each case unless an explicit skip reason is recorded; stands down on the Godot signature in favor of the D-4 floor above.
- Test-strategy consumption floor (F-6, ADR-0089): when a `TEST_STRATEGY.md` exists, every `critical` and `regression` row maps to a cited test file or a recorded waiver; a task with a silently orphaned row is **blocked** (not archived) and routed to `implement-slice-complement` or the waiver record. No-op without a `TEST_STRATEGY.md`.
- Integrity floor (v3 wave3, S1): verify-substrate-batch ran and exited 0 on the task folder, or the explicit integrity-waiver line with a reason is in the final TASK_STATE.md; a silent non-zero archive is invalid output.
- Unresolved-revision floor (ADR-0109, D-10): no `DECISIONS.md ## Decision history` entry remains marked `[OPEN]`; a remaining one **blocks** (not archived) and routes to `decision-interview` or `direction-adjust`, or carries `[WAIVED: <reason>]`.
- Gate decision is exactly one of: **archive** or **blocked**; a blocked result names the smallest unblocking action and does NOT move the folder.
- On archive: the exact `from` -> `to` path and the move mechanism (`git mv` or `mv`) are stated; `### Artifact changes` marks the move and final `TASK_STATE.md` write as `APPLIED` only when actually persisting in Agent mode, otherwise `PROPOSED`.
- On archive: exactly one `knowledge/<task-slug>.md` note is created and `knowledge/index.md` updated (idempotent; deterministic links written automatically; topic links proposed and human-confirmed, never silently inserted), marked `APPLIED` in Agent mode or `PROPOSED` otherwise; the `knowledge/` folder is never auto-read.
- On archive: exactly one outcome line is appended to the project's OUTCOMES.jsonl per `templates/OUTCOMES.schema.md` (`APPLIED` in Agent mode, `PROPOSED` otherwise), and a helper or append failure is reported without blocking the archive.
- No artifacts are deleted; closure is a move that preserves the full task record.
- Per-task worktree teardown (ADR-0074): when `SOURCE_OF_TRUTH.md` has a `## Workspace` section, the worktree is removed and pruned in Agent mode, OR the removal is halted and surfaced when the tree is unclean or unmerged (never `--force`); when there is no `## Workspace` section, teardown is a no-op.
- If already archived with final state, the run returns a short `NO_OP_TRACE` instead of re-moving.
- Output ends with a complete `### Handoff` block per the adaptive format in `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract`.
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
Optimize for honest closure, scope discipline (whole task vs slice), a preserved task record, and a clean archive transition.
