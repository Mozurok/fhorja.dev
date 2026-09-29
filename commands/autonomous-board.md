---
name: autonomous-board
description: Read-only board-of-record view for an autonomous-run task (ADR-0044 D7, wos/autonomous-track.md). Renders the run as the spec, the IMPLEMENTATION_PLAN waves and slices, and the TASK_STATE phases mapped to to-do / in-progress / escalated / proposed / done columns, sourced only from the Fhorja task artifacts. No external work tracker; no writes. Use when the maintainer wants a single-glance status of an autonomous run without opening every artifact. Do not use to change state (use sync-task-state), to assess a normal multi-slice task (use where-we-at), or to route the next command (use what-next).
metadata:
  category: autonomy
  primary-cursor-mode: Ask
  multi-repo-aware: false
  context-layers-consumed: [memory]
  context-layers-produced: []
  tools: [Read, Bash, Glob, Grep]
  x-wos-profiles: [full]
  provenance: first-party
  suggested-model: claude-haiku-4-5
---
# autonomous-board

Act as a read-only status renderer for an autonomous delivery run.

Goal:
Render the current state of an `autonomous-run` task as a board of record, sourced only from the Fhorja task artifacts (the spec, `IMPLEMENTATION_PLAN.md` waves and slices, `TASK_STATE.md` phases, and `SLICES/` notes). This is the Fhorja-internal substitute for an external tracker (ADR-0044 D7): the spec plus the plan plus the phases already model the work, so this command only reads and arranges them. It performs no writes.

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
- IMPLEMENTATION_PLAN.md (waves and slices), TASK_STATE.md (phase, last completed step), SLICES/ notes if present
- last completed step from TASK_STATE.md (command + summary)

Operating rules:
- Do not implement code. Do not write any artifact; this command is read-only (`context-layers-produced: []`).
- Map each slice to one column: to-do, in-progress, escalated (boundary or test/eval slice awaiting the human gate), proposed (PROPOSED diff awaiting the merge gate), done (closed slice).
- Derive every cell from the artifacts only. Do not infer status that the artifacts do not support; mark unknown cells as unknown.
- Do not integrate or read an external work tracker (D7).
- Read `.wos/runs/*.json` (the ADR-0080 runs-feed v1 contract) as an additional source: when a feed file for this task exists, render a live-run line above the artifact-derived columns showing state, current_step, and last_update_ts, with a staleness note when last_update_ts is older than 15 minutes; when no feed file exists this changes nothing. This command still performs no writes to the feed.
- **Handoff:** end with the adaptive `### Handoff` block per `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract`.

Required output:
1. Run header: task, current phase, governor status if recorded, wave count
2. The board: one row per slice with its column, work complexity, and the EARS exit-criterion status
3. What is at a gate now (escalated slices, PROPOSED diffs awaiting merge)
4. Best next command and editor mode toward finishing the run

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
- The board is sourced only from the Fhorja task artifacts; no external tracker is read (D7).
- `### Artifact changes` is `None` (read-only command); no writes occur.
- Every slice maps to exactly one column; unsupported cells are marked unknown rather than guessed.
- Output ends with a complete `### Handoff` block per the adaptive format in `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract`.
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
A glanceable, honest status. Show what the artifacts prove and nothing more.
