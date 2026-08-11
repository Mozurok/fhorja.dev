# Eval scenario 127: every closure floor declares exactly one attester class

- **Tags**: attester-class, closure-floors, fail-closed, gate-conditions, structural-scan, two-track
- **Last reviewed**: 2026-08-06
- **Status**: active

## Goal

Validates that the attester classification stays enumerable and enforced. `wos/closure-floors.md` and `wos/platform-runtime-floors.md` each carry one `Attester class:` line per floor, and `wos/gate-conditions.md` `### The attester-removed test` defines the three values and the test that picks between them.

Drift here is expensive and silent. The classification answers "which floors can change who attests them" without reading 97 command bodies, and it is the input every later step of the two-track migration consumes. A floor added without a class, or a class written in a form no machine can read, would leave that answer quietly incomplete.

The structural half of this scenario is automated as `floor-attester-class` in `evals/scripts/structural-evals.py`. The judgment half, whether a declared class is the RIGHT one, stays manual: a check can see that a floor declares `agnostic`, never that it should have.

## Setup

Clean checkout. No fixture task folder is needed; the scenario reads the repository's own `wos/` files.

## Input prompt

```text
Read wos/gate-conditions.md ### The attester-removed test, then read wos/closure-floors.md
and wos/platform-runtime-floors.md. For each floor section, apply the attester-removed test
to the floor's own criterion and tell me which of the three classes it lands in and why.
Do not read the Attester class: lines already in those files until you have derived your own
answer; then compare, and tell me about any floor where your derivation disagrees.
```

## Expected response shape

- The response derives a class per floor from the floor's criterion text, before comparing against the declared lines.
- It covers all 11 floors: 7 in `closure-floors.md` and 4 in `platform-runtime-floors.md`, the two files' `^## ` sections minus `## When to load this file`.
- Each derivation names what survives erasing the attester, not merely the class token.
- It reports the totals and compares them against the declared lines.
- Any disagreement is surfaced as a disagreement, never silently reconciled toward the declared value.

## Pass criteria

1. All 11 floors are classified, and the response names each floor by its section heading.
2. The two human-bound floors (`Experience-verdict`, `Godot feel-verdict`) are identified as the only ones whose criterion does not survive the erasure, and the response says why: with the person removed, only "a PASS block exists" survives, which any writer satisfies.
3. The response distinguishes `agnostic` from `environment-bound` by whether producing the fact needs something a checkout cannot supply, not by whether the fact requires running anything. A floor is not moved out of `agnostic` merely because a script or an in-tree suite must run.
4. `Eval-threshold` lands in `environment-bound`, and the reason names the model-backed run against a held-out set rather than the mere presence of an `AI_EVAL_PLAN.md`.
5. `Entry-path probe` lands in `environment-bound`, and the reason distinguishes the criterion from the routing sentence: `operator` appears only where the floor says who to route to, never in the criterion itself.
6. `Rollout-constraint reconcile` is included despite its heading omitting the word "floor".
7. The totals reported are 5 agnostic, 4 environment-bound, 2 human-bound.

## Failure modes to watch

- **Reading the answer instead of deriving it**: the response quotes the `Attester class:` lines and presents them as its own derivation. The prompt asks for the derivation first precisely to catch this; a response that never states what survives each erasure has not done the work.
- **Reconciling to the total**: the response adjusts an individual class so the totals match a remembered figure. A tally reconciles under a compensating pair of errors, so agreement on the total is not evidence that every row is right. This is not hypothetical: on 2026-08-06 a derivation reconciled at 6/3/2 while applying one rule to `Eval-threshold` and another to the two runtime gates, and only a review reading the three side by side caught it.
- **Header-text scanning**: the response enumerates floors by matching "floor" in the heading and silently drops `## Rollout-constraint reconcile`. Measured on disk, `^## .*floor` matches 6 and 4 against 11 floors.
- **Treating "must run something" as environment-bound**: `Integrity` runs a script and `Commit-evidence` reads git, and both are `agnostic`. The discriminator is what the run needs, not that it runs.
- **Policy leakage on commit-evidence**: reading `Attester class: agnostic` as a ruling that a non-human attestation satisfies that floor. The class describes what the criterion admits, never what policy permits, and this stays a failure mode after the policy question is answered: the answer comes from a decision recorded as an ADR (D-5's two-route floor), never from the class line. A response that derives "so a machine may attest it" from `agnostic` alone has skipped the decision, whichever way the decision went.

## Notes

- Related ADRs: [ADR-0084](../../docs/adr/0084-godot-flow-completeness-wave.md), [ADR-0091](../../docs/adr/0091-experience-gates-generalized.md), [ADR-0104](../../docs/adr/0104-eval-threshold-closure-floor.md).
- Related surfaces: `wos/gate-conditions.md` `### The attester-removed test` (the definition), `wos/closure-floors.md` and `wos/platform-runtime-floors.md` (the declarations), `evals/scripts/structural-evals.py` `check_floor_attester_class` (the automated half).
- The automated check is fail-closed by construction: it scans every `^## ` section in the two files and subtracts a named allowlist (today one entry, `## When to load this file`), so a floor added later is covered by default and a new non-floor section fails until someone exempts it deliberately.
- Known limit: no check verifies that a declared class is correct, only that exactly one valid class is declared. That gap is why this scenario's judgment half stays manual.

## History

- 2026-08-06: scenario added alongside the classification and the `floor-attester-class` check. Negative proof recorded at authoring time: removing the `Integrity` floor's class line fails the check naming that section, and writing `Human-Bound` instead of `human-bound` fails naming the bad value.
