# ADR-0006: Lazy-load WOS pattern

- **Status**: Accepted
- **Date**: 2026-05-08
- **Tags**: token-economy, context-engineering, prompt-caching, wos-structure

## Context

Every command in this workflow is supposed to "read these sections of `WORKFLOW_OPERATING_SYSTEM.md` first" as part of its mandatory context bootstrap. With 33 commands, the WOS is loaded at the start of every run; in cached scenarios it sits in the prompt cache, in uncached scenarios it pays full cost on every cold start.

Two trends made the WOS-load cost worth attacking:

1. **The WOS grew**. As more commands landed (multi-repo support, db-context-supabase, project-level memory, incident-triage, etc.), normative content accumulated inside the WOS. The 18,786-token baseline (measured 2026-05-07) reflected real growth, not bloat per se: each section was load-bearing for some command. But not for **every** command.
2. **Cache thresholds matter**. Anthropic's prompt caching has a 5-minute default TTL. Sessions that hit the cache pay roughly 0.1× per cached read; sessions that miss pay 1.0× plus a 1.25× write cost. The minimum cacheable size for Opus 4.7 is 4,096 tokens. The WOS clearly exceeded that, so caching worked, but the per-cache-write cost still scaled with WOS size.

The empirical observation: many WOS sections are **routing-critical at every command run** (e.g., `## LLM execution contract`, `## Editor mode policy`, `## Global output contract` core), but others are **reference-heavy and only consulted when something specific comes up** (e.g., the full directory tree, the per-command role detail with distinctness rules, the multi-repo schema with locked decisions D1-D7). Loading the second set every run was paying for context the model rarely used.

The "context engineering" research literature (Anthropic effective-context-engineering, Agentic Context Engineering arxiv 2510.04618, 12-Factor Agents F3 "own your context window") all converged on the same heuristic: **just-in-time loading beats upfront loading** for content that only some runs need. Combined with Anthropic's "compaction" beta (drop messages older than a threshold while keeping a summary), this argued for a structural split: keep routing content inline; move reference content to lazy files that each command can load **only when needed**.

## Decision

WOS sections are split into two tiers:

- **Inline (always loaded)**: definitions, decision tables, normative rules, routing indexes, capability rubrics, cross-cutting guardrails. The WOS keeps these because every command's `Mandatory context bootstrap:` cites them.
- **Lazy-loaded**: per-command role detail, sequencing heuristics, multi-repo schema/decisions/invariants, full directory trees, lifecycle narratives, motivational rationale, calibration vignettes. These live as separate files under `wos/<topic>.md`, each with a header explaining when to load it.

The WOS section that would have carried the lazy content is replaced by a **compact stub** plus a pointer line: "For the full <thing>, load `wos/<topic>.md`." The stub keeps the routing-critical fragment inline; the pointer tells the reader where to find the rest.

Each `wos/<topic>.md` file follows a uniform pattern:

1. Title line referencing the source section.
2. A "Load this file when:" block listing the specific triggers (specific routing question, contributor onboarding, edge-case clarification).
3. A "Single-task day-to-day execution does not need this file" note, so casual readers do not over-load.
4. The full content that was lifted from the WOS, organized as the original section.

The split is incremental: rounds 1-6 (May 2026) moved Command roles, Cross-cutting workflow guardrails, Multi-repo support v1, Repository structure, Project-level memory, and Global output contract non-normative subsections to lazy files. Cumulative WOS reduction: 29.2% (18,786 → 13,298 estimated tokens).

The Minimum read map at the top of the WOS is updated after every round so readers (humans and agents) can see which lazy files exist and when to load them.

## Consequences

### Positive

- **Lower context cost on every command run**. The WOS body shrinks from ~18.8k to ~13.3k tokens; commands that do not need the lazy content do not pay for it.
- **The lazy files are still in the repo**. Anyone needing the full reference (multi-repo schema, full directory tree, per-command role distinctness rules) can load the topic file on demand. No information is lost; only the loading discipline changed.
- **Per-topic ownership**. Each lazy file has a clear scope and lifecycle. Editing the multi-repo schema means editing `wos/multi-repo-support.md`; the WOS stub stays stable.
- **Reduces per-command cognitive load**. A new contributor reading `commands/task-init.md` is no longer flooded with context they do not need at first.
- **Plays well with cache**. The reduced WOS still exceeds the 4,096-token cacheable minimum, so caching benefits remain. Lazy files are **not** loaded by default and therefore do not enter the cache unless a specific command actually needs them.

### Negative

- **Two-step lookup for some content**. A reader who used to find the full directory tree in the WOS now has to follow a pointer to `wos/repository-structure.md`. The pointer is explicit, but the indirection is real.
- **Authoring discipline required**. Each new WOS section has to be evaluated for "is this routing-critical or reference-heavy?". Misjudging the split (putting reference-heavy content inline; or, worse, putting routing-critical content in a lazy file) re-introduces the cost or breaks routing.
- **Diminishing returns past round 6**. Further reductions would require lazy-loading sections that **are** consulted at every command run (Editor mode policy, Default workflow, Recommended workflows by task shape). That trades architectural clarity for marginal token savings; the project chose to stop at the natural boundary.

### Neutral

- The exact threshold for "routing-critical at every command run" is judgment, not a mechanical rule. Some sections are borderline (e.g., `## Anti-patterns` is informational but useful at every run). Those stay inline by default.

## Alternatives considered

### Alternative 1: Compact the WOS in place, no lazy files

- Tighten wording, remove redundancy, shrink each section.
- Rejected: the content is dense and largely necessary; further compaction without splitting just removed useful detail. Token savings would have been smaller and harder to maintain.

### Alternative 2: Move all reference content to a single sidecar (`wos/reference.md`)

- One large file instead of per-topic files.
- Rejected: a single sidecar has the same load-everything-at-once cost as the original WOS. Per-topic files let consumers load only what they need.

### Alternative 3: Per-command preloading

- Each command's `Mandatory context bootstrap:` lists the exact sub-sections it needs (no whole-WOS load).
- Rejected: would require restructuring the WOS into many micro-sections and rewriting every command's bootstrap. Architectural complexity not worth the additional savings, especially given prompt caching already amortizes the WOS load across multiple runs in a session.

## References

- `WORKFLOW_OPERATING_SYSTEM.md` → top-of-file "Minimum read map" (lists every lazy file and when to load it).
- `wos/command-roles.md`, `wos/cross-cutting-workflow-guardrails.md`, `wos/multi-repo-support.md`, `wos/repository-structure.md`, `wos/project-level-memory.md`, `wos/global-output-contract.md` (the six lazy topic files).
- `scripts/measure-tokens.py` (token footprint measurement script with cache scenario projection).
- `scripts/baseline-2026-05-07.md` (pre-pilot baseline) and `scripts/baseline-2026-05-08-post-rounds-5-6.md` (post-round-6 snapshot).
- [Anthropic effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) (just-in-time vs upfront loading; accessed 2026-05-07).
- [Agentic Context Engineering, arxiv 2510.04618](https://arxiv.org/abs/2510.04618) (brevity bias and context collapse; accumulate-don't-summarize for state files; accessed 2026-05-08).

## Notes

The WOS_CORE ≤3k tokens target appeared early on the ROADMAP (Wave 2). After 6 rounds, the WOS sits at ~13.3k. The remaining gap (~10k) would require lazy-loading sections that are normative at every run, which trades architectural simplicity for marginal token savings. The project explicitly declared the WOS_CORE ≤3k aspiration **at a natural stopping point** rather than chasing it indefinitely. That declaration is recorded in ROADMAP Wave 2 and in the post-round-6 commit message.
