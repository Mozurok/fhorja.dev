# Eval scenario 117: the Godot surface is dimension-routed and a 3D scene plan must declare its renderer tier

- **Tags**: ADR-0117, godot, 3d, dimension-routing, no-new-command, reference-layer, structural
- **Last reviewed**: 2026-07-26
- **Status**: active

## Goal

Validates **ADR-0117** (Godot 3D ships as a dimension-routed widening of the existing surface, not a new cluster): the seven previously 2D-bound command files no longer name 2D as a default dimension, `godot-scene-plan` treats a 3D scene plan with no declared renderer tier as incomplete, and the three `wos/godot-3d-*.md` topics are reachable from the spec's Minimum read map without duplicating 2D prose. This is a structural scenario, exercised by running the check functions directly rather than by reading a model's prose output, per `TEST_STRATEGY.md` scenarios 1, 2, 3, and 5.

This exercises:

- The tier gate exists and is enforceable: `check_godot_tier_gate()` fails when `commands/godot-scene-plan.md` loses the `REQUIRED` marking, loses the stated incompleteness consequence, stops carrying the three tiers (`Forward+`, `Mobile`, `Compatibility`) as ONE enumeration in either the declaring step or the self-review step, stops naming both dimension values in the self-review step, or renames the fence info string the declaration parser matches. The enumeration is asserted as a contiguous list, not per value: `Forward+` appears three times on the declaring line and `Compatibility` twice, only one of each inside the canonical list, so a per-value substring test was satisfied by incidental prose and two of its three assertions were dead.
- No 2D default survives: `check_godot_dimension_routing()` fails when any command file mentions 2D and never mentions 3D, which is the machine-visible form of the silent-2D-assumption risk ADR-0117 `## Consequences` names.
- No orphaned topic, no dangling row, and no copied prose: `check_godot_3d_topics_indexed()` fails when a `wos/godot-3d-*.md` file is missing from the `WORKFLOW_OPERATING_SYSTEM.md` read map, when the read map cites a `wos/godot-3d-*.md` that is not on disk, or when any sentence of 12 or more words is duplicated verbatim between a 3D topic and ANY other Godot topic, including another 3D topic, instead of cross-referenced. Quoted and fenced material is exempt in both fence characters, because two topics showing the same API call or quoting the same upstream sentence is shared material rather than copied prose. This is the machine-visible form of ADR-0117 D-5, widened to the 3D-to-3D direction the original wording left open.
- No new command was added: `count:commands` is unchanged by the widening, which the existing `count-markers` check already asserts.

## Setup

No live harness or model turn needed; this is a static-invariant scenario backed by three functions in `evals/scripts/structural-evals.py`, run automatically by the `structural-evals` CI job on every push per `.github/workflows/lint.yml`.

- A checkout of this repo with the ADR-0117 changes applied: the seven widened command files, the three `wos/godot-3d-*.md` topics, the Minimum read map entries, and the regenerated `.claude/skills/*/SKILL.md`.
- A scratch copy of the files a step temporarily breaks, restored at the end of the run.

## Steps

1. Run `python3 ./evals/scripts/structural-evals.py` against the unmodified checkout. Capture the `godot-tier-gate`, `godot-dimension-routing`, and `godot-3d-topics-indexed` lines. All three must PASS.
2. Back up `commands/godot-scene-plan.md`. Replace `REQUIRED for a 3D target` with `optional for a 3D target`. Re-run. `godot-tier-gate` must FAIL, naming the missing `REQUIRED` marking. Restore the file.
2b. Back up the same file again. Delete the whole `- **Step 8a:` line. Re-run. `godot-tier-gate` must FAIL, naming the missing self-review step. Restore the file. This step exists because the check previously graded the FIRST step matching a loose filter, so deleting the declaring step let a different step take its place and the gate passed with the requirement gone.
3. Back up `WORKFLOW_OPERATING_SYSTEM.md`. Rename one `wos/godot-3d-*.md` reference in the Minimum read map so the topic is unreachable. Re-run. `godot-3d-topics-indexed` must FAIL, naming the orphaned topic. Restore the file.
4. Back up `commands/test-strategy.md`. Replace every `3D` token with a placeholder so the file mentions 2D and never 3D. Re-run. `godot-dimension-routing` must FAIL, naming that file. Restore the file.
2c. Back up `commands/godot-scene-plan.md`. Replace the canonical tier enumeration `naming exactly one of `Forward+`, `Mobile`, or `Compatibility`` with `naming exactly one of `Mobile``. Re-run. `godot-tier-gate` must FAIL, naming the enumeration. Restore the file. This step exists because the superseded per-value test still passed with the list gutted down to a single tier.
2d. Back up the same file again. Replace every `wos-godot-declaration` occurrence with `wos-godot-decl`. Re-run. `godot-tier-gate` must FAIL, naming the fence info string. Restore the file. That string is the one anchor the whole gate keys on, and renaming it in the contract failed zero checks.
3b. Back up two `wos/godot-3d-*.md` topics. Append a sentence of 12 or more words copied verbatim from one into the other. Re-run. `godot-3d-topics-indexed` must FAIL, naming BOTH files. Restore them.
3c. Back up `WORKFLOW_OPERATING_SYSTEM.md`. Add a Minimum read map row naming a `wos/godot-3d-*.md` that does not exist. Re-run. `godot-3d-topics-indexed` must FAIL, naming the dangling row. Restore the file.
5. Re-run once more against the restored checkout and confirm all three PASS again.

## Pass criteria

- Step 1: all three checks PASS on the clean checkout.
- Step 2: `godot-tier-gate` FAILS and its failure names the missing `REQUIRED` marking. A pass here means the gate is decorative.
- Step 2b: `godot-tier-gate` FAILS and names the missing self-review step. Every literal this scenario tells you to substitute is grepped in the file it names before the run; the superseded version of this step named `SHALL name the renderer tier`, which appeared zero times, so the step could not be executed as written and nobody noticed.
- Step 2c: `godot-tier-gate` FAILS and its failure names the enumeration rather than a single tier, since the point is that the list is asserted as a list.
- Step 2d: `godot-tier-gate` FAILS and names the fence info string the parser matches.
- Step 3: `godot-3d-topics-indexed` FAILS and names the specific orphaned topic file.
- Step 3b: `godot-3d-topics-indexed` FAILS and names BOTH files of the pair, since "duplicated from a 2D topic" is the wrong sentence for a 3D-to-3D copy and the operator needs both ends to act.
- Step 3c: `godot-3d-topics-indexed` FAILS and names the file the read map cites but disk does not carry.
- Step 4: `godot-dimension-routing` FAILS and names `commands/test-strategy.md` specifically, not a generic count.
- Step 5: all three PASS again, proving the failures came from the injected breakage and not from a dirty tree.

## FAIL

- Any of the three checks PASSES in its corresponding breakage step. A check that cannot fail is not protecting anything, and this scenario exists precisely because the tier gate is the only new behavior ADR-0117 introduced.
- A check FAILS in step 1 or step 5, meaning the real corpus does not satisfy the invariant it asserts.
- A failure message names a count without naming the offending file, since the operator cannot act on that.
- `count:commands` changed, which would mean the widening quietly added a command and contradicted ADR-0117 D-1 and D-9.
