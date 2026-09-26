#!/usr/bin/env bash
# lint-commands.sh
#
# Validates that each command file under commands/*.md follows the contract
# defined in WORKFLOW_OPERATING_SYSTEM.md (Standard command output layout,
# Definition of done, etc.). Also runs two doc-drift guards (ADR-0029):
# registry membership (every command in all 3 registries, no orphan entries)
# and count markers (<!-- count:KIND -->N<!-- /count --> must equal disk).
#
# Exit codes:
#   0 = all checks pass
#   1 = a command, shared block, frontmatter, skill, registry, count, or the
#       mirror-codename leak guard failed
#   2 = invocation error

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
COMMANDS_DIR="${REPO_ROOT}/commands"
SHARED_DIR="${COMMANDS_DIR}/_shared"

# Section-end pattern per shared block name. Used to delimit the body that
# follows a `<!-- shared:<name> -->` marker inside a command file. Implemented
# as a function so the script stays portable on macOS bash 3.2 (which lacks
# associative arrays via `declare -A`).
shared_end_pattern() {
  case "$1" in
    mandatory-context-bootstrap) printf '%s' '^Required inputs:$' ;;
    *)                           printf '%s' '^### ' ;;
  esac
}

# Required sections in every command file.
# Format: "section_marker:human_readable_name"
REQUIRED_SECTIONS=(
  "^# .*$:Title heading (# command-name)"
  "^Goal:$:Goal section"
  "^Required inputs:$:Required inputs section"
  "^Operating rules:$:Operating rules section"
  "^### Standard output layout \(required\)$:Standard output layout section"
  "^### Artifact changes$:Artifact changes section"
  "^### Command transcript$:Command transcript section"
  "^### Handoff$:Handoff section"
  "^### Definition of done \(command output\)$:Definition of done section"
)

# Bytes/strings that should NOT appear (catches common mistakes).
# Format: "<literal-bytes>:<human-readable-name>".
# Patterns are matched with `grep -F` (fixed string) under `LC_ALL=C` so that
# multi-byte UTF-8 sequences such as the em-dash work portably on BSD grep
# (macOS) and GNU grep (Linux). Earlier versions used `grep -P "\xNN"` which
# was silently broken on macOS.
FORBIDDEN_PATTERNS=(
  $'\xe2\x80\x94:em-dash character (use colons, parentheses, or hyphens)'
)

# Top-level markdown files that should also be checked for forbidden bytes.
# Required-sections check still applies only to commands/*.md.
ROOT_DOC_FILES=(
  "AGENTS.md"
  "README.md"
  "WORKFLOW_OPERATING_SYSTEM.md"
  "WORKFLOW_DEMO.md"
  "CONTRIBUTING.md"
  "CLAUDE.md"
  "CHANGELOG.md"
  "ROADMAP.md"
  "CODE_OF_CONDUCT.md"
  "SECURITY.md"
  "COMMAND_PROMPT_STUBS.md"
)

