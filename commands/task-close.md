---
name: task-close
description: Perform the terminal task lifecycle transition for a finished task: verify the spec done-conditions, set TASK_STATE.md to its final closed state, and move the task folder from active/ to archive/. The symmetric counterpart to task-init and the only official way to close a whole task. Use when every slice is closed, the work is merged or explicitly waived, and the whole task is ending. Do not use when only a single slice is ending (use slice-closure), when implementation or review is still in progress, when the goal is only to assess progress (use where-we-at) or sync memory (use sync-task-state), or when a follow-up is really new scope (use task-init for a new task). Before archiving a long session, use harvest-session-learnings to sweep durable lessons. For picking the next thread after archiving, use portfolio-review.
metadata:
  category: execution-and-closure
  primary-cursor-mode: Agent
  multi-repo-aware: false
  context-layers-consumed: [memory]
  context-layers-produced: [memory]
  unconditional-loads: [wos/closure-floors.task-close.md]
  tools: [Read, Write, Edit, Bash, Glob, Grep]
  x-wos-profiles: [minimal, core, full]
  provenance: first-party
  suggested-model: claude-opus-5-5
---
# task-close

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
- **Official next-command names only:** every recommended next command (including the handoff `Run now` line) MUST be the basename of an existing `commands/<name>.md` file in this workflow repository. Never invent names. One exception: `Run now: none` with `Mode: N/A` declares the chain ended with no honest next step, defined under `### Official command names (routing integrity)` (ADR-0126); use it only then, never to end a chain that has a real next step.

Required inputs:
- active task folder path (`projects/<client>__<project>/active/YYYY-MM-DD_<task-slug>/`)
- TASK_STATE.md (current)
- IMPLEMENTATION_PLAN.md and SLICES/ closure status, if present
- evidence (or explicit user waiver) for each done-condition: implementation complete, review complete, team approval, merge into the target integration branch

Done-conditions gate (from the spec `## When a task moves to `done``):
1. implementation complete
2. review complete
3. team approval happened
4. merge into the target integration branch happened
5. `TASK_STATE.md` updated to final state (this command performs this one)
- For each condition, classify exactly one of: **met** (cite evidence: commit, PR, slice note), **not-met**, or **not-applicable / waived** (user-confirmed for this context).
- If any condition is **not-met** and not explicitly waived by the user, do NOT archive. Return a gate-blocked result and route to the smallest unblocking action (`review-hard` if review is missing, `pr-package` if the PR is not prepared, or an explicit user confirmation for approval/merge).
- **Condition 4 is checked, never auto-waived (ADR-0191).** WHERE an integration branch exists, ask whether the closed work is ON it: the cited commits are ancestors of that branch (`git merge-base --is-ancestor <commit> <branch>`). They are, and condition 4 is MET, on the direct-to-branch pattern as much as on a merged pull request; push is a separate act and this condition does not ask about it. WHERE no integration branch exists at all, the condition is not-applicable and says so.

**Solo/local auto-waiver (ADR-0191).** WHEN either route below holds THEN condition 3 (team approval) AND the knowledge-note topic/tag confirmation (see the Knowledge-layer note rule below) are AUTO-WAIVED and recorded verbatim in the final `TASK_STATE.md` as a solo-delivery auto-waiver.
  - **Route A, no infrastructure to approve through:** the product repo has no configured git remote AND the task folder is not tracked by the workflow repository. This is a purely local tree.
  - **Route B, the project declares solo governance:** its `CONTRIBUTING.md` (or equivalent governance file) states a single-maintainer model, for example BDFL or solo maintainer.
  WHEN neither route holds, fall back to requiring an explicit maintainer waiver recorded verbatim. Do NOT infer solo governance from the commit history. The auto-waiver NEVER covers the experience-verdict floor below nor the commit-evidence floor (uncommitted real work is still a bounded deferral, not auto-archived). The auto-waiver collapses only the team-approval and knowledge-note-confirmation ceremony.
