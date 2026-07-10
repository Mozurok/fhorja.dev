# ADR-0020: Task cost observability

- **Status**: Accepted
- **Date**: 2026-05-18
- **Tags**: observability, token-cost, simulation, multi-tool-neutral, locked-assumptions

## Context

Slice 02 of the 2026-05-15 context-engineering uplift (ADR-0013) measured per-command token cost and surfaced it as a frontmatter target. That gives PER-COMMAND visibility but misses the SESSION-LEVEL picture: when a user runs a full task lifecycle (task-init through pr-package), what is the cumulative cost? And how much does prompt caching actually save?

Three failure modes the absence of task-level observability creates:

1. **Per-command optimization can be deceptive**. A command may pass its `token-budget` while task-level cost is unsustainable because the command runs many times within a session. Per-command numbers are necessary but not sufficient.
2. **Cache wins are invisible at the per-command layer**. The WOS bootstrap (~17.6k tokens) is reread per command without cache; with cache it is amortized across the session via Anthropic's 5-minute TTL multipliers (1.25x write, 0.1x read). The cost difference only becomes visible at the session level.
3. **Release-quality stats are missing**. Phase 3 public release will benefit from a published "typical task costs ~N tokens with cache" number. Today the project has per-command snapshots but no end-to-end one.

D-8 of the task's DECISIONS.md trimmed the scope explicitly: simulation only; no per-tool cache-hit tracking; no real API integration. The justification is multi-tool neutrality (ADR-0005): per-tool instrumentation locks the WOS to specific vendors; a simulation grounded in Anthropic's published cache multipliers stays vendor-neutral while providing a meaningful baseline.

## Decision

The WOS adopts a simulation-based task cost observability layer:

