# Eval scenario 129: Unity ships as an adapter plus contract widenings, with no net-new command

- **Tags**: ADR-0130, unity, mobile, adapter, no-new-command, bug-classes, reference-layer, structural
- **Last reviewed**: 2026-08-07
- **Status**: active

## Goal

Validates **ADR-0130** (Unity 3D mobile ships as an `app-runtime-verify` adapter plus contract widenings, with no net-new command): no engine-named Unity command exists, the Unity adapter and its topics stay cited by both consuming commands, the store-integrity bug-class stays widened rather than forked per engine, and every `wos/unity-*.md` is reachable from the spec read map without copying prose from the Godot or React Native topics. This is a structural scenario, exercised by running the check functions directly rather than by reading a model's prose output.

This exercises:

- **The surface shape holds (D-5).** `check_unity_no_new_command()` fails when any `commands/unity-*` file or folder appears. Asserted directly rather than through `count:commands`, because a moved count marker says a command was added but not which one, and the invariant here is specifically that no command is named for the engine. Adding one reopens ADR-0069 D-4 and needs a superseding ADR, not a new file.
- **The adapter and its topics stay wired (D-4).** `check_unity_adapter_surface()` fails when `commands/app-runtime-verify.md` stops citing `wos/unity-runtime-evidence.md`, loses the `MANAGED_EXCEPTION` code (the one taxonomy addition the managed-versus-native split requires), or loses the `Step 5a` adapter block (asserted by the step marker rather than by the word `Unity`, which the frontmatter description also satisfies, so a deleted step would otherwise pass); and when `commands/test-strategy.md` stops citing `wos/unity-testing-and-ci.md` or stops naming `-testResults`, the only signal a Unity CI gate can rely on given that Unity documents no exit-code contract. A widening whose topic nothing cites is the orphan failure ADR-0127 was written about.
- **Widen-never-fork holds in both directions (D-3).** `check_store_integrity_engine_agnostic()` fails when `wos/bug-classes/godot-monetization-integrity.md` drops `csharp` from `languages`, drops `**/*.cs` from `file-patterns`, or loses the `**Scope note (ADR-0130).**` marker (without which the Godot-prefixed filename is the only signal a reader gets, and it is wrong), AND fails when a `unity-*` sibling matching the same store-integrity mechanism appears beside it. Guarding only the widening would let a fork land later and leave two files drifting on one CWE. The scope-note assertion keys on the distinctive marker rather than the phrase `engine-agnostic`, which occurs twice inside the note's own sentence and would therefore survive the note's deletion: the incidental-prose failure ADR-0119 recorded, caught here by a review pass.
- **No orphaned topic, no dangling row, no copied prose.** `check_unity_topics_indexed()` fails when a `wos/unity-*.md` is missing from the `WORKFLOW_OPERATING_SYSTEM.md` read map, when the map cites a `wos/unity-*.md` absent from disk, or when any sentence of 12 or more words is duplicated verbatim between a Unity topic and a Godot topic, an RN topic, or another Unity topic. Both directions are asserted because the sibling Godot check had to learn the dangling-row half after shipping without it.

## Setup

No live harness or model turn needed; this is a static-invariant scenario backed by four functions in `evals/scripts/structural-evals.py`, run by the `structural-evals` CI job.

- A checkout with the ADR-0130 changes applied: the two `wos/unity-*.md` topics, the widened `commands/app-runtime-verify.md` and `commands/test-strategy.md`, the widened `wos/bug-classes/godot-monetization-integrity.md`, the three new Unity bug-class templates, the read-map entry, and the regenerated `.claude/skills/*/SKILL.md`.
- A scratch copy of each file a step temporarily breaks, restored at the end of the run.

## Steps

1. Run `python3 evals/scripts/structural-evals.py` and confirm all four `scenario 129` checks report PASS.
2. **Injected breakage, D-5.** Create an empty `commands/unity-scene-plan.md` (deliberately absent from the tree; this step creates it so the check must fail on its presence). Re-run; `unity-no-new-command` MUST fail. Delete the file and confirm the check returns to PASS. <!-- lint:skip -->
3. **Injected breakage, D-4 taxonomy.** Replace every occurrence of `MANAGED_EXCEPTION` in `commands/app-runtime-verify.md` with a placeholder. Re-run; `unity-adapter-surface` MUST fail. Restore.
3a. **Injected breakage, D-4 adapter block.** Rename the `**Step 5a: Classify` heading in `commands/app-runtime-verify.md`. Re-run; `unity-adapter-surface` MUST fail. Restore.
4. **Injected breakage, D-3 widening.** Change `languages: [gdscript, csharp]` back to `languages: [gdscript]` in `wos/bug-classes/godot-monetization-integrity.md`. Re-run; `store-integrity-engine-agnostic` MUST fail. Restore.
4a. **Injected breakage, D-3 scope note.** Delete the `**Scope note (ADR-0130).**` line. Re-run; `store-integrity-engine-agnostic` MUST fail. Restore.
5. **Injected breakage, D-3 fork direction.** Create an empty `wos/bug-classes/unity-iap-client-side-entitlement-grant.md`. Re-run; `store-integrity-engine-agnostic` MUST fail on the fork predicate specifically, not only on the widening predicate. Delete and restore.
6. **Injected breakage, read map.** Delete the Unity entry from the `Minimum read map for execution:` block in `WORKFLOW_OPERATING_SYSTEM.md`. Re-run; `unity-topics-indexed` MUST fail with an orphaned-topic message. Restore.
7. Confirm the full suite exits 0 after every restore.

## Pass criteria

- All four `scenario 129` checks PASS on the unmodified tree.
- Each of the five injected breakages in steps 2 to 6 produces a FAIL on the named check, and only after restoring does the suite return to exit 0.
- `count:commands` is unchanged by this ADR, which the existing `count-markers` check already asserts.

## FAIL conditions

- Any `scenario 129` check passes while its invariant is broken, which means the check asserts nothing. This is the specific failure ADR-0119 recorded when a substring assertion was satisfied by incidental prose and two of three assertions were dead.
- **A step reports FAIL for the wrong reason.** Reading only the `[FAIL] <check-name>` header is not proof the check works: per-check exception isolation renders a crashed check as a FAIL, so a check with an undefined name reports FAIL on every injected breakage while asserting nothing. Every step above MUST be verified by reading the indented failure message under the header and confirming it names the injected breakage, not `check raised NameError`. This exact false green occurred during the ADR-0130 build and was caught by the review pass, not by the first negative test.
- `check_unity_no_new_command()` passes with a `commands/unity-*` file present.
- `check_store_integrity_engine_agnostic()` passes when a per-engine fork exists, or when the widened frontmatter has been reverted.
- `check_unity_topics_indexed()` passes with a Unity topic absent from the read map, with a read-map row citing a file that is not on disk, or with a sentence copied verbatim between topics instead of cross-referenced.
- A Unity command is added without a superseding ADR reopening ADR-0069 D-4 and ADR-0130 D-5.
