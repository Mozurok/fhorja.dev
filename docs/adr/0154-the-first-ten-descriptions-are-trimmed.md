# ADR-0154: The first ten descriptions are trimmed, and the realistic cut is a third, not a half

Date: 2026-08-17

Status: Accepted

## Context

ADR-0152 D-6 and ADR-0153 both recorded permission without action: the evidence for trimming the
Advertise stage existed across four providers, but "editing 98 descriptions is a separate change with
its own review". This is the first instalment of that change, deliberately scoped to ten so the
result could be measured before scaling.

The ten chosen are the heaviest on disk, all between 995 and 1024 chars against the 1024-char
per-description lint cap: `web-runtime-verify`, `post-deploy-verifier`, `delivery-asset`,
`autonomous-run`, `frontend-system-design`, `frontend-architecture-review`, `pr-feedback-ingest`,
`code-locate`, `implementation-plan`, `problem-framing`.

## Decision

**D-1. The trim is hand-written, not generated.** The probe's mechanical `B_trim` transform was
checked against the reference baseline first and would have dropped tracked cross-references in 6 of
the 10 (`post-deploy-verifier` losing `branch-commit` and `slice-closure`, `pr-feedback-ingest`
losing `state-reconcile` and `sync-task-state`, and one each in `delivery-asset`,
`frontend-system-design`, `implementation-plan`, `problem-framing`). ADR-0135 D-4 treats a dropped
reference as the regression the gate exists to catch, so the experiment's transform is a measurement
instrument and not a production edit. Each of the ten was rewritten by hand instead, preserving all
32 tracked references, the `Do not use` routing marker, and the 150-char capability floor.

**D-2. The realistic cut is about a third, and that revises the extrapolation.** Measured:

| | chars |
|---|---|
| the ten before | 9693 |
| the ten after | 6520 |
| cut | 32.7% |
| Advertise stage before | 81065 |
| Advertise stage after | 77482 |
| headroom against the 84000 ceiling | 2935 to 6518 |
| commands that fit at the 827-char mean | 3 to 7 |

The experiment's `B_trim` reached 47 per cent of original size, but it got there partly by discarding
references. Preserving them costs length. Anyone planning the remaining 88 should budget a one-third
cut, not the one-half the probe suggested: roughly 25000 chars recoverable corpus-wide rather than
43000, which is still room for about 30 more commands.

**D-3. Behaviour is unchanged, measured the only way that isolates it.** The probe was re-emitted
against the descriptions as they now stand, with the same 89 commands and the same committed case
set. The hash-keyed permutation is derived from command names, so the expected-answer mapping is
byte-identical to the pre-trim run and the only variable is the description text. Result: 100 per
cent across three replicates, zero misroutes, identical to the pre-trim 100 per cent, with the
shuffled control at 0 per cent. A regression would have shown as a drop against a mapping that did
not move.

**D-4. Nine of the ten are covered by the probe; the tenth is covered only by the structural gates.**
`post-deploy-verifier` is a folder-format persona command and carries no case in
`cases-89.json`, which was generated from the 89 flat `commands/*.md` files. Its trim satisfies the
reference, marker and floor checks but has no routing measurement. Stated rather than glossed,
because the same gap applies to the other 8 folder-format commands whenever this work continues.

## Consequences

- Headroom more than doubled from ten edits. The ceiling is no longer three commands away.
- The remaining 88 are now a mechanical exercise with a known method and a known gate: rewrite
  preserving references, run `build-agent-skills.sh`, run lint and structural evals, re-emit the
  probe and confirm no drop.
- The 9 folder-format persona commands need cases written before their trims can be verified rather
  than assumed.
- No ADR here claims the descriptions read better for a human. They are shorter and they still route.
  The catalog's human readability was not measured and is not asserted.
