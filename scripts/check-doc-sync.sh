#!/usr/bin/env bash
# check-doc-sync.sh -- Fhorja doc-sync validator
#
# Scans curated doc surfaces for references to commands, ADRs, and wos topics
# and verifies that each referenced artifact exists on disk.
#
# Usage:
#   scripts/check-doc-sync.sh [--verbose] [--strict]
#   scripts/check-doc-sync.sh --against HEAD [--repo <path>]
#
# The second form is the renumber check (ADR-0225). It reads only what changed
# against the revision and asks whether an unchanged line still points at it: a
# numbered heading whose number now names another section, a heading whose text
# is gone, or a deleted path. The default form cannot see the first case, because
# an inserted `## 6.` keeps a section 6 in existence. `--repo` points it at another
# git repository; the default is the checkout this script lives in.
#
# Exit codes:
#   0  all refs resolved (or only warnings in non-strict mode)
#   1  one or more broken refs (or warnings in --strict mode)
#   2  usage error, or --against could not read the revision (not measured)

set -u

VERBOSE=0
STRICT=0
AGAINST=""
TARGET_REPO=""

while [ $# -gt 0 ]; do
  case "$1" in
    --verbose) VERBOSE=1 ;;
    --strict)  STRICT=1  ;;
    --against)
      shift
      AGAINST="${1:-}"
      if [ -z "$AGAINST" ]; then echo "doc-sync: --against needs a revision" >&2; exit 2; fi
      ;;
    --repo)
      shift
      TARGET_REPO="${1:-}"
      if [ -z "$TARGET_REPO" ]; then echo "doc-sync: --repo needs a path" >&2; exit 2; fi
      ;;
    -h|--help)
      echo "Usage: $0 [--verbose] [--strict]"
      echo "       $0 --against HEAD [--repo <path>]"
      exit 0
      ;;
    *)
      echo "doc-sync: unknown flag: $1" >&2
      exit 2
      ;;
  esac
  shift
done

if [ -n "$TARGET_REPO" ] && [ -z "$AGAINST" ]; then
  echo "doc-sync: --repo is read only with --against" >&2
  exit 2
fi

# Resolve repo root from this script's location.
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT" || exit 2

# --- The renumber check: --against <rev> (ADR-0225) ------------------------------
# WHY. The defect of record (2026-09-16): a section inserted into AGENTS.md above
# section 6 renumbered it, and seven live "AGENTS.md section 6" citations went stale.
# The default form below exits 0 on that tree (measured 2026-09-23: "10423 refs
# verified, 0 broken"), because it asks only whether a `## 6.` exists, and after an
# insertion one does. Existence cannot see a renumbering; only a comparison with the
# tree before the change can.
#
# WHAT IT READS. Only the change: the markdown files modified or renamed against the
# revision, and the paths it deleted. From each changed markdown file it takes
#   - every numbered heading (`## 6. Title`) whose number now names a different
#     heading, or none;
#   - every heading whose text is gone;
# and it then reads every line that the change did NOT add, in the scan set, for a
# citation of one of those, or of a deleted path. A citation of a heading names the
# file on the same line, the rule scan_agents_sections below already uses. Lines the
# diff added are the change itself: a new line citing the new section 6 is correct.
#
# SCAN SET. Every tracked markdown file except the historical records, the same
# policy the heading scans below state: a record cites the tree as it stood when it
# was written. Excluded: CHANGELOG.md, ROADMAP.md, the numbered ADRs (their Decision
# text is immutable, so a failure there could never be fixed), docs/audit/,
# docs/DELETION_LEDGER.md (it names deleted paths by design), evals/runs/, _internal/,
# the dated token baselines scripts/baseline-*.md, and .claude/ (generated copies of
# commands/, which is scanned). docs/adr/README.md is an index, not a record, and is
# scanned. A line that names a deleted path to say it is gone is spared, with the
# same phrase list the path check below uses.
if [ -n "$AGAINST" ]; then
  TARGET="${TARGET_REPO:-$ROOT}"
  if ! git -C "$TARGET" rev-parse --verify --quiet "${AGAINST}^{commit}" >/dev/null 2>&1; then
    echo "doc-sync --against ${AGAINST}: not measured ($(basename "$TARGET") is not a git repository with a commit ${AGAINST})"
    exit 2
  fi
  TOP="$(git -C "$TARGET" rev-parse --show-toplevel)"
  python3 - "$TOP" "$AGAINST" <<'PY'
