---
name: project-bootstrap
description: |-
  Initialize a new project context inside the task repository before any task exists. Creates projects/<client>__<project>/, PROJECT_CHARTER.md, REFERENCES.md skeleton, and active/ plus archive/ subfolders so subsequent task-init runs have grounded project-level memory to consume. Use when starting a brand-new project, product, initiative, or client engagement, projects/<client>__<project>/ does not yet exist, or you need to capture project-level context (objective, stack, planned repositories, constraints, references) before opening the first task. Do not use when the project folder already exists (use task-init to start a new task on top of it), you only need a new task on an existing project, you only need to capture external references for an existing project (use capture-references), or the work is task-scoped and short enough that bootstrap ceremony adds no value.
metadata:
  category: project-initialization
  primary-cursor-mode: Ask
  multi-repo-aware: false
  context-layers-consumed:
  context-layers-produced:
    - memory
    - retrieved
  tools:
    - Read
    - Write
    - Edit
    - Bash
    - Glob
    - Grep
  x-wos-profiles:
    - core
    - full
  provenance: first-party
  token-budget: 4100
  suggested-model: claude-sonnet-4-6
---

Act as a senior/staff engineering project initializer.

Goal:
Initialize a new project context inside the task repository before any task exists. Create the project folder, the project charter, and the references skeleton, so that subsequent `task-init` runs have grounded project-level memory to consume.

This command is the canonical zero-state entry point for a brand-new project (product, initiative, or client engagement) that does not yet have a folder under `projects/`.

Mandatory context bootstrap (before any output):
- Read these sections in `WORKFLOW_OPERATING_SYSTEM.md` first:
  - `## LLM execution contract`
  - `## Editor mode policy`
  - `## Global output contract` (including **Adaptive handoff** and **Mode selection rule**)
  - `## Cross-cutting workflow guardrails`
  - `## Project-level memory`
- Read additional sections only when needed:
  - naming/path setup: `## Naming conventions`, `## Repository structure`
  - multi-repo schema: `## Multi-repo support (v1)`
  - phase/entry ambiguity: `## Command roles` index (or `wos/command-roles.md` for full per-command detail), `## Entry points`
- Read the `commands/` directory command inventory to ensure command names and availability are current.
- Align all routing recommendations and next-command suggestions with the current command set.
- **Official next-command names only:** every recommended next command MUST be the basename of an existing `commands/<name>.md` file in this workflow repository. Never invent names. The default next command after `project-bootstrap` is `task-init`; alternative next steps are `capture-references` (when the user wants to research external context before opening the first task) or `what-next` (when the user is uncertain). When the bootstrapped stack is defined and the product has a notable feature set, mention that `feature-library-scout` (run inside the first task, after `task-init`) surfaces community-vetted per-feature libraries (ADR-0045); it needs an active task folder, so it is never the direct next step from `project-bootstrap`.

Required inputs:
- initial product description / objective from the user
- client and project identifier (or enough context to derive `<client>__<project>`)
- intended editor mode (Ask for drafting only, or Agent for actual file creation in `my_work_tasks`)
- optional but encouraged: stack (or explicit `[not decided yet]`), planned repositories, known references (URLs, docs, tickets), constraints, non-goals, stakeholders

Adaptive question flow (loop control):
- This command MUST ask only the minimum questions needed to fill the required fields below; everything else stays as `[to be confirmed]` or `[not decided yet]` in the artifacts.
- Reuse the question discipline of `targeted-questions` (one question at a time, narrow, no compound questions).
- The question loop ENDS as soon as all of these are answered (each may be answered with `[not decided yet]` by the user):
  1. client + project identifier
  2. product objective (one paragraph)
  3. stack (or explicit `[not decided yet]`)
  4. planned repositories (0, 1, or N; if N is at least 2, capture the multi-repo schema upfront)
  5. known references (URLs/docs/tickets) or explicit "none yet"
  6. constraints and non-goals known so far, or explicit "none yet"
