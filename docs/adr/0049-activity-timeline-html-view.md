# ADR-0049: A generated HTML activity timeline over the audit log (a human-readable view, not a new log)

- **Status**: Accepted
- **Date**: 2026-06-22
- **Tags**: visibility, generated-artifact, audit-log, activity-timeline, zero-dependency, gitignored, additive, oss-onboarding

## Context

Task memory lives under `projects/<client>__<project>/active/<task>/` as a set of markdown files (`TASK_STATE.md`, `DECISIONS.md`, `IMPLEMENTATION_PLAN.md`, `SLICES/`, ...). To understand what happened across a task, or to show the process to someone (a screen-share, a demo, an OSS onboarding walk-through), a reader has to open several markdown files and reconstruct the order of events. That is workable for the author mid-task and poor for reading back or presenting.

The WOS already keeps an append-only machine-readable audit log, `.wos/VERIFICATION_LOG.jsonl` (ADR-0034, the substrate-write protocol): one JSON object per substrate section write, carrying `cmd`, `ts`, `run_id`, `writes`/`file`, `reason`, and more. It holds the raw material for a chronological view but is JSONL, built for validation and provenance, not for a human to read.

There is a generator precedent: `scripts/build-command-catalog.py` renders a single offline HTML file from a data source (the command files), stdlib-only, with no runtime dependency (ADR-0005, ADR-0029). The question this ADR answers: can the WOS give a task a readable, presentable timeline of what ran and why, without adding a new log, a new command, a hook, or a runtime dependency, and without changing the machine-readable audit contract?

## Decision

Add an optional, dependency-free generator, `scripts/build-activity-timeline.py`, that RENDERS the existing audit log as a human-readable timeline. It does not create or replace any log.

- Output: a single self-contained `ACTIVITY.html` written inside the task folder, one entry per command run, each showing the command, a capped 2-to-3-line "what it did and why", the files it touched, and a timestamp. Chronological, with a client-side text filter and a theme toggle. Zero external resource references, so it opens offline (good for a screen-share).
- Data source and grouping: it reads the task's own `.wos/VERIFICATION_LOG.jsonl` when present, else the repository-root log filtered by the `task` field. It groups lines into one entry per command run. The grouping key is `(run_id, command)`, not `run_id` alone: canonical per-section lines of one command collapse into one entry, while distinct commands that reuse a `run_id` stay separate. A `run_id` is unique per invocation by contract, so the command in the key never wrongly merges two real runs. Lines with no `run_id` (legacy free-form) each stand alone and are never dropped.
- The "why": prefer an optional, additive `summary` field on the audit line; otherwise aggregate the per-section `reason` values; otherwise fall back to other free-form descriptive keys so legacy lines still say something. The `summary` field is OPTIONAL and additive; the 14-field required set in the audit schema and `scripts/verify-log-validator.py` are unchanged.
- Scope: state-changing (audit-logged) commands only. Read-only and navigation commands do not write the log and do not appear; the page states this and labels itself an activity / change log, not "every command run".
- Liveness and invocation: on-demand regeneration (a refresh step), no hook dependency. It ships as a single stdlib script (mirroring `build-command-catalog.py`), not a new WOS command.

Load-bearing constraints:

- Renders the log, never mutates it. The machine-readable audit contract (ADR-0034) and the validator are untouched; `summary` is the only schema addition and it is optional and additive.
- Gitignored output. `ACTIVITY.html` lives under `projects/` (gitignored per ADR-0007), so it is local task memory. No `--check` drift guard applies (unlike the committed command catalog).
- Zero new dependency. Stdlib Python only, consistent with ADR-0027's stance.
- Defensive over real data. The live log is non-uniform (canonical per-section lines plus legacy free-form lines, ~50 distinct keys); the generator normalizes defensively and never crashes on a missing field, an unparseable line, or a non-dict line.

## Consequences

### Positive

- One file gives a readable, presentable account of a task: what ran, what changed, why, in order. Better for reading back, learning, and screen-sharing; serves the OSS visibility goal.
- Incremental for free: regenerating after each command picks up new entries, because the log already grows incrementally. No per-command HTML authoring.
- Zero dependency, additive, and reversible: deleting the script and the optional `summary` note removes the feature without touching the machine contract.

### Negative

- It shows state-changing commands only. Presenting it as "everything that happened" would mislead; the page states the scope to avoid that.
- A richer per-run "why" depends on commands emitting the optional `summary`; until a command opts in, the timeline uses the shorter per-section `reason`.

### Neutral

- The timeline is on-demand, not live. A refresh before showing covers the screen-share case; a hook is a documented optional add-on, not a dependency.
- The output is local task memory (gitignored). Sharing a sanitized or exemplar timeline outside the repo is a separate, later question.

## Alternatives considered

### Alternative 1: per-command HTML append (each command writes its own HTML)

- Rejected. It duplicates the existing audit-log write, touches every command, and is drift-prone. Rendering from the single existing log keeps one source of truth and stays incremental for free.

### Alternative 2: a new WOS command wrapping the generator

- Deferred. A command adds 4-registry membership, a `count:commands` bump, an eval scenario, and a skills rebuild. The stdlib script alone meets the need; a thin command wrapper (parallel to `autonomous-board`) can be added later if discoverability demands it.

### Alternative 3: make every command emit `summary`, and have read-only commands log

- Deferred. `summary` adoption is gradual and opt-in; making read-only commands write the log to widen coverage is a larger protocol change. v1 renders what the log already captures and labels its scope honestly.

## References

- `projects/<client>__<project>/active/2026-06-22_task-activity-html-timeline/` (this task: IMPACT_ANALYSIS.md, DECISIONS.md DL1/DL2/D-A..D-D, IMPLEMENTATION_PLAN.md, SLICES/01..03).
- ADR-0034 (substrate peers and the audit-log write protocol) which this view reads and does not change.
- ADR-0005 and ADR-0029 (generated artifacts and drift guards), the `build-command-catalog.py` precedent this generator mirrors.
- ADR-0007 (gitignored task memory), why the HTML is local and uncommitted.
- ADR-0027 (zero new runtime dependency), which the stdlib-only generator honors.
- `scripts/build-activity-timeline.py` (the generator), `wos/substrate-peers.md ## Audit trail` and `commands/_shared/substrate-write-protocol.md` (the optional `summary` field this ADR adds).

## Notes

Built and dogfooded in the `2026-06-22_task-activity-html-timeline` task. Dogfooding the generator on this task's own log surfaced that several commands had reused a single `run_id` (copied transaction headers), which is why the grouping key is `(run_id, command)` rather than `run_id` alone. Follow-ups, not part of this ADR: a thin discoverability command (Alternative 2), broader coverage including read-only commands (Alternative 3), and basename-shortening of long file paths in entries (cosmetic).
