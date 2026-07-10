# Eval scenario 33: substrate-write-protocol round-trip with scan-substrate-orphans.py

- **Tags**: substrate-write-protocol, K.2, parallel-dispatch, scan-substrate-orphans, ADR-0038, verification-log
- **Last reviewed**: 2026-06-05
- **Status**: active

## Goal

Validates the K.2 substrate-write-protocol round-trip. When a parallel batch dispatch produces multiple worker outputs targeting a single TASK_STATE.md substrate, the apply step MUST funnel each write through `commands/_shared/substrate-write-protocol.md` (transaction-header + JSONL audit log) so that bullets land under the correct H2 sections, `scan-substrate-orphans.py` reports 0 orphans, and `.wos/VERIFICATION_LOG.jsonl` records one row per write. The negative path validates that a malformed batch (a bullet appended between sections) is detected by the scanner with a non-zero exit, line number, nearest H2, and an ADR-0038 Rule 3 quote in the error.

## Setup

Active task at `projects/fhorja__epic-k/active/2026-06-05_k2-substrate-roundtrip/`. Five parallel workers were dispatched (per K.8 parallel-dispatch pattern); each returned a substrate patch targeting one of three H2 sections in `TASK_STATE.md`: `## Current known facts`, `## Risks to watch`, `## Active files in scope`. The apply step is about to merge worker outputs.

`TASK_STATE.md` before apply (excerpt):

```text
# TASK_STATE
## Current phase
implementation (slice 3 of 5)
## Current known facts
- baseline fact A (D-1).
## Risks to watch
- R1: existing risk (active).
## Active files in scope
- packages/wos-engine/scripts/scan-substrate-orphans.py
```

Worker outputs (5 patches): 3 facts -> `## Current known facts`; 1 risk -> `## Risks to watch`; 1 file -> `## Active files in scope`.

The user requests the apply step.

## Input prompt (happy path)

```text
Run @commands/_shared/substrate-write-protocol.md

Active task: projects/fhorja__epic-k/active/2026-06-05_k2-substrate-roundtrip/
Mode: Agent

Apply the 5 worker substrate patches from the batch dispatch into TASK_STATE.md, then run scan-substrate-orphans.py.
```

## Input prompt (negative path)

```text
Same task. A rogue apply step appended a bullet between `## Current known facts` and `## Risks to watch` without a section anchor. Run scan-substrate-orphans.py.
```

## Expected response shape (happy path)

- Each worker patch is wrapped in a transaction-header block (target H2, write-id, timestamp, worker-id) per substrate-write-protocol.
- Bullets land under the correct H2 sections; no bullet appears between H2 boundaries.
- `.wos/VERIFICATION_LOG.jsonl` gains exactly 5 new rows, one per write, each with `{write_id, target_section, worker_id, sha_before, sha_after, ts}`.
- `scan-substrate-orphans.py` exits 0 and prints `0 orphans`.

## Expected response shape (negative path)

- `scan-substrate-orphans.py` exits non-zero.
- Error names the file path, the line number of the orphan bullet, the nearest H2 above it, and a verbatim quote of ADR-0038 Rule 3.
- No silent recovery; the apply step is refused until the orphan is reconciled under a real H2.

## Pass criteria

1. **Transaction headers present**: each of the 5 writes has a transaction-header block referencing the target H2 by exact heading text; no write is anchorless.
2. **Bullets land under correct H2**: 3 facts under `## Current known facts`, 1 under `## Risks to watch`, 1 under `## Active files in scope`. No cross-section leakage.
3. **JSONL audit log complete**: `.wos/VERIFICATION_LOG.jsonl` has exactly 5 appended rows in dispatch order; each row parses as valid JSON and carries `write_id`, `target_section`, `worker_id`, `sha_before`, `sha_after`, `ts`.
4. **Scanner clean on happy path**: `scan-substrate-orphans.py` exits 0 with `0 orphans` reported; stdout names TASK_STATE.md and the 3 inspected sections.
5. **Scanner fails loud on orphan**: on the negative path, the script exits non-zero AND the error includes (a) the orphan line number, (b) the nearest H2 above, (c) a verbatim ADR-0038 Rule 3 quote.
6. **No reorder of pre-existing bullets**: baseline fact A, R1, and the pre-existing file path are untouched in position and wording.
7. **PROPOSED vs APPLIED contract honored**: Agent mode applies the writes; Plan mode would propose them. The scenario is Agent so APPLIED is expected; APPLIED rows in VERIFICATION_LOG match the in-file state.
8. **No invented sections**: the apply step does not create new H2 sections to absorb a patch; if a worker targets a missing H2, the protocol refuses the write and surfaces the gap.

## Failure modes to watch

- **Anchorless append**: a bullet appended between H2 boundaries with no transaction-header; this is the substrate-bullet-orphan bug-class.
- **Missing JSONL row**: a write that succeeded in the file but was not logged to `.wos/VERIFICATION_LOG.jsonl`; breaks the audit trail.
- **Silent scanner pass on orphan**: scanner exits 0 despite a real orphan; the bug-class detector is broken.
- **Cross-section leakage**: a risk bullet lands under `## Current known facts` because the apply step matched the wrong H2 heading.

## Notes

- Related: K.2 substrate-write-protocol, ADR-0038 Rule 3 (every substrate write MUST anchor to an exact H2 heading via transaction-header), substrate-bullet-orphan bug-class in `packages/wos-engine/internal/wos/bug-classes/`.
- Related commands: `commands/_shared/substrate-write-protocol.md`, `scripts/scan-substrate-orphans.py`, `commands/sync-task-state.md` (sibling consumer of the same protocol).

## History

- 2026-06-05: scenario authored as K.2 round-trip coverage; first eval of substrate-write-protocol + scan-substrate-orphans.py pair.
