---
name: workflow-prompt-too-long
category: agent-prompt-engineering
default-severity: P1
cwe: [CWE-573]
languages: [markdown, typescript]
file-patterns: ["packages/wos-engine/internal/commands/**", "packages/wos-engine/internal/wos/**", "apps/web/src/server/ai/**"]
perspectives: [operator, maintainer]
reversibility-check: false
---

# workflow-prompt-too-long

## Trigger

A dispatched subagent prompt drifts past roughly 600 words, fans out into more than one objective, or loses its explicit closing schema reminder. The subagent then answers in prose, omits required fields, or returns the wrong artifact or mode, and the orchestrator either crashes or records a no-op.

The cost is not only the failed dispatch. A missing structured call is read as no output, so downstream slices proceed on stale state: the run looks successful and the artifact was never written, which is an observability failure and a correctness failure at the same time. Multi-goal prompts also inflate token cost on every retry and make root-cause analysis harder, because the failure mode becomes "the model did one of three things" rather than "the model failed at one thing". Internal dispatch logs put the skip rate near zero for focused prompts and above ten per cent for drifted ones.

CWE-573 (Improper Following of Specification by Caller), read as advisory here: the caller is the orchestrator dispatching to the subagent, the specification is the output schema, and a drifted prompt is what makes the callee skip it.

## Detection

Five signals, each checkable without running anything:

1. **More than one top-level objective.** The prompt asks the subagent to read a document, then create an artifact, and also update an index. Count distinct imperatives; more than one is the smell.
2. **Body past the danger zone.** Word-count the composed body, counting preamble, schema reminders, and inline examples. Roughly 600 words and up is where the empirical curve turns.
3. **No closing reminder.** Read the last five lines. If none of them names the output call explicitly, flag it.
4. **Constraints buried mid-body.** Enum values, required keys, and the no-preamble instruction stated once in the middle and never repeated at the tail. Models attend to the tail.
5. **Chat-style preamble in the response.** A reply that opens with "Sure, I'll do that" instead of going straight to the tool call is the same failure seen from the other end.

Signals 2 and 3 are mechanical for a prompt kept as a Markdown file. `scripts/detect-workflow-prompt-too-long.sh <dir> [<dir> ...]` strips front matter and fenced code from every `*.md` under the directories you name, then reports `<file>:<line>: <words> words over 600` for a long body and, as a separate finding, `<file>:<line>: no typed-return reminder in the last 5 lines` when none of the last five body lines names `Return one payload matching worker_output_schema`, `Write one JSON payload matching worker_output_schema`, or `StructuredOutput`. It exits 1 on any finding and 2 on a directory that is missing or holds no `*.md`. Pass `--threshold N` to move the length line. Scenario 39 grades it on `evals/fixtures/workflow-prompt/`. It reads the file as written, so a prompt composed at runtime from includes still needs the composed text (see Retrieval).

For prompts built in code, a grep that finds dispatch sites building long prompts with no closing reminder:

```
# Find dispatch sites that build long prompts without a closing schema reminder
rg -n "dispatch\\(|spawnSubagent\\(|Task\\.create" packages/wos-engine -A 40 \
  | rg -B 1 -A 1 "StructuredOutput" --files-without-match
```

## Retrieval

- The composed prompt, not the template literal. Shared includes, a bootstrap block, and runtime interpolation all change both the length and what the last line actually is, and the template alone shows none of that.
- Every shared include the template pulls in, read as its own unit, because a reminder that lives in a preamble include is in the worst possible position and looks present to a naive grep.
- The dispatch call itself, to learn how many artifacts and modes this one call is responsible for. Objective count is a property of the call, not of the prose.
- Sibling dispatch sites in the same module. This class travels by copy-paste, so a single site read alone will understate how much of the surface carries it.
- Any recorded skip rate, retry count, or per-dispatch outcome for this site. Its absence is a finding to state, not a gap to skip past.

## Analysis prompt

Given the retrieved dispatch site, its composed prompt, and its shared includes:

1. Compose the prompt exactly as the code builds it, including every include and interpolation, then report its word count. Count the body as sent, not the template as written.
2. Report the last five lines verbatim. State whether any of them names the output call explicitly, and if a reminder exists elsewhere, name its position. The fix for a misplaced reminder is a move, and the report should make that obvious.
3. Enumerate the top-level imperatives and quote each one. Report the count. If it exceeds one, name which objectives would become separate dispatches.
4. Locate every schema constraint (enum values, required keys, forbidden preamble) and report whether each is repeated near the tail or stated once mid-body.
5. Identify which parts of the body are reusable context rather than this dispatch's own instructions, and report their word count separately. Context that belongs in a shared include is the cheapest length to remove.
6. Check the sibling dispatch sites in the same module for the same shape and report how many carry it. One site is a fix; five sites is a template problem.
7. Report whether anything measures this site's skip rate. If nothing does, say so plainly, because the fix below is unverifiable without it.
8. Recommend, in order: one objective per dispatch, and dispatch twice when there are two; hold the body under roughly 500 words by pushing reusable context into shared includes; repeat the schema reminder as the final line rather than adding a second one mid-body; and record a per-dispatch skip count so the next drift is visible as a trend rather than as a surprise. Do not treat the word count as the rule. It is a proxy for attention budget, and a 700-word prompt with one objective and a tail reminder is safer than a 400-word prompt with three objectives and none.

## Severity rubric

- **P1**: a dispatch whose composed prompt carries more than one objective or lacks a tail reminder, at a site whose result is consumed without a guard. Justification: the skip it causes is read as no output, so a later stage runs on stale state and the run reports success. It is not P0 on its own because the prompt is a cause rather than the missing check; the unguarded consumer is the separate P0.
- **P2**: prompt drift at a site whose consumer does check for a missing payload. The waste and the retries are real, and the failure is loud rather than silent.
- **P2**: constraints stated only mid-body at a site that is otherwise focused and guarded. This is the shape that regresses first when the prompt next grows.

## Confidence factors

- **HIGH**: the composed prompt ends with a line that is not the schema reminder, and the same prompt contains two or more top-level imperatives. Both are read directly off the composed text.
- **MEDIUM**: the body is past the length threshold with a single objective and a tail reminder present. Length alone predicts risk without establishing it.
- **LOW**: a template literal that looks long in source but is mostly interpolation of a short runtime value, so the composed prompt is well under the threshold.

## Examples

### Positive (three objectives, tail is a formatting note)

```
Read ADR-0039 and summarize its decision. Then create the bug-class template
at the path below. Also update the category index so the new template appears.
...
Remember to keep the tone neutral and avoid the em-dash character.
```

Three imperatives, and the last line is about typography. The reminder to call the output tool sits about forty lines up, right after the bootstrap block, which is where a grep finds it and the model does not.

### Negative (one objective, tail reminder, context in an include)

```ts
const prompt = `${MANDATORY_CONTEXT_BOOTSTRAP}

# Objective
${singleObjectiveOneSentence}

# Inputs
${inputsBulleted}

# Output contract
- mode: ${mode}
- artifact: ${artifactPath}
- content: ${contentShape}

IMPORTANT: Return one payload matching the declared output schema and nothing else. NEVER use em-dash; use -- or : instead.`;
```

On the native Agent path, replace that final reminder with `Write one JSON payload matching worker_output_schema to fleet_inbox_artifact and nothing else`; supply the schema and resolved destination from the worker-contract envelope. The dynamic-workflow runtime supplies its typed result without a worker-side tool call (ADR-0158).

One objective, the reusable context behind a shared include so the body stays short, and the reminder in the last position where recency works for it rather than against it.
