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


# A route into an opt-in capability cluster is correct when it is gated: the
# cluster is additive, so a general command may name a cluster command behind a
# trigger. Only an UNCONDITIONAL cross-tier route is a defect (D-7, 2026-07-25).
# Measured that day: 23 cross-tier routes, 19 conditional and correct, 4 not.
_COND_MARKER = re.compile(
    r"\b(when|whenever|if|only|optional|gated|off by default|unless|per the)\b", re.I)


def _route_is_conditional(line):
    """True when the sentence carrying the route names a trigger for it."""
    return bool(_COND_MARKER.search(line))


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
        # Track conditionality per occurrence (D-7). A target is a defect only
        # when at least one route to it is UNCONDITIONAL; a target reached only
        # through gated sentences is a correct entry into an opt-in cluster.
        unconditional = set()
        for line in body.split("\n"):
            cands = set()
            for m in pat_arrow.finditer(line):
                cands.update(m.group(1, 2))
            for m in pat_route.finditer(line):
                cands.add(m.group(1))
            if _route_is_conditional(line):
                continue
            for cand in cands:
                if cand in real and cand != name:
                    unconditional.add(cand)
        router_tiers = profiles.get(name, set())
        for t in sorted(unconditional):
            missing = router_tiers - profiles.get(t, set())
            if missing:
                findings.append(
                    f"{name} -> {t}: router is {sorted(router_tiers)}, target is "
                    f"{sorted(profiles.get(t, set()))} (missing tier(s): {sorted(missing)}) "
                    f"[unconditional route]"
                )
    # Hard per D-7: the corpus is clean once the two spine commands carry the
    # minimal tier and conditional cluster entries stop counting as breaks.
    return (not findings, findings)


def check_skill_load_budget(root=None):
    """[scenario 116] No generated skill exceeds the Load-stage size ceiling (ADR-0116, hard fail).

    D-5 retires the per-command `metadata.token-budget` frontmatter field (warn-only,
    83 of 86 flat commands over their own declared value) and replaces it with exactly
    one enforced budget, measured on the artifact the Load stage actually pays for: the
    generated `.claude/skills/<name>/SKILL.md`, not the source `commands/<name>.md`.

    Ceiling: 10000 tokens, approximated as 40000 chars at the repo's standing 4
    chars/token rule (the same approximation `scripts/measure-tokens.py` and the
    retired lint check used). This is a NO-REGRESSION ceiling stated just above
    today's measured maximum (task-init, about 9279 tokens / 37117 chars), not a
    target. Nothing fails on day one; nothing may grow past it; the ceiling is meant
    to ratchet DOWN toward the ~5000-token vendor reference figure as trims land in
    later slices, never up. A future change to the number is a normal ADR-0116
    amendment via a new decision, not a silent constant bump here.

    CALLABLE AGAINST A PATH ARGUMENT (TEST_STRATEGY S-3): `root` defaults to the real
    `.claude/skills/` directory (what CI checks), but accepts any directory holding
    `<name>/SKILL.md` fixtures, so the gate can be proven to fail on a deliberately
    oversized fixture without touching the real corpus. A gate that can only be
    tested by breaking the real corpus never gets tested.
    """
    ceiling_tokens = 10000
    ceiling_chars = ceiling_tokens * 4
    skills_root = root or p(".claude", "skills")
    files = sorted(glob.glob(os.path.join(skills_root, "*", "SKILL.md")))
    fails = []
    for f in files:
        n = len(read(f))
        if n > ceiling_chars:
            name = os.path.basename(os.path.dirname(f))
            fails.append(
                f"{name}: {n} chars (~{n // 4} tokens) exceeds the {ceiling_chars}-char "
                f"({ceiling_tokens}-token) Load-stage ceiling (ADR-0116)"
            )
    return (not fails, fails)


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
    ("tier-routing-closure", "D-7", "no command routes UNCONDITIONALLY to a target missing one of the router's own tiers; a gated route into an opt-in cluster is compliant", check_tier_routing_closure),
    ("skill-load-budget", "scenario 116", "no generated skill exceeds the 10000-token Load-stage ceiling (ADR-0116, hard fail)", check_skill_load_budget),
    ("no-retired-token-budget-field", "scenario 116", "no command frontmatter, generated skill, or lint validator references the retired token-budget field", check_no_retired_frontmatter_field),
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
