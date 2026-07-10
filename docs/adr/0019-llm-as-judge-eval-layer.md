# ADR-0019: LLM-as-judge eval layer

- **Status**: Accepted (the `judge.py` Python implementation is superseded by [ADR-0033](./0033-verify-against-rubric-stateless-subagent.md); the eval-scenario concept and locked-rubric layer remain in force)
- **Date**: 2026-05-18
- **Tags**: evals, observability, llm-as-judge, optional-second-pass, locked-rubric

## Context

The WOS manual eval harness (`evals/scripts/run-evals.sh`) walks through scenarios under `evals/scenarios/`; the user pastes each scenario's input prompt into their AI tool, reads the response against the scenario's `## Pass criteria` numbered list, and records the outcome in the scenario's `## History` section. The loop has been stable since slice ADR-0001 era but has three growing pains as coverage approaches 20+ scenarios:

1. **Reviewer fatigue degrades fidelity**. After 20+ scenarios, criteria get skimmed. The numbered list is supposed to be falsifiable; in practice, late scenarios receive less attention than early ones.
2. **Pre-release runs are expensive enough that they get skipped**. Anthropic's eval guidance ("run all scenarios before tagging a release; failures block release") only works if the run is cheap enough to actually do. At 14 scenarios, a full run takes ~30 minutes; at 30 scenarios, ~60 minutes; manual review at that scale is rarely done routinely.
3. **Regressions are detected qualitatively**. Today a scenario passes or fails based on the reviewer's judgment; there is no structured per-criterion record. Comparing "scenario 03 in model version A vs. B" requires reading two transcripts, not diffing two structured verdicts.

The Pragmatic Engineer's December 2025 piece distinguishes three eval types: code-based (deterministic checks), LLM-as-judge (model-as-evaluator with a rubric), and human (the highest fidelity). Hamel Husain's "Your AI Product Needs Evals" warns that LLM-as-judge WITHOUT a rubric is noise. Anthropic's test-evaluate guide emphasizes rubric-based judging with locked wording.

The WOS already has the rubric: every scenario's `## Pass criteria` numbered list IS the rubric. Adding an LLM-as-judge layer becomes a parsing-and-piping problem rather than a design problem.

## Decision

The WOS introduces an OPTIONAL LLM-as-judge layer:

1. **`evals/scripts/judge.py`**: Python script that extracts `## Pass criteria` from a scenario file, formats it with a LOCKED rubric wrapper (defined in the script as a module constant; changes require slice-history and ADR update), pipes the rubric to a configurable AI tool via stdin/stdout, parses per-criterion verdicts (PASS / FAIL / UNCERTAIN) plus an overall verdict using a strict regex, and emits markdown (default) or JSON (`--json`).
2. **Tool abstraction via `--tool <command>`**: the script does not call any vendor API directly. It pipes through a shell command the user supplies. Default: `claude code --print` (when available); users with Cursor / Codex / Copilot can supply equivalents. No API keys handled by the WOS; no vendor lock-in.
3. **`evals/scripts/run-evals.sh --judge` flag**: after each scenario, prompt the user for the path to the model's response, then call judge.py and display the structured verdict. Continues to the next scenario. Skippable per scenario (empty path on the prompt = skip).
4. **OPTIONAL second pass; never replaces manual review**: the judge's verdicts are ADVISORY. UNCERTAIN always defers to the human. FAIL is a hint to look closely; the human can override (and should log the override in the scenario's `## History`). PASS is a hint that the scenario looks good; the human can spot-check.
5. **Locked rubric wrapper**: the prompt the judge sends to the AI tool is the same across all runs. The wrapper instructs the model to emit per-criterion verdicts in a strict format and explicitly forbids inventing criteria, scoring on aesthetic dimensions, or skipping criteria silently. Changes to the wrapper require a new slice history entry plus this ADR's Notes section update.
6. **Meta-test scenario 15**: scenario 15 (`evals/scenarios/15-llm-as-judge-self-check.md`) applies the judge to a known-good output for scenario 01. Validates the judge itself before we trust it on real outputs.

## Consequences

### Positive

- **Pre-release runs become cheap**. The judge handles the common PASS case automatically; the human reads only UNCERTAIN and FAIL verdicts. Estimated time drop from 30-60 minutes (manual) to 5-15 minutes (judge plus spot-checks).
- **Structured artifact per run**. The judge emits machine-readable verdicts (markdown or JSON). Future tooling (trend dashboards, regression detection) consumes the structured output directly.
- **Rubric is now first-class**. The numbered list under `## Pass criteria` was always the rubric; now it is mechanically consumed. Authors writing new scenarios know the criteria will be parsed and evaluated; vague criteria show up as UNCERTAIN verdicts.
- **Tool-agnostic**. The `--tool <command>` abstraction works for any AI tool with stdin/stdout. Cursor users, Claude Code users, Codex users, Copilot users all benefit. No vendor lock-in.
- **Locked wrapper prevents prompt drift**. The judge's prompt does not vary across runs; verdict consistency is mechanical.

