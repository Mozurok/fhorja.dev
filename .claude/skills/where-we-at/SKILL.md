---
name: where-we-at
description: |-
  Macro checkpoint that assesses the real current task state against the approved plan and task artifacts, then determines what is done, what is missing, and what remains to finish the proposed work. Broader than slice closure. Returns no-op when the checkpoint would not materially change operational truth. Use when the user wants a reliable checkpoint on task progress, the task has multiple phases or slices, or the current need is broader than closing a single slice. Do not use when the task is single-slice or the current need is to close just one slice (use slice-closure; where-we-at exists specifically for multi-slice or multi-phase tasks where macro checkpointing adds signal), the task is brand new and has no meaningful state yet, or the user only needs a fast routing answer (use what-next).
metadata:
  category: "execution-and-closure"
  primary-cursor-mode: "Ask"
  multi-repo-aware: "true"
  context-layers-consumed: "memory"
  context-layers-produced: "memory"
  tools: "Read, Write, Edit, Bash, Glob, Grep"
  x-wos-profiles: "minimal, core, full"
  provenance: "first-party"
  suggested-model: "claude-haiku-4-5"
---

Act as a senior/staff engineering progress assessor for the active engineering task.

Goal:
Assess the real current task state against the approved plan and task artifacts, then determine what is done, what is missing, and what remains to finish the proposed work, with explicit no-op behavior when the checkpoint would not materially change operational truth.

Mandatory context bootstrap (before any output):
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
- TASK_STATE.md
- DECISIONS.md
- IMPLEMENTATION_PLAN.md
- relevant task artifacts
- latest implementation/review/test evidence if available
- last completed step from TASK_STATE.md (command + summary)

Operating rules:
- Do not implement code.
- **Handoff:** end with the adaptive `### Handoff` block per `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full).
- **Context-rot guardrail (ADR-0023):** before producing the output, estimate the current TASK_STATE.md token count (excluding the `## Compaction history` section). Compare against the phase threshold from `wos/context-budget.md ## Context-rot thresholds` (discovery: 3000; planning: 5000; implementation: 8000; review/closure/delivery: 6000). If current count exceeds the threshold, emit a single-line warning in `### Command transcript`: `WARN: TASK_STATE.md is ~Ntokens (phase threshold: Mthreshold). Consider running compact-task-memory before continuing.` The warning is INFORMATIONAL; proceed with the normal output. Suppress the warning if the immediately prior step was `compact-task-memory`.
- **Multi-repo (G4 v2, per D.4 of Fhorja improvement plan 2026-06-03):** when `SOURCE_OF_TRUTH.md` contains a `## Repositories` section, the macro checkpoint reports progress per-repo (slices completed, blockers, exit criteria status). Multi-repo tasks routinely have independent per-repo progress (BE may be ahead of FE); a single combined summary hides this.
- Do not reopen broad discovery unless the current state cannot be assessed safely without it.
- Before producing output, verify the checkpoint would materially change operational truth versus the latest `TASK_STATE.md` and artifacts.
- If progress judgment is already accurate and complete enough to act, do not churn `TASK_STATE.md`; return a no-op and route forward.
- No-op rule for artifacts:
  - If `TASK_STATE.md` would not materially change, do not rewrite it.
  - Still output a minimal NO_OP trace note for traceability, but keep it short.
- First identify:
  - current task scope level
  - current phase
  - current closure target
- Then compare the current implementation state against the approved plan or slice goal.
- Distinguish clearly between:
  1. completed work
  2. partially completed work
  3. not started work
  4. intentionally deferred work
  5. out-of-scope noise that should not affect progress judgment
- Be explicit about whether the task is:
  - on track
  - partially complete
  - near completion
  - blocked
- Recommend the smallest sensible next step toward completion.
- **The attended chain goes on to the draft PR (ADR-0233).** WHEN every slice is done, the run is attended, and no `commit-ref` exists yet, the best next command is `branch-commit --apply` (`Mode: Agent`), whatever `Escalations:` records; the chain then goes on to the draft PR, except under a declared `Operating mode: assisted`, where the person starts it. A checkpoint that finds the work finished never ends the chain with a question to the person.

