# Measurement and context lab

Opt-in experiments for measurement repair and selective context. The workflow
continues to load its required Markdown normally. This directory installs no
catalog command and promotes no retrieval backend or model.

## Offline checks

Run from the repository root:

```sh
./scripts/tests/test-context-lab.sh
```

Tests use Python's standard library. Node checks the browser adapter's syntax;
the offline suite launches no browser, downloads no weights and makes no paid calls.

## Scoped access capture

`access_capture.py` is an opt-in offline consistency check for trusted retained
broker captures. It reconciles a hash-linked access journal, ordered rollout
files and CLI JSONL tool events. It does not launch a provider or change the
pilot's capture path. Set `PROFILE_SHA256` to the digest recorded at invocation:

```sh
python3 -B evals/lab/access_capture.py \
  --journal capture/access.jsonl \
  --stdout capture/stdout.jsonl \
  --rollout capture/rollout.jsonl \
  --workspace /workspace/candidate \
  --profile-sha256 "$PROFILE_SHA256"
```

Repeat `--rollout` in observed order when a capture spans multiple files. The
resolved workspace and profile digest must match `broker.started`. Journal
rows carry zero-based integer `seq` and `previous`, the SHA-256 of the previous
row serialized with sorted keys, compact separators and no non-finite values.
Tool operations must form serial started/completed pairs ending in
`broker.closed`; MCP initialize and tool-list control-plane rows are ignored.

The adapter supports scoped `files`, `read`, `write` and `run` observations,
direct calls, and Code Mode exec/wait with nested MCP completion. It tracks a
yielded cell until its matched wait completes, including nested completion
between yield and wait. Unknown tools, malformed lifecycle headers, incomplete
pairs, altered results and ambiguous concurrent gateways produce an incomplete
report. Direct rollout outputs, when present, must cover all direct calls and
contain the supported JSON MCP envelope with one text result and `isError`.
When those outputs are absent, direct-call results reconcile through the broker
journal and CLI terminal events; this is not a root-retention completeness check.

An exact scoped ENOENT read is a captured failure rather than successful access.
It qualifies only for a relative path without parent segments or current
symlinks, with the exact platform error reproduced in every observed result.
Replay therefore depends on the original workspace path, current symlink layout
and platform error representation. Other broker errors remain incomplete.

The JSON report contains `complete`, `issues`, `observed_tools` and `scope`.
Exit 0 means access observations reconciled; exit 1 means incomplete; invalid
CLI arguments exit 2. Hash links establish consistency, not authentication.
Root origin, usage, budgets, process success, sandbox enforcement and comparative
code quality require separate evidence. The portable synthetic regressions run
through the offline gate above; new host schemas require their own qualification.

## Quality evidence

`quality.py` reads a quality directory containing command return codes and
browser evidence, then writes a new `auto-v3.json`, preserving `auto.json` and
`auto-v2.json`. Existing v3 output also refuses overwrite. Return codes must be
actual JSON integers: `false`, `0.0`, unknown and missing values earn no command
credit. Old reports retain their original scorer and are not rescored in place.
Browser schema version 2 records expected routes, successful HTTP responses,
completed viewport and axe probes, and fatal interaction errors. Empty arrays
without completed probes earn no browser credit. A successful example-button
click does not prove example data loaded.

CSV and budget behavior credit requires a separate `behavior.json`: schema
version 2, producer `independent-harness`, completed features, and successful
executed cases with `case_id`, `passed`, integer `exit_code`, `observed` and
`expected`. Errors or incomplete cleanup contradict success. Independently
selected `--cases`, repeated `--source` paths and a separately held
`--candidate-command` JSON argv file are mandatory for domain credit.
The fixture determines the exact ordered IDs, feature groups and expected values;
omissions, duplicates, invented IDs, reordered cases and rewritten expectations
withhold credit. Unknown feature groups are invalid. A supplied feature-level
`passed` flag must also be true; it cannot contradict completed cases.
Object key order is harmless; array order, booleans, integers
and floating-point values remain distinct. Nonfinite JSON and duplicate keys
are invalid. Test comments and names earn no behavior credit. The scorer trusts
the external harness, so the candidate must not author its evidence.

`behavior.py` executes a trusted local adapter against separately held expected
outputs. Each process receives only a case's input JSON on stdin and must emit
exactly `{"result": <observed value>}` on stdout. A failed case, nonzero exit,
malformed response or timeout withholds feature completion. Comparison preserves
JSON types, so a boolean cannot substitute for integer cents.

```sh
lab_python="$(python3 -c 'import sys; print(sys.executable)')"
python3 evals/lab/behavior.py --cases evals/lab/fixtures/behavior_cases.json \
  --output /tmp/fhorja-behavior-new.json --timeout 5 \
  --source "$PWD/evals/lab/fixtures/reference_behavior.py" \
  -- "$lab_python" "$PWD/evals/lab/fixtures/reference_behavior.py"
```

