# ADR-0060: Pre-emit secret-scan gate for code-context-map

- **Status**: Accepted
- **Date**: 2026-06-27
- **Tags**: security, secret-scanning, code-context-map, presence-gated, hard-gate, ecosystem-adoption, additive

## Context

The 2026-06-26 vibe-coding ecosystem research (round 1, rank 4; round 4 security cluster) flagged that `code-context-map` writes an AI-readable map of a target repo and has no secret scan before it emits, so a credential in source could land in the map. Repomix wires Secretlint as a hard pre-pack gate; `security-review` in the WOS only carries a manual reminder to grep or run gitleaks, not a wired gate. The gap is that the one command that reads a whole product repo and writes a derived artifact has no hard stop.

## Decision

Add a presence-gated pre-emit secret gate to `code-context-map`, implemented in `scripts/secret-scan-gate.sh` and invoked before the MAP.md (and MAP.html) write. The gate honors ADR-0027 (no install) with a three-tier order:

1. **gitleaks** if present: `gitleaks dir <path>`; a finding BLOCKS the write (exit 1).
2. else **trufflehog** `filesystem <path> --no-verification --fail` (offline, no live credential calls); a finding BLOCKS.
3. else a built-in **ripgrep** coarse pattern scan that WARNS only and never blocks, because coarse regex is too false-positive-prone to gate on.

A BLOCK stops the write and surfaces the findings; the human override is the explicit `--skip-secret-scan` input. The command never auto-skips. Scanner choice and the block-vs-warn split are the maintainer decision D-10 (locked 2026-06-27): external scanners block (calibrated rulesets and entropy), the built-in fallback only warns.

Grounded in REFERENCES.md: gitleaks, trufflehog, and Repomix/Secretlint.

## Consequences

- The only command that writes a derived artifact from a whole product repo now has a hard stop on leaked credentials when a real scanner is installed, and a best-effort warning otherwise.
- No new dependency is forced: with neither scanner installed the gate degrades to a warn-only rg scan, and the command still runs.
- `scripts/secret-scan-gate.sh` is standalone and testable (exit 0 proceed / 1 blocked / 2 usage), verified against clean, planted-secret (rg warn), skip, and usage fixtures; the gitleaks/trufflehog block paths require the tool installed to exercise live.
- trufflehog runs with `--no-verification` so the gate makes no external network calls (a verified-credential scan would; the WOS gate stays local).
- This ADR is additive and does not supersede `security-review` (which keeps its broader manual checklist); it wires the specific code-context-map case.
