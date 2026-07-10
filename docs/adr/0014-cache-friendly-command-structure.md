# ADR-0014: Cache-friendly command structure (cache-breakpoint marker)

- **Status**: Accepted
- **Date**: 2026-05-15
- **Tags**: context-engineering, prompt-caching, cache-breakpoint, lint-enforced-contract, tool-integration-signal

## Context

Slice 01 of the 2026-05-15 context-engineering uplift named the six context layers (ADR-0012). Slice 02 quantified per-command cost with `token-budget:` frontmatter (ADR-0013). The third foundation piece is cache awareness.

Anthropic prompt caching (5-minute and 1-hour TTLs; 4096-token floor for Opus 4.7) reduces cost on long-horizon agentic tasks by 41-80 percent and TTFT by 13-31 percent (PwC `Don't Break the Cache`, 2026). The benefits depend on the static prefix being identifiable and stable. Different AI tools (Claude Code, Cursor, Codex, Copilot, Gemini CLI) implement cache placement differently:

- Some cache the full system prompt up to the first user turn.
- Some cache up to an explicit `cache_control` directive at a byte offset.
- Some cache nothing.

Without an explicit signal from the WOS, each tool's adapter has to guess where the cacheable boundary belongs. The guesses are not wrong, but they are not the workflow's intent either. The workflow needs a primitive that says "the command file is the static prefix; user / task content is dynamic."

Audited all 35 commands during slice 03 authoring. Finding: NO current command has in-file dynamic input. The user's actual paste content (failure traces, PR feedback, URLs) arrives via the slash-command invocation at runtime, NOT as a section within the command file. The command file in its entirety is the static prefix. The marker simply needs to delimit end-of-body.

## Decision

The WOS adopts an `<!-- cache-breakpoint -->` HTML comment marker as the cache-boundary signal:

1. **Placement**: every `commands/<name>.md` carries exactly one `<!-- cache-breakpoint -->` marker as the LAST non-blank line of the body, after the `Quality bar:` paragraph that closes `### Definition of done (command output)`.
2. **Mechanical detection**: `scripts/lint-commands.sh` validates marker presence (exactly one), count, and position (must appear after `### Definition of done`). Drift is a hard FAIL.
3. **Tool-integration interpretation**: tools that consume the WOS (and the generated `.claude/skills/<name>/SKILL.md`) read the marker as "static prefix ends here; conversation extends below". A tool's adapter can translate the marker into the API's native cache_control directive (Anthropic API direct), or it can ignore the marker and fall back to its default cache heuristic.
4. **Verbatim propagation**: `scripts/build-agent-skills.sh` copies the command body verbatim into `.claude/skills/<name>/SKILL.md`, including the marker. Open Agent Skills spec validators accept HTML comments.
5. **Documentation**: the rationale and edge cases live in `wos/context-budget.md ## Cache breakpoint convention` (lazy-loaded). The WOS `## Context budget` section has a one-paragraph inline stub for routing.

## Consequences

### Positive

- **Tool integrations can act on intent**. Adapters that support explicit cache_control (Anthropic API) can pass the byte offset of the marker. Adapters that do not still get the default behavior; correctness is unchanged.
- **The cache boundary is verifiable**. Reviewers and lint can confirm the marker is in the right place. Drift is mechanical, not judgment-based.
- **Future evolution is documented**. If a future command embeds a paste-here section within the file body, the marker moves to BEFORE that section. The rule extends naturally without an ADR rewrite.
- **No reorder required**. The audit confirmed current commands are already cache-friendly. The marker is additive; existing structure is preserved.

### Negative

- **One more lint rule to maintain**. Each new command must place the marker correctly. Lint message names the ADR for traceability.
- **Token cost per command**. The marker adds ~25 bytes (~7 tokens) per command. Total +245 tokens across 35 commands. Negligible at the cluster (1.5k-4k per command) but recorded for transparency.
- **HTML comments are invisible in rendered markdown**. A contributor copying a command without realizing the marker is significant might delete it. Mitigation: lint catches the deletion immediately with a clear error.
- **The marker is a contract signal, not a runtime mechanism**. It does not by itself enable caching; a tool's adapter must read and act on it. The value is in declaring intent so adapters CAN act on it.

