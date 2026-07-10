#!/usr/bin/env bash
# build-agent-skills.sh
#
# Generates `.claude/skills/<name>/SKILL.md` from each canonical
# `commands/<name>.md`. The canonical command files already carry the
# Agent Skills frontmatter (validated by `lint-commands.sh`), so this
# adapter only has to:
#
#   1. Copy the frontmatter block verbatim.
#   2. Drop the H1 heading right after the closing `---` (Agent Skills
#      uses the `name:` field; the H1 is redundant).
#   3. Copy the rest of the body verbatim.
#
# The result is byte-stable across runs (idempotent), so the script can
# safely run in pre-commit hooks or in CI under `--check` mode.
#
# Modes:
#   build (default): writes / overwrites every `.claude/skills/<name>/SKILL.md`
#                    that has a corresponding `commands/<name>.md`. Prunes
#                    stale skill directories whose canonical command no
#                    longer exists.
#   --check:         exits 0 if every committed `.claude/skills/<name>/SKILL.md`
#                    matches what `build` would produce; exits 1 if there is
#                    drift (or stale skills); never writes.
#
# Other flags:
#   --no-prune     do not delete stale `.claude/skills/<name>/` directories
#                  whose canonical command was removed
#   --dry-run      print actions only; do not write or delete
#   --verbose|-v   print each command processed, not only failures / drift
#
# Exit codes:
#   0 = success (or no drift in --check mode)
#   1 = drift detected in --check mode, or runtime failure
#   2 = invocation error

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
COMMANDS_DIR="${REPO_ROOT}/commands"
SKILLS_DIR="${REPO_ROOT}/.claude/skills"

MODE="build"
DRY_RUN=0
VERBOSE=0
DO_PRUNE=1

usage() {
  cat <<'EOF'
Usage: scripts/build-agent-skills.sh [options]

Generate .claude/skills/<name>/SKILL.md from each commands/<name>.md.

Options:
  --check        Verify that committed skills match canonical commands.
                 Exits 1 on any drift; never writes.
  --no-prune     Keep stale skill directories whose canonical command was
                 removed (default: prune them in build mode).
  --dry-run      Print actions only; do not write or delete.
  --verbose, -v  Print every command processed, not only drift / failures.
  --help, -h     Show this message.

Exit codes:
  0 = success (or no drift in --check mode)
  1 = drift detected in --check mode, or runtime failure
  2 = invocation error
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --check) MODE="check" ;;
    --no-prune) DO_PRUNE=0 ;;
    --dry-run) DRY_RUN=1 ;;
    --verbose|-v) VERBOSE=1 ;;
    -h|--help) usage; exit 0 ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
  shift
done

if [[ ! -d "$COMMANDS_DIR" ]]; then
  echo "Error: commands directory not found: $COMMANDS_DIR" >&2
  exit 2
fi

