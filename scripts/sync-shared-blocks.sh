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
#   1 = a command file declares an unknown marker (no canonical file found)
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
  1 = unknown marker referenced
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
