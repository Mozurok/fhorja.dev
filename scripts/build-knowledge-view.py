#!/usr/bin/env python3
"""Render a project's knowledge/ folder as a single offline, navigable HTML view.

Data source: the per-project human knowledge layer `projects/<client>__<project>/knowledge/`
(ADR-0054, ADR-0055): one Markdown note per closed task plus an `index.md` map of content,
wikilinked. This script READS that folder and renders a human-facing `KNOWLEDGE.html` inside
it: the index as the landing section, then each note, with Obsidian-style `[[wikilinks]]`
resolved to in-page links. It is the app-independent visual view (D-10); opening the folder
in Obsidian gives the graph and Canvas instead.

It RENDERS, never mutates (the ADR-0049 invariant). It does not read or expose the AI
task-memory; the knowledge layer is human-read only and is never auto-loaded by the AI.

This is NOT a full Markdown engine: it converts the subset the templates use (frontmatter
tags, headings, lists, inline bold and code, paragraphs) plus wikilink resolution. An
unresolved `[[link]]` degrades to muted text, never a crash.

Usage:
  python3 scripts/build-knowledge-view.py <project-folder>           # write <project>/knowledge/KNOWLEDGE.html
  python3 scripts/build-knowledge-view.py <project-folder> --stdout  # print HTML, do not write
  python3 scripts/build-knowledge-view.py <project-folder> --verbose

Output lives under projects/ (gitignored per ADR-0007): local project memory, no drift guard.
Stdlib only; no third-party dependencies. Modeled on scripts/build-activity-timeline.py.
"""
import sys
import re
import html
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
OUTPUT_NAME = "KNOWLEDGE.html"
INDEX_STEM = "index"


def resolve_knowledge_dir(arg):
    """Accept a project folder (use its knowledge/ subdir) or the knowledge/ folder itself."""
    p = Path(arg).resolve()
    if p.name == "knowledge" and p.is_dir():
        return p
    sub = p / "knowledge"
    if sub.is_dir():
        return sub
    return None


def parse_frontmatter(text):
    """Return (meta dict, body). Defensive: a malformed block is treated as no frontmatter."""
    meta = {}
    if not text.startswith("---"):
        return meta, text
    end = text.find("\n---", 3)
    if end == -1:
        return meta, text
    block = text[3:end].strip("\n")
    body = text[end + 4:]
    body = body[1:] if body.startswith("\n") else body
    for line in block.splitlines():
        if ":" not in line:
            continue
        key, val = line.split(":", 1)
        key, val = key.strip(), val.strip()
        if key == "tags":
            val = val.strip("[]")
            meta["tags"] = [t.strip().strip("'\"") for t in val.split(",") if t.strip()]
        elif key:
            meta[key] = val
    return meta, body


def load_notes(kdir):
    """Read every .md note (excluding the generated HTML). Returns (index_note, task_notes)."""
    index_note, notes = None, []
    for f in sorted(kdir.glob("*.md")):
        try:
            text = f.read_text(encoding="utf-8")
        except OSError:
            continue
        meta, body = parse_frontmatter(text)
        title = _first_heading(body) or f.stem
        # render_section already shows the title as the section heading; drop the body's
        # leading title heading so it does not render a second time.
        note = {"stem": f.stem, "title": title, "date": meta.get("date", ""),
                "tags": meta.get("tags", []), "body": _strip_first_heading(body)}
        if f.stem == INDEX_STEM:
            index_note = note
        else:
            notes.append(note)
    # Newest first by frontmatter date, then by stem (descending so dated slugs sort recent-first).
    notes.sort(key=lambda n: (n["date"], n["stem"]), reverse=True)
    return index_note, notes


def _first_heading(body):
    for line in body.splitlines():
        m = re.match(r"^#{1,6}\s+(.*)", line.strip())
        if m:
            return m.group(1).strip()
    return ""


