#!/usr/bin/env bash
# lint-commands.sh
#
# Validates that each command file under commands/*.md follows the contract
# defined in WORKFLOW_OPERATING_SYSTEM.md (Standard command output layout,
# Definition of done, etc.). Also runs two doc-drift guards (ADR-0029):
# registry membership (every command in all 4 registries, no orphan entries)
# and count markers (<!-- count:KIND -->N<!-- /count --> must equal disk).
#
# Exit codes:
#   0 = all checks pass
#   1 = a command, shared block, frontmatter, skill, registry, or count failed
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

  # Cache-breakpoint marker validation (ADR-0014). Required: exactly one marker;
  # must appear AFTER the `### Definition of done (command output)` line.
  cb_count="$(grep -cE '^<!-- cache-breakpoint -->$' "$file" || true)"
  if [[ "$cb_count" == "0" ]]; then
    file_failures+=("missing: <!-- cache-breakpoint --> marker (ADR-0014)")
  elif [[ "$cb_count" -gt "1" ]]; then
    file_failures+=("cache-breakpoint marker appears $cb_count times (must be exactly one; ADR-0014)")
  else
    dod_line=$(grep -nE '^### Definition of done \(command output\)$' "$file" | head -1 | cut -d: -f1)
    cb_line=$(grep -nE '^<!-- cache-breakpoint -->$' "$file" | head -1 | cut -d: -f1)
    if [[ -n "$dod_line" ]] && [[ -n "$cb_line" ]] && (( cb_line < dod_line )); then
      file_failures+=("cache-breakpoint marker (line $cb_line) appears BEFORE '### Definition of done' (line $dod_line); per ADR-0014 the marker is the last non-blank line of the body")
    fi
  fi

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
  "state-and-navigation"
  "discovery-and-scoping"
  "database-context"
  "contract-and-decision-hardening"
  "planning-and-validation"
  "execution-and-closure"
  "delivery-and-communication"
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
VALID_TOOLS=(Read Write Edit Bash Glob Grep WebFetch WebSearch Task)
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
TB_WARNED=0
TB_WARNINGS=()

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

  # Per-command token budget (ADR-0013). Required positive integer >= 100.
  # Current command-file token cost is recomputed from file size and compared
  # against the declared budget; overruns emit a warning (not a failure).
  fm_token_budget="$(printf '%s\n' "$fm_block" | awk '/^  token-budget: / { sub(/^  token-budget: /, ""); print; exit }')"
  if [[ -z "$fm_token_budget" ]]; then
    fm_failures+=("frontmatter: missing required field 'metadata.token-budget' (ADR-0013)")
  elif ! [[ "$fm_token_budget" =~ ^[0-9]+$ ]]; then
    fm_failures+=("frontmatter: token-budget '$fm_token_budget' is not a non-negative integer")
  elif (( fm_token_budget < 100 )); then
    fm_failures+=("frontmatter: token-budget '$fm_token_budget' is below the floor of 100")
  else
    # Compute current token cost (chars / 4, same approximation as measure-tokens.py).
    current_chars=$(wc -c < "$file")
    current_tokens=$(( (current_chars + 2) / 4 ))
    if (( current_tokens > fm_token_budget )); then
      TB_WARNED=$((TB_WARNED + 1))
      TB_WARNINGS+=("${command_name}: current ~${current_tokens} > budget ${fm_token_budget}")
      if [[ $VERBOSE -eq 1 ]] || [[ $STRICT -eq 1 ]]; then
        echo "WARN (token-budget): ${command_name} current ~${current_tokens} > budget ${fm_token_budget}"
      fi
    fi
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

# --- Command-catalog drift check (ADR-0005) ---------------------------------
# docs/command-catalog.html and the README "## Command catalog" section are
# GENERATED from commands/*.md by build-command-catalog.py. Drift is a FAIL: the
# catalog is the offline / multi-tool command reference and must not desync from
# the canonical command files. Skipped (with a note) when the generator is absent.
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
  # Forward: each command present in all four registries.
  for file in "${COMMAND_FILES[@]}"; do
    cmd="$(canonical_name_from_path "$file")"
    REG_TOTAL=$((REG_TOTAL + 1))
    reg_missing=""
    grep -qE "^### ${cmd}\$" "$WOS_FILE"                || reg_missing="${reg_missing} spec-roles-index"
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

  # Reverse: the spec Command roles index entries map to real commands.
  while IFS= read -r name; do
    [[ -z "$name" ]] && continue
    if [[ ! -f "${COMMANDS_DIR}/${name}.md" && ! -f "${COMMANDS_DIR}/${name}/SKILL.md" ]]; then
      REG_FAILED=$((REG_FAILED + 1))
      REG_FAILURES+=("orphan entry: the spec Command roles '### ${name}' has no commands/${name}.md (flat) or commands/${name}/SKILL.md (folder-shaped)")
    fi
  done < <(awk '/^## Command roles/{f=1;next} /^## /{if(f)f=0} f && /^### [a-z][a-z-]+$/{sub(/^### /,"");print}' "$WOS_FILE")

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

