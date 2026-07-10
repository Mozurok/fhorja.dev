#!/usr/bin/env python3
"""Generate the command catalog from the canonical command files.

Single source of truth: commands/<name>.md (and folder-shaped commands/<name>/SKILL.md) frontmatter,
COMMAND_PROMPT_STUBS.md (example prompts), and wos/command-roles.md (next-commands). The catalog is a
GENERATED artifact (ADR-0005): never hand-edit docs/command-catalog.html; edit the command files and
re-run this script. Modeled on build-agent-skills.sh.

Usage:
  python3 scripts/build-command-catalog.py            # build: write docs/command-catalog.html
  python3 scripts/build-command-catalog.py --check     # drift: exit 1 if the committed HTML is stale
  python3 scripts/build-command-catalog.py --verbose   # also print per-command processing

Output is deterministic (no timestamps) so --check is stable. Stdlib only.
"""
import sys
import html
import json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
COMMANDS_DIR = REPO / "commands"
STUBS_FILE = REPO / "COMMAND_PROMPT_STUBS.md"
ROLES_FILE = REPO / "wos" / "command-roles.md"
HTML_OUT = REPO / "docs" / "command-catalog.html"
JSON_OUT = REPO / "docs" / "command-catalog.json"
README_FILE = REPO / "README.md"
README_HEADING = "## Command catalog"

# Canonical metadata.category values (lint-validated) in lifecycle display order.
CATEGORY_ORDER = [
    ("project-initialization", "Project initialization"),
    ("discovery-and-scoping", "Discovery and scoping"),
    ("contract-and-decision-hardening", "Contract and decision hardening"),
    ("planning-and-validation", "Planning and validation"),
    ("execution-and-closure", "Execution and closure"),
    ("delivery-and-communication", "Delivery and communication"),
    ("state-and-navigation", "State and navigation"),
    ("database-context", "Database context"),
    ("prompt-tooling", "Prompt tooling"),
]
CATEGORY_LABELS = dict(CATEGORY_ORDER)


def parse_frontmatter(path):
    """Return {name, description, category} from a command file's YAML frontmatter, or None."""
    text = path.read_text()
    if not text.startswith("---"):
        return None
    lines = text.splitlines()
    # frontmatter is between the first and second '---'
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        return None
    fm = lines[1:end]
    meta = {"name": None, "description": "", "category": "",
            "mode": "", "model": "", "token_budget": "", "multi_repo": ""}
    in_metadata = False
    for line in fm:
        if line.startswith("name:"):
            meta["name"] = line.split(":", 1)[1].strip()
        elif line.startswith("description:"):
            meta["description"] = line.split(":", 1)[1].strip()
        elif line.startswith("metadata:"):
            in_metadata = True
        elif in_metadata and line.startswith("  ") and ":" in line:
            key = line.strip().split(":", 1)[0].strip()
            val = line.split(":", 1)[1].strip()
            if key == "category":
                meta["category"] = val
            elif key == "primary-cursor-mode":
                meta["mode"] = val
            elif key == "suggested-model":
                meta["model"] = val
            elif key == "token-budget":
                meta["token_budget"] = val
            elif key == "multi-repo-aware":
                meta["multi_repo"] = val
    if not meta["name"]:
        return None
    return meta


def discover_commands():
    """Discover flat commands/<name>.md and folder-shaped commands/<name>/SKILL.md."""
    found = {}
    for f in sorted(COMMANDS_DIR.glob("*.md")):
        if f.name == "_index.md" or f.parent.name == "_shared":
            continue
        meta = parse_frontmatter(f)
        if meta:
            found[meta["name"]] = meta
    for f in sorted(COMMANDS_DIR.glob("*/SKILL.md")):
        if f.parent.name == "_shared":
            continue
        meta = parse_frontmatter(f)
        if meta:
            found[meta["name"]] = meta
    return found


