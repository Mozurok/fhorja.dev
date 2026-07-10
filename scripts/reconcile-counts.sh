#!/usr/bin/env bash
# reconcile-counts.sh -- reconcile every `<!-- count:KIND -->N<!-- /count -->`
# marker across the repo's docs to the live on-disk count for KIND (ADR-0029).
#
# This is the FIX side of the count-marker guard in `lint-commands.sh` (which is
# the CHECK side and remains the source of truth). Adding an artifact (a command,
# an ADR, a wos topic, an eval scenario, a bug-class) drifts the same count marker
# across several files; this script finds every home and sets it right in one pass,
# so you do not hunt them file-by-file. Run `lint-commands.sh` after to confirm.
#
# By default it reconciles ONLY the count markers. The command catalog and the Agent
# Skills are separate generated surfaces; pass --all to also regenerate them (or, with
# --check, drift-check them) in the same pass, so one command covers every surface a
# command-add drifts.
#
# Usage:
#   scripts/reconcile-counts.sh                # fix every drifted count marker in place
#   scripts/reconcile-counts.sh --check        # report count drift only, write nothing; exit 1 if any
#   scripts/reconcile-counts.sh --all          # fix counts AND regenerate the command catalog + Agent Skills
#   scripts/reconcile-counts.sh --check --all  # report drift across counts, catalog, and skills; write nothing
#
# The KIND -> on-disk-count formulas mirror `lint-commands.sh` disk_count(); if the
# two ever disagree, lint (the authority) will still fail after a reconcile, which
# surfaces the drift rather than hiding it.
# No `set -e`: the `ls | wc -l` disk-count pipes trip pipefail when a glob misses;
# the script uses explicit exit codes instead of relying on errexit.
set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMMANDS_DIR="${REPO_ROOT}/commands"

CHECK_ONLY=0
ALL_MODE=0
for arg in "$@"; do
  case "$arg" in
    --check) CHECK_ONLY=1 ;;
    --all)   ALL_MODE=1 ;;
    -h|--help)
      grep -E '^#( |$)' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
      exit 0 ;;
    *) echo "unknown option: ${arg}" >&2
       echo "usage: reconcile-counts.sh [--check] [--all]" >&2
       exit 2 ;;
  esac
done

# On-disk count for a KIND. Mirrors lint-commands.sh disk_count().
disk_count() {
  local n
  case "$1" in
    commands)           n=$(( $(ls "${COMMANDS_DIR}"/*.md 2>/dev/null | wc -l) + $(ls "${COMMANDS_DIR}"/*/SKILL.md 2>/dev/null | wc -l) )) ;;
    skills)             n=$(ls "${REPO_ROOT}"/.claude/skills/*/SKILL.md 2>/dev/null | wc -l) ;;
    command-categories) n=$(grep -h '^  category:' "${COMMANDS_DIR}"/*.md "${COMMANDS_DIR}"/*/SKILL.md 2>/dev/null | sed 's/.*category:[[:space:]]*//' | sort -u | wc -l) ;;
    adrs)               n=$(ls "${REPO_ROOT}"/docs/adr/[0-9]*.md 2>/dev/null | wc -l) ;;
    scenarios)          n=$(ls "${REPO_ROOT}"/evals/scenarios/[0-9]*.md 2>/dev/null | wc -l) ;;
    wos-topics)         n=$(ls "${REPO_ROOT}"/wos/*.md 2>/dev/null | wc -l) ;;
    bug-templates)      n=$(ls "${REPO_ROOT}"/wos/bug-classes/*.md 2>/dev/null | grep -vc '_index') ;;
    bug-categories)     n=$(grep -h '^category:' "${REPO_ROOT}"/wos/bug-classes/*.md 2>/dev/null | sed 's/category:[[:space:]]*//' | sort -u | wc -l) ;;
    anti-patterns)      n=$(grep -c '^- ' "${REPO_ROOT}"/wos/anti-patterns.md 2>/dev/null) ;;
    entry-points)       n=$(grep -c '^## ' "${REPO_ROOT}"/wos/entry-points.md 2>/dev/null) ;;
    fleet-commands)     n=$(ls "${COMMANDS_DIR}"/*-fleet.md 2>/dev/null | wc -l) ;;
    personas)           n=$(ls "${COMMANDS_DIR}"/*/SKILL.md 2>/dev/null | wc -l) ;;
    *)                  printf '__UNKNOWN__'; return 0 ;;
  esac
  printf '%s' "$n" | tr -d '[:space:]'
}

