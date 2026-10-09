---
name: task-init
description: |-
  Initialize the task folder and base task memory inside projects/<client>__<project>/active/YYYY-MM-DD_<task-slug>/, seeded from PROJECT_CHARTER.md when present, or from a vetted issue-tracker MCP item (gated, off by default). Use at the START of any engineering work in this workflow's repositories, before the first file is edited, including a one-line docs change or a typo fix (small scope never skips the workflow). Do not use when the task folder exists, to resume (use resume-from-state), or to update memory (use sync-task-state). For a brief with 3 or more independent sub-tasks, use task-init-fleet.
metadata:
  category: "state-and-navigation"
  primary-cursor-mode: "Ask"
  multi-repo-aware: "true"
  context-layers-consumed: "memory"
  context-layers-produced: "memory"
  tools: "Read, Write, Edit, Bash, Glob, Grep"
  x-wos-profiles: "minimal, core, full"
  provenance: "first-party"
  suggested-model: "claude-opus-5-5"
---
> **Output contract, in brief.** This body is over the per-skill re-injection cap, so
> after a compaction the sections below are truncated away while this summary survives.
> They remain authoritative in full; re-read this file before emitting if you need them.
>
> - `Standard output layout (required)`: Produce the command output using this structure (English only):
> - `Artifact changes`: Follow `## Global output contract` in `WORKFLOW_OPERATING_SYSTEM.md` for `APPLIED` / `PROPOSED` / `SKIP` rules. Every listed file...
> - `Command transcript`: Brief audit trail (max 4 lines; max 3 in no-op runs with `NO_OP_TRACE`).
> - `Handoff`: Use the adaptive ending format of `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract`. Every Handoff is one fenced `text` b...
> - `Definition of done (command output)`: All resolved paths are explicit (project + task folder) and naming rules are satisfied.


Act as a senior/staff engineering workflow state initializer.

Goal: create the official task folder and base task memory for a new engineering task. Mandatory at the start of every new task.

Mandatory context bootstrap (before any output):
- **Resolving the spec and `wos/<topic>.md`:** canonical repository FIRST. Otherwise use active-adapter docs: `~/.claude/workflow-docs` (`CLAUDE_WORKFLOW_DOCS_DIR`), `~/.cursor/workflow-docs` (`WORKFLOW_DOCS_DIR`; project `.cursor/workflow-docs` on project installs), `~/.codex/workflow-docs` (`CODEX_WORKFLOW_DOCS_DIR`), or `<kimi-home>/workflow-docs` (`KIMI_WORKFLOW_DOCS_DIR`). Nonempty overrides win. Kimi home: `KIMI_CODE_HOME`, else existing `~/.kimi-code`, else existing `~/.kimi`, default `~/.kimi-code`. Use one root for both paths; try other adapters if absent or unknown. Report resolved root, fallback to other adapters, or missing mandatory context in `### Command transcript`. Installed snapshots refresh and prune retired topics only on sync.
- Read these `WORKFLOW_OPERATING_SYSTEM.md` sections first: `## LLM execution contract`, `## Editor mode policy`, `## Global output contract` (including **Adaptive handoff** and **Mode selection rule**), `## Cross-cutting workflow guardrails`, `## Project-level memory`.
- Read additional sections only when needed:
  - naming/path setup: `## Naming conventions`, `## Repository structure`
  - artifact requirements: `## Task files`, `## TASK_STATE policy` (per-file contract: load `wos/task-file-contracts.md`)
  - phase/entry ambiguity: `## Command roles` index (or `wos/command-roles.md` for full per-command detail), `## Entry points`, `## Gate conditions`
  - output sizing: `## Output depth policy`
- Read project-level memory when present:
  - `projects/<client>__<project>/PROJECT_CHARTER.md`
  - `projects/<client>__<project>/REFERENCES.md`: check that it EXISTS and link to it; do NOT read it here (ADR-0214).
  - Do NOT read `projects/<client>__<project>/knowledge/` (ADR-0054, ADR-0055) or seed `SOURCE_OF_TRUTH.md` from it.
  - When either file is missing, treat the project as not yet bootstrapped and warn (see Operating rules); do not block the task.
