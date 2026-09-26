#!/usr/bin/env python3
"""baseline_audit.py -- read-only structural/graph/history/convention baseline.

Python stdlib only. Writes nothing except the JSON file named by --out (and the
plain-text mismatch summary on stdout).

Facts only. Every check records either its result or the reason it could not
run. No check ranks severity, proposes a fix, or interprets a finding.

Usage:
  python3 scripts/audit/baseline_audit.py --out docs/audit/<date>-baseline.json
  python3 scripts/audit/baseline_audit.py --stdout-json     # JSON to stdout
  python3 scripts/audit/baseline_audit.py --launch-ref <sha> # pin the launch commit

Determinism: every key is byte-stable for an unchanged tree except
meta.run_timestamp. Set SOURCE_DATE_EPOCH to pin that field too.
"""

import argparse
import collections
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import lib_repo as R  # noqa: E402

AUDIT_VERSION = "1.0.0"

BT = "`"

# Paragraph shingling parameters for check 18. Recorded in the JSON so a future
# run can tell a parameter change from a tree change.
SHINGLE_K = 5
SHINGLE_MIN_WORDS = 12
JACCARD_THRESHOLD = 0.8

SKILL_BODY_LINE_LIMIT = 500
DESCRIPTION_CHAR_LIMIT = 1024

# The four registries lint enforces (ADR-0029).
REGISTRY_SPEC = "WORKFLOW_OPERATING_SYSTEM.md"
REGISTRY_ROLES = "wos/command-roles.md"
REGISTRY_STUBS = "COMMAND_PROMPT_STUBS.md"

HARNESS_NAMES = [
    "Claude Code", "Cursor", "Codex", "GitHub Copilot", "Copilot",
    "Windsurf", "Zed", "Aider",
]

# Registry heading pattern. Command names may carry digits (a11y-audit), so the
# character class is wider than the one lint uses for its reverse orphan scan.
NAME_HEADING_RE = r"(?m)^### ([a-z][a-z0-9-]*)$"

MISMATCHES = []


def mismatch(check, expected, actual, location):
    MISMATCHES.append({
        "check": check,
        "expected": str(expected),
        "actual": str(actual),
        "location": location,
    })


def approx_tokens(text):
    """Character count over four. The same heuristic scripts/measure-tokens.py
    uses; it is an approximation, not a tokenizer result."""
    return len(text) // 4


# ==========================================================================
# Inventory shared by many checks
# ==========================================================================


class Inventory(object):
    def __init__(self):
        self.commands = R.command_files()
        self.names = [n for n, _, _ in self.commands]
        self.name_set = set(self.names)
        self.path_by_name = {n: p for n, p, _ in self.commands}
        self.shape_by_name = {n: s for n, _, s in self.commands}
        self.meta = {}
        for name, path, _ in self.commands:
            self.meta[name] = R.command_meta(path)
        self.spec_clusters = self._spec_clusters()
        self.cluster_of = {}
        for cluster, members in self.spec_clusters.items():
            for m in members:
                self.cluster_of.setdefault(m, cluster)

    def _spec_clusters(self):
        """### <Cluster> subsections of '## Command categories' in the spec."""
        path = os.path.join(R.ROOT, REGISTRY_SPEC)
        lines = R.read_lines(path)
        clusters = collections.OrderedDict()
        in_section = False
        current = None
        for line in lines:
            if line.startswith("## "):
                in_section = line.strip() == "## Command categories"
                current = None
                continue
            if not in_section:
                continue
            if line.startswith("### "):
                current = line[4:].strip()
                clusters.setdefault(current, [])
                continue
            m = re.fullmatch(r"- " + BT + r"([a-z][a-z0-9-]*)" + BT, line.strip())
            if m and current:
                clusters[current].append(m.group(1))
        return clusters

    def cluster(self, name):
        return self.cluster_of.get(name, "(no cluster)")


# ==========================================================================
# 1. Counts
# ==========================================================================


def check_counts(inv):
    files_on_disk = len(inv.commands)
    skills = R.built_skills()

    spec_text = R.read_text(os.path.join(R.ROOT, REGISTRY_SPEC)) or ""
    roles_text = R.read_text(os.path.join(R.ROOT, REGISTRY_ROLES)) or ""
    stubs_text = R.read_text(os.path.join(R.ROOT, REGISTRY_STUBS)) or ""

    spec_cluster_entries = sorted({c for members in inv.spec_clusters.values()
                                   for c in members})
    roles_entries = sorted(set(re.findall(NAME_HEADING_RE, roles_text)))
    stubs_entries = sorted(set(re.findall(
        r"(?m)^\| " + BT + r"([a-z][a-z0-9-]*)" + BT + r" \|", stubs_text)))

    catalog_path = os.path.join(R.ROOT, "docs", "command-catalog.json")
    catalog_count = None
    catalog_note = None
    if os.path.isfile(catalog_path):
        try:
            catalog = json.loads(R.read_text(catalog_path))
            catalog_count = len(catalog.get("commands", []))
        except (ValueError, TypeError):
            catalog_note = "docs/command-catalog.json is not parseable JSON"
    else:
        catalog_note = "docs/command-catalog.json absent"

    # README carries no one-row-per-command index. It carries an editorial
    # cluster table plus count markers. Both are reported; neither is silently
    # substituted for the other.
    readme_lines = R.read_lines(os.path.join(R.ROOT, "README.md"))
    readme_cluster_rows = 0
    in_cluster_table = False
    for line in readme_lines:
        if line.startswith("| Cluster | "):
            in_cluster_table = True
            continue
        if in_cluster_table:
            if line.startswith("|---") or line.startswith("|--"):
                continue
            if line.startswith("|"):
                readme_cluster_rows += 1
            else:
                in_cluster_table = False

    sources = [
        {"source": "commands/ on disk (flat + folder-shaped)",
         "value": files_on_disk, "location": "commands/"},
        {"source": ".claude/skills/<name>/SKILL.md built",
         "value": len(skills), "location": ".claude/skills/"},
        {"source": "registry: spec cluster bullets",
         "value": len(spec_cluster_entries),
         "location": REGISTRY_SPEC + " ## Command categories"},
        {"source": "registry: wos/command-roles.md",
         "value": len(roles_entries), "location": REGISTRY_ROLES},
        {"source": "registry: COMMAND_PROMPT_STUBS.md table rows",
         "value": len(stubs_entries), "location": REGISTRY_STUBS},
        {"source": "docs/command-catalog.json commands[]",
         "value": catalog_count, "location": "docs/command-catalog.json"},
        {"source": "README.md editorial cluster table rows",
         "value": readme_cluster_rows, "location": "README.md ## Command clusters",
         "note": ("this is a cluster table, not a per-command index; "
                  "README.md carries no one-row-per-command index")},
    ]

    for s in sources:
        if s["value"] is None:
            continue
        if s["source"].startswith("README.md"):
            continue
        if s["value"] != files_on_disk:
            mismatch("01-counts", files_on_disk, s["value"], s["location"])

    markers, marker_exclusions = _count_markers(inv)
    for m in markers:
        if m["compared"] and m["declared"] != m["disk"]:
            mismatch("01-counts (count marker)", m["disk"], m["declared"],
                     "%s:%d count:%s" % (m["file"], m["line"], m["kind"]))

    return {
        "status": "ok",
        "command_count_sources": sources,
        "count_markers": markers,
        "count_markers_compared": sum(1 for m in markers if m["compared"]),
        "count_markers_out_of_scan_set": sum(1 for m in markers if not m["compared"]),
        "count_marker_walk_exclusions": marker_exclusions,
        "notes": [n for n in [catalog_note] if n],
    }


def _count_markers(inv):
    """Every count marker in the tree. Markers inside the lint scan-set are
    compared against disk; markers outside it are listed uncompared, because
    frozen snapshots pin them to a past count on purpose."""
    scan_set = {os.path.abspath(p) for p in R.count_scan_files()}
    excluded_roots = {
        # gitignored task memory: private project content, out of scope for a
        # repository-structure audit and a leak risk in a written report.
        "projects": "gitignored task memory, excluded from this walk",
        # this audit's own output, so a re-run does not read its own report.
        "docs/audit": "the audit's own output directory",
        ".git": "git internals",
        "node_modules": "vendored dependencies",
        "__pycache__": "bytecode cache",
    }
    seen = []
    disk_cache = {}
    for dirpath, dirnames, filenames in os.walk(R.ROOT):
        here = R.rel(dirpath)
        dirnames[:] = sorted(
            d for d in dirnames
            if ((d if here == "." else here + "/" + d) not in excluded_roots
                and d not in (".git", "node_modules", "__pycache__")))
        for fn in sorted(filenames):
            if not fn.endswith((".md", ".html", ".json", ".txt")):
                continue
            full = os.path.join(dirpath, fn)
            text = R.read_text(full)
            if not text or "<!-- count:" not in text:
                continue
            for i, line in enumerate(text.splitlines(), start=1):
                for m in R.COUNT_MARKER_RE.finditer(line):
                    kind, declared = m.group(1), int(m.group(2))
                    if kind not in disk_cache:
                        disk_cache[kind] = R.disk_count(kind)
                    compared = os.path.abspath(full) in scan_set and \
                        disk_cache[kind] is not None
                    seen.append({
                        "file": R.rel(full),
                        "line": i,
                        "kind": kind,
                        "declared": declared,
                        "disk": disk_cache[kind],
                        "compared": compared,
                        "reason": None if compared else (
                            "kind has no on-disk formula"
                            if disk_cache[kind] is None
                            else "outside the lint count scan-set "
                                 "(frozen snapshot or generated view)"),
                    })
    return (sorted(seen, key=lambda r: (r["file"], r["line"], r["kind"])),
            [{"path": k, "reason": v} for k, v in sorted(excluded_roots.items())])


