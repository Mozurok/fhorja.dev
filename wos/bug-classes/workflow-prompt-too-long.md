---
name: workflow-prompt-too-long
category: agent-prompt-engineering
default-severity: P1
priority: P1
pillars: [observability, correctness]
cwe: [CWE-573]
languages: [markdown, typescript]
file-patterns: ["packages/wos-engine/internal/commands/**", "packages/wos-engine/internal/wos/**", "apps/web/src/server/ai/**"]
perspectives: [operator, maintainer]
reversibility-check: false
---

# workflow-prompt-too-long

Fhorja subagent prompts that drift past ~600 words, fan out into multiple objectives, or drop the explicit StructuredOutput reminder empirically cause schema-skip rates to climb from ~0% to >10%. The subagent answers in prose, omits required fields, or returns mode/artifact incorrectly -- the orchestrator then either crashes or silently records a no-op.

## What it looks like

- A single dispatched prompt asks the subagent to do two or more things (e.g., "read the ADR, then create the bug-class, AND update the index") instead of one tightly scoped objective.
- The prompt body crosses ~600 words once preamble, schema reminders, and inline examples are counted.
- The closing instruction omits an explicit final-line StructuredOutput reminder (no "Call StructuredOutput exactly once with {artifact, mode, content}" near the bottom).
- The schema constraints (enum values, required keys, "no preamble") are buried in the middle of the prompt instead of being repeated at the end where the model attends most.
- The subagent's response begins with a chat-style preamble ("Sure, I'll do that...") instead of going straight to the tool call.

## Why it matters

- Schema-skip rate jumps from ~0% (focused prompts) to >10% (drifted prompts) in our internal dispatch logs. Each skip is a wasted dispatch + a silent gap in the workflow audit trail.
- The orchestrator treats a missing StructuredOutput call as "no output", so downstream slices proceed on stale state. This is an observability failure (the run looks successful) AND a correctness failure (the artifact was never written).
- Long multi-goal prompts also inflate token cost on every retry and make root-cause analysis harder, because the failure mode is "the model did one of three things" instead of "the model failed at one thing".

## How to detect

Eyeball pattern:

- Count distinct imperatives ("create X", "update Y", "also do Z"). More than one top-level objective is a smell.
- Word-count the prompt body. ~600+ words is the empirical danger zone.
- Scan the last 5 lines: is there an explicit "Call StructuredOutput exactly once" reminder? If not, flag.

Grep heuristic:

```
# Find dispatch sites that build long prompts without a closing schema reminder
rg -n "dispatch\\(|spawnSubagent\\(|Task\\.create" packages/wos-engine -A 40 \
  | rg -B 1 -A 1 "StructuredOutput" --files-without-match
```

Also flag any prompt template literal in `apps/web/src/server/ai/**` whose body exceeds ~600 words and lacks a final-line StructuredOutput reminder.

## How to fix

Use the focused-prompt template: 300-500 words, single objective, explicit final-line reminder.

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

IMPORTANT: Call StructuredOutput exactly once with {artifact, mode, content}. No preamble outside the tool call. NEVER use em-dash; use -- or : instead.`;
```

Rules:

- One objective per dispatch. If you have two, dispatch twice.
- Keep the body under ~500 words; push reusable context into shared includes (e.g., `mandatory-context-bootstrap.md`).
- Repeat the schema reminder as the final line of the prompt. Models attend to the tail.

## CWE / standard refs

- CWE-573: Improper Following of Specification by Caller (advisory). The "caller" here is the orchestrator dispatching to the subagent; the spec is the StructuredOutput schema. Drifted prompts cause the callee to skip the spec.

## See also

- ADR-0038 (subagent dispatch contract)
- ADR-0039 (focused-prompt template + StructuredOutput discipline)
- `wos/workflow-patterns.md` (canonical dispatch shapes)
- `wos/bug-classes/schema-skip-on-structured-output.md` (downstream failure mode this class causes)
