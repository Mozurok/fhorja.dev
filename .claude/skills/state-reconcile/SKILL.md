---
name: state-reconcile
description: |-
  Detect drift between TASK_STATE.md, other task-memory artifacts, and observable reality (code, tests, diff when provided), then propose the minimum set of updates so operational memory is trustworthy again. Use when TASK_STATE.md is stale or internally inconsistent after many edits, IMPLEMENTATION_PLAN.md or SLICES/*.md or slice status disagree with each other or with what was actually done, you need a full cross-check before trusting routing or before delivery prep, or the user explicitly wants a one-shot "repair state" pass. Also runs an opt-in read-only memory-lint mode that reports memory-hygiene issues (dead cross-links, orphaned slice files, stale facts) without writing. Do not use with no active task folder (run task-init first), when a small incremental update fits (use sync-task-state), when the need is fast routing on trusted artifacts (use what-next or resume-from-state), or for broad product discovery.
metadata:
  category: "state-and-navigation"
  primary-cursor-mode: "Ask"
  multi-repo-aware: "false"
  context-layers-consumed: "memory"
  context-layers-produced: "memory"
  tools: "Read, Write, Edit, Bash, Glob, Grep"
  x-wos-profiles: "core, full"
  provenance: "first-party"
  suggested-model: "claude-opus-5-5"
---

Act as a senior/staff engineering workflow reconciler for the active engineering task.

Goal:
Detect drift between `TASK_STATE.md`, other task-memory artifacts, and observable reality (code, tests, diff when provided), then propose the **minimum** set of updates so operational memory is trustworthy again.

Mandatory context bootstrap (before any output):
- Read these sections in `WORKFLOW_OPERATING_SYSTEM.md` first:
  - `## LLM execution contract`
  - `## Editor mode policy` (mode definitions only; the tool mapping table is lazy-loaded in `wos/editor-mode-mappings.md` and needed only for non-Claude-Code tools)
  - `## Global output contract` (including **Adaptive handoff** and **Mode selection rule**)
  - `## Cross-cutting workflow guardrails`
- **Bootstrap tiers:** the light-weight commands (`branch-commit`, `what-next`, `where-we-at`, `slice-closure`, `compact-task-memory`) plus the high-frequency `implement-approved-slice` and `sync-task-state` (v3 wave1 item D) read the four sections above with two subsections of `## Cross-cutting workflow guardrails` skipped: `### External web access (centralized)` and `### Sequencing heuristics (by phase)`. Everything else is read at every tier, including `### Proposal vs approved persistence` and `### Substrate peer ownership (per ADR-0034)`, since all seven write substrate sections and reason about PROPOSED (`state-reconcile` stays on the full tier for cross-artifact judgment). The full tier is measured at 11678 tokens, the four always-read sections combined; the two skipped subsections are 1,035 of those (measured 2026-09-24), so the reduced tier is about 10,643. The leaf-reviewer tier (`verify-against-rubric`, ADR-0226) reads only `## Global output contract`, measured at 4841 tokens, plus its rubric.
- **Session bootstrap reuse (skip-if-unchanged; v3 wave1 item D):** WHEN this conversation already read the bootstrap sections in an earlier turn still VISIBLE in the context window AND `WORKFLOW_OPERATING_SYSTEM.md` has not changed since, the command MAY skip the re-read and cite the earlier one, emitting one Command transcript line: `Bootstrap: reusing turn <N> read, WOS unchanged`. Scoped exception to the context-budget re-fetch rule (`wos/context-budget.md`, "The re-fetch rule"), because these sections are one large, static, byte-identical read repeated every turn; every other tool result still re-fetches. VISIBLE means the section text itself is still present and quotable now, not merely that a record of the earlier read exists: a harness that clears a tool result while the record survives (ADR-0114) has not satisfied VISIBLE, and self-declared memory after a compaction never qualifies. A stateless-per-turn harness is excluded. The transcript line is mandatory; a silent skip is invalid output.
- **Resolving `WORKFLOW_OPERATING_SYSTEM.md` and a relative `wos/<topic>.md`.** Both resolve the same way: try the canonical workflow repository root FIRST, then the installed docs directory (`~/.claude/workflow-docs/` or `~/.cursor/workflow-docs/`, the spec at that root and topics under its `wos/`). Repository first, because the installed copy is a snapshot no sync prunes; preferring it would hide a `wos/` edit from every command until a reinstall. Name the resolved root in `### Command transcript`, and say so explicitly when NEITHER resolved rather than continuing silently, since several of these loads are MANDATORY.
- Read additional sections only when relevant to this command's role.
- Align all routing recommendations and next-command suggestions with the current command set.
- **Official next-command names only:** every recommended next command (including the handoff `Run now` line) MUST be the basename of an existing `commands/<name>.md` file in this workflow repository. Never invent names. One exception: `Run now: none` with `Mode: N/A` declares the chain ended with no honest next step, defined under `### Official command names (routing integrity)` (ADR-0126); use it only then, never to end a chain that has a real next step.

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
- **Execution-versus-plan conformance (per ADR-0094).** For the specific question "did the executed slice set and the command sequence match the approved `IMPLEMENTATION_PLAN`", run `scripts/plan-adherence.py <task-dir>` and fold its verdict into the drift report: a slice-set FAIL (a planned slice never executed, or an executed slice never planned) is at least `IMPORTANT` drift; a command-sequence FAIL (implementation before an approval gate, a write after `task-close`) is `BLOCKING`. A slice-set `UNKNOWN` is NOT drift: it means the task offers no executed signal at all to compare against, so record it as a memory-hygiene observation (usually slice files with no `Status:` line) and move on. The script reads three executed signals, `SLICES/*.md` status lines first, then `TASK_STATE.md ### Completed`, then the audit log; the trace alone is never enough, because `implement-approved-slice` closes LOW and MEDIUM slices inline and that path writes no audit line. It also reports halted or de-scoped units and units the plan never approved on their own lines, and neither counts as drift. Read-only, and a closure or checkpoint tool rather than a mid-slice check. Resolve `scripts/plan-adherence.py` against the WORKFLOW ROOT (the clone, or the installed docs directory, which ships it per ADR-0224), never against the task repository. Its exit 2 (`not checked, no IMPLEMENTATION_PLAN.md`), or the script in neither root, means conformance was NOT checked: say so in `### Command transcript` and never report the task as conformant.
- Tie-breaker when it is unclear which artifact is wrong: prefer fixing `TASK_STATE.md` first, per the direction test above; touch `IMPLEMENTATION_PLAN.md` / slices only when the mismatch is factual, not a new scope request.
- **Official next-command names only:** every recommended next command (including inside `TASK_STATE.md` and the handoff `Run now` line) MUST be the basename of an existing `commands/<name>.md` file in this workflow repository. Never invent names.
- Set **work complexity** for the **next** real step from reconciled truth (definitions in `WORKFLOW_OPERATING_SYSTEM.md`). Never name model SKUs.

Optional mode: memory-lint (read-only) (per ADR-0053):
- Enter this mode only when the user asks for a memory-lint or memory-hygiene pass (not a drift repair). In this mode the command reports, it never writes.
- Run `scripts/memory-lint.sh <task-dir>` for the deterministic checks (dead relative cross-links across task and project memory, orphaned `SLICES/` files, LEARNINGS entry quality) and fold its findings in. Resolve `scripts/memory-lint.sh` against the WORKFLOW ROOT (the clone, or the installed docs directory, which ships it per ADR-0224); when it is in neither, or its last line is `MEMORY-LINT: not scanned`, say in `### Command transcript` that the deterministic checks did not run, and never emit the zero-findings no-op for them. Then add the check it cannot do: stale `TASK_STATE.md` facts (claims contradicted by other artifacts or long marked resolved).
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
5. Recommended next command (must exist as `commands/<name>.md` or `commands/<name>/SKILL.md`; verify before output)
6. Recommended editor mode
7. Recommended work complexity (`LOW` | `MEDIUM` | `HIGH` | `N/A`) for that next step
8. Why this is the correct next step
9. What should explicitly not be done yet

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
- Start with the **Drift report** block (required).
- List each file in the task repository that would change, or `None`.
- For each file, mark `APPLIED` / `PROPOSED` / `SKIP` and follow the task-memory write policy in `WORKFLOW_OPERATING_SYSTEM.md` (task memory is `APPLIED` in every mode; a section this command does not own gets a `<!-- PROPOSED by <command>: ... -->` block for its owner, ADR-0034).

### Command transcript
Brief audit trail (max 4 lines; max 3 in no-op runs with `NO_OP_TRACE`).

### Handoff
Use the adaptive ending format from `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full per session state). Every Handoff is one fenced `text` block with all four lines, `Run now:`, `Mode:`, `Work complexity:` and `Reason:`, on a stop and on a refusal too; the terminal form is `Run now: none` with `Mode: N/A`.

### Definition of done (command output)
- Drift report exists with severities and evidence pointers.
- No silent `DECISIONS.md` semantic edits; blocking drift routes to the correct upstream command.
- `### Artifact changes` marks task-memory writes `APPLIED` in every mode (ADR-0199). A section this command does not own gets a `<!-- PROPOSED by <command>: ... -->` block for its owner instead (ADR-0034): that is ownership, not a mode gate, and it holds in Agent mode too.
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
Restore trustworthy operational memory with the smallest safe patch set and clear next routing.