- Read `/USER_MEMORY.md` at the repo root when present (ADR-0016); when absent, proceed silently. Apply its preferences where they shape the artifacts, by the precedence in `wos/project-level-memory.md ### Layered precedence`.
- Read prior LEARNINGS when present (ADR-0017 consume side):
  - Resolve `scripts/rank-learnings.sh` against the WORKFLOW ROOT, the same root the two-root preflight found for the spec and `wos/` (the repository clone, or the installed docs directory, which ships this one script per ADR-0214), never against the task repository, which has no `scripts/`. When it is present in neither, say so in one `### Command transcript` line (`rank-learnings: not installed, prior LEARNINGS not consulted`) instead of skipping the step silently.
  - Run it as `rank-learnings.sh "<task keywords or objective>" <project-path>` (ADR-0071) over `projects/<client>__<project>/active/*/LEARNINGS.md` and recent `archive/` tasks; also read the cross-project learnings in `/USER_MEMORY.md`.
  - Surface the ranker's capped "relevant prior lessons" block in the handoff. Read-only: never compact, prune, or rewrite any `LEARNINGS.md`. When nothing is relevant, say nothing.
- Read the clone command inventory when available; otherwise use installed Fhorja commands and skills.
- **Official next-command names only:** every recommended next command (including inside `TASK_STATE.md` and the handoff `Run now` line) MUST be a registered canonical command name or an available installed Fhorja command or skill. Never invent names. The after-init route is set under Escalation assessment. Exception: `Run now: none` with `Mode: N/A` declares the chain ended with no honest next step (`### Official command names (routing integrity)`, ADR-0126); never use it to end a chain that has a real next step.

Required inputs:
- task description / objective
- client and project identifier (or context to derive `<client>__<project>`)
- task slug (or context to derive `YYYY-MM-DD_<task-slug>`)
- intended editor mode (Ask for drafting only, Agent for actual file creation)
- known source-of-truth pointers (codebase path, branch, tickets, docs), if any
- optional: repositories, only when the task touches 2 or more coordinated product repositories. Each entry: identifier (lowercase, hyphenated, unique), local path, base branch, role tag (`backend` / `frontend` / `shared` / `infra` / `mobile` / `other`). Schema: spec `## Multi-repo support (v1)`.
- optional: worktree isolation opt-in (`task-workspace`, ADR-0074, spec `### Per-task worktree isolation (opt-in, v1)`).

Task repository structure to use: `projects/<client>__<project>/active/YYYY-MM-DD_<task-slug>/`

Mandatory files to create: README.md, TASK_STATE.md, SOURCE_OF_TRUTH.md, DECISIONS.md, IMPLEMENTATION_PLAN.md

Optional files must NOT be created unless the user explicitly asks: IMPACT_ANALYSIS.md, INVARIANTS_AND_NON_GOALS.md, TEST_STRATEGY.md, PR_PACKAGE.md, SLICES/

Naming rules: spec `## Naming conventions` (an English, lowercase, hyphenated slug specific enough to distinguish the work, never a vague one such as `fix-bug`).

Operating rules:
- **Two-root preflight (before creating the task folder; ADR-0129):** the **task repository** holds `projects/<client>__<project>/`; the **workflow root** is where the spec and `wos/` resolved from (the canonical checkout, or an installed `workflow-docs/`). NEVER require `commands/`, `scripts/`, or `wos/` inside the task repository. Resolve the task repository from source-of-truth pointers, the working directory, or a user-supplied path; validate each root for what it should hold, then:
  - **STOP 1:** neither the spec nor `wos/` is reachable. Name what is missing, ask for the correct path, create nothing.
  - **STOP 2:** the resolved TASK repository holds `commands/` and `wos/` but no `projects/` (it is the workflow checkout, not a task repository). Name it, ask the user to confirm or supply the right path, create nothing there.
  - Record the workflow root used in one `### Command transcript` line. An installed docs tree is the NORMAL mode, never reported as a degradation; when it carries no `scripts/`, `commands/_shared/substrate-digest-fallback.md` applies and the run says so.
  - **Task folder already exists.** Create and overwrite nothing: emit `NO_OP_TRACE` naming the folder, then route to `where-we-at` when the work continues that task, or ask for a distinct slug when it is new work.
