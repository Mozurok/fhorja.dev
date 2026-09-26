---
name: schema-skip-on-structured-output
category: agent-prompt-engineering
default-severity: P0
cwe: [CWE-754]
languages: [typescript, javascript, markdown]
file-patterns: ["**/dispatch/**", "**/agents/**", "**/prompts/**", "**/*.prompt.md"]
perspectives: [operator, maintainer]
reversibility-check: false
---

# schema-skip-on-structured-output

## Trigger

For current Fhorja dispatches, apply this class to the payload on the selected ADR-0158
carrier: the runtime's typed result or the assigned native JSON file. Validate that payload
against the declared schema; do not require a worker-side tool call. The tool-call code
examples below describe the historical failure mechanism, not the current Fhorja API.

A subagent is dispatched with a JSON schema (the StructuredOutput tool) as its required return contract, and it ends its turn by writing prose to its final assistant message instead of calling the tool. The orchestrator's apply step reads only the tool call, so the prose is discarded and the structured payload is null.

The failure is silent by construction. Nothing throws, nothing logs, no metric moves, and every agent exits cleanly, so the orchestrator reports a successful batch. The loss surfaces later, when an expected artifact is missing from disk or the next stage fails on an empty input, far from the dispatch that caused it. It also scales with fan-out: one internal batch had 10 of 12 dispatched agents skip the tool call entirely, which is a batch that consumed full token cost and produced almost no usable output while looking green.

CWE-754 (Improper Check for Unusual or Exceptional Conditions): the orchestrator treats the run as successful without ever checking that the expected tool call occurred.

## Detection

Three shapes, in rough order of how often they are missed:

1. **Prose in place of the tool call.** The agent's final message reads like a report to a human, typically "I have created the file at `<path>` with the requested sections", and there is no tool invocation anywhere in the turn. The consuming code finds nothing:

   ```ts
   const artifact = result.toolCalls.find(c => c.name === "StructuredOutput")?.input.artifact;
   // artifact === undefined, silently dropped
   ```

2. **A dispatch site with no closing reminder.** The prompt names the schema somewhere in its body but its last line is something else. The final line is the highest-recency position in the context window, and a reminder placed anywhere earlier is empirically insufficient.

3. **A batch whose skip rate is nonzero but small.** A sustained skip rate above a few per cent is a prompt-quality regression rather than a transient, and it is the shape that survives longest because no single run looks broken.

Post-batch sweep, which is what turns shape 3 from invisible into a number:

```ts
const skipped = results.filter(r => !r.artifact);
if (skipped.length > 0) {
  logger.error("StructuredOutput skip detected", {
    batchId, skipCount: skipped.length, total: results.length,
  });
  metrics.increment("agent.structured_output.skip", skipped.length);
}
```

Prompt-template check, cheap enough to run in CI on every change to a prompt file:

```bash
grep -LE "Return one payload matching|Write one JSON payload matching" packages/**/prompts/*.md
# any file in the list lacks either carrier reminder; inspect final-line placement separately
```

Alert threshold: any batch where `skipCount / total > 0.05` should page. A sustained skip rate is a regression in prompt quality, not a transient, and the per-batch numbers are too small to notice one at a time.

## Retrieval

- The full dispatch site, not the prompt string alone: the call that builds the prompt, the schema it passes, and the code that reads the result. The class lives in the gap between what is sent and what is read, so pulling only one side reproduces the blindness.
- Every prompt template the dispatch site can reach, including shared includes and any template composed at runtime. A reminder that exists in a shared preamble but not at the tail is a finding, and only the composed order shows that.
- The result-handling path, all the way to the write. The question is what the code does when the payload is absent, and that answer is usually several lines below the extraction.
- Any post-batch sweep, alert rule, or metric on skip rate. Their absence is itself the finding, so record it explicitly rather than as silence.
- Recorded run output for the dispatch, when it exists: the per-agent turn ends are the only direct evidence that the tool was or was not called.

