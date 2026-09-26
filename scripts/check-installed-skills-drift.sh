#!/usr/bin/env bash
# check-installed-skills-drift.sh
#
# Advisory (warn-only, NEVER fails the build) drift check between the canonical
# `commands/<name>.md` sources and the copies actually installed under the
# operator's agent roots. Three arms: the skill DESCRIPTION, the skill BODY, and
# the docs PAYLOAD (the wos topics and the spec) that sits beside the skills.
#
# The body and payload arms were added after the description arm alone reported
# `0 differ` across all three roots on 2026-08-30 while 98 of 98 bodies differed,
# the wos topic count was 55 installed against 54 in the repo, and the spec was
# 81706 bytes installed against 81210. The cause was one older generator's
# frontmatter shape, not 98 separate events, but the guard could not see any of
# it: it was green about the one field it read and blind to the file around it.
#
# Why this exists. The Advertise stage is the only cost every session pays before
# any work starts, and `check_advertise_stage_budget` (ADR-0135, Layer 1) measures
# the REPO. The model reads the INSTALLED copy. On 2026-08-21 those had diverged:
# the repo stood at 72272 chars after the ADR-0154/0155/0157 trim of 38
# descriptions, while all three install roots sat at exactly 81065, the pre-trim
# figure. 2198 tokens of earned saving had never reached the machine, and nothing
# reported it. Running `sync-workflow-slash-commands.sh` (skills sync by default) is manual.
#
# Layer 2 by necessity, not by preference: CI cannot see a developer's home
# directory, so this can never be a build gate. It is the honest ceiling for this
# check, and the script says so rather than implying more.
#
# A root that is absent is reported as NOT MEASURED, never as clean. A checker
# that measures zero inputs and prints clean is the defect this repository fixed
# once in check-instruction-budget.sh; do not reintroduce it here.
#
# Exit codes: ALWAYS 0 (advisory), except 2 on a usage error.

set -uo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERBOSE=0
case "${1:-}" in
  --verbose|-v) VERBOSE=1 ;;
  "") ;;
  *) echo "check-installed-skills-drift: skipped (usage error: unknown argument '$1')" >&2; exit 2 ;;
esac

VERBOSE="$VERBOSE" python3 - "$REPO_ROOT" <<'PY'
import os, sys, glob, re, importlib.util

repo = sys.argv[1]
verbose = os.environ.get("VERBOSE") == "1"

spec = importlib.util.spec_from_file_location(
    "se", os.path.join(repo, "evals", "scripts", "structural-evals.py"))
se = importlib.util.module_from_spec(spec)
sys.modules["se"] = se
spec.loader.exec_module(se)
canon, _ = se.skill_descriptions(None)
canon = {k: v for k, v in canon.items() if v}

if not canon:
    print("Installed-skills-drift: not measured (no canonical descriptions parsed from the repo)")
    sys.exit(0)

# ~/.claude/skills and ~/.agents/skills are where a default sync writes. ~/.cursor/skills is
# written only under --cursor-skills since ADR-0228, but an install from before that left the
# skills there and Cursor still reads them, so it stays measured whenever it exists. A sync
# without --cursor-skills does not refresh it; the line printed below says which flag does.
ROOTS = [os.path.expanduser(p) for p in
         ("~/.claude/skills", "~/.agents/skills", "~/.cursor/skills")]
OPT_IN_ROOT = os.path.expanduser("~/.cursor/skills")

def read_installed(root):
    """Fhorja skill descriptions under `root`, via the CANONICAL parser.

    Never write a second parser for these. `routing-probe.py` carries the same
    warning for the same reason: a hand-rolled regex here captured the leading
    "- " of a YAML block scalar that the canonical parser strips, and reported
    98 of 98 descriptions as drifted when 40 had. The number was wrong in the
    alarming direction, which is not safer, just differently wrong.
    """
    d, _ = se.skill_descriptions(root)
    return {k: v for k, v in d.items() if v and k in canon}


def body_differ(root, inst):
    """Names whose INSTALLED SKILL.md body differs from the repo's generated one.

    The description arm above compares one field. Measured 2026-08-30 it reported
    `0 differ` across all three roots while 98 of 98 bodies differed: the machine
    carried an older generator's frontmatter shape (`multi-repo-aware: false` and
    list-valued layer keys) against the repo's quoted scalars, so every body was
    stale and every description matched. A guard green on the field it reads and
    blind to the file around it is worse than no guard, because the green is cited.

    Byte comparison on purpose. Anything softer reintroduces a second parser, which
    is what the read_installed docstring above already refuses.
    """
    out = []
    for name in sorted(inst):
        repo_body = os.path.join(repo, ".claude", "skills", name, "SKILL.md")
        inst_body = os.path.join(root, name, "SKILL.md")
        try:
            with open(repo_body, "rb") as a, open(inst_body, "rb") as b:
                if a.read() != b.read():
                    out.append(name)
        except OSError:
            continue
    return out


