# ADR-0038: Workflow tool as canonical parallel-orchestration primitive

- **Status**: Accepted (2026-06-05 PM lap, lived evidence)
- **Date**: 2026-06-05
- **Tags**: orchestration, workflow-tool, parallelism, structured-output, substrate-safety, sibling-of-adr-0036, sibling-of-adr-0034

## Context

Across the 2026-06-05 WOS session (K.6 maturity ladder first-lived-test + K.7 eval push + K.8 persona promotions L1->L3 + Phase 6 fleet pilot), the Workflow tool ran 11+ batches dispatching ~150+ parallel agents totaling ~5M subagent tokens. The patterns surfaced are now load-bearing in WOS operations:

- **Parallel-then-sequential-apply**: agents fan out in parallel returning structured outputs; main loop applies to substrate sequentially. Used in K.7 iter batches, K.8 fleet runs, Phase 6 pilot.
- **Structured-output schema**: each agent declares a JSON Schema for its return shape; the workflow tool forces the agent to call StructuredOutput; main loop consumes typed data. Eliminates prose-parsing failures.
- **Mega-batch intel-gathering**: one workflow batches 15-25 agents covering broad discovery (Figma reads, file reads, parallel drafts) before any synthesis.
- **Per-persona iteration batching**: N personas x M scenarios x 2 conditions dispatched together for K.7 eval throughput.

Three failure modes surfaced empirically:
1. **Substrate-bullet-orphan** (bug-class commit 615c6bb; detector commit 5840755): apply scripts appending bullets at section-end offsets that were 1+ lines BEFORE next H2 boundary, producing orphan bullets between sections. 8 orphans observed in pilot-repo substrate; K.5 validator passed (per-line shape ok) while file structure was broken.
2. **Schema-skip**: agents writing prose output without invoking the StructuredOutput tool the schema requires (~80% of one batch failed this way). Failure mode emerged in lap PM batch where 10 of 12 agents produced free-form content not consumable as typed data.
3. **Substrate write from parallel agents**: when an agent inside the workflow writes substrate directly (instead of returning a PROPOSED block for the main loop to apply), SHA chain integrity breaks under fan-out.

Without an ADR formalizing the safe pattern, future authors mis-use Workflow (e.g., sequential work where Agent fits better, or stateful prompts that break parallel safety, or write-from-agent shortcuts that break substrate). The ADR codifies the lived pattern + ties it to existing WOS contracts (ADR-0034 substrate-peers, ADR-0036 K.7 + L3 evidence weighting, wos/sub-agent-orchestration.md predecessor topic, wos/workflow-patterns.md new topic in commit 6b6414d).

## Decision

We adopt the **Workflow tool** as the canonical primitive for parallel agent orchestration in WOS. All future multi-agent fan-out work (audits, fleet operations, parallel discovery, parallel synthesis) MUST use the Workflow tool rather than ad-hoc Task spawning, shell parallelism, or improvised dispatch scripts.

This adoption is bound by three non-negotiable rules, derived from what worked and what failed across the K.2 / K.8 session:

**Rule 1 -- Structured output is mandatory.** Every workflow agent MUST declare and return a structured output schema. Free-form text dumps from workflow agents are forbidden. The main loop MUST be able to consume each agent's output as typed data, not as prose that needs re-parsing. This eliminates the class of failures where a parent agent extracts the wrong substring, misreads a heading, or hallucinates structure that the child never emitted. K.8's parallel persona dispatch succeeded because each worker returned a schema-bound block; earlier improvised flows failed precisely because they leaned on prose extraction.

**Rule 2 -- Substrate writes MUST be sequenced through a deterministic apply step in the main loop.** Parallel agents MUST NOT write to canonical substrate files (TASK_STATE.md, DECISIONS.md, IMPLEMENTATION_PLAN.md, SOURCE_OF_TRUTH.md, REFERENCES.md, or any project-level memory) from inside the workflow. The pattern is **parallel-then-sequential-apply**: N workers run in parallel and return structured output; the main loop then applies those outputs to substrate one at a time, in a defined order, with deterministic merge rules. This preserves substrate as a single-writer resource even when discovery is fanned out, and it makes the apply step independently reviewable, replayable, and testable.