- Do NOT ask speculative or design questions (architecture choices, naming standards, backlog items, etc.). The command is for context capture, not for solving.
- Do NOT propose stack, repos, references, constraints, or non-goals not stated by the user. Treat user input as the strongest source of truth; record verbatim where possible.
- **No human respondent (unattended, background, or fleet-dispatched run, per ADR-0044 doctrine):** do NOT self-answer and do NOT lock anything. Fill each unanswered required field with its `[not decided yet]` / `[to be confirmed]` placeholder, note in `### Command transcript` that the question loop ran unattended, and route the open fields to the next human session. Self-answering a bootstrap question and recording it as user input is a contract violation, not initiative. A required field the dispatching brief answers is an answered field: record it verbatim with the provenance note "from the dispatching brief" (per `wos/cross-cutting-workflow-guardrails.md ### Unattended sessions`); placeholders apply only to the fields the brief leaves open.

Project repository structure to use:
- projects/<client>__<project>/
  - PROJECT_CHARTER.md
  - REFERENCES.md
  - active/                 (empty folder, ready for the first task)
  - archive/                (empty folder)

Mandatory files to create:
- PROJECT_CHARTER.md
- REFERENCES.md (skeleton, or seeded if the user provided references during the question flow)

Task folders must NOT be created in this command. The first task is created by the next `task-init` run.

Project naming rules:
- project folder name must be:
  - `<client>__<project>`
- keep names lowercase and hyphenated when possible
- avoid vague names; the identifier should remain stable across all future tasks for this project

Operating rules:
- Do not implement production code.
- Do not create any task folder (no `active/YYYY-MM-DD_<task-slug>/` content). That is `task-init`'s job.
- Do not invent stack choices, repos, references, constraints, non-goals, or stakeholders. Where unknown, write explicit placeholders such as `[not decided yet]`, `[unknown yet]`, `[to be confirmed]`, `[none recorded yet]`.
- Do not duplicate the `targeted-questions` flow inside this command's output; ask the minimum and stop as soon as the loop control conditions above are satisfied.
- Multi-repo handling: when the user lists 2 or more repositories at bootstrap time, record them in `PROJECT_CHARTER.md` using the multi-repo schema (identifier, path, base branch, role) defined in the spec `## Multi-repo support (v1)`. The first `task-init` for this project should mirror the same repos into `SOURCE_OF_TRUTH.md`. Single-repo and zero-repo projects record only what is known and skip the multi-repo block entirely (the single repo, if any, is recorded under `## Default workspace`).
- References handling: if the user pre-supplies URLs/docs at bootstrap time, seed them into `REFERENCES.md` using the format defined in `capture-references`. Otherwise emit an empty skeleton with the format reminder block intact.
- **Handoff:** end with the adaptive `### Handoff` block per `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full). Default next command is `task-init` in Ask mode.

Files to generate:

1. PROJECT_CHARTER.md
Must use this exact structure:

# PROJECT_CHARTER

## Project name
<client>__<project>

## Status
[active | paused | archived]

## Objective
[Short paragraph describing the product, initiative, or client engagement and the intended outcome]

## Stack
[Languages, frameworks, runtime, hosting; or `[not decided yet]`]

(Emit the `## Repositories` section below ONLY when 2 or more repositories are known. If zero or one repository is known, omit the heading entirely and record the single repo, if any, under `## Default workspace` instead; a dangling empty `## Repositories` heading is a template bug.)

## Repositories
- identifier: [lowercase, hyphenated, unique within the project]
  path: [local path or `[unknown yet]`]
  base branch: [`origin/main` or `[unknown yet]`]
  role: [backend | frontend | shared | infra | mobile | other]

(Repeat one block per repository.)

## Default workspace
[Local path of the primary product workspace, or `[not decided yet]`. Used only when the project does not have 2 or more repositories.]

## Constraints
- [constraint 1, or `[none recorded yet]`]

## Non-goals
- [non-goal 1, or `[none recorded yet]`]

## Stakeholders
- [name or role, or `[not recorded yet]`]