def _strip_first_heading(body):
    """Remove the first heading line (used as the section title) from the body. No-op
    when the body has no heading."""
    out, removed = [], False
    for line in body.splitlines():
        if not removed and re.match(r"^#{1,6}\s+", line.strip()):
            removed = True
            continue
        out.append(line)
    return "\n".join(out)


def _esc(s):
    return html.escape(str(s), quote=True)


_WIKILINK = re.compile(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]")
_BOLD = re.compile(r"\*\*([^*]+)\*\*")
_CODE = re.compile(r"`([^`]+)`")


def _inline(text, anchors):
    """Escape, then apply inline code, bold, and wikilink resolution (in that order)."""
    out, last = [], 0
    # Code spans first so their contents are not re-parsed for bold/links.
    for m in _CODE.finditer(text):
        out.append(_inline_no_code(text[last:m.start()], anchors))
        out.append("<code>%s</code>" % _esc(m.group(1)))
        last = m.end()
    out.append(_inline_no_code(text[last:], anchors))
    return "".join(out)


def _inline_no_code(text, anchors):
    def wikilink(m):
        target = m.group(1).strip()
        label = (m.group(2) or m.group(1)).strip()
        if target in anchors:
            return '<a class="wl" href="#%s">%s</a>' % (_esc(target), _esc(label))
        return '<span class="wl-broken" title="unresolved link">[[%s]]</span>' % _esc(label)
    # Escape, then re-introduce bold and wikilinks on the escaped text.
    s = _esc(text)
    s = _BOLD.sub(lambda m: "<strong>%s</strong>" % m.group(1), s)
    # Wikilinks were escaped ([[ stays literal); match on the escaped form.
    s = re.sub(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]",
               lambda m: wikilink(m), s)
    return s


def md_to_html(body, anchors):
    """Convert the template subset to HTML: headings, lists, paragraphs, inline. Defensive."""
    lines = body.splitlines()
    out, in_list = [], False
    for raw in lines:
        line = raw.rstrip()
        stripped = line.strip()
        if not stripped:
            if in_list:
                out.append("</ul>"); in_list = False
            continue
        if stripped.startswith("<!--"):
            continue  # drop template guidance comments
        h = re.match(r"^(#{1,6})\s+(.*)", stripped)
        if h:
            if in_list:
                out.append("</ul>"); in_list = False
            level = min(len(h.group(1)) + 1, 6)  # shift down: note H1 becomes page H2
            out.append("<h%d>%s</h%d>" % (level, _inline(h.group(2), anchors), level))
            continue
        li = re.match(r"^[-*]\s+(.*)", stripped)
        if li:
            if not in_list:
                out.append("<ul>"); in_list = True
            out.append("<li>%s</li>" % _inline(li.group(1), anchors))
            continue
        if in_list:
            out.append("</ul>"); in_list = False
        out.append("<p>%s</p>" % _inline(stripped, anchors))
    if in_list:
        out.append("</ul>")
    return "\n".join(out)


def render_section(note, anchors):
    tags = "".join('<span class="tag">%s</span>' % _esc(t) for t in note["tags"])
    date = '<span class="date">%s</span>' % _esc(note["date"]) if note["date"] else ""
    return (
        '<section class="note" id="%s">'
        '<div class="nhead"><h2>%s</h2>%s</div>'
        '<div class="tags">%s</div>'
        '<div class="body">%s</div>'
        '</section>'
    ) % (_esc(note["stem"]), _esc(note["title"]), date, tags, md_to_html(note["body"], anchors))


