---
activation: model_decision
description: Full directory tree + governance files inventory. Load when the compact path index in the spec does not suffice.
---

# wos/repository-structure.md

Lazy reference for `## Repository structure` in the spec. The compact path index (key folders and files commands actually create or read) remains in `WORKFLOW_OPERATING_SYSTEM.md`. This file holds the full directory tree (with file-level annotations) and the inventory of repository governance files (LICENSE, CONTRIBUTING.md, SECURITY.md, etc.) that are part of the repository contract but not the runtime workflow contract.

Load this file when:
- onboarding a new contributor and the full repo layout is needed
- writing or updating tooling that touches governance files
- the compact index in the spec is not enough to resolve a path question

Single-task day-to-day execution does not need this file.

---

## Full directory tree

The workflow operates on a separate task-memory repository. The tree is a sample, not an inventory: each folder lists the files a reader most often needs, and `ls` is the full list (the `wos/` topics are also indexed by the spec's Minimum read map).

```text
<workflow-repository>/
  WORKFLOW_OPERATING_SYSTEM.md         # normative spec (lazy-loadable sub-topics under wos/)
  README.md                            # human onboarding entry point
  AGENTS.md                            # build, style, and which-tree rules for any coding agent (tool-agnostic)
  WORKFLOW_DEMO.md                     # optional; illustrative prompts + mock outputs for onboarding
  COMMAND_PROMPT_STUBS.md              # optional; minimal @commands/ prompts per phase (one row per command)
  CLAUDE.md                            # maintainer memory; excluded from the public tree (ADR-0090)
  USER_MEMORY.md                       # gitignored; bootstrap from templates/USER_MEMORY.template.md; ADR-0016
  LICENSE                              # MIT
  CONTRIBUTING.md                      # contribution flow, DCO sign-off, style guide
  SECURITY.md                          # security scope and reporting policy
  CODE_OF_CONDUCT.md                   # Contributor Covenant 2.1
  CHANGELOG.md                         # Keep a Changelog format
  ROADMAP.md                           # project waves and direction (non-binding)
  templates/
    PR_PACKAGE.md
    LEARNINGS.md                      # task-scoped reflexion log; 5 required bullets from `Anchor:` to `Cross-project promotion:`, plus an optional `Tags:` bullet that rank-learnings.sh scores (ADR-0017, ADR-0071)
    USER_MEMORY.template.md           # bootstrap for /USER_MEMORY.md (ADR-0016)
  scripts/
    sync-workflow-slash-commands.sh   # optional; copies commands/ to Cursor + Claude Code + Codex (Kimi Code has no command dir, skills only); --with-docs mirrors the spec/README/DEMO/stubs/templates to ~/.cursor/workflow-docs and ~/.claude/workflow-docs; skills sync by default from .claude/skills/ to ~/.claude/skills and ~/.agents/skills (shared by Codex, Kimi and Cursor 3.17.8 or later; ~/.cursor/skills only under --cursor-skills, ADR-0228), --no-skills skips them and --with-skills is kept for backward compatibility; --profile=minimal|core|full picks the command set, minimal by default (see --help)
    lint-commands.sh                  # validates command file contract, shared-block drift, frontmatter, token-budget overrun, and skills drift (via build-agent-skills.sh --check)
    reconcile-counts.sh               # FIX side of the lint count-marker guard: sets every count:KIND marker across the lint scan-set to the live on-disk count in one pass; --check reports drift without writing; narrow scan-set (never touches the maintainer-local, gitignored _internal/ snapshots)
    sync-shared-blocks.sh             # propagates commands/_shared/<name>.md content into commands that declare the marker
    build-agent-skills.sh             # generates .claude/skills/<name>/SKILL.md from commands/<name>.md (idempotent; --check, --no-prune, --dry-run)
    typecheck-hook.sh                 # Claude Code PostToolUse hook; runs tsc --noEmit after Edit/Write on .ts/.tsx, filters pre-existing errors via project-level .typecheck-baseline, surfaces only new ones (non-blocking)
    hook-integrity-check.sh           # Claude Code SessionStart hook (advisory); warns when .claude/settings.json has a hook command absent from .claude/hooks-baseline.json (config-tamper nudge); always exits 0, silent without a baseline; templates/hook-integrity-check.template.md + templates/hooks-baseline.json.template
    s3-thin-skills.py                 # one-shot maintenance helper; strips boilerplate sections from command files during a thinning pass
    bootstrap-user-setup.sh           # first-time setup helper; bootstraps USER_MEMORY.md from template, runs lint sanity check, prints next-steps hints
    measure-tokens.py                 # optional; estimates spec / commands / shared / TASK_STATE token footprint and projects cache scenarios; --per-command emits per-command table
    measure-task-cost.py              # optional; simulates a canonical <!-- count:task-cost-phases -->9<!-- /count -->-phase task lifecycle and reports per-phase token cost under uncached vs cached models (ADR-0020)
    measure-grounding-shape.py        # ADR-0146 forward instrument; counts `Grounded in:` cite shape in task artifacts (internal file:line vs external REFERENCES entry) and window-vs-whole read shape in harness transcripts; baseline snapshot at scripts/baseline-grounding-shape-2026-08-13.md
    check-doc-sync.sh                 # doc-drift detector; greps cited counts vs on-disk artifacts; companion to monthly audit cadence
    check-natural-voice.sh            # natural-voice scanner; flags AI tells in prose; standalone, run by hand (ADR-0171); companion to wos/natural-voice.md
    check-instruction-budget.sh       # warn-only guard for always-loaded files (CLAUDE.md, USER_MEMORY.md) over a soft size/line budget; advisory line in lint (W-15, ADR-0023 idea)
    monitor-fleet-progress.sh         # tails active fleet batches; surfaces convergence + worker status (ADR-0038)
    scan-substrate-orphans.py         # detects substrate files with no inbound references (K.2 audit)
    build-activity-timeline.py        # optional; renders a task's .wos audit log as a gitignored, self-contained ACTIVITY.html (one entry per command run, grouped by run_id+command); on-demand, stdlib-only (ADR-0049)
    baseline-*.md                     # snapshots produced by the measure-*.py scripts; frozen at write time for trend comparison
  commands/
    # K.3 (2026-06-04) dual layout. Both layouts are first-class; scripts
    # (build-agent-skills, lint-commands, sync-shared-blocks) discover both.
    #
    # FLAT layout (one file per command, plus the folder-shaped persona commands below; the live
    # total is the count marker in README.md; no migration planned):
    <one markdown file per command, e.g.>
    task-init.md                      # example
    what-next.md                      # example
    implementation-plan.md            # example
    implement-approved-slice.md       # example
    pr-package.md                     # example
    approve-proposed.md               # on request only: promotes PROPOSED blocks a non-owner staged (ADR-0034, ADR-0199)
    db-context-postgres.md            # example
    extract-foundations-from-screens.md # example
    #
    # FOLDER-SHAPED layout (K.8 and later personas; <!-- count:personas -->9<!-- /count --> folder-shaped):
    <one folder per command/persona>/
      SKILL.md                        # canonical body with frontmatter (same shape as flat .md)
      # additional persona assets (rubrics, examples, etc.) live in the folder
      # alongside SKILL.md and are not propagated by sync-shared-blocks
    #
    # Canonical-block bodies (shared across commands, both layouts; a sample, `ls commands/_shared` for all):
    _shared/
      mandatory-context-bootstrap.md  # canonical 8-bullet bootstrap block
      standard-output-layout.md       # canonical single-line layout body
      artifact-changes-default.md     # canonical 1-line pointer to the spec's ## Global output contract
      handoff-body.md                 # canonical handoff template
      command-transcript-standard.md  # canonical 4-bullet transcript body
      command-transcript-lean.md      # 3-bullet transcript body for capture-observation
      worker-contract.md              # canonical worker I/O + status taxonomy (ADR-0034)
      orchestrator-bootstrap.md       # additional bootstrap for orchestrator commands (Epic J)
      convergence-policy.md           # canonical convergence patterns + failure classification
      substrate-write-protocol.md     # canonical transaction-header + JSONL audit line (K.2)
      task-state-slice-closure-pattern.md # canonical <!-- count:closure-pattern-sections -->5<!-- /count -->-section write pattern
      README.md                       # documents the marker convention + per-block consumer counts
  wos/                                # a sample of the lazy topics; `ls wos` for all
    command-roles.md                  # lazy: full per-command role detail
    cross-cutting-workflow-guardrails.md  # lazy: sequencing heuristics + external-web motivation
    multi-repo-support.md             # lazy: schema + decisions + invariants + non-goals + decision table + implementation notes
    repository-structure.md           # lazy: this file (full tree + governance file inventory)
    project-level-memory.md           # lazy: project-memory layer rationale (ADR-0007) + relationship to user memory (ADR-0016)
    global-output-contract.md         # lazy: PROPOSED/APPLIED/SKIP vocabulary; Artifact-changes shape; Handoff contract
    natural-voice.md                  # lazy: natural-voice catalog (AI-tell patterns + before/after rewrites); standalone scanner in scripts/check-natural-voice.sh
    model-routing.md                  # lazy: escalation-to-SKU table, override rules, six-week refresh cadence (moved out of ADR-0025 by ADR-0172)
    context-budget.md                 # lazy: six-layer context model; per-phase compaction guidance; context-rot thresholds (ADR-0012, ADR-0013, ADR-0023)
    sub-agent-orchestration.md        # lazy: orchestrator-workers pattern documentation (ADR-0022)
    design-system-conventions.md      # lazy: design-system spec conventions (tokens, components, Style Dictionary, DTCG)
    output-depth-policy.md            # lazy: Lean / Balanced / Deep output sizing policy
    anti-patterns.md                  # lazy: <!-- count:anti-patterns -->29<!-- /count --> anti-patterns to avoid
    entry-points.md                   # lazy: <!-- count:entry-points -->21<!-- /count --> first-command quick-start scenarios
    gate-conditions.md                # lazy: 6 phase-boundary gate checklists
    operating-modes.md                # lazy: minimal, strict, teaching, assisted operating modes
    task-file-contracts.md            # lazy: required/optional task-file purpose and structure
    workflow-shapes.md                # lazy: task-shape flows with skip rationales
    editor-mode-mappings.md           # lazy: Ask/Plan/Agent/Debug mapping to other tools
    external-integration-patterns.md  # lazy: outbound webhook + 3rd-party API conventions
    maturity-ladder.md                # lazy: maturity ladder definitions, including the L3 -> L4 review gate
    substrate-peers.md                # lazy: substrate peer relationships
    workflow-patterns.md              # lazy: workflow patterns catalog
    bug-classes/                      # lazy: <!-- count:bug-templates -->81<!-- /count --> bug-class files across <!-- count:bug-categories -->22<!-- /count --> categories
  docs/
    FAQ.md                            # user-facing entry point for common questions
    MIGRATION.md                      # adoption + forking + tool migration guide
    adr/                              # Architecture Decision Records (<!-- count:adrs -->242<!-- /count --> ADR files; 0037 is an intentional gap; highest is 0243)
      README.md                       # index + format + when to write
      template.md                     # ADR template
      0001-proposed-by-default.md     # example; the full list, highest number included, is docs/adr/README.md
      ...
    command-catalog.json              # generated by build-command-catalog.py: per-command manifest plus a `counts` block (11 artifact counts, same formulas as reconcile-counts.sh disk_count)
    command-catalog.html              # generated by build-command-catalog.py: browsable per-command reference
  evals/
    README.md                         # eval harness overview + cadence + the spine runner (run-spine-evals.py)
    scenarios/                        # <!-- count:scenarios -->144<!-- /count --> scenarios; one markdown file per scenario, each with a row in evals/README.md
      template.md                     # scenario template
      01-bootstrap-and-init.md        # example
      ...
    scripts/
      run-evals.sh                    # manual walkthrough (one scenario per stdin prompt)
      run-spine-evals.py              # runs the evals/spine-evals.json set against a model command; --record writes one History line
      spine_eval_extract.py           # pure prompt and rubric extraction the runner imports
  .claude/
    skills/                           # generated; do not edit by hand
      <name>/
        SKILL.md                      # generated from commands/<name>.md (flat) OR commands/<name>/SKILL.md
                                      # (folder-shaped) by scripts/build-agent-skills.sh
                                      # consumed natively by Claude Code; by Cursor, Copilot,
                                      # OpenAI Codex, Gemini CLI, OpenHands, Goose, Junie, etc.
  .github/
    ISSUE_TEMPLATE/
      bug_report.md
      feature_request.md
    pull_request_template.md
    workflows/
      lint.yml                         # CI: 6 jobs (lint-commands, validate-skills-spec, structural-evals, script-tests, lint-shellcheck, check-doc-sync)

  projects/                           # gitignored per ADR-0007 (project-level memory; not part of open-source distribution); in a product repo, by projects/.gitignore per ADR-0223
    <client>__<project>/
      PROJECT_CHARTER.md                # project-level; created by project-bootstrap
      REFERENCES.md                     # project-level; appended to by capture-references; ADR-0018 adds `Context within project` field
      active/
        YYYY-MM-DD_<task-slug>/
          README.md
          TASK_STATE.md
          SOURCE_OF_TRUTH.md
          DECISIONS.md
          IMPLEMENTATION_PLAN.md
          IMPACT_ANALYSIS.md                # optional
          INVARIANTS_AND_NON_GOALS.md       # optional
          TEST_STRATEGY.md                  # optional
          PR_PACKAGE.md                     # optional
          LEARNINGS.md                      # optional; ADR-0017 reflexion-style learnings
          DB_CONTEXT.md                     # optional; created by db-context-* commands
          SLICES/                           # optional
            01_<slice-slug>.md
            02_<slice-slug>.md
      archive/                          # completed tasks; equivalent to legacy "done/"
        YYYY-MM-DD_<task-slug>/
          ...
      done/                             # legacy alias for archive/; either is acceptable
        YYYY-MM-DD_<task-slug>/
          ...
```

## Repository governance files

The repository includes standard open-source governance files. They are not part of the runtime workflow contract, but they are part of the repository contract:

- `LICENSE`: project is licensed under MIT (relicensed from AGPL-3.0 on 2026-07-12), which permits commercial and closed-source use without a separate agreement.
- `CONTRIBUTING.md`: how to report issues, propose changes, submit PRs, and how sign-off works. Contribution is certified with the Developer Certificate of Origin (`git commit -s`), not a CLA. Source of truth for contribution policy.
- `SECURITY.md`: scope of "security" in a markdown-based workflow repo, plus reporting flow.
- `CODE_OF_CONDUCT.md`: Contributor Covenant 2.1.
- `CHANGELOG.md`: chronological record of changes following Keep a Changelog and SemVer.
- `ROADMAP.md`: high-level direction across waves and phases. Non-binding.
- `CLAUDE.md`: maintainer memory for the staging tree; excluded from the public tree (ADR-0090).
- `.github/ISSUE_TEMPLATE/*` and `.github/pull_request_template.md`: standardize incoming reports and PRs.
- `.github/workflows/lint.yml`: CI that validates command files, the structural evals, script tests, bash scripts, and cross-document references on every push and PR to `main`.

When a command file or task artifact references licensing, contribution flow, security, or release versioning, defer to these files; do not duplicate their content inside command files or `TASK_STATE.md`.
