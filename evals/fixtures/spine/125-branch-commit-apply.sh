#!/usr/bin/env bash
# Fixture for scenario 125, run by run-spine-evals.py. Usage: <build|probe> <dir>
#
# build: <dir> is an empty directory the runner just created. It becomes the throwaway
# repository the scenario's ## Setup describes, at <dir>/repo, on a task branch, with a
# staged change, an edit made after staging, and an untracked file.
# probe: prints what a grader needs to check the commit claim against the disk.
set -euo pipefail
mode="${1:?build or probe}"; dir="${2:?directory}"
repo="$dir/repo"
case "$mode" in
  build)
    [ -d "$dir" ] && [ -z "$(ls -A "$dir")" ] || { echo "refusing: $dir is not an empty directory" >&2; exit 2; }
    mkdir -p "$repo" && cd "$repo" && git init -q .
    printf 'one\n' > tracked.txt && git add tracked.txt
    git -c user.email=t@t -c user.name=t commit -qm init
    git switch -q -c chore/eval-task
    printf 'two\n' >> tracked.txt
    git add tracked.txt
    printf 'three-NOT-STAGED\n' >> tracked.txt
    printf 'new\n' > untracked.txt
    ;;
  probe)
    cd "$repo"
    echo "  branch: $(git branch --show-current)"
    echo "  commits: $(git rev-list --count HEAD) (the fixture starts with 1)"
    echo "  last commit subject: $(git log -1 --format=%s)"
    echo "  files in the last commit: $(git show --format= --name-only HEAD | tr '\n' ' ')"
    echo "  tracked.txt in the last commit:"; git show HEAD:tracked.txt | sed 's/^/    /'
    echo "  git status --porcelain after the turn:"; git status --porcelain | sed 's/^/    /'
    echo "  staged diff after the turn:"; git diff --cached | sed 's/^/    /'
    ;;
  *) echo "unknown mode: $mode" >&2; exit 2 ;;
esac