The reference implementation calibrates the grader; it is not an agent baseline.
For an actual implementation, replace the command with an adapter calling its
business functions and translating their inputs and outputs without fixing their
logic. Freeze the fixture briefs before a new agent run. The supplied briefs
explicitly define same-file duplicate retention and refund classification;
historical tasks with different or ambiguous requirements need separate cases.

This runner is not an adversarial sandbox. Candidate code can access local files;
expected outputs are withheld from stdin, not protected by an isolation boundary.
Only a small environment whitelist is inherited. The process group is killed on
POSIX timeout. The output size check runs after capture and is not a memory cap.
Post-kill pipe draining has a bounded grace period. A detached helper may survive;
`cleanup_incomplete` records failure to finish cleanup within that period.

Every declared candidate file and dependency, fixture and evaluator has a before
and after SHA-256 snapshot. The scorer recomputes it from its independently
selected paths. A missing source set remains unbound; changed source or evaluator,
stale evidence or a different fixture cannot earn domain credit. This detects
changes between snapshots, not intermediate edits restored before the second
snapshot. It does not discover undeclared imports or prove which functions a
trusted adapter invoked. Declare the complete dependency set explicitly.
The independently selected command must match the producer's command and its
script entry must belong to the declared sources. Direct declared executables
and interpreter commands with a script as their first argument can bind. Both
executable and script paths must be absolute. Bare PATH entries and relative
script paths remain unbound, avoiding a different process working directory.
Declaring the interpreter itself never binds its inline code. Inline
`-c`, module `-m`, interpreter flags and command wrappers without a declared entry
remain unbound rather than guessing their imports from unused trailing arguments.

## Continuity acceptance

`continuity.py` prepares either a fresh integration task or an interrupted
inventory implementation. Both expose the same public JSON contract. The
interrupted task has an obsolete ordering rule and an incomplete progress note.
Previously valid helpers and an unrelated dirty note must remain byte-identical.
The public handoff distinguishes an unknown previous verification from a pass.

```sh
python3 evals/lab/continuity.py /tmp/fhorja-continuity --prepare continuity
python3 evals/lab/continuity.py /tmp/fhorja-continuity \
  --output /tmp/fhorja-continuity-grade.json
```

Preparation refuses an existing destination and copies no expected cases or
calibration implementation into it. After implementing the candidate and public
handoff, grading runs each external case in a real subprocess, then checks file
preservation and the handoff. A failed process, timeout, malformed response or
wrong JSON type cannot earn acceptance. `fixtures/reference_continuity.py`
contains two calibration algorithms and deliberate behavioral faults; these
are evaluator checks, never agent results. The suite also exercises preservation
and handoff faults. Matching a handoff requirement does not prove model
investigation, context understanding or workflow ROI. Execution is trusted local
code, with the same post-capture output-size limitation as `behavior.py`.
Continuity evidence is version 2 and also requires unchanged fixture, evaluator
and declared sources. Its default source set is `candidate.py` and `helpers.py`;
repeat `--source` to replace it with the complete dependency set. A candidate
that modifies itself during probes fails acceptance even if all outputs match.
Output files refuse overwrite.

## Prospective attempt metadata

`attempt.py` freezes a new sidecar before dispatch. The caller supplies resolved
policy values and a source for every field, including provider, model, effort,
timeout, call ceiling, actual and equivalent cost limits, limit mode and whether
the last response may overrun a monitored limit. Unknown or inapplicable money
limits remain `null` with explicit provenance. It never reads provider defaults,
authorizes a larger limit, changes billing or treats equivalent cost as an invoice.
`resolve_policy` applies explicit value/source overrides before freezing; a
synthetic 100-to-1000 test is preservation evidence, not spending authorization.

Freeze six nonempty artifact roles: driver, prompt, settings, scorer, cases and
source. Include each declared driver and evaluator dependency in its role.
`freeze` returns the attempt ID, path and SHA-256; hold that binding independently
of the sidecar. `guarded_launch(binding, callback)` verifies metadata and current
artifacts before invoking the callback. Missing, changed or stale inputs prevent
the callback. An existing output is never replaced. The CLI accepts explicit JSON
requests for `freeze`, `verify` and `seal`; it has no provider or billing client.

Implementation may legitimately change its starting source. `seal_evidence`
captures its evaluated post-implementation source and command, browser and domain
artifacts in a separate immutable receipt, retaining the original attempt ID and
sidecar digest. Other frozen inputs remain unchanged. Hold the receipt digest
independently too. The evaluator checks its own before/after source snapshot;
the receipt is a capture, not proof that arbitrary submitted JSON is truthful.
With `quality.py --prospective REQUEST_JSON`, command return-code files and
browser and optional domain JSON must match both the receipt and the values being
scored. Invalid prospective binding earns zero. Without the request, available
signals remain explicitly `unbound` and cannot be reported as a prospective run.

