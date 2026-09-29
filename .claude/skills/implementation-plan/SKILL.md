---
name: implementation-plan
description: |-
  Define an incremental, reviewable, production-safe implementation plan for the active task and persist it as IMPLEMENTATION_PLAN.md plus a TASK_STATE.md update. Breaks work into the smallest safe slices with objective, exact scope, ordering rationale, key risks, validation approach, exit criteria, and work complexity per slice. No code is written. An annotate-only retrofit mode backfills per-slice Scope and Depends-on plus Execution waves onto an in-progress plan so it can adopt implement-fleet. A --spec mode derives slices from a spec or PRD. Do not use when the task is still too unclear, when key facts or decisions remain open, or when the need is to implement an already-approved slice (use implement-approved-slice).
metadata:
  category: "planning-and-validation"
  primary-cursor-mode: "Plan"
  multi-repo-aware: "false"
  context-layers-consumed: "memory"
  context-layers-produced: "memory"
  tools: "Read, Write, Edit, Bash, Glob, Grep"
  x-wos-profiles: "minimal, core, full"
  provenance: "first-party"
  suggested-model: "claude-sonnet-5-5"
---
> **Output contract, in brief.** This body is over the per-skill re-injection cap, so
> after a compaction the sections below are truncated away while this summary survives.
> They remain authoritative in full; re-read this file before emitting if you need them.
>
> - `Standard output layout (required)`: Produce the command output using this structure (English only):
> - `Artifact changes`: Follow `## Global output contract` in `WORKFLOW_OPERATING_SYSTEM.md` for `APPLIED` / `PROPOSED` / `SKIP` rules. Every listed file...
> - `Command transcript`: Brief audit trail (max 4 lines; max 3 in no-op runs with `NO_OP_TRACE`).
> - `Handoff`: Use the adaptive ending format of `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract`. Every Handoff is one fenced `text` b...
> - `Definition of done (command output)`: `scripts/check-plan-coverage.sh <task-folder>` was run against the task folder and reports no unmatched pair, or the run's unavail...


Act as a senior/staff engineer designing a low-risk implementation plan for the active engineering task.

Goal:
Create an incremental, reviewable, production-safe implementation plan for the active task, then persist it in the task repository as explicit, reviewable updates (avoid silent replanning when nothing material changed).

Mandatory context bootstrap (before any output):
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
- active task folder path
- TASK_STATE.md
- SOURCE_OF_TRUTH.md
- DECISIONS.md
- IMPACT_ANALYSIS.md, if available
- INVARIANTS_AND_NON_GOALS.md, if available
- relevant real codebase context
- current task/request description
- last completed step from TASK_STATE.md (command + summary)
- any "relevant prior lessons" surfaced by `task-init` from prior LEARNINGS (read-only; let them inform slice shaping and risk notes, per ADR-0017)
- optional: `--spec <path>` to a spec, PRD, or requirements document (internal to the repo or already captured) to derive the plan from that spec and check coverage of every spec item, per ADR-0061 (see the spec-ingest mode in Operating rules)