# ==========================================================================
# 2. Registry integrity
# ==========================================================================


def check_registry(inv):
    spec_text = R.read_text(os.path.join(R.ROOT, REGISTRY_SPEC)) or ""
    roles_text = R.read_text(os.path.join(R.ROOT, REGISTRY_ROLES)) or ""
    stubs_text = R.read_text(os.path.join(R.ROOT, REGISTRY_STUBS)) or ""

    registries = {
        "spec-cluster-list": sorted({c for members in inv.spec_clusters.values()
                                     for c in members}),
        "wos/command-roles.md": sorted(set(re.findall(NAME_HEADING_RE, roles_text))),
        "COMMAND_PROMPT_STUBS.md": sorted(set(re.findall(
            r"(?m)^\| " + BT + r"([a-z][a-z0-9-]*)" + BT + r" \|", stubs_text))),
    }

    on_disk_missing = []
    for name in inv.names:
        missing = [reg for reg, entries in registries.items() if name not in entries]
        if missing:
            on_disk_missing.append({"command": name, "missing_from": sorted(missing)})
            for reg in sorted(missing):
                mismatch("02-registry", "present in " + reg, "absent", "commands/" + name)

    orphans = []
    for reg, entries in registries.items():
        for entry in entries:
            if entry not in inv.name_set:
                orphans.append({"registry": reg, "entry": entry})
                mismatch("02-registry", "a command file for " + entry,
                         "no commands/" + entry + ".md and no commands/" + entry + "/SKILL.md",
                         reg)

    commands_in_no_cluster = sorted(n for n in inv.names if n not in inv.cluster_of)
    for n in commands_in_no_cluster:
        mismatch("02-registry", "membership in one spec cluster", "no cluster",
                 "commands/" + n)

    empty_clusters = sorted(c for c, members in inv.spec_clusters.items() if not members)
    for c in empty_clusters:
        mismatch("02-registry", "at least one member", "zero members",
                 REGISTRY_SPEC + " ### " + c)

    # Frontmatter metadata.category and the spec cluster headings are two
    # different taxonomies with a partial name overlap. The cross-tab is
    # reported; a per-command disagreement is only flagged where the command's
    # spec cluster slug exists as a frontmatter category value somewhere.
    def slug(s):
        return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")

    category_values = {inv.meta[n]["category"] for n in inv.names} - {None}
    cluster_slugs = {slug(c) for c in inv.spec_clusters}
    overlapping = cluster_slugs & category_values

    category_disagreements = []
    for name in inv.names:
        cat = inv.meta[name]["category"]
        cluster = inv.cluster_of.get(name)
        if cat is None or cluster is None:
            continue
        cslug = slug(cluster)
        if cslug in overlapping and cat != cslug:
            category_disagreements.append({
                "command": name,
                "frontmatter_category": cat,
                "spec_cluster": cluster,
            })
            mismatch("02-registry", "frontmatter category " + cslug,
                     cat, "commands/" + name)

    cross_tab = collections.Counter()
    for name in inv.names:
        cross_tab[(inv.cluster(name), inv.meta[name]["category"] or "(none)")] += 1

    return {
        "status": "ok",
        "registries": {k: len(v) for k, v in registries.items()},
        "commands_missing_from_a_registry": on_disk_missing,
        "orphan_registry_entries": sorted(orphans, key=lambda r: (r["registry"], r["entry"])),
        "commands_in_no_cluster": commands_in_no_cluster,
        "clusters_with_no_members": empty_clusters,
        "cluster_membership_counts": [
            {"cluster": c, "members": len(m)} for c, m in inv.spec_clusters.items()],
        "taxonomy_note": (
            "the spec '## Command categories' headings and the frontmatter "
            "metadata.category values are two taxonomies that overlap by name but "
            "are not the same set. Only clusters whose slug also exists as a "
            "category value are compared per command."),
        "spec_clusters_with_no_matching_category_value": sorted(cluster_slugs - category_values),
        "category_values_with_no_matching_spec_cluster": sorted(category_values - cluster_slugs),
        "spec_cluster_by_frontmatter_category": [
            {"spec_cluster": a, "frontmatter_category": b, "commands": n}
            for (a, b), n in sorted(cross_tab.items())],
        "frontmatter_category_vs_spec_cluster_disagreements": category_disagreements,
    }


# ==========================================================================
# 3. Shared block drift
# ==========================================================================

SHARED_MARKER_RE = re.compile(r"^<!-- shared:([a-z-]+) -->\s*$")
SHARED_END_OVERRIDE = {"mandatory-context-bootstrap": re.compile(r"^Required inputs:$")}
SHARED_END_DEFAULT = re.compile(r"^### ")


def shared_regions(lines):
    """Yield (name, marker_lineno_1based, first_content_idx, end_idx_exclusive).

    Mirrors the region rule in scripts/sync-shared-blocks.sh: the block runs from
    the line after the marker up to (not including) the first line matching the
    end pattern for that block.
    """
    out = []
    for i, line in enumerate(lines):
        m = SHARED_MARKER_RE.match(line)
        if not m:
            continue
        name = m.group(1)
        end_re = SHARED_END_OVERRIDE.get(name, SHARED_END_DEFAULT)
        j = i + 1
        while j < len(lines) and not end_re.match(lines[j]):
            j += 1
        out.append((name, i + 1, i + 1, j))
    return out


def check_shared_blocks(inv):
    canonical = R.shared_block_files()
    canon_text = {name: (R.read_text(path) or "") for name, path in canonical.items()}

    drifted = []
    unknown_marker = []
    marker_total = 0
    usage = collections.Counter()

    targets = list(inv.commands) + [
        (name, path, "shared") for name, path in sorted(canonical.items())]

    for name, path, _shape in targets:
        lines = R.read_lines(path)
        for block, marker_line, start, end in shared_regions(lines):
            marker_total += 1
            usage[block] += 1
            if block not in canon_text:
                unknown_marker.append({
                    "file": R.rel(path), "line": marker_line, "block": block})
                mismatch("03-shared-blocks", "commands/_shared/" + block + ".md",
                         "no such shared block", R.rel(path) + ":" + str(marker_line))
                continue
            observed = "\n".join(lines[start:end])
            expected = canon_text[block].rstrip("\n")
            if observed.rstrip("\n") != expected:
                drifted.append({
                    "file": R.rel(path),
                    "line": marker_line,
                    "block": block,
                    "observed_chars": len(observed),
                    "canonical_chars": len(expected),
                })
                mismatch("03-shared-blocks",
                         "copy identical to commands/_shared/" + block + ".md",
                         "copy differs", R.rel(path) + ":" + str(marker_line))

    unused = sorted(b for b in canon_text if usage.get(b, 0) == 0)

    return {
        "status": "ok",
        "method": ("region rule replicated from scripts/sync-shared-blocks.sh; "
                   "cross-checked against that script's --dry-run in "
                   "scripts/audit/run-baseline.sh"),
        "markers_total": marker_total,
        "blocks_on_disk": len(canon_text),
        "usage_per_block": [{"block": b, "markers": usage.get(b, 0)}
                            for b in sorted(canon_text)],
        "shared_blocks_with_no_consumer": unused,
        "files_with_drifted_copy": drifted,
        "files_referencing_a_missing_block": unknown_marker,
    }


# ==========================================================================
# 4. Cross-reference integrity
# ==========================================================================

# The leading boundary matters: `.wos/VERIFICATION_LOG.jsonl` is a path inside a
# consumer project, not `wos/` in this repository.
PATH_REF_RE = re.compile(
    r"(?<![A-Za-z0-9._/-])(?:@)?"
    r"((?:commands|wos|scripts|templates|docs|evals|recommended-mcp-configs)"
    r"/[A-Za-z0-9._/-]+\.[A-Za-z0-9]+)")


