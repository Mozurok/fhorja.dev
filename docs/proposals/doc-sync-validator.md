# Proposal: Doc-Sync Validator

## Problem Statement

Fhorja is a high-velocity surface. In the current cycle alone we have shipped 5+ batches touching 13+ files across the command set, ADR layer, and shared docs, with the command count crossing 68. Whenever a command is renamed, added, retired, or has its scope shifted, downstream documentation drifts silently:

- FAQ.md keeps referencing commands that no longer exist, or fails to mention new ones.
- MIGRATION.md skips entries for new commands and ADRs.
- README files keep stale counts (e.g. "27 commands") long after the registry has moved on.
- ADR-NNNN cross-references rot when ADRs are renumbered or superseded.
- `wos/<topic>.md` references break when topics are split, merged, or renamed.

Manual sync is fragile because the diff surface is wide, the human reviewer (Bruno, solo) is doing planning and implementation in the same session, and the cost of catching drift in PR review is much higher than catching it at lint time.

## Proposed Approach

Extend `scripts/lint-commands.sh` with a new `doc-sync` mode (invoked via `--mode doc-sync` or as a second pass after the existing checks). The validator runs four greps and emits warnings, never edits:

1. **Command-name references.** Grep FAQ.md, MIGRATION.md, ROADMAP.md, and every README.md under `packages/wos-engine/internal/` for slash-style command tokens (`/[a-z][a-z0-9-]+`). For each hit, verify the command exists in the registry. Unknown tokens become warnings with file:line.

2. **ADR references.** Grep the same surfaces for `ADR-[0-9]{4}` patterns. For each hit, verify a matching file exists under `internal/docs/adr/`. Missing ADRs become warnings.

3. **Topic references.** Grep for `wos/[a-z0-9-]+\.md` references. For each hit, verify the topic file exists. Broken topic links become warnings.

4. **New-command coverage.** Diff the command registry vs. the last commit (`git diff HEAD~1 -- <registry>`). For each newly-added command, check whether it is mentioned in at least one of FAQ.md, MIGRATION.md, or the relevant README. Uncovered new commands become warnings ("command X added but not referenced in any user-facing surface").

All four checks are warnings, not errors, on first rollout. They can be promoted to errors per check once the baseline is clean.

## Acceptance Criteria

- `scripts/lint-commands.sh --mode doc-sync` runs in under 5 seconds on the current repo.
- Running it against the current main produces a finite, reviewable list (not noise).
- Each warning includes file path, line number, and the offending token.
- Exit code is 0 in warn-mode, non-zero in strict-mode.
- A `--strict` flag promotes warnings to errors for CI use.
- The validator is idempotent: same input, same output, no ordering flakiness.

## Interaction With Existing Lint

The existing `lint-commands.sh` already validates:

- Registry membership (every command file is registered).
- Count markers (numeric counts in headers match reality).
- Index-row membership (every command appears in the index table).

Doc-sync is additive and runs after those checks pass. It assumes the registry is authoritative and treats every other doc as a consumer. No existing check changes behavior; the new mode is opt-in until the warning baseline is at zero, then it joins the default pass.

## Out of Scope

- **Auto-rewriting docs.** The validator never edits FAQ.md, MIGRATION.md, READMEs, or ADRs. Doc updates remain a manual, decision-bearing act (which commands to highlight, what migration narrative to tell, which ADR to cross-link). The validator only surfaces drift.
- **Semantic checks.** We do not verify that a command's described behavior matches its prompt. Only existence and reference integrity.
- **Cross-repo doc sync.** Scope is `packages/wos-engine/internal/` only for v1.
