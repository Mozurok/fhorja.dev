# ADR-0177: The runtime gates share one skeleton and load their adapters from wos/

- **Status**: Accepted
- **Date**: 2026-08-30
- **Tags**: runtime-verify, shared-blocks, lazy-loading, adr-0048, adr-0084, adr-0099, adr-0107, adr-0116, adr-0130, adr-0148

## Context

Four commands verify a running artifact: `app-runtime-verify`, `web-runtime-verify`, `api-runtime-verify` and `godot-runtime-verify`. Measured on 2026-08-30 before this wave, they were 99661 chars of command text. They run the same eight steps and the same four cross-cutting rules; what differs is the battery of observations each surface admits and the taxonomy it classifies against.

That common shape was written out four times, and each adapter sat inline in its own command, paid on every invocation whether or not the target was that surface. The obvious next move was to merge the four into one command, and the obvious risk in that move is losing capability inside prose that looks like boilerplate: a taxonomy code, a named rule, a consequence sentence that only one of the four carries.

## Decision

The skeleton is shared and the adapters are lazy. `commands/_shared/runtime-verify-skeleton.md` holds the eight steps and the four cross-cutting rules, propagated by `scripts/sync-shared-blocks.sh` into all four commands. Each surface's battery and taxonomy live in a `wos/<surface>-runtime-battery.md` topic loaded when the command runs, NEVER as a paragraph inside the command. Each command keeps, outside the shared block, what is its own: its artifact name, the name of its battery topic, its per-step pointers into that topic, and the gate consequences specific to it.

No command was removed or renamed here. `check_runtime_verify_parity` inventories every taxonomy code and every named battery rule that existed before the extraction and requires each to be present on disk, in a command file or in an adapter topic. Any future merge has to prove preservation against that inventory rather than assume it.

## Consequences

### Positive

- The four commands went from 99661 to a measured smaller sum, with the adapter layers moved to four topics that are read only when the matching gate runs.
- A merge in a later wave starts from an inventory, not from a reading of prose.
- The battery is MANDATORY with a BLOCKED verdict when it resolves nowhere, so a topic that fails to load cannot degrade into a silent skip.

### Negative

- The parity check is a literal inventory, so a legitimate rewrite that renames a rule breaks it. Mitigated by keeping the inventory beside the file each rule lives in, inside the scenario, so a rename has to touch both in one commit.
- Four adapter topics is four more files to keep in the read map, and the read map is inside a section every command reads. That cost is real and is what the ADR-0012 bootstrap floor measures.

### Neutral

- Each command's numbered steps stay, because they carry the pointers into the battery topic. The shared block states the shape; it does not replace the surface-specific text.

## Alternatives considered

### Alternative 1: merge the four commands now

- One `runtime-verify` command with a surface argument.
- Rejected for this wave: the merge is the wave-8 question and it needs the parity inventory to exist first. Merging before the inventory is exactly the capability loss this ADR exists to prevent.

### Alternative 2: leave the adapters inline and share only the skeleton

- Deduplicate the prose, keep every battery in its command.
- Rejected: the adapter is the larger half and it is paid on every invocation. Sharing the skeleton alone leaves the load-stage cost untouched (ADR-0116 measures that cost per generated skill).

### Alternative 3: one combined adapter topic for all four surfaces

- A single `wos/runtime-battery.md`.
- Rejected: a Godot run and an HTTP probe share no observation mechanism, so one topic would be four topics with headers, loaded whole for whichever surface is running.

## References

- [ADR-0048](./0048-deterministic-gate-evidence.md): evidence, not trust; the rule the skeleton restates.
- [ADR-0116](./0116-single-load-stage-size-budget.md): the per-skill load ceiling this extraction serves.
- [ADR-0012](./0012-context-budget-as-explicit-contract.md): the bootstrap floor that measures what the read map costs.
- `wos/app-runtime-battery.md`, `wos/web-runtime-battery.md`, `wos/api-runtime-battery.md`, `wos/godot-runtime-battery.md`.
- `evals/scenarios/140-runtime-verify-adapter-parity.md`.
