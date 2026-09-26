#!/usr/bin/env bash
# test-doc-invocations.sh -- every installer invocation printed in a user-facing doc must run.
#
# Why this exists. Measured 2026-08-30: README.md:53,54,55 and docs/FAQ.md:49 all printed the
# space form (`--profile minimal`, `--project /path`), the argument parser accepted only the `=`
# form, and every one of those four lines exited 2 with `Unknown option`. That is the first
# command a new user copies, so the install failed before anything else could. Nothing measured
# it, because check-doc-sync.sh verifies cross-document REFERENCES, not that a printed command
# runs. The parser now accepts both forms; this test is what keeps the pair honest, in the
# direction that matters: a doc may print any form, and the script must accept it.
#
# It extracts, it does not hardcode. A new invocation added to a scanned doc is picked up on the
# next run without editing this file, which is the point: the previous defect was four lines
# nobody had a reason to re-read.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$REPO_ROOT" || exit 2

INSTALLER="scripts/sync-workflow-slash-commands.sh"
DOCS=(README.md docs/FAQ.md docs/MIGRATION.md)
PASS=0; FAIL=0
ok()   { PASS=$((PASS+1)); echo "ok   - $1"; }
bad()  { FAIL=$((FAIL+1)); echo "FAIL - $1"; }

# A value-taking flag needs a real target, so --project is rewritten to a scratch git dir.
# Rewriting is honest here: the test asserts the PARSER accepts the form, not that the operator's
# path exists. Any other flag is passed through untouched.
SCRATCH="$(mktemp -d)"; mkdir -p "$SCRATCH/.git"
cleanup() { rm -rf "$SCRATCH"; }
trap cleanup EXIT

found=0
for doc in "${DOCS[@]}"; do
  [[ -f "$doc" ]] || { bad "$doc: scanned doc is missing"; continue; }
  while IFS= read -r line; do
    found=$((found+1))
    # strip a trailing shell comment, then the leading ./ path
    inv="${line%%#*}"
    inv="$(printf '%s' "$inv" | sed -E 's#^.*sync-workflow-slash-commands\.sh##')"
    # shellcheck disable=SC2206
    args=( $inv )
    rewritten=()
    set +u
    for ((i=0; i<${#args[@]}; i++)); do
      a="${args[$i]}"
      case "$a" in
        --project=*) rewritten+=( "--project=$SCRATCH" ) ;;
        --project)   rewritten+=( "--project" "$SCRATCH" ); i=$((i+1)) ;;
        /path/*|~/*) rewritten+=( "$SCRATCH" ) ;;
        *)           rewritten+=( "$a" ) ;;
      esac
    done
    # The bare invocation opens an interactive wizard by design (README:43 says so). Running it
    # here would hang the suite, and it is not what this test is for, so it is skipped by name
    # rather than silently: a zero-argument invocation IS a documented form and a reader should
    # know it is not covered.
    set -u
    if [[ ${#rewritten[@]} -eq 0 ]]; then
      ok "$doc: bare invocation, skipped (opens the wizard; interactive by design)"
      continue
    fi
    if ./"$INSTALLER" "${rewritten[@]}" --dry-run --yes >/dev/null 2>&1; then
      ok "$doc: $(printf '%s ' "${rewritten[@]}" | sed "s#$SCRATCH#<dir>#g" | head -c 70)"
    else
      rc=$?
      bad "$doc: exit $rc for: $(printf '%s ' "${rewritten[@]}" | sed "s#$SCRATCH#<dir>#g" | head -c 70)"
    fi
  done < <(grep -hoE "\./scripts/sync-workflow-slash-commands\.sh[^\`]*" "$doc" 2>/dev/null || true)
done

# An empty scan is a failure, not a vacuous pass: the docs cite the installer by name today, so
# finding nothing means the extractor broke, not that the docs got clean.
if (( found == 0 )); then
  bad "no installer invocation found in any scanned doc; the extractor is broken, not the docs"
fi

# Both flag forms must stay accepted. This is the regression the defect was.
for form in "--profile=minimal" "--profile minimal"; do
  # shellcheck disable=SC2086
  if ./"$INSTALLER" $form --dry-run >/dev/null 2>&1; then
    ok "parser accepts: $form"
  else
    bad "parser rejects: $form"
  fi
done

# And a flag with no value must still be refused, so accepting the space form did not make the
# parser swallow the next flag as a value.
if ./"$INSTALLER" --profile --dry-run >/dev/null 2>&1; then
  bad "--profile with no value was accepted; it swallowed the following flag"
else
  ok "--profile with no value is refused"
fi

echo
echo "test-doc-invocations: $PASS passed, $FAIL failed ($found invocation(s) extracted)"
[[ $FAIL -eq 0 ]]