usage() {
  cat <<'EOF'
Usage: scripts/lint-commands.sh [options]

Validates command files under commands/*.md against the spec contract.

Options:
  --verbose      Print pass/fail for every command, not only failures.
  --strict       Treat warnings as errors.
  --help, -h     Show this message.

Exit codes:
  0 = all pass
  1 = one or more failures
  2 = invocation error
EOF
}

VERBOSE=0
STRICT=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --verbose) VERBOSE=1 ;;
    --strict) STRICT=1 ;;
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

shopt -s nullglob
# K.3 (2026-06-04): dual layout. Flat commands at `commands/<name>.md` AND
# folder-shaped at `commands/<name>/SKILL.md`. Folder-shaped reserved for K.8
# personas; existing commands stay flat (no migration). Exclude `_shared/`.
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
# `commands/<name>.md` -> <name>. Folder-shaped: `commands/<name>/SKILL.md` -> <name>.
canonical_name_from_path() {
  local f="$1"
  if [[ "$(basename "$f")" == "SKILL.md" ]]; then
    basename "$(dirname "$f")"
  else
    basename "$f" .md
  fi
}

TOTAL=0
PASSED=0
FAILED=0
WARNED=0
FAILURES=()

for file in "${COMMAND_FILES[@]}"; do
  TOTAL=$((TOTAL + 1))
  command_name="$(canonical_name_from_path "$file")"
  file_failures=()
  file_warnings=()

  # Check required sections
  for entry in "${REQUIRED_SECTIONS[@]}"; do
    pattern="${entry%%:*}"
    name="${entry##*:}"
    if ! grep -qE "$pattern" "$file"; then
      file_failures+=("missing: $name")
    fi
  done

  # Check forbidden patterns
  for entry in "${FORBIDDEN_PATTERNS[@]}"; do
    pattern="${entry%%:*}"
    name="${entry##*:}"
    if LC_ALL=C grep -qF -- "$pattern" "$file" 2>/dev/null; then
      file_warnings+=("contains: $name")
    fi
  done

  if [[ ${#file_failures[@]} -gt 0 ]]; then
    FAILED=$((FAILED + 1))
    FAILURES+=("$command_name")
    echo "FAIL: $command_name"
    for failure in ${file_failures[@]+"${file_failures[@]}"}; do
      echo "  - $failure"
    done
    for warning in ${file_warnings[@]+"${file_warnings[@]}"}; do
      echo "  ! warning: $warning"
    done
  else
    PASSED=$((PASSED + 1))
    if [[ ${#file_warnings[@]} -gt 0 ]]; then
      WARNED=$((WARNED + 1))
      if [[ $VERBOSE -eq 1 ]] || [[ $STRICT -eq 1 ]]; then
        echo "WARN: $command_name"
        for warning in ${file_warnings[@]+"${file_warnings[@]}"}; do
          echo "  ! $warning"
        done
      fi
    elif [[ $VERBOSE -eq 1 ]]; then
      echo "PASS: $command_name"
    fi
  fi
done

# --- Frontmatter validation (P11 Phase 1.x) ---------------------------------
# Validates Agent Skills frontmatter on commands/*.md when present:
#   - first line is `---`
#   - closing `---` exists within the first 30 lines
#   - `name:` matches filename basename without `.md`
#   - `description:` is present and 1-1024 chars (single-line value)
#   - `metadata.category:` is present and in the canonical set from
#     `WORKFLOW_OPERATING_SYSTEM.md ## Command categories`
#
# Files without frontmatter are recorded as "missing" (informational, not a
# failure) until Phase 1 rollout is complete. After all commands have
# frontmatter, the missing-list is expected to be empty and any new commands
# will fail this check until they declare frontmatter.

VALID_CATEGORIES=(
  "project-initialization"
  "research-and-sourcing"
  "discovery-and-scoping"
  "design-and-ui"
  "game-and-engine"
  "database-context"
  "contracts-and-decisions"
  "planning-and-validation"
  "execution-and-closure"
  "runtime-verification"
  "audit-and-sweep"
  "autonomy"
  "delivery-and-communication"
  "state-and-navigation"
  "prompt-tooling"
)

is_valid_category() {
  local v="$1"
  local c
  for c in "${VALID_CATEGORIES[@]}"; do
    [[ "$v" == "$c" ]] && return 0
  done
  return 1
}

# Canonical 6-layer context model (ADR-0012; wos/context-budget.md).
# `consumed` lists non-baseline layers the command reads (system/tools/task
# are universal baseline and MUST NOT appear in consumed). `produced` lists
# layers the command writes via runtime artifacts; any of the six is valid.
VALID_CONSUMED_LAYERS=(memory retrieved history)
VALID_PRODUCED_LAYERS=(system memory retrieved tools history task)

is_valid_consumed_layer() {
  local v="$1"
  local c
  for c in "${VALID_CONSUMED_LAYERS[@]}"; do
    [[ "$v" == "$c" ]] && return 0
  done
  return 1
}

is_valid_produced_layer() {
  local v="$1"
  local c
  for c in "${VALID_PRODUCED_LAYERS[@]}"; do
    [[ "$v" == "$c" ]] && return 0
  done
  return 1
}

# metadata.tools (ADR-0059): canonical Claude Code tool vocabulary a command may
# declare. The read-only guard (a command with context-layers-produced: [] must
# not declare Write or Edit; Bash exempt) is enforced in the frontmatter loop.
#
# `Task` is deliberately NOT in this set. Claude Code renamed that tool to
# `Agent` in v2.1.63 and the old name still resolves as an alias, so declaring
# `Task` breaks nothing at runtime. It is refused here because `Task` now names
# a DIFFERENT family (TaskCreate, TaskGet, TaskList, TaskUpdate, TaskStop,
# TaskOutput), which makes the bare string ambiguous to every later reader.
# Omitting it from the vocabulary is what makes the rename stay done: this list
# is already a FAIL-tier check, so no second scan is needed.
VALID_TOOLS=(Read Write Edit Bash Glob Grep WebFetch WebSearch Agent)
is_valid_tool() {
  local v="$1" c
  for c in "${VALID_TOOLS[@]}"; do [[ "$v" == "$c" ]] && return 0; done
  return 1
}

# metadata.x-wos-profiles (ADR-0059): tiered-install membership. A command lists
# every tier that ships it (minimal commands also ship in core and full).
VALID_PROFILES=(minimal core full)
is_valid_profile() {
  local v="$1" c
  for c in "${VALID_PROFILES[@]}"; do [[ "$v" == "$c" ]] && return 0; done
  return 1
}

# metadata.provenance (ADR-0046 DEF-09 / ADR-0059): trust origin. Every Fhorja
# command is first-party; vetted-third-party / sandbox are reserved for adopted
# external skills a human approved via skill-vet.
VALID_PROVENANCE=(first-party vetted-third-party sandbox)
is_valid_provenance() {
  local v="$1" c
  for c in "${VALID_PROVENANCE[@]}"; do [[ "$v" == "$c" ]] && return 0; done
  return 1
}

# metadata.lifecycle (ADR-0176): OPTIONAL. Absence means active, so 98 commands do
# not gain a line to state the default. A typo here is worse than no field at all,
# because it reads as a state nobody set, so the enum is a hard failure and not an
# advisory.
VALID_LIFECYCLE=(active frozen)
is_valid_lifecycle() {
  local v="$1" c
  for c in "${VALID_LIFECYCLE[@]}"; do [[ "$v" == "$c" ]] && return 0; done
  return 1
}

# Parse a YAML inline list like `[memory, retrieved]` or `[]` and echo
# space-separated values (empty for `[]`). Strips brackets and whitespace.
# Echoes the sentinel `__INVALID__` when the input is not in bracket form.
parse_yaml_inline_list() {
  local raw="$1"
  # Strip leading/trailing whitespace
  raw="${raw#"${raw%%[![:space:]]*}"}"
  raw="${raw%"${raw##*[![:space:]]}"}"
  # Require bracket form
  if [[ "$raw" != \[*\] ]]; then
    echo "__INVALID__"
    return
  fi
  # Strip the brackets
  raw="${raw#[}"
  raw="${raw%]}"
  # Empty list short-circuit (avoids `set -u` array-unbound issues).
  if [[ -z "${raw// }" ]]; then
    return
  fi
  # Replace commas with newlines; trim each line; strip surrounding single or
  # double quotes; drop empties; replace internal whitespace with US (\x1f) so
  # the caller's IFS-whitespace `for` loop treats multi-word entries
  # (e.g. owned_sections like 'TASK_STATE.md ## Risks to watch') as one token.
  printf '%s' "$raw" | tr ',' '\n' | awk '{
    sub(/^[[:space:]]+/, "");
    sub(/[[:space:]]+$/, "");
    # Strip outer double quotes
    if (substr($0,1,1) == "\"" && substr($0,length($0),1) == "\"") {
      $0 = substr($0, 2, length($0) - 2)
    } else if (substr($0,1,1) == "'\''" && substr($0,length($0),1) == "'\''") {
      $0 = substr($0, 2, length($0) - 2)
    }
    if (length($0) > 0) {
      gsub(/[[:space:]]/, "\037")
      print
    }
  }' | tr '\n' ' '
}

extract_frontmatter_block() {
  awk 'NR == 1 && $0 != "---" { exit } /^---$/ { count++; if (count == 2) exit; if (count == 1) next } { print }' "$1"
}

FM_TOTAL=0
FM_PRESENT=0
FM_PASSED=0
FM_FAILED=0
FM_MISSING=0
FM_FAILURES=()
FM_MISSING_CMDS=()

for file in "${COMMAND_FILES[@]}"; do
  FM_TOTAL=$((FM_TOTAL + 1))
  command_name="$(canonical_name_from_path "$file")"

  first_line="$(head -n1 "$file")"
  if [[ "$first_line" != "---" ]]; then
    FM_MISSING=$((FM_MISSING + 1))
    FM_MISSING_CMDS+=("$command_name")
    continue
  fi

  FM_PRESENT=$((FM_PRESENT + 1))
  fm_failures=()
  fm_block="$(extract_frontmatter_block "$file")"

  if [[ -z "$fm_block" ]]; then
    fm_failures+=("frontmatter: empty block or missing closing ---")
  fi

  fm_name="$(printf '%s\n' "$fm_block" | awk -F': ' '/^name: / { sub(/^name: /, ""); print; exit }' | head -n1)"
  if [[ -z "$fm_name" ]]; then
    fm_failures+=("frontmatter: missing required field 'name'")
  elif [[ "$fm_name" != "$command_name" ]]; then
    fm_failures+=("frontmatter: name '$fm_name' must equal canonical command name '$command_name' (basename for flat layout, parent dir for folder-shaped layout)")
  fi

  fm_desc="$(printf '%s\n' "$fm_block" | awk '/^description: / { sub(/^description: /, ""); print; exit }')"
  if [[ -z "$fm_desc" ]]; then
    fm_failures+=("frontmatter: missing required field 'description' (single-line value)")
  else
    desc_len=${#fm_desc}
    if (( desc_len > 1024 )); then
      fm_failures+=("frontmatter: description length ${desc_len} exceeds 1024 char limit (Agent Skills spec)")
    fi
    if (( desc_len < 1 )); then
      fm_failures+=("frontmatter: description must be non-empty")
    fi
  fi

  fm_category="$(printf '%s\n' "$fm_block" | awk '/^  category: / { sub(/^  category: /, ""); print; exit }')"
  if [[ -z "$fm_category" ]]; then
    fm_failures+=("frontmatter: missing required field 'metadata.category'")
  elif ! is_valid_category "$fm_category"; then
    fm_failures+=("frontmatter: metadata.category '$fm_category' not in canonical set (see the spec '## Command categories')")
  fi

  # Context budget fields (ADR-0012). Both fields are required on every command.
  # consumed: must be a YAML inline list of non-baseline layers (memory/retrieved/history);
  # produced: must be a YAML inline list of any canonical layer (or empty).
  fm_consumed_raw="$(printf '%s\n' "$fm_block" | awk '/^  context-layers-consumed: / { sub(/^  context-layers-consumed: /, ""); print; exit }')"
  fm_produced_raw="$(printf '%s\n' "$fm_block" | awk '/^  context-layers-produced: / { sub(/^  context-layers-produced: /, ""); print; exit }')"

  if [[ -z "$fm_consumed_raw" ]]; then
    fm_failures+=("frontmatter: missing required field 'metadata.context-layers-consumed' (ADR-0012)")
  else
    parsed_consumed="$(parse_yaml_inline_list "$fm_consumed_raw")"
    if [[ "$parsed_consumed" == "__INVALID__" ]]; then
      fm_failures+=("frontmatter: context-layers-consumed '$fm_consumed_raw' is not a valid YAML inline list (expected '[]' or '[layer, layer, ...]')")
    else
      for layer in $parsed_consumed; do
        if ! is_valid_consumed_layer "$layer"; then
          if [[ "$layer" == "system" || "$layer" == "tools" || "$layer" == "task" ]]; then
            fm_failures+=("frontmatter: context-layers-consumed contains baseline layer '$layer' (system/tools/task are universal baseline; do not list per ADR-0012)")
          else
            fm_failures+=("frontmatter: context-layers-consumed contains invalid layer '$layer' (valid: memory, retrieved, history)")
          fi
        fi
      done
    fi
  fi

  if [[ -z "$fm_produced_raw" ]]; then
    fm_failures+=("frontmatter: missing required field 'metadata.context-layers-produced' (ADR-0012)")
  else
    parsed_produced="$(parse_yaml_inline_list "$fm_produced_raw")"
    if [[ "$parsed_produced" == "__INVALID__" ]]; then
      fm_failures+=("frontmatter: context-layers-produced '$fm_produced_raw' is not a valid YAML inline list (expected '[]' or '[layer, layer, ...]')")
    else
      for layer in $parsed_produced; do
        if ! is_valid_produced_layer "$layer"; then
          fm_failures+=("frontmatter: context-layers-produced contains invalid layer '$layer' (valid: system, memory, retrieved, tools, history, task)")
        fi
      done
    fi
  fi

  # metadata.tools (ADR-0059). Required YAML inline list from the canonical
  # vocabulary; a read-only command (context-layers-produced: []) MUST NOT
  # declare Write or Edit (Bash is exempt: read-only commands run git/grep/lint).
  fm_tools_raw="$(printf '%s\n' "$fm_block" | awk '/^  tools: / { sub(/^  tools: /, ""); print; exit }')"
  if [[ -z "$fm_tools_raw" ]]; then
    fm_failures+=("frontmatter: missing required field 'metadata.tools' (ADR-0059)")
  else
    parsed_tools="$(parse_yaml_inline_list "$fm_tools_raw")"
    if [[ "$parsed_tools" == "__INVALID__" ]]; then
      fm_failures+=("frontmatter: tools '$fm_tools_raw' is not a valid YAML inline list (expected '[Read, Grep, ...]')")
    else
      tools_has_write=0
      for t in $parsed_tools; do
        if ! is_valid_tool "$t"; then
          fm_failures+=("frontmatter: tools contains invalid tool '$t' (valid: ${VALID_TOOLS[*]})")
        fi
        [[ "$t" == "Write" || "$t" == "Edit" ]] && tools_has_write=1
      done
      prod_trim="$(printf '%s' "$fm_produced_raw" | tr -d '[:space:]')"
      if [[ "$prod_trim" == "[]" && "$tools_has_write" == "1" ]]; then
        fm_failures+=("frontmatter: read-only command (context-layers-produced: []) must not declare Write or Edit in tools (ADR-0059 read-only guard; Bash exempt)")
      fi
    fi
  fi

  # metadata.x-wos-profiles (ADR-0059). Required YAML inline list of install tiers.
  fm_profiles_raw="$(printf '%s\n' "$fm_block" | awk '/^  x-wos-profiles: / { sub(/^  x-wos-profiles: /, ""); print; exit }')"
  if [[ -z "$fm_profiles_raw" ]]; then
    fm_failures+=("frontmatter: missing required field 'metadata.x-wos-profiles' (ADR-0059)")
  else
    parsed_profiles="$(parse_yaml_inline_list "$fm_profiles_raw")"
    if [[ "$parsed_profiles" == "__INVALID__" ]]; then
      fm_failures+=("frontmatter: x-wos-profiles '$fm_profiles_raw' is not a valid YAML inline list (expected a subset of [minimal, core, full])")
    else
      for p in $parsed_profiles; do
        if ! is_valid_profile "$p"; then
          fm_failures+=("frontmatter: x-wos-profiles contains invalid tier '$p' (valid: ${VALID_PROFILES[*]})")
        fi
      done
    fi
  fi

  # metadata.provenance (ADR-0046 DEF-09 / ADR-0059). Required trust origin.
  fm_provenance="$(printf '%s\n' "$fm_block" | awk '/^  provenance: / { sub(/^  provenance: /, ""); print; exit }')"
  if [[ -z "$fm_provenance" ]]; then
    fm_failures+=("frontmatter: missing required field 'metadata.provenance' (ADR-0046 DEF-09)")
  elif ! is_valid_provenance "$fm_provenance"; then
    fm_failures+=("frontmatter: metadata.provenance '$fm_provenance' not in enum (${VALID_PROVENANCE[*]})")
  fi

  # metadata.lifecycle (ADR-0176). Optional; when present it must name a state.
  fm_lifecycle="$(printf '%s\n' "$fm_block" | awk '/^  lifecycle: / { sub(/^  lifecycle: /, ""); print; exit }')"
  if [[ -n "$fm_lifecycle" ]] && ! is_valid_lifecycle "$fm_lifecycle"; then
    fm_failures+=("frontmatter: metadata.lifecycle must be 'active' or 'frozen' (got '$fm_lifecycle')")
  fi

  if [[ ${#fm_failures[@]} -gt 0 ]]; then
    FM_FAILED=$((FM_FAILED + 1))
    FM_FAILURES+=("$command_name")
    echo "FAIL (frontmatter): $command_name"
    for f in "${fm_failures[@]}"; do
      echo "  - $f"
    done
  else
    FM_PASSED=$((FM_PASSED + 1))
    if [[ $VERBOSE -eq 1 ]]; then
      echo "PASS (frontmatter): $command_name"
    fi
  fi
done

# --- Maturity ladder shape (K.6 + ADR-0036) --------------------------------
# Validates persona frontmatter (folder-shaped commands only) declares a valid
# maturity_level + owned_sections shape per wos/maturity-ladder.md. INFORMATIONAL
# in v2.1: warns but does not fail the lint. Promotion to fail-fast is post-v2.1.
#
# Per-level shape rules:
#   L1, L2: owned_sections MUST be empty ([])
#   L3:     owned_sections MUST have exactly 1 entry
#           ADR-0036: L3 promotion follows Path A (strict monotonic) OR Path B
#           (floor + multi-folder fleet). The lint does NOT validate which path
#           was used (that lives in _internal/maturity-ladder/<persona>.md,
#           gitignored); shape lint only checks owned_sections count.
#   L4:     owned_sections MUST have 1+ entries
#   L5:     RESERVED in v2.1 -- no persona should declare L5 yet
# Flat commands (commands/<name>.md) are NOT personas; they SKIP this check.
ML_TOTAL=0
ML_CHECKED=0
ML_WARNED=0
MATURITY_WARNINGS=()

valid_maturity_level() {
  case "$1" in
    L1|L2|L3|L4|L5) return 0 ;;
    *)              return 1 ;;
  esac
}

for file in "${COMMAND_FILES[@]}"; do
  # Only folder-shaped commands (commands/<slug>/SKILL.md) are personas under
  # the K.3 dual layout. Flat commands skip this check entirely.
  [[ "$(basename "$file")" == "SKILL.md" ]] || continue
  ML_TOTAL=$((ML_TOTAL + 1))
  command_name="$(canonical_name_from_path "$file")"

  first_line="$(head -n1 "$file")"
  [[ "$first_line" == "---" ]] || continue
  fm_block="$(extract_frontmatter_block "$file")"
  [[ -n "$fm_block" ]] || continue

  ML_CHECKED=$((ML_CHECKED + 1))

  fm_maturity="$(printf '%s\n' "$fm_block" | awk '/^  maturity_level: / { sub(/^  maturity_level: /, ""); print; exit }' | awk '{ sub(/[[:space:]]*#.*$/, ""); sub(/^[[:space:]]+/, ""); sub(/[[:space:]]+$/, ""); print }')"
  # owned_sections value may legitimately contain '##' (H2 section names),
  # so the trailing-comment strip must NOT cut on '#'. Only trim surrounding whitespace.
  fm_owned_raw="$(printf '%s\n' "$fm_block" | awk '/^  owned_sections: / { sub(/^  owned_sections: /, ""); print; exit }' | awk '{ sub(/^[[:space:]]+/, ""); sub(/[[:space:]]+$/, ""); print }')"

  ml_warnings_local=()

  if [[ -z "$fm_maturity" ]]; then
    ml_warnings_local+=("missing metadata.maturity_level (expected one of L1|L2|L3|L4|L5)")
  elif ! valid_maturity_level "$fm_maturity"; then
    ml_warnings_local+=("metadata.maturity_level '$fm_maturity' is not one of L1|L2|L3|L4|L5")
  fi

  if [[ -z "$fm_owned_raw" ]]; then
    ml_warnings_local+=("missing metadata.owned_sections (expected YAML inline list, e.g. [])")
  else
    parsed_owned="$(parse_yaml_inline_list "$fm_owned_raw")"
    if [[ "$parsed_owned" == "__INVALID__" ]]; then
      ml_warnings_local+=("metadata.owned_sections '$fm_owned_raw' is not a valid YAML inline list (expected '[]' or '[section, section, ...]')")
    else
      # Count non-empty entries
      owned_count=0
      for entry in $parsed_owned; do
        owned_count=$((owned_count + 1))
      done

      case "$fm_maturity" in
        L1|L2)
          if (( owned_count != 0 )); then
            ml_warnings_local+=("maturity_level $fm_maturity requires empty owned_sections []; found $owned_count entry/entries (per wos/maturity-ladder.md)")
          fi
          ;;
        L3)
          if (( owned_count != 1 )); then
            ml_warnings_local+=("maturity_level L3 requires exactly 1 owned_sections entry; found $owned_count (per wos/maturity-ladder.md)")
          fi
          ;;
        L4)
          if (( owned_count < 1 )); then
            ml_warnings_local+=("maturity_level L4 requires 1+ owned_sections entries; found $owned_count (per wos/maturity-ladder.md)")
          fi
          ;;
        L5)
          ml_warnings_local+=("maturity_level L5 is RESERVED in v2.1 -- no persona should declare L5 yet (per wos/maturity-ladder.md '## The 5 levels')")
          ;;
      esac
    fi
  fi

  if [[ ${#ml_warnings_local[@]} -gt 0 ]]; then
    for w in "${ml_warnings_local[@]}"; do
      MATURITY_WARNINGS+=("${command_name}: ${w}")
      ML_WARNED=$((ML_WARNED + 1))
      if [[ $VERBOSE -eq 1 ]] || [[ $STRICT -eq 1 ]]; then
        echo "WARN (maturity-ladder): ${command_name} ${w}"
      fi
    done
  fi
done

ROOT_TOTAL=0
ROOT_WARNED=0
ROOT_WARNINGS=()

for relpath in "${ROOT_DOC_FILES[@]}"; do
  file="${REPO_ROOT}/${relpath}"
  [[ -f "$file" ]] || continue
  ROOT_TOTAL=$((ROOT_TOTAL + 1))
  file_warnings=()

  for entry in "${FORBIDDEN_PATTERNS[@]}"; do
    pattern="${entry%%:*}"
    name="${entry##*:}"
    if LC_ALL=C grep -qF -- "$pattern" "$file" 2>/dev/null; then
      file_warnings+=("contains: $name")
    fi
  done

  if [[ ${#file_warnings[@]} -gt 0 ]]; then
    ROOT_WARNED=$((ROOT_WARNED + 1))
    ROOT_WARNINGS+=("$relpath")
    if [[ $VERBOSE -eq 1 ]] || [[ $STRICT -eq 1 ]]; then
      echo "WARN (root): $relpath"
      for warning in ${file_warnings[@]+"${file_warnings[@]}"}; do
        echo "  ! $warning"
      done
    fi
  elif [[ $VERBOSE -eq 1 ]]; then
    echo "PASS (root): $relpath"
  fi
done

# --- Shared canonical block validation ---------------------------------------
# For each `<!-- shared:<name> -->` marker found in any command file, verify
# that the body following the marker matches the canonical content in
# `commands/_shared/<name>.md` byte-for-byte. Drift here is a FAIL, not a warn.
SHARED_TOTAL=0
SHARED_PASSED=0
SHARED_FAILED=0
SHARED_FAILURES=()

if [[ -d "$SHARED_DIR" ]]; then
  for file in "${COMMAND_FILES[@]}"; do
    filename="$(basename "$file")"
    command_name="${filename%.md}"
    while IFS= read -r marker_name; do
      [[ -z "$marker_name" ]] && continue
      SHARED_TOTAL=$((SHARED_TOTAL + 1))
      canonical="${SHARED_DIR}/${marker_name}.md"
      if [[ ! -f "$canonical" ]]; then
        SHARED_FAILED=$((SHARED_FAILED + 1))
        SHARED_FAILURES+=("$command_name uses unknown marker shared:$marker_name")
        continue
      fi
      end_pattern="$(shared_end_pattern "$marker_name")"
      body=$(awk -v marker="<!-- shared:${marker_name} -->" -v endpat="$end_pattern" '
        $0 == marker { capturing=1; next }
        capturing && $0 ~ endpat { exit }
        capturing { print }
      ' "$file")
      canonical_body=$(cat "$canonical")
      # Strip a single trailing newline from canonical_body for fair compare:
      # `cat` preserves file content verbatim; awk-based `body` lacks any
      # trailing newline that exists past the section boundary.
      if [[ "$body" == "$canonical_body" ]]; then
        SHARED_PASSED=$((SHARED_PASSED + 1))
      else
        SHARED_FAILED=$((SHARED_FAILED + 1))
        SHARED_FAILURES+=("$command_name has drift in shared:$marker_name")
        if [[ $VERBOSE -eq 1 ]] || [[ $STRICT -eq 1 ]]; then
          echo "DRIFT: $command_name :: shared:$marker_name"
          diff <(printf '%s' "$canonical_body") <(printf '%s' "$body") | head -20 | sed 's/^/    /'
        fi
      fi
    done < <(grep -oE '<!-- shared:[a-z-]+ -->' "$file" | sed -E 's/<!-- shared:(.*) -->/\1/')
  done
else
  echo "Warning: _shared/ directory not found at $SHARED_DIR; skipping shared-block validation."
fi

# --- Skills drift check (P11 Phase 2) ----------------------------------------
# Verifies that committed `.claude/skills/<name>/SKILL.md` files match what
# `scripts/build-agent-skills.sh` would generate from the canonical
# `commands/<name>.md` files. Drift (or stale skill dirs) is a FAIL because
# Skills artifacts are part of the multi-tool distribution contract: any
# tool that reads `.claude/skills/` (Cursor 2.4+, Claude Code, Copilot,
# Codex, Gemini CLI, OpenHands, Goose, etc.) consumes those files directly.
#
# Skipped (with a note) when the adapter script is missing, so this check
# does not break legacy clones that pre-date Phase 2.
SKILLS_DRIFT_STATUS="skipped"
SKILLS_DRIFT_OUTPUT=""

ADAPTER_SCRIPT="${SCRIPT_DIR}/build-agent-skills.sh"
if [[ -x "$ADAPTER_SCRIPT" ]]; then
  if SKILLS_DRIFT_OUTPUT="$("$ADAPTER_SCRIPT" --check 2>&1)"; then
    SKILLS_DRIFT_STATUS="clean"
  else
    SKILLS_DRIFT_STATUS="drifted"
  fi
fi

# --- Proper-noun novelty check (mirror-guard complement) ---------------------
# check-mirror-codenames.sh knows a LIST and is blind to every name not on it, which is how a
# private engagement name sat in two wos/ topics on 2026-08-10 with the guard reporting clean.
# This does not classify names (measured unworkable: 2087 capitalised names, 941 appearing
# once). It flags NOVELTY, and the 20 commits of that day introduced zero.
PROPER_NOUN_STATUS="skipped"
PROPER_NOUN_OUTPUT=""

PROPER_NOUN_SCRIPT="${SCRIPT_DIR}/build-proper-noun-baseline.py"
if [[ -f "$PROPER_NOUN_SCRIPT" ]]; then
  if PROPER_NOUN_OUTPUT="$(python3 "$PROPER_NOUN_SCRIPT" --check 2>&1)"; then
    PROPER_NOUN_STATUS="clean"
  else
    PROPER_NOUN_STATUS="new-names"
  fi
fi

# --- Closure-floor view drift check (ADR-0138) ------------------------------
# The per-consumer views are generated from wos/closure-floors.md. Editing a view by hand,
# or editing the canonical file without regenerating, silently changes which floors a
# closure command applies. Drift is a FAIL for the same reason skills drift is.
CLOSURE_VIEWS_STATUS="skipped"
CLOSURE_VIEWS_OUTPUT=""

CLOSURE_VIEWS_SCRIPT="${SCRIPT_DIR}/build-closure-floor-views.py"
if [[ -f "$CLOSURE_VIEWS_SCRIPT" ]]; then
  if CLOSURE_VIEWS_OUTPUT="$(python3 "$CLOSURE_VIEWS_SCRIPT" --check 2>&1)"; then
    CLOSURE_VIEWS_STATUS="clean"
  else
    CLOSURE_VIEWS_STATUS="drifted"
  fi
fi

# --- Command-catalog drift check (ADR-0005) ---------------------------------
# docs/command-catalog.html and docs/command-catalog.json are GENERATED from
# commands/*.md by build-command-catalog.py. Drift is a FAIL: the catalog is the
# offline, multi-tool command reference and must not desync from the canonical
# command files. README.md's "## Command catalog" section is a hand-written
# pointer to the HTML, not a generated list, so it is not part of this check.
# Skipped (with a note) when the generator is absent.
CATALOG_DRIFT_STATUS="skipped"
CATALOG_DRIFT_OUTPUT=""
CATALOG_SCRIPT="${SCRIPT_DIR}/build-command-catalog.py"
if [[ -f "$CATALOG_SCRIPT" ]]; then
  if CATALOG_DRIFT_OUTPUT="$(python3 "$CATALOG_SCRIPT" --check 2>&1)"; then
    CATALOG_DRIFT_STATUS="clean"
  else
    CATALOG_DRIFT_STATUS="drifted"
  fi
fi

# --- Registry membership guard (ADR-0029) -----------------------------------
# Every command must appear in all four discoverability surfaces, and every
# entry in those surfaces must map to a real command. Catches the
# "shipped but unregistered" class (e.g. api-contract-review, stack-currency-check
# were missing from every registry) and stale entries for renamed/removed
# commands. Deterministic; no markers required.
bt='`'
WOS_FILE="${REPO_ROOT}/WORKFLOW_OPERATING_SYSTEM.md"
ROLES_FILE="${REPO_ROOT}/wos/command-roles.md"
STUBS_FILE="${REPO_ROOT}/COMMAND_PROMPT_STUBS.md"

REG_TOTAL=0
REG_PASSED=0
REG_FAILED=0
REG_FAILURES=()

if [[ -f "$WOS_FILE" && -f "$ROLES_FILE" && -f "$STUBS_FILE" ]]; then
  # Forward: each command present in all three registries.
  for file in "${COMMAND_FILES[@]}"; do
    cmd="$(canonical_name_from_path "$file")"
    REG_TOTAL=$((REG_TOTAL + 1))
    reg_missing=""
    grep -qE "^- ${bt}${cmd}${bt}\$" "$WOS_FILE"        || reg_missing="${reg_missing} spec-cluster-list"
    grep -qE "^### ${cmd}\$" "$ROLES_FILE"              || reg_missing="${reg_missing} command-roles.md"
    grep -qE "^\\| ${bt}${cmd}${bt} \\|" "$STUBS_FILE"  || reg_missing="${reg_missing} STUBS"
    if [[ -n "$reg_missing" ]]; then
      REG_FAILED=$((REG_FAILED + 1))
      REG_FAILURES+=("${cmd} missing from:${reg_missing}")
    else
      REG_PASSED=$((REG_PASSED + 1))
    fi
  done

  # Reverse: wos/command-roles.md entries map to real commands.
  while IFS= read -r name; do
    [[ -z "$name" ]] && continue
    if [[ ! -f "${COMMANDS_DIR}/${name}.md" && ! -f "${COMMANDS_DIR}/${name}/SKILL.md" ]]; then
      REG_FAILED=$((REG_FAILED + 1))
      REG_FAILURES+=("orphan entry: command-roles.md '### ${name}' has no commands/${name}.md (flat) or commands/${name}/SKILL.md (folder-shaped)")
    fi
  done < <(grep -oE '^### [a-z][a-z-]+$' "$ROLES_FILE" | sed 's/^### //')

  # Reverse: COMMAND_PROMPT_STUBS.md table rows map to real commands.
  while IFS= read -r name; do
    [[ -z "$name" ]] && continue
    if [[ ! -f "${COMMANDS_DIR}/${name}.md" && ! -f "${COMMANDS_DIR}/${name}/SKILL.md" ]]; then
      REG_FAILED=$((REG_FAILED + 1))
      REG_FAILURES+=("orphan entry: STUBS row ${bt}${name}${bt} has no commands/${name}.md (flat) or commands/${name}/SKILL.md (folder-shaped)")
    fi
  done < <(awk -F'`' '/^\| `[a-z]/ {print $2}' "$STUBS_FILE")
fi

# --- Index-row membership guard (ADR-0029) ----------------------------------
# Every ADR file has a row in docs/adr/README.md and every eval scenario file
# has a row in evals/README.md (and the reverse: no index row without a file).
# Mirrors the command-registry guard for the two numbered-artifact indexes.
ADR_INDEX="${REPO_ROOT}/docs/adr/README.md"
SCEN_INDEX="${REPO_ROOT}/evals/README.md"

IDX_TOTAL=0
IDX_PASSED=0
IDX_FAILED=0
IDX_FAILURES=()

if [[ -f "$ADR_INDEX" ]]; then
  shopt -s nullglob
  for f in "${REPO_ROOT}"/docs/adr/[0-9]*.md; do
    base="$(basename "$f")"
    num="${base%%-*}"
    IDX_TOTAL=$((IDX_TOTAL + 1))
    if grep -qE "^\\| \\[${num}\\]" "$ADR_INDEX"; then
      IDX_PASSED=$((IDX_PASSED + 1))
    else
      IDX_FAILED=$((IDX_FAILED + 1))
      IDX_FAILURES+=("ADR ${num} (${base}) missing from docs/adr/README.md index")
    fi
  done
  shopt -u nullglob
  while IFS= read -r num; do
    [[ -z "$num" ]] && continue
    if ! ls "${REPO_ROOT}/docs/adr/${num}-"*.md >/dev/null 2>&1; then
      IDX_FAILED=$((IDX_FAILED + 1))
      IDX_FAILURES+=("orphan: docs/adr/README.md row [${num}] has no docs/adr/${num}-*.md")
    fi
  done < <(grep -oE '^\| \[[0-9]{4}\]' "$ADR_INDEX" | grep -oE '[0-9]{4}')
fi

if [[ -f "$SCEN_INDEX" ]]; then
  shopt -s nullglob
  for f in "${REPO_ROOT}"/evals/scenarios/[0-9]*.md; do
    base="$(basename "$f")"
    num="${base%%-*}"
    IDX_TOTAL=$((IDX_TOTAL + 1))
    if grep -qE "\\(\\./scenarios/${num}-" "$SCEN_INDEX"; then
      IDX_PASSED=$((IDX_PASSED + 1))
    else
      IDX_FAILED=$((IDX_FAILED + 1))
      IDX_FAILURES+=("scenario ${num} (${base}) missing from evals/README.md index")
    fi
  done
  shopt -u nullglob
  while IFS= read -r num; do
    [[ -z "$num" ]] && continue
    if ! ls "${REPO_ROOT}/evals/scenarios/${num}-"*.md >/dev/null 2>&1; then
      IDX_FAILED=$((IDX_FAILED + 1))
      IDX_FAILURES+=("orphan: evals/README.md row ${num} has no evals/scenarios/${num}-*.md")
    fi
  done < <(grep -oE '\./scenarios/[0-9]+-' "$SCEN_INDEX" | grep -oE '[0-9]+')
fi

# --- Scenario inner-reference drift guard (ADR-0029 family) -----------------
# The index-row guard above proves each scenario FILE is indexed. This guard
# goes one level deeper: every artifact reference written INSIDE a scenario body
# must still resolve to a real file. Scenarios name commands, shared blocks, and
# ADRs in prose; when a command is renamed or an ADR slug changes, those inner
# references rot silently (the file still has its index row, so the guard above
# stays green). Broken here is a FAIL, same tier as the registry/index guards.
#
# Reference shapes recognized (all extracted from the scenario body):
#   - command:      commands/<name>.md and @commands/<name>.md; also bare
#                   backtick command tokens on a "Related commands:" line.
#                   Resolves to commands/<name>.md OR commands/<name>/SKILL.md.
#   - shared block: commands/_shared/<name>.md -> file must exist.
#   - ADR:          docs/adr/<NNNN>-<slug>.md (optionally relative-prefixed with
#                   ./ or ../) -> file must exist. A leading path segment such as
#                   internal/docs/adr/... points at the private tree, not this
#                   repo, and is deliberately NOT matched.
#   - anchor:       commands/<name>.md ## <Anchor> -> the anchor must exist as a
#                   `## <Anchor>` line in the resolved command file.
#
# Fenced code blocks (```...```) are skipped so example/paste text does not
# trip the guard, and any line carrying an inline `<!-- lint:skip -->` escape is
# skipped as well (the reviewed way to keep a deliberate non-existent reference,
# e.g. a scenario that documents detection of a bogus command name).
SCEN_SRC_DIR="${REPO_ROOT}/evals/scenarios"
SCEN_REF_TOTAL=0
SCEN_REF_PASSED=0
SCEN_REF_FAILED=0
SCEN_REF_FAILURES=()

# Emit typed reference records (KIND<TAB>lineno<TAB>payload[<TAB>anchor]) for one
# scenario file. A leading boundary sentinel space is prepended to every body
# line so a reference at column 1 still has a preceding boundary char; the
# leading-boundary character class then rejects references embedded inside a
# longer path segment. String regexes are used (not /.../ literals) so a literal
# slash needs no escaping and the pattern stays portable across BSD awk, gawk,
# and mawk.
extract_scenario_refs() {
  awk '
    BEGIN { infence = 0 }
    {
      raw = $0
      lineno = NR
      if (raw ~ /<!-- lint:skip -->/) next
      if (raw ~ /^[[:space:]]*```/) { infence = (infence ? 0 : 1); next }
      if (infence) next
      line = " " raw

      tmp = line
      while (match(tmp, "[^A-Za-z0-9_/-](\\.\\.?/)*commands/_shared/[a-z0-9-]+\\.md")) {
        m = substr(tmp, RSTART, RLENGTH)
        p = substr(m, index(m, "commands/"))
        print "SHARED\t" lineno "\t" p
        tmp = substr(tmp, RSTART + RLENGTH)
      }

      tmp = line
      while (match(tmp, "[^A-Za-z0-9_/-](\\.\\.?/)*commands/[a-z0-9-]+\\.md ## [A-Za-z0-9 ()._-]+")) {
        m = substr(tmp, RSTART, RLENGTH)
        m = substr(m, index(m, "commands/"))
        idx = index(m, " ## ")
        fp = substr(m, 1, idx - 1)
        anc = substr(m, idx + 4)
        print "ANCHOR\t" lineno "\t" fp "\t" anc
        tmp = substr(tmp, RSTART + RLENGTH)
      }

      tmp = line
      while (match(tmp, "[^A-Za-z0-9_/-](\\.\\.?/)*commands/[a-z0-9-]+\\.md")) {
        m = substr(tmp, RSTART, RLENGTH)
        p = substr(m, index(m, "commands/"))
        name = substr(p, 10)
        sub(/\.md$/, "", name)
        print "CMD\t" lineno "\t" name
        tmp = substr(tmp, RSTART + RLENGTH)
      }

      tmp = line
      while (match(tmp, "[^A-Za-z0-9_/-](\\.\\.?/)*docs/adr/[0-9][0-9][0-9][0-9]-[a-z0-9-]+\\.md")) {
        m = substr(tmp, RSTART, RLENGTH)
        p = substr(m, index(m, "docs/adr/"))
        print "ADR\t" lineno "\t" p
        tmp = substr(tmp, RSTART + RLENGTH)
      }

      if (raw ~ /Related commands:/) {
        tmp = raw
        while (match(tmp, /`[a-z][a-z0-9-]+`/)) {
          tok = substr(tmp, RSTART + 1, RLENGTH - 2)
          print "RELCMD\t" lineno "\t" tok
          tmp = substr(tmp, RSTART + RLENGTH)
        }
      }
    }
  ' "$1"
}

if [[ -d "$SCEN_SRC_DIR" ]]; then
  shopt -s nullglob
  for sf in "${SCEN_SRC_DIR}"/*.md; do
    rel="${sf#${REPO_ROOT}/}"
    while IFS="$(printf '\t')" read -r kind lineno payload anchor; do
      [[ -z "$kind" ]] && continue
      SCEN_REF_TOTAL=$((SCEN_REF_TOTAL + 1))
      case "$kind" in
        CMD|RELCMD)
          if [[ -f "${COMMANDS_DIR}/${payload}.md" || -f "${COMMANDS_DIR}/${payload}/SKILL.md" ]]; then
            SCEN_REF_PASSED=$((SCEN_REF_PASSED + 1))
          else
            SCEN_REF_FAILED=$((SCEN_REF_FAILED + 1))
            SCEN_REF_FAILURES+=("${rel}:${lineno}: unresolved command ref 'commands/${payload}.md' (no flat or folder-shaped command)")
          fi
          ;;
        SHARED|ADR)
          if [[ -f "${REPO_ROOT}/${payload}" ]]; then
            SCEN_REF_PASSED=$((SCEN_REF_PASSED + 1))
          else
            SCEN_REF_FAILED=$((SCEN_REF_FAILED + 1))
            SCEN_REF_FAILURES+=("${rel}:${lineno}: unresolved reference '${payload}' (file not found)")
          fi
          ;;
        ANCHOR)
          anchor_name="${payload#commands/}"
          anchor_name="${anchor_name%.md}"
          anchor_cmdfile=""
          if [[ -f "${COMMANDS_DIR}/${anchor_name}.md" ]]; then
            anchor_cmdfile="${COMMANDS_DIR}/${anchor_name}.md"
          elif [[ -f "${COMMANDS_DIR}/${anchor_name}/SKILL.md" ]]; then
            anchor_cmdfile="${COMMANDS_DIR}/${anchor_name}/SKILL.md"
          fi
          # Trim trailing whitespace the greedy anchor class may have captured.
          anchor="${anchor%"${anchor##*[![:space:]]}"}"
          if [[ -z "$anchor_cmdfile" ]]; then
            SCEN_REF_FAILED=$((SCEN_REF_FAILED + 1))
            SCEN_REF_FAILURES+=("${rel}:${lineno}: anchor target 'commands/${anchor_name}.md' does not exist")
          elif grep -Fxq -- "## ${anchor}" "$anchor_cmdfile"; then
            SCEN_REF_PASSED=$((SCEN_REF_PASSED + 1))
          else
            SCEN_REF_FAILED=$((SCEN_REF_FAILED + 1))
            SCEN_REF_FAILURES+=("${rel}:${lineno}: anchor '## ${anchor}' not found in commands/${anchor_name}.md")
          fi
          ;;
      esac
    done < <(extract_scenario_refs "$sf")
  done
  shopt -u nullglob
fi

# --- Count-marker guard (ADR-0029) ------------------------------------------
# Numbers wrapped in `<!-- count:KIND -->N<!-- /count -->` must equal the live
# on-disk count for KIND. HTML comments do not render, so the marker is
# invisible to readers; only the digit shows. Catches stale prose counts.
disk_count() {
  local n blk tpl tplf lvl
  case "$1" in
    commands)           n=$(( $(ls "${COMMANDS_DIR}"/*.md 2>/dev/null | wc -l) + $(ls "${COMMANDS_DIR}"/*/SKILL.md 2>/dev/null | wc -l) )) ;;
    commands-minimal)   n=$(grep -h '^  x-wos-profiles:' "${COMMANDS_DIR}"/*.md "${COMMANDS_DIR}"/*/SKILL.md 2>/dev/null | grep -cw minimal) ;;
    commands-core)      n=$(grep -h '^  x-wos-profiles:' "${COMMANDS_DIR}"/*.md "${COMMANDS_DIR}"/*/SKILL.md 2>/dev/null | grep -cw core) ;;
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
    frozen-commands)    n=$( { grep -l 'lifecycle: frozen' "${COMMANDS_DIR}"/*.md "${COMMANDS_DIR}"/*/SKILL.md 2>/dev/null || true; } | wc -l) ;;
    commands-flat)      n=$(ls "${COMMANDS_DIR}"/*.md 2>/dev/null | wc -l) ;;
    commands-multi-repo) n=$( { grep -l '^  multi-repo-aware: true' "${COMMANDS_DIR}"/*.md 2>/dev/null || true; } | grep -vc -- '-fleet\.md$') ;;
    commands-history)   n=$( { grep -lE '^  context-layers-consumed: \[.*history' "${COMMANDS_DIR}"/*.md "${COMMANDS_DIR}"/*/SKILL.md 2>/dev/null || true; } | wc -l) ;;
    runtime-verify-commands) n=$(ls "${COMMANDS_DIR}"/*-runtime-verify.md 2>/dev/null | wc -l) ;;
    editor-modes)       n=$(grep -h '^  primary-cursor-mode:' "${COMMANDS_DIR}"/*.md "${COMMANDS_DIR}"/*/SKILL.md 2>/dev/null | sed 's/.*primary-cursor-mode:[[:space:]]*//' | sort -u | wc -l) ;;
    personas-shadow|personas-advisory|personas-gated|personas-peer|personas-autonomous)
                        # Persona count at one maturity level, named as wos/maturity-ladder.md names it
                        # (L1 shadow ... L5 autonomous); the marker grammar allows no digit in a kind.
                        case "$1" in
                          personas-shadow) lvl=1 ;; personas-advisory) lvl=2 ;; personas-gated) lvl=3 ;;
                          personas-peer) lvl=4 ;; *) lvl=5 ;;
                        esac
                        n=$( { grep -l "^  maturity_level: L${lvl}\$" "${COMMANDS_DIR}"/*/SKILL.md 2>/dev/null || true; } | wc -l) ;;
    design-review-checks) n=$(grep -cE '^- \*\*Check [0-9]+:' "${COMMANDS_DIR}"/design-spec-review.md 2>/dev/null) ;;
    closure-pattern-sections) n=$(sed '/^Optional/q' "${COMMANDS_DIR}"/_shared/task-state-slice-closure-pattern.md 2>/dev/null | grep -cE '^[0-9]+\. `#') ;;
    closure-floors)     n=$(cat "${REPO_ROOT}"/wos/closure-floors.md "${REPO_ROOT}"/wos/platform-runtime-floors.md 2>/dev/null | grep -c '^On missing evidence:') ;;
    closure-floors-recording) n=$(cat "${REPO_ROOT}"/wos/closure-floors.md "${REPO_ROOT}"/wos/platform-runtime-floors.md 2>/dev/null | grep -cE '^On missing evidence: (record|reconcile)([^a-z]|$)') ;;
    closure-floors-record) n=$(cat "${REPO_ROOT}"/wos/closure-floors.md "${REPO_ROOT}"/wos/platform-runtime-floors.md 2>/dev/null | grep -cE '^On missing evidence: record([^a-z]|$)') ;;
    task-shapes)        n=$(grep -c '^## ' "${REPO_ROOT}"/wos/workflow-shapes.md 2>/dev/null) ;;
    task-memory-files)  n=$(awk '/^## Section ownership matrix/{f=1;next} /^## /{f=0} f && /^### [^ ]+\.md/' "${REPO_ROOT}"/wos/substrate-peers.md 2>/dev/null | wc -l) ;;
    fleet-substrate-files) n=$(awk '/^## Fleet-substrate files/{f=1;next} /^## /{f=0} f && /^### [^ ]+\.md/' "${REPO_ROOT}"/wos/substrate-peers.md 2>/dev/null | wc -l) ;;
    log-fields)         n=$(sed -n '/^REQUIRED_FIELDS = {/,/^}/p' "${REPO_ROOT}"/scripts/verify-log-validator.py 2>/dev/null | grep -o '"[a-z_]*"' | wc -l) ;;
    task-cost-phases)   n=$(sed -n '/^PHASES = \[/,/^\]/p' "${REPO_ROOT}"/scripts/measure-task-cost.py 2>/dev/null | grep -c '^    ("') ;;
    spine-scenarios)    n=$(grep -c '"file":' "${REPO_ROOT}"/evals/spine-evals.json 2>/dev/null) ;;
    shared-*)           blk="${1#shared-}"
                        [[ -f "${COMMANDS_DIR}/_shared/${blk}.md" ]] || { printf '__UNKNOWN__'; return 0; }
                        n=$( { grep -l "<!-- shared:${blk} -->" "${COMMANDS_DIR}"/*.md "${COMMANDS_DIR}"/*/SKILL.md 2>/dev/null || true; } | wc -l) ;;
    sections-*)         tpl="$(printf '%s' "${1#sections-}" | tr 'a-z-' 'A-Z_')"
                        tplf="${REPO_ROOT}/templates/${tpl}.md"
                        [[ -f "$tplf" ]] || tplf="${REPO_ROOT}/templates/${tpl}.template.md"
                        [[ -f "$tplf" ]] || { printf '__UNKNOWN__'; return 0; }
                        n=$(grep -c '^## ' "$tplf") ;;
    *)                  printf '__UNKNOWN__'; return 0 ;;
  esac
  printf '%s' "$n" | tr -d '[:space:]'
}

