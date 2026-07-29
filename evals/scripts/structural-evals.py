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
import itertools

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def p(*parts):
    return os.path.join(REPO, *parts)


def read(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


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


# Each row's second field is the label printed beside the check. It names the eval
# scenario the invariant enforces, or, when the invariant predates or postdates any
# scenario, the ADR that locked it. It is never a D-N task decision: those live under
# projects/, which .gitignore excludes, so the printed anchor resolved to nothing a
# reader of this repository could open.
CHECKS = [
    ("corpus-wellformed", "scenario corpus", "every scenario has a goal, criteria, and a FAIL section", check_corpus_wellformed),
    ("corpus-indexed", "scenario corpus", "every scenario is linked from evals/README.md", check_corpus_indexed),
    ("scenario-numbers-unique", "scenario corpus", "no two scenarios claim the same number", check_scenario_numbers_unique),
    ("handoff-basenames", "scenario 85", "every Run now: in a command names a real command", check_handoff_basenames),
    ("tier-routing-closure", "ADR-0084", "no command routes UNCONDITIONALLY to a target missing one of the router's own tiers; a gated route into an opt-in cluster is compliant", check_tier_routing_closure),
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
    ("godot-tier-artifact-gate", "ADR-0119", "the tier floor fails closed on every fixture directory on disk, decoy and near misses included", check_godot_tier_artifact_gate),
    ("godot-tier-floor-variants", "ADR-0119", "the tier floor keeps its variants and every command it names a variant for cites it", check_godot_tier_floor_variants),
    ("godot-tier-gate", "scenario 117", "godot-scene-plan requires a declared renderer tier on a 3D plan (ADR-0117 D-9)", check_godot_tier_gate),
    ("godot-dimension-routing", "scenario 117", "no command names 2D as a default dimension", check_godot_dimension_routing),
    ("godot-3d-topics-indexed", "scenario 117", "every wos/godot-3d-*.md is in the read map, the map cites nothing absent from disk, and no 3D topic copies a sentence from any other Godot topic", check_godot_3d_topics_indexed),
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