def parse_stubs():
    """name -> example prompt stub, from the COMMAND_PROMPT_STUBS.md tables."""
    stubs = {}
    if not STUBS_FILE.exists():
        return stubs
    for line in STUBS_FILE.read_text().splitlines():
        if not line.startswith("| `"):
            continue
        cells = line.split(" | ")
        if len(cells) < 2:
            continue
        name = cells[0].strip().strip("|").strip().strip("`")
        stub = cells[1].strip().rstrip("|").strip()
        # un-escape table-escaped pipes
        stub = stub.replace("\\|", "|")
        if name:
            stubs[name] = stub
    return stubs


def parse_roles_next():
    """name -> list of next-command names, from wos/command-roles.md '### name' blocks."""
    nexts = {}
    if not ROLES_FILE.exists():
        return nexts
    current = None
    collecting = False
    for line in ROLES_FILE.read_text().splitlines():
        if line.startswith("### "):
            current = line[4:].strip().strip("`")
            collecting = False
            nexts.setdefault(current, [])
        elif current and line.strip().lower().startswith("typical next commands"):
            collecting = True
        elif current and collecting:
            s = line.strip()
            if s.startswith("- `"):
                # take the first backticked token on the bullet
                inner = s.split("`")
                if len(inner) >= 2 and inner[1]:
                    nexts[current].append(inner[1])
            elif s.startswith("### ") or s == "":
                if s.startswith("### "):
                    collecting = False
    return {k: v for k, v in nexts.items() if v}


def esc(s):
    return html.escape(s or "", quote=True)


def split_use(description):
    """Split a description into (lead, use, dont) on the 'Use when'/'Do not use' cues, best-effort."""
    d = description
    dont = ""
    use = ""
    lead = d
    low = d.lower()
    iuse = low.find("use when")
    idont = low.find("do not use")
    if idont != -1:
        dont = d[idont:].strip()
        d = d[:idont].strip()
        low = d.lower()
        iuse = low.find("use when")
    if iuse != -1:
        use = d[iuse:].strip()
        lead = d[:iuse].strip()
    else:
        lead = d.strip()
    return lead, use, dont


def pretty_model(m):
    """claude-sonnet-4-6 -> Sonnet 4.6 (display only)."""
    if not m:
        return ""
    m = m.replace("claude-", "")
    parts = m.split("-")
    tier = parts[0].capitalize()
    ver = ".".join(parts[1:3]) if len(parts) > 1 else ""
    return (tier + " " + ver).strip()


def render_card(m, stubs, nexts):
    lead, use, dont = split_use(m["description"])
    badges = [f'<span class="badge cat-badge">{esc(CATEGORY_LABELS.get(m["category"], m["category"]))}</span>']
    if m.get("mode"):
        badges.append(f'<span class="badge mode mode-{esc(m["mode"].lower())}">{esc(m["mode"])}</span>')
    if m.get("model"):
        badges.append(f'<span class="badge soft">{esc(pretty_model(m["model"]))}</span>')
    if m.get("token_budget"):
        badges.append(f'<span class="badge soft">~{esc(m["token_budget"])} tok</span>')
    if str(m.get("multi_repo", "")).lower() == "true":
        badges.append('<span class="badge soft">multi-repo</span>')
    badge_row = "".join(badges)

    parts = [f'<p class="lead">{esc(lead)}</p>']
    if use:
        parts.append(f'<p class="callout use"><span class="ico">Use when</span> {esc(use[len("Use when"):].lstrip(" :"))}</p>')
    if dont:
        parts.append(f'<p class="callout dont"><span class="ico">Avoid</span> {esc(dont[len("Do not use"):].lstrip(" :"))}</p>')
    stub = stubs.get(m["name"])
    if stub:
        parts.append(
            '<div class="ex"><div class="ex-head"><span class="exlabel">Example prompt</span>'
            '<button class="copy" type="button" aria-label="Copy example">Copy</button></div>'
            f'<code>{esc(stub)}</code></div>'
        )
    nx = nexts.get(m["name"])
    if nx:
        chips = "".join(f'<a class="chip" href="#cmd-{esc(c)}">{esc(c)}</a>' for c in nx)
        parts.append(f'<div class="next"><span class="nextlabel">Next</span> {chips}</div>')
    body = "\n        ".join(parts)
    return (
        f'<article class="cmd" id="cmd-{esc(m["name"])}" data-name="{esc(m["name"])}">\n'
        f'        <div class="cmd-head"><h3><a class="anchor" href="#cmd-{esc(m["name"])}">#</a><code>{esc(m["name"])}</code></h3></div>\n'
        f'        <div class="badges">{badge_row}</div>\n'
        f'        {body}\n'
        f'      </article>'
    )


