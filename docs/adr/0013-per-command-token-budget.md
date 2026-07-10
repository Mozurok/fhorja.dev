# ADR-0013: Per-command token budget

- **Status**: Accepted
- **Date**: 2026-05-15
- **Tags**: context-engineering, token-budget, cost-visibility, lint-enforced-warning

## Context

ADR-0012 named the six context layers and made each command declare which layers it consumes and produces. That was the qualitative half. The quantitative half (how big is each command in tokens, when does the cost cross a meaningful threshold) was still implicit.

`scripts/measure-tokens.py` had a session-flow projection (5-step canonical task) but not a per-command surface. Three problems followed:

1. **Growth was invisible**. A well-intentioned addition to a command (new operating rule, new example, expanded scope) added tokens silently. Comparing month-old measurements to current was the only mechanism, and that comparison was never done routinely.
2. **Downstream slices had no foundation**. Slice 03 (cache structure) reorders commands for cache friendliness but cannot evaluate the win without a per-command baseline. Slice 04 (compact-task-memory) needs a trigger threshold. Slice 13 (context-rot guardrails) needs a budget concept to enforce.
3. **The 4 chars/token approximation was reliable enough at session scale, but per-command was never validated**. The 35 commands cluster between 1.5k and 4k tokens; the approximation's ~10% precision is more than adequate at that resolution.

Per-command budgets are also a teaching surface. Future contributors who add a new command see a budget seed and a lint that warns on overrun; this primes them to think about cost while writing, not after.

## Decision

The WOS adopts per-command token budgets as a declared frontmatter field with lint-enforced warnings:

1. **Frontmatter field**: every `commands/<name>.md` declares `metadata.token-budget:` as a positive integer ≥ 100. Kebab-case per D-7 of the 2026-05-15 context-engineering uplift task.
2. **Seeded initial values**: at slice 02 seed time, the budget for each command is `ceil(current_transitive_tokens * 1.2 / 100) * 100`. The 1.2x headroom absorbs routine wording changes; the round-to-100 makes the value human-readable.
3. **"Transitive" definition (current architecture)**: equals the command file's own bytes. Shared blocks under `commands/_shared/` are inlined into the command file by `sync-shared-blocks.sh`, so reading the command file yields the post-sync cost. The WOS bootstrap (loaded at every command run via `mandatory-context-bootstrap`) is a session-shared constant amortized by prompt cache (ADR-0006) and is explicitly NOT included.
4. **Measurement tool**: `scripts/measure-tokens.py --per-command` emits a markdown table (default) or JSON (`--json`) per command, including a suggested budget column for new commands.
5. **Baseline snapshot**: `scripts/baseline-per-command-tokens-<date>.md` captures the state at slice 02 closure. Future deltas compare against it.
6. **Lint policy (warn, not fail)**: `scripts/lint-commands.sh` recomputes current cost at lint time. When current > budget, a WARN is emitted: `command-name: current ~Ntokens > budget Nbudget`. Total overruns are reported in the summary line. Strict mode (`--strict`) escalates warnings to failures.

## Consequences

### Positive

- **Growth is now visible**. Any edit that pushes a command over its budget produces a clear lint warning. Contributors decide: raise the budget (recorded edit) or trim the command (also a recorded edit). No silent drift.
- **Downstream slices have a foundation**. Slice 03 can compare cache reorder before/after. Slice 04 can pick a compaction threshold based on the budget concept. Slice 13 can enforce session-level budgets composed from per-command ones.
- **Cost is a first-class artifact**. New contributors see `token-budget:` in frontmatter and learn the concept by example. The lint message names the rule. Zero onboarding cost for the discipline.
- **Lint summary surfaces the number**. The summary line "Token budget: N command(s) over declared budget" is a single dashboard number for cost discipline.

### Negative

- **One more frontmatter field to maintain**. The Agent Skills frontmatter grows by one field. Field is namespaced under `metadata:` to avoid conflict with the open spec.
- **Approximation drift on long commands**. The 4 chars/token approximation may be ~10% off vs the real Claude tokenizer. For 4k-token commands, that is ±400 tokens. The 1.2x headroom absorbs this comfortably.
- **Warn-not-fail can be ignored**. A team that does not act on lint warnings could let all commands drift over budget. Mitigation: slice 13 (context-rot guardrails) can escalate to FAIL once session-level budgets are in place. Strict mode is available immediately for CI gating.

### Neutral

- The decision codifies a measurement discipline the project was missing. It does not change runtime behavior; it changes what the lint reports.

## Alternatives considered

### Alternative 1: hard fail on overrun

- Any command exceeding its budget fails the lint. Commits cannot land until the budget is raised or the command is trimmed.
- **Rejected for slice 02; reconsider in slice 13**. Hard fail at this stage blocks well-intentioned scope additions on commands that may legitimately need more bytes (e.g., adding a new failure-mode classification to `incident-triage`). The warn-then-trim cycle preserves agency; slice 13's session-level budget concept will be a better place to enforce hard limits because session cost composes from many commands.

### Alternative 2: no per-command budget; rely on session-wide measurement

- Keep the existing 5-step session projection in `measure-tokens.py`; no per-command field.
- **Rejected**: invisible until someone runs the script. Per-command frontmatter surfaces the cost during edits and the lint surfaces it on every commit. Visibility beats precision.

### Alternative 3: declare budget in a separate `BUDGETS.md` file

- Keep the budget out of frontmatter; centralize in a single document.
- **Rejected**: divorces budget from the command it constrains. Editors who change a command would not see the budget. Frontmatter is the closest point of co-location.

### Alternative 4: derive budget automatically from current size

- The lint computes budget = current * 1.2 at every run; no declared value.
- **Rejected**: this means the budget tracks reality instead of constraining it. The whole point is for the budget to be a CEILING that growth must justify. An automatically-tracking budget is no constraint at all.

## References

- `scripts/measure-tokens.py` (extended with `--per-command` mode in slice 02).
- `scripts/baseline-per-command-tokens-2026-05-15.md` (the slice 02 baseline snapshot).
- `scripts/lint-commands.sh` (token-budget validation extension added in slice 02).
- `wos/context-budget.md` (the lazy-loaded framework that names the layers this budget targets).
- ADR-0006 (lazy-load WOS pattern; the reason WOS bootstrap is excluded from per-command budget).
- ADR-0012 (context budget as explicit contract; the qualitative half this quantitative slice extends).
- ADR-0011 (shared canonical blocks; the reason "transitive" cost in current architecture equals command-file own bytes after sync).
- Anthropic prompt caching docs (5-minute and 1-hour TTLs; cache floor 4096 tokens for Opus 4.7; why static prefix size matters).
- PwC, "Don't Break the Cache" (2026): empirical evidence on cache cost reductions and TTFT improvements; motivates per-command budget visibility.

## Notes

The 4 chars/token approximation is from `scripts/measure-tokens.py`. It is within ~10% of the real Claude tokenizer for English markdown. Per-command budgets are precise enough at the 2k-4k token cluster the WOS commands inhabit; budgets are rounded to nearest 100 to make this rounding explicit.

Slice 13 (context-rot guardrails) will define session-level token budgets that compose from per-command ones. If a future iteration introduces hard FAIL on overrun, that decision lives in a new ADR (per ADR immutability) rather than amending this one.
