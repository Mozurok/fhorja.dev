#!/usr/bin/env bash
# Sync workflow command markdown files to Cursor, Claude Code, Codex, and Kimi Code CLI directories.
# Source: <repo>/commands/*.md  →  same filenames (e.g. task-init.md → /task-init in Claude Code).
#
# Run it bare on a terminal for a guided wizard; pass any flag (or run in CI / a
# pipe) for the scriptable non-interactive path. Skills sync by default; use
# --no-skills to opt out.
#
# Defaults:
#   Cursor (legacy slash):  ~/.cursor/commands
#   Claude  (legacy slash):  ~/.claude/commands
#   Codex  (custom prompts): ~/.codex/prompts (invoked as /prompts:<name>)
#   Kimi   (skills only):    no custom-command directory exists; see the Kimi note below
#   Skills (open standard): ~/.claude/skills and ~/.agents/skills (ON by default).
#                           Cursor 3.17.8 or later reads ~/.agents/skills natively, so
#                           ~/.cursor/skills is written only under --cursor-skills (ADR-0228).
#
# Docs:
#   Cursor: project .cursor/commands or user commands (this script targets the user dir by default).
#   Claude Code: https://code.claude.com/docs/en/skills (custom commands under .claude/commands/)
#   Codex CLI: https://developers.openai.com/codex/custom-prompts
#              Custom prompts are deprecated; prefer skills for reusable workflows.
#              https://developers.openai.com/codex/skills
#   Kimi Code CLI: https://www.kimi.com/code/docs/en/kimi-code-cli/customization/skills.html
#                  https://www.kimi.com/code/docs/en/kimi-code-cli/configuration/data-locations.html
#   Agent Skills (open standard): https://agentskills.io/specification
#
# Kimi note: Kimi Code CLI has no user-defined slash-command directory. Its entire
# customization surface is Agent Skills, invoked as /skill:<name>. At user level it
# scans $KIMI_CODE_HOME/skills (default ~/.kimi-code/skills) AND the generic
# ~/.agents/skills, so this script targets the generic directory by default: it is
# already written for Codex, both tools read it, and a second copy under the Kimi
# brand directory would register every skill twice. Point --kimi-dir at
# ~/.kimi-code/skills if you want a Kimi-owned copy instead.
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
SRC="${REPO_ROOT}/commands"
SKILLS_SRC="${REPO_ROOT}/.claude/skills"

CURSOR_DEST="${CURSOR_COMMANDS_DIR:-${HOME}/.cursor/commands}"
CLAUDE_DEST="${CLAUDE_COMMANDS_DIR:-${HOME}/.claude/commands}"
CODEX_DEST="${CODEX_PROMPTS_DIR:-${HOME}/.codex/prompts}"

CLAUDE_SKILLS_DEST="${CLAUDE_SKILLS_DIR:-${HOME}/.claude/skills}"
CURSOR_SKILLS_DEST="${CURSOR_SKILLS_DIR:-${HOME}/.cursor/skills}"
CODEX_SKILLS_DEST="${CODEX_SKILLS_DIR:-${HOME}/.agents/skills}"
# The root Cursor reads by default is the shared ~/.agents/skills, the same one Codex
# and Kimi read, so it follows CODEX_SKILLS_DIR rather than having a variable of its own.
# Cursor loads it natively from 3.17.8 (older builds did not inject it). Writing
# ~/.cursor/skills as well made Cursor list every Fhorja skill twice, so that root is now
# opt-in through --cursor-skills, which Cursor Cloud Agents sync needs because only
# ~/.cursor/skills syncs there (ADR-0228). CURSOR_SKILLS_DIR moves that opt-in root.
CURSOR_SHARED_SKILLS_DEST="$CODEX_SKILLS_DEST"
DEFAULT_CODEX_SKILLS_DEST="${HOME}/.agents/skills"
LEGACY_CODEX_SKILLS_DEST="${HOME}/.codex/skills"

# Kimi's home directory carries two names in the wild: the current Kimi Code CLI
# uses ~/.kimi-code (relocatable via KIMI_CODE_HOME), while the older open-source
# kimi-cli uses ~/.kimi. Detect whichever is actually installed instead of
# guessing, and fall back to the current one when neither exists yet.
resolve_kimi_home() {
  if [[ -n "${KIMI_CODE_HOME:-}" ]]; then printf '%s' "${KIMI_CODE_HOME%/}"; return 0; fi
  if [[ -d "${HOME}/.kimi-code" ]]; then printf '%s' "${HOME}/.kimi-code"; return 0; fi
  if [[ -d "${HOME}/.kimi" ]]; then printf '%s' "${HOME}/.kimi"; return 0; fi
  printf '%s' "${HOME}/.kimi-code"
}
KIMI_HOME="$(resolve_kimi_home)"
# Project-level skills live under the same brand directory name Kimi uses at home
# (.kimi-code/skills or .kimi/skills), so derive it rather than hardcoding one.
KIMI_BRAND_DIRNAME="$(basename "$KIMI_HOME")"
# Default to the generic cross-tool directory Kimi scans natively. See the Kimi
# note in the header for why this is not the brand-owned ~/.kimi-code/skills.
KIMI_SKILLS_DEST="${KIMI_SKILLS_DIR:-${HOME}/.agents/skills}"

DRY_RUN=0
DO_CURSOR=1
DO_CLAUDE=1
DO_CODEX=1
DO_KIMI=1
ONLY_MODE=0
WITH_DOCS=0
WITH_SKILLS=1          # skills ON by default (opt out with --no-skills)
DO_CLEAN_ORPHANS=0
ASSUME_YES=0
WITH_CURSOR_SKILLS=0   # ~/.cursor/skills is opt-in (ADR-0228); --cursor-skills turns it on
PRINT_OVERRIDES=""     # --print-skill-overrides=<minimal|core>: print, write nothing
PROJECT=""
PROFILE_SET=0   # 1 only when the caller passed --profile=TIER explicitly (D-4, ADR-0059)

# Capture whether the script was invoked with zero arguments, before the arg
# loop consumes them. This drives the interactivity gate below: a bare, TTY
# invocation opens the wizard; any flag, or a non-TTY stdin/stdout (CI, pipe,
# redirect), takes the scriptable path with the historical semantics.
INVOKED_ARGC=$#

WORKFLOW_DOCS_DEST="${WORKFLOW_DOCS_DIR:-${HOME}/.cursor/workflow-docs}"
CLAUDE_WORKFLOW_DOCS_DEST="${CLAUDE_WORKFLOW_DOCS_DIR:-${HOME}/.claude/workflow-docs}"
# Codex had no docs destination, so a --codex-only sync installed prompts whose wos/ loads
# resolved nowhere: the payload was gated on the other two tools alone.
CODEX_WORKFLOW_DOCS_DEST="${CODEX_WORKFLOW_DOCS_DIR:-${HOME}/.codex/workflow-docs}"
# Kimi keeps its payload under its own home so it moves with KIMI_CODE_HOME, the
# same way the other three destinations sit next to the config each tool reads.
KIMI_WORKFLOW_DOCS_DEST="${KIMI_WORKFLOW_DOCS_DIR:-${KIMI_HOME}/workflow-docs}"

