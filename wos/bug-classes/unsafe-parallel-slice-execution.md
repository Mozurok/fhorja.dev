---
name: unsafe-parallel-slice-execution
category: agent-prompt-engineering
default-severity: P1
cwe: [CWE-754, CWE-362]
languages: [markdown, typescript, javascript]
file-patterns: ["**/IMPLEMENTATION_PLAN.md", "**/dispatch/**", "**/agents/**", "**/*.prompt.md"]
perspectives: [operator, maintainer]
reversibility-check: true
---

# unsafe-parallel-slice-execution

## Trigger

A fleet orchestrator runs approved implementation slices in parallel with one of its two safety gates bypassed: either a slice's declared file scope is narrower than the files it actually writes, or the integration gate on the merged tree never runs.

Both produce a green-looking run that is broken, and both get worse as fan-out grows. An under-declared scope reintroduces exactly the race that single-writer doctrine exists to prevent: two workers on one file, last write wins, the loss silent. A skipped integration gate ships code that never compiled together, and the failure surfaces later in CI or production with nothing pointing back at the parallel wave that caused it. The most expensive property of both is not that they fail but where they fail: far from the decision that made them possible.

CWE-754 (Improper Check for Unusual or Exceptional Conditions): the orchestrator treats a wave as complete without checking that the integrated tree builds and passes. CWE-362 (Concurrent Execution using Shared Resource with Improper Synchronization): an under-declared scope lets two parallel workers write one file.

## Detection

Two manifestations, and they fail differently enough to be worth separating.

1. **Scope under-declaration.** A slice's declared `Scope` omits a file the slice writes. The pre-dispatch disjointness check compares declared scopes, finds no overlap, and dispatches the slice alongside a sibling that touches the same real file. The check passed on paper while the file sets overlapped. A plan shape that carries it:

   ```text
   ### Slice 3: AuthN and RBAC guards
   Scope: src/lib/auth/session.ts, src/lib/authz/guard.ts
   Depends-on: 1
   ```

   while the slice also edits `src/lib/actions/leads.ts`, which Slice 7 declares.

2. **Integration gate skipped.** After merging a wave's worktrees, the orchestrator advances to the next wave without running build, typecheck, and the affected tests on the merged tree. File-scope disjointness gave a conflict-free merge, so the merge succeeded, and two file-disjoint slices were still semantically coupled: one added a symbol or a type the other imports, or a shared barrel export changed. The integrated tree does not compile, and nothing ran the integrated build to notice.

The review-side smell for both: a wave that reports satisfied workers with no recorded integration-gate result, or a `Scope` line narrower than the files the slice's own notes say it touched.

Plan-side check that catches manifestation 1 directly, by testing the declaration against the diff rather than against another declaration:

```bash
# Every slice that declares a Scope should be cross-checked against the real diff
# it produces. After a slice runs, compare files touched vs declared scope:
git -C "$WORKTREE" diff --name-only "$BASE_REF" \
  | grep -vxF -f <(printf '%s\n' "${DECLARED_SCOPE[@]}") \
  && echo "SCOPE VIOLATION: slice touched files not in its declared Scope"
```

## Retrieval

- Every slice's declared `Scope` and `Depends-on` in the plan, for the whole wave rather than the slice under suspicion. Disjointness is a property of the set, so a single-slice read cannot evaluate it.
- The actual diff each worker produced against its base ref, per slice. This is the only source that shows the real file set; the declaration is the claim being tested.
- The orchestrator's per-wave record, including the `VERIFICATION_LOG.jsonl` lines for the merge. The gate result is folded into the merge event's reason rather than carried as its own event, so pulling only the event names will miss it.
- The coupling artifacts the explicit scopes tend to omit: migrations, lockfiles, codegen output, barrel exports, generated schema. Retrieve them by path pattern across the wave, not per slice, because their whole risk is that two slices touch them without either declaring it.
- The build, typecheck, and test commands the product repo actually uses, so a claimed gate can be compared against a real one.

## Analysis prompt

Given the retrieved plan, the per-worker diffs, and the orchestrator's wave record:

