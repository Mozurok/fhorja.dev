# Scenario 140: no taxonomy code and no named battery rule was lost in the adapter extraction

- Command under test: `evals/scripts/structural-evals.py` (`check_runtime_verify_parity`), over `commands/*runtime-verify.md` and `wos/*-runtime-battery.md`
- Mode: structural (the check is a hard failure in the CI structural-evals job)
- Related ADRs: [ADR-0177](../../docs/adr/0177-runtime-verify-skeleton-and-adapters.md), [ADR-0048](../../docs/adr/0048-deterministic-gate-evidence.md), [ADR-0116](../../docs/adr/0116-single-load-stage-size-budget.md)

## Goal

Prove that the four runtime gates can be reshaped without quietly losing a classification or a rule.

The four commands measured 99661 chars before the extraction and ran the same eight steps four times over, each carrying its own adapter inline. Moving the adapters into `wos/` topics and sharing the skeleton is the first half of that reshaping; merging the four commands is the question wave 8 asks. Both moves rewrite prose that reads as boilerplate, and the failure they invite is silent: a taxonomy code drops out of a rewritten paragraph and nothing notices, because a code nobody emits looks exactly like a code nobody needed.

This scenario is the inventory that makes the reshape provable. Every code and every named rule that existed before the move is listed below beside the file it lives in today. The check requires each to be present in ANY of the eight files, which is what lets a merge move text freely while still having to prove it kept everything.

## Setup

None. The check reads the tracked tree.

## Steps

1. Run `python3 evals/scripts/structural-evals.py` and read the `runtime-verify-parity` line.
2. For the negative case, delete `LAUNCH_INTENT_LOST` from `wos/app-runtime-battery.md`, run the check again, then restore with `git checkout -- wos/app-runtime-battery.md`.
3. Repeat with `PLAYTEST_RUNBOOK.md`, deleting it from BOTH `wos/godot-runtime-battery.md` and `commands/godot-runtime-verify.md`. Deleting it from the topic alone leaves the check GREEN, measured 2026-08-30, because the command's Step 7 still names the artifact.

## Pass criteria

1. The check reports `[PASS] runtime-verify-parity` with the whole inventory satisfied: 10 app codes, 8 web codes, 9 api codes, 11 godot codes (38 entries, 35 distinct: `CLEAN` is shared by all four), and 16 named battery rules.
2. Deleting `LAUNCH_INTENT_LOST` fails the check by name, with a message saying the classification it named can no longer be emitted. Restoring the file returns the check to PASS.
3. Deleting `PLAYTEST_RUNBOOK.md` from BOTH files fails the same way, proving the inventory covers named rules and not only taxonomy codes. Deleting it from one does NOT fail, and that asymmetry is the check behaving correctly rather than a hole: the inventory holds 54 list items, 51 of them distinct (35 codes plus 16 rules; `CLEAN` appears in all four taxonomies), and 24 of those 51 live in more than one file today. Requiring a specific file for any of them would forbid the merge. `LAUNCH_INTENT_LOST` is usable as a single-file proof precisely because it is one of the 27 that live in exactly one.
4. A code is satisfied by presence in ANY of `commands/*runtime-verify.md` or `wos/*-runtime-battery.md`, never by presence in one specific file. That is deliberate: pinning a code to a file would forbid the merge this inventory exists to enable.
5. Both lists are LITERAL, not derived. A list computed from the files it checks would empty itself along with them, which is the failure mode of every inventory that regenerates from its own subject.
6. An empty scan is a failure, not a vacuous pass: if neither surface exists the check says so rather than reporting clean over nothing.

## The inventory, and where each entry lives today

Measured on 2026-08-30 against the tracked tree. `command` means `commands/<surface>-runtime-verify.md`, `topic` means `wos/<surface>-runtime-battery.md`. An entry in both is not duplication to clean up: the command keeps the pointer and its gate consequence, the topic keeps the procedure.

| entry | kind | lives in |
|---|---|---|
| `NATIVE_CRASH`, `NAVIGATION_TEARDOWN`, `JS_ERROR`, `MISSING_NATIVE_MODULE`, `STARTUP_CRASH`, `LAUNCH_INTENT_LOST`, `ANR`, `PERMISSION_OR_CONFIG` | app taxonomy | topic only |
| `MANAGED_EXCEPTION` | app taxonomy, Unity adapter | topic and command (Step 5a, pinned by `check_unity_adapter_surface`) |
| `PAGE_IDENTITY_MISMATCH` | web taxonomy | topic only |
| `SERVE_FAILURE`, `CONSOLE_ERROR`, `OVERFLOW`, `FOCUS_DEFECT`, `A11Y_VIOLATION`, `PERF_MEASUREMENT` | web taxonomy | topic and command (Step 7 gate decision) |
| `UNREACHABLE`, `STATUS_MISMATCH`, `CONTENT_TYPE_MISMATCH`, `SHAPE_MISMATCH`, `AUTH_BOUNDARY`, `ERROR_LEAK`, `EFFECT_NOT_OBSERVED`, `LATENCY_MEASUREMENT` | api taxonomy | topic and command (Step 7 gate decision) |
| `SCRIPT_ERROR`, `MISSING_NODE_OR_RESOURCE`, `SIGNAL_NOT_CONNECTED`, `NULL_REFERENCE`, `PHYSICS_OR_COLLISION`, `INPUT_NOT_MAPPED`, `PERFORMANCE_STALL`, `STATE_INVARIANT_VIOLATION`, `TRANSPARENCY_SORTING`, `RENDERER_TIER_MISMATCH` | godot taxonomy | topic only |
| `CLEAN` | shared by all four taxonomies | all four topics |
| `minimum frame set`, `clean persisted state` | app named rules | topic only |
| `cold-start`, `warm-only` | app named rules | topic and command |
| `G2 recovery rule`, `320, 768, 1280 and 2560`, `WEB_RUNTIME_VERIFY_SHOTS/`, `ephemeral free port` | web named rules | topic, and `ephemeral free port` also in the command's port rule |
| `n/a (tool absent)` | web named rule, reused by api | web topic plus both the web and api commands |
| `the confirming read` | api named rule | topic only |
| `blast radius`, `failure path` | api named rules | topic and command |
| `get_tree().quit()` | godot named rule | topic only |
| `probes/`, `adversarial`, `PLAYTEST_RUNBOOK.md` | godot named rules | topic and command |

## Failure modes to watch

- A legitimate rewrite renaming `failure path` to `error path` breaks the check without anything being lost. That is the cost of a literal inventory and it is paid on purpose: the table above sits beside the check, so a rename has to touch both in one commit and the reviewer sees it.
- Adding a fifth runtime surface without adding its codes here leaves that surface uninventoried. The check cannot detect its own incompleteness.
- `CLEAN` appears in all four taxonomies. Its presence anywhere satisfies all four, so it is the weakest entry in the table and proves the least.

## Notes

`check_runtime_verify_parity` accepts a `root=` argument so the negative case can run against a fixture instead of the live tree. The steps above use the live tree with a `git checkout --` restore because both battery topics are tracked and committed, which makes the restore exact.

## History

- 2026-08-30: added with ADR-0177, after the four adapter extractions took the command set from 99661 to 92757 chars.
