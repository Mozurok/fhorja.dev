#!/usr/bin/env python3
"""One-time backfill: add metadata.tools, metadata.x-wos-profiles, and
metadata.provenance to every command frontmatter, rule-derived from existing
fields (ADR-0059 + ADR-0046 DEF-09). Idempotent: re-running updates the three
lines in place rather than duplicating them.

Derivation (no hand-assignment):
- tools: base [Read, Grep, Glob, Bash]; + [Write, Edit] unless the command is
  read-only (context-layers-produced: []); + [Task] for orchestrators; +
  [WebFetch, WebSearch] for the authorized web-fetch set.
- x-wos-profiles: minimal = the lifecycle spine; full-only = orchestrators +
  design-system + database-context + specialist personas + autonomous; core =
  everything else. A command lists every tier that includes it.
- provenance: first-party (every Fhorja command is first-party by definition).
"""
from __future__ import annotations
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CMD_DIR = ROOT / "commands"

MINIMAL = {
    "task-init", "impact-analysis", "decision-interview", "implementation-plan",
    "approve-plan", "implement-approved-slice", "slice-closure", "review-hard",
    "pr-package", "what-next", "sync-task-state", "task-close",
}
ORCH = {
    "atom-audit-fleet", "external-research-fleet", "feature-library-scout-fleet",
    "implement-fleet", "screen-spec-fleet", "task-init-fleet",
    "verify-against-rubric-fleet",
}
DESIGN = {
    "atom-audit", "component-spec", "screen-spec", "design-bootstrap",
    "foundation-audit", "extract-foundations-from-screens", "journey-map",
    "pattern-doc", "inventory-snapshot", "color-contrast-architect",
    "design-spec-review",
}
DBCTX = {"db-context-postgres", "db-context-supabase"}
PERSONAS = {
    "a11y-audit", "ai-feature-eval-harness", "migration-safety-steward",
    "rls-auth-boundary-auditor", "post-deploy-verifier", "postmortem-author",
    "slo-define", "release-plan", "performance-budget", "jtbd-switch-interviewer",
    "verify-against-rubric", "skill-vet",
}
AUTONOMOUS = {"autonomous-run", "autonomous-board"}
FULL_ONLY = ORCH | DESIGN | DBCTX | PERSONAS | AUTONOMOUS
WEBFETCH = {
    "capture-references", "external-research", "external-research-fleet",
    "stack-recommend", "stack-currency-check", "feature-library-scout",
    "feature-library-scout-fleet",
}
TOOL_ORDER = ["Read", "Write", "Edit", "Bash", "Glob", "Grep", "WebFetch", "WebSearch", "Task"]


def field(block: str, key: str) -> str:
    m = re.search(rf"^\s*{re.escape(key)}:\s*(.*)$", block, re.M)
    return m.group(1).strip() if m else ""


def derive_tools(name: str, produced_raw: str) -> list[str]:
    produced_empty = produced_raw.strip() in ("[]", "")
    tools = {"Read", "Grep", "Glob", "Bash"}
    if not produced_empty:
        tools |= {"Write", "Edit"}
    if name in ORCH:
        tools.add("Task")
    if name in WEBFETCH:
        tools |= {"WebFetch", "WebSearch"}
    return [t for t in TOOL_ORDER if t in tools]


def derive_profiles(name: str) -> list[str]:
    if name in MINIMAL:
        return ["minimal", "core", "full"]
    if name in FULL_ONLY:
        return ["full"]
    return ["core", "full"]


def main() -> int:
    files = sorted(p for p in CMD_DIR.rglob("*.md") if "/_shared/" not in str(p))
    changed = 0
    rows = []
    for f in files:
        text = f.read_text(encoding="utf-8")
        if not text.startswith("---\n"):
            continue
        end = text.index("\n---", 4)
        block = text[4:end]
        name = field(block, "name")
        produced = field(block, "context-layers-produced")
        tools = derive_tools(name, produced)
        profiles = derive_profiles(name)
        tools_line = f"  tools: [{', '.join(tools)}]"
        prof_line = f"  x-wos-profiles: [{', '.join(profiles)}]"
        prov_line = "  provenance: first-party"
        new_meta = f"{tools_line}\n{prof_line}\n{prov_line}"

        # Idempotent: if tools already present in metadata, replace the 3 lines.
        if re.search(r"^\s*tools:\s*\[", block, re.M):
            block2 = re.sub(r"^\s*tools:.*$", tools_line, block, count=1, flags=re.M)
            block2 = re.sub(r"^\s*x-wos-profiles:.*$", prof_line, block2, count=1, flags=re.M)
            block2 = re.sub(r"^\s*provenance:.*$", prov_line, block2, count=1, flags=re.M)
        else:
            # Insert the 3 lines immediately after the context-layers-produced line.
            block2 = re.sub(
                r"(^\s*context-layers-produced:.*$)",
                r"\1\n" + new_meta.replace("\\", "\\\\"),
                block, count=1, flags=re.M,
            )
        if block2 != block:
            f.write_text("---\n" + block2 + text[end:], encoding="utf-8")
            changed += 1
        rows.append((name, "|".join(profiles), " ".join(tools)))

    for name, prof, tools in sorted(rows):
        print(f"{name:34s} profiles={prof:18s} tools=[{tools}]")
    print(f"\nbackfilled {changed} of {len(rows)} command files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