### Negative

- **Judge can be wrong**. The model evaluating may misread an ambiguous criterion. Mitigation: UNCERTAIN-by-default policy; FAIL is advisory; human override is the canonical resolution. The judge's job is to surface PROBABLE PASS cases automatically and probable issues for human review, not to be the final arbiter.
- **Locked rubric needs iteration**. The wrapper text may need adjustment as we learn what works. Mitigation: changes are explicit (slice history + ADR notes); the wrapper lives in one place (judge.py); revisions are mechanical and reviewable.
- **Local AI tool dependency**. Users without a CLI-piping AI tool cannot use the judge. Mitigation: the script falls back to a stub error message naming the `--tool` flag; manual review remains the default; `--judge` is opt-in.
- **One more Python script to maintain**. judge.py is ~200 lines. Mitigation: small surface; explicit tests via meta-test scenario 15.

### Neutral

- The judge does not enforce a pass-rate threshold or track trends across runs. Single-run verdicts only; trends live in scenario `## History` sections written by humans. Future tooling can consume the JSON output if trend tracking becomes useful.
- Code-based deterministic checks (e.g., "the response contains exactly N artifact-change bullets") are NOT introduced in this slice. The numbered list under `## Pass criteria` mixes code-checkable and semantic criteria; the judge handles both via the rubric.

## Alternatives considered

### Alternative 1: skip LLM-as-judge entirely; keep manual review only

- Continue with the current loop; reviewers handle all scenarios manually.
- **Rejected**: reviewer fatigue at 20+ scenarios is real. The trio of code-based, LLM-as-judge, human is broadly accepted in the eval discipline; missing the middle tier leaves a gap.

### Alternative 2: code-based deterministic checks instead of LLM-as-judge

- Refactor `## Pass criteria` into structured assertions (`assert response contains "Artifact changes" section`); use a Python evaluator.
- **Rejected**: most criteria mix structural and semantic checks ("response includes a Handoff block AND the Paste this next body starts with Run @commands/<expected>.md"). The structural part is code-checkable but the semantic part needs a model. Splitting into two layers doubles the maintenance burden without proportional gain.

### Alternative 3: vendor-direct API integration (Anthropic SDK, OpenAI SDK)

- judge.py imports the Anthropic Python SDK directly; uses a configured API key.
- **Rejected**: vendor lock-in. The WOS multi-tool architecture (ADR-0005) requires neutrality. The `--tool <command>` abstraction handles any AI tool with stdin/stdout; users with API access can wrap it in a shell command.

### Alternative 4: pass-rate threshold gating

- Aggregate verdicts across runs; gate releases at >= N% pass rate.
- **Rejected for this slice**: premature. Single-run verdicts are sufficient now; trend tracking is a future tooling layer that consumes the JSON output. Adding gating before the data exists locks in metrics we may regret.

### Alternative 5: free-form scoring (no rubric)

- Ask the judge "rate this response 0-10 with reasoning".
- **Rejected**: Hamel Husain's warning is explicit ("LLM-as-judge without a rubric is noise"). The rubric is the value; locking it is the discipline.

## References

- `evals/scripts/judge.py` (the judge; LOCKED rubric wrapper lives at the top of the file).
- `evals/scripts/run-evals.sh` (harness; `--judge` flag).
- `evals/scenarios/15-llm-as-judge-self-check.md` (meta-test scenario; the judge's first validation surface).
- `evals/README.md` (user-facing documentation of the optional second pass).
- ADR-0005 (multi-tool architecture; the reason judge.py is vendor-agnostic via `--tool <command>`).
- ADR-0012 (context budget; names the layers the judge operates on).
- ADR-0021 (evaluator-optimizer via self-critique-and-revise; reuses the locked-rubric pattern at a different layer, applied to draft artifacts instead of eval scenarios).
- Pragmatic Engineer, "A pragmatic guide to LLM evals for devs" (December 2025): the trio of code-based, LLM-as-judge, human.
- Hamel Husain, "Your AI Product Needs Evals": the rubric-is-the-value insight.
- Anthropic, "Testing and evaluation guide" (docs): rubric-based judging with locked wording.

## Notes

The locked rubric wrapper lives at the top of `judge.py` as a module constant `RUBRIC_WRAPPER`. Future changes require updating both the wrapper string AND this ADR's Notes section AND the slice 07 history.

The chicken-and-egg risk (judge not validated before use) is addressed by scenario 15: the meta-test. Before trusting the judge on scenarios 01-14, run scenario 15 once to confirm the judge correctly parses, formats, and emits verdicts. After scenario 15 passes, the judge is trusted within its OPTIONAL-second-pass policy bounds.

Future evolutions:
- A `judge-batch.py` that runs all scenarios in one shot. Not planned; the manual loop is intentional.
- Trend tracking (pass rate over time). Consumes JSON output; out of scope for this slice.
- Pass-rate gating in CI. Requires the trend tracking layer first; not planned.
