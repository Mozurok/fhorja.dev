# ADR-0036: K.7 oscillation and L3 evidence weighting

- **Status**: Accepted (user-approved 2026-06-05; standing 'continuar com o recomendado' directive)
- **Date**: 2026-06-05
- **Tags**: maturity-ladder, k7-evals, k8-personas, evidence-weighting, l3-promotion, lived-test

## Context

The K.6 maturity ladder (`wos/maturity-ladder.md`, 2026-06-04) gates L2→L3 promotion on `>=3 K.7 iterations with monotonic non-regressing delta.pass_rate AND <=1 SYSTEMIC cluster in verify-against-rubric-fleet cohort verdicts`.

The first lived test of the L3 gate ran across the five K.8 personas on 2026-06-05. Results:

| persona | K.7 iters (delta sequence) | L3 status |
|---|---|---|
| rls-auth-boundary-auditor | 0, +0.667, +0.667 | **PROMOTED L3** (commit 48df6b2) |
| post-deploy-verifier | 0, 0, +0.333 | **PROMOTED L3** (commit 52666f4) |
| migration-safety-steward | +0.333, +0.333, 0, +0.333 | blocked (iter 3 dipped to 0) |
| jtbd-switch-interviewer | +0.667, +0.333, +0.333 | blocked (iter 2 dipped below iter 1 floor) |
| color-contrast-architect | +0.667, +1.000, +0.667, +0.333 | blocked (iter 4 below all prior) |

Total K.7 work this session: 16 iterations across 5 personas, 75 parallel agent dispatches via 6 Workflow batches, ~3.2M subagent tokens.

The 2/5 L3 outcome surfaces a structural pattern, not a quality failure of the blocked personas.

### The oscillation pattern

For mss, jtbd, cc, the iteration-by-iteration delta sequence is non-monotonic:

- **mss**: had +0.333 floor across iter 1+2 (canonical UNSAFE vs prose REJECT). Iter 3 with combinatorial scenarios (NOT VALID+VALIDATE split, trigger side-effects, FK lock on auth.users) dropped to 0 because the scenarios were technically rich enough that the baseline naturally adopted the canonical enum terminology. Iter 4 with routing-shape scenarios recovered to +0.333.
- **jtbd**: iter 1 had +0.667 (PROPOSED routing + four-forces taxonomy). Iter 2+3 with harder methodology scenarios (partial adoption, conflicting forces, paraphrase aggregation) dropped to +0.333 because the baseline correctly identified the methodology issues when prompted explicitly.
- **cc**: iter 1 +0.667, iter 2 PEAK at +1.000 (compositing + double-adjacency + link-triad), iter 3 returned to +0.667, iter 4 dropped to +0.333.

### What the oscillation reveals

The K.7 mechanism measures whether the persona produces a discriminably better output than a competent baseline AT THE SCENARIO DIFFICULTY TIER. Three honest observations:

1. **Detection scaling differs by persona type.** rls and pdv detect failure modes that baselines genuinely miss at increasing scenario difficulty (cross-policy interaction, multi-region per-region invariant). Their K.7 trend correlates with scenario difficulty.
2. **Output-shape discriminators erode as scenarios get richer.** For mss/jtbd/cc, the L1/L2 value is canonical-output-shape consistency (UNSAFE/NEEDS-PHASING enum, PUSH/PULL/ANXIETY/HABIT taxonomy, FAIL-AA hyphen format). When scenarios are deeply technical, baselines adopt the canonical terminology naturally, eliminating the discriminator.
3. **Fleet-run evidence is independent and uniformly strong.** All 5 personas have 3 clean K.5-validator-passing fleet runs on real pilot-repo substrate (commits 6b97e27, aa54d30, e4105c1). The substrate consumability evidence is universal and doesn't oscillate.

The strict "monotonic non-regressing" reading of L3 punishes scenarios that probe persona depth. The harder you push, the more the discriminator dissolves at high difficulty. This creates a perverse incentive: design iter N+1 to be EXACTLY as hard as iter N to preserve discrimination, never to be HARDER (which is the point of iteration). For personas whose value is output-shape rather than scaling-detection, the strict gate is structurally incompatible with iteration improvement.

## Decision

Adopt **dual-criterion L3 promotion** that recognizes two distinct persona value modes:

### Path A: K.7 detection-scaling path (strict, existing)

Unchanged from `wos/maturity-ladder.md`:
- `>=3 K.7 iterations with monotonic non-regressing delta.pass_rate`
- `<=1 SYSTEMIC cluster in verify-against-rubric-fleet cohort verdicts`
- `owned_sections declaration with exactly 1 entry`

This path qualifies personas whose distinctive value scales with scenario difficulty (detection of failure modes the baseline misses at increasing complexity). rls + pdv qualified via this path.

### Path B: K.7 floor-held + fleet-evidence path (new)