- **Closure floors (lazy-loaded, UNCONDITIONAL).** Load `wos/closure-floors.task-close.md` and apply every floor in it exactly as written there; the task record SHALL cite which subsections were read and applied. The load is unconditional, not signature-gated: every floor below is evaluated on every task. The six, each with its trigger, its routing, and where the outcome is a recorded string rather than a route, that string:
  - **Commit-evidence floor** (ADR-0084, ADR-0100, ADR-0128, ADR-0133). Fires always, even when merge (condition 4) is waived. Satisfied by `commit-ref` or `ref-attested`. Routing has two branches and both are required: where a human turn is available it routes to `branch-commit --apply`, the only path in this repository that can create a commit; an unattended external execution layer SHALL route to `ref-attested` when its driver-owned-branch route is unavailable. Direct-use `autonomous-run` creates neither class and records `deferred: pending human commit (<one-line context>)`. On a no-VCS workspace, ask for archive-with-waiver instead.
  - **Experience-verdict floor** (ADR-0091). Fires WHEN the closure includes a deliverable tagged `user-facing-content` or `new-user-facing-surface`. Routes to the experience-verdict check. The `## Experience verdict` block carries a mandatory `Attested by:` line valued `run` or `human`; `run` is valid only when the block cites the evidence the run captured, and a green run is never recorded as `human` (ADR-0179). WHILE the Godot task signature is present this floor stands down in favor of the D-4 feel-verdict floor above.
  - **Entry-path probe floor** (ADR-0091). Fires WHEN the closure includes a deliverable tagged `new-user-facing-surface`. Routes the operator to run the real entry path once. WHILE the Godot task signature is present this floor stands down in favor of the D-4 feel-verdict floor above.
  - **Test-strategy consumption floor** (F-6, ADR-0089). Fires WHEN the task folder contains a `TEST_STRATEGY.md`. Routes to `implement-slice-complement`, or the waiver is recorded first.
  - **Integrity floor** (blocking). Fires always: run `bash scripts/verify-substrate-batch.sh <task-folder>`. A non-zero exit blocks the archive unless the final `TASK_STATE.md` records `integrity-waiver: N advisories unresolved (<one-line reason>)`, naming the failing validator(s). Resolve `scripts/verify-substrate-batch.sh` against the WORKFLOW ROOT (ADR-0224); when it is in neither, record `integrity: not checked (verify-substrate-batch not installed)`, neither a pass nor a waiver.
  - **Unresolved-revision floor** (ADR-0109, D-10). Fires WHEN `DECISIONS.md ## Decision history` holds a revision entry still marked `[OPEN]` (or `[OPEN: equal-rank, escalate]`). Routes to `decision-interview` or `direction-adjust`, or the entry is tagged `[WAIVED: <reason>]`.
- **Platform runtime floors (lazy-loaded).** WHEN the active task matches the Godot signature (a `project.godot` or `.gd` codebase, or `GODOT_SCENE_PLAN.md` / `GODOT_RUNTIME_VERIFY.md` in the task folder), the mobile signature (the `mobile-runtime-target` tag, or a `package.json` with an `expo` or `react-native` dependency plus a generated `android/` or `ios/` folder), the web signature (the `web-runtime-target` tag, or a slice scope touching a servable frontend surface in a project whose manifest declares a web build or preview script), or the backend HTTP signature (the `http-runtime-target` tag, or a slice scope touching an HTTP route handler, controller, or router definition), load `wos/platform-runtime-floors.md` and apply its **task-close variants** (whole-task backstops for Godot runtime-gate, Godot feel-verdict, Godot tier-declaration, mobile-runtime-gate, web-runtime-gate, backend-runtime-gate) exactly as written there; the task record SHALL cite which subsection was read and applied. Inert on a task with no platform signature.
- Multi-repo task: condition 4 must hold for every repository in scope before archiving; confirm each repo's merge (or waiver) explicitly.

