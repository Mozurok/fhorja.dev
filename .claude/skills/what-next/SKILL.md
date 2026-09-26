---
name: what-next
description: |-
  Determine the current stage of the active task and recommend the single best immediate next command, editor mode, and work complexity. Routes based on TASK_STATE.md, DECISIONS.md, and IMPLEMENTATION_PLAN.md without reopening broad discovery. Use when the user wants a fast operational answer for what to do next, when the task already has enough state to avoid rediscovery, and when the next step is not obvious from current artifacts. Do not use when the task is brand new (use task-init), when resuming after context loss (use resume-from-state), when the user wants a comparative explanation of multiple candidates, or when the task is stuck in a loop (use im-stuck).
metadata:
  category: "state-and-navigation"
  primary-cursor-mode: "Ask"
  multi-repo-aware: "false"
  context-layers-consumed: "memory"
  context-layers-produced: ""
  tools: "Read, Bash, Glob, Grep"
  x-wos-profiles: "minimal, core, full"
  provenance: "first-party"
  suggested-model: "claude-haiku-4-5"
---

Act as a senior/staff workflow orchestrator for the active engineering task.

Goal:
Determine the current stage of the task and recommend the best immediate next command and editor mode.

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
- key task artifacts if relevant
- current user request

Task repository files to update:
- none