def check_cross_references(inv):
    broken = []
    outside_tree = []
    resolved = 0
    per_target = collections.Counter()

    scan = list(inv.commands) + [
        (n, p, "shared") for n, p in sorted(R.shared_block_files().items())]

    for name, path, _shape in scan:
        for i, line in enumerate(R.read_lines(path), start=1):
            for m in PATH_REF_RE.finditer(line):
                ref = m.group(1)
                if any(ch in ref for ch in "<>*"):
                    continue
                target = os.path.join(R.ROOT, ref)
                if os.path.exists(target):
                    resolved += 1
                    per_target[ref] += 1
                    continue
                parent = os.path.dirname(os.path.join(R.ROOT, ref))
                if os.path.isdir(parent):
                    broken.append({"file": R.rel(path), "line": i, "ref": ref})
                    mismatch("04-cross-references", "a file at " + ref,
                             "missing", R.rel(path) + ":" + str(i))
                else:
                    outside_tree.append({"file": R.rel(path), "line": i, "ref": ref})

    # Command-to-command references by name, target existence by construction.
    # Reported for completeness: a name-shaped reference that resolves to no file.
    name_like = re.compile(BT + r"([a-z][a-z0-9]+(?:-[a-z0-9]+)+)" + BT)
    known_non_commands = set()
    for d in ("wos", "templates", "scripts"):
        base = os.path.join(R.ROOT, d)
        if os.path.isdir(base):
            for f in os.listdir(base):
                known_non_commands.add(os.path.splitext(f)[0])

    # Templates referenced by no command.
    templates_dir = os.path.join(R.ROOT, "templates")
    template_files = []
    for dirpath, dirnames, filenames in os.walk(templates_dir):
        dirnames[:] = sorted(dirnames)
        for fn in sorted(filenames):
            template_files.append(R.rel(os.path.join(dirpath, fn)))

    command_corpus = "\n".join(
        (R.read_text(p) or "") for _, p, _ in scan)
    unreferenced_templates = []
    for t in sorted(template_files):
        base = os.path.basename(t)
        if t in command_corpus or base in command_corpus:
            continue
        unreferenced_templates.append(t)

    # Same question for scripts/ and wos/, reported separately and not merged.
    def unreferenced(directory, suffixes):
        out = []
        base_dir = os.path.join(R.ROOT, directory)
        if not os.path.isdir(base_dir):
            return out
        for fn in sorted(os.listdir(base_dir)):
            if not fn.endswith(suffixes):
                continue
            path_ref = directory + "/" + fn
            if path_ref in command_corpus or fn in command_corpus:
                continue
            out.append(path_ref)
        return out

    outside_by_prefix = collections.Counter()
    for r in outside_tree:
        outside_by_prefix["/".join(r["ref"].split("/")[:2])] += 1

    return {
        "status": "ok",
        "classification_rule": (
            "a path-shaped reference is resolved when the file exists here. When "
            "it does not, it is called broken only if its parent directory exists "
            "in this repository; otherwise it is recorded as pointing outside the "
            "tree, which is what a path in a consumer project looks like."),
        "path_references_resolved": resolved,
        "path_references_broken": sorted(broken, key=lambda r: (r["file"], r["line"])),
        "path_references_outside_the_tree": sorted(
            outside_tree, key=lambda r: (r["file"], r["line"])),
        "path_references_outside_the_tree_by_prefix": [
            {"prefix": p, "references": c} for p, c in
            sorted(outside_by_prefix.items(), key=lambda kv: (-kv[1], kv[0]))],
        "most_referenced_targets": [
            {"target": t, "references": c} for t, c in
            sorted(per_target.items(), key=lambda kv: (-kv[1], kv[0]))[:20]],
        "templates_referenced_by_no_command": unreferenced_templates,
        "template_files_total": len(template_files),
        "wos_topics_referenced_by_no_command": unreferenced("wos", (".md",)),
        "scripts_referenced_by_no_command": unreferenced("scripts", (".sh", ".py")),
    }


# ==========================================================================
# 5. ADR coverage
# ==========================================================================


def check_adrs(inv):
    adr_dir = os.path.join(R.ROOT, "docs", "adr")
    index_path = os.path.join(adr_dir, "README.md")
    if not os.path.isdir(adr_dir):
        return {"status": "could_not_run", "reason": "docs/adr/ does not exist"}

    files = sorted(f for f in os.listdir(adr_dir)
                   if f.endswith(".md") and re.match(r"^\d{4}-", f))
    file_numbers = {}
    duplicates = []
    for f in files:
        num = f[:4]
        if num in file_numbers:
            duplicates.append({"number": num, "files": [file_numbers[num], f]})
            mismatch("05-adr", "one file per ADR number",
                     "two files: " + file_numbers[num] + " and " + f,
                     "docs/adr/")
        file_numbers[num] = f

    index_rows = {}
    index_status = {}
    if os.path.isfile(index_path):
        for line in R.read_lines(index_path):
            m = re.match(r"^\| \[(\d{4})\]\((\./[^)]+)\) \| (.*?) \| (.*?) \|", line)
            if m:
                num, link, title, status = m.groups()
                index_rows[num] = {"link": link, "title": title.strip(),
                                   "status": status.strip()}
                index_status[num] = status.strip()
    else:
        return {"status": "could_not_run", "reason": "docs/adr/README.md is absent"}

    missing_rows = sorted(n for n in file_numbers if n not in index_rows)
    for n in missing_rows:
        mismatch("05-adr", "an index row", "no row",
                 "docs/adr/README.md for ADR " + n)
    rows_without_file = sorted(n for n in index_rows if n not in file_numbers)
    for n in rows_without_file:
        mismatch("05-adr", "a file docs/adr/" + n + "-*.md", "no file",
                 "docs/adr/README.md row " + n)

    nums = sorted(int(n) for n in file_numbers)
    gaps = []
    if nums:
        present = set(nums)
        for i in range(min(nums), max(nums) + 1):
            if i not in present:
                gaps.append("%04d" % i)

    superseded = sorted(n for n, s in index_status.items()
                        if "superseded" in s.lower())

    # Superseded ADRs still cited from a command file.
    cited = collections.defaultdict(list)
    adr_ref_re = re.compile(r"ADR-(\d{4})")
    for name, path, _shape in inv.commands:
        for i, line in enumerate(R.read_lines(path), start=1):
            for m in adr_ref_re.finditer(line):
                cited[m.group(1)].append({"command": name, "line": i})

    superseded_still_cited = []
    for num in superseded:
        if num in cited:
            superseded_still_cited.append({
                "adr": num,
                "status": index_status[num],
                "citations": sorted(
                    {c["command"] for c in cited[num]}),
            })

    cited_missing = sorted(n for n in cited if n not in file_numbers)
    for n in cited_missing:
        mismatch("05-adr", "docs/adr/" + n + "-*.md", "cited but no file",
                 "commands/ (" + ", ".join(sorted({c["command"] for c in cited[n]})) + ")")

    return {
        "status": "ok",
        "adr_files": len(file_numbers),
        "index_rows": len(index_rows),
        "highest_number": "%04d" % max(nums) if nums else None,
        "numbering_gaps": gaps,
        "duplicate_numbers": duplicates,
        "files_missing_an_index_row": missing_rows,
        "index_rows_without_a_file": rows_without_file,
        "superseded_adrs": [{"adr": n, "status": index_status[n]} for n in superseded],
        "superseded_adrs_still_cited_by_a_command": superseded_still_cited,
        "adrs_cited_by_a_command_with_no_file": cited_missing,
        "citation_counts": [
            {"adr": n, "commands": len({c["command"] for c in v})}
            for n, v in sorted(cited.items(), key=lambda kv: (-len(
                {c["command"] for c in kv[1]}), kv[0]))[:20]],
    }


# ==========================================================================
# 6. Eval coverage
# ==========================================================================


def check_eval_coverage(inv):
    scen_dir = os.path.join(R.ROOT, "evals", "scenarios")
    if not os.path.isdir(scen_dir):
        return {"status": "could_not_run", "reason": "evals/scenarios/ does not exist"}

    scenarios = sorted(f for f in os.listdir(scen_dir)
                       if f.endswith(".md") and f[:1].isdigit())

    tagged = collections.defaultdict(set)
    mentioned = collections.defaultdict(set)
    for f in scenarios:
        text = R.read_text(os.path.join(scen_dir, f)) or ""
        m = re.search(r"(?m)^- \*\*Tags\*\*:\s*(.+)$", text)
        if m:
            for tag in m.group(1).split(","):
                tag = tag.strip().strip(BT)
                if tag in inv.name_set:
                    tagged[tag].add(f)
        for name in inv.names:
            if re.search(r"(?<![a-z0-9-])" + re.escape(name) + r"(?![a-z0-9-])", text):
                mentioned[name].add(f)

    per_command = []
    for name in inv.names:
        per_command.append({
            "command": name,
            "cluster": inv.cluster(name),
            "tagged_scenarios": sorted(tagged.get(name, ())),
            "mentioned_scenarios": sorted(mentioned.get(name, ())),
            "tagged_count": len(tagged.get(name, ())),
            "mentioned_count": len(mentioned.get(name, ())),
            "has_tagged_coverage": bool(tagged.get(name)),
            "has_any_coverage": bool(mentioned.get(name)),
        })

    per_cluster = []
    clusters = collections.defaultdict(list)
    for row in per_command:
        clusters[row["cluster"]].append(row)
    for cluster in sorted(clusters):
        rows = clusters[cluster]
        tag_cov = sum(1 for r in rows if r["has_tagged_coverage"])
        any_cov = sum(1 for r in rows if r["has_any_coverage"])
        per_cluster.append({
            "cluster": cluster,
            "commands": len(rows),
            "tagged_covered": tag_cov,
            "tagged_percent": round(100.0 * tag_cov / len(rows), 1),
            "mentioned_covered": any_cov,
            "mentioned_percent": round(100.0 * any_cov / len(rows), 1),
        })

    zero_tag_clusters = [c["cluster"] for c in per_cluster if c["tagged_covered"] == 0]
    zero_any_clusters = [c["cluster"] for c in per_cluster if c["mentioned_covered"] == 0]

    # Coverage is reported, not flagged: a command with no scenario is a
    # coverage fact, not a disagreement between two surfaces.
    uncovered = [r["command"] for r in per_command if not r["has_any_coverage"]]

    return {
        "status": "ok",
        "scenarios_total": len(scenarios),
        "method": ("two independent signals: the scenario '**Tags**:' line "
                   "(explicit) and a whole-file word-boundary mention (loose). "
                   "Both are reported; neither is treated as the other."),
        "per_command": per_command,
        "per_cluster": per_cluster,
        "clusters_with_zero_tagged_coverage": zero_tag_clusters,
        "clusters_with_zero_mention_coverage": zero_any_clusters,
        "commands_with_zero_coverage": uncovered,
        "totals": {
            "tagged_covered": sum(1 for r in per_command if r["has_tagged_coverage"]),
            "mentioned_covered": sum(1 for r in per_command if r["has_any_coverage"]),
            "commands": len(per_command),
        },
    }


