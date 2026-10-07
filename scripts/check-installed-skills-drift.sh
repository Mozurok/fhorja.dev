#!/usr/bin/env bash
# Advisory comparison of installed Fhorja skills and runtime documentation.
# Skill roots and adapter docs roots are separate: a shared skills directory does
# not imply a shared docs destination. Environment overrides mirror the installer.
# Exact skill bytes and recursive wos markdown paths/content are checked, together
# with the spec. Helper scripts, shared blocks and optional docs are not checked.
# Missing, unreadable and partial inventories never produce an unconditional clean.
# Exit 0 is advisory, including missing inputs; exit 2 means invalid arguments.
set -uo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERBOSE=0
case "$#:${1:-}" in
  0:) ;;
  1:--verbose|1:-v) VERBOSE=1 ;;
  *) echo "check-installed-skills-drift: skipped (usage error: expected no arguments or --verbose)" >&2; exit 2 ;;
esac
VERBOSE="$VERBOSE" python3 - "$REPO_ROOT" <<'PY'
import importlib.util
import glob
import os
from pathlib import Path
import sys

repo = Path(sys.argv[1])
verbose = os.environ.get("VERBOSE") == "1"
try:
    spec = importlib.util.spec_from_file_location("se", repo / "evals/scripts/structural-evals.py")
    se = importlib.util.module_from_spec(spec)
    sys.modules["se"] = se
    spec.loader.exec_module(se)
    canon, _ = se.skill_descriptions(glob.escape(str(repo / ".claude/skills")))
    if not canon or any(not value for value in canon.values()):
        raise ValueError("canonical descriptions absent or unparsed")
    registered = {path.stem for path in (repo / "commands").glob("*.md")}
    registered.update(path.parent.name for path in (repo / "commands").glob("*/SKILL.md"))
    if registered != set(canon):
        raise ValueError("canonical catalog incomplete or stale: missing "
                         + ", ".join(sorted(registered - set(canon)))
                         + "; extra " + ", ".join(sorted(set(canon) - registered)))
except (OSError, UnicodeError, ValueError) as error:
    print(f"Installed-skills-drift: not measured ({error})")
    sys.exit(0)

# Preserve the installer's nonempty override semantics, including Kimi's home
# precedence. Do not infer docs as siblings of the shared .agents skills root.
home = Path(os.path.expanduser("~"))
def destination(key, default):
    return Path(os.environ.get(key) or default)

kimi_home = destination("KIMI_CODE_HOME", next((home / name for name in (".kimi-code", ".kimi")
                                             if (home / name).is_dir()), home / ".kimi-code"))
shared = destination("CODEX_SKILLS_DIR", home / ".agents/skills")
adapters = [
    ("Claude", destination("CLAUDE_SKILLS_DIR", home / ".claude/skills"),
     destination("CLAUDE_WORKFLOW_DOCS_DIR", home / ".claude/workflow-docs")),
    ("Cursor", shared, destination("WORKFLOW_DOCS_DIR", home / ".cursor/workflow-docs")),
    ("Codex", shared, destination("CODEX_WORKFLOW_DOCS_DIR", home / ".codex/workflow-docs")),
    ("Kimi", destination("KIMI_SKILLS_DIR", home / ".agents/skills"),
     destination("KIMI_WORKFLOW_DOCS_DIR", kimi_home / "workflow-docs")),
]
skill_roots, docs_roots = {}, {}
def register(registry, path, label):
    key = os.path.realpath(path)
    registry.setdefault(key, [path, []])[1].append(label)

for label, skills, docs in adapters:
    register(skill_roots, skills, label)
    register(docs_roots, docs, label)
opt_in = destination("CURSOR_SKILLS_DIR", home / ".cursor/skills")
if os.environ.get("CURSOR_SKILLS_DIR") or opt_in.exists():
    register(skill_roots, opt_in, "Cursor opt-in (--cursor-skills)")