import os, re, subprocess, sys

top, rev = sys.argv[1], sys.argv[2]
os.chdir(top)


def git(*args):
    return subprocess.run(["git", *args], capture_output=True, text=True).stdout


HISTORICAL = re.compile(r"^(?:CHANGELOG\.md|ROADMAP\.md|docs/adr/\d{4}-[^/]*\.md|docs/audit/"
                        r"|docs/DELETION_LEDGER\.md|evals/runs/|_internal/|scripts/baseline-|\.claude/)")
absent = re.compile(r"does not exist|doesn't exist|not in the tree|Create an empty|deleted|instead of"
                    r"|no longer|consuming repo|product repo|host repo|your repo", re.I)

deleted, modified = [], []
for row in git("diff", "--name-status", "-M", rev, "--").splitlines():
    parts = row.split("\t")
    kind = parts[0][:1]
    if kind == "D":
        deleted.append(parts[1])
    elif kind == "R":
        deleted.append(parts[1])
        modified.append((parts[1], parts[2]))
    elif kind in ("M", "T"):
        modified.append((parts[1], parts[1]))

# The lines the diff added, per file: those are the change itself and are not read.
added, cur = {}, None
for row in git("diff", "-U0", "--no-color", "-M", rev, "--").splitlines():
    if row.startswith("+++ "):
        cur = row[6:] if row.startswith("+++ b/") else None
        continue
    m = re.match(r"@@ -\S+ \+(\d+)(?:,(\d+))? @@", row)
    if m and cur:
        start, count = int(m.group(1)), int(m.group(2) if m.group(2) is not None else 1)
        added.setdefault(cur, set()).update(range(start, start + count))


def headings(text):
    out, fence = [], False
    for line in text.split("\n"):
        if re.match(r"^\s*(```|~~~)", line):
            fence = not fence
            continue
        m = None if fence else re.match(r"^(#{1,6})\s+(.+?)\s*#*\s*$", line)
        if m:
            out.append(m.group(2).strip())
    return out


def numbered(titles):
    """number -> heading, for numbers that head exactly one heading in the file."""
    seen = {}
    for t in titles:
        m = re.match(r"^(\d+)\.\s", t)
        if m:
            seen.setdefault(m.group(1), []).append(t)
    return {n: ts[0] for n, ts in seen.items() if len(ts) == 1}


def slug(t):
    return re.sub(r"[^\w\- ]", "", t.lower()).strip().replace(" ", "-")


# (file tokens a citing line must carry, pattern, label, kind, the changed file itself).
# Inside the changed file a citation need not name it: AGENTS.md says "See section 6."
targets = []
md_read = 0
for old, new in modified:
    if not old.endswith(".md"):
        continue
    md_read += 1
    before = headings(git("show", f"{rev}:{old}"))
    after = headings(open(new, encoding="utf-8").read()) if os.path.isfile(new) else []
    base = os.path.basename(old)
    tokens = (base, new)
    for t in before:
        if t in after:
            continue
        targets.append((tokens, re.compile(r"#{1,6} " + re.escape(t) + r"(?![\w.])"),
                        f"{base} ## {t}", "removed-heading"))
        if slug(t):
            targets.append((tokens, re.compile(re.escape(base) + "#" + re.escape(slug(t)) + r"(?![\w-])"),
                            f"{base}#{slug(t)}", "removed-heading"))
    now = numbered(after)
    for n, t in numbered(before).items():
        if now.get(n) != t:
            targets.append((tokens, re.compile(r"(?:[Ss]ection|§)\s?" + n + r"(?!\d)(?!\.\d)"),
                            f"{base} section {n}", "renumbered-section"))

