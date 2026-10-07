#!/usr/bin/env bash
# Assemble isolated approval inputs from the caller's task, including on installs.
set -eu
exec python3 - "$@" <<'PY'
import hashlib
import json
import re
import sys
from pathlib import Path


def fail(message):
    raise ValueError(message)


def visible(text):
    """Mask examples and comments without moving source offsets."""
    result = []
    fence = None
    comment = False
    for line in text.splitlines(keepends=True):
        match = re.match(r"^ {0,3}(`{3,}|~{3,})", line)
        if not comment and match:
            marker = match[1]
            if fence is None:
                fence = (marker[0], len(marker))
            elif marker[0] == fence[0] and len(marker) >= fence[1] and not line[match.end():].strip():
                fence = None
            result.append(re.sub(r"[^\n\r]", " ", line))
            continue
        if fence:
            result.append(re.sub(r"[^\n\r]", " ", line))
            continue
        i = 0
        chars = list(line)
        while i < len(line):
            if not comment and line.startswith("<!--", i):
                comment = True
            if comment:
                if line.startswith("-->", i):
                    chars[i:i + 3] = "   "
                    i += 3
                    comment = False
                    continue
                if chars[i] not in "\r\n":
                    chars[i] = " "
            i += 1
        result.append("".join(chars))
    if fence or comment:
        fail("unclosed fence or comment")
    return "".join(result)


def clean_tail(text):
    # A following section's write annotation is not part of this quoted entry.
    return re.sub(r"(?m)^<!-- wos:write [^\n]*-->\r?\n(?:[ \t]*\r?\n)*\Z", "", text)


def section(text, title, required=True):
    mask = visible(text)
    headings = list(re.finditer(r"^## ([^\n\r]+)\r?$", mask, re.M))
    matches = [(i, h) for i, h in enumerate(headings) if h[1] == title]
    if len(matches) > 1:
        fail("duplicate section: " + title)
    if not matches:
        if required:
            fail("not found: section " + title)
        return None
    i, heading = matches[0]
    end = headings[i + 1].start() if i + 1 < len(headings) else len(text)
    start = text.find("\n", heading.end())
    return clean_tail(text[start + 1:end] if start != -1 else "")


def entries(body):
    mask = visible(body)
    heads = list(re.finditer(r"^### ([^\n\r]+)\r?$", mask, re.M))
    for i, h in enumerate(heads):
        end = heads[i + 1].start() if i + 1 < len(heads) else len(body)
        yield h[1], clean_tail(body[h.start():end])


def ids(text):
    # Inline code examples do not add decision references in the prose fallback.
    return set(re.findall(r"(?<![\w-])([DP]-\d+)(?![\w-])", text))


def digest(data):
    return hashlib.sha256(data).hexdigest()


def provisional_metadata(quote, key):
    fields = {"Evidence": [], "Impact": [], "Status": []}
    for line in visible(quote).splitlines():
        match = re.match(r"^[ \t]*(?:[-*] )?(?:\*\*)?(Evidence|Impact|Status)(?:\*\*)?:[ \t]*(.*)$", line)
        if not match:
            continue
        field, value = match.groups()
        if field == "Impact":
            combined = re.fullmatch(r"(normal|high)\.[ \t]+Status:[ \t]*(provisional)\.?", value)
            if combined:
                value = combined[1]
                fields["Status"].append(combined[2])
        fields[field].append(value)
    for field, values in fields.items():
        if not values or not values[0].strip():
            fail("missing provisional field " + field + ": " + key)
        if len(values) != 1:
            fail("duplicate provisional metadata " + field + ": " + key)
    if fields["Impact"][0] not in ("normal", "high", "normal.", "high.") or fields["Status"][0] not in ("provisional", "provisional."):
        fail("malformed provisional metadata: " + key)