COUNT_SCAN_FILES=()
for rf in "${ROOT_DOC_FILES[@]}"; do COUNT_SCAN_FILES+=("${REPO_ROOT}/${rf}"); done
for wf in "${REPO_ROOT}"/wos/*.md; do COUNT_SCAN_FILES+=("$wf"); done
COUNT_SCAN_FILES+=("${REPO_ROOT}/docs/FAQ.md" "${REPO_ROOT}/docs/MIGRATION.md" "${REPO_ROOT}/docs/adr/README.md" "${REPO_ROOT}/evals/README.md")

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

# --- Natural-voice advisory -------------------------------------------------
# Delegates to scripts/check-natural-voice.sh. INFORMATIONAL: never increments
# FAILED and never flips the exit code (mirrors the maturity-ladder model).
# Surfaces AI-tell hits (slash and/or, not-just-X parallelism, vocab cliches,
# emoji) on the summary line; detail under --verbose/--strict. The em-dash hard
# block stays in FORBIDDEN_PATTERNS above; this is the advisory tier.
NV_SCRIPT="${SCRIPT_DIR}/check-natural-voice.sh"
NV_HITS=0
NV_FILES=0
NV_STATUS="skipped"
NV_OUTPUT=""
if [[ -x "$NV_SCRIPT" ]]; then
  # Explicit branches instead of an args array: macOS bash 3.2 errors on empty
  # array expansion (`"${arr[@]}"`) under `set -u`.
  set +e
  if [[ $VERBOSE -eq 1 && $STRICT -eq 1 ]]; then
    NV_OUTPUT="$("$NV_SCRIPT" --verbose --strict 2>&1)"
  elif [[ $VERBOSE -eq 1 ]]; then
    NV_OUTPUT="$("$NV_SCRIPT" --verbose 2>&1)"
  elif [[ $STRICT -eq 1 ]]; then
    NV_OUTPUT="$("$NV_SCRIPT" --strict 2>&1)"
  else
    NV_OUTPUT="$("$NV_SCRIPT" 2>&1)"
  fi
  set -e
  nv_summary_line="$(printf '%s\n' "$NV_OUTPUT" | grep -iE '^natural-voice: [0-9]+ advisory hit' | tail -n1 || true)"
  if [[ -n "$nv_summary_line" ]]; then
    NV_HITS="$(printf '%s' "$nv_summary_line" | sed -E 's/^[Nn]atural-voice: ([0-9]+) advisory hit\(s\) across ([0-9]+) file\(s\).*/\1/')"
    NV_FILES="$(printf '%s' "$nv_summary_line" | sed -E 's/^[Nn]atural-voice: ([0-9]+) advisory hit\(s\) across ([0-9]+) file\(s\).*/\2/')"
    NV_STATUS="ran"
  else
    NV_STATUS="ran"
  fi
elif [[ -f "$NV_SCRIPT" ]]; then
  NV_STATUS="skipped (not executable)"
fi

echo ""
echo "================================================================================"
echo "Lint summary: $TOTAL command(s), $PASSED passed, $FAILED failed, $WARNED warned"
echo "Root docs:    $ROOT_TOTAL file(s) scanned for forbidden bytes, $ROOT_WARNED warned"
echo "Shared:       $SHARED_TOTAL marker(s), $SHARED_PASSED matched canonical, $SHARED_FAILED drifted"
echo "Frontmatter:  $FM_TOTAL command(s), $FM_PRESENT with frontmatter ($FM_PASSED passed, $FM_FAILED failed), $FM_MISSING pending migration"
echo "Token budget: $TB_WARNED command(s) over declared budget (warning only; per ADR-0013)"
echo "Maturity ladder: $ML_CHECKED persona(s) checked; $ML_WARNED warning(s) (per wos/maturity-ladder.md)"
echo "Skills:       ${SKILLS_DRIFT_STATUS} (build-agent-skills.sh --check)"
echo "Catalog:      ${CATALOG_DRIFT_STATUS} (build-command-catalog.py --check)"
echo "Registry:     $REG_TOTAL command(s), $REG_PASSED in all 4 registries, $REG_FAILED gap(s)"
echo "Indexes:      $IDX_TOTAL file(s) (ADR+scenario), $IDX_PASSED indexed, $IDX_FAILED gap(s)"
echo "Scenario refs: $SCEN_REF_TOTAL reference(s), $SCEN_REF_PASSED resolved, $SCEN_REF_FAILED broken"
echo "Counts:       $COUNT_TOTAL marker(s), $COUNT_PASSED match disk, $COUNT_FAILED stale"
echo "DoD-bullet:   ${#DOD_SCAN[@]} command(s) scanned, $DOD_FAILED on the old declarative form"
if [[ "$DS_STATUS" == "ran" ]]; then
  echo "Doc-sync:     $DSCOUNT refs verified, $DSBROKEN broken"
