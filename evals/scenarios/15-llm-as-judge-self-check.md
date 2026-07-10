# Eval scenario 15: LLM-as-judge self-check (meta-test)

- **Tags**: llm-as-judge, meta-test, judge-validation, optional-second-pass
- **Last reviewed**: 2026-05-18
- **Status**: active

## Goal

Validates that `evals/scripts/judge.py` correctly parses the canonical `## Pass criteria` numbered list from any scenario, formats it as a rubric, calls the configured AI tool, and emits structured per-criterion verdicts. This is the judge's first user: a meta-test where the judge is applied to a synthetic known-good model output for scenario 01 (bootstrap-and-init) so we can confirm the judge identifies all numbered criteria as PASS.

Without this scenario, the judge has no validation surface; we would trust it on scenarios 01-14 without ever checking that it produces correct structural output. The chicken-and-egg risk (judge not validated before use) is closed here.

## Setup

A synthetic known-good model output for scenario 01 is provided inline below. It is intentionally simplified: enough structure to satisfy all 7 numbered pass criteria of scenario 01, but no real model invocation is required.

Save the inline output to a temp file: `/tmp/judge-self-check-input.txt`.

Verify the judge tool is configured. Default is `claude code --print`. If that is not available locally, set `--tool 'some other tool --print-only'` so the script can pipe stdin through the tool.

## Input prompt

The judge is invoked directly, not via a slash command. The "input prompt" here is the shell invocation:

```text
python3 evals/scripts/judge.py \
  --scenario evals/scenarios/01-bootstrap-and-init.md \
  --output /tmp/judge-self-check-input.txt
```

Inline known-good model output to paste into `/tmp/judge-self-check-input.txt`:

```text
### Artifact changes
- PROPOSED: projects/acme__widget-pricing/PROJECT_CHARTER.md
- PROPOSED: projects/acme__widget-pricing/REFERENCES.md

### Handoff
```text
Run now: /task-init
Mode: Ask
Work complexity: MEDIUM
Reason: project bootstrapped; now initialize the first task
Resume context:
- Task: projects/acme__widget-pricing/active/2026-05-18_first-task/
- Description: ...
```

(Turn 2 task-init output follows the same pattern with 5 PROPOSED task files including SOURCE_OF_TRUTH.md referencing ../../PROJECT_CHARTER.md, plus the Handoff routing to impact-analysis. All artifacts grounded in the user-supplied inputs; no fabricated stack or repo URLs.)
```

## Expected response shape

The judge.py output (markdown by default; JSON with `--json`) contains:

- A `# Judge verdict:` heading naming the scenario file.
- A `## Per-criterion verdicts` section with one bullet per numbered criterion from scenario 01 (7 bullets expected: criteria 1-7).
- Each bullet has the format `- Criterion N: **VERDICT** -- <reasoning>` where VERDICT is one of PASS / FAIL / UNCERTAIN.
- A `## Overall: **VERDICT**` section.
- A `## Raw judge response (for audit)` section with the AI tool's raw stdout fenced as a code block.

## Pass criteria

1. **All 7 criteria addressed**: the judge emits exactly 7 per-criterion bullets (one per numbered criterion in scenario 01). If the judge skipped any, the fallback fills `UNCERTAIN` with reasoning "judge did not address this criterion".
2. **No invented criteria**: the judge does NOT add criteria beyond the 7 in scenario 01. The output has exactly 7 lines matching the `^- Criterion N:` pattern.
3. **Overall verdict present**: the `## Overall:` section names exactly one verdict (PASS / FAIL / UNCERTAIN) with reasoning.
4. **Raw response preserved**: the `## Raw judge response (for audit)` section contains non-empty content matching what the tool emitted.
5. **Exit code 0**: judge.py exits 0 regardless of PASS/FAIL/UNCERTAIN aggregate.
6. **JSON mode parity**: rerunning with `--json` produces a JSON object with `per_criterion`, `overall`, `raw_response`, and `policy` keys; the policy string mentions ADR-0019.

## Failure modes to watch

- **Judge invents criteria**: emits more than 7 bullets, addressing checks not in scenario 01. Symptom: judge is not respecting the locked rubric wrapper.
- **Judge skips criteria silently**: emits fewer than 7 bullets and no UNCERTAIN fillers. Symptom: parse_verdicts fallback is not working.
- **Tool command errors loud but judge.py exits 0**: judge.py should propagate non-zero exit from the tool subprocess (exit code 2).
- **Aesthetic scoring**: judge emits verdicts on dimensions not in the criteria (writing style, tone, completeness beyond what's asked). Symptom: locked rubric is being ignored.
- **OVERALL inferred wrong**: judge omits the Overall line and the fallback infers PASS when at least one per-criterion is FAIL. Symptom: parse_verdicts logic bug.

## Notes

- Related ADRs: [ADR-0019](../../docs/adr/0019-llm-as-judge-eval-layer.md).
- Related commands: none directly; the judge operates on scenario files, not commands.
- Related scenarios: scenario 01 (the target of the meta-test) and any future scenario that the judge is applied to.
- Known issues: dependency on a local AI tool with stdin/stdout (claude code --print, or equivalent). Users without such a tool cannot run this scenario.

## History

- 2026-05-18: scenario authored as the judge's first validation surface. Slice 07 of the 2026-05-15 context-engineering uplift.
