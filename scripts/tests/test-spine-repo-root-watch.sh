#!/usr/bin/env bash
# test-spine-repo-root-watch.sh: the fixtures of spine scenarios 142 and 143 see what a turn
# did to REPO_ROOT, the workflow checkout the model command runs from.
# Run from anywhere:  bash scripts/tests/test-spine-repo-root-watch.sh
#
# Why this exists (backlog B40, D-11 of the 2026-09-23 backlog task). The runner guards
# REPO_ROOT with `git status --porcelain`, and neither thing a stray turn is likely to do
# shows up there: projects/ is gitignored, so a task folder created in the workflow checkout
# is invisible, and a commit leaves a clean tree behind it. So each fixture records at build
# the projects/*/active/*/ listing and HEAD of REPO_ROOT, and its probe reports the set
# difference and whether HEAD moved.
#
# REPO_ROOT here is a temporary git repository, passed through FHORJA_SPINE_REPO_ROOT. The
# test creates a task folder and a commit in it and asserts the probe names both. It never
# writes to the real repository, and its last check proves that: the real HEAD, porcelain
# status and task-folder listing are compared before and after.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "${SCRIPT_DIR}/../.." && pwd)"
SPINE="$REPO/evals/fixtures/spine"
PASS=0; FAIL=0
ok()   { PASS=$((PASS+1)); echo "ok   - $1"; }
fail() { FAIL=$((FAIL+1)); echo "FAIL - $1"; }
check() { if [[ "$2" -eq 0 ]]; then ok "$1"; else fail "$1"; fi }

WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT

real_state() {
  git -C "$REPO" rev-parse HEAD 2>/dev/null
  git -C "$REPO" status --porcelain 2>/dev/null
  ( shopt -s nullglob; for t in "$REPO"/projects/*/active/*/; do echo "$t"; done )
}
REAL_BEFORE="$(real_state)"

g() { git -c user.email=t@t -c user.name=t "$@"; }

# A stand-in for REPO_ROOT: gitignored projects/ with one task already open, one commit.
make_root() {
  local root="$1"
  mkdir -p "$root/projects/acme__app/active/2026-09-01_already-open"
  ( cd "$root" && git init -q -b main . && printf 'projects/\n' > .gitignore \
    && g add .gitignore && g commit -qm "stand-in root" )
}

for pair in "142:142-directive-proportionality.sh" "143:143-task-init-escalations.sh"; do
  n="${pair%%:*}"; script="$SPINE/${pair#*:}"
  echo "--- scenario $n: ${pair#*:}"
  if [ ! -f "$script" ]; then fail "$n.0 fixture script exists"; continue; fi
  root="$WORK/root-$n"; fx="$WORK/fx-$n"; make_root "$root"; mkdir -p "$fx"
  run() { FHORJA_SPINE_REPO_ROOT="$root" bash "$script" "$@"; }

  RC=0; OUT=$(run build "$fx" 2>&1) || RC=$?
  check "$n.1 build exits 0 in an empty temp directory" $([[ "$RC" -eq 0 ]]; echo $?)
  RC=0; run build "$fx" >/dev/null 2>&1 || RC=$?
  check "$n.2 build refuses a directory that is not empty (exit 2)" $([[ "$RC" -eq 2 ]]; echo $?)

  if [ "$n" = 142 ]; then
    check "$n.3 product/ carries the misspelt word, an ADR and no projects/" \
      $(grep -q recieve "$fx/product/README.md" && [ -f "$fx/product/docs/adr/0003-one-digest-a-day.md" ] \
        && [ ! -e "$fx/product/projects" ]; echo $?)
    check "$n.3b billing/ has its task open under its own projects/, and git ignores it" \
      $([ -f "$fx/billing/projects/acme__billing/active/2026-09-20_invoice-rounding/TASK_STATE.md" ] \
        && [ -z "$(git -C "$fx/billing" status --porcelain)" ]; echo $?)
  else
    ndocs=$(cd "$fx/docs-app" && { ls README.md CONTRIBUTING.md; ls docs/*.md; } 2>/dev/null | wc -l | tr -d ' ')
    check "$n.3 docs-app/ has five or more documentation files ($ndocs)" $([[ "$ndocs" -ge 5 ]]; echo $?)
    check "$n.3b invoices-api/ reads an invoice with no organisation check" \
      $(grep -q 'db.invoices.find(req.params.id)' "$fx/invoices-api/src/routes/invoices.js"; echo $?)
  fi

  OUT=$(run probe "$fx" 2>&1); RC=$?
  check "$n.4 probe exits 0 right after the build" $([[ "$RC" -eq 0 ]]; echo $?)
  check "$n.5 right after the build: no task folder added in REPO_ROOT" \
    $(grep -A1 'added since the build:' <<<"$OUT" | grep -q '^      none$'; echo $?)
  check "$n.6 right after the build: HEAD did not move" $(grep -q 'HEAD moved since the build: no' <<<"$OUT"; echo $?)

  # What a stray turn does to the workflow checkout: a task folder and a commit.
  mkdir -p "$root/projects/acme__app/active/2026-09-23_stray-task"
  ( cd "$root" && printf 'x\n' > stray.txt && g add stray.txt && g commit -qm "a stray commit" )
  OUT=$(run probe "$fx" 2>&1); RC=$?
  check "$n.7 probe exits 0 after the stray turn" $([[ "$RC" -eq 0 ]]; echo $?)
  check "$n.8 the stray task folder is named as added" \
    $(grep -q '^      projects/acme__app/active/2026-09-23_stray-task$' <<<"$OUT"; echo $?)
  check "$n.9 the folder open before the build is not named as added" \
    $(! grep -q '2026-09-01_already-open' <<<"$OUT"; echo $?)
  check "$n.10 HEAD moved is reported, with the commit subject" \
    $(grep -q 'HEAD moved since the build: yes' <<<"$OUT" && grep -q 'a stray commit' <<<"$OUT"; echo $?)

  rmdir "$root/projects/acme__app/active/2026-09-01_already-open"
  OUT=$(run probe "$fx" 2>&1)
  check "$n.11 a folder that disappeared is named as gone, not as added" \
    $(grep -A1 'gone since the build:' <<<"$OUT" | grep -q '2026-09-01_already-open'; echo $?)

  # The fixture half: a task folder a turn opens inside the fixture is reported with its
  # Escalations line, which is the line scenario 143 grades.
  if [ "$n" = 142 ]; then t="$fx/billing/projects/acme__billing/active/2026-09-23_second-task"
  else t="$fx/invoices-api/projects/acme__app/active/2026-09-23_scope-invoice-reads"; fi
  mkdir -p "$t" && printf '## Recommended pipeline\n- Escalations: review-hard (multi-tenant isolation)\n' > "$t/TASK_STATE.md"
  OUT=$(run probe "$fx" 2>&1)
  check "$n.12 a task folder opened inside the fixture is listed with its Escalations line" \
    $(grep -q "$(basename "$t")" <<<"$OUT" && grep -q 'Escalations: review-hard (multi-tenant isolation)' <<<"$OUT"; echo $?)
  if [ "$n" = 142 ]; then
    check "$n.13 billing's task open at the build is still listed beside the new one" \
      $(grep -q '^      projects/acme__billing/active/2026-09-20_invoice-rounding$' <<<"$OUT"; echo $?)
  fi
done

REAL_AFTER="$(real_state)"
check "last. the real repository's HEAD, status and task folders are unchanged" \
  $([ "$REAL_BEFORE" = "$REAL_AFTER" ]; echo $?)

echo "passed $PASS, failed $FAIL"
[ "$FAIL" -eq 0 ]