This package tests real local callback refusal and adapter wiring. Actual paid
implementation launchers must consume the gate before every call in the later
pilot. Helper existence does not establish that enforcement. No historical run
or provider call is launched by these checks.

## Mechanical state prototype

`state.py` is an opt-in Python module for disposable tasks and later ablations.
It registers an explicit physical task root, captures actual local check exits,
renders a typed event, then publishes one existing factual section and its
canonical log record. It installs no command and changes no workflow default.
Use the module from a repository checkout so its canonical command registry and
SHA/log validator remain available. Python and a POSIX host are required;
the focused tests also invoke the existing Bash emitter and `jq`.

The three event kinds are `phase_selected`, `step_recorded` and `status_reported`.
The model supplies phase, activity, command, mode and required checks explicitly.
The renderer derives verification from bound check records. An empty required
set or missing evidence is `unknown`; an explicitly unexecuted record is
`not_run`; a completed integer nonzero exit is `failed`. Only a nonempty set of
current, completed integer-zero checks is `passed`. These facts do not establish
requirement completion, review approval or semantic test coverage.

Run this complete example from the repository root. It creates a new temporary
task, executes a real candidate check, renders and applies a step, verifies
exact replay and inspects the retained event. It makes no provider calls:

```sh
PYTHONPATH="$PWD/evals/lab" python3 - <<'PY'
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from attempt import canonical, digest, snapshot, strict_json
from state import (apply_event, capture_check, initialize, project,
                   recover_event, section_sha)

root = Path(tempfile.mkdtemp(prefix='fhorja-state-')).resolve()
for name in ('README.md', 'DECISIONS.md', 'IMPLEMENTATION_PLAN.md'):
    (root / name).write_text('# Model authority\nPreserve explicit decisions.\n')
target = root / 'TASK_STATE.md'
target.write_text('# Task state\n\n## Current phase\nimplementation\n\n'
                  '## Last completed step\nunknown\n\n'
                  '## Current status\nunknown\n\n'
                  '## Unknowns\nSemantic coverage remains unknown.\n')
source = root / 'candidate.py'
source.write_text('raise SystemExit(0)\n')
identity = initialize(root, 'demo-task', genesis=True)
record = capture_check(root, identity['task_id'], 'candidate-check',
                       [sys.executable, str(source)], [source], timeout=5)
evidence = root / '.wos/check-1.json'
raw = (canonical(record) + '\n').encode()
evidence.write_bytes(raw)  # The trusted caller retains this check binding.
event = {
    'schema_version': 1, 'event_id': 'step-1',
    'task_id': identity['task_id'], 'task_root': str(root),
    'owner': 'sync-task-state', 'run_id': '01Jstate_demo',
    'ts': datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z'),
    'target': 'TASK_STATE.md',
    'expected_section_sha': section_sha(target, '## Last completed step'),
    'authority_snapshot': snapshot(root / n for n in
                                   ('README.md', 'DECISIONS.md', 'IMPLEMENTATION_PLAN.md')),
    'candidate_snapshot': snapshot([source]), 'kind': 'step_recorded',
    'payload': {'command': 'implement-approved-slice', 'mode': 'Agent',
                'required_checks': ['candidate-check'], 'check_refs': [
                    {'check_id': 'candidate-check', 'path': str(evidence),
                     'sha256': digest(raw)}]},
}
print(canonical({'projection': project(root, event)}))
print(canonical({'apply': apply_event(root, event)}))
log = root / '.wos/VERIFICATION_LOG.jsonl'
before = (target.read_bytes(), log.read_bytes())
replay = apply_event(root, event)
assert before == (target.read_bytes(), log.read_bytes())
assert len(log.read_bytes().splitlines()) == 1
assert recover_event(root, 'step-1')['outcome'] == 'already_applied'
receipt = strict_json((root / '.wos/state-replay/events/step-1.done.json').read_bytes())
print(canonical({'task_root': str(root), 'replay': replay,
                 'receipt_outcome': receipt['outcome'], 'canonical_records': 1}))
PY
```

The output contains `verification: passed`, an `applied` result, then
`already_applied` with one canonical record. Keep the printed task root to inspect
`TASK_STATE.md`, `.wos/VERIFICATION_LOG.jsonl` and `.wos/state-replay/events/`.
Inspection of the retained JSON files is read-only. The example leaves its
temporary task available; remove that exact directory after inspection.

Initialize existing logged tasks without `genesis=True`. Genesis is allowed only
for a new disposable task with no owning headers. Never use it to recreate lost
history. Supply canonical physical paths: symlink ancestors, including a platform
alias such as `/var`, are refused; resolving a known intended root is explicit
caller responsibility. Moving or archiving a registered task does not rebind it.

