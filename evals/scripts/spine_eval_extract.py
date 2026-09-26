#!/usr/bin/env python3
"""spine_eval_extract.py: read an eval scenario, hand back prompt turns and rubric.

Pure functions over scenario text. It reaches no network, launches no process
and writes no file: the runner that fires a model imports this and stays the
only thing with side effects, so the reading half can be tested on its own.

The turn rule is concatenate, not pick. Measured on disk 2026-08-29: the first
'## Input prompt' section of scenario 08 carries TWO fenced blocks and the other
eight sections across the five spine scenarios carry one each. An extractor that
demanded exactly one block would silently refuse the scenario the manifest
elects, which is the defect this exists to avoid.

Nothing here returns an empty string quietly. A section with no fenced block is
reported unparseable and a rubric under three items raises, because a blank turn
or a two-item rubric becomes a false verdict downstream, and a false PASS is
worse than a missing one.
"""

import re

UNPARSEABLE = "ERROR: unparseable input prompt"

# Same header family check_corpus_wellformed() accepts in structural-evals.py,
# in falling priority. The corpus spans years and uses equivalent headings.
RUBRIC_HEADERS = (
    r"^##\s+Pass\s+criteria\s*$",
    r"^##\s+Expected\s+behavior",
    r"^##\s+Expected\s+response\s+shape",
)

_HEADING = re.compile(r"^(##\s+.*)$", re.M)
_FENCE = re.compile(r"^```[^\n]*\n(.*?)^```\s*$", re.M | re.S)


class RubricTooThin(Exception):
    """Fewer than three rubric items. Named so a caller can catch just this."""


# A fenced block is masked to spaces, newlines kept, so offsets in the mask line up with
# the original text and a heading position found in one indexes the other.
_FENCE_BLOCK = re.compile(r"^```[^\n]*\n.*?^```[^\n]*$", re.M | re.S)


def _mask_fences(text):
    """The same text with every fenced region blanked, length and line breaks preserved."""
    return _FENCE_BLOCK.sub(lambda m: re.sub(r"[^\n]", " ", m.group(0)), text)


def _sections(text):
    """[(heading, body), ...] in file order, for every '## ' heading OUTSIDE a fenced block.

    Fence-aware since 2026-08-30. A scenario quoting a document that has its own '## '
    headings, which is most of what a Setup block shows, used to have its section cut at
    the first quoted heading. Measured across the corpus that day: 15 of the 138 numbered
    scenarios carry at least one '## ' inside a fence, 05-drift-and-reconcile alone has 22.

    Scenario 03 is the case that shows what it costs. Its '## Setup' quotes an
    IMPLEMENTATION_PLAN carrying '## Slice 01' and '## Slice 02', so the section ended at
    offset 1470 instead of 2281 and the extracted setup lost both the slice's 'Scope:' and
    its 'Exit criteria', which is exactly the material the eval needs to grade against.
    """
    masked = _mask_fences(text)
    starts = [m.start() for m in _HEADING.finditer(masked)]
    out = []
    for k, start in enumerate(starts):
        eol = text.find("\n", start)
        eol = len(text) if eol == -1 else eol
        end = starts[k + 1] if k + 1 < len(starts) else len(text)
        out.append((text[start:eol].strip(), text[eol + 1:end]))
    return out


def read_setup(text):
    """The body of '## Setup', stripped. A literal 'None.' body reads as empty."""
    for heading, body in _sections(text):
        if re.match(r"^##\s+Setup\s*$", heading, re.I):
            body = body.strip()
            return "" if body.lower() in ("none.", "none") else body
    return ""


def input_prompt_sections(text):
    """[(heading, body), ...] for every heading matching '## Input prompt', in
    file order. Scenario 03, 01, 125 and 08 each carry more than one."""
    return [(h, b) for h, b in _sections(text)
            if re.match(r"^##\s+Input\s+prompt", h, re.I)]


def fenced_blocks(section_body):
    """Every fenced block in the section, in order, each stripped."""
    return [m.group(1).strip() for m in _FENCE.finditer(section_body)]