Operating rules:
- Do not implement production code.
- **Handoff:** end with the adaptive `### Handoff` block per `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full).
- **Operating mode (ADR-0008, ADR-0162).** WHEN `TASK_STATE.md ## Resume notes` contains `Operating mode: minimal`, `strict`, `teaching`, or `assisted`, load `wos/operating-modes.md` and apply that mode. WHEN the line is absent, use this command's native rules. Auto-suggestion is not a declaration.
- This is a **whole-task** closure. If only a slice is ending, stop and route to `slice-closure` instead.
- Archive move: `active/YYYY-MM-DD_<slug>/` -> `archive/YYYY-MM-DD_<slug>/`, preserving the folder name. `archive/` is canonical; if the project already uses the legacy `done/` alias, keep using `done/` for consistency within that project.
- In every mode: perform the move with `git mv` when the folder is tracked (preserves history), otherwise `mv`; then write the final `TASK_STATE.md` (ADR-0199).
- **Per-task worktree teardown (opt-in, ADR-0074).** When `SOURCE_OF_TRUTH.md` has a `## Workspace` section (the task was worktree-isolated via `task-workspace`), tear the worktree down as part of closure. In **Agent** mode, first check the worktree is clean and the task branch is merged, then run `git worktree remove <worktree-path>` followed by `git worktree prune`. IF the worktree has uncommitted changes or the task branch is unmerged, halt the removal and surface the unclean state; do NOT pass `--force`. The done-conditions gate (condition 4, merge) governs whether the task archives; a halted teardown is reported for the user to resolve. When there is no `## Workspace` section, this is a no-op. In **Ask** or **Plan** mode, propose the `git worktree` commands without running them (ADR-0222).
- Idempotency and no-op: if the folder is already under `archive/` (or `done/`) and `TASK_STATE.md` is already final, return a short `NO_OP_TRACE`; do not re-move or rewrite.
- **Reopen mode (ADR-0105).** The symmetric reverse of this command's own move, used when a recorded closure waiver authorizes reopening or the user asks for it. Move the folder from `archive/` (or the legacy `done/`) back to `active/` with the same mechanism (`git mv` when tracked, otherwise `mv`), reset the final `TASK_STATE.md` fields via the canonical <!-- count:closure-pattern-sections -->5<!-- /count -->-section pattern in `commands/_shared/task-state-slice-closure-pattern.md` (phase back from closed to the resumed working phase, recommended next step pointing at the work that reopened it), and append exactly one OUTCOMES.jsonl `reopen` event, read under the same latest-event-wins rule as `revert` (per `templates/OUTCOMES.schema.md`). Like the archive move, the reverse move and its writes are `APPLIED` in every mode (ADR-0222).
- **Knowledge-layer note (ADR-0055, D-9/D-11):** when the gate decision is **archive**, write the note `projects/<client>__<project>/knowledge/<task-slug>.md` from `templates/knowledge-layer-entry.template.md` and its `knowledge/index.md` entry (from `templates/knowledge-index.template.md` if absent), per `wos/project-level-memory.md ## Human knowledge layer`. Write the deterministic links (`[[<task-slug>]]`, `[[index]]`, the task's `DECISIONS.md`) automatically; **propose** topic links and tags (from the task's tags, slice titles and decisions) for the human to confirm or edit, never inserting them silently, except that under the solo/local auto-waiver they are auto-accepted and recorded as auto-defaulted. Idempotent: no second note for the same slug. The note, its deterministic links and the index entry are `APPLIED` in every mode (ADR-0222); only the topic links wait on the confirmation. Never auto-read the `knowledge/` folder.
- **Outcome record (outcome ledger, per `templates/OUTCOMES.schema.md`):** when the gate decision is **archive**, append exactly one outcome line to `projects/<client>__<project>/OUTCOMES.jsonl` (create the file when absent). Produce and append the line with `python3 scripts/compute-task-outcome.py <task-folder> --merge-status <merged|waived|not-merged> --evidence "<condition-4 evidence or waiver text>" >> projects/<client>__<project>/OUTCOMES.jsonl` (the helper only prints; the `>>` is the append, so report `APPLIED` only once the line is in the file; ADR-0217), passing the verdict the done-conditions gate recorded. Pass `--usage-source <adapter>:<path>` when the harness keeps a usage record (ADR-0236); without one the tokens field is null. Resolve `scripts/compute-task-outcome.py` against the WORKFLOW ROOT (the clone, or the installed docs directory), never against the task repository; when it is in neither, name that in `### Command transcript` instead of reporting the append. The append is `APPLIED` in every mode (ADR-0222). The append NEVER blocks archiving: when the helper or the append fails, report the failure and proceed with the archive. A later revert of this task's merged work is recorded after the fact with the helper's `--revert` mode; the schema doc carries the read rules (latest event wins).
- Never delete artifacts. Closure preserves the full task record; archiving is a move, not a cleanup.
- The final `TASK_STATE.md` must set: `Current phase` to delivery/closed, `Current status` fully reflecting completion, any waivers recorded, and `Recommended next step` to either none (task closed) or the follow-up task to spin off via `task-init`.
- **Substrate write protocol (ADR-0034, ADR-0105).** The `## Closure record` H2 this command writes into the final `TASK_STATE.md` is owned by task-close and carries its own `wos:write` transaction header plus one `.wos/VERIFICATION_LOG.jsonl` line per `commands/_shared/substrate-write-protocol.md`. The final phase and status update goes through the canonical <!-- count:closure-pattern-sections -->5<!-- /count -->-section pattern in `commands/_shared/task-state-slice-closure-pattern.md`.
- If the closure surfaced a follow-up that is genuinely new scope, do not smuggle it into this task; name it and route to `task-init` for a fresh task.
- Do not reopen broad discovery, broad review, or signed-off contract issues.