`apply_event(root, event)` writes the selected existing H2 only. Before publication
it verifies current authority/candidate snapshots, the selected section preimage,
historical log chain and exact retained prefix. Dirty unrelated state sections
and product files are preserved. A changed target or log after preparation
conflicts instead of overwriting the edit. Event IDs bind complete canonical
event content; retry with changed content is a conflict. A fresh event cannot
bypass an unfinished publication: recover it explicitly first.
If authority or candidate changes before target publication, recovery refuses
and the pending event still blocks fresh publication. This prototype has no
cancellation operation; retain the disposable task for inspection rather than
deleting its receipts or history to resume it.

`recover_event(root, event_id)` uses the same-task prepared receipt. Before/before
resumes only current facts; target-after/log-before appends only captured historical
provenance; after/after finalizes without duplication. A changed authority or
candidate after target publication permits exact log repair and reports current
verification `unknown` with stale flags. Historical state text can still contain
the original passed fact. It is not recertified or rewritten by that repair.
Completed replay validates required regular destinations and retained history,
then proves a historical record without restoring an older target. It does not
certify all current transaction-header metadata after an external header-only edit.

Prepared receipts retain whole before/after target and log bytes. This deliberately
simple prototype grows with history and revisits retained receipts; storage size
and latency must be measured before any default rollout. The POSIX lock serializes
prototype writers only. Other writers must be quiescent or coordinated by the
caller. Individual replacements are atomic; the target/log pair has a recoverable
target-ahead interval, not atomic visibility or a power-loss durability guarantee.
Hashes detect captured inconsistency, not hostile alteration or restored
intermediate edits. Check records and receipts are trusted local artifacts;
the model/candidate must not author its own successful evidence.

Focused controls include real process termination at preparation, target and log
publication boundaries, late log failure, stale repair, malformed receipts,
missing/truncated history, wrong tasks, real archive moves, symlinks and byte SHA
parity with the production emitter:

```sh
python3 -m unittest discover -s evals/lab/tests -p test_state.py -v
```

## Independent ablation preparation

`ablation.py` prepares separate context, state and catalog comparisons. Each pair
starts from the same full-context/manual-state baseline and varies one declared
factor. Common policies, tools, permissions, collaboration, facts, protected
bytes, helper dependencies and independently selected checks remain equal.
The full payload includes the exact current shared bootstrap reuse contract.
The kernel retains caller-audited passages with full sources available on demand;
eight valid passage names and hashes do not certify their meaning or model compliance.

Run this disposable example from a checkout. It copies current canonical sources,
creates explicit demonstration requirements and prepares all three pairs through
the CLI. Python and Git are required. The copied state helper's eventual publication
requires a POSIX host; manual publication also requires Bash, `jq` and the emitter's
operation-specific utilities. Trusted check commands have their own dependencies.
This example executes no state publication or model calls and changes no settings.

