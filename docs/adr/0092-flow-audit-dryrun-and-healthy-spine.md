# ADR-0092: Dry-run command-flow audit tool, orphan-edge lint advisory, and the healthy-spine finding

- **Status**: Accepted
- **Date**: 2026-07-11
- **Tags**: flow-audit, command-graph, orphan-edges, lint-advisory, dry-run, dogfood-driven, healthy-spine, no-new-command, descriptive-first

## Context

The workflow ships 94 commands, yet real work keeps reaching for a small recurring subset. The maintainer asked whether that is a work-pattern effect or weak interconnection between commands, and whether a repeatable process could raise WOS quality by strengthening the connections.

The 2026-07-11 flow audit (task `2026-07-10_wos-flow-audit-dryrun-process`) measured it from real telemetry: 171 task audit logs, 11,167 substrate write-lines, plus the declared command graph. The premise is real but decomposes into three separable phenomena, only one of which is a defect:

1. A lean spine (healthy). Seven commands (task-init, impact-analysis, decision-interview, implementation-plan, approve-plan, implement-approved-slice, task-close) appear in 60 to 95 percent of tasks. A dominant happy path is intended design, not a bug.
2. Read-only and pre-task commands, undercounted. Commands like what-next and review-hard are used constantly but write little substrate, and problem-framing, project-bootstrap, and task-init-fleet run before or around a task folder. The write-log undercounts them; they are not unused.
3. The fixable interconnection gap. 15 commands have zero inbound references in the command graph (every fleet variant except implement-fleet, plus portfolio-review, harvest-session-learnings, backend-system-design, and others). A command with no inbound edge is reachable only if the user already knows it exists. Separately, five commands that fit the maintainer's work (contract-signoff, resolve-contract-gaps, self-critique-and-revise, team-update, task-workspace) are mentioned in prose but never offered as a positive next step where they would help.

Two properties of the measurement matter. Routing is user-driven: the `invoked_by` field is dominated by `user ->` edges, so the realized flow graph is nearly invisible to current telemetry, and the complete signal is the static reference in-degree. And the command set is 85 flat `commands/*.md` plus 9 folder-shaped `commands/*/SKILL.md` (the persona-style commands); an audit that globs only `*.md` silently misses 9 of 94. The tool build caught that blind spot in the first inline analysis and fixed it.

## Decision

**(a) A dry-run flow-audit tool.** `scripts/flow-audit.py` is a read-only auditor. It SHALL report reference in-degree per command, the orphan list (in-degree 0 or 1), realized-usage frequency across all projects, the classified never-invoked set, and the declared-versus-realized edge deltas. It SHALL enumerate both flat and folder-shaped commands. It SHALL write nothing except its report to stdout and an explicit `--out` path, and it SHALL emit command names only, never task content or project identities.

**(b) A warn-only orphan-edge lint advisory.** `scripts/lint-commands.sh` SHALL print a `Flow-orphans:` advisory line (via `flow-audit.py --orphans-brief`) reporting the count of zero-inbound commands. The advisory SHALL be informational and SHALL NOT change the lint pass or fail exit status, mirroring the natural-voice and skill-triggers advisory tier. A missing python3 SHALL degrade to a skipped advisory, never a lint failure.

**(c) The healthy-spine finding is load-bearing.** Usage concentration on the spine SHALL be treated as intended design and left as is. The fixable gap is the orphan edges plus the fits-but-cold commands. The WOS SHALL NOT add a new command to diagnose or fix command-surface concerns: a flow-audit command would itself become a new orphan and grow the surface the concern is about. The tool is a script and a lint advisory (D-1 of the task).

**(d) Used means owner or router.** A command SHALL count as used if it appears as an `owner` OR as an `invoked_by` routing parent in the telemetry, so propose-only commands (personas whose applied write is owned by approve-proposed) are not miscounted as cold.

**(e) Descriptive first.** This wave ships the tool, the advisory, and a recommendations report (`FLOW_RECOMMENDATIONS.md` in the task folder) naming the orphan-edge and fits-but-cold targets with a proposed predecessor edge for each. It edits no file under `commands/` (D-3). Applying the edges is a separate follow-up task, so the edges are driven by the tool's real output rather than by intuition.

## Consequences

- Command-flow health becomes measurable on demand and drift becomes visible every commit, without growing the command surface.
- The recommendations are grounded in a re-runnable tool, so the follow-up interconnection task starts from evidence and can re-verify after each edit.
- The classification uses two small curated sets (read-only-by-design, pre-task) that can drift as commands are added; anything never-invoked and not listed surfaces as `cold (review)`, so a genuinely new cold command is never silently bucketed. Keeping those sets in sync is a known maintenance cost, flagged in the script header.
- The realized-flow blind spot (user-driven routing, undercounted read-only commands) is accepted as a known limit for this version; closing it would need a routing-telemetry change to the substrate and handoff contract, out of scope here.
- No new command; no change to any command contract. Additive tooling plus one warn-only lint line.
