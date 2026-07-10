---
name: schema-skip-on-structured-output
category: agent-prompt-engineering
priority: P0
pillars: [correctness, observability]
default-severity: P0
cwe: [CWE-754]
languages: [typescript, javascript, markdown]
file-patterns: ["**/dispatch/**", "**/agents/**", "**/prompts/**", "**/*.prompt.md"]
perspectives: [operator, maintainer]
reversibility-check: false
---

# schema-skip-on-structured-output

## What it looks like

A subagent is dispatched with a JSON schema (StructuredOutput tool) as the required return contract, but the agent ends its turn by writing prose to its final assistant message instead of calling the StructuredOutput tool. The orchestrator's apply step reads only the tool call, so the prose is discarded. Empirically observed in batch w59uu3zym, where 10 of 12 dispatched agents skipped the StructuredOutput tool call entirely and returned narrative summaries instead. From the orchestrator's perspective the batch "succeeded" -- all agents exited cleanly -- but the structured payload was null.

Typical shape: the agent finishes with something like "I have created the file at <path> with the requested sections..." and stops. No tool invocation. Downstream code path:

```ts
const artifact = result.toolCalls.find(c => c.name === "StructuredOutput")?.input.artifact;
// artifact === undefined -- silently dropped
```

## Why it matters

Downstream apply steps receive `null` or `undefined` and silently no-op. There is no error, no retry, no surfaced warning -- the run looks green. The user only discovers data loss later when expected artifacts are missing from disk or when the next workflow stage fails on an empty input. This is silent data loss at the agent-orchestration boundary and it scales with fan-out: a 12-agent batch with 80%+ skip rate produces almost no usable output while consuming full token cost.

Correctness pillar: the contract between orchestrator and subagent is violated. Observability pillar: the failure is invisible -- no exception, no log line, no metric increment.

## How to detect

Programmatic post-batch sweep:

```ts
const skipped = results.filter(r => !r.artifact);
if (skipped.length > 0) {
  logger.error("StructuredOutput skip detected", {
    batchId, skipCount: skipped.length, total: results.length,
  });
  metrics.increment("agent.structured_output.skip", skipped.length);
}
```

Prompt-template grep (CI check):

```bash
grep -L "Call StructuredOutput" packages/**/prompts/*.md
# any file in the list is missing the final-line reminder
```

Runtime alert: any batch where `skipCount / total > 0.05` should page; sustained skip rate is a regression in prompt quality, not a transient.

## How to fix

Two mitigations, applied together:

1. Focused prompt: keep the dispatched agent prompt narrow -- one artifact, one schema, one job. Long prompts with multiple instructions buried mid-body cause the agent to forget the tool-call contract.
2. Explicit final-line reminder: the last line of every dispatched agent prompt must be:

   ```
   IMPORTANT: Call StructuredOutput exactly once with {artifact, mode, content}.
   ```

   The final line is the highest-recency position in the context window. Placing the reminder anywhere else (preamble, mid-prompt, section header) is empirically insufficient. After this mitigation in batch w59uu3zym, skip rate dropped from 83% to 0%.

Belt-and-suspenders: orchestrator should retry once on null artifact with an even more explicit reminder, then surface a hard failure rather than no-op.

## CWE / standard refs

- CWE-754: Improper Check for Unusual or Exceptional Conditions -- the orchestrator does not check that the expected tool call actually occurred before treating the run as successful.

## See also

- ADR-0038 -- agent dispatch contract
- ADR-0039 -- structured output schema versioning
- bug-class: workflow-prompt-too-long -- root cause amplifier; long prompts make schema-skip more likely
