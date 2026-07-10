#!/usr/bin/env python3
"""add-wos-topic-activation.py - Add YAML frontmatter with activation metadata to wos/*.md topics

Per G.4 of Fhorja improvement plan 2026-06-03. Adds path-glob and decision-based activation
metadata so future tools can decide deterministically when to load each topic instead of
relying purely on the model's read-when-needed judgment.

Schema added:
  ---
  activation: <always_on | glob | model_decision | manual>
  description: <one-line trigger>
  globs: [optional, only for activation: glob]
  ---

Idempotent: if a file already has a YAML frontmatter block, this script skips it.
"""

import re
import sys
from pathlib import Path

WOS_DIR = Path(__file__).resolve().parent.parent / "wos"

# (filename, activation, description, globs)
ACTIVATIONS = [
    ("anti-patterns.md", "always_on",
     "Cross-cutting anti-patterns. Small and broadly applicable; reads useful for almost any task.",
     []),
    ("command-roles.md", "model_decision",
     "Full per-command roles + guard rails. Load on routing disputes that the inline ## Command roles index does not resolve.",
     []),
    ("context-budget.md", "model_decision",
     "Six canonical layer names, frontmatter convention, debugging context overruns. Load when designing a new command or debugging context inflation.",
     []),
    ("cross-cutting-workflow-guardrails.md", "model_decision",
     "Heuristics + external-web motivation + NEEDS CLARIFICATION marker. Load on phase-by-phase sequencing ambiguity.",
     []),
    ("design-system-conventions.md", "glob",
     "Design system work (foundations, components, tokens, Storybook, screen documentation).",
     ["apps/**/*.tsx", "apps/**/*.jsx", "packages/ui/**/*.tsx", "packages/design-system/**/*",
      "docs/research/**/*", "docs/app/screens/**/*", "**/*.stories.tsx", "**/tokens/**/*"]),
    ("editor-mode-mappings.md", "model_decision",
     "Editor mode translation to non-Claude-Code tools (Cursor, Copilot, Codex, Gemini CLI equivalents). Load only when working in a tool other than Claude Code.",
     []),
    ("entry-points.md", "always_on",
     "Entry-point selection: which command to start with. Small and broadly applicable.",
     []),
    ("gate-conditions.md", "model_decision",
     "Six phase-gate checklists. Load when validating command output shape against a phase gate.",
     []),
    ("global-output-contract.md", "model_decision",
     "Calibration vignettes for Work complexity + Why the Handoff block is mandatory. Load when calibrating complexity or debugging handoff shape.",
     []),
    ("multi-repo-support.md", "model_decision",
     "Multi-repo task schema, locked decisions, invariants, decision table. Load when SOURCE_OF_TRUTH.md contains a ## Repositories section.",
     []),
    ("operating-modes.md", "model_decision",
     "Operating modes (minimal / strict / teaching). Load when the task posture needs to change.",
     []),
    ("output-depth-policy.md", "always_on",
     "Lean / Balanced / Deep per-command depth assignment. Small and routing-relevant.",
     []),
    ("project-level-memory.md", "model_decision",
     "Project-level memory lifecycle, retroactive bootstrap, multi-repo charter schema, three-tier memory pyramid. Load for project memory edge cases.",
     []),
    ("repository-structure.md", "model_decision",
     "Full directory tree + governance files inventory. Load when the compact path index in the spec does not suffice.",
     []),
    ("sub-agent-orchestration.md", "model_decision",
     "Orchestrator-workers pattern + four-question checklist + per-tool primitives table. Load when deciding whether to delegate to a sub-agent.",
     []),
    ("task-file-contracts.md", "model_decision",
     "Required and optional task files: purpose and structure. Load when the file structure is in question.",
     []),
    ("workflow-shapes.md", "model_decision",
     "Task shape selection: which workflow flow for this type of task. Load when the task does not fit the default flow.",
     []),
]


def build_frontmatter(activation, description, globs):
    lines = ["---", f"activation: {activation}", f"description: {description}"]
    if globs:
        lines.append("globs:")
        for g in globs:
            lines.append(f"  - {g}")
    lines.append("---")
    return "\n".join(lines) + "\n\n"


def has_frontmatter(text):
    return text.startswith("---\n") and "\n---\n" in text[4:200]


updated = 0
skipped = 0
missing = 0

for fname, activation, description, globs in ACTIVATIONS:
    path = WOS_DIR / fname
    if not path.exists():
        print(f"MISSING: {fname}", file=sys.stderr)
        missing += 1
        continue

    text = path.read_text()
    if has_frontmatter(text):
        print(f"  skipped (already has frontmatter): {fname}", file=sys.stderr)
        skipped += 1
        continue

    fm = build_frontmatter(activation, description, globs)
    path.write_text(fm + text)
    print(f"  added activation={activation:<15} -> {fname}", file=sys.stderr)
    updated += 1

print(f"\nSummary: {updated} updated, {skipped} already had frontmatter, {missing} missing.", file=sys.stderr)