# ==========================================================================
# 7. Skills spec conformance
# ==========================================================================


def check_skills(inv):
    skills = R.built_skills()
    if not skills:
        return {"status": "could_not_run", "reason": ".claude/skills/ holds no SKILL.md"}

    required = ["name", "description"]
    rows = []
    for name, path in skills:
        text = R.read_text(path) or ""
        fm_lines, body_lines, _ = R.split_frontmatter(text)
        fm = R.parse_frontmatter(fm_lines)
        missing = [f for f in required if not fm.get(f)]
        desc = fm.get("description") or ""
        body_count = len(body_lines)
        row = {
            "skill": name,
            "frontmatter_keys": sorted(fm.keys()),
            "missing_required_fields": missing,
            "description_chars": len(desc),
            "description_over_limit": len(desc) > DESCRIPTION_CHAR_LIMIT,
            "body_lines": body_count,
            "body_over_limit": body_count > SKILL_BODY_LINE_LIMIT,
            "name_matches_directory": fm.get("name") == name,
            "has_canonical_command": name in inv.name_set,
        }
        rows.append(row)
        for f in missing:
            mismatch("07-skills", "frontmatter field " + f, "absent",
                     ".claude/skills/" + name + "/SKILL.md")
        if row["description_over_limit"]:
            mismatch("07-skills", "description <= %d chars" % DESCRIPTION_CHAR_LIMIT,
                     "%d chars" % len(desc), ".claude/skills/" + name + "/SKILL.md")
        if row["body_over_limit"]:
            mismatch("07-skills", "body <= %d lines" % SKILL_BODY_LINE_LIMIT,
                     "%d lines" % body_count, ".claude/skills/" + name + "/SKILL.md")
        if not row["name_matches_directory"]:
            mismatch("07-skills", "name: " + name, str(fm.get("name")),
                     ".claude/skills/" + name + "/SKILL.md")
        if not row["has_canonical_command"]:
            mismatch("07-skills", "a canonical commands/ source", "none",
                     ".claude/skills/" + name + "/SKILL.md")

    missing_skill = sorted(n for n in inv.names
                           if n not in {s for s, _ in skills})
    for n in missing_skill:
        mismatch("07-skills", ".claude/skills/" + n + "/SKILL.md", "not built",
                 "commands/" + n)

    return {
        "status": "ok",
        "limits": {"body_lines": SKILL_BODY_LINE_LIMIT,
                   "description_chars": DESCRIPTION_CHAR_LIMIT},
        "skills_total": len(rows),
        "per_skill": sorted(rows, key=lambda r: r["skill"]),
        "commands_without_a_built_skill": missing_skill,
        "over_body_limit": [r["skill"] for r in rows if r["body_over_limit"]],
        "over_description_limit": [r["skill"] for r in rows if r["description_over_limit"]],
        "missing_a_required_field": [r["skill"] for r in rows
                                     if r["missing_required_fields"]],
    }


# ==========================================================================
# 8. Token footprint
# ==========================================================================


def check_tokens(inv):
    rows = []
    for name, path, shape in inv.commands:
        text = R.read_text(path) or ""
        meta = inv.meta[name]
        rows.append({
            "command": name,
            "shape": shape,
            "cluster": inv.cluster(name),
            "chars": len(text),
            "approx_tokens": approx_tokens(text),
            "profiles": sorted(meta["profiles"]),
        })

    by_size = sorted(rows, key=lambda r: (-r["approx_tokens"], r["command"]))

    profile_totals = {}
    for profile in ("minimal", "core", "full"):
        member_rows = [r for r in rows if profile in r["profiles"]]
        profile_totals[profile] = {
            "commands": len(member_rows),
            "approx_tokens": sum(r["approx_tokens"] for r in member_rows),
            "chars": sum(r["chars"] for r in member_rows),
        }

    budget = _context_budget_statements()

    return {
        "status": "ok",
        "method": "approximate tokens = file characters // 4 (not a tokenizer result)",
        "per_command": sorted(rows, key=lambda r: r["command"]),
        "ten_largest": by_size[:10],
        "profile_totals": profile_totals,
        "budget_source": "wos/context-budget.md",
        "per_profile_budget_stated": budget["per_profile_budget_stated"],
        "budget_statement_note": budget["note"],
        "numeric_budget_statements_found": budget["statements"],
    }


def _context_budget_statements():
    path = os.path.join(R.ROOT, "wos", "context-budget.md")
    if not os.path.isfile(path):
        return {"per_profile_budget_stated": False,
                "note": "wos/context-budget.md is absent",
                "statements": []}
    statements = []
    for i, line in enumerate(R.read_lines(path), start=1):
        if re.search(r"\d[\d,]*\s*(tokens|token)", line, re.I):
            statements.append({"line": i, "text": line.strip()[:400]})
    per_profile = any(
        re.search(r"(minimal|core|full)", s["text"], re.I) and
        re.search(r"budget", s["text"], re.I)
        for s in statements)
    note = ("wos/context-budget.md states per-phase TASK_STATE.md context-rot "
            "thresholds and a measured bootstrap figure. It states no token "
            "budget for the minimal, core, or full install profiles, so the "
            "per-profile totals above are reported against no stated budget.")
    return {"per_profile_budget_stated": per_profile, "note": note,
            "statements": statements}


# ==========================================================================
# 9. Claim consistency
# ==========================================================================


def check_claims(inv):
    surfaces = ["README.md", "docs/FAQ.md", "docs/command-catalog.html",
                "docs/MIGRATION.md"]
    present = [s for s in surfaces if os.path.isfile(os.path.join(R.ROOT, s))]
    absent = [s for s in surfaces if s not in present]

    on_disk = {
        "commands": len(inv.commands),
        "spec_clusters": len(inv.spec_clusters),
        "frontmatter_categories": len({inv.meta[n]["category"] for n in inv.names} - {None}),
        "readme_editorial_clusters": None,
    }

    claims = []

    # Unprotected prose claims only. Any number wrapped in a count marker is
    # compared against disk by check 01 and is blanked out below.
    bare_count_re = re.compile(r"(?<![\d.])(\d{1,4})\s+commands\b")
    cluster_claim_re = re.compile(r"(\d{1,3})\s+clusters\b")
    category_claim_re = re.compile(r"(\d{1,3})[- ]categor")

    for surface in present:
        path = os.path.join(R.ROOT, surface)
        for i, line in enumerate(R.read_lines(path), start=1):
            # Numbers already wrapped in a count marker are check 01's job.
            # Blank them out here so this check only sees unprotected prose.
            stripped = R.COUNT_MARKER_RE.sub(lambda m: " " * len(m.group(0)), line)
            for m in bare_count_re.finditer(stripped):
                claimed = int(m.group(1))
                claims.append(_claim("command count", surface, i, claimed,
                                     on_disk["commands"], line.strip()[:300]))
            for m in cluster_claim_re.finditer(stripped):
                claimed = int(m.group(1))
                readme_clusters = _readme_cluster_rows()
                claims.append(_claim("cluster count", surface, i, claimed,
                                     readme_clusters, line.strip()[:300],
                                     basis="README.md editorial cluster table rows"))
            for m in category_claim_re.finditer(stripped):
                claimed = int(m.group(1))
                claims.append(_claim("category count", surface, i, claimed,
                                     on_disk["frontmatter_categories"],
                                     line.strip()[:300],
                                     basis="distinct frontmatter metadata.category values"))

    # License.
    license_path = os.path.join(R.ROOT, "LICENSE")
    license_declared = None
    if os.path.isfile(license_path):
        first = (R.read_lines(license_path) or [""])[0].strip()
        license_declared = first
    license_rows = [{
        "source": "LICENSE",
        "value": license_declared,
        "note": "first line of the file",
    }]
    for surface in ["README.md", "docs/FAQ.md"]:
        if surface not in present:
            continue
        text = R.read_text(os.path.join(R.ROOT, surface)) or ""
        found = sorted(set(re.findall(
            r"\b(MIT|AGPL-3\.0|AGPL|Apache-2\.0|GPL-3\.0|BSD-3-Clause)\b", text)))
        license_rows.append({"source": surface, "value": ", ".join(found) or None,
                             "note": "license identifiers mentioned anywhere in the file"})
    pkg = os.path.join(R.ROOT, "package.json")
    if os.path.isfile(pkg):
        try:
            data = json.loads(R.read_text(pkg))
            license_rows.append({"source": "package.json", "value": data.get("license"),
                                 "note": "license field"})
        except ValueError:
            license_rows.append({"source": "package.json", "value": None,
                                 "note": "file is not parseable JSON"})
    else:
        license_rows.append({"source": "package.json", "value": None,
                             "note": "no package.json in the tree; nothing to compare"})

    license_mismatches = []
    canonical_license = "MIT" if license_declared and "MIT" in license_declared else None
    for row in license_rows:
        if row["source"] == "LICENSE" or row["value"] is None:
            continue
        if canonical_license and canonical_license not in str(row["value"]):
            license_mismatches.append(row)
            mismatch("09-claims (license)", canonical_license, row["value"], row["source"])

    # Harnesses.
    harness_rows = []
    for surface in present:
        text = R.read_text(os.path.join(R.ROOT, surface)) or ""
        found = {}
        for h in HARNESS_NAMES:
            c = len(re.findall(r"(?<![A-Za-z])" + re.escape(h) + r"(?![A-Za-z])", text))
            if c:
                found[h] = c
        harness_rows.append({"surface": surface, "harnesses_named": found})

    harness_evidence = {
        ".claude/skills/": os.path.isdir(os.path.join(R.ROOT, ".claude", "skills")),
        "scripts/sync-workflow-slash-commands.sh": os.path.isfile(
            os.path.join(R.ROOT, "scripts", "sync-workflow-slash-commands.sh")),
        "wos/editor-mode-mappings.md": os.path.isfile(
            os.path.join(R.ROOT, "wos", "editor-mode-mappings.md")),
    }

    for c in claims:
        if not c["matches"] and c["on_disk"] is not None:
            mismatch("09-claims (" + c["kind"] + ")", c["on_disk"], c["claimed"],
                     c["surface"] + ":" + str(c["line"]))

    return {
        "status": "ok",
        "surfaces_scanned": present,
        "surfaces_absent": absent,
        "on_disk_reference_values": {
            "commands": on_disk["commands"],
            "spec_clusters": on_disk["spec_clusters"],
            "frontmatter_categories": on_disk["frontmatter_categories"],
            "readme_editorial_cluster_rows": _readme_cluster_rows(),
        },
        "numeric_claims": claims,
        "numeric_claims_matching": sum(1 for c in claims if c["matches"]),
        "numeric_claims_mismatching": sum(1 for c in claims if not c["matches"]),
        "license_declarations": license_rows,
        "license_mismatches": license_mismatches,
        "harness_names_per_surface": harness_rows,
        "harness_on_disk_evidence": harness_evidence,
        "harness_note": ("harness support is a claim about external tools; this "
                         "check reports which names each surface uses and which "
                         "in-repo integration files exist. Whether a named harness "
                         "actually works cannot be determined by inspecting this tree."),
    }