### Neutral

- The HTML comment pattern is reused from the shared-blocks system (ADR-0011: `<!-- shared:<name> -->`). Contributors who know one know the other.
- The marker is invariant across all 35 commands. If the architecture ever introduces in-file dynamic content, the rule generalizes: marker goes BEFORE the dynamic section.

## Alternatives considered

### Alternative 1: let each tool guess the cache boundary

- Do nothing in the WOS; rely on each tool's default cache heuristic.
- **Rejected**: indistinguishable from the current state. Three problems: tool defaults vary; the workflow's intent is invisible to integrators; cache benefits depend on the boundary being stable, which guessing does not guarantee.

### Alternative 2: place the marker per-section, not per-command

- Insert `<!-- cache-breakpoint -->` after EACH static section (persona, goal, bootstrap, etc.). Tool integrations can pick the granularity they want.
- **Rejected**: over-engineering. The 5-minute Anthropic cache TTL writes the prefix once per session window; the granularity gain is small. The cost is per-section maintenance and confusion about which boundary the tool actually uses.

### Alternative 3: encode the boundary in frontmatter, not body

- Add `metadata.cache-prefix-ends-at:` with a line-number value.
- **Rejected**: byte offsets in frontmatter are brittle. Any edit to the body invalidates the field. An inline HTML comment moves with the body content automatically.

### Alternative 4: hard-FAIL on cache-floor (commands below 4096 static tokens)

- Reject any command whose static portion is below the Anthropic cache floor.
- **Rejected for this slice**. The 4096 floor applies to the SESSION static prefix (WOS bootstrap + active command + shared blocks), which is always above the floor (WOS alone is ~13k tokens). Per-command floor would force artificial inflation of small commands. Session-level cache-floor enforcement lives in slice 13 (context-rot guardrails) where the budget composes correctly.

## References

- `wos/context-budget.md ## Cache breakpoint convention` (the lazy-loaded full framework; edge cases, tool-integration notes).
- `WORKFLOW_OPERATING_SYSTEM.md ## Context budget` (compact in-line stub).
- `scripts/lint-commands.sh` (marker validation extension added in slice 03).
- `scripts/build-agent-skills.sh` (verbatim body copy; marker propagates to .claude/skills/).
- ADR-0011 (shared canonical blocks; same HTML-comment marker convention).
- ADR-0012 (context budget as explicit contract; the qualitative half this slice extends).
- ADR-0013 (per-command token budget; the quantitative half this slice composes with).
- Anthropic prompt caching docs (5-min and 1-hour TTLs; pricing tiers; min cacheable size for Opus 4.7).
- PwC, "Don't Break the Cache" (2026): 41-80 percent cost reductions; 13-31 percent TTFT improvements; placement-matters finding.
- ngrok, "Prompt caching: 10x cheaper LLM tokens, but how?" (Dec 2025): OpenAI automatic vs Anthropic explicit comparison.

## Notes

The marker is invisible in rendered markdown. This was a deliberate choice: it should not pollute the reading experience for humans who view the file in a markdown viewer. Lint enforces the contract from the source file; rendering tools may strip it harmlessly.

If a future evolution of the workflow embeds in-file dynamic content (e.g., a slash command that takes a free-form paste block within its body), the marker rule generalizes: marker placed BEFORE the dynamic section. A new ADR would be written only if the broader convention (one marker, last non-blank line) needs to change. The audit during slice 03 confirmed no current command needs this.

Slice 03 closes Wave 1 of the 2026-05-15 context-engineering uplift task. Wave 2 (memory layer: compact-task-memory, USER_MEMORY.md, reflexion-style learnings) opens after the `where-we-at` macro checkpoint.