- **Git-authority preflight (after the two-root preflight; detect and recommend only):** WHEN the active PRODUCT codebase path is known, run ONE check, `git -C <path> rev-parse --is-inside-work-tree` (a missing path counts as no git authority); when unknown, skip and leave the placeholder. On no git authority, record `Git status: no git authority at <path>` plus `Recommended action: git init -b main (requires human authorization)` in `SOURCE_OF_TRUTH.md ## Active codebase / repo`, mirror the action line into `TASK_STATE.md ## Risks to watch` in the same batch, and cite it in the handoff. Task creation NEVER blocks on this check; `git init` always waits for human authorization. Late-binding hook: any command that later promotes `## Active codebase / repo` from a vague pointer to a concrete path SHALL trigger this same one-call check at that moment.
- **Task branch (ADR-0233).** WHEN the run is attended with no `Operating mode: assisted`, no worktree is requested, and the product codebase has a remote, apply `wos/task-init-opt-ins.md ## Task branch`, which writes `Task branch:` and `Base branch:` (Ask and Plan only propose the switch). Under standing authorization (ADR-0244) apply it with no remote too. Otherwise create no branch.
- **Assumptions (ADR-0233).** In an attended run with no `Operating mode: assisted`, list under `### Assumptions` each decision the brief lacks and the option the chain will take, or `None.`, and do not wait: the command that needs it records a provisional `### P-N`; a mid-chain answer replaces it.
- **Opt-in steps:** read `wos/task-init-opt-ins.md` and apply the matching rule when the harness restricts the write root, the user requests worktree isolation, or the task is product work on a project with a notable feature set.
- Do not implement production code.
- **Handoff:** end with the adaptive `### Handoff` block per `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full).
- **Substrate write protocol (ADR-0034, ADR-0110 `batch`).** MANDATORY on TASK_STATE.md, DECISIONS.md, IMPLEMENTATION_PLAN.md, SOURCE_OF_TRUTH.md (not README.md). Header IMMEDIATELY above each created H2, no blank line: `<!-- wos:write owner=task-init section='## X' run_id=<ULID> ts=<ISO-8601-ms-Z> reason=task-init-<slug> mode=applied -->`. `reason` <= 80 chars. Same `run_id`+`ts` on all four files. Then one `bash scripts/emit-substrate-write.sh batch --owner task-init --file <FILE> --reason task-init-<slug> --mode applied --task-root <task-folder> --run-id <id>` per file. Never `apply`. COUNT 0: header not previous line or missing `owner=task-init `.
  FORBIDDEN: half-compliant pattern (JSONL emitted but inline header omitted on any section, OR `sha_after` set to `null` on any applied write).
- Do not invent missing facts, decisions, or constraints. If required initialization context is missing, ask only the minimum targeted questions needed to create the task safely.
- **No human respondent (unattended or fleet-dispatched run, or a background session failing the ADR-0237 test in `wos/cross-cutting-workflow-guardrails.md ### Unattended sessions`):** do NOT self-answer the initialization questions. Seed every field the dispatching brief supplies, recording each with the provenance note "from the dispatching brief"; fill the rest with the explicit placeholders below; note in `### Command transcript` that the run was unattended; and never self-lock the residue. Exception: under standing authorization (ADR-0244, same section) open decisions become provisional `### P-N` and the pipeline below binds.
- **Escalation assessment (ADR-0184).** After creating the task folder the pipeline is `task-init` -> `implementation-plan` -> `approve-plan` -> `implement-approved-slice` -> `branch-commit` (-> `pr-package --apply` in an attended chain on a task branch), with the `minimal` profile suggested. Add a command only when a disqualifier below fires, and NAME the fired disqualifier on the `Escalations:` line of `## Recommended pipeline`; an escalation with no named disqualifier is invalid output. Uncertainty is not a disqualifier; only a signal you can point at is.
  - Add `impact-analysis` before the plan when the scope needs more than one sentence to state, OR the change touches 5 or more files.
  - Add `decision-interview` when a decision the prompt does not contain is required before the first line of code, OR the change spans multiple packages or adds an external service dependency.
  - Add `invariants-and-non-goals`, `test-strategy` and `review-hard`, and suggest `Operating mode: strict`, when the surface is auth, payments, compliance, PII, or multi-tenant isolation. Categorical, not a judgment call.
  When no disqualifier fires AND the unattended bullet did not fire, that pipeline binds (ADR-0159); it is not an offer. Unless the one-slice route below applies, the Handoff is `Run now: implementation-plan`, `Mode: Agent`, in every mode: the five files are written, not proposed. When the unattended bullet fired, do not bind that pipeline, save under standing authorization (ADR-0244). The user can override by choosing another command. Do not re-ask decisions the task description already locks.