_README_CLUSTER_ROWS = [None]


def _readme_cluster_rows():
    if _README_CLUSTER_ROWS[0] is not None:
        return _README_CLUSTER_ROWS[0]
    rows = 0
    in_table = False
    for line in R.read_lines(os.path.join(R.ROOT, "README.md")):
        if line.startswith("| Cluster | "):
            in_table = True
            continue
        if in_table:
            if line.startswith("|--"):
                continue
            if line.startswith("|"):
                rows += 1
            else:
                in_table = False
    _README_CLUSTER_ROWS[0] = rows
    return rows


def _claim(kind, surface, line_no, claimed, on_disk, text, basis=None):
    return {
        "kind": kind,
        "surface": surface,
        "line": line_no,
        "claimed": claimed,
        "on_disk": on_disk,
        "matches": on_disk is not None and claimed == on_disk,
        "basis": basis or "on-disk count",
        "text": text,
    }


# ==========================================================================
# 10. Staleness  and  14. Churn  (one git pass, two checks)
# ==========================================================================


def git_history(inv, launch_ref):
    """One numstat pass over commands/. Returns per-path stats and commit sets."""
    if not R.git_available():
        return None

    def parse(range_args):
        out = R.git("log", "-M", "--numstat", "--format=%x01%H%x01%cI",
                    *range_args, "--", "commands/")
        if out is None:
            return None
        commits = []
        current = None
        for line in out.splitlines():
            if line.startswith("\x01"):
                parts = line.split("\x01")
                current = {"sha": parts[1], "date": parts[2], "files": {}}
                commits.append(current)
                continue
            if not line.strip() or current is None:
                continue
            bits = line.split("\t")
            if len(bits) != 3:
                continue
            added, deleted, path = bits
            path = _normalize_rename(path)
            a = 0 if added == "-" else int(added)
            d = 0 if deleted == "-" else int(deleted)
            prev = current["files"].get(path, (0, 0))
            current["files"][path] = (prev[0] + a, prev[1] + d)
        return commits

    full = parse([])
    if full is None:
        return None
    since = parse([launch_ref + "..HEAD"]) if launch_ref else None
    return {"full": full, "since_launch": since}


def _normalize_rename(path):
    """git numstat renders renames as 'a => b' or 'p/{a => b}/s'. Keep the new path."""
    m = re.match(r"^(.*)\{(.*) => (.*)\}(.*)$", path)
    if m:
        return (m.group(1) + m.group(3) + m.group(4)).replace("//", "/")
    if " => " in path:
        return path.split(" => ", 1)[1]
    return path


def resolve_launch(explicit):
    """Resolve the public launch commit. Reported, never guessed silently."""
    if explicit:
        sha = (R.git("rev-parse", explicit) or "").strip()
        if sha:
            date = (R.git("log", "-1", "--format=%cI", sha) or "").strip()
            subject = (R.git("log", "-1", "--format=%s", sha) or "").strip()
            return {"sha": sha, "date": date, "subject": subject,
                    "resolved_by": "--launch-ref argument"}
        return {"sha": None, "reason": "could not resolve " + explicit}
    out = R.git("log", "--format=%H\x01%cI\x01%s")
    if out is None:
        return {"sha": None, "reason": "git log unavailable"}
    candidates = []
    for line in out.splitlines():
        sha, date, subject = line.split("\x01", 2)
        if re.search(r"cut v1\.0\.0", subject):
            candidates.append((sha, date, subject))
    if not candidates:
        return {"sha": None,
                "reason": "no commit subject matches 'cut v1.0.0'; pass --launch-ref"}
    sha, date, subject = candidates[-1]
    return {"sha": sha, "date": date, "subject": subject,
            "resolved_by": "oldest commit whose subject matches 'cut v1.0.0'"}


def check_staleness(inv, history, launch):
    if history is None:
        return {"status": "could_not_run", "reason": "git history is unavailable"}

    last_touch = {}
    for commit in history["full"]:
        for path in commit["files"]:
            last_touch.setdefault(path, commit["date"])

    rows = []
    for name, path, shape in inv.commands:
        rp = R.rel(path)
        rows.append({
            "command": name,
            "path": rp,
            "cluster": inv.cluster(name),
            "last_commit_date": last_touch.get(rp),
        })

    dated = [r for r in rows if r["last_commit_date"]]
    undated = [r for r in rows if not r["last_commit_date"]]
    oldest = sorted(dated, key=lambda r: (r["last_commit_date"], r["command"]))[:10]

    before_launch = []
    if launch.get("date"):
        for r in dated:
            if r["last_commit_date"] < launch["date"]:
                before_launch.append(r)

    return {
        "status": "ok",
        "method": ("last commit date per path from a single 'git log -M --numstat' "
                   "pass over commands/. Renames are normalized to the new path in "
                   "the commit that performed them; older commits still carry the "
                   "old path, so a renamed file's date can read as newer than its "
                   "content history. A repository-wide sweep resets the last-touch "
                   "date of every file it touches; check 15's commit-size "
                   "histogram shows how often that happens here."),
        "launch_commit": launch,
        "per_command": sorted(rows, key=lambda r: r["command"]),
        "ten_least_recently_touched": oldest,
        "untouched_since_before_launch": sorted(
            before_launch, key=lambda r: (r["last_commit_date"], r["command"])),
        "commands_with_no_commit_record": [r["command"] for r in undated],
    }


def check_churn(inv, history, launch):
    if history is None:
        return {"status": "could_not_run", "reason": "git history is unavailable"}

    def aggregate(commits):
        stats = collections.defaultdict(lambda: {"commits": 0, "added": 0, "deleted": 0})
        for commit in commits:
            for path, (a, d) in commit["files"].items():
                s = stats[path]
                s["commits"] += 1
                s["added"] += a
                s["deleted"] += d
        return stats

    full = aggregate(history["full"])
    since = aggregate(history["since_launch"]) if history["since_launch"] is not None else None

    rows = []
    for name, path, shape in inv.commands:
        rp = R.rel(path)
        f = full.get(rp, {"commits": 0, "added": 0, "deleted": 0})
        s = (since or {}).get(rp, {"commits": 0, "added": 0, "deleted": 0})
        rows.append({
            "command": name,
            "path": rp,
            "cluster": inv.cluster(name),
            "commits_all_time": f["commits"],
            "lines_changed_all_time": f["added"] + f["deleted"],
            "added_all_time": f["added"],
            "deleted_all_time": f["deleted"],
            "commits_since_launch": s["commits"] if since is not None else None,
            "lines_changed_since_launch": (s["added"] + s["deleted"]) if since is not None else None,
        })

    by_commits = sorted(rows, key=lambda r: (-r["commits_all_time"], r["command"]))
    return {
        "status": "ok",
        "launch_commit": launch,
        "since_launch_available": since is not None,
        "since_launch_reason": None if since is not None else (
            "the launch commit could not be resolved, so the since-launch columns "
            "are null"),
        "per_command": sorted(rows, key=lambda r: r["command"]),
        "ten_highest_commit_count": by_commits[:10],
        "ten_lowest_commit_count": by_commits[-10:][::-1],
        "ten_highest_lines_changed": sorted(
            rows, key=lambda r: (-r["lines_changed_all_time"], r["command"]))[:10],
        "ten_lowest_lines_changed": sorted(
            rows, key=lambda r: (r["lines_changed_all_time"], r["command"]))[:10],
    }