def measure_skills(root):
    lines, details = [], []
    try:
        entries = list(root.iterdir())  # A readable directory is a coverage prerequisite.
    except OSError as error:
        return [f"skills not measured ({error})"], [], False, False
    cached, malformed, unreadable, missing, body_drift = {}, [], [], [], []
    extra = []
    for entry in entries:
        if entry.name not in canon:
            try:
                text = (entry / "SKILL.md").read_text(encoding="utf-8")
                frontmatter = text.split("\n---", 1)[0] if text.startswith("---\n") else ""
                if any(line.startswith("  x-wos-profiles:") for line in frontmatter.splitlines()):
                    extra.append(entry.name)
            except (OSError, UnicodeError):
                pass  # Unrelated vendor skills are outside this check's scope.
    for name in sorted(canon):
        path = root / name / "SKILL.md"
        try:
            raw = path.read_bytes()
            cached[str(path)] = raw.decode("utf-8")
            if raw != (repo / ".claude/skills" / name / "SKILL.md").read_bytes():
                body_drift.append(name)
        except FileNotFoundError:
            missing.append(name)
        except (OSError, UnicodeError) as error:
            unreadable.append(name)
            details.append(f"unreadable {name}/SKILL.md: {error}")
    # Reuse the canonical description parser, supplying the already read text.
    # This keeps a broken file from aborting measurements of independent skills.
    original_read = se.read
    try:
        se.read = lambda path: cached.get(str(path), "")
        descriptions, _ = se.skill_descriptions(glob.escape(str(root)))
    finally:
        se.read = original_read
    inst = {}
    for name in sorted(canon):
        if str(root / name / "SKILL.md") not in cached:
            continue
        text = cached[str(root / name / "SKILL.md")]
        if not text.startswith("---\n") or "\n---\n" not in text[4:] or not descriptions.get(name):
            malformed.append(name)
        else:
            inst[name] = descriptions[name]
    differ = sorted(name for name in inst if inst[name] != canon[name])
    delta = sum(len(value) - len(canon[name]) for name, value in inst.items())
    lines.append(f"{len(inst)} Fhorja skill(s), {len(differ)} description(s) differ, "
                 f"{len(body_drift)} body(ies) differ, {len(missing)} not installed, "
                 f"{len(malformed)} malformed, {len(unreadable)} unreadable, "
                 f"{len(extra)} extra workflow-tagged skill(s)")
    complete = len(inst) == len(canon) and not unreadable
    if not inst:
        lines.append("no Fhorja skills measured; inventory not measured")
    elif not complete:
        lines.append(f"partial catalog coverage ({len(inst)}/{len(canon)}); absent names may be profile exclusions")
    if delta:
        lines.append(f"description delta {delta:+d} chars (~{delta / 4:+.0f} estimated tokens; not measured session usage)")
    for label, names in (("not installed", missing), ("malformed", malformed),
                         ("description differs", differ), ("body differs", body_drift), ("extra skills", sorted(extra))):
        if names:
            details.append(f"{label}: {', '.join(names)}")
    return lines, details, complete, bool(differ or body_drift or extra)


def markdown_tree(root):
    paths, errors = set(), []
    if not root.is_dir():
        return paths, ["directory absent or invalid"]
    def onerror(error):
        errors.append(str(error))
    for base, dirs, files in os.walk(root, onerror=onerror):
        for name in list(dirs):
            if (Path(base) / name).is_symlink():
                errors.append(f"directory symlink not traversed: {Path(base) / name}")
                dirs.remove(name)
        for name in files:
            if name.endswith(".md"):
                paths.add((Path(base) / name).relative_to(root).as_posix())
    return paths, errors


canonical_topics, canonical_errors = markdown_tree(repo / "wos")
if not canonical_topics:
    canonical_errors.append("canonical markdown inventory is empty")

def measure_docs(root):
    lines, details, complete, drift = [], [], True, False
    try:
        a = (root / "WORKFLOW_OPERATING_SYSTEM.md").read_bytes()
        b = (repo / "WORKFLOW_OPERATING_SYSTEM.md").read_bytes()
        equal = a == b and bool(b)
        lines.append("spec matches (exact bytes)" if equal else "spec differs")
        drift |= not equal
    except OSError as error:
        lines.append(f"spec not measured ({error})")
        complete = False
    topics, errors = markdown_tree(root / "wos")
    errors = canonical_errors + errors
    changed, unreadable = [], []
    missing, extra = sorted(canonical_topics - topics), sorted(topics - canonical_topics)
    for relative in sorted(canonical_topics & topics):
        try:
            if (repo / "wos" / relative).read_bytes() != (root / "wos" / relative).read_bytes():
                changed.append(relative)
        except OSError as error:
            unreadable.append(relative)
            details.append(f"unreadable {relative}: {error}")
    if errors:
        lines.append("wos not measured completely (" + "; ".join(errors) + ")")
        complete = False
    if missing or extra or changed or unreadable:
        lines.append(f"wos: {len(changed)} changed, {len(missing)} missing, "
                     f"{len(extra)} extra, {len(unreadable)} unreadable markdown path(s)")
    elif not errors:
        lines.append(f"wos: {len(topics)} recursive markdown path(s), content matches (exact bytes)")
    for label, names in (("changed", changed), ("missing", missing), ("extra", extra)):
        if names:
            details.append(f"{label}: {', '.join(names)}")
    complete &= not unreadable and not missing
    drift |= bool(missing or extra or changed)
    return lines, details, complete, drift


rows = []
for kind, roots, measure in (("skills", skill_roots, measure_skills), ("docs", docs_roots, measure_docs)):
    for path, labels in roots.values():
        lines, details, complete, drift = measure(path)
        rows.append((kind, path, labels, lines, details, complete, drift))
complete = all(row[5] for row in rows)
drift = any(row[6] for row in rows)
label = "drift detected" if drift else ("clean" if complete else "partial or not measured")
print(f"Installed-skills-drift: {label} (warn-only; "
      f"{len(skill_roots)} distinct skill root(s), {len(docs_roots)} distinct docs root(s)"
      + ("; coverage partial" if not complete else "") + ")")
for kind, path, labels, lines, details, _, _ in rows:
    print(f"  {', '.join(labels)} {kind}: {path}")
    for line in lines:
        print(f"    {line}")
    if verbose:
        for detail in details:
            print(f"      {detail}")
if drift or not complete:
    print("  Absent roots describe observed coverage, not required adapter installations.")
    print("  Run scripts/sync-workflow-slash-commands.sh for the intended adapters and destinations.")
    if opt_in.exists() or os.environ.get("CURSOR_SKILLS_DIR"):
        print("  Cursor's opt-in skills root is refreshed only with --cursor-skills (ADR-0228).")
PY