scan = [f for f in git("ls-files", "-z").split("\0")
        if f.endswith(".md") and not HISTORICAL.match(f) and os.path.isfile(f)]

if not targets and not deleted:
    print(f"doc-sync --against {rev}: {md_read} changed markdown file(s) and 0 deleted path(s) read; "
          f"no heading or path the change removed, so nothing can point at one")
    sys.exit(0)

hits = []
for f in scan:
    skip = added.get(f, set())
    try:
        lines = open(f, encoding="utf-8").read().split("\n")
    except (OSError, UnicodeDecodeError):
        continue
    for n, line in enumerate(lines, 1):
        if n in skip or re.match(r"^\s*#", line):
            continue
        for (base, home), pat, label, kind in targets:
            if (f == home or base in line) and pat.search(line):
                hits.append((kind, label, f, n))
        if not deleted or absent.search(line):
            continue
        for path in deleted:
            if re.search(r"(?<![\w./-])" + re.escape(path) + r"(?![\w/-])", line):
                hits.append(("deleted-path", path, f, n))
                continue
            for link in re.findall(r"\]\((\.{0,2}/?[^)#\s]+)", line):
                if os.path.normpath(os.path.join(os.path.dirname(f), link)) == path:
                    hits.append(("deleted-path", path, f, n))

for kind, label, f, n in hits:
    print(f"doc-sync: BROKEN {kind} ref '{label}' in {f}:{n}")
print(f"doc-sync --against {rev}: {md_read} changed markdown file(s) and {len(deleted)} deleted path(s) read, "
      f"{len(hits)} stale reference(s)")
sys.exit(1 if hits else 0)
PY
  exit $?
fi

COMMANDS_DIR="commands"
ADR_DIR="docs/adr"
WOS_DIR="wos"

