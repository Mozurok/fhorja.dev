---
name: slice-closure
description: |-
  Decide whether the current slice is ready to close, distinguishing slice completion from full task completion, then persist the result in slice notes and TASK_STATE.md as explicit reviewable closure notes. For single-slice tasks may route directly to delivery. Returns no-op when slice memory would not materially change. Use when a slice was just implemented, slice-level validation was completed or reviewed, or the next decision is whether this slice can be closed cleanly. Do not use when no concrete slice implementation happened yet, the task is still in broad planning or contract work, or the goal is to understand overall task progress (use where-we-at). Before closing a long session, use harvest-session-learnings to capture durable lessons.
metadata:
  category: "execution-and-closure"
  primary-cursor-mode: "Ask"
  multi-repo-aware: "true"
  context-layers-consumed: "memory"
  context-layers-produced: "memory"
  unconditional-loads: "wos/closure-floors.slice-closure.md"
  tools: "Read, Write, Edit, Bash, Glob, Grep"
  x-wos-profiles: "minimal, core, full"
  provenance: "first-party"
  suggested-model: "claude-haiku-4-5"
---
> **Output contract, in brief.** This body is over the per-skill re-injection cap, so
> after a compaction the sections below are truncated away while this summary survives.
> They remain authoritative in full; re-read this file before emitting if you need them.
>
> - `Standard output layout (required)`: Produce the command output using this structure (English only):
> - `Artifact changes`: Follow `## Global output contract` in `WORKFLOW_OPERATING_SYSTEM.md` for `APPLIED` / `PROPOSED` / `SKIP` rules. Every listed file...
> - `Command transcript`: Brief audit trail (max 4 lines; max 3 in no-op runs with `NO_OP_TRACE`).
> - `Handoff`: Use the adaptive ending format from `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full per...
> - `Definition of done (command output)`: Closure status is exactly one of: ready / ready-with-followups / not-ready, with evidence.


Act as a senior/staff engineering slice-closure reviewer for the active engineering task.

Goal:
Decide whether the current slice is ready to close, without confusing slice completion with full task completion, then persist the result in the task repository as explicit, reviewable closure notes.

Note: this command is **opt-in for LOW and MEDIUM complexity slices**. Use `slice-closure` when: work complexity is HIGH, exit criteria require manual verification beyond typecheck, or the slice has follow-ups that need explicit tracking.

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
- IMPLEMENTATION_PLAN.md
- current slice artifact, if present
- latest implementation outputs
- latest validation/test results, if available
- relevant real codebase context
- last completed step from TASK_STATE.md (command + summary)

Operating rules:
- **Closure scope boundary.** Do not implement code. Never open another command's SKILL or command body from inside this run; never create or edit another slice's SLICES file; never emit a substrate write with an owner other than slice-closure (or its documented co-writer role); inherited chain authorization ("run the handoff commands without stopping") ends at this run's Handoff: the next command appears ONLY on the `Run now:` line, never executed inline.
- **Slice-note fill, never rewrite.** WHEN the closing slice has a skeleton note with `Status: in progress` (born under the slice-note-first floor in `implement-approved-slice`), this command FILLS that same file via Edit: files touched, what changed, what was intentionally not changed, validation, residual risks, preserving the skeleton's Goal, Scope and Complexity; a scope change is recorded as an explicit revision line, never a silent overwrite.
- **Handoff:** end with the adaptive `### Handoff` block per `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full).
- **Operating mode (ADR-0008, ADR-0162).** WHEN `TASK_STATE.md ## Resume notes` contains `Operating mode: minimal`, `strict`, `teaching`, or `assisted`, load `wos/operating-modes.md` and apply that mode. WHEN the line is absent, use this command's native rules. Auto-suggestion is not a declaration.
- **Substrate write protocol (ADR-0034).** MANDATORY for every write to a substrate section this command owns or co-writes (per `wos/substrate-peers.md`; slice-closure writes the canonical 5 sections per `commands/_shared/task-state-slice-closure-pattern.md`). Per `commands/_shared/substrate-write-protocol.md ## Concrete computation`:
  1. Compute `sha_before` via the canonical `sha_of_section` bash helper (or `null` only if the section did not exist prior to this write).
  2. Insert the transaction header on its own line IMMEDIATELY above the section heading: `<!-- wos:write owner=slice-closure section='## X' run_id=<ULID-or-uuid> ts=<ISO-8601-ms-with-Z> reason=<<=80chars> mode=applied -->`.
  3. Write or update the section content.
  4. Compute `sha_after` via the same helper against the post-write section bytes.
  5. Append exactly one JSON line to `active/<task>/.wos/VERIFICATION_LOG.jsonl` per the 14-field schema in `wos/substrate-peers.md ## Audit trail`. `sha_after` MUST be valid SHA-256 hex (64 lowercase hex chars) -- NEVER `null` on applied writes. `sha_before` is `null` ONLY on first write to a fresh section.
  6. slice-closure writes 5 sections in one run per the canonical closure pattern. Repeat steps 1-5 PER section. Reuse the same `run_id` + `ts` across all 5 section writes in this single invocation.

  FORBIDDEN: the half-compliant pattern (JSONL line emitted but inline header omitted, OR `sha_*` fields set to `null` when the section already existed).
