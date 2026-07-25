# Eval scenario 115: contract-fixing examples survive an example-reduction fold

- **Tags**: ADR-0115, context-engineering, examples, contract-fixing, judgment-illustrating, substrate-write-protocol, extends-adr-0093
- **Last reviewed**: 2026-07-25
- **Status**: active

## Goal

Validates **ADR-0115** (the example classification rule in `WORKFLOW_OPERATING_SYSTEM.md`): every command-file example is classified as contract-fixing (its exact shape is parsed by a script or validator) or judgment-illustrating (everything else), and a fold that reduces examples on context-engineering grounds applies to the judgment-illustrating class only. A contract-fixing example, `commands/_shared/substrate-write-protocol.md`'s transaction-header and JSONL example being the concrete instance on file, is exempt because trimming it breaks `scripts/emit-substrate-write.sh`, not because of a blanket rule against editing examples.

This exercises:

- Correct classification: a run asked to classify a set of command-file examples sorts the substrate-write-protocol example as contract-fixing and sorts a plain narrative worked example (one with no parser reading its literal text) as judgment-illustrating.
- The exemption's scope: a context-engineering fold that proposes trimming examples across the command corpus skips the contract-fixing example and states why, rather than silently dropping it or silently keeping it with no rationale.
- The exemption is not a mandate: the same fold does not treat the ADR as license to strip every judgment-illustrating example it finds; each one is still judged on its own merit.

## Setup

No live harness needed; the scenario tests the doctrine `WORKFLOW_OPERATING_SYSTEM.md` and ADR-0115 state. Two examples are in front of the model: (1) the transaction-header and JSONL example in `commands/_shared/substrate-write-protocol.md`, parsed byte-exact by `scripts/emit-substrate-write.sh`; (2) the dated-bullet example in `commands/capture-observation.md` (line 61: "Example: `- [2026-05-10] [question] should we cache the verification result client-side or always re-fetch?`"), a tone-and-format illustration with no script or validator reading its literal text.

## Input prompt

```text
A context-engineering pass is proposing to trim worked examples across the command corpus to reduce token cost. Two candidates are in scope:

1. The transaction-header and JSONL example in commands/_shared/substrate-write-protocol.md.
2. The dated-bullet example in commands/capture-observation.md ("Example: `- [2026-05-10] [question] should we cache the verification result client-side or always re-fetch?`").

For each, classify it as contract-fixing or judgment-illustrating per the spec's example-classification rule, and say whether the fold may trim it.
```

## Expected behavior

Candidate 1 is classified contract-fixing (its exact bytes are parsed by `scripts/emit-substrate-write.sh`) and the fold does not trim it; the answer names the mechanical reason (breaking the parser), not a general "examples are protected" claim. Candidate 2, the `commands/capture-observation.md` dated-bullet example, is classified judgment-illustrating and is evaluated on its own merit for the fold, not automatically kept just because a contract-fixing exemption exists elsewhere in the same pass.

## Pass criteria

1. The response classifies the substrate-write-protocol example as contract-fixing and names `scripts/emit-substrate-write.sh` (or the parsing behavior) as the reason, not a vague "it looks important" judgment.
2. The response states the contract-fixing example is exempt from the trim, grounded in ADR-0115 or the spec's example-classification rule.
3. The response classifies the `commands/capture-observation.md` dated-bullet example as judgment-illustrating and evaluates it independently for the fold (may be kept or trimmed on its own tone-and-format merit), rather than exempting it by association with the contract-fixing example.
4. The response does not generalize the exemption into "do not trim examples" or "no example may ever be reduced"; it frames the exemption as scoped to the contract-fixing class only.
5. No response invents a script or validator dependency for the `commands/capture-observation.md` example (no script reads its literal text; `capture-observation` only appends free-form, user-supplied text to `TASK_STATE.md`) to justify keeping it.

## Failure modes to watch

- **Misclassification**: sorting the substrate-write-protocol example as judgment-illustrating, or sorting a parsed example as merely illustrative, missing the mechanical dependency.
- **Over-application**: treating ADR-0115 as blanket cover to keep every example in the corpus, defeating the context-engineering fold's purpose for the judgment-illustrating class it was never meant to protect.
- **Vague rationale**: exempting the contract-fixing example with reasoning like "it seems load-bearing" instead of naming the actual parser (`scripts/emit-substrate-write.sh`) that reads its exact bytes.
- **Silent drop**: the fold trims the contract-fixing example without ever surfacing that it was in scope, leaving no record that the exemption was considered and applied.

## Notes

- Related ADRs: [ADR-0115](../../docs/adr/0115-contract-fixing-examples-exempt.md), [ADR-0093](../../docs/adr/0093-provenance-preserving-compaction-and-four-context-operations.md).
- Related files: `WORKFLOW_OPERATING_SYSTEM.md` (`### Example classification (contract-fixing exemption)`), `commands/_shared/substrate-write-protocol.md`, `scripts/emit-substrate-write.sh`, `commands/capture-observation.md` (line 61, the judgment-illustrating candidate).
- Known issues: none yet (first run pending).

## History

- 2026-07-25: created with ADR-0115 (task `2026-07-24_context-engineering-frontier-sweep`, slice 04).
