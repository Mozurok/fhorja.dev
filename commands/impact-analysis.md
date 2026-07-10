---
name: impact-analysis
description: Understand the requested change deeply enough to make safe workflow decisions, then persist the analysis as IMPACT_ANALYSIS.md in the active task folder. Per-repo subsections when multi-repo. Identifies blast radius, contract impacts, schema/runtime risks, and integration points before planning or coding. Use when a new task was just initialized, the task is still unclear or partially understood, the blast radius is not yet known, or the request may affect contracts, schema, integrations, runtime behavior, or critical user flows. Do not use when the task is already in a well-defined planning phase with valid impact analysis, the goal is only to sync task memory after progress, the main issue is an observed technical failure (use incident-triage), or the current need is to implement an already-approved slice (use implement-approved-slice).
metadata:
  category: discovery-and-scoping
  primary-cursor-mode: Ask
  multi-repo-aware: true
  context-layers-consumed: [memory]
  context-layers-produced: [memory]
  tools: [Read, Write, Edit, Bash, Glob, Grep]
  x-wos-profiles: [minimal, core, full]
  provenance: first-party
  token-budget: 3500
  suggested-model: claude-opus-4-7
---
# impact-analysis

Act as a senior/staff engineer performing a bounded, evidence-driven impact analysis for the active engineering task.

Goal:
Understand the requested change deeply enough to make safe workflow decisions, then persist the analysis in the active task folder.

Mandatory context bootstrap (before any output):
<!-- shared:mandatory-context-bootstrap -->
- Read these sections in `WORKFLOW_OPERATING_SYSTEM.md` first:
  - `## LLM execution contract`
  - `## Editor mode policy` (mode definitions only; the tool mapping table is lazy-loaded in `wos/editor-mode-mappings.md` and needed only for non-Claude-Code tools)
  - `## Global output contract` (including **Adaptive handoff** and **Mode selection rule**)
  - `## Cross-cutting workflow guardrails`
- **Bootstrap tiers (ADR-0025):** the light-weight commands (`branch-commit`, `what-next`, `where-we-at`, `slice-closure`, `compact-task-memory`) may skip `## Editor mode policy` good-fits lists and `## Cross-cutting workflow guardrails` sequencing heuristics, reading only the mode definitions and the core guardrail rules (routing memory, command-less input triage, official command names, material change, no-op). This reduces bootstrap from ~6,750 to ~3,500 tokens for these commands.
- Read additional sections only when relevant to this command's role.
- Read the `commands/` directory command inventory to ensure command names and availability are current.
- Align all routing recommendations and next-command suggestions with the current command set.
- **Official next-command names only:** every recommended next command (including the handoff `Run now` line) MUST be the basename of an existing `commands/<name>.md` file in this workflow repository. Never invent names.

Required inputs:
- active task folder path
- TASK_STATE.md
- SOURCE_OF_TRUTH.md
- current task/request description
- relevant real codebase context
- relevant tests, if available
- official external docs only if needed to understand framework/library behavior
- last completed step from TASK_STATE.md (command + summary)

Task repository files to create or update:
- IMPACT_ANALYSIS.md
- TASK_STATE.md

