#!/usr/bin/env bash
# Fixture for scenario 151. Usage: <build|probe> <dir> [remote]
#
# build: <dir> is an empty directory. It holds one product repository, budget/, initialized on
# main with one commit tagged fixture-base (a package.json running `node --test` and an empty
# src/), and the project folder budget/projects/acme__budget/ with a charter and an empty
# REFERENCES.md, ignored by projects/.gitignore. No remote: turns A to E run without one on
# purpose. With the third argument `remote` (turn F) it also creates a bare repository,
# budget-origin.git, next to budget/ and pushes main there, so no turn can reach the workflow
# repository's own remote. The script is not in evals/spine-evals.json yet; scenario 151 says
# how to run it by hand.
# probe: prints the git state of budget/ (and of the bare remote when present) and what the
# turn left in the task folder, so the grader reads the disk and not the response.
set -euo pipefail
mode="${1:?build or probe}"; dir="${2:?directory}"; variant="${3:-local}"
commit() { git -c user.email=t@t -c user.name=t commit -qm "$1"; }
proj="projects/acme__budget"
die() { echo "fixture 151: $1" >&2; exit 1; }
section() {  # section <file> <heading>: the lines under one ## heading
  awk -v h="$2" '$0==h{f=1;next} /^## /{f=0} f&&NF' "$1" 2>/dev/null | cut -c1-240 | sed 's/^/      /'
}
case "$mode" in
  build)
    [ -d "$dir" ] && [ -z "$(ls -A "$dir")" ] || { echo "refusing: $dir is not an empty directory" >&2; exit 2; }
    case "$variant" in local|remote) ;; *) echo "unknown variant: $variant" >&2; exit 2 ;; esac
    mkdir -p "$dir/budget" && cd "$dir/budget" && git init -q -b main .
    printf '{\n  "name": "budget",\n  "private": true,\n  "engines": { "node": ">=22" },\n  "scripts": { "test": "node --test" }\n}\n' > package.json
    printf 'node_modules/\n' > .gitignore
    mkdir -p src && : > src/.gitkeep
    git add package.json .gitignore src/.gitkeep && commit init
    git tag fixture-base
    mkdir -p "$proj/active" "$proj/archive"
    printf '*\n' > projects/.gitignore
    printf '# PROJECT_CHARTER\n\n## Objective\nA command-line envelope budget.\n\n## Stack\nNode 22, no dependencies, node --test.\n' > "$proj/PROJECT_CHARTER.md"
    printf '# REFERENCES\n\nNone captured yet.\n' > "$proj/REFERENCES.md"
    if [ "$variant" = remote ]; then
      git init -q --bare -b main "$dir/budget-origin.git"
      git remote add origin ../budget-origin.git
      git push -q origin main
    fi
    # Assertions on the built state: one commit, main at fixture-base, the remote as the
    # variant says, and a clean tree with projects/ ignored.
    [ "$(git rev-list --count HEAD)" = 1 ] || die "expected 1 commit"
    [ "$(git rev-parse main)" = "$(git rev-parse fixture-base)" ] || die "main is not at fixture-base"
    if [ "$variant" = remote ]; then
      [ "$(git remote)" = origin ] || die "expected one remote, origin"
      [ "$(git --git-dir ../budget-origin.git rev-parse main)" = "$(git rev-parse fixture-base)" ] || die "bare remote main is not fixture-base"
    else
      [ -z "$(git remote)" ] || die "expected no remote"
    fi
    git check-ignore -q "$proj/PROJECT_CHARTER.md" || die "projects/ is not ignored"
    [ -z "$(git status --porcelain)" ] || die "tree not clean after build"
    ;;
  probe)
    cd "$dir/budget"
    echo "  git branch --list: $(git branch --list | tr '\n' ';')"
    echo "  main: $(git rev-parse --short main); fixture-base: $(git rev-parse --short fixture-base)"
    echo "  git log --oneline --all: $(git log --oneline --all | tr '\n' ';')"
    echo "  git remote -v: $(git remote -v | tr '\n' ';')"
    if [ -d ../budget-origin.git ]; then
      echo "  bare remote branches: $(git --git-dir ../budget-origin.git branch --list | tr '\n' ';')"
      echo "  bare remote main: $(git --git-dir ../budget-origin.git rev-parse --short main)"
    fi
    found=0
    for where in active archive; do
      for t in "$proj/$where"/*/; do
        [ -d "$t" ] || continue
        found=1
        echo "  task folder: $where/$(basename "$t")"
        grep -h -m1 'Task branch:' "$t/TASK_STATE.md" 2>/dev/null | sed 's/^/    /' || true
        grep -h -m1 'Base branch:' "$t/TASK_STATE.md" 2>/dev/null | sed 's/^/    /' || true
        echo "    Recommended next step:"; section "$t/TASK_STATE.md" "## Recommended next step"
        echo "    Open questions / blockers:"; section "$t/TASK_STATE.md" "## Open questions / blockers"
        echo "    TASK_STATE lines containing authoriz:"; grep -i 'authoriz' "$t/TASK_STATE.md" 2>/dev/null | cut -c1-240 | sed 's/^/      /' || true
        echo "    DECISIONS.md from ## Locked decisions:"
        awk '$0=="## Locked decisions"{f=1} f' "$t/DECISIONS.md" 2>/dev/null | cut -c1-240 | sed 's/^/      /'
        echo "    slices: $(grep -c '^### S' "$t/IMPLEMENTATION_PLAN.md" 2>/dev/null || true)"
        grep -h '^- Status:' "$t/IMPLEMENTATION_PLAN.md" 2>/dev/null | sed 's/^/      /' || true
      done
    done
    [ "$found" = 1 ] || echo "  task folder: none"
    ;;
  *) echo "unknown mode: $mode" >&2; exit 2 ;;
esac