def assemble(task):
    if not task.is_dir():
        fail("not found: task folder")
    sources = {}

    def read(name):
        path = task / name
        if not path.is_file():
            fail("not found: " + name)
        raw = path.read_bytes()
        sources[name] = digest(raw)
        return raw.decode("utf-8")

    plan = read("IMPLEMENTATION_PLAN.md")
    decisions = read("DECISIONS.md")
    locked = section(decisions, "Locked decisions")
    provisional = section(decisions, "Provisional decisions", required=False) or ""
    catalog = {}
    all_entries = []
    for kind, body in (("D", locked), ("P", provisional)):
        for title, quote in entries(body):
            match = re.match(r"([DP]-\d+)(?=[:\s]|$)", title)
            if not match:
                continue
            key = match[1]
            if key in catalog:
                fail("duplicate decision: " + key)
            catalog[key] = (kind, title, quote)
            all_entries.append((key, quote))

    cited = set()
    refs = {}
    for title, body in entries(section(plan, "Slices")):
        slice_id = re.split(r"[:\s]", title, maxsplit=1)[0]
        if slice_id in refs:
            fail("duplicate slice: " + slice_id)
        mask = visible(body)
        fields = re.findall(r"^[-*] \*{0,2}Decision-ref\*{0,2}:([^\n]*)$", mask, re.M)
        if len(fields) > 1:
            fail("duplicate Decision-ref: " + slice_id)
        # Exit criteria are another supported authorization surface, even when
        # a Decision-ref field exists. Inline examples remain non-authorizing.
        exits = re.findall(r"^[-*] \*{0,2}Exit criteri(?:on|a)\*{0,2}:([^\n]*)$", mask, re.M)
        text = fields[0] + "\n" + re.sub(r"`+[^`\n]*`+", "", "\n".join(exits)) if fields else re.sub(r"`+[^`\n]*`+", "", mask)
        selected = ids(text)
        if not selected:
            has_locked = any(k.startswith("D-") and "PROPOSED" not in v[1] for k, v in catalog.items())
            if has_locked or not re.search(r"\b(?:none|no)\b", text, re.I):
                fail("no explicit decision trace: " + slice_id)
        if fields:
            # Malformed IDs must not silently turn a missing decision into 'none'.
            malformed = re.findall(r"\b[DP]-[\w.-]*", fields[0])
            if any(not re.fullmatch(r"[DP]-\d+\.?", token) for token in malformed):
                fail("malformed Decision-ref: " + slice_id)
        for key in selected:
            if key not in catalog:
                fail("not found: cited decision " + key)
            kind, heading, quote = catalog[key]
            if kind != key[0] or "PROPOSED" in heading or re.search(r"<!--\s*PROPOSED\b", quote):
                fail("not active in correct section: " + key)
            if key.startswith("P-"):
                label = re.search(r"rests on provisional\b(.*)", text, re.I)
                if not label or key not in ids(label[1]):
                    fail("unlabeled provisional: " + key)
                provisional_metadata(quote, key)
            # Stale provisional choices and superseded locked decisions are not authorization.
            for other, value in all_entries:
                other_kind, other_title, _ = catalog[other]
                if "PROPOSED" in other_title:
                    continue
                fields = ("Replaces", "Supersedes") if key.startswith("P-") else ("Supersedes",)
                for line in visible(value).splitlines():
                    for field in fields:
                        source_kind = "P" if field == "Replaces" else "D"
                        if other_kind == source_kind and re.match(r"(?:[-*] )?" + field + r":", line) and key in ids(line):
                            fail("superseded citation: " + key + " by " + other)
            if re.search(r"\bSuperseded by\b", visible(quote), re.I):
                fail("superseded citation: " + key)
        refs[slice_id] = sorted(selected)
        cited.update(selected)
    if not refs:
        fail("not found: plan slices")

    # Follow only the cited provisional ancestry. The canonical coverage gate
    # also covers a Confirms origin through a later Replaces head (ADR-0235).
    parents = {}
    successors = {}
    for key, (kind, title, quote) in catalog.items():
        if kind != "P" or key[0] != "P" or "PROPOSED" in title:
            continue
        for line in visible(quote).splitlines():
            if re.match(r"(?:[-*] )?Replaces:", line):
                for origin in ids(line):
                    parents.setdefault(key, set()).add(origin)
                    successors.setdefault(origin, set()).add(key)
    ancestry = set()

    def visit(key, trail):
        if key in trail:
            fail("cyclic replacement: " + key)
        if key not in catalog:
            fail("not found: replacement origin " + key)
        kind, title, quote = catalog[key]
        if kind != "P" or key[0] != "P" or "PROPOSED" in title:
            fail("not active replacement origin: " + key)
        if len(successors.get(key, ())) > 1:
            fail("ambiguous replacement: " + key)
        if key in ancestry:
            return
        for origin in parents.get(key, ()):
            visit(origin, trail | {key})
        ancestry.add(key)

    for key in cited:
        if key.startswith("P-"):
            visit(key, set())

    # Transport linked locked entries, never the unrelated author history.
    for key, (kind, title, quote) in catalog.items():
        if kind != "D" or "PROPOSED" in title:
            continue
        for line in visible(quote).splitlines():
            if re.match(r"(?:[-*] )?Confirms:", line) and ids(line) & ancestry:
                if re.search(r"\bSuperseded by\b", visible(quote), re.I):
                    fail("superseded confirmation: " + key)
                for other_kind, other_title, other_quote in catalog.values():
                    if other_kind == "D" and "PROPOSED" not in other_title:
                        for relation in visible(other_quote).splitlines():
                            if re.match(r"(?:[-*] )?Supersedes:", relation) and key in ids(relation):
                                fail("superseded confirmation: " + key)
                cited.add(key)

    brief = None
    brief_source = None
    if (task / "README.md").is_file():
        brief = section(read("README.md"), "Brief", required=False)
        if brief is not None:
            brief_source = "README.md ## Brief"
            # A consumed intake brief is a task-local pointer, not another history file.
            pointer = re.fullmatch(r"\s*(?:See\s+)?(?:`BRIEF\.md`|BRIEF\.md|\[[^\]\n]+\]\(\./BRIEF\.md\)|\[[^\]\n]+\]\(BRIEF\.md\))\.?\s*", brief)
            if pointer:
                path = task / "BRIEF.md"
                if not path.resolve().is_relative_to(task.resolve()):
                    fail("brief pointer escapes task")
                brief = read("BRIEF.md")
                brief_source = "BRIEF.md"
            elif re.search(r"BRIEF\.md", brief) and not brief.strip().startswith(("#", "-")):
                # Do not turn an unsupported file pointer into a silently empty brief.
                if len(brief.strip().splitlines()) == 1 and re.search(r"\b(?:See|Source|Brief)\b|\]\(", brief, re.I):
                    fail("unsupported brief pointer")

    criteria = [
        "Per slice, does its behavior exceed the quoted locked D-N authorization? If none are locked, report that explicitly; identifier matching alone is insufficient.",
        "Do cited P-N choices remain labeled 'rests on provisional P-N', never counted as authorization, with independently verified Evidence and correct Impact? Return needs_revision for unresolved or unsupported Evidence, or Impact: normal touching data, security, payments or cost. An honest Evidence: none found passes only with Impact: high and a provisional label. Do not open author-history carriers referenced by an Evidence line; use narrow canonical branch code or verbatim brief evidence, otherwise record support as unverified.",
        "Does any slice or P-N drop, merge or reclassify stored user data or money values without quoting the brief line that authorizes it? An uncovered provisional rule needs Impact: high and Evidence: brief silent on <term>. If no brief is found this question is not applicable.",
        "Return satisfied, needs_revision or failed per criterion and per slice, with reasons, and an overall verdict. Do not add confidence fields."
    ]
    rubric = "# Locked authorization rubric\n\n" + "\n".join("- " + c for c in criteria)
    empty_locked = "None cited; no locked decisions to trace.\n" if not any(k.startswith("D-") for k in catalog) else "No locked D-N cited; P-N choices are provisional, never authorization.\n"
    rubric += "\n\n## Cited locked decisions\n" + ("\n".join(catalog[k][2] for k in sorted(cited) if k.startswith("D-")) or empty_locked)
    rubric += "\n## Cited provisional decisions\n" + ("\n".join(catalog[k][2] for k in sorted(cited) if k.startswith("P-")) or "None cited.\n")
    rubric += "\n## Slice references\n" + "\n".join(k + ": " + (", ".join(v) or "none locked") for k, v in refs.items())
    rubric += "\n\n## Verbatim brief\n" + (brief if brief is not None else "brief: none found, rubric carries none\n")
    return {
        "schema_version": 1,
        "artifact": {"path": str(task / "IMPLEMENTATION_PLAN.md"), "sha256": sources["IMPLEMENTATION_PLAN.md"]},
        "rubric": rubric,
        "sources": sources,
        "brief_source": brief_source,
    }


try:
    if len(sys.argv) != 2 or sys.argv[1] in ("-h", "--help"):
        print("Usage: build-plan-review-input.sh <task-folder>", file=sys.stderr)
        sys.exit(2)
    payload = assemble(Path(sys.argv[1]).resolve())
    print(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False))
except (ValueError, OSError, UnicodeError) as error:
    print("Review-input: not assembled (" + str(error) + ")", file=sys.stderr)
    sys.exit(2)
PY
