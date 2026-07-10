# ADR-0004: Capability routing without model SKUs

- **Status**: Accepted
- **Date**: 2026-05-08
- **Tags**: capability-routing, model-agnostic, work-complexity, future-proofing

## Context

The workflow's commands need to communicate **how hard the next step is** so the user (and any orchestrating tool) can route the right resource to it. Cheap routing is critical: a typo fix should not consume the same capability budget as a database migration.

Two communication shapes were available:

1. **Name the model directly**. "Use Claude Opus 4.7 for this slice; Haiku for the typo fix." Clear, immediate, but tightly coupled to a specific vendor's lineup at a specific time.
2. **Name the capability**. "This slice is HIGH complexity; that one is LOW." Vendor-neutral, time-stable, but requires the user to know which model maps to which capability today.

Two forces pushed against directly naming SKUs:

- **The lineup changes**. Anthropic ships new models on a roughly monthly cadence (Opus 4.6 → 4.7 → 4.8...; Haiku 4.5; Sonnet 4.6). Every command file that mentioned "Opus 4.6" would rot within weeks. The repo would either drift or accumulate constant SKU-bumping commits.
- **Multi-tool target**. The workflow targets Cursor, Claude Code, GitHub Copilot, OpenAI Codex, Gemini CLI, OpenHands, Goose, and 30+ others. Each tool ships its own model lineup. Hard-coding "Opus 4.7" in a command file means Codex users see a recommendation for a model they cannot select.

A third force pulled toward capability naming: **routing should reflect what the work needs, not what model happens to be cheapest this week**. A HIGH-complexity slice is HIGH because of the work's properties (blast radius, contract sensitivity, weak test signal), not because of the model's price. The capability label is intrinsic to the task; the model choice is a routing decision the consumer makes.

## Decision

Every command that emits a routing recommendation uses the capability rubric **`LOW` / `MEDIUM` / `HIGH` / `N/A`**, never a model SKU. The rubric is defined in `WORKFLOW_OPERATING_SYSTEM.md` → `## Global output contract` → `### Work complexity (capability routing)` and calibrated by vignettes in `wos/global-output-contract.md` → `## Calibration examples (non-normative)`.

Specifically:

- **`LOW`**: low-risk changes; mistake cost low; clear contract; small blast radius. Examples: typo fix, single failing unit test with obvious context, log-line additions.
- **`MEDIUM`**: clear integration seams; moderate blast radius; backward-compatible refactors with focused test signal; user-facing API changes with a migration path.
- **`HIGH`**: weak test signal; cross-package coordination; safety-critical paths (auth, crypto, payments); production incidents under time pressure.
- **`N/A`**: capability routing does not apply (e.g., the next step is `what-next`, which is itself a routing command).

Every command's `### Definition of done` requires the `Work complexity:` line in the Handoff to be one of those four values, with a one-line rationale and **no model name**. Lint does not currently enforce this lexically (it would require a per-line scan), but the WOS and command files cross-reference the rubric uniformly, and reviews catch SKU mentions.

When two vignettes seem to fit, the rubric prefers the higher complexity if mistake cost is asymmetric. That tiebreaker is itself non-normative calibration (lazy-loaded), but it shapes how borderline cases are graded.

## Consequences

### Positive

- The repo survives model lineup churn without per-release patches. New models slot into the existing rubric without changing a single command file.
- Multi-tool consumers (Cursor, Codex, Gemini CLI, etc.) get recommendations they can act on with whatever model their tool offers. The recommendation is "use a HIGH-complexity-capable resource", which translates to whichever model the consumer's tool maps that to.
- Future capability layers (reasoning models, computer-use models) can be added without retroactively recoloring tasks. The rubric is open-ended at the consumer's end.
- Calibration debate happens once (at the vignette level) instead of per-command.

### Negative

- A new user has to learn the rubric. "What does HIGH mean here?" is a real question; the calibration vignettes answer it but require reading.
- Mapping capability to model is left to the consumer (the user, the orchestrating tool, the IDE). For a solo developer this means picking the model manually each time; for a team it means setting up routing tables once.

### Neutral

- The `N/A` category is rare in practice. Most workflow steps have non-trivial complexity; `N/A` shows up mainly for routing commands (`what-next`, `workflow-guide`, `im-stuck`).

## Alternatives considered

### Alternative 1: Always name the latest Anthropic model

- Default the recommendation to "Opus" or "the latest Anthropic model" with a HIGH complexity hint.
- Rejected: vendor lock-in by language; rots with every release; alienates non-Anthropic tool users.

### Alternative 2: Tier the rubric to provider-neutral families

- Use "frontier" / "balanced" / "fast" instead of LOW/MEDIUM/HIGH.
- Rejected: implies a fixed mapping (frontier = top-tier model) that is just SKU naming under a thin abstraction. Capability routing is about the work, not the model class.

### Alternative 3: Let each command pick its own rubric

- Some commands use small/medium/large; others use easy/medium/hard.
- Rejected: the user has to learn N rubrics instead of one. Also breaks comparability across commands ("is medium-here the same as moderate-there?").

## References

- `WORKFLOW_OPERATING_SYSTEM.md` → `## Global output contract` → `### Work complexity (capability routing)`.
- `wos/global-output-contract.md` → `## Calibration examples (non-normative)` (lazy-loaded vignettes).
- Every `commands/*.md` `### Standard ending format` and `### Definition of done` that requires `Work complexity:` in the Handoff.
- Anthropic's repeated guidance against hard-coding model SKUs in production prompts.

## Notes

The "never name model SKUs" rule has one narrow exception: **CLAUDE.md** (this repo's internal Phase 1 context file) may name specific models to inform Claude Code about its own runtime, since CLAUDE.md is a Claude-Code-specific configuration file, not a workflow contract. That exception is local to CLAUDE.md and does not propagate into `commands/*.md` or the WOS. Other tool-specific config files (e.g., AGENTS.md for OpenAI tooling, GEMINI.md for Gemini CLI) may carry the same narrow exception when generated.