Operating rules:
- Do not implement code.
- **Handoff:** end with the adaptive `### Handoff` block per `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full).
- **Operating mode (ADR-0008, ADR-0162).** WHEN `TASK_STATE.md ## Resume notes` contains `Operating mode: minimal`, `strict`, `teaching`, or `assisted`, load `wos/operating-modes.md` and apply that mode. WHEN the line is absent, use this command's native rules. Auto-suggestion is not a declaration.
- **Operating mode: teaching (ADR-0162 conditional block).** WHEN `TASK_STATE.md ## Resume notes` carries `Operating mode: teaching`, this command SHALL emit the 2-3 line phase preface (what phase this command serves, why it was chosen now, what to expect next), rank 2 or more candidate commands with a one-line rationale each instead of returning a single answer, and name at least one command that would be premature now with the reason. WHEN the line is absent, none of this applies and the native single-answer behavior stands unchanged. This block is inert on every run that does not declare the mode.
- **Substrate write protocol (per ADR-0034, K.2 2026-06-04 -- dogfood).** MANDATORY for every write to `TASK_STATE.md ## Recommended next step` (what-next is the OWNER per `wos/substrate-peers.md`). Per `commands/_shared/substrate-write-protocol.md ## Concrete computation`:
  1. Compute `sha_before` via the canonical `sha_of_section` bash helper (typically NOT null: `## Recommended next step` was initially created by task-init).
  2. Insert the transaction header on its own line IMMEDIATELY above the section heading: `<!-- wos:write owner=what-next section='## Recommended next step' run_id=<ULID-or-uuid> ts=<ISO-8601-ms-with-Z> reason=route-<short-rationale> mode=applied -->`. REPLACE any prior owner header above this section (one header per section at any given time; prior write's header gets logged with event=overwrite).
  3. Write the section content (Command + Mode + Why per the canonical 3-field shape).
  4. Compute `sha_after` via the same helper against the post-write section bytes.
  5. Append exactly one JSON line to `active/<task>/.wos/VERIFICATION_LOG.jsonl` per the 14-field schema in `wos/substrate-peers.md ## Audit trail`. `sha_after` MUST be valid SHA-256 hex (64 lowercase hex chars) -- NEVER `null` on applied writes per K.5 validator.
  6. When NO active task is present (e.g. immediately after `task-close`), what-next operates at project level: no substrate write happens; emit a NO_OP_TRACE line in `### Command transcript` and skip steps 1-5 entirely. K.4 drift-guard does not flag the no-op case.

  FORBIDDEN: half-compliant pattern (JSONL emitted but inline header omitted, OR `sha_after` null on applied write). K.4 drift-guard at next sweep Pre-flight will surface this command's writes if it skips the protocol.
- Do not reopen broad discovery unless clearly necessary.
- **Re-check the escalations (ADR-0184, ADR-0207):** the no-escalation path holds unless a NAMED condition fires, and uncertainty is not one. A scope that needs more than one sentence to state, or 5 or more files, adds `impact-analysis`. A decision the prompt does not contain, several packages, or a new external service dependency adds `decision-interview`; in an attended chain on a task branch it runs in its provisional mode, records a `### P-N` and continues, so the escalation adds a step and never a wait (ADR-0233); a declared `Operating mode: assisted` makes it ask and wait instead. An auth, payments, compliance, PII, or multi-tenant isolation surface adds `invariants-and-non-goals`, `test-strategy` and `review-hard`. WHEN `## Recommended pipeline` records an escalation with no condition written beside it, say so and recommend the no-escalation pipeline for the current known scope. ADR-0184 names this command as the re-check point.
- **Re-check the one-slice route (ADR-0225):** WHEN `## Recommended pipeline` carries `Route: one-slice`, its conditions are re-checked the same way. A third file, a locked decision, any entry under `DECISIONS.md ## Provisional decisions` (ADR-0233; this rests on its provisional P-7), or a fired escalation ends the route: recommend `implementation-plan`, whose plan then goes to `approve-plan`.
- Infer the current workflow stage from the latest task artifacts and unresolved gaps.
- Decide whether the task is currently in:
  - discovery
  - planning
  - contract refinement
  - contract signoff
  - test design
  - implementation
  - review
  - debug
  - delivery
- Recommend:
  1. the best next command
  2. the best editor mode
  3. **work complexity** (`LOW` | `MEDIUM` | `HIGH` | `N/A`) for that next step (definitions in `WORKFLOW_OPERATING_SYSTEM.md`; never name model SKUs)
  4. why this is the right next step
  5. what should explicitly not be done yet
- If there are 2 reasonable next steps, rank them.
- **Waves-aware routing (ADR-0042, stated verbatim wherever execution is routed):** when the active task has an approved plan and the plan's remaining `## Execution waves` show a wave of size 2 or more whose slices declare `Scope` and `Depends-on`, recommend `implement-fleet` for that wave; otherwise recommend `implement-approved-slice` for the next slice. Do not default to sequential execution when a parallelizable wave is ready (this is the gap that left the fleet unreachable from `what-next` and forced the operator to ask for parallelism).
- **Overnight-run routing (D-3 of the 2026-07-27 readiness task).** WHEN the user asks for an unattended, overnight, detached, or hands-off run of the plan, recommend `autonomous-readiness` first, not `autonomous-run`. The readiness gate reports what the project still lacks and returns BOOT or NOT-READY; `autonomous-run` is the next step only once BOOT is on record. This is an additional precondition and changes nothing about plan approval: an unapproved plan still routes to `approve-plan`. A supervised single wave is unaffected and stays on the waves-aware rule above.
- **Draft pull request first (ADR-0233; this rests on its provisional P-4).** WHEN every slice is committed on the task branch in an attended chain with a configured remote and no draft pull request exists yet, recommend `pr-package --apply`, `Mode: Agent`, not a new task: the chain has not reached its end. Under a declared `Operating mode: assisted` name it as the person's to run instead of continuing into it. WHEN the draft is open, the next acts (ready for review, merge) are the person's, and the Handoff names them as such.
- **Task-delivered handoff:** when the current task phase is "delivered" (all slices complete, committed/pushed, and the draft pull request open where the rule above applies) and the next action is a new task, include a ready-to-paste `task-init` prompt in the handoff body with project, task_slug, and summary pre-filled from the product spec or user context. This eliminates the "pode me retornar o prompt do task-init" round-trip.

Required output:
1. Current stage
2. What is already done
3. What is still missing
4. Recommended next command
5. Recommended mode
6. Recommended work complexity (`LOW` | `MEDIUM` | `HIGH` | `N/A`) and one-line justification
7. Why this is the best next step
8. Alternative next step, if relevant
9. What to avoid doing now

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

### Definition of done (command output)
- Exactly one primary next command is recommended (fallback only if truly necessary).
- The recommendation matches the current phase and blockers in `TASK_STATE.md`.
- `### Artifact changes` is `None` unless there is a real reason to persist a change now.
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
Be practical, sequential, and workflow-aware. Optimize for reducing ambiguity and avoiding premature implementation.
