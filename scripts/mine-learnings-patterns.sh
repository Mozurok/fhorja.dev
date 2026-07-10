#!/usr/bin/env bash
# mine-learnings-patterns.sh - opt-in, embeddings-free LEARNINGS pattern-mining pass.
#
# ADR-0071 already ranks LEARNINGS.md entries for retrieval (rank-learnings.sh);
# nothing groups them into named recurring themes. This script is that grouping
# pass, done in-context instead of with embeddings (kura's meta-clustering
# splits into a neighborhood-grouping stage, which is the only stage that uses
# embeddings/K-means, and a naming/assignment stage, which is already LLM-driven;
# see docs/adr/0076-learnings-pattern-mining.md). We substitute the whole thing
# with one bounded LLM grouping prompt: no vector index, no new dependency.
#
# What it does:
#   1. Collects entries from <project-dir>/active/*/LEARNINGS.md and
#      <project-dir>/archive/*/LEARNINGS.md. An entry is a `## ` heading block
#      that carries all four required bullets: Anchor, Tried, Failed because,
#      Next time (Tags is optional). This mirrors templates/LEARNINGS.md's
#      5(+1)-bullet shape and rank-learnings.sh's precedent of silently
#      skipping non-conforming headers rather than guessing at their shape.
#   2. Assembles ONE grouping prompt: every collected entry, then instructions
#      asking the model to propose named recurring-pattern groups, each group
#      listing its member entries by heading and anchor (the kura naming-stage
#      contract: the LLM sees names/descriptions of the children, not vectors).
#   3. Pipes the prompt to an external CLI AI tool exactly the way
#      evals/scripts/judge.py's call_tool() does: printf the prompt on stdin,
#      let the tool command do the rest.
#   4. Writes the result plus a header (date, corpus size, corpus SHA-256) to
#      a cache file under <project-dir>/.wos-mined-patterns/patterns.md.
#      When the corpus hash is unchanged since the cached run, the cached
#      result is printed and no tool call is made (kura's JSONL-checkpoint,
#      skip-if-present analog).
#
# This script NEVER writes to a LEARNINGS.md (read-only over that corpus) and
# NEVER uses embeddings or a vector index. If faithful grouping ever seemed to
# need either, that is a STOP condition, not a feature to add here (R-1 in
# this task's DECISIONS.md rejects every embeddings/vector-index mechanism).
#
# Usage:
#   mine-learnings-patterns.sh <project-dir> [--tool '<cli command>'] [--dry-run] [--max-entries N]
#   - project-dir: a projects/<client>__<project> directory containing active/
#     and/or archive/ task folders.
#   - --tool: shell command that takes the grouping prompt on stdin and emits
#     the model's response on stdout. Default: "claude code --print" (ADR-0019
#     convention; same default as evals/scripts/judge.py).
#   - --dry-run: print the assembled prompt and corpus stats; no tool call, no
#     cache write.
#   - --max-entries: cap on how many entries go into the prompt (default 120).
#     Bounds the prompt regardless of how large the corpus grows.
#
# Exit codes: 0 = ran (mined or cache-reused or nothing to mine); 1 = usage
# error; 2 = the external tool call failed or returned nothing.

set -uo pipefail

usage() {
  cat <<'EOF'
Usage: mine-learnings-patterns.sh <project-dir> [--tool '<cli command>'] [--dry-run] [--max-entries N]

  <project-dir>       projects/<client>__<project> directory (active/ and/or archive/)
  --tool '<command>'  shell command taking the prompt on stdin, default: claude code --print
  --dry-run           print the assembled prompt and corpus stats; no tool call, no cache write
  --max-entries N     cap on entries included in the prompt (default 120)

Reads LEARNINGS.md files only. Never writes to a LEARNINGS.md. Never uses embeddings.
EOF
}

if [[ $# -eq 0 || "$1" == "-h" || "$1" == "--help" ]]; then
  usage
  exit 0
fi

project_dir="$1"
shift
if [[ "$project_dir" == --* ]]; then
  echo "mine-learnings-patterns: expected <project-dir> as the first argument, got: $project_dir" >&2
  usage
  exit 1
fi
project_dir="${project_dir%/}"

tool_cmd="claude code --print"
dry_run=0
max_entries=120

while [[ $# -gt 0 ]]; do
  case "$1" in
    --tool)
      tool_cmd="${2:-}"
      shift 2
      ;;
    --tool=*)
      tool_cmd="${1#--tool=}"
      shift
      ;;
    --dry-run)
      dry_run=1
      shift
      ;;
    --max-entries)
      max_entries="${2:-}"
      shift 2
      ;;
    --max-entries=*)
      max_entries="${1#--max-entries=}"
      shift
      ;;
    *)
      echo "mine-learnings-patterns: unknown argument: $1" >&2
      usage
      exit 1
      ;;
  esac
done

if [[ ! "$max_entries" =~ ^[0-9]+$ || "$max_entries" -eq 0 ]]; then
  echo "mine-learnings-patterns: --max-entries must be a positive integer, got: $max_entries" >&2
  exit 1
