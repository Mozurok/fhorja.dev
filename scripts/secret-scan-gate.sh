#!/usr/bin/env bash
# secret-scan-gate.sh - pre-emit secret gate for code-context-map (ADR-0060).
#
# Presence-gated, no install (ADR-0027). Scans a target path for secrets before
# an AI-readable artifact (the code-context map) is written, so credentials in
# source never leak into a map. Tool order:
#   1. gitleaks present  -> `gitleaks dir <path>`; a finding BLOCKS (exit 1).
#   2. else trufflehog   -> `trufflehog filesystem <path> --no-verification --fail`
#                           (offline, no live credential calls); a finding BLOCKS.
#   3. else built-in rg  -> coarse pattern scan that WARNS only (never blocks),
#                           because coarse regex is too false-positive-prone to gate on.
#
# The human override is `--skip`; this script never auto-bypasses. Grounded in
# REFERENCES.md (gitleaks, trufflehog, Repomix/Secretlint).
#
# Every exit 0 prints one line naming what ran, so a clean result is never silent.
#
# Usage:  secret-scan-gate.sh <path> [--skip]
# Exit:   0 = proceed (clean, skipped, or warn-only fallback)
#         1 = BLOCKED (a real scanner found secrets; findings on stdout)
#         2 = usage error (no path, or path not found)
#         3 = NOT scanned: none of gitleaks, trufflehog or rg is on PATH. This exited 0
#             with no output until 2026-09-23, which a caller could not tell from a clean
#             scan (ADR-0224). Proceeding is the caller's decision, and the map it writes
#             must say the source was not scanned.

set -uo pipefail

path="${1:-}"
flag="${2:-}"

if [[ -z "$path" ]]; then
  echo "usage: secret-scan-gate.sh <path> [--skip]" >&2
  exit 2
fi
if [[ "$flag" == "--skip" || "$path" == "--skip" ]]; then
  echo "secret-scan-gate: skipped (--skip); no scan performed."
  exit 0
fi
if [[ ! -e "$path" ]]; then
  echo "secret-scan-gate: path not found: $path" >&2
  exit 2
fi

out="$(mktemp)"
trap 'rm -f "$out"' EXIT

# Tier 1: gitleaks (blocks on finding).
if command -v gitleaks >/dev/null 2>&1; then
  if gitleaks dir "$path" --no-banner --exit-code 1 >"$out" 2>/dev/null; then
    echo "secret-scan-gate: clean (gitleaks found no secret in $path)"
    exit 0
  fi
  echo "secret-scan-gate: BLOCKED by gitleaks. Revoke or whitelist (gitleaks:allow), then re-run with --skip if confirmed false positive."
  grep -iE 'secret|rule|finding|file|line' "$out" 2>/dev/null | head -40
  exit 1
fi

# Tier 2: trufflehog, offline (blocks on finding).
if command -v trufflehog >/dev/null 2>&1; then
  if trufflehog filesystem "$path" --no-verification --fail >"$out" 2>/dev/null; then
    echo "secret-scan-gate: clean (trufflehog found no secret in $path)"
    exit 0
  fi
  echo "secret-scan-gate: BLOCKED by trufflehog. Revoke the credential, then re-run with --skip if confirmed false positive."
  head -40 "$out"
  exit 1
fi

# Tier 3: built-in rg coarse scan (WARN only, never blocks).
if command -v rg >/dev/null 2>&1; then
  hits="$(rg -l --no-heading \
    -e 'AKIA[0-9A-Z]{16}' \
    -e '-----BEGIN [A-Z ]*PRIVATE KEY-----' \
    -e 'ghp_[A-Za-z0-9]{36}' \
    -e 'xox[baprs]-[A-Za-z0-9-]{10,}' \
    "$path" 2>/dev/null || true)"
  if [[ -n "$hits" ]]; then
    echo "secret-scan-gate: WARN (built-in pattern scan; install gitleaks for a definitive blocking gate). Possible secrets in:"
    printf '%s\n' "$hits"
  else
    echo "secret-scan-gate: no match (coarse rg pattern scan of four credential shapes, not a secret scanner; install gitleaks for a definitive gate)"
  fi
  exit 0
fi

echo "secret-scan-gate: NOT scanned (no gitleaks, trufflehog or rg on PATH)"
exit 3