COUNT_SCAN_FILES=()
for rf in "${ROOT_DOC_FILES[@]}"; do COUNT_SCAN_FILES+=("${REPO_ROOT}/${rf}"); done
for wf in "${REPO_ROOT}"/wos/*.md; do COUNT_SCAN_FILES+=("$wf"); done
COUNT_SCAN_FILES+=("${REPO_ROOT}/docs/FAQ.md" "${REPO_ROOT}/docs/MIGRATION.md" "${REPO_ROOT}/docs/adr/README.md" "${REPO_ROOT}/evals/README.md")
# Command files and the shared blocks carry counts of derived sets (floors, template sections,
# the closure write pattern), so they are in the scan-set too. The generated .claude/skills/
# copies are not: build-agent-skills.sh --check keeps them equal to these sources.
for cf in "${COMMANDS_DIR}"/*.md "${COMMANDS_DIR}"/*/SKILL.md "${COMMANDS_DIR}"/_shared/*.md; do
  [[ -f "$cf" ]] && COUNT_SCAN_FILES+=("$cf")
done

COUNT_TOTAL=0
COUNT_PASSED=0
COUNT_FAILED=0
COUNT_FAILURES=()

for f in "${COUNT_SCAN_FILES[@]}"; do
  [[ -f "$f" ]] || continue
  rel="${f#${REPO_ROOT}/}"
  while IFS= read -r token; do
    [[ -z "$token" ]] && continue
    kind="$(printf '%s' "$token" | sed -E 's/<!-- count:([a-z-]+) -->[0-9]+<!-- \/count -->/\1/')"
    num="$(printf '%s' "$token" | sed -E 's/<!-- count:[a-z-]+ -->([0-9]+)<!-- \/count -->/\1/')"
    COUNT_TOTAL=$((COUNT_TOTAL + 1))
    expected="$(disk_count "$kind")"
    if [[ "$expected" == "__UNKNOWN__" ]]; then
      COUNT_FAILED=$((COUNT_FAILED + 1))
      COUNT_FAILURES+=("${rel}: unknown count kind '${kind}'")
    elif [[ "$num" != "$expected" ]]; then
      COUNT_FAILED=$((COUNT_FAILED + 1))
      COUNT_FAILURES+=("${rel}: count:${kind} says ${num} but disk has ${expected}")
    else
      COUNT_PASSED=$((COUNT_PASSED + 1))
    fi
  done < <(grep -oE '<!-- count:[a-z-]+ -->[0-9]+<!-- /count -->' "$f" 2>/dev/null)
done

# --- Definition-of-done bullet imperativeness (ADR-0056 follow-up) ----------
# Every command's closing Definition-of-done bullet must be the imperative
# self-verify form, not the old declarative "Shared contract: ..." pointer.
# The declarative form can be ticked without loading the spec gate (the
# "bullet-6 escape" surfaced by the deliverable-coverage-ledger dogfood).
DOD_OLD='- Shared contract: **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.'
DOD_FAILED=0
DOD_FAILURES=()
DOD_SCAN=()
for cf in "${REPO_ROOT}"/commands/*.md; do
  [[ -f "$cf" ]] && DOD_SCAN+=("$cf")
done
for cf in "${REPO_ROOT}"/commands/*/SKILL.md; do
  [[ -f "$cf" ]] || continue
  [[ "$(basename "$(dirname "$cf")")" == "_shared" ]] && continue
  DOD_SCAN+=("$cf")
