---
name: resume-from-state
description: Resume the task from TASK_STATE.md and the linked artifacts, reconstruct the current truth, and determine the best next step. Brings back full context after a session break or a chat switch. Also owns the explicit --lost-session recovery mode for when the transcript itself is lost: a capped, read-only sweep of the harness session files that proposes context with provenance. Use when work resumes in a new chat, or the task was paused and needs fast reconstruction. Do not use for a brand-new task (use task-init), when the need is only to sync memory after progress (use sync-task-state), or when the artifacts are stale or contradictory and must be corrected first (use sync-task-state for narrow drift, state-reconcile when drift is wide).
metadata:
  category: state-and-navigation
  primary-cursor-mode: Ask
  multi-repo-aware: false
  context-layers-consumed: [memory, history]
  context-layers-produced: [memory]
  tools: [Read, Write, Edit, Bash, Glob, Grep]
  x-wos-profiles: [core, full]
  provenance: first-party
  suggested-model: claude-haiku-4-5
---
# resume-from-state

Act as a senior/staff engineer resuming work from task memory for the active engineering task.

Goal:
Resume the task from TASK_STATE.md and linked task artifacts, reconstruct the current truth, and determine the best next step.

Mandatory context bootstrap (before any output):
<!-- shared:mandatory-context-bootstrap -->
- Read these sections in `WORKFLOW_OPERATING_SYSTEM.md` first:
  - `## LLM execution contract`
  - `## Editor mode policy` (mode definitions only; the tool mapping table is lazy-loaded in `wos/editor-mode-mappings.md` and needed only for non-Claude-Code tools)
  - `## Global output contract` (including **Adaptive handoff** and **Mode selection rule**)
  - `## Cross-cutting workflow guardrails`
- **Bootstrap tiers:** the light-weight commands (`branch-commit`, `what-next`, `where-we-at`, `slice-closure`, `compact-task-memory`) plus the high-frequency `implement-approved-slice` and `sync-task-state` (v3 wave1 item D) read the four sections above with two subsections of `## Cross-cutting workflow guardrails` skipped: `### External web access (centralized)` and `### Sequencing heuristics (by phase)`. Everything else is read at every tier, including `### Proposal vs approved persistence` and `### Substrate peer ownership (per ADR-0034)`, since all seven write substrate sections and reason about PROPOSED (`state-reconcile` stays on the full tier for cross-artifact judgment). The full tier is measured at 12109 tokens, the four always-read sections combined; the two skipped subsections are 1,034 of those (measured 2026-09-28), so the reduced tier is about 11,074. The leaf-reviewer tier (`verify-against-rubric`, ADR-0226) reads only `## Global output contract`, measured at 5215 tokens, plus its rubric.
- **Session bootstrap reuse (skip-if-unchanged; v3 wave1 item D):** WHEN this conversation already read the bootstrap sections in an earlier turn still VISIBLE in the context window AND `WORKFLOW_OPERATING_SYSTEM.md` has not changed since, the command MAY skip the re-read and cite the earlier one, emitting one Command transcript line: `Bootstrap: reusing turn <N> read, WOS unchanged`. Scoped exception to the context-budget re-fetch rule (`wos/context-budget.md`, "The re-fetch rule"), because these sections are one large, static, byte-identical read repeated every turn; every other tool result still re-fetches. VISIBLE means the section text itself is still present and quotable now, not merely that a record of the earlier read exists: a harness that clears a tool result while the record survives (ADR-0114) has not satisfied VISIBLE, and self-declared memory after a compaction never qualifies. A stateless-per-turn harness is excluded. The transcript line is mandatory; a silent skip is invalid output.
- **Resolving `WORKFLOW_OPERATING_SYSTEM.md` and a relative `wos/<topic>.md`.** Both resolve the same way: try the canonical workflow repository root FIRST, then the installed docs directory (`~/.claude/workflow-docs/` or `~/.cursor/workflow-docs/`, the spec at that root and topics under its `wos/`). Repository first, because the installed copy is a snapshot no sync prunes; preferring it would hide a `wos/` edit from every command until a reinstall. Name the resolved root in `### Command transcript`, and say so explicitly when NEITHER resolved rather than continuing silently, since several of these loads are MANDATORY.
- Read additional sections only when relevant to this command's role.
- Align all routing recommendations and next-command suggestions with the current command set.
- **Official next-command names only:** every recommended next command (including the handoff `Run now` line) MUST be the basename of an existing `commands/<name>.md` file in this workflow repository. Never invent names. One exception: `Run now: none` with `Mode: N/A` declares the chain ended with no honest next step, defined under `### Official command names (routing integrity)` (ADR-0126); use it only then, never to end a chain that has a real next step.

Required inputs:
- active task folder path
- TASK_STATE.md
- SOURCE_OF_TRUTH.md
- DECISIONS.md
- IMPLEMENTATION_PLAN.md
- other relevant task artifacts if present
- optional: `--lost-session` to recover working context when the session transcript itself is lost (per ADR-0113; see the Lost-session recovery mode in Operating rules)

Task repository files to update:
- none by default
- recommend sync-task-state explicitly if the state is stale, contradictory, or incomplete

