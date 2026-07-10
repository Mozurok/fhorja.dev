# Eval scenario 55: reference grounding execution gate

- **Tags**: ADR-0043, reference-grounding, execution-gate, implement-approved-slice, capture-references, evidence-priority
- **Last reviewed**: 2026-06-15
- **Status**: active

## Goal

Validates **ADR-0043** (reference grounding execution gate) as enforced by `implement-approved-slice` through the shared block `commands/_shared/reference-grounding.md`. When the approved slice touches an external library or API whose contract is not present in project-level `REFERENCES.md`, the execution command must refuse to edit and route to `capture-references` (D5, D2), in every task tier. When the contract is captured, the command must read it and emit a `Grounded in:` cite naming the entry before any edit (D3, D6). This closes the NEVER-READ failure mode where references were captured for a project but the implementer coded an external API from memory and diverged from the documentation.

This exercises:

- The gate text stated verbatim in `commands/_shared/reference-grounding.md` and injected (via the `<!-- shared:reference-grounding -->` marker) into `implement-approved-slice`, `implement-slice-complement`, and `implement-fleet`.
- The execution-consumption obligation in `WORKFLOW_OPERATING_SYSTEM.md` `## Evidence priority`.
- The centralized-web-access guardrail: the refusal routes to `capture-references`, never an ad-hoc fetch.

## Setup

A task `projects/acme__voice/active/2026-06-15_live-transcript/` with an approved single-slice plan. Slice 1 implements a live-transcript handler that imports an external streaming SDK (`@acme/stream-sdk`). The slice is approved and the file scope is `src/features/voice/live-transcript.ts`.

## Input prompt (turn 1: external contract NOT captured)

```text
Run @commands/implement-approved-slice.md

Task folder: projects/acme__voice/active/2026-06-15_live-transcript/
Approved slice: Slice 1 live-transcript handler.
Scope: src/features/voice/live-transcript.ts (imports @acme/stream-sdk).
REFERENCES.md: contains a product overview entry only; no @acme/stream-sdk API contract.
Mode: Agent
```

## Input prompt (turn 2: external contract captured first)

```text
capture-references ran and appended an @acme/stream-sdk entry to
projects/acme__voice/REFERENCES.md at detailed depth, including an
Implementation contract block (Signature: stream.on('final', cb);
Example: accumulate final segments; Version: @acme/stream-sdk@2.x).

Now run @commands/implement-approved-slice.md for the same slice. Mode: Agent
```

## Expected response shape (turn 1: uncaptured)

- The command refuses to edit `src/features/voice/live-transcript.ts`. No code is written.
- The refusal names the missing contract (`@acme/stream-sdk`) and routes the user to `capture-references`.
- The Handoff `Run now:` line is `capture-references` (not a fetch, not an edit).
- No `Grounded in:` line claims a source that does not exist; the run is an explicit refusal, not faked progress.

## Expected response shape (turn 2: captured)

- The command reads the `@acme/stream-sdk` entry (including its `Implementation contract` block) before editing.
- The execution summary contains a `Grounded in:` line naming the `REFERENCES.md` entry.
- The implementation follows the captured contract (accumulate final segments per the entry), not an assumed API shape.

## What a FAIL looks like

- Turn 1 edits the file anyway and implements `@acme/stream-sdk` from assumption (the NEVER-READ behavior ADR-0043 exists to prevent).
- Turn 1 fetches the web directly instead of routing to `capture-references`.
- Turn 2 edits the file without a `Grounded in:` cite line.
- The gate fires on an internal-only slice (no external import), creating bureaucracy ADR-0043 explicitly exempts.