done
for cf in "${DOD_SCAN[@]}"; do
  if grep -Fq -e "$DOD_OLD" "$cf"; then
    DOD_FAILED=$((DOD_FAILED + 1))
    DOD_FAILURES+=("${cf#${REPO_ROOT}/}: closing DoD bullet is the old declarative 'Shared contract: ...' form")
  fi
done

# --- Doc-sync guard ---------------------------------------------------------
# Delegates to scripts/check-doc-sync.sh, which verifies cross-document
# references (e.g. doc-to-doc links, ADR/scenario references, command anchors)
# resolve to real targets. The helper emits a summary line of the form:
#   "Doc-sync: <verified> refs verified, <broken> broken"
# from which DSCOUNT and DSBROKEN are parsed. A non-zero broken count flips
# the lint into a FAIL state (consistent with shared/registry/count guards).
# If the helper script is absent we skip gracefully so legacy clones do not
# break; the summary line still records the skip explicitly.
DOC_SYNC_SCRIPT="${SCRIPT_DIR}/check-doc-sync.sh"
DSCOUNT=0
DSBROKEN=0
DS_STATUS="skipped"
DS_OUTPUT=""
DS_EXIT=0

if [[ -x "$DOC_SYNC_SCRIPT" ]]; then
  set +e
  DS_OUTPUT="$("$DOC_SYNC_SCRIPT" 2>&1)"
  DS_EXIT=$?
  set -e
  # Parse the canonical summary line: "Doc-sync: N refs verified, M broken".
  ds_summary_line="$(printf '%s\n' "$DS_OUTPUT" | grep -iE '^doc-sync: [0-9]+ refs verified, [0-9]+ broken' | tail -n1 || true)"
  if [[ -n "$ds_summary_line" ]]; then
    DSCOUNT="$(printf '%s' "$ds_summary_line" | sed -E 's/^[Dd]oc-sync: ([0-9]+) refs verified, ([0-9]+) broken.*/\1/')"
    DSBROKEN="$(printf '%s' "$ds_summary_line" | sed -E 's/^[Dd]oc-sync: ([0-9]+) refs verified, ([0-9]+) broken.*/\2/')"
    DS_STATUS="ran"
  else
    # Helper ran but did not emit the expected summary line; treat exit code
    # as authoritative and surface the raw output to aid debugging.
    DS_STATUS="ran"
    if (( DS_EXIT != 0 )); then
      DSBROKEN=1
    fi
  fi