fi

if [[ -z "$tool_cmd" ]]; then
  echo "mine-learnings-patterns: --tool requires a non-empty command" >&2
  exit 1
fi

if [[ ! -d "$project_dir" ]]; then
  echo "mine-learnings-patterns: project dir not found: $project_dir" >&2
  exit 1
fi

cache_dir="$project_dir/.wos-mined-patterns"
cache_file="$cache_dir/patterns.md"

# ---------------------------------------------------------------------------
# 1. Resolve the LEARNINGS.md files to scan (active/ and archive/, one level
#    of task folders under each, matching every other Fhorja project-scan script).
# ---------------------------------------------------------------------------
files=()
while IFS= read -r f; do
  files+=("$f")
done < <(find "$project_dir/active" "$project_dir/archive" -maxdepth 2 -name 'LEARNINGS.md' 2>/dev/null | sort)

file_count="${#files[@]}"
if [[ "$file_count" -eq 0 ]]; then
  echo "mine-learnings-patterns: no LEARNINGS.md found under $project_dir/active or $project_dir/archive"
  exit 0
fi

hash_string() { # $1 = string -> prints a sha256 hex digest on stdout
  if command -v shasum >/dev/null 2>&1; then
    printf '%s' "$1" | shasum -a 256 | awk '{print $1}'
  elif command -v sha256sum >/dev/null 2>&1; then
    printf '%s' "$1" | sha256sum | awk '{print $1}'
  else
    echo "no-sha256-tool-available"
  fi
}

extract_field() { # $1 = block text, $2 = exact bullet label (e.g. "Tried")
  printf '%s\n' "$1" \
    | grep -E "^[[:space:]]*-[[:space:]]*${2}:" \
    | head -n 1 \
    | sed -E "s/^[[:space:]]*-[[:space:]]*${2}:[[:space:]]*//"
}

# ---------------------------------------------------------------------------
# 2. Parse every file into `## `-delimited blocks and keep only the blocks
#    that carry all four required bullets. One valid entry becomes one line
#    in entries_tmp, tab-separated: relpath, heading, anchor, tried, failed,
#    next, tags. Each extracted field is already a single line (extract_field
#    takes the first matching bullet line), so tabs/newlines never leak in.
# ---------------------------------------------------------------------------
entries_tmp="$(mktemp 2>/dev/null || echo "${TMPDIR:-/tmp}/mine-learnings-patterns.$$")"
trap 'rm -f "$entries_tmp"' EXIT

flush_block() { # $1 = relpath, $2 = block text
  local relpath="$1" block="$2"
  local heading anchor tried failed next tags
  heading="$(printf '%s\n' "$block" | head -n 1 | sed -E 's/^##[[:space:]]*//')"
  anchor="$(extract_field "$block" "Anchor")"
  tried="$(extract_field "$block" "Tried")"
  failed="$(extract_field "$block" "Failed because")"
  next="$(extract_field "$block" "Next time")"
  tags="$(extract_field "$block" "Tags")"
  if [[ -z "$anchor" || -z "$tried" || -z "$failed" || -z "$next" ]]; then
    return 0
  fi
  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
    "$relpath" "$heading" "$anchor" "$tried" "$failed" "$next" "${tags:-(none)}" >> "$entries_tmp"
}

for f in "${files[@]}"; do
  relpath="${f#"$project_dir"/}"
  block=""
  while IFS= read -r line || [[ -n "$line" ]]; do
    if [[ "$line" == "## "* ]]; then
      [[ -n "$block" ]] && flush_block "$relpath" "$block"
      block="$line"$'\n'
    else
      [[ -n "$block" ]] && block="$block$line"$'\n'
    fi
  done < "$f"
  [[ -n "$block" ]] && flush_block "$relpath" "$block"
done

total_entries=0
[[ -s "$entries_tmp" ]] && total_entries="$(wc -l < "$entries_tmp" | tr -d '[:space:]')"

if [[ "$total_entries" -eq 0 ]]; then
  echo "mine-learnings-patterns: found $file_count LEARNINGS.md file(s) but no entry had all four required bullets (Anchor, Tried, Failed because, Next time); nothing to mine."
  exit 0
fi

capped_tmp="$entries_tmp.capped"
trap 'rm -f "$entries_tmp" "$capped_tmp"' EXIT
head -n "$max_entries" "$entries_tmp" > "$capped_tmp"
used_entries=0
[[ -s "$capped_tmp" ]] && used_entries="$(wc -l < "$capped_tmp" | tr -d '[:space:]')"

cap_note=""
if [[ "$total_entries" -gt "$used_entries" ]]; then
  cap_note=" (capped from $total_entries; --max-entries $max_entries)"
fi

