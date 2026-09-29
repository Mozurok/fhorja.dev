---
name: autonomous-readiness
description: Decide whether an already-defined project is ready to boot an unattended overnight run, and refuse until it is. Reads the project's own definition artifacts through the shared definition-completeness reader, emits a per-criterion ledger with a BOOT or NOT-READY verdict naming every missing item, and returns NOT-READY when a declared runtime surface has no evidence adapter rather than booting blind. It reports and routes: it never answers a criterion on the operator's behalf, never records a decision as user input, and a BOOT verdict never substitutes for plan approval. Use before handing a night to autonomous-run. Do not use to approve a plan (use approve-plan), to drive the run itself (use autonomous-run), to view a run already in flight (use autonomous-board), or to shape a fuzzy objective before a task exists (use problem-framing).
metadata:
  category: autonomy
  primary-cursor-mode: Ask
  multi-repo-aware: false
  context-layers-consumed: [memory]
  context-layers-produced: [memory]
  tools: [Read, Write, Edit, Bash, Glob, Grep]
  x-wos-profiles: [full]
  provenance: first-party
  suggested-model: claude-sonnet-5-5
---
# autonomous-readiness

Act as the boot gate for the autonomous delivery track, deciding whether a project is defined well
enough to hand a night to `autonomous-run`, and refusing until it is.

Goal:
Produce a per-criterion readiness ledger and one verdict, BOOT or NOT-READY, over an already-defined
project. The gate exists because `autonomous-run` checks only that a plan is approved and waved; it
never asks whether the product context behind that plan is complete, so an underspecified project
could reach a detached night and spend it stalling. This command asks first. It reports and routes;
it decides nothing on the operator's behalf and it writes no product code.

Mandatory context bootstrap (before any output):
<!-- shared:mandatory-context-bootstrap -->
- Read these sections in `WORKFLOW_OPERATING_SYSTEM.md` first:
  - `## LLM execution contract`
  - `## Editor mode policy` (mode definitions only; the tool mapping table is lazy-loaded in `wos/editor-mode-mappings.md` and needed only for non-Claude-Code tools)
  - `## Global output contract` (including **Adaptive handoff** and **Mode selection rule**)
  - `## Cross-cutting workflow guardrails`
- **Bootstrap tiers:** the light-weight commands (`branch-commit`, `what-next`, `where-we-at`, `slice-closure`, `compact-task-memory`) plus the high-frequency `implement-approved-slice` and `sync-task-state` (v3 wave1 item D) read the four sections above with two subsections of `## Cross-cutting workflow guardrails` skipped: `### External web access (centralized)` and `### Sequencing heuristics (by phase)`. Everything else is read at every tier, including `### Proposal vs approved persistence` and `### Substrate peer ownership (per ADR-0034)`, since all seven write substrate sections and reason about PROPOSED (`state-reconcile` stays on the full tier for cross-artifact judgment). The full tier is measured at 12109 tokens, the four always-read sections combined; the two skipped subsections are 1,034 of those (measured 2026-09-28), so the reduced tier is about 11,074. The leaf-reviewer tier (`verify-against-rubric`, ADR-0226) reads only `## Global output contract`, measured at 5215 tokens, plus its rubric.
- **Session bootstrap reuse (skip-if-unchanged; v3 wave1 item D):** WHEN this conversation already read the bootstrap sections in an earlier turn still VISIBLE in the context window AND `WORKFLOW_OPERATING_SYSTEM.md` has not changed since, the command MAY skip the re-read and cite the earlier one, emitting one Command transcript line: `Bootstrap: reusing turn <N> read, WOS unchanged`. Scoped exception to the context-budget re-fetch rule (`wos/context-budget.md`, "The re-fetch rule"), because these sections are one large, static, byte-identical read repeated every turn; every other tool result still re-fetches. VISIBLE means the section text itself is still present and quotable now, not merely that a record of the earlier read exists: a harness that clears a tool result while the record survives (ADR-0114) has not satisfied VISIBLE, and self-declared memory after a compaction never qualifies. A stateless-per-turn harness is excluded. The transcript line is mandatory; a silent skip is invalid output.
- **Resolving `WORKFLOW_OPERATING_SYSTEM.md` and a relative `wos/<topic>.md`.** Both resolve the same way: try the canonical workflow repository root FIRST, then the installed docs directory (`~/.claude/workflow-docs/` or `~/.cursor/workflow-docs/`, the spec at that root and topics under its `wos/`). Repository first, because the installed copy is a snapshot no sync prunes; preferring it would hide a `wos/` edit from every command until a reinstall. Name the resolved root in `### Command transcript`, and say so explicitly when NEITHER resolved rather than continuing silently, since several of these loads are MANDATORY.
- Read additional sections only when relevant to this command's role.
- Align all routing recommendations and next-command suggestions with the current command set.
- **Official next-command names only:** every recommended next command (including the handoff `Run now` line) MUST be the basename of an existing `commands/<name>.md` file in this workflow repository. Never invent names. One exception: `Run now: none` with `Mode: N/A` declares the chain ended with no honest next step, defined under `### Official command names (routing integrity)` (ADR-0126); use it only then, never to end a chain that has a real next step.