# Curated scan surfaces. Missing files are skipped silently.
# Scan set. Widened on 2026-08-21 from the six root docs to the surfaces that actually carry the
# citations. Measured: the six-file set verified 1790 refs and reported "0 broken", while 899 ADR refs
# inside commands/ and 554 inside wos/ were never resolved at all. Widening takes it to 6951 verified
# and surfaced exactly one real break (wos/godot-2d-architecture.md:67 cited a wos topic that does not
# exist), fixed in the same commit so the gate is born green. The second loop below already iterated
# these same paths for WOS headings, so the headline count was padded by the very files whose ADR refs
# went unchecked.
# Widened again on 2026-09-23 (ADR-0225) by CONTRIBUTING.md, docs/adr/README.md and
# .github/pull_request_template.md: the renumber check found live "AGENTS.md section 6"
# citations in all three, and no loop read any of them. The ADR index joins only the
# two loops that resolve citations of live structure (spec headings and AGENTS.md
# sections). Its rows name a retired wos topic and the reserved ADR-0037 gap on purpose,
# as the record of what each ADR did, so the existence scans below would fail on history.
SURFACES="
CLAUDE.md
AGENTS.md
README.md
CONTRIBUTING.md
.github/pull_request_template.md
docs/FAQ.md
docs/MIGRATION.md
ROADMAP.md
WORKFLOW_OPERATING_SYSTEM.md
commands/*.md
commands/_shared/*.md
wos/*.md
templates/*.md
"

# WOS section/anchor reference integrity (N3, 2026-07-18). Catches the silent
# failure mode of a WORKFLOW_OPERATING_SYSTEM.md refactor: a citation that names
# a '## ' section or '### ' sub-anchor which no longer resolves to a real heading.
BT=$(printf '\140')  # literal backtick, kept out of awk/grep source
WOS_SPEC="WORKFLOW_OPERATING_SYSTEM.md"
WOS_HEADINGS="$(grep -E '^#{2,3} ' "$WOS_SPEC" 2>/dev/null || true)"

VERIFIED=0
BROKEN=0
WARNINGS=0
BROKEN_LINES=""
WARN_LINES=""

log_verbose() {
  if [ "$VERBOSE" -eq 1 ]; then
    echo "doc-sync: checked $1"
  fi
}

record_broken() {
  # $1=file $2=line-no $3=ref $4=kind
  BROKEN=$((BROKEN + 1))
  BROKEN_LINES="${BROKEN_LINES}doc-sync: BROKEN $4 ref '$3' in $1:$2
"
}

record_warning() {
  WARNINGS=$((WARNINGS + 1))
  WARN_LINES="${WARN_LINES}doc-sync: WARN  $2 in $1
"
}

command_exists() {
  name="$1"
  if [ -f "$COMMANDS_DIR/$name.md" ]; then
    return 0
  fi
  if [ -f "$COMMANDS_DIR/$name/SKILL.md" ]; then
    return 0
  fi
  return 1
}

adr_exists() {
  num="$1"
  # Match docs/adr/NNNN-*.md
  for f in "$ADR_DIR/$num"-*.md; do
    [ -f "$f" ] && return 0
  done
  return 1
}

wos_topic_exists() {
  topic="$1"
  [ -f "$WOS_DIR/$topic.md" ]
}

wos_heading_exists() {
  # $1 = a heading token like "## Global output contract" or "### Adaptive handoff"
  printf '%s\n' "$WOS_HEADINGS" | grep -Fxq -- "$1"
}

scan_file() {
  file="$1"
  [ -f "$file" ] || return 0

  # 1. Command refs: backtick-wrapped tokens like `command-name`.
  #    Heuristic: lowercase, digits, hyphens; len 2..64; no slashes/dots.
  awk '
    {
      line = $0
      lineno = NR
      while (match(line, /`[a-z][a-z0-9-]+`/)) {
        tok = substr(line, RSTART + 1, RLENGTH - 2)
        print "CMD\t" lineno "\t" tok
        line = substr(line, RSTART + RLENGTH)
      }
    }
  ' "$file" | while IFS=$(printf '\t') read -r kind lineno tok; do
    [ -z "$tok" ] && continue
    if command_exists "$tok"; then
      VERIFIED=$((VERIFIED + 1))
      log_verbose "$file:$lineno command '$tok'"
      echo "OK"
    else
      # Could be a shell command (`ls`, `grep`) -- treat as unknown shape.
      if [ "$STRICT" -eq 1 ]; then
        echo "WARN $file:$lineno unknown backtick token '$tok'"
      fi
    fi
  done >/dev/null 2>&1 || true

  # Re-run command scan in current shell so counters update.
  while IFS=$(printf '\t') read -r kind lineno tok; do
    [ -z "$tok" ] && continue
    if command_exists "$tok"; then
      VERIFIED=$((VERIFIED + 1))
      log_verbose "$file:$lineno command '$tok'"
    else
      # Unknown backtick token: shell command, code symbol, or broken ref.
      # Only flag as warning in --strict mode.
      if [ "$STRICT" -eq 1 ]; then
        record_warning "$file:$lineno" "unknown backtick token '$tok' (not a registered command)"
      fi
    fi
  done <<EOF
$(awk '
    {
      line = $0
      lineno = NR
      while (match(line, /`[a-z][a-z0-9-]+`/)) {
        tok = substr(line, RSTART + 1, RLENGTH - 2)
        print "CMD\t" lineno "\t" tok
        line = substr(line, RSTART + RLENGTH)
      }
    }
  ' "$file")
EOF

  # 2. ADR refs: ADR-NNNN or [NNNN](./docs/adr/...) or (docs/adr/NNNN-...).
  while IFS=$(printf '\t') read -r lineno num; do
    [ -z "$num" ] && continue
    if adr_exists "$num"; then
      VERIFIED=$((VERIFIED + 1))
      log_verbose "$file:$lineno ADR-$num"
    else
      record_broken "$file" "$lineno" "ADR-$num" "ADR"
    fi
  done <<EOF
$(awk '
    {
      line = $0
      lineno = NR
      # ADR-NNNN style
      tmp = line
      while (match(tmp, /ADR-[0-9][0-9][0-9][0-9]/)) {
        num = substr(tmp, RSTART + 4, 4)
        print lineno "\t" num
        tmp = substr(tmp, RSTART + RLENGTH)
      }
      # docs/adr/NNNN- style paths
      tmp = line
      while (match(tmp, /docs\/adr\/[0-9][0-9][0-9][0-9]-/)) {
        num = substr(tmp, RSTART + 9, 4)
        print lineno "\t" num
        tmp = substr(tmp, RSTART + RLENGTH)
      }
    }
  ' "$file" | sort -u)
EOF

  # 3. wos topic refs: wos/<topic>.md
  while IFS=$(printf '\t') read -r lineno topic; do
    [ -z "$topic" ] && continue
    if wos_topic_exists "$topic"; then
      VERIFIED=$((VERIFIED + 1))
      log_verbose "$file:$lineno wos/$topic.md"
    else
      record_broken "$file" "$lineno" "wos/$topic.md" "wos-topic"
    fi
  done <<EOF
$(awk '
    {
      line = $0
      lineno = NR
      while (match(line, /wos\/[a-z0-9-]+\.md/)) {
        ref = substr(line, RSTART, RLENGTH)
        # Strip "wos/" prefix and ".md" suffix
        topic = substr(ref, 5, length(ref) - 7)
        print lineno "\t" topic
        line = substr(line, RSTART + RLENGTH)
      }
    }
  ' "$file" | sort -u)
EOF
}

scan_wos_headings() {
  file="$1"
  [ -f "$file" ] || return 0
  # Only lines that name the spec file carry a WOS section/anchor citation.
  # Extract backtick-wrapped `## X` / `### Y` tokens from those lines and verify
  # each resolves to a real heading in WORKFLOW_OPERATING_SYSTEM.md.
  while IFS=$(printf '\t') read -r lineno tok; do
    [ -z "$tok" ] && continue
    # Skip non-WOS-heading tokens that recur on WOS-mentioning lines:
    # placeholders, and the command-OUTPUT block names (which are produced by a
    # command, not headings in the spec) even though they sit next to a WOS cite.
    case "$tok" in
      *"<"*|*">"*) continue ;;
      "### Handoff"|"### Artifact changes"|"### Command transcript"|"### Definition of done"|"### Definition of done (command output)"|"### Command transcript (standard)"|"### Standard output layout (required)") continue ;;
    esac
    if wos_heading_exists "$tok"; then
      VERIFIED=$((VERIFIED + 1))
      log_verbose "$file:$lineno WOS heading '$tok'"
    else
      record_broken "$file" "$lineno" "$tok" "wos-heading"
    fi
  done <<EOF
$(awk -v bt="$BT" '
    index($0, "WORKFLOW_OPERATING_SYSTEM") > 0 {
      line = $0
      lineno = NR
      re = bt "##+ [^" bt "]+" bt
      while (match(line, re)) {
        tok = substr(line, RSTART + 1, RLENGTH - 2)
        print lineno "\t" tok
        line = substr(line, RSTART + RLENGTH)
      }
    }
  ' "$file" | sort -u)
EOF
}

for surface in $SURFACES; do
  scan_file "$surface"
done

# WOS heading-resolution scan over the ACTIVE-contract surfaces where a dangling
# WOS ref actually breaks runtime behavior. Historical records (ROADMAP.md,
# CHANGELOG.md, docs/adr/*.md) are deliberately excluded: they cite the spec as
# it stood when written, and a since-renamed anchor there is expected drift, not
# a bug. Limitation: this check verifies a cited heading EXISTS, not that it
# still contains what the citation implies (semantic staleness is out of scope).
for f in CLAUDE.md README.md CONTRIBUTING.md docs/adr/README.md .github/pull_request_template.md docs/FAQ.md docs/MIGRATION.md "$WOS_SPEC" commands/*.md commands/_shared/*.md wos/*.md templates/*.md; do
  scan_wos_headings "$f"
done

# AGENTS.md section-number references (B3, 2026-09-17). The rule that changing a
# rule needs a superseding ADR lives in a NUMBERED section of AGENTS.md, and other
# files cite it by number. Inserting a section renumbers everything below it and
# every one of those citations goes stale in silence: this checker did not read
# AGENTS.md at all, and its section logic resolves headings only inside the spec.
# Measured 2026-09-17: seven live "AGENTS.md section 6" citations.
# Scope mirrors the policy directly above rather than inventing a second one.
# Historical records are excluded, and here that exclusion is load-bearing and not
# merely consistent: one of the seven sits inside ADR-0187's `## Decision`, whose
# text section 5 of AGENTS.md declares immutable. A check that failed on it would
# be a check nobody can ever make pass.
scan_agents_sections() {
  file="$1"
  [ -f "$file" ] || return 0
  [ -f AGENTS.md ] || return 0
  while IFS=$(printf '\t') read -r lineno num; do
    [ -z "$num" ] && continue
    if grep -q "^## ${num}\. " AGENTS.md; then
      VERIFIED=$((VERIFIED + 1))
      log_verbose "$file:$lineno AGENTS.md section $num"
    else
      record_broken "$file" "$lineno" "AGENTS.md section $num" "agents-section"
    fi
  done <<EOF
$(awk '
    index($0, "AGENTS.md") > 0 {
      line = $0
      while (match(line, /[Ss]ection [0-9]+/)) {
        tok = substr(line, RSTART, RLENGTH)
        sub(/[Ss]ection /, "", tok)
        print NR "\t" tok
        line = substr(line, RSTART + RLENGTH)
      }
    }
  ' "$file" | sort -u)
EOF
}

for f in CLAUDE.md AGENTS.md README.md CONTRIBUTING.md docs/adr/README.md .github/pull_request_template.md docs/FAQ.md docs/MIGRATION.md docs/DELETION_LEDGER.md "$WOS_SPEC" commands/*.md commands/_shared/*.md wos/*.md templates/*.md; do
  scan_agents_sections "$f"
done

# File paths, bug classes, relative links and next-step command names (docs drift
# audit, gap 5, 2026-09-23). Everything above resolves commands, ADR numbers, wos
# topics, spec headings and AGENTS.md sections, and nothing else. So `AGENTS.md`
# could send people to `templates/ADR.template.md`, a topic could name
# `scripts/check-model-routing-cadence.sh`, templates could cite bug classes that
# were never written, a context-budget line could route to `command-router`, and
# the ADR-0162 Status link could point at a renamed ADR, all with this checker
# green, because it did not read paths, did not read docs/adr/ or the eval
# scenarios, and only warned on an unknown command under --strict.
#
# Scope, and why it stops where it does:
#   - Paths are checked under the prefixes this repository owns. `docs/research/`,
#     `docs/app/` and a consuming repo's `scripts/` are product-repo paths the
#     design commands write to, so `docs/` is limited to adr/, security/, audit/.
#   - A line that names a path in order to say it is absent ("does not exist",
#     "Create an empty", "instead of") is not a reference to it.
#   - Relative links are read in docs/adr/ and the scenarios, where the ADR-0162
#     break lived. An ADR's Decision text stays frozen; a link in it is not
#     Decision text, and ADR-0162's own fix was a link fix.
#   - A section cited beside a wos topic (`wos/x.md` `## Y`, or (section "Y")) must be a
#     heading of that topic or a section key in its own table.
#   - An unknown name after `Run now:` or `routes to` is a failure, not a warning:
#     that position is where a reader or a model takes the next step. So is an
#     unknown name inside a parenthesized list of commands, the `command-router`
#     shape. A line that names the token to say it is not a command is the
#     negative example scenario 85 grades, and is spared. Any other unknown
#     backticked token stays a --strict warning: shell commands and field names
#     share that shape, and failing on them would make the check unpassable.
EXTRA_OUT="$(python3 - <<'PY'
import glob, os, re

def files(*patterns):
    out = []
    for pat in patterns:
        out.extend(sorted(glob.glob(pat)))
    return [f for f in out if os.path.isfile(f)]

surfaces = files("CLAUDE.md", "AGENTS.md", "README.md", "CONTRIBUTING.md",
                 ".github/pull_request_template.md", "docs/FAQ.md", "docs/MIGRATION.md",
                 "docs/HOOKS.md", "ROADMAP.md", "WORKFLOW_OPERATING_SYSTEM.md", "WORKFLOW_DEMO.md",
                 "COMMAND_PROMPT_STUBS.md", "commands/*.md", "commands/*/SKILL.md",
                 "commands/_shared/*.md", "wos/*.md", "templates/*.md", "templates/*/*.md",
                 "evals/README.md", "evals/scenarios/*.md")
