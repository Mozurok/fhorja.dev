# Eval scenario 06: external-research synthesis

- **Tags**: external-research, source-grounding, capture-references-integration, synthesis
- **Last reviewed**: 2026-05-08
- **Status**: active

## Goal

Validates that `external-research` produces a task-scoped synthesis grounded in `REFERENCES.md` entries, with every claim citing a source, the model's recommendation visually separated from the source-grounded analysis, and source acquisition routing through `capture-references` (no ad-hoc fetches).

This exercises:

- The "every claim cites a source" rule (the audit trail is load-bearing).
- The visual separation of recommendation (model's call) from analysis (sources' content).
- The `capture-references` integration (sources are appended to project-level `REFERENCES.md`).
- The Handoff routing to `decision-interview` or `implementation-plan` based on whether new questions surfaced.

## Setup

Assume an active task at `projects/acme__widget-pricing/active/2026-05-08_pick-queue-tech/` with the following key artifacts (paste these into your AI tool's context):

`TASK_STATE.md` (excerpt):

```text
# TASK_STATE
## Task summary
Pick a queue technology for the price-ingestion pipeline.
## Current phase
discovery
## Objective
Choose a queue suitable for batch price imports (~1M rows/day, retry-friendly, observable). Latency budget is generous; throughput and operational simplicity matter.
## Open questions / blockers
- Which queue tech fits this workload best?
```

`projects/acme__widget-pricing/REFERENCES.md` is currently empty (no entries; the user has not run `capture-references` yet for this task).

## Input prompt

```text
Run @commands/external-research.md

Active task: projects/acme__widget-pricing/active/2026-05-08_pick-queue-tech/
Research question: For a batch price-ingestion pipeline at ~1M rows/day, optimizing for retry-friendliness, observability, and operational simplicity (latency tolerant), which queue technology should we evaluate first?
Sources:
  - https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/welcome.html (AWS SQS overview)
  - https://docs.temporal.io/temporal (Temporal overview)
  - https://docs.celeryq.dev/en/stable/getting-started/introduction.html (Celery overview)
Output structure: comparison-table
Mode: Ask
```

## Expected response shape

- Response begins with external-research's persona line.
- The response identifies that all 3 sources are not yet in `REFERENCES.md` and proposes appending them via `capture-references` semantics. The proposed `### Artifact changes` includes a patch to `projects/acme__widget-pricing/REFERENCES.md` adding 3 new entries (one per URL, each with title, URL, accessed date, summary, optional verbatim key points, tags).
- The proposed `### Artifact changes` also includes `EXTERNAL_RESEARCH.md` PROPOSED in the active task folder.
- The proposed `EXTERNAL_RESEARCH.md` follows the canonical synthesis format: metadata block (research question, last refreshed, sources synthesized, source IDs, output structure), question recap, sources list, analysis with per-dimension citations like `[Source 1]`, comparison table, recommendation visually separated from analysis, optional open questions.
- Every claim in the analysis traces to one of the 3 sources via citation. Unsourced claims are absent.
- The recommendation paragraph is clearly labeled (e.g., `## Recommendation (model's call; not source-derived)`) and is separable from the analysis above it.
- The proposed `SOURCE_OF_TRUTH.md` patch adds a single `## External research` section with a relative pointer to `./EXTERNAL_RESEARCH.md`.
- `### Handoff` block at the end. `Run now:` is `decision-interview` (the synthesis usually surfaces decision questions about ops fit) or `implementation-plan` (if the synthesis closed the question). Mode B `Resume context:` includes the active task path.

## Pass criteria

1. **REFERENCES.md patch**: `### Artifact changes` includes 3 PROPOSED entries to `REFERENCES.md`, one per URL, each with title, URL, `Accessed: 2026-05-08`, summary, and tags.
2. **EXTERNAL_RESEARCH.md structure**: includes metadata block (with all required fields), question recap, sources list, per-dimension analysis, comparison table (the requested output structure), recommendation, and (optionally) open questions.
3. **Citation discipline**: every concrete claim in the analysis traces to a source via inline citation (e.g., `[Source 1]`, `[Source 2]`, or by source title). Unsourced claims are absent.
4. **Recommendation visually separated**: the `## Recommendation` section is clearly marked as the model's call, distinct from the source-grounded analysis above it.
5. **SOURCE_OF_TRUTH.md cross-link**: a single `## External research` section pointing to `./EXTERNAL_RESEARCH.md` is added.
6. **No fabrication**: the response does not invent claims about queue tech that the cited sources do not contain. A claim like "Temporal scales to 100M events/day" must trace to one of the cited sources or be marked `[unclear from source]`.
7. **Handoff intact**: response ends with a complete Handoff. `Run now:` is `decision-interview` or `implementation-plan`. adaptive handoff block has the task path.

## Failure modes to watch

- **Synthesis without source capture**: response writes EXTERNAL_RESEARCH.md but does not propose appending the 3 URLs to REFERENCES.md. The audit trail is broken; sources used for synthesis must be captured.
- **Hallucinated metrics**: the response cites specific throughput numbers, latency benchmarks, or cost figures that are not in the linked source pages. Watch for "Temporal handles 1M events/sec" or "SQS costs $0.40/million messages" without a verbatim citation.
- **Recommendation embedded in analysis**: the recommendation paragraph is mixed into the analysis dimensions rather than separated. Reader cannot distinguish what the sources say from what the model concludes.
- **Comparison table with empty cells filled in**: the table marks cells as "good" / "bad" or "high" / "low" without source backing. If a source does not address a dimension, the cell should be `[unclear from source]`, not invented.
- **Wrong routing**: response recommends `pr-package` or `implement-approved-slice` after the synthesis. The synthesis is discovery; the next step is decision (decision-interview) or planning (implementation-plan), not execution.

## Notes

- Related ADRs: [ADR-0007](../../docs/adr/0007-project-level-memory.md) (REFERENCES.md as project-level memory; sources outlive the task).
- Related commands: `commands/external-research.md`, `commands/capture-references.md`. The two are complementary: capture-references records single sources at the project level; external-research synthesizes across many.
- This scenario uses 3 well-known external services as sources to keep the synthesis evaluable; a real run would use the user's actual candidate technologies. The structure of the test (3 sources, comparison-table output, citation discipline) generalizes.
- The "no fabrication" rule is the single most failure-prone aspect of this command. Models trained on broad web data will tend to know facts about SQS/Temporal/Celery that are not in the specific source pages cited; the rule says they must cite or omit, not pull from training memory.

## History

- 2026-05-08: scenario authored. Initial pass criteria defined; not yet run against a model.