# ==========================================================================
# 15. Co-change coupling
# ==========================================================================


def check_cochange(inv, history):
    if history is None:
        return {"status": "could_not_run", "reason": "git history is unavailable"}

    path_to_name = {R.rel(p): n for n, p, _ in inv.commands}
    pairs = collections.Counter()
    commit_sizes = collections.Counter()
    for commit in history["full"]:
        names = sorted({path_to_name[p] for p in commit["files"] if p in path_to_name})
        commit_sizes[len(names)] += 1
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                pairs[(names[i], names[j])] += 1

    rows = []
    for (a, b), count in pairs.items():
        if count < 3:
            continue
        rows.append({
            "a": a,
            "b": b,
            "commits_together": count,
            "cluster_a": inv.cluster(a),
            "cluster_b": inv.cluster(b),
            "same_cluster": inv.cluster(a) == inv.cluster(b),
        })
    rows.sort(key=lambda r: (-r["commits_together"], r["a"], r["b"]))

    return {
        "status": "ok",
        "threshold": 3,
        "pairs_at_or_above_threshold": len(rows),
        "pairs_total_observed": len(pairs),
        "commits_touching_commands": sum(commit_sizes.values()),
        "commit_size_histogram": [
            {"command_files_in_commit": k, "commits": v}
            for k, v in sorted(commit_sizes.items())],
        "pairs": rows,
    }


# ==========================================================================
# 11 to 13. Reference graph, reachability, cluster coupling
# ==========================================================================


def build_graph(inv):
    """Directed command-to-command reference graph.

    An edge a -> b exists when command a's file names command b (backticked, or
    as a commands/<b>.md path). Kind is the nearest preceding heading, or
    'frontmatter' when the reference sits in the frontmatter description.
    """
    name_re = {n: re.compile(r"(?<![A-Za-z0-9_-])" + re.escape(n) + r"(?![A-Za-z0-9_-])")
               for n in inv.names}

    edges = []
    seen = set()
    for src, path, _shape in inv.commands:
        text = R.read_text(path) or ""
        fm_lines, _body, body_start = R.split_frontmatter(text)
        lines = text.splitlines()
        fm_end = body_start - 1
        shared = shared_regions(lines)
        shared_mask = set()
        for _blk, _ml, start, end in shared:
            for k in range(start, end):
                shared_mask.add(k)

        heading = None
        for idx, line in enumerate(lines):
            if line.startswith("#"):
                # The H1 of a command file is the command's own name; calling it
                # a kind would read as an edge kind named after a command.
                heading = None if line.startswith("# ") else line.lstrip("#").strip()
            in_fm = idx < fm_end
            kind = "frontmatter" if in_fm else (
                "shared-block" if idx in shared_mask else (heading or "body"))
            for dst, rx in name_re.items():
                if dst == src:
                    continue
                if rx.search(line):
                    key = (src, dst, kind)
                    if key in seen:
                        continue
                    seen.add(key)
                    edges.append({"source": src, "target": dst, "kind": kind,
                                  "line": idx + 1})

    edges.sort(key=lambda e: (e["source"], e["target"], e["kind"], e["line"]))
    return edges


def distinct_pairs(edges, exclude_shared=False):
    out = set()
    for e in edges:
        if exclude_shared and e["kind"] == "shared-block":
            continue
        out.add((e["source"], e["target"]))
    return out


def check_graph(inv, edges, token_rows):
    tokens = {r["command"]: r["approx_tokens"] for r in token_rows}
    fan_out = collections.Counter()
    fan_in = collections.Counter()
    distinct_out = collections.defaultdict(set)
    distinct_in = collections.defaultdict(set)
    own_out = collections.defaultdict(set)
    own_in = collections.defaultdict(set)
    for e in edges:
        fan_out[e["source"]] += 1
        fan_in[e["target"]] += 1
        distinct_out[e["source"]].add(e["target"])
        distinct_in[e["target"]].add(e["source"])
        if e["kind"] != "shared-block":
            own_out[e["source"]].add(e["target"])
            own_in[e["target"]].add(e["source"])

    nodes = []
    for name in inv.names:
        nodes.append({
            "id": name,
            "cluster": inv.cluster(name),
            "shape": inv.shape_by_name[name],
            "approx_tokens": tokens.get(name, 0),
            "fan_in_edges": fan_in.get(name, 0),
            "fan_out_edges": fan_out.get(name, 0),
            "fan_in_distinct": len(distinct_in.get(name, ())),
            "fan_out_distinct": len(distinct_out.get(name, ())),
            "fan_in_distinct_excl_shared": len(own_in.get(name, ())),
            "fan_out_distinct_excl_shared": len(own_out.get(name, ())),
        })

    return {
        "status": "ok",
        "method": ("an edge a -> b exists when command a's file mentions command "
                   "b's exact name at a word boundary. Edge kind is the nearest "
                   "preceding heading, 'frontmatter' inside the frontmatter, or "
                   "'shared-block' inside a region propagated from "
                   "commands/_shared/. Distinct-pair counts collapse the per-kind "
                   "edges. Text inside a shared block is identical across every "
                   "file that carries the block, so both the total and the "
                   "excluding-shared-block figures are reported side by side."),
        "nodes": nodes,
        "edges": edges,
        "edge_count": len(edges),
        "distinct_pair_count": len(distinct_pairs(edges)),
        "distinct_pair_count_excl_shared": len(distinct_pairs(edges, True)),
        "edge_kinds": [{"kind": k, "edges": c} for k, c in
                       sorted(collections.Counter(e["kind"] for e in edges).items(),
                              key=lambda kv: (-kv[1], kv[0]))],
        "ten_highest_fan_in": sorted(
            nodes, key=lambda n: (-n["fan_in_distinct"], n["id"]))[:10],
        "ten_highest_fan_out": sorted(
            nodes, key=lambda n: (-n["fan_out_distinct"], n["id"]))[:10],
        "ten_highest_fan_in_excl_shared": sorted(
            nodes, key=lambda n: (-n["fan_in_distinct_excl_shared"], n["id"]))[:10],
        "ten_highest_fan_out_excl_shared": sorted(
            nodes, key=lambda n: (-n["fan_out_distinct_excl_shared"], n["id"]))[:10],
    }


def check_reachability(inv, edges):
    ep_path = os.path.join(R.ROOT, "wos", "entry-points.md")
    if not os.path.isfile(ep_path):
        return {"status": "could_not_run", "reason": "wos/entry-points.md is absent"}

    text = R.read_text(ep_path) or ""
    seeds = sorted({m for m in re.findall(BT + r"([a-z][a-z0-9-]*)" + BT, text)
                    if m in inv.name_set})
    if not seeds:
        return {"status": "could_not_run",
                "reason": "wos/entry-points.md names no known command"}

    def walk(exclude_shared):
        adj = collections.defaultdict(set)
        for e in edges:
            if exclude_shared and e["kind"] == "shared-block":
                continue
            adj[e["source"]].add(e["target"])
        reached = set(seeds)
        frontier = list(seeds)
        depth = {s: 0 for s in seeds}
        while frontier:
            node = frontier.pop(0)
            for nxt in sorted(adj.get(node, ())):
                if nxt not in reached:
                    reached.add(nxt)
                    depth[nxt] = depth[node] + 1
                    frontier.append(nxt)
        return reached, depth

    # Reported, not flagged: the brief is explicit that unreachability is
    # recorded without interpretation.
    reached, depth = walk(False)
    reached_own, depth_own = walk(True)
    unreachable = sorted(n for n in inv.names if n not in reached)
    unreachable_own = sorted(n for n in inv.names if n not in reached_own)

    return {
        "status": "ok",
        "seed_source": "wos/entry-points.md",
        "seeds": seeds,
        "seed_count": len(seeds),
        "reachable_count": len(reached),
        "unreachable_count": len(unreachable),
        "unreachable": [{"command": n, "cluster": inv.cluster(n)} for n in unreachable],
        "excl_shared_note": ("the second walk drops edges whose only source is "
                             "text propagated from commands/_shared/, which is "
                             "identical in every file carrying the block"),
        "reachable_count_excl_shared": len(reached_own),
        "unreachable_count_excl_shared": len(unreachable_own),
        "unreachable_excl_shared": [
            {"command": n, "cluster": inv.cluster(n)} for n in unreachable_own],
        "depth_histogram": [{"depth": d, "commands": c} for d, c in
                            sorted(collections.Counter(depth.values()).items())],
        "per_command_depth": sorted(
            [{"command": n, "cluster": inv.cluster(n),
              "reachable": n in reached, "depth": depth.get(n),
              "reachable_excl_shared": n in reached_own,
              "depth_excl_shared": depth_own.get(n)}
             for n in inv.names], key=lambda r: r["command"]),
    }


