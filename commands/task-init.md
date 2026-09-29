---
name: task-init
description: Initialize the official task folder and base task memory inside projects/<client>__<project>/active/YYYY-MM-DD_<task-slug>/. Creates README.md, TASK_STATE.md, SOURCE_OF_TRUTH.md, DECISIONS.md, IMPLEMENTATION_PLAN.md; seeds from PROJECT_CHARTER.md when present; emits a multi-repo ## Repositories section in SOURCE_OF_TRUTH.md when 2+ repos are provided. Can seed from a vetted issue-tracker MCP item, gated and off by default. Use at the START of any engineering work in this workflow's repositories, before the first file is edited, including a one-line docs change or a typo fix: small scope is a reason to take the short pipeline, never a reason to skip the workflow. Do not use when the task folder already exists, when work should resume from existing TASK_STATE.md (use resume-from-state), or when the goal is only to update task memory after progress (use sync-task-state). For a brief with 3 or more independent sub-tasks, use task-init-fleet.
metadata:
  category: state-and-navigation
  primary-cursor-mode: Ask
  multi-repo-aware: true
  context-layers-consumed: [memory]
  context-layers-produced: [memory]
  tools: [Read, Write, Edit, Bash, Glob, Grep]
  x-wos-profiles: [minimal, core, full]
  provenance: first-party
  suggested-model: claude-opus-5-5
---
# task-init

Act as a senior/staff engineering workflow state initializer.

Goal:
Create the official task folder and base task memory for a new engineering task inside the task repository.

This command is mandatory at the start of every new task.

Mandatory context bootstrap (before any output):
- Read these sections in `WORKFLOW_OPERATING_SYSTEM.md` first:
  - `## LLM execution contract`
  - `## Editor mode policy`
  - `## Global output contract` (including **Adaptive handoff** and **Mode selection rule**)
  - `## Cross-cutting workflow guardrails`
  - `## Project-level memory`
- Read additional sections only when needed:
  - naming/path setup: `## Naming conventions`, `## Repository structure`
  - artifact requirements: `## Task files`, `## TASK_STATE policy` (per-file contract: load `wos/task-file-contracts.md`)
  - phase/entry ambiguity: `## Command roles` index (or `wos/command-roles.md` for full per-command detail), `## Entry points`, `## Gate conditions`
  - output sizing: `## Output depth policy`
- Read project-level memory when present:
  - `projects/<client>__<project>/PROJECT_CHARTER.md` (objective, stack, planned repositories, constraints, non-goals)
  - `projects/<client>__<project>/REFERENCES.md`: check that it EXISTS and link to it; do NOT read it here (ADR-0214).
  - Do NOT read the `projects/<client>__<project>/knowledge/` folder (the human knowledge layer, ADR-0054 and ADR-0055), and do NOT seed `SOURCE_OF_TRUTH.md` from it. It is never auto-loaded at `task-init`; its content reaches the AI only when a human pastes an excerpt into the task prompt.
  - When either file is missing, treat the project as not yet bootstrapped and warn the user (see Operating rules); do not block the task.
