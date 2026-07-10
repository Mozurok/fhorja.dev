# ADR-0010: Centralized external web access

- **Status**: Accepted
- **Date**: 2026-05-09
- **Tags**: external-web-access, audit-trail, references, freshness-metadata, deduplication

## Context

Engineering tasks frequently depend on external sources: vendor docs, regulatory text, framework guides, comparison articles, RFC drafts. Without an explicit policy, every command could fetch URLs as needed (a `targeted-questions` run pulling from MDN, an `impact-analysis` checking the Postgres docs, an `implementation-plan` reviewing a vendor page). Three failure modes recurred when ad-hoc fetches were allowed:

1. **No audit trail**. The conversation showed conclusions drawn from external sources but did not record **which sources** were consulted, **when** they were accessed, or **what they actually said**. Reviewers could not verify the conclusions; future readers (the same user three months later, a teammate joining the project) had no way to retrace the research.
2. **Re-fetching the same sources**. A vendor's pricing page might be consulted by `decision-interview` on Monday and `pr-package` on Friday, with the second run unaware of the first. Beyond wasted effort, this allowed two different commands to draw subtly different conclusions from the "same" page that may have actually changed between fetches.
3. **Research orphaned to a single task**. Sources fetched during one task were lost when the task moved to `archive/`. The next task on the same project, often by the same user days later, had to re-discover the same sources without knowing they had been read before.

The workflow already had a primitive for project-level external memory: `REFERENCES.md` under `projects/<client>__<project>/`, with the canonical entry format defined by `capture-references` (URL, accessed date, summary, optional verbatim key points, tags). What was missing was the **rule** that all external web access flows through this primitive.

A second force pushed in the same direction: the v0.1.x release plans included Anthropic's "centralized web access" guidance from the Effective Context Engineering article and the "audit trail" property the AGPL-3.0 distribution model implicitly assumes (anyone can run the workflow on their own projects; their research should be recoverable per-user without depending on conversation transcripts).

## Decision

**All external web access in the workflow goes through one of exactly two commands**: `capture-references` (single-source records appended to project-level `REFERENCES.md`, deduplicated by URL) or `external-research` (multi-source task-level synthesis that itself routes acquisition through `capture-references` for each new URL). No other command may fetch a URL directly.

The rule is enforced normatively in `WORKFLOW_OPERATING_SYSTEM.md` → `## Cross-cutting workflow guardrails` → `### External web access (centralized)`, and explicitly cross-referenced from every command whose `Operating rules:` section lists external sources as inputs. Commands that need external context list `external web references via capture-references only (never ad-hoc fetches)` in their `Evidence priority:` block.

The rule has three load-bearing components:

1. **Single point of capture**: every URL the workflow has consulted lives in `projects/<client>__<project>/REFERENCES.md` with freshness metadata. The conversation transcript is not the audit surface; the file is.
2. **Single format for entries**: the canonical entry format (title, URL, accessed date, summary, optional verbatim key points, tags) is enforced by `capture-references` and consumed unchanged by `external-research`. Ad-hoc shapes are not allowed.
3. **Deduplication by URL**: re-running `capture-references` on a URL already in `REFERENCES.md` is a no-op (or an `Accessed:` date refresh, depending on staleness). The same URL never produces two entries.

Synthesis-level uses (vendor comparisons, regulatory evaluations, framework choices) route through `external-research`, which produces a task-scoped `EXTERNAL_RESEARCH.md` grounded in `REFERENCES.md` entries. Every claim in the synthesis cites a captured source; unsourced claims are invalid output.

## Consequences

### Positive