Operating rules:
- Do not implement anything.
- **Handoff:** end with the adaptive `### Handoff` block per `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full).
- **Substrate write protocol (per ADR-0034, K.2 2026-06-04 -- dogfood).** MANDATORY for every substrate write per `wos/substrate-peers.md`. Per `commands/_shared/substrate-write-protocol.md ## Concrete computation`:
  1. Compute `sha_before` via the canonical `sha_of_section` bash helper (or `null` only if the section did not exist prior to this write).
  2. Insert the transaction header on its own line IMMEDIATELY above the section heading: `<!-- wos:write owner=impact-analysis section='## X' run_id=<ULID-or-uuid> ts=<ISO-8601-ms-with-Z> reason=<<=80chars> mode=<applied|proposed> -->`.
  3. Write or update the section content.
  4. Compute `sha_after` via the same helper against the post-write section bytes.
  5. Append exactly one JSON line to `active/<task>/.wos/VERIFICATION_LOG.jsonl` per the 12-field schema in `wos/substrate-peers.md ## Audit trail`. `sha_after` MUST be valid SHA-256 hex (64 lowercase hex chars) -- NEVER `null` on applied writes per K.5 validator. `sha_before` is `null` ONLY on first write to a fresh section.
  6. impact-analysis writes ONE owned section (`TASK_STATE.md ## Active files in scope`) AND emits PROPOSED CO-WRITER blocks under `TASK_STATE.md ## Current known facts` + `## Risks to watch`. Distinct K.2 handling per role:
     - **Owner write** (`## Active files in scope`): mode=applied; full protocol per steps 1-5; this is impact-analysis's substrate write that K.4 drift-guard catches if skipped.
     - **Co-writer PROPOSED blocks** (`## Current known facts`, `## Risks to watch`): emit a PROPOSED block INSIDE the existing section with `<!-- PROPOSED by impact-analysis: ... -->` content marker. DO NOT emit a wos:write transaction header for the section -- ownership stays with sync-task-state. emit a single JSONL line per PROPOSED block with `event=propose`, `mode=proposed`, owner=impact-analysis. When `approve-proposed` later promotes the block, the OWNER (sync-task-state) emits the wos:write header + a JSONL line with `event=approve`.

  FORBIDDEN: half-compliant pattern (JSONL emitted but inline header omitted on the owner write, OR `sha_after` null on the applied write). K.4 drift-guard at next sweep Pre-flight will surface this command's writes if it skips the protocol.
- Do not assume undocumented business rules.
- Before producing output, inspect the latest `TASK_STATE.md` and determine whether `impact-analysis` is still the highest-value command now.
- If the latest state already contains a valid and current impact analysis with no material gap, do not rewrite artifacts just to restate them; return a no-op with the best next command instead.
- No-op rule for artifacts:
  - If `IMPACT_ANALYSIS.md` would not materially change, do not rewrite it.
  - If `TASK_STATE.md` would not materially change, do not rewrite it.
  - Still output a minimal NO_OP note for traceability, but keep it short.
- Keep the analysis bounded to directly affected code paths, contracts, data model, consumers, tests, runtime dependencies, and failure modes.
- Distinguish clearly between:
  1. confirmed facts from evidence
  2. assumptions or unresolved interpretations
  3. open questions that affect correctness
- If correctness depends on information not grounded in code, tests, docs, or explicit user input, stop and surface targeted questions instead of guessing.
- Prefer asking a few high-value questions over filling gaps with speculation.
- Avoid broad architectural exploration unless it is necessary for correctness.
- If production behavior could be affected, explicitly call out silent failure risk, backward compatibility risk, and rollout risk.
- Multi-repo handling: keys off the presence of `## Repositories` in `SOURCE_OF_TRUTH.md`. When the section exists (multi-repo task), produce per-repo blast radius assessments, one subsection per repo in `IMPACT_ANALYSIS.md` (`### Repo: <identifier>`). Each per-repo subsection covers the full `IMPACT_ANALYSIS.md must include` set for that repo. Reject silent omission of any repo listed in `## Repositories`. When the section is absent, produce a single flat `IMPACT_ANALYSIS.md` per the existing schema (no behavior change).
- Deliverable coverage (per ADR-0056): read `## Requested deliverables` in `TASK_STATE.md` when present; every direction MUST account for each in-scope row. IF a direction drops, defers, or narrows a named deliverable, THEN surface that de-scope as an explicit question or decision for `decision-interview`, never let it fall out silently. This generalizes the multi-repo no-silent-omission rule to user-named deliverables. WHEN the section is absent, no-op.
- **Currency check trigger (greenfield only):** during the affected-areas pass, classify each affected area as either "incremental" (existing code precedent in the area) or "greenfield" (no internal precedent). When at least one area is greenfield AND the project uses an established framework (Next.js, Supabase, React, Tailwind, Stripe, etc.) AND `CURRENT_PATTERNS.md` is absent or stale (>30 days) for that framework, add a `## Currency check required` section to `IMPACT_ANALYSIS.md` listing the frameworks needing verification, and route the next step to `stack-currency-check` BEFORE `implementation-plan`. Do NOT trigger this gate when all affected areas are incremental (existing patterns provide the precedent). It implements the greenfield clause in the spec `## Evidence priority`, preventing the gold-standard-audit anti-pattern.
- **Feature-library trigger (greenfield product surface, per ADR-0045):** when the affected areas include greenfield product features whose library choice is not yet settled (for example a large-list surface, camera, forms, keyboard, or sheets), and no `FEATURE_LIBRARIES.md` exists for them, note them in the analysis and offer `feature-library-scout` (or `feature-library-scout-fleet` for 3 or more such features) as a routed next step before `implementation-plan`. It is additive to and independent of the currency-check trigger (that verifies framework pattern currency, this picks the per-feature libraries); both may apply to one analysis, and neither replaces the other.
- **Optional blast-radius diagram (Mermaid, ADR-0047):** on request, append to `## Affected areas` a Mermaid flowchart of the change's blast radius (the changed module plus its inbound and outbound edges and contract or boundary touch points): strictly the dependency subgraph, not a whole-repo redraw, framed as a seed to verify that does not replace the prose blast-radius. Mermaid is host-rendered; no new dependency.
- Keep the output practical and reviewable, not essay-like.
- Update `TASK_STATE.md` only when the analysis introduces material changes (new facts, new blockers, changed risks, or changed next step).
- If no material state change exists, state that `TASK_STATE.md` should remain unchanged and explain why.