usage() {
  sed -n '1,160p' <<'EOF'
Usage: sync-workflow-slash-commands.sh [options]

Run with no options on a terminal to open an interactive wizard. Pass any option
(or run in CI / a pipe) to take the non-interactive path and copy the workflow
repository's commands/*.md and, by default, the agent skills to Cursor, Claude
Code, Codex, and/or Kimi Code directories.

Options:
  --dry-run              Print actions only; do not write files.
  --profile=TIER         Which command set to install: minimal (the everyday
                         loop; the default), core (~50 commands), or full
                         (every flat command file). Passing --profile explicitly also
                         filters the skills mirror: minimal installs the spine
                         skills, core installs only core-tier skills, full (or an
                         empty --profile=) installs every skill. Omitting --profile
                         entirely leaves skills unfiltered. Add --no-skills to install
                         commands without skills.
  --no-skills            Do NOT sync agent skills (skills sync by default).
  --with-skills          Sync agent skills (default; kept for backward compatibility).
  --clean-orphans        Also remove command files in the destinations that no
                         longer exist in the source (renamed or deleted commands),
                         and, unless --cursor-skills is set, the Fhorja skills an
                         earlier install left in ~/.cursor/skills. A skill there counts
                         as Fhorja's only when its name is a Fhorja skill AND its
                         SKILL.md carries the x-wos-profiles key; any other skill is
                         left alone. Asks for confirmation on a terminal; needs --yes
                         otherwise; deletes nothing under --dry-run.
  --yes                  Assume yes for confirmations (non-interactive clean-orphans).
  --cursor-skills        Also write the skills to ~/.cursor/skills (CURSOR_SKILLS_DIR
                         moves it). Off by default: Cursor 3.17.8 or later reads
                         ~/.agents/skills natively, and a second copy is listed twice.
                         Cursor Cloud Agents sync needs it, because only
                         ~/.cursor/skills syncs there.
  --print-skill-overrides=TIER
                         Print a Claude Code skillOverrides object (JSON) that sets
                         every Fhorja skill outside TIER (minimal or core) to
                         name-only, then exit. Writes nothing: merge it into
                         ~/.claude/settings.json yourself if you want it.
  --cursor-only          Update only the Cursor destination.
  --claude-only          Update only the Claude Code destination.
  --codex-only           Update only the Codex prompts destination.
  --kimi-only            Update only the Kimi Code destination (skills + runtime payload;
                         Kimi has no custom-command directory).
                         The four --*-only flags compose: passing two of them selects
                         both tools rather than cancelling each other out.
  --cursor-dir=PATH      Override Cursor commands directory (default: ~/.cursor/commands).
  --claude-dir=PATH      Override Claude commands directory (default: ~/.claude/commands).
  --codex-dir=PATH       Override Codex prompts directory (default: ~/.codex/prompts).
  --kimi-dir=PATH        Override the Kimi skills directory (default: ~/.agents/skills,
                         the generic directory Kimi scans natively). Use
                         --kimi-dir=~/.kimi-code/skills for a Kimi-owned copy.
  --project=PATH         Also copy into PATH/.cursor/commands and PATH/.claude/commands,
                         and the skills into PATH/.claude/skills and PATH/.agents/skills
                         (PATH/.cursor/skills as well only under --cursor-skills).
                         Codex custom prompts are user-local only, so --project does not
                         create project-level Codex prompts. Kimi has no command
                         directory at either level; its project skills go to
                         PATH/.agents/skills (or PATH/.kimi-code/skills under --kimi-dir).
  --with-docs            Also copy the optional reference docs (README, demo, stubs, templates/)
                         into WORKFLOW_DOCS_DIR (default: ~/.cursor/workflow-docs),
                         CLAUDE_WORKFLOW_DOCS_DIR (default: ~/.claude/workflow-docs), and, if
                         --project is set, into PATH/.cursor/workflow-docs/.

Environment:
  CURSOR_COMMANDS_DIR    Same as --cursor-dir.
  CLAUDE_COMMANDS_DIR    Same as --claude-dir.
  CODEX_PROMPTS_DIR      Same as --codex-dir.
  WORKFLOW_DOCS_DIR      Destination for --with-docs, Cursor-side copy (default: ~/.cursor/workflow-docs).
  CLAUDE_WORKFLOW_DOCS_DIR  Second copy for Claude Code (default: ~/.claude/workflow-docs).
  CODEX_WORKFLOW_DOCS_DIR   Third copy for Codex (default: ~/.codex/workflow-docs).
  KIMI_WORKFLOW_DOCS_DIR    Fourth copy for Kimi (default: <kimi-home>/workflow-docs).
  CLAUDE_SKILLS_DIR      Skills destination, Claude Code (default: ~/.claude/skills).
  CURSOR_SKILLS_DIR      Skills destination written only under --cursor-skills (default: ~/.cursor/skills).
  CODEX_SKILLS_DIR       Skills destination shared by Codex, Kimi and Cursor (default: ~/.agents/skills).
  KIMI_SKILLS_DIR        Skills destination, Kimi Code (default: ~/.agents/skills). Same as --kimi-dir.
  KIMI_CODE_HOME         Kimi's own home directory. Read, never set, by this script; it
                         picks the installed one (~/.kimi-code, then ~/.kimi) when unset.

Default skill roots: ~/.claude/skills and ~/.agents/skills. Claude Code reads the
first and not the second; Codex, Kimi, and Cursor 3.17.8 or later read the second.
Cursor before 3.17.8 did not load ~/.agents/skills: update Cursor, or pass
--cursor-skills. Before copying skills, the installer runs
scripts/build-agent-skills.sh --check and refuses on drift; without python3 it
prints "skills not checked: python3 absent" and continues. --no-skills skips both.

Note: EVERY sync, with or without --with-docs, also writes the runtime payload
(WORKFLOW_OPERATING_SYSTEM.md + wos/) into the four workflow-docs destinations above, for
whichever tools the run targets. Every command's mandatory bootstrap reads four named
sections of the spec, and commands cite wos/<topic>.md with several of those loads MANDATORY,
so both are runtime dependencies rather than the optional reading material --with-docs
carries. The spec moved into the payload in ADR-0129; before that it shipped only to the
Cursor and Claude destinations, so a Codex- or Kimi-only machine could not bootstrap.

Note: Command files reference WORKFLOW_OPERATING_SYSTEM.md and paths under this repo.
For best results, open Claude Code or Codex with the workflow repository as cwd, or
add it via your normal workflow so those paths resolve.

Codex note: custom prompts load from ~/.codex/prompts and are invoked as
/prompts:<name> (for example /prompts:task-init). They are deprecated in favor
of skills, so the default skills sync is the recommended Codex workflow surface.

Kimi note: Kimi Code CLI has no user-defined slash-command directory, so a Kimi
sync writes skills and the runtime payload only, and --no-skills leaves it with
the payload alone. Skills are invoked as /skill:<name> (for example
/skill:task-init). Kimi scans both <kimi-home>/skills and the generic
~/.agents/skills, and this script writes the generic one so a skill is not
registered twice.
EOF
}

PROFILE="${PROFILE:-minimal}"

# --<tool>-only used to be spelled as "turn the other two off", which stopped
# scaling at the fourth tool and made two such flags together cancel each other
# out (every destination off, a silent no-op). Selecting additively keeps the
# single-flag meaning identical and makes --claude-only --kimi-only mean those two.
select_only() {
  if [[ "$ONLY_MODE" -eq 0 ]]; then
    DO_CURSOR=0; DO_CLAUDE=0; DO_CODEX=0; DO_KIMI=0
    ONLY_MODE=1
  fi
  case "$1" in
    cursor) DO_CURSOR=1 ;;
    claude) DO_CLAUDE=1 ;;
    codex)  DO_CODEX=1 ;;
    kimi)   DO_KIMI=1 ;;
  esac
}

# Bash does not tilde-expand a `~` that follows `=` inside an ordinary argument,
# so --claude-dir=~/x used to create a literal directory named `~` under the CWD.
# Expand a leading ~ or ~/ before it reaches mkdir.
expand_tilde() {
  local p="$1"
  case "$p" in
    "~") printf '%s' "$HOME" ;;
    "~/"*) printf '%s' "${HOME}/${p#\~/}" ;;
    *) printf '%s' "$p" ;;
  esac
}