HTML_SHELL = r"""<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<style>
:root{--bg:#fff;--bg-soft:#f7f7f8;--fg:#18181b;--muted:#71717a;--faint:#a1a1aa;--line:#e4e4e7;
 --line-soft:#efeff1;--accent:#4f46e5;--accent-weak:#eef2ff;--card:#fff;--code-bg:#f4f4f5;
 --shadow:0 1px 2px rgba(24,24,27,.05),0 1px 3px rgba(24,24,27,.04);--radius:12px;
 --font:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
 --mono:ui-monospace,SFMono-Regular,"SF Mono",Menlo,Consolas,monospace;}
html[data-theme="dark"]{--bg:#0b0d12;--bg-soft:#0f1218;--fg:#e8e8ea;--muted:#9aa0ac;--faint:#6b7280;
 --line:#242833;--line-soft:#1b1e26;--accent:#818cf8;--accent-weak:#1a1d2b;--card:#12151c;
 --code-bg:#1a1e27;--shadow:0 1px 2px rgba(0,0,0,.4);}
*{box-sizing:border-box}
body{margin:0;font:15px/1.65 var(--font);background:var(--bg);color:var(--fg);-webkit-font-smoothing:antialiased}
code{font:13px/1.5 var(--mono);background:var(--code-bg);border-radius:5px;padding:1px 5px}
.topbar{position:sticky;top:0;z-index:20;display:flex;align-items:center;gap:16px;padding:12px 22px;
 background:color-mix(in srgb,var(--bg) 86%,transparent);backdrop-filter:saturate(160%) blur(10px);
 border-bottom:1px solid var(--line)}
.brand{font-weight:650;letter-spacing:-.01em;white-space:nowrap}.brand .dot{color:var(--accent)}
.search{position:relative;flex:1;max-width:520px;margin:0 auto}
#q{width:100%;padding:9px 12px 9px 34px;font:14px var(--font);color:var(--fg);background:var(--bg-soft);
 border:1px solid var(--line);border-radius:9px;outline:none}
#q:focus{border-color:var(--accent);box-shadow:0 0 0 3px var(--accent-weak)}
.search .mag{position:absolute;left:11px;top:50%;transform:translateY(-50%);color:var(--faint)}
.tog{cursor:pointer;border:1px solid var(--line);background:var(--bg-soft);color:var(--fg);border-radius:9px;padding:7px 10px}
.tog:hover{border-color:var(--accent)}
.wrap{max-width:880px;margin:0 auto;padding:26px 22px 80px}
h1{font-size:20px;margin:0 0 4px;letter-spacing:-.01em}
.sub{color:var(--muted);font-size:13px;margin:0 0 6px}
.note{background:var(--card);border:1px solid var(--line);border-radius:var(--radius);padding:16px 18px;
 margin:0 0 16px;box-shadow:var(--shadow);scroll-margin-top:64px}
.note.index{border-color:var(--accent);background:var(--accent-weak)}
.nhead{display:flex;align-items:baseline;justify-content:space-between;gap:10px}
.nhead h2{font-size:16px;margin:0}
.nhead .date{font:11.5px var(--mono);color:var(--faint);white-space:nowrap}
.note h2,.note h3,.note h4{margin:14px 0 6px}.note h3{font-size:14px}.note h4{font-size:13px;color:var(--muted)}
.body p{margin:8px 0}.body ul{margin:8px 0;padding-left:20px}.body li{margin:3px 0}
a.wl{color:var(--accent);text-decoration:none;border-bottom:1px solid color-mix(in srgb,var(--accent) 40%,transparent)}
a.wl:hover{border-bottom-color:var(--accent)}
.wl-broken{color:var(--faint);text-decoration:line-through;text-decoration-color:var(--faint)}
.tags{display:flex;flex-wrap:wrap;gap:6px;margin:8px 0 0}
.tag{font:10px var(--mono);text-transform:lowercase;color:var(--accent);background:var(--accent-weak);
 border-radius:5px;padding:1px 7px}
.empty{display:none;color:var(--muted);padding:40px 0;text-align:center}
footer{color:var(--faint);font-size:12px;border-top:1px solid var(--line-soft);margin-top:26px;padding-top:18px}
@media(max-width:640px){.topbar .brand .full{display:none}}
</style>
</head>
<body>
<div class="topbar">
 <div class="brand"><span class="dot">/</span> Fhorja <span class="full">knowledge</span></div>
 <div class="search"><span class="mag">&#x2315;</span>
  <input id="q" type="search" placeholder="Filter notes by title, tag, or text..." autocomplete="off" spellcheck="false"></div>
 <button class="tog" id="theme" type="button" aria-label="Toggle theme">&#x25D1;</button>
</div>
<div class="wrap">
 <h1>__TITLE__</h1>
 <p class="sub">__SUB__</p>
__SECTIONS__
 <div class="empty" id="empty">No notes match the filter.</div>
 <footer>__FOOTER__</footer>
</div>
<script>
(function(){
 var t=document.getElementById('theme'),r=document.documentElement;
 t.addEventListener('click',function(){r.setAttribute('data-theme',r.getAttribute('data-theme')==='dark'?'light':'dark')});
 var q=document.getElementById('q'),items=[].slice.call(document.querySelectorAll('.note')),e=document.getElementById('empty');
 q.addEventListener('input',function(){
  var v=q.value.toLowerCase(),n=0;
  items.forEach(function(el){var hit=el.textContent.toLowerCase().indexOf(v)>=0;el.style.display=hit?'':'none';if(hit)n++;});
  e.style.display=n?'none':'block';
 });
})();
</script>
</body>
</html>
"""