- Read `/USER_MEMORY.md` at the repo root when present (gitignored, ADR-0016); when absent, proceed silently (bootstrapping it is the user's job). Apply its preferences where they shape the proposed artifacts (language, response length, emoji policy, comment density), by the precedence in `wos/project-level-memory.md ### Layered precedence`.
- Read prior LEARNINGS when present (ADR-0017 consume side):
  - Resolve `scripts/rank-learnings.sh` against the WORKFLOW ROOT, the same root the two-root preflight found for the spec and `wos/` (the repository clone, or the installed docs directory, which ships this one script per ADR-0214), never against the task repository, which has no `scripts/`. When it is present in neither, say so in one `### Command transcript` line (`rank-learnings: not installed, prior LEARNINGS not consulted`) instead of skipping the step silently.
  - Run it as `rank-learnings.sh "<task keywords or objective>" <project-path>` to scan `projects/<client>__<project>/active/*/LEARNINGS.md` and the most recently archived tasks under `archive/`, ranking entries by recency plus tag and keyword overlap (ADR-0071); also read the cross-project learnings in `/USER_MEMORY.md`.
  - Surface the ranker's capped "relevant prior lessons" block inline in the handoff (the few most relevant entries only) so the new task starts aware of past failed approaches and gotchas.
  - Read-only: never compact, prune, or rewrite any `LEARNINGS.md` (per ADR-0017 item 6). When nothing is relevant, say nothing.
- Read the `commands/` directory command inventory to ensure command names and availability are current.
- Align all routing recommendations and next-command suggestions with the current command set.
- **Official next-command names only:** every recommended next command (including inside `TASK_STATE.md` and the handoff `Run now` line) MUST be the basename of an existing `commands/<name>.md` file in this workflow repository. Never invent names. The after-init route is set under Escalation assessment. One exception: `Run now: none` with `Mode: N/A` declares the chain ended with no honest next step, defined under `### Official command names (routing integrity)` (ADR-0126); use it only then, never to end a chain that has a real next step.

Required inputs:
- new task description / objective from the user
- client and project identifier (or enough context to derive `<client>__<project>`)
- task slug (or enough context to derive `YYYY-MM-DD_<task-slug>`)
- intended editor mode (Ask for drafting only, or Agent for actual file creation in the task repository)
- relevant source-of-truth pointers known so far (codebase path, branch, tickets, docs), if available
- optional: list of repositories for multi-repo tasks. Provide only when the task touches 2 or more product repositories that ship coordinated. Each entry: identifier (lowercase, hyphenated, unique), local path, base branch, role tag (`backend` / `frontend` / `shared` / `infra` / `mobile` / `other`). See the spec `## Multi-repo support (v1)` for the schema.
- optional: worktree isolation opt-in, for a task that needs its own working tree on a git-backed project; `task-workspace` provisions it (ADR-0074, spec `### Per-task worktree isolation (opt-in, v1)`).

Task repository structure to use:
- projects/<client>__<project>/active/YYYY-MM-DD_<task-slug>/

Mandatory files to create:
- README.md
- TASK_STATE.md
- SOURCE_OF_TRUTH.md
- DECISIONS.md
- IMPLEMENTATION_PLAN.md

Optional files must NOT be created yet unless the user explicitly asks:
- IMPACT_ANALYSIS.md
- INVARIANTS_AND_NON_GOALS.md
- TEST_STRATEGY.md
- PR_PACKAGE.md
- SLICES/

Naming rules: the task folder is `YYYY-MM-DD_<task-slug>` and the project folder `<client>__<project>`, both by the spec `## Naming conventions` (an English, lowercase, hyphenated slug specific enough to distinguish the work, never a vague one such as `fix-bug`).

Operating rules:
- **Two-root preflight (before creating the task folder; ADR-0129):** the **task repository** holds `projects/<client>__<project>/`; the **workflow root** is where `WORKFLOW_OPERATING_SYSTEM.md` and `wos/` resolved from for this run's own bootstrap (the canonical checkout, or an installed `workflow-docs/`). They coincide only in the maintainer's checkout, so NEVER require `commands/`, `scripts/`, or `wos/` inside the task repository. Resolve the task repository from source-of-truth pointers, the current working directory, or a user-supplied path; validate each root for what it should hold, then:
  - **STOP 1:** neither the spec nor `wos/` is reachable anywhere. No command can honor its mandatory bootstrap; name what is missing, ask for the correct path, create nothing.
  - **STOP 2:** the resolved TASK repository holds `commands/` and `wos/` but no `projects/`. That is the workflow checkout, not a task repository (the wrong-repo hazard this preflight exists for); name it, ask the user to confirm or supply the right path, create nothing there.
  - Record which workflow root was used in one `### Command transcript` line.
  - **Task folder already exists (the frontmatter's first do-not-use condition).** Create and overwrite
    nothing: emit `NO_OP_TRACE` naming the existing folder, then route to `where-we-at` when the work
    continues that task, or ask for a distinct slug when it is new work. An installed docs tree is the NORMAL mode, never reported as a degradation; when it carries no `scripts/`, `commands/_shared/substrate-digest-fallback.md` applies and the run says so.
- **Git-authority preflight (after the two-root preflight; detect and recommend only):** WHEN the active PRODUCT codebase path is known at init time (from source-of-truth pointers or a user-supplied path), run ONE check, `git -C <path> rev-parse --is-inside-work-tree` (a missing path counts as no git authority); when the path is not known, skip and leave the placeholder. On no git authority, record `Git status: no git authority at <path>` plus `Recommended action: git init -b main (requires human authorization)` in `SOURCE_OF_TRUTH.md ## Active codebase / repo`, mirror the action line into `TASK_STATE.md ## Risks to watch` in this run's batch, and cite it in the handoff. Task creation NEVER blocks on this check, and `git init` always waits for human authorization. Late-binding hook: any command that later promotes `## Active codebase / repo` from a vague pointer to a concrete path SHALL trigger this same one-call check at that moment.
- **Task branch (ADR-0233).** WHEN the run is attended with no `Operating mode: assisted`, no worktree is requested, and the product codebase has a remote, apply `wos/task-init-opt-ins.md ## Task branch`, which writes `Task branch:` and `Base branch:` (Ask and Plan only propose the switch). Otherwise create no branch.
- **Assumptions (ADR-0233).** In an attended run with no `Operating mode: assisted`, list under `### Assumptions` each decision the brief lacks and the option the chain will take, or `None.`, and do not wait: the command that needs it records a provisional `### P-N`; an answer arriving mid-chain replaces it.
- **Opt-in steps (lazy; `wos/task-init-opt-ins.md`).** Read it and apply the matching rule when the harness restricts the write root, the user requests worktree isolation, or the task is product work on a project with a notable feature set.
- Do not implement production code.
- **Handoff:** end with the adaptive `### Handoff` block per `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full).
- **Substrate write protocol (ADR-0034, K.2; genesis via ADR-0110 `batch`).** MANDATORY on TASK_STATE.md, DECISIONS.md, IMPLEMENTATION_PLAN.md, SOURCE_OF_TRUTH.md (not README.md). Header IMMEDIATELY above each created H2, no blank line: `<!-- wos:write owner=task-init section='## X' run_id=<ULID> ts=<ISO-8601-ms-Z> reason=task-init-<slug> mode=applied -->`. `reason` <= 80 chars. Same `run_id`+`ts` on all four files. Then one `bash scripts/emit-substrate-write.sh batch --owner task-init --file <FILE> --reason task-init-<slug> --mode applied --task-root <task-folder> --run-id <id>` per file. Never `apply`. COUNT 0: header not previous line or missing `owner=task-init `.
  FORBIDDEN: half-compliant pattern (JSONL emitted but inline header omitted on any section, OR `sha_after` set to `null` on any applied write).
- Do not invent missing facts, decisions, or constraints.
- If required initialization context is missing, ask only the minimum targeted questions needed to create the task safely.
- **No human respondent (unattended or fleet-dispatched run, or a background session failing the ADR-0237 test in `wos/cross-cutting-workflow-guardrails.md ### Unattended sessions`):** do NOT self-answer the initialization questions. Seed every field the dispatching brief supplies, recording each with the provenance note "from the dispatching brief"; fill the rest with the explicit placeholders below; note in `### Command transcript` that the run was unattended; and never self-lock the residue (the open fields stall for the next human session).
- **Escalation assessment (ADR-0184).** After creating the task folder the pipeline is `task-init` -> `implementation-plan` -> `approve-plan` -> `implement-approved-slice` -> `branch-commit` (-> `pr-package --apply` in an attended chain on a task branch), with the `minimal` profile suggested. Add a command only when a disqualifier below fires, and NAME the fired disqualifier on the `Escalations:` line of `## Recommended pipeline`. Uncertainty is not a disqualifier: "I am not sure" adds nothing, only a signal you can point at does. An escalation with no named disqualifier is invalid output.
  - Add `impact-analysis` before the plan when the scope needs more than one sentence to state, OR the change touches 5 or more files.
  - Add `decision-interview` when a decision the prompt does not contain is required before the first line of code, OR the change spans multiple packages or adds an external service dependency.
  - Add `invariants-and-non-goals`, `test-strategy` and `review-hard`, and suggest `Operating mode: strict`, when the surface is auth, payments, compliance, PII, or multi-tenant isolation. Categorical, not a judgment call.
  When no disqualifier fires AND the unattended bullet did not fire, that pipeline binds (ADR-0159), it is not an offer. Unless the one-slice route below applies, the Handoff is `Run now: implementation-plan`, `Mode: Agent`, in every mode: the five files are written, not proposed. When the unattended bullet fired, do not bind that pipeline. The user can override by choosing a different command. When the task description already contains locked decisions, do not re-ask them later.
- **State the escalation set in the handoff:** name every disqualifier that fired, or say none did, plus the sentence-length scope.
- **One-slice route (ADR-0225, ADR-0239).** Take it only when every condition holds, each written with its evidence on a `Route: one-slice` line in `## Recommended pipeline`: (1) no escalation fired, the run is attended, and no `Operating mode: strict` is declared; (2) the change fits one sentence and touches at most two files the brief names; (3) `DECISIONS.md ## Locked decisions` stays empty and every `### Assumptions` entry is `Impact: normal` on a run with a `Task branch:` line; write each in the same batch as a `### P-N` under `## Provisional decisions` (the draft PR lists it), and it fires no `decision-interview`, while an `Impact: high` one keeps the full path; and `scripts/check-doc-sync.sh` resolves in the workflow root (the check that replaces the plan review). A condition you cannot show has failed: doubt keeps the full path, since this route drops a review. On the route, write in the same batch the one slice in `## Slices` (`Scope:` the named files, `Depends-on: none`, `Status: approved`, `Work complexity: LOW`, `Decision-ref:` `rests on provisional P-N` per P-N, else `none (<why>)`, exit criterion `WHEN the slice diff is complete, check-doc-sync.sh --against HEAD SHALL exit 0`), a `## Approval log` line `<date>: APPROVED (one-slice route); check-doc-sync.sh --against HEAD replaces the blinded review.`, and `## Current phase` `implementation (plan APPROVED, one-slice route)`: both lock signals `implement-approved-slice` reads. Then run `scripts/check-plan-coverage.sh <task-folder>`; any exit but 0 ends the route and hands off to `implementation-plan`. Otherwise hand off `Run now: implement-approved-slice`, `Mode: Agent`. `implementation-plan` and `approve-plan` are skipped on this route only.
- Use explicit placeholders such as:
  - [unknown yet]
  - [to be confirmed]
  - [not decided yet]
- Treat code and existing task context as the strongest source of truth. Keep the files concise and operational: a usable foundation, not a solved task.
- Project-level memory handling:
  - When `projects/<client>__<project>/PROJECT_CHARTER.md` exists, seed `SOURCE_OF_TRUTH.md` automatically from it (stack, repositories, constraints, non-goals, default workspace) instead of re-asking the user.
  - When `projects/<client>__<project>/REFERENCES.md` exists, link to it from `SOURCE_OF_TRUTH.md` under `## Project-level memory` so the new task can consume external references without duplicating them.
  - When the project folder exists but `PROJECT_CHARTER.md` is missing, warn the user with a one-line note ("project not bootstrapped: recommended to run `project-bootstrap` first to capture project-level context") and continue with the task using user-supplied inputs and explicit placeholders. Do not block the task.
  - When `projects/<client>__<project>/` itself does not exist, recommend running `project-bootstrap` before proceeding; if the user insists on starting the task immediately, create the project folder ad-hoc with only the task subtree and emit the same warning. When that creates `projects/` itself, apply `### Task memory stays out of git` below.
  - **Ignore check (ADR-0223 D-2).** WHEN `projects/` existed before this run, run `git -C <task repository> check-ignore -q projects/<client>__<project>/` once. Exit 1 means git would track the task memory: print one `### Command transcript` line, `projects/ is not ignored in <task repository>: add projects/.gitignore holding '*'; if task files are already committed, also run git rm -r --cached projects`. Exit 0 (ignored) and 128 (not a git repository) print nothing. Warn on every run and never write the fix yourself.
  - When `projects/<client>__<project>/BRIEF.md` exists (a transient intake brief written by `problem-framing`, ADR-0058), consume it: seed the task description, `SOURCE_OF_TRUTH.md`, and the `## Requested deliverables` ledger from its <!-- count:sections-brief -->5<!-- /count --> fields (problem statement, success criteria, non-goals, recommended approach, named deliverables), then MOVE `BRIEF.md` into the new task folder (so a stale brief never lingers at the project root). The brief is task-scoped, not durable project memory; do not leave it at the root after consuming it.
  - **MCP-sourced seed (gated, opt-in; `wos/mcp-capability-routing.md`, read only when this fires):** WHEN the user references an issue-tracker item AND a vetted issue-tracker MCP is connected, pull it: title and body seed the task description and the `## Requested deliverables` ledger (ADR-0056); identifier and URL go to `SOURCE_OF_TRUTH.md` as a `source: mcp` provenance pointer. A failed pull follows that block's failure policy, never a fabricated item. With no MCP connected this bullet does not apply.
- Deliverable-ledger seeding (per ADR-0056): seed the `## Requested deliverables` section in `TASK_STATE.md` from the user's brief (or from the `Named deliverables` field of a consumed `BRIEF.md` when present). List one row per concrete deliverable the user named (an artifact to produce or an input to analyze), tagged `in-scope`, not every implied sub-task. When the brief names no concrete deliverable, write the section with a single `- none named` row rather than omitting it. WHEN a ledger row is user-facing product content or a new user-facing surface, the row SHALL carry the tag `user-facing-content` or `new-user-facing-surface` (ADR-0091) next to its in-scope tag, by the ADR-0103 tagging test in the `## Requested deliverables` annotation of `templates/TASK_STATE.template.md`.
- Multi-repo handling: if the user provided 2 or more repositories (directly or inherited from `PROJECT_CHARTER.md`), generate a `## Repositories` section in `SOURCE_OF_TRUTH.md` per the schema in the spec `## Multi-repo support (v1)`. Validate that identifiers are lowercase, hyphenated, and unique within the task. If only 1 repo (or no repo) is provided, omit the `## Repositories` section entirely; single-repo tasks continue using the existing `active codebase / repo` field unchanged.

Files to generate:

1. README.md
Must include:
- task name
- project name
- short task summary
- objective
- current status
- `## Brief`: the user's brief verbatim (in an unattended run, the dispatching brief; with a consumed `BRIEF.md`, a pointer to it), so a provisional decision can quote it and `approve-plan`'s blinded review can resolve that quote

2. TASK_STATE.md
Must use this exact structure:

Section annotations (what each section is for, who owns it, how it is rebuilt) live in
`templates/TASK_STATE.template.md`. Read that file when seeding the artifact. The
<!-- count:sections-task-state -->20<!-- /count -->-section structure itself is below and is normative for the section names and order.

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
- Command: (official basename only, must match `commands/<name>.md` in this repo, e.g. `impact-analysis`, not `task-plan`)
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
Must include, under the canonical H2 names of the `wos/substrate-peers.md` SOURCE_OF_TRUTH rows (one name for a section task-init creates and a later command owns):
- `## Active codebase / repo` (carries the Git-authority preflight's `Git status:` and `Recommended action:` lines when that preflight found no git authority)
- `## Active branch`, if known
- `## Main files in scope`, if known (code-locate owns this section once it names concrete files)
- `## Tickets / docs / Figma / links`: tickets, docs and links, plus the one-line pointer `Requested deliverables: see TASK_STATE.md ## Requested deliverables` (ADR-0056; the ledger is not duplicated here)
- `## Official external docs`: official references to use before making decisions
- `## Repositories`, only under the Multi-repo handling rule above
- optional `## Project-level memory` section listing relative pointers to project-level files when present:
  - `../../PROJECT_CHARTER.md` (high-level project context)
  - `../../REFERENCES.md` (external references with freshness metadata)
  Omit this section entirely when the project was not bootstrapped (no `PROJECT_CHARTER.md` at the project root).

4. DECISIONS.md
Must include only approved decisions, under the exact header `## Locked decisions`; when none are approved yet, say so there ("None locked in this task."). On the one-slice route, add its `## Provisional decisions`.

5. IMPLEMENTATION_PLAN.md
Must include, under the canonical H2 names `implementation-plan` later owns:
- `## Target behavior`
- `## Current gaps`
- `## Constraints` (known constraints)
- `## Slices` (initial expected phases or slices)
- `## Open questions or approvals still needed` (unknowns that block safe planning)
- `## Approval log`, on the one-slice route only (see Escalation assessment)

Required output:
1. Resolved project folder name
2. Resolved task folder name
3. Full task path to create
4. Why this is a create operation
5. Exact content for:
   - README.md
   - TASK_STATE.md
   - SOURCE_OF_TRUTH.md
   - DECISIONS.md
   - IMPLEMENTATION_PLAN.md
6. `### Assumptions` and the `Task branch:` value
7. Recommended next command (must exist as `commands/<name>.md` or `commands/<name>/SKILL.md`; verify against directory listing before output)
8. Recommended editor mode
9. Why that is the correct next step

### MCP-sourced seed (gated, opt-in)
WHEN the MCP-sourced seed bullet above fires, read `wos/mcp-capability-routing.md` first and apply its trust gate, capability routing, failure policy and ingest mapping exactly as written.

### Task memory stays out of git
<!-- shared:projects-ignore -->
WHEN this run creates the `projects/` directory itself in the task repository, it writes `projects/.gitignore` in the same batch, holding the single line `*` (ADR-0223). That line ignores everything under `projects/`, the file included, so task memory stays out of the product repository's history without touching a file the user owns. List it `APPLIED` in `### Artifact changes`.
- Never edit the repository's own `.gitignore`.
- Never write `projects/.gitignore` into a `projects/` that already exists. A user who deleted it chose to track the tree.
- Write it outside a git repository too, so a later `git init` inherits the rule.
### Substrate digest fallback
<!-- shared:substrate-digest-fallback -->
**Digest fallback when the canonical helper is unreachable.** `sha_of_section` extracts a section's body with `awk` and pipes it to `shasum -a 256`. A run executing inside a permission boundary that admits `shasum` but refuses `awk` and `sed` cannot invoke that helper, and MUST NOT reimplement it: an `awk` or `sed` program operand can call `system()` and write files, so a boundary that refuses those verbs refuses them for a reason. Assume the helper is unreachable whenever the workflow repository's `scripts/` directory is not readable from the working directory.

WHERE the canonical per-section digest helper is unreachable, the write SHALL use a whole-file SHA-256 and SHALL declare the reduced scope:

```bash
# One call per file. `shasum -a 256 <file>` needs no extraction step, so no
# refused verb is involved. Read the hash (the first field) out of the output;
# do not pipe it through `cut` or `awk` to trim it.
shasum -a 256 TASK_STATE.md
```

Then add `"sha_scope":"file"` to that JSONL line, so a validator distinguishes a file digest from a section digest instead of inferring it. Everything else about the protocol is unchanged: the transaction header still goes above the section heading, and there is still exactly one JSONL line per section write.

Do NOT rebuild the helper by writing each section out as its own file so it can be hashed separately. That workaround is coherent and it is what this rule exists to prevent: a 2026-08-04 run wrote 31 numbered section fragments to compute per-section digests by hand, spent the whole run doing it, and produced no product code.

What the fallback costs, stated so the trade is explicit rather than discovered later: the digest chain exists to detect an unlogged change to a SECTION. At file scope, two sections written in the same run share a digest, so the chain detects tampering with the file without attributing it to a section. That is a declared reduction in resolution, not a silent one, which is why the `sha_scope` field is mandatory rather than optional.
### Claim grounding (active epistemic humility)
<!-- shared:claim-grounding -->
**Claim grounding (active epistemic humility).** This block governs what you may assert and how you record it. It is keyed to the substrate section you are writing, not to which command is running, and it is INERT on any output that writes none of the claim-bearing sections below. Full contract and rationale: `wos/active-epistemic-humility.md`.

1. When this applies. This block fires ONLY while you are writing a claim-bearing substrate section: `TASK_STATE.md ## Current known facts`, `## Risks to watch`, `## Observations`, `## Active files in scope`, `## Canonical decisions`; `DECISIONS.md ## Locked decisions`; `IMPLEMENTATION_PLAN.md ## Current gaps`, `## Risks and mitigations`; `IMPACT_ANALYSIS.md`; `EXTERNAL_RESEARCH.md`; `REFERENCES.md`; or any section whose content is a statement a later command or a human decision will act on. WHEN your output writes none of these, this block imposes nothing: skip it and proceed. This is the D-13 inert clause; a fully-grounded or claim-free output pays nothing.

2. The unit is the load-bearing claim. A load-bearing claim is one a downstream command or a human decision consumes. A passing aside is not load-bearing; a statement someone will act on is. Apply the rest of this block per load-bearing claim, not per sentence.

3. Ground it or abstain. Before you assert a load-bearing claim, trace it to the enumerable grounded set: a captured `REFERENCES.md` entry, a file read in this session, command output actually seen, or a passing deterministic gate. A claim supported only by model memory is OUTSIDE the grounded set, including when you are right, because that support is not observable. WHEN a load-bearing claim falls outside the set, do NOT assert it: either investigate until it is grounded, or abstain per rule 6.

4. Status records provenance, never confidence. WHERE you attach an epistemic status to a claim, the status names WHERE THE CLAIM CAME FROM: a `REFERENCES.md` entry title, a file path plus line, or the gate output it came from. It SHALL NOT express a degree of certainty. Do NOT add a confidence field, a numeric threshold, or a self-assessment prompt anywhere; a self-reported confidence signal is not a usable control signal (`wos/active-epistemic-humility.md` Part 1.3). A status whose referent slot is empty is read as UNKNOWN, not as a weak yes.

5. Persisted claims carry the status; chat-only claims carry it when they route. Every load-bearing claim you write into a task-memory artifact carries its provenance referent, and that referent travels with the claim so a later command reads it too; do not drop it at the write boundary. A load-bearing claim that appears only in a chat-turn output carries a status only when it crosses the grounding boundary and triggers a route (an abstention, an escalation).

6. Abstain as a routed continuation, never a bare refusal. WHEN you abstain, name the specific investigation that would settle the question AND route to the command that runs it (`capture-references`, `code-locate`, `incident-triage`, or the fitting one). A withholding that stalls the work is invalid output. Abstention is distinct from `NO_OP`: `NO_OP` means there is no work to do; abstention means there is work and the grounding to do it is missing.

7. An unfired gate is not evidence. The absence of a fired check does not mean grounding existed. Do not read silence here as a pass.
### Standard output layout (required)
<!-- shared:standard-output-layout -->
Produce the command output using this structure (English only):

### Artifact changes
<!-- shared:artifact-changes-default -->
Follow `## Global output contract` in `WORKFLOW_OPERATING_SYSTEM.md` for `APPLIED` / `PROPOSED` / `SKIP` rules. Every listed file carries one of those three tokens, in Lean output too; a prose verb like "written" is not a label.

### Command transcript
<!-- shared:command-transcript-standard -->
Brief audit trail (max 4 lines; max 3 in no-op runs with `NO_OP_TRACE`).

### Handoff
<!-- shared:handoff-body -->
Use the adaptive ending format of `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract`. Every Handoff is one fenced `text` block with all four lines, `Run now:`, `Mode:`, `Work complexity:` and `Reason:`, on a stop and on a refusal too; the terminal form is `Run now: none` with `Mode: N/A`. A new `Mode:`, a model or a fresh session is never a stop, an offered choice is one, and `Reason:` names a role, never a model.
### Definition of done (command output)
- All resolved paths are explicit (project + task folder) and naming rules are satisfied.
- All five mandatory files (`README.md`, `TASK_STATE.md`, `SOURCE_OF_TRUTH.md`, `DECISIONS.md`, `IMPLEMENTATION_PLAN.md`) are emitted with the full structure specified in `Files to generate`; missing or partial files invalidate the run (placeholders are required where facts are unknown, but the file itself must exist).
- `### Artifact changes` marks task-memory writes `APPLIED` in every mode (ADR-0199). A section this command does not own gets a `<!-- PROPOSED by <command>: ... -->` block for its owner instead (ADR-0034): that is ownership, not a mode gate, and it holds in Agent mode too.
- The basename in the `Run now:` line corresponds to a real file in `commands/<name>.md`; invented names such as `task-plan` or `plan` are invalid output.
- `SOURCE_OF_TRUTH.md` carries `## Repositories` exactly when the Multi-repo handling rule requires it, one valid entry per repository, and omits it otherwise.
- Output ends with a complete `### Handoff` block per the adaptive format in `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract`. A response that ends after the mandatory file contents without a complete Handoff is invalid output.
- Optionally self-check K.2 substrate-write compliance via `bash scripts/verify-substrate-batch.sh <task-folder>` (headers, log and orphans in one call, ADR-0110) before finishing; not a gate.
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
Optimize for strong initialization, low ambiguity, resumability, and strict alignment with the official task repository structure.