# Defined before the argument loop, not after it, because both the loop and the wizard call it.
# It was below the loop until 2026-08-30, when the space form of --profile was added and could
# not reach it (`line 223: set_profile: command not found`). Routing both call sites through
# this helper is what keeps check_wizard_sets_profile_set strict: PROFILE and PROFILE_SET move
# together, and no new literal PROFILE= assignment site exists for the guard to have to allow.
set_profile() {
  PROFILE="$1"
  PROFILE_SET=1
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run) DRY_RUN=1 ;;
    --profile=*) PROFILE="${1#*=}"; PROFILE_SET=1 ;;
    # The space form is accepted because every doc and every muscle memory writes it that way.
    # Measured 2026-08-30: README and docs/FAQ.md carried four invocations in the space form and
    # all four exited 2 with "Unknown option", which is the first thing a new user copies.
    --profile) [[ $# -ge 2 && "$2" != -* ]] || { echo "--profile needs a value" >&2; exit 2; }; set_profile "$2"; shift ;;
    --no-skills) WITH_SKILLS=0 ;;
    --with-skills) WITH_SKILLS=1 ;;
    --clean-orphans) DO_CLEAN_ORPHANS=1 ;;
    --yes|-y) ASSUME_YES=1 ;;
    --cursor-skills) WITH_CURSOR_SKILLS=1 ;;
    --print-skill-overrides=*) PRINT_OVERRIDES="${1#*=}"; [[ -n "$PRINT_OVERRIDES" ]] || { echo "--print-skill-overrides needs a value: minimal or core" >&2; exit 2; } ;;
    --print-skill-overrides) [[ $# -ge 2 && "$2" != -* ]] || { echo "--print-skill-overrides needs a value: minimal or core" >&2; exit 2; }; PRINT_OVERRIDES="$2"; shift ;;
    --cursor-only) select_only cursor ;;
    --claude-only) select_only claude ;;
    --codex-only) select_only codex ;;
    --kimi-only) select_only kimi ;;
    --cursor-dir=*) CURSOR_DEST="$(expand_tilde "${1#*=}")" ;;
    --cursor-dir) [[ $# -ge 2 && "$2" != -* ]] || { echo "--cursor-dir needs a value" >&2; exit 2; }; CURSOR_DEST="$(expand_tilde "$2")"; shift ;;
    --claude-dir=*) CLAUDE_DEST="$(expand_tilde "${1#*=}")" ;;
    --claude-dir) [[ $# -ge 2 && "$2" != -* ]] || { echo "--claude-dir needs a value" >&2; exit 2; }; CLAUDE_DEST="$(expand_tilde "$2")"; shift ;;
    --codex-dir=*) CODEX_DEST="$(expand_tilde "${1#*=}")" ;;
    --codex-dir) [[ $# -ge 2 && "$2" != -* ]] || { echo "--codex-dir needs a value" >&2; exit 2; }; CODEX_DEST="$(expand_tilde "$2")"; shift ;;
    --kimi-dir=*) KIMI_SKILLS_DEST="$(expand_tilde "${1#*=}")" ;;
    --kimi-dir) [[ $# -ge 2 && "$2" != -* ]] || { echo "--kimi-dir needs a value" >&2; exit 2; }; KIMI_SKILLS_DEST="$(expand_tilde "$2")"; shift ;;
    --project=*) PROJECT="$(expand_tilde "${1#*=}")" ;;
    --project) [[ $# -ge 2 && "$2" != -* ]] || { echo "--project needs a value" >&2; exit 2; }; PROJECT="$(expand_tilde "$2")"; shift ;;
    --with-docs) WITH_DOCS=1 ;;
    -h|--help) usage; exit 0 ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
  shift
done

if [[ ! -d "$SRC" ]]; then
  echo "Source directory not found: $SRC" >&2
  exit 1
fi

# Counted from the same glob sync_one_dest copies, so the number the wizard and
# the summary quote cannot drift from what a full sync actually writes. It used
# to be the hardcoded 85 of an older corpus, in three separate strings.
FLAT_COMMAND_COUNT="$(find "$SRC" -maxdepth 1 -name '*.md' | wc -l | tr -d ' ')"

# Profile filter (ADR-0059, ADR-0178): the default profile is `minimal` (the
# everyday loop). Include a command file when its metadata.x-wos-profiles inline
# list contains the requested tier, or when the profile is explicitly empty
# (PROFILE= copies all, the pre-default behavior). minimal/core/full are distinct
# tokens, so a substring match against the inline list is sufficient.
file_in_profile() {
  local f="$1" p="$2" line
  [[ -z "$p" ]] && return 0
  line="$(awk '/^  x-wos-profiles:/{print; exit}' "$f")"
  [[ "$line" == *"$p"* ]] && return 0
  return 1
}

# Skill profile filter (D-4, ADR-0059). Same intent as file_in_profile(), but
# reads the generated .claude/skills/<name>/SKILL.md, not the canonical
# commands/*.md source. build-agent-skills.sh normalizes the canonical
# flow-style `x-wos-profiles: [core, full]` into spec-conformant block-style
# YAML on emit (see render_skill() in that script), so the shape here is:
#   x-wos-profiles:
#     - core
#     - full
# Only ever called with a tier the caller explicitly asked for; see
# skills_effective_profile() below for how that intent is derived.
# Reads BOTH shapes of x-wos-profiles, on purpose and in this order:
#   old, a block sequence:   x-wos-profiles:\n    - minimal\n    - core
#   new, a quoted scalar:    x-wos-profiles: "minimal, core, full"
# E4.1b flattens every SKILL.md to the scalar form, because the Agent Skills spec
# fixed metadata as a map from string keys to STRING values on 2026-08-03. This
# parser lands FIRST and is proved by scripts/tests/test-skill-in-profile.sh, so no
# ordering of the two slices can leave `--profile=minimal` copying zero skills in
# silence. The block branch stays afterwards as compatibility for installed trees
# that have not been re-synced yet.
# Comparison is per ITEM after the split, never a substring match: `core` must not
# match inside `hardcore`. It runs inside awk rather than a shell associative array,
# which returns empty in silence under this machine's zsh.
skill_in_profile() {
  local skill_dir="$1" p="$2" f
  f="${skill_dir%/}/SKILL.md"
  [[ -z "$p" ]] && return 0
  [[ -f "$f" ]] || return 1
  awk -v want="$p" '
    /^  x-wos-profiles:/ {
      rest = $0
      sub(/^  x-wos-profiles:[ \t]*/, "", rest)
      gsub(/^"|"$/, "", rest)
      if (rest != "") {
        n = split(rest, items, /,[ \t]*/)
        for (i = 1; i <= n; i++) {
          gsub(/^[ \t]+|[ \t]+$/, "", items[i])
          if (items[i] == want) found = 1
        }
        next
      }
      in_block = 1; next
    }
    in_block && /^    - / { val=$0; sub(/^    - /, "", val); if (val == want) found=1; next }
    in_block { in_block=0 }
    END { exit(found ? 0 : 1) }
  ' "$f"
}

# advertise_chars <skills-src> <profile> -> total chars of the `description:` field
# across every skill in <skills-src> that belongs to <profile>.
#
# Every agent run pays for these descriptions whether or not the skill is invoked,
# so this is the one number that scales with how much got mirrored. All 98 skills in
# this repository carry a multi-line description, so the continuation-line branch
# below is the normal path and not an edge case; dropping it undercounts by most of
# the total. Reads the SOURCE tree only, never a destination: it reports what this
# run mirrored, which is not the same as what the destination now holds, because
# sync_skills_dest never removes.
advertise_chars() {
  local src="$1" prof="$2" total=0 d n
  shopt -s nullglob
  for d in "${src}"/*/; do
    [[ -f "${d}SKILL.md" ]] || continue
    skill_in_profile "$d" "$prof" || continue
    n="$(awk '
      /^---[[:space:]]*$/ { fm++; if (fm == 2) exit; next }
      fm != 1 { next }
      /^description:/ {
        cap = 1
        line = substr($0, 13)
        gsub(/^[[:space:]]+|[[:space:]]+$/, "", line)
        acc = line
        next
      }
      cap && /^[[:space:]]/ {
        line = $0
        gsub(/^[[:space:]]+|[[:space:]]+$/, "", line)
        if (line != "") acc = acc " " line
        next
      }
      cap { cap = 0 }
      END { print length(acc) }
    ' "${d}SKILL.md")"
    total=$((total + n))
  done
  shopt -u nullglob
  printf '%s' "$total"
}

# The profile that actually gates the skills mirror. Skills stay unfiltered
# (empty string -> file_in_profile-style "copy everything") unless the caller
# passed --profile explicitly; PROFILE's own default ("minimal", set below for
# the *command* sync) must never leak into the skills filter, or a bare
# invocation would silently start refusing/filtering skills it always mirrored
# in full before D-4.
skills_effective_profile() {
  if [[ "$PROFILE_SET" -eq 1 ]]; then
    printf '%s' "$PROFILE"
  else
    printf ''
  fi
}

# --print-skill-overrides=<minimal|core> (ADR-0228). Claude Code lists every skill it can
# see on every turn, and a skillOverrides entry of "name-only" keeps a skill's name in that
# listing while dropping its description. Which skills a machine demotes is the operator's
# call and lives in their own settings file, so this prints the object and writes nothing.
print_skill_overrides() {
  local tier="$1" d
  case "$tier" in
    minimal|core) ;;
    *) echo "--print-skill-overrides takes minimal or core, not '${tier}'" >&2; exit 2 ;;
  esac
  if [[ ! -d "$SKILLS_SRC" ]]; then
    echo "--print-skill-overrides: no skills at ${SKILLS_SRC}; run scripts/build-agent-skills.sh first" >&2
    exit 1
  fi
  local names=()
  shopt -s nullglob
  for d in "${SKILLS_SRC}"/*/; do
    [[ -f "${d}SKILL.md" ]] || continue
    skill_in_profile "$d" "$tier" && continue
    names+=("$(basename "$d")")
  done
  shopt -u nullglob
  local i n=${#names[@]} sep
  printf '{\n  "skillOverrides": {\n'
  for ((i = 0; i < n; i++)); do
    sep=","; [[ $i -eq $((n - 1)) ]] && sep=""
    printf '    "%s": "name-only"%s\n' "${names[$i]}" "$sep"
  done
  printf '  }\n}\n'
  echo "Printed ${n} Fhorja skill(s) outside the ${tier} tier as name-only. Nothing was written;" >&2
  echo "merge the object into ~/.claude/settings.json yourself if you want it." >&2
}

if [[ -n "$PRINT_OVERRIDES" ]]; then
  print_skill_overrides "$PRINT_OVERRIDES"
  exit 0
fi

# ---------------------------------------------------------------------------
# State-detection helpers (read-only). Shared by the wizard's state panel and
# the end-of-run summary; they never write.
# ---------------------------------------------------------------------------
count_md() { # $1 = dir -> number of *.md files present
  find "$1" -maxdepth 1 -name '*.md' 2>/dev/null | wc -l | tr -d ' '
}

count_skills() { # $1 = dir -> number of skill subdirs present
  find "$1" -mindepth 1 -maxdepth 1 -type d 2>/dev/null | wc -l | tr -d ' '
}

detect_source() { # -> "<repo-basename> @ <branch>"
  local branch
  branch="$(git -C "$REPO_ROOT" rev-parse --abbrev-ref HEAD 2>/dev/null || echo '?')"
  printf '%s @ %s' "$(basename "$REPO_ROOT")" "$branch"
}

list_orphans() { # $1 = dest dir -> basenames present in dest but absent from SRC
  local dest="$1" f base
  [[ -d "$dest" ]] || return 0
  shopt -s nullglob
  for f in "$dest"/*.md; do
    base="$(basename "$f")"
    [[ -f "${SRC}/${base}" ]] || echo "$base"
  done
  shopt -u nullglob
}

# Two tools can legitimately resolve to the same directory: Kimi and Codex both
# read ~/.agents/skills, and any *_DIR override can collide by hand. Writing the
# same tree twice is wasted work at best and, on the skills side, a second
# rm -rf plus re-copy of a directory a concurrent reader may be scanning. Record
# what each phase already wrote and skip the repeat, out loud.
SYNCED_SKILL_DESTS="|"
SYNCED_PAYLOAD_DESTS="|"

# dest_is_new <list-contents> <dest> -> 0 when unseen. Callers append themselves.
dest_is_new() {
  local list="$1" d="${2%/}"
  [[ "$list" == *"|${d}|"* ]] && return 1
  return 0
}

sync_one_dest() {
  local label="$1"
  local dest="$2"
  if [[ -z "$dest" ]]; then
    return 0
  fi
  echo "==> ${label}: ${dest}"
  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "    mkdir -p $(printf '%q' "$dest")"
    local would=0
    shopt -s nullglob
    for f in "${SRC}"/*.md; do
      file_in_profile "$f" "$PROFILE" || continue
      echo "    cp $(printf '%q' "$f") $(printf '%q' "${dest}/$(basename "$f")")"
      would=$((would + 1))
    done
    shopt -u nullglob
    echo "    would write ${would} markdown files (profile: ${PROFILE:-all})"
    return 0
  fi
  mkdir -p "$dest"
  local copied=0
  shopt -s nullglob
  for f in "${SRC}"/*.md; do
    file_in_profile "$f" "$PROFILE" || continue
    cp "$f" "${dest}/$(basename "$f")"
    copied=$((copied + 1))
  done
  shopt -u nullglob
  echo "    wrote ${copied} markdown files (profile: ${PROFILE:-all})"
}

# The RUNTIME payload: the spec, wos/, SHIPPED_SCRIPTS and SHIPPED_SHARED_BLOCKS (both lists
# below). It began as wos/ alone; the spec, the scripts and the shared blocks joined it one at a
# time for the same reason wos/ did. Distinct from --with-docs, which by its own
# help text carries optional reading material (the spec, README, demo, stubs, templates/).
# This is a runtime dependency: every command file cites at least one `wos/<topic>.md`, and
# several of those loads are declared MANDATORY, so a session bootstrapping from an
# installed copy was resolving them against nothing.
# Copied on EVERY sync, deliberately OUTSIDE the --with-docs gate: that flag defaults to 0
# and bootstrap-user-setup.sh never suggests it, so behind it the fix would not reach a new
# user, who is the population it exists for.
# NO scripts are shipped, per D-3 of the retro wave-1 task. A first pass shipped a measured
# subset and review found the measurement was the wrong one: it ranked by how often a script
# is MENTIONED, not by whether it can run where it lands. `portfolio-review.sh` derives its
# data root from its own file location, so the installed copy chdirs into this directory,
# finds no projects/, and prints a well-formed EMPTY board with exit 0 while a command is
# told to trust that output. Shipping a helper that answers confidently and wrongly is worse
# than shipping none. Which scripts can ship at all is a per-script question and has its own
# task.
#
# The per-script answer, one entry at a time (ADR-0214). A script ships only when it passes
# BOTH tests that D-3 names, measured by running an installed copy from outside this repo:
#   1. it runs where it lands: no path derived from its own location (no BASH_SOURCE, no $0,
#      no SCRIPT_DIR), and every input it reads arrives as an argument;
#   2. on an empty or missing input it NAMES the absence rather than printing a well-formed
#      empty result with exit 0, which is the portfolio-review.sh failure D-3 was written from.
# rank-learnings.sh, measured 2026-09-22: an installed copy run from /tmp against a real
# project returned its ranked lessons; against an empty project it printed "no LEARNINGS.md
# found under: <path>" and "0 ranked / 0 scanned". It depends on awk, find, grep, sed and sort
# only. task-init's LEARNINGS consume step calls it, so without it the consume path fails
# silently on every install that is not a clone of this repository.
# compute-task-outcome.py, measured 2026-09-22: an installed copy run from outside the repo
# printed a schema-valid plan_review line, and against a task folder that does not exist it
# exits 2 with "task folder not found". It reads only its arguments and the stdlib. approve-plan,
# review-hard and task-close append its output to OUTCOMES.jsonl, so without it the ledger
# ADR-0208 relies on is never written on an install.
# ingest-scan.py, measured 2026-09-22: read-only, stdlib only, no self-location. It failed
# test 2 until the same day: empty input printed "VERDICT: CLEAN" with exit 0, and a missing
# file raised a traceback. Both now exit 2 with the absence named. It is the ASI06 poisoning
# scan four commands and a shared block run before ingested content enters task memory, so
# on an install without it that scan was skipped with nothing saying so.
# scan-substrate-orphans.py, measured 2026-09-22: stdlib only, no self-location. It failed
# test 2 until the same day: a named file that did not exist printed a warning, then OK with
# exit 0. It now exits 2 with the absent targets named. Six fleet commands gate their apply
# step on its exit code, so on an install without it every one of those gates failed.
# Measured 2026-09-23 (ADR-0224), the rest of the scripts commands run. Each was run as an
# installed copy from outside the repo against an empty target, and each now names what it
# did not read, with a non-zero exit wherever the exit is not advisory by contract:
# rank-references.sh passed as it was ("nothing to rank"). emit-substrate-write.sh,
# scan-substrate-headers.sh, verify-log-validator.py and verify-substrate-batch.sh ship as
# ONE unit: the batch wrapper is the closure integrity floor and runs the other two plus the
# orphan scan from its own directory, and without the emitter, or without the validator's
# file-scope digest reading, every installed close would fail that floor. The wrapper is the
# one script here that locates siblings through its own path; every sibling it names ships
# beside it, which the install test asserts. emit-substrate-write.sh needs jq. The others:
# check-live-markers.sh, check-plan-coverage.sh, plan-adherence.py, memory-lint.sh,
# secret-scan-gate.sh and portfolio-review.sh, which now reads the directory it runs from
# and refuses one with no projects/, the D-3 failure above.
# monitor-fleet-progress.sh, measured 2026-09-29 (ADR-0242): an installed run of implement-fleet
# lacked it (the E4 simulation), and as it stood it would have failed test 2, polling a missing
# inbox for 15 minutes and then printing "0 dispatched" with exit 0. It now exits 2 naming a
# missing task folder, a missing inbox with no return folder named, or a timeout with no worker
# seen; it reads the flat <worker_id>.json returns, and it has no self-location and no
# macOS-only stat call.
SHIPPED_SCRIPTS=(rank-learnings.sh compute-task-outcome.py ingest-scan.py scan-substrate-orphans.py rank-references.sh emit-substrate-write.sh scan-substrate-headers.sh verify-log-validator.py verify-substrate-batch.sh check-live-markers.sh check-plan-coverage.sh plan-adherence.py memory-lint.sh secret-scan-gate.sh portfolio-review.sh monitor-fleet-progress.sh)

# The commands/_shared/ blocks an installed file cites, shipped to <dest>/commands/_shared/.
# Most blocks are inlined into the commands by sync-shared-blocks.sh and need no copy, but
# some are cited by path as a contract to read: implement-fleet's frontmatter names
# commands/_shared/worker-contract.md as its workers' contract_ref, and nine closure writers
# follow commands/_shared/task-state-slice-closure-pattern.md. Measured 2026-09-29: the E4
# rerun of implement-fleet, run from an installed tree, found neither under
# ~/.claude/workflow-docs. The list is every block a command file, the spec, a wos topic or
# another listed block names by its commands/_shared/ path (13 of 24 on that date);
# check_command_scripts_shipped in evals/scripts/structural-evals.py fails when a cited block
# is missing from it, so the list cannot fall behind the citations.
SHIPPED_SHARED_BLOCKS=(claim-grounding.md convergence-policy.md definition-completeness-reader.md deliverable-reconcile.md grounded-residue-termination.md mandatory-context-bootstrap.md mcp-capability-routing.md orchestrator-bootstrap.md reference-grounding.md substrate-digest-fallback.md substrate-write-protocol.md task-state-slice-closure-pattern.md worker-contract.md)

sync_runtime_payload() {
  local label="$1"
  local dest="$2"
  if [[ -z "$dest" ]]; then
    return 0
  fi
  if ! dest_is_new "$SYNCED_PAYLOAD_DESTS" "$dest"; then
    echo "==> ${label} (runtime payload): ${dest%/} already written this run; skipping duplicate copy"
    return 0
  fi
  SYNCED_PAYLOAD_DESTS="${SYNCED_PAYLOAD_DESTS}${dest%/}|"
  echo "==> ${label} (runtime payload): ${dest}"
  local topics classes
  # Count the two categories the repository counts separately, rather than one
  # recursive find that calls a bug-class template a topic. The count markers in
  # the docs are `count:wos-topics` (the lazy topics at the root of wos/) and
  # `count:bug-templates` (the curated library under wos/bug-classes/), and a
  # message that reports their sum as "topics" overstates the first by 2.5x.
  topics="$(find "${REPO_ROOT}/wos" -maxdepth 1 -name '*.md' | wc -l | tr -d ' ')"
  classes="$(find "${REPO_ROOT}/wos/bug-classes" -name '*.md' 2>/dev/null | wc -l | tr -d ' ')"
  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "    mkdir -p $(printf '%q' "${dest}/wos")"
    echo "    cp WORKFLOW_OPERATING_SYSTEM.md -> $(printf '%q' "$dest")"
    echo "    cp -R wos/. -> $(printf '%q' "${dest}/wos")  (${topics} topics, recursive)"
    local s
    for s in "${SHIPPED_SCRIPTS[@]}"; do
      echo "    cp scripts/${s} -> $(printf '%q' "${dest}/scripts")"
    done
    echo "    cp ${#SHIPPED_SHARED_BLOCKS[@]} shared block(s) -> $(printf '%q' "${dest}/commands/_shared")"
    return 0
  fi
  mkdir -p "${dest}/wos"
  # The spec ships with the payload, not behind --with-docs (ADR-0129). Same argument as
  # wos/ above: the first item of EVERY command's mandatory context bootstrap is four named
  # sections of this file, so a session bootstrapping from an installed copy without it
  # resolves its first mandatory read against nothing. Before this, sync_workflow_docs was
  # called for the Cursor and Claude destinations only, so a Codex- or Kimi-only machine got
  # wos/ and no spec, and worked solely by falling back to a Claude install that happened to
  # sit beside it. --with-docs keeps the genuinely optional material (README, DEMO, STUBS,
  # templates/); the spec was never that.
  cp "${REPO_ROOT}/WORKFLOW_OPERATING_SYSTEM.md" "${dest}/"
  # Recursive: wos/ has subdirectories (bug-classes/), and a flat copy would drop them.
  # The payload's wos/ belongs to Fhorja alone, so a topic retired from the repository is
  # removed from it too. A copy on top never removes anything, and on 2026-09-22 and again
  # on 2026-09-23 an installed payload carried a retired topic a model could still read.
  local rel
  while IFS= read -r rel; do
    [[ -f "${REPO_ROOT}/wos/${rel}" ]] || rm -f "${dest}/wos/${rel}"
  done < <(cd "${dest}/wos" && find . -type f -name '*.md' | sed 's|^\./||')
  cp -R "${REPO_ROOT}/wos/." "${dest}/wos/"
  echo "    copied WORKFLOW_OPERATING_SYSTEM.md + wos/ (${topics} topics, ${classes} bug-class files)"
  if [[ "${#SHIPPED_SCRIPTS[@]}" -gt 0 ]]; then
    mkdir -p "${dest}/scripts"
    local s
    for s in "${SHIPPED_SCRIPTS[@]}"; do
      cp "${REPO_ROOT}/scripts/${s}" "${dest}/scripts/${s}"
      chmod +x "${dest}/scripts/${s}"
    done
    echo "    copied ${#SHIPPED_SCRIPTS[@]} script(s): ${SHIPPED_SCRIPTS[*]}"
  fi
  # The payload's commands/_shared/ belongs to Fhorja alone, so a block dropped from the list
  # is removed from it too, the rule wos/ follows above.
  mkdir -p "${dest}/commands/_shared"
  local b listed
  while IFS= read -r rel; do
    listed=0
    for b in "${SHIPPED_SHARED_BLOCKS[@]}"; do
      [[ "$rel" == "$b" ]] && listed=1
    done
    [[ "$listed" -eq 1 ]] || rm -f "${dest}/commands/_shared/${rel}"
  done < <(cd "${dest}/commands/_shared" && find . -maxdepth 1 -type f -name '*.md' | sed 's|^\./||')
  for b in "${SHIPPED_SHARED_BLOCKS[@]}"; do
    cp "${REPO_ROOT}/commands/_shared/${b}" "${dest}/commands/_shared/${b}"
  done
  echo "    copied ${#SHIPPED_SHARED_BLOCKS[@]} shared block(s) to commands/_shared/"
}

# The OPTIONAL reading material, behind --with-docs. The spec is deliberately NOT here
# any more (ADR-0129): it moved into sync_runtime_payload, which runs on every sync to
# every destination, because it is a runtime dependency rather than reading material.
sync_workflow_docs() {
  local label="$1"
  local dest="$2"
  echo "==> ${label} (docs): ${dest}"
  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "    mkdir -p $(printf '%q' "$dest")"
    echo "    cp README.md WORKFLOW_DEMO.md COMMAND_PROMPT_STUBS.md -> $(printf '%q' "$dest")"
    echo "    cp -R templates -> $(printf '%q' "$dest/templates")"
    return 0
  fi
  mkdir -p "${dest}/templates"
  # templates/ under the docs destination belongs to Fhorja alone, so a template retired
  # from the repository is removed from it too, the rule sync_runtime_payload applies to
  # its topics (ADR-0228, D-6 of the 2026-09-23 backlog task). A copy on top never
  # removes anything.
  local rel
  while IFS= read -r rel; do
    [[ -f "${REPO_ROOT}/templates/${rel}" ]] || rm -f "${dest}/templates/${rel}"
  done < <(cd "${dest}/templates" && find . -type f | sed 's|^\./||')
  cp "${REPO_ROOT}/README.md" "${dest}/"
  cp "${REPO_ROOT}/WORKFLOW_DEMO.md" "${dest}/"
  cp "${REPO_ROOT}/COMMAND_PROMPT_STUBS.md" "${dest}/"
  cp -R "${REPO_ROOT}/templates/"* "${dest}/templates/"
  echo "    copied README, DEMO, STUBS, and templates/ (the spec ships with the runtime payload)"
}

sync_skills_dest() {
  local label="$1"
  local dest="$2"
  if [[ -z "$dest" ]]; then
    return 0
  fi
  if [[ ! -d "$SKILLS_SRC" ]]; then
    echo "==> ${label}: skipped (source ${SKILLS_SRC} not present; run scripts/build-agent-skills.sh first)" >&2
    return 0
  fi
  if ! dest_is_new "$SYNCED_SKILL_DESTS" "$dest"; then
    echo "==> ${label}: ${dest%/} already written this run; skipping duplicate copy"
    return 0
  fi
  SYNCED_SKILL_DESTS="${SYNCED_SKILL_DESTS}${dest%/}|"
  local sp
  sp="$(skills_effective_profile)"
  echo "==> ${label}: ${dest}"
  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "    mkdir -p $(printf '%q' "$dest")"
    local would=0
    shopt -s nullglob
    for d in "${SKILLS_SRC}"/*/; do
      skill_in_profile "$d" "$sp" || continue
      name="$(basename "$d")"
      echo "    cp -R $(printf '%q' "$d") $(printf '%q' "${dest}/${name}")"
      would=$((would + 1))
    done
    shopt -u nullglob
    echo "    would write ${would} skill(s) (profile: ${sp:-all})"
    return 0
  fi
  mkdir -p "$dest"
  shopt -s nullglob
  local n=0
  for d in "${SKILLS_SRC}"/*/; do
    skill_in_profile "$d" "$sp" || continue
    local name
    name="$(basename "$d")"
    rm -rf "${dest}/${name}"
    mkdir -p "${dest}/${name}"
    cp -R "$d"/. "${dest}/${name}/"
    n=$((n + 1))
  done
  shopt -u nullglob
  echo "    wrote ${n} skill(s) (profile: ${sp:-all})"
}

# is_fhorja_skill <skill-dir> -> 0 when the directory holds a skill Fhorja installed: its
# name is one of this repository's skills AND its SKILL.md frontmatter carries the
# x-wos-profiles key every generated Fhorja skill has. A name match alone is not enough:
# ~/.cursor/skills is shared with skills the operator installed from elsewhere, and on
# 2026-09-17 the maintainer's copy held 11 of those beside Fhorja's 98 (backlog B19).
is_fhorja_skill() {
  local dir="${1%/}" name
  name="$(basename "$dir")"
  [[ -d "${SKILLS_SRC}/${name}" && -f "${dir}/SKILL.md" ]] || return 1
  awk '
    /^---[[:space:]]*$/ { fm++; if (fm == 2) exit; next }
    fm == 1 && /^[[:space:]]+x-wos-profiles:/ { found = 1; exit }
    END { exit(found ? 0 : 1) }
  ' "${dir}/SKILL.md"
}

# list_cursor_skill_leftovers -> names of Fhorja skills an earlier install wrote to
# ~/.cursor/skills, which is no longer a default destination (ADR-0228). Empty when
# --cursor-skills is set (the root is still a destination) or Cursor is deselected.
list_cursor_skill_leftovers() {
  [[ "$WITH_CURSOR_SKILLS" -eq 0 && "$DO_CURSOR" -eq 1 ]] || return 0
  [[ -d "$CURSOR_SKILLS_DEST" ]] || return 0
  local d
  shopt -s nullglob
  for d in "$CURSOR_SKILLS_DEST"/*/; do
    is_fhorja_skill "$d" && basename "$d"
  done
  shopt -u nullglob
  return 0
}

# Skills preflight (D-14 of the 2026-09-23 backlog task). The installer copies
# .claude/skills as it finds it, so a clone whose generated skills no longer match
# commands/ used to install the stale copies without a word. build-agent-skills.sh
# --check re-renders every skill and exits 1 on drift or a stale directory; it needs
# python3 and the rest of this installer does not, so a machine without python3 is
# told the check did not run instead of being refused.
preflight_skills() {
  [[ "$WITH_SKILLS" -eq 1 ]] || return 0
  if ! command -v python3 >/dev/null 2>&1; then
    echo "==> Skills check: skills not checked: python3 absent (build-agent-skills.sh --check needs it); continuing"
    return 0
  fi
  local out rc=0
  out="$(bash "${SCRIPT_DIR}/build-agent-skills.sh" --check 2>&1)" || rc=$?
  if [[ "$rc" -eq 0 ]]; then
    echo "==> Skills check: .claude/skills matches commands/ (build-agent-skills.sh --check)"
    return 0
  fi
  {
    printf '%s\n' "$out" | grep -E '^(Drifted skills:|Stale skill directories|  - )' | head -20 || true
    echo "Refusing to install skills: .claude/skills does not match commands/ (build-agent-skills.sh --check exit ${rc})."
    echo "Fix: ./scripts/build-agent-skills.sh, then re-run this installer."
    echo "Or pass --no-skills to install the commands and the payload without skills."
  } >&2
  exit 1
}

cleanup_legacy_codex_skills() {
  local legacy_dest="$1"

  # Codex moved user-level skills from ~/.codex/skills to ~/.agents/skills.
  # Only clean the legacy root when the canonical destination was not overridden,
  # and only remove names owned by this workflow. Leave unrelated skills intact.
  if [[ "$CODEX_SKILLS_DEST" != "$DEFAULT_CODEX_SKILLS_DEST" || ! -d "$legacy_dest" ]]; then
    return 0
  fi

  echo "==> OpenAI Codex legacy skill cleanup: ${legacy_dest}"
  shopt -s nullglob
  local n=0
  local d name
  for d in "${SKILLS_SRC}"/*/; do
    name="$(basename "$d")"
    if [[ ! -e "${legacy_dest}/${name}" ]]; then
      continue
    fi
    if [[ "$DRY_RUN" -eq 1 ]]; then
      echo "    rm -rf $(printf '%q' "${legacy_dest}/${name}")"
    else
      rm -rf -- "${legacy_dest}/${name}"
    fi
    n=$((n + 1))
  done
  shopt -u nullglob
  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "    would remove ${n} duplicate legacy skill(s)"
  else
    echo "    removed ${n} duplicate legacy skill(s)"
  fi
}

# ---------------------------------------------------------------------------
# Clean orphans: remove command files in the command destinations that no
# longer exist in the source (renamed or deleted commands). Strictly scoped:
# a dest file is removed only when its basename has NO match under commands/.
# ---------------------------------------------------------------------------
clean_orphans() {
  local dests=("$CURSOR_DEST" "$CLAUDE_DEST" "$CODEX_DEST")
  local labels=("Cursor" "Claude Code" "Codex")
  local found=0 i dest label base
  echo "Scanning for orphan command files (present in a destination, absent from source)..."
  for i in "${!dests[@]}"; do
    dest="${dests[$i]}"; label="${labels[$i]}"
    [[ -d "$dest" ]] || continue
    while IFS= read -r base; do
      [[ -z "$base" ]] && continue
      printf '  %-12s %s\n' "$label" "$base"
      found=$((found + 1))
    done < <(list_orphans "$dest")
  done
  # ~/.cursor/skills stopped being a default destination in ADR-0228. The Fhorja skills an
  # earlier install left there make Cursor list every skill twice, and a sync never removes
  # anything, so this is the one path that takes them out. Only Fhorja's (is_fhorja_skill).
  local leftovers
  leftovers="$(list_cursor_skill_leftovers)"
  while IFS= read -r base; do
    [[ -z "$base" ]] && continue
    printf '  %-12s %s\n' "Cursor skill" "${CURSOR_SKILLS_DEST}/${base}"
    found=$((found + 1))
  done <<<"$leftovers"
  if [[ "$found" -eq 0 ]]; then
    echo "  No orphans. Nothing to clean."
    return 0
  fi
  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "  (dry run: would ask to delete these ${found} item(s); nothing deleted)"
    return 0
  fi
  local confirm="n"
  if [[ -t 0 ]]; then
    printf 'Delete these %d item(s)? [y/N] ' "$found"
    read -r confirm || true
  elif [[ "$ASSUME_YES" -eq 1 ]]; then
    confirm="y"
  else
    echo "  (nothing deleted: pass --yes to delete, or run with no flags for the wizard)"
    return 0
  fi
  case "$confirm" in
    y|Y|yes)
      for i in "${!dests[@]}"; do
        dest="${dests[$i]}"
        while IFS= read -r base; do
          [[ -z "$base" ]] && continue
          rm -f "${dest}/${base}"
        done < <(list_orphans "$dest")
      done
      while IFS= read -r base; do
        [[ -z "$base" ]] && continue
        # Re-checked at the moment of deletion, not trusted from the listing above.
        is_fhorja_skill "${CURSOR_SKILLS_DEST}/${base}" && rm -rf -- "${CURSOR_SKILLS_DEST:?}/${base}"
      done <<<"$leftovers"
      echo "Removed ${found} orphan item(s)."
      ;;
    *) echo "Cancelled. Nothing deleted." ;;
  esac
}

# End-of-run summary: an honest line naming what was synced and how to get more.
print_summary() {
  local skills_txt cmd_txt sp tools=""
  sp="$(skills_effective_profile)"
  if [[ "$WITH_SKILLS" -eq 1 ]]; then
    if [[ -n "$sp" ]]; then skills_txt="${sp}-tier skills"; else skills_txt="all skills"; fi
  else
    skills_txt="no skills"
  fi
  # Only claim a command install when a tool that HAS a command directory was
  # targeted. --kimi-only used to report "minimal commands" for a run that, by
  # Kimi's own design, installed no command file anywhere.
  if [[ "$DO_CURSOR" -eq 1 || "$DO_CLAUDE" -eq 1 || "$DO_CODEX" -eq 1 ]]; then
    cmd_txt=" + ${PROFILE:-all} commands"
  else
    cmd_txt=""
  fi
  [[ "$DO_CURSOR" -eq 1 ]] && tools="${tools}Cursor, "
  [[ "$DO_CLAUDE" -eq 1 ]] && tools="${tools}Claude Code, "
  [[ "$DO_CODEX" -eq 1 ]] && tools="${tools}Codex, "
  [[ "$DO_KIMI" -eq 1 ]] && tools="${tools}Kimi Code, "
  tools="${tools%, }"
  echo ""
  echo "Summary: synced ${skills_txt}${cmd_txt} to ${tools:-nothing (every destination was deselected)}."
  if [[ "$DO_KIMI" -eq 1 ]]; then
    echo "  Kimi Code got skills only (no custom-command directory exists); invoke them as /skill:<name>."
  fi
  if [[ "$WITH_SKILLS" -eq 1 ]]; then
    local adv_chars adv_tokens
    adv_chars="$(advertise_chars "$SKILLS_SRC" "$sp")"
    adv_tokens=$((adv_chars / 4))
    echo "  Every agent run pays for these skill descriptions before it reads any work:"
    echo "  about ${adv_tokens} tokens (${adv_chars} chars) for the set this run mirrored."
    if [[ -z "$sp" ]]; then
      local min_chars min_tokens
      min_chars="$(advertise_chars "$SKILLS_SRC" minimal)"
      min_tokens=$((min_chars / 4))
      echo "  --profile=minimal mirrors the everyday spine instead, at about ${min_tokens} tokens."
      echo "  This run mirrored the full set. Skills already installed are never removed, so an"
      echo "  earlier full sync keeps costing its own price until you remove those files yourself."
    fi
  fi
  if [[ "$WITH_SKILLS" -eq 1 && "$DO_CURSOR" -eq 1 ]]; then
    if [[ "$WITH_CURSOR_SKILLS" -eq 1 ]]; then
      echo "  Cursor skills went to ${CURSOR_SKILLS_DEST} (--cursor-skills) as well as ${CURSOR_SHARED_SKILLS_DEST};"
      echo "  Cursor 3.17.8 or later reads both, so it lists each Fhorja skill twice."
    else
      echo "  Cursor reads the skills from ${CURSOR_SHARED_SKILLS_DEST} (Cursor 3.17.8 or later)."
      echo "  Pass --cursor-skills to also write ${CURSOR_SKILLS_DEST}, which Cloud Agents sync needs."
      local left_n
      left_n="$(list_cursor_skill_leftovers | grep -c . || true)"
      if [[ "${left_n:-0}" -gt 0 ]]; then
        echo "  ${left_n} Fhorja skill(s) from an earlier install remain in ${CURSOR_SKILLS_DEST}, so Cursor"
        echo "  lists them twice; --clean-orphans removes them after asking."
      fi
    fi
  fi
  if [[ "$PROFILE" == "minimal" && -n "$cmd_txt" ]]; then
    echo "  Only the everyday spine commands are installed. For all ${FLAT_COMMAND_COUNT}, re-run with"
    echo "  --profile=full, or pick 'Sync everything' in the wizard (run with no flags)."
  fi
}

# ---------------------------------------------------------------------------
# Interactive wizard (pure bash; no dependency). Rendered only on a real TTY.
# ---------------------------------------------------------------------------
_MENU_SAVED_STTY=""
_menu_cleanup() {
  printf '\033[?25h'  # show cursor
  [[ -n "$_MENU_SAVED_STTY" ]] && stty "$_MENU_SAVED_STTY" 2>/dev/null || true
}

# menu_select "<prompt>" "Label|dim description" ...  -> sets MENU_CHOICE (index, -1 on quit)
menu_select() {
  local prompt="$1"; shift
  local options=("$@")
  local n=${#options[@]}
  local sel=0 first=1 key key2 i label desc
  _MENU_SAVED_STTY="$(stty -g 2>/dev/null || true)"
  trap '_menu_cleanup' EXIT INT TERM
  printf '\033[?25l'  # hide cursor
  stty -echo -icanon time 0 min 1 2>/dev/null || true
  while true; do
    if [[ $first -eq 0 ]]; then printf '\033[%dA' $((n + 1)); fi
    first=0
    printf '  \033[1m%s\033[0m\033[K\n' "$prompt"
    for ((i = 0; i < n; i++)); do
      label="${options[$i]%%|*}"
      desc="${options[$i]#*|}"; [[ "$desc" == "${options[$i]}" ]] && desc=""
      if [[ $i -eq $sel ]]; then
        printf '  \033[36m>\033[0m \033[1m%s\033[0m  \033[2m%s\033[0m\033[K\n' "$label" "$desc"
      else
        printf '    %s  \033[2m%s\033[0m\033[K\n' "$label" "$desc"
      fi
    done
    IFS= read -rsn1 key 2>/dev/null || true
    if [[ "$key" == $'\033' ]]; then
      IFS= read -rsn2 -t 1 key2 2>/dev/null || true
      key+="$key2"
    fi
    case "$key" in
      $'\033[A'|k) sel=$(( (sel - 1 + n) % n )) ;;
      $'\033[B'|j) sel=$(( (sel + 1) % n )) ;;
      ''|$'\n'|$'\r') break ;;
      q|Q) sel=-1; break ;;
    esac
  done
  _menu_cleanup
  trap - EXIT INT TERM
  MENU_CHOICE=$sel
}

show_header() {
  printf '\n'
  printf '  \033[1;38;5;208m🔥 Fhorja\033[0m  \033[2m·  workflow sync\033[0m\n'
  printf '  \033[2mMarkdown + bash. Wired into every tool.\033[0m\n\n'
}

show_state_panel() {
  local orphans
  printf '  \033[2mCurrent state\033[0m\n'
  printf '    %-12s %s skills · %s commands\n' "Claude Code" "$(count_skills "$CLAUDE_SKILLS_DEST")" "$(count_md "$CLAUDE_DEST")"
  printf '    %-12s %s skills · %s commands\n' "Cursor" "$(count_skills "$CURSOR_SHARED_SKILLS_DEST")" "$(count_md "$CURSOR_DEST")"
  printf '    %-12s %s skills · %s prompts\n' "Codex" "$(count_skills "$CODEX_SKILLS_DEST")" "$(count_md "$CODEX_DEST")"
  printf '    %-12s %s skills · %s\n' "Kimi Code" "$(count_skills "$KIMI_SKILLS_DEST")" "no command dir"
  printf '    %-12s %s\n' "Source" "$(detect_source)"
  orphans="$(list_orphans "$CLAUDE_DEST" | tr '\n' ' ')"
  if [[ -n "${orphans// /}" ]]; then
    printf '    \033[33m⚠ orphan commands:\033[0m %s\n' "$orphans"
  fi
  orphans="$(list_cursor_skill_leftovers | grep -c . || true)"
  if [[ "${orphans:-0}" -gt 0 ]]; then
    printf '    \033[33m⚠ %s Fhorja skill(s) left in %s:\033[0m Cursor lists them twice\n' "$orphans" "$CURSOR_SKILLS_DEST"
  fi
  printf '\n'
}

# The wizard sets both halves of the profile choice. skills_effective_profile()
# reads PROFILE_SET, not PROFILE, so a bare `PROFILE=x` from the wizard installs
# the full skill set while the command list honours the choice.

wizard_custom() {
  menu_select "Which command set?" \
    "minimal|the everyday spine commands" \
    "core|around 50 commands" \
    "full|all ${FLAT_COMMAND_COUNT} commands"
  case "$MENU_CHOICE" in 0) set_profile minimal ;; 1) set_profile core ;; 2) set_profile "" ;; esac
  menu_select "Sync skills too?" "Yes|recommended, the surface models actually load" "No|commands only"
  case "$MENU_CHOICE" in 0) WITH_SKILLS=1 ;; 1) WITH_SKILLS=0 ;; esac
}

run_wizard() {
  show_header
  show_state_panel
  menu_select "What do you want to do?" \
    "Sync everything|all skills + all ${FLAT_COMMAND_COUNT} commands, every tool (recommended)" \
    "Everyday loop|the everyday spine: skills and commands" \
    "Custom|choose the command set and skills" \
    "Health check|show what would change, write nothing" \
    "Clean orphans|remove stale command files, and Fhorja skills left in ~/.cursor/skills" \
    "Quit|"
  case "$MENU_CHOICE" in
    0) set_profile ""; WITH_SKILLS=1; run_sync; print_summary ;;
    1) set_profile minimal; WITH_SKILLS=1; run_sync; print_summary ;;
    2) wizard_custom; run_sync; print_summary ;;
    3) DRY_RUN=1; set_profile ""; WITH_SKILLS=1; echo ""; run_sync ;;
    4) clean_orphans ;;
    *) echo "Nothing to do." ; return 0 ;;
  esac
}

# ---------------------------------------------------------------------------
# The non-interactive sync driver. Both the wizard and the scriptable path
# funnel through here; the wizard only collects intent into the same variables
# the flags set, so there is a single sync code path.
# ---------------------------------------------------------------------------
run_sync() {
  # Validate --project BEFORE any destination is written. It used to sit after the three
  # home sync_one_dest calls, so a bad path left a fully installed command set behind and
  # then aborted before the payload: commands present, every wos/ load resolving nowhere.
  if [[ -n "$PROJECT" ]] && [[ ! -d "$PROJECT" ]]; then
    echo "Project path is not a directory: $PROJECT" >&2
    exit 1
  fi
  # Also before any destination is written, for the same reason: a refusal after the
  # commands and the payload were copied would leave a half-installed machine behind.
  preflight_skills
  if [[ "$DO_CURSOR" -eq 1 ]]; then
    sync_one_dest "Cursor" "$CURSOR_DEST"
  fi
  if [[ "$DO_CLAUDE" -eq 1 ]]; then
    sync_one_dest "Claude Code" "$CLAUDE_DEST"
  fi
  if [[ "$DO_CODEX" -eq 1 ]]; then
    sync_one_dest "OpenAI Codex prompts" "$CODEX_DEST"
  fi
  if [[ "$DO_KIMI" -eq 1 ]]; then
    # Stated rather than silently omitted: Kimi Code CLI exposes no user-defined
    # slash-command directory, so there is nowhere for commands/*.md to land. Its
    # customization surface is Agent Skills, synced below and invoked as /skill:<name>.
    echo "==> Kimi Code commands: skipped (Kimi has no custom-command directory; its surface is skills, invoked as /skill:<name>)"
    if [[ "$WITH_SKILLS" -eq 0 ]]; then
      echo "    warning: with --no-skills, this run installs nothing for Kimi beyond the runtime payload." >&2
    fi
  fi

  if [[ -n "$PROJECT" ]]; then
    if [[ "$DO_CURSOR" -eq 1 ]]; then
      sync_one_dest "Cursor (project)" "${PROJECT}/.cursor/commands"
    fi
    if [[ "$DO_CLAUDE" -eq 1 ]]; then
      sync_one_dest "Claude Code (project)" "${PROJECT}/.claude/commands"
    fi
    if [[ "$DO_CODEX" -eq 1 ]]; then
      echo "==> OpenAI Codex prompts (project): skipped (Codex custom prompts are user-local under ~/.codex/prompts)"
    fi
  fi

  # Unconditional with respect to --with-docs, and that placement is the point: inside the
  # WITH_DOCS block below, the payload every command depends on would ship only to users who
  # already knew to ask for optional docs. Gated per tool like every sibling call, so
  # --cursor-only does not write a Claude destination.
  if [[ "$DO_CURSOR" -eq 1 ]]; then
    sync_runtime_payload "Runtime payload (Cursor)" "$WORKFLOW_DOCS_DEST"
  fi
  if [[ "$DO_CLAUDE" -eq 1 ]]; then
    sync_runtime_payload "Runtime payload (Claude)" "$CLAUDE_WORKFLOW_DOCS_DEST"
  fi
  if [[ "$DO_CODEX" -eq 1 ]]; then
    sync_runtime_payload "Runtime payload (Codex)" "$CODEX_WORKFLOW_DOCS_DEST"
  fi
  if [[ "$DO_KIMI" -eq 1 ]]; then
    sync_runtime_payload "Runtime payload (Kimi)" "$KIMI_WORKFLOW_DOCS_DEST"
  fi
  if [[ -n "$PROJECT" ]] && [[ "$DO_CURSOR" -eq 1 ]]; then
    sync_runtime_payload "Runtime payload (project / Cursor)" "${PROJECT}/.cursor/workflow-docs"
  fi

  if [[ "$WITH_DOCS" -eq 1 ]]; then
    sync_workflow_docs "Workflow docs (Cursor)" "$WORKFLOW_DOCS_DEST"
    sync_workflow_docs "Workflow docs (Claude)" "$CLAUDE_WORKFLOW_DOCS_DEST"
    if [[ -n "$PROJECT" ]]; then
      sync_workflow_docs "Workflow docs (project / Cursor)" "${PROJECT}/.cursor/workflow-docs"
    fi
  fi

  if [[ "$WITH_SKILLS" -eq 1 ]]; then
    if [[ "$DO_CLAUDE" -eq 1 ]]; then
      sync_skills_dest "Claude Code skills" "$CLAUDE_SKILLS_DEST"
    fi
    if [[ "$DO_CURSOR" -eq 1 ]]; then
      # Cursor reads the shared root natively; Codex and Kimi read it too, so the dedup
      # guard in sync_skills_dest turns their later call into a named skip.
      sync_skills_dest "Cursor skills (shared root)" "$CURSOR_SHARED_SKILLS_DEST"
      if [[ "$WITH_CURSOR_SKILLS" -eq 1 ]]; then
        sync_skills_dest "Cursor skills (--cursor-skills)" "$CURSOR_SKILLS_DEST"
      else
        echo "==> Cursor skills: ${CURSOR_SKILLS_DEST} not written (Cursor 3.17.8 or later reads ${CURSOR_SHARED_SKILLS_DEST}; --cursor-skills writes it)"
      fi
    fi
    if [[ "$DO_CODEX" -eq 1 ]]; then
      sync_skills_dest "OpenAI Codex skills" "$CODEX_SKILLS_DEST"
      cleanup_legacy_codex_skills "$LEGACY_CODEX_SKILLS_DEST"
    fi
    if [[ "$DO_KIMI" -eq 1 ]]; then
      # Usually the same ~/.agents/skills Codex just wrote, in which case the
      # dedup guard reports the skip instead of copying 98 trees a second time.
      sync_skills_dest "Kimi Code skills" "$KIMI_SKILLS_DEST"
    fi
    if [[ -n "$PROJECT" ]]; then
      if [[ "$DO_CLAUDE" -eq 1 ]]; then
        sync_skills_dest "Project Claude Code skills" "${PROJECT}/.claude/skills"
      fi
      if [[ "$DO_CURSOR" -eq 1 ]]; then
        # The same default as at user level: Cursor reads <project>/.agents/skills
        # natively, and <project>/.cursor/skills is written only under --cursor-skills.
        sync_skills_dest "Project Cursor skills (shared root)" "${PROJECT}/.agents/skills"
        if [[ "$WITH_CURSOR_SKILLS" -eq 1 ]]; then
          sync_skills_dest "Project Cursor skills (--cursor-skills)" "${PROJECT}/.cursor/skills"
        fi
      fi
      if [[ "$DO_CODEX" -eq 1 ]]; then
        sync_skills_dest "Project OpenAI Codex skills" "${PROJECT}/.agents/skills"
      fi
      if [[ "$DO_KIMI" -eq 1 ]]; then
        # Project level, Kimi scans <project>/.kimi-code/skills and <project>/.agents/skills.
        # Prefer the generic one for the same no-duplicate-registration reason as at
        # user level, and fall back to the brand directory when a --kimi-dir override
        # moved the user-level copy off the generic path.
        if [[ "$KIMI_SKILLS_DEST" == "${HOME}/.agents/skills" ]]; then
          sync_skills_dest "Project Kimi Code skills" "${PROJECT}/.agents/skills"
        else
          sync_skills_dest "Project Kimi Code skills" "${PROJECT}/${KIMI_BRAND_DIRNAME}/skills"
        fi
      fi
    fi
  fi

  if [[ "$DO_CLEAN_ORPHANS" -eq 1 ]]; then
    clean_orphans
  fi
}

# Interactivity gate (D-1): a bare invocation on a real terminal opens the
# wizard. Any flag, or a non-TTY stdin/stdout (CI, pipe, redirect), takes the
# scriptable path with the historical semantics.
if [[ "$INVOKED_ARGC" -eq 0 && -t 0 && -t 1 ]]; then
  run_wizard
else
  run_sync
  print_summary
fi

echo "Done."