def render_html(project_name, index_note, notes, kdir):
    anchors = {n["stem"] for n in notes}
    anchors.add(INDEX_STEM)  # [[index]] always resolves when an index exists
    sections = []
    if index_note:
        sec = render_section(index_note, anchors).replace('class="note"', 'class="note index"', 1)
        sections.append(sec)
    elif notes:
        sections.append('<p class="sub">No index.md yet; showing notes only.</p>')
    sections.extend(render_section(n, anchors) for n in notes)
    body = "\n".join(sections) if sections else '<p class="sub">No knowledge notes yet for this project.</p>'
    sub = "%d note%s. A navigable view of the project's knowledge layer; wikilinks jump in-page." % (
        len(notes), "" if len(notes) == 1 else "s")
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    try:
        rel = kdir.relative_to(REPO)
    except ValueError:
        rel = kdir
    footer = ("Generated %s by scripts/build-knowledge-view.py from %s. Regenerate on demand; "
              "this file is local project memory (gitignored). The AI does not read it.") % (
        _esc(generated), _esc(str(rel)))
    return (HTML_SHELL
            .replace("__TITLE__", _esc("Knowledge: %s" % project_name))
            .replace("__SUB__", _esc(sub))
            .replace("__SECTIONS__", body)
            .replace("__FOOTER__", footer))


def main(argv):
    args = [a for a in argv if not a.startswith("--")]
    flags = {a for a in argv if a.startswith("--")}
    verbose = "--verbose" in flags
    to_stdout = "--stdout" in flags

    if not args:
        sys.stderr.write("usage: build-knowledge-view.py <project-folder> [--stdout] [--verbose]\n")
        return 2
    kdir = resolve_knowledge_dir(args[0])
    if kdir is None:
        sys.stderr.write("error: no knowledge/ folder found at or under: %s\n" % Path(args[0]).resolve())
        return 2

    index_note, notes = load_notes(kdir)
    project_name = kdir.parent.name
    if verbose:
        sys.stderr.write("knowledge dir: %s\n" % kdir)
        sys.stderr.write("index: %s, notes: %d\n" % ("present" if index_note else "absent", len(notes)))

    document = render_html(project_name, index_note, notes, kdir)
    if to_stdout:
        sys.stdout.write(document)
        return 0
    out_path = kdir / OUTPUT_NAME
    out_path.write_text(document, encoding="utf-8")
    sys.stderr.write("wrote %s (%d note%s)\n" % (out_path, len(notes), "" if len(notes) == 1 else "s"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
