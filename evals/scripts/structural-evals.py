#!/usr/bin/env python3
"""Structural evals: the automatable subset of the scenario regression net.

The eval scenarios under evals/scenarios/ are prose cases: a reviewer reads a
model's output against numbered pass criteria (evals/scripts/run-evals.sh walks
them). That review is not automatable without running a model, and this script
does NOT run a model.

What it DOES do is run the structural invariants that a subset of those
scenarios depend on, the parts that reduce to a static property of this repo.
Each check is labelled with the scenario it enforces, or with the ADR that locked
the invariant when it predates or postdates any scenario. If one of these breaks,
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
import hashlib
import json
import itertools

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


# Mutation-testability, 2026-09-18. Every check resolves paths through p() or
# _repo(), and both consult _ROOT. evals/scripts/guard-mutation.py sets _ROOT to a
# fixture directory, runs one check, and restores it, which is what lets a check be
# pointed at a planted defect instead of at the real tree.
#
# Why here instead of a `root=` parameter on each check: 41 of the 60 checks already
# resolve through p() and 11 more through REPO, so one indirection reaches 52 of them
# at once. The 18 checks that already take `root=` keep it; that parameter names a
# narrower subpath (a skills root, an ADR root) and stays the more precise tool where
# it exists. Nothing resolves a path at module import time, which is what makes an
# override after import safe: checked 2026-09-18, the only module-level use of REPO is
# its own definition.
_ROOT = None


def _repo():
    return _ROOT or REPO


def p(*parts):
    return os.path.join(_repo(), *parts)


class fixture_root:
    """Point every path-resolving check at `path` for the duration of the block."""

    def __init__(self, path):
        self.path = path
        self._prev = None

    def __enter__(self):
        global _ROOT
        self._prev = _ROOT
        _ROOT = self.path
        return self

    def __exit__(self, *exc):
        global _ROOT
        _ROOT = self._prev
        return False


class MissingArtifact(FileNotFoundError):
    """A file a check requires is absent from the tree.

    The generic exception handler in the runner renders any raise as "a defect in the
    check itself, not necessarily in the repo". That sentence is right for a NameError
    and wrong for a deleted artifact, and it sends the reader to the checker instead of
    to the file. Measured 2026-09-18: 12 checks read a fixed path with no existence
    guard, so deleting any one of those artifacts produced exactly that misdirection.

    Subclasses FileNotFoundError, so anything already handling that keeps working.
    """

    def __init__(self, path):
        self.path = path
        super().__init__(f"{path}: required by a check and absent from the tree")


def read(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        # relpath only while it stays inside the tree: a fixture under /var/folders
        # renders as a wall of `../`, which buries the filename the message is for.
        rel = os.path.relpath(path, _repo())
        raise MissingArtifact(path if rel.startswith("..") else rel) from None


def _read_verbatim(path):
    """Read without universal-newline translation.

    read() opens with newline=None, so Python rewrites CRLF and a lone CR to LF before
    any check sees the text. That is why a CRLF fixture on disk could not assert
    anything about CRLF: it reached the gate as LF. Scoped to the tier gate rather than
    folded into read(), because the prose checks compare sentences and would start
    seeing stray CR.
    """
    with open(path, "r", encoding="utf-8", newline="") as f:
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


def _command_path(name):
    """Path to ONE command whose source may be flat OR folder-shaped.

    commands/performance-budget/ is already folder-shaped, so p("commands", name + ".md")
    is not a safe way to reach a command by name: it raises FileNotFoundError, and a
    raise is swallowed by main()'s per-check isolation and printed as infrastructure
    noise rather than as a failing invariant. Returns None when neither shape exists,
    so a genuinely missing command is a named FAIL.
    """
    flat = p("commands", f"{name}.md")
    if os.path.isfile(flat):
        return flat
    folder = p("commands", name, "SKILL.md")
    return folder if os.path.isfile(folder) else None


def _command_body(name):
    path = _command_path(name)
    return read(path) if path else None


def _scenario_files():
    return sorted(glob.glob(p("evals", "scenarios", "[0-9]*.md")))


# The documents that describe the workflow as it runs today, as opposed to the record of how
# it got here. The 2026-09-22 drift audit found the same retired rule restated in the spec, the
# wos topics, the templates, the FAQ, the eval scenarios and the e2e walkthrough, while the checks
# that guarded it read commands/ alone. So a tree-wide rule reads this set.
#
# Left out on purpose, because they are history and rewriting them would falsify the record:
# docs/adr/ (AGENTS.md section 5 freezes a Decision), CHANGELOG.md, ROADMAP.md, docs/audit/ and
# docs/DELETION_LEDGER.md.
LIVE_DOC_ROOT_FILES = ("WORKFLOW_OPERATING_SYSTEM.md", "README.md", "AGENTS.md", "CLAUDE.md",
                       "COMMAND_PROMPT_STUBS.md", "WORKFLOW_DEMO.md", "CONTRIBUTING.md",
                       "SECURITY.md", "docs/FAQ.md", "docs/MIGRATION.md", "docs/HOOKS.md",
                       "docs/EXAMPLE_TRANSCRIPT.md", "evals/README.md", "evals/spine-evals.json")
LIVE_DOC_GLOBS = ("commands/*.md", "commands/*/SKILL.md", "commands/_shared/*.md", "wos/*.md",
                  "templates/*.md", "templates/*/*.md", "templates/*.json", "docs/security/*.md",
                  "evals/scenarios/*.md", "evals/e2e/*.md")


def _live_doc_files():
    files = set()
    for rel in LIVE_DOC_ROOT_FILES:
        if os.path.isfile(p(*rel.split("/"))):
            files.add(p(*rel.split("/")))
    for pattern in LIVE_DOC_GLOBS:
        files.update(glob.glob(p(*pattern.split("/"))))
    return sorted(files)


def _shared_block_bodies():
    """Verbatim content of every commands/_shared/<name>.md source block.

    sync-shared-blocks.sh injects these bodies unchanged into every command that
    declares the matching `<!-- shared:X -->` marker, so the same sentence can
    appear identically in 80+ command files. Routing-signal extraction needs
    this list to subtract that boilerplate before it goes looking for a
    command's OWN curated routing text; see check_tier_routing_closure().
    """
    return [read(f).strip("\n") for f in glob.glob(p("commands", "_shared", "*.md"))]


def _strip_shared_blocks(body, shared_bodies):
    for block in shared_bodies:
        if block and block in body:
            body = body.replace(block, "")
    return body


def _command_name_from_path(f):
    name = os.path.splitext(os.path.basename(f))[0]
    if name == "SKILL":
        name = os.path.basename(os.path.dirname(f))
    return name


def _command_profiles():
    """Command basename -> its own declared metadata.x-wos-profiles tier set."""
    profiles = {}
    for f in _command_files():
        name = _command_name_from_path(f)
        m = re.search(r"x-wos-profiles:\s*\[([^\]]*)\]", read(f))
        profiles[name] = (
            set(x.strip() for x in m.group(1).split(",") if x.strip()) if m else set()
        )
    return profiles


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
    # Fail closed on an empty subject. "every command's name matches" and "there are
    # no command files" print the same clean line, and the second is a broken run.
    # The same reasoning check_unconditional_load_declared already carries; it had
    # not propagated. Added 2026-09-18 after check_highest_adr_claim was found
    # reporting [PASS] over zero surfaces when run from another directory.
    commands = sorted(glob.glob(p("commands", "*.md")))
    if not commands:
        return (False, ["commands/: no command files found; this check lost its subject "
                        "rather than the subject becoming clean"])
    for f in commands:
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
        return (False, ["scripts/reconcile-counts.sh: missing; this check delegates the entire "
                        "count-marker comparison to it, so its absence is an unmeasured tree "
                        "rather than a clean one"])
    res = subprocess.run(["bash", script, "--check"], cwd=_repo(),
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


def _table_cells(line):
    """Cells in a markdown table row, ignoring pipes inside code spans and escaped pipes."""
    text = re.sub(r"`[^`]*`", "C", line).replace("\\|", "E")
    return text.strip().strip("|").count("|") + 1


# The index tables the registry lint reads for row membership (ADR-0029), each with the heading
# of its first column, which is how its header row is found.
INDEX_TABLES = (("evals/README.md", "| # |"), ("docs/adr/README.md", "| ADR |"))


def check_index_tables_whole():
    """[docs drift audit, gap 10] Each index table is one table, and every row has the header's cells.

    The index lint asks whether each scenario and each ADR HAS a row. It never asked whether the
    rows form a table. A blank line at evals/README.md:149 ended the scenario table there, so every
    row below it rendered as a paragraph, and four rows carried four cells under a three-column
    header; the lint stayed green because the filenames were still on the page. The ADR index had
    the same defect in 23 rows that dropped their Status and Tags cells.

    So: from the header row to the last row, every line is a table row (no blank line, no prose in
    between), and every row has exactly as many cells as the header.
    """
    fails = []
    for rel, header in INDEX_TABLES:
        path = p(*rel.split("/"))
        if not os.path.isfile(path):
            fails.append(f"{rel}: missing, so its index table cannot be checked")
            continue
        lines = read(path).split("\n")
        start = next((i for i, l in enumerate(lines) if l.startswith(header)), None)
        if start is None:
            fails.append(f"{rel}: no index table header starting `{header}`")
            continue
        width = _table_cells(lines[start])
        rows = [i for i, l in enumerate(lines) if i > start and l.startswith("| ")
                and re.match(r"\| (?:\[)?\d", l)]
        if not rows:
            fails.append(f"{rel}: the index table has a header and no rows")
            continue
        for i in range(start + 1, rows[-1] + 1):
            line = lines[i]
            if not line.startswith("|"):
                fails.append(f"{rel}:{i + 1}: breaks the index table ({'a blank line' if not line.strip() else repr(line[:40])}); "
                             f"every row below it renders as a paragraph")
            elif _table_cells(line) != width:
                fails.append(f"{rel}:{i + 1}: has {_table_cells(line)} cells under a {width}-column header")
    return (not fails, fails)


def check_walker_covers_corpus():
    """[scenario corpus] The manual walkthrough enumerates every scenario in the corpus.

    run-evals.sh builds its list from a shell glob. A two-digit character class cannot match a
    three-digit prefix, so on 2026-08-21 the walk reached 99 of 135 scenarios: everything from
    100- onward was invisible to the walk and to --list, while CLAUDE.md and evals/README.md both
    instruct a full walk before tagging a release. evals/README.md records the same drift class
    biting once before, when the walker stopped at 101 while the corpus reached 117; that was fixed
    for the README rows and never audited for the walker itself.

    This check is where the coverage becomes a gate. run-evals.sh emits no verdict, exits 0 on every
    coverage outcome, and CI never invokes it (lint.yml mentions it only in a comment), so fixing the
    glob alone would leave nothing to notice the next regression. structural-evals.py IS a CI job and
    returns 1 on any failure.
    """
    src = read(p("evals", "scripts", "run-evals.sh"))
    m = re.search(r'ALL_SCENARIOS=\(\s*"?\$\{?SCENARIOS_DIR\}?"?\s*/\s*([^\s)"]+)', src)
    if not m:
        return (False, ["run-evals.sh: no ALL_SCENARIOS glob found; this check cannot verify coverage"])
    pattern = m.group(1)
    walked = {os.path.basename(f) for f in glob.glob(p("evals", "scenarios", pattern))}
    corpus = {os.path.basename(f) for f in _scenario_files()}
    fails = []
    missing = sorted(corpus - walked)
    if missing:
        shown = ", ".join(missing[:5]) + (" ..." if len(missing) > 5 else "")
        fails.append(
            f"run-evals.sh glob={pattern} walks {len(walked)} of {len(corpus)} scenarios; "
            f"{len(missing)} never enumerated: {shown}"
        )
    extra = sorted(walked - corpus)
    if extra:
        fails.append(
            f"run-evals.sh glob={pattern} matches {len(extra)} file(s) outside the corpus: "
            + ", ".join(extra[:5])
        )
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
    # `none` is the sanctioned TERMINAL form, not a command and not an
    # illustrative placeholder: `Run now: none` with `Mode: N/A` declares that
    # the chain has ended and no following command would be honest (ADR-0126,
    # WORKFLOW_OPERATING_SYSTEM.md `## Global output contract`). It names no
    # file by design, so the basename invariant does not apply to it. It is kept
    # apart from known_illustrative because that set means "an example of a BAD
    # handoff", and folding a valid contract value into it would teach the
    # opposite of what the contract says.
    terminal = {"none"}
    pat = re.compile(r"Run now:\s*/?([a-z][a-z0-9-]+)")
    fails = []
    for f in _command_files():
        body = read(f)
        for m in pat.finditer(body):
            name = m.group(1)
            if name in real or name in known_illustrative or name in terminal:
                continue
            fails.append(f"{os.path.relpath(f, REPO)}: Run now references unknown command '{name}'")
    return (not fails, fails)


# A route into an opt-in capability cluster is correct when it is gated: the
# cluster is additive, so a general command may name a cluster command behind a
# trigger. Only an UNCONDITIONAL cross-tier route is a defect (D-7, 2026-07-25).
# Measured that day: 23 cross-tier routes, 19 conditional and correct, 4 not.
_COND_MARKER = re.compile(
    r"\b(when|whenever|if|only|optional|gated|off by default|unless|per the)\b", re.I)


def _route_is_conditional(line):
    """True when the sentence carrying the route names a trigger for it."""
    return bool(_COND_MARKER.search(line))


# Conditional cross-tier routes whose target is NOT full-only. The class-wide conditional
# exemption below covers opt-in capability clusters, which are full-only by construction; these
# two are core-tier lifecycle commands a minimal router sends a session to, so the exemption was
# never the right home for them. Measured 2026-08-30 when the exemption was narrowed: of 12
# conditional cross-tier pairs, 10 target a full-only cluster command and these 2 do not.
#
# They are named here rather than left inside a class-wide skip so a reader sees them. Both are
# the ADR-0178 shape and the same question: retag the target into the spine, or reword the route.
# That is an owner decision about spine size, not something a check may take, so the entries stay
# until it is answered. An entry that stops matching a real route is removed, not left to rot.
# Both entries this held were closed on 2026-08-31 (ADR-0182): incident-triage joined the
# minimal profile, so review-hard's ADR-0088 first-action route lands inside the tier, and the
# abstention rule's menu now names a command the installed profile has. An empty dict is the
# point: an exemption that outlives its cases stops being a record and becomes a hole.
TIER_ROUTE_OPEN = {}
TIER_ROUTE_OPEN_REVIEWED = "2026-08-31"


# The opt-in capability clusters a gated route may enter from a lower tier (ADR-0229). Until
# 2026-09-23 the exemption asked only whether the target was full-only, on the reasoning that
# every full-only command is a cluster command. It is not: `verify-against-rubric` was full-only
# and is the general reviewer `approve-plan` and `review-hard` dispatch, so `review-hard ->
# verify-against-rubric` passed as a cluster entry while a minimal install had no reviewer to run.
# Membership is now named here instead of inferred from a tag. A gated route is exempt only when
# its target is a member AND still full-only, so a member later retagged into core loses the
# exemption rather than keeping it.
#
# Listed are the clusters a gated route from a lower tier reaches today, each with every member,
# not only the member currently routed to. Clusters no lower-tier command routes into (design
# system, database context, autonomy, frontend) are not listed; a gated route into one of them
# fails here until the cluster is added, which is the review this registry exists to force.
# Checked 2026-09-23, every pair the old exemption covered:
#   approve-plan, implement-approved-slice, implementation-plan -> implement-fleet: fleet, gated on
#     a remaining wave of size 2 or more; the in-tier path is implement-approved-slice, one slice
#     at a time. Stays exempt.
#   branch-commit -> task-workspace: per-task worktree isolation (ADR-0074, opt-in and git-gated),
#     offered beside the in-tier alternative of naming the branch. Stays exempt.
#   implement-approved-slice -> web-runtime-verify: runtime verification, gated on the web
#     signature. A minimal install on a web task has to add the cluster. Stays exempt.
#   implementation-plan -> unity-scene-plan: game development, gated on a Unity target. Stays exempt.
#   incident-triage -> postmortem-author: reliability, gated on a significant resolved incident.
#     Stays exempt.
#   security-review -> mcp-server-vet: third-party vetting, gated on an agent or MCP surface. The
#     router is core, not minimal. Stays exempt.
#   review-hard -> verify-against-rubric: not a cluster command. Closed by retagging it and its
#     closure (direction-adjust, resolve-contract-gaps, contract-signoff) into minimal and core.
CAPABILITY_CLUSTERS = {
    "fleet (ADR-0038, ADR-0041)": (
        "implement-fleet", "task-init-fleet", "external-research-fleet",
        "feature-library-scout-fleet", "screen-spec-fleet", "atom-audit-fleet",
        "verify-against-rubric-fleet"),
    "per-task workspace (ADR-0074)": ("task-workspace",),
    "runtime verification (ADR-0177)": (
        "web-runtime-verify", "api-runtime-verify", "app-runtime-verify", "godot-runtime-verify"),
    "game development (ADR-0069, ADR-0132)": (
        "godot-scene-plan", "godot-runtime-verify", "unity-scene-plan"),
    "reliability (ADR-0102, ADR-0156)": (
        "slo-define", "release-plan", "post-deploy-verifier", "postmortem-author"),
    "third-party vetting (ADR-0046, ADR-0070)": ("skill-vet", "mcp-server-vet"),
}
CAPABILITY_CLUSTER_MEMBERS = frozenset(m for ms in CAPABILITY_CLUSTERS.values() for m in ms)


def check_tier_routing_closure():
    """[D-4 prerequisite] A command's own pipeline chain must stay inside its tier.

    D-4 (`x-wos-profiles`, ADR-0059) wants the generated skills profile-filtered
    at the `core` tier, gated on a rule that catches a router handing off to a
    command absent from its own declared tier list before the `minimal` tier is
    ever offered. This is that rule.

    Extraction: two patterns over a command's own prose, after shared-block
    boilerplate is stripped (see below).

    1. The explicit backtick arrow-chain a command uses to spell out its OWN
       recommended next-step sequence, e.g. task-init's Express-tier line
       `` `task-init` -> `implementation-plan` -> `implement-approved-slice` ->
       `branch-commit` ``.
    2. The prose "route to `X`" / "routes to `X`" / "routing to `X`" pattern.
       This catches the far more common real shape of a handoff in this corpus:
       a conditional directive written as a sentence, not an arrow chain, e.g.
       "IF the plan's remaining wave is size 2 or more THEN route to
       `implement-fleet`". A conditional handoff is still a real handoff:
       whichever branch of the IF fires at runtime, a session that lacks the
       target command in its own tier hits the same break the arrow-chain
       pattern already catches. Restricting to a bare mention (no arrow, no
       "route to") stays out of scope on purpose; that is what makes
       flow-audit.py's whole-word scan noisy (27 hits in task-init.md alone),
       not signal for this rule.

    Shared-block boilerplate (identical text injected into 80+ command files by
    sync-shared-blocks.sh, such as the generic claim-grounding abstention
    example list, which names capture-references, code-locate, and
    incident-triage as ILLUSTRATIVE investigation examples, not per-command
    handoffs) is stripped first, so a hit always comes from a command's own
    curated routing text. This is what stops the ~89-file false-positive
    explosion a naive scan of that boilerplate would otherwise produce.

    Known residual gap from that same stripping: a handful of real routing
    directives live inside a shared block used by only a few files (for
    example the references-reconcile block's "route to
    `implement-slice-complement`" line, injected into review-hard.md,
    slice-closure.md, and task-close.md). Stripping ALL shared blocks removes
    those too, so review-hard's copy of that break is not visible to this
    check even though it is real; the corpus needs a human sweep for that
    class, a pattern change would reopen the false-positive explosion this
    check exists to avoid.

    Confirmed over the real corpus (2026-07-25 re-verification): the corpus is
    NOT clean, and it is less clean than this check previously reported. The
    single-finding picture (`task-init -> branch-commit`, a minimal-tier
    break) undercounted because the earlier extraction only matched arrow
    chains; adding the prose "route to" pattern surfaces 16 further breaks,
    THREE of them at the `core` tier (a `core`+`full` router handing off to a
    `full`-only target): `incident-triage -> postmortem-author`,
    `problem-framing -> godot-scene-plan`, `security-review -> mcp-server-vet`.
    The rest are minimal-tier, spanning `approve-plan`, `implement-approved-
    slice`, `implementation-plan`, `decision-interview`, `slice-closure`, and
    `task-close`, each routing to at least one target absent from their own
    minimal tier (see the findings list at runtime for the exact pairs).

    This matters for D-4 specifically: D-4's profile-filter-at-`core` plan
    implicitly assumed `core` was already clean and only `minimal` had a known
    gap. That assumption does NOT hold. The `core` tier has its own unresolved
    breaks, so D-4 should NOT filter generated skills at the `core` tier until
    the three core-tier findings above are resolved; today only the `full`
    tier (which every router and target here already carries) is safe to
    filter on the evidence this check produces.

    Warn-only by design (per D-4 and this task's TEST_STRATEGY): this check
    always returns `ok=True` and surfaces findings for a human to read rather
    D-7 (2026-07-25) made this a HARD check. Two changes made that safe. First,
    `branch-commit` and `implement-slice-complement` were retagged to the minimal
    tier: both are required unconditionally by floors that fire inside minimal
    commands (the ADR-0084 commit-evidence floor at three closure homes, and the
    ready-to-close-with-followups route), so they were spine in practice while
    ADR-0059's 2026-06-26 minimal list, written ten days before ADR-0084, still
    said otherwise. Second, this check now distinguishes a CONDITIONAL route from
    an unconditional one. A gated route into an opt-in capability cluster is
    correct by design: `full` partitions exactly by cluster membership (measured
    2026-07-25: twelve clusters, zero core commands inside one, every cluster
    100% full), so a general command naming a cluster command behind a trigger is
    the additive architecture working, not a leak. Of 23 cross-tier routes
    measured that day, 19 were conditional and correct; the 4 that were not all
    pointed at the two commands now retagged.

    NARROWED 2026-08-30 (ADR-0178). The D-7 sentence above is right about WHY a
    gated route can be correct and wrong about WHEN. `full` partitions by cluster
    membership, so an opt-in cluster target is full-only by construction; a gated
    route to a CORE target is not that case at all. Exempting every gated route
    therefore hid two real breaks for a year: `approve-plan -> test-strategy` and
    `implement-approved-slice -> where-we-at` both read "WHEN ... route to X", both
    reported nothing here, and both left a minimal install with nowhere to go. The
    exemption now requires the target to be full-only. Measured on the day it was
    narrowed: of 12 conditional cross-tier pairs, 10 target a full-only cluster
    command and stay exempt; the 2 that do not are named in TIER_ROUTE_OPEN with
    the reason and a review date, because retagging them changes the spine again
    and that is the owner's call, not this check's.

    NARROWED AGAIN 2026-09-23 (ADR-0229). "Full-only" was standing in for "cluster
    command", and the stand-in leaked: `verify-against-rubric` was full-only without
    being in any cluster, so `review-hard -> verify-against-rubric` (ADR-0145, a
    SHALL on every zero-finding review) passed as a cluster entry while a minimal
    install had no reviewer to dispatch. The exemption now requires the target to be
    named in CAPABILITY_CLUSTERS and to be full-only, both.
    """
    profiles = _command_profiles()
    real = _command_basenames()
    shared_bodies = _shared_block_bodies()
    pat_arrow = re.compile(r"`([a-z][a-z0-9-]+)`\s*->\s*`([a-z][a-z0-9-]+)`")
    pat_route = re.compile(r"(?:route|routes|routing)\s+to\s+`([a-z][a-z0-9-]+)`")
    findings = []
    for f in _command_files():
        name = _command_name_from_path(f)
        body = _strip_shared_blocks(read(f), shared_bodies)
        # Track conditionality per occurrence (D-7), narrowed 2026-08-30. D-7 exempted every
        # gated route on the reasoning that "a target reached only through gated sentences is a
        # correct entry into an opt-in cluster". That reasoning holds for a cluster command and
        # only for a cluster command: `full` partitions exactly by cluster membership, so an
        # opt-in cluster target is full-only by construction. A gated route to a CORE target is
        # a different thing, and the exemption was hiding it: `approve-plan -> test-strategy`
        # and `implement-approved-slice -> where-we-at` both read "WHEN ... route to X", both
        # were invisible here, and both left a minimal install with nowhere to go (ADR-0178).
        # So conditionality exempted a target only when that target was full-only, and since
        # 2026-09-23 (ADR-0229) only when it is also a named member of CAPABILITY_CLUSTERS:
        # full-only turned out to include a general reviewer that belongs to no cluster.
        unconditional = set()
        conditional = set()
        for line in body.split("\n"):
            cands = set()
            for m in pat_arrow.finditer(line):
                cands.update(m.group(1, 2))
            for m in pat_route.finditer(line):
                cands.add(m.group(1))
            gated = _route_is_conditional(line)
            for cand in cands:
                if cand in real and cand != name:
                    (conditional if gated else unconditional).add(cand)
        # A gated route counts when the target is not a full-only cluster command.
        for cand in sorted(conditional - unconditional):
            if cand not in CAPABILITY_CLUSTER_MEMBERS or profiles.get(cand, set()) != {"full"}:
                unconditional.add(cand)
        router_tiers = profiles.get(name, set())
        for t in sorted(unconditional):
            if (name, t) in TIER_ROUTE_OPEN:
                continue
            missing = router_tiers - profiles.get(t, set())
            if missing:
                findings.append(
                    f"{name} -> {t}: router is {sorted(router_tiers)}, target is "
                    f"{sorted(profiles.get(t, set()))} (missing tier(s): {sorted(missing)}) "
                    f"[{'gated route to a non-cluster target' if t in conditional else 'unconditional route'}]"
                )
    # Hard per D-7: the corpus is clean once the two spine commands carry the
    # minimal tier and conditional cluster entries stop counting as breaks.
    return (not findings, findings)


# The Load-stage ceiling (ADR-0116, ratcheted by ADR-0227). This is the ONE place the number
# lives: check_skill_load_budget, check_skill_load_ceiling_slack, the real-load advisory, the
# CHECKS label, scenario 116 and scripts/measure-tokens.py all read or name this constant.
LOAD_CEILING_CHARS = 36000
"""Hard ceiling on one generated `.claude/skills/<name>/SKILL.md`, in chars (9,000 tokens at the
repo's standing 4 chars/token rule).

It only moves down. ADR-0227 pre-authorizes every lowering, so a lower value needs no new
decision; a raise does. check_skill_load_ceiling_slack fails when this number sits more than
LOAD_SLACK_CHARS above the largest skill, so the ratchet turns when trims land instead of
waiting for someone to remember it. 40,000 until 2026-09-23.
"""

LOAD_TARGET_CHARS = 20000
"""Where the ceiling is heading, in chars. Nothing checks against it; it names the destination.

Two outside figures meet at 5,000 tokens (20,000 chars): the Agent Skills specification
recommends keeping a skill's instructions under 5,000 tokens, and the host re-attaches only the
first 5,000 tokens of each skill after a compaction, so a skill over it loses its tail exactly
when a session has run longest. `REINJECTION_CAP_CHARS` below measures that second figure.
"""

# How far the ceiling may sit above the largest skill before check_skill_load_ceiling_slack
# fails and names the lower value. 4,000 chars is one ceiling step of headroom: small enough
# that a finished trim turns the ratchet, large enough that ordinary edits do not trip it.
LOAD_SLACK_CHARS = 4000

# How close to the ceiling check_skill_load_budget starts warning. Chosen against the measured
# distribution rather than picked: on 2026-08-30 it catches the 2 skills under 2000 chars of the
# ceiling and excludes the next one at 2551, so it names what is actually near the edge. It stays
# advisory at the 36,000 ceiling (ADR-0227): a skill in the band warns and never fails.
LOAD_WARN_BAND_CHARS = 2000


def _skill_sizes(root=None):
    """{skill name: chars} over `<root>/*/SKILL.md`, defaulting to the real `.claude/skills/`."""
    skills_root = root or p(".claude", "skills")
    return {
        os.path.basename(os.path.dirname(f)): len(read(f))
        for f in sorted(glob.glob(os.path.join(skills_root, "*", "SKILL.md")))
    }


def check_skill_load_budget(root=None):
    """[scenario 116] No generated skill exceeds the Load-stage size ceiling (ADR-0116, hard fail).

    D-5 retires the per-command `metadata.token-budget` frontmatter field (warn-only,
    83 of 86 flat commands over their own declared value) and replaces it with exactly
    one enforced budget, measured on the artifact the Load stage actually pays for: the
    generated `.claude/skills/<name>/SKILL.md`, not the source `commands/<name>.md`.

    Ceiling: `LOAD_CEILING_CHARS` above, the one place the number is held. It started at
    40000 chars (10000 tokens), a no-regression line just above the 2026-07-25 maximum;
    ADR-0227 lowered it to 36000 once the five skills above that line were trimmed, and
    check_skill_load_ceiling_slack keeps lowering it from here toward `LOAD_TARGET_CHARS`.

    CALLABLE AGAINST A PATH ARGUMENT (TEST_STRATEGY S-3): `root` defaults to the real
    `.claude/skills/` directory (what CI checks), but accepts any directory holding
    `<name>/SKILL.md` fixtures, so the gate can be proven to fail on a deliberately
    oversized fixture without touching the real corpus. A gate that can only be
    tested by breaking the real corpus never gets tested.

    Warning band added 2026-08-30. A ceiling with no approach signal reports the same green
    at 20000 chars and at 39814, and the first news of a problem is a build that broke on a
    paragraph somebody just wrote. The band WARNS and never fails: only a skill over the
    ceiling fails, exactly as before.
    """
    ceiling_chars = LOAD_CEILING_CHARS
    ceiling_tokens = ceiling_chars // 4
    fails, warns = [], []
    for name, n in sorted(_skill_sizes(root).items()):
        if n > ceiling_chars:
            fails.append(
                f"{name}: {n} chars (~{n // 4} tokens) exceeds the {ceiling_chars}-char "
                f"({ceiling_tokens}-token) Load-stage ceiling (ADR-0116)"
            )
        elif ceiling_chars - n <= LOAD_WARN_BAND_CHARS:
            warns.append(
                f"{name}: {n} chars, {ceiling_chars - n} under the {ceiling_chars}-char "
                f"ceiling; inside the {LOAD_WARN_BAND_CHARS}-char warning band, so the next "
                f"paragraph added to this command is the one that fails the build"
            )
    # Failures first: a skill already over the ceiling outranks one approaching it. When
    # nothing is over, ok stays True and the runner prints the band as WARN, which keeps the
    # finding visible without turning CI red over a command that is still inside its budget.
    if fails:
        return (False, fails + warns)
    return (True, warns)


def check_skill_load_ceiling_slack(root=None):
    """[scenario 116] The ceiling sits within LOAD_SLACK_CHARS of the largest skill (ADR-0227, hard fail).

    ADR-0116 called its ceiling "a starting point, not a target" and the docstring above said
    it was meant to ratchet down. It never did: on 2026-09-23 the largest skill was 39,940
    chars and 56 of 98 skills were over 20,000, against 29 when the ceiling was set. A
    ratchet nobody has to turn stays where it is. This check turns it: once trims leave more
    than LOAD_SLACK_CHARS between the ceiling and the largest skill, the build fails and names
    the value to lower `LOAD_CEILING_CHARS` to, the largest skill rounded up to the next
    1,000. Lowering is pre-authorized by ADR-0227, so acting on the finding needs no decision.

    Same `root=` contract as check_skill_load_budget. An empty skills root fails closed: no
    largest skill is a broken run, not a ceiling with room to spare.
    """
    sizes = _skill_sizes(root)
    if not sizes:
        return (False, [".claude/skills/: no generated skills found; this check lost its "
                        "subject rather than the subject becoming clean"])
    largest_name, largest = max(sizes.items(), key=lambda kv: (kv[1], kv[0]))
    slack = LOAD_CEILING_CHARS - largest
    if slack > LOAD_SLACK_CHARS:
        new_value = (largest // 1000 + 1) * 1000
        return (False, [
            f"LOAD_CEILING_CHARS is {LOAD_CEILING_CHARS}, {slack} chars above the largest skill "
            f"({largest_name}, {largest} chars), more than the {LOAD_SLACK_CHARS}-char slack; "
            f"lower it to {new_value} in evals/scripts/structural-evals.py (ADR-0227 "
            f"pre-authorizes a lowering; the target is {LOAD_TARGET_CHARS})"
        ])
    return (True, [])


def skill_descriptions(root=None):
    """Parse every generated skill's frontmatter `description` into {name: text}.

    THE one parser for this surface. Every check on it and the baseline builder call it,
    and that is deliberate: the descriptions are YAML BLOCK scalars (`|-` plus indented
    continuation lines), and a parser written for the single-line shape returns the block
    indicator itself and reports about 2 chars per skill while looking like a valid run.
    Two such parsers were written and discarded here before this helper existed.

    A blank line INSIDE a block scalar belongs to the scalar; the block ends at the first
    line that is non-indented AND non-empty. Breaking on the blank instead truncates the
    description at its first paragraph, which makes a size gate count LOW and a reference
    gate see fewer references: both fail OPEN. Measured 2026-08-10: no description in the
    real corpus carries an internal blank line, so this branch is unreachable from the
    corpus and only `evals/fixtures/description-blank-line/` exercises it.

    Returns (descriptions, files): `descriptions` maps skill name to the joined text (the
    empty string when the skill has no `description:` at all), `files` is the file list the
    names came from, so a caller can assert coverage rather than assume it.
    """
    skills_root = root or p(".claude", "skills")
    files = sorted(glob.glob(os.path.join(skills_root, "*", "SKILL.md")))
    descriptions = {}
    for f in files:
        lines = read(f).split("\n")
        body, grab = [], False
        for line in lines[1:]:
            if line.startswith("description:"):
                grab = True
                continue
            if grab:
                if not line.strip():
                    continue
                if line.startswith((" ", "\t")):
                    body.append(line.strip())
                else:
                    break
        descriptions[os.path.basename(os.path.dirname(f))] = " ".join(body)
    return descriptions, files


def description_references(descriptions):
    """Map each skill to the sorted other-skill names its description mentions.

    Longest name first, so `task-init` is never matched inside `task-init-fleet`, and each
    match is consumed from the working copy so one mention is not counted twice under two
    overlapping names. Word-boundary anchors are hyphen-aware: `(?<![\\w-])` and
    `(?![\\w-])` rather than `\\b`, because `\\b` treats a hyphen as a boundary and would
    match `state-reconcile` inside `sync-state-reconcile`.
    """
    names = sorted(descriptions, key=len, reverse=True)
    out = {}
    for name, text in descriptions.items():
        hits, working = [], text
        for other in names:
            if other == name:
                continue
            pattern = r"(?<![\w-])" + re.escape(other) + r"(?![\w-])"
            if re.search(pattern, working):
                hits.append(other)
                working = re.sub(pattern, " ", working)
        out[name] = sorted(hits)
    return out


def check_description_reference_preservation(root=None, baseline_path=None):
    """[scenario 133] A skill description keeps every cross-reference it carried before.

    The corpus discriminates confusable skills by pointing at each other. Measured
    2026-08-10: 93 of 98 descriptions name at least one other skill, 286 cross-references
    in total, 27 reciprocal pairs where each names the other. A trim that shortens
    descriptions is most likely to cut exactly those clauses, because they read as
    boilerplate, and cutting them is what makes a shorter description stop routing.

    This is the comparative half of the ADR-0135 item-2 gate (D-4). The absolute half, a
    floor on each description's capability segment, is what D-6 locks and does not exist
    yet; naming it here in the present tense would assert a symbol this file lacks.

    The baseline is `evals/skill-description-baseline.json`, regenerated deliberately by
    `evals/scripts/build-description-baseline.py`. That regeneration is the gate's honest
    limit: it cannot stop someone from regenerating, only from doing it silently, since
    the regeneration lands as a reviewable diff. Same shape as a lockfile.

    A skill present in one side and absent from the other FAILS rather than being skipped.
    A silently uncovered skill is the direction that fails open.

    WHY AN ADDED REFERENCE ALSO FAILS, which is not obvious: dropping a reference is the
    regression, so a first version failed only on drops. That gate erodes. A reference
    added without regenerating the baseline sits permanently outside it, and when a later
    edit removes that same reference the check passes, because the baseline never learned
    it existed. Requiring the baseline to MATCH rather than merely be covered is what makes
    every description edit pass through a deliberate regeneration, which is the reviewable
    diff this gate's value rests on. Same shape as the count-marker guard and
    scripts/reconcile-counts.sh: the check asserts, a separate script updates.

    The two failure kinds read differently on purpose. A drop names the lost reference,
    because that is the semantic regression a reviewer must judge. An addition just says
    the baseline is stale, because regenerating is the whole answer.
    """
    if bool(root) != bool(baseline_path):
        given, missing = ("root=", "baseline_path=") if root else ("baseline_path=", "root=")
        return (False, [
            f"called with {given} but no {missing}; the two describe the same corpus and travel "
            f"together, so pass both or neither. Crossing a fixture with the real side reports "
            f"every skill on one side as missing, which looks like a catastrophic failure and is "
            f"not one"
        ])
    path = baseline_path or p("evals", "skill-description-baseline.json")
    if not os.path.exists(path):
        return (False, [f"no baseline at {os.path.relpath(path, REPO)}; run evals/scripts/build-description-baseline.py"])
    baseline = json.loads(read(path))["references"]
    live = description_references(skill_descriptions(root)[0])

    fails = []
    for name in sorted(set(baseline) - set(live)):
        fails.append(f"{name}: in the baseline but not on disk; regenerate the baseline if the skill was removed on purpose")
    for name in sorted(set(live) - set(baseline)):
        fails.append(f"{name}: on disk but not in the baseline, so nothing checks it; regenerate the baseline")
    for name in sorted(set(baseline) & set(live)):
        dropped = sorted(set(baseline[name]) - set(live[name]))
        if dropped:
            fails.append(f"{name}: description no longer names {', '.join(dropped)}")
        added = sorted(set(live[name]) - set(baseline[name]))
        if added:
            fails.append(
                f"{name}: description now names {', '.join(added)}, which the baseline does not "
                f"record, so nothing would catch their later removal; run "
                f"evals/scripts/build-description-baseline.py"
            )
    return (not fails, fails)


CAPABILITY_FLOOR_CHARS = 150

# `Do not use when ...` CONTAINS the string `use when`, so a naive case-insensitive
# `Use when` pattern matches inside the other marker. Measured 2026-08-10: all 63
# lowercase matches in the corpus were that, and ZERO were a real capitalisation variant.
# The lookbehind separates them FOR THE CANONICAL SPACING, a single space after `not`. It
# is deliberately not a full guarantee: `not  use when` (two spaces) and `not\tuse when`
# still overlap, and min() below is what covers those. Neither shape exists in the corpus
# today. Saying the markers are simply disjoint would be the same overstatement this
# comment replaced.
#
# Without the lookbehind the segment came out right ONLY through min() preferring the
# outer match, on the 18 descriptions carrying no standalone `Use when`. That correctness
# was stated nowhere, so an edit replacing min() with "first Use when, else Do not use"
# would have inflated those 18 segments by 7 chars and loosened the floor, in the
# fail-open direction. Verified behavior-preserving when introduced: 0 of 98 segment
# lengths changed.
_MARKER_USE_WHEN = re.compile(r"(?<!not )\bUse when\b", re.I)
_MARKER_DO_NOT_USE = re.compile(r"\bDo not use\b", re.I)


def capability_segment(text):
    """The part of a description that says what the skill DOES.

    Defined as the text before its first routing marker: `Use when`, or `Do not use` when
    the first is absent. Everything after is routing (when to reach for it, when not to).

    Case-insensitive so a capitalisation variant cannot slip past. On today's corpus that
    flag changes nothing by itself, because no real variant exists; see the pattern
    comments above for what it DID change and why the lookbehind is there.

    Returns the whole text when neither marker is present. That is not a free pass: the
    marker clause in check_description_capability_floor fails such a description anyway,
    so a description with no markers cannot slip through on a generous segment.
    """
    starts = [m.start() for m in (p.search(text) for p in (_MARKER_USE_WHEN, _MARKER_DO_NOT_USE)) if m]
    return text[:min(starts)] if starts else text


def check_description_capability_floor(root=None):
    """[scenario 133] A description keeps a capability segment and its `Do not use` marker.

    The absolute half of the ADR-0135 item-2 gate (D-6). The comparative half is
    check_description_reference_preservation above.

    WHY A FLOOR AND NOT A CAP ON WHAT AN EDIT REMOVES. D-5 first specified a bound on
    removal volume, and measurement killed that form: the fail-open attack (keep the
    cross-references, delete the substance) removes between 14 and 90 percent of a
    description, median 64, while the reduction this gate exists to enable removes about
    52 percent. Those ranges overlap, and on 23 of 93 descriptions the attack removes LESS
    than the intended trim. No delta bound separates them. What separates them is what
    REMAINS: the attack drives the capability segment toward zero however much it removed.

    THE FLOOR, derived rather than picked. Measured 2026-08-10 across the 98 generated
    descriptions: capability segments run from 186 chars (`team-update`) to 744, median
    380. 150 is the largest round value below the current minimum, which makes it a
    no-regression floor in the same form ADR-0135 used for the aggregate ceiling. All 98
    clear it today.

    THE MARKER CLAUSE IS DEFINITIONAL, NOT ADDITIVE. The segment is defined BY the first
    routing marker, so a rewrite that drops the markers makes the whole description read as
    capability text. Measured: all 98 clear a 150 floor under that rewrite, which is a total
    bypass. Requiring the marker closes it. Stated absolutely rather than as a
    before-and-after comparison because 98 of 98 carry `Do not use` today, so no baseline is
    needed and this check reads only the live corpus.

    KNOWN RESIDUAL, not closed: a standalone `Use when` is present in 80 of 98, so it cannot
    be required the same way. An edit dropping only `Use when` inflates the measured segment
    and softens the floor without defeating it. (85 appears in earlier notes from this task;
    it counted matches sitting inside `Do not use when`, before _MARKER_USE_WHEN gained its
    lookbehind. Under the shipped pattern the count is 80, and 18 descriptions carry no
    standalone `Use when` rather than 13.)

    WHAT THIS DOES NOT DO: it bounds how gutted a description can get, not whether the
    surviving text says anything. An edit keeping 150 characters of filler passes. No
    deterministic check verifies meaning and this one does not pretend to.
    """
    descriptions, _files = skill_descriptions(root)
    fails = []
    for name in sorted(descriptions):
        text = descriptions[name]
        if not _MARKER_DO_NOT_USE.search(text):
            fails.append(
                f"{name}: no `Do not use` routing marker; without it the capability segment "
                f"is the whole description and the floor below stops meaning anything"
            )
        n = len(capability_segment(text))
        if n < CAPABILITY_FLOOR_CHARS:
            fails.append(
                f"{name}: capability segment is {n} chars, under the {CAPABILITY_FLOOR_CHARS}-char "
                f"floor (D-6); the corpus minimum was 186 when the floor was derived"
            )
    return (not fails, fails)


def check_advertise_stage_budget(root=None):
    """[scenario 132] The Advertise stage (every generated skill's frontmatter
    `description`, injected into every run before any skill is loaded) stays under an
    AGGREGATE budget of 21000 tokens, approximated as 84000 chars at the repo's standing
    4 chars/token rule.

    Budget: a NO-REGRESSION ceiling stated just above the measured 20233 tokens
    (2026-08-09), per ADR-0135. It stops growth; it reduces nothing. The 206-vs-100
    tokens-per-skill gap the 2026-08-08 audit named stays OPEN.

    Why aggregate and not per-skill: lint already caps each description at 1024 chars,
    and a per-skill cap alone has a worst case of 98 * 1024 = 100352 chars with nothing
    firing until each one individually crosses. The aggregate is the missing half.

    Path-parameterized like check_skill_load_budget(root=...) for the same reason: a gate
    that can only be tested by breaking the real corpus never gets tested.

    Parser note: the generated skills carry `description:` as a YAML BLOCK scalar (`|-`
    plus indented continuation lines), not a single-line value. A parser written for the
    single-line shape returns the block indicator itself and reports about 2 chars per
    skill, which looks like a valid run. The fixture RED is what distinguishes a working
    parser from that. The parser itself now lives in skill_descriptions(); this check no
    longer carries its own copy, because a second copy is how the two discarded parsers
    happened.

    What this check CANNOT report, stated here because a reader will otherwise assume it
    can: on success it returns (True, []) and names the measured total only on failure, so
    a parser that truncated every description while leaving each non-empty would pass both
    the coverage assert below and this ceiling from underneath. Guarding the parser is
    check_description_reference_preservation's job, not this one's.
    """
    budget_tokens = 21000
    budget_chars = budget_tokens * 4
    descriptions, files = skill_descriptions(root)
    total = sum(len(d) for d in descriptions.values() if d)
    counted = sum(1 for d in descriptions.values() if d)
    if counted != len(files):
        return (False, [
            f"read a description from only {counted} of {len(files)} generated skills; a "
            f"skill with no description shrinks this surface and makes the budget check "
            f"greener, so the count is asserted rather than assumed"
        ])
    if total > budget_chars:
        return (False, [
            f"the Advertise stage is {total} chars (~{total // 4} tokens) across {counted} "
            f"descriptions, over the {budget_chars}-char ({budget_tokens}-token) aggregate "
            f"budget (ADR-0135)"
        ])
    return (True, [])


def check_no_retired_frontmatter_field():
    """[scenario 116] The retired metadata.token-budget field (ADR-0013, superseded by
    ADR-0116) leaves no trace on the surfaces this repo controls mechanically.

    Scoped to the mechanical field, not the bare substring: no command frontmatter
    declares `token-budget:`, no generated skill carries it forward, and
    scripts/lint-commands.sh no longer requires or computes it. ADR-0013 and
    ADR-0116 themselves, and other historical prose that discusses the retirement,
    are expected to keep saying "token-budget" and are intentionally out of scope
    here; this check guards the field, not the word.
    """
    fails = []
    # Fail closed: no command files and no generated skills is a broken run, not a
    # repository where the retired field has been fully removed.
    subjects = _command_files() + sorted(glob.glob(p(".claude", "skills", "*", "SKILL.md")))
    if not subjects:
        return (False, ["commands/ and .claude/skills/: no files to scan; this check "
                        "lost its subject rather than the subject becoming clean"])
    fm_pat = re.compile(r"^\s*token-budget:\s*\S+", re.M)
    for f in _command_files():
        if fm_pat.search(read(f)):
            fails.append(f"{os.path.relpath(f, REPO)}: frontmatter still declares token-budget")
    for f in sorted(glob.glob(p(".claude", "skills", "*", "SKILL.md"))):
        if fm_pat.search(read(f)):
            fails.append(f"{os.path.relpath(f, REPO)}: generated skill still carries token-budget")
    lint_script = p("scripts", "lint-commands.sh")
    if os.path.exists(lint_script) and "token-budget" in read(lint_script):
        fails.append("scripts/lint-commands.sh: still references the retired token-budget field")
    # Templates are how the field comes back: a template that still declares it
    # seeds the retired field into every artifact authored from it, and the
    # command-frontmatter scan above stays green while it happens.
    for f in sorted(glob.glob(p("templates", "*.md"))):
        if fm_pat.search(read(f)):
            fails.append(f"{os.path.relpath(f, REPO)}: template still seeds the retired token-budget field")
    # Scripts are how the retirement silently breaks something: a script that
    # anchors on the field stops working the moment the field is gone, without
    # failing. add-suggested-model-hint.sh did exactly that until it was repaired.
    anchor_pat = re.compile(r'"\^\s*token-budget:|\^  token-budget:|\[.token.budget.\]')
    for f in sorted(glob.glob(p("scripts", "*.sh")) + glob.glob(p("scripts", "*.py"))):
        if os.path.basename(f) == "lint-commands.sh":
            continue  # covered by its own check above
        body = read(f)
        if anchor_pat.search(body):
            fails.append(f"{os.path.relpath(f, REPO)}: script still anchors on the retired token-budget field")
    return (not fails, fails)


# Derived from the measured minimum, the way ADR-0136 set the spec ceiling just off its
# measurement rather than off an aspiration: a bound that is already red teaches nothing and
# gets waived. Measured 2026-08-30 across all 98 commands, counting only the items the command
# itself authored: the floor is 3, held by 12 commands, and the distribution runs 3 to 15.
# It lands on the same number as CRITERIA_ITEM_FLOOR, reached independently, and the sentence
# that check uses applies here word for word: fewer than three is a paragraph, not a rubric.
DOD_ITEM_FLOOR = 3

# Every one of the 98 commands ends its DoD with the same inherited line, so a raw item count
# says 4 where the author wrote 3. Counting it would mean a command that authored one bullet
# could sit two away from the floor instead of two below it. The floor is about what the
# command's author is accountable for, so the inherited line is excluded from the count.
_DOD_SHARED_ITEM = re.compile(r"confirm it satisfies the shared", re.I)
_DOD_SECTION = re.compile(r"^### Definition of done.*?$(.*?)(?=^### |^## |\Z)", re.M | re.S)
_DOD_ITEM = re.compile(r"^\s*(?:\d+\.|[-*])\s+(\S.*)$", re.M)


def check_required_sections():
    """[required-sections scenarios] Every command carries its DoD and Handoff, and the DoD
    holds a rubric rather than a header.

    Presence was the whole test until 2026-08-30, so `### Definition of done` followed by
    nothing passed. Reproduced before the change: emptying that section in
    commands/what-next.md left this check green, and the DoD is the command's output contract,
    which makes an empty one worse than a missing one. A missing header is visible; an empty
    section reads as satisfied.

    Written in the shape of check_criteria_content_floor, against the same enumerable-item
    idea, because the two are the same claim about two corpora.
    """
    fails = []
    for f in _command_files():
        body = read(f)
        rel = os.path.relpath(f, REPO)
        has_dod = "### Definition of done" in body
        if not has_dod:
            fails.append(f"{rel}: no '### Definition of done'")
        if "### Handoff" not in body:
            fails.append(f"{rel}: no '### Handoff'")
        if not has_dod:
            continue
        section = _DOD_SECTION.search(body)
        if section is None:
            fails.append(
                f"{rel}: '### Definition of done' is present but no section body could be "
                f"read from it; the content floor could not be measured")
            continue
        own = [i for i in _DOD_ITEM.findall(section.group(1)) if not _DOD_SHARED_ITEM.search(i)]
        if len(own) < DOD_ITEM_FLOOR:
            fails.append(
                f"{rel}: the Definition of done has {len(own)} item(s) the command authored, "
                f"below the floor of {DOD_ITEM_FLOOR}; the shared closing line is not counted "
                f"because every command inherits it. A DoD nobody can check is a heading")
    return (not fails, fails)


def check_registry_membership():
    """[registry scenarios] Every command appears in all three human-facing registries.

    Anchored on the line forms lint-commands.sh already enforces rather than on bare substring
    membership, so the two guards cannot disagree about the same tree. Reproduced 2026-08-30
    before the change: a registry whose only mention of a command was the sentence "the foo-bar
    command is great" satisfied this check and failed the lint. Prose is not a registry row.

    The spec cluster list was not read at all, so the check covered two of the three registries
    its own docstring named, and the one it skipped is the one ADR-0029 puts first.
    """
    spec = read(p("WORKFLOW_OPERATING_SYSTEM.md"))
    stubs = read(p("COMMAND_PROMPT_STUBS.md"))
    roles = read(p("wos", "command-roles.md"))
    fails = []
    for name in sorted(_command_basenames()):
        n = re.escape(name)
        if not re.search(rf"^- `{n}`$", spec, re.M):
            fails.append(f"{name}: no cluster-list bullet in WORKFLOW_OPERATING_SYSTEM.md")
        if not re.search(rf"^\| `{n}` \|", stubs, re.M):
            fails.append(f"{name}: no table row in COMMAND_PROMPT_STUBS.md")
        if not re.search(rf"^### {n}$", roles, re.M):
            fails.append(f"{name}: no `### {name}` heading in wos/command-roles.md")
    return (not fails, fails)


def check_adr_indexed():
    """[ADR index scenarios] Every ADR file has a row in docs/adr/README.md.

    The row predicate is the one lint-commands.sh uses, `^| [NNNN]`. It used to accept the
    filename or the bare four-digit number appearing anywhere in the file, and a four-digit
    number appears in that README constantly, in prose and in other rows' cross-references.
    Reproduced 2026-08-30: a README reading "See 0179 discussed in prose. No table row."
    satisfied this check for docs/adr/0179-x.md and failed the lint.
    """
    index = read(p("docs", "adr", "README.md"))
    fails = []
    # Fail closed on an empty subject, same reasoning as above: an ADR directory with
    # no numbered files is a broken run, not a fully indexed corpus.
    adrs = sorted(glob.glob(p("docs", "adr", "[0-9]*.md")))
    if not adrs:
        return (False, ["docs/adr/: no numbered ADR files found; this check lost its "
                        "subject rather than the subject becoming clean"])
    for f in adrs:
        name = os.path.basename(f)
        num = name.split("-")[0]
        if not re.search(rf"^\| \[{re.escape(num)}\]", index, re.M):
            fails.append(f"{name}: no `| [{num}]` row in docs/adr/README.md")
    return (not fails, fails)


def check_no_emdash():
    """[natural-voice / forbidden-bytes scenarios] No em-dash in commands, shared blocks, wos, or root docs.

    Widened on 2026-08-21. CLAUDE.md, WORKFLOW_OPERATING_SYSTEM.md and wos/natural-voice.md all state
    without qualification that an em-dash is a hard build failure; before this, the only directory that
    could actually fail was commands/*.md. Two surfaces are added here because their text reaches a
    model verbatim at runtime: commands/_shared/, whose blocks sync-shared-blocks.sh injects into
    commands and which 9 fleet commands plus orchestrator-bootstrap read by path, and wos/, which
    commands lazy-load by path. Measured at the time of widening: _shared held one occurrence
    (worker-contract.md:115, fixed in the same commit) and wos/ held none, so this ships green.

    Widened again the same day to templates/** and docs/adr/, after the maintainer decided both. The
    templates glob is RECURSIVE on purpose: a flat templates/*.md would have matched 6 of the 15 dirty
    files and reported clean over templates/foundations/, which held the other 9. Partial coverage that
    is born green over a dirty directory is worse than none.

    On the ADRs: this repository treats an accepted ADR as immutable, but the rule is scoped to the
    DECISION ("reverses or supersedes a load-bearing decision", CLAUDE.md; "immutable in spirit",
    docs/adr/README.md), not to typography. ADR-0090 already records an in-place codename redaction
    across nine ADRs as a documented exception, which is a larger edit than this one. The 19
    occurrences cleaned were 15 reference-list glosses and 4 prose spans; no decision text changed.

    Widened again on 2026-08-30 to the seven remaining tracked root documents: AGENTS.md,
    WORKFLOW_DEMO.md, CLAUDE.md, CHANGELOG.md, ROADMAP.md, CODE_OF_CONDUCT.md and SECURITY.md.
    All seven were measured clean before the widening, so this ships green rather than forcing a
    cleanup in the same change. Two of them are the ones a contributor reads first, and AGENTS.md
    is the file that states the rule to every agent working in this tree, so it not being covered
    by the rule it states was the gap worth closing.

    What stays outside coverage, measured the same day and deliberately left: the six
    scripts/baseline-*.md files hold 30 occurrences between them. They are dated token-measurement
    snapshots from 2026-05-07 and 2026-05-08, and editing their typography would alter a record of
    what was measured on a given day. Frozen history is not drift.
    """
    fails = []
    targets = _command_files() + sorted(glob.glob(p("commands", "_shared", "*.md"))) \
        + sorted(glob.glob(p("wos", "*.md"))) \
        + sorted(glob.glob(p("templates", "**", "*.md"), recursive=True)) \
        + sorted(glob.glob(p("docs", "adr", "*.md"))) + [
        p("README.md"), p("docs", "FAQ.md"), p("CONTRIBUTING.md"),
        p("WORKFLOW_OPERATING_SYSTEM.md"), p("COMMAND_PROMPT_STUBS.md"),
        p("AGENTS.md"), p("WORKFLOW_DEMO.md"), p("CLAUDE.md"), p("CHANGELOG.md"),
        p("ROADMAP.md"), p("CODE_OF_CONDUCT.md"), p("SECURITY.md"),
    ]
    # Fail closed on an empty subject, and test the files that EXIST rather than the
    # candidate list. `targets` ends with twelve literal root-doc paths appended
    # whether or not they are on disk, so `if not targets` is dead code that can never
    # fire. The first version of this guard was exactly that, and the empty-subject
    # mutation refused to bite, which is how it was caught: a guard that cannot
    # trigger is decoration, and the harness would not record it as proof.
    present = [f for f in targets if os.path.exists(f)]
    if not present:
        return (False, ["commands/, wos/, templates/, docs/adr/ and the root docs: no "
                        "files to scan; this check lost its subject rather than the "
                        "subject becoming clean"])
    for f in targets:
        if not os.path.exists(f):
            continue
        body = read(f)
        # Widened 2026-09-18 to the en-dash. AGENTS.md:89 states the rule as "No
        # em-dash and no en-dash anywhere. The lint fails on those bytes", and this
        # check read only U+2014, so half the advertised rule had no gate behind it.
        # Two en-dashes were live in the scanned surfaces when this was found
        # (wos/sub-agent-orchestration.md and templates/PR_PACKAGE.md) and every gate
        # was green on them. The defect was never "can this check fail"; it fails
        # readily on an em-dash. It was that its predicate did not match its claim,
        # which no mutation test asks about.
        em, en = body.count("—"), body.count("–")
        if em or en:
            # Name WHICH byte. The count was widened to the en-dash on 2026-09-18 and
            # this message was not, so an en-dash reported as "1 em-dash character(s)"
            # sent the reader searching for a character that is not in the file. The
            # mutation harness carries one entry per byte and each asserts its own
            # word, so the two cannot collapse back into one message unnoticed.
            parts = []
            if em:
                parts.append(f"{em} em-dash")
            if en:
                parts.append(f"{en} en-dash")
            fails.append(f"{os.path.relpath(f, REPO)}: {' and '.join(parts)} "
                         f"character(s); AGENTS.md forbids both bytes")
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
    brittle and the doctrine forbids asserting its own wording). Its CARVE-OUT is a
    different property and is guarded hard by check_confidence_carveout_matches:
    that one asserts set equality between the commands Part 1.3 names and the
    commands that declare a graded field, never the doctrine's wording.
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



def check_confidence_carveout_matches(root=None):
    """[ADR-0109] The confidence carve-out the doctrine names equals the commands that declare one.

    Rule 1.3 scopes its own prohibition: "no confidence field, no numeric threshold, and no
    self-assessment prompt anywhere IN THIS CONTRACT". The shared block that every command carries
    drops the scope and reads as absolute: "Do NOT add a confidence field, a numeric threshold, or
    a self-assessment prompt anywhere". Measured 2026-08-30: 99 files carry the unscoped sentence
    and four commands declare a graded confidence field in their own output contract, so four
    commands read as violating a rule they themselves carry. Part 1.3 now names the carve-out, and
    this check makes that list and the disk agree in BOTH directions, so a fifth command cannot
    appear unlisted and a listed command cannot quietly stop declaring one.

    scripts/check-claim-grounding.sh is not redundant with this and was deliberately not widened
    to cover it. Its pattern is assignment-shaped (`confidence: high`) and finds ZERO matches
    across the 98 commands, because the four declare through a JSON enum, a table column, and a
    slash-separated scale instead. That script scans the doctrine's own three source surfaces for
    a D-2 regression; this scans the command corpus for carve-out drift.

    Path-parameterized like check_supersession_marked(root=...) so the negative proof runs on a
    FIXTURE and never on the live tree.
    """
    base = root or _repo()
    doctrine = os.path.join(base, "wos", "active-epistemic-humility.md")
    if not os.path.isfile(doctrine):
        return (False, ["wos/active-epistemic-humility.md: missing, so no list says which commands may declare one"])
    listed, opener = [], False
    for ln in read(doctrine).split("\n"):
        if ln.startswith("The scope of that sentence is this contract"):
            opener = True
            continue
        if opener:
            m = re.match(r"- `([a-z0-9-]+)`", ln)
            if m:
                listed.append(m.group(1))
            elif ln.strip():
                break
    if not opener:
        return (False, ["wos/active-epistemic-humility.md: the Part 1.3 carve-out paragraph is gone, "
                        "so nothing names which commands may declare a confidence field"])
    files = (sorted(glob.glob(os.path.join(base, "commands", "*.md")))
             + sorted(glob.glob(os.path.join(base, "commands", "*", "SKILL.md"))))
    if not files:
        return (False, ["commands/: no command files found"])
    # A graded field, not a mention. Every command carries the shared block's own sentence about
    # confidence, so a bare word match would return all 98. What separates a declaration is the
    # grading scale beside it: an ordered HIGH/MEDIUM/LOW scale, or a JSON `confidence` key.
    graded = re.compile(r"\bHIGH\b.{0,40}\bMEDIUM\b|\bMEDIUM\b.{0,40}\bLOW\b|\"confidence\"\s*[:,\]]")
    declares = set()
    for f in files:
        name = (os.path.basename(os.path.dirname(f)) if os.path.basename(f) == "SKILL.md"
                else os.path.splitext(os.path.basename(f))[0])
        for ln in read(f).split("\n"):
            if re.search(r"confidence", ln, re.I) and graded.search(ln):
                declares.add(name)
                break
    fails = []
    for name in sorted(declares - set(listed)):
        fails.append(f"commands/{name}: declares a graded confidence field and the Part 1.3 carve-out "
                     f"does not name it, so it reads as violating the no-confidence rule it carries")
    for name in sorted(set(listed) - declares):
        fails.append(f"wos/active-epistemic-humility.md: the carve-out names {name}, which declares no "
                     f"graded confidence field; a stale carve-out licenses what nobody is doing")
    return (not fails, fails)



def _names_enumeration(text, values):
    """True WHERE `text` carries ONE contiguous list whose member set is exactly `values`.

    A value that merely OCCURS in the text does not count. Step 7a names Forward+ three
    times and Compatibility twice, only one of each inside the canonical list, so the
    superseded per-value substring test was satisfied by incidental prose: two of its
    three assertions were dead, and gutting the enumeration down to a single tier still
    graded green. Order-independent and backtick-optional so a legitimate rewording does
    not false-fail; CONTIGUITY is what separates the canonical list from its prose.
    """
    alt = "|".join(re.escape(v) for v in values)
    tok = r"`?(?:" + alt + r")`?"
    sep = r"\s*[,;]?\s*(?:or\s+|and\s+)?"
    run = re.compile(tok + r"(?:" + sep + tok + r")+")
    want = set(values)
    for mm in run.finditer(text):
        if {t.strip("`") for t in re.findall(tok, mm.group(0))} == want:
            return True
    return False


def check_godot_tier_gate():
    """[scenario 117] godot-scene-plan states the renderer-tier declaration as REQUIRED for a 3D target.

    Asserts the declaring step, the self-review step, and the fence info string the
    parser keys on. Every prose assertion is driven off the code's OWN value tuples
    (_TIER_VALUES, _DIMENSION_VALUES, _DECL_INFO) rather than a second literal copy, so
    adding a fourth tier to the code forces the prose to name it.
    """
    fails = []
    body = _command_body("godot-scene-plan")
    if body is None:
        return (False, ["commands/godot-scene-plan: neither a flat .md nor a folder-shaped SKILL.md exists"])
    # Assert INSIDE the gate step, not file-wide: a file-wide substring test would
    # false-pass the moment an unrelated line happens to contain "REQUIRED".
    steps = [ln for ln in body.splitlines() if ln.lstrip().startswith("- **Step")]
    declaring = [ln for ln in steps if "declare the renderer tier" in ln.lower()]
    reviewing = [ln for ln in steps if "self-review" in ln.lower() and "renderer tier" in ln.lower()]
    if not declaring:
        fails.append("commands/godot-scene-plan.md: no step DECLARES the renderer-tier requirement (ADR-0117 D-9)")
        return (False, fails)
    if len(declaring) > 1:
        fails.append("commands/godot-scene-plan.md: more than one step claims to declare the renderer tier; "
                     "grading the first lets a second step stand in for a deleted one")
    line = declaring[0]
    if "REQUIRED" not in line.upper():
        fails.append("commands/godot-scene-plan.md: the renderer-tier step is not marked REQUIRED")
    if "INCOMPLETE" not in line.upper():
        fails.append("commands/godot-scene-plan.md: the renderer-tier step states no consequence for a missing tier")
    if not _names_enumeration(line, _TIER_VALUES):
        fails.append("commands/godot-scene-plan.md: the renderer-tier step does not carry "
                     + ", ".join(_TIER_VALUES) + " as one enumeration (an incidental mention "
                     "elsewhere on the same line is not the contract)")
    if not reviewing:
        fails.append("commands/godot-scene-plan.md: no self-review step checks the declaration (D-2/D-8 first enforcement point)")
    else:
        if len(reviewing) > 1:
            fails.append("commands/godot-scene-plan.md: more than one step claims to self-review the declaration")
        if not _names_enumeration(reviewing[0], _TIER_VALUES):
            fails.append("commands/godot-scene-plan.md: the self-review step does not enumerate the tiers "
                         "it tells the author to check")
        if not _names_enumeration(reviewing[0], _DIMENSION_VALUES):
            fails.append("commands/godot-scene-plan.md: the self-review step does not enumerate both dimension values")
    if _DECL_INFO not in body:
        fails.append(f"commands/godot-scene-plan.md: never names the fence info string {_DECL_INFO!r} "
                     "that the declaration parser matches")
    return (not fails, fails)


def check_godot_dimension_routing():
    """[scenario 117] No command names 2D as a default dimension: any command mentioning 2D also mentions 3D.

    Assumption, verified 2026-07-26: every command mentioning 2D today is Godot-related, so the
    corpus-wide form does not over-constrain. If a future NON-Godot command uses "2D" in a layout or
    design sense, scope this check to Godot-context lines rather than deleting it.
    """
    fails = []
    two = re.compile(r"\b2D\b")
    three = re.compile(r"\b3D\b")
    for f in _command_files():
        body = read(f)
        if two.search(body) and not three.search(body):
            rel = os.path.relpath(f, REPO)
            fails.append(f"{rel}: mentions 2D but never 3D (2D is acting as the default dimension)")
    return (not fails, fails)


def _unfenced_lines(text):
    """Lines outside every code-block form and outside a blockquote, for prose compare.

    Was a SECOND fence scanner with its own regex, its own `rstrip("\r")` and
    `str.splitlines()`, forty lines from the one the gate unified onto. That duplication
    is the mechanism behind every defect in this task, and it produced the NBSP split
    directly: two definitions of the same thing drift the moment one is edited.

    It now filters _fence_walk like every other reader. The old justification (the tier
    gate's eligibility rule would let a tilde sample leak) is stale: _fence_walk already
    separates RECOGNIZING a fence from a fence being ELIGIBLE to open a declaration, so
    a tilde sample is recognized and closed here without ever being a declaration.

    A fenced sample, an indented sample, and a quoted upstream line are shared MATERIAL,
    not copied prose: two topics quoting the same sentence of the upstream Godot docs is
    not what ADR-0117 D-5 bans.
    """
    return _prose_lines(text)


def _topic_sentences(path):
    """Sentences of 12 or more words, split per markdown BLOCK first.

    A line with no terminal punctuation (a heading, a list item, a table row) used to be
    glued to the sentence after it, so a sentence copied out from under its heading never
    matched its source. Detection stays VERBATIM-only: a copy reworded by one word, or
    one below the word floor, still escapes, and the docstring says so rather than
    letting "duplicates no prose" imply more than the check does.
    """
    out = set()
    for line in _unfenced_lines(read(path)):
        line = re.sub(r"https?://\S+", "", line).strip()
        if not line or line.startswith("#"):
            continue
        for s in re.split(r"(?<=[.!?])\s+", line):
            s = s.strip(" -*|")
            if len(s.split()) >= 12:
                out.add(s)
    return out


def check_wizard_sets_profile_set(root=None):
    """[ADR-0059] No literal PROFILE= assignment escapes the three places allowed to make one.

    Reproduced 2026-08-30 before the fix: wizard_custom() and run_wizard() assigned PROFILE
    without touching PROFILE_SET, and skills_effective_profile() reads PROFILE_SET, not PROFILE.
    Choosing "Everyday loop" therefore installed 14 commands and all 98 skills. The wizard's own
    harness printed PROFILE=minimal PROFILE_SET=0 on both paths.

    The fix routes every wizard choice through set_profile(), which sets both halves. This check
    is what keeps it that way: a future edit that writes `PROFILE=x` inline anywhere else fails
    the build instead of silently reopening the gap.

    Three assignments are allowed, by line content, not by line number (rule 6): the default
    `PROFILE="${PROFILE:-minimal}"`, the `--profile=` flag branch, and the body of set_profile().
    """
    base = root or _repo()
    path = os.path.join(base, "scripts", "sync-workflow-slash-commands.sh")
    if not os.path.isfile(path):
        return (False, [f"{path}: missing"])
    lines = read(path).splitlines()
    in_helper = False
    fails = []
    # Match an assignment ANYWHERE on the line, not just at line start. The defect this closes
    # lived inside `case` branches (`1) PROFILE="minimal"; ...`), so a line-anchored pattern is
    # blind to exactly the shape that broke, which a fixture proved on the first attempt.
    # `[^A-Z_]` before the name keeps PROFILE_SET= out, and the lowercase `--profile=` in help
    # text never matches because this is case-sensitive.
    assign = re.compile(r"(?:^|[^A-Z_])PROFILE=")
    for n, line in enumerate(lines, 1):
        if re.match(r"^set_profile\(\)", line):
            in_helper = True
        elif in_helper and line.startswith("}"):
            in_helper = False
        if not assign.search(line):
            continue
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        if 'PROFILE="${PROFILE:-' in line:
            continue
        if "--profile=*)" in line:
            continue
        if in_helper and stripped == 'PROFILE="$1"':
            continue
        fails.append(f"scripts/sync-workflow-slash-commands.sh:{n}: literal PROFILE= outside the "
                     f"default, the --profile flag, and set_profile(); a bare assignment leaves "
                     f"PROFILE_SET at 0 and installs every skill regardless of the choice: {stripped}")
    return (not fails, fails)


def check_supersession_marked(root=None):
    """[ADR-0029] An ADR that declares it supersedes another is named in that target's Status line.

    ADRs are immutable by design, which protected the DECISION text and left the METADATA
    unmaintained. Measured 2026-08-29: five ADRs had been superseded in whole or in part with
    nothing in their own Status line saying so, and two of the superseding ADRs declared it only
    in body prose, invisible to any header-level reader.

    Scope is the first 15 lines of each file, deliberately. It forces the declaration into the
    header where a reader looks, and it is exactly why prose-only declarations escaped until now.
    The origin is accepted as `ADR-0139` or as the relative link form `/0139-`, because the
    appositions use markdown links.

    A declaration also counts when it is written into the Status line rather than as its own
    header, which is how four ADRs on disk write it (0170, 0175, 0178, 0179). Only the active
    verb declares: `supersedes` is the declaring side, `is superseded by` the receiving one, and
    a denial such as ADR-0179's "Does NOT supersede ADR-0048" is cut out of the scan so the check
    does not accuse an ADR of failing to record a supersession that explicitly does not exist.

    Path-parameterized like check_skill_load_budget(root=...) so the negative proof runs on a
    FIXTURE and never on the live tree.
    """
    base = root or _repo()
    adr_dir = os.path.join(base, "docs", "adr")
    if not os.path.isdir(adr_dir):
        return (False, [f"{adr_dir}: missing"])
    files = sorted(glob.glob(os.path.join(adr_dir, "[0-9]*.md")))
    if not files:
        return (False, ["docs/adr/: no ADR files found"])
    by_num = {}
    for f in files:
        m = re.match(r"(\d{4})-", os.path.basename(f))
        if m:
            by_num[m.group(1)] = f

    def head(path):
        with open(path, "r", encoding="utf-8") as fh:
            return [next(fh, "") for _ in range(15)]

    decl_re = re.compile(r"^\s*(?:-\s*)?(?:\*\*)?Supersedes\b")
    status_re = re.compile(r"^\s*(?:-\s*)?(?:\*\*)?Status(?:\*\*)?\s*:")
    # A declaration also counts when it is written INTO the Status line rather than as its own
    # header, which is how four ADRs on disk write it (0170, 0175, 0178, 0179). Direction is what
    # separates a declaration from a reception, and the verb carries it: the active `supersedes`
    # is the declaring side, while a superseded ADR says `is superseded by` or `Superseded (by`.
    active_re = re.compile(r"\bsupersedes\b", re.I)
    # And an ADR id can appear on a declaring line inside an explicit denial: ADR-0179 ends its
    # Status with "Does NOT supersede ADR-0048". Harvesting ids from the whole line would accuse
    # 0048 of failing to record a supersession its superseder says does not exist, so the scan
    # runs from the verb and stops at the denial.
    deny_re = re.compile(r"\b(?:does\s+not|do\s+not|never)\s+supersede", re.I)

    # The explicit `Supersedes:` header can deny too, and until 2026-09-20 only the
    # Status branch below knew that. ADR-0212 opens with `Supersedes: nothing. ADR-0171's
    # advisory-by-design decision stands`, and this branch harvested 0171 out of the
    # sentence that says the opposite, then accused 0171 of failing to record it. The
    # denial reasoning was written into `deny_re` for one branch and absent from the
    # other, four lines away, which is the same local-lesson shape this file has now hit
    # four times.
    none_re = re.compile(r"^\s*(?:nothing|none|n/?a)\b", re.I)

    def declared_targets(line):
        if decl_re.match(line):
            _, sep, value = line.partition(":")
            # No colon means no value to read; treat the whole line as the value so a
            # `Supersedes ADR-0100` without punctuation still declares.
            if sep and none_re.match(value):
                return []
            return re.findall(r"ADR-(\d{4})", line)
        if not status_re.match(line):
            return []
        verb = active_re.search(line)
        if not verb:
            return []
        span = line[verb.end():]
        denial = deny_re.search(span)
        if denial:
            span = span[:denial.start()]
        return re.findall(r"ADR-(\d{4})", span)

    fails = []
    for f in files:
        origin = re.match(r"(\d{4})-", os.path.basename(f))
        if not origin:
            continue
        origin = origin.group(1)
        for line in head(f):
            for target in declared_targets(line):
                if target == origin:
                    continue
                tpath = by_num.get(target)
                if not tpath:
                    fails.append(f"docs/adr/{origin}: declares it supersedes ADR-{target}, which is not on disk")
                    continue
                status = [ln for ln in head(tpath) if status_re.match(ln)]
                if not status:
                    fails.append(f"docs/adr/{target}: no Status line in its first 15 lines, so the "
                                 f"supersession declared by ADR-{origin} cannot be recorded there")
                    continue
                if f"ADR-{origin}" not in status[0] and f"/{origin}-" not in status[0]:
                    fails.append(f"docs/adr/{target}: superseded by ADR-{origin} and its Status line "
                                 f"does not say so; a reader who opens it follows a decision that no "
                                 f"longer holds")
    return (not fails, fails)


def check_read_map_headings_resolve(root=None):
    """[ADR-0006] Every section the always-read Minimum read map orders resolves to a real heading.

    Why this gap existed: scripts/check-doc-sync.sh only extracts `## X` tokens from lines that
    NAME the spec file (its scan_wos_headings guards on index($0, "WORKFLOW_OPERATING_SYSTEM")).
    The read map's own rows sit inside the spec, so they never repeat the filename and were never
    scanned. Two dead pointers survived in the one block every command reads on every invocation.

    Three rules, each derived by running the algorithm against disk before it was written:

    1. Scope to the map, not the file. Terminate at the next "\n## ", reusing the idiom
       check_godot_3d_topics_indexed already uses. Its docstring records the opposite mistake:
       a file-wide substring test that gave the right answer by luck.
    2. Resolve per LINE, not per file. A token resolves first against the headings of the
       wos/<topic>.md named on the SAME row, then against the spec. Without this, four correct
       rows fail: `## Calibration examples (non-normative)` lives in wos/global-output-contract.md,
       `## Relationship to user-level memory` in wos/project-level-memory.md, and
       `### Unattended sessions` in wos/cross-cutting-workflow-guardrails.md.
    3. Match by PREFIX, not equality. A real heading matches when it equals the token or begins
       with it followed by a space or a colon. Without this, `### Unattended sessions` and
       `### Claim status and abstention` fail against headings that carry a suffix.

    Rules 2 and 3 exist by measurement, not convenience: written the naive way this check is born
    red on four correct rows, and a guard born red becomes a waiver, then noise, then deleted.
    Path-parameterized like check_skill_load_budget(root=...) so the negative proof runs on a
    FIXTURE and never on the live tree.
    """
    base = root or _repo()
    spec_path = os.path.join(base, "WORKFLOW_OPERATING_SYSTEM.md")
    if not os.path.isfile(p(spec_path)):
        return (False, [f"{spec_path}: missing"])
    spec = read(spec_path)
    marker = "Minimum read map for execution:"
    if marker not in spec:
        return (False, ["WORKFLOW_OPERATING_SYSTEM.md: no 'Minimum read map for execution:' section to check against"])
    read_map = spec.split(marker, 1)[1].split("\n## ", 1)[0]

    def headings_of(text):
        return [ln.strip() for ln in text.splitlines() if ln.startswith("#")]

    def resolves(token, pool):
        for h in pool:
            if h == token or h.startswith(token + " ") or h.startswith(token + ":"):
                return True
        return False

    spec_headings = headings_of(spec)
    fails = []
    for line in read_map.splitlines():
        tokens = re.findall(r"`(#{2,3} [^`]+)`", line)
        if not tokens:
            continue
        pools = [spec_headings]
        for topic in re.findall(r"wos/([A-Za-z0-9._-]+\.md)", line):
            tpath = os.path.join(base, "wos", topic)
            if os.path.isfile(tpath):
                pools.insert(0, headings_of(read(tpath)))
            else:
                fails.append(f"read map cites wos/{topic}, which is not on disk")
        for tok in tokens:
            if not any(resolves(tok, pool) for pool in pools):
                where = " or ".join(["wos/" + t for t in re.findall(r"wos/([A-Za-z0-9._-]+\.md)", line)]) or "the spec"
                fails.append(f"read map orders `{tok}`, which resolves to no heading in {where} or WORKFLOW_OPERATING_SYSTEM.md")
    return (not fails, fails)


def check_godot_3d_topics_indexed():
    """[scenario 117] Every wos/godot-3d-*.md is in the spec read map, the map cites no file
    that is absent from disk, and no 3D topic copies a sentence verbatim from ANY other
    Godot topic (2D, mobile, testing, or another 3D one) instead of cross-referencing it.
    """
    fails = []
    spec = read(p("WORKFLOW_OPERATING_SYSTEM.md"))
    # Scope to the READ MAP, not the whole file. The docstring has always claimed
    # "reachable from the spec read map" while the assertion was a file-wide
    # substring: a filename mentioned anywhere in the spec passed. Today all three
    # happen to sit inside the map, so the file-wide test gave the right answer by
    # luck and would keep passing if the mention moved out of it.
    marker = "Minimum read map for execution:"
    if marker not in spec:
        return (False, ["WORKFLOW_OPERATING_SYSTEM.md: no 'Minimum read map for execution:' section to check against"])
    read_map = spec.split(marker, 1)[1].split("\n## ", 1)[0]
    topics = sorted(glob.glob(p("wos", "godot-3d-*.md")))
    if not topics:
        # An empty result is NOT a pass: the spec read map and godot-scene-plan both cite these
        # files by name, so their absence is a broken contract, not an inapplicable check.
        return (False, ["wos/godot-3d-*.md: no 3D topic files exist, but the spec read map and "
                        "commands/godot-scene-plan.md still cite them by name"])
    on_disk = {os.path.basename(t) for t in topics}
    for name in sorted(on_disk):
        if name not in read_map:
            fails.append(f"wos/{name}: not referenced from the WORKFLOW_OPERATING_SYSTEM.md read map (orphaned topic)")
    # Inverse direction of the same predicate: a read-map row naming a 3D topic that is
    # not on disk. Only the topic-on-disk half was ever checked, so a dangling row
    # passed silently.
    for cited in sorted(set(re.findall(r"wos/(godot-3d-[A-Za-z0-9._-]+\.md)", read_map))):
        if cited not in on_disk:
            fails.append(f"wos/{cited}: cited by the read map but absent from disk (dangling row)")
    # Corpus by SUBTRACTION, not by name-shape enumeration, and 3D topics compared to
    # EACH OTHER as well as to the rest: godot-testing-and-ci.md had to be hand-added to
    # the old glob list once already (D-5), which is the enumeration failing in slow
    # motion, and a sentence lifted from one 3D topic into another escaped entirely.
    others = sorted(set(glob.glob(p("wos", "godot-*.md"))) - set(topics))
    cache = {f: _topic_sentences(f) for f in topics + others}
    for a, b in itertools.chain(((t, o) for t in topics for o in others),
                                itertools.combinations(topics, 2)):
        for dup in sorted(cache[a] & cache[b]):
            fails.append(f"wos/{os.path.basename(a)} and wos/{os.path.basename(b)}: identical "
                         f"sentence instead of a cross-reference: {dup[:60]}...")
    return (not fails, fails)



_TIER_VALUES = ("Forward+", "Mobile", "Compatibility")

_TIER_FIXTURE_EXPECTATIONS = {
    # Fail-closed: absence, duplication, emptiness, and every near miss are all
    # the same verdict. Under the superseded permissive parser three of the six
    # near-miss forms below returned a silent stand-down (verified 2026-07-26).
    "no-declaration": "block",
    "waived-no-declaration": "waived",
    "3d-no-tier": "block",
    "3d-decoy": "block",
    "3d-bad-tier": "block",
    "near-miss-lowercase": "block",
    "near-miss-heading": "block",
    "near-miss-table": "block",
    "near-miss-bulleted": "block",
    "near-miss-emphasis": "block",
    "near-miss-inline-reason": "block",
    "double-declaration": "block",
    "empty-fence": "block",
    "indented-fence": "pass",
    "over-indented-fence": "block",
    "extra-key-in-fence": "block",
    "2d-with-tier": "block",
    "waived-malformed": "block",
    "waiver-names-other-plan": "block",
    "crlf-declaration": "pass",
    "nested-in-outer-fence": "block",
    "tab-indented-fence": "block",
    "nbsp-info-quoted": "block",
    "nbsp-info-bare": "block",
    "over-indented-closer": "block",
    "waiver-indented-code-block": "block",
    "waiver-blockquoted": "block",
    "closer-at-three-spaces": "pass",
    "unterminated-declaration": "block",
    "tilde-fenced-declaration": "block",
    "waiver-without-reason": "block",
    "waiver-inside-code-block": "block",
    "2d-declared": "pass",
    "3d-forward-plus": "pass",
    "3d-mobile": "pass",
    "3d-compatibility": "pass",
    # Fence CHARACTER siblings. Every case above existed in backticks only, so the
    # tilde half of each rule was open: a tilde outer fence was invisible, a tilde
    # sample never opened a block, and a ``` could "close" a ~~~ one.
    "nested-in-tilde-outer-fence": "block",
    "cross-char-close": "block",
    "tilde-sample-then-declaration": "pass",
    "unterminated-tilde-sample": "block",
    "waiver-inside-tilde-block": "block",
    "waiver-after-unterminated-tilde": "block",
    "waiver-prose-beside-tilde-sample": "waived",
    "valid-plus-tilde-declaration": "block",
    "quoting-fence-unterminated": "block",
    "unclosed-declaration-at-eof": "block",
    # LINE-ENDING siblings. crlf-declaration covers only the CRLF pass path, so the
    # CRLF malformed routes had never been exercised; each of these pairs a malformed
    # route with a waiver, which is the only combination whose verdict moved.
    "crlf-malformed-declaration": "block",
    "crlf-unterminated-declaration": "block",
    "crlf-nested-in-outer-fence": "block",
    "crlf-tab-indented-waived": "block",
    "cr-only-unterminated-waived": "block",
    "crlf-waived-no-declaration": "waived",
    "crlf-waiver-inside-code-block": "block",
    # Separators str.splitlines() breaks on and CommonMark does not: a "fence" glued
    # together by one is not a fence any renderer shows.
    "form-feed-pseudo-fence": "block",
    "form-feed-pseudo-fence-waived": "waived",
    "nel-pseudo-fence": "block",
    # WAIVER-MATCHING siblings: every superstring of the plan name used to waive it.
    "waiver-names-superstring-plan": "block",
    "waiver-names-suffixed-plan": "block",
    "waiver-path-qualified-plan": "block",
    "waiver-decorated-plan-name": "block",
    "waiver-superstring-no-reason": "block",
    "waiver-tab-separated": "waived",
    # MULTI-PLAN, the form Step 9 sanctions and the check could not express. A dict
    # value names the verdict per plan file, which is what makes "one waiver line per
    # plan" assertable from a single TASK_STATE.md.
    "multi-plan-declared": "pass",
    "multi-plan-waived-one": {
        "GODOT_SCENE_PLAN_menu.md": "waived",
        "GODOT_SCENE_PLAN_arena.md": "block",
    },
}

_DIMENSION_VALUES = ("2D", "3D")
_DECLARATION_KEYS = ("Dimension", "Renderer tier")

# One anchor, matched exactly. The superseded parser tried to tolerate the many
# ways a bare key-value line can be written; every tolerated form was one the
# author imagined and every missed form was a silent hole. A fence has exactly
# one near miss: it is not there.
# F9: the tolerance counts SPACES, one unit, up to three. The previous
# `[ \t]{0,3}` counted a tab as one unit, so three tabs (twelve columns at the
# conventional width) passed while six spaces blocked: the rule the code ran was
# not the rule its own comment stated. Tabs are rejected outright rather than
# assigned a width, because any width choice is an invention.
_DECL_INFO = "wos-godot-declaration"

# ONE fence recognizer for the whole gate, BOTH characters, so no reader here can be
# blind to a fence another reader sees. Per CommonMark a fence closes only with the
# SAME character, with at least as many marks, and carrying no info string; the
# character and the mark count therefore travel with the open container. Recognizing a
# fence is deliberately separate from being ELIGIBLE to open a declaration: a `~~~`
# block delimits content exactly as a ``` one does, while a tilde-fenced MARKER stays
# malformed (the floor and Step 7 both say so in words).
_FENCE_LINE = re.compile(r"^(?P<indent>[ \t]*)(?P<fence>(?P<char>[`~])(?P=char){2,})(?P<info>.*)$")


# TWO predicates over the same info string, deliberately different and named here so
# the difference stops being an accident. The run that unified the scanner left
# `.strip()` (unicode whitespace) on one side and `[ \t]` on the other, and ONE NBSP
# between the ticks and the info string then flipped a quoted exemplar from MALFORMED
# to waiver-escapable: invisible input undid a ruling taken on purpose.
#   VALID  is strict: only spaces and tabs may surround the info string, because a
#          renderer reading "\u00a0wos-godot-declaration" shows no declaration, and the
#          gate must not accept what the renderer does not.
#   MARKER is permissive: any whitespace, because the question it answers is "did
#          someone ATTEMPT a declaration here", and an attempt with an odd space is
#          still an attempt. Under-counting attempts is what lets a waiver escape.
# Strict about what is VALID, permissive about what is an ATTEMPT: fail-closed in both
# directions, where one shared definition is fail-open in whichever direction it picks.
def _info_is_decl_strict(info):
    return info.strip(" \t") == _DECL_INFO


def _info_is_decl_attempt(info):
    return info.strip() == _DECL_INFO

# The marker on a line of its own, in ANY fence character and at ANY indent. Used only
# to tell "no declaration was written" (absent, waiver-escapable) from "one was written
# and could not be parsed" (malformed, never waiver-escapable). Without it, an
# unterminated fence, a declaration swallowed by an earlier unbalanced fence, and a
# tilde-fenced declaration all landed in the absent bucket the waiver clears.
# Anchored at BOTH ends on purpose: a substring test would call a plan that merely
# MENTIONS the info string in prose malformed and deny it the waiver it honestly earns.
# Read LINE BY LINE through _lines(). It used to be an re.M pattern matched against raw
# text, which a CRLF plan defeats (`[ \t]*$` cannot cross the \r), so every malformed
# route collapsed to absent and the waiver cleared it. There are now no raw-text
# anchored regexes left in this gate; any future one is the same defect.



def _lines(text):
    """The ONE line splitter this gate uses.

    A markdown line ends with LF, CRLF, or CR, and nothing else is a line break. Two
    other splitters were in play and they disagreed: an re.MULTILINE `$` breaks only on
    LF, so a CRLF marker line never matched; str.splitlines() also breaks on VT, FF, FS,
    GS, RS, NEL, U+2028 and U+2029, so a "block" glued together by a control character
    was credited as a declaration no markdown renderer would show. One splitter, used by
    every reader here, makes both impossible rather than fixed. The two-step replace is
    load-bearing: a bare split("\\n") would regress a CR-only file that splitlines()
    used to read.
    """
    return text.replace("\r\n", "\n").replace("\r", "\n").split("\n")


def _fence_walk(text):
    """Yield (line, kind, frame) for every line; kind is "open", "close", or "text".

    ONE fence scanner for the whole gate. The declaration reader and the prose reader
    each carried their own and the two drifted: a tilde outer fence was invisible to
    both, so a plan that merely QUOTED the exemplar graded pass and a waiver written
    inside a ~~~ sample counted as a recorded human act.

    A fence closes only with the SAME character and at least as many marks, and a closer
    carries no info string. A ~~~ never closes a ``` fence and a ``` never closes a ~~~
    one; without that rule a stray sample fence silently reopens prose.

    Keeps F4: a declaration fence nested inside another fence is content, not a
    declaration, which is what stops a plan being credited for quoting the exemplar
    Step 7 tells authors to copy verbatim.
    """
    frame = None
    for line in _lines(text):
        m = _FENCE_LINE.match(line)
        if m:
            indent, fence = m.group("indent"), m.group("fence")
            info_raw, char, width = m.group("info"), m.group("char"), len(fence)
            info = info_raw.strip()
            if frame is None:
                frame = {
                    "char": char,
                    "width": width,
                    "lines": [],
                    # Eligibility, kept separate from being a fence at all: backticks
                    # only, spaces only, at most three. F9: the tolerance counts SPACES,
                    # one unit; a tab is rejected outright rather than assigned a width,
                    # because any width choice is an invention.
                    "decl": (_info_is_decl_strict(info_raw) and char == "`"
                             and "\t" not in indent and len(indent) <= 3),
                }
                yield (line, "open", frame)
                continue
            # The CLOSER now carries the opener's indentation rule. It had none, so any
            # indent closed: a 2D block whose tier entry sat past a 4-space closer
            # graded pass, and a 9-space closer let the gate see a clean block where a
            # renderer sees an unterminated one. An over-indented closer now leaves the
            # fence OPEN, which is malformed, which is the fail-closed direction.
            if (not info and char == frame["char"] and width >= frame["width"]
                    and "\t" not in indent and len(indent) <= 3):
                closed, frame = frame, None
                yield (line, "close", closed)
                continue
        if frame is not None:
            frame["lines"].append(line)
        yield (line, "text", frame)


def _declaration_bodies(plan_text):
    """Bodies of CLOSED top-level backtick wos-godot-declaration fences, in order.

    An unterminated fence yields no body on purpose: it is malformed, not absent, and
    the marker scan below is what records that.
    """
    return ["\n".join(frame["lines"])
            for _line, kind, frame in _fence_walk(plan_text)
            if kind == "close" and frame["decl"]]


def _declaration_markers(text):
    """How many declaration MARKER lines the document carries, fenced or not.

    Whole-text on purpose, not restricted to fence-open events: in the nested case the
    marker line is fence CONTENT rather than an opener, and the floor says a marker
    appearing anywhere in the plan makes it MALFORMED rather than missing.
    """
    return sum(1 for line in _lines(text)
               for m in [_FENCE_LINE.match(line)]
               if m and _info_is_decl_attempt(m.group("info")))


# The blockquote marker is gone from the prefix on purpose (see _prose_lines): a
# quoted line is someone else's sentence, not this task's recorded act.
_WAIVER = re.compile(r"^[ \t*-]*tier-declaration waiver:[ \t]*(?P<rest>.+)$")


def _prose_lines(text):
    """Lines that are a RECORD: outside every code-block form and outside a blockquote.

    The previous round enumerated fence CHARACTERS and never enumerated code-block
    FORMS, so a waiver written as a four-space-indented sample counted as a recorded
    human act while the identical waiver in a ``` fence did not. Markdown has two code
    block forms and the contract's reasoning ("a sample is an illustration") applies to
    both; enumerating one axis and not the other is the same twin-case miss this gate
    has now produced four times.

    Blockquoted lines are dropped for the same reason and for consistency with
    _unfenced_lines forty lines up, which already dropped them: the file cannot treat
    `> ...` as a quotation for one reader and a record for another.

    Fail-closed direction: every rule here REMOVES waiver candidates. An over-strict
    reading costs a block on a plan that could have been waived, and the operator sees
    why; an under-strict one silently opens the only escape a fail-closed gate has.
    """
    for line, kind, frame in _fence_walk(text):
        if kind != "text" or frame is not None:
            continue
        stripped = line.lstrip(" \t")
        if not stripped:
            continue
        if line[:len(line) - len(stripped)].replace("\t", "    ")[:4] == "    ":
            continue  # indented code block: an illustration, in any indent unit
        if stripped.startswith(">"):
            continue  # a quotation, not this task's record
        yield line


def _waived(task_state_text, plan_name):
    """True only when a waiver line NAMES this plan AND gives a reason.

    The floor requires the form `tier-declaration waiver: <plan filename> <reason>`.
    A presence-only test let one junk line waive every plan in a multi-plan task
    (Step 9 allows GODOT_SCENE_PLAN_<slug>.md), a name-only test accepted a waiver with
    no reason at all, and a substring test let any superstring of the name (a path
    prefix, an OLD_ prefix, a .bak suffix) waive the plan it merely contains. Read from
    prose only: a line inside a fenced block, in either fence character, is a code
    sample rather than a recorded human act.
    """
    for line in _prose_lines(task_state_text):
        m = _WAIVER.match(line)
        if not m:
            continue
        # The filename is the FIRST whitespace-delimited token and is compared WHOLE.
        # Substring containment let `archive/OLD_GODOT_SCENE_PLAN.md.bak`,
        # `OLD_GODOT_SCENE_PLAN.md`, `GODOT_SCENE_PLAN.md.bak` and
        # `docs/GODOT_SCENE_PLAN.md` each waive `GODOT_SCENE_PLAN.md`: every superstring
        # of the name waived it, in both directions and through a path prefix. It also
        # defeated the separate reason test, because the residue of the foreign filename
        # counted as the reason. Whole-token equality still supports the multi-plan case
        # (Step 9's `GODOT_SCENE_PLAN_<slug>.md`) because the comparison is on the name
        # as written, not on a shape. The name is written BARE: a path prefix, a backtick
        # or quote wrapper, or an extra extension is a different name and waives nothing.
        # split(None, 1), not partition(" "), so a tab or a run of spaces still separates
        # the filename from the reason.
        parts = m.group("rest").strip().split(None, 1)
        if parts[0] != plan_name:
            continue
        if len(parts) > 1 and parts[1].strip(" \t,;.:-"):
            return True
    return False


def _parse_declaration(plan_text):
    """Return ("absent"|"malformed"|"ok", entries-or-None).

    Absent and malformed are DISTINCT, and collapsing them was a real defect: the
    waiver covers a missing block only (wos/platform-runtime-floors.md says so
    outright), so a single None made the waiver escape an extra key, an empty
    fence, and a duplicated block. Contract and code disagreed while every check
    stayed green, because no fixture paired malformed with a waiver.
    """
    blocks = _declaration_bodies(plan_text)
    markers = _declaration_markers(plan_text)
    if not blocks:
        return ("malformed", None) if markers else ("absent", None)
    # A parsed block PLUS a marker that produced no block is two declarations, one of
    # them broken: the same ambiguity `double-declaration` blocks on, so it blocks here.
    if len(blocks) > 1 or markers > len(blocks):
        return ("malformed", None)
    entries = {}
    for line in _lines(blocks[0]):
        line = line.strip()
        if not line:
            continue
        key, sep, value = line.partition(":")
        key, value = key.strip(), value.strip()
        if not sep or not key or not value or key in entries:
            return ("malformed", None)
        # "Nothing else goes inside the fence" is contract text in both
        # commands/godot-scene-plan.md Step 7 and the floor. Accepting an unknown
        # key made fail-closed silently fail-OPEN for extra content, and the most
        # likely extra key is `Reason:`, which the SUPERSEDED contract taught.
        if key not in _DECLARATION_KEYS:
            return ("malformed", None)
        entries[key] = value
    return ("ok", entries) if entries else ("malformed", None)


def _tier_gate_verdict(plan_text, task_state_text, plan_name):
    """The tier-declaration floor's logic in ONE place, so floor and check cannot drift.

    Mirrors wos/platform-runtime-floors.md '## Godot tier-declaration floor'.
    Returns 'pass', 'waived', or 'block'. There is deliberately NO stand-down for
    an absent declaration: D-10 reversed that default because the permissive
    reading disabled the whole floor on a lowercase typo.

    The waiver covers a MISSING block only. A block that is present but malformed
    blocks regardless of any waiver, matching the floor's own wording.

    plan_name is required, never defaulted: the default was a second hardcoded
    GODOT_SCENE_PLAN.md, and a caller that omitted it for a GODOT_SCENE_PLAN_<slug>.md
    matched the waiver against the wrong filename and failed OPEN.
    """
    status, entries = _parse_declaration(plan_text)
    if status == "malformed":
        return "block"  # a plan that declared badly has declared; no waiver applies
    if status == "absent":
        return "waived" if _waived(task_state_text, plan_name) else "block"
    dimension = entries.get("Dimension")
    if dimension not in _DIMENSION_VALUES:
        return "block"
    if dimension == "2D":
        # The block is required in 2D; the tier entry is required to be ABSENT.
        return "block" if "Renderer tier" in entries else "pass"
    return "pass" if entries.get("Renderer tier") in _TIER_VALUES else "block"


def _is_plan_filename(name):
    """The two plan filenames godot-scene-plan Step 9 sanctions, and no others.

    A prefix match would sweep in a decoy like OLD_GODOT_SCENE_PLAN.md and a bare
    startswith would sweep in GODOT_SCENE_PLANS.md; the fixture unit is the directory,
    so a stray file must not silently become an asserted plan.
    """
    return name == "GODOT_SCENE_PLAN.md" or (
        name.startswith("GODOT_SCENE_PLAN_") and name.endswith(".md"))


def check_godot_tier_artifact_gate(root=None):
    """[ADR-0119] The tier floor's logic behaves correctly on every fixture.

    Path-parameterized like check_skill_load_budget(root=...). The fixture unit is a
    DIRECTORY holding one or more plan files and, where the case needs one, a
    TASK_STATE.md carrying the waiver line: that is what makes the waiver path
    deterministic rather than asserted only in prose. It never reads a live task folder.

    Fixtures are read VERBATIM (no universal-newline translation), because a
    line-ending fixture that reaches the gate as LF asserts nothing about the bytes on
    disk. Do not swap _read_verbatim back to read() for tidiness.

    Iteration is over the DIRECTORY LISTING, not the expectation dict, and the same rule
    holds one level down: a plan file inside a fixture that no expectation names is a
    FAILURE. The superseded version iterated the dict, so a fixture nobody listed could
    be added, look present, and assert nothing.
    """
    base = root or p("evals", "fixtures", "godot-tier-artifact")
    fails = []
    if not os.path.isdir(base):
        return (False, [f"fixture directory missing: {base}"])
    on_disk = {d for d in os.listdir(base) if os.path.isdir(os.path.join(base, d))}
    expected = set(_TIER_FIXTURE_EXPECTATIONS)
    for extra in sorted(on_disk - expected):
        fails.append(f"fixture {extra}: on disk but absent from the expectation set (exercises nothing)")
    for missing in sorted(expected - on_disk):
        fails.append(f"fixture {missing}: in the expectation set but not on disk")
    for name in sorted(on_disk & expected):
        fixture_dir = os.path.join(base, name)
        plans = sorted(f for f in os.listdir(fixture_dir) if _is_plan_filename(f))
        if not plans:
            fails.append(f"fixture {name}: no GODOT_SCENE_PLAN.md or GODOT_SCENE_PLAN_<slug>.md")
            continue
        state = os.path.join(fixture_dir, "TASK_STATE.md")
        state_text = _read_verbatim(state) if os.path.isfile(state) else ""
        want = _TIER_FIXTURE_EXPECTATIONS[name]
        # A bare string means every plan in the directory reaches that verdict; a dict
        # names the verdict PER PLAN, which is the only way to express the multi-plan
        # case the floor requires (one waiver line per plan, so one plan waived and its
        # sibling blocked from the SAME TASK_STATE.md).
        want = {plan: want for plan in plans} if isinstance(want, str) else want
        for extra in sorted(set(plans) - set(want)):
            fails.append(f"fixture {name}: plan {extra} on disk but absent from the expectation set")
        for missing in sorted(set(want) - set(plans)):
            fails.append(f"fixture {name}: expectation names plan {missing}, not on disk")
        for plan in sorted(set(plans) & set(want)):
            actual = _tier_gate_verdict(
                _read_verbatim(os.path.join(fixture_dir, plan)), state_text, plan)
            if actual != want[plan]:
                fails.append(f"fixture {name}/{plan}: expected {want[plan]!r}, got {actual!r}")
    return (not fails, fails)


def check_godot_tier_floor_variants():
    """[ADR-0119] The floor exists with its variants and every command it names cites it.

    The consumer list is DERIVED from the floor block (intersected with real command
    basenames), not hardcoded, so a fourth variant added to the floor is checked for a
    citation automatically. The three explicit variant-presence assertions stay above
    it: a purely derived list would silently shrink when a variant is DELETED instead
    of failing.

    Command bodies are reached through _command_body, which handles both the flat and
    the folder-shaped source layouts. The superseded direct read raised
    FileNotFoundError on a folder-shaped command, and a raise reads as infrastructure
    noise rather than as a failing invariant.
    """
    fails = []
    floors = read(p("wos", "platform-runtime-floors.md"))
    if "## Godot tier-declaration floor" not in floors:
        return (False, ["wos/platform-runtime-floors.md: no Godot tier-declaration floor section"])
    block = floors.split("## Godot tier-declaration floor", 1)[1].split("\n## ", 1)[0]
    for variant in ("implement-approved-slice variant", "slice-closure variant", "task-close variant"):
        if variant not in block:
            fails.append(f"wos/platform-runtime-floors.md: tier-declaration floor missing the {variant}")
    consumers = sorted({"implement-approved-slice", "slice-closure", "task-close"}
                       | {n for n in _command_basenames() if f"{n} variant" in block})
    for cmd in consumers:
        body = _command_body(cmd)
        if body is None:
            fails.append(f"commands/{cmd}: neither a flat .md nor a folder-shaped SKILL.md exists")
        elif "Godot tier-declaration" not in body:
            fails.append(f"commands/{cmd}: does not cite the Godot tier-declaration floor")
    return (not fails, fails)


# The routes a commit-evidence home may name. `branch-commit --apply` is the human
# route and the only command in this repository that can create a commit.
# `ref-attested` is the autonomous route (D-5): the runner points a quarantine ref at
# the run's work and the floor accepts that ref as the evidence. A home satisfies this
# check by ROUTING to either; routing to neither is what fails.
# NOT a catalogue of the routes that exist: this is the set EVERY home must route to.
# `_routes_missing_from` requires all of them, so adding a member here makes all three
# homes fail until each is edited. A route that applies only in some contexts does not
# belong in this tuple.
COMMIT_EVIDENCE_ROUTES = ("branch-commit --apply", "ref-attested")

# A route counts only where the text ROUTES to it, never where it merely says the words.
# Matching the bare token lets a sentence that DENIES the route satisfy the check:
# measured 2026-08-07, a home with its routing stripped and the sentence "This floor has
# nothing to do with ref-attested evidence" appended still passed.
#
# Not hypothetical for this migration, in either direction. `commands/task-close.md`
# ALREADY carries "the `branch-commit --apply` fallback below is unreachable here" for the
# human route, and the ADR authorizing the second route must state where `ref-attested`
# does NOT apply, so the prose rewriting these homes will carry sentences that name a
# route precisely in order to exclude it.
#
# The anchor is the phrasing all three homes already use, `route to <route>`. THIS IS THE
# CONTRACT FOR THE PROSE: a home offering the autonomous route must route to it in those
# words, the same way it routes to `branch-commit --apply` today. Bounded to a single
# sentence (`[^.\n]`) so a match cannot wander past a sentence boundary into an unrelated
# clause.
# The span between the routing verb and the route may not contain ANOTHER route. A plain
# `[^.\n]{0,40}` window respects only a period, and a clause boundary is not always a
# period: measured 2026-08-07, `commands/task-close.md` reads "... route to
# `branch-commit --apply`) and `ref-attested` ...", where the verb belongs to the FIRST
# route inside a parenthetical and the second sits outside it. The window bridged the
# closing paren, so a home routing ONLY to `branch-commit --apply` satisfied the
# `ref-attested` requirement, which is the single-route wording this check exists to
# keep out. The per-character lookahead stops the span at the first route it meets, so a
# route counts only when its own verb reaches it with nothing else in between.
#
# The verb is case-insensitive via a SCOPED `(?i:...)` group, never a blanket
# `re.IGNORECASE` on the pattern. Normative prose starts sentences with the imperative
# ("Route to `ref-attested` when no human turn exists"), and a lowercase-only verb failed
# that while the error message accused correct prose of not routing. A blanket flag would
# also loosen the ROUTE TOKEN, accepting `REF-ATTESTED`, which is the opposite of what a
# contract phase is for: the verb's spelling is prose, the route's spelling is the
# contract.
_ANY_ROUTE = "|".join(re.escape(route) for route in COMMIT_EVIDENCE_ROUTES)
ROUTES_TO_RE = {
    route: re.compile(
        r"(?i:rout(?:e|es|ing)\s+to\s+)(?:(?!" + _ANY_ROUTE + r")[^.\n]){0,40}?" + re.escape(route)
    )
    for route in COMMIT_EVIDENCE_ROUTES
}


def _routes_missing_from(text: str) -> list[str]:
    """The routes `text` does not route to. Empty means the home carries both.

    ALL, not ANY, and the difference is the whole point of this check's final form.
    Slice 04 asserted ANY so that the prose could be rewritten without the suite going
    red in between; that is the expand half of expand-migrate-contract and it is loose
    on purpose. With the prose on disk the looseness runs the other way: a later edit
    could drop `ref-attested` from a home and stay green, which is exactly the
    single-route wording creeping back.
    """
    return [route for route, pattern in ROUTES_TO_RE.items() if not pattern.search(text)]


def check_commit_evidence_routes_to_apply():
    """[ADR-0084, ADR-0133, ADR-0197] Every floor home keeps both routes and their owners.

    The original assertion was that every home routes to `branch-commit --apply`, because a
    home routing anywhere else is circular by construction: it tells the reader to go get a
    commit and names a path that cannot produce one. That was the live defect the --apply mode
    was built to fix, and it stays a failure.

    ADR-0133 adds a second route rather than replacing the first, so BOTH are required per
    home. An external execution layer with no human turn can reach its driver-owned branch or
    `ref-attested`; an attended run reaches `--apply`. ADR-0197 makes the subject part of the
    contract: direct-use `autonomous-run` owns neither external route and records bounded
    deferral instead.

    This is the contract half of expand-migrate-contract, and it is deliberately stricter than
    what shipped one slice ago. The expand half asserted ANY, so that the prose could be
    rewritten without the suite going red in between. With the prose on disk, ANY would let a
    later edit drop `ref-attested` from a home and stay green, which is the single-route wording
    creeping back. ALL is what closes that door.

    Asserted PER HOME, never by grepping the whole file. A file-wide search passes while one
    of the three homes silently loses its routing, which is the failure mode the assertion
    exists to catch.
    """
    fails = []
    floors = read(p("wos", "closure-floors.md"))
    marker = "## Commit-evidence floor"
    if marker not in floors:
        return (False, ["wos/closure-floors.md: no Commit-evidence floor section"])
    block = floors.split(marker, 1)[1].split("\n## ", 1)[0]
    for variant in ("implement-approved-slice variant", "slice-closure variant"):
        head = f"### {variant}"
        if head not in block:
            fails.append(f"wos/closure-floors.md: commit-evidence floor missing the {variant}")
            continue
        body = block.split(head, 1)[1].split("\n### ", 1)[0]
        missing = _routes_missing_from(body)
        if missing:
            fails.append(
                f"wos/closure-floors.md: the {variant} of the commit-evidence floor does not "
                f"`route to` {', '.join(f'`{route}`' for route in missing)}; every home routes to "
                f"BOTH classes, so a human turn and an unattended run each have a reachable path"
            )
        if "Direct-use `autonomous-run`" not in body or "bounded deferral" not in body:
            fails.append(
                f"wos/closure-floors.md: the {variant} of the commit-evidence floor does not "
                "assign bounded deferral to direct-use `autonomous-run` (ADR-0197)"
            )
    # The third home. Scoped to the floor bullet, not the whole file: task-close names
    # `branch-commit --apply` in several places, so a file-wide search stays green while the
    # floor itself loses its routing. A mutation proved that exact miss before this was scoped.
    # The delimiter matches a bullet at ANY indentation because ADR-0134 turned the floors into
    # sub-bullets: anchoring on the top-level `\n- **` silently widened this slice from 647 to
    # 2071 chars, swallowing five sibling floors and restoring the fail-open this scoping exists
    # to prevent.
    body = _command_body("task-close")
    if body is None:
        fails.append("commands/task-close: neither a flat .md nor a folder-shaped SKILL.md exists")
    else:
        head = "**Commit-evidence floor"
        if head not in body:
            fails.append("commands/task-close: no commit-evidence floor bullet")
        else:
            bullet = re.split(r"\n\s*- \*\*", body.split(head, 1)[1], maxsplit=1)[0]
            missing = _routes_missing_from(bullet)
            if missing:
                fails.append(
                    "commands/task-close: the commit-evidence floor bullet does not `route to` "
                    f"{', '.join(f'`{route}`' for route in missing)}; every home routes to BOTH "
                    f"classes, so a human turn and an unattended run each have a reachable path"
                )
            if "Direct-use `autonomous-run`" not in bullet or "deferred: pending human commit" not in bullet:
                fails.append(
                    "commands/task-close: the commit-evidence floor bullet does not assign "
                    "bounded deferral to direct-use `autonomous-run` (ADR-0197)"
                )
    return (not fails, fails)


SUBSTRATE_BLOCK = "commands/_shared/substrate-write-protocol.md"


def check_substrate_emit_teaches_full_schema():
    """[ADR-0034] The shared block's hand-rolled emit teaches every field the validator wants.

    The block offers two paths: `scripts/emit-substrate-write.sh` (preferred, ADR-0110) and a
    hand-rolled `jq -nc` for hosts where the helper does not fit. 29 commands cite the block,
    so a field dropped from that `jq` call teaches 29 commands to emit a line the validator
    rejects, and the damage shows up much later as an unreadable audit trail rather than as a
    failing command.

    Measured 2026-08-10 before this check existed: the block was already correct (14 of 14),
    the helper was verified end-to-end against the validator, and the normal-flow error rate
    had fallen from 66 per cent in June to 7 per cent in August. So this guards a healthy
    surface rather than fixing a broken one: the field list is the coupling nobody was
    watching, between a validator and a code block in prose.
    """
    validator = "scripts/verify-log-validator.py"
    for path in (validator, SUBSTRATE_BLOCK):
        if not os.path.isfile(p(path)):
            return (False, [f"{path}: missing"])

    src = open(p(validator), encoding="utf-8").read()
    required = set(re.findall(r'obj\.get\("([a-z_]+)"\)', src)) | {"ts"}
    # A field the validator declares optional is read when present and valid when absent
    # (ADR-0224: `sha_scope`, which only the digest fallback writes). Demanding it of the
    # hand-rolled emit would teach every section-scope write to carry a field it does not need.
    om = re.search(r"^OPTIONAL_FIELDS = \{([^}]*)\}", src, re.M)
    if om:
        required -= set(re.findall(r'"([a-z_]+)"', om.group(1)))

    block = open(p(SUBSTRATE_BLOCK), encoding="utf-8").read()
    m = re.search(r"jq -nc(.*?)>> \.wos/VERIFICATION_LOG\.jsonl", block, re.S)
    if not m:
        return (False, [
            f"{SUBSTRATE_BLOCK}: no hand-rolled `jq -nc ... >> .wos/VERIFICATION_LOG.jsonl` "
            f"emit to check. If the manual path was removed on purpose, remove this check "
            f"with it rather than leaving it matching nothing"
        ])

    emitted = set(re.findall(r'(\w+):\s*(?:\$|\(|null|")', m.group(1)))
    missing = sorted(required - emitted)
    if missing:
        return (False, [
            f"{SUBSTRATE_BLOCK}: the hand-rolled emit omits {missing}, which "
            f"{validator} requires. Every command following this path would emit an invalid "
            f"line, and the failure surfaces later as a broken audit trail rather than here"
        ])
    return (True, [])


def check_declared_event_in_taxonomy():
    """[ADR-0034] Every `event=` a command declares emitting is in the canonical taxonomy.

    The taxonomy lives in `scripts/verify-log-validator.py` and the validator rejects an
    unknown event, but nothing checked the COMMANDS, so a command could declare emitting an
    invented event and the defect only surfaced later as an invalid audit line. Measured
    2026-08-10: two commands did exactly that (`orphan_detected`, `fleet-merge-orphan-refused`)
    while `task-init-fleet` had already documented the right pattern, a canonical event plus
    an additive field.

    A NEGATIVE mention is not an emission. `task-init-fleet` says "there is NO
    `event=orphan_scan`" to teach the pattern, and a naive grep counts that as a violation:
    it did, in the first run of this check's own baseline. Text preceding the match is
    scanned for a negation so documenting a non-event stays legal.
    """
    validator = "scripts/verify-log-validator.py"
    if not os.path.isfile(p(validator)):
        return (False, [f"{validator}: missing; the taxonomy has no home"])
    src = open(p(validator), encoding="utf-8").read()
    m = re.search(r"^EVENTS\s*=\s*\{(.*?)\}", src, re.S | re.M)
    if not m:
        return (False, [f"{validator}: no EVENTS set to check against"])
    events = set(re.findall(r'"([a-z_-]+)"', m.group(1)))

    negation = re.compile(r"\b(no|not|never|without)\b[^.]{0,70}$", re.I)
    fails = []
    for path in sorted(glob.glob(p("commands", "*.md")) + glob.glob(p("commands", "*", "SKILL.md"))):
        text = open(path, encoding="utf-8").read()
        for hit in re.finditer(r"`?event=([a-z_][a-z0-9_-]*)`?", text):
            name = hit.group(1)
            if name in events:
                continue
            before = text[max(0, hit.start() - 90):hit.start()]
            if negation.search(before):
                continue
            fails.append(
                f"{path}: declares `event={name}`, which is not in the {len(events)}-event "
                f"canonical taxonomy in {validator}. The validator rejects it, so every line "
                f"this command emits lands invalid. Use a canonical event plus an additive "
                f"field, the pattern task-init-fleet documents"
            )
    return (not fails, fails)


def check_canonical_not_loaded_when_views_exist():
    """[ADR-0138] Nothing orders the canonical file loaded once per-consumer views exist.

    When a topic is split into generated views, the canonical file stops being the thing
    anyone loads: it becomes the source the generator reads. Any surviving `load
    `wos/X.md`` instruction then sends a reader to the whole 32k file the split existed to
    avoid, and it is invisible to every other guard because the file still exists, so
    check-doc-sync resolves it happily.

    This is not hypothetical. ADR-0138 migrated the three closure commands to their views on
    2026-08-10 and left `WORKFLOW_OPERATING_SYSTEM.md:60` ordering the monolith loaded
    UNCONDITIONAL. An adversarial pass found it hours later. Nothing in the repo reads the
    spec, so a contradiction between the spec and every command it governs had no way to
    surface.

    Scope is deliberately narrow: it fires only for a canonical file that HAS views, so it
    stays silent for the topics the spec tells the agent to read directly.
    """
    views = {}
    for path in glob.glob(p("wos", "*.*.md")):
        stem = os.path.basename(path).split(".")[0]
        canonical = p("wos", f"{stem}.md")
        if os.path.isfile(canonical):
            views.setdefault(canonical, []).append(path)
    # Fail closed on an empty subject (EX-B1). This used to return a bare pass, so running the
    # script from any directory but the repo root reported clean over zero files: the glob was
    # relative to the cwd, matched nothing, and "no canonical file has views" reads identical to
    # "every canonical file with views is correct". Measured 2026-08-30 from a parent directory:
    # this check and unconditional-load-declared both said PASS with no subject at all.
    if not views:
        return (False, [f"wos/: no canonical file with generated views found; this check lost "
                        f"its subject rather than the subject becoming clean"])

    surfaces = [p("WORKFLOW_OPERATING_SYSTEM.md")] + sorted(
        glob.glob(p("commands", "*.md")) + glob.glob(p("commands", "*", "SKILL.md"))
    )
    generator = "scripts/build-closure-floor-views.py"

    fails = []
    for canonical, view_list in sorted(views.items()):
        # Case-insensitive: commands write "Load `wos/X.md`" at the start of a bullet and the
        # spec writes "load `wos/X.md`" mid-sentence. A case-sensitive pattern caught the spec
        # and missed every command, which a mutation exposed. Same defect as the first version
        # of highest-adr-claim, twice in one day: a guard's regex narrower than the prose it
        # polices reports clean.
        # Match the RELATIVE path, which is the only form prose ever uses. Until
        # 2026-09-18 this escaped `canonical`, which `p()` returns absolute, so the
        # pattern searched every command and the spec for a `/Users/.../wos/x.md`
        # string that appears in none of them. The check was inert from the day it
        # shipped: the 2026-08-10 regression it was written to catch, the spec
        # ordering the 32k monolith loaded, passes it. Found by writing its first
        # mutation fixture, which refused to bite.
        rel = os.path.relpath(canonical, _repo())
        pattern = re.compile(r"\bload `" + re.escape(rel) + r"`", re.I)
        for path in surfaces:
            if not os.path.isfile(path):
                continue
            for n, line in enumerate(open(path, encoding="utf-8"), 1):
                if pattern.search(line):
                    fails.append(
                        f"{os.path.relpath(path, _repo())}:{n}: orders `{rel}` loaded, but that file has "
                        f"{len(view_list)} generated per-consumer view(s) and is now only the "
                        f"generator's source. Point at the consumer's view instead (the "
                        f"command's `unconditional-loads` names it); loading the canonical "
                        f"file re-imposes the whole cost the split removed. Generated by "
                        f"{generator}"
                    )
    return (not fails, fails)


CLOSURE_CANONICAL = "wos/closure-floors.md"
CLOSURE_CONSUMERS = ("task-close", "slice-closure", "implement-approved-slice")


def _closure_preamble(text):
    for sec in re.split(r"(?m)^(?=## )", text):
        if sec.startswith("## ") and sec.split("\n", 1)[0][3:].strip().startswith("When to load"):
            return sec
    return ""


def _closure_effective(text, consumer, from_view):
    """The normative content a consumer must apply, as an ordered list of hashes.

    Whitespace-normalized so re-flowing is free, but every wording change shows up. The
    preamble is included because it is NOT scaffolding: it carries the G3 safeguard that
    every consumer must obey. Leaving it out made a hand-run version of this validator blind
    to two of three seeded mutations, since the file's first `SHALL` lives there.
    """
    def norm(t):
        return hashlib.sha256(re.sub(r"\s+", " ", t).strip().encode()).hexdigest()[:16]

    rows = [("(preamble)", norm(_closure_preamble(text)), "")]
    for sec in re.split(r"(?m)^(?=## )", text):
        if not sec.startswith("## "):
            continue
        name = sec.split("\n", 1)[0][3:].split("(")[0].strip()
        if name.startswith("When to load"):
            continue
        parts = re.split(r"(?m)^(?=### )", sec)
        if from_view:
            variants = parts[1:]
        else:
            variants = [
                p for p in parts[1:]
                if p.split("\n", 1)[0][4:].strip().startswith(f"{consumer} variant")
            ]
        variants = [
            v for v in variants
            if not (v.split("\n", 1)[1] if "\n" in v else "").strip().startswith("None.")
        ]
        if not variants:
            continue
        rows.append((name, norm(parts[0]), "".join(norm(v) for v in variants)))
    return rows


DESIGN_GROUNDING_COMMANDS = (
    "api-contract-review",
    "backend-system-design",
    "feature-library-scout",
    "frontend-system-design",
    "graphql-contract-review",
    "implementation-plan",
    "stack-recommend",
)


def check_design_grounding_coverage():
    """[ADR-0043] Commands that DECIDE against an external contract carry the design gate.

    The execution gate (`shared:reference-grounding`) refuses an edit when the contract is
    uncaptured, and it sits on 4 commands, all of which write code. But the decision about
    WHICH external contract to build against is made earlier, by the commands listed here, and
    none of them carried any grounding gate: measured 2026-08-10, all seven cite REFERENCES.md
    in prose and zero enforced anything.

    That ordering is the failure ADR-0043 came from. The NEVER-READ session implemented against
    a streaming API from memory; by the time the execution gate could refuse, the plan naming
    that API was already approved. The design gate does not refuse, because refusing to produce
    a plan is the wrong response to a missing reference. It MARKS, so the gap is visible while
    the plan is still cheap to change.

    The list is explicit rather than inferred. Inferring "is a design command" from prose would
    be the same brittle guessing the phrasing-vocabulary problem already demonstrates; a
    hand-kept list is honest about being hand-kept.
    """
    marker = "shared:reference-grounding-design"
    fails = []
    for name in DESIGN_GROUNDING_COMMANDS:
        path = f"commands/{name}.md"   # relative: it is also the failure label
        if not os.path.isfile(p(path)):
            path = f"commands/{name}/SKILL.md"
        if not os.path.isfile(p(path)):
            fails.append(f"commands/{name}: listed for the design gate but the command is gone")
            continue
        if marker not in open(p(path), encoding="utf-8").read():
            fails.append(
                f"{path}: decides against external contracts but does not carry "
                f"`<!-- {marker} -->`. Without it the first thing to notice an uncaptured "
                f"contract is the execution gate, mid-slice, after the plan was approved"
            )
    return (not fails, fails)


NORMATIVE_MARKER = re.compile(r"\b(SHALL|MUST|REQUIRED|routes? to|refuse|is invalid)\b", re.I)


def check_omitted_variant_carries_no_rule():
    """[ADR-0138] A variant the generator drops as empty carries no normative text.

    `check_closure_view_equivalence` asks whether the view matches what the canonical file
    says for that consumer, and it decides "empty variant" with `startswith("None.")`, the
    SAME predicate `scripts/build-closure-floor-views.py:49` uses. Two sides sharing a
    predicate always agree, so that check can never question the predicate itself: it
    confirms the generator did what the checker would have done.

    This is the independent half. It does not ask whether the two agree; it asks whether the
    text they agreed to DROP contains a rule. Write `None. But the runner SHALL emit X` and
    the equivalence check stays green while `SHALL emit X` disappears from every view.

    Measured 2026-08-10: five variants are dropped today, carrying 21 to 98 chars each, all
    of it prose explaining WHY the variant is empty ("this floor has one home, task-close").
    Zero carry a marker. The guard exists so that stays true.
    """
    if not os.path.isfile(p(CLOSURE_CANONICAL)):
        return (False, [f"{CLOSURE_CANONICAL}: missing"])

    fails = []
    text = open(p(CLOSURE_CANONICAL), encoding="utf-8").read()
    for sec in re.split(r"(?m)^(?=## )", text):
        if not sec.startswith("## "):
            continue
        floor = sec.split("\n", 1)[0][3:].split("(")[0].strip()
        if floor.startswith("When to load"):
            continue
        for part in re.split(r"(?m)^(?=### )", sec)[1:]:
            head = part.split("\n", 1)[0][4:].strip()
            body = part.split("\n", 1)[1].strip() if "\n" in part else ""
            if not body.startswith("None."):
                continue
            tail = body[len("None."):]
            found = sorted({m.group(1).upper() for m in NORMATIVE_MARKER.finditer(tail)})
            if found:
                fails.append(
                    f"{CLOSURE_CANONICAL}: the `{head}` of `{floor}` starts with `None.` so "
                    f"the generator drops it from that consumer's view, but the text after it "
                    f"carries {found}. That rule would vanish from the view while "
                    f"closure-view-equivalence stays green, because it shares the "
                    f"`None.` predicate with the generator. Move the rule out of a dropped "
                    f"variant, or stop marking the variant empty"
                )
    return (not fails, fails)


def check_closure_view_equivalence():
    """[ADR-0138] Each generated closure view carries exactly its consumer's normative text.

    This file gates task and slice closure, so the failure mode of a bad split is a floor
    that silently stops firing. The property asserted is not "the files match" but "the
    normative text this consumer must apply is identical to the canonical file's", compared
    hash by hash, floor by floor, preamble included.
    """
    if not os.path.isfile(p(CLOSURE_CANONICAL)):
        return (False, [f"{CLOSURE_CANONICAL}: missing"])
    canonical = open(p(CLOSURE_CANONICAL), encoding="utf-8").read()

    fails = []
    for consumer in CLOSURE_CONSUMERS:
        path = f"wos/closure-floors.{consumer}.md"
        if not os.path.isfile(p(path)):
            fails.append(f"{path}: missing; run scripts/build-closure-floor-views.py")
            continue
        want = _closure_effective(canonical, consumer, from_view=False)
        got = _closure_effective(open(p(path), encoding="utf-8").read(), consumer, from_view=True)
        if want == got:
            continue
        want_floors = [r[0] for r in want]
        got_floors = [r[0] for r in got]
        missing = [f for f in want_floors if f not in got_floors]
        extra = [f for f in got_floors if f not in want_floors]
        if missing:
            fails.append(
                f"{path}: floor(s) {missing} are in {CLOSURE_CANONICAL} for this consumer "
                f"but absent from the view. A dropped floor is a closure gate that stops "
                f"firing without anything saying so"
            )
        if extra:
            fails.append(f"{path}: floor(s) {extra} appear in the view but not for this consumer")
        for a, b in zip(want, got):
            if a != b:
                which = "shared body" if a[1] != b[1] else "variant"
                fails.append(
                    f"{path}: the {which} of `{a[0]}` differs from {CLOSURE_CANONICAL}; the "
                    f"view is generated, so edit the canonical file and re-run "
                    f"scripts/build-closure-floor-views.py"
                )
                break
    return (not fails, fails)


# Phrasings that make a load unconditional. The first version listed three, and an adversarial
# pass got a real 109-per-cent-of-ceiling load past every gate with "Always read X in full,
# with no exceptions; skipping it is not permitted" - imperative, obviously unconditional, and
# using none of the three. Four of five plain imperative phrasings passed.
#
# This stays a VOCABULARY, not semantics, and therefore stays incomplete by construction: the
# check greps for known ways of saying "always", it does not understand the sentence. What it
# buys is that the obvious phrasings are covered, so evading it now takes deliberate wording
# rather than ordinary English. The residual is recorded in ADR-0137 Consequences.
UNCONDITIONAL_PROSE = re.compile(
    r"UNCONDITIONAL"
    r"|load is unconditional"
    r"|MANDATORY,? not conditional"
    r"|\bthis load is MANDATORY"
    r"|\balways read\b"
    r"|\bmust (?:be )?read\b"
    r"|\bSHALL read\b"
    r"|\bread .{0,40}\bin full\b"
    r"|\bwith no exceptions\b"
    r"|\bon every (?:run|invocation|slice|task)\b",
    re.I,
)
REINJECTION_CAP_CHARS = 20000  # 5,000 tokens, the documented per-skill re-injection cap


def _declared_unconditional_loads(text):
    """Parse `unconditional-loads:` from a command's frontmatter, inline or block form."""
    # `[ \t]*`, never `\s*`: `\s` matches newlines, so a greedy run would swallow the first
    # `- item` of the block form and silently report a short list. The generated SKILL.md
    # files use exactly that block form, so this bug would have blinded the check on half
    # the corpus while still passing.
    m = re.search(r"^[ \t]*unconditional-loads:[ \t]*(.*)$", text, re.M)
    if not m:
        return None
    inline = m.group(1).strip()
    if inline.startswith("["):
        return [x.strip().strip("`") for x in inline.strip("[]").split(",") if x.strip()]
    out = []
    for line in text[m.end():].split("\n"):
        s = line.strip()
        if s.startswith("- "):
            out.append(s[2:].strip().strip("`"))
        elif s and not s.startswith("#"):
            break
    return out


def check_unconditional_load_declared():
    """[ADR-0006] A load the prose calls unconditional is declared in frontmatter.

    The Load gate measures `.claude/skills/<name>/SKILL.md` alone, so text moved into a
    topic the command then loads on EVERY run satisfies the gate while the real cost is
    unchanged. Measured 2026-08-10: task-close went from 38,656 chars to 33,872 plus a
    32,124-char unconditional topic, green at 165 per cent of the ceiling.

    The fix is NOT to interpret prose. That has no published precedent and just moves the
    target (rewrite "load X" as "load X when relevant" and nothing changes). It follows the
    pattern the harness itself uses for `paths:` in rules and for MCP schema deferral: the
    load condition is DECLARED in metadata, and this check only greps for disagreement
    between the declaration and the prose. Both directions fail, because a declaration
    nobody honours and a load nobody declares are the same defect from opposite sides.
    """
    fails = []
    surfaces = sorted(glob.glob(p("commands", "*.md")) + glob.glob(p("commands", "*", "SKILL.md")))
    # Fail closed on an empty subject (EX-B1), for the same reason as
    # canonical-not-loaded-with-views: "no command declares an unconditional load in prose" and
    # "there are no command files" produce the same clean line, and the second is a broken run.
    if not surfaces:
        return (False, [f"commands/: no command files found; this check lost its subject "
                        f"rather than the subject becoming clean"])
    for path in surfaces:
        text = open(path, encoding="utf-8").read()
        declared = _declared_unconditional_loads(text) or []
        prose_topics = set()
        for line in text.split("\n"):
            # Skip the declaration line itself. The field is NAMED `unconditional-loads`, so
            # it matches the prose pattern, and counting it made every declared topic look
            # like prose: both directions cancelled and the check passed on anything. A
            # mutation test caught this; the check was inert before it.
            if re.match(r"^[ \t]*unconditional-loads:", line):
                continue
            if UNCONDITIONAL_PROSE.search(line):
                prose_topics.update(re.findall(r"wos/[A-Za-z0-9._-]+\.md", line))

        for topic in sorted(prose_topics - set(declared)):
            fails.append(
                f"{path}: prose calls the load of `{topic}` unconditional but the frontmatter "
                f"does not declare it. Add `unconditional-loads: [{topic}]` so the real "
                f"per-invocation cost is measurable instead of inferred from wording"
            )
        # The declaration line itself names the topic, so comparing against the raw text
        # would always find it and this half of the check would never fire.
        body = "\n".join(
            l for l in text.split("\n") if not re.match(r"^[ \t]*unconditional-loads:", l)
        )
        for topic in sorted(set(declared) - prose_topics):
            # `p(topic)`, not the bare relative path: the declaration is written
            # repo-relative, so `os.path.isfile(topic)` resolved it against the
            # WORKING DIRECTORY and reported every declared topic missing when the
            # script ran from anywhere but the repo root. Latent until 2026-09-18
            # because the branch is only reached when a declaration has no matching
            # prose, which no command has today.
            if not os.path.isfile(p(topic)):
                fails.append(f"{path}: declares `{topic}`, which does not exist on disk")
            elif topic not in body:
                fails.append(
                    f"{path}: declares `{topic}` as an unconditional load but never "
                    f"references it; a declaration nobody honours inflates the measured cost"
                )
    return (not fails, fails)


def check_real_load_advisory():
    """[ADR-0116] ADVISORY: the real per-invocation load, declared inclusions counted.

    Deliberately advisory, for two reasons. Making it hard today would land red on three
    commands and force a refactor of the closure cluster in the same change, and the
    surrogation evidence says what reduces metric-gaming is MULTIPLE measures rather than one
    harder one. So this sits beside the ADR-0116 gate instead of replacing it.

    It also reports the documented 5,000-token per-skill re-injection cap, which sits well
    under the Load ceiling (it is `LOAD_TARGET_CHARS`): a skill can pass the gate and still
    lose its tail after the first compaction, and truncation keeps the start of the file.
    """
    notes = []
    for path in sorted(glob.glob(p("commands", "*.md")) + glob.glob(p("commands", "*", "SKILL.md"))):
        name = os.path.basename(os.path.dirname(path)) if path.endswith("/SKILL.md") \
            else os.path.basename(path)[:-3]
        declared = _declared_unconditional_loads(open(path, encoding="utf-8").read())
        if not declared:
            continue
        skill = p(".claude", "skills", name, "SKILL.md")
        own = os.path.getsize(skill) if os.path.isfile(skill) else 0
        extra = sum(os.path.getsize(p(t)) for t in declared if os.path.isfile(p(t)))
        total = own + extra
        if total > LOAD_CEILING_CHARS:
            notes.append(
                f"{name}: real load {total} chars ({own} skill + {extra} declared) is "
                f"{total / LOAD_CEILING_CHARS * 100:.0f} per cent of the "
                f"{LOAD_CEILING_CHARS}-char ceiling, which the gate does not see"
            )
    over_cap = []
    for skill in sorted(glob.glob(p(".claude", "skills", "*", "SKILL.md"))):
        size = os.path.getsize(skill)
        if size > REINJECTION_CAP_CHARS:
            over_cap.append(os.path.basename(os.path.dirname(skill)))
    if over_cap:
        notes.append(
            f"{len(over_cap)} of {len(glob.glob(p('.claude', 'skills', '*', 'SKILL.md')))} skills exceed "
            f"the {REINJECTION_CAP_CHARS}-char (5,000-token) re-injection cap and lose their "
            f"tail after a compaction; truncation keeps the start, and the output contract "
            f"lives at the end"
        )
    return (True, notes)


def check_wos_topic_reachable():
    """[ADR-0006] Every lazy topic is reachable from something that loads it.

    Two engine-scoped checks already assert this with narrow globs (`wos/godot-3d-*.md`,
    `wos/unity-*.md`), covering 7 of 47 topics. This generalizes the predicate to the whole
    directory, with one correction learned by measuring: the read map is NOT the only
    legitimate entry point. Commands cite topics directly, and 39 of 47 are reached that way,
    so requiring a read-map row for all of them would force about 4750 chars into the spec,
    against 1328 of headroom under ADR-0136. Reachability is the real invariant; a read-map
    row is one way to satisfy it.

    CHANGELOG.md is excluded on purpose: it records that a file was created, which is history
    rather than a live path to it. A topic whose only mention is its own birth announcement is
    exactly the orphan this check exists to find.
    """
    # `t`, not `p`: the comprehension variable would shadow the path helper it calls.
    topics = sorted(os.path.basename(t) for t in glob.glob(p("wos", "*.md")))
    if not topics:
        return (False, ["wos/: no topics found"])

    haystack = []
    for pattern in (
        "WORKFLOW_OPERATING_SYSTEM.md",
        "README.md",
        "commands/*.md",
        "commands/*/SKILL.md",
        "wos/*.md",
        "wos/bug-classes/*.md",
        "evals/scenarios/*.md",
        "scripts/*.sh",
        "scripts/*.py",
        "evals/scripts/*.py",
        "docs/adr/*.md",
    ):
        for full in glob.glob(p(pattern)):
            # the label stays repo-relative; only the read is rooted
            haystack.append(
                (os.path.relpath(full, REPO), open(full, encoding="utf-8", errors="ignore").read())
            )

    fails = []
    for topic in topics:
        ref = f"wos/{topic}"
        homes = [p for p, text in haystack if ref in text and os.path.basename(p) != topic]
        if not homes:
            fails.append(
                f"wos/{topic}: orphaned topic, not referenced from the read map, any command, "
                f"any scenario, any ADR, or any sibling topic. A lazy file nothing loads is "
                f"not lazy, it is dead: it costs maintenance and lint and never enters "
                f"context. Give it a trigger or retire it"
            )
    return (not fails, fails)


def check_task_state_template_sync():
    """[ADR-0111] The TASK_STATE template and task-init's inline structure stay identical.

    ADR-0134's sibling refactor moved the per-section annotations out of `task-init` into
    `templates/TASK_STATE.template.md` and left the 20 names inline, which created a second
    place that can drift from the first with nothing watching. Name AND order both matter:
    the order is normative (ADR-0111 puts `## Quick reanchor` first so it survives
    compaction and lands where Lost-in-the-Middle says recall is best), so a reordering is a
    regression even when every name still matches.
    """
    cmd_path = "commands/task-init.md"
    tpl_path = "templates/TASK_STATE.template.md"
    for required in (cmd_path, tpl_path):   # not `p`: that name is the path helper
        if not os.path.isfile(p(required)):
            return (False, [f"{required}: missing"])

    cmd = open(p(cmd_path), encoding="utf-8").read()
    anchor = "\n# TASK_STATE\n"
    if anchor not in cmd:
        return (False, [
            f"{cmd_path}: no `# TASK_STATE` block; the inline normative structure is the "
            f"thing this check compares against {tpl_path}"
        ])
    tail = cmd[cmd.index(anchor):]
    stop = re.search(r"\n(?:# (?!TASK_STATE)|<!-- shared:)", tail[1:])
    block = tail[: stop.start() + 1] if stop else tail

    inline = [l.strip() for l in block.split("\n") if l.startswith("## ")]
    template = [
        l.strip()
        for l in open(p(tpl_path), encoding="utf-8").read().split("\n")
        if l.startswith("## ")
    ]

    if inline == template:
        return (True, [])

    fails = []
    only_cmd = [s for s in inline if s not in template]
    only_tpl = [s for s in template if s not in inline]
    if only_cmd:
        fails.append(
            f"{cmd_path}: section(s) {only_cmd} are in the inline structure but not in "
            f"{tpl_path}; the template is what the command tells the agent to read while seeding"
        )
    if only_tpl:
        fails.append(
            f"{tpl_path}: section(s) {only_tpl} are in the template but not in the inline "
            f"structure of {cmd_path}, which is the normative list"
        )
    if not only_cmd and not only_tpl:
        for n, (a, b) in enumerate(zip(inline, template), 1):
            if a != b:
                fails.append(
                    f"same {len(inline)} sections but the order diverges at position {n}: "
                    f"{cmd_path} has {a!r}, {tpl_path} has {b!r}. Order is normative per "
                    f"ADR-0111 and `## Quick reanchor` must stay first"
                )
                break
    return (False, fails)


SPINE_OPERATING_MODE_READERS = (
    "impact-analysis",
    "decision-interview",
    "implementation-plan",
    "approve-plan",
    "implement-approved-slice",
    "implement-slice-complement",
    "slice-closure",
    "review-hard",
    "pr-package",
    "what-next",
    "sync-task-state",
    "task-close",
    "branch-commit",
)

OPERATING_MODE_READER_BULLET = "Operating mode (ADR-0008, ADR-0162)."


def check_spine_reads_operating_mode():
    """[ADR-0162] Spine readers after task-init carry the Resume notes operating-mode bullet.

    ADR-0008 already said every subsequent command reads `Operating mode:` from Resume notes.
    Scenario 08's fail mode was that task-init recorded the line and implementation-plan
    behaved as if unset. The pin is the command-level bullet, not the topic prose.
    """
    fails = []
    for name in SPINE_OPERATING_MODE_READERS:
        path = p("commands", f"{name}.md")
        if not os.path.isfile(path):
            fails.append(f"{path}: missing, so the ADR-0162 reader set cannot be checked")
            continue
        if OPERATING_MODE_READER_BULLET not in read(path):
            fails.append(
                f"commands/{name}.md: missing the ADR-0162 operating-mode reader bullet; "
                "scenario 08's mode-drift failure is a command with no rule to read Resume notes"
            )
    init_path = p("commands", "task-init.md")
    if os.path.isfile(init_path) and OPERATING_MODE_READER_BULLET in read(init_path):
        fails.append(
            "commands/task-init.md: carries the reader bullet; task-init is the writer of "
            "the Resume notes line and is not a subsequent-command reader"
        )
    plan = read(p("commands", "implementation-plan.md"))
    # ADR-0208 deleted the inline Approval log outright, so ADR-0162's exception has nothing
    # left to forbid. What ADR-0162 still requires, and what scenario 08's mode-drift failure
    # was actually about, is that a declared strict ROUTES rather than proceeding: the next
    # missing of invariants-and-non-goals, test-strategy, approve-plan. Pinning the deleted
    # sentence would fail the build for a rule that no longer has a referent.
    if "Operating mode: strict" not in plan or "invariants-and-non-goals" not in plan:
        fails.append(
            "commands/implementation-plan.md: declared strict must route to the next missing "
            "of invariants-and-non-goals, test-strategy, approve-plan (ADR-0162); without that "
            "exception a strict-marked one-field change proceeds as if unmarked"
        )
    slice_cmd = read(p("commands", "implement-approved-slice.md"))
    if "do not contain `Operating mode: strict`" not in slice_cmd:
        fails.append(
            "commands/implement-approved-slice.md: the Express attended lock must stand down "
            "when Resume notes declare strict, or the missing inline log deadlocks execution"
        )
    return (not fails, fails)


# The phrasings that would reintroduce a human turn at plan approval. Asserted as the
# ABSENCE of a small, named set rather than by trying to read intent, which is the same
# form check_apply_commits_after_display uses for the retired confirmation rule. Measured
# 2026-09-18: none of the six appears in `commands/approve-plan.md`, which is what
# ADR-0208 recorded when it removed the last stop ("contains no instruction to wait for a
# person"). The set is the natural ways to write it back, not a catalogue of every
# possible sentence, and it does not pretend to be one.
APPROVAL_WAIT_PHRASES = (
    "wait for the user",
    "wait for the maintainer",
    "wait for a human",
    "await approval",
    "ask the user to approve",
    "pause until the user",
)

# The two sentences in the spec that carry the self-running property. Kept as exact
# strings because each is the operative clause of a decision, not a paraphrase of one.
ATTENDED_CONTINUES = ("an attended session continues into it in the same turn rather "
                      "than waiting to be asked")
APPROVAL_NOT_REASON_TWO = "Approving a plan is not an instance of reason 2"


# The shape every residual mode gate took: an Artifact changes line that conditions APPLIED
# on the mode. Measured 2026-09-22 across the command tree.
MODE_GATE_RE = re.compile(r"`### Artifact changes` marks .{0,160}?`APPLIED` only (?:if|when)")

# Commands that keep a mode gate PENDING a decision, each with the reason it may be deliberate.
# An entry here is a claim the gate is under review, not that it is right; the check reports
# an entry that no longer carries the gate, so the list cannot outlive what it names.
MODE_GATE_PENDING = {
    "compact-task-memory": "the compaction is lossy, and what it drops cannot be recovered by "
                           "reading the file afterwards, which was the reversibility ADR-0199 rested on",
}


# A condition keyed on a tier NAME. After ADR-0207 the recommended pipeline records the fired
# conditions (`Escalations: none`, or the added commands) and never a tier name, so any rule
# of this shape can no longer be true.
#
# Widened 2026-09-23 (docs drift audit, gap 2). The first version read commands/ only, left
# `Strict` out, and could not see a heading or the `complexity_tier` field, so thirteen live
# lines across the spec, wos/, the templates and the stubs passed. `Strict mode` (the operating
# mode) and `Strict surface` (the ADR-0184 disqualifier) are live names and are not matched:
# only `Strict` in a tier position is.
_TIER = r"(?:Express|Standard|Disciplined|Strict)"
RETIRED_TIER_CONDITION_RE = re.compile(
    r"(?:names|is|records?|carries|identifies the task as) (?:an? )?\**(?:Express|Standard|Disciplined)\b"
    r"|pipeline (?:names|is) " + _TIER + r"\b"
    r"|(?:the|an?) " + _TIER + r"[- ]tier\b"
    r"|\b" + _TIER + r"[- ]tier\b"
    r"|\b(?:pipeline|bound) tier\b"
    r"|\btier\s*[=:]\s*`?" + _TIER + r"\b"
    r"|^#{1,6} " + _TIER + r"(?: task| tier| pipeline| path)?\s*(?:\(|$)"
    r"|\bcomplexity_tier\b"
    r"|\bTier: `?\[?" + _TIER)

# A line that records the name AS retired is history, not a condition.
RETIRED_TIER_HISTORY_RE = re.compile(
    r"retired|until 2026-|keyed on the label|used to|superseded|no longer|historical|formerly"
    r"|ADR-0207|the old name|replaced|is gone")


def check_no_condition_on_a_retired_tier_name():
    """[ADR-0207] No live document gates behavior on a tier name the pipeline no longer writes.

    ADR-0207 (2026-09-16) retired the tier labels and made `task-init` record the conditions
    that fired, as `Escalations:`. A rule written as "when the pipeline names Express" could
    not be true after that, and nothing noticed. On 2026-09-22 two such rules were live:
    `implement-approved-slice` routed the last slice to `branch-commit --apply` only when the
    pipeline "names Express", and `what-next` re-checked "the Express tier". The last-slice
    commit kept happening in scenario 137 only because the model read `Escalations: none` as
    the old name. A more literal model would not have committed.

    The scan covers every live document (`_live_doc_files`), not only commands: the same audit
    found the tier names as headings in wos/workflow-shapes.md, as `complexity_tier` in the
    stubs, and as pass criteria in the eval scenarios. It still fails closed when commands/ is
    empty, because the commands are the one surface that must be present for the rule to mean
    anything.

    A mention that says the name is retired is not a condition and is not matched: the pattern
    requires the name in a conditional position (names, is, records, the ... tier, a heading).
    """
    fails = []
    if not (glob.glob(p("commands", "*.md")) or glob.glob(p("commands", "*", "SKILL.md"))):
        return (False, ["commands/: no command files found; this check lost its subject"])
    for path in _live_doc_files():
        for n, line in enumerate(read(path).split("\n"), 1):
            m = RETIRED_TIER_CONDITION_RE.search(line)
            if m and not RETIRED_TIER_HISTORY_RE.search(line):
                fails.append(
                    f"{os.path.relpath(path, _repo())}:{n}: gates behavior on the retired tier name "
                    f"({m.group(0).strip()!r}). The pipeline records `Escalations:` since ADR-0207, so this "
                    f"condition cannot be true; key it on the escalations instead")
    return (not fails, fails)


def check_task_memory_written_in_every_mode():
    """[ADR-0199, ADR-0215] No command writes task or project memory PROPOSED because of the mode.

    ADR-0199 removed the ADR-0001 mode gate: a command writes its task-memory files and marks
    them APPLIED in every mode. It stated its reach, "the gate reached 57 command-tree files
    plus the spec", and the change was taken as done. On 2026-09-22 the gate was still live in
    eight commands, `task-init` among them (the command ADR-0199 says it shrank), and the spec
    and the FAQ still described it as current policy. Nothing measured the residue, which is how
    a decision that declared its full reach left part of it behind.

    WHAT IS NOT A MODE GATE, and stays: a `<!-- PROPOSED by <command>: ... -->` block a command
    stages in a section it does not own, for the owner to promote (ADR-0034). That is ownership,
    it holds in Agent mode too, and ADR-0199 preserved it. This check matches only the mode-
    conditioned Artifact changes line, so it cannot mistake one for the other.

    One command keeps the gate, compact-task-memory, because its write is lossy (ADR-0220); it is
    the single entry in MODE_GATE_PENDING, with the reason. self-critique-and-revise left that list
    when ADR-0220 settled it. The same rule stated in other words, and in documents other than the
    commands, is check_no_mode_gate_phrasing's job.
    """
    fails = []
    files = sorted(glob.glob(p("commands", "*.md")) + glob.glob(p("commands", "*", "SKILL.md")))
    if not files:
        return (False, ["commands/: no command files found; this check lost its subject"])
    still_gated = set()
    for path in files:
        name = os.path.basename(os.path.dirname(path)) if path.endswith("/SKILL.md") \
            else os.path.basename(path)[:-3]
        if MODE_GATE_RE.search(read(path)):
            still_gated.add(name)
            if name not in MODE_GATE_PENDING:
                fails.append(
                    f"commands/{name}.md: conditions APPLIED on the mode in its Artifact changes "
                    f"line. ADR-0199 writes task memory APPLIED in every mode; a section the "
                    f"command does not own gets a PROPOSED block for its owner instead (ADR-0034)")
    for name in sorted(set(MODE_GATE_PENDING) - still_gated):
        fails.append(
            f"MODE_GATE_PENDING names `{name}`, which no longer carries a mode gate; remove the "
            f"entry so the pending list cannot outlive what it names")
    # The two documents a reader meets first stopped describing the gate as current.
    for rel, dead in (("WORKFLOW_OPERATING_SYSTEM.md",
                       "The PROPOSED-by-default write policy (Ask/Plan modes; see ADR-0001) means"),
                      ("docs/FAQ.md", "(PROPOSED-by-default writes; full artifact content emitted inline")):
        path = p(*rel.split("/"))
        if os.path.isfile(path) and dead in read(path):
            fails.append(f"{rel}: describes the removed ADR-0001 write gate as current policy again")
    return (not fails, fails)


# Every other way the tree has written the retired ADR-0001 gate. MODE_GATE_RE matches one
# sentence shape, and ADR-0215 said so ("matches one sentence shape"); the 2026-09-22 audit then
# found sixteen commands and twenty-five document lines using other shapes, none of which it saw.
# Each alternative below is a phrasing that was on disk, not a guess at one. "In Ask or Plan
# mode" opening a sentence is task-close's old reopen line, which the lowercase form missed.
MODE_GATE_PHRASE_RE = re.compile(
    r"`?APPLIED`? only (?:if|when)[^.]{0,80}\bAgent\b"
    r"|(?i:proposed)`?\s*\(?(?:in |for )?(?:Ask|Plan)\b"
    r"|`?APPLIED`?\s*\(?(?:in )?Agent\b(?: mode)?\)?,? (?:or |and )?`?PROPOSED`?\s*(?:otherwise|\(?(?:in )?(?:Ask|Plan)\b)"
    r"|\b(?:PROPOSED|APPLIED|persisted|marked)\b[^.]{0,40}\bper (?:editor )?mode\b"
    r"|[Dd]efault(?: for this command)?:\s*`PROPOSED`"
    r"|(?<![\w-])PROPOSED[- ]by[- ]default"
    r"|\b[Ii]n (?:Ask|Plan)(?: or (?:Ask|Plan))? mode[^.]{0,60}`?PROPOSED\b"
    r"|\b(?:Ask|Plan)\s*\(PROPOSED\)|APPLIED[- ]by[- ]default in Agent"
    r"|\bthen `approve-proposed`|ready for `approve-proposed`"
    r"|Run now:`?\s*(?:is\s*)?`?/?approve-proposed\b")

# A line that names the gate in order to say it is gone.
MODE_GATE_HISTORY_RE = re.compile(
    r"retired|removed|superseded|replaces|ADR-0199|ADR-0215|no longer|used to|until 2026-|gone"
    r"|now gets")

# The one command that keeps the gate (ADR-0220), and its own scenario.
MODE_GATE_KEPT_FILES = ("commands/compact-task-memory.md",
                        "evals/scenarios/20-compact-task-memory-multi-slice.md")

# Files where the same words gate something that is not a memory write, each with why.
MODE_GATE_OUT_OF_SCOPE = {
    "commands/task-workspace.md":
        "the gated act is `git worktree add` in the user's repository, not a write to task or "
        "project memory (ADR-0215, Neutral consequences; ADR-0222 keeps it)",
}

# Files where only the lines naming one act may keep a mode condition: (marker, why). ADR-0222
# made task-close's outcome append, knowledge note and reopen move APPLIED in every mode, so the
# file is read like any other except the worktree teardown, which runs git in the product repo.
MODE_GATE_OUT_OF_SCOPE_LINES = {
    "commands/task-close.md":
        ("git worktree", "the teardown runs `git worktree remove` in the product repository, a "
                         "command rather than a substrate write, so it keeps Agent mode (ADR-0222)"),
}


def check_no_mode_gate_phrasing():
    """[ADR-0199, ADR-0220] No live document states the retired mode gate in any of its phrasings.

    check_task_memory_written_in_every_mode reads one sentence shape in the commands. The gate
    was also written as "PROPOSED (Ask) or APPLIED (Agent)", "default: `PROPOSED` in Ask/Plan",
    "PROPOSED or APPLIED per editor mode", "APPLIED in Agent mode, PROPOSED otherwise",
    "PROPOSED-by-default", and "then `approve-proposed`" as the next step, in the spec, wos/, the
    FAQ, the templates and the eval scenarios. None of those was read, which is how the audit of
    2026-09-22 found sixteen commands and twenty-five document lines still stating it after two
    ADRs had declared it gone.

    Allowed: compact-task-memory, the one command that keeps the gate (ADR-0220), and any line
    naming it or ADR-0220; a line that names the gate to say it was retired; the files in
    MODE_GATE_OUT_OF_SCOPE, where the same words gate an act that is not a memory write; and in
    the files of MODE_GATE_OUT_OF_SCOPE_LINES, only the lines carrying that file's marker (the
    task-close worktree teardown, ADR-0222). A `<!-- PROPOSED by <command>` ownership block
    (ADR-0034) is not matched by any alternative.
    """
    fails = []
    files = _live_doc_files()
    if not files:
        return (False, ["no live document found; this check lost its subject"])
    for path in files:
        rel = os.path.relpath(path, _repo()).replace(os.sep, "/")
        if rel in MODE_GATE_KEPT_FILES or rel in MODE_GATE_OUT_OF_SCOPE:
            continue
        line_marker = MODE_GATE_OUT_OF_SCOPE_LINES.get(rel, (None, None))[0]
        for n, line in enumerate(read(path).split("\n"), 1):
            m = MODE_GATE_PHRASE_RE.search(line)
            if not m or MODE_GATE_HISTORY_RE.search(line):
                continue
            if line_marker and line_marker in line:
                continue
            if "compact-task-memory" in line or "ADR-0220" in line:
                continue
            fails.append(
                f"{rel}:{n}: states the retired mode gate ({m.group(0).strip()!r}). Task and project "
                f"memory is written APPLIED in every mode (ADR-0199); only compact-task-memory keeps "
                f"the gate (ADR-0220)")
    return (not fails, fails)


# Loose artifact totals (docs drift audit, gap 6). Only a number inside a count marker is
# reconciled, so the audit found 23 lines whose totals had gone stale in plain prose: "53
# commands", "the 7 deferred commands", "CI: 4 jobs", five fleets where there were seven. The
# fix the ADR-0029 guard already offers is the marker; this makes a total written without one
# fail, in the files reconcile-counts.sh reads, so the marker is used or the number goes.
COUNT_SCAN_ROOT_FILES = ("AGENTS.md", "README.md", "WORKFLOW_OPERATING_SYSTEM.md", "WORKFLOW_DEMO.md",
                         "CONTRIBUTING.md", "CLAUDE.md", "CODE_OF_CONDUCT.md", "SECURITY.md",
                         "COMMAND_PROMPT_STUBS.md", "docs/FAQ.md", "docs/MIGRATION.md", "evals/README.md")
_NUMBER_WORDS = {w: i for i, w in enumerate(
    "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen "
    "sixteen seventeen eighteen nineteen twenty".split())}
# A total of one of the large sets: a two-digit-or-more number is a claim about the whole set.
LOOSE_TOTAL_RE = re.compile(
    r"(?<![\w.:/#-])(\d{2,4}) (?:flat |folder-shaped |persona |eval |registered |official |shipped )?"
    r"(commands?|command files|wos topics|topic files|ADRs|scenarios|bug-class templates|skills)\b")
# The small sets, claimed as a whole ("the seven fleet commands", "all 9 persona commands").
LOOSE_SMALL_TOTAL_RE = re.compile(
    r"\b(?:the|all|of the|across the) (\d{1,2}|" + "|".join(_NUMBER_WORDS) + r") "
    r"(fleet commands|fleets|persona commands|folder-shaped persona commands)\b", re.I)
# The derived sets (docs drift audit, D-11). Each has a count marker kind computed from the tree:
# closure floors from their `On missing evidence:` lines, the task-memory and fleet-substrate files
# from the substrate-peers matrix, the VERIFICATION_LOG field schema from the validator, the
# closure write pattern from its shared block, a spec template's sections from its headings, the
# runtime gates and personas from the command files, the task shapes from wos/workflow-shapes.md,
# the spine manifest from evals/spine-evals.json, and the history readers from frontmatter.
_N = r"(?<![\w.:/#-])(?:\d{1,2}|" + "|".join(_NUMBER_WORDS) + r")"
LOOSE_DERIVED_TOTAL_RE = re.compile(
    _N + r"(?: of the " + _N + r")? (?:closure )?floors\b"
    r"|" + _N + r" (?:task-memory|fleet-substrate) files\b"
    r"|" + _N + r"-field (?:schema|required set)\b"
    r"|" + _N + r"[- ]sections? (?:TASK_STATE(?:\.md)? )?(?:write )?pattern\b"
    r"|canonical " + _N + r" sections\b"
    r"|" + _N + r" sections of the [A-Z_]+ template\b"
    r"|" + _N + r" (?:runtime gates|runtime-verify commands)\b"
    r"|" + _N + r" task shapes\b"
    r"|" + _N + r" (?:specialist )?persona commands\b"
    r"|manifest elects " + _N + r" scenarios\b|" + _N + r" scenarios the manifest elects\b"
    r"|" + _N + r" commands (?:that )?declar\w* `?history\b"
    r"|Multi-repo aware \(" + _N + r" commands\)", re.I)
LOOSE_JOBS_RE = re.compile(r"\b(\d{1,2}|" + "|".join(_NUMBER_WORDS) + r") (?:CI )?jobs\b", re.I)
LOOSE_TOTAL_HISTORY_RE = re.compile(
    r"\bhad\b|\bwas\b|\bwere\b|at the time|when (?:this|it) was written|[Mm]easured (?:on )?20\d\d"
    r"|as of|\bthen\b|grew|from \d+ to|retired|until 20\d\d|superseded|dogfood 20\d\d-\d\d-\d\d")


SENTENCE_SPLIT_RE = re.compile(r"(?<=[.;!?])\s+(?=[A-Z`(\[*])")


def check_artifact_totals_are_markers():
    """[ADR-0029, docs drift audit gap 6] A total of an artifact set is a count marker, not a loose number.

    Three shapes, each a claim about a whole set that goes stale when the set changes: a number of
    ten or more before commands, topics, ADRs, scenarios, bug-class templates or skills; "the N fleet
    commands" or "the N persona commands" in digits or words; and "N jobs" on a line about CI, which
    is compared with the jobs .github/workflows/lint.yml actually declares, since no marker kind
    counts jobs. A number inside `<!-- count:KIND -->` is skipped: reconcile-counts.sh owns it.

    Since D-11 of the same audit it also reads the command sources (flat, folder-shaped and
    commands/_shared/) and a fourth shape: a hand-written total of a set a marker kind derives from
    the tree (LOOSE_DERIVED_TOTAL_RE: closure floors, task-memory and fleet-substrate files, the log
    field schema, the closure write pattern, spec template sections, runtime gates, task shapes,
    persona commands, the spine manifest, the history readers, the multi-repo-aware commands). A
    frontmatter `description:` line is exempt from that shape: it is emitted verbatim as the skill
    description, where a marker would show.

    Out of scope, and why: an evals/README.md scenario row records what its scenario measured when
    it was written, and a line that dates or narrates a past number ("had", "was", "measured
    2026-...") is history. CHANGELOG.md, ROADMAP.md and the ADR index are history by construction.
    """
    fails = []
    marker = re.compile(r"<!-- count:[a-z-]+ -->\d+<!-- /count -->")
    files = [p(*r.split("/")) for r in COUNT_SCAN_ROOT_FILES] + sorted(glob.glob(p("wos", "*.md")))
    files += sorted(glob.glob(p("commands", "*.md")) + glob.glob(p("commands", "*", "SKILL.md"))
                    + glob.glob(p("commands", "_shared", "*.md")))
    files = [f for f in files if os.path.isfile(f)]
    if not files:
        return (False, ["no count-scan file found; this check lost its subject"])
    jobs = None
    workflow = p(".github", "workflows", "lint.yml")
    if os.path.isfile(workflow):
        body = read(workflow)
        if "\njobs:\n" in body:
            jobs = len(re.findall(r"(?m)^  [a-z][a-z0-9_-]*:\s*$", body.split("\njobs:\n", 1)[1]))
    for path in files:
        rel = os.path.relpath(path, _repo()).replace(os.sep, "/")
        for n, line in enumerate(read(path).split("\n"), 1):
            if rel == "evals/README.md" and re.match(r"\| \d+ \|", line):
                continue
            # History is exempt per sentence, not per line: a paragraph is one line, and one
            # "was" anywhere in it used to hide every current total beside it.
            kept = [x for x in SENTENCE_SPLIT_RE.split(line) if not LOOSE_TOTAL_HISTORY_RE.search(x)]
            if not kept:
                continue
            text = re.sub(r"`[^`]*`", "", marker.sub("", " ".join(kept)))
            for m in LOOSE_TOTAL_RE.finditer(text):
                fails.append(f"{rel}:{n}: states a total ({m.group(0)!r}) as a loose number; wrap it in a "
                             f"`<!-- count:KIND -->` marker so reconcile-counts.sh keeps it true, or drop it")
            for m in LOOSE_SMALL_TOTAL_RE.finditer(text):
                fails.append(f"{rel}:{n}: states a total ({m.group(0)!r}) as a loose number; wrap it in a "
                             f"`<!-- count:fleet-commands -->` or `<!-- count:personas -->` marker, or drop it")
            if re.match(r"description:", line):
                continue
            for m in LOOSE_DERIVED_TOTAL_RE.finditer(text):
                fails.append(f"{rel}:{n}: states a total ({m.group(0)!r}) of a set the tree defines; wrap it in "
                             f"the count marker whose kind computes that set (scripts/reconcile-counts.sh "
                             f"disk_count), or drop the number")
            if jobs is not None and re.search(r"\bCI\b|lint\.yml", line):
                for m in LOOSE_JOBS_RE.finditer(text):
                    raw = m.group(1).lower()
                    said = int(raw) if raw.isdigit() else _NUMBER_WORDS[raw]
                    if said != jobs:
                        fails.append(f"{rel}:{n}: says CI runs {said} jobs; .github/workflows/lint.yml "
                                     f"declares {jobs}")
    return (not fails, fails)


# Dash-prefixed tokens a command names that are not ITS flags: another tool's option, each with
# where it comes from. The flags table is for the command's own gated modes (docs drift audit,
# gap 8), and a token here is not one, so it needs no row.
NON_COMMAND_FLAGS = {
    "--version": "a binary's version probe (autonomous-readiness, problem-framing)",
    "--no-verification": "trufflehog's offline mode (code-context-map)",
    "--db-url": "the Supabase CLI (db-context-supabase)",
    "--linked": "the Supabase CLI (db-context-supabase)",
    "--local": "the Supabase CLI (db-context-supabase)",
    "--headless": "the Godot CLI (godot-runtime-verify)",
    "--stat": "git diff (pr-feedback-ingest, state-reconcile)",
    "--ready": "gh pr (pr-package names it to forbid it)",
    "--force": "git (task-close and task-workspace name it to forbid it)",
    "--revert": "compute-task-outcome.py (task-close)",
    "--residual": "compute-task-outcome.py (review-hard)",
}


def _stub_flag_rows():
    """COMMAND_PROMPT_STUBS.md `## Optional flags at a glance`: command -> the flags its row lists."""
    path = p("COMMAND_PROMPT_STUBS.md")
    if not os.path.isfile(path):
        return None
    section = read(path).split("## Optional flags at a glance", 1)
    if len(section) < 2:
        return None
    rows = {}
    for line in section[1].split("\n## ", 1)[0].split("\n"):
        m = re.match(r"\|\s*((?:`[a-z0-9-]+`(?:,\s*)?)+)\s*\|\s*(.*?)\s*\|", line)
        if not m or "Command" in line:
            continue
        flags = set(re.findall(r"`(--[a-z][a-z0-9-]*)", m.group(2)))
        for name in re.findall(r"`([a-z0-9-]+)`", m.group(1)):
            rows.setdefault(name, set()).update(flags)
    return rows


def check_command_flags_in_stub_table():
    """[docs drift audit, gap 8] Every flag a command accepts has a row in the stubs flag table, and back.

    The table says "A command not listed here has no optional dash-prefixed flags" and "This table
    is hand-maintained". Nothing compared it with the commands, which is how performance-budget
    carried `--mobile` and `--godot-mobile` as if they were its flags with no row, and a reader of
    the table could not know they existed (C32).

    A backticked `--flag` in a command is fine when the table lists it for that command, when it
    is another command's flag and that command is named on the same line (a cross-reference), or
    when NON_COMMAND_FLAGS records it as another tool's option. The reverse holds too: a flag the
    table lists for a command must appear in that command, or the row outlived the flag.
    """
    rows = _stub_flag_rows()
    if rows is None:
        return (False, ["COMMAND_PROMPT_STUBS.md: no `## Optional flags at a glance` table to check against"])
    if not rows:
        return (False, ["COMMAND_PROMPT_STUBS.md: the flag table has no rows; the check lost its subject"])
    owner = {}
    for name, flags in rows.items():
        for flag in flags:
            owner.setdefault(flag, set()).add(name)
    fails = []
    seen = {}
    for path in _command_files():
        name = _command_name_from_path(path)
        rel = os.path.relpath(path, _repo()).replace(os.sep, "/")
        for n, line in enumerate(read(path).split("\n"), 1):
            for flag in re.findall(r"`(--[a-z][a-z0-9-]*)", line):
                seen.setdefault(name, set()).add(flag)
                if flag in rows.get(name, set()) or flag in NON_COMMAND_FLAGS:
                    continue
                if any(re.search(r"\b" + re.escape(o) + r"\b", line) for o in owner.get(flag, ()) if o != name):
                    continue
                fails.append(f"{rel}:{n}: names `{flag}` as a flag, and COMMAND_PROMPT_STUBS.md lists no such "
                             f"flag for `{name}`; add its row, or say whose option it is")
    for name, flags in sorted(rows.items()):
        if _command_path(name) is None:
            continue  # an unknown command in a table is the registry lint's finding, not this one
        for flag in sorted(flags - seen.get(name, set())):
            fails.append(f"COMMAND_PROMPT_STUBS.md: lists `{flag}` for `{name}`, and commands/{name} never "
                         f"names it; the row outlived the flag, or the command lost it")
    return (not fails, fails)


INSTALLER = "scripts/sync-workflow-slash-commands.sh"
# A line may name the no-op flag as long as it says it is one.
WITH_SKILLS_EXCUSED_RE = re.compile(
    r"compatib|optional|still parses|no-op|changes nothing|by default|\(default", re.I)


def _installer_flags():
    """(accepted, documented): the flags the installer's parser takes, and the ones usage() lists."""
    body = read(p(*INSTALLER.split("/")))
    usage = body.split("usage() {", 1)[1].split("\n}\n", 1)[0] if "usage() {" in body else ""
    documented = set(re.findall(r"(?m)^\s+(--[a-z][a-z-]*)", usage))
    loop = body.split('while [[ $# -gt 0 ]]; do', 1)[1] if 'while [[ $# -gt 0 ]]; do' in body else ""
    loop = loop.split("\ndone", 1)[0]
    accepted = set()
    for arm in re.findall(r"(?m)^\s+((?:-[-a-z]+(?:=\*)?\|?)+)\)", loop):
        accepted.update(f.replace("=*", "") for f in arm.split("|") if f.startswith("--"))
    accepted.discard("--help")  # usage() is what --help prints; it need not list itself
    return accepted, documented


def check_installer_flags_documented():
    """[docs drift audit, gap 11] The installer's flags are named the way its parser takes them.

    Skills sync by default since 2026-07-18, and `--with-skills` still parses and changes nothing.
    Eight lines kept presenting it as the switch that turns skills on, including the shared
    substrate protocol and two scripts' own help text, and nothing compared the installer's
    `--help` with what the docs tell people to type.

    Three assertions. A line outside the installer that names `--with-skills` says it is kept for
    compatibility or that skills sync by default. Every `sync-workflow-slash-commands.sh --flag`
    written in a document or a script is a flag the parser accepts. Every flag the parser accepts
    is listed by usage(), so `--help` is the whole surface.
    """
    if not os.path.isfile(p(*INSTALLER.split("/"))):
        return (False, [f"{INSTALLER}: missing, so the documented flags cannot be checked"])
    accepted, documented = _installer_flags()
    if not accepted:
        return (False, [f"{INSTALLER}: no flag parsed from its argument loop; the check lost its subject"])
    fails = [f"{INSTALLER}: accepts `{f}` and usage() does not list it, so --help hides it"
             for f in sorted(accepted - documented)]
    files = set(_live_doc_files())
    files.update(glob.glob(p("scripts", "*.sh")) + glob.glob(p("scripts", "*.py")))
    if os.path.isfile(p("ROADMAP.md")):
        files.add(p("ROADMAP.md"))
    invocation = re.compile(r"sync-workflow-slash-commands\.sh((?:\s+--?[a-z][a-z-]*(?:[= ][^\s`'\"]+)?)+)")
    for path in sorted(files):
        rel = os.path.relpath(path, _repo()).replace(os.sep, "/")
        if rel == INSTALLER:
            continue
        for n, line in enumerate(read(path).split("\n"), 1):
            if "--with-skills" in line and not WITH_SKILLS_EXCUSED_RE.search(line):
                fails.append(f"{rel}:{n}: presents `--with-skills` as the switch for skills; they sync by "
                             f"default and the flag is kept only for compatibility")
            for m in invocation.finditer(line):
                for flag in re.findall(r"(?<!\S)(--[a-z][a-z-]*)", m.group(1)):
                    if flag not in accepted:
                        fails.append(f"{rel}:{n}: tells the reader to run the installer with `{flag}`, "
                                     f"which its parser rejects as an unknown option")
    return (not fails, fails)


# The documents that tell a reader where a default install puts the skills (ADR-0228). Each
# wraps the roots it names in a skill-roots span, so the check reads the claim itself and not
# whatever path a nearby sentence happens to mention.
SKILL_ROOT_DOCS = ("README.md", "docs/FAQ.md", "docs/MIGRATION.md")
SKILL_ROOTS_SPAN_RE = re.compile(r"<!-- skill-roots -->(.*?)<!-- /skill-roots -->", re.S)
SKILL_ROOT_RE = re.compile(r"~/\.[a-z][a-z-]*/skills")


def check_default_skill_roots_agree():
    """[ADR-0228] The default skill roots named in the installer usage, README, FAQ and MIGRATION agree.

    The default install stopped writing ~/.cursor/skills on 2026-09-23 because Cursor 3.17.8 and
    later read ~/.agents/skills natively and listed every Fhorja skill twice. Before that change
    six places promised ~/.cursor/skills as a default, and nothing compared them with each other
    or with the installer. The installer test pins that `--help` names the roots a default run
    actually writes; this check pins that the three documents name the same set.

    Two assertions. Each document carries a skill-roots span, and every span names exactly the
    roots on the usage line `Default skill roots:`. No line of those documents calls another
    skill root a default.
    """
    inst = p(*INSTALLER.split("/"))
    if not os.path.isfile(inst):
        return (False, [f"{INSTALLER}: missing, so the default skill roots cannot be compared"])
    body = read(inst)
    usage = body.split("usage() {", 1)[1].split("\n}\n", 1)[0] if "usage() {" in body else ""
    m = re.search(r"(?m)^Default skill roots: (.*)$", usage)
    want = set(SKILL_ROOT_RE.findall(m.group(1))) if m else set()
    if not want:
        return (False, [f"{INSTALLER}: usage() has no `Default skill roots:` line naming a root; "
                        f"the check lost its subject"])
    fails = []
    for rel in SKILL_ROOT_DOCS:
        path = p(*rel.split("/"))
        if not os.path.isfile(path):
            fails.append(f"{rel}: missing")
            continue
        text = read(path)
        spans = SKILL_ROOTS_SPAN_RE.findall(text)
        if not spans:
            fails.append(f"{rel}: carries no skill-roots span, so the default skill roots it states "
                         f"are compared with nothing")
        for span in spans:
            got = set(SKILL_ROOT_RE.findall(span))
            if got != want:
                fails.append(f"{rel}: its skill-roots span names {sorted(got)} as the default skill roots; "
                             f"the installer usage names {sorted(want)}")
        for n, line in enumerate(text.split("\n"), 1):
            if "by default" not in line:
                continue
            for root in set(SKILL_ROOT_RE.findall(line)) - want:
                fails.append(f"{rel}:{n}: calls `{root}` a default skill root; the installer usage "
                             f"names {sorted(want)}")
    return (not fails, fails)


def check_mcp_routing_view_matches():
    """[B32] wos/mcp-capability-routing.md is a byte copy of the canonical shared block.

    task-init stopped inlining the MCP routing block on 2026-09-22 to get off the ADR-0116
    Load ceiling (78 chars of headroom left), and reads this copy lazily instead, because
    commands/_shared/ does not ship on an install and wos/ does. A copy nobody compares is
    a rule that silently stops matching the three commands still carrying it inline.
    """
    canon, view = p("commands", "_shared", "mcp-capability-routing.md"), p("wos", "mcp-capability-routing.md")
    for path in (canon, view):
        if not os.path.isfile(path):
            return (False, [f"{os.path.relpath(path, _repo())}: missing"])
    body = read(view)
    rule = "\n---\n\n"
    if rule not in body:
        return (False, ["wos/mcp-capability-routing.md: the header rule is gone, so the copy cannot be located"])
    if body.split(rule, 1)[1] != read(canon):
        return (False, ["wos/mcp-capability-routing.md: differs from commands/_shared/mcp-capability-routing.md "
                        "below the rule; copy the canonical block over it, so task-init reads the rule the "
                        "other three commands carry"])
    return (True, [])


def check_projects_ignore_in_creators():
    """[ADR-0223, scenario 141] Both commands that create projects/ carry the self-ignoring rule.

    After an install, task-init creates projects/ in the product repository, and until
    2026-09-23 nothing there ignored it. The rule is one shared block; lint compares a
    declared marker byte for byte but never notices a command that stops declaring it, and
    task-init's ignore check lives outside the block. This asserts all three.
    """
    msgs = []
    canon = p("commands", "_shared", "projects-ignore.md")
    if not os.path.isfile(canon):
        return (False, ["commands/_shared/projects-ignore.md: missing"])
    block = read(canon)
    for needle in ("`projects/.gitignore`", "the single line `*`", "Never edit the repository's own `.gitignore`"):
        if needle not in block:
            msgs.append(f"commands/_shared/projects-ignore.md: no longer says {needle}")
    for name in ("task-init", "project-bootstrap"):
        path = p("commands", f"{name}.md")
        if not os.path.isfile(path) or "<!-- shared:projects-ignore -->" not in read(path):
            msgs.append(f"commands/{name}.md: creates projects/ but does not carry the projects-ignore block")
    ti = p("commands", "task-init.md")
    if os.path.isfile(ti) and "check-ignore -q projects/<client>__<project>/" not in read(ti):
        msgs.append("commands/task-init.md: the ADR-0223 ignore check on an existing projects/ is gone")
    return (not msgs, msgs)


ONE_SLICE_ROUTE_NEEDLES = (
    ("Route: one-slice", "the line that records the route and its evidence"),
    ("attended", "condition 1: the route is for an attended run"),
    ("Operating mode: strict", "condition 1: a declared strict rules the route out"),
    ("at most two files", "condition 2"),
    ("Locked decisions` stays empty", "condition 3"),
    ("Depends-on: none", "the slice field the route fixes"),
    ("Status: approved", "the slice field the route fixes"),
    ("Work complexity: LOW", "the slice field the route fixes"),
    ("check-doc-sync.sh --against HEAD", "the check that replaces the plan review"),
    ("## Approval log", "the first lock signal implement-approved-slice reads"),
    ("plan APPROVED", "the second lock signal; implement-approved-slice refuses when only one exists"),
    ("check-plan-coverage.sh", "rule 5 of the coverage checker, the route's mechanical conditions"),
    ("Run now: implement-approved-slice", "the handoff that skips implementation-plan and approve-plan"),
)


def check_one_slice_route():
    """[ADR-0225, scenario 144] The one-slice route writes both lock signals and its check runs.

    The route removes the blinded plan review from a one-sentence change to at most two named
    files. What makes that safe is written in three commands, and each half fails silently
    without the other: task-init must write BOTH signals the attended lock reads (the first
    draft of the route wrote only the Approval log line, and implement-approved-slice refuses
    on one), implement-approved-slice must run `check-doc-sync.sh --against HEAD` at inline
    close and route its exit 1, and autonomous-run must not read a route line as an approval,
    because the route is for attended runs. The lint must run the mode too, or the check that
    replaced the review runs only when a model remembers it.
    """
    msgs = []
    ti = p("commands", "task-init.md")
    if not os.path.isfile(ti):
        return (False, ["commands/task-init.md: missing, so the one-slice route has no home"])
    m = re.search(r"\*\*One-slice route \(ADR-0225\)\.\*\*(.*)", read(ti))
    if not m:
        return (False, ["commands/task-init.md: no one-slice route bullet (ADR-0225)"])
    for needle, why in ONE_SLICE_ROUTE_NEEDLES:
        if needle not in m.group(1):
            msgs.append(f"commands/task-init.md: the one-slice route no longer names {needle!r}, {why}")
    ias = p("commands", "implement-approved-slice.md")
    body = read(ias) if os.path.isfile(ias) else ""
    r = re.search(r"\*\*Renumber check on the one-slice route \(ADR-0225\)\.\*\*(.*)", body)
    if not r or "check-doc-sync.sh --against HEAD" not in r.group(1):
        msgs.append("commands/implement-approved-slice.md: does not run check-doc-sync.sh --against HEAD "
                    "at inline close on the one-slice route, so nothing replaces the review it skipped")
    else:
        for target in ("implement-slice-complement", "implementation-plan"):
            if f"`{target}`" not in r.group(1):
                msgs.append(f"commands/implement-approved-slice.md: the renumber check no longer routes "
                            f"to `{target}` on exit 1")
    if "implement only when BOTH" not in body:
        msgs.append("commands/implement-approved-slice.md: the attended lock no longer requires both signals")
    ar = p("commands", "autonomous-run.md")
    if not os.path.isfile(ar) or "A `one-slice route` line is not that entry" not in read(ar):
        msgs.append("commands/autonomous-run.md: reads a one-slice route line as the approval an "
                    "unattended run needs; the route is attended only")
    lint = p("scripts", "lint-commands.sh")
    if not os.path.isfile(lint) or '"$DOC_SYNC_SCRIPT" --against HEAD' not in read(lint):
        msgs.append("scripts/lint-commands.sh: does not run check-doc-sync.sh --against HEAD")
    return (not msgs, msgs)


def check_agent_directive_copies_match():
    """[B17, ADR-0189] The agent directive has three copies and they say the same thing.

    templates/AGENT_DIRECTIVE.template.md is what a user pastes; AGENTS.md and CLAUDE.md carry it
    for this repository. Nothing compared them, so an edit to one was an edit to one. AGENTS.md
    must hold the template's block byte for byte. CLAUDE.md must hold its first paragraph: the
    rest of that file is maintainer memory, it adds a measurement note after the paragraph, and
    the public tree does not ship it, so its absence is not a failure.
    """
    tpl = p("templates", "AGENT_DIRECTIVE.template.md")
    if not os.path.isfile(tpl):
        return (False, ["templates/AGENT_DIRECTIVE.template.md: missing"])
    parts = read(tpl).split("\n---\n")
    if len(parts) < 3 or not parts[1].strip():
        return (False, ["templates/AGENT_DIRECTIVE.template.md: the directive is no longer fenced by two --- lines"])
    block = parts[1].strip("\n")
    first = block.split("\n\n", 1)[0]
    msgs = []
    agents = p("AGENTS.md")
    if not os.path.isfile(agents) or block not in read(agents):
        msgs.append("AGENTS.md: does not carry the directive block of templates/AGENT_DIRECTIVE.template.md "
                    "byte for byte; copy the block, or change both in one edit")
    claude = p("CLAUDE.md")
    if os.path.isfile(claude) and first not in read(claude):
        msgs.append("CLAUDE.md: does not carry the directive's first paragraph from "
                    "templates/AGENT_DIRECTIVE.template.md")
    return (not msgs, msgs)


def check_output_blocks_name_their_fields():
    """[scenario 137, 125, 08] The shared Handoff and Artifact changes blocks name what they require.

    Both blocks used to say only "follow the spec". On 2026-09-22, isolated runs against Opus 5.5
    dropped `Work complexity:` from three of eight Handoffs, a minimal-mode run wrote "written" where
    a label belongs, and one run said it formatted its refusal from the command file alone. The
    Handoff is what an external consumer parses fail-closed (ADR-0169), so the four lines are stated
    where every command carries them. This asserts the canonical blocks still say so; lint's
    shared-block drift check carries them into all commands.
    """
    fails = []
    checks = [
        (("commands", "_shared", "handoff-body.md"),
         ["fenced `text` block", "`Run now:`", "`Mode:`", "`Work complexity:`", "`Reason:`", "on a stop and on a refusal too"],
         "no longer names the four Handoff lines, so a run that does not reread the spec drops one"),
        (("commands", "_shared", "artifact-changes-default.md"),
         ["Every listed file carries one of those three tokens", "in Lean output too"],
         "no longer requires a label on every listed file, so Lean output drops it"),
    ]
    for parts, needles, why in checks:
        path = p(*parts)
        rel = "/".join(parts)
        if not os.path.isfile(path):
            fails.append(f"{rel}: missing")
            continue
        body = read(path)
        missing = [n for n in needles if n not in body]
        if missing:
            fails.append(f"{rel}: {why} (missing {', '.join(repr(m) for m in missing)})")
    return (not fails, fails)


def check_workflow_root_scripts_ship():
    """[ADR-0218] A script a command resolves against the workflow root ships there.

    On an install the workflow root is the installed docs directory, and it holds only the
    scripts in SHIPPED_SCRIPTS. A command that says "resolve `scripts/x` against the
    WORKFLOW ROOT" for a script outside that list sends the model to a file that is never
    there on an install, and the step it guards is skipped. Measured 2026-09-22: the
    outcome helper and the ASI06 ingest scan were both named by commands and shipped by
    nothing. Reads every such promise in the commands and asserts each script is listed.

    One direction only. A shipped script no command resolves this way is dead weight,
    not a silent skip, and the install test already runs every shipped script.
    """
    fails = []
    sync = p("scripts", "sync-workflow-slash-commands.sh")
    if not os.path.isfile(sync):
        return (False, ["scripts/sync-workflow-slash-commands.sh: missing, so the payload cannot be checked"])
    m = re.search(r"^SHIPPED_SCRIPTS=\((.*)\)$", read(sync), re.M)
    shipped = set(m.group(1).split()) if m else set()
    promise = re.compile(
        r"[Rr]esolve `scripts/([\w.-]+)` against the WORKFLOW ROOT"
        r"|`scripts/([\w.-]+)` \(resolved against the WORKFLOW ROOT")
    promised = 0
    for path in sorted(glob.glob(p("commands", "*.md")) + glob.glob(p("commands", "*", "SKILL.md"))):
        for n, line in enumerate(read(path).split("\n"), 1):
            for mm in promise.finditer(line):
                promised += 1
                name = mm.group(1) or mm.group(2)
                if name not in shipped:
                    fails.append(
                        f"{os.path.relpath(path, _repo())}:{n}: resolves scripts/{name} against the "
                        "workflow root, and SHIPPED_SCRIPTS does not ship it, so on an install the "
                        "step it guards finds nothing")
    if promised == 0:
        fails.append("no command resolves a script against the workflow root; the scan found "
                     "nothing to check, which is not the same as every promise being kept")
    return (not fails, fails)


def check_outcome_ledger_is_written():
    """[ADR-0217] Every command that runs the outcome helper appends what it prints.

    `compute-task-outcome.py` computes a line and prints it; it never opens the ledger. On
    2026-09-22 `approve-plan` said the plan_review line was appended "via" the helper, and a
    run against Opus 5.5 reported that append APPLIED on the helper's exit 0 while no
    OUTCOMES.jsonl existed. So every invocation line in a command must carry the append
    (`>> projects/...OUTCOMES.jsonl`), and the helper must stay in the install payload, or
    the three commands call a script that is not there on any install that is not a clone.

    Fails on an empty scan too: zero invocations found means the pattern stopped matching,
    not that every invocation is correct. It asserts the instruction, not the obedience,
    which only a rerun of scenario 137 read against the disk measures.
    """
    fails = []
    files = sorted(glob.glob(p("commands", "*.md")) + glob.glob(p("commands", "*", "SKILL.md")))
    invocations = 0
    for path in files:
        for n, line in enumerate(read(path).split("\n"), 1):
            if "python3 scripts/compute-task-outcome.py" not in line:
                continue
            invocations += 1
            if not re.search(r">>\s*projects/\S*OUTCOMES\.jsonl", line):
                fails.append(
                    f"{os.path.relpath(path, _repo())}:{n}: runs compute-task-outcome.py without "
                    "appending its output to OUTCOMES.jsonl; the helper only prints, so its exit 0 "
                    "is not a write")
    if invocations == 0:
        fails.append("no command invokes `python3 scripts/compute-task-outcome.py`; the scan "
                     "found nothing to check, which is not the same as every append being present")
    sync = p("scripts", "sync-workflow-slash-commands.sh")
    if not os.path.isfile(sync):
        fails.append("scripts/sync-workflow-slash-commands.sh: missing, so the install payload cannot be checked")
    else:
        m = re.search(r"^SHIPPED_SCRIPTS=\((.*)\)$", read(sync), re.M)
        if not m or "compute-task-outcome.py" not in m.group(1).split():
            fails.append("scripts/sync-workflow-slash-commands.sh: compute-task-outcome.py left "
                         "SHIPPED_SCRIPTS, so on an install the outcome ledger is never written")
    return (not fails, fails)


def check_memory_consume_path():
    """[ADR-0214] The memory consume path is wired, and stays wired.

    Four rounds of research in August 2026 (about 6.3M subagent tokens) concluded that
    Fhorja's memory defect is the moment of CONSUMPTION, not storage, and that "the fix is
    to wire what exists, not to build a new artifact". The round confirmed five concrete
    defects by hand. On 2026-09-22 one had been fixed and four had not, a month later, and
    nothing in the tree would have said so. This asserts the four, one clause each.

    1. `task-init` does not READ the project's REFERENCES.md: it only writes a pointer to it,
       and that file had grown to 676 KB, roughly 79,000 tokens in a default read of its
       first 2,000 lines, paid on every task-init to produce one link.
    2. `task-init` resolves `rank-learnings.sh` against the WORKFLOW root, so the LEARNINGS
       consume step works on an install and not only on a clone, and names its absence.
    3. `impact-analysis` reads prior analyses of the same code in the same project, filtered
       by a grep on the files in scope: 292 of them sat on disk with no command told to read
       them.
    4. `memory-lint` treats Tags as optional, as ADR-0071 made it. `required` flagged every
       entry that predates the field as malformed.
    Plus the installer half of 2: `rank-learnings.sh` ships in the runtime payload.

    Substring assertions on the load-bearing clause, the same shape as
    check_bare_commit_tree_proof. They bound how each fix comes UNDONE in the obvious
    wording; they do not prove the agent obeys the instruction, which only a run measures.
    """
    fails = []
    checks = [
        (("commands", "task-init.md"), "check that it EXISTS and link to it; do NOT read it here",
         "reads REFERENCES.md again instead of only linking to it; that file grows with every "
         "capture and task-init only writes a pointer to it"),
        (("commands", "task-init.md"), "Resolve `scripts/rank-learnings.sh` against the WORKFLOW ROOT",
         "no longer resolves the learnings ranker against the workflow root, so the LEARNINGS "
         "consume step fails silently on every install that is not a clone"),
        (("commands", "impact-analysis.md"), "Prior analyses in this project (ADR-0214)",
         "no longer reads prior analyses of the same code; they sit on disk and no command "
         "is told to consult them"),
        (("scripts", "memory-lint.sh"), 'check_learning_field "Tags" value-only',
         "treats Tags as required again, against ADR-0071, which made it optional"),
        (("scripts", "sync-workflow-slash-commands.sh"), "SHIPPED_SCRIPTS=(rank-learnings.sh",
         "no longer ships rank-learnings.sh in the runtime payload, so task-init has no ranker "
         "to run on an install"),
    ]
    for parts, needle, why in checks:
        path = p(*parts)
        rel = "/".join(parts)
        if not os.path.isfile(path):
            fails.append(f"{rel}: missing, so this part of the consume path cannot be checked")
            continue
        if needle not in read(path):
            fails.append(f"{rel}: {why} (missing {needle!r})")
    return (not fails, fails)


def check_cwe_mapping_allowed():
    """[ADR-0213] No bug-class template maps to a CWE MITRE forbids mapping to.

    The library is described as CWE-grounded, and on 2026-09-21 twelve of its 81 templates
    mapped to an ID MITRE tells mappers not to use. Two were `Prohibited`, whose own text
    reads "This CWE ID must not be used to map to real-world vulnerabilities", and in ten
    of the twelve the flagged ID was the template's ONLY one, so there was no valid
    mapping beside it.

    FAIL on Prohibited, WARN on Discouraged, and the split is MITRE's own. Prohibited is
    categorical: the entry is a quality issue with no direct security implication, and no
    review makes it fit. Discouraged says a lower-level child would be better, which is a
    judgment about precision rather than a refusal, and `CWE-400` on `n-plus-one-query`
    still communicates. Failing the build over the second class would force six rewrites
    on a schedule this check does not get to set.

    OFFLINE, against `evals/cwe-mapping-guidance.json`, extracted from the MITRE catalogue
    with its version and date recorded in the file. Reading cwe.mitre.org from a check
    would make the build depend on a third party's uptime and would silently change verdict
    when the catalogue moves; a versioned list changes verdict only when someone
    regenerates it, which is a commit a reader can see.

    WHAT THIS DOES NOT DO: only the two refusing values are stored, so an ID in neither
    list is not asserted to be `Allowed`. It could be absent because the catalogue moved
    on. The check is a floor under known-bad mappings, not a statement that the rest are
    right for the weakness they describe.
    """
    guidance = p_json = p("evals", "cwe-mapping-guidance.json")
    if not os.path.isfile(guidance):
        return (False, ["evals/cwe-mapping-guidance.json: missing; this check delegates the "
                        "whole verdict to it, so its absence is an unmeasured tree rather "
                        "than a clean one"])
    data = json.loads(read(guidance))
    prohibited = set(data.get("prohibited", []))
    discouraged = set(data.get("discouraged", []))
    if not prohibited:
        return (False, ["evals/cwe-mapping-guidance.json: no prohibited ids; the list lost "
                        "its subject rather than the corpus becoming clean"])

    files = sorted(glob.glob(p("wos", "bug-classes", "*.md")))
    files = [f for f in files if not os.path.basename(f).startswith("_")]
    if not files:
        return (False, ["wos/bug-classes/: no templates found; this check lost its subject"])

    hard, soft = [], []
    for path in files:
        m = re.search(r"(?m)^cwe:\s*\[(.*?)\]", read(path))
        if not m:
            continue
        rel = os.path.relpath(path, _repo())
        ids = [int(x) for x in re.findall(r"CWE-(\d+)", m.group(1))]
        for cid in ids:
            if cid in prohibited:
                hard.append(
                    f"{rel}: maps to CWE-{cid}, which MITRE marks Prohibited: \"this CWE ID "
                    f"must not be used to map to real-world vulnerabilities\". Use a child "
                    f"that names the weakness, or an empty list, which 37 templates carry"
                    + ("" if len(ids) > 1 else "; this is the template's only mapping, so it "
                       "currently has none that holds"))
            elif cid in discouraged:
                soft.append(
                    f"{rel}: maps to CWE-{cid}, which MITRE marks Discouraged, meaning a "
                    f"lower-level child would carry the weakness better. Not a build failure: "
                    f"the ID here is a triage label, not an NVD submission")
    # The extract's own age. MITRE moves ids between mapping values, so a verdict computed
    # from a snapshot can be wrong about an id that moved after it was taken, and nothing
    # else in the tree would notice. Reported, never failed: ADR-0171's finding was that a
    # date-triggered failure teaches people to move the date rather than redo the work, and
    # that applies here exactly as it does to check-doc-currency.sh.
    prov = data.get("_provenance", {})
    taken, cadence = prov.get("extracted"), prov.get("cadence_days")
    if taken and cadence:
        import datetime
        age = (datetime.date.today() - datetime.date.fromisoformat(taken)).days
        if age > cadence:
            soft.append(
                f"evals/cwe-mapping-guidance.json: extracted {taken} from catalogue "
                f"{prov.get('catalogue_version')}, {age} days ago, past its {cadence}-day "
                f"cadence. Re-extract per ADR-0213; an id that moved to Discouraged upstream "
                f"since then still reads as allowed here"
            )
    # WARN tier: ok=True with findings prints as WARN and keeps the count visible without
    # failing the build over a precision judgment MITRE itself frames as advice.
    return (not hard, hard + soft)


def check_scan_stamp_covers_its_claims():
    """[ADR-0212] A file's scan stamp is not newer than a section that dates itself.

    `scripts/check-doc-currency.sh` reads `Last scanned:` and `Cadence:` and reports the
    AGE of the stamp. It cannot see what the stamp covers, and on 2026-09-18 that gap had
    a live instance: `wos/sub-agent-orchestration.md` said `Last scanned: 2026-09-17` and
    the lint reported all three dated docs within cadence, while three rows of its
    per-tool primitives table were wrong. Two were wrong before the date the table itself
    claims: the header read `## Per-tool primitives (as of 2026-06-05)` and Gemini CLI
    shipped subagents on 2026-04-15, seven weeks earlier.

    THE PREDICATE, and why this shape rather than a richer manifest. A section heading
    that carries `(as of DATE)` is making a currency claim about that section. If the file
    then says it was scanned LATER, the two disagree: either the scan reached that section,
    in which case the heading's date should have moved, or it did not, in which case the
    file-level stamp is broader than the work behind it. Both are defects and both are
    fixed by the same edit. A per-row manifest would catch more and cost a format nobody
    maintains; this catches the instance that actually shipped, for one comparison.

    SCOPED TO HEADINGS, deliberately. `as of <date>` in prose is often historical ("the
    rule as of 2024 was X, and it changed"), where the old date IS the point. A heading is
    different: it labels everything under it, which is what makes it a currency claim
    rather than a fact about the past.
    """
    fails = []
    files = sorted(glob.glob(p("wos", "*.md")) + glob.glob(p("wos", "bug-classes", "*.md")))
    # Fail closed on an empty subject: three files carry a stamp today, and a glob that
    # matched nothing would report clean over a tree with no wos/ at all.
    if not files:
        return (False, ["wos/: no topic files found; this check lost its subject rather "
                        "than the subject becoming clean"])
    stamped = 0
    for path in files:
        body = read(path)
        stamp = re.search(r"(?m)^Last scanned: (\d{4}-\d{2}-\d{2})$", body)
        if not stamp:
            continue
        stamped += 1
        for head in re.finditer(r"(?m)^#{2,4} .*\(as of (\d{4}-\d{2}-\d{2})\).*$", body):
            if head.group(1) < stamp.group(1):
                fails.append(
                    f"{os.path.relpath(path, _repo())}: `Last scanned: {stamp.group(1)}` is "
                    f"newer than the section it covers, `{head.group(0).strip()}`. Either the "
                    f"scan reached that section and its date should have moved, or it did not "
                    f"and the file-level stamp claims more than was done. check-doc-currency.sh "
                    f"reads the stamp's age and cannot see this"
                )
    if not stamped:
        return (False, ["wos/: no file declares `Last scanned:`; the currency convention "
                        "left the tree and this check lost its subject"])
    return (not fails, fails)


def check_attended_chain_self_runs():
    """[ADR-0186, ADR-0207, ADR-0208] The attended chain runs without a human turn.

    Three decisions built this property and nothing asserted it. ADR-0186 made an attended
    session continue into `Run now:` instead of waiting to be asked, and named the four
    reasons that stop it. ADR-0207 retired the tier LABELS so `task-init` emits the
    disqualifier that fired. ADR-0208 removed the last stop, plan approval, on the finding
    that a plan routes to decisions already locked rather than making one.

    What checked it, until this: prose, plus `evals/scenarios/137-express-one-human-stop.md`,
    which needs a model, costs a 1800-second timeout, and carries `verdict_required: false`
    in `evals/spine-evals.json`. That is a real eval and it is not a gate. A reintroduced
    wait would ship green and surface as the workflow feeling slow again, which is the
    friction the maintainer named on 2026-08-31 and which took three ADRs to remove.

    WHY ABSENCE OF NAMED PHRASES, for the approval half. Reading a command for intent has
    no deterministic form. What is checkable is that the specific sentences which would put
    a person back in the loop are not there, which is the shape ADR-0163's retired
    confirmation rule is already guarded with. It bounds how the rule comes back in the
    obvious wording; it does not prove the command can never ask. Stated that way rather
    than as full coverage.

    WHY THE SPEC STRINGS ARE EXACT. Each is the operative clause of its decision. A
    rewording that preserves the meaning fails this check, and that is the intended cost:
    the sentence is the contract 98 commands read, so an edit to it should be deliberate
    and should update the guard in the same change.
    """
    fails = []
    spec = p(SPEC_PATH)
    if not os.path.isfile(spec):
        return (False, [f"{SPEC_PATH}: missing; the continuation rule has no home"])
    body = read(spec)
    if ATTENDED_CONTINUES not in body:
        fails.append(
            f"{SPEC_PATH}: no longer states that an attended session continues into "
            f"`Run now:` in the same turn (ADR-0186). Without it every command's Handoff "
            f"becomes a prompt to the person, which is the friction three ADRs removed"
        )
    if APPROVAL_NOT_REASON_TWO not in body:
        fails.append(
            f"{SPEC_PATH}: no longer excludes plan approval from stop-reason 2 (ADR-0208). "
            f"A plan routes to decisions already locked in DECISIONS.md rather than making "
            f"one, and without this sentence approval reads as a decision and stops"
        )

    approve = p("commands", "approve-plan.md")
    if not os.path.isfile(approve):
        fails.append("commands/approve-plan.md: missing, so the approval gate cannot be read")
    else:
        approve_body = read(approve).lower()
        for phrase in APPROVAL_WAIT_PHRASES:
            if phrase in approve_body:
                fails.append(
                    f"commands/approve-plan.md: carries {phrase!r}, which puts a human turn "
                    f"back at plan approval. ADR-0208 removed it on the finding that what "
                    f"remains at approval is a check against a rubric, not a decision"
                )

    # ADR-0207: the disqualifier, not the label. Asserted on the template because that is
    # what task-init seeds and what every later command reads.
    state_template = p("templates", "TASK_STATE.template.md")
    if not os.path.isfile(state_template):
        fails.append("templates/TASK_STATE.template.md: missing")
    else:
        template_body = read(state_template)
        if "Escalations:" not in template_body:
            fails.append(
                "templates/TASK_STATE.template.md: no `Escalations:` line; ADR-0207 "
                "replaced the tier label with the disqualifiers that fired, and that line "
                "is where the record of WHY a task got a longer pipeline lives"
            )
        if re.search(r"(?m)^- Tier:", template_body):
            fails.append(
                "templates/TASK_STATE.template.md: the `Tier:` label is back. ADR-0207 "
                "retired it because the label did no routing work: what routed was the "
                "disqualifier, and the label carried strictly less information"
            )
    return (not fails, fails)


def check_apply_commits_after_display():
    """[ADR-0163] Attended --apply creates the local commit after the display.

    The retired rule was confirmation after display in the same turn. Scenario 125
    used to treat a commit in that same reply as a FAIL. If that wording returns,
    models wait for sim again and Express stops on a reversible local commit.
    """
    fails = []
    # os.path.exists before read(), the reasoning check_unity_scene_plan_gates already
    # carries: read() raises FileNotFoundError on a missing file, the runner isolates
    # it into a FAIL, and the message that reaches the report reads like a defect in
    # this check rather than naming the file that is gone. Safe either way, since an
    # isolated exception fails closed; what is lost is the diagnosis. Added 2026-09-18,
    # the third lesson found written in one check's comment and absent from another.
    for required in ("commands/branch-commit.md",
                     "evals/scenarios/125-branch-commit-apply-authorization.md"):
        if not os.path.exists(p(required)):
            return (False, [f"{required}: missing; this check cannot read its subject"])
    body = read(p("commands", "branch-commit.md"))
    if "Create the commit in this turn after the display" not in body:
        fails.append(
            "commands/branch-commit.md: missing the ADR-0163 create-after-display rule"
        )
    if "Confirmation AFTER the display, in the same turn" in body:
        fails.append(
            "commands/branch-commit.md: retired confirmation-after-display rule is back; "
            "attended Express would wait for sim on a local commit"
        )
    if "getting the user's confirmation in the same turn" in body:
        fails.append(
            "commands/branch-commit.md: description still asks for same-turn confirmation"
        )
    s125 = read(p("evals", "scenarios", "125-branch-commit-apply-authorization.md"))
    if "Turn 1 creates no commit: HEAD is identical before and after" in s125:
        fails.append(
            "evals/scenarios/125-branch-commit-apply-authorization.md: still grades an "
            "attended commit after display as a FAIL, which is the pre-ADR-0163 contract"
        )
    if "Create the commit in this turn after the display" not in read(
        p(".claude", "skills", "branch-commit", "SKILL.md")
    ):
        fails.append(
            ".claude/skills/branch-commit/SKILL.md: generated skill missing ADR-0163; "
            "regen with build-agent-skills.sh"
        )
    return (not fails, fails)


def check_bare_commit_tree_proof():
    """[ADR-0167] The apply commit is bare, proven by tree hash, and names its branch.

    Successor to scripts/tests/test-branch-commit-unchanged.sh, which asserted D-4 of an
    earlier task: that commands/branch-commit.md is byte-identical to the ref that task
    started from. Three ADRs have edited that file on purpose since (0163, 0165, 0167), so
    on 2026-08-30 the test reported a violation of a rule nobody holds any more, 11
    insertions and 13 deletions against its pinned base. It sat outside the CI allowlist,
    so nothing was red and nobody had reason to look.

    A frozen file was never the contract; what the file SAYS is. So this asserts the rules
    instead of the bytes, in both directions the way the sibling ADR-0163 check does: the
    ADR-0167 obligations are present, and the ADR-0163 pathspec rule it superseded has not
    come back. That one matters most: a pathspec rebuilds each named path from the WORKING
    TREE, so it commits content the display never showed, which is the defect ADR-0167
    reproduced in a throwaway repository before deciding.
    """
    fails = []
    body = read(p("commands", "branch-commit.md"))
    skill = read(p(".claude", "skills", "branch-commit", "SKILL.md"))
    required = (
        ("bare `git commit` carrying message flags only", "the bare-commit rule"),
        ("`git commit -a`, `git commit -am`, and a pathspec",
         "the list of forbidden commit forms"),
        ("record `git write-tree` as `T_shown`", "the T_shown record taken after the display"),
        ("`git rev-parse HEAD^{tree}` equals `T_shown`",
         "the post-commit tree-hash assertion"),
        ("read `git branch --show-current` and cite the value it read",
         "condition 7 reading and citing the current branch"),
        ("A detached HEAD counts as unnamed and refuses the same way",
         "the detached-HEAD refusal"),
    )
    for needle, what in required:
        if needle not in body:
            fails.append(f"commands/branch-commit.md: missing {what} (ADR-0167)")
        if needle not in skill:
            fails.append(
                f".claude/skills/branch-commit/SKILL.md: missing {what}; the generated skill "
                f"is what a run actually loads, so regen with build-agent-skills.sh"
            )
    retired = "The commit SHALL be created with an explicit pathspec"
    for path, text in (("commands/branch-commit.md", body),
                       (".claude/skills/branch-commit/SKILL.md", skill)):
        if retired in text:
            fails.append(
                f"{path}: the superseded ADR-0163 explicit-pathspec rule is back. A pathspec "
                f"rebuilds each named path from the working tree, so an edit landing after the "
                f"display is committed as though it had been reviewed (ADR-0167)"
            )
    return (not fails, fails)


def check_structured_output_names_its_path(root=None):
    """[ADR-0158 D-1] Preserve the path guard and reject verified stale return mandates.

    The additional checks match the carrier contradictions found in the fleet audit,
    including a worker-call requirement that survived the existing path sentinel.
    They inspect command-owned prose and the direct dispatch template/guidance, excluding
    exact canonical shared bodies. Historical examples and runtime correctness remain
    subjects for contract review; these patterns are not a semantic prompt validator.
    """
    fails = []
    repo = root or _repo()
    files = sorted(glob.glob(os.path.join(repo, "commands", "*.md")))
    if not files:
        return (False, ["commands/: no command files found; this check lost its subject "
                        "rather than the subject becoming clean"])
    for f in files:
        rel = os.path.relpath(f, repo)
        body = read(f)
        if "StructuredOutput" in body and "Name the path you are on" not in body:
            fails.append(
                f"{rel}: mandates `StructuredOutput` without naming the dispatch path that "
                f"has it; on the `Agent` path that instructs a worker to call a tool it does "
                f"not have (ADR-0158 D-1)")
        if "artifact=" in body:
            fails.append(
                f"{rel}: carries an `artifact=` mandate. There is no `artifact=` key in the "
                f"workflow runtime's API and no such tool on the `Agent` path, so the line "
                f"names a parameter that exists on neither (commands/_shared/worker-contract.md)")
    shared = [read(f).strip("\n") for f in
              glob.glob(os.path.join(repo, "commands", "_shared", "*.md"))]
    direct = [os.path.join(repo, "templates", "ORCHESTRATOR_COMMAND.template.md"),
              os.path.join(repo, "wos", "cross-cutting-workflow-guardrails.md")]
    worker_call = re.compile(
        r"\b(?:worker\s+must\s+invoke(?:\s+the)?|every worker invoked(?:\s+the)?|"
        r"workers that did not invoke)\s+[`*]*StructuredOutput\b", re.I)
    stale = ("worker returns text and the orchestrator persists it",
             "explicit StructuredOutput call reminder")
    for f in files + [f for f in direct if os.path.isfile(f)]:
        own = _strip_shared_blocks(read(f), shared)
        if f not in files and "artifact=" in own:
            fails.append(f"{os.path.relpath(f, repo)}: unavailable artifact= mandate "
                         "in direct dispatch guidance (ADR-0158 D-1)")
        for line in own.splitlines():
            if worker_call.search(line) or any(term in line for term in stale):
                fails.append(
                    f"{os.path.relpath(f, repo)}: stale worker-return carrier: {line.strip()[:180]} "
                    "(ADR-0158: native JSON file or runtime typed result; no worker tool call)")
    return (not fails, fails)


def check_highest_adr_claim():
    """[ADR-0136] Prose that names the highest ADR number matches disk.

    The count-marker guard (ADR-0029) checks the number INSIDE the marker and is blind to the
    sentence around it. Measured twice on 2026-08-10: the same CLAUDE.md sentence had its
    `count:adrs` marker bumped 132 -> 134 by a commit that left `the highest is 0133` intact,
    and then landing ADR-0136 in this very session left `the highest is 0135` behind. A number
    a machine checks stays right; the number beside it drifts. This closes the pair.
    """
    fails = []
    numbers = []
    for path in glob.glob(p("docs", "adr", "0*.md")):
        m = re.match(r"^(\d{4})-", os.path.basename(path))
        if m:
            numbers.append(int(m.group(1)))
    if not numbers:
        return (False, ["docs/adr/: no numbered ADR files found"])
    highest = f"{max(numbers):04d}"

    # `the` is OPTIONAL and the match is case-insensitive. The first version of this check
    # required the literal "the highest is" and therefore passed over
    # wos/repository-structure.md:126, which writes "highest is 0121" inside a parenthetical
    # and was 17 releases stale on the day the check landed. A guard whose regex is narrower
    # than the phrasing it polices reports clean and teaches nothing.
    pattern = re.compile(r"\bhighest is (\d{4})", re.I)
    # Through p(), not bare. Until 2026-09-18 these four were opened relative to the
    # process's working directory, so running structural-evals.py from anywhere but
    # the repo root found no files and reported [PASS] over zero surfaces. Verified
    # by running it from /tmp on the day this was fixed: clean, checking nothing.
    # The same failure the comment above describes, moved from the regex to the path:
    # a guard narrower than the thing it polices reports clean and teaches nothing.
    for path in ("CLAUDE.md", "README.md", "docs/adr/README.md", "wos/repository-structure.md"):
        full = p(path)
        if not os.path.isfile(full):
            continue
        for n, line in enumerate(open(full, encoding="utf-8"), 1):
            for m in pattern.finditer(line):
                if m.group(1) != highest:
                    fails.append(
                        f"{path}:{n}: claims the highest ADR is {m.group(1)}, disk says "
                        f"{highest}. The count marker beside this sentence is machine-checked "
                        f"and this number was not, which is how it drifted"
                    )
    return (not fails, fails)


# Content floors for the eval corpus. Presence of a heading is not content: an
# emptied corpus keeps every section header and passes every structural check.
# These two numbers go UP over time and never down, the mirror image of the
# ceiling rule in ADR-0116. Lowering either one is an ADR, not an edit.
# Measured on 2026-08-29: smallest scenario 1466 chars, corpus mean 4742 chars.
CRITERIA_ITEM_FLOOR = 3  # Same floor the spine eval runner needs before it will grade.
SCENARIO_FLOOR_CHARS = 1200
CORPUS_MEAN_FLOOR_CHARS = 4200


def check_scenario_content_floor(root=None):
    """[scenario 138] The corpus has weight, not just section headers.

    Every other structural check over the corpus asks whether a section is
    PRESENT. None asked whether it says anything, so deleting the body of every
    section (roughly 641 KB down to 177 KB) left the regression net reporting
    itself healthy while testing nothing.

    Two independent findings, because they are two different defects: one file
    being a stub, and the corpus being gutted in bulk. The corpus gate is on the
    MEAN rather than the total, and that is the load-bearing choice. A total
    would forbid deprecating a scenario, which is ordinary work; the mean catches
    bulk emptying, which is the actual failure.

    root= exists for the fixture proof, same pattern as check_skill_load_budget.
    """
    if root is None:
        files = _scenario_files()
    else:
        files = sorted(glob.glob(os.path.join(root, "evals", "scenarios", "[0-9]*.md")))
    if not files:
        return (False, ["evals/scenarios: no scenario files found"])

    fails = []
    sizes = []
    for path in files:
        size = len(read(path))
        sizes.append(size)
        if size < SCENARIO_FLOOR_CHARS:
            name = os.path.basename(path)
            fails.append(
                f"evals/scenarios/{name}: {size} chars is below the "
                f"{SCENARIO_FLOOR_CHARS}-char scenario floor; a scenario this short "
                f"states a heading, not a behavior")

    mean = sum(sizes) // len(sizes)
    if mean < CORPUS_MEAN_FLOOR_CHARS:
        fails.append(
            f"evals/scenarios: corpus mean {mean} chars is below the "
            f"{CORPUS_MEAN_FLOOR_CHARS}-char mean floor; the corpus was emptied in "
            f"bulk, not pruned")
    return (not fails, fails)


def check_criteria_content_floor(root=None):
    """[scenario 138] A criteria section holds a rubric, not a paragraph.

    Deliberately written against the same header family check_corpus_wellformed
    accepts, not against the literal `## Pass criteria`. Measured 2026-08-29: 78
    of 136 scenarios use that header, 3 use `## Pass Criteria`, and 55 use an
    `## Expected ...` variant. A literal rule would have painted 55 files red,
    nearly all of them false alarms, and the first response to that is a waiver.

    Three is the same floor the spine eval runner requires before it will grade a
    scenario at all, so a file that fails here cannot be scored there either.
    """
    if root is None:
        files = _scenario_files()
    else:
        files = sorted(glob.glob(os.path.join(root, "evals", "scenarios", "[0-9]*.md")))
    head = re.compile(r"^##\s+(expected|pass\s+criteria)", re.I)
    item = re.compile(r"^\s*(\d+\.|[-*])\s+\S", re.M)
    fails = []
    for path in files:
        inside, buf = False, []
        for line in read(path).split("\n"):
            if line.startswith("## "):
                inside = bool(head.match(line))
                continue
            if inside:
                buf.append(line)
        n = len(item.findall("\n".join(buf)))
        if n < CRITERIA_ITEM_FLOOR:
            fails.append(
                f"evals/scenarios/{os.path.basename(path)}: the criteria section has "
                f"{n} enumerable check(s), below the floor of {CRITERIA_ITEM_FLOOR}; "
                f"fewer than three is a paragraph, not a rubric")
    return (not fails, fails)


SPEC_PATH = "WORKFLOW_OPERATING_SYSTEM.md"
SPEC_CEILING_CHARS = 126000  # ~31500 tokens. Non-regression, set just above the 2026-08-10
                             # measurement of 124672 chars. It comes DOWN, never up (ADR-0116
                             # rule). The headroom is ~1 per cent: enough for a typo fix,
                             # not for a new section.


def check_spec_size_budget(root=None):
    """[ADR-0136] The always-read spec stays under a non-regression size ceiling.

    The system layer was the last always-paid surface with no budget of any kind, while the
    two cheaper ones had hard gates: Load (ADR-0116) and Advertise (ADR-0135). Measured
    2026-08-10 the spec is 124672 chars, 31168 tokens, 2.34x the 13298 that ADR-0006 recorded
    as the natural stopping point after the lazy-load split. Nothing had stopped that growth
    because nothing was watching it.

    This is deliberately a NON-REGRESSION ceiling, not the ADR-0006 figure: a gate that is
    already red teaches nothing and gets waived. Returning to 13298 is a content decision,
    not a check.
    """
    spec = os.path.join(root, SPEC_PATH) if root else p(SPEC_PATH)
    if not os.path.isfile(spec):
        return (False, [f"{SPEC_PATH}: missing"])

    # Chars, not bytes: scripts/measure-tokens.py is the repository's canonical meter and it
    # counts chars, so byte-counting here would print a number that disagrees with the
    # baselines by the file's multibyte content (50 on the 2026-08-10 measurement).
    size = len(open(spec, encoding="utf-8").read())
    if size > SPEC_CEILING_CHARS:
        return (False, [
            f"{SPEC_PATH}: {size} chars (~{size // 4} tokens) exceeds the "
            f"{SPEC_CEILING_CHARS}-char non-regression ceiling by {size - SPEC_CEILING_CHARS}. "
            f"Every command pays this on every invocation, so growth here is the most "
            f"expensive growth in the repository. Move the new content to a lazy `wos/` topic "
            f"and cite it from the Minimum read map (ADR-0006). Raising this ceiling is not a "
            f"fix: per ADR-0116 the number comes down, never up"
        ])
    return (True, [])


BOOTSTRAP_BLOCK = "commands/_shared/mandatory-context-bootstrap.md"
BOOTSTRAP_SECTIONS = (
    "## LLM execution contract",
    "## Editor mode policy",
    "## Global output contract",
    "## Cross-cutting workflow guardrails",
)
BOOTSTRAP_TOLERANCE = 0.03  # 3 per cent, below the ~10 per cent error of the chars/4 method
# The two `## Cross-cutting workflow guardrails` subsections the reduced tier skips. The block
# names them; the check measures them, so the reduced figure is checked like the full one.
BOOTSTRAP_REDUCED_SKIPS = (
    "### External web access (centralized)",
    "### Sequencing heuristics (by phase)",
)
# The leaf-reviewer tier (ADR-0226): the one section a blinded reviewer reads from the spec.
LEAF_TIER_SECTIONS = ("## Global output contract",)


def _spec_span(lines, heading):
    """Chars of one spec section, from its heading line to the next heading of the same
    or a higher level. Anchored at line start, like the floor check, so the Minimum read
    map that names every section never stands in for the section itself."""
    level = len(heading) - len(heading.lstrip("#"))
    stops = tuple("#" * n + " " for n in range(1, level + 1))
    for i, line in enumerate(lines):
        if line.strip() != heading:
            continue
        end = i + 1
        while end < len(lines) and not lines[end].startswith(stops):
            end += 1
        return len("\n".join(lines[i:end]))
    return None


def check_bootstrap_floor_measured():
    """[ADR-0012] The declared bootstrap floor equals the measured size of the four sections.

    The floor is the third always-paid surface, next to Load and Advertise, and it was the
    only one governed by prose: the block asserted 9610 tokens while the four sections it
    names measured 10530, a 9.6 per cent gap replicated into 92 commands, because nothing
    recomputed it when the spec grew. This closes that by construction.

    Sections are matched anchored at line start. Matching the bare string would hit the
    Minimum read map at the top of the spec, which names all four, and silently measure the
    wrong span: that exact miss produced a 39632-char reading before this was anchored.
    """
    fails = []
    spec_path = "WORKFLOW_OPERATING_SYSTEM.md"
    if not os.path.isfile(p(spec_path)):
        return (False, [f"{spec_path}: missing"])

    lines = open(p(spec_path), encoding="utf-8").read().split("\n")
    heads = [(i, l.strip()) for i, l in enumerate(lines) if l.startswith("## ")]
    measured = 0
    seen = set()
    for k, (i, head) in enumerate(heads):
        if head not in BOOTSTRAP_SECTIONS:
            continue
        seen.add(head)
        end = heads[k + 1][0] if k + 1 < len(heads) else len(lines)
        measured += len("\n".join(lines[i:end]))

    absent = [s for s in BOOTSTRAP_SECTIONS if s not in seen]
    if absent:
        fails.append(
            f"{spec_path}: the bootstrap block names sections absent from the spec: "
            f"{', '.join(absent)}; the floor cannot be measured against a section that moved"
        )
        return (False, fails)

    measured_tokens = measured // 4
    if not os.path.isfile(p(BOOTSTRAP_BLOCK)):
        return (False, [f"{BOOTSTRAP_BLOCK}: missing"])

    block = open(p(BOOTSTRAP_BLOCK), encoding="utf-8").read()
    m = re.search(r"full tier is measured at (\d[\d,]*) tokens", block)
    if not m:
        fails.append(
            f"{BOOTSTRAP_BLOCK}: no `full tier is measured at N tokens` claim to check; "
            f"the floor is measured at {measured_tokens} tokens and must be stated"
        )
        return (False, fails)

    declared = int(m.group(1).replace(",", ""))
    drift = abs(measured_tokens - declared) / declared if declared else 1.0
    if drift > BOOTSTRAP_TOLERANCE:
        fails.append(
            f"{BOOTSTRAP_BLOCK}: declares a {declared}-token bootstrap floor, the four "
            f"`{spec_path}` sections measure {measured_tokens} tokens "
            f"({measured} chars), a {drift * 100:.1f} per cent gap over the "
            f"{BOOTSTRAP_TOLERANCE * 100:.0f} per cent tolerance. This number is inlined into "
            f"every command carrying the block, so a stale floor misprices every invocation. "
            f"Re-measure and propagate with scripts/sync-shared-blocks.sh"
        )

    # The reduced tier, measured since 2026-09-23 (ADR-0226). The block used to say its
    # reduced figure was stated as the subsections dropped because only the full figure was
    # machine-checked; the leaf-reviewer tier made a second measured figure, and the reduced
    # one is measured here the same way rather than left as the one unchecked number.
    rm = re.search(r"reduced tier is about (\d[\d,]*)", block)
    if not rm:
        fails.append(
            f"{BOOTSTRAP_BLOCK}: no `reduced tier is about N` claim to check; the reduced "
            f"tier is measured at {measured_tokens} tokens minus the skipped subsections")
    else:
        skipped = 0
        for sub in BOOTSTRAP_REDUCED_SKIPS:
            size = _spec_span(lines, sub)
            if f"`{sub}`" not in block or size is None:
                fails.append(
                    f"{BOOTSTRAP_BLOCK}: the reduced tier skips `{sub}`, which the block or "
                    f"the spec no longer names; the reduced figure cannot be measured")
                size = 0
            skipped += size
        reduced_tokens = (measured - skipped) // 4
        reduced_declared = int(rm.group(1).replace(",", ""))
        rdrift = abs(reduced_tokens - reduced_declared) / reduced_declared if reduced_declared else 1.0
        if rdrift > BOOTSTRAP_TOLERANCE:
            fails.append(
                f"{BOOTSTRAP_BLOCK}: declares the reduced tier at about {reduced_declared} "
                f"tokens, the four sections minus the two skipped subsections measure "
                f"{reduced_tokens}, a {rdrift * 100:.1f} per cent gap over the "
                f"{BOOTSTRAP_TOLERANCE * 100:.0f} per cent tolerance")

    # The copies (docs drift audit, gap 7). The block is synced into every command, but the
    # number was also copied by hand into the FAQ, wos/context-budget.md and two templates, and
    # this check measured only the block: the copies read 10,470, 10530 and ~6,750 while the
    # block said 11042. A sentence outside commands/ that names the bootstrap or the always-read
    # sections and states a token figure must agree with the block's full or reduced tier.
    stated = [declared]
    if rm:
        stated.append(int(rm.group(1).replace(",", "")))
    lm = re.search(r"leaf-reviewer tier[^.]*?measured at (\d[\d,]*) tokens", block)
    if lm:
        stated.append(int(lm.group(1).replace(",", "")))
    subject = re.compile(r"bootstrap|always-read|four spec sections", re.I)
    figure = re.compile(r"(\d{1,2},?\d{3}) tokens")
    for path in _live_doc_files():
        rel = os.path.relpath(path, _repo()).replace(os.sep, "/")
        if rel.startswith("commands/"):
            continue
        for n, line in enumerate(read(path).split("\n"), 1):
            for sentence in re.split(r"(?<=[.;])\s+", line):
                if not subject.search(sentence):
                    continue
                for fm in figure.finditer(sentence):
                    value = int(fm.group(1).replace(",", ""))
                    if min(abs(value - s) / s for s in stated) > BOOTSTRAP_TOLERANCE:
                        fails.append(
                            f"{rel}:{n}: states the bootstrap at {value} tokens; {BOOTSTRAP_BLOCK} "
                            f"declares {declared} (full tier), measured against the spec. Cite the "
                            f"block instead of copying the number, or copy the current one")
    return (not fails, fails)


# What each dispatcher's blinded review carries, pinned so the leaf-reviewer tier (which
# changes what the reviewer READS from the spec) is never mistaken for licence to change what
# the dispatch CARRIES. ADR-0033 set the isolation, ADR-0145 applied it to reviews.
REVIEWER_ISOLATION_PINS = (
    ("commands/verify-against-rubric.md", "The sub-agent receives ONLY:"),
    ("commands/verify-against-rubric.md", "NO TASK_STATE.md, NO DECISIONS.md, NO prior conversation history."),
    ("commands/approve-plan.md", "The dispatch carries the artifact path and the rubric and NOTHING else."),
    ("commands/review-hard.md", "The sub-agent receives the diff and the rubric ONLY"),
)


def check_leaf_reviewer_tier():
    """[ADR-0226] The blinded reviewer reads one spec section, and only the reviewer does.

    The bootstrap block names a leaf-reviewer tier: `## Global output contract` plus the
    rubric, and none of the other three always-read sections, which govern an agent that
    edits the task or dispatches other commands. This check holds four things together:

    - the tier sentence exists, names exactly the sections in LEAF_TIER_SECTIONS, and states
      a figure within tolerance of what those sections measure in the spec today;
    - every command the sentence names declares the tier in its own text, outside the
      inlined block, and no other command does, so a writer or a dispatcher cannot slide
      onto the reviewer's diet by copying the declaration;
    - the isolation clauses of the reviewer and both dispatchers are still present, word
      for word: the tier changes what the reviewer reads, never what the dispatch carries.

    Before ADR-0226 the block had no such tier and `verify-against-rubric` paid the full
    four-section floor on every review, which is how this check fails on the old tree.
    """
    fails = []
    spec = p("WORKFLOW_OPERATING_SYSTEM.md")
    if not os.path.isfile(spec):
        return (False, ["WORKFLOW_OPERATING_SYSTEM.md: missing"])
    lines = read(spec).split("\n")
    block = read(p(BOOTSTRAP_BLOCK))

    m = re.search(r"The leaf-reviewer tier (.*?) plus its rubric\.", block, re.S)
    if not m:
        return (False, [
            f"{BOOTSTRAP_BLOCK}: names no leaf-reviewer tier (`The leaf-reviewer tier ... "
            f"plus its rubric.`); the blinded reviewer pays the full four-section floor on "
            f"every review (ADR-0226)"])
    sentence = m.group(1)
    sections = tuple(re.findall(r"`(#+ [^`]+)`", sentence))
    named = sorted(set(re.findall(r"`([a-z][a-z0-9-]+)`", sentence)))

    if sections != LEAF_TIER_SECTIONS:
        fails.append(
            f"{BOOTSTRAP_BLOCK}: the leaf-reviewer tier reads {list(sections)}; ADR-0226 "
            f"says it reads exactly {list(LEAF_TIER_SECTIONS)}. `## Global output contract` "
            f"is what makes the verdict parseable by the command that dispatched it, and the "
            f"other three govern editing and dispatch")
    measured = 0
    for s in sections:
        size = _spec_span(lines, s)
        if size is None:
            fails.append(f"{BOOTSTRAP_BLOCK}: the leaf-reviewer tier names `{s}`, absent from the spec")
        else:
            measured += size
    fm = re.search(r"measured at (\d[\d,]*) tokens", sentence)
    if not fm:
        fails.append(f"{BOOTSTRAP_BLOCK}: the leaf-reviewer tier states no `measured at N tokens` figure")
    elif measured:
        declared = int(fm.group(1).replace(",", ""))
        drift = abs(measured // 4 - declared) / declared if declared else 1.0
        if drift > BOOTSTRAP_TOLERANCE:
            fails.append(
                f"{BOOTSTRAP_BLOCK}: the leaf-reviewer tier declares {declared} tokens, its "
                f"sections measure {measured // 4} ({measured} chars), a {drift * 100:.1f} per "
                f"cent gap over the {BOOTSTRAP_TOLERANCE * 100:.0f} per cent tolerance")
    if not named:
        fails.append(f"{BOOTSTRAP_BLOCK}: the leaf-reviewer tier names no command that runs on it")

    shared = _shared_block_bodies()
    declaring = set()
    for f in sorted(glob.glob(p("commands", "*.md"))):
        own = _strip_shared_blocks(read(f), shared)
        if "runs on the leaf-reviewer tier" in own:
            declaring.add(os.path.basename(f)[:-3])
    for name in named:
        if name not in declaring:
            fails.append(
                f"commands/{name}.md: the bootstrap block puts it on the leaf-reviewer tier and "
                f"it does not declare so in its own text (`runs on the leaf-reviewer tier`)")
    for name in sorted(declaring - set(named)):
        fails.append(
            f"commands/{name}.md: declares the leaf-reviewer tier and is not named in the "
            f"block's tier sentence; a command that edits the task or dispatches other commands "
            f"needs the sections that tier skips")

    for rel, phrase in REVIEWER_ISOLATION_PINS:
        path = p(*rel.split("/"))
        if not os.path.isfile(path) or phrase not in read(path):
            fails.append(
                f"{rel}: lost its reviewer isolation clause {phrase!r}; the dispatch must carry "
                f"the artifact and the rubric only (ADR-0033, ADR-0145), whatever tier the "
                f"reviewer reads")
    return (not fails, fails)


FLOOR_FILES = ("closure-floors.md", "platform-runtime-floors.md")
NON_FLOOR_SECTIONS = {"## When to load this file"}
ATTESTER_CLASSES = ("agnostic", "environment-bound", "human-bound")


def check_floor_attester_class():
    """[scenario 127] Every closure floor declares exactly one attester class.

    The scan is fail-closed BY CONSTRUCTION: it starts from every `^## ` section in the
    two floor files and subtracts a named allowlist, rather than matching the header
    text. Anchoring on the word "floor" would be fail-open, measured on disk:
    `^## .*floor` matches 6 and 4 against 11 floors, missing `## Rollout-constraint
    reconcile`, a floor whose heading omits the word. Structure-minus-allowlist means a
    floor added tomorrow is covered by default, and a new non-floor section fails until
    someone exempts it on purpose, which is a decision rather than an accident.

    The grammar is anchored and unadorned (`^Attester class: <value>$`, column zero, no
    emphasis) because this is the line a machine reads; `wos/gate-conditions.md`
    `### The attester-removed test` defines it and says why.
    """
    fails = []
    line_re = re.compile(r"^Attester class: (.*)$", re.M)
    for name in FLOOR_FILES:
        path = p("wos", name)
        if not os.path.exists(path):
            fails.append(f"wos/{name}: file is missing")
            continue
        # A capturing split yields [preamble, head1, body1, head2, body2, ...]. `^## `
        # cannot match a `### ` variant heading, so each body is one whole floor section.
        parts = re.split(r"^(## .*)$", read(path), flags=re.M)
        for head, body in zip(parts[1::2], parts[2::2]):
            head = head.strip()
            if head in NON_FLOOR_SECTIONS:
                continue
            found = line_re.findall(body)
            if not found:
                fails.append(f"wos/{name}: `{head}` declares no `Attester class:` line")
            elif len(found) > 1:
                fails.append(
                    f"wos/{name}: `{head}` declares {len(found)} attester-class lines, expected exactly one"
                )
            elif found[0] not in ATTESTER_CLASSES:
                fails.append(
                    f"wos/{name}: `{head}` declares attester class '{found[0]}', "
                    f"not one of {', '.join(ATTESTER_CLASSES)}"
                )
    return (not fails, fails)


# Each row's second field is the label printed beside the check. It names the eval
# scenario the invariant enforces, or, when the invariant predates or postdates any
# scenario, the ADR that locked it. It is never a D-N task decision: those live under
# projects/, which .gitignore excludes, so the printed anchor resolved to nothing a
# reader of this repository could open.
def check_unity_no_new_command():
    """[scenario 129] ADR-0130 D-5: Unity lands as reference topics plus contract widenings,
    with NO net-new Unity command. Asserted directly rather than through count:commands,
    because a count marker moving tells you a command was added but not which one, and the
    invariant here is specifically that no command is NAMED for the engine.
    """
    fails = []
    # ADR-0130 D-5 said "no net-new Unity command in this wave"; ADR-0132 superseded that scope for
    # exactly one command, on an empirical test. The invariant is therefore no UNAUTHORIZED Unity
    # command, with the authorized set enumerated here so adding a second one fails until an ADR
    # names it. Widening this to a bare glob-and-pass would delete the guard.
    AUTHORIZED = {"unity-scene-plan.md"}
    for path in sorted(set(glob.glob(p("commands", "unity-*")))):
        base = os.path.basename(path)
        if base in AUTHORIZED:
            continue
        fails.append(f"{os.path.relpath(path, REPO)}: engine-named Unity command with no ADR authorizing it. "
                     f"ADR-0130 D-5 delivers Unity as reference topics plus contract widenings; ADR-0132 "
                     f"superseded that for `unity-scene-plan` alone, on a recorded empirical test. A second one "
                     f"needs its own superseding ADR, not a new file.")
    return (not fails, fails)


def check_unity_adapter_surface():
    """[scenario 129] ADR-0130 D-4: Unity runtime verification lives as an app-runtime-verify
    adapter, not a sibling command, and the two consuming commands actually reach the topics.
    A widening whose topic nothing cites is the orphan failure ADR-0127 was written about.
    """
    fails = []
    arv = read(p("commands", "app-runtime-verify.md"))
    for needle, why in [
        ("wos/unity-runtime-evidence.md", "does not cite the Unity capture topic, so the adapter has no documented capture path"),
        ("MANAGED_EXCEPTION", "lost the MANAGED_EXCEPTION code, the one taxonomy addition the managed-versus-native split requires"),
        ("Step 5a", "lost the Step 5a Unity adapter block; a bare mention of Unity in the description "
                    "is not the adapter, and asserting on the word alone would pass with the step deleted"),
    ]:
        if needle not in arv:
            fails.append(f"commands/app-runtime-verify.md: {why} (missing {needle!r})")
    ts = read(p("commands", "test-strategy.md"))
    for needle, why in [
        ("wos/unity-testing-and-ci.md", "does not cite the Unity testing topic, leaving it orphaned"),
        ("-testResults", "no longer names the -testResults file, the only signal a Unity CI gate can rely on"),
    ]:
        if needle not in ts:
            fails.append(f"commands/test-strategy.md: {why} (missing {needle!r})")
    return (not fails, fails)


def check_store_integrity_engine_agnostic():
    """[scenario 129] ADR-0130 D-3: an engine-agnostic bug-class mechanism is widened, never
    forked per engine. Guards both directions: the widened template must keep its multi-stack
    frontmatter, and no per-engine fork of the same CWE-602 mechanism may appear beside it.
    """
    fails = []
    rel = os.path.join("wos", "bug-classes", "godot-monetization-integrity.md")
    tpl = read(p("wos", "bug-classes", "godot-monetization-integrity.md"))
    front = tpl.split("---", 2)[1] if tpl.count("---") >= 2 else ""
    langs = re.search(r"^languages:\s*\[(.*?)\]", front, re.M)
    if not langs or "csharp" not in langs.group(1):
        fails.append(f"{rel}: languages no longer declares csharp, so a Unity entitlement defect of the "
                     f"same CWE-602 class is invisible to repo-consistency-sweep (ADR-0130 D-3)")
    if "**/*.cs" not in front:
        fails.append(f"{rel}: file-patterns no longer matches **/*.cs, so the widened languages list has "
                     f"nothing to run against")
    # Assert the distinctive marker, not the bare phrase "engine-agnostic": that phrase
    # occurs twice inside the note's own sentence, so a substring test would be satisfied
    # by either half surviving the note's deletion. This is the incidental-prose failure
    # ADR-0119 recorded, caught here by a review pass rather than in production.
    if "**Scope note (ADR-0130).**" not in tpl:
        fails.append(f"{rel}: lost its ADR-0130 scope note. The filename says godot, so without the note "
                     f"stating the class is engine-agnostic the name is the only signal a reader gets, "
                     f"and it is wrong")
    for path in sorted(glob.glob(p("wos", "bug-classes", "unity-*monetization*.md"))
                       + glob.glob(p("wos", "bug-classes", "unity-*iap*.md"))
                       + glob.glob(p("wos", "bug-classes", "unity-*entitlement*.md"))):
        fails.append(f"{os.path.relpath(path, REPO)}: per-engine fork of the store-integrity mechanism. "
                     f"ADR-0130 D-3 widens the existing template instead; 69 of 78 templates are multi-stack.")
    return (not fails, fails)


def check_unity_topics_indexed():
    """[scenario 129] Every wos/unity-*.md is reachable from the spec read map, the map cites no
    unity topic absent from disk, and no unity topic copies a sentence verbatim from a Godot or
    RN topic instead of cross-referencing it. Same three predicates as the ADR-0117 Godot check,
    including the dangling-row direction that check had to learn.
    """
    fails = []
    spec = read(p("WORKFLOW_OPERATING_SYSTEM.md"))
    marker = "Minimum read map for execution:"
    if marker not in spec:
        return (False, ["WORKFLOW_OPERATING_SYSTEM.md: no 'Minimum read map for execution:' section to check against"])
    read_map = spec.split(marker, 1)[1].split("\n## ", 1)[0]
    topics = sorted(glob.glob(p("wos", "unity-*.md")))
    if not topics:
        return (False, ["wos/unity-*.md: no Unity topic files exist, but commands/app-runtime-verify.md and "
                        "commands/test-strategy.md cite them by name"])
    on_disk = {os.path.basename(t) for t in topics}
    for name in sorted(on_disk):
        if name not in read_map:
            fails.append(f"wos/{name}: not referenced from the WORKFLOW_OPERATING_SYSTEM.md read map (orphaned topic)")
    for cited in sorted(set(re.findall(r"wos/(unity-[A-Za-z0-9._-]+\.md)", read_map))):
        if cited not in on_disk:
            fails.append(f"wos/{cited}: cited by the read map but absent from disk (dangling row)")
    others = sorted(set(glob.glob(p("wos", "godot-*.md")) + glob.glob(p("wos", "rn-expo-*.md"))))
    cache = {f: _topic_sentences(f) for f in topics + others}
    for a, b in itertools.chain(((t, o) for t in topics for o in others),
                                itertools.combinations(topics, 2)):
        for dup in sorted(cache[a] & cache[b]):
            fails.append(f"wos/{os.path.basename(a)} and wos/{os.path.basename(b)}: identical "
                         f"sentence copied instead of cross-referenced: {dup[:90]!r}")
    return (not fails, fails)


def check_unity_multiplayer_surface():
    """[scenario 130] ADR-0131: multiplayer ships as one Unity-scoped topic plus two conditional
    blocks, with no net-new command and no engine-neutral extraction. Guards E-1 through E-4.
    """
    fails = []
    topic_rel = os.path.join("wos", "unity-netcode-architecture.md")
    # isfile before read, not `if not topic` after it: read() raises on an absent file,
    # so the falsiness test could only ever fire on a file that exists and is empty.
    # The specific message is worth keeping, which is why this guard is made live
    # rather than deleted in favour of the runner's generic one.
    topic_path = p("wos", "unity-netcode-architecture.md")
    if not os.path.isfile(topic_path):
        return (False, [f"{topic_rel}: absent, but security-review and performance-budget cite it (ADR-0131 E-1)"])
    topic = read(topic_path)
    # E-3: the absent scope is named IN the topic, so a reader cannot mistake absence for coverage.
    for needle, why in [
        ("Deliberately absent", "lost its absent-scope section; without it a reader takes the NGO-only "
                                "scope for full coverage of a six-framework landscape (ADR-0131 E-3)"),
        ("doesn't have a full implementation of client-side prediction",
         "lost the NGO prediction-and-reconciliation absence, the wave's sharpest captured fact and a "
         "plan-time forcing item (ADR-0131)"),
        ("no server side rewind", "lost the NGO server-rewind absence (ADR-0131)"),
    ]:
        if needle not in topic:
            fails.append(f"{topic_rel}: {why}")
    # E-1: both conditional blocks exist and reach the topic. A block whose topic nothing cites is
    # the orphan failure ADR-0127 was written about.
    sr = read(p("commands", "security-review.md"))
    if "Step 3c" not in sr or "wos/unity-netcode-architecture.md" not in sr:
        fails.append("commands/security-review.md: lost the Step 3c multiplayer trust-boundary lens or its "
                     "citation of wos/unity-netcode-architecture.md (ADR-0131 E-1)")
    pb = read(p("commands", "performance-budget", "SKILL.md"))
    if "Networked multiplayer budget" not in pb or "wos/unity-netcode-architecture.md" not in pb:
        fails.append("commands/performance-budget/SKILL.md: lost the multiplayer budget block or its citation "
                     "of wos/unity-netcode-architecture.md (ADR-0131 E-1)")
    # E-4: no invented number. The block states every row is pending a real baseline.
    elif "PROPOSED-pending-baseline" not in pb.split("Networked multiplayer budget", 1)[1].split("- **Godot", 1)[0]:
        fails.append("commands/performance-budget/SKILL.md: the multiplayer budget block no longer marks its rows "
                     "PROPOSED-pending-baseline; no captured source supplies a bandwidth, tick-rate, or latency "
                     "figure, so a stated number there is invention (ADR-0131 E-4)")
    # E-2: the engine-neutral extraction stays rejected. Guarded because it is the one alternative
    # that would look like an improvement to a later author and reopen a decision made on evidence.
    for path in sorted(glob.glob(p("wos", "multiplayer-*.md")) + glob.glob(p("wos", "netcode-*.md"))):
        fails.append(f"{os.path.relpath(path, REPO)}: engine-neutral multiplayer extraction. ADR-0131 E-2 "
                     f"rejected it on written evidence (the engine-neutral residue is two concepts) and there "
                     f"is still one consumer; reopening it needs a superseding ADR.")
    return (not fails, fails)


def check_unity_scene_plan_gates():
    """[scenario 131] ADR-0132: unity-scene-plan keeps its two REQUIRED declarations, names its
    human-applied steps, has an inbound route, and no merged engine-axis command appears.
    """
    fails = []
    rel = os.path.join("commands", "unity-scene-plan.md")
    # os.path.exists, not read()-and-test: read() raises FileNotFoundError on a missing file, and
    # the per-check exception isolation would render that as a FAIL whose message says NameError-
    # class "defect in the check itself" instead of naming the absent command. Found by a negative
    # test that read the message rather than the header.
    if not os.path.exists(p("commands", "unity-scene-plan.md")):
        return (False, [f"{rel}: absent, but ADR-0132 G-1 ships it and implementation-plan routes to it"])
    cmd = read(p("commands", "unity-scene-plan.md"))
    for needle, why in [
        ("REQUIRED for a 3D target", "lost the render-pipeline REQUIRED marking; without it a 3D plan with no "
                                     "declared pipeline reads as complete (ADR-0132 G-2)"),
        ("REQUIRED when the feature is networked", "lost the networked-authority REQUIRED marking (ADR-0132 G-2)"),
        ("human-applied", "lost the human-applied step; the vetted MCP surface cannot apply assembly definitions, "
                          "project settings, or render-pipeline configuration, so a build stalls silently on them "
                          "(ADR-0132 G-4)"),
        ("wos/unity-mobile-rendering-and-performance.md", "no longer cites the rendering topic, orphaning it"),
        ("wos/unity-netcode-architecture.md", "no longer cites the netcode topic for the authority declaration"),
        # The 2026-08-07 dogfood's sharpest finding: without per-component authority in Step 4, a plan
        # can name a server-side input sampler and a client-side movement simulator, satisfy every other
        # rule, pass self-review, and describe a cheatable architecture. Guarded because prose that
        # survived one review can be trimmed by the next.
        ("owner-only, server-only, or everywhere", "lost the per-component authority rule in Step 4; a "
                                                   "plan can then describe a cheatable architecture and "
                                                   "still pass self-review (dogfood 2026-08-07, F-2)"),
        ("TWO trees, not one", "lost the two-tree rule in Step 3; a networked plan then merges the "
                               "runtime-spawned prefab into the scene tree, which is wrong (F-1)"),
    ]:
        if needle not in cmd:
            fails.append(f"{rel}: {why}")
    # G-3: the command must NOT assert a Unity mobile recommendation no captured page makes.
    if "do NOT assert that Unity recommends URP for mobile" not in cmd:
        fails.append(f"{rel}: lost the prohibition on asserting a Unity mobile pipeline recommendation. No "
                     f"captured page makes one; the grounded facts are HDRP's enumerated platform list and its "
                     f"compute-shader requirement (ADR-0132 G-3). Asserted as the PRESENCE of the prohibition "
                     f"rather than by scanning for the claim, because the first form matched this command's own "
                     f"negation of it.")
    # G-5: inbound route, so the command is not a flow orphan (the ADR-0127 failure).
    ip = read(p("commands", "implementation-plan.md"))
    if "unity-scene-plan" not in ip:
        fails.append("commands/implementation-plan.md: no route to unity-scene-plan, so the command is a flow "
                     "orphan and a Unity feature gets sliced before its architecture is decided (ADR-0132 G-5)")
    # ADR-0069 D-4: a merged engine-axis command is the thing D-4 forbids, distinct from a
    # capability-named sibling, which it permits.
    for path in sorted(set(glob.glob(p("commands", "scene-plan*")) + glob.glob(p("commands", "game-scene-plan*")))):
        fails.append(f"{os.path.relpath(path, REPO)}: engine-generalized scene-plan command. ADR-0069 D-4 forbids "
                     f"merging engines that share no vocabulary; capability-named siblings are what it permits.")
    return (not fails, fails)


# evals/fixtures/bug-class-dispatch: the sweep dispatch fixture family.
#
# D-3 of the 2026-08-12 bug-class-validator task says the family carries one expectation
# entry PER VARIANT and that the consumer fails when the on-disk variant set and the
# expectation set differ. "Variant" is the SIBLING families' word: description-gutted/
# and godot-tier-artifact/ put one variant per directory, so for them the on-disk set is
# a directory listing.
#
# This family has no such listing, deliberately. Its unit is a seeded CASE inside ONE
# synthetic repository, because the audit-log case IS a cross-file pair (0002 grants
# SELECT, INSERT and 0005 later grants UPDATE, DELETE) and splitting it into per-variant
# directories deletes the only thing that case tests; the fixture README carries that
# reasoning under "Why one tree instead of per-variant directories". So D-3's intent is
# implemented KEYED TO THE CASE ID, and the manifest that stands in for the directory
# listing is the README's own case table. Restructuring the fixture to match the literal
# wording would trade a real test for a matching noun.
#
# The case table is prose, so on its own it would only ever assert prose against prose.
# Three anchors keep it tied to bytes: every expectation names the tree-relative files
# its case is seeded in and they must exist, every class resolves to a real
# wos/bug-classes/ file, and every file in tree/ is either named by a case or declared
# context below. That last one is the same rule the tier gate applies one level down (a
# plan file no expectation names is a FAILURE).

# The case table writes a SHORT class label; the expected-findings table and the library
# write the full name. Neither is derivable from the other (`skill-poisoning` is not a
# prefix of `skill-context-poisoning`), so the mapping is written once and both tables
# are read through it.
_DISPATCH_CLASS_LABELS = {
    "multi-tenant": "multi-tenant-cross-agency-leak",
    "pii-encryption": "pii-encryption-boundary-leak",
    "pii-last-4": "pii-last-4-only-rule-violation",
    "skill-poisoning": "skill-context-poisoning",
    "audit-log": "audit-log-missing-append-only",
}

# One entry per seeded case. `finding` is None where the case is a control that should
# produce nothing, and a (severity, confidence) pair where the README predicts a finding.
# AL-C1 is the row that makes the distinction worth encoding: it is a CONTROL that
# correctly produces a P2, so "control" and "predicts no finding" are not the same
# predicate and a consumer that conflated them would grade a correct run as a false
# positive.
#
# `files` is written here rather than parsed out of the README's File column: that column
# is prose ("`repo-helper` pair", "`serializers/account.ts` vs `serializers/base.ts`",
# a `**` glob), and a parser for it would be inventing a grammar the fixture never
# promised. Paths are tree-relative and carry the full prefixes the README shortens.
_DISPATCH_EXPECTATIONS = {
    "MT-1": {"class": "multi-tenant-cross-agency-leak", "kind": "defect",
             "files": ("apps/web/src/server/api/orders.ts",), "finding": ("P0", "HIGH")},
    "MT-2": {"class": "multi-tenant-cross-agency-leak", "kind": "defect",
             "files": ("apps/web/src/server/api/orders.ts",), "finding": ("P0", "HIGH")},
    "MT-3": {"class": "multi-tenant-cross-agency-leak", "kind": "defect",
             "files": ("apps/web/src/models/base.ts", "apps/web/src/models/invoice.ts"),
             "finding": ("P1", "HIGH")},
    "MT-4": {"class": "multi-tenant-cross-agency-leak", "kind": "defect",
             "files": ("supabase/migrations/0001_core.sql",), "finding": ("P0", "MEDIUM")},
    "PE-1": {"class": "pii-encryption-boundary-leak", "kind": "defect",
             "files": ("apps/web/src/server/db/customers.ts",), "finding": ("P0", "HIGH")},
    "PE-2": {"class": "pii-encryption-boundary-leak", "kind": "defect",
             "files": ("apps/web/src/server/db/customers.ts",), "finding": ("P0", "HIGH")},
    "PE-3": {"class": "pii-encryption-boundary-leak", "kind": "defect",
             "files": ("supabase/migrations/0003_customers.sql",), "finding": ("P0", "HIGH")},
    "L4-1": {"class": "pii-last-4-only-rule-violation", "kind": "defect",
             "files": ("packages/api-contracts/serializers/account.ts",), "finding": ("P0", "HIGH")},
    "L4-2": {"class": "pii-last-4-only-rule-violation", "kind": "defect",
             "files": ("packages/api-contracts/serializers/account.ts",), "finding": ("P0", "HIGH")},
    "L4-3": {"class": "pii-last-4-only-rule-violation", "kind": "defect",
             "files": ("packages/api-contracts/serializers/account.ts",), "finding": ("P0", "HIGH")},
    "L4-4": {"class": "pii-last-4-only-rule-violation", "kind": "defect",
             "files": ("apps/web/src/components/checkout-review.tsx",), "finding": ("P0", "HIGH")},
    "L4-5": {"class": "pii-last-4-only-rule-violation", "kind": "defect",
             "files": ("apps/web/src/components/checkout-review.tsx",), "finding": ("P0", "HIGH")},
    "L4-6": {"class": "pii-last-4-only-rule-violation", "kind": "defect",
             "files": ("apps/web/src/server/routes/order-confirm.ts",), "finding": ("P0", "HIGH")},
    "L4-7": {"class": "pii-last-4-only-rule-violation", "kind": "defect",
             "files": ("packages/api-contracts/serializers/account.ts",
                       "packages/api-contracts/serializers/base.ts"), "finding": ("P1", "HIGH")},
    "SP-1": {"class": "skill-context-poisoning", "kind": "defect",
             "files": (".claude/skills/repo-helper/SKILL.md",), "finding": ("P0", "HIGH")},
    "SP-2": {"class": "skill-context-poisoning", "kind": "defect",
             "files": (".claude/skills/repo-helper/SKILL.md",), "finding": ("P0", "HIGH")},
    "SP-3": {"class": "skill-context-poisoning", "kind": "defect",
             "files": (".claude/skills/repo-helper/setup.js",), "finding": ("P0", "HIGH")},
    "SP-4": {"class": "skill-context-poisoning", "kind": "defect",
             "files": (".claude/skills/repo-helper/SKILL.md", ".claude/skills/repo-helper/setup.js"),
             "finding": ("P1", "MEDIUM")},
    "AL-1": {"class": "audit-log-missing-append-only", "kind": "defect",
             "files": ("supabase/migrations/0002_audit_log.sql",
                       "supabase/migrations/0005_audit_backfill.sql"), "finding": ("P0", "HIGH")},
    "AL-2": {"class": "audit-log-missing-append-only", "kind": "defect",
             "files": ("supabase/migrations/0005_audit_backfill.sql",), "finding": ("P0", "HIGH")},
    "AL-3": {"class": "audit-log-missing-append-only", "kind": "defect",
             "files": ("apps/web/src/server/db/audit-log.ts",), "finding": ("P0", "HIGH")},
    "AL-4": {"class": "audit-log-missing-append-only", "kind": "defect",
             "files": ("supabase/migrations/0002_audit_log.sql",), "finding": ("P1", "HIGH")},
    "MT-C1": {"class": "multi-tenant-cross-agency-leak", "kind": "control",
              "files": ("apps/web/src/models/invoice.ts",), "finding": None},
    "MT-C2": {"class": "multi-tenant-cross-agency-leak", "kind": "control",
              "files": ("apps/web/src/server/routes/order-confirm.ts",), "finding": None},
    "MT-C3": {"class": "multi-tenant-cross-agency-leak", "kind": "control",
              "files": ("supabase/migrations/0003_customers.sql",
                        "supabase/migrations/0004_beneficiaries.sql"), "finding": None},
    "PE-C1": {"class": "pii-encryption-boundary-leak", "kind": "control",
              "files": ("supabase/migrations/0004_beneficiaries.sql",), "finding": None},
    "PE-C2": {"class": "pii-encryption-boundary-leak", "kind": "control",
              "files": ("packages/api-contracts/serializers/beneficiary.ts",), "finding": None},
    "L4-C1": {"class": "pii-last-4-only-rule-violation", "kind": "control",
              "files": ("apps/web/src/components/payment-confirmation.tsx",), "finding": None},
    "L4-C2": {"class": "pii-last-4-only-rule-violation", "kind": "control",
              "files": ("packages/api-contracts/serializers/base.ts",), "finding": None},
    "SP-C1": {"class": "skill-context-poisoning", "kind": "control",
              "files": (".claude/skills/table-formatter/SKILL.md",
                        ".claude/skills/table-formatter/reference/columns.md"), "finding": None},
    "AL-C1": {"class": "audit-log-missing-append-only", "kind": "control",
              "files": ("supabase/migrations/0006_compliance_log.sql",), "finding": ("P2", "MEDIUM")},
}

# Files the fixture repository needs but that no case is seeded in: the tree's own label,
# the display rule a `## Retrieval` step reads so the required digit count is read rather
# than assumed, and three modules the analysis prompts pull in as context. Declared so
# that a file added to tree/ without a decision about what it is for FAILS instead of
# sitting there asserting nothing.
_DISPATCH_CONTEXT_FILES = (
    "README.md",
    "docs/pii-display-rule.md",
    "apps/web/src/server/db/client.ts",
    "apps/web/src/server/session.ts",
    "packages/api-contracts/serializers/types.ts",
)


def _md_section(text, heading):
    """Body of one `## ` section, or None when the heading is absent.

    Bounded at the next `## ` so a table in a later section cannot be read as this
    section's. Returning None rather than "" keeps a MISSING heading distinguishable from
    a section that exists and is empty; the caller reports those differently.
    """
    if heading not in text:
        return None
    return text.split(heading, 1)[1].split("\n## ", 1)[0]


def _md_rows(section):
    """Cell lists for every content row of the markdown tables in `section`.

    Header and separator rows are the caller's problem except for the separator, which
    carries no cells worth returning. A row is content when at least one cell holds
    something other than the `-`, `:` and space a separator is made of.
    """
    rows = []
    for line in section.split("\n"):
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if all(set(c) <= set("-: ") for c in cells):
            continue
        rows.append(cells)
    return rows


def check_bug_class_dispatch_cases(root=None):
    """[dispatch fixture D-3] Every seeded case in bug-class-dispatch has an expectation.

    Path-parameterized like check_godot_tier_artifact_gate(root=...), and fail-closed the
    same way: a missing fixture is a FAILURE, not an inapplicable check, because the
    fixture is what the consumer exists to execute.

    The two directions are reported separately on purpose. A case on disk with no
    expectation asserts nothing, which is the failure mode an unexecuted fixture already
    has. An expectation with no case is a prediction about something that no longer
    exists, and reads as coverage while covering nothing.

    What this check does NOT do: run repo-consistency-sweep. The severity and confidence
    columns are the fixture author's reading of the five templates, and the README says so
    plainly; nothing here upgrades them into measured behavior. What is asserted is that
    the answer key, the seeded tree, and the bug-class library still describe the same
    fixture, so the blind validation run has something coherent to grade against.
    """
    base = root or p("evals", "fixtures", "bug-class-dispatch")
    rel = os.path.relpath(base, REPO)
    readme_path = os.path.join(base, "README.md")
    tree = os.path.join(base, "tree")
    if not os.path.isdir(base):
        return (False, [f"fixture directory missing: {base}"])
    if not os.path.isfile(readme_path):
        return (False, [f"{rel}/README.md: absent, so the fixture carries no case manifest to check against"])
    if not os.path.isdir(tree):
        return (False, [f"{rel}/tree: absent, so every case below is anchored to nothing"])
    readme = read(readme_path)
    fails = []

    cases_section = _md_section(readme, "## Seeded cases")
    findings_section = _md_section(readme, "## Expected findings")
    for heading, section in (("## Seeded cases", cases_section), ("## Expected findings", findings_section)):
        if section is None:
            fails.append(f"{rel}/README.md: no '{heading}' section, so the expectation set has nothing to agree with")
    if fails:
        return (False, fails)

    seeded = {}
    for cells in _md_rows(cases_section):
        if cells[0] == "Case":
            continue
        if len(cells) < 4:
            fails.append(f"{rel}/README.md: case row {cells[0]!r} has {len(cells)} columns, expected Case, File, "
                         f"Class, Kind and a note")
            continue
        if cells[0] in seeded:
            fails.append(f"case {cells[0]}: seeded twice in the case table, so one of the two rows is unreachable")
            continue
        seeded[cells[0]] = (cells[2], cells[3])

    expected = set(_DISPATCH_EXPECTATIONS)
    for extra in sorted(set(seeded) - expected):
        fails.append(f"case {extra}: seeded in {rel}/README.md but absent from the expectation set (asserts nothing)")
    for missing in sorted(expected - set(seeded)):
        fails.append(f"case {missing}: in the expectation set but no longer seeded in {rel}/README.md")

    for cid in sorted(set(seeded) & expected):
        want = _DISPATCH_EXPECTATIONS[cid]
        label, kind = seeded[cid]
        full = _DISPATCH_CLASS_LABELS.get(label)
        if full is None:
            fails.append(f"case {cid}: class label {label!r} resolves to no full class name, so it names no "
                         f"wos/bug-classes/ file")
        elif full != want["class"]:
            fails.append(f"case {cid}: seeded under {full}, the expectation set says {want['class']}")
        if kind != want["kind"]:
            fails.append(f"case {cid}: the case table calls it a {kind}, the expectation set says a {want['kind']}")
        for path in want["files"]:
            if not os.path.isfile(os.path.join(tree, path)):
                fails.append(f"case {cid}: anchor file tree/{path} does not exist, so the case is seeded in nothing")

    for label, full in sorted(_DISPATCH_CLASS_LABELS.items()):
        if not os.path.isfile(p("wos", "bug-classes", f"{full}.md")):
            fails.append(f"wos/bug-classes/{full}.md: named by the fixture as {label!r} but absent from the library, "
                         f"so Step 4 would never dispatch that class over the tree")

    predicted = {}
    for cells in _md_rows(findings_section):
        if cells[0] == "Case":
            continue
        if len(cells) < 4:
            fails.append(f"{rel}/README.md: expected-findings row {cells[0]!r} has {len(cells)} columns, expected "
                         f"Case, Class, severity, confidence and a note")
            continue
        predicted[cells[0]] = (cells[1], cells[2], cells[3])

    want_finding = {cid: v for cid, v in _DISPATCH_EXPECTATIONS.items() if v["finding"] is not None}
    # Three distinct shapes, worded apart because they need different fixes: a real
    # disagreement about the prediction, an expectation entry that was dropped, and a
    # prediction about a case nothing seeds. Collapsing the middle one into the last
    # accuses a seeded case of not existing, which sends a reader to the wrong table.
    for extra in sorted(set(predicted) - set(want_finding)):
        if extra in _DISPATCH_EXPECTATIONS:
            fails.append(f"case {extra}: the expected-findings table predicts a finding, the expectation set "
                         f"predicts none")
        elif extra in seeded:
            fails.append(f"case {extra}: predicted in the expected-findings table but absent from the expectation set")
        else:
            fails.append(f"case {extra}: predicted in the expected-findings table but seeded by no case row")
    for missing in sorted(set(want_finding) - set(predicted)):
        fails.append(f"case {missing}: the expectation set predicts a finding, the expected-findings table has no "
                     f"row for it")
    for cid in sorted(set(predicted) & set(want_finding)):
        cls, severity, confidence = predicted[cid]
        want = _DISPATCH_EXPECTATIONS[cid]
        if cls != want["class"]:
            fails.append(f"case {cid}: the expected-findings table files it under {cls}, the expectation set says "
                         f"{want['class']}")
        if (severity, confidence) != want["finding"]:
            fails.append(f"case {cid}: the expected-findings table predicts severity {severity} confidence "
                         f"{confidence}, the expectation set predicts severity {want['finding'][0]} confidence "
                         f"{want['finding'][1]}")

    # The one number the README states in prose rather than in a table. A case added to
    # the table and to this dict would otherwise leave the sentence a grader reads
    # ("fewer than the N defect rows has a miss") quietly wrong.
    defects = sum(1 for v in _DISPATCH_EXPECTATIONS.values() if v["kind"] == "defect")
    stated = re.search(r"fewer than the (\d+) defect rows", readme)
    if stated is None:
        fails.append(f"{rel}/README.md: the sentence stating how many defect rows a run must report is gone, so a "
                     f"grader has no miss threshold")
    elif int(stated.group(1)) != defects:
        fails.append(f"{rel}/README.md: prose says {stated.group(1)} defect rows, the expectation set carries "
                     f"{defects}")

    named = {f for v in _DISPATCH_EXPECTATIONS.values() for f in v["files"]} | set(_DISPATCH_CONTEXT_FILES)
    on_disk_files = set()
    for dirpath, _dirs, filenames in os.walk(tree):
        for filename in filenames:
            # .DS_Store is a Finder artifact, never fixture content; it appears from
            # merely opening the directory and would fail the check on the machine that
            # looked rather than on the change that broke something. Nothing else hidden
            # is skipped: a hidden file IS a shape this fixture's poisoning class covers.
            if filename == ".DS_Store":
                continue
            on_disk_files.add(os.path.relpath(os.path.join(dirpath, filename), tree))
    for extra in sorted(on_disk_files - named):
        fails.append(f"tree/{extra}: in the fixture repository but named by no case and not declared context, so "
                     f"nothing says what it is there to do")
    for missing in sorted(set(_DISPATCH_CONTEXT_FILES) - on_disk_files):
        fails.append(f"tree/{missing}: declared as fixture context but absent, so the case that reads it for context "
                     f"reads nothing")
    return (not fails, fails)


def check_fanout_floor_consistency(root=None):
    """[ADR-0173] One fan-out floor, named once and agreed to everywhere.

    Three numbers claimed to be the floor before this existed: the spec said 5 in two
    sentences, ADR-0039 said 10 about a different unit, and the seven fleet commands
    declared 3, 4 and 6. A reader had three answers and no way to pick.

    The floor is read from wos/workflow-patterns.md, so moving it is a one-line edit
    and this check finds whatever stopped agreeing. A command whose threshold cannot
    be parsed fails the same way one below the floor does: an unverifiable threshold
    is not better than a wrong one.
    """
    root = root or _repo()
    fails = []
    body = read(os.path.join(root, "wos/workflow-patterns.md"))
    m = re.search(r"The fan-out floor is (\d+)", body)
    if not m:
        return (False, ["wos/workflow-patterns.md: no 'The fan-out floor is N' line to read the floor from"])
    floor = int(m.group(1))

    spec = read(os.path.join(root, SPEC_PATH))
    if not re.search(rf"{floor} or more independent items", spec):
        fails.append(f"{SPEC_PATH}: '### When to use' does not say '{floor} or more independent items'")
    if not re.search(rf"Fewer than {floor} items", spec):
        fails.append(f"{SPEC_PATH}: '### When NOT to use' does not say 'Fewer than {floor} items'")

    # Exceptions are registered under a heading, with a reason. A bare mention of a
    # command name elsewhere in the file does not exempt it.
    parts = body.split("### Registered exceptions", 1)
    registered = set()
    if len(parts) > 1:
        registered = set(re.findall(r"`([a-z0-9-]+-fleet)`", parts[1].split("\n## ", 1)[0]))

    threshold = re.compile(r"N >= (\d+)|(\d+) or more|wave of (\d+)")
    # A section-presence rule is not a dispatch floor. external-research-fleet says
    # "`## Conflicts surfaced` section present when N >= 1 CONTRADICTING group", and
    # reading that as a threshold of 1 is the exact mistake the audit map made before
    # this check existed. Skip the lines that describe whether a section appears.
    presence = re.compile(r"section present|section absent|present when|absent otherwise", re.I)
    for path in sorted(glob.glob(os.path.join(root, "commands/*-fleet.md"))):
        name = os.path.basename(path)[:-3]
        found = [int(g) for line in read(path).splitlines() if not presence.search(line)
                 for mm in threshold.finditer(line) for g in mm.groups() if g]
        if not found:
            fails.append(f"commands/{name}.md: no parseable fan-out threshold")
            continue
        lowest = min(found)
        if lowest < floor and name not in registered:
            fails.append(f"commands/{name}.md: fans out at {lowest}, below the floor of {floor}, "
                         f"and is not in the '### Registered exceptions' list of wos/workflow-patterns.md")
    return (not fails, fails)


def check_internal_refs_annotated(root=None):
    """[H13] Every live reference to _internal/ says what _internal/ is.

    _internal/ is gitignored, so it does not exist in a fresh clone. A line that
    sends a reader there without saying so sends them to a path that is not on
    their disk, and the reader has no way to tell that from a broken reference.

    The scan set is deliberately narrow: the docs a user reads and the templates
    they fill in. It does NOT include docs/adr/ or CHANGELOG.md, which are frozen
    historical record. Widening it there would paint the guard red over text nobody
    may edit, and a guard that is red by design becomes a waiver on its first day.

    ROADMAP.md joined on 2026-09-23 (docs drift audit, gap 9). It was left out as
    history, but its open items are what a new reader acts on, and the audit found
    unannotated `_internal/` pointers there (06#7) that this guard never read. It is
    edited like any live document, so it can be held to the rule.

    This checks TEXT only. A script that WRITES into _internal/ still breaks on a
    clone; that is the fallback the same wave installed in the three scripts that
    did, and it is a different failure with a different fix.
    """
    root = root or _repo()
    scan = []
    for pattern in ("wos/*.md", "templates/*.md"):
        scan.extend(sorted(glob.glob(os.path.join(root, pattern))))
    for named in ("evals/README.md", "evals/skill-evals/README.md", "README.md",
                  "AGENTS.md", "docs/FAQ.md", "docs/MIGRATION.md", "CONTRIBUTING.md",
                  "ROADMAP.md"):
        path = os.path.join(root, named)
        if os.path.exists(path):
            scan.append(path)

    fails = []
    for path in scan:
        rel = os.path.relpath(path, root)
        for n, line in enumerate(read(path).splitlines(), 1):
            if "_internal/" not in line:
                continue
            low = line.lower()
            if "gitignored" in low or "maintainer-local" in low:
                continue
            fails.append(f"{rel}:{n}: names _internal/ without saying it is maintainer-local "
                         f"and gitignored: {line.strip()[:90]!r}")
    return (not fails, fails)


OLD_REPO_NAME = "my_work_tasks"
OLD_REPO_NAME_DIRS = ("commands", ".claude/skills", "wos", "templates", "scripts")
OLD_REPO_NAME_EXEMPT_DIRS = ("docs", "evals")
OLD_REPO_NAME_EXEMPT_FILES = ("CHANGELOG.md", "CLAUDE.md")


def _old_repo_name_scope(rel):
    """True when a repo-relative path is in the set the old-name check reads."""
    rel = rel.replace(os.sep, "/")
    if rel in OLD_REPO_NAME_EXEMPT_FILES:
        return False
    if any(rel == d or rel.startswith(d + "/") for d in OLD_REPO_NAME_EXEMPT_DIRS):
        return False
    if any(rel.startswith(d + "/") for d in OLD_REPO_NAME_DIRS):
        return True
    return rel.endswith(".md")


def _old_repo_name_candidates(root):
    """Tracked files when root is the top of a git work tree, else a walk.

    A walk of the real checkout would read what git ignores (projects/, USER_MEMORY.md,
    the retention sidecar, agent worktrees), none of which reaches the public tree, and
    would fail on text nobody is asked to change. A fixture is not a work tree, so it is
    walked; the same scope filter applies to both.
    """
    import subprocess
    try:
        top = subprocess.run(["git", "-C", root, "rev-parse", "--show-toplevel"],
                             capture_output=True, text=True, check=True).stdout.strip()
        if os.path.realpath(top) == os.path.realpath(root):
            out = subprocess.run(["git", "-C", root, "ls-files", "-z"],
                                 capture_output=True, check=True).stdout
            return [f for f in out.decode("utf-8").split("\0") if f]
    except (OSError, subprocess.CalledProcessError):
        pass
    found = []
    for dirpath, dirs, filenames in os.walk(root):
        dirs[:] = [d for d in dirs if d not in (".git", "projects", "_internal", "node_modules")]
        for name in filenames:
            found.append(os.path.relpath(os.path.join(dirpath, name), root))
    return found


def check_private_repo_name_absent(root=None):
    """[D-10] The staging repository's old name is gone from the tree that ships.

    The private repository used to be called `my_work_tasks`. Commands, skills, wos
    topics, templates, scripts and the root docs named it as if every reader had that
    checkout; they now say the workflow repository or the task repository (ADR-0129
    tells the two apart). The scope is the one the slice's exit criterion greps:
    docs/, evals/, CHANGELOG.md and CLAUDE.md are left out because ADRs and the
    changelog are frozen history, scenarios quote the old wording, and CLAUDE.md is
    maintainer memory that never reaches the public tree (ADR-0090).
    """
    root = root or _repo()
    fails = []
    scanned = 0
    for rel in sorted(_old_repo_name_candidates(root)):
        if not _old_repo_name_scope(rel):
            continue
        path = os.path.join(root, rel)
        try:
            with open(path, "r", encoding="utf-8") as fh:
                text = fh.read()
        except (UnicodeDecodeError, FileNotFoundError, IsADirectoryError):
            continue
        scanned += 1
        for n, line in enumerate(text.splitlines(), 1):
            if OLD_REPO_NAME in line:
                fails.append(f"{rel}:{n}: names the private repository `{OLD_REPO_NAME}`; "
                             f"say the workflow repository or the task repository: "
                             f"{line.strip()[:90]!r}")
    if scanned == 0:
        fails.append("no files in scope to scan; the check lost its subject")
    return (not fails, fails)


# The inventory a future merge has to prove itself against. Two literal lists, not a
# derivation: the point is that a code or a rule cannot vanish quietly while the prose
# around it is rewritten, and a derived list would rederive itself from the file being
# emptied. Satisfied by presence in ANY runtime-verify command or ANY adapter topic,
# which is exactly what lets wave 8 merge the four commands without loss.
RUNTIME_TAXONOMY = {
    "app": ["NATIVE_CRASH", "NAVIGATION_TEARDOWN", "JS_ERROR", "MISSING_NATIVE_MODULE",
            "STARTUP_CRASH", "LAUNCH_INTENT_LOST", "ANR", "PERMISSION_OR_CONFIG", "CLEAN",
            "MANAGED_EXCEPTION"],
    "web": ["PAGE_IDENTITY_MISMATCH", "SERVE_FAILURE", "CONSOLE_ERROR", "OVERFLOW",
            "FOCUS_DEFECT", "A11Y_VIOLATION", "PERF_MEASUREMENT", "CLEAN"],
    "api": ["UNREACHABLE", "STATUS_MISMATCH", "CONTENT_TYPE_MISMATCH", "SHAPE_MISMATCH",
            "AUTH_BOUNDARY", "ERROR_LEAK", "EFFECT_NOT_OBSERVED", "LATENCY_MEASUREMENT",
            "CLEAN"],
    "godot": ["SCRIPT_ERROR", "MISSING_NODE_OR_RESOURCE", "SIGNAL_NOT_CONNECTED",
              "NULL_REFERENCE", "PHYSICS_OR_COLLISION", "INPUT_NOT_MAPPED",
              "PERFORMANCE_STALL", "STATE_INVARIANT_VIOLATION", "TRANSPARENCY_SORTING",
              "RENDERER_TIER_MISMATCH", "CLEAN"],
}

RUNTIME_NAMED_RULES = ["cold-start", "warm-only", "minimum frame set", "clean persisted state",
                       "ephemeral free port", "G2 recovery rule", "320, 768, 1280 and 2560",
                       "n/a (tool absent)", "WEB_RUNTIME_VERIFY_SHOTS/", "blast radius",
                       "failure path", "the confirming read", "probes/", "get_tree().quit()",
                       "adversarial", "PLAYTEST_RUNBOOK.md"]


def check_runtime_verify_parity(root=None):
    """[scenario 140] Every runtime taxonomy code and every named battery rule inventoried
    before the extraction is still present on disk, in a command file or in an adapter topic.

    ADR-0177 moved four adapter layers out of four commands and into four wos/ topics. The
    risk in that move, and in the merge it enables, is losing capability inside prose that
    reads as boilerplate. This is the inventory that makes a later merge prove preservation
    instead of assuming it: a code satisfied by ANY of the eight files is a code that
    survived the move, wherever it now lives.
    """
    root = root or _repo()
    scan = sorted(glob.glob(os.path.join(root, "commands", "*runtime-verify.md"))) + \
           sorted(glob.glob(os.path.join(root, "wos", "*-runtime-battery.md")))
    if not scan:
        return (False, ["commands/*runtime-verify.md and wos/*-runtime-battery.md: neither "
                        "surface exists, so the parity inventory has nothing to check against"])
    corpus = "\n".join(read(f) for f in scan)
    fails = []
    for surface in sorted(RUNTIME_TAXONOMY):
        for code in RUNTIME_TAXONOMY[surface]:
            if code not in corpus:
                fails.append(f"{surface} taxonomy code {code} is in no runtime-verify command "
                             f"and in no adapter topic; the classification it named can no "
                             f"longer be emitted")
    for rule in RUNTIME_NAMED_RULES:
        if rule not in corpus:
            fails.append(f"named battery rule {rule!r} is in no runtime-verify command and in "
                         f"no adapter topic; a rule nothing states is a rule nothing runs")
    return (not fails, fails)


def check_experience_verdict_attester(root=None):
    """[ADR-0179] The experience-verdict floor names its attester, and never claims a human.

    The floor used to contradict itself inside one paragraph: machine-green evidence SHALL NOT
    substitute for the human verdict, and, two sentences later, on attended Express the floor
    stands down because "that commit is the attester". A commit the agent created IS machine
    evidence, so the paragraph forbade the substitution and performed it. ADR-0179 resolves it by
    recording WHO attested rather than requiring a person: `Attested by: run` when the block cites
    what the run captured, `Attested by: human` when a person looked.

    This asserts the shape that resolution depends on. It reads the SOURCE, `wos/closure-floors.md`,
    because the per-command views are generated from it and a drift between them is what
    build-closure-floor-views.py --check already covers.
    """
    base = root or _repo()
    path = os.path.join(base, "wos", "closure-floors.md")
    if not os.path.isfile(path):
        return (False, [f"{path}: missing"])
    body = read(path)
    fails = []

    # An empty read is a failure, not a vacuous pass: this file carries floors today.
    if "Experience-verdict floor" not in body:
        return (False, ["wos/closure-floors.md: no experience-verdict floor found; the check lost "
                        "its subject rather than the subject becoming clean"])

    variants = body.count("**Experience-verdict floor")
    if variants < 3:
        fails.append(f"wos/closure-floors.md: {variants} experience-verdict variant(s), expected the "
                     f"three closure homes (inline-close, slice-closure, task-close)")

    attested = body.count("`Attested by:` line valued `run` or `human`")
    if attested != variants:
        fails.append(f"wos/closure-floors.md: {attested} variant(s) require an `Attested by:` line, "
                     f"{variants} exist; a variant without it lets `Overall: PASS` stand with no "
                     f"recorded attester, which is the 2026-07-10 defect")

    # The false claim must not come back, in either half.
    for dead, why in [
        ("that commit is the attester",
         "a commit the agent created is machine evidence, so this sentence performs the substitution "
         "the same paragraph forbids (ADR-0179)"),
        ("stands down in favor of the local commit",
         "the Express stand-down keyed the requirement to the pipeline rather than to what was "
         "verified; ADR-0179 removed it"),
    ]:
        if dead in body:
            fails.append(f"wos/closure-floors.md: {dead!r} is back. {why}")

    # The half that stays true must stay.
    if body.count("SHALL NOT substitute for the human verdict") != variants:
        fails.append("wos/closure-floors.md: the 'SHALL NOT substitute for the human verdict' clause "
                     "is missing from a variant; ADR-0179 keeps it, because under it machine evidence "
                     "no longer pretends to be a human verdict")

    # The vocabulary word, and it must be one the vocabulary defines.
    gate = os.path.join(base, "wos", "gate-conditions.md")
    if os.path.isfile(gate) and "Attester class: <agnostic | environment-bound | human-bound>" not in read(gate):
        fails.append("wos/gate-conditions.md: the Attester class vocabulary line moved or changed; "
                     "this check keys on it")
    if "Attester class: human-bound" in body:
        fails.append("wos/closure-floors.md: an experience floor is human-bound again; ADR-0179 made "
                     "the experience-verdict floor agnostic about WHO attests and strict about it "
                     "being recorded")

    # The Godot feel-verdict floor is a different floor and stays human-bound. Asserting that here
    # keeps this change from being read as a blanket removal of human attestation.
    plat = os.path.join(base, "wos", "platform-runtime-floors.md")
    if os.path.isfile(plat) and "Attester class: human-bound" not in read(plat):
        fails.append("wos/platform-runtime-floors.md: the Godot feel-verdict floor is no longer "
                     "human-bound; ADR-0179 explicitly did not touch it, because whether a build "
                     "FEELS right is not something a run can capture")

    return (not fails, fails)


CHECKS = [
    ("corpus-wellformed", "scenario corpus", "every scenario has a goal, criteria, and a FAIL section", check_corpus_wellformed),
    ("corpus-indexed", "scenario corpus", "every scenario is linked from evals/README.md", check_corpus_indexed),
    ("scenario-numbers-unique", "scenario corpus", "no two scenarios claim the same number", check_scenario_numbers_unique),
    ("walker-covers-corpus", "scenario corpus", "run-evals.sh enumerates every scenario in the corpus", check_walker_covers_corpus),
    ("handoff-basenames", "scenario 85", "every Run now: in a command names a real command", check_handoff_basenames),
    ("tier-routing-closure", "ADR-0084", "no command routes UNCONDITIONALLY to a target missing one of the router's own tiers; a gated route into an opt-in cluster is compliant", check_tier_routing_closure),
    ("skill-load-budget", "scenario 116", f"no generated skill exceeds the {LOAD_CEILING_CHARS}-char Load-stage ceiling (ADR-0116, hard fail), and one within {LOAD_WARN_BAND_CHARS} chars of it is named", check_skill_load_budget),
    ("skill-load-ceiling-slack", "scenario 116", f"the Load-stage ceiling sits no more than {LOAD_SLACK_CHARS} chars above the largest skill, so a finished trim lowers it (ADR-0227, hard fail)", check_skill_load_ceiling_slack),
    ("advertise-stage-budget", "scenario 132", "the Advertise stage (98 skill descriptions, injected every run) stays under the 21000-token aggregate budget (ADR-0135, hard fail)", check_advertise_stage_budget),
    ("substrate-emit-full-schema", "ADR-0034", "the shared block's hand-rolled emit teaches every field verify-log-validator.py requires; 29 commands cite that block, so a dropped field teaches 29 commands to emit invalid lines", check_substrate_emit_teaches_full_schema),
    ("declared-event-in-taxonomy", "ADR-0034", "every `event=` a command declares emitting is in the canonical taxonomy; a negative mention that teaches the pattern stays legal", check_declared_event_in_taxonomy),
    ("canonical-not-loaded-with-views", "ADR-0138", "nothing orders the canonical file loaded once per-consumer views exist; the spec governs 98 commands and nothing else reads it", check_canonical_not_loaded_when_views_exist),
    ("design-grounding-coverage", "ADR-0043", "commands that decide against an external contract carry the design gate; the execution gate refuses mid-slice, long after the plan naming that contract was approved", check_design_grounding_coverage),
    ("omitted-variant-no-rule", "ADR-0138", "a variant the generator drops as empty carries no normative text; the independent half of the equivalence check, which shares its `None.` predicate with the generator and so cannot question it", check_omitted_variant_carries_no_rule),
    ("closure-view-equivalence", "ADR-0138", "each generated closure view carries exactly its consumer's normative text from the canonical file, preamble included; a dropped floor is a closure gate that stops firing silently", check_closure_view_equivalence),
    ("unconditional-load-declared", "ADR-0006", "a load the prose calls unconditional is declared in frontmatter, so the real per-invocation cost is measurable instead of inferred from wording; both directions fail", check_unconditional_load_declared),
    ("real-load-advisory", "ADR-0116", "ADVISORY: reports the real per-invocation load with declared inclusions counted, plus how many skills exceed the 5,000-token re-injection cap", check_real_load_advisory),
    ("wos-topic-reachable", "ADR-0006", "every lazy wos/ topic is reachable from the read map, a command, a scenario, an ADR, or a sibling topic; generalizes the two engine-scoped globs that covered 7 of 47", check_wos_topic_reachable),
    ("task-state-template-sync", "ADR-0111", "the TASK_STATE template and task-init's inline 20-section structure stay identical in name AND order; the extraction created a second place that can drift", check_task_state_template_sync),
    ("spine-reads-operating-mode", "scenario 08", "spine readers after task-init carry the ADR-0162 Resume notes operating-mode bullet; declared strict forbids the Express inline Approval log", check_spine_reads_operating_mode),
    ("no-retired-tier-condition", "ADR-0207", "no live document gates behavior on a tier name the pipeline no longer writes (Express, Standard, Disciplined or Strict as a tier, a tier heading, or `complexity_tier`); a rule keyed on one cannot be true after ADR-0207", check_no_condition_on_a_retired_tier_name),
    ("artifact-totals-are-markers", "ADR-0029", "a total of commands, topics, ADRs, scenarios, bug classes, skills, fleets or personas in the count scan-set is a count marker, and a CI job count matches lint.yml", check_artifact_totals_are_markers),
    ("command-flags-in-stub-table", "C32, docs drift audit gap 8", "every backticked --flag a command names is its row in the COMMAND_PROMPT_STUBS.md flag table, another listed command's flag named on the same line, or a recorded tool option; and every row's flag still appears in its command", check_command_flags_in_stub_table),
    ("index-tables-whole", "docs drift audit gap 10", "the scenario index in evals/README.md and the ADR index are each one unbroken table whose every row has the header's cell count", check_index_tables_whole),
    ("installer-flags-documented", "docs drift audit gap 11", "no line presents --with-skills as required, every installer flag a document or script tells people to type is one the parser accepts, and usage() lists every accepted flag", check_installer_flags_documented),
    ("no-mode-gate-phrasing", "ADR-0199, ADR-0220", "no live document states the retired editor-mode write gate in any of the phrasings found on disk; only compact-task-memory keeps it", check_no_mode_gate_phrasing),
    ("task-memory-every-mode", "ADR-0199", "no command conditions APPLIED on the mode in its Artifact changes line, outside two named pending cases, and the spec and FAQ no longer describe the removed write gate as current", check_task_memory_written_in_every_mode),
    ("agent-directive-copies-match", "B17", "AGENTS.md carries the directive template's block byte for byte and CLAUDE.md its first paragraph", check_agent_directive_copies_match),
    ("one-slice-route", "ADR-0225", "the one-slice route writes both lock signals the attended lock reads, implement-approved-slice runs check-doc-sync.sh --against HEAD at inline close and routes its exit 1, autonomous-run refuses a route line, and the lint runs the mode", check_one_slice_route),
    ("projects-ignore-in-creators", "ADR-0223", "both commands that create projects/ carry the self-ignoring projects/.gitignore rule, and task-init checks an existing tree", check_projects_ignore_in_creators),
    ("default-skill-roots-agree", "ADR-0228", "the installer usage, README, FAQ and MIGRATION name the same default skill roots, and none of those documents calls another root a default", check_default_skill_roots_agree),
    ("mcp-routing-view-matches", "B32", "the lazy wos copy task-init reads for its MCP seed is byte-identical to the shared block the other three consumers inline", check_mcp_routing_view_matches),
    ("output-blocks-name-fields", "scenario 137", "the shared Handoff block names its four lines and the Artifact changes block requires a label on every file, in Lean output too; both used to point at the spec only, and runs dropped a field", check_output_blocks_name_their_fields),
    ("workflow-root-scripts-ship", "ADR-0218", "every script a command resolves against the workflow root is in SHIPPED_SCRIPTS, so an install has it; the outcome helper and the ASI06 ingest scan were both promised and shipped by nothing", check_workflow_root_scripts_ship),
    ("outcome-ledger-written", "ADR-0217", "every command that runs compute-task-outcome.py appends its printed line to OUTCOMES.jsonl on the same line, and the helper ships in the install payload; its exit 0 alone is not a write", check_outcome_ledger_is_written),
    ("memory-consume-path", "ADR-0214", "the memory consume path the August research concluded on is wired: task-init links REFERENCES without reading it, resolves the learnings ranker against the workflow root, impact-analysis reads prior analyses, memory-lint keeps Tags optional, and the ranker ships", check_memory_consume_path),
    ("cwe-mapping-allowed", "ADR-0213", "no bug-class template maps to a CWE MITRE marks Prohibited; Discouraged ones are reported and do not fail the build", check_cwe_mapping_allowed),
    ("scan-stamp-covers-claims", "ADR-0212", "no file's `Last scanned:` stamp is newer than a section heading that dates itself; check-doc-currency.sh reads the stamp's age and cannot see what it covers", check_scan_stamp_covers_its_claims),
    ("attended-chain-self-runs", "ADR-0208", "the attended chain runs without a human turn: the spec keeps the continuation rule and the plan-approval exclusion, approve-plan names no wait, and the task record carries the disqualifier rather than the retired tier label", check_attended_chain_self_runs),
    ("apply-commits-after-display", "scenario 125", "attended --apply creates the local commit after the staged display; the retired same-turn confirmation rule must not return (ADR-0163)", check_apply_commits_after_display),
    ("bare-commit-tree-proof", "ADR-0167", "the --apply commit is bare, proven by tree hash, and refuses an unnamed default branch", check_bare_commit_tree_proof),
    ("highest-adr-claim", "ADR-0136", "prose naming the highest ADR number matches disk; the count-marker guard checks the number inside the marker and is blind to the sentence around it", check_highest_adr_claim),
    ("wizard-profile-set", "ADR-0059", "no literal PROFILE= assignment escapes the default, the --profile flag, and set_profile(); a bare assignment in a wizard case branch leaves PROFILE_SET at 0, so the chosen profile governs the command list while every skill is installed anyway", check_wizard_sets_profile_set),
    ("supersession-marked", "ADR-0029", "an ADR that declares it supersedes another is named in that target's Status line; a reader who opens the superseded file otherwise follows a decision that no longer holds", check_supersession_marked),
    ("read-map-headings-resolve", "ADR-0006", "every section the always-read Minimum read map orders resolves to a real heading, in the spec or in the wos/ topic named on the same row; doc-sync only scans lines that name the spec file, so the map's own rows were never checked", check_read_map_headings_resolve),
    ("spec-size-budget", "scenario 134", "the always-read WORKFLOW_OPERATING_SYSTEM.md stays under a non-regression size ceiling; the system layer was the last always-paid surface with no budget (ADR-0136, hard fail)", check_spec_size_budget),
    ("bootstrap-floor-measured", "ADR-0012", "the bootstrap floor declared in the shared block equals the measured size of the four always-read spec sections; the third always-paid surface stops being governed by prose", check_bootstrap_floor_measured),
    ("leaf-reviewer-tier", "ADR-0226", "the blinded reviewer reads only `## Global output contract` plus its rubric: the bootstrap block names the tier and its measured figure, exactly the commands it names declare it, and the reviewer's and both dispatchers' isolation clauses are unchanged", check_leaf_reviewer_tier),
    ("description-reference-preservation", "scenario 133", "every skill description's cross-references MATCH the baseline: a drop is the regression, an addition means the baseline is stale and would stop protecting that reference (ADR-0135 item 2, D-4)", check_description_reference_preservation),
    ("description-capability-floor", "scenario 133", "every skill description keeps a capability segment of at least 150 chars and a `Do not use` routing marker; the marker is what makes the segment measurable, so dropping it is a total bypass (ADR-0135 item 2, D-6)", check_description_capability_floor),
    ("runtime-verify-parity", "scenario 140", "every runtime taxonomy code and every named battery rule inventoried before the extraction is still present on disk, in a command file or in an adapter topic", check_runtime_verify_parity),
    ("experience-verdict-attester", "ADR-0179", "the experience-verdict floor names its attester in every variant and never claims a human verdict no person reached; the Express stand-down and the commit-is-the-attester claim stay gone", check_experience_verdict_attester),
    ("no-retired-token-budget-field", "scenario 116", "no command frontmatter, generated skill, or lint validator references the retired token-budget field", check_no_retired_frontmatter_field),
    ("required-sections", "required-section scenarios", "every command has a Handoff and a Definition of done with items in it", check_required_sections),
    ("command-frontmatter", "frontmatter scenarios", "every command's frontmatter name equals its basename", check_command_frontmatter_name),
    ("registry-membership", "registry scenarios", "every command appears in all three registries, matched on the line form lint uses", check_registry_membership),
    ("structured-output-path", "ADR-0158", "a command mandating StructuredOutput names the dispatch path that has it, and no command carries a bare artifact= mandate", check_structured_output_names_its_path),
    ("count-markers", "count-marker scenarios", "every count marker equals the on-disk count", check_count_markers),
    ("adr-indexed", "ADR index scenarios", "every ADR file has a row in docs/adr/README.md", check_adr_indexed),
    ("no-emdash", "forbidden-bytes scenarios", "no em-dash in commands, shared blocks, wos topics, templates, ADRs, or root docs", check_no_emdash),
    ("shared-block-sources", "shared-block scenarios", "every <!-- shared:X --> has a canonical source", check_shared_block_sources),
    ("epistemic-doctrine-surfaces", "scenarios 110, 112", "the ADR-0109 doctrine surfaces exist and claim-grounding covers the universal command layer", check_epistemic_doctrine_surfaces),
    ("confidence-carveout", "ADR-0109", "the commands the Part 1.3 carve-out names are exactly the commands that declare a graded confidence field, so neither the list nor the corpus can drift past the other", check_confidence_carveout_matches),
    ("commit-evidence-apply-route", "ADR-0084, ADR-0133, ADR-0197", "every commit-evidence floor home routes attended runs and external execution layers to their reachable evidence paths, while direct-use autonomous-run records bounded deferral", check_commit_evidence_routes_to_apply),
    ("floor-attester-class", "scenario 127", "every closure floor declares exactly one attester class, scanned structurally rather than by header text", check_floor_attester_class),
    ("godot-tier-artifact-gate", "ADR-0119", "the tier floor fails closed on every fixture directory on disk, decoy and near misses included", check_godot_tier_artifact_gate),
    ("bug-class-dispatch-cases", "dispatch fixture D-3", "every case seeded in evals/fixtures/bug-class-dispatch has one expectation entry, anchored to the files it is seeded in and to a real bug-class file; both directions fail", check_bug_class_dispatch_cases),
    ("godot-tier-floor-variants", "ADR-0119", "the tier floor keeps its variants and every command it names a variant for cites it", check_godot_tier_floor_variants),
    ("godot-tier-gate", "scenario 117", "godot-scene-plan requires a declared renderer tier on a 3D plan (ADR-0117 D-9)", check_godot_tier_gate),
    ("godot-dimension-routing", "scenario 117", "no command names 2D as a default dimension", check_godot_dimension_routing),
    ("godot-3d-topics-indexed", "scenario 117", "every wos/godot-3d-*.md is in the read map, the map cites nothing absent from disk, and no 3D topic copies a sentence from any other Godot topic", check_godot_3d_topics_indexed),
    ("unity-no-new-command", "scenario 129", "no engine-named Unity command exists (ADR-0130 D-5)", check_unity_no_new_command),
    ("unity-adapter-surface", "scenario 129", "app-runtime-verify carries the Unity adapter and test-strategy routes Unity, both citing their topics (ADR-0130 D-4)", check_unity_adapter_surface),
    ("store-integrity-engine-agnostic", "scenario 129", "the store-integrity bug-class stays widened rather than forked per engine (ADR-0130 D-3)", check_store_integrity_engine_agnostic),
    ("unity-scene-plan-gates", "scenario 131", "unity-scene-plan keeps its two REQUIRED declarations, its human-applied step, and an inbound route (ADR-0132)", check_unity_scene_plan_gates),
    ("unity-multiplayer-surface", "scenario 130", "multiplayer is one Unity-scoped topic plus two conditional blocks, with no engine-neutral extraction (ADR-0131)", check_unity_multiplayer_surface),
    ("fanout-floor-consistency", "ADR-0173", "the fan-out floor is named once in wos/workflow-patterns.md and the spec and every fleet command agree with it, or the exception is registered", check_fanout_floor_consistency),
    ("internal-refs-annotated", "H13", "every live reference to the gitignored _internal/ says so, in the docs and templates a user reads; the frozen historical record is out of scope on purpose", check_internal_refs_annotated),
    ("private-repo-name-absent", "D-10", "no command, skill, wos topic, template, script or root doc names the staging repository's old name; docs/, evals/, CHANGELOG.md and CLAUDE.md are history or maintainer memory and stay out", check_private_repo_name_absent),
    ("scenario-content-floor", "scenario 138", "every scenario clears a per-file character floor and the corpus clears a mean floor, so emptying the corpus fails the build instead of passing every presence-only check", check_scenario_content_floor),
    ("criteria-content-floor", "scenario 138", "every scenario's criteria section holds at least three enumerable checks, so a rubric cannot decay into a paragraph the grader cannot score", check_criteria_content_floor),
    ("unity-topics-indexed", "scenario 129", "every wos/unity-*.md is in the read map, the map cites nothing absent from disk, and no Unity topic copies a sentence from a Godot or RN topic", check_unity_topics_indexed),
]


def main():
    print("Structural evals: the automatable subset of the scenario regression net.")
    print("(This does NOT run a model; it asserts the repo invariants a subset of scenarios depend on.)")
    print("=" * 78)
    total = len(CHECKS)
    passed = 0
    any_fail = False
    for cid, scen, desc, fn in CHECKS:
        # Per-check exception isolation (S4 of the 2026-07-26 tier-gate task).
        # Without this, one raising check aborts the whole loop and every check
        # after it is silently never run: the suite reports nothing and exits on
        # a traceback, which reads as infrastructure noise rather than as a
        # failing invariant. A raiser is a FAILURE of that check, not a reason to
        # stop asserting the others.
        try:
            ok, fails = fn()
        except MissingArtifact as exc:
            # Named separately from the generic handler below: an absent artifact is
            # the repo's problem and the message must name the file, not accuse the
            # checker. The check still FAILS, which is the fail-closed behaviour a
            # missing subject has to have.
            ok, fails = False, [
                f"{exc.path}: required by this check and absent from the tree; the "
                f"check lost its subject rather than the subject becoming clean",
            ]
        except Exception as exc:  # noqa: BLE001 - a check may raise anything
            ok, fails = False, [
                f"check raised {type(exc).__name__}: {exc}",
                "this is a defect in the check itself, not necessarily in the repo",
            ]
        # A check can PASS with findings: warn-only checks (per D-4/TEST_STRATEGY,
        # a known gap that is reported but does not fail the build yet) return
        # ok=True with a non-empty findings list. That prints as WARN so the
        # finding stays visible without turning CI red over an accepted gap.
        if not ok:
            status = "FAIL"
        elif fails:
            status = "WARN"
        else:
            status = "PASS"
        print(f"[{status}] {cid:<22} ({scen}): {desc}")
        if not ok:
            any_fail = True
            for line in fails[:20]:
                print(f"         - {line}")
            if len(fails) > 20:
                print(f"         ... and {len(fails) - 20} more")
        else:
            passed += 1
            if fails:
                for line in fails[:20]:
                    print(f"         - {line}")
                if len(fails) > 20:
                    print(f"         ... and {len(fails) - 20} more")
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