```sh
PYTHONPATH="$PWD/evals/lab" python3 - <<'PY'
# offline-ablation-example
import copy
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from ablation import catalog_closure, verify_factor
from attempt import canonical, digest, resolve_policy

repo = Path.cwd().resolve()
root = Path(tempfile.mkdtemp(prefix='fhorja-ablation-')).resolve()
workflow = root / 'workflow'
workflow.mkdir()
for directory in ('commands', 'wos'):
    shutil.copytree(repo / directory, workflow / directory)
for name in ('WORKFLOW_OPERATING_SYSTEM.md', 'docs/command-catalog.json',
             'evals/lab/state.py', 'evals/lab/attempt.py',
             'scripts/verify-log-validator.py', 'scripts/emit-substrate-write.sh'):
    target = workflow / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes((repo / name).read_bytes())
clauses = {
    'source': 'Use this canonical source copy; unavailable sources remain unknown.',
    'authorization': 'Prepare offline pairs only; no model calls or setting changes.',
    'protected_work': 'Preserve notes.txt exactly in both initial workspaces.',
    'latest_requirement': 'This current brief supersedes obsolete prior task rules.',
    'unknown_verification': 'Absent or stale verification remains unknown.',
    'verification_evidence': 'Pass needs actual completed independent checks.',
    'one_factor': 'Change exactly the declared factor in each separate pair.',
    'no_default_promotion': 'Do not promote a treatment merely for shorter text.',
}
guard_text = ''.join(text + '\n' for text in clauses.values())
(workflow / 'task-guards.md').write_text(guard_text)
guards = {name: {'path': 'task-guards.md', 'start_line': line, 'end_line': line,
                 'sha256': digest((text + '\n').encode())}
          for line, (name, text) in enumerate(clauses.items(), 1)}
seed = root / 'seed'
seed.mkdir()
(seed / 'README.md').write_text(guard_text)
(seed / 'notes.txt').write_bytes(b'unrelated dirty notes\xff\n')
cases = root / 'audited-guards.json'
cases.write_text(canonical(guards) + '\n')
entry = repo / 'evals/lab/ablation.py'
inputs = {
    'seed': {name: str(seed / name) for name in ('README.md', 'notes.txt')},
    'helper': {'reference/' + str(p.relative_to(workflow)): str(p)
               for p in sorted((workflow / 'wos').rglob('*.md'))},
    'driver': {'ablation.py': str(entry)},
    'scorer': {'local-integrity-validator.py': str(entry)},
    'cases': {'audited-guards.json': str(cases)},
}
# Local preparation policy labels are explicit, not provider or spend attestation.
values = dict(provider='local', model='offline-demo', effort='offline',
              timeout_seconds=10, max_calls=1, max_actual_usd=None,
              max_equivalent_usd=None, limit_mode='monitored',
              accept_last_response_overrun=True)
common = {
    'baseline_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
    'policy': resolve_policy({k: {'value': v, 'source': 'offline demonstration only'}
                              for k, v in values.items()}),
    'tools': ['read', 'write', 'shell'],
    'permissions': {'sandbox': 'disposable-local-demo', 'network': False},
    'collaboration': {'allowed': True, 'max_agents': 2},
    'required_checks': ['acceptance', 'preservation'],
    'protected_files': ['notes.txt'], 'facts': ['README.md'], 'public_brief': 'README.md',
}
for role, field in [('seed', 'seed_hashes'), ('helper', 'helper_hashes'),
                    ('driver', 'driver_hashes'), ('scorer', 'scorer_hashes'),
                    ('cases', 'case_hashes')]:
    common[field] = {name: digest(Path(path).read_bytes()) for name, path in inputs[role].items()}
graph = catalog_closure(workflow, ['branch-commit'])
baseline = dict(mandatory_context='full', mechanical_state='manual', exposed_catalog=graph['names'])
variants = dict(mandatory_context='kernel', mechanical_state='prototype', exposed_catalog=graph['selected'])
bindings = {}
for factor, value in variants.items():
    treatment = dict(copy.deepcopy(baseline), **{factor: value})
    spec = {'schema_version': 1, 'pair_id': 'offline-' + factor, 'factor': factor,
            'arms': [{'arm_id': name, 'common': copy.deepcopy(common), 'treatment': settings}
                     for name, settings in [('control', copy.deepcopy(baseline)), ('treatment', treatment)]]}
    request = dict(destination=str(root / factor), spec=spec, inputs=inputs,
                   workflow_root=str(workflow), guards=guards, catalog_roots=['branch-commit'])
    request_path = root / (factor + '-request.json')
    request_path.write_text(canonical(request) + '\n')
    prepared = subprocess.run([sys.executable, '-B', str(entry), '--prepare', str(request_path)],
                              check=True, capture_output=True, text=True)
    binding_path = root / (factor + '-binding.json')
    binding_path.write_text(prepared.stdout)  # Hold independently of factor.json.
    bindings[factor] = json.loads(prepared.stdout)
    checked = subprocess.run([sys.executable, '-B', str(entry), '--verify', str(binding_path)],
                             check=True, capture_output=True, text=True)
    print(checked.stdout.strip())
record = verify_factor(bindings['mandatory_context'])
prompt = Path(record['invocations']['treatment']['prompt']['path'])
before = prompt.read_bytes()
try:
    prompt.write_bytes(before + b'changed\n')
    refused = subprocess.run([sys.executable, '-B', str(entry), '--verify',
                              str(root / 'mandatory_context-binding.json')], capture_output=True, text=True)
    assert refused.returncode != 0 and not refused.stdout and 'ValueError' in refused.stderr
    (root / 'changed-prompt-refusal.log').write_text(refused.stderr)
    print(canonical({'changed_prompt': 'refused', 'model_delivery': 'unknown'}))
finally:
    prompt.write_bytes(before)
verify_factor(bindings['mandatory_context'])
print(canonical({'demo_root': str(root), 'registered_count': len(graph['names']),
                 'static_selected_count': len(graph['selected'])}))
PY
```

Each successful verification reports `local_integrity: verified` and
`model_delivery: unknown`. The changed prompt refuses verification; restoring
its exact bytes restores local integrity. Keep the printed root to inspect the
three independent bindings, `factor.json`, exact invocation prompts and common
source references. Remove that exact disposable directory after inspection.
Existing package destinations refuse overwrite. Any legitimate implementation
change needs a new attempt; these initial-package guards do not authorize changes.

The demonstration scorer is the local integrity validator. No behavioral
acceptance or prospective episode is claimed. The sample guards are explicit
demonstration requirements, not an audit of every skill. The real catalog count
is measured at execution; its static closure preserves registered routes and
arguments but cannot discover every dynamic route.