Operating rules:
- Do not implement code yet.
- **Workspace path resolution (before reading any files):** the task folder (under `projects/<client>__<project>/active/...`) may live in a Fhorja/task-memory repo that is separate from the product codebase. Before reading product code or assuming file locations:
  1. Read `SOURCE_OF_TRUTH.md` in the task folder for `## Active codebase / repo` (what `task-init` emits for a single-repo task), `## Repositories` (emitted only for 2 or more repos), or a legacy `## Product workspace` heading. Checking only the last two finds nothing on an ordinary single-repo task, which is most of them.
  2. If those are absent, read `PROJECT_CHARTER.md` two levels up from the task folder for `## Default workspace` or `## Repositories`.
  3. Read task artifacts (TASK_STATE.md, DECISIONS.md, IMPLEMENTATION_PLAN.md, SLICES/) from the task folder in the Fhorja repo. Read product code from the resolved workspace path. Never assume the two share the same root.
  4. If neither source yields a workspace path and the task references product code, ask the user for the workspace path (one targeted question) instead of failing with file-not-found errors.
- **Archived task path (ADR-0105):** WHEN the given task path resolves under `archive/` (or the legacy `done/`) instead of `active/`, do not fail. Route to `task-close`'s reopen mode first (the folder moves back to `active/` and the final state is reset), then resume normally from the reopened state.
- **Lost-session recovery mode (`--lost-session`, per ADR-0113):** recover working context when the session transcript itself is lost (a crash or dropped session that left no Handoff). The trigger is EXPLICIT only: this flag or an unequivocal user ask; a missing `TASK_STATE.md` alone never fires it (the normal missing-state path stays unchanged). Flow:
  1. Before any tool call, ask ONE targeted question for a date window and the harness (zero tool cost; both shrink the sweep).
  2. Load `wos/session-recovery.md` for the per-harness session-file map and cite which subsection was read (the G3-style safeguard); sweep for candidate session files per that map only.
  3. Hard cap: 6 tool calls TOTAL for the whole recovery, PREVAILING over any per-step budget. Candidates found but not read are reported as unconfirmed leads, never silently dropped (guard-rail G1: the shortcut is auditable).
  4. Every extraction (active task folder, last completed command and its Handoff, files being edited, decisions stated in the final turns) is PROPOSED with provenance: the source file plus the line or event it came from. The mode is read-only by construction: it writes no task file, no product file, and no session file, and emits no substrate write (mirrored in `wos/substrate-peers.md ## Read/write contracts`).
  5. Mandatory handoff, never self-resolution: a found task folder routes to `state-reconcile` (which reconciles the PROPOSED extractions against the on-disk substrate); none found routes to `task-init`. Unattended runs with an unknown project slug stall as PROPOSED rather than guessing a directory to sweep.
- **Handoff:** end with the adaptive `### Handoff` block per `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full).
- **Context-rot guardrail (ADR-0023):** before producing the output, estimate the current TASK_STATE.md token count (excluding the `## Compaction history` section). Compare against the phase threshold from `wos/context-budget.md ## Context-rot thresholds` (discovery: 3000; planning: 5000; implementation: 8000; review/closure/delivery: 6000). If current count exceeds the threshold, emit a single-line warning in `### Command transcript`: `WARN: TASK_STATE.md is ~Ntokens (phase threshold: Mthreshold). Consider running compact-task-memory before continuing.` The warning is INFORMATIONAL; proceed with the normal output. Suppress the warning if the immediately prior step was `compact-task-memory`.
- Treat TASK_STATE.md as the operational memory for the task.
- **Quick reanchor fast path (ADR-0111):** WHEN `## Quick reanchor` is present, read it FIRST and trust it ONLY after the freshness cross-check: the highest D-N cited in the block equals the highest locked D-N in `DECISIONS.md ## Locked decisions`. On mismatch, or when the block is absent (legacy task), fall back to the full artifact re-read; never resume from a stale anchor.
- Treat linked plan/decision/test artifacts as the current source of truth.
- Reconstruct:
  - what has already been done
  - what decisions are locked
  - which phase the task is in
  - what remains
  - **work complexity** for the next step (`TASK_STATE.md` section if present; otherwise infer using `WORKFLOW_OPERATING_SYSTEM.md` definitions; never name model SKUs)
- If TASK_STATE.md is missing, stale, or contradictory, say so explicitly.
- If artifacts disagree, identify the conflict clearly and recommend the smallest corrective next step.
- Avoid broad rediscovery unless the saved state is not trustworthy enough to continue safely.

Required output:
1. Current phase
2. Confirmed source of truth
3. What is completed
4. What is still pending
5. Any stale or conflicting state
6. Recommended next command
7. Recommended editor mode
8. Recommended work complexity (`LOW` | `MEDIUM` | `HIGH` | `N/A`) for that next step
9. Why this is the correct next step
10. What should explicitly not be done yet

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
- Reconstruction is grounded in `TASK_STATE.md` plus linked artifacts (no broad rediscovery).
- Conflicts are surfaced with the smallest corrective next step.
- `### Artifact changes` is `None` unless a correction must be persisted (then justify why not `sync-task-state`).
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
Optimize for fast, correct resumption with minimal ambiguity and minimal repeated analysis.