## Analysis prompt

Given the retrieved dispatch site, its prompt templates, and its result-handling path:

1. Compose the prompt as the code actually builds it, then read its LAST line. Report that line verbatim. A schema reminder anywhere other than the tail does not satisfy this check, and report where it does appear so the fix is a move rather than an addition.
2. Count the distinct top-level objectives the prompt asks for. Report the count and quote each imperative. More than one objective per dispatch is a cause of this class, not a style preference.
3. Trace the result path from the selected carrier's payload to the write: the runtime result or the assigned native JSON file for Fhorja. Report exactly what happens when the payload is absent: an exception, a retry, a logged warning, or a no-op. A no-op is the finding; name the line.
4. Determine whether anything counts skips. Report the presence or absence of a post-batch sweep, a metric, and an alert threshold, each as a separate answer. Absence is a fact worth stating, because it is the difference between a failure that is rare and one that is invisible.
5. Check whether the orchestrator retries on a null payload, and if so whether the retry prompt differs from the original. A retry that re-sends the same prompt tends to reproduce the same skip.
6. Report whether the schema constraints (enum values, required keys, the no-preamble instruction) are repeated near the tail or stated only mid-body.
7. Recommend, in order: keep each dispatched prompt to one artifact, one schema, one job; make its final line an explicit typed-return reminder for the selected carrier, naming the output schema and the assigned file on the native path; add a post-batch sweep that counts payload-less results and increments a metric; retry once on a null payload with a more explicit reminder and then surface a hard failure rather than a no-op. In one internal batch, moving the reminder to the final line took the skip rate from 83 per cent to zero, so the ordering above is not arbitrary: the prompt fix is the one that pays, and the sweep is what tells you when it stops paying.

## Severity rubric

- **P0**: a dispatch whose payload is read but never checked, so an absent payload becomes a silent no-op. Justification for the ceiling: this is data loss with no signal, at a boundary that fans out, and the run reports success. There is no lower tier for "it only happened to two agents", because the property that makes it P0 is the absence of the check, not the observed rate.
- **P1**: the check exists and the run fails loudly on an absent payload, but the prompt still lacks a tail reminder or carries more than one objective. The loss is visible; the waste is not prevented.
- **P2**: prompt and check are both sound and nothing counts skips over time, so a future prompt regression would be caught per-run but not as a trend.

## Confidence factors

- **HIGH**: the result-handling path extracts the payload with an optional chain and writes it without a guard, and no branch handles the undefined case. The code says what it does.
- **MEDIUM**: the tail reminder is absent and no recorded run output is available, so the prompt is a known cause with no observed effect yet.
- **LOW**: a reminder string appears in the repository but not provably in the composed prompt for this dispatch, for example in a sibling template or in documentation about dispatch.

## Examples

### Positive (payload read, absence unhandled)

```ts
// dispatch site: last line of the prompt is an instruction about formatting
const result = await dispatch(agentPrompt, { schema: ArtifactSchema });
const artifact = result.toolCalls.find(c => c.name === "StructuredOutput")?.input.artifact;
await writeArtifact(artifact);   // undefined reaches the writer, which no-ops
```

Nothing here fails. The batch reports twelve successes, the writer is called twelve times, and the disk gains whatever subset of agents happened to call the tool.

### Negative (checked and reminded)

```ts
const result = await dispatch(agentPrompt, { schema: ArtifactSchema });
const call = result.toolCalls.find(c => c.name === "StructuredOutput");
if (!call) {
  metrics.increment("agent.structured_output.skip");
  throw new SchemaSkipError(batchId, agentId);   // loud, attributable, retryable
}
```

The prompt for this dispatch ends with an explicit single-sentence reminder to call the tool exactly once with the named fields, and the batch records a skip count even when it is zero. A zero recorded deliberately is what makes the first nonzero one legible.