Required output:
1. Task scope confirmation (whole task is closing, not just a slice)
2. Done-conditions checklist: each condition with verdict (met / not-met / waived) and evidence
3. Gate decision: **archive** or **blocked** (with the smallest unblocking action if blocked)
4. Exact archive move (`from` -> `to` path) and the mechanism (`git mv` or `mv`), or a `NO_OP_TRACE` note if already archived
5. Exact final `TASK_STATE.md` update block (or explicit `TASK_STATE: NO_CHANGE`)
6. Knowledge-layer note (ADR-0055): the created `knowledge/<task-slug>.md` note and the `knowledge/index.md` update (deterministic links written; proposed topic links presented for the human to confirm), or a `NO_OP_TRACE` note if a note for this task already exists; marked `APPLIED` in every mode (ADR-0222)
7. Outcome record: the exact OUTCOMES.jsonl line appended, or the reported append failure alongside the completed archive (never a blocked archive)
7a. **Unverified-floor report (D-20).** A `### Unverified floors` block listing every floor that recorded `unverified:` across the task's slices, one row per floor: the floor name, the slice it fired on, and the reason recorded verbatim. It is BUILT FROM the recorded lines in the slice notes, never re-derived. WHEN no floor recorded one, the block reads `none` rather than being omitted. This is the visible half of D-20: <!-- count:closure-floors-record -->9<!-- /count --> floors now record instead of refusing.
8. Learnings pass (ADR-0234), before the archive move. WHEN the task recorded a signal (a `needs_revision` or `ESCALATED` Approval-log line, a check shown failing before it passed, a fixed review finding, a refusal or stop, a revert or reopen, a de-scope, an `unverified:` line), apply the `harvest-session-learnings` contract to the task and append its entries to `LEARNINGS.md` (created from `templates/LEARNINGS.md` if absent), `source: task-close`. The pass may be NO_OP, never edits an entry, and lists cross-project lessons as `USER_MEMORY.md` pointers without writing it. With no signal, one transcript line: `Learnings: none harvested (no signal recorded)`.
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
Follow `## Global output contract` in `WORKFLOW_OPERATING_SYSTEM.md` for `APPLIED` / `PROPOSED` / `SKIP` rules. Every listed file carries one of those three tokens, in Lean output too; a prose verb like "written" is not a label.

### Command transcript
<!-- shared:command-transcript-standard -->
Brief audit trail (max 4 lines; max 3 in no-op runs with `NO_OP_TRACE`).

### Handoff
<!-- shared:handoff-body -->
Use the adaptive ending format of `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract`. Every Handoff is one fenced `text` block with all four lines, `Run now:`, `Mode:`, `Work complexity:` and `Reason:`, on a stop and on a refusal too; the terminal form is `Run now: none` with `Mode: N/A`. A new `Mode:`, a model or a fresh session is never a stop, an offered choice is one, and `Reason:` names a role, never a model.
### Deliverable reconcile (closure gate, per ADR-0056)
<!-- shared:deliverable-reconcile -->
**Deliverable reconcile (per ADR-0056).** Reconcile the task's `## Requested deliverables` ledger in `TASK_STATE.md` against the delivered work. The gate is lifecycle-aware: it hard-fails only when the run is finalizing the whole task, and reports without failing at a mid-task checkpoint.

