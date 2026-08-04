#!/usr/bin/env bash
# sync-shared-blocks.sh
#
# Propagates the canonical content of `commands/_shared/<name>.md` into every
# command file that declares a `<!-- shared:<name> -->` marker.
#
# Workflow:
#   1. Edit `commands/_shared/<name>.md` with the new canonical body.
#   2. Run this script. It rewrites the matching section body in each
#      command file that declares the marker for `<name>`.
#   3. Run `./scripts/lint-commands.sh` to confirm drift is zero.
#
# Idempotent: running the script when nothing changed produces no diff.
#
# Exit codes:
#   0 = success (any number of files updated)
#   1 = nothing propagated. Either a command file declares an unknown marker (no
#       canonical file found), or the codename gate refused: a listed codename was
#       found in a block, or the guard is missing, unparseable, or exited a code
#       that is neither a verdict nor a skip. The printed message names which.
#   2 = invocation error

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
COMMANDS_DIR="${REPO_ROOT}/commands"
SHARED_DIR="${COMMANDS_DIR}/_shared"

usage() {
  cat <<'EOF'
Usage: scripts/sync-shared-blocks.sh [options]

Propagates content from commands/_shared/<name>.md into every command file
that declares a <!-- shared:<name> --> marker.

Options:
  --dry-run     Show which files would change without writing them.
  --verbose     Print every file inspected, not just changed ones.
  --help, -h    Show this message.

Exit codes:
  0 = success
  1 = nothing propagated (unknown marker referenced, or the codename gate refused)
  2 = invocation error
EOF
}

DRY_RUN=0
VERBOSE=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run) DRY_RUN=1 ;;
    --verbose) VERBOSE=1 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
  shift
done

if [[ ! -d "$SHARED_DIR" ]]; then
  echo "Error: shared directory not found at $SHARED_DIR" >&2
  exit 2
fi

# Codename gate, BEFORE anything is written. A shared block is copied into every
# command declaring its marker, and each command is then compiled into a tracked
# SKILL.md, so one codename here reaches roughly 195 tracked files. The lint finds
# that only on a later run, which is after it already happened.
#
# The gate scans a COPY of the blocks outside any git work tree, and that detail is
# the whole point. check-mirror-codenames.sh scans with `git grep` when its target
# sits inside a work tree, which reads TRACKED files only. That is right for its
# usual job (auditing what is published) and wrong here: the propagator enumerates
# the source directory with opendir, so it copies untracked files too. Pointed at
# commands/_shared directly, the gate would clear a brand-new block that has not
# been `git add`ed and then propagate the codename out of it -- on the exact
# authoring order this script's own header documents (edit block, run sync, run
# lint; no git step in between). Copying to a non-git temp dir routes the guard
# down its plain-grep branch, which reads every file on disk.
#
# `bash -n` first, so a truncated or unparseable guard is told apart from a real
# verdict. Without it, bash's own exit 2 on a parse error lands in the no-sidecar
# arm and prints a reassuring "skipped" while propagating.
#
# Fail-closed on any unexpected code, deliberately diverging from the softer
# handling in scripts/lint-commands.sh: that caller reports on a tree that already
# exists, this one decides whether to write into ~195 files. The message never
# claims a codename was found unless the guard actually said so.
#
# Reproduces NONE of the guard's output, matching scripts/lint-commands.sh: the
# guard's LEAK lines carry the codename, so echoing them here would leak it into
# wherever this output gets pasted.
#
# `|| gate_rc=$?` is load-bearing under `set -e` above: without it a non-zero exit
# aborts the script before the case can classify it, turning a skip into a crash.
# SYNC_GATE_SCRIPT overrides the guard path, mirroring MIRROR_CODENAMES_FILE in
# check-mirror-codenames.sh. It exists so the two fail-closed branches below can be
# exercised by scripts/tests/test-sync-shared-blocks.sh: without it those branches
# are asserted and never run, which is how the previous task shipped three
# fail-open paths that no test could see.
GATE="${SYNC_GATE_SCRIPT:-${SCRIPT_DIR}/check-mirror-codenames.sh}"
if [[ ! -f "$GATE" ]]; then
  echo "Codename gate: MISSING at ${GATE#"$REPO_ROOT"/}. Refusing to propagate." >&2
  exit 1
fi
if ! bash -n "$GATE" 2>/dev/null; then
  echo "Codename gate: ${GATE#"$REPO_ROOT"/} is not parseable shell. Refusing to propagate." >&2
  exit 1
fi
GATE_SCAN_DIR="$(mktemp -d)"
cp -R "$SHARED_DIR"/. "$GATE_SCAN_DIR"/
gate_rc=0
bash "$GATE" "$GATE_SCAN_DIR" >/dev/null 2>&1 || gate_rc=$?
rm -rf "$GATE_SCAN_DIR"
case "$gate_rc" in
  0) ;;
  1) echo "Codename gate: found a listed codename under ${SHARED_DIR#"$REPO_ROOT"/}. Nothing propagated." >&2
     echo "  Run scripts/check-mirror-codenames.sh commands/_shared to see where." >&2
     exit 1 ;;
  2) echo "Codename gate: skipped (no sidecar; see scripts/.mirror-codenames.example)"
     echo "  NOTE: the absolute-path check is skipped too, because the guard returns before it." ;;
  *) echo "Codename gate: guard exited ${gate_rc}, which is neither a verdict nor a skip. Nothing propagated." >&2
     exit 1 ;;
