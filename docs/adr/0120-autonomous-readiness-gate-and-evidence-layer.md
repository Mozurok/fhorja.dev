# ADR-0120: The overnight run is gated on readiness and evidenced by capability-routed adapters

- **Status**: Accepted
- **Date**: 2026-07-27
- **Tags**: autonomy, readiness-gate, runtime-evidence, classifier, annotation-only, shared-reader, api-runtime-verify

## Context

The autonomy cluster (ADR-0044) shipped a working controller and never got used. Three separate
findings, each verified against the repository rather than recalled:

- `autonomous-run` validated exactly two things before a run: an approved `## Approval log` entry and
  an `## Execution waves` section. It never asked whether the product context behind that plan was
  complete, so an underspecified project could reach a detached night and spend it stalling.
- Nothing routed into the cluster. A grep across `commands/` excluding its own two files returned
  zero hits, and `what-next`, `approve-plan`, and `implement-fleet` mentioned it zero times. The
  controller was reachable only by typing its name.
- The evidence a maintainer would review in the morning did not exist. `curl` appeared zero times
  across `commands/` and `wos/`; `maestro`, `simctl`, and `xcrun` returned zero hits repo-wide; the
  only screenshot line in `web-runtime-verify` was a prohibition; and `db-context-supabase` was
  MCP-only.

The maintainer's ask was to leave a defined product running overnight and review finished work in the
morning. Read literally that collides with the ADR-0044 D9 skip list, which forbids default-no-approval
auto-run and model-picked autonomy tiers. Read as a gate-placement question it does not: the human
work moves earlier rather than disappearing.

## Decision

The overnight capability is delivered inside the existing autonomy cluster as a readiness gate in
front of the controller, plus a capability-routed evidence layer, with the classifier reporting more
without deciding more. Ten decisions (D-1 to D-10 of the 2026-07-27 task) fix the shape:

- No parallel cluster (D-1). The governor, STOP sentinel, detached launcher, and runs feed already
  exist under `scripts/autonomy/`, so a second cluster would duplicate the safety layer.
- The continuation envelope, letting an agent take a recommended path on a residual gap, splits into
  a follow-up task opened after one real detached night (D-2). It is the only piece with doctrine
  surface, and the detached path has never completed end to end in this repository.
- `autonomous-readiness` is a new command and the routing target (D-3, D-8); `what-next` and
  `approve-plan` route an overnight run to it, which is the fix for the zero-inbound-route finding.
- The classifier annotates a covered boundary and never downgrades a verdict (D-4). Its default-deny
  direction and both regexes are unchanged, proven by a byte-identical fixture diff.
- One definition-completeness reader, consumed by `problem-framing` at intake and by the gate at boot
  (D-5). Two implementations of the same question drift.
- The backend HTTP gate is a sibling command, `api-runtime-verify`, not a widened web gate (D-6),
  because the web gate's battery is browser-shaped and no existing command owned runtime HTTP.
- No web closure floor in this task (D-7). Mandating a gate before the gate is proven inverts the
  order; the recorded cost is that the evidence layer ships available and never required.
- Eval scenarios 56 and 57 are amended minimally and 92 stays unedited (D-9); `api-runtime-verify`
  ships with its own scenario (D-10).

Enforcement lives in `commands/autonomous-readiness.md` (the BOOT / NOT-READY verdict and the
surface-to-adapter check), `commands/autonomous-run.md` (the readiness precondition, additive to the
approval refusal), `commands/_shared/definition-completeness-reader.md` (the shared engine), and
`scripts/autonomy/classify-slice.sh` (annotation with a path-boundary match).

## Consequences

### Positive

- The gate refuses to boot an underspecified project and names every missing item, so a night that
  would have stalled is prevented before it starts rather than diagnosed afterwards.
- A declared surface with no evidence adapter returns NOT-READY naming that adapter, so the run never
  starts work it cannot produce morning evidence for.
- The cluster is reachable: two commands now route into it, closing the finding that a working
  controller had never been reached.
- The classifier's safety property is now checkable rather than assumed: every fixture verdict and
  exit code is diffed before and after, and a mutation test proves the assertions are not vacuous.

### Negative

- The evidence layer ships available and never required (D-7). A slice can close with the gate never
  run, which is the decay mode ADR-0106 cites for `app-runtime-verify`. Accepted deliberately, with
  the enforcement question deferred to a decision after one real night.
- The readiness gate's read-never-fill rule is a model instruction, not a mechanism. One eval
  scenario checks it; nothing structurally prevents a gate run from answering a criterion.
- The surface-to-adapter map is a literal list in the command body. A gate added later does not
  appear until someone edits that list, and nothing detects the omission.
- Two new commands raise the corpus from 95 to 97, with the attendant registry, skill, and count
  surface.

### Neutral

- The maximum honest promise is unchanged by any of this: a morning of PROPOSED diffs parked at the
  merge gate with evidence attached, plus a queue of human verdicts. No opt-in makes it a merged,
  deployed feature, because the controller still may not commit, merge, or deploy.
- The detached background path remains unproven in this repository (`.wos/runs/` empty; ADR-0081
  validated against a mock CLI). Proving it once is a success criterion, not an assumption.

## Alternatives considered

### Alternative 1: a new overnight cluster on fhorja.dev

- A named cluster with its own commands, README row, and site presence, parallel to the autonomy one.
- Rejected on the ADR-0117 gap rule, refused one day before this task for a Godot 3D cluster, and on
  the CONTRIBUTING fold-first rule. The safety substrate this ask needs already exists.

### Alternative 2: widen `web-runtime-verify` to cover API routes

- One command with an API mode instead of a sibling.
- Rejected because the whole battery is browser-shaped (overflow sweep, keyboard walk, Lighthouse,
  axe) and half of it would be `n/a` by construction, while the command's stated target would stop
  being true.

### Alternative 3: let the classifier downgrade a boundary slice to auto when a decision covers it

- The version that would actually lengthen the night.
- Deferred rather than rejected. It cannot lock until three adjacent flows are answered on the record
  (a superseded decision, scope drift beyond the declared scope, and partial coverage), because the
  classifier is safe today precisely because it reads nothing and cannot be misled.

## References

- `WORKFLOW_OPERATING_SYSTEM.md` -> `## Command roles` (both new commands registered).
- `commands/autonomous-readiness.md`, `commands/api-runtime-verify.md`, `commands/autonomous-run.md`.
- `commands/_shared/definition-completeness-reader.md`, `scripts/autonomy/classify-slice.sh`.
- `docs/adr/0044-autonomous-delivery-track.md` (the D6 gates and the D9 skip list this extends).
- `docs/adr/0117-godot-3d-dimension-routed-surface.md` (the gap rule that argued against a cluster).

## Notes

The continuation envelope is deliberately absent. Deciding how much an agent may author on its own
before watching one real detached night would be deciding without the evidence that matters, which is
why D-2 split it into its own task rather than shipping it here.