IMPACT_ANALYSIS.md must include:
1. Request understanding
2. Confirmed facts
3. Assumptions / unresolved interpretations
4. Affected areas (optionally with a Mermaid blast-radius subgraph, ADR-0047)
5. Risks and failure modes
6. Viable implementation directions: when 2 or more viable directions exist, a structured alternatives-with-trade-offs table (one row per direction: approach, key trade-off, effort, risk, reversibility) with the recommended pick called out. Omit the table only when a single direction is obvious. Per-decision rationale still lives in DECISIONS.md and ADRs (which own the chosen-design-plus-rejected-alternatives record); this table is the comparison spine, not a second decision record.
7. Recommended path
8. Open questions
9. Suggested next step
10. Recommended next command
11. Recommended editor mode
12. Why that is the correct next step

For multi-repo tasks (when `SOURCE_OF_TRUTH.md` has a `## Repositories` section): items 2-7 above are produced per repo, organized under `### Repo: <identifier>` subsections. Items 1, 8, 9, 10, 11, 12 are task-level (shared across repos). Cross-repo dependencies (e.g., backend change required before frontend can land) appear in item 5 (Risks and failure modes) and item 7 (Recommended path).

TASK_STATE.md update must reflect:
- current phase
- current known facts
- blockers / open questions
- risks to watch
- recommended next step
- current closure target, if clarified by the analysis

Required output:
1. Whether IMPACT_ANALYSIS.md should be created or updated
2. Exact content for IMPACT_ANALYSIS.md (full document if create/update; otherwise a short NO_OP note)
3. Exact TASK_STATE.md update block, or explicit `TASK_STATE: NO_CHANGE`
4. Recommended next command
5. Recommended editor mode
6. Why this is the correct next step
7. What should explicitly not be done yet

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
- Separates confirmed facts vs assumptions vs correctness-critical open questions.
- Blast radius is bounded to real evidence (no architecture fanfiction).
- `IMPACT_ANALYSIS.md` is `PROPOSED` unless persisting in Agent mode; `TASK_STATE.md` follows the global write policy.
- Multi-repo coverage: when `SOURCE_OF_TRUTH.md` has a `## Repositories` section, every listed repo has its own `### Repo: <identifier>` subsection in `IMPACT_ANALYSIS.md` with items 2-7 fully populated; silently omitting a listed repo is invalid output. Single-repo tasks (no `## Repositories` section) produce a flat `IMPACT_ANALYSIS.md` per the v1.0 contract.
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
Be evidence-driven, skeptical, bounded, and operational.
Optimize for clarity, low ambiguity, and safe downstream planning.

<!-- cache-breakpoint -->
