# Eval scenario 70: ai-feature-eval-harness (dataset-backed eval plan for a product AI feature)

- **Tags**: ai-feature-eval-harness, llm-eval, success-criteria, held-out-dataset, code-then-llm-grading, adr-0048, planning-and-validation, wave-1-capability-expansion
- **Last reviewed**: 2026-06-24
- **Status**: active

## Goal
Verify that ai-feature-eval-harness designs a repeatable, dataset-backed evaluation plan for a model-backed product feature, and that its guardrails hold:
- Gates on a model-backed output: a deterministic feature routes to test-strategy, not an eval plan.
- Every success criterion is measurable, or is explicitly marked NEEDS a measurable definition; no vague criterion ("good answers") is left as a pass target.
- The dataset spec names size, sourcing, label schema, and a split with no train/eval leakage.
- Each criterion gets a grading tier (code-based first; LLM-as-judge only for nuanced criteria).
- The three boundaries are stated: vs test-strategy (deterministic tests), vs verify-against-rubric (judges Fhorja's own artifacts), vs ADR-0048 (code-graded tier IS Layer-1 evidence).
- The command plans the eval; it does not build or run the harness.

## Setup
An active task adding an LLM-backed support-reply feature (takes a ticket, produces a drafted reply). No labeled dataset exists yet. A sibling task is a deterministic currency-formatting utility.

## Input prompt (turn 1: the LLM feature, no dataset)
"Run ai-feature-eval-harness on the new AI support-reply feature. No eval dataset yet."

## Input prompt (turn 2: a deterministic utility)
"Run ai-feature-eval-harness on the currency-formatting helper."

## Expected response shape (turn 1: LLM feature, no dataset)
- Produces `<task>/AI_EVAL_PLAN.md` with measurable success criteria (e.g. groundedness/no-hallucination rate, helpfulness pass rate, refusal rate on out-of-scope tickets, p95 latency, cost per call), each with a target number.
- Vague asks are restated measurably or marked NEEDS a measurable definition with the resolving question; no bare "good replies" target.
- A dataset bootstrap plan: minimum viable size, sourcing (sampled real tickets + adversarial edge cases), label schema, and a held-out split with no leakage.
- A grading tier per criterion: code-based for objective ones (latency, cost, refusal-on-blocklist), LLM-as-judge with a locked rubric for nuanced ones (groundedness, helpfulness).
- A suite-level pass threshold and a regression rule; the code-graded tier is tied to the ADR-0048 deterministic gate.
- The three boundaries stated explicitly (vs test-strategy, vs verify-against-rubric, vs ADR-0048).
- Persists the plan (APPLIED in Agent mode) and routes Handoff to implementation-plan (slice the harness build) or decision-interview (lock the quality target).

## Expected response shape (turn 2: deterministic utility)
- Gates: returns a route to test-strategy ("deterministic behavior, no model-backed output"); does NOT author an AI_EVAL_PLAN.md for a pure function.

## What a FAIL looks like
- An eval plan is authored for the deterministic utility instead of routing to test-strategy.
- A success criterion is left vague ("answers should be good") with no measurable target and no NEEDS marker.
- The dataset spec omits the split or allows train/eval leakage.
- Every criterion is sent to an LLM judge (no code-graded tier), or the ADR-0048 composition is not stated.
- The command claims to have built or run the eval harness.