def payload_rows(root):
    """The docs payload beside the skills: the wos topics and the spec.

    A skill body can match while the reference material it cites does not, and
    that half was never measured. Reports per root and says `not measured` when
    the payload directory is absent, which is the case for one root today and for
    every root in CI.
    """
    docs = os.path.join(os.path.dirname(root), "workflow-docs")
    if not os.path.isdir(docs):
        return f"payload not measured (no {os.path.basename(docs)}/ beside the skills)"
    parts = []
    inst_wos = os.path.join(docs, "wos")
    if os.path.isdir(inst_wos):
        r = len(glob.glob(os.path.join(repo, "wos", "*.md")))
        i = len(glob.glob(os.path.join(inst_wos, "*.md")))
        parts.append(f"wos {i} installed vs {r} in the repo" if i != r
                     else f"wos {r} topic(s) match")
    else:
        parts.append("wos not measured")
    spec_name = "WORKFLOW_OPERATING_SYSTEM.md"
    inst_spec = os.path.join(docs, spec_name)
    repo_spec = os.path.join(repo, spec_name)
    if os.path.isfile(inst_spec) and os.path.isfile(repo_spec):
        i, r = os.path.getsize(inst_spec), os.path.getsize(repo_spec)
        parts.append(f"spec {i} vs {r} bytes" if i != r else "spec matches")
    else:
        parts.append("spec not measured")
    return "payload: " + ", ".join(parts)


present = [r for r in ROOTS if os.path.isdir(r)]
absent = [r for r in ROOTS if not os.path.isdir(r)]

if not present:
    print(f"Installed-skills-drift: not measured (none of the {len(ROOTS)} agent "
          "roots exist here; this check cannot run in CI by design)")
    sys.exit(0)

repo_chars = sum(len(v) for v in canon.values())
rows, drifted_names, body_names = [], set(), set()
for root in present:
    inst = read_installed(root)
    if not inst:
        rows.append((root, 0, 0, 0, 0, "no Fhorja skills installed", []))
        continue
    differ = [n for n, d in inst.items() if canon.get(n, "") != d]
    missing = [n for n in canon if n not in inst]
    ichars = sum(len(v) for v in inst.values())
    rchars = sum(len(canon[n]) for n in inst)
    bdiff = body_differ(root, inst)
    rows.append((root, len(inst), len(differ), len(missing), ichars - rchars, "", bdiff))
    drifted_names.update(differ)
    body_names.update(bdiff)

parts = []
if drifted_names:
    parts.append(f"{len(drifted_names)} distinct description(s) differ")
if body_names:
    parts.append(f"{len(body_names)} distinct body(ies) differ")
label = ", ".join(parts) + " from the repo" if parts else "clean"
print(f"Installed-skills-drift: {label} (warn-only; measured {len(present)} of "
      f"{len(ROOTS)} agent root(s)"
      + (f", {len(absent)} absent and NOT measured" if absent else "") + ")")

for root, n, differ, missing, delta, note, bdiff in rows:
    short = root.replace(os.path.expanduser("~"), "~")
    if note:
        print(f"  {short}: {note}")
        continue
    extra = f", costs {delta:+d} chars (~{delta // 4:+d} tokens) per session" if delta else ""
    miss = f", {missing} not installed" if missing else ""
    print(f"  {short}: {n} Fhorja skill(s), {differ} description(s) differ, "
          f"{len(bdiff)} body(ies) differ{miss}{extra}")
    print(f"    {payload_rows(root)}")

if drifted_names or body_names:
    print("  Run scripts/sync-workflow-slash-commands.sh to reconcile (skills sync by default).")
    if OPT_IN_ROOT in present:
        print("  ~/.cursor/skills is refreshed only with --cursor-skills (ADR-0228); without it, "
              "--clean-orphans removes the Fhorja skills there after asking.")
    print(f"  The repo's own Advertise total is {repo_chars} chars (~{repo_chars // 4} tokens); "
          "check_advertise_stage_budget measures that number, never the installed copies.")

if verbose and drifted_names:
    for root in present:
        inst = read_installed(root)
        d = sorted(n for n, v in inst.items() if canon.get(n, "") != v)
        if d:
            print(f"  {root.replace(os.path.expanduser('~'), '~')} drifted: {', '.join(d)}")
PY
