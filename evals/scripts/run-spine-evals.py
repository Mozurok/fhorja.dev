#!/usr/bin/env python3
"""run-spine-evals.py: run the spine scenarios in evals/spine-evals.json against a model.

The other half of the harness. evals/scripts/run-evals.sh stays the manual walk
over the whole corpus and still calls nothing; this runs the elected few against
whatever model the caller names, and leaves prompt, response, rubric and verdict
on disk.

It knows no vendor. --model-cmd is any shell command that reads a prompt on stdin
and writes a response on stdout, run from the repository root so a prompt saying
"Run @commands/x.md" can actually open the file.

One pass per scenario. No retry, no token counter, no cost, no governor, no hook,
no state between runs. None of that is a surface of this repository.

Nothing here fabricates a verdict. Every refusal has its own exit code and emits
no verdict for the scenario it refused:

  2  no --model-cmd and no --dry-run
  3  a rubric under three criteria, naming the scenario
  4  a model command that failed or wrote nothing, or a scenario that wrote
     into the working tree
  5  a dirty working tree at the start of a run that will invoke a model

The overall verdict is computed here, never read from the grader's output. A
criterion the grader did not answer counts as UNCERTAIN, because a silent
criterion is an unanswered one, and a false PASS is worse than a missing verdict.
"""

import argparse
import json
import os
import re
import hashlib
import secrets
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DIRECTIVE_TEMPLATE = os.path.join(REPO_ROOT, "templates", "AGENT_DIRECTIVE.template.md")
sys.path.insert(0, os.path.join(REPO_ROOT, "evals", "scripts"))

import spine_eval_extract as sx  # noqa: E402

MANIFEST = os.path.join(REPO_ROOT, "evals", "spine-evals.json")
RUNS_DIR = os.path.join(REPO_ROOT, "evals", "runs")
DEFAULT_TIMEOUT = 900

EXIT_NO_MODEL_CMD = 2
EXIT_RUBRIC_TOO_THIN = 3
EXIT_MODEL_FAILED = 4
EXIT_DIRTY_TREE = 5

# The one way past the clean-tree refusal. An environment variable rather than a flag, and
# named for what it costs, because the refusal exists to keep a graded run reproducible and
# a convenient-looking flag is the kind an operator reaches for to make a refusal go away.
ALLOW_DIRTY_ENV = "FHORJA_EVAL_ALLOW_DIRTY_TREE"

GRADER_TEMPLATE = """You are scoring one recorded run of an eval scenario.

The criteria, verbatim:

{criteria}

The response under review:

{response}
{disk}
Answer with one line per criterion, in order, in exactly this form:

- Criterion N: PASS | FAIL | UNCERTAIN -- <one sentence>

Then one final line:

- Overall: PASS | FAIL | UNCERTAIN -- <one sentence>

Say UNCERTAIN when the response does not carry enough to decide. Do not restate
the criteria and do not add any other text."""

_VERDICT_LINE = re.compile(
    # A CLI may decorate its first stdout line (kimi prefixes "\u2022 "), and that is not
    # whitespace, so a bare ^\\s*- anchor drops criterion 1 and only criterion 1. Measured
    # 2026-09-01 across three runs: the grader answered it every time and the runner recorded
    # "the grader did not answer this criterion". Leading list glyphs are skipped.
    r"^[\s\u2022\u00b7\u2023\u25e6*>]*-\s*Criterion\s+(\d+)\s*:\s*(PASS|FAIL|UNCERTAIN)\b\s*-*\s*(.*)$",
    re.IGNORECASE | re.MULTILINE,
)


def scenario_number(path):
    """The NN prefix of a scenario filename, as a string."""
    base = os.path.basename(path)
    return base.split("-", 1)[0]


def new_run_id():
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + secrets.token_hex(3)


def load_manifest(path=None):
    # Read the module global at CALL time. A default argument binds once at
    # definition, so a caller that points MANIFEST at a fixture would silently
    # get the real manifest back, and the test would pass against the wrong file.
    with open(path or MANIFEST) as f:
        return json.load(f)