`retain_observation` and `inspect_observation` keep submitted prompts, tool returns,
host inventories, provider-visible records, usage and invoices as separate exact
byte layers. `catalog_inventory` reports missing, extra, unsupported or truncated
entries. Even a matching inventory leaves actual exposure and delivery unknown.
Caller provenance labels authenticate neither provider records nor invoices.
Raw produced bytes, returned bytes, tokens and charges are different measurements.
Shared helper paths do not prove sandbox accessibility. An actual host capture
adapter, independently calibrated behavioral checks and effective spending policy
remain prerequisites for the later prospective pilot. No default is promoted here.

## Prospective three-class pilot

`pilot.py` is an opt-in controller for a competitive native versus selected
Fhorja bundle comparison. It allocates twelve episodes across multimodule
configuration, persistent batch recovery and real two-session continuity, with
two repetitions per arm. Continuity uses two fresh root threads per episode;
the complete allocation is sixteen roots. This differs from the one-factor
offline ablations and does not identify individual mechanism effects.

Prepare a JSON request with `destination`, `workspace_root` and `spec`.
The two destinations must be new, separate directories. Public workspaces must
be outside the workflow checkout and its instruction-bearing ancestors.
`spec` is the closed protocol accepted by `freeze_protocol`: explicit matched
policy and host settings, treatment files, common facts/checks/seeds/host
inventory, source-backed kernel audit and canonical passages, frozen artifact
roles, independently held calibration binding and `schedule()` allocation.
`pilot_oracle.calibrate` produces that binding from six valid controls and
twenty-six intended defects. Keep hidden cases and references controller-held.

Optional `pricing` has `rates`, `pricing_date`, `credits_per_usd` and `source`.
Rates use the ledger's USD-per-million-token fields. Their source and any
equivalent-credit conversion must be explicit and frozen before outcomes.
Omitting pricing keeps equivalent cost unknown; it does not make use free.
Nominal token prices and equivalent credits are separate from actual charges.

Run from the repository root, using unused output filenames:

```sh
(set -C; python3 evals/lab/pilot.py --prepare REQUEST.json > RUN_BINDING.json)
python3 evals/lab/pilot.py --verify RUN_BINDING.json
(set -C; python3 evals/lab/pilot.py --report RUN_BINDING.json > INITIAL_REPORT.json)
```

Preparation and reporting make no provider calls. Retain the printed run binding
independently of the controller's `run.json`. Its report lists all twelve planned
episodes and their allocated slots even before any launch.

For real execution, use the declared existing-account adapter, commit the final
runner, fixtures, graders and case files, and prepare a fresh final package.
Do not reuse a protocol whose driver changed. Launch only an allocated slot
from the frozen counterbalanced schedule, sequentially, with continuity stage1
before stage2:

```sh
(set -C; python3 evals/lab/pilot.py --execute RUN_BINDING.json \
  --slot multimodule-r1-native-s1 > SLOT_RESULT_BINDING.json)
(set -C; python3 evals/lab/pilot.py --report RUN_BINDING.json > CURRENT_REPORT.json)
```

`--execute` makes a real provider invocation. It checks committed sources and
fresh workspace-specific read-only host metadata, then reserves the allocated
slot before launch. It never retries a reserved slot or allocates corrections.
Provider refusal stops further dispatch. A process interruption after reservation
remains visible as `reserved-without-terminal` until retained evidence resolves
it; no replacement call is authorized. The sixteen-root allocation does not
bound internal provider turns, descendants or dollars. The adapter's observed
configuration remains distinct from backend model delivery.
The exec adapter skips user configuration and submits an empty MCP table.
Per-server disable overrides belong to the read-only metadata layer that loads
existing transports. Sending those partial entries to a cold strict exec layer
would fail transport validation before creating a model session. These two
configuration layers are recorded separately; metadata is not exec attestation.

If a terminal delivery was sealed but its evaluation or result publication was
interrupted, recover the assessment offline:

```bash
(set -C; python3 evals/lab/pilot.py --recover RUN_BINDING.json \
  --slot SLOT_ID > RECOVERED_RESULT.json)
```

Recovery uses a fresh grading copy and makes no provider or account calls. It
never replaces the invocation or retries a reservation without a retained
terminal. Reporting retains captured usage even before assessment recovery.

Each first terminal product, response and raw trace is sealed before grading.
The oracle executes a controller-held copy, preserving the original snapshot.
Calibration validates raw reports for both correct controls and targeted mutants.
Contradictory negative evidence cannot authorize a frozen implementation run.
The runner checks the complete sealed file inventory against its bound index
before grading, transition and reporting, and again after grading. Added files,
missing files, changed bytes or symlinks invalidate the snapshot. The grading
copy must match that frozen index before the oracle runs. These are trusted
capture checks, not an adversarial filesystem boundary.
Read-only host observations use separate immutable attempt directories. A
failed observation before reservation can be retried while retaining its
captures; an existing invocation reservation still cannot be retried.