def render_html(commands):
    by_cat = {}
    for meta in commands.values():
        by_cat.setdefault(meta["category"], []).append(meta)
    stubs = parse_stubs()
    nexts = parse_roles_next()
    total = len(commands)

    nav, sections, ncats = [], [], 0
    for key, label in CATEGORY_ORDER:
        cmds = sorted(by_cat.get(key, []), key=lambda m: m["name"])
        if not cmds:
            continue
        ncats += 1
        nav.append(
            f'<li><a href="#{esc(key)}" data-cat="{esc(key)}">'
            f'<span class="nav-label">{esc(label)}</span><span class="nav-n">{len(cmds)}</span></a></li>'
        )
        cards = "\n      ".join(render_card(m, stubs, nexts) for m in cmds)
        sections.append(
            f'<section class="cat" id="{esc(key)}" data-cat="{esc(key)}">\n'
            f'      <h2><span>{esc(label)}</span><span class="n">{len(cmds)}</span></h2>\n'
            f'      {cards}\n'
            f'    </section>'
        )

    shell = HTML_SHELL
    shell = shell.replace("__TOTAL__", str(total))
    shell = shell.replace("__NCATS__", str(ncats))
    shell = shell.replace("__NAV__", "\n        ".join(nav))
    shell = shell.replace("__SECTIONS__", "\n    ".join(sections))
    return shell