Required inputs:
- active task folder path, and the project folder above it
- the definition sources to read: `PROJECT_CHARTER.md`, `REFERENCES.md`, and the task's
  `SOURCE_OF_TRUTH.md`, `DECISIONS.md`, `IMPLEMENTATION_PLAN.md`, plus any spec or brief the operator
  names
- the declared runtime surfaces the work produces (web, backend HTTP, mobile app, game, database), or
  a statement that the operator has not declared them yet
- last completed step from `TASK_STATE.md` (command plus summary)

Operating rules:
- Do not implement code. Do not edit `DECISIONS.md`, `SOURCE_OF_TRUTH.md`, or `IMPLEMENTATION_PLAN.md`.
- **Handoff:** end with the adaptive `### Handoff` block per `WORKFLOW_OPERATING_SYSTEM.md`
  `## Global output contract` (Mode A compact or Mode B full).
- **Report, never decide (the load-bearing rule).** The gate SHALL NOT answer an open criterion, fill
  a missing decision, or record its own inference as user input. A gap is reported as a gap and the
  operator fills the SOURCE, not the ledger. An agent-authored answer recorded as the operator's is a
  contract violation (`wos/cross-cutting-workflow-guardrails.md` -> unattended sessions), and it is
  the failure this gate would cause at maximum blast radius: a green light nobody actually gave.
- **A BOOT verdict is not an approval.** Plan approval stays a separate, upstream, hard precondition:
  `autonomous-run` still refuses a plan with no `## Approval log` entry and still routes to
  `approve-plan`, and it refuses a `one-slice route` approval line the same way: `task-init` writes
  that line for an attended run only (ADR-0225). This gate is an ADDITIONAL check in front of that one, never a replacement, and it
  SHALL say so whenever it returns BOOT.
- **Surface-to-adapter check.** For every declared runtime surface, name the evidence adapter that
  will produce its morning artifact: web -> `web-runtime-verify`; backend HTTP -> `api-runtime-verify`;
  mobile app -> `app-runtime-verify`; Godot -> `godot-runtime-verify`; database -> `db-context-supabase`
  or `db-context-postgres`. IF a declared surface has no adapter THEN the verdict is NOT-READY naming
  that surface and that gap; do NOT return BOOT with a surface the run cannot produce evidence for.
  A surface the operator has NOT declared is itself a missing criterion, not an absent one.
- **Incremental, and re-runnable.** The ledger is regenerated from the sources on every run. Filling a
  gap in the source and re-running flips that row with no hand-editing. Never edit a prior ledger row
  to make a verdict change; rewrite the ledger from what the sources now say.
- **The governor envelope is part of readiness.** `autonomous-run` takes the STOP sentinel path and the
  governor limits (max-iteration, wall-clock timeout) as required inputs with no defaults. Report
  whether the operator has them; an unset envelope is a `missing` row, because a night with no
  wall-clock bound is not a bounded run.
- **The D9 skip list is unchanged and unreachable from here.** This gate adds a precondition; it grants
  no permission. It SHALL NOT accept a flag that relaxes a permission posture, and IF asked to, it
  refuses and cites ADR-0044 D9.