Operating rules:
- Do not write code.
- **Handoff:** end with the adaptive `### Handoff` block per `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full).
- **Operating mode (ADR-0008, ADR-0162).** WHEN `TASK_STATE.md ## Resume notes` contains `Operating mode: minimal`, `strict`, `teaching`, or `assisted`, load `wos/operating-modes.md` and apply that mode. WHEN the line is absent, use this command's native rules. Auto-suggestion is not a declaration.
- **Substrate write protocol (ADR-0034, ADR-0101).** MANDATORY for EVERY H2 this run writes to IMPLEMENTATION_PLAN.md or DECISIONS.md (per `commands/_shared/substrate-write-protocol.md ## When to emit`). Ownership per `wos/substrate-peers.md`: this command owns `## Target behavior`, `## Current gaps`, `## Infrastructure prerequisites`, `## Slices`, `## Execution waves`, `## Rollout and rollback notes`, `## Risks and mitigations`, `## Open questions or approvals still needed`, and `## Spec coverage` (--spec mode); it CO-WRITES `## Constraints` and `## Validation expectations` with a direct write ONLY while the owning artifact does not exist (ADR-0101). Genesis (first plan write): headers on the line IMMEDIATELY above each H2, then `bash scripts/emit-substrate-write.sh batch --owner implementation-plan --file IMPLEMENTATION_PLAN.md --reason <reason> --mode applied --task-root <task-folder> --run-id <id>`. Existing sections: `bash scripts/emit-substrate-write.sh apply --owner implementation-plan --file IMPLEMENTATION_PLAN.md --section '## X' --reason <reason> --body-file B` (`apply` dies if the section is missing). A re-plan uses the full-document-rewrite pre-snapshot pattern; dropped H2s emit `event=delete`. Reuse the same `run_id` + `ts`. Per-slice status mutations by `implement-approved-slice` / `slice-closure` log at parent `## Slices`.
  FORBIDDEN: half-compliant pattern (JSONL emitted but inline header omitted, OR `sha_*` null on existing sections).
