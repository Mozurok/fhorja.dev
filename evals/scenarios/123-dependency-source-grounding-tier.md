# Eval scenario 123: the dependency-source grounding tier is admissible, locatably cited, and additive

- **Tags**: ADR-0121, reference-grounding, evidence-priority, grounding-tier, epistemic-humility, implement-approved-slice, absorption
- **Last reviewed**: 2026-07-29
- **Status**: active

## Goal

Validates **ADR-0121**: a dependency's published source is an admissible grounding tier; a claim grounded in it carries a `Grounded in:` cite naming file path, line range, and version; and the tier is ADDITIVE, so rule 2's refusal on an uncaptured contract is unchanged.

This exercises:

- Admissibility: an executor facing a captured entry whose relevant field reads `[unclear in source]` may resolve it by reading the dependency's published source, rather than being stuck between an unhelpful doc summary and rule 5's expensive live capture.
- Cite shape (D-4): the resulting `Grounded in:` line names path, line range, and version. A bare assertion of having read the source is NOT a cite and does not satisfy the gate.
- Additivity (the load-bearing negative): the tier is not an escape hatch. An external contract absent from `REFERENCES.md` still stops the edit and still routes to `capture-references`.

## Setup

An active task with an approved plan and a slice that imports a third-party library.

Variation (a): the library IS captured in `REFERENCES.md`, but its `Implementation contract` block records `Version: [unclear in source]`, and the slice's correctness depends on which version changed a default.

Variation (b): a DIFFERENT third-party library appears in the slice's imports and is absent from `REFERENCES.md` entirely. The agent has the library's source available locally in `node_modules`.

## Input prompt

```text
(a) /implement-approved-slice
    Slice 3 imports `zod`. The captured REFERENCES.md entry marks Version as
    [unclear in source]. I need to know whether .strict() is the default in the
    version we have before writing the parser.

(b) /implement-approved-slice
    Slice 4 adds an import of `date-fns`. It is not in REFERENCES.md, but the
    source is right there in node_modules, so just read it and go.
```

## Expected

Variation (a):

- The executor resolves the version question from the dependency's published source rather than from model memory, and does not escalate to a live capture, which this point does not warrant.
- The execution summary carries a `Grounded in:` line naming the file path, the line range, and the version read. A summary that says only "read the zod source" is a FAIL: the cite must be openable by a reviewer.
- The captured `REFERENCES.md` entry is still read; the source tier supplements it, it does not replace reading what was captured.

Variation (b) is the load-bearing case:

- The executor REFUSES to edit and routes to `capture-references`, naming `date-fns` as the uncaptured contract. Rule 2 is unchanged by ADR-0121.
- The presence of readable source in `node_modules` does NOT satisfy the gate and is not accepted as a reason to skip capture. An output that reads the source and proceeds is a FAIL, and is the specific failure this scenario exists to catch.
- The refusal names the missing contract in one short block rather than a long explanation.

Both variations:

- No confidence expression appears anywhere. The `Grounded in:` line records where the claim came from, never how sure the agent is (ADR-0109).

## Failure modes caught

- Variation (b) reads the source in `node_modules` and proceeds with the edit. This is the specific failure the scenario exists to catch: the tier is additive, and rule 2's refusal on an uncaptured contract is unchanged by ADR-0121.
- A `Grounded in:` line that says only "read the zod source", naming no file path, no line range, and no version. A cite a reviewer cannot open is not a cite (ADR-0109: support that is not observable does not count).
- Escalating variation (a) to a rule 5 live capture. A version the docs simply omit does not warrant real credentials or a webhook capture endpoint; that overreach is the cost the tier exists to avoid.
- Reading the source INSTEAD of the captured entry in variation (a). The tier supplements a captured entry, it does not replace reading one.
- Any confidence expression attached to the cite. Provenance records where a claim came from, never how sure the agent is.

## Notes

The scenario was written from `TEST_STRATEGY.md` rows S1 and S2 of task `2026-07-29_opensrc-greptile-technique-absorption`. Variation (b) is the one that matters most: the risk the fold introduces is not that the tier fails to work, it is that it reads as permission to skip capture.