- **No-op rule.** WHEN a current ledger already covers these sources with no material change since the
  last run, return a short `NO_OP_TRACE` and route forward rather than rewriting the ledger.
- Write the ledger as `RUN_READINESS.md` in the active task folder. Task-memory write policy applies:
  `APPLIED`.

### Definition-completeness reader
<!-- shared:definition-completeness-reader -->
**Definition-completeness reader (shared engine, D-5 of the 2026-07-27 readiness task).** One reader, two consumers: `problem-framing` runs it at intake over a supplied spec, `autonomous-readiness` runs it at boot over the project's own artifacts. The criteria and the reporting shape are identical; only the source set and what the caller does with the result differ. Two implementations of the same question drift, and the drift would show up as a gate booting a run the intake had already called underspecified.

1. **Read, never fill.** The reader REPORTS what each criterion's sources say and what they do not say. It SHALL NOT answer a criterion on the user's behalf, and it SHALL NOT record its own inference as a confirmed fact or a locked decision. A criterion the sources leave open is reported open. This is the load-bearing rule: a reader that quietly fills gaps turns an unprepared project into a green light, which is the exact failure the reader exists to prevent.

2. **The criteria.** For each one, name the source actually read (file plus section) or report it absent:
   - Objective: what the work is for, stated in the product's terms rather than the workflow's.
   - Success criteria: user-observable and checkable, not a restatement of the objective.
   - Non-goals: what is deliberately out of scope.
   - Stack and workspace: what is being built on, and where the code lives.
   - Constraints: what must not change.
   - Named deliverables: the concrete things the user asked for by name.
   - Locked decisions: for every boundary the work will touch (schema, contract, auth, migration, permission), whether a decision covering it is locked or still open.
   - Declared surfaces: which runtime surfaces the work produces (web, backend HTTP, mobile app, game, database), because each one needs an evidence adapter downstream.
   - Declared external dependencies: which things the sources require the ENVIRONMENT to provide before the work can start (a named MCP server, a credential or account, a tool binary, a dataset, a device). Report each one and whether it is reachable right now, because a dependency that is named in the spec and absent from the environment stops the work at its first step rather than at review. Reachability is a fact this reader may check the cheap way (the tool is in the session's tool list, the binary answers `--version`, the path exists); it is never inferred from the spec merely naming the dependency. Rule 1 still binds: report `named, not reachable`, never resolve it on the user's behalf.

3. **Three statuses, and nothing else.** Report each criterion as `present` (naming the source read), `partial` (naming both what is there and what is missing), or `missing`. A status carries the source it came from, never a degree of confidence; a status whose source slot is empty reads as unknown, not as a weak yes (`wos/active-epistemic-humility.md`).

4. **Incremental by construction.** The reader is stateless and re-runnable: it reads the sources as they are now. Filling a gap in the SOURCE and re-running SHALL flip that criterion without anyone hand-editing the ledger. A reader whose output has to be corrected by hand has failed, because the hand-edit is exactly the unverified claim the ledger was supposed to expose.

5. **The reader emits no verdict of its own.** It produces the per-criterion table and stops. The caller decides what a given status set means: at intake it shapes the next question, at boot it decides BOOT or NOT-READY. Keeping the verdict out of the reader is what lets both consumers share it without one inheriting the other's policy.
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
### Definition of done (command output)
- Every criterion in the shared reader has a row with a status and the source it was read from; a row
  whose source slot is empty reads as unknown, never as a weak yes.
- The verdict is exactly one of BOOT or NOT-READY, on its own line, with its reason.
- A declared surface with no evidence adapter produced NOT-READY naming that surface; returning BOOT
  with an unadaptered surface is invalid output.
- No criterion was answered by this command. No `DECISIONS.md` entry, no `SOURCE_OF_TRUTH.md` fact, and
  no ledger row was authored on the operator's behalf.
- A BOOT verdict restated that plan approval remains a separate upstream precondition.
- Output ends with a complete `### Handoff` block per the adaptive format in
  `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract`.
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command
  outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
A boring gate that says no clearly. NOT-READY naming three concrete gaps is worth more than a BOOT
that skipped the question, because the operator can act on the first before going to sleep and cannot
act on the second at all.