HTML_SHELL = r'''<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Fhorja command catalog</title>
<style>
:root{
  --bg:#ffffff; --bg-soft:#f7f7f8; --fg:#18181b; --muted:#71717a; --faint:#a1a1aa;
  --line:#e4e4e7; --line-soft:#efeff1; --accent:#4f46e5; --accent-weak:#eef2ff;
  --card:#ffffff; --code-bg:#f4f4f5; --shadow:0 1px 2px rgba(24,24,27,.05),0 1px 3px rgba(24,24,27,.04);
  --shadow-lift:0 4px 16px rgba(24,24,27,.10); --radius:12px;
  --ok-bg:#ecfdf5; --ok-fg:#047857; --warn-bg:#fef2f2; --warn-fg:#b91c1c;
  --font:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
  --mono:ui-monospace,SFMono-Regular,"SF Mono",Menlo,Consolas,monospace;
}
html[data-theme="dark"]{
  --bg:#0b0d12; --bg-soft:#0f1218; --fg:#e8e8ea; --muted:#9aa0ac; --faint:#6b7280;
  --line:#242833; --line-soft:#1b1e26; --accent:#818cf8; --accent-weak:#1a1d2b;
  --card:#12151c; --code-bg:#1a1e27; --shadow:0 1px 2px rgba(0,0,0,.4);
  --shadow-lift:0 8px 28px rgba(0,0,0,.5);
  --ok-bg:#0c241c; --ok-fg:#4ade80; --warn-bg:#2a1416; --warn-fg:#f87171;
}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0;font:15px/1.6 var(--font);background:var(--bg);color:var(--fg);-webkit-font-smoothing:antialiased}
a{color:var(--accent);text-decoration:none}
code{font:13px/1.5 var(--mono)}

.topbar{position:sticky;top:0;z-index:20;display:flex;align-items:center;gap:16px;
  padding:12px 22px;background:color-mix(in srgb,var(--bg) 86%,transparent);
  backdrop-filter:saturate(160%) blur(10px);border-bottom:1px solid var(--line)}
.brand{font-weight:650;letter-spacing:-.01em;white-space:nowrap}
.brand .dot{color:var(--accent)}
.search{position:relative;flex:1;max-width:540px;margin:0 auto}
#q{width:100%;padding:9px 12px 9px 34px;font:14px var(--font);color:var(--fg);
  background:var(--bg-soft);border:1px solid var(--line);border-radius:9px;outline:none}
#q:focus{border-color:var(--accent);box-shadow:0 0 0 3px var(--accent-weak)}
.search .mag{position:absolute;left:11px;top:50%;transform:translateY(-50%);color:var(--faint);font-size:14px}
.search .kbd{position:absolute;right:9px;top:50%;transform:translateY(-50%);font:11px var(--mono);
  color:var(--faint);border:1px solid var(--line);border-radius:5px;padding:1px 6px;background:var(--bg)}
.tog{cursor:pointer;border:1px solid var(--line);background:var(--bg-soft);color:var(--fg);
  border-radius:9px;padding:7px 10px;font-size:14px;line-height:1}
.tog:hover{border-color:var(--accent)}

.layout{display:grid;grid-template-columns:248px minmax(0,1fr);gap:0;max-width:1180px;margin:0 auto}
.sidebar{position:sticky;top:57px;align-self:start;height:calc(100vh - 57px);overflow-y:auto;
  padding:22px 14px 40px;border-right:1px solid var(--line-soft)}
.stats{font-size:12px;color:var(--muted);padding:0 10px 12px;letter-spacing:.01em}
.sidebar ul{list-style:none;margin:0;padding:0}
.sidebar li a{display:flex;align-items:center;justify-content:space-between;gap:8px;
  padding:7px 10px;border-radius:8px;color:var(--muted);font-size:13.5px;font-weight:500}
.sidebar li a:hover{background:var(--bg-soft);color:var(--fg)}
.sidebar li a.active{background:var(--accent-weak);color:var(--accent)}
.nav-n{font:11px var(--mono);color:var(--faint)}
.sidebar li a.active .nav-n{color:var(--accent)}

main{padding:26px 30px 80px;min-width:0}
.intro{color:var(--muted);font-size:13px;margin:0 0 8px;max-width:70ch}
.cat{margin-top:34px;scroll-margin-top:70px}
.cat:first-of-type{margin-top:8px}
.cat>h2{display:flex;align-items:baseline;gap:10px;position:sticky;top:57px;z-index:5;
  margin:0 0 14px;padding:8px 0;font-size:13px;font-weight:650;text-transform:uppercase;
  letter-spacing:.06em;color:var(--muted);background:linear-gradient(var(--bg),var(--bg) 70%,transparent)}
.cat>h2 .n{font:11px var(--mono);color:var(--faint);text-transform:none}

.cmd{background:var(--card);border:1px solid var(--line);border-radius:var(--radius);
  padding:16px 18px;margin:0 0 14px;box-shadow:var(--shadow);transition:border-color .15s,box-shadow .15s,transform .15s}
.cmd:hover{border-color:color-mix(in srgb,var(--accent) 45%,var(--line));box-shadow:var(--shadow-lift)}
.cmd-head{display:flex;align-items:center;gap:8px}
.cmd-head h3{margin:0;font-size:16px;display:flex;align-items:center;gap:6px}
.cmd-head code{font-size:15.5px;font-weight:600;color:var(--fg)}
.anchor{opacity:0;color:var(--faint);font-weight:400;transition:opacity .15s;margin-left:-16px;width:12px}
.cmd:hover .anchor{opacity:1}
.badges{display:flex;flex-wrap:wrap;gap:6px;margin:9px 0 11px}
.badge{font:11px/1.5 var(--mono);padding:1px 8px;border-radius:20px;border:1px solid var(--line);color:var(--muted);white-space:nowrap}
.badge.cat-badge{background:var(--accent-weak);color:var(--accent);border-color:transparent}
.badge.soft{background:var(--bg-soft)}
.badge.mode-agent{background:var(--ok-bg);color:var(--ok-fg);border-color:transparent}
.badge.mode-ask{background:var(--bg-soft);color:var(--muted)}
.badge.mode-plan{background:var(--accent-weak);color:var(--accent);border-color:transparent}
.lead{margin:0 0 10px}
.callout{display:block;margin:7px 0;padding:7px 11px;border-radius:8px;font-size:13.5px;border:1px solid transparent}
.callout .ico{font:10px/1.4 var(--mono);text-transform:uppercase;letter-spacing:.05em;font-weight:700;margin-right:7px;padding:1px 6px;border-radius:4px;vertical-align:1px}
.callout.use{background:var(--ok-bg);color:var(--fg)}
.callout.use .ico{background:var(--ok-fg);color:#fff}
.callout.dont{background:var(--warn-bg);color:var(--fg)}
.callout.dont .ico{background:var(--warn-fg);color:#fff}
.ex{margin:11px 0 4px}
.ex-head{display:flex;align-items:center;justify-content:space-between;margin-bottom:4px}
.exlabel,.nextlabel{font:10px var(--mono);text-transform:uppercase;letter-spacing:.06em;color:var(--faint)}
.copy{cursor:pointer;font:11px var(--mono);color:var(--muted);background:var(--bg-soft);
  border:1px solid var(--line);border-radius:6px;padding:2px 8px}
.copy:hover{border-color:var(--accent);color:var(--accent)}
.copy.done{color:var(--ok-fg);border-color:var(--ok-fg)}
.ex code{display:block;background:var(--code-bg);border:1px solid var(--line-soft);border-radius:8px;
  padding:11px 13px;white-space:pre-wrap;word-break:break-word;color:var(--fg)}
.next{margin:11px 0 0;display:flex;flex-wrap:wrap;align-items:center;gap:6px}
.chip{font:12px var(--mono);background:var(--bg-soft);border:1px solid var(--line);
  border-radius:20px;padding:2px 10px;color:var(--muted)}
.chip:hover{border-color:var(--accent);color:var(--accent)}
.empty{display:none;color:var(--muted);padding:40px 0;text-align:center}
footer{max-width:1180px;margin:0 auto;padding:24px 30px 50px;color:var(--faint);font-size:12px;border-top:1px solid var(--line-soft)}

@media(max-width:820px){
  .layout{grid-template-columns:1fr}
  .sidebar{display:none}
  .topbar .brand .full{display:none}
}
</style>
</head>
<body>
<div class="topbar">
  <div class="brand"><span class="dot">/</span> Fhorja <span class="full">command catalog</span></div>
  <div class="search">
    <span class="mag">&#x2315;</span>
    <input id="q" type="search" placeholder="Filter commands by name, text, or category..." autocomplete="off" spellcheck="false">
    <span class="kbd">/</span>
  </div>
  <button class="tog" id="theme" type="button" aria-label="Toggle theme">&#x25D1;</button>
</div>
<div class="layout">
  <aside class="sidebar">
    <div class="stats">__TOTAL__ commands &middot; __NCATS__ categories</div>
    <ul>
        __NAV__
    </ul>
  </aside>
  <main id="main">
    <p class="intro">Generated from <code>commands/*.md</code> by <code>scripts/build-command-catalog.py</code>. Do not hand-edit; edit the command files and re-run. Offline quick reference.</p>
    __SECTIONS__
    <p class="empty" id="noresults">No commands match your filter.</p>
  </main>
</div>
<footer>Fhorja command catalog &middot; generated artifact (ADR-0005) &middot; source of truth: <code>commands/*.md</code></footer>
<script>
(function(){
  var root=document.documentElement;
  try{var saved=localStorage.getItem('wos-theme');
    if(saved){root.setAttribute('data-theme',saved);}
    else if(window.matchMedia&&matchMedia('(prefers-color-scheme: light)').matches){root.setAttribute('data-theme','light');}
  }catch(e){}
  document.getElementById('theme').addEventListener('click',function(){
    var next=root.getAttribute('data-theme')==='dark'?'light':'dark';
    root.setAttribute('data-theme',next);
    try{localStorage.setItem('wos-theme',next);}catch(e){}
  });

  var q=document.getElementById('q');
  var cards=[].slice.call(document.querySelectorAll('.cmd'));
  var cats=[].slice.call(document.querySelectorAll('.cat'));
  var noresults=document.getElementById('noresults');
  q.addEventListener('input',function(){
    var t=q.value.trim().toLowerCase();var any=false;
    cards.forEach(function(c){var hit=t===''||c.textContent.toLowerCase().indexOf(t)>-1;
      c.style.display=hit?'':'none';if(hit)any=true;});
    cats.forEach(function(s){var vis=s.querySelectorAll('.cmd:not([style*="none"])').length;s.style.display=vis?'':'none';});
    noresults.style.display=any?'none':'block';
  });
  document.addEventListener('keydown',function(e){
    if(e.key==='/'&&document.activeElement!==q){e.preventDefault();q.focus();}
    if(e.key==='Escape'&&document.activeElement===q){q.value='';q.dispatchEvent(new Event('input'));q.blur();}
  });

  document.querySelectorAll('.copy').forEach(function(b){
    b.addEventListener('click',function(){
      var code=b.parentElement.parentElement.querySelector('code');
      navigator.clipboard.writeText(code.textContent).then(function(){
        b.textContent='Copied';b.classList.add('done');
        setTimeout(function(){b.textContent='Copy';b.classList.remove('done');},1400);
      });
    });
  });

  var links={};document.querySelectorAll('.sidebar a').forEach(function(a){links[a.getAttribute('data-cat')]=a;});
  if('IntersectionObserver' in window){
    var obs=new IntersectionObserver(function(entries){
      entries.forEach(function(en){
        if(en.isIntersecting){
          Object.keys(links).forEach(function(k){links[k].classList.remove('active');});
          var a=links[en.target.getAttribute('data-cat')];if(a)a.classList.add('active');
        }
      });
    },{rootMargin:'-60px 0px -70% 0px'});
    cats.forEach(function(s){obs.observe(s);});
  }
})();
</script>
</body>
</html>
'''


