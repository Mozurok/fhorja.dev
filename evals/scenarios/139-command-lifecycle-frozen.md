# Scenario 139: a command can be frozen, and freezing is not deprecating

- Command under test: `scripts/lint-commands.sh` (frontmatter validation, `Lifecycle:` line)
- Mode: structural (the enum check is a hard lint failure)
- Related ADRs: [ADR-0176](../../docs/adr/0176-command-lifecycle-frozen.md), [ADR-0046](../../docs/adr/0046-no-auto-install-skill-trust.md) (the `metadata.provenance` enum this mirrors).

## Goal

Prove that the catalog can record "this works and we are done with it" as a state, and that recording it wrong fails the build.

Before this field, a working surface with no demand came back as an open question in every audit. Answering "leave it" cost the same as answering it the first time, because nothing recorded that the answer had been given.

## Setup

None. The field is optional and the mechanism ships with zero frozen commands.

## Steps

1. Run `./scripts/lint-commands.sh` and read the `Lifecycle:` line.
2. For the negative case, add `lifecycle: bogus` under `metadata:` in one command and run the lint again. Revert afterwards and confirm the exit code returns to 0.
3. Run `./scripts/reconcile-counts.sh --check --all` and confirm the `frozen-commands` marker resolves.

## Pass criteria

1. The lint prints a `Lifecycle:` line reporting how many commands are frozen and how many are active, with absence of the field counted as active.
2. `lifecycle: bogus` fails the lint with a message naming the enum, `metadata.lifecycle must be 'active' or 'frozen'`. It is a hard failure, not an advisory: a typo reads as a state nobody set, which is worse than no field.
3. Reverting the injected value returns the lint to exit 0.
4. The field is OPTIONAL. A command without it is valid and counts as active; requiring it would add a line to 98 commands to state the default.
5. `frozen-commands` is a count kind in BOTH `scripts/lint-commands.sh` and `scripts/reconcile-counts.sh`. The two mirror each other, and adding the kind to only one makes the reconciler fail with an unknown-kind error.
6. The count marker in `wos/maturity-ladder.md` matches disk, so the number of frozen surfaces cannot drift from what the commands declare.
7. Freezing does not authorize removal. Removing a command needs its own ADR, and the normative text says so.
8. The register of frozen surfaces that are NOT commands lives in the same section, so a reader asking what this repository stopped investing in gets one answer rather than two lists.

## Failure modes to watch

- A FAIL if the enum check is warn-only. An unvalidated lifecycle value is a state nobody set.
- A FAIL if the field is made required, which buys a line on 98 commands and no information.
- A FAIL if the kind is added to one script and not its mirror; the reconciler then reports an unknown kind.
- A FAIL if frozen is treated as permission to delete, or if the register collapses "frozen" and "never again" into one word. A frozen thing may thaw; a decision about direction is not the same claim.

## Notes

The mechanism ships empty on purpose. Which commands carry the field is a separate decision, applied by a later slice, so that installing the vocabulary and using it are not the same commit.

## History

- 2026-08-30: scenario authored with the mechanism. Zero commands frozen; four non-command surfaces registered, three frozen and one marked never again.