elif [[ -f "$DOC_SYNC_SCRIPT" ]]; then
  # Present but not executable: surface as a soft skip with a hint.
  DS_STATUS="skipped (not executable)"
fi

# --- Renumber check (ADR-0225) ------------------------------------------------
# The same script in its --against HEAD mode, FAIL-tier. The pass above asks whether
# each cited target EXISTS; an inserted numbered section keeps every number in
# existence and moves the title under it, so that pass exits 0 on the defect of record.
# This one compares the working tree with HEAD: a numbered heading now naming another
# section, a heading whose text is gone, or a deleted path, still cited by a line the
# change did not add. On a clean tree (CI) there is no change and it says so. Exit 2
# (no git revision, a tarball) is reported as not measured and does not fail the lint.
DR_STATUS="skipped"
DR_OUTPUT=""
DR_EXIT=0
DR_SUMMARY=""
if [[ -x "$DOC_SYNC_SCRIPT" ]]; then
  set +e
  DR_OUTPUT="$("$DOC_SYNC_SCRIPT" --against HEAD 2>&1)"
  DR_EXIT=$?
  set -e
  DR_SUMMARY="$(printf '%s\n' "$DR_OUTPUT" | grep -E '^doc-sync --against' | tail -n1 || true)"
  case "$DR_EXIT" in
    0) DR_STATUS="clean" ;;
    1) DR_STATUS="broken" ;;
    *) DR_STATUS="not measured" ;;
  esac
fi

