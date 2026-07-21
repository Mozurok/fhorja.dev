#!/usr/bin/env python3
"""Structural evals: the automatable subset of the scenario regression net.

The eval scenarios under evals/scenarios/ are prose cases: a reviewer reads a
model's output against numbered pass criteria (evals/scripts/run-evals.sh walks
them). That review is not automatable without running a model, and this script
does NOT run a model.

What it DOES do is run the structural invariants that a subset of those
scenarios depend on, the parts that reduce to a static property of this repo.
Each check names the scenario(s) it enforces. If one of these invariants breaks,
the corresponding scenario cannot pass, so catching it here is a real regression
gate that runs in CI on every push.

This covers a subset by design. The output prints exactly which scenarios are
covered by a static check and states plainly that the rest stay manual; it never
implies full automated coverage.

Exit code: 0 if every check passes, 1 if any fails.
"""

import os
import re
import sys
import glob

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def p(*parts):
    return os.path.join(REPO, *parts)


def read(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


# Each check returns (ok: bool, failures: list[str]). The registry maps a short
# id to (scenarios, description, fn).

def _command_files():
    """Flat command files plus folder-shaped persona SKILL.md sources."""
    flat = sorted(glob.glob(p("commands", "*.md")))
    folder = sorted(glob.glob(p("commands", "*", "SKILL.md")))
    return flat + folder


def _command_basenames():
    names = set()
    for f in glob.glob(p("commands", "*.md")):
        names.add(os.path.splitext(os.path.basename(f))[0])
    for d in glob.glob(p("commands", "*", "SKILL.md")):
        names.add(os.path.basename(os.path.dirname(d)))
    return names


def _scenario_files():
    return sorted(glob.glob(p("evals", "scenarios", "[0-9]*.md")))


def check_corpus_wellformed():
    """[scenario corpus] Every scenario file carries the sections a reviewer needs.

    The corpus is intentionally heterogeneous: behavioral scenarios use an Input
    prompt, while CI/structural scenarios (34-43) use Setup/Steps. So the
    universal invariants checked here are the three every scenario shares: a
    goal or title, a criteria section, and a failure section. A scenario missing
    any of these is a hole in the regression net, so the net's own integrity is
    itself an eval.
    """
    # The corpus spans several years and uses varied but equivalent headings
    # ("Goal"/"Purpose"/"Intent"; "Expected response shape"/"Expected behavior"/
    # "Pass criteria"; "What a FAIL"/"Failure modes"/"Failure signals"/"FAIL
    # conditions"). The matchers below accept every accepted variant, so the
    # check flags a genuinely missing section, not a stylistic difference.
    fails = []
    for f in _scenario_files():
        body = read(f)
        name = os.path.basename(f)
        has_goal = (
            re.search(r"^#\s+(eval\s+)?scenario\b", body, re.I | re.M)
            or re.search(r"^##\s+(goal|purpose|intent)\b", body, re.I | re.M)
        )
        has_criteria = re.search(r"^##\s+(expected|pass\s+criteria)", body, re.I | re.M)
        has_fail = re.search(r"^##.*\bfail", body, re.I | re.M)
        missing = []
        if not has_goal:
            missing.append("Goal or title")
        if not has_criteria:
            missing.append("Expected/Pass criteria")
        if not has_fail:
            missing.append("FAIL/Failure section")
        if missing:
            fails.append(f"{name}: missing {', '.join(missing)}")
    return (not fails, fails)


def check_scenario_numbers_unique():
    """[scenario corpus] No two scenario files claim the same NN prefix."""
    seen = {}
    fails = []
    for f in _scenario_files():
        name = os.path.basename(f)
        num = name.split("-")[0]
        if num in seen:
            fails.append(f"duplicate scenario number {num}: {seen[num]} and {name}")
        else:
            seen[num] = name
    return (not fails, fails)


def check_command_frontmatter_name():
    """[frontmatter scenarios] Every flat command's frontmatter name equals its basename."""
    fails = []
    for f in glob.glob(p("commands", "*.md")):
        base = os.path.splitext(os.path.basename(f))[0]
        body = read(f)
        m = re.search(r"^name:\s*(\S+)", body, re.M)
        if not m:
            fails.append(f"{base}.md: no frontmatter name")
        elif m.group(1) != base:
            fails.append(f"{base}.md: frontmatter name '{m.group(1)}' != basename")
    return (not fails, fails)


def check_count_markers():
    """[count-marker scenarios] Every count marker equals the on-disk count."""
    import subprocess
    script = p("scripts", "reconcile-counts.sh")
    if not os.path.exists(script):
        return (True, [])  # nothing to check
    res = subprocess.run(["bash", script, "--check"], cwd=REPO,
                         capture_output=True, text=True)
    if res.returncode == 0:
        return (True, [])
    out = (res.stdout + res.stderr).strip().splitlines()
    return (False, [l for l in out if l.strip()][:20])


def check_corpus_indexed():
    """[scenario corpus] Every scenario file is linked from evals/README.md."""
    index = read(p("evals", "README.md"))
    fails = []
    for f in _scenario_files():
        name = os.path.basename(f)
        if name not in index:
            fails.append(f"{name}: no row in evals/README.md")
    return (not fails, fails)


def check_handoff_basenames():
    """[scenario 85] Every `Run now: <name>` in a command names a real command.

    Scenario 85 (handoff routing integrity) fails if a handoff routes a name
    with no commands/<name>.md file (the device-verify defect class). The static
    invariant: no command file's own examples reference a non-existent command.
    """
    real = _command_basenames()
    # A curated allowlist of illustrative placeholders used in prose examples of
    # what an INVALID handoff looks like (the scenarios teach the failure mode).
    known_illustrative = {"device-verify", "test-on-device", "task-plan", "plan", "execute-task"}
    pat = re.compile(r"Run now:\s*/?([a-z][a-z0-9-]+)")
    fails = []
    for f in _command_files():
        body = read(f)
        for m in pat.finditer(body):
            name = m.group(1)
            if name in real or name in known_illustrative:
                continue
            fails.append(f"{os.path.relpath(f, REPO)}: Run now references unknown command '{name}'")
    return (not fails, fails)


def check_required_sections():
    """[required-sections scenarios] Every command carries its DoD and Handoff."""
    fails = []
    for f in _command_files():
        body = read(f)
        rel = os.path.relpath(f, REPO)
        if "### Definition of done" not in body:
            fails.append(f"{rel}: no '### Definition of done'")
        if "### Handoff" not in body:
            fails.append(f"{rel}: no '### Handoff'")
    return (not fails, fails)


def check_registry_membership():
    """[registry scenarios] Every command appears in the human-facing registries."""
    stubs = read(p("COMMAND_PROMPT_STUBS.md"))
    roles = read(p("wos", "command-roles.md"))
    fails = []
    for name in sorted(_command_basenames()):
        if name not in stubs:
            fails.append(f"{name}: missing from COMMAND_PROMPT_STUBS.md")
        if name not in roles:
            fails.append(f"{name}: missing from wos/command-roles.md")
    return (not fails, fails)


def check_adr_indexed():
    """[ADR index scenarios] Every ADR file has a row in docs/adr/README.md."""
    index = read(p("docs", "adr", "README.md"))
    fails = []
    for f in glob.glob(p("docs", "adr", "[0-9]*.md")):
        name = os.path.basename(f)
        num = name.split("-")[0]
        if name not in index and num not in index:
            fails.append(f"{name}: no row in docs/adr/README.md")
    return (not fails, fails)


def check_no_emdash():
    """[natural-voice / forbidden-bytes scenarios] No em-dash in commands or root docs."""
    fails = []
    targets = _command_files() + [
        p("README.md"), p("docs", "FAQ.md"), p("CONTRIBUTING.md"),
        p("WORKFLOW_OPERATING_SYSTEM.md"), p("COMMAND_PROMPT_STUBS.md"),
    ]
    for f in targets:
        if not os.path.exists(f):
            continue
        body = read(f)
        if "—" in body:
            n = body.count("—")
            fails.append(f"{os.path.relpath(f, REPO)}: {n} em-dash character(s)")
    return (not fails, fails)


def check_shared_block_sources():
    """[shared-block scenarios] Every <!-- shared:X --> marker has a canonical source."""
    fails = []
    pat = re.compile(r"<!--\s*shared:([a-z0-9-]+)\s*-->")
    for f in _command_files():
        body = read(f)
        for m in pat.finditer(body):
            block = m.group(1)
            src = p("commands", "_shared", f"{block}.md")
            if not os.path.exists(src):
                fails.append(f"{os.path.relpath(f, REPO)}: shared block '{block}' has no _shared source")
    return (not fails, fails)


def check_epistemic_doctrine_surfaces():
    """[scenarios 110, 112] The ADR-0109 doctrine's load-bearing surfaces exist and
    the claim-grounding block covers the whole universal command layer.

    Guards TEST_STRATEGY.md row 8 (a silent removal of the spec fold, the reference
    topic, or the read-map reference) and row 7's completeness half (a command
    dropping the universal claim-grounding marker). The invariant is claim-driven,
    not count-driven: every command file that carries the standard-output-layout
    shared marker (the universal layer) MUST also carry claim-grounding. This covers
    both the flat commands/*.md and the folder-shaped persona commands/*/SKILL.md.
    The row 6 no-confidence-field property is guarded warn-only by
    scripts/check-claim-grounding.sh, not here (structural: a prose check would be
    brittle and the doctrine forbids asserting its own wording).
    """
    fails = []
    spec = read(p("WORKFLOW_OPERATING_SYSTEM.md"))
    if not re.search(r"^### Claim status and abstention", spec, re.M):
        fails.append("WORKFLOW_OPERATING_SYSTEM.md: missing '### Claim status and abstention' H3 (ADR-0109 spec fold)")
    if "active-epistemic-humility.md" not in spec:
        fails.append("WORKFLOW_OPERATING_SYSTEM.md: no reference to wos/active-epistemic-humility.md (read-map row and H3 both gone)")
    if not os.path.exists(p("wos", "active-epistemic-humility.md")):
        fails.append("wos/active-epistemic-humility.md: reference topic missing")
    if not os.path.exists(p("commands", "_shared", "claim-grounding.md")):
        fails.append("commands/_shared/claim-grounding.md: shared block source missing")
    for f in _command_files():
        body = read(f)
        if "shared:standard-output-layout" in body and "shared:claim-grounding" not in body:
            fails.append(f"{os.path.relpath(f, REPO)}: has standard-output-layout but missing <!-- shared:claim-grounding --> marker")
    return (not fails, fails)


CHECKS = [
    ("corpus-wellformed", "scenario corpus", "every scenario has a goal, criteria, and a FAIL section", check_corpus_wellformed),
    ("corpus-indexed", "scenario corpus", "every scenario is linked from evals/README.md", check_corpus_indexed),
    ("scenario-numbers-unique", "scenario corpus", "no two scenarios claim the same number", check_scenario_numbers_unique),
    ("handoff-basenames", "scenario 85", "every Run now: in a command names a real command", check_handoff_basenames),
    ("required-sections", "required-section scenarios", "every command has a Definition of done + Handoff", check_required_sections),
    ("command-frontmatter", "frontmatter scenarios", "every command's frontmatter name equals its basename", check_command_frontmatter_name),
    ("registry-membership", "registry scenarios", "every command appears in the human-facing registries", check_registry_membership),
    ("count-markers", "count-marker scenarios", "every count marker equals the on-disk count", check_count_markers),
    ("adr-indexed", "ADR index scenarios", "every ADR file has a row in docs/adr/README.md", check_adr_indexed),
    ("no-emdash", "forbidden-bytes scenarios", "no em-dash in commands or root docs", check_no_emdash),
    ("shared-block-sources", "shared-block scenarios", "every <!-- shared:X --> has a canonical source", check_shared_block_sources),
    ("epistemic-doctrine-surfaces", "scenarios 110, 112", "the ADR-0109 doctrine surfaces exist and claim-grounding covers the universal command layer", check_epistemic_doctrine_surfaces),
]


def main():
    print("Structural evals: the automatable subset of the scenario regression net.")
    print("(This does NOT run a model; it asserts the repo invariants a subset of scenarios depend on.)")
    print("=" * 78)
    total = len(CHECKS)
    passed = 0
    any_fail = False
    for cid, scen, desc, fn in CHECKS:
        ok, fails = fn()
        status = "PASS" if ok else "FAIL"
        print(f"[{status}] {cid:<22} ({scen}): {desc}")
        if not ok:
            any_fail = True
            for line in fails[:20]:
                print(f"         - {line}")
            if len(fails) > 20:
                print(f"         ... and {len(fails) - 20} more")
        else:
            passed += 1
    print("=" * 78)
    n_scenarios = len(_scenario_files())
    print(f"Structural checks: {passed}/{total} passed.")
    print(f"Coverage: these {total} checks cover the statically-verifiable invariants of a")
    print(f"subset of the {n_scenarios} scenarios. The rest are behavioral and stay MANUAL")
    print("(run evals/scripts/run-evals.sh, paste each prompt into your AI tool, read the")
    print("output against the pass criteria). No claim of full automated coverage is made.")
    return 1 if any_fail else 0


if __name__ == "__main__":
    sys.exit(main())
