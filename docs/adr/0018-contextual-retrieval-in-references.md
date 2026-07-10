# ADR-0018: Contextual retrieval in REFERENCES.md

- **Status**: Accepted
- **Date**: 2026-05-18
- **Tags**: context-engineering, retrieval, cross-source-context, human-readable-RAG

## Context

Anthropic's Contextual Retrieval technique (2024) showed that prepending chunk-specific context before embedding cuts retrieval failure rates by up to 67 percent on benchmark RAG tasks (combined with BM25 and reranking). The underlying insight is that "this paragraph means X" depends on document-level context that gets lost when chunks are embedded in isolation.

The WOS does not host a vector database. `capture-references` produces a markdown-based, human-readable, dedup-by-URL reference store at `projects/<client>__<project>/REFERENCES.md`. `external-research` reads that store and synthesizes a per-task `EXTERNAL_RESEARCH.md` with a model recommendation. Both commands are content-grounded ("never invent claims; cite every assertion").

Three failure modes the lack of cross-source context creates in this human-readable RAG analogue:

1. **Sources read as a flat list**. The current entry shape captures URL, accessed date, summary, optional verbatim key points, and tags. The RELATIONSHIP between sources (do they reinforce / contradict / address different aspects?) is implicit. A reviewer scanning REFERENCES.md cannot tell at a glance which sources reinforce vs. contradict.
2. **External-research synthesis underspecified on relationship**. The current synthesis recommendation can name sources but does not consistently surface "Source A is competitor framing; Source B is regulatory baseline; Source C disagrees with A's framing". The relationship language depends on the model inferring it from summaries, which is unreliable.
3. **Re-capture loses cross-source context.** Dedup-by-URL updates `Accessed:` but does not refresh the relationship-to-other-refs context. If new sources were captured after, the existing source's relationship is stale.

The Anthropic technique solves these for vector stores by prepending chunk-specific context at embed time. The WOS adopts the human-readable analogue: capture cross-source context AT CAPTURE TIME and surface it in synthesis.

## Decision

The WOS extends the `capture-references` canonical entry shape and updates `external-research` to consume it:

1. **New required field in capture-references entry shape**: `Context within project`. 1-3 sentences naming (a) how the source relates to the active project's objective from `PROJECT_CHARTER.md`; (b) the relationship to other refs already in `REFERENCES.md`. Vocabulary is open but specific phrases are encouraged: `complements <existing-tag>`, `contradicts <existing-tag>`, `regulatory baseline`, `customer-testimonial that disagrees with <existing-tag>`, `competitor-framing`, `mirror-of <existing-tag>`, `addresses a separate aspect not covered by existing entries`. When this is the first reference in the project, the value is `first reference in this project`.
2. **Required at all depths**. `summary` depth (the default) and `detailed` depth both include `Context within project`. Empty or vague values ("related to the project", "useful context") should be rejected at capture time; the field must name a specific relationship.
3. **Grandfathering rule**: pre-slice-06 entries (captured before this ADR shipped) are grandfathered. Lint does NOT inspect `REFERENCES.md` (gitignored at the project level anyway). Existing entries without the field remain valid; only NEW captures must include it.
4. **External-research consumption**: when reading `REFERENCES.md`, the synthesis must surface the cross-source context in the recommendation. Distinguish three relationship types:
   - **Reinforcing**: multiple sources agree on a claim. Recommendation can rely on the convergence.
   - **Contradicting**: factual disagreement that needs resolution. Recommendation must name the disagreement and route to `decision-interview` (or escalate).
   - **Different framing**: sources address different aspects of the same question; not a contradiction. Recommendation can synthesize across them without resolving.
5. **Stale-context handling**: if a source's `Context within project` is missing (grandfathered) or feels stale to the model at synthesis time, the synthesis annotates `[Context within project: not captured; consider re-running capture-references on <URL>]` but does NOT block the synthesis. The user decides whether to refresh.

## Consequences

### Positive

