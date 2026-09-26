# Scenario 39: workflow prompt too long, CI detection

## Purpose

Validate the CI-side detection logic for the `workflow-prompt-too-long`
bug-class. The detector must reliably flag oversized prompt-template files,
and templates whose last lines do not name the typed return, so that a
drifted dispatch prompt is caught before it ships.

No dispatch prompt lives in a file in this repository, so the detector takes
the directories to scan as arguments rather than owning a fixed path. The
scenario runs it on its own fixtures, and CI runs the same check through the
test below.

References:
- `wos/bug-classes/workflow-prompt-too-long.md` (Detection signals 2 and 3:
  the body past roughly 600 words, and no reminder in the last five lines)
- `scripts/detect-workflow-prompt-too-long.sh` (the detector)
- `scripts/tests/test-detect-workflow-prompt-too-long.sh` (runs this
  scenario's cases in the `script-tests` job of `.github/workflows/lint.yml`)
- ADR-0038 (the typed-return invariant a closing reminder protects)
- ADR-0039 (the 300 to 500 word authoring discipline; the detector's 600 is
  the bug class's danger threshold, not that discipline)

## Setup

Fixtures under `evals/fixtures/workflow-prompt/`, one directory each so a
run can include or leave out any of them:

1. `oversized/fixture-oversized.md`: a prompt-template of about 750 body
   words (over the 600-word threshold). Body contains representative section
   headings (`## Context`, `## Steps`, `## Output`) and prose, plus YAML
   front matter and a fenced code block that the count must skip. No
   typed-return reminder anywhere.
2. `safe/fixture-safe.md`: a prompt-template of about 400 body words.
   Ends with the dynamic-workflow reminder:
   `Return one payload matching worker_output_schema and nothing else`.
3. `padded/fixture-padded.md`: a control. Its body is under the threshold,
   but its front matter and a fenced example push the raw file over 600
   words. It ends with the native-path reminder:
   `Write one JSON payload matching worker_output_schema to fleet_inbox_artifact and nothing else`.
4. `buried/fixture-reminder-buried.md`: a control. A short body whose
   reminder sits in the first line of the preamble and not in the last five
   lines.

The fixtures are read in place; nothing is copied into the production tree.

## Given / When / Then

### Case A: oversized template must be flagged

- Given `oversized/fixture-oversized.md` (about 750 body words, no reminder).
- When the detector runs over the oversized and safe directories:
  `scripts/detect-workflow-prompt-too-long.sh evals/fixtures/workflow-prompt/oversized evals/fixtures/workflow-prompt/safe`
  (front matter and fenced code removed, then a `wc -w` style count of the
  body, then a read of the last five non-blank body lines).
- Then the detector emits a word-count finding for `fixture-oversized.md` with:
  - file path,
  - first line of the prompt body (line number),
  - measured word count,
  - threshold reference (600),
  in the form `<file>:<line>: <words> words over 600`.
- And it emits a separate reminder finding for the same file:
  `<file>:<line>: no typed-return reminder in the last 5 lines`.
- And the step exits non-zero.

### Case B: safe template must not be flagged

- Given `safe/fixture-safe.md` (about 400 body words) ends with an explicit
  typed-return reminder line for its selected carrier.
- When the same detector runs.
- Then `fixture-safe.md` is not present in the findings output.
- And, in isolation (only the `safe/` directory given), the step exits zero
  with no output.

### Controls

- `padded/` alone exits zero: front matter and fenced code are not counted,
  and the native-path reminder is accepted.
- `buried/` alone yields exactly one finding, the reminder one: a reminder in
  the preamble does not count, and the length check stays silent.

## Pass criteria

1. Case A produces exactly one word-count finding and exactly one reminder
   finding for `fixture-oversized.md`, on separate lines. The two are counted
   separately; neither stands in for the other.
2. The word-count finding includes `file:line` plus the measured word count
   and the threshold, not just a generic warning.
3. The reported word count is within +/- 5% of the true count from
   `wc -w` over the body with front matter and fenced code removed.
4. Case B produces zero findings for `fixture-safe.md`.
5. The detector reads only the directories it is given: `safe/` run alone
   does not report the oversized fixture in the sibling directory.
6. The detector tolerates UTF-8 content, fenced code blocks, and YAML
   front matter without crashing, and counts none of the front matter or
   fenced code (the `padded/` control stays clean).
7. Over directories that exist and hold `*.md` files, the exit code is
   non-zero if and only if at least one finding of either kind is reported.
   A target directory that is missing, or holds no `*.md`, is refused by name
   with exit 2 and is never reported as clean.
8. Detector runtime stays under 2s on a normal tree (the test times it over
   `commands/` and `wos/`).

## Failure modes to watch

- False negative: oversized template silently passes because the check
  matched on heading count instead of word count.
- False positive: safe template flagged because front matter or code
  blocks inflated the word count.
- Reminder by grep: a reminder anywhere in the file satisfies the check,
  so a reminder left in the preamble (the `buried/` control) looks present.
- Merged findings: the oversized fixture reports one combined line, so a
  file with only one of the two defects cannot be told apart.
- Path scoping leak: the detector reads `*.md` outside the directories it was
  given (e.g. ADRs, runbooks).
- Exit-code drift: the detector logs a finding but still exits 0, or reports
  a missing directory as clean, hiding the regression from CI.

## Cleanup

None. The fixtures are read in place and the detector writes nothing.