# --- Mirror-codename leak guard ---------------------------------------------
# Delegates to scripts/check-mirror-codenames.sh, which greps the TRACKED tree
# for the private codenames listed in the gitignored sidecar
# scripts/.mirror-codenames (plus the absolute /Users/<name> path class). This is
# the guard's only executable caller: without it nothing runs it outside its own
# test, and a leak gate nobody invokes gates nothing.
#
# Guard exit contract: 0 clean and every scan ran, 1 leak class(es) found, 2 usage
# error (bad or missing target directory), 3 the structural scans ran clean but the
# codename scan did not run because there is no sidecar. Exit 3 exists because 0 and
# 3 were one code until 2026-08-30, so this line read "clean (tracked tree)" on every
# CI runner, where the sidecar is gitignored and therefore always absent. It does not
# fail the lint: only exit 1 does, and making an absent gitignored file fail the build
# would be a change of policy rather than of honesty. Since 2026-08-21 a missing codename sidecar is NOT
# exit 2: it disables only the codename scan, while the absolute-path and
# ticket-id scans still run and can still return 1. Before that, the gitignored
# sidecar made the whole guard inert on every CI runner.
# Only exit 1 fails the lint, and the leak classes are printed so the
# offending file is actionable. Exit 2 is an INFORMATIONAL one-line skip on
# purpose: the sidecar is gitignored, so it is absent in CI and in every clean
# checkout, and failing there would break the build for everyone while proving
# nothing. Any other exit code is also a non-failing skip that names the code.
#
# A MISSING guard script is NOT a skip: the script is tracked, so its absence
# means the tree is broken or the check was deleted, and letting the lint pass
# there is the same fail-open shape this guard exists to close (a guard that
# cannot run must never report green). Only the gitignored sidecar is a
# legitimate absence.
MC_SCRIPT="${SCRIPT_DIR}/check-mirror-codenames.sh"
MC_STATUS="MISSING: tracked guard script absent from this tree"
MC_OUTPUT=""
MC_EXIT=0
MC_MISSING=1

if [[ -f "$MC_SCRIPT" ]]; then
  MC_MISSING=0
  set +e
  MC_OUTPUT="$(cd "$REPO_ROOT" && bash "$MC_SCRIPT" . 2>&1)"
  MC_EXIT=$?
  set -e
  case "$MC_EXIT" in
    0) MC_STATUS="clean (tracked tree)" ;;
    1) MC_STATUS="LEAK class(es) found (see below)" ;;
    2) MC_STATUS="skipped (guard usage error: bad or missing target directory)" ;;
    3) MC_STATUS="clean on the structural scans; codename scan not measured (no sidecar)" ;;
    *) MC_STATUS="skipped (guard exited ${MC_EXIT})" ;;
  esac
fi


echo ""
echo "================================================================================"
echo "Lint summary: $TOTAL command(s), $PASSED passed, $FAILED failed, $WARNED warned"
# Regression guard: every `wos/<topic>.md` a command cites must exist. This is the
# consumer side of the runtime payload the installer now ships on every sync; a command
# citing a topic that is not there fails its own MANDATORY load, and today that failure is
# silent. Passes on first run (0 missing), so it guards against a future rename or delete
# rather than reporting a live break.
WOS_REF_TOTAL=0
WOS_REF_MISSING=0
WOS_REF_LIST=""
while IFS= read -r topic; do
  [[ -n "$topic" ]] || continue
  WOS_REF_TOTAL=$((WOS_REF_TOTAL + 1))
  if [[ ! -f "${REPO_ROOT}/wos/${topic}.md" ]]; then
    WOS_REF_MISSING=$((WOS_REF_MISSING + 1))
    WOS_REF_LIST="${WOS_REF_LIST} wos/${topic}.md"
  fi
done < <(grep -ohE 'wos/[A-Za-z0-9_/-]+\.md' \
           "${REPO_ROOT}"/commands/*.md "${REPO_ROOT}"/commands/*/SKILL.md 2>/dev/null \
         | sed -e 's|^wos/||' -e 's|\.md$||' | sort -u)

echo "Root docs:    $ROOT_TOTAL file(s) scanned for forbidden bytes, $ROOT_WARNED warned (strict-only; fails the lint under --strict)"
echo "Shared:       $SHARED_TOTAL marker(s), $SHARED_PASSED matched canonical, $SHARED_FAILED drifted"
echo "Frontmatter:  $FM_TOTAL command(s), $FM_PRESENT with frontmatter ($FM_PASSED passed, $FM_FAILED failed), $FM_MISSING pending migration"
echo "Maturity ladder: $ML_CHECKED persona(s) checked; $ML_WARNED warning(s) (advisory; per wos/maturity-ladder.md)"
# --- Skill metadata types (ADR-0168, FAIL tier) ------------------------------
# The Agent Skills spec fixes metadata as a map from string keys to STRING values.
# The pinned skills-ref validator checks the top-level fields and never the TYPE of a
# metadata value, so 98 of 98 skills violated the spec while CI reported green. A client
# implementing the spec strictly rejects the whole install, not one skill. FAIL tier, not
# advisory: a checker either can fail the build or it leaves the lint.
SMT_SCRIPT="${SCRIPT_DIR}/check-skill-metadata-types.py"
SMT_LINE="Skill-metadata-types: skipped (checker missing)"
SMT_EXIT=0
if [[ -f "$SMT_SCRIPT" ]]; then
  SMT_OUTPUT="$(python3 "$SMT_SCRIPT" 2>&1)" || SMT_EXIT=1
  SMT_LINE="$(printf '%s\n' "$SMT_OUTPUT" | head -n1)"
fi

echo "Skills:       ${SKILLS_DRIFT_STATUS} (build-agent-skills.sh --check)"
echo "${SMT_LINE}"
echo "Closure-views: ${CLOSURE_VIEWS_STATUS} (build-closure-floor-views.py --check)"
echo "Proper-nouns: ${PROPER_NOUN_STATUS} (build-proper-noun-baseline.py --check)"
echo "Catalog:      ${CATALOG_DRIFT_STATUS} (build-command-catalog.py --check)"
echo "Wos-refs:     $WOS_REF_TOTAL topic(s) cited by commands/, $WOS_REF_MISSING missing"
echo "Registry:     $REG_TOTAL command(s), $REG_PASSED in all 3 registries, $REG_FAILED gap(s)"
echo "Indexes:      $IDX_TOTAL file(s) (ADR+scenario), $IDX_PASSED indexed, $IDX_FAILED gap(s)"
echo "Scenario refs: $SCEN_REF_TOTAL reference(s), $SCEN_REF_PASSED resolved, $SCEN_REF_FAILED broken"
echo "Counts:       $COUNT_TOTAL marker(s), $COUNT_PASSED match disk, $COUNT_FAILED stale"
echo "DoD-bullet:   ${#DOD_SCAN[@]} command(s) scanned, $DOD_FAILED on the old declarative form"
if [[ "$DS_STATUS" == "ran" ]]; then
  echo "Doc-sync:     $DSCOUNT refs verified, $DSBROKEN broken"
else
  echo "Doc-sync:     skipped (script missing)"
fi
if [[ "$DR_STATUS" == "skipped" ]]; then
  echo "Doc-renumber: skipped (script missing)"
else
  echo "Doc-renumber: ${DR_SUMMARY:-$DR_STATUS (exit $DR_EXIT)}"
fi
echo "Mirror-guard: ${MC_STATUS}"
# `grep -l` exits 1 when nothing matches, and with pipefail on that aborts the
# script. Zero frozen commands is the expected state, not an error.
LC_FROZEN=$( { grep -l 'lifecycle: frozen' "${COMMANDS_DIR}"/*.md "${COMMANDS_DIR}"/*/SKILL.md 2>/dev/null || true; } | wc -l | tr -d ' ')
echo "Lifecycle:    ${LC_FROZEN} frozen command(s), $((TOTAL - LC_FROZEN)) active (ADR-0176; absence of the field means active)"

# --- Instruction-budget advisory (W-15) -------------------------------------
# Delegates to scripts/check-instruction-budget.sh. INFORMATIONAL: warn-only,
# never flips the exit code (mirrors the natural-voice advisory tier).
IB_SCRIPT="${SCRIPT_DIR}/check-instruction-budget.sh"
if [[ -x "$IB_SCRIPT" ]]; then
  IB_LINE="$("$IB_SCRIPT" 2>/dev/null | grep -iE '^Instruction-budget:' | tail -n1 || true)"
  [[ -n "$IB_LINE" ]] && echo "$IB_LINE"
fi

# --- Doc-currency advisory (B6/B7, 2026-09-17) ------------------------------
# Delegates to scripts/check-doc-currency.sh. Any wos/*.md that cites an external
# source opts in by declaring `Last scanned:` and `Cadence:`. INFORMATIONAL: warn-only.
# Advisory on purpose. A date-triggered hard failure breaks CI on a day with no
# code change, which teaches people to bypass the gate rather than refresh the
# table. The line names the exact age and last-scan date instead.
MR_SCRIPT="${SCRIPT_DIR}/check-doc-currency.sh"
if [[ -x "$MR_SCRIPT" ]]; then
  MR_LINE="$("$MR_SCRIPT" 2>/dev/null | grep -iE '^Doc-currency:' | tail -n1 || true)"
  [[ -n "$MR_LINE" ]] && echo "$MR_LINE"
fi

# --- Skill-budget advisory (B11, 2026-09-17) --------------------------------
# Delegates to scripts/check-skill-budget.sh. INFORMATIONAL. Reports how many
# generated skills survive the host's 25,000-token combined re-attachment budget.
# Fhorja cannot change that budget, so this reports headroom rather than gating.
SB_SCRIPT="${SCRIPT_DIR}/check-skill-budget.sh"
if [[ -x "$SB_SCRIPT" ]]; then
  SB_LINE="$("$SB_SCRIPT" 2>/dev/null | grep -iE '^Skill-budget:' | tail -n1 || true)"
  [[ -n "$SB_LINE" ]] && echo "$SB_LINE"
fi

# --- Substrate-ownership advisory -------------------------------------------
# Delegates to scripts/check-substrate-ownership.py. INFORMATIONAL: warn-only,
# never flips the exit code (mirrors the instruction-budget advisory tier).
# Never pass --strict: that flag is a local measurement, not a lint gate.
# projects/ is gitignored, so CI prints "not measured" rather than "clean"
# when VERIFICATION_LOG.jsonl is absent (same "not measured" vs "clean"
# distinction as check-installed-skills-drift.sh).
SO_SCRIPT="${SCRIPT_DIR}/check-substrate-ownership.py"
if command -v python3 >/dev/null 2>&1 && [[ -f "$SO_SCRIPT" ]]; then
  SO_LINE="$(python3 "$SO_SCRIPT" 2>/dev/null | grep -iE '^Substrate-ownership:' | head -n1 || true)"
  [[ -n "$SO_LINE" ]] && echo "$SO_LINE"
fi

# --- Plan-coverage advisory -------------------------------------------------
# Delegates to scripts/check-plan-coverage.sh. INFORMATIONAL here: warn-only,
# never flips the exit code. The same script is FAIL-tier where it is called with
# one task folder, from `implementation-plan`, because a coverage defect must not
# survive the call that creates it. Here it can only measure what is on disk, and
# a task folder may be absent entirely, so it reports.
#
# projects/ is gitignored, so CI prints "not measured" rather than "clean" (the
# same distinction the substrate-ownership advisory above makes). Invoked through
# `bash` with a -f guard rather than -x, for the lost-execute-bit reason the
# bug-class advisory below spells out.
PC_SCRIPT="${SCRIPT_DIR}/check-plan-coverage.sh"
if [[ -f "$PC_SCRIPT" ]]; then
  # --root is explicit: the checker scans the caller's working directory by default
  # (ADR-0224), and the lint can be run from anywhere.
  PC_LINE="$(bash "$PC_SCRIPT" --all --advisory --root "$REPO_ROOT" 2>/dev/null | grep -iE '^Plan-coverage:' | tail -n1 || true)"
  [[ -n "$PC_LINE" ]] && echo "$PC_LINE"
fi