def check_cluster_coupling(inv, edges):
    def tally(pairs):
        matrix = collections.Counter()
        intra = collections.Counter()
        cross = collections.Counter()
        for src, dst in pairs:
            cs, cd = inv.cluster(src), inv.cluster(dst)
            matrix[(cs, cd)] += 1
            if cs == cd:
                intra[cs] += 1
            else:
                cross[cs] += 1
        return matrix, intra, cross

    matrix, intra, cross = tally(distinct_pairs(edges))
    _m2, intra2, cross2 = tally(distinct_pairs(edges, True))

    clusters = sorted(set(inv.spec_clusters.keys()) |
                      {inv.cluster(n) for n in inv.names})
    return {
        "status": "ok",
        "method": ("distinct source-target pairs, collapsing per-kind edges. The "
                   "excluding-shared-block columns drop pairs whose only source "
                   "is text propagated from commands/_shared/."),
        "clusters": clusters,
        "per_cluster": [{
            "cluster": c,
            "members": sum(1 for n in inv.names if inv.cluster(n) == c),
            "intra_cluster_edges": intra.get(c, 0),
            "cross_cluster_edges": cross.get(c, 0),
            "intra_cluster_edges_excl_shared": intra2.get(c, 0),
            "cross_cluster_edges_excl_shared": cross2.get(c, 0),
        } for c in clusters],
        "matrix": [{"from": a, "to": b, "edges": matrix[(a, b)]}
                   for a in clusters for b in clusters if matrix.get((a, b))],
    }


# ==========================================================================
# 16. Section vocabulary
# ==========================================================================


def check_section_vocabulary(inv):
    per_command_headings = {}
    freq = collections.Counter()
    for name, path, _shape in inv.commands:
        text = R.read_text(path) or ""
        _fm, body_lines, _start = R.split_frontmatter(text)
        headings = []
        for line in body_lines:
            if re.match(r"^#{1,6} ", line):
                headings.append(line.lstrip("#").strip())
        per_command_headings[name] = headings
        for h in set(headings):
            freq[h] += 1

    total = len(inv.commands)
    half = total / 2.0
    majority = []
    for heading, count in sorted(freq.items(), key=lambda kv: (-kv[1], kv[0])):
        if count > half:
            missing = sorted(n for n in inv.names
                             if heading not in per_command_headings[n])
            majority.append({
                "heading": heading,
                "commands_with": count,
                "percent": round(100.0 * count / total, 1),
                "commands_missing": missing,
                "missing_count": len(missing),
            })

    return {
        "status": "ok",
        "commands_scanned": total,
        "distinct_headings": len(freq),
        "frequency": [{"heading": h, "commands": c,
                       "percent": round(100.0 * c / total, 1)}
                      for h, c in sorted(freq.items(), key=lambda kv: (-kv[1], kv[0]))],
        "majority_headings": majority,
        "per_command_heading_count": sorted(
            [{"command": n, "headings": len(per_command_headings[n])}
             for n in inv.names], key=lambda r: r["command"]),
    }


# ==========================================================================
# 17. External surface inventory
# ==========================================================================

EXTERNAL_PATTERNS = [
    ("WebFetch tool", re.compile(r"\bWebFetch\b")),
    ("WebSearch tool", re.compile(r"\bWebSearch\b")),
    ("MCP server or MCP tool", re.compile(r"\bMCP\b")),
    ("curl", re.compile(r"(?<![A-Za-z])curl(?![A-Za-z])")),
    ("gh CLI", re.compile(r"(?<![A-Za-z])gh (?:pr|api|issue|repo)\b")),
    ("git fetch or git remote", re.compile(r"\bgit (?:fetch|remote|clone|ls-remote)\b")),
    ("literal http(s) URL", re.compile(r"https?://[^\s)`\"']+")),
    ("package registry lookup",
     re.compile(r"\b(?:npm view|npm registry|PyPI|crates\.io|Maven Central)\b")),
    ("psql or pg_dump", re.compile(r"\b(?:psql|pg_dump)\b")),
    ("delegates web access to capture-references",
     re.compile(r"capture-references")),
]


def check_external_surface(inv):
    rows = []
    shared_hits = []
    for block, spath in sorted(R.shared_block_files().items()):
        slines = R.read_lines(spath)
        labels = []
        for label, rx in EXTERNAL_PATTERNS:
            if any(rx.search(l) for l in slines):
                labels.append(label)
        if labels:
            shared_hits.append({"shared_block": block, "mechanism_labels": labels})

    for name, path, _shape in inv.commands:
        lines = R.read_lines(path)
        # Propagated shared-block regions carry the same text into most command
        # files; they are attributed to the block, not to each command.
        masked = set()
        for _blk, _ml, start, end in shared_regions(lines):
            masked.update(range(start, end))
        meta = inv.meta[name]
        tools = meta["tools"] if isinstance(meta["tools"], list) else []
        mechanisms = []
        for label, rx in EXTERNAL_PATTERNS:
            hits = []
            for i, line in enumerate(lines, start=1):
                if (i - 1) in masked:
                    continue
                if rx.search(line):
                    hits.append({"line": i, "text": line.strip()[:240]})
            if hits:
                mechanisms.append({
                    "mechanism": label,
                    "hits": len(hits),
                    "first_hit": hits[0],
                })
        declared_network_tools = sorted(
            t for t in tools if t in ("WebFetch", "WebSearch"))
        if mechanisms or declared_network_tools:
            rows.append({
                "command": name,
                "cluster": inv.cluster(name),
                "declared_network_tools": declared_network_tools,
                "mechanisms": mechanisms,
                "mechanism_labels": [m["mechanism"] for m in mechanisms],
            })

    return {
        "status": "ok",
        "note": ("inventory only. A match means the file's own text names the "
                 "mechanism; it does not establish that the command performs a "
                 "network call at runtime. Text propagated from "
                 "commands/_shared/ is excluded from the per-command rows and "
                 "attributed to the block instead."),
        "patterns_scanned": [label for label, _ in EXTERNAL_PATTERNS],
        "commands_with_an_external_surface": len(rows),
        "commands_scanned": len(inv.commands),
        "per_command": sorted(rows, key=lambda r: r["command"]),
        "shared_blocks_naming_a_mechanism": shared_hits,
    }


# ==========================================================================
# 18. Near-duplicate text
# ==========================================================================


def check_near_duplicates(inv):
    paragraphs = []
    path_of = {n: R.rel(p) for n, p, _ in inv.commands}
    for name, path, _shape in inv.commands:
        text = R.read_text(path) or ""
        lines = text.splitlines()
        fm_lines, _body, body_start = R.split_frontmatter(text)
        fm_end = body_start - 1
        masked = set(range(0, fm_end))
        for _blk, _ml, start, end in shared_regions(lines):
            masked.update(range(start - 1, end))

        buf = []
        buf_start = None
        in_fence = False
        for idx, line in enumerate(lines):
            if line.strip().startswith("```"):
                in_fence = not in_fence
            if idx in masked or in_fence or not line.strip():
                if buf:
                    paragraphs.append(_make_paragraph(name, buf, buf_start, idx))
                    buf, buf_start = [], None
                continue
            if buf_start is None:
                buf_start = idx
            buf.append(line)
        if buf:
            paragraphs.append(_make_paragraph(name, buf, buf_start, len(lines)))

    paragraphs = [p for p in paragraphs if p and len(p["shingles"]) >= 1]
    paragraphs = [p for p in paragraphs if p["word_count"] >= SHINGLE_MIN_WORDS]
    paragraphs.sort(key=lambda p: (len(p["shingles"]), p["command"], p["start_line"]))

    results = []
    n = len(paragraphs)
    for i in range(n):
        a = paragraphs[i]
        sa = a["shingles"]
        la = len(sa)
        for j in range(i + 1, n):
            b = paragraphs[j]
            lb = len(b["shingles"])
            # Jaccard >= T implies min/max size ratio >= T.
            if la < JACCARD_THRESHOLD * lb:
                break
            if a["command"] == b["command"]:
                continue
            inter = len(sa & b["shingles"])
            if inter == 0:
                continue
            union = la + lb - inter
            score = inter / float(union)
            if score >= JACCARD_THRESHOLD:
                results.append({
                    "score": round(score, 4),
                    "a_command": a["command"],
                    "a_lines": "%d-%d" % (a["start_line"], a["end_line"]),
                    "a_file": path_of[a["command"]],
                    "b_command": b["command"],
                    "b_lines": "%d-%d" % (b["start_line"], b["end_line"]),
                    "b_file": path_of[b["command"]],
                    "a_excerpt": a["text"][:200],
                })

    # Reported, not flagged: a near-duplicate pair is an observation about the
    # text, not a disagreement between two surfaces that should match.
    results.sort(key=lambda r: (-r["score"], r["a_command"], r["b_command"]))

    return {
        "status": "ok",
        "parameters": {
            "shingle_k_words": SHINGLE_K,
            "min_paragraph_words": SHINGLE_MIN_WORDS,
            "jaccard_threshold": JACCARD_THRESHOLD,
            "excluded": ("frontmatter, fenced code blocks, and every region "
                         "propagated from commands/_shared/"),
        },
        "paragraphs_compared": n,
        "pairs_above_threshold": len(results),
        "pairs": results,
        "reported_cap": None,
    }


def _make_paragraph(command, buf, start_idx, end_idx):
    text = " ".join(line.strip() for line in buf)
    norm = re.sub(r"[^a-z0-9 ]+", " ", text.lower())
    words = norm.split()
    if len(words) < SHINGLE_K:
        return None
    shingles = frozenset(
        " ".join(words[i:i + SHINGLE_K]) for i in range(len(words) - SHINGLE_K + 1))
    return {
        "command": command,
        "start_line": start_idx + 1,
        "end_line": end_idx,
        "word_count": len(words),
        "shingles": shingles,
        "text": text,
    }