def working_tree_state():
    """`git status --porcelain` as a set of lines, or None when git cannot answer.

    The runner invokes --model-cmd with shell=True and cwd=REPO_ROOT, so the command
    it is handed can write anywhere in this repository. Two guards use this: the run
    refuses to start dirty, and every scenario is compared against the state before it.
    evals/runs/ is gitignored, so the runner's own artifacts never show up here.
    """
    try:
        proc = subprocess.run(
            ["git", "-C", REPO_ROOT, "status", "--porcelain"],
            capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0:
        return None
    return {line for line in proc.stdout.splitlines() if line.strip()}


def run_model(command, prompt, timeout):
    """(stdout, stderr, returncode). Never raises on a failing command."""
    try:
        proc = subprocess.run(
            command, shell=True, cwd=REPO_ROOT, input=prompt,
            capture_output=True, text=True, timeout=timeout,
        )
        return proc.stdout, proc.stderr, proc.returncode
    except subprocess.TimeoutExpired:
        return "", f"timed out after {timeout}s", 124


def parse_grader(raw, criteria_count):
    """[{"criterion": N, "result": ..., "note": ...}, ...], one per criterion.

    A criterion the grader did not answer is UNCERTAIN, not absent: the list is
    always as long as the rubric, so a truncated grader reply cannot shrink the
    rubric it was scored against.
    """
    seen = {}
    for m in _VERDICT_LINE.finditer(raw or ""):
        n = int(m.group(1))
        if 1 <= n <= criteria_count and n not in seen:
            seen[n] = (m.group(2).upper(), m.group(3).strip())
    out = []
    for n in range(1, criteria_count + 1):
        result, note = seen.get(n, ("UNCERTAIN", "the grader did not answer this criterion"))
        out.append({"criterion": n, "result": result, "note": note})
    return out


def overall_of(criteria):
    """FAIL beats UNCERTAIN beats PASS. Computed here, never read from output."""
    results = [c["result"] for c in criteria]
    if "FAIL" in results:
        return "FAIL"
    if "UNCERTAIN" in results:
        return "UNCERTAIN"
    return "PASS"


FIXTURE_TOKEN = "{fixture}"

DISK_PREAMBLE = """
The disk state below was measured by the runner after each turn, not reported by the
model. It is ground truth: a claim in the response that the disk contradicts is false,
and a criterion about a file, a commit or a ledger line is graded against this, not
against what the response says it did.

"""


def snapshot(root):
    """{relative path: sha256} for every file under root, skipping .git internals.

    The runner's own diff of a fixture directory, so a scenario learns what a turn
    wrote without trusting the turn to say so. A response that reports a write the
    disk does not show is exactly the defect scenario 137 hid on 2026-09-22.
    """
    out = {}
    for base, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d != ".git"]
        for name in files:
            full = os.path.join(base, name)
            try:
                with open(full, "rb") as fh:
                    out[os.path.relpath(full, root)] = hashlib.sha256(fh.read()).hexdigest()
            except OSError:
                out[os.path.relpath(full, root)] = "unreadable"
    return out


def snapshot_diff(before, after):
    """Lines naming every file a turn added, changed or removed, sorted."""
    lines = []
    for path in sorted(set(before) | set(after)):
        if path not in before:
            lines.append(f"  added    {path}")
        elif path not in after:
            lines.append(f"  removed  {path}")
        elif before[path] != after[path]:
            lines.append(f"  changed  {path}")
    return lines or ["  (no file added, changed or removed)"]


def fixture_script(entry):
    """Absolute path of the entry's fixture script, or None when it declares none."""
    rel = entry.get("fixture")
    return os.path.join(REPO_ROOT, rel) if rel else None


def probe_script(entry):
    """A read-only probe for a scenario with no fixture, run against the repository itself.

    Scenario 01 writes into the repository it runs in (a project folder and its task
    files), so it needs no fixture, but its criteria still name files. The
    probe reports those files after each turn, so the grader reads them instead of the
    response's account of them."""
    rel = entry.get("probe")
    return os.path.join(REPO_ROOT, rel) if rel else None


