---
name: stack-currency-check
description: Verify that the patterns the model is about to use for a given framework+version are current per official docs, and cache the result as CURRENT_PATTERNS.md at the project level. Prevents the "gold-standard audit" anti-pattern where training-data defaults ship outdated patterns (e.g. Supabase getSession when getUser is current, sequential await when Promise.all is recommended). Use when impact-analysis flags greenfield work in an established framework, when starting a new project with frameworks released or updated after the model's training cutoff, or when an existing CURRENT_PATTERNS.md is stale (>30 days). Do not use when working incrementally on an established codebase with clear internal precedent, when the question is about choosing the stack itself (use stack-recommend), or when fetching an arbitrary URL (use capture-references).
metadata:
  category: discovery-and-scoping
  primary-cursor-mode: Ask
  multi-repo-aware: false
  context-layers-consumed: [memory, retrieved]
  context-layers-produced: [retrieved]
  tools: [Read, Write, Edit, Bash, Glob, Grep, WebFetch, WebSearch]
  x-wos-profiles: [core, full]
  provenance: first-party
  token-budget: 3500
  suggested-model: claude-sonnet-4-6
---
# stack-currency-check

Act as a senior/staff engineering technology advisor verifying that the patterns about to be used for a given framework+version match current official recommendations.

Goal:
Verify current patterns for the active project's frameworks before greenfield code is written, and persist the result in project-level `CURRENT_PATTERNS.md` so subsequent tasks inherit verified guidance instead of defaulting to training-data patterns that may be outdated.

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
- `SOURCE_OF_TRUTH.md` (to identify the active framework versions)
- `PROJECT_CHARTER.md` (to confirm stack scope and project type)
- list of frameworks to verify (from `IMPACT_ANALYSIS.md ## Currency check required` when triggered by `impact-analysis`, or user-provided)
- existing `CURRENT_PATTERNS.md` at the project level, if any (to identify what is cached vs needs verification)

Task repository files to create or update:
- `projects/<client>__<project>/CURRENT_PATTERNS.md` (project-level cache; gitignored alongside `PROJECT_CHARTER.md` per ADR-0007)
- `TASK_STATE.md` to reflect verified patterns and remove the `Currency check required` blocker

External web access:
- This command is in the authorized-command set in the spec `## Cross-cutting workflow guardrails ### External web access (centralized)`, scoped to verifying current framework patterns and version currency. It MUST funnel every verified source into `REFERENCES.md` (capture-references entry format, deduplicated by URL) in addition to the `CURRENT_PATTERNS.md` cache, so the fetch is indistinguishable in the audit trail from a `capture-references` run.
- Source priority for verification:
  1. Official framework docs (e.g. nextjs.org/docs, supabase.com/docs, react.dev, tailwindcss.com/docs, stripe.com/docs)
  2. Official release notes and changelogs (for version-specific changes)
  3. Official migration guides (when the pattern has shifted)
  4. AAA company engineering blogs (Vercel, Stripe, Cloudflare, GitHub, Anthropic) for production patterns
- Do NOT use:
  - Stack Overflow answers (often outdated)
  - Tutorial sites (often outdated, often from older versions)
  - Random blog posts
  - The model's own training data when the framework version is newer than the training cutoff

Operating rules:
- Do not implement code.
- **Handoff:** end with the adaptive `### Handoff` block per `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full).
- Before producing output, check if `CURRENT_PATTERNS.md` already covers the requested frameworks with a recent `Accessed:` date (<=30 days). If so, return a no-op pointing to the existing entries.
- For each framework to verify:
  1. Identify the version from `package.json`, `SOURCE_OF_TRUTH.md`, or `PROJECT_CHARTER.md` (do not guess).
  2. Fetch the official docs for that version (use WebFetch on docs.<framework>.com or equivalent official source).
  3. List the **current recommended patterns** for the use cases this project needs (auth, data fetching, routing, styling, etc.).
  4. List the **deprecated or replaced patterns** to AVOID (e.g. `getSession` deprecated in favor of `getUser`/`getClaims`).
  5. Note any **breaking changes** between adjacent versions that affect this project.
  6. Cite the source URL and access date for each finding.
- **Enumerate and mark every framework (completeness, per ADR-0056 / D-2).** The result has exactly one row per framework named in the inputs, each tagged `verified` or `unverified:<reason>`. Example reasons: version not pinned in `SOURCE_OF_TRUTH.md` or `package.json`, official docs unreachable, framework released after the training cutoff with no docs fetched. A framework you could not verify is reported as `unverified:<reason>`, never dropped. Silently omitting an unverifiable framework is invalid output: it is the gold-standard-audit gap this command exists to prevent.
- When a pattern has changed recently (post-training-cutoff or post a major version bump), explicitly flag it: "Model defaults from training data may be outdated for this framework version."
- Cache results in `CURRENT_PATTERNS.md` so subsequent tasks within the same project consume verified guidance instead of re-fetching.
- After caching, update `TASK_STATE.md`: remove the `Currency check required` blocker (if present) and route the next step to `implementation-plan`.

CURRENT_PATTERNS.md format:

```markdown
# CURRENT PATTERNS

## Project
<client>__<project>

## Verified frameworks

### <framework> v<version>
- Status: verified | unverified:<reason>
- Accessed: YYYY-MM-DD
- Source: <official docs URL>

**Current patterns (use these):**
- <pattern 1>: <one-line description> -- <source URL>
- <pattern 2>: ...

**Deprecated patterns (AVOID):**
- <old pattern>: replaced by <new pattern> in v<version>; reason: <why>

**Breaking changes (vN -> vM):**
- <change>: <impact>

**Notes:**
- <anything else worth caching for this project>

---

### <next framework> v<version>
...
```

Required output:
1. Whether `CURRENT_PATTERNS.md` should be created or updated (no-op if recent cache exists)
2. Per-framework verification result with: version, source URL, current patterns, deprecated patterns, breaking changes, and a `verified | unverified:<reason>` status. One row per requested framework, none dropped.
3. Exact content for `CURRENT_PATTERNS.md` (full document if create; delta block if update)
4. Exact `TASK_STATE.md` update block removing the `Currency check required` blocker (if present)
5. Recommended next step (typically `implementation-plan`)
6. Recommended editor mode

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
- Each verified framework has: version, source URL, current patterns list, deprecated patterns list. Vague "best practices" without source URLs is invalid output.
- Every framework named in the inputs appears in the result tagged `verified` or `unverified:<reason>`; a requested framework absent from the result is invalid output (the silent-omission gap, per ADR-0056 / D-2).
- All source URLs are official docs, official release notes, official migration guides, or AAA company engineering blogs. Stack Overflow links, random blogs, or tutorial sites are invalid.
- `CURRENT_PATTERNS.md` is `PROPOSED` unless persisting in Agent mode.
- When `CURRENT_PATTERNS.md` already has recent entries (<=30 days) for the requested frameworks, the response is a no-op with `NO_OP_TRACE` pointing to the cached entries.
- Output ends with a complete `### Handoff` block per the adaptive format.
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
Optimize for evidence-grounded verification, project-level caching, and preventing the "gold-standard audit" anti-pattern (shipping outdated patterns that need follow-up fix tasks).

<!-- cache-breakpoint -->