**Rule 3 -- The apply step MUST detect and prevent the substrate-bullet-orphan failure mode** documented in `wos/bug-classes/substrate-bullet-orphan.md` (introduced in commit `615c6bb`) and enforced by `scripts/scan-substrate-orphans.py` (orphan detector landed in commit `5840755`). When applying writes from N parallel outputs, the apply step MUST: (a) anchor every appended bullet to an existing parent heading or list, (b) refuse to write bullets whose anchor was not located, and (c) run the orphan scanner against the touched files before declaring the apply step successful. This is the formalization of the exact failure that produced 8 orphans in `pilot-repo` during K.2 -- bullets were appended without verifying that the heading still existed in the file after parallel edits, leaving them stranded at the bottom with no semantic parent.

## Consequences

**Positive.**

- *Convergent safe pattern for future workflows.* All future workflow scripts now have one canonical shape (structured output + sequential apply + orphan check) instead of each author reinventing dispatch. This reduces the cognitive cost of writing new fleet commands and makes them mutually reviewable.
- *Complete prevention layer for the orphan failure class.* The bug class (`615c6bb`) names the failure, the detector (`5840755`) makes it mechanically visible, and Rule 3 makes running the detector part of the apply contract. Together they form a closed loop: a regression cannot land silently again.
- *Substrate stays single-writer under fan-out.* Reviewers reading TASK_STATE.md or DECISIONS.md after a parallel run still see a coherent, ordered diff -- not a race-condition merge.
- *Schema-bound outputs make worker results inspectable.* When a workflow misbehaves, the structured output is the source of truth for triage, not a transcript of free-form prose.

**Negative.**

- *Structured output schemas add upfront design cost per workflow.* Authors must define the worker output shape before dispatch instead of letting workers narrate. For one-off explorations this feels heavier than it is for production fleet commands.
- *Some existing workflows may need refactoring to return structured output instead of free-form prose.* The scope of this churn is bounded: only workflows still in `author` status need to be brought in line; workflows already shipped under the old pattern can be grandfathered until their next material change.
- *The apply step becomes a serial bottleneck.* By design -- that is what makes substrate writes safe under fan-out -- but it does cap the throughput gain of parallelization at "discovery is parallel, write is serial."

## Open follow-ups

- Schema-skip mode (10/12 agents in the PM lap failed to call StructuredOutput) needs further investigation. Hypothesis: longer/more-complex prompts may delay or skip the structured-output emission. Mitigation: keep prompts focused, explicitly emit `Return STRUCTURED OUTPUT with artifact='...' content='...'` as final instruction. Track in future iterations.
- Apply-step orphan check is currently manual (Python script). Future enhancement: auto-invoke `scripts/scan-substrate-orphans.py` as a pre-commit / post-apply hook in WOS infrastructure (`repo-consistency-sweep` Step 7 integration proposed in `docs/proposals/scan-orphans-sweep-integration.md` -- deferred when 10-of-12 workflow batch surfaced schema-skip).

## References

- ADR-0034 (substrate peers + worker contract; canonical substrate single-writer rules)
- ADR-0036 (K.7 oscillation + L3 evidence weighting; sibling ADR for the maturity ladder)
- `wos/workflow-patterns.md` (canonical patterns topic; commit 6b6414d)
- `wos/sub-agent-orchestration.md` (predecessor lazy-loaded topic for sub-agent design)
- `wos/bug-classes/substrate-bullet-orphan.md` (commit 615c6bb; bug class)
- `scripts/scan-substrate-orphans.py` (commit 5840755; orphan detector)
- Session evidence: ~150+ parallel agents across 11+ Workflow batches on 2026-06-05.
