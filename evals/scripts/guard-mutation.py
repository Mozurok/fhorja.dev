#!/usr/bin/env python3
"""Mutation harness for the structural guards: prove each covered check BITES.

A guard is trusted because it is green, and this repository has now twice shipped a
green that meant nothing. `check_supersession_marked` returned zero findings because
its regex could not see the form four ADRs actually use. `check-installed-skills-drift.sh`
reported `0 differ` across three roots while 98 of 98 bodies differed. Both were green
about something real and blind to the thing they were cited for.

A passing check proves nothing on its own. What proves a check works is that it FAILS
when the thing it guards is broken. This harness does that mechanically: for every
covered check it builds a clean fixture, asserts the check PASSES on it, applies one
named mutation, and asserts the check FAILS with the finding the entry named. All three,
every run. A control that does not pass is as much a defect as a mutation that does not
bite, because a check that fails on a clean fixture is not measuring what its name says.

The third assertion is the youngest and the reason is the same one that produced the
other two. Almost every check here has more than one failing branch, and most carry a
fail-closed branch that fires on an empty subject. Asserting only that the mutated check
FAILS therefore passes just as happily when the mutation broke its own fixture rather
than the rule: the check reports its lost-subject finding, the harness prints BITES, and
the branch under test was never reached. So each entry carries the substring its finding
must contain, and `scripts/tests/test-guard-mutation.sh` refuses an entry without one.

Coverage is reported, never claimed. Only checks that accept `root=` can be pointed at a
fixture at all, and the summary prints how many of the live CHECKS table this covers and
how many it cannot reach, so the gap stays visible instead of being implied away.

Usage:  python3 evals/scripts/guard-mutation.py [--verbose]
Exit:   0 when every control passes and every mutation bites, 1 otherwise.
"""

import glob
import importlib.util
import json
import os
import re
import shutil
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SE_PATH = os.path.join(REPO, "evals", "scripts", "structural-evals.py")

_spec = importlib.util.spec_from_file_location("se", SE_PATH)
se = importlib.util.module_from_spec(_spec)
sys.modules["se"] = se
_spec.loader.exec_module(se)


# --- fixture builders -------------------------------------------------------
# Each copies ONLY what its check reads. Copying the repo would be 124 MB per
# mutation and would also hide which paths a check actually depends on.

def _skill(d, name, description="A short description.", body="Body.\n"):
    os.makedirs(os.path.join(d, name), exist_ok=True)
    with open(os.path.join(d, name, "SKILL.md"), "w", encoding="utf-8") as f:
        f.write(f"---\nname: {name}\ndescription: |-\n  {description}\n---\n\n{body}")


def build_skills_root(d):
    """A skills root with three small, valid skills."""
    for n in ("alpha", "beta", "gamma"):
        _skill(d, n)


def build_spec_root(d):
    """A repo root carrying only the spec file."""
    with open(os.path.join(d, se.SPEC_PATH), "w", encoding="utf-8") as f:
        f.write("# spec\n" + ("x" * 1000))


def build_adr_root(d):
    """A repo root with two ADRs: one declares a supersession, the target records it."""
    adr = os.path.join(d, "docs", "adr")
    os.makedirs(adr)
    head = "# ADR-{n}: t\n\n- **Status**: {st}\n- **Date**: 2026-01-01\n- **Tags**: t\n"
    with open(os.path.join(adr, "0100-a.md"), "w", encoding="utf-8") as f:
        f.write(head.format(n="0100", st="Accepted; supersedes the mechanism of ADR-0101."))
    with open(os.path.join(adr, "0101-b.md"), "w", encoding="utf-8") as f:
        f.write(head.format(n="0101", st="Accepted; superseded by ADR-0100."))
    # A third ADR that supersedes NOTHING while naming one in the same sentence. It is in
    # the CONTROL rather than in a mutation on purpose: the defect it guards against is a
    # parser that harvests every id off a `Supersedes:` line, and that parser reports a
    # FAILURE here, not a pass. So a widening shows up as CONTROL FAILED, which the
    # harness refuses, instead of as a mutation that quietly stops biting. Written after
    # the live instance on 2026-09-20, where ADR-0212's `Supersedes: nothing. ADR-0171's
    # decision stands` was read as superseding ADR-0171.
    with open(os.path.join(adr, "0102-c.md"), "w", encoding="utf-8") as f:
        f.write(head.format(n="0102", st="Accepted")
                + "- **Supersedes**: nothing. ADR-0101's decision stands.\n")
    # An index with a row per ADR, and prose naming the highest, so this root also
    # serves check_adr_indexed and check_highest_adr_claim.
    with open(os.path.join(adr, "README.md"), "w", encoding="utf-8") as f:
        f.write("# ADR index\n\n| id | summary |\n| --- | --- |\n"
                "| [0100](./0100-a.md) | a |\n| [0101](./0101-b.md) | b |\n"
                "| [0102](./0102-c.md) | c |\n")
    with open(os.path.join(d, "CLAUDE.md"), "w", encoding="utf-8") as f:
        f.write("- `docs/adr/` as decisions; the highest is 0102.\n")
    return d


def build_carveout_root(d):
    """A repo root where the Part 1.3 carve-out and the commands agree."""
    os.makedirs(os.path.join(d, "wos"))
    os.makedirs(os.path.join(d, "commands"))
    with open(os.path.join(d, "wos", "active-epistemic-humility.md"), "w", encoding="utf-8") as f:
        f.write("### 1.3 x\n\nThe scope of that sentence is this contract, the claim status.\n\n"
                "- `grader` grades each item by a stated rubric.\n\nEnd.\n")
    with open(os.path.join(d, "commands", "grader.md"), "w", encoding="utf-8") as f:
        f.write("- Each item carries a confidence of `HIGH`, `MEDIUM`, or `LOW`.\n")


# --- mutators ---------------------------------------------------------------

def build_fleet_return_root(d):
    """Exercise the real fleet text and the shared bodies the guard excludes."""
    os.makedirs(os.path.join(d, "commands"))
    shutil.copytree(os.path.join(REPO, "commands", "_shared"),
                    os.path.join(d, "commands", "_shared"))
    for relative in ("commands/screen-spec-fleet.md",
                     "templates/ORCHESTRATOR_COMMAND.template.md",
                     "wos/cross-cutting-workflow-guardrails.md"):
        target = os.path.join(d, relative)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        shutil.copyfile(os.path.join(REPO, relative), target)


def _replace_fleet_text(d, before, after):
    path = os.path.join(d, "commands", "screen-spec-fleet.md")
    with open(path, encoding="utf-8") as f:
        body = f.read()
    assert body.count(before) == 1, f"fixture lost its mutation target: {before}"
    with open(path, "w", encoding="utf-8") as f:
        f.write(body.replace(before, after))


def mutate_fleet_text_return(d):
    _replace_fleet_text(d,
        "the worker writes one schema-conforming JSON payload there and the orchestrator reads it",
        "the worker returns text and the orchestrator persists it")
    return "native worker file replaced by parent-persisted prose, retaining the path sentinel"


def mutate_fleet_worker_call(d):
    _replace_fleet_text(d,
        "Write one JSON payload matching worker_output_schema to fleet_inbox_artifact and nothing else",
        "Worker MUST invoke the `StructuredOutput` tool exactly once")
    return "native final reminder requires the unavailable worker tool, retaining the sentinel"


def mutate_fleet_missing_path(d):
    _replace_fleet_text(d, "Name the path you are on", "Carrier choice omitted")
    return "dispatch-path sentinel removed from the real command"


def mutate_fleet_artifact_parameter(d):
    _replace_fleet_text(d, "Name the path you are on", "Name the path you are on; artifact=wrong")
    return "unavailable artifact= parameter restored"


def mutate_fleet_empty_commands(d):
    os.remove(os.path.join(d, "commands", "screen-spec-fleet.md"))
    return "all command subjects removed, leaving only shared blocks and guidance"


def mutate_fleet_dispatch_guidance(d):
    path = os.path.join(d, "wos", "cross-cutting-workflow-guardrails.md")
    with open(path, "a", encoding="utf-8") as f:
        f.write("\nEvery dispatched agent prompt MUST include an explicit StructuredOutput call reminder.\n")
    return "the live dispatch guidance reinstates the worker-call reminder"


def mutate_fleet_template_carrier(d):
    path = os.path.join(d, "templates", "ORCHESTRATOR_COMMAND.template.md")
    with open(path, "a", encoding="utf-8") as f:
        f.write("\nEach worker MUST return its result via the `StructuredOutput` tool "
                "keyed `artifact=fleet-inbox/<run_id>/<worker_id>`.\n")
    return "the template's actual previous worker-call and artifact= mandate is restored"

def mutate_skill_over_ceiling(d):
    _skill(d, "alpha", body="x" * (se.LOAD_CEILING_CHARS + 1))
    return f"one skill body pushed past the {se.LOAD_CEILING_CHARS}-char ADR-0116 ceiling"


def build_skills_near_ceiling(d):
    """Control for the slack check: the largest skill sits 1,000 chars under the ceiling, well
    inside the allowed slack, beside two small ones."""
    build_skills_root(d)
    _skill(d, "alpha", body="x" * (se.LOAD_CEILING_CHARS - 1000 - 60))
    return d


def mutate_ceiling_left_slack(d):
    """Trims land and the ceiling stays put: the largest skill is now 20,000 chars under a
    ceiling that did not move, which is the drift ADR-0227 found after ADR-0116."""
    _skill(d, "alpha", body="x" * (se.LOAD_TARGET_CHARS - 60))
    return (f"the largest skill trimmed to about {se.LOAD_TARGET_CHARS} chars under an unchanged "
            f"{se.LOAD_CEILING_CHARS}-char ceiling")


def mutate_description_emptied(d):
    """A skill with no description shrinks the Advertise surface and looks cheaper."""
    with open(os.path.join(d, "beta", "SKILL.md"), "w", encoding="utf-8") as f:
        f.write("---\nname: beta\n---\n\nBody.\n")
    return "one skill's description removed, which makes the aggregate budget greener"


def mutate_spec_over_ceiling(d):
    with open(os.path.join(d, se.SPEC_PATH), "w", encoding="utf-8") as f:
        f.write("x" * (se.SPEC_CEILING_CHARS + 1))
    return f"the spec grown past the {se.SPEC_CEILING_CHARS}-char non-regression ceiling"


def mutate_supersession_unrecorded(d):
    path = os.path.join(d, "docs", "adr", "0101-b.md")
    body = open(path, encoding="utf-8").read()
    with open(path, "w", encoding="utf-8") as f:
        f.write(body.replace("Accepted; superseded by ADR-0100.", "Accepted"))
    return "the superseded ADR's Status line no longer names its superseder"


def mutate_carveout_unlisted(d):
    with open(os.path.join(d, "commands", "intruder.md"), "w", encoding="utf-8") as f:
        f.write("- Each finding carries `HIGH` / `MEDIUM` / `LOW` confidence.\n")
    return "a command declares a graded confidence field the Part 1.3 carve-out does not name"


# --- the table --------------------------------------------------------------

def build_scenario_corpus_root(d):
    """A scenario corpus whose single scenario carries the three required sections.

    Reachable only because structural-evals.py routes path resolution through p(),
    which consults _ROOT (2026-09-18). Before that this check read the real tree and
    could not be pointed anywhere, which is why it sat outside coverage.
    """
    sc = os.path.join(d, "evals", "scenarios")
    os.makedirs(sc, exist_ok=True)
    # An index row and a walker glob, so this root also serves check_corpus_indexed
    # and check_walker_covers_corpus.
    with open(os.path.join(d, "evals", "README.md"), "w") as fh:
        fh.write("# Evals\n\n| scenario | covers |\n| --- | --- |\n"
                 "| 01-example.md | the example |\n")
    os.makedirs(os.path.join(d, "evals", "scripts"), exist_ok=True)
    with open(os.path.join(d, "evals", "scripts", "run-evals.sh"), "w") as fh:
        fh.write('#!/usr/bin/env bash\nALL_SCENARIOS=( "${SCENARIOS_DIR}"/[0-9]*.md )\n')
    with open(os.path.join(sc, "01-example.md"), "w") as fh:
        fh.write("# Eval scenario 01: example\n\n## Goal\n\nA goal.\n\n"
                 # Three enumerable checks, because CRITERIA_ITEM_FLOOR rejects a
                 # criteria section that reads as a paragraph rather than a rubric.
                 "## Pass criteria\n\n1. It passes.\n2. It names the file.\n"
                 "3. It exits zero.\n\n"
                 "## Failure modes to watch\n\n- It does not.\n\n"
                 # Padded past the 1200-char scenario floor. check_scenario_content_floor
                 # rejects a scenario too short to describe a real situation, and a
                 # fixture below it fails the control rather than the mutation.
                 "## Notes\n\n" + ("A sentence of setup that gives the scenario "
                 "enough shape to be worth running, repeated so the fixture clears "
                 "the content floor without pretending to be a real scenario. ") * 40)
    return d


def mutate_scenario_drops_failure_section(d):
    """Remove the failure section, the hole in the regression net the check names."""
    f = os.path.join(d, "evals", "scenarios", "01-example.md")
    body = open(f).read()
    body = body.split("## Failure modes to watch")[0].rstrip() + "\n"
    open(f, "w").write(body)
    return "the scenario's failure section removed"


def build_prose_root(d):
    """A wos topic with clean prose: no em-dash, no en-dash."""
    w = os.path.join(d, "wos")
    os.makedirs(w, exist_ok=True)
    with open(os.path.join(w, "example-topic.md"), "w") as fh:
        fh.write("# Example topic\n\nA sentence with no forbidden bytes in it.\n")
    return d


def mutate_prose_em_dash(d):
    """The byte the check has always caught."""
    f = os.path.join(d, "wos", "example-topic.md")
    open(f, "a").write("\nAn em-dash \u2014 lands here.\n")
    return "an em-dash added to a wos topic"


def mutate_prose_en_dash(d):
    """The byte AGENTS.md forbids in the same sentence and the check used to miss.

    Two of these were live in the scanned surfaces on 2026-09-18 and every gate was
    green. A mutation that only ever planted an em-dash would have stayed green too,
    which is why this entry exists beside the other one rather than instead of it.
    """
    f = os.path.join(d, "wos", "example-topic.md")
    open(f, "a").write("\nAn en-dash \u2013 lands here.\n")
    return "an en-dash added to a wos topic"


def build_topic_reachability_root(d):
    """A wos topic that the spec loads by path, which is what makes it reachable.

    ADR-0006's rule is that a lazy topic must be reachable from something that loads
    it, so the fixture needs both halves: the topic, and a file in the haystack that
    names it by its `wos/<name>.md` path.
    """
    os.makedirs(os.path.join(d, "wos"), exist_ok=True)
    with open(os.path.join(d, "wos", "covered-topic.md"), "w") as fh:
        fh.write("# Covered topic\n\nLoaded on demand.\n")
    with open(os.path.join(d, "WORKFLOW_OPERATING_SYSTEM.md"), "w") as fh:
        fh.write("# Spec\n\n## Minimum read map\n\nLoad `wos/covered-topic.md` when routing.\n")
    return d


def mutate_topic_orphaned(d):
    """A topic nothing in the haystack names. The orphan ADR-0006 exists to catch."""
    with open(os.path.join(d, "wos", "orphan-topic.md"), "w") as fh:
        fh.write("# Orphan topic\n\nNothing loads this.\n")
    return "a wos topic no loader names"


def build_commands_root(d):
    """One flat command whose frontmatter name matches its basename, plus the
    `_shared` source for the one shared marker its body carries.

    Serves several checks at once because they read the same tree through
    `_command_files()` and `p("commands", ...)`, and a fixture that satisfies all of
    them keeps each control honest: a control that fails for an unrelated reason
    would hide whether the mutation is what bit.
    """
    c = os.path.join(d, "commands")
    os.makedirs(os.path.join(c, "_shared"), exist_ok=True)
    with open(os.path.join(c, "_shared", "handoff-body.md"), "w") as fh:
        fh.write("Use the adaptive ending format.\n")
    with open(os.path.join(c, "example-command.md"), "w") as fh:
        fh.write(
            "---\n"
            "name: example-command\n"
            "description: An example command used only as an eval fixture.\n"
            "---\n"
            "# example-command\n\n"
            "### Handoff\n"
            "<!-- shared:handoff-body -->\n"
            "Run now: example-command\n\n"
            # Three authored items, because check_required_sections enforces a
            # floor of three and does not count a shared closing line toward it.
            "### Definition of done (command output)\n"
            "- The output names what it did and what it did not reach.\n"
            "- Every path it printed resolves on disk.\n"
            "- The handoff names one real command or declares the chain ended.\n"
        )
    return d


def mutate_frontmatter_name_diverges(d):
    """The name stops matching the basename, which is what ADR-0029 registry drift
    looks like at the file level."""
    f = os.path.join(d, "commands", "example-command.md")
    body = open(f).read().replace("name: example-command", "name: renamed-command")
    open(f, "w").write(body)
    return "a command's frontmatter name no longer matches its basename"


def mutate_shared_marker_without_source(d):
    """A shared marker pointing at a block that does not exist. sync-shared-blocks.sh
    would silently inject nothing."""
    f = os.path.join(d, "commands", "example-command.md")
    open(f, "a").write("\n<!-- shared:no-such-block -->\n")
    return "a shared marker with no canonical source"



def mutate_dod_section_removed(d):
    """The Definition of done goes. A command with no closing rubric cannot be told
    from one that finished."""
    f = os.path.join(d, "commands", "example-command.md")
    body = open(f).read()
    body = body.split("### Definition of done")[0].rstrip() + "\n"
    open(f, "w").write(body)
    return "a command with no Definition of done section"