- **State the escalation set in the handoff:** every disqualifier that fired (or that none did), plus the sentence-length scope.
- **One-slice route (ADR-0225, ADR-0239).** Take it only when every condition holds, each written with its evidence on a `Route: one-slice` line in `## Recommended pipeline`: (1) no escalation fired, the run is attended, and no `Operating mode: strict` is declared; (2) the change fits one sentence and touches at most two files the brief names; (3) `DECISIONS.md ## Locked decisions` stays empty and every `### Assumptions` entry is `Impact: normal` on a run with a `Task branch:` line; write each in the same batch as a `### P-N` under `## Provisional decisions` (the draft PR lists it), and it fires no `decision-interview`, while an `Impact: high` one keeps the full path; and `scripts/check-doc-sync.sh` resolves in the workflow root. A condition you cannot show has failed: doubt keeps the full path. On the route, write in the same batch the one slice in `## Slices` (`Scope:` the named files, `Depends-on: none`, `Status: approved`, `Work complexity: LOW`, `Decision-ref:` `rests on provisional P-N` per P-N, else `none (<why>)`, exit criterion `WHEN the slice diff is complete, check-doc-sync.sh --against HEAD SHALL exit 0`), a `## Approval log` line `<date>: APPROVED (one-slice route); check-doc-sync.sh --against HEAD replaces the blinded review.`, and `## Current phase` `implementation (plan APPROVED, one-slice route)`: both lock signals `implement-approved-slice` reads. Then run `scripts/check-plan-coverage.sh <task-folder>`; any exit but 0 ends the route and hands off to `implementation-plan`. Otherwise hand off `Run now: implement-approved-slice`, `Mode: Agent`. `implementation-plan` and `approve-plan` are skipped on this route only.
- Use explicit placeholders (`[unknown yet]`, `[to be confirmed]`, `[not decided yet]`). Code and existing task context are the strongest source of truth. Keep the files concise: a usable foundation, not a solved task.
- Project-level memory handling:
  - When `PROJECT_CHARTER.md` exists, seed `SOURCE_OF_TRUTH.md` from it (stack, repositories, constraints, non-goals, default workspace) instead of re-asking. When `REFERENCES.md` exists, link to it under `## Project-level memory`.
  - When the project folder exists but `PROJECT_CHARTER.md` is missing, warn the user with a one-line note ("project not bootstrapped: recommended to run `project-bootstrap` first to capture project-level context") and continue with user-supplied inputs and explicit placeholders. Do not block the task.
  - When `projects/<client>__<project>/` itself does not exist, recommend running `project-bootstrap` before proceeding; if the user insists on starting the task immediately, create the project folder ad hoc with only the task subtree and emit the same warning. A session with no human respondent, standing authorization included, creates it ad hoc the same way with the warning, and never recommends `project-bootstrap` first. When that creates `projects/` itself, apply `### Task memory stays out of git` below.
  - **Ignore check (ADR-0223 D-2).** WHEN `projects/` existed before this run, run `git -C <task repository> check-ignore -q projects/<client>__<project>/` once. Exit 1 means git would track the task memory: print one `### Command transcript` line, `projects/ is not ignored in <task repository>: add projects/.gitignore holding '*'; if task files are already committed, also run git rm -r --cached projects`. Exit 0 (ignored) and 128 (not a git repository) print nothing. Warn on every run and never write the fix yourself.
  - When `projects/<client>__<project>/BRIEF.md` exists (a transient intake brief written by `problem-framing`, ADR-0058), consume it: seed the task description, `SOURCE_OF_TRUTH.md`, and the `## Requested deliverables` ledger from its 5 fields (problem statement, success criteria, non-goals, recommended approach, named deliverables), then MOVE `BRIEF.md` into the new task folder; do not leave it at the project root.
  - **MCP-sourced seed (gated, opt-in):** WHEN the user references an issue-tracker item AND a vetted issue-tracker MCP is connected, read `wos/mcp-capability-routing.md` first and apply its trust gate, capability routing, failure policy and ingest mapping exactly as written, then pull it: title and body seed the task description and the `## Requested deliverables` ledger (ADR-0056); identifier and URL go to `SOURCE_OF_TRUTH.md` as a `source: mcp` provenance pointer. A failed pull follows that file's failure policy, never a fabricated item. With no MCP connected this bullet does not apply.