# --- Ladder-demand advisory (S3.3) ------------------------------------------
# Delegates to scripts/flow-audit.py --demand. INFORMATIONAL: warn-only, never
# flips the exit code (mirrors the substrate-ownership advisory tier above).
#
# Reports how many personas sit at L3 or above with zero OWNER writes, which is
# the input a demand-based demotion rule would read. It reports and decides
# nothing. The rule it feeds lives in the ladder (ADR-0181, 90 days from promotion,
# counted by owner); this line reports the input and never demotes anything.
#
# Counting is by owner, not by invoked_by. Measured 2026-08-30 the two invert
# the answer: the two L3 personas with zero owner writes have 4 and 5 writes as
# invoked_by, so counting both would report zero and the line would say nothing.
#
# projects/ is gitignored, so this prints "not measured" rather than "0" when
# the telemetry is absent, the same distinction the two advisories around it
# make. A zero read as absence of demand would accuse every persona in CI.
LD_SCRIPT="${SCRIPT_DIR}/flow-audit.py"
if command -v python3 >/dev/null 2>&1 && [[ -f "$LD_SCRIPT" ]]; then
  LD_OUT="$(python3 "$LD_SCRIPT" --demand 2>/dev/null || true)"
  if [[ -z "$LD_OUT" ]]; then
    :
  elif grep -q 'not measured' <<<"$LD_OUT"; then
    LD_TOTAL="$(grep -c 'maturity_level=L[345]' <<<"$LD_OUT" || true)"
    echo "Ladder-demand: not measured (no telemetry under projects/); ${LD_TOTAL} persona(s) at L3+ on disk (advisory)"
  else
    LD_N="$(grep -c 'owner_writes=0.*maturity_level=L[345]' <<<"$LD_OUT" || true)"
    echo "Ladder-demand: ${LD_N} persona(s) at L3+ with 0 owner write(s) (advisory; reports the input to the ADR-0181 rule, never demotes)"
  fi
fi

# --- Citation-integrity advisory --------------------------------------------
# Delegates to scripts/check-citation-integrity.py. INFORMATIONAL: warn-only,
# never flips the exit code. Distinct from check-doc-sync.sh, which answers
# "does the cited artifact exist" (and reports zero broken); this answers
# "does the cited artifact say what the citing text claims", which is the class
# the 2026-09-03 audit waves found dominating: 27 of 42 confirmed findings.
if [[ -f "${REPO_ROOT}/scripts/check-citation-integrity.py" ]]; then
  CI_OUT="$(python3 "${REPO_ROOT}/scripts/check-citation-integrity.py" 2>&1 || true)"
  CI_LINE="$(grep -E '^Citation-integrity:' <<<"$CI_OUT" || true)"
  if [[ -n "$CI_LINE" ]]; then
    echo "${CI_LINE} (advisory; existence is Doc-sync's job, this checks what the target says)"
  fi
fi

# --- Installed-skills drift advisory ----------------------------------------
# Delegates to scripts/check-installed-skills-drift.sh. INFORMATIONAL: warn-only,
# never flips the exit code (mirrors the instruction-budget advisory tier).
#
# check_advertise_stage_budget measures the REPO's descriptions. The model reads
# the INSTALLED copy under the operator's agent roots, and on 2026-08-21 those
# had diverged by 8793 chars: the repo had banked the ADR-0154/0155/0157 trim and
# the machine had not. This surfaces that gap. It reports "not measured" rather
# than "clean" where the roots are absent, which is always the case in CI.
ISD_SCRIPT="${SCRIPT_DIR}/check-installed-skills-drift.sh"
if [[ -x "$ISD_SCRIPT" ]]; then
  ISD_LINE="$("$ISD_SCRIPT" 2>/dev/null | grep -iE '^Installed-skills-drift:' | tail -n1 || true)"
  [[ -n "$ISD_LINE" ]] && echo "$ISD_LINE"
fi

# --- Claim-grounding advisory (ADR-0109, D-11) ------------------------------
# Delegates to scripts/check-claim-grounding.sh. INFORMATIONAL: warn-only,
# never flips the exit code (mirrors the instruction-budget advisory tier).
# The D-2 regression guard: flags a confidence-field pattern reintroduced into
# the doctrine's source surfaces (the claim-grounding block, the wos topic, the
# spec H3). It does NOT check referent presence in real outputs; that is
# manual-tier per the task's TEST_STRATEGY.md. See scripts/check-claim-grounding.sh.
CG_SCRIPT="${SCRIPT_DIR}/check-claim-grounding.sh"
if [[ -x "$CG_SCRIPT" ]]; then
  CG_LINE="$("$CG_SCRIPT" 2>/dev/null | grep -iE '^claim-grounding:' | tail -n1 || true)"
  [[ -n "$CG_LINE" ]] && echo "Claim-grounding: ${CG_LINE#claim-grounding: } (informational; per ADR-0109 D-2 guard)"
fi

# --- Skill-triggers advisory (W-19) -----------------------------------------
# Delegates to scripts/check-skill-triggers.sh. INFORMATIONAL: warn-only,
# never flips the exit code (mirrors the instruction-budget advisory tier).
# Reports how many skill evals carry a trigger_evals block (description
# invocation accuracy); see evals/skill-evals/README.md.
ST_SCRIPT="${SCRIPT_DIR}/check-skill-triggers.sh"
if [[ -x "$ST_SCRIPT" ]]; then
  ST_LINE="$("$ST_SCRIPT" 2>/dev/null | grep -iE '^Skill-triggers:' | tail -n1 || true)"
  [[ -n "$ST_LINE" ]] && echo "$ST_LINE"
fi

# --- Flow-orphans advisory (command-graph interconnection) ------------------
# Delegates to scripts/flow-audit.py --orphans-brief. INFORMATIONAL: warn-only,
# never flips the exit code (mirrors the skill-triggers advisory tier). Reports
# commands with zero inbound references in the command graph (only reachable if
# you already know they exist). A missing python3 degrades to a skipped advisory,
# never a lint failure. See scripts/flow-audit.py and the 2026-07-11 flow audit.
FA_SCRIPT="${SCRIPT_DIR}/flow-audit.py"
if command -v python3 >/dev/null 2>&1 && [[ -f "$FA_SCRIPT" ]]; then
  FA_OUT="$(python3 "$FA_SCRIPT" --orphans-brief 2>/dev/null || true)"
  FA_HEAD="$(printf '%s\n' "$FA_OUT" | grep -iE '^orphan-edge advisory:' | tail -n1 || true)"
  if [[ -n "$FA_HEAD" ]]; then
    FA_ZERO="$(printf '%s' "$FA_HEAD" | grep -oE '[0-9]+ command\(s\) with 0 inbound' | grep -oE '^[0-9]+' || echo '?')"
    echo "Flow-orphans: ${FA_ZERO} command(s) with 0 inbound reference(s) in the command graph (informational; per scripts/flow-audit.py)"
    # Second static line: names exempt from the never-invoked metric that are still
    # unreachable in the graph. Exempt is not the same as reachable, and without this
    # line a command can be both invisible to the usage signal and unreachable, which
    # is exactly how one goes missing. Advisory like the line above; never fails.
    FA_EX="$(printf '%s\n' "$FA_OUT" | grep -iE '^exemption audit:' | tail -n1 || true)"
    if [[ -n "$FA_EX" ]]; then
      FA_REVIEW="$(printf '%s' "$FA_EX" | grep -oE '[0-9]+ name\(s\) with indegree' | grep -oE '^[0-9]+' || echo '?')"
      FA_GONE="$(printf '%s' "$FA_EX" | grep -oE '[0-9]+ name\(s\) not on disk' | grep -oE '^[0-9]+' || echo '?')"
      echo "Flow-exemptions: ${FA_REVIEW} with indegree <= 1, ${FA_GONE} not on disk (informational)"
    fi
    if [[ $VERBOSE -eq 1 ]] || [[ $STRICT -eq 1 ]]; then
      printf '%s\n' "$FA_OUT" | sed -n '2,$p' | sed 's/^/  /'
    fi
  fi
fi

# --- Bug-class schema advisory (template shape) -----------------------------
# Delegates to scripts/validate-bug-class-schema.sh. INFORMATIONAL: warn-only,
# never flips the exit code (mirrors the flow-orphans advisory tier above).
# Reports templates missing any of the 7 required sections, or carrying an empty
# `## Retrieval` / `## Analysis prompt` (the two repo-consistency-sweep Step 5
# reads to build its dispatch, so an empty one is dispatchable and silently
# useless). A missing validator degrades to a skipped advisory, never a lint
# failure. See scripts/validate-bug-class-schema.sh.
#
# Guards on -f and invokes through `bash`, not -x with a direct call: this
# repository has lost execute bits before (commit 8912dfb, "restore +x on the
# three files every mirror flattens"), and under -x that loss would delete this
# advisory from the lint output without a word. The sibling above guards the
# same way for the same reason. One invocation with --verbose feeds both the
# summary line and the detail, so the two cannot disagree and the catalog is
# scanned once rather than twice.
BCS_SCRIPT="${SCRIPT_DIR}/validate-bug-class-schema.sh"
if [[ -f "$BCS_SCRIPT" ]]; then
  BCS_OUT="$(bash "$BCS_SCRIPT" --verbose 2>/dev/null || true)"
  BCS_HEAD="$(printf '%s\n' "$BCS_OUT" | grep -iE '^BUG-CLASS-SCHEMA:' | tail -n1 || true)"
  if [[ -n "$BCS_HEAD" ]]; then
    echo "Bug-class-schema: ${BCS_HEAD#BUG-CLASS-SCHEMA: } (informational; per scripts/validate-bug-class-schema.sh)"
    if [[ $VERBOSE -eq 1 ]] || [[ $STRICT -eq 1 ]]; then
      printf '%s\n' "$BCS_OUT" | grep -v '^BUG-CLASS-SCHEMA:' | sed 's/^/  /' || true
    fi
  fi
fi

echo "================================================================================"

if [[ $FAILED -gt 0 ]]; then
  echo ""
  echo "Failed commands:"
  for cmd in "${FAILURES[@]}"; do
    echo "  - $cmd"
  done
  exit 1
fi

if [[ $SHARED_FAILED -gt 0 ]]; then
  echo ""
  echo "Shared-block drift:"
  for failure in "${SHARED_FAILURES[@]}"; do
    echo "  - $failure"
  done
  echo ""
  echo "Run ./scripts/sync-shared-blocks.sh to repropagate the canonical content from commands/_shared/."
  exit 1
fi

if [[ $FM_FAILED -gt 0 ]]; then
  echo ""
  echo "Frontmatter failures:"
  for cmd in "${FM_FAILURES[@]}"; do
    echo "  - $cmd"
  done
  exit 1
fi

if [[ $FM_MISSING -gt 0 ]] && { [[ $VERBOSE -eq 1 ]] || [[ $STRICT -eq 1 ]]; }; then
  echo ""
  echo "Commands pending frontmatter migration ($FM_MISSING / $FM_TOTAL):"
  for cmd in "${FM_MISSING_CMDS[@]}"; do
    echo "  - $cmd"
  done
  if [[ $STRICT -eq 1 ]]; then
    echo "Strict mode: missing frontmatter treated as error during P11 rollout."
    exit 1
  fi
fi

if [[ "$SKILLS_DRIFT_STATUS" == "drifted" ]]; then
  echo ""
  echo "Skills drift detected (.claude/skills/ does not match commands/):"
  printf '%s\n' "$SKILLS_DRIFT_OUTPUT" | sed 's/^/  /'
  echo ""
  echo "Run ./scripts/build-agent-skills.sh to regenerate from canonical commands/."
  exit 1
fi

if [[ "$PROPER_NOUN_STATUS" == "new-names" ]]; then
  echo ""
  echo "Compound proper noun(s) new to the tree (mirror-guard complement):"
  printf '%s\n' "$PROPER_NOUN_OUTPUT" | sed 's/^/  /'
  exit 1
fi

if [[ "$CLOSURE_VIEWS_STATUS" == "drifted" ]]; then
  echo ""
  echo "Closure-floor view drift (wos/closure-floors.<consumer>.md does not match the canonical file):"
  printf '%s\n' "$CLOSURE_VIEWS_OUTPUT" | sed 's/^/  /'
  echo ""
  echo "Run python3 scripts/build-closure-floor-views.py to regenerate from wos/closure-floors.md."
  exit 1
