# ADR-0195: code-context-map keeps global RRF ordering

- **Status**: Accepted
- **Date**: 2026-09-07
- **Tags**: code-context-map, ranking, rrf, audit, supersedes-adr-0072
- **Supersedes**: ADR-0072 only for the guarantee that a symbol with zero keyword hits cannot outrank a matching symbol

## Context

The optional keyword rerank in `commands/code-context-map.md` promises both descending
reciprocal rank fusion (RRF) and absolute priority for matching symbols. Independent verification
confirmed their contradiction in `verify-batch-1.json`, finding 0. With `k = 60`, a zero-hit symbol
at fan-in rank 1 scores `1/61 = 0.01639344`. A matching symbol at fan-in rank 500 and keyword
rank 100 scores `1/560 + 1/160 = 0.00803571`. Global RRF puts the zero-hit symbol first.

ADR-0072 explicitly chose a blend of structural and lexical signals and rejected replacing the
structural signal with keyword order. It also records that textual matches can come from comments.
The original implementation notes describe a prose ranking rule, with no backend ranking script.
The contradiction therefore lives in the instruction the map generator follows.

## Decision

Keep global descending RRF over the existing Layer 2 candidate set, with `k = 60` and zero
keyword contribution for nonmatches. Remove the absolute matching-first guarantee from the
command. This preserves the existing blend without adding a grouping stage. The candidate set,
default behavior without keywords, Layer 1, module ordering, and ranking explanations remain
unchanged. `commands/code-context-map.md` holds the operational rule; eval scenario 27 exercises
both the default path and the counterexample.

## Consequences

- A structurally central nonmatch can appear before a weakly ranked match. Keywords influence
  ordering but do not guarantee placement above every nonmatch.
- If all candidates have zero hits, their RRF order reduces to fan-in order. If all match, the
  existing two-term RRF calculation applies to every candidate.
- `--explain-ranking` still exposes the ranks and score that determine placement. A zero-hit
  candidate shows keyword rank `none`.
- This resolves a contract contradiction. No comparative relevance benchmark was run, so this
  decision makes no claim that global RRF improves retrieval accuracy over matching-first grouping.

## Alternatives considered

### Matching-first grouping

Place every matching candidate before every nonmatch, then sort by RRF within each group.
This preserves the guarantee but changes the global ordering already specified by the command
and template. It makes even an incidental textual match outrank every nonmatch. The existing
blend is retained because it lets structural relevance compete with the lexical signal.

### Disable keyword reranking

Remove the optional feature and always sort by fan-in. This avoids the contradiction but removes
the task-scoped relevance input. A correction to one incompatible guarantee preserves that input.

## References

- [ADR-0072](./0072-code-context-map-optional-keyword-rerank.md): optional keyword blend and conflicting guarantee.
- [ADR-0027](./0027-code-context-map-and-product-repo-artifacts.md): structural map and deferred retrieval extension.
- [ADR-0166](./0166-supersession-is-marked-on-the-superseded-adr.md): supersession metadata.
- `commands/code-context-map.md`: keyword rerank blend operating rule.
- `templates/CODE_CONTEXT_MAP.template.md`: ranking source and explanation format.
- `evals/scenarios/27-code-context-map.md`: ordering regression cases.