- **Source relationships are now explicit**. A reviewer scanning REFERENCES.md sees `Context within project: contradicts <tag>` and immediately knows the landscape. The mental cost of inferring relationships from summaries drops to near zero.
- **External-research recommendations gain rigor**. The three-way reinforcing / contradicting / different-framing distinction is explicit; the recommendation can ground itself in the source relationships rather than the model's general impression.
- **Audit trail extends to relationships**. Every synthesis claim about "Sources A and C reinforce each other" can be checked by reading the captured Context within project fields. No hidden inference.
- **Aligned with Anthropic's contextual retrieval research without a vector DB**. The technique inspires the slice; the implementation stays in markdown for the WOS's multi-tool portability.

### Negative

- **Capture step is heavier**. Users (or the model proposing entries for user review) must produce 1-3 sentences of cross-source context per entry. For projects with many existing refs, this requires the user/model to scan REFERENCES.md before adding a new entry. Mitigation: the field is bounded (max 3 sentences); the cost is recoverable through the better synthesis downstream.
- **Vague entries possible**. A user can still write `Context within project: related to the project` and pass capture-review. Mitigation: the field's prompt explicitly asks for the two specific elements; vague entries are caught at review time, not by lint. Documented in `capture-references.md` operating rules.
- **Existing entries are inconsistent**. Pre-slice-06 entries lack the field; new entries have it. Mitigation: grandfathered; the user can re-run `capture-references` on existing URLs to refresh both freshness AND the cross-source context. Not enforced.

### Neutral

- The field name `Context within project` is verbose but unambiguous. A shorter name (`Relation:`, `Cross-ref:`) loses clarity for non-experts reading REFERENCES.md by hand.
- The rule for `external-research` is one new bullet in operating rules; the synthesis-format spec already supports including relationship language in the recommendation paragraph.

## Alternatives considered

### Alternative 1: embedding-based retrieval (vector DB)

- Embed every captured source; retrieve by similarity at synthesis time; use Anthropic Contextual Retrieval verbatim.
- **Rejected**: out of scope for the WOS. The workflow is markdown-based and multi-tool; adding a vector DB requires runtime infrastructure that does not fit the architecture (per PROJECT_CHARTER.md non-goals: "no application runtime").

### Alternative 2: post-capture cross-source context (inference at synthesis time)

- Capture sources as-is; the model infers relationships when external-research runs.
- **Rejected**: relationships shift as new sources are captured; inferring at synthesis time produces inconsistent results across runs. Capturing at the source's capture time pins the relationship to the moment of greatest context (the user is actively thinking about WHY this source is relevant).

### Alternative 3: separate `RELATIONSHIPS.md` file

- Keep `REFERENCES.md` shape unchanged; capture relationships in a parallel file.
- **Rejected**: split-brain. The source and its relationship are tightly coupled; reading them in two places adds friction. Single entry per source is cleaner.

### Alternative 4: structured tags (`relation: contradicts:<tag>`)

- Encode the relationship in machine-parseable tags.
- **Rejected for now**: premature structure. The human-readable prose is more flexible and captures nuance ("regulatory baseline that REINFORCES competitor framing in <tag> but DISAGREES on the implementation timeline"). A future migration to structured tags is possible if synthesis tooling emerges.

## References

- `commands/capture-references.md` (canonical entry shape; updated by this slice).
- `commands/external-research.md` (consumption rule; updated by this slice).
- `wos/project-level-memory.md ## Edge cases worth noting` (one-line pointer to this ADR).
- ADR-0007 (project-level memory; defines REFERENCES.md as part of project memory).
- ADR-0010 (centralized external web access; the only mechanism for capturing external sources).
- ADR-0012 (context budget; names the `retrieved` layer that REFERENCES.md and EXTERNAL_RESEARCH.md live in).
- Anthropic, "Contextual Retrieval" (2024): the inspiration; vector-DB technique adopted at the human-readable layer.
- Lewis et al., 2020, "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks": the original RAG framing.

## Notes

The slice deliberately stops short of automating relationship inference. Manual capture preserves the user's judgment at the moment of greatest context (when they are deciding WHY a source matters). Future slices may add a `validate-references` command that re-checks grandfathered entries; not planned now.

This slice opens Wave 3 (retrieval + evals) of the 2026-05-15 context-engineering uplift after the D-1 reassessment (D-8 of this task's DECISIONS.md) confirmed continuing with the full plan with modest scope adjustments to slices 08 and 11.