Post-freeze batch boundary checks use `pilot_supplementary.py` and their own
case fixture. They witness and terminate a live process after receipt publication,
then require a fresh process to replay without changing any bytes. Binary target
preimages and external-edit conflicts are checked separately. Both reference
algorithms retain raw preimages as hex and recognize completion from matching
payload, once-only receipt and actual output bytes, even before the final marker.

```bash
python3 -B evals/lab/pilot_supplementary.py --calibrate /tmp/fhorja-supplementary-controls
python3 -B evals/lab/pilot_supplementary.py /path/to/retained-batch-copy
```

Calibration creates a new directory with two valid controls and four targeted
mutants, retaining bound raw reports. Evaluation binds all local Python sources,
cases, evaluator dependencies and raw captures; report validation independently
derives checks from calls and byte snapshots. These post-freeze selected grades
remain supplementary and never replace primary pilot cases or outcomes. Process
termination evidence does not certify power-loss durability or hostile isolation.
Paused stdout and stderr use controller-owned temporary files to avoid pipe
backpressure. Incomplete captures retain their observations with coherent=false;
unsupported error annotations cannot turn successful raw evidence into a rejection.
The primary batch validator accepts an empty-check decoding failure only when
retained expected-file bytes reproduce UnicodeDecodeError, the expected call
count is complete and the row has the producer's failure shape. Other capture
failures retain diagnostics but cannot establish coherent candidate rejection.

Continuity grades actual stage1 work, then adds the public v2 contract and dirty
user work to that same workspace. Failed stage1 work is retained. A prepared
transition journals exact preimages and postimages before publishing public
files. Recovery accepts those images after an interrupted atomic replacement,
preserves unexpected user edits by refusing publication, and appends dirty notes
only once. Hidden expected outputs are never added to the model prompt.
Transition and result records publish complete sibling files through an atomic
exclusive link. An interrupted write cannot leave a partial canonical record;
an existing record is never overwritten. This covers process interruption,
not power-loss durability.

The report separates stage1 milestones, final first delivery, process status,
independent acceptance, elapsed time, linked observed tokens, equivalent prices,
account-wide snapshots and unknown invoice charges. Corrections are zero and
not allocated; self-fixes within an invocation remain in its raw trace.
Missing traces, descendant usage or rates cannot earn complete cost credit.
Reports retain refusals, timeouts and unlaunched episodes in the denominator.
Coordination cost is not attributed to individual episode ledgers. Two
repetitions support descriptive comparisons, not broad ROI, statistical
significance, default promotion or certification of every skill.

## Whole-session ledger

```sh
python3 evals/lab/usage.py SESSION_DIR ROOT_ID \
  --prices PRICES_JSON --pricing-date YYYY-MM-DD --output LEDGER_JSON
```

The input is raw Codex session JSONL with explicit session IDs and parent links.
Call records take precedence over cumulative token snapshots. Duplicate call
identities and repeated cumulative snapshots are not charged twice. Counter
decreases, missing expected descendants (`--expect-child ID`), malformed usage
and absent model rates make the priced total unknown. Observed partial usage
remains available. Rates are USD per million tokens under `input`,
`cached_input` and `output`, with cached input included in input tokens.

`complete` means no detected gap in the available linked graph. It cannot prove
that an undeclared descendant was captured, nor reconcile a provider invoice.
Unknown cache-write pricing stays unknown; reasoning tokens are already part
of output and are not charged again. When both call and cumulative views exist,
they must reconcile; they are never added together.

Ledger version 2 also identifies a call immediately followed by a `compacted`
event. Such a call remains priced once. A call/cumulative difference is explained
only when the last call's explicit `thread_token_usage` equals all calls and the
cumulative view equals ordinary calls, including every observed optional field.
Missing or inconsistent proof retains an unknown total. `compaction_tokens` and
`reconciliations` expose this classification and its attestation. This recognizes
the observed trace format, not every possible compaction format.

## Auxiliary benchmark adapters

`harness/` preserves the repaired adapters from an existing benchmark layout.
To integrate into that layout, copy its three files into `harness/`, and keep
`attempt.py`, `quality.py` and `behavior.py` together in the parent directory.
Copy `usage.py` as `harness/usage_ledger.py`. The existing `lib.sh`, `prices.json`, `runs/`, and
`envs/codex-ARM/home/.codex/sessions/` remain required. Browser execution also
uses the benchmark's Playwright, axe and Lighthouse installation.

