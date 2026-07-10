# ADR-0090: Phase 3 public-release transition (fresh-history release, CLAUDE.md disposition, redaction exception, flip-day governance)

- **Status**: Accepted
- **Date**: 2026-07-10
- **Tags**: release, governance, phase-3, fresh-history, claude-md-disposition, redaction-exception, branch-protection, flip-day

## Context

Phase 1 (private refinement) ends with the v1.0 public release. The 2026-07-10 readiness audit (maintainer-local task memory, five-dimension fleet sweep) found: a dirty git history (full private-client task folders reachable from the early commits, already on the private origin), private codenames in evergreen tracked docs, governance files present but with currency gaps, and no recorded plan for the transition mechanics that CLAUDE.md itself promised ("the decision will be recorded in an ADR before Phase 3"). Five task decisions (D-5 to D-9) locked the direction this ADR makes durable.

## Decision

1. **Fresh-history release.** The v1.0 public repository is a NEW repository, `github.com/Mozurok/fhorja.dev`, receiving a curated clean root (a single initial commit or a short curated series). The current private repository is archived unchanged, keeping the full development history privately. Nothing is force-pushed to the old origin. Before the clean root is cut, `refs/original/*` and the `pre-trailer-strip-backup` tag are purged from the working clone (`git update-ref -d`, `git tag -d`, `git reflog expire --expire=now --all`, `git gc --prune=now`), and a full-history re-scan must come back clean.
2. **CLAUDE.md disposition.** CLAUDE.md is not part of the public tree. The fresh root excludes it and lists it in `.gitignore`; the file remains local maintainer memory for AI sessions. Its public-facing equivalents already exist: README.md (onboarding), CONTRIBUTING.md (contribution flow), docs/FAQ.md (scope and licensing questions).
3. **Redaction exception.** Private codenames were redacted in place across ADRs 0030 (file renamed), 0035, 0036, 0038, 0041, 0051, 0056, and 0086-0088, plus their index rows, on 2026-07-10. This is a one-time pre-publication exception to the ADR immutability rule: labels were neutralized, no recorded decision changed. Future corrections return to the supersede-only rule.
4. **Governance at flip.** Branch protection is enabled on `main` at flip (PR-based contribution with the lint workflow as a required check); the Phase 1 direct-to-main pattern ends. Commits from the new root onward use the maintainer's GitHub noreply identity.
5. **Flip-day checklist** (executed by the maintainer by hand; the task only prepares): verify the new repository; push the curated root; enable branch protection; enable GitHub Discussions (governance files reference it); enable private vulnerability reporting; confirm a public contact email or put an explicit address in SECURITY.md; wire CLA Assistant (CONTRIBUTING promises it); verify the GitHub community profile checklist is fully green; push the v1.0.0 tag only after the GO verdict.

## Consequences

- The public repo starts with a zero-leak guarantee and no dangling-object exposure; the cost is giving up the public provenance of the 253 private-phase commits (they remain in the private archive).
- The maintainer's local AI workflow is unchanged: CLAUDE.md keeps working untracked.
- The one-time redaction is auditable here rather than silently embedded in ten superseded ADRs.
- Everything on the flip-day checklist is out-of-repo state; the GO_NO_GO gate cites this ADR as its checklist source.

## References

- The 2026-07-10 readiness audit and decisions D-5 to D-9 (maintainer-local task memory; the audit's punch-list drove commits a06618b and 4b94b0a).
- GitHub community profile checklist and the Open Source Guides launch and maintainer norms (captured in the maintainer's project reference log, 2026-07-10).
- CLAUDE.md `## What this file is` (the pre-Phase-3 promise this ADR fulfills).