def turn_text(section_body):
    """All fenced blocks of the section, in order, joined by a blank line.
    UNPARSEABLE when the section carries none."""
    blocks = fenced_blocks(section_body)
    if not blocks:
        return UNPARSEABLE
    return "\n\n".join(blocks)


def build_prompt(setup, turns_so_far, turn_index, setup_mode="inline-context",
                 directive=None):
    """The text to send for turn `turn_index` (1-based).

    turns_so_far is [(user_text, assistant_text), ...] for the turns already
    answered, plus the current turn's user text as the last entry's first item.

    Turn 1 carries the setup as read-only context when the mode asks for it.
    Later turns carry an explicit transcript instead of relying on a session
    flag, so the runner works against any CLI, including one with no
    conversation state at all.

    `directive` is the paragraph a correctly installed Fhorja puts in the
    consuming repository's always-loaded instruction file (ADR-0189,
    `templates/AGENT_DIRECTIVE.template.md`). It leads turn 1 because a rubric
    that grades the command chain is grading a configuration that has it, and a
    prompt without it measures an install that is missing its last step. Passed
    in rather than read here, so this stays a pure function.
    """
    current = turns_so_far[turn_index - 1][0]
    if turn_index == 1:
        head = (directive.strip() + "\n\n") if directive else ""
        if setup_mode == "inline-context" and setup:
            return (head + "Setup context (read as given, do not re-derive):\n"
                    + setup + "\n\n" + current)
        return head + current
    lines = ["Continuing the same session. The transcript so far:", ""]
    for i in range(turn_index - 1):
        user, assistant = turns_so_far[i]
        lines.append(f"--- turn {i + 1} user ---")
        lines.append(user)
        lines.append(f"--- turn {i + 1} assistant ---")
        lines.append(assistant if assistant else "(no response captured)")
        lines.append("")
    lines.append(current)
    return "\n".join(lines)


def read_directive(path):
    """The agent directive paragraph out of `templates/AGENT_DIRECTIVE.template.md`.

    The template is prose with the paragraph fenced between two `---` rules, so
    users paste one block. This reads that block and nothing else. Returns "" when
    the file is absent or carries no fenced block: the eval then runs without the
    directive, which is a real configuration (an install missing its last step)
    rather than an error.
    """
    try:
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
    except OSError:
        return ""
    parts = text.split("\n---\n")
    if len(parts) < 3:
        return ""
    return parts[1].strip()


def rubric_items(text, scenario_name="<scenario>"):
    """The rubric as a list of strings. Numbered lines when the section has
    any, bullets otherwise. Raises RubricTooThin under three items."""
    body = None
    for pattern in RUBRIC_HEADERS:
        for heading, section in _sections(text):
            if re.match(pattern, heading, re.I):
                body = section
                break
        if body is not None:
            break
    if body is None:
        raise RubricTooThin(f"{scenario_name}: no rubric section found")
    # A criterion that wraps keeps its wrapped lines. Taking only the first line of each
    # item dropped the second half of the sentence the eval grades against: measured across
    # the corpus on 2026-08-30, 36 of 802 criteria in 14 files carry at least one
    # continuation line. The run stops at the first blank line rather than at the next item,
    # so a paragraph written after the last criterion is not glued onto it. The two rules
    # agree on every criterion in the corpus today (0 divergences); the blank-line one is
    # chosen because it stays right when a scenario later adds that trailing paragraph.
    lines = body.splitlines()
    starts = [i for i, l in enumerate(lines) if re.match(r"^\s*\d+\.\s", l)]
    if not starts:
        starts = [i for i, l in enumerate(lines) if re.match(r"^\s*[-*]\s", l)]
    items = []
    for k, start in enumerate(starts):
        end = starts[k + 1] if k + 1 < len(starts) else len(lines)
        chunk = [lines[start].strip()]
        for line in lines[start + 1:end]:
            if not line.strip():
                break
            chunk.append(line.strip())
        items.append(" ".join(chunk))
    if len(items) < 3:
        raise RubricTooThin(
            f"{scenario_name}: rubric has {len(items)} item(s), needs at least 3")
    return items
