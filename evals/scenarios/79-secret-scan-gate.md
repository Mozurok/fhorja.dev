# Eval scenario 79: secret-scan gate blocks code-context-map before it leaks a credential

- **Tags**: ADR-0060, security, secret-scanning, code-context-map, presence-gated, hard-gate, regression-guard
- **Last reviewed**: 2026-06-27
- **Status**: active

## Goal

Validates **ADR-0060** (D-10): `code-context-map` runs a presence-gated pre-emit secret gate (`scripts/secret-scan-gate.sh`) before writing the map, blocking on a real scanner's finding and requiring an explicit `--skip-secret-scan` override.

This exercises:

- The tier order: gitleaks if present (block on finding), else trufflehog `--no-verification` (offline, block), else a built-in rg scan that warns only.
- The hard stop: a blocking finding prevents the MAP.md write; the command surfaces the findings and does not auto-skip.
- The human override: `--skip-secret-scan` is the only way past a block, after a confirmed false positive.
- No-install posture (ADR-0027): with neither external scanner installed the gate degrades to a warn-only rg scan and the map still generates.

## Setup

A target repo with a planted credential (for example a file containing `AKIAIOSFODNN7EXAMPLE`), and `code-context-map` invoked on it.

## Expected behavior

- WHEN gitleaks (or trufflehog) is installed and finds the planted secret, the gate exits 1, code-context-map does NOT write MAP.md, and the output names the finding and tells the user to revoke or whitelist and re-run with `--skip-secret-scan` if it is a false positive.
- WHEN neither scanner is installed, the rg fallback prints a WARN naming the file and the map still writes (warn-only, never blocks).
- WHEN `--skip-secret-scan` is passed, the gate is skipped and the map writes.
- A clean repo passes the gate silently and the map writes normally.

## Failure modes (a FAIL looks like)

- Writes MAP.md despite a gitleaks/trufflehog finding (no hard stop).
- Treats the built-in rg fallback as a blocker (coarse regex is warn-only by design) or, conversely, blocks the run when no scanner is installed.
- Auto-skips the scan without the explicit `--skip-secret-scan` input.
- Makes a network call during the scan (trufflehog must run `--no-verification`).