commands = {os.path.basename(f)[:-3] for f in glob.glob("commands/*.md")}
commands |= {os.path.basename(os.path.dirname(f)) for f in glob.glob("commands/*/SKILL.md")}

placeholder = re.compile(r"[<>*{}\[\]$]|\.\.\.|NNNN|XXXX")
absent = re.compile(r"does not exist|doesn't exist|not in the tree|Create an empty|deleted|instead of"
                    r"|no longer|consuming repo|product repo|host repo|your repo", re.I)
path_re = re.compile(r"`((?:templates|scripts|wos|evals|docs/adr|docs/security|docs/audit)/[^`\s]+\.(?:md|sh|py|json))`")
bug_re = re.compile(r"(?<![\w/.-])bug-classes/([a-z0-9_-]+)\.md|\*\*Bug class:\*\*\s*`([a-z0-9-]+)`")
next_re = re.compile(r"Run now:\**\s*`?/?([a-z][a-z0-9-]+)"
                     r"|\b(?:routes?|routed|routing) (?:it |them )?(?:back )?to `/?([a-z][a-z0-9]*-[a-z0-9-]+)`")
not_command = re.compile(r"not a (?:Fhorja )?command|no `commands/|is not a command|or any name"
                         r"|or any slash command", re.I)
# Names that follow "route to" and are not commands: the commit-evidence floor's evidence
# classes (wos/closure-floors.md), which a run routes its work to.
ROUTE_CLASSES = {"ref-attested", "commit-ref"}
link_re = re.compile(r"\]\((\.{1,2}/[^)#\s]+)")
# A section of a wos topic cited next to it: `wos/x.md` `## Y`, `wos/x.md ## Y`, or
# `wos/x.md` (section "Y"), the shape scenario 32 used for a section that never existed.
section_re = re.compile(r"`?(wos/[a-z0-9-]+\.md)`?\s*(?:`(#{2,4} [^`]+)`|\(section \"([^\"]+)\"\)"
                        r"|(#{2,4} [A-Z][^`,;)\n]*?)(?=[`,;)]|$))")
