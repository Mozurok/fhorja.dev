#!/usr/bin/env bash
# launch-background-run.sh -- Fhorja background-autonomous-run launcher (D-1,
# D-2, D-4 of
# projects/bmazurok__my-work-tasks/active/2026-07-03_background-autonomous-run/DECISIONS.md).
#
# Detaches ONE configured agent CLI (WOS_AGENT_CMD, D-2) to drive
# autonomous-run for a task folder, unsupervised, in its own git worktree.
# Refuses a second concurrent launch (D-4, via runs-feed.sh check) and never
# uses, documents, or suggests a permissive headless permission flag of any
# kind (D-1; the ADR-0044 D9 skip list -- acceptEdits, bypassPermissions,
# skip-permissions, yolo -- stays off-limits here, in code and in the manual
# instructions this script prints).
#
# This script writes exactly three things: the runs-feed file (via
# runs-feed.sh), the run's log file, and, when no worktree is already
# recorded for the task, a freshly provisioned git worktree. Nothing else.
#
# Paths resolve relative to the repo root (this script's grandparent dir,
# same convention as runs-feed.sh/governor.sh/stop-check.sh), so the launcher
# may be invoked from anywhere. Scope note: this launcher assumes the task
# folder and the codebase it automates live in that same repo (true for the
# background-autonomous-run task itself, whose Active codebase is the Fhorja
# repo); a task whose SOURCE_OF_TRUTH.md Active codebase is a different
# repository should provision its worktree in advance with task-workspace so
# this launcher takes the reuse path instead of the fallback provisioning
# path below.
#
# Usage:  launch-background-run.sh <task-folder>
#   <task-folder>  path to projects/<client>__<project>/active/YYYY-MM-DD_<slug>/
#
# Env:    WOS_AGENT_CMD  the configured agent CLI invocation (D-2). Required
#                        to actually launch; when unset this script prints
#                        manual detached-launch instructions and exits 0
#                        (that is expected behavior, not a failure).
#
# Exit:   0  launched detached, or manual instructions printed (WOS_AGENT_CMD unset)
#         1  refused: a fresh-heartbeat background run already exists (D-4)
#         2  usage error

set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$DIR/../.." && pwd)"
RUNS_FEED="$DIR/runs-feed.sh"

usage() {
  echo "usage: launch-background-run.sh <task-folder>" >&2
  exit 2
}

task_folder="${1:-}"
[[ -z "$task_folder" ]] && usage
task_folder="${task_folder%/}"
[[ -d "$task_folder" ]] || { echo "launch-background-run: no such task folder: $task_folder" >&2; exit 2; }

# The full task-folder basename (YYYY-MM-DD_<slug>), per the ADR-0074
# convention: using the full name (not the bare slug) keeps branch and
# worktree names unique across dates.
task_dir="$(basename "$task_folder")"

# --- 1. D-4 refusal: refuse when a fresh-heartbeat run already exists. ---
check_output="$("$RUNS_FEED" check)" && check_exit=0 || check_exit=$?
if [[ "$check_exit" -ne 0 ]]; then
  fresh_line="$(printf '%s\n' "$check_output" | grep '^check: fresh run' | head -n1)"
  echo "REFUSED: a fresh background run already exists (${fresh_line:-see runs-feed.sh check output above}). Only one background run may be active at a time (D-4). Let it finish, or inspect .wos/runs/*.json directly if it looks stuck." >&2
  exit 1
fi

# --- 2. D-2 config: WOS_AGENT_CMD absent -> manual instructions, exit 0. ---
if [[ -z "${WOS_AGENT_CMD:-}" ]]; then
  stop_path_example="$REPO/.wos/STOP-$task_dir"
  wt_dir_example="$REPO/.wos/bg-worktrees/$task_dir"
  cat <<EOF
No WOS_AGENT_CMD configured (D-2): this launcher needs the agent CLI
invocation set in the environment before it can detach a run. Here is the
manual detached-launch procedure a human runs instead:

1. Provision or reuse the task worktree.
   - IF $task_folder/SOURCE_OF_TRUTH.md already has a '## Workspace'
     section, cd into the worktree path recorded there.
   - ELSE provision one:
       git worktree add $wt_dir_example -b task/$task_dir
     (reuse the existing branch with
       git worktree add $wt_dir_example task/$task_dir
     when task/$task_dir already exists).

2. Set the absolute STOP sentinel path in the MAIN repo (never inside the
   worktree; the run halts the moment this file exists, so do not create it
   now):
       STOP_PATH="$stop_path_example"

3. Start your agent CLI, detached, from inside the worktree, with the
   autonomous-run invocation for this task folder, redirecting output to a
   log file:
       ( cd <worktree-path> && \\
         WOS_STOP_PATH="\$STOP_PATH" \\
         nohup <your-agent-cli> "Run autonomous-run for task $task_dir. STOP file: \$STOP_PATH." \\
           >> $REPO/.wos/runs/bg-$task_dir-<epoch>.log 2>&1 & )

4. Note the printed PID (or read the "pid <N>" line nohup's own shell prints
   at the top of the log); that is how you find and stop the detached
   process later.

Set WOS_AGENT_CMD once (for example: export WOS_AGENT_CMD="claude -p") to
skip this manual dance next time.
EOF
  exit 0
fi

# --- 3. Worktree: reuse the recorded ADR-0074 workspace, else provision. ---
sot="$task_folder/SOURCE_OF_TRUTH.md"
worktree_path=""
if [[ -f "$sot" ]] && grep -q '^## Workspace' "$sot"; then
  worktree_path="$(awk '
    /^## Workspace/ { f=1; next }
    f && /^## / { exit }
    f && tolower($0) ~ /worktree path/ { print; exit }
  ' "$sot" | sed -E 's/^[^:]*:[[:space:]]*//; s/`//g; s/[[:space:]]+$//')"
fi

if [[ -n "$worktree_path" ]]; then
  echo "worktree: reusing recorded workspace from $sot -> $worktree_path"
else
  branch="task/$task_dir"
  worktree_path="$REPO/.wos/bg-worktrees/$task_dir"
  if git -C "$REPO" worktree list --porcelain | grep -qx "worktree $worktree_path"; then
    echo "worktree: reusing already-provisioned $worktree_path (same task, prior launch)"
  else
    mkdir -p "$REPO/.wos/bg-worktrees"
    if git -C "$REPO" show-ref --verify --quiet "refs/heads/$branch"; then
      echo "worktree: branch $branch exists; attaching it at $worktree_path"
      git -C "$REPO" worktree add "$worktree_path" "$branch"
    else
      echo "worktree: provisioning $worktree_path on new branch $branch"
      git -C "$REPO" worktree add "$worktree_path" -b "$branch"
    fi
  fi
fi

# --- 4. STOP path: absolute, main repo, printed for the human. ---
stop_path="$REPO/.wos/STOP-$task_dir"
echo "STOP sentinel path (absolute, main repo): $stop_path"

# --- 5. Feed: write the initial feed file. ---
run_id="bg-$task_dir-$(date +%s)"
"$RUNS_FEED" start "$run_id" "$task_dir" "launching"

# --- 6. Detach: nohup $WOS_AGENT_CMD, no permission flags added, ever. ---
mkdir -p "$REPO/.wos/runs"
log="$REPO/.wos/runs/$run_id.log"
: > "$log"
prompt="Run autonomous-run for task $task_dir. STOP file: $stop_path. Run id: $run_id."

(
  cd "$worktree_path"
  # shellcheck disable=SC2086  # WOS_AGENT_CMD is a user-configured command
  # line (D-2) and is word-split intentionally so it may carry its own
  # arguments; it is used verbatim, never augmented with a permission flag.
  WOS_STOP_PATH="$stop_path" WOS_RUN_ID="$run_id" WOS_TASK_DIR="$task_dir" \
    nohup $WOS_AGENT_CMD "$prompt" >>"$log" 2>&1 &
  child_pid=$!
  echo "pid $child_pid" >> "$log"
  echo "launched: run_id=$run_id pid=$child_pid worktree=$worktree_path log=$log"
)

exit 0