else
  echo "Doc-sync:     skipped (script missing)"
fi
if [[ "$NV_STATUS" == "ran" ]]; then
  echo "Natural-voice: $NV_HITS advisory hit(s) across $NV_FILES file(s) (informational; per wos/natural-voice.md)"
else
  echo "Natural-voice: $NV_STATUS"
fi

# --- Instruction-budget advisory (W-15) -------------------------------------
# Delegates to scripts/check-instruction-budget.sh. INFORMATIONAL: warn-only,
# never flips the exit code (mirrors the natural-voice advisory tier).
IB_SCRIPT="${SCRIPT_DIR}/check-instruction-budget.sh"
if [[ -x "$IB_SCRIPT" ]]; then
  IB_LINE="$("$IB_SCRIPT" 2>/dev/null | grep -iE '^Instruction-budget:' | tail -n1 || true)"
  [[ -n "$IB_LINE" ]] && echo "$IB_LINE"
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

# --- NEEDS CLARIFICATION marker count (informational; non-blocking) --------
# Per wos/cross-cutting-workflow-guardrails.md NEEDS CLARIFICATION inline marker.
# Greps every .md file under projects/*/active/*/ for the literal marker prefix.
# Reports per task folder; total is informational only (not a lint failure).
NC_TOTAL=0
NC_TASKS_WITH_MARKERS=0
declare -a NC_DETAILS
if [[ -d "${REPO_ROOT}/projects" ]]; then
  while IFS= read -r task_dir; do
    [[ -z "$task_dir" ]] && continue
    count=$(grep -rE -c '\[NEEDS CLARIFICATION:' "$task_dir" 2>/dev/null | awk -F: '{ s += $2 } END { print s+0 }' || true)
    count="${count:-0}"
    if [[ "$count" -gt 0 ]] 2>/dev/null; then
      NC_TOTAL=$((NC_TOTAL + count))
      NC_TASKS_WITH_MARKERS=$((NC_TASKS_WITH_MARKERS + 1))
      rel_path="${task_dir#${REPO_ROOT}/}"
      NC_DETAILS+=("$rel_path: $count")
    fi
  done < <(find "${REPO_ROOT}/projects" -mindepth 3 -maxdepth 3 -type d -path '*/active/*' 2>/dev/null || true)
fi
echo "Clarify:      $NC_TOTAL [NEEDS CLARIFICATION:] marker(s) across $NC_TASKS_WITH_MARKERS active task folder(s) (informational)"
echo "================================================================================"

if [[ $NC_TOTAL -gt 0 ]] && { [[ $VERBOSE -eq 1 ]] || [[ $STRICT -eq 1 ]]; }; then
  echo ""
  echo "NEEDS CLARIFICATION markers (informational):"
  for d in "${NC_DETAILS[@]}"; do
    echo "  - $d"
  done
fi

# Natural-voice advisory detail (informational; never flips the exit code).
if [[ "$NV_STATUS" == "ran" ]] && [[ "$NV_HITS" -gt 0 ]] 2>/dev/null && { [[ $VERBOSE -eq 1 ]] || [[ $STRICT -eq 1 ]]; }; then
  echo ""
  printf '%s\n' "$NV_OUTPUT"
fi

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

if [[ "$CATALOG_DRIFT_STATUS" == "drifted" ]]; then
  echo ""
  echo "Command-catalog drift detected (docs/command-catalog.html or README ## Command catalog out of sync):"
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
  echo "Every command must appear in: a spec '### <cluster>' bullet, the spec '## Command roles' index, wos/command-roles.md, and the COMMAND_PROMPT_STUBS.md table."
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

if [[ $TB_WARNED -gt 0 ]] && { [[ $VERBOSE -eq 1 ]] || [[ $STRICT -eq 1 ]]; }; then
  echo ""
  echo "Token-budget overruns ($TB_WARNED command(s)):"
  for w in "${TB_WARNINGS[@]}"; do
    echo "  - $w"
  done
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

if [[ $STRICT -eq 1 ]] && [[ $((WARNED + ROOT_WARNED + TB_WARNED)) -gt 0 ]]; then
  echo "Strict mode: warnings present, exiting non-zero."
  exit 1
fi

exit 0
