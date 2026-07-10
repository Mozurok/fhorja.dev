# Scenario 39 -- Workflow prompt too long: CI detection

## Purpose

Validate the CI-side detection logic for the `workflow-prompt-too-long`
bug-class. The detector must reliably flag oversized prompt-template files
under `packages/wos-engine/internal/commands/_shared/` so that prompts that
exceed the safe-context budget are caught before they ship.

References:
- `packages/wos-engine/internal/wos/bug-classes/workflow-prompt-too-long.md`
- ADR-0038 (prompt-budget invariants)
- ADR-0039 (CI grep + word-count heuristic)

## Setup

Two synthetic fixtures placed under
`packages/wos-engine/internal/commands/_shared/` for the duration of the
eval:

1. `fixture-oversized.md` -- a prompt-template authored at roughly
   ~750 words (deliberately over the 600-word threshold defined in
   ADR-0039). Body contains representative section headings
   (`## Context`, `## Steps`, `## Output`) and prose. No explicit final-line
   `StructuredOutput` reminder.
2. `fixture-safe.md` -- a prompt-template at roughly ~400 words. Ends with
   an explicit final-line reminder:
   `Call StructuredOutput exactly once with {artifact, mode, content}.`

## Given / When / Then

### Case A: oversized template must be flagged

- Given `fixture-oversized.md` (~750 words) lives under
  `packages/wos-engine/internal/commands/_shared/`.
- When the CI job runs the bug-class detector
  (`scripts/lint/detect-workflow-prompt-too-long.sh`, grep + `wc -w` over
  every `*.md` in `_shared/`).
- Then the detector emits one finding for `fixture-oversized.md` with:
  - file path,
  - first line of the prompt body (line number),
  - measured word count,
  - threshold reference (600).
- And the CI step exits non-zero.

### Case B: safe template must not be flagged

- Given `fixture-safe.md` (~400 words) lives under the same directory and
  ends with an explicit `StructuredOutput` reminder line.
- When the same CI grep runs.
- Then `fixture-safe.md` is not present in the findings output.
- And, in isolation (only `fixture-safe.md` present), the CI step exits
  zero.

## Pass criteria

1. Case A produces exactly one finding for `fixture-oversized.md`.
2. The finding includes `file:line` plus the measured word count, not just
   a generic warning.
3. The reported word count is within +/- 5% of the true count from
   `wc -w` over the body.
4. Case B produces zero findings for `fixture-safe.md`.
5. Detector ignores non-`_shared/` paths, even if oversized (scoping
   invariant from ADR-0039).
6. Detector tolerates UTF-8 content, fenced code blocks, and YAML
   front-matter without crashing.
7. Exit code is non-zero if and only if at least one `_shared/` template
   exceeds the threshold.
8. Detector runtime stays under 2s on the current `_shared/` tree (perf
   budget per ADR-0039).

## Failure modes to watch

- False negative: oversized template silently passes because grep matched
  on heading count instead of word count.
- False positive: safe template flagged because front-matter or code
  blocks inflated the word count.
- Path scoping leak: detector flags `*.md` outside `_shared/`
  (e.g. ADRs, runbooks), violating ADR-0039 scope.
- Exit-code drift: detector logs a finding but still exits 0, hiding the
  regression from CI.

## Cleanup

Remove both fixtures from `_shared/` after the scenario completes so the
production tree is unaffected.