# ==========================================================================
# meta
# ==========================================================================


def script_versions():
    out = []
    audit_dir = os.path.dirname(os.path.abspath(__file__))
    for fn in sorted(os.listdir(audit_dir)):
        if fn.endswith((".py", ".sh")):
            path = os.path.join(audit_dir, fn)
            digest = hashlib.sha256(open(path, "rb").read()).hexdigest()[:16]
            out.append({"script": R.rel(path), "sha256_16": digest})
    for fn in ("lint-commands.sh", "build-agent-skills.sh", "sync-shared-blocks.sh",
               "reconcile-counts.sh"):
        path = os.path.join(R.ROOT, "scripts", fn)
        if os.path.isfile(path):
            digest = hashlib.sha256(open(path, "rb").read()).hexdigest()[:16]
            out.append({"script": R.rel(path), "sha256_16": digest,
                        "role": "reused by scripts/audit/run-baseline.sh"})
    return out


REUSED_GATES = [
    {"key": "lint-commands",
     "argv": ["scripts/lint-commands.sh"],
     "covers": "command lint, shared-block drift, frontmatter, registries, "
               "index rows, count markers, skills drift, doc-sync",
     "keep": re.compile(r"^[A-Z][A-Za-z-]*(?: [a-z-]+)?:\s+\S")},
    {"key": "build-agent-skills-check",
     "argv": ["scripts/build-agent-skills.sh", "--check"],
     "covers": "generated Agent Skills drift against commands/",
     "keep": re.compile(r".")},
    {"key": "sync-shared-blocks-dry-run",
     "argv": ["scripts/sync-shared-blocks.sh", "--dry-run"],
     "covers": "shared-block propagation drift",
     "keep": re.compile(r"^Dry run:")},
    {"key": "reconcile-counts-check",
     "argv": ["scripts/reconcile-counts.sh", "--check"],
     "covers": "count-marker drift against disk",
     "keep": re.compile(r"^(DRIFT|Checked|Scanned|.*marker)")},
]


def run_reused_gates(enabled):
    """Run the repository's own guards and record their verdicts verbatim.

    These are reused rather than reimplemented; the audit's own checks 1, 2, 3,
    and 7 overlap them on purpose so a disagreement between the two is visible.
    """
    if not enabled:
        return {"status": "skipped", "reason": "--no-gates was passed"}
    import subprocess
    out = []
    for gate in REUSED_GATES:
        path = os.path.join(R.ROOT, gate["argv"][0])
        if not os.path.isfile(path):
            out.append({"gate": gate["key"], "status": "could_not_run",
                        "reason": gate["argv"][0] + " is absent",
                        "covers": gate["covers"]})
            continue
        try:
            proc = subprocess.run(
                ["bash", path] + gate["argv"][1:], cwd=R.ROOT,
                capture_output=True, text=True, check=False, timeout=600)
        except (OSError, subprocess.SubprocessError) as exc:
            out.append({"gate": gate["key"], "status": "could_not_run",
                        "reason": str(exc)[:200], "covers": gate["covers"]})
            continue
        lines = [l.rstrip() for l in (proc.stdout or "").splitlines()
                 if l.strip() and gate["keep"].search(l.strip())]
        out.append({
            "gate": gate["key"],
            "command": " ".join(gate["argv"]),
            "covers": gate["covers"],
            "status": "ok",
            "exit_code": proc.returncode,
            "summary_lines": lines,
            "stderr_lines": [l.rstrip() for l in (proc.stderr or "").splitlines()
                             if l.strip()][:20],
        })
    return {"status": "ok", "gates": out}


def build_meta(launch):
    epoch = os.environ.get("SOURCE_DATE_EPOCH")
    if epoch and epoch.isdigit():
        stamp = datetime.fromtimestamp(int(epoch), tz=timezone.utc).isoformat()
    else:
        stamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    sha = (R.git("rev-parse", "HEAD") or "").strip() or None
    dirty = R.git("status", "--porcelain")
    return {
        "audit_version": AUDIT_VERSION,
        "lib_version": R.LIB_VERSION,
        "git_sha": sha,
        "git_commit_time": (R.git("log", "-1", "--format=%cI") or "").strip() or None,
        "git_branch": (R.git("rev-parse", "--abbrev-ref", "HEAD") or "").strip() or None,
        "working_tree_dirty_paths": len([l for l in (dirty or "").splitlines() if l.strip()]),
        "run_timestamp": stamp,
        "determinism": ("every key is byte-stable for an unchanged tree except "
                        "meta.run_timestamp and meta.working_tree_dirty_paths. "
                        "Set SOURCE_DATE_EPOCH to pin the timestamp."),
        "launch_commit": launch,
        "scripts": script_versions(),
        "read_only": ("this script writes only the JSON path given by --out"),
    }


# ==========================================================================
# main
# ==========================================================================


def main(argv):
    ap = argparse.ArgumentParser(description="Fhorja repository baseline audit")
    ap.add_argument("--out", default=None, help="write the JSON report here")
    ap.add_argument("--stdout-json", action="store_true",
                    help="print the JSON report on stdout instead of a summary")
    ap.add_argument("--launch-ref", default=None,
                    help="git ref for the public launch commit")
    ap.add_argument("--no-gates", action="store_true",
                    help="skip the reused repository guards")
    args = ap.parse_args(argv)

    inv = Inventory()
    launch = resolve_launch(args.launch_ref)
    history = git_history(inv, launch.get("sha"))

    report = collections.OrderedDict()
    report["meta"] = build_meta(launch)
    report["reused_gates"] = run_reused_gates(not args.no_gates)

    report["check_01_counts"] = check_counts(inv)
    report["check_02_registry_integrity"] = check_registry(inv)
    report["check_03_shared_block_drift"] = check_shared_blocks(inv)
    report["check_04_cross_reference_integrity"] = check_cross_references(inv)
    report["check_05_adr_coverage"] = check_adrs(inv)
    report["check_06_eval_coverage"] = check_eval_coverage(inv)
    report["check_07_skills_conformance"] = check_skills(inv)
    tokens = check_tokens(inv)
    report["check_08_token_footprint"] = tokens
    report["check_09_claim_consistency"] = check_claims(inv)
    report["check_10_staleness"] = check_staleness(inv, history, launch)

    edges = build_graph(inv)
    report["check_11_reference_graph"] = check_graph(inv, edges, tokens["per_command"])
    report["check_12_reachability"] = check_reachability(inv, edges)
    report["check_13_cluster_coupling"] = check_cluster_coupling(inv, edges)

    report["check_14_churn"] = check_churn(inv, history, launch)
    report["check_15_cochange_coupling"] = check_cochange(inv, history)
    report["check_16_section_vocabulary"] = check_section_vocabulary(inv)
    report["check_17_external_surface"] = check_external_surface(inv)
    report["check_18_near_duplicate_text"] = check_near_duplicates(inv)

    checks = [k for k in report if k.startswith("check_")]
    could_not_run = [k for k in checks if report[k].get("status") == "could_not_run"]
    report["mismatches"] = sorted(
        MISMATCHES, key=lambda m: (m["check"], m["location"], m["expected"]))
    report["summary"] = {
        "commands_total": len(inv.commands),
        "checks_run": len(checks) - len(could_not_run),
        "checks_total": len(checks),
        "checks_could_not_run": could_not_run,
        "mismatches_total": len(report["mismatches"]),
        "mismatches_by_check": [
            {"check": k, "count": v} for k, v in
            sorted(collections.Counter(m["check"] for m in report["mismatches"]).items(),
                   key=lambda kv: (-kv[1], kv[0]))],
    }

    blob = json.dumps(report, indent=2, sort_keys=False, ensure_ascii=False)
    if "—" in blob or "–" in blob:
        sys.stderr.write("baseline_audit: refusing to emit: an em-dash or en-dash "
                         "reached the report payload\n")
        return 3

    if args.out:
        out_path = args.out if os.path.isabs(args.out) else os.path.join(R.ROOT, args.out)
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as fh:
            fh.write(blob + "\n")

    if args.stdout_json:
        sys.stdout.write(blob + "\n")
    else:
        print_summary(report, args.out)
    return 0


def print_summary(report, out_path):
    s = report["summary"]
    print("Fhorja baseline audit")
    print("  git sha:        %s" % (report["meta"]["git_sha"] or "unavailable"))
    print("  commands:       %d" % s["commands_total"])
    print("  checks run:     %d of %d" % (s["checks_run"], s["checks_total"]))
    if s["checks_could_not_run"]:
        print("  could not run:  %s" % ", ".join(s["checks_could_not_run"]))
    else:
        print("  could not run:  none")
    print("  mismatches:     %d" % s["mismatches_total"])
    if out_path:
        print("  json:           %s" % out_path)
    print("")
    if not report["mismatches"]:
        print("No mismatches.")
        return
    print("Mismatches (check | expected | actual | location)")
    width = max(len(m["check"]) for m in report["mismatches"])
    for m in report["mismatches"]:
        print("  %-*s | %s | %s | %s" % (
            width, m["check"], m["expected"], m["actual"], m["location"]))
    print("")
    print("By check:")
    for row in s["mismatches_by_check"]:
        print("  %4d  %s" % (row["count"], row["check"]))


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
