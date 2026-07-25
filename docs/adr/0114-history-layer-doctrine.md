# ADR-0114: the history layer names three intra-session operations and a re-fetch rule

- **Status**: Accepted
- **Date**: 2026-07-25
- **Tags**: context-engineering, history-layer, context-budget, re-fetch-rule, harness-agnostic, extends-adr-0093, grounded-2026

## Context

A 2026-07-25 deep read of two sources already sitting at title depth in `REFERENCES.md` since 2026-06-13 (see the project REFERENCES.md section "2026-07-25 (deep read): intra-session context operations") found a real gap in `wos/context-budget.md`. The `### 5. history` section described the layer and stated, in full, that compaction shrinks it and a new session resets it. No doctrine governed what a command should do when part of that layer is gone.

Two sources ground the gap. The Anthropic cookbook on context engineering tools names three distinct intra-session operations with three distinct cost profiles: compaction compresses the whole window into a summary and pays inference; clearing is a sub-transcript operation that surgically empties stale, re-fetchable `tool_result` content while leaving user messages, assistant reasoning, and the `tool_use` record untouched, and it pays nothing; memory moves data out of the window so it survives past the session. "The Complexity Trap" (arXiv 2508.21433), an independent academic study run inside SWE-agent on SWE-bench Verified across five model configurations, found that a simple observation-masking strategy (the same move as clearing) halves cost relative to raw context growth while matching, and sometimes slightly exceeding, the solve rate of LLM summarization, and its authors state the result "raise[s] concerns regarding the trend towards pure LLM summarization."

ADR-0093 already named a four-operation vocabulary for context engineering: write, select, compress, isolate. It mapped `isolate` to the fleet worker contract (ADR-0038: a sub-agent's own working context is thrown away and only a typed `StructuredOutput` payload returns to the orchestrator). That is isolation of a SEPARATE agent's context from the orchestrator's. It never addressed clearing inside ONE agent's own transcript, which is a different operation on the same `history` layer within a single session. A grep for observation masking, tool clearing, or context editing across `docs/adr/`, `wos/`, and `commands/` at the time of this ADR returns only ADR-0093's four-operation vocabulary, confirming the gap was real and not merely undocumented.

The honest limit on what Fhorja can do here: Fhorja is markdown and bash, model-agnostic and harness-agnostic by design. It cannot invoke a harness-side clearing operation, and naming a vendor API identifier as doctrine would tie normative text to one vendor's dated type name. What Fhorja can state is the operation, in vendor-neutral terms, and the discipline a command author needs regardless of which operations a given harness actually performs.

## Decision

**(a) Name the three intra-session `history` operations in `wos/context-budget.md`.** The `### 5. history` section states, without naming a vendor API: compaction compresses the whole window into a summary; clearing drops stale, re-fetchable data from inside the window while leaving the rest of the transcript intact; memory moves data out of the window so it survives past the session (this third one is the existing `memory` layer, not `history`). A harness may implement any, all, or none of the three; Fhorja assumes nothing about which.

**(b) The re-fetch rule.** A command that needs a large, deterministic tool result re-runs the command or re-reads the file rather than citing an older transcript entry, because that entry may have been compacted away or, on a harness that clears, surgically emptied while the record that the tool ran survives. This rule is stated once, in `wos/context-budget.md`, and applies uniformly; it does not vary by harness.

**(c) Document the `consumed: [history]` interaction.** `resume-from-state` and `im-stuck` are the two commands that declare `history` in `consumed:`. Both treat `history` as a best-effort, possibly-partial source: on a harness with clearing enabled, the `tool_result` content they might otherwise rely on can be empty while the `tool_use` record that a call happened still survives. Both commands already fall back to `memory` (`TASK_STATE.md`, `DECISIONS.md`) as the source of record; this ADR makes that fallback's reason explicit rather than incidental.

**(d) Fhorja does not implement clearing.** No command, script, or shared block invokes a harness-side clearing operation, and no normative text names a vendor API identifier as doctrine. The three operations are named so a command author can reason about `history`'s volatility; implementing any of them is out of scope, because doing so would require a harness-specific integration Fhorja's markdown-plus-bash shape cannot provide and public-tree neutrality does not want.

## Consequences

- The `history` layer stops being the one layer in `wos/context-budget.md` with no governing doctrine; `### 5. history` now states what can happen to it and what a command should do about it.
- The re-fetch rule is cheap to follow (a command already capable of reading a file or re-running itself pays nothing extra) and removes a class of silent staleness: a command that would have cited a compacted or cleared transcript entry now re-derives it instead.
- `resume-from-state` and `im-stuck` gain a documented reason for their existing `memory`-first fallback rather than leaving it as an unstated convention.
- Additive and harness-agnostic: no command contract changes, no new command, no vendor API named in normative text. ADR-0093's four-operation vocabulary (write, select, compress, isolate) is unchanged; this ADR adds a fifth, narrower vocabulary scoped to what can happen inside one session's `history` layer, and clarifies that ADR-0093's `isolate` (a separate agent's context) and this ADR's clearing (inside one agent's own transcript) are different operations that happened to go undistinguished until now.
- Accepted residual: this doctrine cannot be verified against a live harness from within Fhorja itself, since Fhorja has no harness integration to exercise; the evidence is the two grounded sources and the internal consistency of the resulting rule, not a runtime probe.