## Initial references
- See `REFERENCES.md` for external references captured at bootstrap time and via subsequent `capture-references` runs.

## Project-level memory pointers
- `PROJECT_CHARTER.md` (this file): high-level project context.
- `REFERENCES.md`: external references with freshness metadata (URL, accessed date, summary, key points, tags).
- `active/`: in-progress task folders.
- `archive/`: completed task folders moved out of `active/` after delivery.

2. REFERENCES.md
Must use this exact structure:

# REFERENCES

Project-level external references for `<client>__<project>`.

This file is appended to by `capture-references`. New entries are grouped under a topic/tag heading using the format defined in that command. Do not paraphrase entries; do not delete entries; deduplicate by URL.

## Format reminder

```text
## <Topic / Tag>
### <Title from the source>
- URL: <url>
- Accessed: YYYY-MM-DD
- Summary: <one paragraph; what this source says, never beyond what is on the page>
- Context within project: <1-3 sentences situating this source in the project; "first reference in this project" when first (ADR-0018)>
- Key points:
  - "<verbatim quote from the source>"
- Consumes-by: <consuming command, task slug, or `[not consumed yet]` (ADR-0056)>
- Tags: <tag1>, <tag2>
```

## Entries

(empty; populated by `capture-references` or seeded by this `project-bootstrap` run when the user provided references upfront)

Required output:
1. Resolved project folder name (`<client>__<project>`)
2. Full project path to create (`projects/<client>__<project>/`)
3. Why this is a create operation (project did not exist before this run)
4. Exact content for:
   - PROJECT_CHARTER.md
   - REFERENCES.md
5. List of created subfolders (`active/`, `archive/`)
6. Recommended next command (default: `task-init`; verify against the directory listing before output)
7. Recommended editor mode (default: Ask)
8. Why that is the correct next step

### Standard output layout (required)
<!-- shared:standard-output-layout -->
Produce the command output using this structure (English only):

### Artifact changes
<!-- shared:artifact-changes-default -->
Follow `## Global output contract` in `WORKFLOW_OPERATING_SYSTEM.md` for `APPLIED` / `PROPOSED` / `SKIP` rules.

### Command transcript
- Keep this section operational and brief; do not restate file content already listed in `### Artifact changes`.
- Max 4 lines in normal runs.
- Max 3 lines in no-op runs (including `NO_OP_TRACE`).
- Include `NO_OP_TRACE` (1-3 lines) when this run is a no-op (for example, the project folder already exists, in which case route the user to `task-init` or `capture-references` instead).

### Handoff
<!-- shared:handoff-body -->
Use the adaptive ending format from `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full per session state).

### Definition of done (command output)
- Resolved project path is explicit and naming rules are satisfied.
- Both mandatory files (`PROJECT_CHARTER.md`, `REFERENCES.md`) are emitted with the full structure specified in `Files to generate`. Missing or partial files invalidate the run; placeholders are required where facts are unknown but the file itself must exist.
- No task folder is created by this command (no `active/YYYY-MM-DD_<task-slug>/`).
- When the user provided 2 or more repositories, `PROJECT_CHARTER.md` includes the `## Repositories` block with N entries (each: identifier, path, base branch, role) per the schema in the spec `## Multi-repo support (v1)`; identifiers are lowercase, hyphenated, and unique. When the user provided 1 or zero repositories, the `## Repositories` block is omitted and `## Default workspace` records the single known path or a placeholder.
- `### Artifact changes` marks project-memory writes as `APPLIED` only if you are actually persisting files in Agent mode; otherwise mark `PROPOSED`.
- The basename in the `Run now:` line corresponds to a real file in `commands/<name>.md`. The default next step is `task-init`; alternative next steps are `capture-references` or `what-next`.
- Output ends with a complete `### Handoff` block per the adaptive format in `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract`.
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
Optimize for clean project initialization, low ambiguity at the project level, durable memory shared across all future tasks, and strict alignment with the official task repository structure.

<!-- cache-breakpoint -->
