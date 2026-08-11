# ADR-0142: Contract reconciliation from the journey validation

Date: 2026-08-11

Status: Accepted

## Context

The 2026-08-11 journey validation ran six end-to-end command chains and graded each with an
independent judge. ADR-0141 took the largest defect it found. Four more were contradictions
between commands that each read as correct alone, which is why none of them had ever failed a
lint: the repository's guards check that a clause is present in a file, never that two files
agree about the same act.

**Diff source.** `commands/branch-commit.md` accepts three diff forms including the working
tree. `commands/repo-consistency-sweep.md` and `commands/pr-package.md` accepted only
`git diff <base>...HEAD`. In the journey that made a real edit and did not commit it, the sweep
set `bug_class_run = false` and skipped its whole analysis, and `pr-package` produced a package
over an empty diff, while four real insertions sat in the working tree. Neither reported an
error. The failure mode is silent empty scope, and it reads downstream as a clean review.

**Compaction gate.** `sync-task-state`, `where-we-at` and `resume-from-state` all route to
`compact-task-memory` by comparing the `TASK_STATE.md` token count against a phase threshold.
`compact-task-memory` refused on a different metric, whether the task was one or two slices old.
A discovery-phase task over its 3,000-token threshold with no closed slices was therefore routed
to a command that refused it by definition, and no growth in the file could ever change that.

**Ownership matrix.** `state-reconcile` appeared in no row of `wos/substrate-peers.md` while
signing seven writes across six sections in one dogfooded run. `incident-triage` has a SHALL
(ADR-0088) persisting an instrument-first note under `## Open questions / blockers` or
`## Risks to watch` and was a declared co-writer of neither. `direction-adjust` declares writes
to `## Last completed step`, `## Recommended next step` and `## Risks to watch`, and was listed
on none of them.

**Undocumented prescribed path.** `commands/_shared/substrate-write-protocol.md` prescribes
`emit-substrate-write.sh apply`. The script's `--help` listed `sha`, `emit` and `batch`. Three
journeys hand-wrote the protocol fields instead, which the protocol does sanction as a fallback,
but they took it because the prescribed path looked absent rather than because it did not fit.

## Decision

1. `repo-consistency-sweep` and `pr-package` fall back to the working tree when
   `<base>...HEAD` is empty, and declare which source they used. Skipping analysis is allowed
   only when both are empty.
2. `compact-task-memory` gates on the same phase-threshold token count its callers use. Slice
   count stops being the gate.
3. The ownership matrix gains the missing co-writer entries, plus rule 2c: `state-reconcile` and
   `compact-task-memory` are whole-file operators authorized on ANY `TASK_STATE.md` section,
   bounded by their own contracts, because both operate on the file rather than on named
   sections and enumerating them per row would be wrong as well as unmaintainable.
4. `emit-substrate-write.sh --help` documents `apply`, including its two limits: the section must
   already exist, and the body may carry no H2 heading or `wos:write` line.

## Consequences

- Three commands now agree about what counts as the change under review. A task working in a
  fresh worktree, or before its first commit, gets reviewed instead of silently skipped.
- The compaction route becomes reachable for the case that motivated the context-rot warning in
  the first place, an early-phase task whose memory grew fast.
- Rule 2c is an authorization, not a widening: both commands were already writing these sections,
  and the matrix simply did not say so. It also removes the incentive to keep adding rows for
  commands whose scope is the whole file.
- **`apply` still cannot create a section, and this ADR does not change that.** The guard exists
  because header lines are excluded from the section hash and would break the self-check. The
  `task-init` case, creating twenty sections from nothing, therefore still goes through the
  sanctioned hand-written fallback. Making `apply` able to create a section is a real design
  question about how the hash is computed, and it is left open here rather than answered in
  passing.
- Nothing here is a new capability. Every item is two files being made to agree, which is why
  none of it needed a new command, a registry row, or an eval scenario. It is also why lint
  stayed green through the whole period the contradictions were live: agreement between files is
  not something the current guards can see.