def build_fixture(script, timeout=120):
    """(directory, error). The directory is one this runner creates, empty, under the
    system temp root; the script is handed that path and nothing else.

    This is the confinement D-3 asked for before a scenario's setup could run at all:
    the runner never executes a setup block it extracted from prose, and it never hands
    a script a path it did not just create. The script is checked in and reviewed like
    any other file under evals/fixtures/spine/.
    """
    d = tempfile.mkdtemp(prefix="fhorja-spine-")
    try:
        proc = subprocess.run(["bash", script, "build", d], cwd=REPO_ROOT,
                              capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as exc:
        shutil.rmtree(d, ignore_errors=True)
        return None, str(exc)
    if proc.returncode != 0:
        shutil.rmtree(d, ignore_errors=True)
        return None, (proc.stderr or proc.stdout).strip()[:300]
    return d, None


def probe_fixture(script, d, timeout=60):
    """The script's own report of the fixture (git state, a ledger), or a named absence."""
    try:
        proc = subprocess.run(["bash", script, "probe", d], cwd=REPO_ROOT,
                              capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return f"  probe failed: {exc}"
    text = (proc.stdout + proc.stderr).rstrip()
    if proc.returncode != 0:
        return f"  probe exited {proc.returncode}:\n{text}"
    return text or "  (probe printed nothing)"


def build_turns(text, setup, setup_mode, directive="", independent=False):
    """[(prompt, None), ...] with each prompt already assembled, or None when a
    section carries no fenced block. Independent turns carry no earlier transcript,
    so --dry-run shows what the run will send."""
    sections = sx.input_prompt_sections(text)
    turns = []
    for heading, body in sections:
        turn = sx.turn_text(body)
        if turn == sx.UNPARSEABLE:
            return None, heading
        turns.append([turn, None])
    prompts = []
    for i in range(1, len(turns) + 1):
        if independent:
            prompts.append(sx.build_prompt(setup, [[turns[i - 1][0], None]], 1,
                                           setup_mode, directive))
        else:
            prompts.append(sx.build_prompt(setup, turns, i, setup_mode, directive))
    return list(zip(prompts, turns)), None


def record_history(path, line):
    """Append exactly one line to the scenario's '## History', creating the
    section at the end of the file when it has none.

    Append only. It never rewrites or reorders what is already there: the
    History is the durable record of previous runs, and a writer that reorders it
    quietly rewrites evidence.
    """
    with open(path) as f:
        text = f.read()
    if not text.endswith("\n"):
        text += "\n"
    if re.search(r"^## History\s*$", text, re.MULTILINE):
        text = text.rstrip("\n") + "\n" + line + "\n"
    else:
        text = text.rstrip("\n") + "\n\n## History\n\n" + line + "\n"
    with open(path, "w") as f:
        f.write(text)


def history_line(verdict, run_id, num):
    """The fixed shape a later check reads back. Keep it greppable."""
    criteria = verdict["criteria"]
    passed = sum(1 for c in criteria if c["result"] == "PASS")
    failed = [str(c["criterion"]) for c in criteria if c["result"] == "FAIL"]
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return (f"- {day}: run {run_id} | model={verdict['model_label']} "
            f"grader={verdict['grader_label']} | {verdict['overall']} "
            f"{passed}/{len(criteria)} | failed: {', '.join(failed) or 'none'} "
            f"| artifacts: evals/runs/{run_id}/{num}/")


def main(argv=None):
    p = argparse.ArgumentParser(
        description="Run the spine scenarios against a model and record the artifacts.")
    p.add_argument("--scenario", help="run only the scenario whose filename starts with this")
    p.add_argument("--model-cmd", default=os.environ.get("FHORJA_EVAL_MODEL_CMD"),
                   help="shell command reading a prompt on stdin, writing a response on stdout. "
                        "A rubric that grades several command turns needs the WHOLE transcript, "
                        "and a CLI in plain print mode returns only its final message; see "
                        "evals/README.md for how to flatten a streaming transcript in this "
                        "command string, which is where vendor knowledge belongs")
    p.add_argument("--grader-cmd", default=os.environ.get("FHORJA_EVAL_GRADER_CMD"),
                   help="same contract as --model-cmd; defaults to --model-cmd")
    p.add_argument("--model-label", default="unlabelled")
    p.add_argument("--grader-label", default="unlabelled")
    p.add_argument("--dry-run", action="store_true",
                   help="assemble and print every prompt and rubric; invoke nothing, write nothing")
    # The runner has never executed a scenario's shell setup and does not start now:
    # its only subprocess for scenario work is the model command itself. So the old
    # name, --allow-setup-shell, promised something no code does. What the flag really
    # removes is the SKIP, which means the scenario is graded against a tree its setup
    # never prepared. The name now says that, because a flag whose name overstates what
    # it enables is the kind a tired operator passes to make a skip go away.
    p.add_argument("--grade-without-setup", action="store_true",
                   help="run a scenario whose setup is a shell script WITHOUT that script "
                        "having run, so it is graded against an unprepared tree")
    p.add_argument("--record", action="store_true",
                   help="append one line per computed verdict to the scenario's ## History")
    args = p.parse_args(argv)
    # A correctly installed Fhorja puts this paragraph in the consuming repository's
    # always-loaded instruction file (ADR-0189). The rubrics grade a command chain, so the
    # prompt has to describe the configuration that runs one. An absent template means the
    # eval runs the install-without-its-last-step configuration, which is real, not an error.
    directive = sx.read_directive(DIRECTIVE_TEMPLATE)
    if not directive:
        sys.stderr.write("run-spine-evals: no agent directive found at "
                         f"{os.path.relpath(DIRECTIVE_TEMPLATE, REPO_ROOT)}; prompts will "
                         "not carry it, so a chain-grading rubric is measuring an install "
                         "with its last step missing (ADR-0189)\n")

    if not args.model_cmd and not args.dry_run:
        sys.stderr.write(
            "run-spine-evals: no --model-cmd and no --dry-run, so there is nothing to run.\n"
            "Pass --model-cmd '<command reading stdin>' or set FHORJA_EVAL_MODEL_CMD,\n"
            "or pass --dry-run to print the prompts without invoking anything.\n")
        return EXIT_NO_MODEL_CMD

    if args.record and args.model_label == "unlabelled":
        sys.stderr.write(
            "run-spine-evals: --record needs --model-label. The runner cannot tell which\n"
            "model sits behind a shell command, and a verdict with no model attribution\n"
            "is not worth recording.\n")
        return EXIT_NO_MODEL_CMD

    # A run that invokes a model starts from a clean tree or does not start. Two reasons,
    # and the second is the one that bites: the model command runs with shell=True from the
    # repository root, so it can write here, and the per-scenario diff below can only name
    # what a scenario wrote if there was nothing to confuse it with. --dry-run invokes
    # nothing and writes nothing, so it is exempt.
    baseline = None
    if args.model_cmd and not args.dry_run:
        baseline = working_tree_state()
        if baseline is None:
            sys.stderr.write(
                "run-spine-evals: cannot read the working tree state from git, so an\n"
                "unexpected write could not be told from an expected one. Refusing.\n")
            return EXIT_DIRTY_TREE
        if baseline and os.environ.get(ALLOW_DIRTY_ENV) != "1":
            sys.stderr.write(
                "run-spine-evals: the working tree is dirty, so this run would grade a model\n"
                "against a state no commit describes, and a later reader could not reproduce\n"
                "it. Commit or stash first. Dirty paths:\n")
            for line in sorted(baseline)[:20]:
                sys.stderr.write(f"  {line}\n")
            if len(baseline) > 20:
                sys.stderr.write(f"  ... and {len(baseline) - 20} more\n")
            sys.stderr.write(
                f"Setting {ALLOW_DIRTY_ENV}=1 starts anyway. It exists so the runner's own\n"
                "test suite can exercise the plumbing while someone is editing this file, and\n"
                "a run that uses it says so on stdout. It does not make the run reproducible.\n")
            return EXIT_DIRTY_TREE
        if baseline:
            # Said on stdout, not stderr, so it lands in whatever the operator captured as
            # the run's own record. An escape nobody can see in the artifact is a silent one.
            print(f"NOTE: started from a dirty tree with {ALLOW_DIRTY_ENV}=1. "
                  f"{len(baseline)} path(s) were already modified; only writes made after "
                  f"this point are attributed to a scenario. This run is not reproducible.")
            print()

    manifest = load_manifest()
    entries = manifest["scenarios"]
    if args.scenario:
        entries = [e for e in entries
                   if os.path.basename(e["file"]).startswith(args.scenario)]
        if not entries:
            sys.stderr.write(f"run-spine-evals: no manifest entry matches {args.scenario!r}\n")
            return EXIT_NO_MODEL_CMD

    run_id = new_run_id()
    run_dir = os.path.join(RUNS_DIR, run_id)
    grader_cmd = args.grader_cmd or args.model_cmd
    failed = False

    for entry in entries:
        path = os.path.join(REPO_ROOT, entry["file"])
        name = os.path.basename(entry["file"])
        num = scenario_number(entry["file"])
        with open(path) as f:
            text = f.read()

        print(f"=== {num} {name} ===")

        if entry.get("setup") == "shell" and not args.grade_without_setup:
            print("SKIPPED (setup is a shell script and this runner never runs one)")
            print()
            continue

        try:
            criteria = sx.rubric_items(text, name)
        except sx.RubricTooThin as exc:
            sys.stderr.write(f"run-spine-evals: {exc}\n")
            return EXIT_RUBRIC_TOO_THIN

        setup = sx.read_setup(text)
        built, bad_heading = build_turns(text, setup, entry.get("setup", "none"), directive,
                                         entry.get("turns") == "independent")
        if built is None:
            print(f"{sx.UNPARSEABLE}: {name} {bad_heading}")
            failed = True
            continue

        rubric = "\n".join(criteria)

        if args.dry_run:
            for i, (prompt, _turn) in enumerate(built, 1):
                print(f"--- prompt turn {i} ({len(prompt)} chars) ---")
                print(prompt)
            print("--- rubric ---")
            print(rubric)
            print()
            continue

        scenario_dir = os.path.join(run_dir, num)
        os.makedirs(scenario_dir, exist_ok=True)
        timeout = entry.get("timeout_seconds", DEFAULT_TIMEOUT)

        turns = [list(t) for _p, t in built]
        responses = []
        disk = []
        broke = False
        # "independent": each turn is its own conversation, with its own fresh fixture.
        # Scenario 08 compares a minimal run with a strict one, and chained, the strict run
        # inherited the minimal run's findings (strict alone 4,145 chars, chained 2,969).
        # Scenario 125's turn 1b needs something staged, and a chained turn 1 had committed it.
        independent = entry.get("turns") == "independent"
        script = fixture_script(entry)
        fixture_dir = None
        for i in range(1, len(turns) + 1):
            if script and (fixture_dir is None or independent):
                if fixture_dir:
                    shutil.rmtree(fixture_dir, ignore_errors=True)
                fixture_dir, ferr = build_fixture(script)
                if fixture_dir is None:
                    sys.stderr.write(f"run-spine-evals: {name} turn {i}: fixture build "
                                     f"failed: {ferr}\n")
                    print("ERROR")
                    failed = broke = True
                    break
            user_text = turns[i - 1][0]
            if fixture_dir:
                user_text = user_text.replace(FIXTURE_TOKEN, fixture_dir)
            if independent:
                prompt = sx.build_prompt(setup, [[user_text, None]], 1,
                                         entry.get("setup", "none"), directive)
            else:
                turns[i - 1][0] = user_text
                prompt = sx.build_prompt(setup, turns, i, entry.get("setup", "none"), directive)
            with open(os.path.join(scenario_dir, f"prompt-turn-{i}.txt"), "w") as f:
                f.write(prompt)
            before = snapshot(fixture_dir) if fixture_dir else None
            out, err, rc = run_model(args.model_cmd, prompt, timeout)
            if rc != 0 or not out.strip():
                sys.stderr.write(
                    f"run-spine-evals: {name} turn {i}: model command exit {rc}, "
                    f"{len(out)} byte(s) on stdout. {err.strip()[:200]}\n")
                print("ERROR")
                failed = True
                broke = True
                break
            with open(os.path.join(scenario_dir, f"response-turn-{i}.txt"), "w") as f:
                f.write(out)
            turns[i - 1][1] = out
            responses.append(out)
            state = None
            if fixture_dir:
                state = ("\n".join([f"Turn {i}, files the turn wrote under the fixture:"]
                                   + snapshot_diff(before, snapshot(fixture_dir)))
                         + f"\nTurn {i}, fixture probe:\n" + probe_fixture(script, fixture_dir))
            elif probe_script(entry):
                state = (f"Turn {i}, repository probe:\n"
                         + probe_fixture(probe_script(entry), REPO_ROOT))
            if state:
                with open(os.path.join(scenario_dir, f"disk-after-turn-{i}.txt"), "w") as f:
                    f.write(state + "\n")
                disk.append(state)
        if fixture_dir:
            shutil.rmtree(fixture_dir, ignore_errors=True)
        if broke:
            continue

        with open(os.path.join(scenario_dir, "rubric.txt"), "w") as f:
            f.write(rubric)

        if len(responses) > 1:
            response_text = "\n\n".join(f"--- turn {i} ---\n{r}"
                                         for i, r in enumerate(responses, 1))
        else:
            response_text = "\n\n".join(responses)
        grader_prompt = GRADER_TEMPLATE.format(
            criteria=rubric, response=response_text,
            disk=(DISK_PREAMBLE + "\n\n".join(disk) + "\n") if disk else "")
        raw, err, rc = run_model(grader_cmd, grader_prompt, timeout)
        with open(os.path.join(scenario_dir, "grader-raw.txt"), "w") as f:
            f.write(raw)
        if rc != 0 or not raw.strip():
            sys.stderr.write(
                f"run-spine-evals: {name}: grader command exit {rc}, "
                f"{len(raw)} byte(s) on stdout. {err.strip()[:200]}\n")
            print("ERROR")
            failed = True
            continue

        scored = parse_grader(raw, len(criteria))
        verdict = {
            "scenario": name,
            "scenario_number": num,
            "run_id": run_id,
            "model_label": args.model_label,
            "grader_label": args.grader_label,
            "criteria": scored,
            "overall": overall_of(scored),
        }
        with open(os.path.join(scenario_dir, "verdict.json"), "w") as f:
            json.dump(verdict, f, indent=2)
            f.write("\n")
        print(f"{verdict['overall']}  ({sum(1 for c in scored if c['result'] == 'PASS')}"
              f"/{len(scored)} criteria PASS)")
        # A verdict says a criterion failed. It does not say why, and the note beside it is the
        # GRADER's reading of the response, not the response. Reading the notes and concluding
        # from them produced two wrong conclusions about one criterion on 2026-09-01, each of
        # which would have changed a command that did not need changing, while the model's own
        # words sat in a file on disk. So the path is printed at the point of reading rather
        # than left to be looked up.
        unresolved = [c['criterion'] for c in scored if c['result'] != 'PASS']
        if unresolved:
            names = ', '.join(str(c) for c in unresolved)
            print(f"  criteria not PASS: {names}. The notes beside them are the grader's reading,")
            print(f"  not the model's words. Read those in "
                  f"evals/runs/{run_id}/{num}/response-turn-*.txt before concluding anything")
            print("  about the command, the scenario, or the model.")
        print()

        wrote = False
        if baseline is not None:
            after = working_tree_state()
            if after is None:
                print("ERROR")
                sys.stderr.write(
                    f"run-spine-evals: {name}: git stopped answering, so this scenario's\n"
                    "writes could not be checked. Treating that as a failure.\n")
                failed = True
                wrote = True
            elif after - baseline:
                print("ERROR")
                sys.stderr.write(
                    f"run-spine-evals: {name} wrote into the working tree. An eval reads the\n"
                    "repository, it does not edit it, and a scenario that edits it makes every\n"
                    "later scenario in the run read a tree nobody described:\n")
                for line in sorted(after - baseline)[:20]:
                    sys.stderr.write(f"  {line}\n")
                failed = True
                # Move the baseline forward so the next scenario is judged on what IT wrote
                # rather than inheriting this one's mess.
                baseline = after
                wrote = True

        if args.record and not wrote:
            # Only a computed verdict writes. ERROR and SKIPPED reached neither of the
            # `continue`s above, and a scenario that wrote into the tree is an ERROR too,
            # so none of them can poison the scenario's history. This runs AFTER the tree
            # check: the history line is itself a write into the tree, and checked first it
            # turned every recorded run on a clean tree into an ERROR (2026-09-23, scenario 141).
            record_history(path, history_line(verdict, run_id, num))
            if baseline is not None:
                refreshed = working_tree_state()
                if refreshed is not None:
                    baseline = refreshed

    if not args.dry_run:
        print(f"artifacts: evals/runs/{run_id}/")
    return EXIT_MODEL_FAILED if failed else 0


if __name__ == "__main__":
    sys.exit(main())