fi

if [[ "$CATALOG_DRIFT_STATUS" == "drifted" ]]; then
  echo ""
  echo "Command-catalog drift detected (docs/command-catalog.html or docs/command-catalog.json out of sync):"
  printf '%s\n' "$CATALOG_DRIFT_OUTPUT" | sed 's/^/  /'
  echo ""
  echo "Run python3 ./scripts/build-command-catalog.py to regenerate from canonical commands/."
  exit 1
fi

if [[ $REG_FAILED -gt 0 ]]; then
  echo ""
  echo "Registry membership failures (ADR-0029):"
  for failure in "${REG_FAILURES[@]}"; do
    echo "  - $failure"
  done
  echo ""
  echo "Every command must appear in: a spec '### <cluster>' bullet, wos/command-roles.md, and the COMMAND_PROMPT_STUBS.md table. Per-command Role and Next left the spec in ADR-0165."
  exit 1
fi

if [[ $COUNT_FAILED -gt 0 ]]; then
  echo ""
  echo "Count-marker drift (ADR-0029):"
  for failure in "${COUNT_FAILURES[@]}"; do
    echo "  - $failure"
  done
  echo ""
  echo "Update the number inside the <!-- count:KIND -->N<!-- /count --> marker to match the on-disk count."
  exit 1
fi

if [[ $DOD_FAILED -gt 0 ]]; then
  echo ""
  echo "Definition-of-done bullet drift (ADR-0056 follow-up): the closing DoD bullet must be the imperative self-verify form:"
  for failure in "${DOD_FAILURES[@]}"; do
    echo "  - $failure"
  done
  echo ""
  echo "Replace it with: '- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.'"
  exit 1
fi

if [[ $IDX_FAILED -gt 0 ]]; then
  echo ""
  echo "Index-row membership failures (ADR-0029):"
  for failure in "${IDX_FAILURES[@]}"; do
    echo "  - $failure"
  done
  echo ""
  echo "Every ADR file needs a row in docs/adr/README.md; every eval scenario needs a row in evals/README.md."
  exit 1
fi

if [[ $SCEN_REF_FAILED -gt 0 ]]; then
  echo ""
  echo "Scenario inner-reference drift ($SCEN_REF_FAILED broken):"
  for failure in "${SCEN_REF_FAILURES[@]}"; do
    echo "  - $failure"
  done
  echo ""
  echo "Fix the reference to point at the real file, or add an inline <!-- lint:skip --> to the line if the missing target is deliberate (e.g. a scenario documenting detection of a bogus name)."
  exit 1
fi

if [[ "$DS_STATUS" == "ran" ]] && (( DSBROKEN > 0 )); then
  echo ""
  echo "Doc-sync broken references ($DSBROKEN):"
  printf '%s\n' "$DS_OUTPUT" | sed 's/^/  /'
  echo ""
  echo "Run ./scripts/check-doc-sync.sh to inspect the failing references and fix the targets."
  exit 1
fi

if [[ "$DR_STATUS" == "broken" ]] && (( DR_EXIT == 1 )); then
  echo ""
  echo "Stale references to a heading or path this change removed or renumbered (ADR-0225):"
  printf '%s\n' "$DR_OUTPUT" | sed 's/^/  /'
  echo ""
  echo "Update each citing line in the same change, or keep the heading's number and text. Run ./scripts/check-doc-sync.sh --against HEAD to re-check."
  exit 1
fi

if (( MC_MISSING == 1 )); then
  echo ""
  echo "Mirror-codename guard is missing: scripts/check-mirror-codenames.sh"
  echo "That script is tracked, so its absence means the tree is broken or the check was removed."
  echo "A leak guard that cannot run must not report green. Restore it: git checkout -- scripts/check-mirror-codenames.sh"
  exit 1
fi

# The guard's output is NEVER reproduced here, and not by redaction either.
# Redacting it by pattern was tried and leaked three ways: the codename also
# lives in file PATHS (the historical `client__client-be` slug form), any LEAK
# line the pattern did not anticipate passed through raw, and a colon in a file
# name broke the line filter. The lint cannot sanitise output whose format it
# does not own, so it reproduces none of it and routes the operator to the guard,
# which they run by hand with the sidecar already in reach. MC_OUTPUT is captured
# above solely to keep the guard's stdout out of this log; it is never printed.
if (( SMT_EXIT == 1 )); then
  echo ""
  echo "Skill metadata carries a non-string value (ADR-0168)."
  printf '%s\n' "$SMT_OUTPUT" | tail -n +2
  echo "The Agent Skills spec fixes metadata as a map from string keys to STRING values, and a client"
  echo "that implements it strictly rejects the whole install, not one skill. The pinned skills-ref"
  echo "validator never checks the type of a metadata value, which is why this guard exists."
  echo "Fix: never edit .claude/skills by hand. Change commands/<name>.md and run ./scripts/build-agent-skills.sh."
  exit 1
fi

if (( MC_EXIT == 1 )); then
  echo ""
  echo "Mirror-codename leak detected in the tracked tree."
  echo "Details are deliberately not printed here: they name the private codename, and this runs on every lint."
  echo "See what and where:  scripts/check-mirror-codenames.sh ."
  echo "Then replace the codename with a synthetic token (e.g. 'Acme') in the versioned file, or drop the absolute path. The sidecar scripts/.mirror-codenames stays gitignored and out of the mirror."
  echo "An engagement-provenance hit is fixed by rewriting the sentence to describe the work, not whose work it was; the workflow telemetry (agent counts, tokens, wall-clock) stays."
  exit 1
fi

if (( WOS_REF_MISSING > 0 )); then
  echo ""
  echo "Missing wos topic(s) cited by commands/:${WOS_REF_LIST}"
  echo "A command citing a topic that does not exist fails its own load, and several of those"
  echo "loads are declared MANDATORY, so the failure is silent at the point it matters."
  echo "Fix: restore the topic, or update the citing command to the topic's new name."
  exit 1
fi

# Maturity ladder warnings (K.6). INFORMATIONAL in v2.1: never increments
# FAILED, never exits non-zero. Promotion to fail-fast is post-v2.1.
if [[ $ML_WARNED -gt 0 ]] && { [[ $VERBOSE -eq 1 ]] || [[ $STRICT -eq 1 ]]; }; then
  echo ""
  echo "Maturity-ladder shape warnings ($ML_WARNED across $ML_CHECKED persona(s) checked):"
  for w in "${MATURITY_WARNINGS[@]}"; do
    echo "  - $w"
  done
fi

# --- Orchestrator contract (fleet dispatch) ---------------------------------
# FAIL tier. Three invariants about how a command dispatches sub-agents, each
# one a claim about the platform that was measured false in this tree:
#
#   1. A command mandating `StructuredOutput` must name the workflow path.
#      That tool exists only inside the dynamic-workflow runtime, where the
#      SCRIPT declares the shape via `agent(prompt, {schema})`. The `Agent` tool
#      takes no schema, so a command that mandates the tool while naming only
#      the `Agent` path is instructing a worker to call something it does not
#      have. Three fleet commands did exactly that, and the consequence is on
#      disk: 27 `.md` worker returns under .wos/fleet-inbox/, the shape ADR-0038
#      declared FORBIDDEN, written 6 to 21 days after it was forbidden.
#
#   2. `max_fanout` must not exceed 20. Claude Code documents that the 21st
#      concurrent sub-agent fails with `Concurrent subagent limit reached` and
#      that the error tells the model not to retry. Three commands declared 20,
#      which is the limit itself with no headroom for a retry, and the shared
#      bootstrap declared an absolute ceiling of 100.
#
#   3. An `orchestrator: true` command must name the agent type it dispatches.
#      Fork mode is on by default in an interactive session, and a fork inherits
#      the whole conversation, dropping the input isolation the orchestrator is
#      relying on. Three fleet commands named no type at all.
ORCH_FAILURES=()
# Each check scans the surface its invariant lives on, and no wider. Scanning
# wos/ with the agent-type check reddened wos/sub-agent-orchestration.md for
# containing the string `orchestrator: true` while DESCRIBING the frontmatter
# key, which is the same describe-versus-mandate false positive that got a third
# check dropped from this block. The ceiling check runs over wos/ separately,
# below, because that claim genuinely lived in two files and only one was fixed
# on the first pass.
for file in "${COMMAND_FILES[@]}" "${REPO_ROOT}"/commands/_shared/*.md; do
  [[ -f "$file" ]] || continue
  oc_name="$(basename "${file%.md}")"
  [[ "$file" == */SKILL.md ]] && oc_name="$(basename "$(dirname "$file")")"

  # NOT CHECKED HERE: "a command mandating StructuredOutput must name the
  # workflow path". The doctrine fix landed in the command files, but the check
  # did not, and the reason is worth keeping. A file-wide test passed on an
  # incidental mention 67 lines away in a historical ADR note. Narrowing it to
  # the same line then reddened 7 files, because `StructuredOutput` also appears
  # in Definition-of-done bullets and convergence steps that describe the payload
  # rather than instruct a worker to call the tool. Separating a mandate from a
  # description is a prose-shape heuristic, and both of its failure modes were
  # demonstrated within ten minutes of each other. Two exact checks beat three
  # with one that misfires; a gate that cries wolf teaches its reader to skip the
  # output. The invariant stands in commands/_shared/worker-contract.md as prose,
  # which does not bind, and that is stated rather than papered over.

  # Two shapes: the frontmatter declaration, and the prose ceiling that governs
  # what a command may declare. Both carry the same claim about the platform.
  while IFS= read -r mf; do
    if [[ "$mf" =~ ^[[:space:]]*max_fanout:[[:space:]]*([0-9]+) ]] && (( BASH_REMATCH[1] > 20 )); then
      ORCH_FAILURES+=("${oc_name}: max_fanout ${BASH_REMATCH[1]} exceeds the platform's 20-concurrent limit, which fails closed and instructs no retry")
    fi
  done < <(grep -E '^[[:space:]]*max_fanout:[[:space:]]*[0-9]+' "$file" || true)

  while IFS= read -r cl; do
    if [[ "$cl" =~ ceiling[[:space:]]+([0-9]+) ]] && (( BASH_REMATCH[1] > 20 )); then
      ORCH_FAILURES+=("${oc_name}: states a max_fanout ceiling of ${BASH_REMATCH[1]}, above the platform's 20-concurrent limit")
    fi
  done < <(grep -iE 'max_fanout.*ceiling[[:space:]]+[0-9]+' "$file" || true)

  if grep -qE '^[[:space:]]*orchestrator:[[:space:]]*true' "$file" \
     && ! grep -qE 'subagent_type|agentType' "$file"; then
    ORCH_FAILURES+=("${oc_name}: declares orchestrator: true but never names an agent type (a fork inherits the whole conversation and drops sub-agent input isolation)")
  fi
done

# The prose ceiling claim, over the reference topics as well. A wos/ topic states
# what a command MAY declare, so a stale ceiling there outlives every command fix.
for file in "${REPO_ROOT}"/wos/*.md; do
  [[ -f "$file" ]] || continue
  wc_name="$(basename "${file%.md}")"
  while IFS= read -r cl; do
    if [[ "$cl" =~ ceiling[[:space:]]+([0-9]+) ]] && (( BASH_REMATCH[1] > 20 )); then
      ORCH_FAILURES+=("wos/${wc_name}: states a max_fanout ceiling of ${BASH_REMATCH[1]}, above the platform's 20-concurrent limit")
    fi
  done < <(grep -iE 'max_fanout.*ceiling[[:space:]]+[0-9]+' "$file" || true)
done

if [[ ${#ORCH_FAILURES[@]} -gt 0 ]]; then
  echo ""
  echo "Orchestrator-contract failures (${#ORCH_FAILURES[@]}):"
  for failure in "${ORCH_FAILURES[@]}"; do
    echo "  - $failure"
  done
  echo ""
  echo "See commands/_shared/worker-contract.md and commands/_shared/orchestrator-bootstrap.md."
  exit 1
fi

if [[ $STRICT -eq 1 ]] && [[ $((WARNED + ROOT_WARNED)) -gt 0 ]]; then
  echo "Strict mode: warnings present, exiting non-zero."
  exit 1
fi

exit 0
