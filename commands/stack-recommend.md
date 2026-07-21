---
name: stack-recommend
description: Research and recommend a technology stack for the active project by consulting official documentation, quality articles, and AAA company practices for latest stable versions. Accepts optional user-provided reference links. Produces a STACK_RECOMMENDATION.md inside the active task folder with versioned recommendations, compatibility notes, and trade-offs grounded in sources. Use when the project stack is undecided or needs validation, when starting a new project from zero, or when evaluating a technology upgrade. Do not use when the stack is already locked in DECISIONS.md, when the question is about a single library (use external-research), or when no active task folder exists yet (run task-init first).
metadata:
  category: discovery-and-scoping
  primary-cursor-mode: Ask
  multi-repo-aware: false
  context-layers-consumed: [memory, retrieved]
  context-layers-produced: [retrieved]
  tools: [Read, Write, Edit, Bash, Glob, Grep, WebFetch, WebSearch]
  x-wos-profiles: [core, full]
  provenance: first-party
  token-budget: 4500
  suggested-model: claude-sonnet-4-6
---
# stack-recommend

Act as a senior/staff engineering technology advisor with deep knowledge of production-grade tooling.

Goal:
Research and recommend a technology stack for the active project, grounded in official documentation (latest stable versions), quality technical articles, and AAA company engineering practices. Persist the recommendation as `STACK_RECOMMENDATION.md` inside the active task folder so that subsequent commands (`implementation-plan`, `project-bootstrap`, `design-bootstrap`) consume it as authoritative context.

This command produces recommendations that are:
1. **Version-pinned** to latest stable releases (never beta, RC, or canary)
2. **Compatibility-verified** across the recommended combination
3. **Source-grounded** with citations to official docs and quality articles
4. **Trade-off-aware** with alternatives for each layer

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
- project type or description (e.g., "SaaS task management app", "mobile fintech", "CLI developer tool")
- optional: constraints (e.g., "must use Supabase", "no AWS", "needs SSR", "mobile-first")
- optional: user-provided reference links to research (official docs, comparison articles, company tech blogs)
- optional: refresh flag (`refresh` to regenerate an existing `STACK_RECOMMENDATION.md`)

External web access:
- This command is in the authorized-command set in the spec `## Cross-cutting workflow guardrails ### External web access (centralized)`, scoped to stack and version research. The Research methodology below fetches official docs, release pages, and AAA-company stack disclosures. It MUST funnel every cited source into `REFERENCES.md` (capture-references entry format, deduplicated by URL), so the fetch is indistinguishable in the audit trail from a `capture-references` run.

Research methodology:
- **Step 1: Identify layers.** Based on the project type, determine which technology layers need recommendations (frontend framework, UI library, backend, database, auth, hosting, payments, analytics, testing, CI/CD, etc.).
- **Step 2: Search official sources.** For each layer, search for:
  - Official documentation and release pages (npm registry, GitHub releases, official blogs)
  - Latest stable version number and release date
  - LTS status and support timeline
- **Step 3: Cross-reference quality articles.** Search for recent (within last 6 months) comparison articles, benchmarks, and "best X for Y in [current year]" posts from reputable sources (official blogs, engineering blogs from AAA companies, well-known dev publications).
- **Step 4: Check AAA company usage.** Research what companies known for engineering excellence use for similar project types (Vercel, Stripe, Linear, Supabase, Shopify, Airbnb, Netflix, etc.). Cite specific tech blog posts or public stack disclosures.
- **Step 5: User-provided links.** If the user provided reference links, fetch and incorporate them. Cite findings alongside other sources.
- **Step 6: Verify compatibility.** Cross-check that recommended tools work together (version compatibility, known conflicts, peer dependency requirements).
- **Step 7: Synthesize.** Produce the recommendation with primary pick + runner-up per layer, trade-offs, and confidence level.

Operating rules:
- Do not implement production code.
- Only recommend STABLE releases. If the latest major version is still in RC/beta, recommend the previous stable and note the upcoming release.
- Always include the exact version number (e.g., "Next.js 16.2", not just "Next.js"). Pin to patch level when the patch carries a security fix.
- Every recommendation must cite at least one source (official docs, quality article, or AAA company blog).
- When user constraints conflict with best practices, honor the constraint and note the trade-off explicitly.
- When sources disagree, present both sides with citations and make a clear recommendation with stated reasoning.
- Do not recommend abandoned or end-of-life projects. Check last commit date and maintenance status.
- **Deprecation awareness**: actively check for sunset timelines, EOL announcements, and breaking migration requirements. Emit the `## Deprecation and sunset warnings` section when any recommended tool (or its predecessor commonly in use) has an active deprecation notice.
- **Version pinning**: always emit the `## Version pinning` section with a copy-paste-ready `package.json` (or equivalent for non-JS stacks like `requirements.txt`, `Cargo.toml`, `go.mod`) containing exact pinned versions for every recommended dependency.
- **Quick start**: always emit the `## Quick start` section with the minimal shell commands (3-8 lines) to scaffold a project using the recommended stack. Commands must be runnable as-is (no placeholders except project name).
- **Output density**: when the project has 5 or fewer layers, use a compact per-layer format (single table row per layer) instead of one full table per layer. Expand to full tables only when layers exceed 5 or when trade-offs are non-obvious.
- Treat task-memory write policy per `WORKFLOW_OPERATING_SYSTEM.md`: `PROPOSED` in Ask/Plan mode, `APPLIED` only in Agent mode.
- Capture sources into project-level `REFERENCES.md` using the `capture-references` format (deduplicated by URL).
- **Handoff:** end with the adaptive `### Handoff` block per `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full). Default next command: `implementation-plan` (stack decided, ready to plan) or `decision-interview` (if trade-offs need user input before locking). When the chosen stack will need per-feature library choices (lists, camera, forms, keyboard, sheets), also offer `feature-library-scout` as a downstream step (it picks the per-feature libraries one granularity below the layers this command chose, per ADR-0045).

Recommendation format (canonical):

```text
# STACK_RECOMMENDATION