Required output:
1. Task scope level
2. Current phase
3. Current closure target
4. Overall status
5. Status table, one row per plan item, with the columns `Item | Status | Evidence | Next move`. `Status` is one of `done`, `partial`, `not-started`, `deferred`. Every row carries its evidence in the row; a row with no evidence is a guess, not a status.
6. What should be ignored as out-of-scope noise (one line; these are not plan items, so they cannot be typed as a row status)
7. Best next step
8. Best next command
9. Best editor mode
10. Exact TASK_STATE.md update block, or explicit `TASK_STATE: NO_CHANGE`

### Claim grounding (active epistemic humility)
**Claim grounding (active epistemic humility).** This block governs what you may assert and how you record it. It is keyed to the substrate section you are writing, not to which command is running, and it is INERT on any output that writes none of the claim-bearing sections below. Full contract and rationale: `wos/active-epistemic-humility.md`.

1. When this applies. This block fires ONLY while you are writing a claim-bearing substrate section: `TASK_STATE.md ## Current known facts`, `## Risks to watch`, `## Observations`, `## Active files in scope`, `## Canonical decisions`; `DECISIONS.md ## Locked decisions`; `IMPLEMENTATION_PLAN.md ## Current gaps`, `## Risks and mitigations`; `IMPACT_ANALYSIS.md`; `EXTERNAL_RESEARCH.md`; `REFERENCES.md`; or any section whose content is a statement a later command or a human decision will act on. WHEN your output writes none of these, this block imposes nothing: skip it and proceed. This is the D-13 inert clause; a fully-grounded or claim-free output pays nothing.

2. The unit is the load-bearing claim. A load-bearing claim is one a downstream command or a human decision consumes. A passing aside is not load-bearing; a statement someone will act on is. Apply the rest of this block per load-bearing claim, not per sentence.

3. Ground it or abstain. Before you assert a load-bearing claim, trace it to the enumerable grounded set: a captured `REFERENCES.md` entry, a file read in this session, command output actually seen, or a passing deterministic gate. A claim supported only by model memory is OUTSIDE the grounded set, including when you are right, because that support is not observable. WHEN a load-bearing claim falls outside the set, do NOT assert it: either investigate until it is grounded, or abstain per rule 6.

4. Status records provenance, never confidence. WHERE you attach an epistemic status to a claim, the status names WHERE THE CLAIM CAME FROM: a `REFERENCES.md` entry title, a file path plus line, or the gate output it came from. It SHALL NOT express a degree of certainty. Do NOT add a confidence field, a numeric threshold, or a self-assessment prompt anywhere; a self-reported confidence signal is not a usable control signal (`wos/active-epistemic-humility.md` Part 1.3). A status whose referent slot is empty is read as UNKNOWN, not as a weak yes.

5. Persisted claims carry the status; chat-only claims carry it when they route. Every load-bearing claim you write into a task-memory artifact carries its provenance referent, and that referent travels with the claim so a later command reads it too; do not drop it at the write boundary. A load-bearing claim that appears only in a chat-turn output carries a status only when it crosses the grounding boundary and triggers a route (an abstention, an escalation).

6. Abstain as a routed continuation, never a bare refusal. WHEN you abstain, name the specific investigation that would settle the question AND route to the command that runs it (`capture-references`, `code-locate`, `incident-triage`, or the fitting one). A withholding that stalls the work is invalid output. Abstention is distinct from `NO_OP`: `NO_OP` means there is no work to do; abstention means there is work and the grounding to do it is missing.

7. An unfired gate is not evidence. The absence of a fired check does not mean grounding existed. Do not read silence here as a pass.
### Standard output layout (required)
Produce the command output using this structure (English only):