1. **`scripts/measure-task-cost.py`** simulates a canonical 9-phase task lifecycle: task-init -> impact-analysis -> decision-interview -> implementation-plan -> implement-approved-slice (slice 01) -> slice-closure (slice 01) -> implement-approved-slice (slice 02) -> slice-closure (slice 02) -> pr-package. For each phase, the script computes per-phase static prefix (WOS + command file), dynamic input (task memory + user invocation), and totals under three cost models: uncached (baseline) and cached (Anthropic 5-minute TTL).
2. **Locked simulation assumptions** (constants in the script and documented in this ADR's references):
   - chars/4 approximation per ADR-0013 (within ~10% of Claude tokenizer).
   - WOS bootstrap: measured from `WORKFLOW_OPERATING_SYSTEM.md` at run time.
   - Command file: measured from `commands/<name>.md` at run time (already includes inlined shared blocks per ADR-0011).
   - User input per phase: 200 tokens (constant; typical slash-command invocation).
   - TASK_STATE initial: 1500 tokens (post-task-init typical).
   - TASK_STATE growth per phase: +300 tokens (typical accumulation).
   - Cache write multiplier: 1.25x (Anthropic 5-minute TTL price tier).
   - Cache read multiplier: 0.1x (Anthropic 5-minute TTL price tier).
3. **Output**: markdown (default; per-phase table plus totals plus assumptions) or JSON (`--json` for downstream tooling).
4. **Baseline snapshots**: `scripts/baseline-task-cost-<YYYY-MM-DD>.md` is the dated snapshot. Future runs compare against the most recent snapshot; dated filenames make trend visible even without a dashboard.
5. **Explicit scope boundary** (what the script is NOT):
   - Not a real model API measurement (no tool call; no API key).
   - Not per-tool cache-hit instrumentation (Cursor/Claude Code/Codex etc. cache differently; out of scope per ADR-0005).
   - Not a trend dashboard (single-baseline snapshot per run; consume `--json` for trend tooling).
   - Not latency (depends on model AND tool AND network; not derivable from tokens alone).

## Consequences

### Positive

- **Session-level cost is visible**. The "typical task is ~Xk tokens cached, ~Yk uncached" number is now a measurable baseline. Per-command optimization can be sanity-checked against the session impact.
- **Cache savings are quantified**. The current run produces a "~67% cache savings" number that grounds discussions of why cache-friendly command structure (slice 03; ADR-0014) matters.
- **Release-quality stat ready**. A published baseline is appropriate for Phase 3 README copy ("typical task: ~70k cached tokens, ~210k uncached") without overselling.
- **Multi-tool neutral**. The simulation uses Anthropic published multipliers as the reference. Real per-tool numbers will differ, but the simulation is the "canonical" benchmark all tools can be compared against (when their numbers are available via their own instrumentation).
- **Trend-ready via JSON**. Future tooling can read the JSON output and build dashboards; the script itself stays simple.

### Negative

- **Approximation error**. chars/4 is ~10% off vs real tokenizer. Mitigation: same approximation as slice 02 (ADR-0013); consistent across the suite; the relative comparisons (cached vs uncached; slice-to-slice deltas) are more meaningful than absolute numbers.
- **TASK_STATE growth model (300 tokens/phase) is rough**. Mitigation: documented as a locked assumption; future iteration can read from a real fixture task; current value is a defensible heuristic.
- **Cache assumption (5-min TTL valid across all 9 phases)**. Slow user reactions can break the cache between phases. Mitigation: the report includes both cached and uncached totals so the user sees the boundary; future iteration could model partial-cache-hit scenarios.
- **Single baseline per run**. No automated trend tracking. Mitigation: dated filenames make manual trend comparisons trivial; JSON output enables future automation.

### Neutral

- The script is intentionally small (~200 lines). The simplicity is the value: locked assumptions; no hidden state; easy to read and modify.
- The canonical 9-phase lifecycle is one of many possible session shapes. A "long task" (15 slices) or a "small task" (3 phases) would yield different numbers. Future slices may parametrize the simulation shape if friction shows up. Not planned now.

## Alternatives considered

### Alternative 1: real API integration with per-tool instrumentation

- The script calls the Anthropic API (or each tool's equivalent) with the actual prompts; measures real token usage and cache hits.
- **Rejected**: violates ADR-0005 multi-tool neutrality. Requires API keys handled by the WOS. Locks the cost model to specific vendors. The simulation is the correct abstraction for a vendor-neutral workflow.

### Alternative 2: skip session-level measurement; rely on per-command

- Continue with slice 02's per-command budgets; no task-level numbers.
- **Rejected**: per-command is necessary but not sufficient. Cache benefits and session accumulation are invisible at the per-command layer.

### Alternative 3: trend dashboard with continuous tracking

- A daemon or CI step runs the simulation on every PR; tracks deltas; alerts on regressions.
- **Rejected for this slice; viable future**. Premature without first having stable baselines. The single-snapshot-per-day pattern via dated filenames is sufficient for v0.1.0; if friction surfaces, a future slice can add CI automation consuming the existing JSON output.

### Alternative 4: measure latency in addition to tokens

- The script measures both token cost AND simulated latency.
- **Rejected**: latency depends on model AND tool AND network; not derivable from tokens alone. Including it would invite false-precision. Tokens are the measurable invariant; latency lives in per-tool instrumentation.

### Alternative 5: full-token tokenizer (e.g., tiktoken)

- Replace chars/4 with a real tokenizer call.
- **Rejected for this slice; viable future**. The chars/4 approximation is consistent with slice 02 (ADR-0013) and is within ~10%. Switching to tiktoken would add a Python dependency and break consistency between the per-command and per-task measurements. If a future slice needs precision, it should update both measure-tokens.py and measure-task-cost.py in lockstep.

## References

- `scripts/measure-task-cost.py` (the simulation script; locked assumptions as named module constants).
- `scripts/baseline-task-cost-2026-05-18.md` (the first snapshot).
- `scripts/measure-tokens.py` (sibling; per-command cost from slice 02 / ADR-0013).
- ADR-0005 (multi-tool architecture; the reason this is simulation not per-tool instrumentation).
- ADR-0011 (shared canonical blocks; the reason command file size IS the post-sync transitive size).
- ADR-0012 (context budget; names the six layers the simulation operates on).
- ADR-0013 (per-command token budget; the chars/4 approximation reused here).
- ADR-0014 (cache-friendly command structure; the cache breakpoint that makes the cache-savings number meaningful).
- Anthropic prompt caching docs (5-min and 1-hour TTLs; price multipliers).
- D-8 of `projects/bmazurok__my-work-tasks/active/2026-05-15_context-engineering-uplift/DECISIONS.md` (Wave 2 reassessment outcome; scope-trim of this slice to simulation-only).

## Notes

The locked assumptions live as named constants at the top of `measure-task-cost.py` (`USER_INPUT_TOKENS`, `TASK_STATE_INITIAL`, `TASK_STATE_GROWTH`, `WRITE_MULT`, `READ_MULT`). Changes require updating both the constants AND this ADR's References block AND the slice 09 history.

The canonical 9-phase lifecycle reflects a TYPICAL fullstack task. Real tasks vary: a docs-only task runs 4 phases (task-init -> impact -> plan -> pr-package); a 15-slice refactor runs ~30 phases. The 9-phase baseline is the reference; users can fork the script for their own task shapes if needed.

Future iteration possibilities (out of scope for slice 09):
- Parametrize phase count and shape via CLI flags.
- Add a "real tokenizer" mode using tiktoken for precision spot-checks.
- Add a "what-if" mode: simulate a hypothetical command shape and report the cost delta.
- CI integration: fail PRs that increase the cached total by more than N% without justification.

None are planned now; all are recoverable from the existing JSON output.