- **Never truncate before Handoff:** even after a long `IMPLEMENTATION_PLAN.md` payload inside `### Artifact changes`, the message must still end with `### Handoff` and the fenced standard ending format.
- When Mode B applies, the Handoff includes the task path and other context the next command needs under `Resume context:`.
- **Engine scene-plan routing (ADR-0132).** WHEN the work in scope is a Unity 3D feature (signalled by a `ProjectSettings/ProjectVersion.txt`, an `Assets/` tree, or the task naming Unity as the target) AND no `UNITY_SCENE_PLAN.md` covers it, the plan SHALL route to `unity-scene-plan` before slicing the build, because the GameObject hierarchy, render pipeline, and networked-authority model are decisions this command slices around rather than makes. The same rule holds for a Godot target and `godot-scene-plan`. A plan that slices an engine feature with no scene plan is flagged in `### Command transcript` and routed, not silently sliced.
- **Design-surface routing (ADR-0099).** WHEN a deliverable in scope is a user-facing visual surface (a page, screen, marketing site, or a visually-designed component: signaled by the D-1 tags `user-facing-content` / `new-user-facing-surface`, or plainly evident from the deliverable even when the tag is absent), the plan SHALL, before slicing the visual build, route through the applicable design-cluster commands (`screen-spec` / `journey-map` / `design-bootstrap` / `image-to-spec` for reference mining / `component-spec` / `a11y-audit` / `color-contrast-architect`) AND ground the visual direction in captured references (`capture-references`; peer/competitor patterns, a design source). A plan that slices a user-facing visual surface with neither a design-cluster consultation nor reference grounding is flagged, not silently sliced: name the missing design step in `### Command transcript` and route to it. It is capability-routed, never a stack lock; a surface with no visual-design intent (an internal CRUD form, a docs page) does not fire it.
- No code changes should happen before plan approval.
- Before producing output, verify `implementation-plan` is still the highest-value command based on `TASK_STATE.md` and whether the plan would materially change.
- No-op rule for artifacts: WHEN `IMPLEMENTATION_PLAN.md` already matches the current approved decisions and scope with no material gap, or it or `TASK_STATE.md` would not materially change, do not rewrite it (not for style either); return a no-op, route forward, and still output a short NO_OP trace note.
- **Enumerate all unmet prerequisites in one NO_OP (ADR-0148; the spec's `### No-op execution rule`).** Here it means: a NO_OP caused by unmet prerequisites (missing reference grounding, references still PROPOSED and not persisted, no design-cluster consultation for a user-facing visual surface, and so on) enumerates every one of them and names the one command that resolves the most at once. The `NO_OP_TRACE` stays mandatory: cheap means fast, not silent.
- Break the work into the smallest safe slices. A single-phase plan covering the whole task is invalid when the work touches more than one file, contract, or behavioral seam; produce explicit numbered slices instead (use `SLICES/01_<slug>.md`, `02_<slug>.md`, ... when slice-level traceability helps).
- Optimize for correctness, low blast radius, and ease of review.
- Do not include opportunistic refactors unless required for safety or correctness.
- Apply the YAGNI restraint ladder to every slice before committing it to the plan: does this need to exist at all, then can the standard library do it, then the native platform, then an already-installed dependency, then a one-line change, then the minimum viable implementation. Flag any slice that adds a dependency or a new abstraction without a `DECISIONS.md` entry backing it. Tie the floor to `DECISIONS.md` and `INVARIANTS_AND_NON_GOALS.md` so safety-required structure is never trimmed away.
- For each phase or slice, define:
  - objective
  - exact scope
  - `Scope:` the explicit file paths or globs this slice creates or modifies (machine-readable, one path per entry). List every file the slice will touch: `implement-fleet` computes its waves from it (ADR-0041).
  - `Depends-on:` the slice IDs this slice requires, or `none` (machine-readable). With `Scope`, this defines the slice DAG.
  - `Deliverable-tag:` WHEN a slice's deliverable is user-facing product content or a new user-facing surface, the slice SHALL carry `Deliverable-tag: user-facing-content` or `Deliverable-tag: new-user-facing-surface` (ADR-0091). Omit for slices with no user-facing deliverable. Derive the tag by reading the `## Requested deliverables` ledger in TASK_STATE.md first: every ledger row tagged `user-facing-content` or `new-user-facing-surface` SHALL have its covering slice(s) carry the matching tag; dropping a ledger-carried tag is flagged in `### Command transcript` and blocks at `approve-plan`'s consistency gate (ADR-0103). Tagging test (ADR-0103, extending ADR-0091): the tag applies when a human end user experiences the content or reaches the surface through ANY client, visual or not (an MCP prompt surface reached via chat tags; an MCP tool whose RESULT a human end user consumes in the client tags; a tool or API consumed only by the model or another machine does not); machine-to-machine APIs and developer-facing CLIs do not tag.
  - `Decision-ref:` the `DECISIONS.md` D-N entry (or entries) this slice implements, or `none` with a one-line reason. Optional but preferred: `approve-plan`'s consistency gate reads it when present and falls back to content-level tracing otherwise (ADR-0103); a task with no locked decisions passes that gate without this field. A slice resting on a provisional P-N SHALL say `rests on provisional P-N`; `approve-plan` passes it labeled, never as authorized (ADR-0233).
  - `Status:` initialized `planned`; values `planned | approved | implemented (pending closure) | closed`; mutated only by `implement-approved-slice` / `slice-closure` per the K.2 co-writer rule.
  - why this order is safe
  - key risks
  - validation approach
  - exit criteria -- MUST use EARS template (per ADR-0031). Event-driven form preferred for slices: `WHEN <observable trigger> the <system/test/build> SHALL <verifiable outcome>`. Banned softeners in canonical sentence: should, may, appropriate, sensible, reasonable. Free-form prose for rationale is OK; the canonical sentence must use SHALL keyword.
  - **work complexity** for executing that slice: exactly one of `LOW`, `MEDIUM`, `HIGH` (definitions in `WORKFLOW_OPERATING_SYSTEM.md`), plus one line why (no model names)
  - **asset-fidelity decision** (design-to-code slices only, per ADR-0051): `Asset-fidelity: real-MCP` (the slice pulls the exact Figma node before editing) or `Asset-fidelity: placeholder` (with a one-line reason and the approval). Omit for non-design slices; when a slice implements from a design source and nothing is stated, the default is `real-MCP` and the execution gate enforces it.
  - optional `STOP conditions:` for escalated and boundary slices, the observable signals that mean the executor must halt and escalate rather than improvise (scope creep beyond the declared `Scope`, a failing test the slice did not introduce, an unexpected schema or contract touch). Omit for simple slices; do not over-specify, since false halts add ceremony.
- **Run the coverage checker before reporting the plan complete.** After writing `IMPLEMENTATION_PLAN.md`, run `scripts/check-plan-coverage.sh <task-folder>`. It is deterministic and FAIL-tier here: WHEN it reports an unmatched pair, fix the plan and re-run; the plan is not complete while any pair is unmatched. It checks three rules this file states in prose: every `## Requested deliverables` row tagged `user-facing-content` or `new-user-facing-surface` has a slice carrying the matching `Deliverable-tag:`; every non-superseded `### D-N` under `DECISIONS.md ## Locked decisions` is cited by a slice `Decision-ref:` or named in an exit criterion (a D-N carrying `Confirms: P-N` is also covered by a slice citing that P-N or a later entry of its `Replaces:` chain; one carrying `Supersedes: P-N` is not); and every slice declares `Scope:`, `Depends-on:`, `Status:`, an EARS exit criterion and a work-complexity value. Record the result in `### Command transcript` as one line (`Plan-coverage: clean in <folder> (...)`). Resolve `scripts/check-plan-coverage.sh` against the WORKFLOW ROOT (the clone, or the installed docs directory, ADR-0224). WHEN it is in neither, exits 2 (`not measured`), or is refused by a permission boundary, write `plan-coverage: not checked (<reason>)` in `### Command transcript`, never a pass, and check the three rules by reading the substrate; a silent skip is invalid output. On the two rules `approve-plan` also asserts, a green here predicts that gate; it does not replace it.
- Explicitly identify:
  - what must change
  - what must not change
  - what remains uncertain
- Include rollout and rollback notes when runtime behavior is affected.
- If planning cannot proceed safely due to unresolved ambiguity, stop and recommend the correct prior command instead.
- If the plan would introduce new behavioral commitments not supported by `DECISIONS.md` and evidence, label them as **PROPOSED** and route to the smallest decisive upstream command (`targeted-questions`, `decision-interview`, `resolve-contract-gaps`, or `contract-signoff`) rather than treat them as decided. In an attended chain on a task branch (ADR-0233) this command writes that `### P-N` itself under `DECISIONS.md ## Provisional decisions` (`Evidence:`, `Impact:`, `Status: provisional`), the slice cites it, and planning continues; a P-N never de-scopes a named deliverable.
- **Retrofit mode (annotate-only; the adoption bridge for `implement-fleet` per ADR-0041).** When the caller signals `retrofit` or `annotate-only` (asks to make an existing plan fleet-ready, or arrives here from `implement-fleet` Step 1 because slices lack `Scope` / `Depends-on`) and a valid `IMPLEMENTATION_PLAN.md` already exists:
  - Do NOT re-derive the plan or change any slice's intent, objective, or ordering. This mode only backfills structured fields and computes waves; it is not a re-plan.
  - Read `TASK_STATE.md` to determine which slices are already executed. Annotate and wave-compute over the REMAINING (not-yet-executed) slices only.
  - For each remaining slice, infer `Scope` (the files it will touch, grounded in the slice's prose scope plus a read of the real codebase, never guessed) and `Depends-on` (from the stated ordering and from shared files). Tag any scope the model is unsure of with a one-line `(inferred; verify)` note so the user can correct it before dispatch.
  - Compute the Execution waves over the remaining slices and say which have size >= 2 and which form a pure chain.
  - Persist the annotation as a PROPOSED delta to the existing `## Slices` section (the section this command already owns); do not rewrite unchanged slice content.
  - Handoff routes to `implement-fleet` when a remaining wave has size >= 2 on a harness with per-agent worktree isolation, otherwise to `implement-approved-slice`.
  - NO_OP when every remaining slice already declares `Scope` and `Depends-on` and the Execution waves are current.
- **Spec-ingest mode (`--spec <path>`, per ADR-0061).** When the caller passes `--spec <path>` (a spec, PRD, or requirements document), derive the plan FROM the spec instead of from a free-form task description:
  - Read the spec in full. Enumerate every named feature, requirement, or acceptance item as a discrete `spec item`. Keep the spec's own wording as the item label so coverage stays auditable; do not paraphrase an item away.
  - Map each spec item to one or more slices. The mapping is many-to-many but TOTAL: every spec item MUST trace to at least one slice ID. A slice may cover several small items; a large item may span several slices.
  - Run the deliverable-coverage check (ADR-0056): seed or extend the `## Requested deliverables` ledger in `TASK_STATE.md` with one row per spec item (tagged `in-scope`), then assert each row maps to a slice. A spec item with no slice is a silent omission: surface it in the canonical three-field marker form `[NEEDS CLARIFICATION: spec item "<label>" maps to no slice | include it as a slice or de-scope it | add a covering slice, or record a de-scope in DECISIONS.md]` rather than dropping it. Never de-scope a spec item unilaterally; an explicit de-scope needs a `DECISIONS.md` entry.
  - Emit a `## Spec coverage` subsection in `IMPLEMENTATION_PLAN.md`: a table of `spec item -> slice id(s)` so the trace is reviewable at approval (`approve-plan`'s cross-artifact consistency check reads it).
  - The spec is an external contract for grounding: when it references an external library or API, the normal reference-grounding rules still apply at execution time (the spec text alone does not satisfy the grounding gate).
  - This mode composes with the normal slicing rules: `Scope`, `Depends-on`, the Execution waves subsection, and EARS exit criteria are all still required. It changes the SOURCE of the slices (a spec, not a free-form description), not the slice format.
  - NO_OP when `--spec` points to a missing or empty file (route back to the caller to supply a valid path), or when the spec is already fully covered by the current plan's `## Spec coverage` table with no new items.

IMPLEMENTATION_PLAN.md must include (items 1-9 are literal file sections; the backticked name is the exact canonical H2, matching the `wos/substrate-peers.md` ownership matrix; items 10-12 are response-only output fields, never file sections):
1. `## Target behavior`
2. `## Current gaps`
3. `## Constraints` (constraints and invariants)
4. `## Infrastructure prerequisites` (when applicable): external services, env vars, docker configs, CLI tools, or credentials that must exist before Slice 1 begins. Omit this section when the task has no external dependencies. When present, list each prerequisite with: what it is, how to verify it exists, and what fails without it.
5. `## Slices` (the slice-by-slice plan, preferred). Phase-only output is allowed only for genuinely single-step work (one file or one contract, no integration seam), and the justification must appear in `### Command transcript`. Each slice includes **work complexity** `LOW` | `MEDIUM` | `HIGH` plus one-line rationale, a machine-readable `Scope:` (files the slice touches), and `Depends-on:` (slice IDs or `none`). Immediately after `## Slices`, include a top-level `## Execution waves` section (its own H2 with its own transaction header, NOT a nested subsection) that layers the slice DAG: list each wave as `Wave k: [slice ids]`, grouping into one wave only slices whose dependencies are already satisfied and whose `Scope` sets are pairwise disjoint (no shared file, migration, lockfile, codegen, or barrel export). A pure chain is N waves of one slice; a wide graph has waves of two or more (ADR-0041).
6. `## Validation expectations` (validation and test strategy by phase)
7. `## Rollout and rollback notes`
8. `## Risks and mitigations`
9. `## Open questions or approvals still needed`
10. Recommended next command (response only)
11. Recommended editor mode (response only)
12. Why that is the correct next step (response only)

TASK_STATE.md update must reflect:
- current phase
- current source of truth
- canonical decisions
- current status
- recommended next step
- active files in scope, if now clearer
- current closure target
- **work complexity** for the next execution step (align with the upcoming slice when known)

Required output:
1. Exact content for IMPLEMENTATION_PLAN.md (full document if create/update; otherwise a short NO_OP note)
2. Exact TASK_STATE.md update block, or explicit `TASK_STATE: NO_CHANGE`
3. Recommended next command. When `TASK_STATE.md ## Resume notes` contains `Operating mode: strict`, Handoff the next missing of `invariants-and-non-goals`, `test-strategy`, `approve-plan` (ADR-0162). Otherwise the default is `approve-plan`, for EVERY plan, whether or not the pipeline recorded an escalation. A plan written after the one-slice route ended is no exception (ADR-0225): `task-init` wrote that route's only plan, and this rewrite of `## Slices` voids its approval line. This command writes no Approval log line (ADR-0208). When a remaining wave has size 2 or more, approval routes on to `implement-fleet` on a harness with per-agent worktree isolation (ADR-0243); when the change carries regression risk and no `TEST_STRATEGY.md` exists, `approve-plan` names `test-strategy` as the step right after approval. When unresolved-clarification markers or open decisions remain, route to the smallest decisive upstream command instead. For a single critique-and-revise pass on the freshly-written plan before approval, use `self-critique-and-revise`.
4. Recommended editor mode
5. Why this is the correct next step
6. What should explicitly not be done yet

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
### Reference grounding (design gate)
**Reference grounding (design gate, ADR-0043 D-3).** This command does not edit code, so it does NOT refuse. It marks. Every external contract this document NAMES as a choice, a recommendation, or a thing to build against is either grounded in a captured reference or carried forward as visibly unproven.

1. Detect. Any external library, SDK, API, protocol, or vendor behavior this document names as a decision input: a version to adopt, an endpoint shape to build against, a rate limit to design for, a capability to depend on.
2. Ground or mark. WHEN the contract is present in `projects/<client>__<project>/REFERENCES.md`, read that entry and cite it inline where the decision is stated. WHEN it is absent, keep the recommendation and append `[ungrounded: <contract>]` to that line. Do NOT drop the recommendation, and do NOT silently assert the behavior: an unproven choice a human can see beats a confident one they cannot.
3. Never launder recollection into a design. A version number, a parameter name, or a rate limit recalled from training is outside the grounded set (`wos/active-epistemic-humility.md`). It may appear as a proposal, marked, never as a stated fact.
4. Route, do not block. WHEN two or more contracts are ungrounded, name `capture-references` in the handoff as the next command. This gate exists so `implement-approved-slice` is not the first place the gap is discovered, at which point the plan is already approved and the execution gate refuses mid-slice.
5. Carry the marks forward. Every `[ungrounded: ...]` marker SHALL survive into the persisted artifact. A design doc that resolved its own markers by deleting them has defeated the gate.
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
Use the adaptive ending format of `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract`. Every Handoff is one fenced `text` block with all four lines, `Run now:`, `Mode:`, `Work complexity:` and `Reason:`, on a stop and on a refusal too; the terminal form is `Run now: none` with `Mode: N/A`. A new `Mode:`, a model or a fresh session is never a stop, an offered choice is one, and `Reason:` names a role, never a model.
### Definition of done (command output)
- `scripts/check-plan-coverage.sh <task-folder>` was run against the task folder and reports no unmatched pair, or the run's unavailability is stated in `### Command transcript` and the three rules were checked by reading. A plan reported complete over an unmatched pair is invalid output.
- Output is sliced (or single-phase with explicit justification in `### Command transcript`); each slice/phase has objective, scope, risks, validation, and exit criteria.
- No opportunistic refactors; dependencies and ordering are explicit.
- Any new behavioral commitment not in `DECISIONS.md` is labeled `PROPOSED` with upstream routing, or rests on a cited provisional P-N (ADR-0233).
- Output ends with a complete `### Handoff` block per the adaptive format in `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract`. A response that ends after `IMPLEMENTATION_PLAN.md` content without a complete Handoff is invalid output.
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
Prefer a boring, safe, reviewable plan over a clever or wide-ranging one.