esac

# K.3 (2026-06-04): dual layout. Flat at commands/<name>.md AND folder-shaped
# at commands/<name>/SKILL.md. _shared/ holds canonical block bodies (skip).
COMMAND_FILES=()
shopt -s nullglob
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

# Single Perl program does the actual rewrite. It reads `_shared/` once,
# then for each command file given on argv it writes the rewritten content
# to a sibling `.tmp` file. The shell wrapper compares old and new and
# either swaps in the new version or discards it, depending on dry-run mode.
PERL_REWRITE=$(cat <<'PERL'
use strict; use warnings;

my $shared = $ENV{SHARED_DIR_ENV};
my %canon;
opendir(my $dh, $shared) or die "open $shared: $!";
while (my $f = readdir($dh)) {
  next unless $f =~ /^([a-z-]+)\.md$/;
  my $name = $1;
  open(my $fh, "<", "$shared/$f") or die "read $shared/$f: $!";
  my @lines = <$fh>;
  close $fh;
  $canon{$name} = \@lines;
}
closedir $dh;

my %end_pat = (
  "mandatory-context-bootstrap" => qr/^Required inputs:$/,
);
my $default_end = qr/^### /;

my $cmd_path = $ARGV[0];
my $out_path = $ARGV[1];

open(my $in, "<", $cmd_path) or die "read $cmd_path: $!";
my @lines = <$in>;
close $in;

my @out;
my $i = 0;
my $unknown = 0;
while ($i < @lines) {
  my $line = $lines[$i];
  push @out, $line;
  if ($line =~ /^<!-- shared:([a-z-]+) -->\s*$/) {
    my $name = $1;
    if (!exists $canon{$name}) {
      print STDERR "UNKNOWN_MARKER:$name\n";
      $unknown++;
      $i++;
      next;
    }
    my $end = $end_pat{$name} // $default_end;
    my $j = $i + 1;
    while ($j < @lines) {
      my $probe = $lines[$j];
      chomp $probe;
      last if $probe =~ $end;
      $j++;
    }
    my @canon_lines = @{ $canon{$name} };
    for my $cl (@canon_lines) {
      $cl .= "\n" unless $cl =~ /\n$/;
    }
    push @out, @canon_lines;
    $i = $j;
  } else {
    $i++;
  }
}

open(my $outfh, ">", $out_path) or die "write $out_path: $!";
print $outfh @out;
close $outfh;
exit($unknown > 0 ? 3 : 0);
PERL
)

CHANGED_FILES=0
INSPECTED_FILES=0
UNKNOWN_MARKERS=0
ERR_FILE="$(mktemp -t sync-shared-blocks.XXXXXX)"
trap 'rm -f "$ERR_FILE"' EXIT

for cmd_file in "${COMMAND_FILES[@]}"; do
  INSPECTED_FILES=$((INSPECTED_FILES + 1))
  rel_path="${cmd_file#$REPO_ROOT/}"
  tmp_file="${cmd_file}.sync-tmp"
  rc=0
  SHARED_DIR_ENV="$SHARED_DIR" perl -e "$PERL_REWRITE" -- "$cmd_file" "$tmp_file" 2>"$ERR_FILE" || rc=$?
  if [[ -s "$ERR_FILE" ]]; then
    while IFS= read -r line; do
      [[ "$line" == UNKNOWN_MARKER:* ]] || continue
      marker_name="${line#UNKNOWN_MARKER:}"
      echo "ERROR: $rel_path declares unknown marker shared:$marker_name (no commands/_shared/$marker_name.md)"
      UNKNOWN_MARKERS=$((UNKNOWN_MARKERS + 1))
    done < "$ERR_FILE"
    : > "$ERR_FILE"
  fi
  if cmp -s "$cmd_file" "$tmp_file"; then
    rm -f "$tmp_file"
    if [[ $VERBOSE -eq 1 ]]; then
      echo "OK:      $rel_path"
    fi
  else
    CHANGED_FILES=$((CHANGED_FILES + 1))
    if [[ $DRY_RUN -eq 1 ]]; then
      rm -f "$tmp_file"
      echo "WOULD UPDATE: $rel_path"
    else
      mv "$tmp_file" "$cmd_file"
      echo "UPDATED: $rel_path"
    fi
  fi
done

echo ""
echo "================================================================================"
if [[ $DRY_RUN -eq 1 ]]; then
  echo "Dry run: $INSPECTED_FILES file(s) inspected, $CHANGED_FILES would change."
else
  echo "Sync:    $INSPECTED_FILES file(s) inspected, $CHANGED_FILES updated."
fi
if [[ $UNKNOWN_MARKERS -gt 0 ]]; then
  echo "Unknown markers: $UNKNOWN_MARKERS"
fi
echo "================================================================================"

if [[ $UNKNOWN_MARKERS -gt 0 ]]; then
  exit 1
fi
exit 0