def mutate_handoff_names_unknown_command(d):
    """`Run now:` points at a command that does not exist, which is the invented-name
    failure ADR-0126 and scenario 85 exist for."""
    f = os.path.join(d, "commands", "example-command.md")
    body = open(f).read().replace("Run now: example-command", "Run now: execute-the-plan")
    open(f, "w").write(body)
    return "a handoff naming a command that does not exist"


def build_task_state_sync_root(d):
    """task-init's inline TASK_STATE structure and the template, in agreement.

    ADR-0111's rule is name AND order, so the fixture carries three sections in the
    same sequence on both sides and the two mutations below attack one half each.
    """
    os.makedirs(os.path.join(d, "commands"), exist_ok=True)
    os.makedirs(os.path.join(d, "templates"), exist_ok=True)
    sections = "## Quick reanchor\n\n## Current phase\n\n## Recommended next step\n"
    with open(os.path.join(d, "commands", "task-init.md"), "w") as fh:
        fh.write("# task-init\n\nMust use this exact structure:\n\n# TASK_STATE\n\n" + sections)
    with open(os.path.join(d, "templates", "TASK_STATE.template.md"), "w") as fh:
        fh.write("# TASK_STATE\n\n" + sections)
    return d


def mutate_template_drops_a_section(d):
    """Membership: the template loses a section the command still orders."""
    f = os.path.join(d, "templates", "TASK_STATE.template.md")
    body = open(f).read().replace("## Current phase\n\n", "")
    open(f, "w").write(body)
    return "the template missing a section the command declares"


def mutate_template_reorders_sections(d):
    """Order only: same three names, swapped. ADR-0111 says name AND order, and this
    is the half a set comparison would miss.
    """
    f = os.path.join(d, "templates", "TASK_STATE.template.md")
    open(f, "w").write(
        "# TASK_STATE\n\n## Current phase\n\n## Quick reanchor\n\n## Recommended next step\n"
    )
    return "the same sections in a different order"


def build_fanout_floor_root(d):
    """One fan-out floor, stated in the topic and agreed to by the spec and a fleet
    command. ADR-0173 exists because three different numbers claimed to be the floor.
    """
    os.makedirs(os.path.join(d, "wos"), exist_ok=True)
    os.makedirs(os.path.join(d, "commands"), exist_ok=True)
    with open(os.path.join(d, "wos", "workflow-patterns.md"), "w") as fh:
        fh.write("# Workflow patterns\n\nThe fan-out floor is 3 independent items.\n")
    with open(os.path.join(d, "WORKFLOW_OPERATING_SYSTEM.md"), "w") as fh:
        fh.write("# Spec\n\n### When to use\n\nDispatch on 3 or more independent items.\n\n"
                 "### When NOT to use\n\nFewer than 3 items runs sequentially.\n")
    with open(os.path.join(d, "commands", "example-fleet.md"), "w") as fh:
        fh.write("# example-fleet\n\nDispatch when N >= 3 independent targets exist.\n")
    return d


def mutate_fleet_declares_lower_floor(d):
    """A fleet command that dispatches below the floor, which is the drift ADR-0173
    names: seven commands declaring 3, 4 and 6 while the spec said 5."""
    f = os.path.join(d, "commands", "example-fleet.md")
    open(f, "w").write("# example-fleet\n\nDispatch when N >= 2 independent targets exist.\n")
    return "a fleet command dispatching below the declared floor"


def mutate_spec_disagrees_with_floor(d):
    """The spec stops echoing the floor the topic states."""
    f = os.path.join(d, "WORKFLOW_OPERATING_SYSTEM.md")
    open(f, "w").write("# Spec\n\n### When to use\n\nDispatch on 5 or more independent items.\n\n"
                       "### When NOT to use\n\nFewer than 5 items runs sequentially.\n")
    return "the spec naming a different floor than the topic"


def build_closure_views_root(d):
    """The canonical closure floors and their three generated views, copied from the
    live tree because they are in a known-good state and the format is generated.

    Reverse-engineering the view format into a synthetic fixture would encode this
    harness's guess about it, and the guess would drift from the generator without
    anything noticing. Copying the four files the check reads keeps the fixture true
    by construction and stays within the rule the builders above follow: copy what
    the check reads, never the repo. About 109 KB, all text.
    """
    w = os.path.join(d, "wos")
    os.makedirs(w, exist_ok=True)
    names = ["closure-floors.md"] + [
        f"closure-floors.{c}.md"
        for c in ("task-close", "slice-closure", "implement-approved-slice")
    ]
    for n in names:
        shutil.copy(os.path.join(REPO, "wos", n), os.path.join(w, n))
    return d


def mutate_view_drops_a_floor(d):
    """A floor vanishes from one consumer's view while the canonical still orders it.

    ADR-0138's stated failure mode, verbatim from the check: "a dropped floor is a
    closure gate that stops firing without anything saying so".
    """
    f = os.path.join(d, "wos", "closure-floors.task-close.md")
    body = open(f).read()
    i = body.index("\n## ", body.index("\n## ") + 1)
    j = body.index("\n## ", i + 1)
    dropped = body[i + 4: body.index("\n", i + 4)]
    open(f, "w").write(body[:i] + body[j:])
    return f"the {dropped.split('(')[0].strip()!r} floor dropped from the task-close view"


def build_epistemic_doctrine_root(d):
    """The four ADR-0109 surfaces present, and a command that carries both shared
    markers rather than only the output layout.

    The last part is the completeness half: a command can pick up the standard output
    layout and silently skip claim-grounding, which is how a new command joins the
    catalogue without the doctrine.
    """
    os.makedirs(os.path.join(d, "wos"), exist_ok=True)
    os.makedirs(os.path.join(d, "commands", "_shared"), exist_ok=True)
    with open(os.path.join(d, "WORKFLOW_OPERATING_SYSTEM.md"), "w") as fh:
        fh.write("# Spec\n\n### Claim status and abstention\n\n"
                 "Ground a claim or abstain. See `wos/active-epistemic-humility.md`.\n")
    open(os.path.join(d, "wos", "active-epistemic-humility.md"), "w").write(
        "# Active epistemic humility\n\nGround or abstain.\n")
    open(os.path.join(d, "commands", "_shared", "claim-grounding.md"), "w").write(
        "Name the referent for every claim.\n")
    open(os.path.join(d, "commands", "example-command.md"), "w").write(
        "# example-command\n\n<!-- shared:standard-output-layout -->\n"
        "<!-- shared:claim-grounding -->\n")
    return d


def mutate_command_skips_claim_grounding(d):
    """A command keeps the output layout and drops the grounding block, which is the
    completeness failure: the doctrine stops covering the universal layer one command
    at a time."""
    f = os.path.join(d, "commands", "example-command.md")
    body = open(f).read().replace("<!-- shared:claim-grounding -->\n", "")
    open(f, "w").write(body)
    return "a command carrying the output layout without claim-grounding"


def mutate_spec_fold_removed(d):
    """The spec's H3 goes. A silent removal of the fold is what TEST_STRATEGY row 8
    names."""
    f = os.path.join(d, "WORKFLOW_OPERATING_SYSTEM.md")
    body = open(f).read().replace("### Claim status and abstention", "### Something else")
    open(f, "w").write(body)
    return "the spec's claim-status fold renamed away"



def mutate_adr_without_index_row(d):
    """A new ADR lands with no row in the index, which is how the index stops being
    the place you can find what was decided."""
    with open(os.path.join(d, "docs", "adr", "0102-c.md"), "w", encoding="utf-8") as f:
        f.write("# ADR-0102: c\n\n- **Status**: Accepted\n- **Date**: 2026-01-01\n- **Tags**: t\n")
    with open(os.path.join(d, "docs", "adr", "README.md"), "a", encoding="utf-8") as f:
        f.write("| [0102](./0102-c.md) | c |\n")
    # the row exists for 0102; remove 0101's instead so the failure is unambiguous
    q = os.path.join(d, "docs", "adr", "README.md")
    body = open(q).read().replace("| [0101](./0101-b.md) | b |\n", "")
    open(q, "w").write(body)
    return "an ADR file with no row in the index"


def mutate_prose_names_stale_highest(d):
    """Prose keeps a number the directory has moved past. This is the drift that
    shipped on 2026-09-17: adding ADR-0210 moved the count markers, which are machine
    checked, and left two sentences saying 0209, which were not."""
    f = os.path.join(d, "CLAUDE.md")
    open(f, "w").write("- `docs/adr/` as decisions; the highest is 0099.\n")
    return "prose naming a highest ADR the directory has moved past"



def mutate_commands_dir_emptied(d):
    """The subject vanishes. A check that reports clean here cannot tell a healthy
    catalogue from a broken run, which is the failure check_highest_adr_claim had
    when it opened its surfaces relative to the process's working directory."""
    for f in glob.glob(os.path.join(d, "commands", "*.md")):
        os.remove(f)
    return "every command file removed, leaving the check with no subject"


def mutate_adr_dir_emptied(d):
    """Same shape, different subject: a numbered-ADR directory with nothing in it."""
    for f in glob.glob(os.path.join(d, "docs", "adr", "0*.md")):
        os.remove(f)
    return "every numbered ADR removed, leaving the check with no subject"



def mutate_prose_surfaces_emptied(d):
    """Every prose surface the byte guard scans, removed at once. Five globs coming
    back empty is a broken run, not a repository with no prose in it."""
    for sub in ("wos", "commands", "templates", os.path.join("docs", "adr")):
        for f in glob.glob(os.path.join(d, sub, "**", "*.md"), recursive=True):
            os.remove(f)
    return "every prose surface removed, leaving the byte guard with no subject"


def mutate_skill_declares_retired_field(d):
    """A generated skill carries the token-budget field ADR-0116 retired. The build
    regenerates skills from commands, so the field coming back in a skill is how the
    retirement quietly stops holding."""
    f = os.path.join(d, ".claude", "skills", "example-command", "SKILL.md")
    os.makedirs(os.path.dirname(f), exist_ok=True)
    open(f, "w").write("---\nname: example-command\ndescription: d\nmetadata:\n"
                       "  token-budget: 4000\n---\nBody.\n")
    return "a generated skill declaring the retired token-budget field"



def mutate_criteria_becomes_a_paragraph(d):
    """The rubric collapses into prose. Nothing is missing, so a section-presence
    check still passes; what is gone is anything a reviewer can tick off."""
    f = os.path.join(d, "evals", "scenarios", "01-example.md")
    body = open(f).read()
    body = body.replace(
        "1. It passes.\n2. It names the file.\n3. It exits zero.\n",
        "The command should broadly do the right thing here.\n")
    open(f, "w").write(body)
    return "a criteria section rewritten as a paragraph"


def build_floor_attester_root(d):
    """The two floor files, copied, because each `^## ` section must declare exactly
    one attester class and that shape is generated prose rather than something to
    invent here."""
    w = os.path.join(d, "wos")
    os.makedirs(w, exist_ok=True)
    for n in ("closure-floors.md", "platform-runtime-floors.md"):
        shutil.copy(os.path.join(REPO, "wos", n), os.path.join(w, n))
    return d


def mutate_floor_drops_its_attester(d):
    """One floor stops declaring who attests it. Scenario 127's scan is fail-closed by
    construction, so a floor with no attester line is a floor nobody owns."""
    f = os.path.join(d, "wos", "closure-floors.md")
    body = open(f).read()
    i = body.index("\nAttester class:")
    j = body.index("\n", i + 1)
    open(f, "w").write(body[:i] + body[j:])
    return "a closure floor with no attester class declared"


def build_registries_root(d):
    """One command present in all three human-facing registries, in the exact line
    forms lint-commands.sh enforces.

    ADR-0029's drift guard. The registries are hand-maintained, so a new command
    reaches the catalogue and one of the three is forgotten; that is the failure, and
    it is silent because each registry reads fine on its own.
    """
    os.makedirs(os.path.join(d, "commands"), exist_ok=True)
    os.makedirs(os.path.join(d, "wos"), exist_ok=True)
    with open(os.path.join(d, "commands", "example-command.md"), "w") as fh:
        fh.write("---\nname: example-command\ndescription: d\n---\n# example-command\n")
    with open(os.path.join(d, "WORKFLOW_OPERATING_SYSTEM.md"), "w") as fh:
        fh.write("# Spec\n\n## Command categories\n\n- `example-command`\n")
    with open(os.path.join(d, "COMMAND_PROMPT_STUBS.md"), "w") as fh:
        fh.write("# Stubs\n\n| command | stub |\n| --- | --- |\n| `example-command` | do it |\n")
    with open(os.path.join(d, "wos", "command-roles.md"), "w") as fh:
        fh.write("# Command roles\n\n### example-command\n\nDoes the thing.\n")
    return d


def mutate_command_missing_from_one_registry(d):
    """The command leaves the roles file and stays in the other two. One of three is
    the realistic shape: nobody forgets all three."""
    f = os.path.join(d, "wos", "command-roles.md")
    open(f, "w").write("# Command roles\n\nNothing here yet.\n")
    return "a command absent from one of the three registries"


def build_internal_refs_root(d):
    """A topic that sends a reader to _internal/ AND says what _internal/ is.

    H13's point: _internal/ is gitignored, so an unannotated reference sends someone
    to a path that does not exist in a fresh clone.
    """
    os.makedirs(os.path.join(d, "wos"), exist_ok=True)
    with open(os.path.join(d, "wos", "example-topic.md"), "w") as fh:
        fh.write("# Example topic\n\nSee `_internal/audit-2026/` (gitignored; local "
                 "maintainer snapshots, absent from a fresh clone).\n")
    return d


def mutate_internal_ref_loses_its_annotation(d):
    """The pointer stays and the explanation goes, which is the exact line H13
    describes: a reader sent to a path that is not there."""
    f = os.path.join(d, "wos", "example-topic.md")
    open(f, "w").write("# Example topic\n\nSee `_internal/audit-2026/` for the numbers.\n")
    return "an _internal/ reference with nothing saying what _internal/ is"


def mutate_roadmap_points_into_internal(d):
    """ROADMAP.md sends a reader to _internal/ with nothing saying what it is, the 06#7 shape
    the guard could not see while ROADMAP was outside its scan set."""
    with open(os.path.join(d, "ROADMAP.md"), "w", encoding="utf-8") as fh:
        fh.write("# Roadmap\n\n- Next: finish the items in `_internal/phase-4/backlog.md`.\n")
    return "an unannotated _internal/ pointer in ROADMAP.md"