The quality shell entry requires `quality.sh RUN_ID PORT full BINDING_JSON`.
It verifies the independently held attempt binding and every non-source frozen
input before sourcing the legacy adapter or running commands. The pre-model
`guarded_launch` still verifies all starting source bytes. Quality evaluation
accepts legitimate committed changes and newly tracked modules inside the same
original source workspace; it checks the selected commit and complete clone file
inventory and hashes before probes, including unexpected Git-ignored files.
This one-workspace shell adapter refuses declared source
dependencies outside that workspace; the standalone evaluators accept explicit
source sets. It creates `quality/RUN_ID-ATTEMPT_ID`, refuses an
existing directory, and never deletes the historical directory. Reusing prior
command evidence with `--browser-only` is refused; record a new full attempt.
Tracked evaluated source is snapshotted before and after probes. The receipt
binds raw command and browser artifacts to that same attempt and source snapshot.
The actual shell, legacy `lib.sh`, scorer and scorer helpers must be included in
their frozen roles. Every tracked starting source must also be declared. A browser
dispatch additionally requires its actual `browser-check.mjs` in the driver role.
An unavailable browser remains empty captured evidence and earns no browser
credit. Offline shell tests use a fake local package manager and do not certify
real dependency installation or hosted browser behavior.

The aggregator writes `summary-v2.json` and `summary-v2.md`. `RESULTS_DIR`
redirects those outputs for replay. Its pricing date describes the original
2026-09-29 benchmark table; change the table and date together for a new study.
Set `FHORJA_SKILLS_DIR` for the optional skill-use counter. That counter is
diagnostic and is not a quality score. Historical reports are not overwritten.

## Context interface

The manifest in `fixtures/context_cases.json` provides explicit section IDs,
paths and H2 headings. `requires` contains `[parent, dependency]` edges;
`supersedes` contains `[new, old]` edges. Duplicate headings need an
`occurrence`. Fenced-code headings do not split a section. Preambles are
addressable as `@preamble`. Paths must stay inside the canonical source root.

Required context and its dependency closure are retained even if they exceed
the character budget. Optional candidates use deterministic lexical overlap.
Selected optional nodes bring their declared dependencies as an atomic bundle;
the whole bundle must fit the remaining budget. An absent, stale or corrupt
SQLite FTS5 index falls back to canonical files.
The strict freshness check reads every indexed source and validates passages,
so SQLite is not expected to remove those reads in this prototype. Dependencies
are declared, not inferred; manifest coverage must be audited before production.

```sh
python3 evals/lab/benchmark.py . evals/lab/fixtures/context_cases.json \
  --index /tmp/fhorja-context.sqlite --output /tmp/fhorja-context.json \
  --query 'task memory' --required execution --budget 80000 --repeats 5
```

The comparison reports four arms: a full corpus dump, complete files matching
the selected document identities, selective files, and equivalent SQLite.
Matched file identities are prepared before timing; that arm excludes selection
cost. File and SQLite arms must agree on required content and optional candidates.
The budget covers the serialized passage list, including passage metadata;
the outer diagnostic envelope is additional. Characters and local CPU time are
not measured model tokens, model reading time or accepted-delivery time. Native
agents may already read sections selectively.

## Optional ranking

```sh
python3 evals/lab/rank.py evals/lab/fixtures/ranking_cases.json \
  --arm deterministic --output /tmp/fhorja-rank.json
```

Learned arms require a separate environment plus explicit `--model` and
`--revision`. Install Laya from source revision
`4aa6761be8173de4ce6d92c31b3e40b6eaf59a7c` and Sentence Transformers separately.
The local diagnostic used Laya 0.3.23 and Sentence Transformers 6.1.0:

| Arm | Model | Weight revision |
|---|---|---|
| Laya | convaiinnovations/laya-multilingual | e4e9ddf21a7b1903b7acffd8814ad4307bf63a67 |
| Cross-encoder | cross-encoder/mmarco-mMiniLMv2-L12-H384-v1 | 1427fd652930e4ba29e8149678df786c240d8825 |

Each arm receives the same optional candidate texts and query, without labels.
Required IDs stay outside the ranking pool. Reports separate setup, first
inference and warm inference, with hashes, package versions and binary
Recall@2/nDCG@2. Missing runtime is explicitly unavailable. Laya uses its
`noul` answer as a relevance score; it is not a calibrated probability.

The twelve bilingual cases are developer-labeled diagnostics with short texts,
not held-out tasks. Their scores do not establish coding quality, production
retrieval recall or ROI. The cross-encoder caps input at 512 tokens and Laya at
1024, so long passages need a separately validated chunking policy. The local
run favored Laya's ordering, with unchanged Recall@2 and greater inference
cost. Keep deterministic files as the baseline until held-out outcomes justify
the extra dependency. This fixture also favors early alphabetic IDs: constant
zero scores with ID tie-breaking reach 9/12 top-one relevance and the same
Recall@2. Laya beating lexical ordering alone is therefore insufficient evidence
of a useful ranking improvement.