- **Auditable research**. Every conclusion drawn from external sources traces to a `REFERENCES.md` entry with an accessed date. Reviewers can verify; future readers can retrace; the AGPL distribution remains honest about what informed each decision.
- **Reusable across tasks**. Sources captured during one task remain available for all subsequent tasks under the same project. A vendor's pricing docs read for a Q1 evaluation are still there for a Q3 follow-up without re-fetching.
- **Deduplication is mechanical**. The same URL never produces two entries; the workflow does not accumulate noise from repeated reads.
- **Synthesis grounds in capture, not in training data**. `external-research` cites captured sources, not the model's general knowledge. This is the property that lets the workflow stay accurate when source pages have changed since the model's training cutoff.
- **The conversation transcript is freed from being the audit surface**. Compaction and `/compact` runs can drop verbose web fetch outputs without losing research; the file is durable.

### Negative

- **Two-step research workflow**. To consult a new URL, the user runs `capture-references` first, then proceeds. For one-off lookups this feels like ceremony; for task-relevant research it is the right discipline.
- **The rule is not mechanically enforced**. A command that violates the rule (an `impact-analysis` run that ad-hoc fetches a URL) would still produce output; the lint cannot detect this from the response alone. Enforcement is via per-command `Operating rules:` and reviewer attention; future tooling could harden this with a deny-list at the AI tool's web-fetch layer.
- **`projects/` is gitignored** (ADR-0007); the project-level memory does not sync between machines unless the user manually copies it. A user who works on the same project from two laptops needs to handle that themselves.

### Neutral

- The "every URL goes through one of two commands" rule is workflow-specific; users coming from looser workflows have to internalize it. The rule is documented in the WOS, explained in the FAQ, and exercised by eval scenario 09.

## Alternatives considered

### Alternative 1: Free ad-hoc web access per command

- Any command may fetch any URL as needed; conclusions are drawn inline.
- Rejected: no audit trail, no deduplication, no reuse across tasks. The three failure modes that motivated this ADR all return.

### Alternative 2: Project-level reference index without entry format constraints

- Allow commands to record references in `REFERENCES.md` but in their own ad-hoc shapes.
- Rejected: the canonical entry format is what makes `external-research` synthesis possible. Without a uniform format, the synthesizer would have to parse heterogeneous shapes; a small consistency cost upstream prevents a much larger one downstream.

### Alternative 3: Whitelist of approved sources per project

- Predefine which URLs are allowed; commands fetch from the whitelist only.
- Rejected: research is inherently exploratory; a whitelist forces premature commitment. The `capture-references` flow allows new URLs to be added with explicit metadata, which preserves the audit trail without restricting exploration.

### Alternative 4: Ad-hoc fetches but with mandatory post-fetch capture

- Commands may fetch URLs directly but must call `capture-references` after the fact.
- Rejected: this is the current rule with worse ergonomics. If `capture-references` happens anyway, putting it before the fetch (so the entry's accessed date is not retrofitted) is strictly better.

## References

- `WORKFLOW_OPERATING_SYSTEM.md` → `## Cross-cutting workflow guardrails` → `### External web access (centralized)` (the normative rule).
- `wos/cross-cutting-workflow-guardrails.md` → `### Why external web access is centralized` (the lazy-loaded motivational subsection).
- `commands/capture-references.md` (the canonical single-source capture command).
- `commands/external-research.md` (the multi-source synthesizer that consumes `REFERENCES.md` entries).
- [`docs/adr/0007-project-level-memory.md`](./0007-project-level-memory.md) (the project-level memory layer that `REFERENCES.md` lives in).
- [`evals/scenarios/09-capture-references-multi-url.md`](../../evals/scenarios/09-capture-references-multi-url.md) (deduplication invariant test).
- [`evals/scenarios/06-external-research-synthesis.md`](../../evals/scenarios/06-external-research-synthesis.md) (synthesis-grounded-in-references test).

## Notes

The "centralized" framing is deliberate: the rule is not "use a particular command for web access" (that would be implementation-specific); it is "external web access is a single workflow concern with a single audit surface". The two commands are the current implementation; if a future architectural change adds more commands that need external sources, they would route through the same primitive rather than introducing parallel paths.

This ADR was written after `external-research` shipped in May 2026 (the second of the two centralization commands). The rule itself predated the command (it was always "use `capture-references` for web access"); the shipping of `external-research` formalized the synthesis path that earlier had no canonical home.
