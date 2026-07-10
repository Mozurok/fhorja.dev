# ADR-0002: Paste-this-next copy-paste contract

- **Status**: Superseded (by Adaptive handoff, v2.0.0-rc1, 2026-05-25)
- **Date**: 2026-05-08
- **Tags**: handoff, output-contract, resumability, multi-step-workflow

## Context

Long engineering tasks span many command invocations. Each invocation produces a recommendation for the next step: "now run `impact-analysis` in Plan mode against this task folder". Without a strict handoff format, three things tended to fail:

1. **Routing decay**. The model would describe the next phase ("now we should plan implementation") without actually emitting the runnable invocation. The user had to translate "we should plan" into "run `/implementation-plan` against `projects/<client>__<project>/active/YYYY-MM-DD_<slug>/`". The translation step lost fidelity, especially across sessions.
2. **Truncation under token pressure**. When responses ran long (large `### Artifact changes` payloads with full file proposals), models sometimes stopped before emitting the handoff. The next step was lost.
3. **Slash-only handoffs**. Some responses ended with just `/sync-task-state` on its own line. That looks runnable but is invalid: `sync-task-state` requires the active task folder path as an input, and a slash without the path is not actually executable.

The workflow already had a notion of "every command should end with a Handoff section". The issue was that the section's body was unconstrained: sometimes prose, sometimes a code block, sometimes missing entirely.

## Decision

Every command response must end with a `### Handoff` block containing a fenced code region in this exact shape:

```text
Run now: /<command>
Mode: <Ask | Plan | Agent | Debug>
Work complexity: <LOW | MEDIUM | HIGH | N/A>
Reason: <one line>
Paste this next:
<exact prompt block, including the active task folder path and any required inputs the next command lists>
```

The `Paste this next:` body is the **primary continuation interface**. It is treated as a single copy-paste unit and must satisfy six rules:

1. **Always present**. Never omitted, never empty, never replaced by "see above".
2. **Start with an invocation line**. First line is `Run @commands/<official-basename>.md` or a `/<official-basename>` line, matching the `Run now:` value.
3. **Task folder included**. When the next command requires an active task folder path, the body includes the concrete `projects/<client>__<project>/active/YYYY-MM-DD_<task-slug>/` path on its own line.
4. **All required inputs satisfied**. Other inputs the next command's file declares (slice path, base branch, PR URL, product workspace, etc.) are present in the body.
5. **Not slash-only**. A body of only `/sync-task-state` is invalid when the next command requires the task path.
6. **Length management is upstream**. If the response risks token limits, shorten earlier sections (especially repeated file content); never drop or truncate the Handoff to save space.

These rules are enforced both as normative WOS content (every command's `### Definition of done (command output)` references the contract) and as the canonical shared block `commands/_shared/handoff-body.md`, which `lint-commands.sh` propagates to every command.

## Consequences

### Positive

- The user resumes any command's recommendation by **literally copy-pasting** the body of `Paste this next:`. No translation, no path lookup, no SKU substitution.
- Routing recommendations are auditable: the conversation history shows exactly what was suggested next, in a runnable form.
- Cross-session resumption works without ceremony. Even after `/compact`, the last response in the conversation contains a complete, runnable continuation.
- Models are explicitly told never to truncate before the Handoff; this catches the common failure mode where large file payloads pushed the handoff out of the response window.

### Negative

- The format is rigid; users cannot customize the Handoff block per their preference. The rigidity is intentional (so `Paste this next:` works mechanically) but it does mean the workflow has an opinionated final shape.
- Some commands have very long required-input lists (e.g., `pr-package` needs base branch, current branch, working tree status, diff commands). The Handoff body inherits that length.

### Neutral

- The contract is enforceable mechanically (lint can check the fenced block exists and starts with `Run now:`) but the **content** of `Paste this next:` is harder to validate without running the next command. Drift here is caught by humans during review or by next-command failures.

## Alternatives considered

### Alternative 1: Free-form handoff prose

- Each command ends with a paragraph describing the next step in natural language.
- Rejected: highest fidelity loss; requires the user to translate prose into a runnable invocation; routing recommendations become inconsistent across commands.

### Alternative 2: Structured handoff but no `Paste this next:` body

- Emit `Run now:`, `Mode:`, `Reason:` but omit the prompt block.
- Rejected: the user still has to assemble the runnable prompt by hand from the task folder path plus the next command's input requirements.

### Alternative 3: External tool (CLI wrapper) generates the next prompt

- A Bash script reads the response, finds the `Run now:` line, looks up the next command's required inputs, and emits a ready-to-paste prompt.
- Rejected for now: adds runtime dependency to a markdown-only project; the in-response Handoff is sufficient. May revisit if the workflow gains a CLI in a future phase.

## References

- `WORKFLOW_OPERATING_SYSTEM.md` → `## Global output contract` → `### Standard ending format`, `### Paste this next (copy-paste contract)`, `### Why this is mandatory`.
- `wos/global-output-contract.md` → `## Why the Handoff block is mandatory` (full motivation, lazy-loaded).
- `commands/_shared/handoff-body.md` (canonical block).
- Every `commands/*.md` ends with the standard ending format.

## Notes

The "models stop before Handoff under token pressure" failure mode was observed repeatedly during the early WOS iterations when commands began emitting full `IMPLEMENTATION_PLAN.md` content inline. The mitigation now lives both in the contract (rule 6: shorten earlier sections, never drop Handoff) and in each command's `### Definition of done` ("response that ends after artifact content without a complete Handoff is invalid output").