1. For each slice in the wave, compute the set difference between the files its diff touched and the files its `Scope` declared. Report every path in the difference. Any nonempty difference is a scope violation, regardless of whether a conflict happened to occur.
2. Intersect the real file sets pairwise across the wave. Report every pair that shares a path, and say whether the declared scopes showed that overlap. A shared path the declarations hid is the finding.
3. Check the wave for coupling artifacts even where explicit files are disjoint: a migration, a lockfile, a codegen output, a barrel export, or a generated schema touched by two slices. Report each as coupled and name both slices. Two slices coupled through a barrel export are not parallelizable no matter how disjoint their explicit scopes look.
4. Determine whether an integration gate ran on the merged tree between this wave and the next. Report the exact commands and their recorded result. A wave that closes with no gate result, or with a status meaning not-run, is the finding; do not infer a pass from the absence of a failure.
5. Compare any claimed gate commands against the product repo's real build, typecheck, and test entry points. A gate that ran a command the repo does not use is a gate in name only.
6. Determine what the orchestrator does when a worker needs to write outside its declared scope. Report whether the worker fails closed and returns a scope violation, or writes anyway. Writing anyway means the declaration is documentation rather than a boundary.
7. Recommend, in order: declare every path a slice creates or modifies, including the coupling artifacts, because an over-broad scope only forces serialization while an under-broad one defeats the gate; serialize any two slices that share a coupling artifact into separate waves; run build, typecheck, and the affected tests on every merged tree and record the exact commands and their result, treating a failure as a stop rather than a note; and make a worker fail closed on a scope violation so the orchestrator can route that slice to sequential execution. When disjointness cannot be proven, serialize. A wave of one is always safe.

## Severity rubric

- **P1**: the wave dispatched in parallel and either a real file set exceeded its declaration or no integration gate ran. Justification: the tree is wrong or unverified, and the run reported success, so the next wave built on an unchecked base. It sits below P0 because the work is recoverable from the worktrees and the diffs are still on disk; the damage is wasted integration time and a delayed failure, not lost history.
- **P1 also**: a worker that writes outside its declared scope without failing closed, even when this run happened not to overlap. The boundary is absent rather than respected, so the next wave is one plan edit away from the race.
- **P2**: scopes and gate are both sound for this wave, and the orchestrator records no gate result in a form a later reader can check. The run was safe and the evidence that it was safe is not durable.

## Confidence factors

- **HIGH**: a path appears in a worker's diff and not in that slice's declared `Scope`. Two sources, one comparison, no interpretation.
- **MEDIUM**: two slices in one wave both touch a lockfile or a barrel export and the merge succeeded. Coupling is established and its effect on this particular tree is not.
- **LOW**: a wave record with no gate line where the orchestrator is known to log gates inconsistently, so absence in the record is not evidence of absence in the run.

## Examples

### Positive (declaration narrower than the diff)

```text
plan:   Slice 3 Scope: src/lib/auth/session.ts, src/lib/authz/guard.ts
diff:   src/lib/auth/session.ts
        src/lib/authz/guard.ts
        src/lib/actions/leads.ts        <- undeclared, and Slice 7 declares it
```

The disjointness check compared declarations and found no overlap, so Slices 3 and 7 ran in the same wave. Both wrote `leads.ts`. Whichever merged second won, and nothing reported a conflict because the worktrees merged cleanly on the paths the orchestrator knew about.

### Negative (declared wide, gated, serialized where coupled)

```text
plan:   Slice 3 Scope: src/lib/auth/session.ts, src/lib/authz/guard.ts,
                       src/lib/actions/leads.ts, package-lock.json
        Slice 7 Scope: src/lib/actions/leads.ts, package-lock.json
waves:  Wave 2: [3]     Wave 3: [7]
merge:  fleet-merge reason="gate pass: pnpm build, pnpm typecheck, pnpm test --filter actions"
```

The scopes are deliberately over-broad, which forced the two coupled slices into separate waves, and the merge event carries the gate commands and their result in a form a later reader can check without rerunning anything.