# A parenthesized list of backticked hyphenated names that contains at least one real command
# is a list of commands, so every name in it must be one: "(`what-next`, `command-router`)".
_name = r"`[a-z][a-z0-9]*-[a-z0-9-]+`"
list_re = re.compile(r"\(((?:" + _name + r"(?:,\s*(?:and |or )?|\s+(?:and|or)\s+))+" + _name + r")\)")

verified = 0
for f in surfaces:
    for n, line in enumerate(open(f, encoding="utf-8"), 1):
        spared = absent.search(line)
        for m in path_re.finditer(line):
            ref = m.group(1)
            if placeholder.search(ref) or spared:
                continue
            if os.path.exists(ref):
                verified += 1
            else:
                print(f"BROKEN\tpath\t{ref}\t{f}:{n}")
        for m in bug_re.finditer(line):
            ref = m.group(1) or m.group(2)
            if spared:
                continue
            if os.path.isfile(f"wos/bug-classes/{ref}.md"):
                verified += 1
            else:
                print(f"BROKEN\tbug-class\t{ref}\t{f}:{n}")
        for m in section_re.finditer(line):
            topic = m.group(1)
            name = re.sub(r"^#+\s*", "", (m.group(2) or m.group(3) or m.group(4) or "")).strip()
            if not name or placeholder.search(name) or not os.path.isfile(topic) or spared:
                continue
            text = open(topic, encoding="utf-8").read()
            heads = [re.sub(r"^#+\s*", "", h).strip() for h in re.findall(r"(?m)^#{1,6} .+$", text)]
            # A heading, or a section named as a key in the topic's own table (`## Decision history`
            # in wos/substrate-peers.md is a row about DECISIONS.md, and citing it is correct).
            if any(h == name or h.startswith(name) for h in heads) or f"`## {name}`" in text:
                verified += 1
            else:
                print(f"BROKEN\ttopic-section\t{topic} {name}\t{f}:{n}")
        for m in list_re.finditer(line):
            names = re.findall(r"`([a-z0-9-]+)`", m.group(1))
            if not any(x in commands for x in names) or not_command.search(line):
                continue
            for ref in names:
                if ref in commands:
                    verified += 1
                else:
                    print(f"BROKEN\tcommand-list\t{ref}\t{f}:{n}")
        for m in next_re.finditer(line):
            ref = m.group(1) or m.group(2)
            if ref in ("none", "skill") or ref in ROUTE_CLASSES or not_command.search(line):
                continue
            if ref in commands:
                verified += 1
            else:
                print(f"BROKEN\tnext-step\t{ref}\t{f}:{n}")

