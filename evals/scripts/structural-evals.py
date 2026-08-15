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
    """[ADR-0084, D-5, ADR-0133] Every commit-evidence floor home routes to BOTH routes.

    The original assertion was that every home routes to `branch-commit --apply`, because a
    home routing anywhere else is circular by construction: it tells the reader to go get a
    commit and names a path that cannot produce one. That was the live defect the --apply mode
    was built to fix, and it stays a failure.

    ADR-0133 adds a second route rather than replacing the first, so BOTH are now required per
    home. The reason is symmetric and both halves matter. An autonomous run has no human turn
    and can never reach `--apply`, whose condition 4 needs a confirmation given after a display;
    a home offering only that route leaves such a run with no reachable evidence at all. A run
    WITH a human turn must still be sent to `--apply`, the only path that can create a commit;
    a home offering only `ref-attested` would send an attended run to a ref where a commit
    belongs.

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
        if not os.path.isfile(path):
            return (False, [f"{path}: missing"])

    src = open(validator, encoding="utf-8").read()
    required = set(re.findall(r'obj\.get\("([a-z_]+)"\)', src)) | {"ts"}

    block = open(SUBSTRATE_BLOCK, encoding="utf-8").read()
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
    if not os.path.isfile(validator):
        return (False, [f"{validator}: missing; the taxonomy has no home"])
    src = open(validator, encoding="utf-8").read()
    m = re.search(r"^EVENTS\s*=\s*\{(.*?)\}", src, re.S | re.M)
    if not m:
        return (False, [f"{validator}: no EVENTS set to check against"])
    events = set(re.findall(r'"([a-z_-]+)"', m.group(1)))

    negation = re.compile(r"\b(no|not|never|without)\b[^.]{0,70}$", re.I)
    fails = []
    for path in sorted(glob.glob("commands/*.md") + glob.glob("commands/*/SKILL.md")):
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
    for path in glob.glob("wos/*.*.md"):
        stem = os.path.basename(path).split(".")[0]
        canonical = f"wos/{stem}.md"
        if os.path.isfile(canonical):
            views.setdefault(canonical, []).append(path)
    if not views:
        return (True, [])

    surfaces = ["WORKFLOW_OPERATING_SYSTEM.md"] + sorted(
        glob.glob("commands/*.md") + glob.glob("commands/*/SKILL.md")
    )
    generator = "scripts/build-closure-floor-views.py"

    fails = []
    for canonical, view_list in sorted(views.items()):
        # Case-insensitive: commands write "Load `wos/X.md`" at the start of a bullet and the
        # spec writes "load `wos/X.md`" mid-sentence. A case-sensitive pattern caught the spec
        # and missed every command, which a mutation exposed. Same defect as the first version
        # of highest-adr-claim, twice in one day: a guard's regex narrower than the prose it
        # polices reports clean.
        pattern = re.compile(r"\bload `" + re.escape(canonical) + r"`", re.I)
        for path in surfaces:
            if not os.path.isfile(path):
                continue
            for n, line in enumerate(open(path, encoding="utf-8"), 1):
                if pattern.search(line):
                    fails.append(
                        f"{path}:{n}: orders `{canonical}` loaded, but that file has "
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
        path = f"commands/{name}.md"
        if not os.path.isfile(path):
            path = f"commands/{name}/SKILL.md"
        if not os.path.isfile(path):
            fails.append(f"commands/{name}: listed for the design gate but the command is gone")
            continue
        if marker not in open(path, encoding="utf-8").read():
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
    if not os.path.isfile(CLOSURE_CANONICAL):
        return (False, [f"{CLOSURE_CANONICAL}: missing"])

    fails = []
    text = open(CLOSURE_CANONICAL, encoding="utf-8").read()
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
    if not os.path.isfile(CLOSURE_CANONICAL):
        return (False, [f"{CLOSURE_CANONICAL}: missing"])
    canonical = open(CLOSURE_CANONICAL, encoding="utf-8").read()

    fails = []
    for consumer in CLOSURE_CONSUMERS:
        path = f"wos/closure-floors.{consumer}.md"
        if not os.path.isfile(path):
            fails.append(f"{path}: missing; run scripts/build-closure-floor-views.py")
            continue
        want = _closure_effective(canonical, consumer, from_view=False)
        got = _closure_effective(open(path, encoding="utf-8").read(), consumer, from_view=True)
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
LOAD_CEILING_CHARS = 40000     # 10,000 tokens, the ADR-0116 ceiling, restated here so the
                               # advisory reads the same number the hard gate computes locally


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
    for path in sorted(glob.glob("commands/*.md") + glob.glob("commands/*/SKILL.md")):
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
            if not os.path.isfile(topic):
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

    It also reports the documented 5,000-token per-skill re-injection cap, which is HALF the
    ADR-0116 ceiling: a skill can pass the gate and still lose its tail after the first
    compaction, and truncation keeps the start of the file.
    """
    notes = []
    for path in sorted(glob.glob("commands/*.md") + glob.glob("commands/*/SKILL.md")):
        name = os.path.basename(os.path.dirname(path)) if path.endswith("/SKILL.md") \
            else os.path.basename(path)[:-3]
        declared = _declared_unconditional_loads(open(path, encoding="utf-8").read())
        if not declared:
            continue
        skill = os.path.join(".claude", "skills", name, "SKILL.md")
        own = os.path.getsize(skill) if os.path.isfile(skill) else 0
        extra = sum(os.path.getsize(t) for t in declared if os.path.isfile(t))
        total = own + extra
        if total > LOAD_CEILING_CHARS:
            notes.append(
                f"{name}: real load {total} chars ({own} skill + {extra} declared) is "
                f"{total / LOAD_CEILING_CHARS * 100:.0f} per cent of the "
                f"{LOAD_CEILING_CHARS}-char ceiling, which the gate does not see"
            )
    over_cap = []
    for skill in sorted(glob.glob(".claude/skills/*/SKILL.md")):
        size = os.path.getsize(skill)
        if size > REINJECTION_CAP_CHARS:
            over_cap.append(os.path.basename(os.path.dirname(skill)))
    if over_cap:
        notes.append(
            f"{len(over_cap)} of {len(glob.glob('.claude/skills/*/SKILL.md'))} skills exceed "
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
    topics = sorted(os.path.basename(p) for p in glob.glob("wos/*.md"))
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
        for path in glob.glob(pattern):
            haystack.append((path, open(path, encoding="utf-8", errors="ignore").read()))

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
    for p in (cmd_path, tpl_path):
        if not os.path.isfile(p):
            return (False, [f"{p}: missing"])

    cmd = open(cmd_path, encoding="utf-8").read()
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
        for l in open(tpl_path, encoding="utf-8").read().split("\n")
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
    for path in glob.glob("docs/adr/0*.md"):
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
    for path in ("CLAUDE.md", "README.md", "docs/adr/README.md", "wos/repository-structure.md"):
        if not os.path.isfile(path):
            continue
        for n, line in enumerate(open(path, encoding="utf-8"), 1):
            for m in pattern.finditer(line):
                if m.group(1) != highest:
                    fails.append(
                        f"{path}:{n}: claims the highest ADR is {m.group(1)}, disk says "
                        f"{highest}. The count marker beside this sentence is machine-checked "
                        f"and this number was not, which is how it drifted"
                    )
    return (not fails, fails)


SPEC_PATH = "WORKFLOW_OPERATING_SYSTEM.md"
SPEC_CEILING_CHARS = 126000  # ~31500 tokens. Non-regression, set just above the 2026-08-10
                             # measurement of 124672 chars. It comes DOWN, never up (ADR-0116
                             # rule). The headroom is ~1 per cent: enough for a typo fix,
                             # not for a new section.


def check_spec_size_budget():
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
    if not os.path.isfile(SPEC_PATH):
        return (False, [f"{SPEC_PATH}: missing"])

    # Chars, not bytes: scripts/measure-tokens.py is the repository's canonical meter and it
    # counts chars, so byte-counting here would print a number that disagrees with the
    # baselines by the file's multibyte content (50 on the 2026-08-10 measurement).
    size = len(open(SPEC_PATH, encoding="utf-8").read())
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
    if not os.path.isfile(spec_path):
        return (False, [f"{spec_path}: missing"])

    lines = open(spec_path, encoding="utf-8").read().split("\n")
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
    if not os.path.isfile(BOOTSTRAP_BLOCK):
        return (False, [f"{BOOTSTRAP_BLOCK}: missing"])

    block = open(BOOTSTRAP_BLOCK, encoding="utf-8").read()
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
    topic = read(p("wos", "unity-netcode-architecture.md"))
    if not topic:
        return (False, [f"{topic_rel}: absent, but security-review and performance-budget cite it (ADR-0131 E-1)"])
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


CHECKS = [
    ("corpus-wellformed", "scenario corpus", "every scenario has a goal, criteria, and a FAIL section", check_corpus_wellformed),
    ("corpus-indexed", "scenario corpus", "every scenario is linked from evals/README.md", check_corpus_indexed),
    ("scenario-numbers-unique", "scenario corpus", "no two scenarios claim the same number", check_scenario_numbers_unique),
    ("handoff-basenames", "scenario 85", "every Run now: in a command names a real command", check_handoff_basenames),
    ("tier-routing-closure", "ADR-0084", "no command routes UNCONDITIONALLY to a target missing one of the router's own tiers; a gated route into an opt-in cluster is compliant", check_tier_routing_closure),
    ("skill-load-budget", "scenario 116", "no generated skill exceeds the 10000-token Load-stage ceiling (ADR-0116, hard fail)", check_skill_load_budget),
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
    ("highest-adr-claim", "ADR-0136", "prose naming the highest ADR number matches disk; the count-marker guard checks the number inside the marker and is blind to the sentence around it", check_highest_adr_claim),
    ("spec-size-budget", "scenario 134", "the always-read WORKFLOW_OPERATING_SYSTEM.md stays under a non-regression size ceiling; the system layer was the last always-paid surface with no budget (ADR-0136, hard fail)", check_spec_size_budget),
    ("bootstrap-floor-measured", "ADR-0012", "the bootstrap floor declared in the shared block equals the measured size of the four always-read spec sections; the third always-paid surface stops being governed by prose", check_bootstrap_floor_measured),
    ("description-reference-preservation", "scenario 133", "every skill description's cross-references MATCH the baseline: a drop is the regression, an addition means the baseline is stale and would stop protecting that reference (ADR-0135 item 2, D-4)", check_description_reference_preservation),
    ("description-capability-floor", "scenario 133", "every skill description keeps a capability segment of at least 150 chars and a `Do not use` routing marker; the marker is what makes the segment measurable, so dropping it is a total bypass (ADR-0135 item 2, D-6)", check_description_capability_floor),
    ("no-retired-token-budget-field", "scenario 116", "no command frontmatter, generated skill, or lint validator references the retired token-budget field", check_no_retired_frontmatter_field),
    ("required-sections", "required-section scenarios", "every command has a Definition of done + Handoff", check_required_sections),
    ("command-frontmatter", "frontmatter scenarios", "every command's frontmatter name equals its basename", check_command_frontmatter_name),
    ("registry-membership", "registry scenarios", "every command appears in the human-facing registries", check_registry_membership),
    ("count-markers", "count-marker scenarios", "every count marker equals the on-disk count", check_count_markers),
    ("adr-indexed", "ADR index scenarios", "every ADR file has a row in docs/adr/README.md", check_adr_indexed),
    ("no-emdash", "forbidden-bytes scenarios", "no em-dash in commands or root docs", check_no_emdash),
    ("shared-block-sources", "shared-block scenarios", "every <!-- shared:X --> has a canonical source", check_shared_block_sources),
    ("epistemic-doctrine-surfaces", "scenarios 110, 112", "the ADR-0109 doctrine surfaces exist and claim-grounding covers the universal command layer", check_epistemic_doctrine_surfaces),
    ("commit-evidence-apply-route", "ADR-0084", "every commit-evidence floor home routes to BOTH evidence routes: branch-commit --apply, the only path that can commit, and the ref-attested route an unattended run can reach (D-5, ADR-0133)", check_commit_evidence_routes_to_apply),
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
