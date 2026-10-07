#!/usr/bin/env bash
# Offline gate: no third-party runtime, model downloads, browser or paid calls.
set -euo pipefail
root="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$root"
python3 -m unittest discover -s evals/lab/tests -v
bash -n evals/lab/harness/quality.sh
node --check evals/lab/harness/browser-check.mjs