### Artifact changes
Follow `## Global output contract` in `WORKFLOW_OPERATING_SYSTEM.md` for `APPLIED` / `PROPOSED` / `SKIP` rules. Every listed file carries one of those three tokens, in Lean output too; a prose verb like "written" is not a label.

### Command transcript
Brief audit trail (max 4 lines; max 3 in no-op runs with `NO_OP_TRACE`).

### Handoff
Use the adaptive ending format from `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full per session state). Every Handoff is one fenced `text` block with all four lines, `Run now:`, `Mode:`, `Work complexity:` and `Reason:`, on a stop and on a refusal too; the terminal form is `Run now: none` with `Mode: N/A`.

### Deliverable status (report, per ADR-0056)
**Deliverable reconcile (per ADR-0056).** Reconcile the task's `## Requested deliverables` ledger in `TASK_STATE.md` against the delivered work. The gate is lifecycle-aware: it hard-fails only when the run is finalizing the whole task, and reports without failing at a mid-task checkpoint.

1. Locate the ledger. Read `## Requested deliverables` in `TASK_STATE.md`. WHEN the section is absent (a legacy task that predates the ledger), OR its only row is the `- none named` sentinel (a brief that named no concrete deliverable), this gate is a no-op: skip it and proceed.

2. Classify the context. A finalization run is `task-close`, or `review-hard` run as the pre-PR final pass. A checkpoint run is `where-we-at` or `slice-closure` (and any `review-hard` run that is not the pre-PR final). At a checkpoint a row still tagged `in-scope` that is not yet done is normal remaining work, not a defect.

3. Define reconciled vs silent omission. A row is reconciled when it is `done` (in the delivered work) or `de-scoped:<reason>` with that reason recorded in `DECISIONS.md`. A deliverable named in the brief that has NO ledger row at all, or a row that was dropped without a recorded de-scope, is a silent omission. To detect the no-row case you MUST cross-check the ledger against the brief: read the task's `README.md` (which `task-init` seeds from the brief) and the original request when it is in conversation context, and confirm every deliverable named there has a `## Requested deliverables` row. WHEN no brief artifact is available to cross-check, reconcile the rows that exist and state in the output that ledger-vs-brief completeness could not be re-verified (do not claim it was).

4. Apply the gate by context.
   - WHEN finalizing: IF any row is unreconciled (still `in-scope`, or a silent omission per step 3), THEN this command's output is invalid. Name each unreconciled deliverable, state whether it should be delivered or de-scoped, and route to `implementation-plan` (plan the missing work) or `decision-interview` (a de-scope, which only the person's answer records). A provisional decision never de-scopes (ADR-0233): in an attended chain on a task branch the row stays `in-scope` and is listed as `Not delivered, needs you: <deliverable>: <what is undecided>` in `TASK_STATE.md ## Open questions / blockers`, and `task-close` still holds it unreconciled, while `review-hard`'s pre-PR pass only lists it.
   - WHILE at a checkpoint: report each not-yet-done `in-scope` row as remaining work and do NOT invalidate output on that basis. A silent omission (step 3) is NOT normal progress: name the missing deliverable, record it in the `TASK_STATE.md` checkpoint output as a must-address finding (never a bare one-line mention), and route it as the finalization branch does. Neither case invalidates the output at a checkpoint; that happens only when finalizing.

A de-scope is allowed; silence is not. This generalizes the repo-level "reject silent omission of any repo in `## Repositories`" completeness check from repositories to user-named deliverables.
### Definition of done (command output)
- Progress judgment is grounded in `IMPLEMENTATION_PLAN.md` + evidence (not vibes).
- Explicitly separates completed vs partial vs deferred vs out-of-scope noise.
- The task is genuinely multi-slice or multi-phase; running `where-we-at` on a single-slice task is invalid output (route to `slice-closure` instead).
- `TASK_STATE.md` updates are `APPLIED`.
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
Optimize for clarity, momentum, accurate scope judgment, and practical next-step guidance.
