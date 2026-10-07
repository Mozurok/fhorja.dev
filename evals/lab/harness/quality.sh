#!/usr/bin/env bash
# Quality pass, RUBRIC block A, for one finished run:
#   quality.sh <run-id> <port> full <independently-held-attempt-binding.json>
# Clones the run's committed state into quality/<run-id>/app (uncommitted work does not
# count, as the prompt asked for everything committed), installs from scratch, runs
# build/typecheck/lint/test, serves the build and runs the browser checks.
# Writes a new attempt-specific directory; historical quality directories are untouched.
set -euo pipefail
lab="$(cd "$(dirname "$0")/.." && pwd)"
binding_file="${4:-}"
[[ -n "$binding_file" && -f "$binding_file" ]] || { echo "attempt binding required before quality launch" >&2; exit 2; }
python3 - "$lab" "$binding_file" <<'PY'
import sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from attempt import strict_json, verify_evaluation_inputs, snapshot
lab = Path(sys.argv[1])
record = verify_evaluation_inputs(strict_json(Path(sys.argv[2]).read_bytes()))
required = {'driver': [lab / 'harness/quality.sh', lab / 'harness/lib.sh'],
            'scorer': [lab / 'quality.py', lab / 'attempt.py', lab / 'behavior.py']}
for role, files in required.items():
    if not snapshot(files).items() <= record['artifacts'][role].items():
        raise ValueError('actual executing ' + role + ' files absent from frozen attempt')
PY
attempt_id="$(python3 - "$binding_file" <<'PY'
import json, re, sys
value = json.load(open(sys.argv[1]))['attempt_id']
if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]*', value):
    raise ValueError('safe attempt directory identity required')
print(value)
PY
)"
source "$(dirname "$0")/lib.sh"
server=""
cleanup_server() {
  if [[ -n "$server" ]]; then
    pkill -P "$server" 2>/dev/null || true
    kill "$server" 2>/dev/null || true
  fi
}
trap cleanup_server EXIT

id="$1"; port="${2:-3301}"; mode="${3:-full}"
src="$RUNS/$id/work"
[[ -d "$src/.git" ]] || { echo "no repo at $src" >&2; exit 2; }
source_commit="$(python3 - "$lab" "$binding_file" "$src" <<'PY'
import subprocess, sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from attempt import strict_json, verify_evaluation_inputs
record = verify_evaluation_inputs(strict_json(Path(sys.argv[2]).read_bytes()))
src = Path(sys.argv[3]).resolve()
git_root = Path(subprocess.check_output(['git', '-C', str(src), 'rev-parse', '--show-toplevel'], text=True).strip()).resolve()
if git_root != src or any(not Path(p).is_relative_to(src) for p in record['artifacts']['source']):
    raise ValueError('actual starting source workspace absent from frozen attempt; shell source dependencies must be inside this workspace')
print(subprocess.check_output(['git', '-C', str(src), 'rev-parse', 'HEAD'], text=True).strip())
PY
)"
[[ "$id" =~ ^[A-Za-z0-9][A-Za-z0-9._-]*$ && "$mode" == full ]] || { echo "new full quality attempt required" >&2; exit 2; }
q="$ROOT/quality/$id-$attempt_id"; app="$q/app"
mkdir -p "$ROOT/quality"
mkdir "$q" # Refuse an existing attempt instead of deleting prior evidence.
mkdir "$q/logs"
git clone -q "$src" "$app"
python3 - "$lab" "$app" "$q" "$source_commit" <<'PY'
import json, subprocess, sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from attempt import digest, snapshot, write_new
app, q = map(Path, sys.argv[2:4])
commit = sys.argv[4]
if subprocess.check_output(['git', '-C', str(app), 'rev-parse', 'HEAD'], text=True).strip() != commit:
    raise ValueError('evaluation clone differs from selected implementation commit')
paths = [p for p in subprocess.check_output(['git', '-C', str(app), 'ls-tree', '-r', '--name-only', '-z', commit]).decode().split('\0') if p]
actual_paths = {p.relative_to(app).as_posix() for p in app.rglob('*')
                if p.relative_to(app).parts[0] != '.git' and (p.is_file() or p.is_symlink())}
if actual_paths != set(paths):
    raise ValueError('evaluation clone file inventory differs from selected committed source')
files = [app / p for p in paths]
observed = snapshot(files)
expected = {str((app / p).resolve()): digest(subprocess.check_output(['git', '-C', str(app), 'show', commit + ':' + p])) for p in paths}
if observed != expected:
    raise ValueError('evaluation clone source differs from selected committed source')
write_new(q / 'evaluation-source.json', observed)
PY
dirty="$( { git -C "$src" status --porcelain | grep -v -E '^\?\? (projects|\.wos)/' || true; } | wc -l | tr -d ' ')"

agent_env "$REAL_HOME"
AENV+=("CI=1" "PORT=$port")

pm=pnpm
[[ -f "$app/package-lock.json" ]] && pm=npm
[[ -f "$app/yarn.lock" ]] && pm=yarn
[[ -f "$app/pnpm-lock.yaml" ]] && pm=pnpm