def first_sentence(text):
    t = (text or "").strip()
    i = t.find(". ")
    return (t[: i + 1] if i != -1 else t).strip()


def render_json(commands):
    """Deterministic machine-readable manifest of the command catalog (no timestamps,
    sorted keys and commands) so --check is byte-stable. Stdlib only."""
    nexts = parse_roles_next()
    items = [
        {
            "name": commands[name]["name"],
            "category": commands[name]["category"],
            "mode": commands[name]["mode"],
            "model": commands[name]["model"],
            "token_budget": commands[name]["token_budget"],
            "multi_repo_aware": commands[name]["multi_repo"],
            "description": commands[name]["description"],
            "next_commands": nexts.get(name, []),
        }
        for name in sorted(commands)
    ]
    doc = {
        "schema_version": 1,
        "generated_by": "scripts/build-command-catalog.py",
        "command_count": len(items),
        "commands": items,
    }
    return json.dumps(doc, indent=2, sort_keys=True) + "\n"


def render_readme_block(commands):
    """The generated body of the README '## Command catalog' section (markdown)."""
    by_cat = {}
    for m in commands.values():
        by_cat.setdefault(m["category"], []).append(m)
    out = [
        "Generated from `commands/*.md` by `scripts/build-command-catalog.py`. Do not hand-edit this "
        "section; edit the command files and re-run. For the browsable reference with examples and "
        "metadata, open `docs/command-catalog.html`; for the machine-readable manifest, see "
        "`docs/command-catalog.json`. For per-command intent and routing, see "
        "`## Command roles` in `WORKFLOW_OPERATING_SYSTEM.md` and `wos/command-roles.md`.",
        "",
    ]
    for key, label in CATEGORY_ORDER:
        cmds = sorted(by_cat.get(key, []), key=lambda m: m["name"])
        if not cmds:
            continue
        out.append(f"### {label}")
        out.append("")
        for m in cmds:
            lead, _, _ = split_use(m["description"])
            out.append(f"- `{m['name']}`: {first_sentence(lead)}")
        out.append("")
    return "\n".join(out).rstrip() + "\n"