def _write(d, rel, text):
    path = os.path.join(d, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def build_old_repo_name_root(d):
    """A tree whose shipped files use the neutral names and whose exempt files keep the old one.

    The exempt copies are there on purpose: the control passing with the old name in an ADR,
    a scenario, the changelog and CLAUDE.md is what proves the scope leaves history alone.
    """
    _write(d, "commands/team-update.md",
           "### Artifact changes\n- List files in the task repository that would change, or `None`.\n")
    _write(d, "scripts/bootstrap-user-setup.sh", '#!/usr/bin/env bash\necho "Fhorja: first-time setup"\n')
    _write(d, "README.md", "# Readme\n\nClone the workflow repository.\n")
    _write(d, "docs/adr/0001-old.md", "# ADR-0001\n\nWritten in `my_work_tasks/`.\n")
    _write(d, "evals/scenarios/04-pr.md", "No `my_work_tasks/` path in the PR body.\n")
    _write(d, "CHANGELOG.md", "# Changelog\n\n- my_work_tasks renamed.\n")
    _write(d, "CLAUDE.md", "This is the my_work_tasks repository.\n")
    return d


def mutate_command_names_old_repo(d):
    """The pre-D-10 line in a command, the shape fifteen commands carried."""
    _write(d, "commands/team-update.md",
           "### Artifact changes\n- List files in `my_work_tasks/` that would change, or `None`.\n")
    return "a command naming the private repository"


def mutate_script_banner_names_old_repo(d):
    """A script prints the old name: a non-markdown file under scripts/ is in scope too."""
    _write(d, "scripts/bootstrap-user-setup.sh", '#!/usr/bin/env bash\necho "my_work_tasks: first-time setup"\n')
    return "a script banner naming the private repository"


def build_branch_commit_root(d):
    """commands/branch-commit.md and its generated skill, copied.

    Both checks below pin exact sentences, several of them long. Retyping them here
    would add a second place the wording can be wrong, and a fixture whose phrasing
    drifts from the real file produces a control failure that looks like a defect.
    Copying keeps the clean side true by construction.
    """
    os.makedirs(os.path.join(d, "commands"), exist_ok=True)
    os.makedirs(os.path.join(d, ".claude", "skills", "branch-commit"), exist_ok=True)
    shutil.copy(os.path.join(REPO, "commands", "branch-commit.md"),
                os.path.join(d, "commands", "branch-commit.md"))
    shutil.copy(os.path.join(REPO, ".claude", "skills", "branch-commit", "SKILL.md"),
                os.path.join(d, ".claude", "skills", "branch-commit", "SKILL.md"))
    # check_apply_commits_after_display also reads scenario 125.
    os.makedirs(os.path.join(d, "evals", "scenarios"), exist_ok=True)
    shutil.copy(os.path.join(REPO, "evals", "scenarios",
                             "125-branch-commit-apply-authorization.md"),
                os.path.join(d, "evals", "scenarios",
                             "125-branch-commit-apply-authorization.md"))
    return d


def mutate_bare_commit_rule_removed(d):
    """The bare-commit rule goes from the command. ADR-0167's point is that the apply
    commit carries message flags only and is proven by tree hash; without the rule
    stated, nothing tells the agent which commit forms are forbidden."""
    f = os.path.join(d, "commands", "branch-commit.md")
    body = open(f).read().replace("bare `git commit` carrying message flags only",
                                  "a commit carrying whatever flags fit")
    open(f, "w").write(body)
    return "the bare-commit rule reworded out of the command"


def mutate_retired_confirmation_rule_returns(d):
    """The retired wording comes back. ADR-0163 replaced confirmation-after-display
    with create-after-display, and scenario 125 used to fail a commit in the same
    reply; if the old sentence returns, the command teaches the retired contract."""
    f = os.path.join(d, "commands", "branch-commit.md")
    open(f, "a").write("\nConfirmation AFTER the display, in the same turn.\n")
    return "the retired confirmation-after-display rule reintroduced"



def mutate_scenario_number_collides(d):
    """Two scenarios claim the same number. Both files exist and read fine; what
    breaks is the number being an identifier."""
    sc = os.path.join(d, "evals", "scenarios")
    shutil.copy(os.path.join(sc, "01-example.md"), os.path.join(sc, "01-duplicate.md"))
    return "two scenarios claiming the same number"


def mutate_scenario_missing_from_index(d):
    """A scenario with no row in evals/README.md. The corpus grows and the index does
    not, so the regression net has a member nobody can find."""
    f = os.path.join(d, "evals", "README.md")
    open(f, "w").write("# Evals\n\n| scenario | covers |\n| --- | --- |\n")
    return "a scenario with no row in the index"


def mutate_walker_glob_narrows(d):
    """run-evals.sh stops enumerating the whole corpus. The walker still runs, still
    reports, and silently covers less than it did."""
    f = os.path.join(d, "evals", "scripts", "run-evals.sh")
    open(f, "w").write('#!/usr/bin/env bash\nALL_SCENARIOS=( "${SCENARIOS_DIR}"/9[0-9]*.md )\n')
    return "the walker glob narrowed to part of the corpus"


def build_engine_root(d):
    """A spec read map naming its engine topics, plus the topics and one authorized
    Unity command. Serves the four engine-scoped checks at once.
    """
    os.makedirs(os.path.join(d, "wos"), exist_ok=True)
    os.makedirs(os.path.join(d, "commands"), exist_ok=True)
    for n in ("godot-3d-scene.md", "unity-netcode-architecture.md"):
        with open(os.path.join(d, "wos", n), "w") as fh:
            fh.write(f"# {n[:-3]}\n\nA topic.\n")
    with open(os.path.join(d, "WORKFLOW_OPERATING_SYSTEM.md"), "w") as fh:
        fh.write("# Spec\n\nMinimum read map for execution:\n\n"
                 "- `wos/godot-3d-scene.md` when the surface is 3D.\n"
                 "- `wos/unity-netcode-architecture.md` for multiplayer.\n\n"
                 "## Next section\n\nUnrelated.\n")
    with open(os.path.join(d, "commands", "unity-scene-plan.md"), "w") as fh:
        fh.write("---\nname: unity-scene-plan\ndescription: d\n---\n"
                 "# unity-scene-plan\n\nHandles 2D and 3D surfaces.\n")
    return d


def mutate_engine_topic_leaves_the_read_map(d):
    """The topic file stays and its read-map row goes. A file-wide substring test
    would still pass, which is the mismatch the check's own comment describes."""
    f = os.path.join(d, "WORKFLOW_OPERATING_SYSTEM.md")
    body = open(f).read().replace("- `wos/godot-3d-scene.md` when the surface is 3D.\n", "")
    open(f, "w").write(body)
    return "an engine topic dropped from the read map while the file remains"


def mutate_command_names_2d_only(d):
    """A command mentions 2D and never 3D, which is 2D acting as the default
    dimension rather than a declared choice."""
    f = os.path.join(d, "commands", "unity-scene-plan.md")
    body = open(f).read().replace("Handles 2D and 3D surfaces.", "Handles 2D surfaces.")
    open(f, "w").write(body)
    return "a command naming 2D as though it were the default dimension"


def mutate_unauthorized_unity_command(d):
    """A second Unity command lands with no ADR naming it. ADR-0130 D-5 allowed none;
    ADR-0132 authorised exactly one."""
    with open(os.path.join(d, "commands", "unity-build-pipeline.md"), "w") as fh:
        fh.write("---\nname: unity-build-pipeline\ndescription: d\n---\n# unity-build-pipeline\n")
    return "an unauthorised Unity command added to the catalogue"



def mutate_unity_topic_leaves_the_read_map(d):
    """The Unity topic's own read-map row goes. Written separately from the Godot one
    because reusing that mutation left this guard ASLEEP: it removed the Godot row and
    this check reads the Unity one, so the mutation was pointed at the wrong object.
    """
    f = os.path.join(d, "WORKFLOW_OPERATING_SYSTEM.md")
    body = open(f).read().replace(
        "- `wos/unity-netcode-architecture.md` for multiplayer.\n", "")
    open(f, "w").write(body)
    return "the Unity topic dropped from the read map while the file remains"


def build_skill_descriptions_root(d):
    """A SKILLS ROOT (not a repo root) whose descriptions clear the ADR-0135 item-2 gate.

    `check_description_capability_floor` takes `root=` and passes it straight to
    `skill_descriptions`, where it IS the skills root, so the fixture writes
    `<d>/<name>/SKILL.md` rather than `<d>/.claude/skills/<name>/SKILL.md`.

    The capability segment has to clear 150 chars before the marker, or the control fails
    on the floor clause and never reaches the clause under test.
    """
    cap = ("Produces the example artifact for a task folder and records every input it "
           "could not reach, so the gap stays visible in the artifact instead of being "
           "assumed away by a later reader. ")
    for n in ("example-one", "example-two"):
        _skill(d, n, cap + "Use when the task needs that artifact and its inputs exist. "
                           "Do not use when the artifact already exists, or when the "
                           "inputs are still open.")
    return d


def mutate_description_loses_routing_marker(d):
    """The `Do not use` half goes, the `Use when` half stays.

    Quiet by construction: the description still reads well, still says what the skill
    does, and still clears the 150-char floor. What left is the half that keeps the skill
    from being routed to when it should not be.
    """
    f = os.path.join(d, "example-one", "SKILL.md")
    body = open(f).read()
    i = body.index("Do not use")
    open(f, "w").write(body[:i].rstrip() + "\n---\n\nBody.\n")
    return "a skill description with no `Do not use` routing marker"


def mutate_read_map_cites_a_missing_heading(d):
    """The read map orders a section that does not resolve. ADR-0006's map is what the
    agent follows, so a row pointing at nothing sends it looking for a heading that is
    not there."""
    f = os.path.join(d, "WORKFLOW_OPERATING_SYSTEM.md")
    body = open(f).read().replace(
        "- `wos/godot-3d-scene.md` when the surface is 3D.",
        "- `## A section that does not exist` when the surface is 3D.")
    open(f, "w").write(body)
    return "a read-map row citing a heading that does not resolve"


def build_count_marker_root(d):
    """A tree with one count marker that matches its on-disk count, plus the real
    `reconcile-counts.sh`.

    The script derives its own REPO_ROOT from `BASH_SOURCE`, not from the working
    directory, so copying it into the fixture points every disk count at the fixture.
    The real script is copied rather than reproduced because this check delegates the
    whole comparison to it: a reimplementation here would be measuring the copy.
    """
    os.makedirs(os.path.join(d, "scripts"), exist_ok=True)
    os.makedirs(os.path.join(d, "docs", "adr"), exist_ok=True)
    shutil.copy(os.path.join(REPO, "scripts", "reconcile-counts.sh"),
                os.path.join(d, "scripts", "reconcile-counts.sh"))
    for n in ("0001-first.md", "0002-second.md"):
        with open(os.path.join(d, "docs", "adr", n), "w") as fh:
            fh.write("# A decision\n")
    with open(os.path.join(d, "docs", "adr", "README.md"), "w") as fh:
        fh.write("# ADR index\n\n<!-- count:adrs -->2<!-- /count --> decisions.\n")
    return d


def mutate_count_marker_drifts_from_disk(d):
    """The marker says three, the directory holds two. This is the drift the marker
    convention exists to catch, and the shape it takes in practice is exactly this: an
    artifact is added or removed and one of the several homes of its count is missed."""
    f = os.path.join(d, "docs", "adr", "README.md")
    body = open(f).read()
    open(f, "w").write(body.replace("-->2<!--", "-->3<!--"))
    return "a count marker claiming 3 ADRs over a directory holding 2"


def build_wizard_root(d):
    """The installer script carrying only the three PROFILE= assignments ADR-0059 allows."""
    os.makedirs(os.path.join(d, "scripts"), exist_ok=True)
    with open(os.path.join(d, "scripts", "sync-workflow-slash-commands.sh"), "w") as fh:
        fh.write('#!/usr/bin/env bash\n'
                 'PROFILE="${PROFILE:-minimal}"\n'
                 'PROFILE_SET=0\n'
                 'set_profile() {\n'
                 '  PROFILE="$1"\n'
                 '  PROFILE_SET=1\n'
                 '}\n'
                 'case "${1:-}" in\n'
                 '  --profile=*) PROFILE="${1#--profile=}"; PROFILE_SET=1 ;;\n'
                 'esac\n'
                 'run_wizard() {\n'
                 '  case "$choice" in\n'
                 '    1) set_profile minimal ;;\n'
                 '    2) set_profile core ;;\n'
                 '  esac\n'
                 '}\n')
    return d


def mutate_wizard_assigns_profile_inline(d):
    """A wizard branch sets PROFILE directly instead of calling set_profile.

    This is the 2026-08-30 defect verbatim: PROFILE_SET stays 0, and
    skills_effective_profile() reads PROFILE_SET, so choosing the everyday loop installs
    every skill. The assignment sits inside a `case` branch, which is why the check's
    pattern is not line-anchored.
    """
    f = os.path.join(d, "scripts", "sync-workflow-slash-commands.sh")
    body = open(f).read()
    open(f, "w").write(body.replace(
        '    2) set_profile core ;;', '    2) PROFILE="core" ;;'))
    return "a wizard branch assigning PROFILE= without set_profile"


def mutate_dropped_variant_gains_a_rule(d):
    """A variant marked `None.` picks up a SHALL clause.

    The generator drops the variant on the `None.` prefix, so the rule never reaches any
    consumer's view, and check_closure_view_equivalence stays green because it decides
    "empty" with the same predicate the generator uses. Only a check that reads what was
    dropped can see this.
    """
    f = os.path.join(d, "wos", "closure-floors.md")
    body = open(f).read()
    i = body.index("None. Same reason as above.")
    j = i + len("None.")
    open(f, "w").write(body[:j] + " The runner SHALL emit the skipped rows anyway."
                       + body[j:])
    return "a rule written into a variant the generator drops as empty"


def build_canonical_views_root(d):
    """A canonical topic that HAS a generated view, and surfaces that point at the view.

    The check only fires for a canonical file with views, so the fixture needs both
    halves of the split plus at least one surface to scan.
    """
    os.makedirs(os.path.join(d, "wos"), exist_ok=True)
    os.makedirs(os.path.join(d, "commands"), exist_ok=True)
    with open(os.path.join(d, "wos", "closure-floors.md"), "w") as fh:
        fh.write("# The canonical floors\n\nEvery floor, every consumer.\n")
    with open(os.path.join(d, "wos", "closure-floors.task-close.md"), "w") as fh:
        fh.write("# task-close view\n\nOnly this consumer's floors.\n")
    with open(os.path.join(d, "WORKFLOW_OPERATING_SYSTEM.md"), "w") as fh:
        fh.write("# Spec\n\nAt closure, load `wos/closure-floors.task-close.md`.\n")
    with open(os.path.join(d, "commands", "task-close.md"), "w") as fh:
        fh.write("---\nname: task-close\ndescription: d\n---\n\n"
                 "Load `wos/closure-floors.task-close.md` and apply every floor in it.\n")
    return d


def mutate_spec_orders_the_canonical_file(d):
    """The spec sends the reader back to the monolith the split existed to avoid.

    This is the 2026-08-10 regression verbatim: the three closure commands moved to
    their views and WORKFLOW_OPERATING_SYSTEM.md:60 kept ordering the whole file
    loaded. Invisible to every other guard, because the canonical file still exists
    and check-doc-sync resolves the reference happily.
    """
    f = os.path.join(d, "WORKFLOW_OPERATING_SYSTEM.md")
    with open(f, "a") as fh:
        fh.write("\nBefore closing anything, load `wos/closure-floors.md` in full.\n")
    return "the spec ordering the canonical file loaded after its views exist"


def build_unconditional_load_root(d):
    """A command whose prose and frontmatter agree that one topic loads every run."""
    os.makedirs(os.path.join(d, "wos"), exist_ok=True)
    os.makedirs(os.path.join(d, "commands"), exist_ok=True)
    with open(os.path.join(d, "wos", "example-floors.md"), "w") as fh:
        fh.write("# Floors\n\nThe text this command pays for on every run.\n")
    with open(os.path.join(d, "commands", "example-command.md"), "w") as fh:
        fh.write("---\nname: example-command\ndescription: d\nmetadata:\n"
                 "  unconditional-loads: [wos/example-floors.md]\n---\n\n"
                 "# example-command\n\n"
                 "- **Floors (UNCONDITIONAL; `wos/example-floors.md`).** Load it and "
                 "apply every floor exactly as written there.\n")
    return d


def mutate_prose_load_undeclared(d):
    """The frontmatter declaration goes, the prose still calls the load unconditional.

    This is the half that hides cost: the Load gate measures SKILL.md alone, so text
    moved into a topic the command loads on every run satisfies the ceiling while the
    real per-invocation cost is unchanged.
    """
    f = os.path.join(d, "commands", "example-command.md")
    body = open(f).read()
    open(f, "w").write(body.replace(
        "metadata:\n  unconditional-loads: [wos/example-floors.md]\n", ""))
    return "prose calling a load unconditional with no frontmatter declaration"


def mutate_declared_load_unreferenced(d):
    """The declaration stays, every reference to the topic goes.

    The opposite direction, and a defect for the opposite reason: a declaration nobody
    honours inflates the measured cost, which makes the budget look tighter than it is
    and buys room that was never spent.
    """
    f = os.path.join(d, "commands", "example-command.md")
    body = open(f).read()
    head, _sep, _tail = body.partition("# example-command")
    open(f, "w").write(head + "# example-command\n\n- **Floors.** Apply every floor "
                       "exactly as the closure view states it.\n")
    return "a declared unconditional load the command never references"


def build_godot_tier_gate_root(d):
    """The real `godot-scene-plan` command, copied because the gate grades its own prose."""
    os.makedirs(os.path.join(d, "commands"), exist_ok=True)
    shutil.copy(os.path.join(REPO, "commands", "godot-scene-plan.md"),
                os.path.join(d, "commands", "godot-scene-plan.md"))
    return d


def mutate_tier_step_loses_required(d):
    """The declaring step stops saying REQUIRED.

    Everything else survives: the step is still there, still names the tiers, still
    states the consequence. Only the word that makes it a gate rather than a suggestion
    is gone, which is the shape a softening edit actually takes.
    """
    f = os.path.join(d, "commands", "godot-scene-plan.md")
    body = open(f).read()
    open(f, "w").write(body.replace(
        "Declare the renderer tier (REQUIRED for a 3D target",
        "Declare the renderer tier (recommended for a 3D target", 1))
    return "the renderer-tier step no longer marked REQUIRED"


def build_tier_floor_root(d):
    """The tier-declaration floor and the three commands that must cite it."""
    os.makedirs(os.path.join(d, "wos"), exist_ok=True)
    os.makedirs(os.path.join(d, "commands"), exist_ok=True)
    shutil.copy(os.path.join(REPO, "wos", "platform-runtime-floors.md"),
                os.path.join(d, "wos", "platform-runtime-floors.md"))
    for n in ("implement-approved-slice", "slice-closure", "task-close"):
        shutil.copy(os.path.join(REPO, "commands", f"{n}.md"),
                    os.path.join(d, "commands", f"{n}.md"))
    return d


def mutate_floor_loses_a_consumer_variant(d):
    """One consumer's variant leaves the floor.

    The floor still exists, the other two variants still read correctly, and the command
    still cites the floor by name. What is gone is the line telling that consumer what
    the floor means for it, so the citation points at nothing.
    """
    f = os.path.join(d, "wos", "platform-runtime-floors.md")
    body = open(f).read()
    head, sep, tail = body.partition("## Godot tier-declaration floor")
    block, sep2, rest = tail.partition("\n## ")
    open(f, "w").write(head + sep + block.replace("slice-closure variant",
                                                  "slice-closure note") + sep2 + rest)
    return "the tier-declaration floor missing its slice-closure variant"


def build_store_integrity_root(d):
    """The store-integrity bug-class template, copied: the check grades its frontmatter
    and its scope note, both of which are the artifact under test."""
    os.makedirs(os.path.join(d, "wos", "bug-classes"), exist_ok=True)
    shutil.copy(os.path.join(REPO, "wos", "bug-classes", "godot-monetization-integrity.md"),
                os.path.join(d, "wos", "bug-classes", "godot-monetization-integrity.md"))
    return d


def mutate_store_template_drops_csharp(d):
    """`csharp` leaves the languages list.

    The template keeps its name, its scope note and its file patterns, so nothing reads
    as broken. A Unity entitlement defect of the same CWE-602 class simply stops being
    scanned for, which is a coverage loss no other guard sees.
    """
    f = os.path.join(d, "wos", "bug-classes", "godot-monetization-integrity.md")
    body = open(f).read()
    open(f, "w").write(re.sub(r"^(languages:\s*\[.*?)csharp,?\s*", r"\1",
                              body, count=1, flags=re.M))
    return "the store-integrity template no longer declaring csharp"


def mutate_store_template_forked_for_unity(d):
    """A per-engine fork appears beside the widened template.

    ADR-0130 D-3 widens the one mechanism rather than forking it per engine; 69 of 78
    templates are already multi-stack. A fork passes every other guard, because it is a
    well-formed template.
    """
    f = os.path.join(d, "wos", "bug-classes", "unity-iap-entitlement.md")
    with open(f, "w") as fh:
        fh.write("---\nid: unity-iap-entitlement\ncategory: security\n"
                 "languages: [csharp]\n---\n\n# Unity IAP entitlement\n")
    return "a per-engine fork of the store-integrity mechanism"


def build_tier_artifact_root(d):
    """The real tier-declaration fixture corpus, copied whole (about 400 KB of text).

    This check is a parser conformance table: 30-odd directories, each a plan the
    declaration parser must reach a stated verdict on. The corpus IS the subject, so
    the fixture copies it rather than synthesising a smaller one, which would test a
    different parser than the one the repo ships.
    """
    src = os.path.join(REPO, "evals", "fixtures", "godot-tier-artifact")
    dst = os.path.join(d, "godot-tier-artifact")
    shutil.copytree(src, dst)
    return dst


def mutate_tier_fixture_verdict_flips(d):
    """A plan the parser must BLOCK is replaced by one it passes.

    The expectation table still says block, so this is the parser and the table
    disagreeing, which is the only thing this check measures. Copying a known-passing
    plan over a known-blocking one keeps the fence format exactly as the repo writes
    it, instead of encoding this harness's guess at it.
    """
    good = os.path.join(d, "3d-forward-plus", "GODOT_SCENE_PLAN.md")
    bad = os.path.join(d, "3d-no-tier", "GODOT_SCENE_PLAN.md")
    shutil.copyfile(good, bad)
    return "a fixture whose parser verdict no longer matches its expectation"


def mutate_tier_fixture_removed(d):
    """A directory the expectation table names leaves the corpus.

    The table keeps the entry, so the case stops being exercised while the check that
    exercises it keeps passing everything else. Erosion, not breakage, and this is the
    branch that sees it.
    """
    shutil.rmtree(os.path.join(d, "near-miss-table"))
    return "an expectation naming a fixture directory that is gone"


def _copy_into(d, *relatives):
    """Copy each repo-relative file into the fixture at the same path."""
    for rel in relatives:
        target = os.path.join(d, rel)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        shutil.copyfile(os.path.join(REPO, rel), target)
    return d


def build_commit_evidence_root(d):
    """The commit-evidence floor and its third home, the task-close bullet."""
    return _copy_into(d, "wos/closure-floors.md", "commands/task-close.md")


def mutate_floor_drops_bounded_deferral(d):
    """The floor stops naming direct-use `autonomous-run` as the bounded-deferral case.

    The routing survives, so the floor still offers both evidence classes. What is gone
    is the sentence assigning the deferral to the one context that cannot produce a
    human commit, which ADR-0197 added precisely because the floor otherwise blocks an
    unattended run at closure with no reachable path.
    """
    f = os.path.join(d, "wos", "closure-floors.md")
    body = open(f).read()
    open(f, "w").write(body.replace("Direct-use `autonomous-run`", "Direct autonomous use"))
    return "the floor no longer assigning bounded deferral to direct-use autonomous-run"


def mutate_task_close_bullet_drops_deferral(d):
    """The same removal, in the third home.

    Worth its own entry because the check reads this one through a SCOPED slice of the
    command rather than the whole file: task-close names these routes in several places,
    and a file-wide search stays green while the floor bullet itself loses them.
    """
    f = os.path.join(d, "commands", "task-close.md")
    body = open(f).read()
    open(f, "w").write(body.replace("Direct-use `autonomous-run`", "Direct autonomous use"))
    return "the task-close floor bullet no longer assigning bounded deferral"


def build_unity_adapter_root(d):
    """The two commands the Unity adapter lives in."""
    return _copy_into(d, "commands/app-runtime-verify.md", "commands/test-strategy.md")


def mutate_adapter_loses_managed_exception(d):
    """MANAGED_EXCEPTION leaves the taxonomy.

    The Step 5a block survives, the capture topic is still cited, and the command still
    reads as Unity-aware. The one taxonomy addition the managed-versus-native split
    requires is what left, so a managed crash has no code to be reported under.
    """
    f = os.path.join(d, "commands", "app-runtime-verify.md")
    body = open(f).read()
    open(f, "w").write(body.replace("MANAGED_EXCEPTION", "RUNTIME_EXCEPTION"))
    return "the Unity adapter without its MANAGED_EXCEPTION code"


def build_unity_multiplayer_root(d):
    """The netcode topic and the two commands that cite it."""
    return _copy_into(d, "wos/unity-netcode-architecture.md",
                      "commands/security-review.md",
                      "commands/performance-budget/SKILL.md")


def mutate_topic_loses_absent_scope(d):
    """The absent-scope section goes.

    Everything the topic DOES cover stays, so it reads as complete. That is the defect:
    the scope is one framework of six, and without the section saying so a reader takes
    the coverage for the landscape (ADR-0131 E-3).
    """
    f = os.path.join(d, "wos", "unity-netcode-architecture.md")
    body = open(f).read()
    open(f, "w").write(body.replace("Deliberately absent", "Further reading"))
    return "the netcode topic with no absent-scope section"


def mutate_engine_neutral_extraction_returns(d):
    """The engine-neutral extraction reappears.

    ADR-0131 E-2 rejected it on written evidence: the engine-neutral residue is two
    concepts and there is one consumer. It is the alternative that looks like an
    improvement to a later author, which is why it carries a guard rather than a note.
    """
    f = os.path.join(d, "wos", "netcode-transport-model.md")
    with open(f, "w") as fh:
        fh.write("# Netcode transport model\n\nThe engine-neutral half.\n")
    return "an engine-neutral multiplayer extraction back on disk"


def build_event_taxonomy_root(d):
    """The validator that owns the event taxonomy, plus one command that emits."""
    _copy_into(d, "scripts/verify-log-validator.py")
    os.makedirs(os.path.join(d, "commands"), exist_ok=True)
    with open(os.path.join(d, "commands", "example-command.md"), "w") as fh:
        fh.write("---\nname: example-command\ndescription: d\n---\n\n"
                 "# example-command\n\nEmit `event=write` when the artifact lands.\n")
    return d


def mutate_command_invents_an_event(d):
    """A command declares an event the validator does not know.

    Nothing local looks wrong: the line reads exactly like the canonical ones beside
    it. The validator rejects the name, so every line the command emits lands invalid,
    and the run that finds out is the one being audited.
    """
    f = os.path.join(d, "commands", "example-command.md")
    body = open(f).read()
    open(f, "w").write(body.replace("event=write", "event=artifact_written"))
    return "a command declaring an event outside the canonical taxonomy"


def build_operating_mode_root(d):
    """Every spine reader ADR-0162 names, plus the writer and the two commands whose
    strict-mode routing the check reads."""
    names = set(se.SPINE_OPERATING_MODE_READERS) | {
        "task-init", "implementation-plan", "implement-approved-slice"}
    return _copy_into(d, *[f"commands/{n}.md" for n in sorted(names)])


def mutate_reader_loses_operating_mode_bullet(d):
    """One spine reader stops reading the Resume notes operating mode.

    The command still works, still routes, still closes. It just no longer knows
    whether the task declared strict, which is scenario 08's mode-drift failure: not a
    command doing the wrong thing, a command with no rule to read the mode at all.
    """
    f = os.path.join(d, "commands", "review-hard.md")
    body = open(f).read()
    open(f, "w").write(body.replace(se.OPERATING_MODE_READER_BULLET,
                                    "Operating mode (ADR-0008)."))
    return "a spine reader without the ADR-0162 operating-mode bullet"


def mutate_writer_gains_reader_bullet(d):
    """task-init picks up the reader bullet.

    The opposite direction and the reason the check asserts absence as well as
    presence: task-init WRITES the Resume notes line, so a rule telling it to read the
    mode from the file it is about to create reads as coverage and is a contradiction.
    """
    f = os.path.join(d, "commands", "task-init.md")
    with open(f, "a") as fh:
        fh.write(f"\n- **{se.OPERATING_MODE_READER_BULLET}** Read the declared mode.\n")
    return "the mode WRITER carrying the subsequent-reader bullet"


def build_unity_scene_plan_root(d):
    """The Unity scene-plan command and the command that routes to it."""
    return _copy_into(d, "commands/unity-scene-plan.md", "commands/implementation-plan.md")


def mutate_scene_plan_loses_per_component_authority(d):
    """Step 4 stops requiring per-component authority.

    The 2026-08-07 dogfood's sharpest finding. Without it a plan can name a server-side
    input sampler and a client-side movement simulator, satisfy every other rule, pass
    self-review, and describe a cheatable architecture.
    """
    f = os.path.join(d, "commands", "unity-scene-plan.md")
    body = open(f).read()
    open(f, "w").write(body.replace("owner-only, server-only, or everywhere",
                                    "the appropriate authority"))
    return "the scene plan without its per-component authority rule"


def mutate_engine_generalized_scene_plan(d):
    """A merged engine-axis scene-plan command appears.

    ADR-0069 D-4 forbids merging engines that share no vocabulary and permits
    capability-named siblings. The difference is invisible to every other guard,
    because a merged command is a well-formed command.
    """
    with open(os.path.join(d, "commands", "scene-plan.md"), "w") as fh:
        fh.write("---\nname: scene-plan\ndescription: d\n---\n\n# scene-plan\n")
    return "an engine-generalized scene-plan command"


def mutate_netcode_topic_deleted(d):
    """The topic file leaves the tree.

    Proves the absence guard is live. It used to be `if not topic` AFTER a read() that
    raises on a missing file, so it could only fire on a file that existed and was
    empty: the one case it was written for could never reach it.
    """
    os.remove(os.path.join(d, "wos", "unity-netcode-architecture.md"))
    return "the netcode topic gone from the tree"


def build_dispatch_fixture_root(d):
    """The sweep dispatch fixture family, copied whole: the README manifest and the
    seeded tree are both the subject, and the check's job is to make them agree."""
    src = os.path.join(REPO, "evals", "fixtures", "bug-class-dispatch")
    dst = os.path.join(d, "bug-class-dispatch")
    shutil.copytree(src, dst)
    return dst


def mutate_dispatch_prose_count_drifts(d):
    """The miss threshold a grader reads drifts from the expectation set.

    The one number the README states in prose rather than in a table, which is why it
    needs its own assertion: a case added to both tables leaves this sentence quietly
    wrong and nothing else notices.
    """
    f = os.path.join(d, "README.md")
    body = open(f).read()
    open(f, "w").write(body.replace("fewer than the 22 defect rows",
                                    "fewer than the 19 defect rows"))
    return "the README's stated defect-row count drifting from the expectation set"


def build_tier_routing_root(d):
    """Two commands in the same tier, one routing to the other.

    The check compares the router's profile set against the target's, so the fixture
    only needs a matched pair. Both are `minimal, core, full`, so the control has no
    missing tier anywhere.
    """
    os.makedirs(os.path.join(d, "commands"), exist_ok=True)
    for name, routes in (("router-command", True), ("target-command", False)):
        with open(os.path.join(d, "commands", f"{name}.md"), "w") as fh:
            fh.write(f"---\nname: {name}\ndescription: d\nmetadata:\n"
                     f"  x-wos-profiles: [minimal, core, full]\n---\n\n# {name}\n\n")
            if routes:
                fh.write("This command routes to `target-command` and hands off there.\n")
    return d


def mutate_route_target_leaves_the_tier(d):
    """The target drops out of the router's tiers.

    Both commands still exist, the route still reads correctly, and every other guard
    is satisfied. What broke is only visible from an install: a minimal session follows
    the route and the target is not there. This is the ADR-0178 shape.
    """
    f = os.path.join(d, "commands", "target-command.md")
    body = open(f).read()
    open(f, "w").write(body.replace("x-wos-profiles: [minimal, core, full]",
                                    "x-wos-profiles: [full]"))
    return "a route whose target no longer carries the router's tiers"


# The reviewer a minimal router dispatches, and the closure it drags in (ADR-0229).
REVIEWER_CLOSURE = ("review-hard", "verify-against-rubric", "direction-adjust",
                    "resolve-contract-gaps", "contract-signoff")


def build_reviewer_closure_root(d):
    """The real review-hard, the reviewer it dispatches, and that reviewer's closure.

    The shared blocks come too, because the check strips them before it reads a route
    and a fixture without them would see routes the real corpus hides. Routes to
    commands the fixture lacks are ignored by the check, so these five are the whole
    subject: review-hard's gated ADR-0145 route to verify-against-rubric, and the
    three routes that made retagging the reviewer alone fail.
    """
    rels = [os.path.join("commands", f"{n}.md") for n in REVIEWER_CLOSURE]
    rels += [os.path.relpath(f, REPO)
             for f in glob.glob(os.path.join(REPO, "commands", "_shared", "*.md"))]
    return _copy_into(d, *rels)


def mutate_reviewer_back_to_full(d):
    """verify-against-rubric returns to [full].

    The route that reaches it is gated ("WHEN this review's verdict names zero
    must-fix ..."), so the check before ADR-0229 exempted it: the target was
    full-only, and full-only was taken to mean a cluster command. It is the general
    reviewer, in no cluster, and a minimal install would again have no reviewer to
    dispatch. This mutation reported ASLEEP against that code.
    """
    f = os.path.join(d, "commands", "verify-against-rubric.md")
    body = open(f).read()
    open(f, "w").write(body.replace("x-wos-profiles: [minimal, core, full]",
                                    "x-wos-profiles: [full]"))
    return "verify-against-rubric retagged back to [full], reached by a gated route"


def build_substrate_emit_root(d):
    """The validator that defines the line schema, and the shared block that hand-rolls
    an emit conforming to it."""
    return _copy_into(d, "scripts/verify-log-validator.py", se.SUBSTRATE_BLOCK)


def mutate_hand_rolled_emit_drops_a_field(d):
    """The documented jq emit stops writing one field the validator requires.

    Nothing fails at the moment of the edit. Every command following the manual path
    emits a line the validator rejects, and that surfaces later as a broken audit
    trail, at the point where someone needs the trail.
    """
    f = os.path.join(d, se.SUBSTRATE_BLOCK)
    body = open(f).read()
    open(f, "w").write(body.replace("event:$event, mode:$mode,", "event:$event,", 1))
    return "a hand-rolled emit missing a field the validator requires"


def build_design_grounding_root(d):
    """Every command on the design-grounding list, copied: the check reads the marker
    out of each one."""
    rels = []
    for name in se.DESIGN_GROUNDING_COMMANDS:
        flat = os.path.join("commands", f"{name}.md")
        rels.append(flat if os.path.isfile(os.path.join(REPO, flat))
                    else os.path.join("commands", name, "SKILL.md"))
    return _copy_into(d, *rels)


def mutate_design_command_drops_grounding_marker(d):
    """One design command loses the reference-grounding marker.

    The command still decides against external contracts, still reads as complete. The
    first thing to notice an uncaptured contract is then the execution gate, mid-slice,
    after the plan was approved.
    """
    name = se.DESIGN_GROUNDING_COMMANDS[0]
    f = os.path.join(d, "commands", f"{name}.md")
    if not os.path.isfile(f):
        f = os.path.join(d, "commands", name, "SKILL.md")
    body = open(f).read()
    open(f, "w").write(body.replace("shared:reference-grounding-design",
                                    "shared:reference-grounding", 1))
    return "a design command with no reference-grounding marker"


def build_description_baseline_root(d):
    """A skills root and the baseline recording what each description references.

    The baseline is BUILT from the fixture rather than copied from the repo, because
    the check's whole job is to compare the two sides of the same corpus. Copying the
    real baseline over a synthetic corpus would report every skill as missing on one
    side, which is the calling error the check refuses outright.
    """
    for n, refs in (("alpha", "`beta` and `wos/example-topic.md`"), ("beta", "`alpha`")):
        _skill(d, n, f"Produces the {n} artifact. Reads {refs} before deciding. "
                     f"Use when that artifact is needed. Do not use once it exists.")
    live = se.description_references(se.skill_descriptions(d)[0])
    with open(os.path.join(d, "description-baseline.json"), "w") as fh:
        json.dump({"references": live}, fh)
    return d


def mutate_description_drops_a_reference(d):
    """A description stops naming a command the baseline records it naming.

    The description still reads well and still says what the skill does. What is gone
    is the pointer that routed a reader to the next command, and the drop is only
    visible against a record of what was there before.
    """
    f = os.path.join(d, "alpha", "SKILL.md")
    body = open(f).read()
    open(f, "w").write(body.replace("Reads `beta` and `wos/example-topic.md`",
                                    "Reads what it needs"))
    return "a description that stopped naming a reference the baseline records"


def build_bootstrap_floor_root(d):
    """The spec sections the floor measures, and the block that states the number."""
    return _copy_into(d, "WORKFLOW_OPERATING_SYSTEM.md", se.BOOTSTRAP_BLOCK)


def mutate_declared_bootstrap_floor_drifts(d):
    """The stated floor drifts past tolerance from what the four sections measure.

    This number is inlined into every command carrying the block, so a stale floor
    misprices every invocation. Nothing else reads it: it is prose about a measurement,
    and prose about a measurement is the thing that goes stale silently.
    """
    f = os.path.join(d, se.BOOTSTRAP_BLOCK)
    body = open(f).read()
    m = re.search(r"full tier is measured at (\d[\d,]*) tokens", body)
    stale = int(m.group(1).replace(",", "")) // 2
    open(f, "w").write(body.replace(m.group(0), f"full tier is measured at {stale} tokens"))
    return "a declared bootstrap floor half the measured size"


def mutate_reduced_tier_drifts(d):
    """The reduced-tier figure drifts past tolerance while the full one stays right.

    Until ADR-0226 the block said the reduced figure was not machine-checked, and it was
    not: a reduced figure half its size would have passed. The leaf-reviewer tier made a
    second measured figure, and the reduced one is measured with it.
    """
    f = os.path.join(d, se.BOOTSTRAP_BLOCK)
    body = open(f).read()
    m = re.search(r"reduced tier is about (\d[\d,]*)", body)
    stale = int(m.group(1).replace(",", "")) // 2
    open(f, "w").write(body.replace(m.group(0), f"reduced tier is about {stale}"))
    return "a declared reduced tier half its measured size"


def build_leaf_tier_root(d):
    """The spec, the bootstrap block, the reviewer, both dispatchers and the fleet variant.

    The fleet is in the fixture on purpose: it is the command most likely to copy the
    reviewer's declaration, and it writes VERIFICATION_LOG.md and dispatches workers, so it
    must stay on the full tier.
    """
    return _copy_into(d, "WORKFLOW_OPERATING_SYSTEM.md", se.BOOTSTRAP_BLOCK,
                      "commands/verify-against-rubric.md", "commands/approve-plan.md",
                      "commands/review-hard.md", "commands/verify-against-rubric-fleet.md")


def mutate_leaf_tier_figure_drifts(d):
    """The leaf-reviewer figure is halved: prose about a measurement, gone stale."""
    f = os.path.join(d, se.BOOTSTRAP_BLOCK)
    body = open(f).read()
    m = re.search(r"(leaf-reviewer tier[^.]*?measured at )(\d[\d,]*)( tokens)", body)
    stale = int(m.group(2).replace(",", "")) // 2
    open(f, "w").write(body.replace(m.group(0), f"{m.group(1)}{stale}{m.group(3)}"))
    return "a leaf-reviewer tier figure half what its section measures"


def mutate_leaf_tier_reads_guardrails_again(d):
    """The tier grows a second section. It reads as caution, and it is the full floor
    coming back one section at a time."""
    _drop(d, se.BOOTSTRAP_BLOCK, "reads only `## Global output contract`,",
          "reads only `## Global output contract` and `## Cross-cutting workflow guardrails`,")
    return "the leaf-reviewer tier reading the dispatch guardrails again"


def mutate_reviewer_stops_declaring_leaf_tier(d):
    """The block still names the reviewer, the reviewer no longer says so."""
    _drop(d, "commands/verify-against-rubric.md", "runs on the leaf-reviewer tier",
          "runs on the full tier")
    return "verify-against-rubric not declaring the tier the block puts it on"


def mutate_fleet_claims_leaf_tier(d):
    """The fleet orchestrator copies the reviewer's declaration. It writes the cohort log
    and dispatches workers, which is exactly what the skipped sections govern."""
    f = os.path.join(d, "commands", "verify-against-rubric-fleet.md")
    with open(f, "a") as fh:
        fh.write("\n- This command runs on the leaf-reviewer tier.\n")
    return "verify-against-rubric-fleet declaring a tier the block does not give it"


def mutate_dispatch_carries_authoring_context(d):
    """approve-plan's dispatch stops carrying only the artifact and the rubric."""
    _drop(d, "commands/approve-plan.md",
          "The dispatch carries the artifact path and the rubric and NOTHING else.",
          "The dispatch carries the artifact path, the rubric and a summary of the planning session.")
    return "approve-plan's blinded dispatch carrying the authoring context"


def build_bootstrap_copies_root(d):
    """The block, the spec it measures, and the two hand copies of its number the audit found
    stale: the FAQ and the context-budget topic."""
    return _copy_into(d, "WORKFLOW_OPERATING_SYSTEM.md", se.BOOTSTRAP_BLOCK, "docs/FAQ.md",
                      "wos/context-budget.md")


def mutate_faq_copies_a_stale_floor(d):
    """The FAQ goes stale against every stated tier (full 11678, reduced 10643, leaf 4841)."""
    _drop(d, "docs/FAQ.md", "about 11,678 tokens", "about 9,000 tokens")
    return "the FAQ quoting a bootstrap floor the block no longer declares"


def mutate_budget_topic_copies_a_stale_floor(d):
    """context-budget goes stale against every stated tier (full 11678, reduced 10643, leaf 4841)."""
    _drop(d, "wos/context-budget.md", "measured at 11678 tokens", "measured at 9,000 tokens")
    return "the context-budget topic quoting a stale bootstrap floor"


def build_runtime_parity_root(d):
    """Every runtime-verify command and every adapter battery topic.

    The check reads them as ONE corpus, because a taxonomy code may live in either
    surface; a fixture holding one surface would pass for the wrong reason.
    """
    rels = [os.path.join("commands", os.path.basename(f))
            for f in sorted(glob.glob(os.path.join(REPO, "commands", "*runtime-verify.md")))]
    rels += [os.path.join("wos", os.path.basename(f))
             for f in sorted(glob.glob(os.path.join(REPO, "wos", "*-runtime-battery.md")))]
    return _copy_into(d, *rels)


def mutate_taxonomy_code_leaves_the_corpus(d):
    """One taxonomy code stops appearing anywhere.

    The classification it named can no longer be emitted by any command, and the
    taxonomy that still defines it looks complete. Nothing breaks at the edit; a run
    that would have emitted the code simply emits nothing.
    """
    surface = sorted(se.RUNTIME_TAXONOMY)[0]
    code = sorted(se.RUNTIME_TAXONOMY[surface])[0]
    for f in glob.glob(os.path.join(d, "commands", "*.md")) + \
             glob.glob(os.path.join(d, "wos", "*.md")):
        body = open(f).read()
        if code in body:
            open(f, "w").write(body.replace(code, "GENERIC_FAILURE"))
    return f"the taxonomy code {code} present in no command and no adapter topic"


def build_experience_verdict_root(d):
    """The closure floors and the vocabulary file the attester wording keys on."""
    return _copy_into(d, "wos/closure-floors.md", "wos/gate-conditions.md")


def mutate_commit_becomes_the_attester(d):
    """The retired sentence comes back.

    A commit the agent created is machine evidence, so "that commit is the attester"
    performs exactly the substitution the same paragraph forbids. ADR-0179 removed it,
    and it is the kind of sentence a later author reinstates as a convenience.
    """
    f = os.path.join(d, "wos", "closure-floors.md")
    with open(f, "a") as fh:
        fh.write("\nWhere the slice ends in a local commit, that commit is the attester.\n")
    return "the retired `that commit is the attester` sentence back in the floors"


# Checks that CANNOT be mutation-tested, each with the reason it cannot. Without this
# list the uncovered number silently includes checks no fixture could ever cover, and
# "1 left to write" would be a promise the harness cannot keep. An entry here is a
# claim about the check's construction, not about how hard the fixture is: a check that
# is merely awkward belongs in the unwritten pile, not here.
UNMUTABLE = {
    "check_real_load_advisory":
        "returns (True, notes) unconditionally. It is an advisory measurement standing "
        "beside the ADR-0116 gate rather than a gate, deliberately, because the "
        "surrogation evidence says multiple measures beat one harder one. There is no "
        "failing input to build: making it capable of failing is a decision about the "
        "ceiling, not a fixture.",
}


def build_attended_chain_root(d):
    """The three surfaces that carry the self-running property, copied from the tree.

    Copied rather than synthesised because two of the assertions are exact sentences
    from the spec: a hand-written stand-in would prove the fixture matches itself.
    """
    return _copy_into(d, se.SPEC_PATH, "commands/approve-plan.md",
                      "templates/TASK_STATE.template.md")


def mutate_spec_drops_the_continuation_rule(d):
    """The spec stops saying an attended session continues in the same turn.

    Every command still works and every Handoff still names the next step. What changes
    is who acts on it: each `Run now:` becomes a prompt to the person, which is the
    friction the maintainer named on 2026-08-31 and which three ADRs removed.
    """
    f = os.path.join(d, se.SPEC_PATH)
    body = open(f).read()
    open(f, "w").write(body.replace(se.ATTENDED_CONTINUES,
                                    "the session reports it and waits"))
    return "the spec without the attended-continuation rule"


def mutate_spec_makes_approval_a_decision(d):
    """Plan approval goes back to being a stop.

    The sentence excluding it from reason 2 is the whole of ADR-0208's effect on the
    spec. Without it, the reason-2 list reads as covering approval, and the chain stops
    at the one place it used to stop.
    """
    f = os.path.join(d, se.SPEC_PATH)
    body = open(f).read()
    open(f, "w").write(body.replace(se.APPROVAL_NOT_REASON_TWO,
                                    "Approving a plan is a product decision"))
    return "the spec putting plan approval back under stop-reason 2"


def mutate_approve_plan_waits_for_a_person(d):
    """`approve-plan` picks up a wait.

    It reads as prudence, which is why it needs a guard rather than a review: nothing
    about the sentence looks wrong, and it reverses the decision that what remains at
    approval is a check against a rubric rather than a decision to make.
    """
    f = os.path.join(d, "commands", "approve-plan.md")
    with open(f, "a") as fh:
        fh.write("\nBefore writing the approval log, wait for the maintainer to confirm.\n")
    return "approve-plan waiting for a person again"


def mutate_task_state_restores_the_tier_label(d):
    """The retired tier label comes back in place of the disqualifier.

    `Tier: Standard` looks like more structure than `Escalations: impact-analysis (scope
    > 1 sentence)` and carries strictly less: the label did no routing work, the
    disqualifier did.
    """
    f = os.path.join(d, "templates", "TASK_STATE.template.md")
    body = open(f).read()
    open(f, "w").write(re.sub(r"(?m)^- Escalations:.*$",
                              "- Tier: [Express | Standard | Disciplined | Strict]", body))
    return "the retired Tier label back in the task record"


def build_scan_stamp_root(d):
    """A topic whose scan stamp and dated section agree: the section is not older."""
    os.makedirs(os.path.join(d, "wos"), exist_ok=True)
    with open(os.path.join(d, "wos", "example-topic.md"), "w") as fh:
        fh.write("# Example topic\n\n## Source currency\n\n"
                 "Last scanned: 2026-09-20\nCadence: 6 weeks\n\n"
                 "## Per-tool primitives (as of 2026-09-20)\n\n"
                 "| Tool | Primitive |\n|---|---|\n| Example | one |\n")
    return d


def mutate_section_older_than_its_scan_stamp(d):
    """The dated section falls behind the file's scan stamp.

    This is the live defect the check was written from, in miniature. The file says it
    was scanned on a date, a section under it claims currency as of an earlier one, and
    check-doc-currency.sh stays green because it reads the stamp's AGE and cannot see
    what the stamp covers.
    """
    f = os.path.join(d, "wos", "example-topic.md")
    body = open(f).read()
    open(f, "w").write(body.replace("## Per-tool primitives (as of 2026-09-20)",
                                    "## Per-tool primitives (as of 2026-06-05)"))
    return "a dated section older than the scan stamp that claims to cover it"


def mutate_currency_convention_leaves(d):
    """No file declares a scan stamp any more.

    Zero stamped files and "every stamp covers its claims" produce the same clean line,
    and the first is the convention being dropped rather than being satisfied.
    """
    f = os.path.join(d, "wos", "example-topic.md")
    body = open(f).read()
    open(f, "w").write(body.replace("Last scanned: 2026-09-20", "Reviewed recently"))
    return "the scan-stamp convention gone from the tree"


def build_bug_class_cwe_root(d):
    """Two templates on Allowed CWE ids, plus the versioned MITRE guidance.

    The guidance file is copied from the tree rather than synthesised: it IS the check's
    authority, and a hand-made stand-in would prove the fixture agrees with itself.
    """
    os.makedirs(os.path.join(d, "wos", "bug-classes"), exist_ok=True)
    os.makedirs(os.path.join(d, "evals"), exist_ok=True)
    shutil.copy(os.path.join(REPO, "evals", "cwe-mapping-guidance.json"),
                os.path.join(d, "evals", "cwe-mapping-guidance.json"))
    for n, cwe in (("null-deref", "CWE-476"), ("sql-injection", "CWE-89")):
        with open(os.path.join(d, "wos", "bug-classes", f"{n}.md"), "w") as fh:
            fh.write(f"---\nname: {n}\ncategory: correctness\ndefault-severity: P2\n"
                     f"cwe: [{cwe}]\nlanguages: [python]\n---\n\n# {n}\n")
    return d


def mutate_template_maps_to_prohibited_cwe(d):
    """A template picks up an id MITRE forbids mapping to.

    It reads as more grounding, not less: the frontmatter gains a CWE where it had one,
    and every other guard sees a well-formed template. What MITRE says about that
    specific id is the only thing that makes it wrong, and nothing in the tree knew it
    until the guidance file was versioned.
    """
    f = os.path.join(d, "wos", "bug-classes", "null-deref.md")
    body = open(f).read()
    open(f, "w").write(body.replace("cwe: [CWE-476]", "cwe: [CWE-1076]"))
    return "a template mapping to a Prohibited CWE id"


def mutate_guidance_list_emptied(d):
    """The prohibited list goes empty.

    Zero forbidden ids and "no template maps to one" read identically, and the first is
    the authority being lost rather than the corpus being clean.
    """
    f = os.path.join(d, "evals", "cwe-mapping-guidance.json")
    body = json.loads(open(f).read())
    body["prohibited"] = []
    open(f, "w").write(json.dumps(body))
    return "the guidance file with an empty prohibited list"



def mutate_guidance_extract_goes_stale(d):
    """The extract's own date falls past its cadence.

    Proves the age half of the check fires. It is soft by design, so this asserts the
    line appears rather than that the build turns red: a snapshot that outlived its
    cadence can be wrong about an id that moved upstream, and the only honest response
    is to say so where someone reads it.
    """
    f = os.path.join(d, "evals", "cwe-mapping-guidance.json")
    body = json.loads(open(f).read())
    body["_provenance"]["extracted"] = "2019-01-01"
    open(f, "w").write(json.dumps(body))
    return "a guidance extract long past its declared cadence"

def build_memory_consume_root(d):
    """The four files the consume-path check reads, copied: each assertion is a clause in
    the real file, and a synthetic stand-in would prove the fixture matches itself."""
    return _copy_into(d, "commands/task-init.md", "commands/impact-analysis.md",
                      "scripts/memory-lint.sh", "scripts/sync-workflow-slash-commands.sh")


def _drop(d, rel, needle, replacement):
    f = os.path.join(d, rel)
    body = open(f).read()
    assert needle in body, f"fixture lost its mutation target: {needle}"
    open(f, "w").write(body.replace(needle, replacement, 1))


def mutate_task_init_reads_references_again(d):
    """task-init goes back to reading the references file. It reads as diligence, which is
    why it needs a guard: the file grows with every capture and the command writes a link."""
    _drop(d, "commands/task-init.md",
          "check that it EXISTS and link to it; do NOT read it here",
          "read it for external references with freshness metadata")
    return "task-init reading REFERENCES.md again"


def mutate_ranker_resolved_against_task_repo(d):
    """The ranker goes back to a relative path, which on an install resolves against the task
    repository, where there is no scripts/, and the LEARNINGS step skips in silence."""
    _drop(d, "commands/task-init.md",
          "Resolve `scripts/rank-learnings.sh` against the WORKFLOW ROOT",
          "Run `scripts/rank-learnings.sh`")
    return "the learnings ranker resolved against the task repository"


def mutate_impact_analysis_forgets_prior_work(d):
    """The prior-analyses step leaves impact-analysis, and 292 analyses go back to sitting on
    disk unread, which is the state the August research found."""
    _drop(d, "commands/impact-analysis.md",
          "Prior analyses in this project (ADR-0214)", "Repo context")
    return "impact-analysis without the prior-analyses step"


def mutate_memory_lint_requires_tags(d):
    """Tags becomes required again, against ADR-0071. Every entry that predates the field
    gets reported as malformed, which is noise that teaches people to ignore the lint."""
    _drop(d, "scripts/memory-lint.sh",
          'check_learning_field "Tags" value-only', 'check_learning_field "Tags" required')
    return "memory-lint requiring the optional Tags field"


def mutate_installer_stops_shipping_ranker(d):
    """The installer drops the ranker from the runtime payload. task-init still names it and
    still resolves it against the workflow root, and finds nothing there."""
    # Keyed on the list's head, not the whole line, so the mutation survives the list growing
    # (it broke when ADR-0224 added eleven entries).
    _drop(d, "scripts/sync-workflow-slash-commands.sh",
          "SHIPPED_SCRIPTS=(rank-learnings.sh ", "SHIPPED_SCRIPTS=(")
    return "the installer no longer shipping the learnings ranker"


def build_mode_gate_root(d):
    """task-init and self-critique-and-revise (fixed, ADR-0220), the pending command (still
    gated), the spec and the FAQ, copied: the check reads the real Artifact changes lines, and a
    stand-in would test itself."""
    return _copy_into(d, "commands/task-init.md", "commands/compact-task-memory.md",
                      "commands/self-critique-and-revise.md", "WORKFLOW_OPERATING_SYSTEM.md",
                      "docs/FAQ.md")


def mutate_task_init_gates_on_mode_again(d):
    """task-init's Artifact changes line goes back to APPLIED only in Agent mode. It is the
    exact residue ADR-0199 left behind: the command it says it shrank, still gated."""
    _drop(d, "commands/task-init.md",
          "marks task-memory writes `APPLIED` in every mode (ADR-0199)",
          "marks task-memory writes as `APPLIED` only if you are actually persisting files in Agent mode")
    return "task-init conditioning APPLIED on the mode again"


def mutate_pending_command_loses_its_gate(d):
    """A pending command stops carrying the gate. The pending list still names it, and an
    exemption that outlives what it names becomes a hole the next regression walks through."""
    _drop(d, "commands/compact-task-memory.md",
          "`APPLIED` only when explicitly persisting in Agent mode",
          "`APPLIED` in every mode")
    return "a pending exemption naming a command that no longer carries the gate"


def mutate_faq_restores_the_old_gate(d):
    """The FAQ goes back to promising PROPOSED-by-default writes, the first thing a new user
    reads about how Fhorja treats their files."""
    _drop(d, "docs/FAQ.md",
          "(every command lists what it wrote under `### Artifact changes`",
          "(PROPOSED-by-default writes; full artifact content emitted inline")
    return "the FAQ describing the removed write gate as current"


def build_tier_condition_root(d):
    """implement-approved-slice and what-next, copied: the two commands that carried a live
    condition on a retired tier name on 2026-09-22. implement-approved-slice also carries the
    history note that names Express as retired, so the control proves that note is not read as
    a condition."""
    return _copy_into(d, "commands/implement-approved-slice.md", "commands/what-next.md")


def mutate_last_slice_commit_keyed_on_express_again(d):
    """The last-slice commit goes back to "when the pipeline is Express", the exact condition
    that could not be true after ADR-0207 and that only a model's inference kept firing."""
    _drop(d, "commands/implement-approved-slice.md",
          "When the run is attended and no `commit-ref` exists yet,",
          "When the pipeline is Express, the run is attended, and no `commit-ref` exists yet,")
    return "the last-slice commit keyed on the retired Express name"


def mutate_what_next_rechecks_a_tier_again(d):
    """what-next goes back to re-checking "the Express tier" instead of the escalations."""
    _drop(d, "commands/what-next.md",
          "**Re-check the escalations (ADR-0184, ADR-0207):**",
          "**Re-check the Express tier (ADR-0025):**")
    return "what-next re-checking a retired tier name"


def build_mode_gate_phrasing_root(d):
    """Real files from each place the audit found the gate restated, copied. compact-task-memory
    keeps the gate (ADR-0220), task-workspace gates a git act, task-close keeps a mode condition
    on its worktree teardown line only (ADR-0222), the roles file names the kept gate, and the
    spec names the retired gate to say it is replaced: the control proves none of those five
    reads as a finding."""
    return _copy_into(d, "commands/backend-system-design.md", "commands/compact-task-memory.md",
                      "commands/task-workspace.md", "commands/task-close.md", "wos/command-roles.md",
                      "evals/scenarios/88-backend-system-design.md", "WORKFLOW_OPERATING_SYSTEM.md")


def mutate_task_close_gates_outcome_append_again(d):
    """task-close's outcome append goes back to its pre-ADR-0222 mode condition. The whole file
    used to be skipped, so this passed; only the worktree teardown line may keep a condition now."""
    _drop(d, "commands/task-close.md",
          "The append is `APPLIED` in every mode (ADR-0222).",
          "In **Agent** mode the append is `APPLIED`; in Ask or Plan mode show the produced line as "
          "`PROPOSED` without appending.")
    return "task-close gating its outcome append on the mode again"


def mutate_task_close_gates_knowledge_note_again(d):
    """The knowledge note's Definition of done line goes back to APPLIED only in Agent mode."""
    _drop(d, "commands/task-close.md",
          "never silently inserted), marked `APPLIED` in every mode (ADR-0222);",
          "never silently inserted), marked `APPLIED` in Agent mode or `PROPOSED` otherwise;")
    return "task-close gating its knowledge note on the mode again"


def mutate_task_close_gates_reopen_again(d):
    """The reopen move goes back to its pre-ADR-0222 sentence, which opens with a capital "In"
    and so slipped past the pattern even before the file was skipped whole."""
    _drop(d, "commands/task-close.md",
          "Like the archive move, the reverse move and its writes are `APPLIED` in every mode (ADR-0222).",
          "In Ask or Plan mode propose the reverse move and updates as `PROPOSED` without executing.")
    return "task-close gating its reopen move on the mode again"


def mutate_design_command_marks_by_mode_again(d):
    """backend-system-design goes back to the parenthesized form, one of the three shapes the
    first mode-gate check could not see."""
    _drop(d, "commands/backend-system-design.md",
          "- The artifact is written and marked `APPLIED` in every mode (ADR-0199).",
          "- The artifact is marked PROPOSED (Ask) or APPLIED (Agent).")
    return "backend-system-design marking its artifact by editor mode again"


def mutate_scenario_grades_the_gate_again(d):
    """A scenario goes back to grading a write per editor mode, so a run that obeys ADR-0199
    would be scored as failing."""
    _drop(d, "evals/scenarios/88-backend-system-design.md",
          "is written and marked APPLIED whatever the editor mode;", "is persisted per editor mode;")
    return "a scenario grading the write per editor mode"


def mutate_topic_restores_proposed_by_default(d):
    """A wos topic describes writes as PROPOSED-by-default, outside commands/, which is where
    the first check never looked."""
    with open(os.path.join(d, "wos", "command-roles.md"), "a", encoding="utf-8") as fh:
        fh.write("\n- Writes are PROPOSED-by-default in Ask mode, then `approve-proposed` persists them.\n")
    return "a wos topic restating PROPOSED-by-default"


def build_tier_names_root(d):
    """The surfaces where the audit found tier names outside commands/, copied, plus two live
    uses of `Strict` the check must NOT read as a tier: the `strict` operating mode in
    wos/operating-modes.md and the ADR-0184 Strict surface in approve-plan."""
    return _copy_into(d, "commands/what-next.md", "commands/approve-plan.md",
                      "wos/workflow-shapes.md", "wos/operating-modes.md", "COMMAND_PROMPT_STUBS.md")


def mutate_shape_heading_names_a_tier_again(d):
    """The workflow-shapes heading goes back to the tier name the audit found there."""
    _drop(d, "wos/workflow-shapes.md",
          "## Well-scoped task (no escalation fired; the retired Express label, ADR-0025)",
          "## Express task (ADR-0025)")
    return "a wos heading named after the retired Express tier"


def mutate_stub_field_restores_complexity_tier(d):
    """The task-init-fleet stub goes back to `complexity_tier?`, a field no pipeline writes."""
    _drop(d, "COMMAND_PROMPT_STUBS.md", "escalations?", "complexity_tier?")
    return "the stubs naming the retired complexity_tier field"


def mutate_strict_tier_returns_as_a_trigger(d):
    """operating-modes goes back to keying the strict suggestion on the Strict tier, which the
    first check could not see because `Strict` was not in its pattern."""
    _drop(d, "wos/operating-modes.md",
          "- an auth, payments, compliance, PII, or multi-tenant isolation surface -> suggests `strict` "
          "(the categorical trip condition that survived the retired Strict tier, ADR-0207)",
          "- Strict tier -> suggests `strict`")
    return "the strict suggestion keyed on the Strict tier"


def build_loose_totals_root(d):
    """The three topics that carried a loose total on 2026-09-23, now wrapped or dropped, the
    README that states the CI job count, and the workflow it counts. Since D-11 also two command
    files and the shared-block README, whose derived-set totals are now markers."""
    return _copy_into(d, "wos/context-budget.md", "wos/workflow-patterns.md",
                      "wos/repository-structure.md", "README.md", ".github/workflows/lint.yml",
                      "commands/task-close.md", "commands/sync-task-state.md",
                      "commands/_shared/README.md")


def mutate_topic_restates_command_total(d):
    """A topic states the command total in prose again, the "53 commands" shape the audit found."""
    with open(os.path.join(d, "wos", "context-budget.md"), "a", encoding="utf-8") as fh:
        fh.write("\nThe bootstrap block reaches 53 commands.\n")
    return "a wos topic stating the command total as a loose number"


def mutate_current_total_beside_history(d):
    """A current total shares a paragraph line with a dated sentence. The whole-line history
    exemption let it through; the per-sentence one does not."""
    with open(os.path.join(d, "wos", "context-budget.md"), "a", encoding="utf-8") as fh:
        fh.write("\nThe block was trimmed on 2026-09-01. Today it reaches 53 commands.\n")
    return "a current command total beside a history sentence on the same line"


def mutate_fleet_total_loses_its_marker(d):
    """The fleet count goes back to a word, which nothing reconciles when an eighth fleet ships."""
    _drop(d, "wos/workflow-patterns.md",
          "two of the <!-- count:fleet-commands -->7<!-- /count --> fleet commands",
          "two of the seven fleet commands")
    return "the fleet total written as a word again"


def mutate_ci_job_count_goes_stale(d):
    """The README says CI runs four jobs, the stale number the audit found in the structure topic."""
    _drop(d, "README.md", "with six jobs:", "with four jobs:")
    return "the README naming a CI job count lint.yml does not declare"


def mutate_floor_total_loses_its_marker(d):
    """task-close types the recording-floor total by hand again, the shape it had before D-11:
    nothing reconciles "nine" when another floor moves to `record` in wos/closure-floors.md."""
    _drop(d, "commands/task-close.md",
          "<!-- count:closure-floors-record -->9<!-- /count --> floors now record",
          "nine floors now record")
    return "a command stating a closure floor total as a word"


def mutate_task_memory_total_loses_its_marker(d):
    """A command writes the task-memory file count as a bare digit again."""
    _drop(d, "commands/sync-task-state.md",
          "the <!-- count:task-memory-files -->4<!-- /count --> task-memory files",
          "the 4 task-memory files")
    return "a command stating the task-memory file count as a loose number"


def mutate_shared_consumers_typed_by_hand(d):
    """The shared-block README types a consumer count again, the "All 53 commands" column the audit
    found 45 commands behind the tree."""
    _drop(d, "commands/_shared/README.md",
          "<!-- count:shared-handoff-body -->98<!-- /count --> commands",
          "All 53 commands")
    return "the shared-block README typing a consumer count by hand"


def build_flag_table_root(d):
    """The stubs table and three commands: performance-budget cites release-plan's flag by name,
    implementation-plan owns a row, and task-close names git's `--force` to forbid it. The control
    proves a cross-reference and a tool option are not read as missing rows."""
    return _copy_into(d, "COMMAND_PROMPT_STUBS.md", "commands/performance-budget/SKILL.md",
                      "commands/release-plan.md", "commands/implementation-plan.md",
                      "commands/task-close.md")


def mutate_command_gains_an_unlisted_flag(d):
    """performance-budget names `--mobile` as its own flag again, the C32 shape: a flag no reader
    of the table can find."""
    with open(os.path.join(d, "commands", "performance-budget", "SKILL.md"), "a", encoding="utf-8") as fh:
        fh.write("\n- `--mobile`: switch to the React Native frame and bundle budgets.\n")
    return "a command flag with no row in the stubs table"


def mutate_table_row_outlives_its_flag(d):
    """The table keeps a row for a flag the command never names."""
    _drop(d, "COMMAND_PROMPT_STUBS.md", "| `implementation-plan` | `--spec` |",
          "| `implementation-plan` | `--draft` | Writes a draft plan. |\n| `implementation-plan` | `--spec` |")
    return "a stubs table row whose flag the command does not have"


def build_index_tables_root(d):
    """The two index tables, copied whole: the check reads their real headers and row shapes."""
    return _copy_into(d, "evals/README.md", "docs/adr/README.md")


def mutate_scenario_table_gains_a_blank_line(d):
    """A blank line lands inside the scenario index, the evals/README.md:149 defect: every row
    below it stops being a table row while the membership lint stays green."""
    body = open(os.path.join(d, "evals", "README.md"), encoding="utf-8").read()
    row = next(l for l in body.split("\n") if l.startswith("| 100 |"))
    _drop(d, "evals/README.md", row, "\n" + row)
    return "a blank line splitting the scenario index table"


def mutate_adr_row_drops_its_cells(d):
    """An ADR index row loses its Status and Tags cells, the shape 23 rows had on 2026-09-23."""
    body = open(os.path.join(d, "docs", "adr", "README.md"), encoding="utf-8").read()
    row = next(l for l in body.split("\n") if l.startswith("| [0199]"))
    _drop(d, "docs/adr/README.md", row, row.rsplit(" | Accepted | ", 1)[0] + " |")
    return "an ADR index row with two of its four cells"


def build_installer_flags_root(d):
    """The installer, the shared protocol and the drift script that named `--with-skills`, and
    the FAQ, which tells people to run the installer with `--project`."""
    return _copy_into(d, "scripts/sync-workflow-slash-commands.sh", "commands/_shared/substrate-write-protocol.md",
                      "scripts/check-installed-skills-drift.sh", "docs/FAQ.md")


def mutate_protocol_requires_with_skills(d):
    """The protocol goes back to telling people to pass `--with-skills`, as if skills needed it."""
    _drop(d, "commands/_shared/substrate-write-protocol.md",
          "- Run `bash scripts/sync-workflow-slash-commands.sh` to propagate to user-level skill registries (skills sync by default)",
          "- Run `bash scripts/sync-workflow-slash-commands.sh --with-skills` to propagate to user-level skill registries")
    return "the protocol presenting --with-skills as required"


def mutate_faq_names_a_flag_the_parser_rejects(d):
    """The FAQ tells people to pass a flag the installer does not have; they get exit 2."""
    _drop(d, "docs/FAQ.md", "sync-workflow-slash-commands.sh --project /path/to/your/repo",
          "sync-workflow-slash-commands.sh --target /path/to/your/repo")
    return "the FAQ naming an installer flag the parser rejects"


def mutate_installer_hides_a_flag_from_help(d):
    """The installer grows a flag that usage() never lists, so --help stops being the whole surface."""
    _drop(d, "scripts/sync-workflow-slash-commands.sh", "    --with-docs) WITH_DOCS=1 ;;",
          "    --with-docs) WITH_DOCS=1 ;;\n    --quiet) QUIET=1 ;;")
    return "an installer flag missing from --help"


def build_skill_roots_root(d):
    """The installer, whose usage names the default skill roots, and the three documents that
    tell a reader where a default install puts the skills (ADR-0228)."""
    return _copy_into(d, "scripts/sync-workflow-slash-commands.sh", "README.md", "docs/FAQ.md",
                      "docs/MIGRATION.md")


def mutate_readme_names_cursor_root_again(d):
    """README goes back to promising ~/.cursor/skills as a default root, as it did before ADR-0228."""
    _drop(d, "README.md", "<!-- skill-roots -->`~/.claude/skills` and `~/.agents/skills`<!-- /skill-roots -->",
          "<!-- skill-roots -->`~/.claude/skills`, `~/.cursor/skills` and `~/.agents/skills`<!-- /skill-roots -->")
    return "README naming ~/.cursor/skills among the default skill roots"


def mutate_faq_loses_skill_roots_span(d):
    """The FAQ rewrites its skill destinations sentence and drops the span, so its roots go unchecked."""
    _drop(d, "docs/FAQ.md", "<!-- skill-roots -->", "")
    return "the FAQ losing its skill-roots span"


def build_outcome_ledger_root(d):
    """The three commands that run the outcome helper, plus the installer that ships it."""
    return _copy_into(d, "commands/approve-plan.md", "commands/task-close.md",
                      "commands/review-hard.md", "scripts/sync-workflow-slash-commands.sh")


def mutate_approve_plan_appends_via_helper_again(d):
    """approve-plan goes back to running the helper with no append, the wording that let a
    run report the plan_review line APPLIED while no ledger existed."""
    _drop(d, "commands/approve-plan.md",
          " >> projects/<client__project>/OUTCOMES.jsonl`. A Strict-surface",
          "`. A Strict-surface")
    return "approve-plan running the helper without the append"


def mutate_task_close_appends_via_helper_again(d):
    """task-close's outcome line loses its append."""
    _drop(d, "commands/task-close.md",
          '\" >> projects/<client>__<project>/OUTCOMES.jsonl` (the helper',
          '\"` (the helper')
    return "task-close running the helper without the append"


def mutate_helper_leaves_the_payload(d):
    """The helper drops out of SHIPPED_SCRIPTS, so an install calls a script it does not have."""
    _drop(d, "scripts/sync-workflow-slash-commands.sh",
          "SHIPPED_SCRIPTS=(rank-learnings.sh compute-task-outcome.py ",
          "SHIPPED_SCRIPTS=(rank-learnings.sh ")
    return "the outcome helper left the install payload"


def build_workflow_root_scripts_root(d):
    """Two commands that resolve a script against the workflow root, plus the installer."""
    return _copy_into(d, "commands/capture-references.md", "commands/task-init.md",
                      "scripts/sync-workflow-slash-commands.sh")


def mutate_ingest_scan_leaves_the_payload(d):
    """The ASI06 scan drops out of SHIPPED_SCRIPTS while capture-references still resolves it."""
    _drop(d, "scripts/sync-workflow-slash-commands.sh",
          "SHIPPED_SCRIPTS=(rank-learnings.sh compute-task-outcome.py ingest-scan.py ",
          "SHIPPED_SCRIPTS=(rank-learnings.sh compute-task-outcome.py ")
    return "the ingest scan left the install payload"


def build_integrity_scripts_root(d):
    """Two commands that resolve an ADR-0224 script against the workflow root, plus the installer."""
    return _copy_into(d, "commands/approve-plan.md", "commands/task-close.md",
                      "scripts/sync-workflow-slash-commands.sh")


def mutate_integrity_wrapper_leaves_the_payload(d):
    """The closure integrity wrapper drops out of SHIPPED_SCRIPTS while task-close still resolves
    it, so every installed close runs a floor whose script is not there (ADR-0224)."""
    _drop(d, "scripts/sync-workflow-slash-commands.sh",
          # Neighbours included: the installer's comment names the script with spaces on both
          # sides too, and _drop replaces the first match.
          "verify-log-validator.py verify-substrate-batch.sh check-live-markers.sh",
          "verify-log-validator.py check-live-markers.sh")
    return "the integrity wrapper left the install payload"


def mutate_live_marker_check_leaves_the_payload(d):
    """The live-marker checker drops out of SHIPPED_SCRIPTS while approve-plan resolves it."""
    _drop(d, "scripts/sync-workflow-slash-commands.sh",
          "verify-substrate-batch.sh check-live-markers.sh check-plan-coverage.sh",
          "verify-substrate-batch.sh check-plan-coverage.sh")
    return "the live-marker checker left the install payload"


def build_output_blocks_root(d):
    """The two canonical shared blocks every command carries its output shape from."""
    return _copy_into(d, "commands/_shared/handoff-body.md", "commands/_shared/artifact-changes-default.md")


def mutate_handoff_block_points_at_spec_only(d):
    """The Handoff block goes back to a bare pointer at the spec."""
    body = open(os.path.join(d, "commands/_shared/handoff-body.md")).read()
    cut = body.index(" Every Handoff is one fenced")
    open(os.path.join(d, "commands/_shared/handoff-body.md"), "w").write(body[:cut] + "\n")
    return "the Handoff block pointing at the spec only"


def mutate_artifact_block_drops_lean_label(d):
    """The Artifact changes block stops requiring a label in Lean output."""
    _drop(d, "commands/_shared/artifact-changes-default.md", " in Lean output too;", ";")
    return "the Artifact changes block without the Lean-output label rule"


def build_mcp_routing_view_root(d):
    """The canonical MCP routing block and the wos copy task-init reads lazily."""
    return _copy_into(d, "commands/_shared/mcp-capability-routing.md", "wos/mcp-capability-routing.md")


def mutate_mcp_view_drifts(d):
    """The canonical block gains a sentence the wos copy never received."""
    path = os.path.join(d, "commands/_shared/mcp-capability-routing.md")
    open(path, "a").write("\nA new rule added only to the canonical block.\n")
    return "the canonical MCP block changed and the wos copy did not"


def build_projects_ignore_root(d):
    """The shared projects-ignore block and the two commands that create projects/."""
    return _copy_into(d, "commands/_shared/projects-ignore.md", "commands/task-init.md",
                      "commands/project-bootstrap.md")


def mutate_bootstrap_drops_projects_ignore(d):
    """project-bootstrap stops declaring the block, so a fresh project is committed again."""
    _drop(d, "commands/project-bootstrap.md", "<!-- shared:projects-ignore -->\n", "")
    return "project-bootstrap without the projects-ignore block"


def mutate_task_init_drops_ignore_check(d):
    """task-init stops checking an existing projects/ tree."""
    _drop(d, "commands/task-init.md", "check-ignore -q projects/<client>__<project>/", "check-ignore projects/")
    return "task-init without the ignore check"


def build_one_slice_route_root(d):
    """The three commands that carry the one-slice route and the lint that runs its check."""
    return _copy_into(d, "commands/task-init.md", "commands/implement-approved-slice.md",
                      "commands/autonomous-run.md", "scripts/lint-commands.sh")


def mutate_route_writes_one_lock_signal(d):
    """The route writes the Approval log line and not the phase stamp, the first draft's defect:
    implement-approved-slice then refuses every route task."""
    _drop(d, "commands/task-init.md", "`implementation (plan APPROVED, one-slice route)`",
          "`implementation (one-slice route)`")
    return "the one-slice route without the plan APPROVED stamp"


def mutate_route_check_not_run(d):
    """implement-approved-slice closes a route slice without the renumber check."""
    _drop(d, "commands/implement-approved-slice.md",
          "run `scripts/check-doc-sync.sh --against HEAD --repo <the repository the slice changed>`",
          "run the slice's validation")
    return "implement-approved-slice without the renumber check"


def mutate_autonomous_run_takes_route_line(d):
    """autonomous-run reads a route line as an approval for an unattended run."""
    _drop(d, "commands/autonomous-run.md", "A `one-slice route` line is not that entry",
          "A `one-slice route` line counts as that entry")
    return "autonomous-run accepting a route approval line"


def build_directive_root(d):
    """The directive template, AGENTS.md, and a CLAUDE.md built from the template's first
    paragraph. The real CLAUDE.md is maintainer memory the public tree does not ship, so the
    fixture writes its own rather than copying one that may be absent."""
    _copy_into(d, "templates/AGENT_DIRECTIVE.template.md", "AGENTS.md")
    block = open(os.path.join(REPO, "templates/AGENT_DIRECTIVE.template.md")).read().split("\n---\n")[1]
    first = block.strip("\n").split("\n\n", 1)[0]
    with open(os.path.join(d, "CLAUDE.md"), "w", encoding="utf-8") as fh:
        fh.write("# CLAUDE.md\n\n## Active task\n\n" + first + " (a measurement note)\n")
    return d


def mutate_agents_md_directive_drifts(d):
    """AGENTS.md rewords the directive and the template does not follow."""
    _drop(d, "AGENTS.md", "a typo fix is a task.", "a typo fix can skip it.")
    return "AGENTS.md reworded the directive"


def mutate_claude_md_directive_drifts(d):
    """CLAUDE.md loses a sentence of the directive's first paragraph."""
    _drop(d, "CLAUDE.md", "Do not edit a file before the task folder\nexists. ", "")
    return "CLAUDE.md dropped a directive sentence"


MUTATIONS = [
    ("check_skill_load_budget", build_skills_root, mutate_skill_over_ceiling,
     'Load-stage ceiling (ADR-0116)'),
    ("check_skill_load_ceiling_slack", build_skills_near_ceiling, mutate_ceiling_left_slack,
     'lower it to'),
    ("check_advertise_stage_budget", build_skills_root, mutate_description_emptied,
     'a skill with no description shrinks this surface'),
    ("check_spec_size_budget", build_spec_root, mutate_spec_over_ceiling,
     'non-regression ceiling'),
    ("check_supersession_marked", build_adr_root, mutate_supersession_unrecorded,
     'its Status line does not say so'),
    ("check_confidence_carveout_matches", build_carveout_root, mutate_carveout_unlisted,
     'declares a graded confidence field and the Part 1.3 carve-out does not name it'),
    ("check_structured_output_names_its_path", build_fleet_return_root, mutate_fleet_text_return,
     'stale worker-return carrier'),
    ("check_structured_output_names_its_path", build_fleet_return_root, mutate_fleet_worker_call,
     'stale worker-return carrier'),
    ("check_structured_output_names_its_path", build_fleet_return_root, mutate_fleet_missing_path,
     'mandates `StructuredOutput` without naming the dispatch path'),
    ("check_structured_output_names_its_path", build_fleet_return_root, mutate_fleet_artifact_parameter,
     'carries an `artifact=` mandate'),
    ("check_structured_output_names_its_path", build_fleet_return_root, mutate_fleet_empty_commands,
     'no command files found'),
    ("check_structured_output_names_its_path", build_fleet_return_root, mutate_fleet_dispatch_guidance,
     'stale worker-return carrier'),
    ("check_structured_output_names_its_path", build_fleet_return_root, mutate_fleet_template_carrier,
     'unavailable artifact= mandate in direct dispatch guidance'),
    ("check_corpus_wellformed", build_scenario_corpus_root, mutate_scenario_drops_failure_section,
     'missing FAIL/Failure section'),
    ("check_no_emdash", build_prose_root, mutate_prose_em_dash,
     '1 em-dash character(s)'),
    ("check_no_emdash", build_prose_root, mutate_prose_en_dash,
     '1 en-dash character(s)'),
    ("check_wos_topic_reachable", build_topic_reachability_root, mutate_topic_orphaned,
     'orphaned topic, not referenced from the read map'),
    ("check_command_frontmatter_name", build_commands_root, mutate_frontmatter_name_diverges,
     '!= basename'),
    ("check_shared_block_sources", build_commands_root, mutate_shared_marker_without_source,
     'has no _shared source'),
    ("check_required_sections", build_commands_root, mutate_dod_section_removed,
     "no '### Definition of done'"),
    ("check_handoff_basenames", build_commands_root, mutate_handoff_names_unknown_command,
     'Run now references unknown command'),
    ("check_task_state_template_sync", build_task_state_sync_root, mutate_template_drops_a_section,
     'are in the inline structure but not in templates/TASK_STATE.template.md'),
    ("check_task_state_template_sync", build_task_state_sync_root, mutate_template_reorders_sections,
     'the order diverges at position'),
    ("check_fanout_floor_consistency", build_fanout_floor_root, mutate_fleet_declares_lower_floor,
     "below the floor of 3, and is not in the '### Registered exceptions'"),
    ("check_fanout_floor_consistency", build_fanout_floor_root, mutate_spec_disagrees_with_floor,
     "does not say '3 or more independent items'"),
    ("check_closure_view_equivalence", build_closure_views_root, mutate_view_drops_a_floor,
     'absent from the view'),
    ("check_epistemic_doctrine_surfaces", build_epistemic_doctrine_root, mutate_command_skips_claim_grounding,
     'missing <!-- shared:claim-grounding --> marker'),
    ("check_epistemic_doctrine_surfaces", build_epistemic_doctrine_root, mutate_spec_fold_removed,
     "missing '### Claim status and abstention' H3"),
    ("check_adr_indexed", build_adr_root, mutate_adr_without_index_row,
     'no `| [0101]` row in docs/adr/README.md'),
    ("check_highest_adr_claim", build_adr_root, mutate_prose_names_stale_highest,
     'claims the highest ADR is 0099, disk says 0102'),
    ("check_command_frontmatter_name", build_commands_root, mutate_commands_dir_emptied,
     'no command files found'),
    ("check_adr_indexed", build_adr_root, mutate_adr_dir_emptied,
     'no numbered ADR files found'),
    ("check_no_emdash", build_prose_root, mutate_prose_surfaces_emptied,
     'no files to scan'),
    ("check_no_retired_frontmatter_field", build_commands_root, mutate_skill_declares_retired_field,
     'generated skill still carries token-budget'),
    ("check_criteria_content_floor", build_scenario_corpus_root, mutate_criteria_becomes_a_paragraph,
     'enumerable check(s), below the floor of 3'),
    ("check_floor_attester_class", build_floor_attester_root, mutate_floor_drops_its_attester,
     'declares no `Attester class:` line'),
    ("check_registry_membership", build_registries_root, mutate_command_missing_from_one_registry,
     'heading in wos/command-roles.md'),
    ("check_internal_refs_annotated", build_internal_refs_root, mutate_internal_ref_loses_its_annotation,
     'without saying it is maintainer-local and gitignored'),
    ("check_internal_refs_annotated", build_internal_refs_root, mutate_roadmap_points_into_internal,
     "ROADMAP.md:3: names _internal/ without saying"),
    ("check_private_repo_name_absent", build_old_repo_name_root, mutate_command_names_old_repo,
     "commands/team-update.md:2: names the private repository"),
    ("check_private_repo_name_absent", build_old_repo_name_root, mutate_script_banner_names_old_repo,
     "scripts/bootstrap-user-setup.sh:2: names the private repository"),
    ("check_bare_commit_tree_proof", build_branch_commit_root, mutate_bare_commit_rule_removed,
     'missing the bare-commit rule (ADR-0167)'),
    ("check_apply_commits_after_display", build_branch_commit_root, mutate_retired_confirmation_rule_returns,
     'retired confirmation-after-display rule is back'),
    ("check_scenario_numbers_unique", build_scenario_corpus_root, mutate_scenario_number_collides,
     'duplicate scenario number 01'),
    ("check_corpus_indexed", build_scenario_corpus_root, mutate_scenario_missing_from_index,
     'no row in evals/README.md'),
    ("check_walker_covers_corpus", build_scenario_corpus_root, mutate_walker_glob_narrows,
     'never enumerated'),
    ("check_scenario_content_floor", build_scenario_corpus_root, mutate_scenario_drops_failure_section,
     'below the 1200-char scenario floor'),
    ("check_godot_3d_topics_indexed", build_engine_root, mutate_engine_topic_leaves_the_read_map,
     'wos/godot-3d-scene.md: not referenced from the WORKFLOW_OPERATING_SYSTEM.md read map'),
    ("check_godot_dimension_routing", build_engine_root, mutate_command_names_2d_only,
     'mentions 2D but never 3D'),
    ("check_unity_no_new_command", build_engine_root, mutate_unauthorized_unity_command,
     'engine-named Unity command with no ADR authorizing it'),
    ("check_unity_topics_indexed", build_engine_root, mutate_unity_topic_leaves_the_read_map,
     'wos/unity-netcode-architecture.md: not referenced from the WORKFLOW_OPERATING_SYSTEM.md read map'),
    ("check_description_capability_floor", build_skill_descriptions_root, mutate_description_loses_routing_marker,
     'no `Do not use` routing marker'),
    ("check_read_map_headings_resolve", build_engine_root, mutate_read_map_cites_a_missing_heading,
     'resolves to no heading in the spec'),
    ("check_count_markers", build_count_marker_root, mutate_count_marker_drifts_from_disk,
     'count:adrs says 3, disk has 2'),
    ("check_wizard_sets_profile_set", build_wizard_root, mutate_wizard_assigns_profile_inline,
     'literal PROFILE= outside the default'),
    ("check_omitted_variant_carries_no_rule", build_closure_views_root, mutate_dropped_variant_gains_a_rule,
     'starts with `None.` so the generator drops it'),
    ("check_canonical_not_loaded_when_views_exist", build_canonical_views_root, mutate_spec_orders_the_canonical_file,
     "orders `wos/closure-floors.md` loaded"),
    ("check_unconditional_load_declared", build_unconditional_load_root, mutate_prose_load_undeclared,
     "prose calls the load of `wos/example-floors.md` unconditional"),
    ("check_unconditional_load_declared", build_unconditional_load_root, mutate_declared_load_unreferenced,
     "as an unconditional load but never references it"),
    ("check_godot_tier_gate", build_godot_tier_gate_root, mutate_tier_step_loses_required,
     "the renderer-tier step is not marked REQUIRED"),
    ("check_godot_tier_floor_variants", build_tier_floor_root, mutate_floor_loses_a_consumer_variant,
     "missing the slice-closure variant"),
    ("check_store_integrity_engine_agnostic", build_store_integrity_root, mutate_store_template_drops_csharp,
     "languages no longer declares csharp"),
    ("check_store_integrity_engine_agnostic", build_store_integrity_root, mutate_store_template_forked_for_unity,
     "per-engine fork of the store-integrity mechanism"),
    ("check_godot_tier_artifact_gate", build_tier_artifact_root, mutate_tier_fixture_verdict_flips,
     "expected 'block', got 'pass'"),
    ("check_godot_tier_artifact_gate", build_tier_artifact_root, mutate_tier_fixture_removed,
     "in the expectation set but not on disk"),
    ("check_commit_evidence_routes_to_apply", build_commit_evidence_root, mutate_floor_drops_bounded_deferral,
     "does not assign bounded deferral to direct-use `autonomous-run`"),
    ("check_commit_evidence_routes_to_apply", build_commit_evidence_root, mutate_task_close_bullet_drops_deferral,
     "commands/task-close: the commit-evidence floor bullet does not assign"),
    ("check_unity_adapter_surface", build_unity_adapter_root, mutate_adapter_loses_managed_exception,
     "lost the MANAGED_EXCEPTION code"),
    ("check_unity_multiplayer_surface", build_unity_multiplayer_root, mutate_topic_loses_absent_scope,
     "lost its absent-scope section"),
    ("check_unity_multiplayer_surface", build_unity_multiplayer_root, mutate_engine_neutral_extraction_returns,
     "engine-neutral multiplayer extraction"),
    ("check_unity_multiplayer_surface", build_unity_multiplayer_root, mutate_netcode_topic_deleted,
     "absent, but security-review and performance-budget cite it"),
    ("check_declared_event_in_taxonomy", build_event_taxonomy_root, mutate_command_invents_an_event,
     "which is not in the"),
    ("check_spine_reads_operating_mode", build_operating_mode_root, mutate_reader_loses_operating_mode_bullet,
     "missing the ADR-0162 operating-mode reader bullet"),
    ("check_spine_reads_operating_mode", build_operating_mode_root, mutate_writer_gains_reader_bullet,
     "carries the reader bullet; task-init is the writer"),
    ("check_unity_scene_plan_gates", build_unity_scene_plan_root, mutate_scene_plan_loses_per_component_authority,
     "lost the per-component authority rule in Step 4"),
    ("check_unity_scene_plan_gates", build_unity_scene_plan_root, mutate_engine_generalized_scene_plan,
     "engine-generalized scene-plan command"),
    ("check_bug_class_dispatch_cases", build_dispatch_fixture_root, mutate_dispatch_prose_count_drifts,
     "prose says 19 defect rows"),
    ("check_tier_routing_closure", build_tier_routing_root, mutate_route_target_leaves_the_tier,
     "missing tier(s)"),
    ("check_tier_routing_closure", build_reviewer_closure_root, mutate_reviewer_back_to_full,
     "review-hard -> verify-against-rubric"),
    ("check_substrate_emit_teaches_full_schema", build_substrate_emit_root, mutate_hand_rolled_emit_drops_a_field,
     "the hand-rolled emit omits"),
    ("check_design_grounding_coverage", build_design_grounding_root, mutate_design_command_drops_grounding_marker,
     "does not carry"),
    ("check_description_reference_preservation", build_description_baseline_root, mutate_description_drops_a_reference,
     "description no longer names"),
    ("check_bootstrap_floor_measured", build_bootstrap_floor_root, mutate_declared_bootstrap_floor_drifts,
     "per cent gap over the"),
    ("check_bootstrap_floor_measured", build_bootstrap_floor_root, mutate_reduced_tier_drifts,
     "declares the reduced tier at about"),
    ("check_leaf_reviewer_tier", build_leaf_tier_root, mutate_leaf_tier_figure_drifts,
     "the leaf-reviewer tier declares"),
    ("check_leaf_reviewer_tier", build_leaf_tier_root, mutate_leaf_tier_reads_guardrails_again,
     "ADR-0226 says it reads exactly"),
    ("check_leaf_reviewer_tier", build_leaf_tier_root, mutate_reviewer_stops_declaring_leaf_tier,
     "does not declare so in its own text"),
    ("check_leaf_reviewer_tier", build_leaf_tier_root, mutate_fleet_claims_leaf_tier,
     "is not named in the block's tier sentence"),
    ("check_leaf_reviewer_tier", build_leaf_tier_root, mutate_dispatch_carries_authoring_context,
     "lost its reviewer isolation clause"),
    ("check_bootstrap_floor_measured", build_bootstrap_copies_root, mutate_faq_copies_a_stale_floor,
     "states the bootstrap at 9000 tokens"),
    ("check_bootstrap_floor_measured", build_bootstrap_copies_root, mutate_budget_topic_copies_a_stale_floor,
     "states the bootstrap at 9000 tokens"),
    ("check_runtime_verify_parity", build_runtime_parity_root, mutate_taxonomy_code_leaves_the_corpus,
     "is in no runtime-verify command"),
    ("check_experience_verdict_attester", build_experience_verdict_root, mutate_commit_becomes_the_attester,
     "'that commit is the attester' is back"),
    ("check_attended_chain_self_runs", build_attended_chain_root, mutate_spec_drops_the_continuation_rule,
     "no longer states that an attended session continues"),
    ("check_attended_chain_self_runs", build_attended_chain_root, mutate_spec_makes_approval_a_decision,
     "no longer excludes plan approval from stop-reason 2"),
    ("check_attended_chain_self_runs", build_attended_chain_root, mutate_approve_plan_waits_for_a_person,
     "puts a human turn back at plan approval"),
    ("check_attended_chain_self_runs", build_attended_chain_root, mutate_task_state_restores_the_tier_label,
     "the `Tier:` label is back"),
    ("check_scan_stamp_covers_its_claims", build_scan_stamp_root, mutate_section_older_than_its_scan_stamp,
     "is newer than the section it covers"),
    ("check_scan_stamp_covers_its_claims", build_scan_stamp_root, mutate_currency_convention_leaves,
     "no file declares `Last scanned:`"),
    ("check_cwe_mapping_allowed", build_bug_class_cwe_root, mutate_template_maps_to_prohibited_cwe,
     "which MITRE marks Prohibited"),
    ("check_cwe_mapping_allowed", build_bug_class_cwe_root, mutate_guidance_list_emptied,
     "no prohibited ids"),
    ("check_cwe_mapping_allowed", build_bug_class_cwe_root, mutate_guidance_extract_goes_stale,
     "warns:past its 180-day cadence"),
    ("check_memory_consume_path", build_memory_consume_root, mutate_task_init_reads_references_again,
     "reads REFERENCES.md again"),
    ("check_memory_consume_path", build_memory_consume_root, mutate_ranker_resolved_against_task_repo,
     "no longer resolves the learnings ranker against the workflow root"),
    ("check_memory_consume_path", build_memory_consume_root, mutate_impact_analysis_forgets_prior_work,
     "no longer reads prior analyses"),
    ("check_memory_consume_path", build_memory_consume_root, mutate_memory_lint_requires_tags,
     "treats Tags as required again"),
    ("check_memory_consume_path", build_memory_consume_root, mutate_installer_stops_shipping_ranker,
     "no longer ships rank-learnings.sh"),
    ("check_task_memory_written_in_every_mode", build_mode_gate_root, mutate_task_init_gates_on_mode_again,
     "conditions APPLIED on the mode"),
    ("check_task_memory_written_in_every_mode", build_mode_gate_root, mutate_pending_command_loses_its_gate,
     "no longer carries a mode gate"),
    ("check_task_memory_written_in_every_mode", build_mode_gate_root, mutate_faq_restores_the_old_gate,
     "describes the removed ADR-0001 write gate"),
    ("check_no_condition_on_a_retired_tier_name", build_tier_condition_root, mutate_last_slice_commit_keyed_on_express_again,
     "gates behavior on the retired tier name"),
    ("check_no_condition_on_a_retired_tier_name", build_tier_condition_root, mutate_what_next_rechecks_a_tier_again,
     "gates behavior on the retired tier name"),
    ("check_no_mode_gate_phrasing", build_mode_gate_phrasing_root, mutate_design_command_marks_by_mode_again,
     "states the retired mode gate ('PROPOSED (Ask'"),
    ("check_no_mode_gate_phrasing", build_mode_gate_phrasing_root, mutate_scenario_grades_the_gate_again,
     "states the retired mode gate ('persisted per editor mode'"),
    ("check_no_mode_gate_phrasing", build_mode_gate_phrasing_root, mutate_topic_restores_proposed_by_default,
     "wos/command-roles.md"),
    ("check_no_mode_gate_phrasing", build_mode_gate_phrasing_root, mutate_task_close_gates_outcome_append_again,
     "commands/task-close.md"),
    ("check_no_mode_gate_phrasing", build_mode_gate_phrasing_root, mutate_task_close_gates_knowledge_note_again,
     "commands/task-close.md"),
    ("check_no_mode_gate_phrasing", build_mode_gate_phrasing_root, mutate_task_close_gates_reopen_again,
     "commands/task-close.md"),
    ("check_no_condition_on_a_retired_tier_name", build_tier_names_root, mutate_shape_heading_names_a_tier_again,
     "retired tier name ('## Express task"),
    ("check_no_condition_on_a_retired_tier_name", build_tier_names_root, mutate_stub_field_restores_complexity_tier,
     "retired tier name ('complexity_tier'"),
    ("check_no_condition_on_a_retired_tier_name", build_tier_names_root, mutate_strict_tier_returns_as_a_trigger,
     "retired tier name ('Strict tier'"),
    ("check_artifact_totals_are_markers", build_loose_totals_root, mutate_topic_restates_command_total,
     "states a total ('53 commands')"),
    ("check_artifact_totals_are_markers", build_loose_totals_root, mutate_current_total_beside_history,
     "states a total ('53 commands')"),
    ("check_artifact_totals_are_markers", build_loose_totals_root, mutate_fleet_total_loses_its_marker,
     "of the seven fleet commands"),
    ("check_artifact_totals_are_markers", build_loose_totals_root, mutate_ci_job_count_goes_stale,
     "says CI runs 4 jobs"),
    ("check_artifact_totals_are_markers", build_loose_totals_root, mutate_floor_total_loses_its_marker,
     "states a total ('nine floors')"),
    ("check_artifact_totals_are_markers", build_loose_totals_root, mutate_task_memory_total_loses_its_marker,
     "states a total ('4 task-memory files')"),
    ("check_artifact_totals_are_markers", build_loose_totals_root, mutate_shared_consumers_typed_by_hand,
     "states a total ('53 commands')"),
    ("check_command_flags_in_stub_table", build_flag_table_root, mutate_command_gains_an_unlisted_flag,
     "names `--mobile` as a flag"),
    ("check_command_flags_in_stub_table", build_flag_table_root, mutate_table_row_outlives_its_flag,
     "lists `--draft` for `implementation-plan`"),
    ("check_index_tables_whole", build_index_tables_root, mutate_scenario_table_gains_a_blank_line,
     "breaks the index table (a blank line)"),
    ("check_index_tables_whole", build_index_tables_root, mutate_adr_row_drops_its_cells,
     "has 2 cells under a 4-column header"),
    ("check_installer_flags_documented", build_installer_flags_root, mutate_protocol_requires_with_skills,
     "presents `--with-skills` as the switch"),
    ("check_installer_flags_documented", build_installer_flags_root, mutate_faq_names_a_flag_the_parser_rejects,
     "with `--target`, which its parser rejects"),
    ("check_installer_flags_documented", build_installer_flags_root, mutate_installer_hides_a_flag_from_help,
     "accepts `--quiet` and usage() does not list it"),
    ("check_outcome_ledger_is_written", build_outcome_ledger_root, mutate_approve_plan_appends_via_helper_again,
     "without appending its output"),
    ("check_outcome_ledger_is_written", build_outcome_ledger_root, mutate_task_close_appends_via_helper_again,
     "without appending its output"),
    ("check_outcome_ledger_is_written", build_outcome_ledger_root, mutate_helper_leaves_the_payload,
     "left SHIPPED_SCRIPTS"),
    ("check_workflow_root_scripts_ship", build_workflow_root_scripts_root, mutate_ingest_scan_leaves_the_payload,
     "resolves scripts/ingest-scan.py against the workflow root"),
    ("check_workflow_root_scripts_ship", build_integrity_scripts_root, mutate_integrity_wrapper_leaves_the_payload,
     "resolves scripts/verify-substrate-batch.sh against the workflow root"),
    ("check_workflow_root_scripts_ship", build_integrity_scripts_root, mutate_live_marker_check_leaves_the_payload,
     "resolves scripts/check-live-markers.sh against the workflow root"),
    ("check_output_blocks_name_their_fields", build_output_blocks_root, mutate_handoff_block_points_at_spec_only,
     "no longer names the four Handoff lines"),
    ("check_output_blocks_name_their_fields", build_output_blocks_root, mutate_artifact_block_drops_lean_label,
     "no longer requires a label"),
    ("check_default_skill_roots_agree", build_skill_roots_root, mutate_readme_names_cursor_root_again,
     "names ['~/.agents/skills', '~/.claude/skills', '~/.cursor/skills'] as the default skill roots"),
    ("check_default_skill_roots_agree", build_skill_roots_root, mutate_faq_loses_skill_roots_span,
     "carries no skill-roots span"),
    ("check_mcp_routing_view_matches", build_mcp_routing_view_root, mutate_mcp_view_drifts,
     "differs from commands/_shared/mcp-capability-routing.md"),
    ("check_projects_ignore_in_creators", build_projects_ignore_root, mutate_bootstrap_drops_projects_ignore,
     "does not carry the projects-ignore block"),
    ("check_projects_ignore_in_creators", build_projects_ignore_root, mutate_task_init_drops_ignore_check,
     "ignore check on an existing projects/ is gone"),
    ("check_one_slice_route", build_one_slice_route_root, mutate_route_writes_one_lock_signal,
     "no longer names 'plan APPROVED'"),
    ("check_one_slice_route", build_one_slice_route_root, mutate_route_check_not_run,
     "does not run check-doc-sync.sh --against HEAD at inline close"),
    ("check_one_slice_route", build_one_slice_route_root, mutate_autonomous_run_takes_route_line,
     "reads a one-slice route line as the approval"),
    ("check_agent_directive_copies_match", build_directive_root, mutate_agents_md_directive_drifts,
     "does not carry the directive block"),
    ("check_agent_directive_copies_match", build_directive_root, mutate_claude_md_directive_drifts,
     "does not carry the directive's first paragraph"),
]


def _call(fn, d):
    """Point one check at the fixture at `d`, by whichever route it supports.

    Two routes exist and neither replaces the other. A check that declares `root=`
    names a narrower subpath (a skills root, an ADR root) and that parameter stays
    the more precise tool. Every other check resolves through `p()` or `_repo()` in
    structural-evals.py, and those consult a module-level `_ROOT` that the
    `fixture_root` context manager swaps for the duration of the call.

    Added 2026-09-18. Before it, this harness could only reach checks carrying an
    explicit `root=`, which was 18 of 60, and its own summary said so.
    """
    import inspect

    params = inspect.signature(fn).parameters
    if "root" in params:
        kwargs = {"root": d}
        # One check takes a second path, and it REFUSES a call carrying only one of the
        # two: a fixture corpus checked against the real baseline reports every skill on
        # one side as missing, which reads as catastrophe and is a calling error. So the
        # fixture supplies the baseline beside the corpus and this passes both. The file
        # sits at the fixture root, which `skill_descriptions` ignores because it globs
        # `<root>/*/SKILL.md`.
        if "baseline_path" in params:
            candidate = os.path.join(d, "description-baseline.json")
            if os.path.isfile(candidate):
                kwargs["baseline_path"] = candidate
        return fn(**kwargs)
    with se.fixture_root(d):
        return fn()


def run_one(name, build, mutate, verbose, expect=None):
    """Control then mutation, both required. Returns (ok, note).

    `expect` is a substring the mutated finding must contain. It is how an entry says
    WHICH of a check's failing branches it aimed at, and it is required on every check
    that has more than one. A check with a fail-closed branch fails on an empty subject
    as readily as on the defect, so a mutation that quietly destroys its own fixture
    still reports BITES and the check looks proven when nothing about it was measured.
    Two such mutations were written here on 2026-09-18, both from
    `open(f, "w").write(open(f).read()...)`, where the write handle truncates the file
    before the read runs. Both happened to report ASLEEP. The other direction is the
    one this argument closes.
    """
    fn = getattr(se, name)
    tmp = tempfile.mkdtemp(prefix="guard-mutation-")
    try:
        # A builder may return the directory the check should be POINTED at, which is
        # not always the temp root: a check taking `root=` sometimes wants a subpath
        # (a skills root, a fixture corpus). Returning nothing keeps the old meaning.
        d = build(tmp) or tmp
        ok, findings = _call(fn, d)
        if not ok:
            return (False, f"CONTROL FAILED on a clean fixture: {findings[:1]}")
        what = mutate(d)
        ok, findings = _call(fn, d)

        # A `warns:` expectation inverts the assertion, for the advisory HALF of a check
        # that has both. `check_cwe_mapping_allowed` fails on a Prohibited id and only
        # REPORTS a stale extract, so a mutation aging that extract cannot make the check
        # fail and the plain contract calls it ASLEEP. The half would then be the only
        # thing in the file with no proof at all, which is what this harness exists to
        # prevent. So the entry says which direction it expects, and both are asserted.
        if expect and expect.startswith("warns:"):
            needle = expect[len("warns:"):]
            if not ok:
                return (False, f"MUTATION FAILED THE BUILD: {what}; this entry expects a "
                               f"report, not a failure. Either the check hardened or the "
                               f"entry is wrong about which tier this is")
            if not any(needle in f for f in findings):
                return (False, f"WARNING DID NOT APPEAR: {what}; expected a finding naming "
                               f"{needle!r}, got {findings[:1]}")
            return (True, f"warns: {what}")

        if ok:
            return (False, f"MUTATION DID NOT BITE: {what}")
        if expect and not any(expect in f for f in findings):
            return (False, f"MUTATION BIT FOR THE WRONG REASON: {what}; expected a "
                           f"finding naming {expect!r}, got {findings[0][:120]!r}")
        if verbose:
            return (True, f"{what} -> {findings[0][:90]}")
        return (True, what)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main(argv):
    verbose = "--verbose" in argv or "-v" in argv
    total = len(se.CHECKS)
    covered = {e[0] for e in MUTATIONS}
    failures = []

    print(f"Guard mutation: {len(MUTATIONS)} mutation(s) over {len(covered)} check(s)\n")
    for entry in MUTATIONS:
        name, build, mutate = entry[0], entry[1], entry[2]
        expect = entry[3] if len(entry) > 3 else None
        ok, note = run_one(name, build, mutate, verbose, expect)
        label = "BITES" if ok else "ASLEEP"
        if ok and note.startswith("warns: "):
            label, note = "WARNS", note[len("warns: "):]
        print(f"[{label}] {name}")
        print(f"          {note}")
        if not ok:
            failures.append(name)

    # Reachability, measured rather than asserted. Until 2026-09-18 this counted
    # checks declaring `root=` and reported the rest as unreachable, which was true
    # then and is not now: structural-evals.py routes path resolution through p()
    # and _repo(), both reading a module-level _ROOT that `fixture_root` swaps, so a
    # check with no parameter can still be pointed at a fixture. The wall became a
    # queue, and the honest number to print is how much of that queue is written.
    #
    # What is still NOT claimed: reachable means a fixture can be aimed at the check,
    # never that the check is correct. A mutation proves the check rejects the ONE
    # input built for it. Nothing here says its predicate matches the rule it
    # advertises, which is a separate and unautomated question.
    explicit = [n for n, _, _, fn in se.CHECKS
                if "root" in fn.__code__.co_varnames[:fn.__code__.co_argcount]]
    unwritten = total - len(covered) - len(UNMUTABLE)
    print(f"\nCoverage: {len(covered)} of {total} check(s) have a fixture and a "
          f"mutation. Every check is reachable: {len(explicit)} by an explicit "
          f"root= parameter and {total - len(explicit)} through fixture_root. The "
          f"{unwritten} without an entry are unwritten, not unreachable.")
    for name, why in sorted(UNMUTABLE.items()):
        print(f"  Advisory by construction, no failing input exists: {name} -- {why}")
    if failures:
        print(f"\n{len(failures)} guard(s) did not prove they work: {', '.join(failures)}")
        return 1
    print("Every control passed and every mutation bit.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
