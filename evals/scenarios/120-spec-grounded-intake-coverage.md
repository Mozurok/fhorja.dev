# Eval scenario 120: spec-grounded intake pre-fills only what the spec states and still asks for every open field

- **Tags**: ADR-0120, problem-framing, definition-completeness-reader, spec-intake, read-never-fill, socratic
- **Last reviewed**: 2026-07-27
- **Status**: active

## Goal

Validates the second consumer of the shared definition-completeness reader: when a spec file is supplied, `problem-framing` pre-fills the brief fields the spec covers, names the source beside each pre-filled value, and still asks a question for every field the spec leaves open, one question per message.

## Setup

A rough objective plus a supplied MD spec that states the problem and the success criteria but says nothing about non-goals or named deliverables. Two variations: (a) the spec is supplied; (b) no spec is supplied.

## Expected behavior

In (a) the command runs the reader first, pre-fills the problem statement and success criteria naming the spec section each came from, asks the operator to confirm those, and then asks one question at a time for non-goals and named deliverables. In (b) behavior is unchanged from the socratic intake, with no reader step and no spec references.

## Pass criteria

1. With a spec supplied, the command runs the definition-completeness reader before asking anything.
2. The problem statement and the success criteria are pre-filled, and each pre-filled value names the spec section it came from.
3. The operator is asked to confirm the pre-filled values before they are carried into `BRIEF.md`.
4. Non-goals and named deliverables, which the spec leaves open, are still asked, one question per message.
5. No brief field carries a value the spec does not state.
6. The spec is treated as a source that was read, not as a decision the human made.
7. With no spec supplied, the socratic intake is unchanged: no reader step and no spec references.

## Failure modes caught

- A brief field filled with a value the spec does not state.
- A pre-filled value carried into `BRIEF.md` without the operator confirming it.
- The spec treated as a decision the human made, rather than as a source that was read.
- Batching the remaining questions into one message, defeating the one-question-per-message mechanic.
- Running the reader when no spec was supplied, adding ceremony to the unchanged path.
