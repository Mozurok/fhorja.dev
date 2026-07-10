# ADR-0075: Standalone live-transcript validator

- **Status**: Accepted
- **Date**: 2026-07-02
- **Tags**: output-contract, validation, transcript, deterministic-gate, instructor

## Context

The WOS checks its output contract at two moments and misses a third. `scripts/lint-commands.sh` validates command *definitions*: it confirms `commands/<name>.md` declares the required sections (`### Standard output layout`, frontmatter, shared blocks) but never runs a command and never looks at what a command actually printed. `evals/scripts/judge.py` validates eval *outputs*, but only inside the eval harness, against scenario-specific rubrics, and only when a human runs the eval suite. Neither touches the transcript a command produces during ordinary, live use: nothing checks that a real `### Handoff` block a session just emitted has all four required fields, that the three mandated blocks appear in order, or that a `Run now: /<name>` line names a command that exists on disk. A malformed live handoff (a missing field, a swapped section, an invented command basename) currently surfaces only if a human reader happens to notice it.

External research for the task that produced this ADR (`EXTERNAL_RESEARCH.md`; `REFERENCES.md` "Instructor (567-labs/instructor)" and "Instructor: Re-asking and validation") named the transferable mechanism: instructor validates a model's structured output against a schema and, on failure, feeds the exact validation error back to the model as the next retry prompt, bounded by a caller-set `max_retries`. The WOS output contract (`WORKFLOW_OPERATING_SYSTEM.md` -> `## Global output contract`) is the same kind of schema: three ordered blocks, a closed `Work complexity` enum, and a Handoff shape with named fields. It has never had the validator half of that pattern.

## Decision

Add `scripts/validate-transcript.sh`, a standalone deterministic stdlib script (recorded as decision D-2 in the task's `DECISIONS.md`) that reads a command transcript (a markdown file passed as `$1`) and checks it against the Standard command output layout: presence and order of `### Artifact changes`, `### Command transcript`, `### Handoff`; the Handoff carries `Run now`, `Mode`, `Work complexity`, `Reason`; `Work complexity` is exactly one of `LOW`, `MEDIUM`, `HIGH`, `N/A`; and the `Run now: /<name>` basename resolves to a real `commands/<name>.md` (the commands directory resolves relative to the script's own location, overridable via a second argument or the `WOS_COMMANDS_DIR` environment variable). On failure it prints the exact missing or malformed element, one line per failure, and exits 1: the instructor pattern applied to a markdown contract instead of a JSON schema, where the error message itself is the retry payload. On success it is silent and exits 0.

- NO_OP outputs carrying `NO_OP_TRACE` and Mode B handoffs carrying a `Resume context:` block are conforming by construction, not special cases: they pass the same checks as any other transcript, with no dedicated branch in the script for either shape.
- The script ships standalone under `scripts/`, not folded into `lint-commands.sh` (definition-time scope) or `judge.py` (eval-time scope), because live-transcript checking is a third moment with its own trigger (any transcript, at any time) and deserves its own artifact rather than overloading an existing one.
- An embedded `--self-test` mode runs a fixture suite (one conforming transcript, one NO_OP, one Mode B, and four mutations: missing Handoff, swapped section order, invalid `Work complexity` value, invented command basename) and reports pass or fail per fixture, so the validator's own correctness does not depend on a human re-deriving expected outputs by hand.

## Consequences

- A live transcript can be checked in seconds, on demand, without running the eval harness or waiting for a human to notice a malformed Handoff.
- The script is advisory until something wires it into a gate. On its own it changes nothing about command behavior; a command that emits a malformed transcript today keeps doing so until an operator (or, in the future, a hook such as the pattern `scripts/typecheck-hook.sh` already establishes) runs the validator against it. Wiring it into a hook is out of scope for this decision.
- One more script to keep in sync with `## Global output contract`. If the contract's required fields or block names change, this script needs a matching edit, the same maintenance cost `lint-commands.sh` already carries for command definitions.
- Additive. No existing script, command, or ADR is modified; `scripts/validate-transcript.sh` and this ADR are both net-new files. `count:adrs` increments by one; the index row and count-marker bump are handled by the task's consolidation slice, not here.

## Alternatives considered

- Extend `lint-commands.sh` to also validate live transcripts. Rejected: lint's job is definition-time (does `commands/<name>.md` declare the right sections), not live output; folding a runtime-shape check into it would blur what a lint failure means and make one script responsible for two different moments in the command lifecycle.
- Extend `judge.py` to run this check as an extra pass. Rejected: `judge.py` is scoped to the eval harness (`evals/scenarios/`) and runs only when a human executes the eval suite; a live-transcript check needs to run against any transcript, any time, independent of the eval flow.
- Skip verbatim failure text and print only a boolean pass or fail. Rejected: a bare failure forces a human to re-diff the transcript against the contract by hand, discarding the exact lesson the instructor research names, that the validation error itself is the fastest path back to a correct output.