for f in files("docs/adr/*.md", "evals/scenarios/*.md", "evals/README.md"):
    for n, line in enumerate(open(f, encoding="utf-8"), 1):
        for m in link_re.finditer(line):
            ref = m.group(1)
            if placeholder.search(ref):
                continue
            if os.path.exists(os.path.normpath(os.path.join(os.path.dirname(f), ref))):
                verified += 1
            else:
                print(f"BROKEN\tlink\t{ref}\t{f}:{n}")
print(f"VERIFIED\t{verified}")
PY
)"
while IFS=$(printf '\t') read -r tag kind ref where; do
  case "$tag" in
    VERIFIED) VERIFIED=$((VERIFIED + kind)) ;;
    BROKEN) record_broken "${where%:*}" "${where##*:}" "$ref" "$kind" ;;
  esac
done <<EOF
$EXTRA_OUT
EOF

# Emit results.
if [ -n "$WARN_LINES" ]; then
  printf "%s" "$WARN_LINES"
fi

if [ "$BROKEN" -gt 0 ]; then
  printf "%s" "$BROKEN_LINES"
  echo "doc-sync: $VERIFIED refs verified, $BROKEN broken, $WARNINGS warnings"
  exit 1
fi

if [ "$STRICT" -eq 1 ] && [ "$WARNINGS" -gt 0 ]; then
  echo "doc-sync: $VERIFIED refs verified, 0 broken, $WARNINGS warnings (strict)"
  exit 1
fi

echo "doc-sync: $VERIFIED refs verified, 0 broken"
exit 0
