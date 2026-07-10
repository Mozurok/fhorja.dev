# ADR-0033: verify-against-rubric command + stateless sub-agent verification (supersedes judge.py)

- **Status**: Accepted
- **Date**: 2026-06-04
- **Tags**: verification, sub-agent, stateless-grader, anthropic-outcomes, supersedes-judge-py
- **Supersedes:** ADR-0019 (`LLM-as-judge eval layer`) Python implementation. The eval-scenario use case remains valid in concept; the Python harness is deprecated.

## Context

ADR-0019 introduced an LLM-as-judge eval layer with a Python implementation (`evals/scripts/judge.py`, 236 lines, created 2026-05-18). The audit on 2026-06-04 (per F.1 of WOS improvement plan) showed:

- 17 days elapsed since creation; **zero invocations** of judge.py in any task, transcript, or commit since its creation.
- Bruno's own assessment (Q2 of 2026-06-03 plan questions): "Acredito que poderias melhorar isso se necessário pro nosso fluxo" -- the script is dormant and available-but-unused.
- The eval workflow (manual via `run-evals.sh --judge`) never integrated into the normal task closure pipeline.

Meanwhile, two external developments changed what "good verification" looks like:

1. **Anthropic Outcomes API (released 2026-05-06):** demonstrated +10pp success rate when the grader runs in a stateless, isolated context vs same-context critique. The grader-as-sub-agent pattern is now the validated production shape.
2. **Same-context critique limits:** `self-critique-and-revise` (ADR-0021) is a useful in-thread evaluator-optimizer for LOW/MEDIUM complexity, but inherits same-context bias on HIGH complexity (the agent that wrote the artifact is also the one critiquing it).

The gap: there is no independent verification primitive in the WOS for HIGH-complexity slices. judge.py was supposed to fill that gap; the empirical signal is that it did not.

## Decision

Introduce `commands/verify-against-rubric.md`. A single command that spawns a stateless sub-agent (Claude Code `Task` tool, Cursor agent mode subagent, or equivalent vendor primitive) with ONLY:

- The artifact path (read-only access).
- The locked rubric (inline or referenced section).

The sub-agent receives NO TASK_STATE.md, NO DECISIONS.md, and NO prior conversation history. It returns a structured verdict (per-criterion + overall classification: satisfied / needs_revision / failed). The main thread persists the verdict to a new optional task file `VERIFICATION_LOG.md` and updates `TASK_STATE.md` to reference the verdict id.

`evals/scripts/judge.py` is deprecated. The top of the file is annotated with the deprecation notice referencing this ADR. The file remains in the repo as archival reference (immutability per `docs/adr/README.md` discipline); future verification work uses `verify-against-rubric` instead.

When to use:

- After `pr-package` for HIGH-complexity slices (before submitting the PR).
- After `contract-signoff` when the contract has high-stakes downstream impact.
- After `review-hard` finds findings on HIGH-complexity slices and wants independent confirmation.

When NOT to use:

- LOW or MEDIUM complexity slices (`self-critique-and-revise` is the cheaper alternative).
- Cosmetic / formatting issues caught by lint or visual review.

## Consequences

### Positive

- Independent verification primitive available for HIGH-complexity work, aligned with Anthropic Outcomes pattern (validated +10pp).
- Sub-agent isolation cuts same-context bias; the verdict comes from a context that did not produce the artifact.
- Vendor-portable: implemented via the host's stateless sub-agent primitive (Claude Code Task tool, Cursor agent mode, Codex agents), not tied to a Python middleware.
- judge.py deprecated cleanly; no orphan code path confuses future readers about where verification happens.

### Negative

- Sub-agent dispatch costs context tokens (the sub-agent has its own context window load). Acceptable when independence value > token cost; restricted to HIGH-complexity slices by command policy.
- VERIFICATION_LOG.md is a new optional task file. One more artifact to maintain, but append-only and short.
- Initial adoption requires Bruno to remember to invoke the command. Mitigated by integration with pr-package / contract-signoff / review-hard "next command" recommendations.

### Neutral

- The eval-scenario use case from ADR-0019 (running judge.py against `evals/scenarios/*.md`) remains conceptually valid but moves to manual / ad hoc until a different need surfaces. The eval scenarios under `evals/scenarios/` continue to be readable spec docs.
- `self-critique-and-revise` continues to exist for LOW/MEDIUM cases. Two complementary primitives, not a replacement.

## Alternatives considered

### Alternative 1: Revive judge.py with better integration

- Add `judge` as a slash command, integrate with slice-closure automatically.
- Rejected: even with auto-integration, the same-context-bias problem persists if judge.py runs in the parent thread. And the Python middleware is one more thing to maintain vs the host's native sub-agent primitive.

### Alternative 2: Extend self-critique-and-revise to support a "stateless mode"

- Add a flag that spawns a fresh sub-agent context.
- Rejected: muddles the contract. `self-critique-and-revise` is documented as in-thread; mixing modes confuses callers about which behavior they get.

### Alternative 3: Do nothing; rely on self-critique-and-revise + review-hard

- Continue as today; tolerate the same-context bias on HIGH-complexity work.
- Rejected: the +10pp signal from Anthropic Outcomes is too strong to ignore on critical slices, and Bruno's stack (auth, billing, etc. via Supabase) has at least a few HIGH-complexity slices per quarter that warrant independent verification.

## References

- `commands/verify-against-rubric.md` -- new command introduced by this ADR.
- `evals/scripts/judge.py` -- deprecated; archival reference only.
- ADR-0019 (`LLM-as-judge eval layer`) -- the eval-scenario use case remains; the Python implementation is superseded.
- ADR-0021 (`Evaluator-optimizer via self-critique-and-revise`) -- complementary; covers LOW/MEDIUM complexity in-thread.
- Anthropic Outcomes API (2026-05-06) -- external pattern reference.
- `_internal/verify-against-rubric-design-2026-06.md` -- F.1 audit + F.2 design rationale.

## Notes

If verify-against-rubric proves valuable in practice (Bruno invokes it on most HIGH-complexity slices), a future ADR may extend it to MEDIUM complexity. For now, the policy restricts it to HIGH to control token cost.

VERIFICATION_LOG.md is APPEND-ONLY. Old verdicts are immutable history; do not edit past entries even when the verdict turns out to be wrong. Wrong verdicts get a follow-up entry with a corrected verdict and a `superseded_by:` reference.
