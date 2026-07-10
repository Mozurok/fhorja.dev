# ADR-0048: A passing deterministic gate satisfies Layer 1 evidence

- **Status**: Accepted
- **Date**: 2026-06-22
- **Tags**: verification, evidence, deterministic-gate, hooks, three-layer-gate, additive, human-in-the-loop

## Context

Wave 1 of the `2026-06-21_implement-wos-improvement-backlog` task added W-02: `implement-approved-slice` must paste the verbatim command and its real output as proof of each validated exit criterion (asserted-not-shown counts as unverified). Wave 3 (W-05) named the three-layer quality gate in `wos/gate-conditions.md`: Layer 1 deterministic checks (typecheck, lint, tests), then Layer 2 AI risk review, then Layer 3 human approval.

The research (W-20, grounded in the Claude Code best-practices source) recommended deterministic Stop/PostToolUse hooks as the strongest verification surface: a script that runs the checks and blocks the turn until they pass. The WOS itself is markdown plus bash plus a small Python helper with no product runtime to gate, so the hook lives in the CONSUMING product repo, not here. The open question: when such a gate is wired and passing, does the agent still have to paste each command's output per exit criterion (W-02), or does the gate result itself count as the evidence?

## Decision

A passing deterministic gate (a Stop or PostToolUse hook in the consuming repo that runs typecheck, lint, and the changed-file tests and blocks until they pass) satisfies Layer 1 of the three-layer quality gate. When such a gate is wired and passing, `implement-approved-slice` may record "deterministic gate passed" as the Layer 1 evidence for the slice's exit criteria, instead of re-pasting each command's output.

Constraints:

- Fallback intact. When no gate is wired, or the gate fails, the W-02 rule holds in full: paste the verbatim command and its real output per validated exit criterion; asserted-not-shown is unverified.
- Layers 2 and 3 still apply. A passing Layer 1 gate does not skip AI risk review (`review-hard`, `repo-consistency-sweep`, `security-review`) or human approval. It substitutes only for the Layer 1 evidence-pasting.
- The gate lives in the consuming repo. The WOS documents the convention and ships a template (`templates/deterministic-gate-hook.template.md`) and a lighter non-blocking example (`scripts/typecheck-hook.sh`); it does not run the gate itself.
- Evidence, not trust. The gate's pass/fail IS the evidence. A gate that is claimed-but-not-shown is no better than an asserted "tests pass"; the agent cites the gate's actual result.

This is additive: it adds an evidence-substitution rule to the verification contract; it changes no command's behavior when no gate is wired.

## Consequences

### Positive

- Cuts repetitive output-pasting on repos that already run a blocking gate, while keeping the honest-evidence guarantee (the gate is deterministic and blocks the turn).
- Aligns the WOS with the strongest 2026 verification surface (deterministic Stop hooks) without adding a runtime the WOS does not have.

### Negative

- A misconfigured gate (one that passes without actually running the checks) would launder false confidence. Mitigated by requiring the gate's actual result be cited and by the template showing a correct blocking gate.

### Neutral

- Layers 2 and 3 are untouched; the human still approves the merge (consistent with ADR-0044's no-auto-merge posture).

## Alternatives considered

### Alternative 1: always require per-criterion output pasting, even with a gate

- Rejected. On a repo with a passing blocking gate, re-pasting each command's output is redundant ceremony; the gate already proved it deterministically.

### Alternative 2: let a gate skip Layers 2 and 3

- Rejected. A deterministic gate proves the mechanical checks pass; it does not assess design risk or substitute for human judgment. Only Layer 1 evidence is substituted.

## References

- `projects/<client>__<project>/active/2026-06-21_implement-wos-improvement-backlog/` (W-20, W-02, W-05) and the captured Claude Code best-practices source in the project `REFERENCES.md`.
- `wos/gate-conditions.md` (the three-layer quality gate, W-05), `commands/implement-approved-slice.md` (W-02 evidence rule + W-20 note), `templates/deterministic-gate-hook.template.md`, `scripts/typecheck-hook.sh`.
- ADR-0043 (reference-grounding execution gate) and ADR-0044 (no auto-merge), the adjacent human-gated verification decisions.

## Notes

Locked in the `2026-06-21_implement-wos-improvement-backlog` task (Wave 5, Bundle 5). Status stays Proposed until the maintainer signs off.