- Deliverable-ledger seeding (ADR-0056): seed `## Requested deliverables` in `TASK_STATE.md` from the user's brief (or the `Named deliverables` field of a consumed `BRIEF.md`). One row per concrete deliverable the user named (an artifact to produce or an input to analyze), tagged `in-scope`, not every implied sub-task. When the brief names none, write a single `- none named` row rather than omitting the section. WHEN a row is user-facing product content or a new user-facing surface, it SHALL carry the tag `user-facing-content` or `new-user-facing-surface` (ADR-0091) next to its in-scope tag, by the ADR-0103 tagging test in the `## Requested deliverables` annotation of `templates/TASK_STATE.template.md`.
- Multi-repo handling: if 2 or more repositories were provided (directly or from `PROJECT_CHARTER.md`), generate a `## Repositories` section in `SOURCE_OF_TRUTH.md` per the spec `## Multi-repo support (v1)`. Validate that identifiers are lowercase, hyphenated, and unique within the task. With 1 repo or none, omit `## Repositories` entirely; single-repo tasks use the `active codebase / repo` field.

Files to generate:

1. README.md
Must include: task name, project name, short task summary, objective, current status, and `## Brief`: the user's brief verbatim (in an unattended run, the dispatching brief; with a consumed `BRIEF.md`, a pointer to it), so a provisional decision can quote it and `approve-plan`'s blinded review can resolve that quote.

2. TASK_STATE.md
Must use this exact structure:

Section annotations live in `templates/TASK_STATE.template.md`; read it when seeding. The 20-section structure below is normative for names and order.

# TASK_STATE