# ---------------------------------------------------------------------------
# 3. Assemble the entries block and the one grouping prompt.
# ---------------------------------------------------------------------------
entries_block=""
entry_id=0
while IFS=$'\t' read -r relpath heading anchor tried failed next tags; do
  entry_id=$((entry_id + 1))
  id_label="$(printf 'E%03d' "$entry_id")"
  entries_block="${entries_block}### ${id_label}
- Source: ${relpath}
- Heading: ${heading}
- Anchor: ${anchor}
- Tried: ${tried}
- Failed because: ${failed}
- Next time: ${next}
- Tags: ${tags}

"
done < "$capped_tmp"

prompt="You are grouping a corpus of engineering \"lessons learned\" entries into named recurring-pattern themes.

Each entry below has a heading, an anchor (where the failure was observed), what was tried, why it failed, and what to do differently next time.

Propose the smallest set of named groups such that every entry sharing a genuine recurring root cause or lesson lands in the same group. A named group needs at least two member entries. Entries with no real match to any other entry go under a final \"Ungrouped\" heading, one line each.

Emit each group in exactly this shape:
## <group name: a short phrase naming the recurring pattern>
<one-sentence description of what recurs across the members>
- <Entry ID> -- <Heading> -- <Anchor>
- <Entry ID> -- <Heading> -- <Anchor>

List every member entry of a group on its own line, always by its Entry ID, Heading, and Anchor. Do not invent entries that are not in the corpus below. Do not merge two entries into one group unless they share a real recurring cause. A shared file or command name alone is not enough.

Corpus (${used_entries} entries from ${file_count} LEARNINGS.md file(s)${cap_note}):

${entries_block}"

if [[ "$dry_run" -eq 1 ]]; then
  echo "=== mine-learnings-patterns: dry run ==="
  echo "Project dir: $project_dir"
  echo "LEARNINGS.md files found: $file_count"
  echo "Entries parsed (all 4 required bullets present): $total_entries"
  echo "Entries included in prompt: $used_entries${cap_note}"
  echo "Corpus SHA-256 (of the assembled prompt): $(hash_string "$prompt")"
  echo
  echo "=== assembled prompt ==="
  printf '%s\n' "$prompt"
  exit 0
fi

corpus_sha="$(hash_string "$prompt")"

# ---------------------------------------------------------------------------
# 4. Cache reuse: if the cached corpus SHA-256 matches, print the cached
#    result and say so, without calling the tool (kura checkpoint analog).
# ---------------------------------------------------------------------------
if [[ -f "$cache_file" ]]; then
  cached_sha="$(command grep -E '^- Corpus SHA-256:' "$cache_file" 2>/dev/null | head -n 1 | sed -E 's/^- Corpus SHA-256:[[:space:]]*//')"
  if [[ -n "$cached_sha" && "$cached_sha" == "$corpus_sha" ]]; then
    cat "$cache_file"
    echo
    echo "mine-learnings-patterns: cache reuse (corpus unchanged)"
    exit 0
  fi
fi

# ---------------------------------------------------------------------------
# 5. Call the tool exactly the way evals/scripts/judge.py's call_tool() does:
#    pipe the prompt in on stdin, read the response on stdout.
# ---------------------------------------------------------------------------
err_tmp="$(mktemp 2>/dev/null || echo "${TMPDIR:-/tmp}/mine-learnings-patterns.err.$$")"
trap 'rm -f "$entries_tmp" "$capped_tmp" "$err_tmp"' EXIT

tool_out="$(printf '%s' "$prompt" | $tool_cmd 2>"$err_tmp")"
tool_rc=$?

if [[ "$tool_rc" -ne 0 ]]; then
  echo "mine-learnings-patterns: tool returned $tool_rc: $tool_cmd" >&2
  [[ -s "$err_tmp" ]] && cat "$err_tmp" >&2
  exit 2
fi
# NOTE: deliberately not `${tool_out//[[:space:]]/}` -- bash's own glob-based
# substitution is pathologically slow on a many-KB string (this tool's output
# can be as large as the prompt); `tr` streams through a C implementation.
tool_out_stripped="$(printf '%s' "$tool_out" | tr -d '[:space:]')"
if [[ -z "$tool_out_stripped" ]]; then
  echo "mine-learnings-patterns: tool returned empty stdout: $tool_cmd" >&2
  exit 2
fi

# ---------------------------------------------------------------------------
# 6. Write the cache file (header + result) and print it.
# ---------------------------------------------------------------------------
mkdir -p "$cache_dir"
{
  echo "<!-- mine-learnings-patterns cache: regenerated by scripts/mine-learnings-patterns.sh, do not hand-edit -->"
  echo "# Mined LEARNINGS patterns"
  echo
  echo "- Date: $(date +%Y-%m-%d 2>/dev/null || echo unknown)"
  echo "- Corpus: ${used_entries} entries from ${file_count} LEARNINGS.md file(s) under ${project_dir}${cap_note}"
  echo "- Corpus SHA-256: ${corpus_sha}"
  echo
  printf '%s\n' "$tool_out"
} > "$cache_file"

cat "$cache_file"
exit 0
