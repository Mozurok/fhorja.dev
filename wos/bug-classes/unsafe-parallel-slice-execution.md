---
name: unsafe-parallel-slice-execution
category: agent-prompt-engineering
priority: P1
pillars: [correctness, resilience]
default-severity: P1
cwe: [CWE-754, CWE-362]
languages: [markdown, typescript, javascript]
file-patterns: ["**/IMPLEMENTATION_PLAN.md", "**/dispatch/**", "**/agents/**", "**/*.prompt.md"]
perspectives: [operator, maintainer]
reversibility-check: true
---

# unsafe-parallel-slice-execution

## What it looks like

A fleet orchestrator (`implement-fleet`, ADR-0041) runs approved implementation slices in parallel, but one of the two safety gates is bypassed. Two manifestations:

1. **Scope under-declaration.** A slice's declared `Scope` in `IMPLEMENTATION_PLAN.md` omits a file the slice actually writes. The orchestrator's pre-dispatch disjointness check compares declared scopes, sees no overlap, and dispatches the slice in parallel with a sibling. At runtime both workers write the undeclared file (or one worker's change silently depends on the other's), so the worktrees no longer merge cleanly or the merged tree is wrong. The check passed on paper while the real file sets overlapped.

   Typical shape in a plan:

   ```text
   ### Slice 3: AuthN + RBAC guards
   Scope: src/lib/auth/session.ts, src/lib/authz/guard.ts
   Depends-on: 1
   ```

   ...while the slice also edits `src/lib/actions/leads.ts` (shared with Slice 7) without listing it.

2. **Integration gate skipped.** After merging a wave's worktrees, the orchestrator proceeds to the next wave without running build, typecheck, and the affected tests on the merged tree. File-scope disjointness gave a conflict-free merge, so the merge "succeeded", but two file-disjoint slices were semantically coupled (one added a symbol or type the other imports, a shared barrel export changed) and the integrated tree does not compile or fails tests. The breakage ships because nothing ran the integrated build.

## Why it matters

Both manifestations produce a green-looking run that is actually broken, and both scale with fan-out. Scope under-declaration reintroduces the exact race ADR-0040 and ADR-0041 exist to prevent: two writers on one file, last-write-wins, silent loss. A skipped integration gate ships code that never compiled together; the failure surfaces later in CI or production, far from the slice that caused it, with no signal pointing back to the parallel wave.

Correctness pillar: the merged result violates the contract that each wave leaves the tree building and passing. Resilience pillar: the failure is silent at the point it is introduced and only detonates downstream, which is the most expensive place to find it.

## How to detect

Plan-side (catch scope under-declaration before dispatch):

```bash
# Every slice that declares a Scope should be cross-checked against the real diff
# it produces. After a slice runs, compare files touched vs declared scope:
git -C "$WORKTREE" diff --name-only "$BASE_REF" \
  | grep -vxF -f <(printf '%s\n' "${DECLARED_SCOPE[@]}") \
  && echo "SCOPE VIOLATION: slice touched files not in its declared Scope"
```

Orchestrator-side (catch a skipped gate): assert that a build + typecheck + test command ran on the merged tree between waves and recorded a pass before the next wave dispatched. A wave that closes with `build_status: not_run` or no `event=integration-gate` line in `VERIFICATION_LOG.jsonl` is the smell.

Review-side: in the fleet output, look for a wave that reports `satisfied` workers but no integration-gate result, or a `Scope` line in the plan that is narrower than the files the slice's own notes say it touched.

## How to fix

1. **Declare every file.** A slice's `Scope` must list every path it creates or modifies, including shared mutation paths and generated artifacts (migrations, schema, lockfiles, codegen output, barrel exports). When in doubt, list it: an over-broad scope only forces serialization (safe), while an under-broad scope defeats the disjointness gate (unsafe).
2. **Treat coupling artifacts as shared scope.** Even with disjoint explicit files, two slices that both touch a migration, a lockfile, a codegen output, or a barrel export are coupled and must serialize into separate waves.
3. **Never skip the integration gate.** After every wave merge, run the product repo's build, typecheck, and affected test subset on the merged tree, and record the exact commands and their result. A failing gate stops the fleet; it is not advisory. File-scope disjointness is necessary but not sufficient for semantic integration, so the gate is the backstop.
4. **Fail closed on scope violation.** A worker that needs to write outside its declared `Scope` stops and returns `scope_violation` rather than writing; the orchestrator holds that wave and routes the slice to sequential `implement-approved-slice`.

When disjointness cannot be proven, serialize. A wave of one is always safe; silently parallelizing coupled slices is the failure this class names.

## CWE / standard refs

- CWE-754: Improper Check for Unusual or Exceptional Conditions. The orchestrator treats a wave as complete without checking that the integrated tree builds and passes.
- CWE-362: Concurrent Execution using Shared Resource with Improper Synchronization (race condition). An under-declared scope lets two parallel workers write the same file.

## See also

- ADR-0041: parallel slice execution and the file-scope disjointness gate (the contract this class defends).
- ADR-0040: single-writer-per-folder (the parent doctrine generalized by ADR-0041).
- `commands/implement-fleet.md`: the orchestrator; Step 3 disjointness gate and Step 10 integration gate.
- `commands/implementation-plan.md`: emits the per-slice `Scope` and `Depends-on` that the gate depends on.
- bug-class: schema-skip-on-structured-output (sibling agent-orchestration failure where the run looks green but the payload is lost).
