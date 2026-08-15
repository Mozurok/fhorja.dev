#!/usr/bin/env bash
# validate-bug-class-schema.sh -- advisory shape check for wos/bug-classes/*.md
#
# The bug-class template schema is normative: 7 required sections plus 2
# optional ones (project design doc, "Sections (7 required + 2 optional)").
# `commands/repo-consistency-sweep.md` Step 5 dispatches an analysis subagent
# using each class's `## Analysis prompt` applied to the slices in
# `## Retrieval`, so a template missing those cannot be dispatched at all: it
# sits in the registry and silently produces no analysis. `lint-commands.sh`
# counts template files and distinct categories; nothing checked their shape,
# which is how a fifth of the catalog drifted into a different section schema
# without a single failing gate.
#
# Conformance means all 7 REQUIRED sections present AND the two the sweep
# actually consumes (`## Analysis prompt`, `## Retrieval`) carrying a body.
# The body check is not pedantry: a template with all 7 headings and nothing
# under them is DISPATCHABLE, so the sweep runs it and reports clean, which is
# strictly worse than the visible failure this validator was written to catch.
# The other five sections are checked for presence only; an empty severity
# rubric degrades the finding, it does not fake a passing scan.
#
# All three checks read the file through one fence-aware filter. A `## ` line
# inside a fenced code block is sample text: several templates show a heading
# as an example of what to look for, and reading those as real headings made a
# missing section look present, let a fenced copy mask a hollow section, and
# reported sample text as out-of-schema drift.
#
# Two further signals are reported separately as advisories, because they
# indicate drift without making a template undispatchable:
#   - sections outside the 7 required plus 2 optional
#   - frontmatter keys beyond the 8 canonical ones
# Keeping them separate is deliberate: conflating them would make one stray
# heading read the same as a template the sweep cannot run.
#
# Usage:   validate-bug-class-schema.sh [--verbose] [<dir>]
#          <dir> defaults to wos/bug-classes relative to the repo root.
# Output:  one summary line, always; per-file detail under --verbose.
# Exit:    ALWAYS 0. This is advisory, matching scripts/memory-lint.sh and
#          scripts/rank-learnings.sh. ADR-0023 rejected hard fail on threshold
#          crossing as too aggressive, so a shape problem is reported, never
#          enforced. Callers that want a gate must read the counts.
#
# bash 3.2 compatible: no associative arrays (the Bash tool runs zsh, where
# they silently return empty), no mapfile, no readarray.

set -uo pipefail

VERBOSE=0
DIR=""

while [ $# -gt 0 ]; do
  case "$1" in
    --verbose) VERBOSE=1; shift ;;
    # Print the leading comment block, stopping at the first non-comment line.
    # Range-free so the help does not silently truncate when the header grows.
    -h|--help) awk 'NR==1{next} /^#/{sub(/^# ?/,"");print;next} {exit}' "$0"; exit 0 ;;
    *)         DIR="$1"; shift ;;
  esac
done

if [ -z "$DIR" ]; then
  script_dir="$(cd "$(dirname "$0")" && pwd)"
  DIR="$(dirname "$script_dir")/wos/bug-classes"
fi

if [ ! -d "$DIR" ]; then
  echo "BUG-CLASS-SCHEMA: n/a (no such directory: $DIR)"
  exit 0
fi

# The 7 required sections, in schema order. Space-delimited with a separator
# that cannot appear in a heading, so bash 3.2 can iterate without an array of
# multi-word entries.
REQUIRED='Trigger|Detection|Retrieval|Analysis prompt|Severity rubric|Confidence factors|Examples'
# The two sections repo-consistency-sweep Step 5 reads to build its dispatch.
# These are checked for a body, not only a heading. Pipe-delimited and iterated
# under IFS='|' like REQUIRED, because "Analysis prompt" contains a space and
# default word splitting would break it into two names that match nothing.
SWEEP_CONSUMED='Retrieval|Analysis prompt'
ALLOWED_RE='^## (Trigger|Detection|Retrieval|Analysis prompt|Severity rubric|Confidence factors|Examples|Reversibility check|Perspective-based prompts)$'
CANONICAL_KEYS='name category default-severity cwe languages file-patterns perspectives reversibility-check'