def readme_text(commands):
    """Return the full README with its '## Command catalog' section body regenerated."""
    lines = README_FILE.read_text().splitlines(keepends=True)
    start = next((i for i, l in enumerate(lines) if l.strip() == README_HEADING), None)
    if start is None:
        raise SystemExit(f"ERROR: '{README_HEADING}' heading not found in README.md")
    end = next((j for j in range(start + 1, len(lines)) if lines[j].startswith("## ")), len(lines))
    block = render_readme_block(commands)
    return "".join(lines[: start + 1]) + "\n" + block + "\n" + "".join(lines[end:])


def main():
    args = sys.argv[1:]
    check = "--check" in args
    verbose = "--verbose" in args or "-v" in args

    commands = discover_commands()
    if verbose:
        for name in sorted(commands):
            print(f"  {name} [{commands[name]['category']}]")

    # Fail loud on an unknown category rather than silently dropping its commands.
    unknown = sorted({
        f"{m['name']} ({m['category'] or 'MISSING'})"
        for m in commands.values()
        if m["category"] not in CATEGORY_LABELS
    })
    if unknown:
        print("ERROR: command(s) with a category not in CATEGORY_ORDER (would be dropped):", file=sys.stderr)
        for u in unknown:
            print(f"  - {u}", file=sys.stderr)
        print("Add the category to CATEGORY_ORDER in build-command-catalog.py.", file=sys.stderr)
        sys.exit(2)

    rendered = render_html(commands)

    new_readme = readme_text(commands)

    rendered_json = render_json(commands)

    # Stdout manifest mode: print JSON for piping, write nothing.
    if "--json" in args and not check:
        print(rendered_json, end="")
        sys.exit(0)

    if check:
        drift = []
        if not HTML_OUT.exists() or HTML_OUT.read_text() != rendered:
            drift.append(str(HTML_OUT.relative_to(REPO)))
        if not JSON_OUT.exists() or JSON_OUT.read_text() != rendered_json:
            drift.append(str(JSON_OUT.relative_to(REPO)))
        if README_FILE.read_text() != new_readme:
            drift.append(f"{README_FILE.relative_to(REPO)} (## Command catalog section)")
        if drift:
            print("DRIFT: out of sync with commands/*.md; re-run build-command-catalog.py:", file=sys.stderr)
            for d in drift:
                print(f"  - {d}", file=sys.stderr)
            sys.exit(1)
        print(f"OK: command catalog in sync ({len(commands)} commands)")
        sys.exit(0)

    HTML_OUT.parent.mkdir(parents=True, exist_ok=True)
    HTML_OUT.write_text(rendered)
    JSON_OUT.write_text(rendered_json)
    README_FILE.write_text(new_readme)
    print(f"wrote {HTML_OUT.relative_to(REPO)}, {JSON_OUT.relative_to(REPO)} and regenerated the README catalog section ({len(commands)} commands)")


if __name__ == "__main__":
    main()