# The scan-set MIRRORS lint-commands.sh COUNT_SCAN_FILES exactly: the 10 root doc
# files, every wos/*.md topic, and four docs/evals files. It is deliberately NARROW
# and must NOT be a repo-wide grep: files like `_internal/audit-*/` and
# `scripts/baseline-*.md` carry count markers frozen at a past snapshot and must
# never be reconciled to the live count. Keep this list in sync with lint.
ROOT_DOC_FILES=(
  README.md WORKFLOW_OPERATING_SYSTEM.md WORKFLOW_DEMO.md CONTRIBUTING.md CLAUDE.md
  CHANGELOG.md ROADMAP.md CODE_OF_CONDUCT.md SECURITY.md COMMAND_PROMPT_STUBS.md
)
FILES=()
for rf in "${ROOT_DOC_FILES[@]}"; do FILES+=("${REPO_ROOT}/${rf}"); done
for wf in "${REPO_ROOT}"/wos/*.md; do [[ -f "$wf" ]] && FILES+=("$wf"); done
FILES+=("${REPO_ROOT}/docs/FAQ.md" "${REPO_ROOT}/docs/MIGRATION.md" \
        "${REPO_ROOT}/docs/adr/README.md" "${REPO_ROOT}/evals/README.md")

fixed=0
drift=0
unknown=0
scanned=0

for f in "${FILES[@]}"; do
  [[ -f "$f" ]] || continue
  rel="${f#${REPO_ROOT}/}"
  while IFS= read -r token; do
    [[ -z "$token" ]] && continue
    kind="$(printf '%s' "$token" | sed -E 's/<!-- count:([a-z-]+) -->[0-9]+<!-- \/count -->/\1/')"
    num="$(printf '%s' "$token" | sed -E 's/<!-- count:[a-z-]+ -->([0-9]+)<!-- \/count -->/\1/')"
    scanned=$((scanned + 1))
    expected="$(disk_count "$kind")"
    if [[ "$expected" == "__UNKNOWN__" ]]; then
      unknown=$((unknown + 1))
      echo "UNKNOWN kind '${kind}' in ${rel} (add it to disk_count in both this script and lint-commands.sh)"
      continue
    fi
    [[ "$num" == "$expected" ]] && continue
    drift=$((drift + 1))
    if [[ "$CHECK_ONLY" == "1" ]]; then
      echo "DRIFT  ${rel}: count:${kind} says ${num}, disk has ${expected}"
    else
      perl -i -pe "s/(<!-- count:${kind} -->)${num}(<!-- \\/count -->)/\${1}${expected}\${2}/g" "$f"
      echo "FIXED  ${rel}: count:${kind} ${num} -> ${expected}"
      fixed=$((fixed + 1))
    fi
  done < <(grep -oE '<!-- count:[a-z-]+ -->[0-9]+<!-- /count -->' "$f" 2>/dev/null)
done

echo "----"
echo "scanned ${scanned} marker(s) across ${#FILES[@]} file(s); ${unknown} unknown kind(s)"
rc=0
if [[ "$CHECK_ONLY" == "1" ]]; then
  echo "${drift} drifted marker(s) (check-only; nothing written)"
  [[ "$drift" -eq 0 && "$unknown" -eq 0 ]] || rc=1
else
  echo "${fixed} marker(s) reconciled"
  [[ "$unknown" -eq 0 ]] || rc=1
fi

# --all: also cover the two other surfaces a command-add drifts (the command catalog
# and the Agent Skills), each with its own tool. Counts were handled above first,
# so the catalog/skills regen never re-introduces a count drift.
if [[ "$ALL_MODE" == "1" ]]; then
  echo "----"
  CATALOG="${REPO_ROOT}/scripts/build-command-catalog.py"
  SKILLS="${REPO_ROOT}/scripts/build-agent-skills.sh"
  if [[ "$CHECK_ONLY" == "1" ]]; then
    echo "checking command catalog + Agent Skills drift (--all)"
    if python3 "$CATALOG" --check >/dev/null 2>&1; then
      echo "OK     command catalog in sync"
    else
      echo "DRIFT  command catalog out of sync (run: python3 scripts/build-command-catalog.py)"; rc=1
    fi
    if bash "$SKILLS" --check >/dev/null 2>&1; then
      echo "OK     Agent Skills in sync"
    else
      echo "DRIFT  Agent Skills out of sync (run: bash scripts/build-agent-skills.sh)"; rc=1
    fi
  else
    echo "regenerating command catalog + Agent Skills (--all)"
    if python3 "$CATALOG" >/dev/null 2>&1; then
      echo "OK     command catalog regenerated"
    else
      echo "FAIL   build-command-catalog.py errored"; rc=1
    fi
    if bash "$SKILLS" >/dev/null 2>&1; then
      echo "OK     Agent Skills regenerated"
    else
      echo "FAIL   build-agent-skills.sh errored"; rc=1
    fi
  fi
fi

exit "$rc"