## Quick reanchor
- Active decisions: [D-N: one clause each | none locked yet]
- Current slice: [from IMPLEMENTATION_PLAN.md ## Slices | none]
- Phase: [current phase]
- Next step: [command from ## Recommended next step]

## Task summary

## Current phase
[discovery | planning | contract refinement | contract signoff | test design | implementation | review | debug | delivery]

## Objective

## Requested deliverables
- [deliverable 1] [in-scope | de-scoped:<reason> | done] [+ user-facing-content or new-user-facing-surface when a human end user experiences or reaches it]

## Recommended pipeline
- Escalations: [none | <added command> (<disqualifier that fired>), ...]

## Source of truth

## Current known facts

## Canonical decisions

## Open questions / blockers

## Last completed step
- Command:
- Mode:
- Summary:

## Current status
### Completed

### In progress

### Not started

## Active files in scope

## Constraints / things that must not change

## Risks to watch

## Recommended next step
- Command: (official basename only, must match `commands/<name>.md` or `commands/<name>/SKILL.md` in this repo, e.g. `impact-analysis`, not `task-plan`) In installed mode use the available Fhorja inventory.
- Mode:
- Why:

## Work complexity (for next execution step)
LOW | MEDIUM | HIGH | N/A
- Rationale (one line):

## Resume notes

## Task scope level
[full task | current phase | current slice | hotfix]

## Current closure target

3. SOURCE_OF_TRUTH.md
Must include, under the canonical H2 names of the `wos/substrate-peers.md` SOURCE_OF_TRUTH rows:
- `## Active codebase / repo` (carries the Git-authority preflight's `Git status:` and `Recommended action:` lines when it found no git authority)
- `## Active branch`, if known
- `## Main files in scope`, if known
- `## Tickets / docs / Figma / links`: tickets, docs and links, plus the one-line pointer `Requested deliverables: see TASK_STATE.md ## Requested deliverables` (ADR-0056; do not duplicate the ledger)
- `## Official external docs`
- `## Repositories`, only under the Multi-repo handling rule above
- optional `## Project-level memory` with relative pointers `../../PROJECT_CHARTER.md` and `../../REFERENCES.md` when present; omit it entirely when the project was not bootstrapped (no `PROJECT_CHARTER.md` at the project root).

4. DECISIONS.md
Must include only approved decisions, under the exact header `## Locked decisions`; when none are approved yet, say so there ("None locked in this task."). On the one-slice route, add its `## Provisional decisions`.
Every task also gets `## Domain terms` (ADR-0245): one row per brief term whose reading changes a stored or displayed value (verbatim quote, a counter-case input that separates two readings, the chosen outcome, where it is shown), or the single row `none: <reason>`. Each chosen outcome is provisional until locked; row format: `wos/task-file-contracts.md ### DECISIONS.md`.

5. IMPLEMENTATION_PLAN.md
Must include, under the canonical H2 names `implementation-plan` later owns: `## Target behavior`, `## Current gaps`, `## Constraints` (known constraints), `## Slices` (initial expected phases or slices), `## Open questions or approvals still needed` (unknowns that block safe planning), and `## Approval log` on the one-slice route only.

Required output:
1. Resolved project folder name, task folder name, and full task path to create
2. Why this is a create operation
3. Exact content for the five files
4. `### Assumptions` and the `Task branch:` value
5. Recommended next command (must exist as `commands/<name>.md` or `commands/<name>/SKILL.md`; verify against the directory listing before output; in installed mode use the available Fhorja inventory), recommended editor mode, and why it is the correct next step

### Task memory stays out of git
WHEN this run creates the `projects/` directory itself in the task repository, it writes `projects/.gitignore` in the same batch, holding the single line `*` (ADR-0223). That line ignores everything under `projects/`, the file included, so task memory stays out of the product repository's history without touching a file the user owns. List it `APPLIED` in `### Artifact changes`.
- Never edit the repository's own `.gitignore`.
- Never write `projects/.gitignore` into a `projects/` that already exists. A user who deleted it chose to track the tree.
- Write it outside a git repository too, so a later `git init` inherits the rule.
### Substrate digest fallback
**Digest fallback when the canonical helper is unreachable.** `sha_of_section` extracts a section's body with `awk` and pipes it to `shasum -a 256`. A run inside a permission boundary that admits `shasum` but refuses `awk` and `sed` cannot invoke that helper, and MUST NOT reimplement it. Assume the helper is unreachable whenever the workflow repository's `scripts/` directory is not readable from the working directory.

WHERE the canonical per-section digest helper is unreachable, the write SHALL use a whole-file SHA-256 and SHALL declare the reduced scope:

```bash
# One call per file. Read the hash (the first field) out of the output;
# do not pipe it through `cut` or `awk` to trim it.
shasum -a 256 TASK_STATE.md
```

Then add `"sha_scope":"file"` to that JSONL line, so a validator distinguishes a file digest from a section digest. The rest of the protocol is unchanged: the transaction header still goes above the section heading, and there is exactly one JSONL line per section write.

Do NOT rebuild the helper by writing each section out as its own file to hash it separately.

At file scope two sections written in the same run share a digest, so the `sha_scope` field is mandatory, not optional.
### Claim grounding (active epistemic humility)
**Claim grounding (active epistemic humility).** This block governs what you may assert and how you record it. It is keyed to the substrate section you are writing, not to which command is running, and it is INERT on any output that writes none of the claim-bearing sections below. Full contract and rationale: `wos/active-epistemic-humility.md`.

1. When this applies. This block fires ONLY while you are writing a claim-bearing substrate section: `TASK_STATE.md ## Current known facts`, `## Risks to watch`, `## Observations`, `## Active files in scope`, `## Canonical decisions`; `DECISIONS.md ## Locked decisions`; `IMPLEMENTATION_PLAN.md ## Current gaps`, `## Risks and mitigations`; `IMPACT_ANALYSIS.md`; `EXTERNAL_RESEARCH.md`; `REFERENCES.md`; or any section whose content is a statement a later command or a human decision will act on. WHEN your output writes none of these, this block imposes nothing: skip it and proceed. This is the D-13 inert clause; a fully-grounded or claim-free output pays nothing.

2. The unit is the load-bearing claim. A load-bearing claim is one a downstream command or a human decision consumes. A passing aside is not load-bearing; a statement someone will act on is. Apply the rest of this block per load-bearing claim, not per sentence.

3. Ground it or abstain. Before you assert a load-bearing claim, trace it to the enumerable grounded set: a captured `REFERENCES.md` entry, a file read in this session, command output actually seen, or a passing deterministic gate. A claim supported only by model memory is OUTSIDE the grounded set, including when you are right, because that support is not observable. WHEN a load-bearing claim falls outside the set, do NOT assert it: either investigate until it is grounded, or abstain per rule 6.

4. Status records provenance, never confidence. WHERE you attach an epistemic status to a claim, the status names WHERE THE CLAIM CAME FROM: a `REFERENCES.md` entry title, a file path plus line, or the gate output it came from. It SHALL NOT express a degree of certainty. Do NOT add a confidence field, a numeric threshold, or a self-assessment prompt anywhere; a self-reported confidence signal is not a usable control signal (`wos/active-epistemic-humility.md` Part 1.3). A status whose referent slot is empty is read as UNKNOWN, not as a weak yes.

5. Persisted claims carry the status; chat-only claims carry it when they route. Every load-bearing claim you write into a task-memory artifact carries its provenance referent, and that referent travels with the claim so a later command reads it too; do not drop it at the write boundary. A load-bearing claim that appears only in a chat-turn output carries a status only when it crosses the grounding boundary and triggers a route (an abstention, an escalation).

6. Abstain as a routed continuation, never a bare refusal. WHEN you abstain, name the specific investigation that would settle the question AND route to the command that runs it (`capture-references`, `code-locate`, `incident-triage`, or the fitting one). A withholding that stalls the work is invalid output. Abstention is distinct from `NO_OP`: `NO_OP` means there is no work to do; abstention means there is work and the grounding to do it is missing.

7. An unfired gate is not evidence. The absence of a fired check does not mean grounding existed. Do not read silence here as a pass.
### Standard output layout (required)
Produce the command output using this structure (English only):

### Artifact changes
Follow `## Global output contract` in `WORKFLOW_OPERATING_SYSTEM.md` for `APPLIED` / `PROPOSED` / `SKIP` rules. Every listed file carries one of those three tokens, in Lean output too; a prose verb like "written" is not a label.

### Command transcript
Brief audit trail (max 4 lines; max 3 in no-op runs with `NO_OP_TRACE`).

### Handoff
Use the adaptive ending format of `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract`. Every Handoff is one fenced `text` block with all four lines, `Run now:`, `Mode:`, `Work complexity:` and `Reason:`, on a stop and on a refusal too; the terminal form is `Run now: none` with `Mode: N/A`. A new `Mode:`, a model or a fresh session is never a stop, an offered choice is one, and `Reason:` names a role, never a model.
### Definition of done (command output)
- All resolved paths are explicit (project + task folder) and naming rules are satisfied.
- All five mandatory files are emitted with the full structure in `Files to generate`; missing or partial files invalidate the run (placeholders are required where facts are unknown, but the file itself must exist).
- `### Artifact changes` marks task-memory writes `APPLIED` in every mode (ADR-0199). A section this command does not own gets a `<!-- PROPOSED by <command>: ... -->` block for its owner instead (ADR-0034), in Agent mode too.
- The `Run now:` basename is a real command (`commands/<name>.md` or `commands/<name>/SKILL.md`; installed mode: the Fhorja inventory); invented names such as `task-plan` or `plan` are invalid output.
- `SOURCE_OF_TRUTH.md` carries `## Repositories` exactly when the Multi-repo handling rule requires it, one valid entry per repository, and omits it otherwise.
- Output ends with a complete `### Handoff` block per the adaptive format in `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract`. A response that ends after the mandatory file contents without a complete Handoff is invalid output.
- Optionally self-check K.2 substrate-write compliance via `bash scripts/verify-substrate-batch.sh <task-folder>` (headers, log and orphans in one call, ADR-0110) before finishing; not a gate.
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
Optimize for strong initialization, low ambiguity, resumability, and strict alignment with the official task repository structure.
