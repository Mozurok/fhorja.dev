---
name: frontend-system-design
description: Produce a staff-grade frontend system-design RFC for the active task: a 12-section design document (problem, requirements, architecture, data model, API and interface contract, rendering and delivery, state management, performance budget, accessibility, security, rollout, trade-offs) covering web and mobile, persisted as FRONTEND_SYSTEM_DESIGN.md. The default mode writes the design doc for real work; an --interview mode reframes the same structure for a frontend system-design interview round (RADIO-aligned). Capability-routed, not React-specific. Use when a frontend feature or surface needs an architecture-level design before planning and slicing, or when preparing a system-design interview artifact. Do not use to frame whether the problem is right (use problem-framing), to slice an already-designed change (use implementation-plan), to analyze blast radius (use impact-analysis), to review an API contract in isolation (use api-contract-review), or with no active task folder (run task-init first).
metadata:
  category: discovery-and-scoping
  primary-cursor-mode: Agent
  multi-repo-aware: false
  context-layers-consumed: [memory]
  context-layers-produced: [memory]
  tools: [Read, Write, Edit, Bash, Glob, Grep]
  x-wos-profiles: [full]
  provenance: first-party
  token-budget: 3200
  suggested-model: claude-sonnet-4-6
---
# frontend-system-design

Act as a staff frontend engineer writing the system-design document for a frontend feature or surface, so the architecture is decided and reviewable before any slicing or code.

Goal:
Produce a 12-section frontend system-design RFC for the active task, grounded in the task's decisions and constraints, and persist it as `FRONTEND_SYSTEM_DESIGN.md`. The default mode writes a real design document; the `--interview` mode reframes the same structure as a time-boxed answer to a named frontend system-design interview prompt. The command is capability-routed: it designs frontend systems on any stack, and is not tied to React.

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
- TASK_STATE.md, SOURCE_OF_TRUTH.md, DECISIONS.md (the design must respect locked decisions)
- IMPACT_ANALYSIS.md and INVARIANTS_AND_NON_GOALS.md when present
- the feature or surface to design (web, mobile, or both), named in the task or the prompt
- for `--interview` mode: the interview prompt (for example "design a news feed", "design an autocomplete"), and optionally a time box
- relevant external references already captured in `projects/<client>__<project>/REFERENCES.md` (read-only grounding)

Task repository files to create or update:
- `FRONTEND_SYSTEM_DESIGN.md` in the active task folder (default mode): the 12-section RFC.
- `FRONTEND_SYSTEM_DESIGN_INTERVIEW.md` in the active task folder (`--interview` mode): the same 12 sections reframed as an interview answer. Keep the two files distinct so a real design doc and an interview artifact never overwrite each other.

