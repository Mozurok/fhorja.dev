# ADR-0109: Active epistemic humility as a claim-keyed doctrine

- **Status**: Accepted
- **Date**: 2026-07-20
- **Tags**: evidence-priority, reference-grounding, global-output-contract, abstention, belief-revision, decision-history, substrate-peers, research-driven, extends-adr-0043, extends-adr-0048

## Context

Fhorja's evidence rules are strong on the input side and absent on the output side. `WORKFLOW_OPERATING_SYSTEM.md` `## Evidence priority` carries a do-not-guess rule and a greenfield clause, and `commands/_shared/reference-grounding.md` is a mandatory execution gate. Measured against the working tree on 2026-07-20, that gate is consumed by exactly three commands (`implement-approved-slice`, `implement-slice-complement`, `implement-fleet`) and its detection step is a scan of the slice's imports and diff.

The trigger is therefore keyed to **the file set**, not to the agent's grounding. Four consequences were observed by the maintainer and confirmed against the repository:

1. Fixing a bug in a library the repository already imports never trips the gate, so the model acts from training memory without consulting documentation. The file is inside the diff; the claim about that library's behavior is outside the retrieved set.
2. Command outputs state verified facts, inferences, and assumptions in the same flat tone. `## Global output contract` mandates structure (`Artifact changes`, transcript, handoff) and never per-claim status. Of 85 command files, `code-locate` is the only one carrying confidence levels, and only for its own candidates.
3. There is no valid "I do not know" output. `NO_OP` means "no work to do", not "insufficient grounding to assert this".
4. Claims persisted into `DECISIONS.md` and `TASK_STATE.md` are never reopened when later evidence contradicts them.