1. Locate the ledger. Read `## Requested deliverables` in `TASK_STATE.md`. WHEN the section is absent (a legacy task that predates the ledger), OR its only row is the `- none named` sentinel (a brief that named no concrete deliverable), this gate is a no-op: skip it and proceed.

2. Classify the context. A finalization run is `task-close`, or `review-hard` run as the pre-PR final pass. A checkpoint run is `where-we-at` or `slice-closure` (and any `review-hard` run that is not the pre-PR final). At a checkpoint a row still tagged `in-scope` that is not yet done is normal remaining work, not a defect.

3. Define reconciled vs silent omission. A row is reconciled when it is `done` (in the delivered work) or `de-scoped:<reason>` with that reason recorded in `DECISIONS.md`. A deliverable named in the brief that has NO ledger row at all, or a row that was dropped without a recorded de-scope, is a silent omission. To detect the no-row case you MUST cross-check the ledger against the brief: read the task's `README.md` (which `task-init` seeds from the brief) and the original request when it is in conversation context, and confirm every deliverable named there has a `## Requested deliverables` row. WHEN no brief artifact is available to cross-check, reconcile the rows that exist and state in the output that ledger-vs-brief completeness could not be re-verified (do not claim it was).

4. Apply the gate by context.
   - WHEN finalizing: IF any row is unreconciled (still `in-scope`, or a silent omission per step 3), THEN this command's output is invalid. Name each unreconciled deliverable, state whether it should be delivered or de-scoped, and route to `implementation-plan` (plan the missing work) or `decision-interview` (a de-scope, which only the person's answer records). A provisional decision never de-scopes (ADR-0233): in an attended chain on a task branch the row stays `in-scope` and is listed as `Not delivered, needs you: <deliverable>: <what is undecided>` in `TASK_STATE.md ## Open questions / blockers`, and `task-close` still holds it unreconciled, while `review-hard`'s pre-PR pass only lists it.
   - WHILE at a checkpoint: report each not-yet-done `in-scope` row as remaining work and do NOT invalidate output on that basis. A silent omission (step 3) is NOT normal progress: name the missing deliverable, record it in the `TASK_STATE.md` checkpoint output as a must-address finding (never a bare one-line mention), and route it as the finalization branch does. Neither case invalidates the output at a checkpoint; that happens only when finalizing.

A de-scope is allowed; silence is not. This generalizes the repo-level "reject silent omission of any repo in `## Repositories`" completeness check from repositories to user-named deliverables.
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
- Closure floors: every floor in `wos/closure-floors.task-close.md`, and on a Godot-, mobile-, web- or backend-HTTP-signature task every task-close variant in `wos/platform-runtime-floors.md`, was applied as its own `On missing evidence:` line states, and the task record cites the subsections read. An unsatisfied floor that refuses (commit-evidence, integrity, unresolved-revision, Godot feel-verdict) makes the result **blocked**, not archived, routed as its gate bullet above says; a floor that records or reconciles writes its line, closure proceeds, and item 7a lists every `unverified:` line.
- On archive: exactly one `knowledge/<task-slug>.md` note and its `knowledge/index.md` entry (topic links human-confirmed, never silently inserted), marked `APPLIED` in every mode (ADR-0222); the `knowledge/` folder is never auto-read.
- Gate decision is exactly one of: **archive** or **blocked**; a blocked result names the smallest unblocking action and does NOT move the folder.
- On archive: the exact `from` -> `to` path and the move mechanism (`git mv` or `mv`) are stated; `### Artifact changes` marks the final `TASK_STATE.md` write and the move to `archive/` `APPLIED` in every mode (ADR-0199).
- Output ends with a complete `### Handoff` block per the adaptive format in `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract`.
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
Optimize for honest closure, scope discipline (whole task vs slice), a preserved task record, and a clean archive transition.