# Render a SKILL.md body to stdout from a canonical commands/*.md file.
# Strategy: copy lines verbatim until the second `---` (closing the
# frontmatter), then on the first body line drop a `# <name>` H1 and copy
# every subsequent line verbatim.
render_skill() {
  awk '
    BEGIN { fm_count = 0; first_body = 0 }
    {
      if (fm_count < 2) {
        if ($0 == "---") { fm_count++; print; next }
        # Inside frontmatter: normalize to spec-conformant YAML so the open
        # Agent Skills validator (skills-ref) accepts it. Canonical command
        # frontmatter uses flow style and unquoted descriptions; skills-ref
        # rejects flow sequences and cannot parse a description containing a
        # colon-space. Transform on emit (canonical files stay unchanged; see
        # DECISIONS.md D-2).
        # 1. description -> literal block scalar: colons and quotes stay literal
        #    with no escaping.
        if ($0 ~ /^description: /) {
          val = substr($0, length("description: ") + 1)
          print "description: |-"
          print "  " val
          next
        }
        # 2. flow sequence  key: [a, b]  -> block sequence.
        if ($0 ~ /^[[:space:]]+[A-Za-z0-9_-]+: \[.*\]$/) {
          match($0, /^[[:space:]]+/); indent = substr($0, 1, RLENGTH)
          rest = substr($0, RLENGTH + 1)
          ci = index(rest, ":")
          key = substr(rest, 1, ci - 1)
          inner = substr(rest, ci + 1)
          sub(/^[[:space:]]*\[/, "", inner)
          sub(/\][[:space:]]*$/, "", inner)
          print indent key ":"
          if (inner ~ /[^[:space:]]/) {
            n = split(inner, arr, /,/)
            for (i = 1; i <= n; i++) {
              item = arr[i]
              gsub(/^[[:space:]]+|[[:space:]]+$/, "", item)
              print indent "  - " item
            }
          }
          next
        }
        print
        next
      }
      if (!first_body) {
        first_body = 1
        if ($0 ~ /^# /) { next }
      }
      print
    }
  ' "$1"
}

shopt -s nullglob
# K.3 (2026-06-04): dual layout. Flat commands at `commands/<name>.md` AND
# folder-shaped at `commands/<name>/SKILL.md`. Folder-shaped is reserved for
# K.8 personas; existing 57 commands stay flat (no migration). The `_shared/`
# directory holds canonical block bodies, not commands; exclude its files.
COMMAND_FILES=()
for f in "${COMMANDS_DIR}"/*.md; do
  [[ "$(dirname "$f")" == "${COMMANDS_DIR}" ]] && COMMAND_FILES+=("$f")
done
for f in "${COMMANDS_DIR}"/*/SKILL.md; do
  parent_name="$(basename "$(dirname "$f")")"
  [[ "$parent_name" == "_shared" ]] && continue
  COMMAND_FILES+=("$f")
done
shopt -u nullglob

if [[ ${#COMMAND_FILES[@]} -eq 0 ]]; then
  echo "Error: no command files found in $COMMANDS_DIR" >&2
  exit 2
fi

# Helper: derive canonical name from a command file path. Flat:
# `commands/<name>.md` -> <name>. Folder-shaped: `commands/<name>/SKILL.md`
# -> <name>.
canonical_name_from_path() {
  local f="$1"
  if [[ "$(basename "$f")" == "SKILL.md" ]]; then
    basename "$(dirname "$f")"
  else
    basename "$f" .md
  fi
}

# Collect canonical names (handles both layouts).
CANONICAL_NAMES=()
for f in "${COMMAND_FILES[@]}"; do
  CANONICAL_NAMES+=("$(canonical_name_from_path "$f")")
done

# Helper: does $1 appear in CANONICAL_NAMES?
is_canonical() {
  local needle="$1" n
  for n in "${CANONICAL_NAMES[@]}"; do
    [[ "$n" == "$needle" ]] && return 0
  done
  return 1
}

WROTE=0
SKIPPED_UPTODATE=0
DRIFTED=()
PRUNED=()
STALE=()

# 1. Build / verify each canonical skill.
for src in "${COMMAND_FILES[@]}"; do
  name="$(canonical_name_from_path "$src")"
  out_dir="${SKILLS_DIR}/${name}"
  out="${out_dir}/SKILL.md"

  rendered_tmp="$(mktemp -t "build-skills.XXXXXX")"
  trap 'rm -f "$rendered_tmp"' EXIT
  render_skill "$src" > "$rendered_tmp"

  if [[ "$MODE" == "check" ]]; then
    if [[ ! -f "$out" ]]; then
      DRIFTED+=("$name (skill missing)")
    elif ! diff -q "$rendered_tmp" "$out" >/dev/null 2>&1; then
      DRIFTED+=("$name (content drift)")
    elif [[ $VERBOSE -eq 1 ]]; then
      echo "OK: $name"
    fi
  else
    if [[ -f "$out" ]] && diff -q "$rendered_tmp" "$out" >/dev/null 2>&1; then
      SKIPPED_UPTODATE=$((SKIPPED_UPTODATE + 1))
      [[ $VERBOSE -eq 1 ]] && echo "UP-TO-DATE: $name"
    else
      if [[ $DRY_RUN -eq 1 ]]; then
        echo "WOULD WRITE: $out"
      else
        mkdir -p "$out_dir"
        cp "$rendered_tmp" "$out"
      fi
      WROTE=$((WROTE + 1))
      [[ $VERBOSE -eq 1 ]] && echo "WROTE: $name"
    fi
  fi

  rm -f "$rendered_tmp"
  trap - EXIT
done

# 2. Detect / prune stale skill directories (no matching canonical command).
if [[ -d "$SKILLS_DIR" ]]; then
  shopt -s nullglob
  for d in "$SKILLS_DIR"/*/; do
    name="$(basename "$d")"
    if ! is_canonical "$name"; then
      if [[ "$MODE" == "check" ]]; then
        STALE+=("$name")
      else
        if [[ $DO_PRUNE -eq 1 ]]; then
          if [[ $DRY_RUN -eq 1 ]]; then
            echo "WOULD PRUNE: $d"
          else
            rm -rf "$d"
          fi
          PRUNED+=("$name")
        else
          STALE+=("$name")
        fi
      fi
    fi
  done
  shopt -u nullglob
fi

# 3. Report.
echo ""
echo "================================================================================"
if [[ "$MODE" == "check" ]]; then
  echo "build-agent-skills check: ${#CANONICAL_NAMES[@]} canonical command(s)"
  echo "  drifted:           ${#DRIFTED[@]}"
  echo "  stale skill dirs:  ${#STALE[@]}"
else
  echo "build-agent-skills build: ${#CANONICAL_NAMES[@]} canonical command(s)"
  echo "  wrote:             ${WROTE}"
  echo "  up-to-date:        ${SKIPPED_UPTODATE}"
  echo "  pruned stale:      ${#PRUNED[@]}"
  echo "  kept stale:        ${#STALE[@]}"
fi
echo "================================================================================"

if [[ "$MODE" == "check" ]]; then
  if [[ ${#DRIFTED[@]} -gt 0 ]] || [[ ${#STALE[@]} -gt 0 ]]; then
    echo ""
    if [[ ${#DRIFTED[@]} -gt 0 ]]; then
      echo "Drifted skills:"
      for d in "${DRIFTED[@]}"; do
        echo "  - $d"
      done
    fi
    if [[ ${#STALE[@]} -gt 0 ]]; then
      echo "Stale skill directories (no canonical command):"
      for s in "${STALE[@]}"; do
        echo "  - $s"
      done
    fi
    echo ""
    echo "Run ./scripts/build-agent-skills.sh to regenerate from canonical commands/."
    exit 1
  fi
  exit 0
fi

# build mode: report stale-but-kept, fail soft.
if [[ ${#STALE[@]} -gt 0 ]]; then
  echo ""
  echo "Stale skill directories kept (--no-prune):"
  for s in "${STALE[@]}"; do
    echo "  - $s"
  done
fi

exit 0