A four-angle research pass (12 sources captured into the project `REFERENCES.md`, synthesized in the task's `EXTERNAL_RESEARCH.md`) produced 9 reinforcing groups, 5 different-framing groups, and 4 contradictions that survived a conservative reconciliation. All four angles independently rejected the file set as the obligation's locus, and all four independently rejected gating on self-reported confidence.

## Decision

Adopt **active epistemic humility** as a doctrine keyed to the claim rather than to the file set, delivered through folds into existing surfaces. No new command.

The normative content lives in `wos/active-epistemic-humility.md`, split into two parts that are deliberately different in kind: a mechanized part where every rule names its enforcement point, and a non-mechanized part explicitly marked as verified by nothing. The split is structural, not cosmetic: a Part 2 rule cited as a gate is a misuse, and moving a rule between parts requires an ADR.

Eleven decisions were locked (D-1 to D-11 in the task's `DECISIONS.md`). The load-bearing ones:

1. **The obligation is keyed to the load-bearing claim** (a claim a downstream command or a human decision consumes) and its traceability to an enumerable grounded set: a captured `REFERENCES.md` entry, a file read this session, command output actually seen, or a passing deterministic gate (composing with ADR-0048). A claim supported only by model memory counts as ungrounded, including when the model is right, because the model-internal axis is not observable from markdown and bash.
2. **Two orthogonal triggers.** An assertion-time trigger when a load-bearing claim falls outside the grounded set, and a defense-time trigger when new evidence bears on an already-persisted claim.
3. **Status records provenance, never confidence.** A referent (reference entry, file plus line, gate output); an empty referent reads as unknown; no confidence field, numeric threshold, or self-assessment prompt exists in the contract.
4. **Status is mandatory on persisted claims** and conditional on chat-only claims (required only when the claim routes).
5. **Abstention is a routed continuation** naming the investigation that would settle the question; a bare refusal is invalid output.
6. **Revision is append-only and provenance-capped**, reusing the existing seven-level `## Evidence priority` list as the cap function; equal-rank conflicts escalate to the user; in-task revisions annotate, and an unresolved revision blocks `task-close`.
7. **Enforcement is script-checkable structure delivered as strict imperative wording**, and an unfired gate is never read as evidence that grounding existed.

Delivery surfaces: a new shared block `commands/_shared/claim-grounding.md` consumed by a bounded set of commands (those that persist claims), one new H3 in `## Global output contract`, an additive claim-keyed test in `commands/_shared/reference-grounding.md`, and an extension of the `## Decision history` write rule in `wos/substrate-peers.md`.

## The four surfaced contradictions and their resolution

Recorded here because a research pass that surfaces contradictions and then hides how they were settled is worse than one that never surfaced them.

| # | Contradiction | Resolved by |
|---|---|---|
| C-1 | Prompt reliance: strict imperative instruction is the one lever with a measured effect on abstention, versus the finding that the comparable honest-boundary behavior came from post-training and an instruction-only version is a weak instrument | **D-11**, toward the structural side: script-checkable verification is the primary mechanism, imperative wording is its delivery, and the design must survive the agent ignoring the block |
| C-2 | Whether a standing character-level rule can carry any enforcement: the philosophy angle argues the cultivated-trait half cannot be mechanized and still belongs, the three empirical angles argue a rule depending on the agent noticing is exactly the unreliable signal | **D-6**, ship both surfaces with a structural visual separation, so unverifiable prose exists but can never be mistaken for a gate |
| C-3 | Whether every claim carries a status even when the label routes nothing | **D-8**, split by surface: always on persisted claims, only-when-routing on chat-only claims |
| C-4 | Trigger breadth: keep it sensitive everywhere, versus scope it to claims where evidence can conflict | **D-9**, dissolved rather than resolved: the two angles were arguing about two different triggers, so the doctrine defines both |

## Consequences

**Accepted.**

- The bounded consumer set for `claim-grounding.md` is a pattern this repository does not have. Shared-block fan-out is bimodal: five blocks sit at 76 to 85 consumers and every other block at 1 to 4, with nothing in between. The membership rule must be stated in the block itself or the set drifts toward universal, which is the ceremony this doctrine's own non-goal forbids.
- The instruction-versus-training gap is not closed, only named. No source establishes that an instruction-level rule reproduces the effect obtained through preference training. The paired eval scenarios are the falsification mechanism; the doctrine is designed assuming the agent sometimes skips it.
- The doctrine's core behavior (did the run genuinely abstain?) is verifiable only by a human walking `evals/scripts/run-evals.sh`. `evals/scripts/structural-evals.py` does not run a model, so no CI check will ever decide it.
- 63 of 109 existing eval scenarios assert on output layout, artifact changes, or handoff. They will keep passing whether or not this doctrine fires, so a green suite is not evidence that the change works. This is the same shape as the ADR-0108 auth-harness gap and is recorded as a named coverage gap, not a defect.
- Cost has no gate. The fully-grounded path is designed to be a membership lookup, and the token cost is measured against the `scripts/baseline-*.md` snapshot rather than thresholded, because no source quantifies an acceptable figure and a number chosen now would be invented.

**Explicitly not changed.**

- `## Evidence priority` keeps its wording and ordering; this ADR reuses that list as a cap function.
- ADR-0043's gate and its import-and-diff detection keep working for the case they already cover. The file set is retired as the doctrine's key, not the gate from the repository.
- ADR-0086's read-the-comment-thread obligation is untouched.
- No command is added, and no existing command is removed or renamed.

## References

- `wos/active-epistemic-humility.md`: the normative topic this ADR accepts.
- Task `projects/bmazurok__my-work-tasks/active/2026-07-20_epistemic-humility-doctrine/`: `BRIEF.md` (framing), `EXTERNAL_RESEARCH.md` (12 sources, 4 angles, 4 contradictions), `DECISIONS.md` (D-1 to D-11), `IMPACT_ANALYSIS.md` (measured fold surface), `TEST_STRATEGY.md` (12 scenarios).
- ADR-0043 (reference-grounding execution gate), ADR-0048 (a passing deterministic gate satisfies Layer 1 evidence), ADR-0086 (deep issue-thread research), ADR-0108 (external-contract live-verification gate).