# --- the fence-aware view every check below reads ---------------------------
#
# Only the heading marker is neutralised: the line is re-emitted with a leading
# space, so it no longer matches `^## ` while staying non-empty. That matters,
# because a section whose entire body is a code block must still read as having
# a body; blanking the line instead would turn those into false hollows.
#
# Recognised: backtick and tilde fences of 3 or more markers, an opening fence
# indented up to 3 spaces, a closing fence of the same character and at least
# the opener's length with nothing after it, and an unclosed fence running to
# EOF. All four follow CommonMark.
#
# Not recognised: a fence indented 4 or more spaces, and fences nested inside
# blockquotes or list items. None of them can hide anything from these checks,
# which all anchor `## ` at column 0; a heading-shaped line inside those
# constructs carries its own prefix or indentation and never matched anyway.
#
# This is the second fence scanner in the repository. evals/scripts/
# structural-evals.py has _fence_walk, hardened well past this one. Folding the
# two together is real work and deliberately not attempted here.
fence_filter() {
  awk '
    BEGIN { fence = 0; fchar = ""; flen = 0 }
    {
      probe = $0
      sub(/^ ? ? ?/, "", probe)
      c = substr(probe, 1, 1)
      n = 0
      if (c == "`" || c == "~") {
        while (substr(probe, n + 1, 1) == c) { n++ }
      }
      if (fence) {
        if (c == fchar && n >= flen) {
          rest = substr(probe, n + 1)
          gsub(/[ \t]/, "", rest)
          if (rest == "") { fence = 0; fchar = ""; flen = 0 }
        }
      } else if (n >= 3) {
        fence = 1; fchar = c; flen = n
      }
      if (fence && /^## /) { print " " $0 } else { print $0 }
    }
    # An unclosed fence runs to end of document per CommonMark, so everything
    # after it is sample text and every heading in it disappears. That is the
    # correct reading, and it is also why the template must not be reported as
    # simply missing those sections: the author would go looking for headings
    # that are right there. Exit 3 so the caller can name the real cause.
    END { if (fence) exit 3 }
  ' "$1"
}

# One scratch file, reused per template. Filtering into a file rather than a
# pipeline keeps `grep -q` usable: under `set -o pipefail` grep -q exits at the
# first match and the writer takes SIGPIPE, which reports 141 on a match.
FILTERED="$(mktemp "${TMPDIR:-/tmp}/bug-class-schema.XXXXXX")" || {
  echo "BUG-CLASS-SCHEMA: n/a (could not create a temp file)"
  exit 0
}
trap 'rm -f "$FILTERED"' EXIT

scanned=0
conforming=0
nonconforming=0
extra_sections=0
noncanonical_fm=0

nonconforming_names=''
extra_names=''
fm_names=''

for f in "$DIR"/*.md; do
  [ -e "$f" ] || continue
  base="$(basename "$f")"
  case "$base" in _*) continue ;; esac
  scanned=$((scanned + 1))
  # Three outcomes, and the two that are not success must never look like a
  # template that merely lost some sections. 3 is an unclosed fence (named in
  # the reason below); anything else is the filter itself failing, which would
  # otherwise leave an empty view and report every section as missing.
  fence_filter "$f" > "$FILTERED"
  filter_rc=$?
  unclosed=''
  case "$filter_rc" in
    0) ;;
    3) unclosed='unclosed code fence swallows the rest of the file' ;;
    *) echo "BUG-CLASS-SCHEMA: n/a (fence filter failed on ${base}, exit ${filter_rc})"
       exit 0 ;;
  esac

  # --- required sections: present ---
  missing=''
  found=0
  old_ifs="$IFS"
  IFS='|'
  for sec in $REQUIRED; do
    if grep -q "^## ${sec}\$" "$FILTERED"; then
      found=$((found + 1))
    else
      missing="${missing}${missing:+, }${sec}"
    fi
  done
  IFS="$old_ifs"

  # --- the two the sweep consumes: present AND non-empty ---
  # A heading with nothing under it still dispatches, so presence alone would
  # let a hollow template pass as conforming and make the sweep report clean.
  hollow=''
  old_ifs="$IFS"
  IFS='|'
  for sec in $SWEEP_CONSUMED; do
    IFS="$old_ifs"
    if grep -q "^## ${sec}\$" "$FILTERED"; then   # absence is already counted in `missing`
      awk -v sec="## ${sec}" '
        $0 == sec { inside = 1; next }
        /^## /    { inside = 0 }
        inside && NF { body = 1 }
        END { exit !body }
      ' "$FILTERED" || hollow="${hollow}${hollow:+, }${sec}"
    fi
    IFS='|'
  done
  IFS="$old_ifs"

  if [ "$found" -eq 7 ] && [ -z "$hollow" ]; then
    conforming=$((conforming + 1))
  else
    nonconforming=$((nonconforming + 1))
    reason="$missing"
    if [ -n "$hollow" ]; then
      reason="${reason}${reason:+; }empty: ${hollow}"
    fi
    # First, because it explains the other two: with a fence left open, the
    # missing-section list is a symptom rather than the defect.
    if [ -n "$unclosed" ]; then
      reason="${unclosed}${reason:+; }${reason}"
    fi
    nonconforming_names="${nonconforming_names}${base}|${found}|${reason}
"
  fi

  # --- advisory: sections outside the schema ---
  n_extra=$(grep '^## ' "$FILTERED" | grep -vcE "$ALLOWED_RE")
  if [ "$n_extra" -gt 0 ]; then
    extra_sections=$((extra_sections + 1))
    extra_list=$(grep '^## ' "$FILTERED" | grep -vE "$ALLOWED_RE" | sed 's/^## //' | tr '\n' ',' | sed 's/,$//')
    extra_names="${extra_names}${base}|${extra_list}
"
  fi

  # --- advisory: frontmatter keys beyond the canonical 8 ---
  # Case-insensitive and indentation-tolerant on purpose: YAML is case-sensitive,
  # so `Priority:` is a different key from `priority:` and must still be reported
  # as non-canonical. A lowercase-anchored pattern reported it as clean.
  keys=$(sed -n '2,/^---$/p' "$f" | grep -E '^[[:space:]]*[A-Za-z][A-Za-z0-9_-]*:' | sed 's/^[[:space:]]*//; s/:.*//')
  stray=''
  for k in $keys; do
    case " $CANONICAL_KEYS " in
      *" $k "*) ;;
      *) stray="${stray}${stray:+, }${k}" ;;
    esac
  done
  if [ -n "$stray" ]; then
    noncanonical_fm=$((noncanonical_fm + 1))
    fm_names="${fm_names}${base}|${stray}