## Snapshot metadata
- Project type: <from input>
- Last refreshed: YYYY-MM-DD
- Sources consulted: <N>
- Constraints applied: <list or "none">

## Project context
<One paragraph describing the project and what the stack needs to support>

## Recommended stack

### <Layer 1: e.g., Frontend Framework>
| Attribute | Value |
|-----------|-------|
| Pick | <Tool name> <exact version> |
| Released | <date> |
| LTS/Support | <status> |
| Runner-up | <alternative + version> |
| Why this over runner-up | <one line> |
| Source | [<title>](<URL>) |
| Used by | <AAA companies using this> |

### <Layer 2: e.g., UI Library>
...

## Compatibility matrix
| Tool A | Tool B | Status | Notes |
|--------|--------|--------|-------|
| Next.js 15.3 | React 19.1 | Compatible | Bundled |
| Tailwind v4.1 | Next.js 15.3 | Compatible | PostCSS plugin |
| ... | ... | ... | ... |

## Trade-off summary
| Layer | Primary pick | Runner-up | Key trade-off |
|-------|-------------|-----------|---------------|
| Frontend | Next.js 15.3 | SvelteKit 2.x | Ecosystem size vs bundle size |
| ... | ... | ... | ... |

## Confidence assessment
| Layer | Confidence | Reason |
|-------|-----------|--------|
| Frontend | HIGH | Stable, widely adopted, AAA-validated |
| Auth | MEDIUM | Two strong options; depends on tenant model |
| ... | ... | ... |

## Deprecation and sunset warnings
- <Tool vX>: <sunset date>, <migration path> ([source](<URL>))

## Version pinning
Partial `package.json` dependencies block with exact pinned versions for copy-paste:
```json
{
  "dependencies": {
    "<package>": "<exact-version>",
    ...
  },
  "devDependencies": {
    "<package>": "<exact-version>",
    ...
  }
}
```

## Quick start
Minimal commands to scaffold a project with the recommended stack:
```bash
# 1. Create monorepo
# 2. Install dependencies
# 3. Initialize key integrations
# ...
```

## Open questions (if any)
- <Question>: what would close it
- ...

## Sources
- [<Source 1>](<URL>): <one-line role>
- [<Source 2>](<URL>): ...
```

Sections with no content for the project type (e.g., "Payments" for an internal tool, or "Deprecation warnings" when none apply) must be omitted.

Task repository files to update:
- `projects/<client>__<project>/active/YYYY-MM-DD_<task-slug>/STACK_RECOMMENDATION.md` (create or regenerate)
- `projects/<client>__<project>/REFERENCES.md` (append newly captured sources per `capture-references` format; deduplicated by URL)
- `projects/<client>__<project>/active/YYYY-MM-DD_<task-slug>/TASK_STATE.md` (append to known facts: "Stack recommendation produced on YYYY-MM-DD")

Required output:
1. Resolved active task path.
2. Project type and constraints (echoed back).
3. Number of sources consulted and layers evaluated.
4. Whether this is a `create` or `refresh` of `STACK_RECOMMENDATION.md`.
5. Exact content for `STACK_RECOMMENDATION.md` using the canonical format.
6. Exact patch to `REFERENCES.md` for newly-captured sources, or `SKIP` if none.
7. Exact patch to `TASK_STATE.md` (known facts update), or `SKIP`.
8. Recommended next command (must exist in `commands/*.md`; verify against directory listing).
9. Recommended editor mode.
10. Why that is the correct next step.

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
- The proposed `STACK_RECOMMENDATION.md` includes all canonical metadata fields (`Project type`, `Last refreshed`, `Sources consulted`, `Constraints applied`).
- Every recommended tool has an exact stable version number, release date, and at least one cited source.
- The compatibility matrix confirms no known conflicts between recommended tools.
- The trade-off summary covers every layer with primary pick, runner-up, and key differentiator.
- Confidence assessment is present for each layer (HIGH/MEDIUM/LOW with reasoning).
- `## Version pinning` section is present with a copy-paste-ready dependency file (package.json, requirements.txt, or equivalent) containing exact pinned versions.
- `## Quick start` section is present with 3-8 runnable shell commands to scaffold the project.
- `## Deprecation and sunset warnings` section is present when any tool has an active deprecation notice; omitted only when no warnings apply.
- Sources used exist in project-level `REFERENCES.md` (pre-existing or newly captured this run).
- `### Artifact changes` marks `STACK_RECOMMENDATION.md` as `PROPOSED` in Ask mode or `APPLIED` only in Agent mode.
- The basename in the `Run now:` line corresponds to a real file in `commands/<name>.md`.
- Output ends with a complete `### Handoff` block per the adaptive format in `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract`.
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
Optimize for version accuracy (always latest stable, never outdated), source traceability (every pick has a citation), compatibility safety (no conflicting recommendations), and actionability (the next command can consume this as authoritative stack context without further research).

<!-- cache-breakpoint -->
