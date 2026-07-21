---
name: state-reconcile
description: Detect drift between TASK_STATE.md, other task-memory artifacts, and observable reality (code, tests, diff when provided), then propose the minimum set of updates so operational memory is trustworthy again. Use when TASK_STATE.md is stale or internally inconsistent after many edits, IMPLEMENTATION_PLAN.md or SLICES/*.md or slice status disagree with each other or with what was actually done, you need a full cross-check before trusting routing or before delivery prep, or the user explicitly wants a one-shot "repair state" pass. Also runs an opt-in read-only memory-lint mode that reports memory-hygiene issues (dead cross-links, orphaned slice files, stale facts) without writing. Do not use with no active task folder (run task-init first), when a small incremental update fits (use sync-task-state), when the need is fast routing on trusted artifacts (use what-next or resume-from-state), or for broad product discovery.
metadata:
  category: state-and-navigation
  primary-cursor-mode: Ask
  multi-repo-aware: false
  context-layers-consumed: [memory]
  context-layers-produced: [memory]
  tools: [Read, Write, Edit, Bash, Glob, Grep]
  x-wos-profiles: [core, full]
  provenance: first-party
  token-budget: 2700
  suggested-model: claude-opus-4-7
---
# state-reconcile

Act as a senior/staff engineering workflow reconciler for the active engineering task.

Goal:
Detect drift between `TASK_STATE.md`, other task-memory artifacts, and observable reality (code, tests, diff when provided), then propose the **minimum** set of updates so operational memory is trustworthy again.

Mandatory context bootstrap (before any output):
<!-- shared:mandatory-context-bootstrap -->
- Read these sections in `WORKFLOW_OPERATING_SYSTEM.md` first:
  - `## LLM execution contract`
  - `## Editor mode policy` (mode definitions only; the tool mapping table is lazy-loaded in `wos/editor-mode-mappings.md` and needed only for non-Claude-Code tools)
  - `## Global output contract` (including **Adaptive handoff** and **Mode selection rule**)
  - `## Cross-cutting workflow guardrails`
- **Bootstrap tiers (ADR-0025):** the light-weight commands (`branch-commit`, `what-next`, `where-we-at`, `slice-closure`, `compact-task-memory`) may skip `## Editor mode policy` good-fits lists and `## Cross-cutting workflow guardrails` sequencing heuristics, reading only the mode definitions and the core guardrail rules (routing memory, command-less input triage, official command names, material change, no-op). This reduces bootstrap from ~6,750 to ~3,500 tokens for these commands.
- Read additional sections only when relevant to this command's role.
- Read the `commands/` directory command inventory to ensure command names and availability are current.
- Align all routing recommendations and next-command suggestions with the current command set.
- **Official next-command names only:** every recommended next command (including the handoff `Run now` line) MUST be the basename of an existing `commands/<name>.md` file in this workflow repository. Never invent names.

Required inputs:
- active task folder path
- `TASK_STATE.md`
- `SOURCE_OF_TRUTH.md`
- `DECISIONS.md`
- `IMPLEMENTATION_PLAN.md`
- optional: `IMPACT_ANALYSIS.md`, `INVARIANTS_AND_NON_GOALS.md`, `TEST_STRATEGY.md`, `PR_PACKAGE.md`, `SLICES/*.md`
- optional: current branch, explicit git base branch, `git diff <base>...HEAD` or `--stat` (when drift vs code is in scope)
- last completed step from `TASK_STATE.md` (command + summary)
- optional: a memory-lint request (run the read-only memory-hygiene mode instead of drift repair)

Operating rules:
- Do not implement production code.
- **Handoff:** end with the adaptive `### Handoff` block per `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full).
- Do not silently change semantic intent in `DECISIONS.md`. Apply the decision-drift direction test: WHEN `TASK_STATE.md` misreports a decision that `DECISIONS.md` records unambiguously, that is stale memory; fix `TASK_STATE.md` here as a factual patch. Route to `decision-interview`, `resolve-contract-gaps`, or `contract-signoff` ONLY when `DECISIONS.md` itself is contradictory, contested, or contradicted by ground truth; list that drift as a **blocker** instead of rewriting `DECISIONS.md` here.
- Before producing output, verify reconciliation would materially change at least one artifact or expose a **blocking** drift that must be resolved before safe routing.
- If no material drift exists after cross-check, return **no-op** and route forward (often `what-next`); still emit `NO_OP_TRACE` in `### Command transcript`.
- Classify each drift line as one of: `BLOCKING` | `IMPORTANT` | `MINOR`.
- **Execution-versus-plan conformance (per ADR-0094).** For the specific question "did the executed slice set and the command sequence match the approved `IMPLEMENTATION_PLAN`", run `scripts/plan-adherence.py <task-dir>` and fold its verdict into the drift report: a slice-set FAIL (a planned slice never executed, or an executed slice never planned) is at least `IMPORTANT` drift; a command-sequence FAIL (implementation before an approval gate, a write after `task-close`) is `BLOCKING`. The script is read-only and trace-based (it reads the append-only `.wos/VERIFICATION_LOG.jsonl`); it is a closure or checkpoint tool, not a mid-slice check, and it needs slice-anchored completion evidence in `TASK_STATE.md` to compare against.
- Tie-breaker when it is unclear which artifact is wrong: prefer fixing `TASK_STATE.md` first, per the direction test above; touch `IMPLEMENTATION_PLAN.md` / slices only when the mismatch is factual, not a new scope request.
- **Official next-command names only:** every recommended next command (including inside `TASK_STATE.md` and the handoff `Run now` line) MUST be the basename of an existing `commands/<name>.md` file in this workflow repository. Never invent names.
- Set **work complexity** for the **next** real step from reconciled truth (definitions in `WORKFLOW_OPERATING_SYSTEM.md`). Never name model SKUs.

Optional mode: memory-lint (read-only) (per ADR-0053):
- Enter this mode only when the user asks for a memory-lint or memory-hygiene pass (not a drift repair). In this mode the command reports, it never writes.
- Run `scripts/memory-lint.sh <task-dir>` for the deterministic checks (dead relative cross-links across task and project memory, orphaned `SLICES/` files, LEARNINGS entry quality) and fold its findings in. Then add the check it cannot do: stale `TASK_STATE.md` facts (claims contradicted by other artifacts or long marked resolved).
- Report findings as advisory hygiene items. Do not classify them with the drift severities and do not propose `TASK_STATE.md` edits in this mode. The normal drift-repair mode above is what proposes fixes.
- Boundary: read-only. memory-lint never repairs (that is the normal mode) and never shrinks memory (that is `compact-task-memory`).
- Output shape: in this mode the Required output's Drift report and the Definition of done's drift-report condition do not apply. Emit a memory-lint findings list instead (per finding: issue type, file and location, evidence), plus an explicit no-op when there are zero findings.

Drift report (required content, place under `### Artifact changes` as the first block before file-level bullets):
- For each drift: field or artifact | what `TASK_STATE` or dependent file claims | ground truth (evidence pointer) | severity (`BLOCKING` | `IMPORTANT` | `MINOR`) | proposed fix (one line)

Required output:
1. Drift report (as specified above; compact)
2. Whether each target file needs update and why (or explicit no-op)
3. Exact `TASK_STATE.md` content or update block (or `TASK_STATE: NO_CHANGE`)
4. Exact updates for other touched task-memory files, or explicit `NO_CHANGE` per file
5. Recommended next command (must exist in `commands/*.md`; verify before output)
6. Recommended editor mode
7. Recommended work complexity (`LOW` | `MEDIUM` | `HIGH` | `N/A`) for that next step
8. Why this is the correct next step
9. What should explicitly not be done yet

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
- Start with the **Drift report** block (required).
- List each file in `my_work_tasks/` that would change, or `None`.
- For each file, mark `APPLIED` / `PROPOSED` / `SKIP` and follow the task-memory write policy in `WORKFLOW_OPERATING_SYSTEM.md` (default: `PROPOSED` in Ask/Plan unless this command explicitly requires `APPLIED`).

### Command transcript
<!-- shared:command-transcript-standard -->
Brief audit trail (max 4 lines; max 3 in no-op runs with `NO_OP_TRACE`).

### Handoff
<!-- shared:handoff-body -->
Use the adaptive ending format from `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full per session state).

### Definition of done (command output)
- Drift report exists with severities and evidence pointers.
- No silent `DECISIONS.md` semantic edits; blocking drift routes to the correct upstream command.
- `### Artifact changes` marks persistence as `APPLIED` only when actually writing in Agent mode; otherwise `PROPOSED`.
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
Restore trustworthy operational memory with the smallest safe patch set and clear next routing.

<!-- cache-breakpoint -->