"
  fi
done

if [ "$VERBOSE" -eq 1 ]; then
  if [ "$nonconforming" -gt 0 ]; then
    echo "--- non-conforming ---"
    printf '%s' "$nonconforming_names" | while IFS='|' read -r name n reason; do
      [ -n "$name" ] || continue
      # `reason` already distinguishes the two failure kinds: a bare list is
      # missing headings, an "empty:" segment is a heading with no body.
      echo "  ${name}: ${n}/7 sections present, ${reason}"
    done
  fi
  if [ "$extra_sections" -gt 0 ]; then
    echo "--- sections outside the schema (advisory) ---"
    printf '%s' "$extra_names" | while IFS='|' read -r name list; do
      [ -n "$name" ] || continue
      echo "  ${name}: ${list}"
    done
  fi
  if [ "$noncanonical_fm" -gt 0 ]; then
    echo "--- frontmatter keys beyond the canonical 8 (advisory) ---"
    printf '%s' "$fm_names" | while IFS='|' read -r name list; do
      [ -n "$name" ] || continue
      echo "  ${name}: ${list}"
    done
  fi
fi

echo "BUG-CLASS-SCHEMA: ${conforming} conforming / ${nonconforming} non-conforming / ${scanned} scanned (advisory; ${extra_sections} with out-of-schema sections, ${noncanonical_fm} with non-canonical frontmatter keys)"

exit 0
