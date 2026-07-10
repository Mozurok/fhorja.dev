# ADR-0076: Opt-in embeddings-free LEARNINGS pattern-mining pass

- **Status**: Accepted
- **Date**: 2026-07-02
- **Tags**: learnings, reflexion, pattern-mining, kura, in-context-grouping, no-embeddings, opt-in, additive, judge-py-pattern

## Context

ADR-0071 gave `LEARNINGS.md` entries a retrieval path: an optional `Tags:` bullet plus `scripts/rank-learnings.sh`, which scores entries by recency and keyword overlap against one query. Nothing groups entries into named recurring themes; that needs seeing many entries together, not ranking one query against them one at a time.

External research for this task's absorption candidates (`EXTERNAL_RESEARCH.md`) looked at Kura, an open-source reproduction of Anthropic's CLIO paper. Its meta-clustering stage runs five steps: take base clusters, optionally group them into neighborhoods (`reduce_clusters` embeds cluster representations and runs K-means), an LLM proposes higher-level category names per neighborhood, an LLM assigns each cluster to the best-fitting name, and the result is finalized with a `parent_id` link (`REFERENCES.md`, "Kura: meta-clustering core concept"). Only the neighborhood-grouping step touches embeddings; naming and assignment are already LLM-driven ("an LLM is prompted with the names and descriptions of all its child clusters"). At WOS scale (tens of `LEARNINGS.md` entries per project, not the thousands of conversations Kura targets), one in-context LLM prompt can do the naming-and-assignment work directly over the whole entry set, which means the embeddings stage is skippable rather than something to reimplement. Kura's checkpoint system (`REFERENCES.md`, "Kura: checkpoints core concept") is a second reusable shape: a file-based cache, JSONL by default, that is skipped on rerun when the input has not changed.

This task's `DECISIONS.md` R-1 rejects every embeddings, K-means, or vector-index mechanism found across the six candidate repos (kura, instructor, outlines, qdrant, langfuse, dspy) on charter grounds (no runtime services, no vector DB, no new Python dependency) and on the standing no-embeddings posture already set for `code-context-map` (ADR-0057, ADR-0072). D-1 in the same file scopes this task's build to A1 + A2 + A3, naming A3 (this pass) the cut line if implementation effort runs over budget.

## Decision

Add `scripts/mine-learnings-patterns.sh`: opt-in, read-only over `LEARNINGS.md`, no new command.

- **In-context grouping substitutes the embedding stage.** The script collects every conforming entry (heading plus the `Anchor`, `Tried`, `Failed because`, `Next time`, and optional `Tags` bullets) from `<project-dir>/active/*/LEARNINGS.md` and `<project-dir>/archive/*/LEARNINGS.md`, and assembles ONE bounded grouping prompt listing every entry by heading and anchor. The prompt asks the model to propose named recurring-pattern groups where every group lists its member entries by heading and anchor, mirroring Kura's naming-stage contract (the LLM sees names and descriptions of the children, never raw vectors); only the neighborhood-grouping step is replaced, because at this scale "every entry in one prompt" already is the neighborhood.
- **Tool call mirrors ADR-0019's convention.** The prompt is piped to an external CLI AI tool the same way `evals/scripts/judge.py`'s `call_tool()` does: `printf` the prompt on stdin, read the response on stdout. Default tool `claude code --print`, overridable with `--tool`.
- **File cache with skip-if-unchanged resume (the Kura checkpoint analog).** The result plus a header (date, corpus size, corpus SHA-256) is written to `<project-dir>/.wos-mined-patterns/patterns.md`. When a rerun's corpus SHA-256 (hashed over the assembled prompt) matches the cached value, the cached result is printed, the tool is not called again, and the script states that it reused the cache.
- **Bounded and reviewable before spend.** `--max-entries N` (default 120) caps how many entries enter the prompt regardless of corpus growth. `--dry-run` prints the assembled prompt and corpus stats with no tool call, so the prompt can be reviewed before it costs a real call.
- **Opt-in, no new command.** It ships as a standalone script, run on demand, the same packaging shape as `scripts/rank-learnings.sh` (ADR-0071). This task's `DECISIONS.md` D-2 already reserves that packaging shape (new standalone script under `scripts/`, not a new command) for the sibling A2 validator; this pass follows the same convention rather than becoming a `commands/*.md` entry.

## Consequences

- Closes a real gap next to ADR-0071: the ranker answers "what is relevant to this new task," this pass answers "what recurs across many tasks," and neither replaces the other.
- The prompt is bounded (`--max-entries`) so it cannot grow past a review-friendly size regardless of how many tasks accumulate `LEARNINGS.md` entries; a large corpus is truncated, not sent unbounded to the tool.
- Read-only: the script never writes a `LEARNINGS.md`, so ADR-0017's append-only invariant on that file is untouched. The only new artifact is the gitignored cache file under `<project-dir>/.wos-mined-patterns/`, which nothing else reads today.
- No new dependency, no runtime service, no vector index: the mechanism is one prompt and one cache file, consistent with R-1.
- Entries predating ADR-0071's five-bullet template (older `## Entry: <title>` headings that embed the anchor inline inside `Failed because` rather than as a standalone `Anchor:` bullet) are silently skipped, the same precedent `scripts/rank-learnings.sh` already set for headers it does not recognize. A corpus dominated by pre-ADR-0071 entries would under-report until those entries are reformatted or promoted.
- `count:commands` is unaffected; this is a script, not a command, so no registry, index-row, or skills-drift update is triggered by this ADR.

## Alternatives considered

- **Full Kura-style pipeline** (embed cluster summaries, run K-means neighborhoods, then LLM names and assigns). Rejected per R-1 and the ADR-0027 D-8 posture: it needs an embedding model, a new Python dependency, and, past a few dozen entries, a vector index, none of which the WOS charter allows.
- **A new dedicated command** (for example `learnings-pattern-mine.md`) instead of a script. Rejected: D-2 in `DECISIONS.md` keeps this task's absorb set to standalone scripts, and a review-facing, opt-in, on-demand pass does not need the command lifecycle (approval gates, a generated skill, four registry rows) that a first-class command carries.
- **Recursive multi-level grouping** (Kura's `reduce_clusters` can be called iteratively to build a hierarchy). Rejected for now: Kura's own docs note no explicit recursion depth or stopping criterion is documented, and the WOS `LEARNINGS.md` corpus is small enough that a single grouping level stays legible. Multi-level hierarchy is a YAGNI addition until a corpus is shown to need it.