- **Bounded slice-status propagation (opt-in).** DEFAULT = OFF: with no propagation scope declared, this command writes ONLY the canonical 5-section TASK_STATE.md pattern (above) and nothing else changes. Propagation fires ONLY when the run declares the bounded scope `propagate-slice-status=<subset of {IMPLEMENTATION_PLAN, SOURCE_OF_TRUTH, README, TEST_STRATEGY}>` (via an invocation arg or a per-slice `Propagate-status:` marker inside `### Slice N`); it is a bounded set of named siblings, never a global flag. For each named target write the bounded slice-status field (closed enum: `in-progress | implemented-pending-closure | closed | closed-with-followups | not-ready`; verdict "ready to close"->closed, "ready with follow-ups"->closed-with-followups, "not ready"->not-ready) honoring its write regime:
  - Regime 1 (SUBSTRATE -- inline `<!-- wos:write owner=slice-closure ... -->` header + one `.wos/VERIFICATION_LOG.jsonl` line reusing THIS run's run_id/ts): `IMPLEMENTATION_PLAN.md` sets the field on the `### Slice N` `Status:` line and LOGS the H3-scoped co-write at the owning `## Slices` H2 (`section='## Slices'`, `reason=slice-N-status-<value>`); `SOURCE_OF_TRUTH.md` writes/extends the `## Slice status` H2 pointer with a header above that H2 and one JSONL line naming `section='## Slice status'`.
  - Regime 2 (PLAIN -- direct Edit only, NO wos:write header, NO JSONL line): `README.md` and `TEST_STRATEGY.md` are outside the 11-file substrate set and outside `scan-substrate-headers.sh`.
- Do not reopen broad discovery, broad review, or signed-off contract issues.
- No-op rule for artifacts: WHEN closure status and evidence are already recorded with no material gap, or the slice documentation or `TASK_STATE.md` would not materially change, do not rewrite it; return a no-op, route forward (often `/sync-task-state`), and still output a short NO_OP trace note.
- Treat this as a closure decision for the current slice only, unless the context explicitly says the whole task is ending.
- First identify:
  - current task scope level
  - current closure target
- Then evaluate whether the approved slice goal was met. Require the verbatim command output recorded at execution as proof of each exit criterion; an exit criterion without shown evidence is unverified, not met.
- **Closure floors (lazy-loaded).** Before emitting any closure verdict, load `wos/closure-floors.slice-closure.md` and apply every floor in it exactly as written there. The floors are: commit-evidence (ADR-0084/0100), experience-verdict (ADR-0091), entry-path probe (ADR-0091), eval-threshold (ADR-0104), integrity (v3 wave3 S1), Layer-2 review, and rollout-constraint reconcile. This load is MANDATORY, not conditional. The closure notes SHALL cite which subsections were read and applied. A slice that does not satisfy a floor takes THAT floor's declared verdict, read from its own `On missing evidence:` line: `record` writes `unverified: <reason>` into the closing notes and the slice closes, `reconcile` records a named deferral and the slice closes, and `refuse` classifies the slice `not ready to close` and routes per that file (ADR-0203).
- **Platform runtime floors (lazy-loaded).** WHEN the active task matches the Godot signature (a `project.godot` or `.gd` codebase, or `GODOT_SCENE_PLAN.md` / `GODOT_RUNTIME_VERIFY.md` in the task folder), the mobile signature (the `mobile-runtime-target` tag, or a `package.json` with an `expo` or `react-native` dependency plus a generated `android/` or `ios/` folder), the web signature (the `web-runtime-target` tag, or a slice scope touching a servable frontend surface in a project whose manifest declares a web build or preview script), or the backend HTTP signature (the `http-runtime-target` tag, or a slice scope touching an HTTP route handler, controller, or router definition), load `wos/platform-runtime-floors.md` and apply its **slice-closure variants** (Godot runtime-gate, Godot feel-verdict, Godot tier-declaration, mobile-runtime-gate, web-runtime-gate, backend-runtime-gate) exactly as written there; the closure notes SHALL cite which subsection was read and applied. Inert on a task with no platform signature.
- **Pending-verdict checkpoint.** WHEN exactly one floor is the only reason a slice is `not ready to close` (every other closure input already verified), the closure output SHALL record a fixed-format checkpoint INSIDE the mandatory 5-section TASK_STATE write, zero additional writes: `### In progress` gains `Checkpoint: awaiting <floor-name> verdict for Slice <N>; investigation complete at commit <ref>; resume via slice-closure with the verdict`, and `## Recommended next step` names what produces the verdict. The commit-evidence floor is EXCLUDED. On a later invocation carrying the verdict, resume from the checkpoint WITHOUT re-investigating; confirm only that the cited commit is still the slice's latest; a moved head invalidates the checkpoint and falls back to the full investigation, never a silent stale close. For the human-verdict floors (feel-verdict, experience-verdict) a bare `PASS` argument SHALL NOT resolve the checkpoint: the real artifact block (`## Feel verdict` or `## Experience verdict` with `Overall: PASS`) must be cited, and the resume is INVALID when this invocation is the same autonomous continuation that recorded the checkpoint under inherited run-without-stopping authorization with no new human turn in between (ADR-0098). Mechanical floors (eval-threshold, the runtime gates) accept the argument verdict. The `### Command transcript` SHALL name both the checkpoint write and the checkpoint resume. The checkpoint belongs to THIS command only and never travels into a finalization context: `task-close` reads the floors themselves. An attended chain on a task branch (ADR-0233) records the floor's own `unverified:` line instead.
- Classify the slice into exactly one of:
  - ready to close
  - ready to close with follow-ups
  - not ready to close
- Distinguish clearly between:
  - what was completed
  - what is intentionally deferred
  - what remains as a blocker inside this slice
- If the slice is ready, recommend closing it and syncing task state; an attended run sends an uncommitted last slice to `branch-commit --apply` (ADR-0233).
- If not, recommend only the smallest remaining action.
- If status is **ready to close with follow-ups**, the output SHALL name the gap as `micro-delta` or as `material`, in those words: explicit micro-deltas under the same slice intent route to `implement-slice-complement`; a material gap reopens a full `implement-approved-slice` pass. A follow-up left unclassified is incomplete output (ADR-0193).
- Explicitly state what should not be reopened now.
- Record one complexity and dead-code debt line: did this slice introduce any abstraction, config, dependency, or dead code not yet justified by a current caller or a DECISIONS entry? Default "none"; a non-empty answer becomes a tracked follow-up (## In progress) rather than silent debt.
- When proposing a `TASK_STATE.md` update, set **Work complexity** for the **next** step after closure; definitions in `WORKFLOW_OPERATING_SYSTEM.md`.
- When adding LEARNINGS during closure, anchor each entry at the exact decision point that failed (`file:line`, slice section header, command name, or timestamped TASK_STATE row) per `templates/LEARNINGS.md` ## Entry shape. Retrospective summaries without anchors disqualify the entry. Add an optional `Tags:` line (comma-separated keywords) for `rank-learnings.sh`.
- **Multi-repo:** when `SOURCE_OF_TRUTH.md` contains a `## Repositories` section, report exit-criteria validation and remaining blockers per-repo in distinct subsections. A multi-repo slice is "ready to close" only when ALL repos meet their exit criteria; partial-close cases must say which repos passed and which did not.

TASK_STATE.md update pattern (canonical sections to edit at slice closure):
Canonical TASK_STATE.md 5-section write pattern. It was defined at slice closure (its origin and empirical validation: pilot-repo session 2026-06-04, 21 slice closures, ~6 section updates per closure stably converged on this set) and is followed by EVERY command that stamps TASK_STATE.md after a meaningful step (slice-closure, approve-plan, implement-fleet, release-plan, ai-feature-eval-harness, the verify fleets, task-close, and peers). Read "closure" below as "the step this command just completed", then edit exactly these 5 sections in this order:

1. `## Current phase` -- if the phase shifted (e.g., discovery -> implementation), update the phase label and any inline progress notes.
2. `## Last completed step` -- replace with `Command: <cmd>`, `Mode: <mode>`, `Summary: <1-2 line outcome>`. This becomes the recovery anchor for `resume-from-state`.
3. `### In progress` (nested under `## Current status`, not a standalone H2, per `task-init.md`'s canonical TASK_STATE.md template) -- if a slice closed cleanly with no follow-up, set to `(none)`. If a follow-up surfaced inside the slice, list it here as the immediate next item.
4. `## Recommended next step` -- replace with `Command: <next>`, `Mode: <mode>`, `Why: <one line>`. Aligns with the Handoff `Run now` line.
5. `## Current closure target` -- if a slice or epic just closed, advance this to the next closure target (next slice or next epic). If the same target still applies, keep it (no-edit OK).

Optional 6th section:

6. `## Resume notes` -- update only when external context shifted (a referenced repo moved, a decision was made elsewhere, etc.). Most slice closures do not touch this.

Rules:

- Use Edit (not Write) per section. Avoid full file rewrites; they invalidate prompt cache and lose audit trail.
- If a section would not materially change, skip it (per `WORKFLOW_OPERATING_SYSTEM.md` `## Cross-cutting workflow guardrails` -> `### Material change (definition)`).
- All 5 mandatory sections must be present in the file. If any is missing, propose adding the missing section first as a separate edit before continuing the closure update.
- Total edits per closure typically range 4-6. More than 8 indicates either drift recovery (mark in transcript) or that `slice-closure` is being misused for closure of multiple slices at once (split into separate runs).
- Every edit above is a SUBSTRATE WRITE: transaction header plus one `.wos/VERIFICATION_LOG.jsonl` line per `commands/_shared/substrate-write-protocol.md`, most cheaply via `scripts/emit-substrate-write.sh`. Read that file for the mechanics and for which OTHER targets are in or out; do not infer the boundary from this list. **Watch section 3.** Four of the five are `TASK_STATE.md` H2 sections, but `### In progress` is an H3 under `## Current status`, so its write LOGS AT THE OWNING H2 (`section='## Current status'`) and never at `### In progress`. Two things break otherwise, and neither is visible when it happens: the validator rejects any `section` not starting with `## `, so `verify-substrate-batch.sh` returns non-zero and fails the integrity gate; and `sha_of_section` runs to the next `^## `, so hashing the H3 swallows its sibling H3s and records a `sha_after` over bytes the writer does not own, surfacing later as a false drift at the `task-close` integrity floor.
### Substrate digest fallback
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
### References status (report, X2)
**References reconcile (X2, 2026-07-18).** Reconcile the references a task cited (its `REFERENCES.md` deliverable, an `EXTERNAL_RESEARCH.md`, or the project-level references it grounded in) against what the task actually shipped, enforcing "cite only what you used." Lifecycle-aware: it reports at a mid-task checkpoint and hard-fails only when finalizing the whole task.

1. Gate on presence. This sub-check fires only WHEN the task produced or cited references: a `REFERENCES.md` or `EXTERNAL_RESEARCH.md` in the task folder, or a `Grounded in:` citation in the shipped work. WHEN none is present, it is a no-op: skip and proceed.

2. Classify the context. A finalization run is `task-close` (or `review-hard` as the pre-PR final pass). A checkpoint run is `slice-closure` or `where-we-at`. At a checkpoint a cited reference not yet reflected is normal in-progress work, not a defect.

3. Reconcile cited vs reflected. For each reference the task cited, confirm the shipped work materially reflects it (a real layout, behavior, or decision traceable to that reference), not merely a name-drop. A reference cited with no material trace in the shipped work is a cited-but-unused reference: this is the failure the brief names ("if the final result does not reflect the references you cited, the REFERENCES.md is wrong").

4. Apply the gate by context.
   - WHEN finalizing: IF any cited reference is unused (no material trace) THEN name it and require either removing the citation or pointing to where it is reflected, and route to `implement-slice-complement` (fix the citation) before closing.
   - WHILE at a checkpoint: report each cited-but-unused reference as a must-address finding (name it, route to `implement-slice-complement`), and do NOT invalidate the whole output on that basis.

"Cite only what you used" is the invariant. This is the produce-side gate for the `capture-references` and `external-research` artifacts, the design-and-research analog of the deliverable-reconcile completeness check.
### Definition of done (command output)
- Closure status is exactly one of: ready / ready-with-followups / not-ready, with evidence.
- Commit-evidence floor (ADR-0084, ADR-0100): a ready-to-close slice cites its commit reference or records an explicit committing-waiver covering only genuinely discardable work; real work pending a human commit is a bounded deferral that keeps the slice open (not a waiver), and a slice with none of the three is classified not-ready and routed to `branch-commit`.
- Eval-threshold floor (ADR-0104): when an `AI_EVAL_PLAN.md` covers the closing slice's feature, closure requires the cited score-vs-threshold outcome met on the held-out set (or an explicit bounded skip reason per ADR-0098); harness-mechanism wording never substitutes for the threshold outcome.
- Closure floors (lazy, unconditional; `wos/closure-floors.slice-closure.md`): the slice-closure variants were loaded and applied, and the closure notes cite which subsections were read. Emitting a closure verdict without that citation is invalid output.
- Layer-2 review floor: a cited `review-hard` verdict (plus `security-review` on a security surface), a named host-repo equivalent, or an explicit one-line skip reason. Layer 1 green never substitutes.
- Rollout-constraint reconcile: when the plan carries `## Rollout and rollback notes`, every constraint naming a file, config key, or release track inside the closing slice's Scope is satisfied or recorded as a named deferral.
- Platform runtime floors: on a Godot-, mobile-, web-, or backend-HTTP-signature task, the slice-closure variants in `wos/platform-runtime-floors.md` were applied and the closure notes cite which subsection was read; a slice failing a floor takes the verdict its `On missing evidence:` line declares and routes per that file. Inert on tasks with no platform signature.
- Experience gates (`On missing evidence: record`): a slice tagged `user-facing-content` or `new-user-facing-surface` records `unverified: no experience verdict on a sample`, and a `new-user-facing-surface` slice `unverified: entry path never exercised`, unless the verdict or the entry-path run is cited or a skip reason is recorded (ADR-0203); stands down on the Godot signature in favor of the D-4 floor above.
- Clearly distinguishes slice completion vs full task completion.
- Slice file updates are `APPLIED`.
- Integrity floor (v3 wave3, S1): verify-substrate-batch ran and exited 0, or the explicit `integrity-waiver: N advisories unresolved (<reason>)` line is recorded; a silent non-zero closure is invalid output.
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
Optimize for clean closure, scope discipline, low ambiguity, and forward momentum.