has_script() { [[ -f "$app/package.json" ]] && python3 -c "import json,sys; sys.exit(0 if sys.argv[2] in json.load(open(sys.argv[1])).get('scripts',{}) else 1)" "$app/package.json" "$1"; }

step() {  # step <name> <cmd...>  -> prints exit code
  local name="$1"; shift
  local rc=0
  ( cd "$app" && run_capped 900 env -i "${AENV[@]}" "$@" > "$q/logs/$name.log" 2>&1 ) || rc=$?
  echo "$rc"
}

declare_rc() { printf '%s' "$1" > "$q/logs/$2.rc"; }

if [[ "$mode" == --browser-only ]]; then
  :
elif [[ -f "$app/package.json" ]]; then
  declare_rc "$(step install "$pm" install)" install
  for s in build typecheck lint test; do
    if has_script "$s"; then declare_rc "$(step "$s" "$pm" run "$s")" "$s"; else declare_rc 127 "$s"; fi
  done
else
  for s in install build typecheck lint test; do declare_rc 127 "$s"; done
fi

# Serve the production build and run the browser checks.
# The brief names no start script; an app that serves its build through `preview`
# (a static export with `serve out`, documented in its README) is served that way.
serve_script=start
if ! has_script start && has_script preview; then serve_script=preview; fi
# An app with neither script but a static export in out/ is served from out/ by a
# neutral static server, so the browser checks run the same build for every app.
static_out=0
if ! has_script start && ! has_script preview && [[ -f "$app/out/index.html" ]]; then static_out=1; fi
if [[ "$(cat "$q/logs/build.rc")" == 0 ]] && { has_script "$serve_script" || [[ "$static_out" == 1 ]]; }; then
  # The prompt told each agent to use port 3101 or 3201, and most pinned it in their
  # start script, so PORT is only a hint: read the real port from the server log.
  for p in 3101 3201 "$port"; do free_port "$p"; done
  if [[ "$static_out" == 1 ]]; then
    ( cd "$app" && exec env -i "${AENV[@]}" npx --yes serve out -l "tcp://127.0.0.1:$port" > "$q/logs/start.log" 2>&1 ) &
  else
    ( cd "$app" && exec env -i "${AENV[@]}" "$pm" run "$serve_script" > "$q/logs/start.log" 2>&1 ) &
  fi
  server=$!
  up=0
  for _ in $(seq 1 60); do
    for p in $(grep -oE 'localhost:[0-9]+' "$q/logs/start.log" 2>/dev/null | cut -d: -f2 | sort -u) "$port" 3101 3201; do
      if curl -sf -o /dev/null "http://localhost:$p/"; then port="$p"; up=1; break 2; fi
    done
    sleep 1
  done
  echo "served on port $port" >> "$q/logs/start.log"
  if [[ "$up" == 1 ]]; then
    python3 - "$lab" "$binding_file" "$HARNESS/browser-check.mjs" <<'PY'
import sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from attempt import strict_json, verify, snapshot
record = verify(strict_json(Path(sys.argv[2]).read_bytes()), check_artifacts=False)
if not snapshot([sys.argv[3]]).items() <= record['artifacts']['driver'].items():
    raise ValueError('actual browser driver absent from frozen attempt')
PY
    cp "$HARNESS/browser-check.mjs" "$ROOT/.tools/browser-check.mjs"
    ( cd "$ROOT/.tools" && run_capped 900 node browser-check.mjs "http://localhost:$port/" "$q" > "$q/logs/browser.log" 2>&1 ) || true
  else
    echo "server did not come up" > "$q/logs/browser.log"
  fi
  pkill -P "$server" 2>/dev/null || true; kill "$server" 2>/dev/null || true
  server=""
  for p in 3101 3201 3301 "$port"; do free_port "$p"; done
fi

python3 - "$lab" "$binding_file" "$q" "$app" "$pm" "$dirty" <<'PY'
import subprocess, sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from attempt import strict_json, snapshot, same, seal_evidence, write_new, verify
binding = strict_json(Path(sys.argv[2]).read_bytes())
q, app = map(Path, sys.argv[3:5])
before = strict_json((q / 'evaluation-source.json').read_bytes())
sources = list(before)
if not same(before, snapshot(sources)):
    raise ValueError('evaluated source changed during quality probes')
if not (q / 'browser.json').exists():
    write_new(q / 'browser.json', {})
artifacts = {'commands': [str(q / 'logs' / (name + '.rc')) for name in ('install', 'build', 'typecheck', 'lint', 'test')],
             'browser': [str(q / 'browser.json')]}
if (q / 'behavior.json').exists():
    artifacts['behavior'] = [str(q / 'behavior.json')]
receipt = seal_evidence(q / 'evidence-receipt.json', binding, artifacts, sources)
prospective = q / 'prospective.json'
write_new(prospective, {'attempt': binding, 'receipt': receipt, 'artifacts': artifacts})
cases = list(verify(binding, check_artifacts=False)['artifacts']['cases'])
if len(cases) != 1:
    raise ValueError('one independently selected behavior fixture required')
command = [sys.executable, str(Path(sys.argv[1]) / 'quality.py'), str(q), str(app), *sys.argv[5:],
           '--cases', cases[0], '--prospective', str(prospective)]
for source in sources:
    command += ['--source', source]
raise SystemExit(subprocess.call(command))
PY