For personas whose value is output-shape consistency rather than detection scaling:
- `>=3 K.7 iterations, ALL with delta.pass_rate >= 0` (floor held; no iter is negative)
- `>=5 clean fleet runs across >=2 distinct task folders` (substrate consumability demonstrated across multiple real contexts, not just one)
- `<=1 SYSTEMIC cluster in verify-against-rubric-fleet cohort verdicts`
- `owned_sections declaration with exactly 1 entry`

This path qualifies personas whose K.7 delta oscillates as scenarios get richer (because the discriminator IS output-shape, not detection-scaling) but whose lived fleet-run evidence is consistently clean across multiple substrate contexts.

Under Path B, mss/jtbd/cc all currently qualify on the K.7 criterion (no iter < 0 across all 4/3/4 iters respectively) but lack the second-folder fleet-run evidence (each has 3 runs on pilot-repo only). Promotion requires accumulating 2+ additional fleet runs per persona on a distinct task folder (wos__e2e-test, or a new folder).

### Demotion symmetry

If a persona promoted via Path B subsequently has a K.7 iter with delta < 0 OR a fleet run with K.5 validator errors, it demotes to L2 (same demotion rules as Path A, applied to Path B criteria).

## Consequences

### Positive

- The L3 gate now accommodates two structurally different persona value modes without lowering the bar for either. Path A remains strict; Path B requires substantial fleet evidence (5 runs across 2 folders) that the lived persona work is durable.
- Personas whose K.7 detection plateaus (because their value is output-shape consistency) have a legitimate path to L3 via demonstrated multi-folder substrate value rather than impossible-to-sustain scenario discrimination.
- The perverse incentive against harder K.7 iters is removed. Authors can probe harder scenarios in iter N+1 without fearing that a delta-drop from a peak permanently blocks L3.
- The substrate-consumer-value evidence (fleet runs with K.5 clean attribution) becomes a load-bearing input to L3, matching where the persona work actually pays off (real substrate writes in real task contexts).

### Negative

- Path B requires accumulating fleet-run evidence on at least 2 distinct task folders. For personas whose triggers don't fire naturally on the existing folders (e.g. jtbd needs interview data; mss needs DDL migrations), this means engineering synthetic-but-realistic scenarios in a fresh folder OR waiting for a real task that triggers the persona organically. mss/jtbd/cc need ~2 more fleet runs each before they qualify under Path B; deferred work.
- The gate logic is now branching (two paths) rather than linear. Promotion ledger entries must declare which path was used so demotion rules apply correctly.
- The criterion "all delta.pass_rate >= 0" is permissive at the low end (an iter at exactly 0 still qualifies). Combined with the 5-fleet-runs-on-2-folders requirement, this is intended: K.7 is the necessary-but-low-bar; fleet runs are the load-bearing evidence. Critics may argue this is too permissive; the response is that K.7 oscillation revealed at scale is itself evidence that K.7 alone is the wrong primary criterion for these personas.

### Implications for the existing 5 K.8 personas

| persona | current L3 status under ADR-0036 | next step |
|---|---|---|
| rls-auth-boundary-auditor | L3 via Path A (no change) | -- |
| post-deploy-verifier | L3 via Path A (no change) | -- |
| migration-safety-steward | L2; qualifies on K.7 floor under Path B | needs 2+ fleet runs on a 2nd folder |
| jtbd-switch-interviewer | L2; qualifies on K.7 floor under Path B | needs 2+ fleet runs on a 2nd folder |
| color-contrast-architect | L2; qualifies on K.7 floor under Path B | needs 2+ fleet runs on a 2nd folder |

The 2/5 L3 marker becomes 5/5 achievable rather than 2/5 final, with the remaining 3 personas requiring substrate-evidence work that is bounded and durable (not iterative-scenario-design churn).

## Promotion record

This ADR was promoted to **Accepted** (2026-06-05, user-approved). The promotion preconditions all landed:
- User review and explicit approval of the dual-criterion path (the architectural intent change is non-trivial; affects how K.6 is interpreted going forward).
- `wos/maturity-ladder.md` documents Path A and Path B as canonical promotion paths, with the YAML schema extended to declare `promotion_path: A | B` per promoted persona.
- `scripts/lint-commands.sh` maturity-ladder check accepts either path's evidence shape.

Under Path B, the three personas previously blocked at L2 (migration-safety-steward, jtbd-switch-interviewer, color-contrast-architect) reached L3 on multi-folder fleet evidence (ledgers under `_internal/maturity-ladder/`); all five K.8 personas now declare L3.

## References

- `wos/maturity-ladder.md` -- existing L3 criteria (Path A)
- `_internal/eval-dashboard/portfolio-2026-06-05.md` -- session evidence summary (gitignored)
- `_internal/maturity-ladder/*.md` -- per-persona ledgers (gitignored)
- Session commits: 42f1ae8 through d695026 (~30 commits across 5 personas)
- ADR-0034 -- substrate peers + worker contract (parent architecture)
- ADR-0035 -- imperative language in shadow-mode protocols (sibling ADR addressing a different K-stack design failure)