Operating rules:
- Do not implement product code. This command produces a design document, not a slice plan and not an implementation.
- **Handoff:** end with the adaptive `### Handoff` block per `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full).
- **Capability-routed, not stack-locked.** Design for the stack the task actually uses (read it from SOURCE_OF_TRUTH.md or DECISIONS.md). Name React, React Native, or any framework only when the task already chose it; never assume one. The structure below holds for any frontend stack.
- **The 12 sections (default mode).** Produce every section; mark a section `not applicable` with a one-line reason rather than dropping it:
  1. Problem statement and context: the user or business problem, scope boundaries, who consumes this surface.
  2. Requirements: functional and non-functional, split explicitly; core versus nice-to-have; success metrics.
  3. High-level architecture: the components and their relationships (view layer, state or store, data-access or networking layer, server or BFF), and the rendering surface boundary.
  4. Data model: entities, fields, what is server-originated versus client-only, cache shape and invalidation.
  5. API and interface contract: client-server transport (REST, GraphQL, WebSocket, SSE), payload shape, pagination, error and retry semantics, and the inter-component contracts.
  6. Rendering and delivery: the rendering strategy per surface (SSR, SSG, ISR, streaming, server components, or client-side) with a TTFB, SEO, or personalization rationale; CDN or edge where relevant. For mobile, the navigation and screen-load strategy.
  7. State management: local versus global versus server-cache state; real-time sync transport when relevant; optimistic updates.
  8. Performance: a numeric budget. For web, Core Web Vitals (LCP, INP, CLS) plus bundle size; for mobile, startup or TTI, frame budget, and list performance. State the percentile and the measurement source; do not assert a number without a source (mark `PROPOSED-pending-baseline` when unmeasured). Compose with `performance-budget` rather than duplicating it when a budget artifact already exists.
  9. Accessibility and i18n: the conformance target, keyboard and focus handling, and localization needs. Compose with `a11y-audit` for a per-criterion ledger.
  10. Security: the client-boundary threats (XSS, CSRF, CSP, token handling); when a BFF is in play, that tokens stay server-side.
  11. Rollout and migration: feature flags, incremental adoption, backward compatibility, deploy independence.
  12. Trade-offs and alternatives: the options considered and why the chosen design wins. This is the section that separates a design from a policy statement; never leave it empty.
- **`--interview` mode.** Reframe the same 12 sections as a time-boxed interview answer aligned to the RADIO framework (Requirements, Architecture, Data, Interface, Optimizations). Open by clarifying requirements and naming the non-functional constraints before designing; spend the largest share on the Optimizations and deep-dive (the staff differentiator); call out the client-side judgment a backend designer would miss (data fetching and caching, optimistic updates, rendering strategy, real-time transport, accessibility, perceived performance). Name the interview prompt at the top. Keep it scannable.
- **Ground design sources (ADR-0051).** When the surface has a design source (a Figma node, screen, or component spec), pull the exact node via the design MCP before writing measurements, tokens, or copy; do not invent values. When the design source is named but unavailable, ask for the link rather than guessing.
- **Ground external contracts.** When the design commits to an external library, SDK, or protocol, ground it in a captured `REFERENCES.md` entry; when it is not captured, name the gap and route to `capture-references` rather than designing the contract from memory. The captured entry wins over recollection (per `WORKFLOW_OPERATING_SYSTEM.md` `## Evidence priority`).
- **Respect locked decisions.** Read DECISIONS.md; the design must not silently reopen a locked decision. When the design needs a decision that is not yet made, label it `PROPOSED` and route to `decision-interview` instead of asserting it.
- **No invented metrics.** Performance thresholds, adoption numbers, and SLAs must cite a source (a measured baseline, a published standard, or a user-supplied target) or be marked `PROPOSED-pending-baseline`.
- Treat task-memory write policy per `WORKFLOW_OPERATING_SYSTEM.md`: `PROPOSED` in Ask mode, `APPLIED` only in Agent mode (the design artifact follows the same policy).
- **Self-review before emit.** Before writing the file, check it for placeholders, contradictions, an empty trade-offs section, and any section asserting a number without a source; fix them inline.

Required output:
1. The mode used (default RFC or `--interview`) and the surface or prompt being designed
2. The 12-section design (or the RADIO-framed interview answer), every section present
3. Exact `FRONTEND_SYSTEM_DESIGN.md` (or `FRONTEND_SYSTEM_DESIGN_INTERVIEW.md`) content, marked PROPOSED or APPLIED per editor mode
4. Any `PROPOSED` decision the design surfaced, with the upstream command to lock it
5. Recommended next command
6. Recommended editor mode
7. Why that is the correct next step

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
- All 12 sections are present (default mode) or the RADIO-framed answer covers them (`--interview` mode); a dropped section is invalid output unless marked `not applicable` with a reason.
- The trade-offs and alternatives section is non-empty and names the rejected options.
- No performance or scale number is asserted without a cited source or a `PROPOSED-pending-baseline` mark.
- The design respects DECISIONS.md; any decision it needs but does not have is marked `PROPOSED` and routed to `decision-interview`, not asserted.
- The artifact is marked PROPOSED (Ask) or APPLIED (Agent); the default and `--interview` modes write distinct files.
- Output ends with a complete `### Handoff` block per the adaptive format in `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract`.
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
A reviewer can read the document and understand the frontend architecture, the contracts, the budgets, and why this design beats the alternatives, with no number asserted on no evidence and no locked decision silently reopened.

<!-- cache-breakpoint -->
