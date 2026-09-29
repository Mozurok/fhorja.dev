---
name: compact-task-memory
description: Produce a lossy compaction summary of TASK_STATE.md when task memory has grown beyond a useful working size, preserving canonical decisions and recommended next step while dropping stale facts. Distinct from sync-task-state (incremental, append-only, never lossy) and state-reconcile (drift repair, no shrinking). Use when task memory has accumulated across multiple slices (5+ completed) and feels heavy, the resume cost is growing as the file scales, the current known facts list is full of resolved or routine entries, or before a session pause where a slim TASK_STATE will speed restart. Do not use when the task is still in early discovery (memory is small), the artifacts disagree across files (use state-reconcile first), an incremental sync would be sufficient (use sync-task-state), or no active task folder exists yet (run task-init first).
metadata:
  category: state-and-navigation
  primary-cursor-mode: Plan
  multi-repo-aware: false
  context-layers-consumed: [memory]
  context-layers-produced: [memory]
  tools: [Read, Write, Edit, Bash, Glob, Grep]
  x-wos-profiles: [core, full]
  provenance: first-party
  suggested-model: claude-haiku-4-5
---
# compact-task-memory

Act as a senior/staff engineering workflow memory compactor for the active engineering task.

Goal:
Produce a compaction summary of TASK_STATE.md that keeps the operational truth needed to resume work, preserves all canonical decisions and recommended next step verbatim, and drops resolved or routine facts that no longer earn their attention budget. Lossy on the prose but provenance-preserving: every dropped fact stays recoverable from the pre-compaction snapshot (ADR-0141) AND traceable to the append-only `.wos/VERIFICATION_LOG.jsonl` audit chain, which this command never rewrites (per ADR-0093).

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
- TASK_STATE.md (current; the file being compacted)
- DECISIONS.md (read-only; canonical decisions must be preserved verbatim)
- IMPLEMENTATION_PLAN.md (read-only; recommended-next-step must trace to a slice in the plan)
- SLICES/*.md (read-only; closed slices are durable, NOT compacted; slice notes outside TASK_STATE survive)

Task repository files to update:
- TASK_STATE.md (slimmed body + new `## Compaction history` entry at the bottom)
- `.wos/compaction/<ISO-8601-timestamp>_TASK_STATE.md` under the task root (byte-for-byte snapshot before pruning)

Only these artifacts and the required substrate audit-log append are written. SLICES/*, DECISIONS.md, INVARIANTS_AND_NON_GOALS.md, SOURCE_OF_TRUTH.md, README.md are immutable in this command.

Operating rules:
- Do not implement production code; this is a memory operation.
- **Always-loaded files (W-15, sibling concern):** this command compacts TASK_STATE.md. The always-loaded context files (CLAUDE.md, USER_MEMORY.md) have their own size guard: `scripts/check-instruction-budget.sh` surfaces a warn-only `Instruction-budget:` line in lint when they exceed a soft size or line budget (the context-rot threshold idea of ADR-0023 applied to files loaded into every session). When that advisory fires, trim or split the named file; this command does not edit those files.
- **Handoff:** end with the adaptive `### Handoff` block per `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full).
- **Preserve verbatim** (NEVER paraphrase, never drop):
  - Quick reanchor
  - Task summary
  - Current phase
  - Objective
  - Requested deliverables (the ADR-0056 coverage ledger; dropping a named deliverable here is the silent de-scope that ledger exists to prevent)
  - Recommended pipeline
  - Source of truth pointers
  - Canonical decisions (entire section)
  - Current status
  - Constraints / things that must not change
  - Recommended next step
  - Resume notes
  - Task scope level
  - Current closure target
  - Work complexity (for next execution step)
  - `## Ruled-out hypotheses` when present (the ADR-0088 ledger; it lives in TASK_STATE.md precisely so dead ends travel with the task across compaction, and `incident-triage` reads it first on intake)
- **Filter (drop or move to history)**:
  - `## Current known facts`: drop entries that are no longer load-bearing for the recommended next step or any active risk; keep entries the next slice will need.
  - `## Open questions / blockers`: keep unresolved; move resolved (with a one-line "resolved in <commit/slice/decision>") to the compaction history entry.
  - `## Active files in scope`: filter to files relevant to remaining slices; drop files only relevant to closed slices.
  - `## Risks to watch`: keep active risks; move mitigated risks (with a one-line "mitigated in <slice>") to the compaction history entry.
  - `## Observations` when present: keep observations still bearing on the recommended next step or an active risk; move the rest (with a one-line "captured <date>") to the compaction history entry. Never drop one without naming it there.
- **Every section is preserved or filtered, except the recovery anchor updated below.** `## Last completed step` records this compaction; its prior bytes remain in the snapshot. WHEN `TASK_STATE.md` carries any other section named in neither list above, preserve it verbatim and name it in the compaction history entry. A section this command does not recognize is not evidence that it is stale.
- **Append `## Compaction history`** entry at the bottom of TASK_STATE.md (or extend if the section exists):
  ```
  ## Compaction history

  ### YYYY-MM-DD HH:MM
  - Compacted from: <pre-compaction snapshot path>
  - Lines before: <N>
  - Lines after: <M>
  - Reduction: <N - M> lines (~<P>%)
  - Preserved verbatim: locked decisions, recommended next step, current phase, objective, invariants, source of truth, constraints
  - Dropped from current known facts: <bulleted list of dropped fact categories or specific entries>
  - Resolved questions moved here: <bulleted list with "<question>: resolved in <slice/commit>">
  - Mitigated risks moved here: <bulleted list with "<risk>: mitigated in <slice>">
  - Summary: <2-4 sentence narrative of where the task is right now>
  - Provenance of dropped facts: <the run_id(s), or owner + section, from `.wos/VERIFICATION_LOG.jsonl` that originally wrote the dropped entries; the log is append-only and is never rewritten or pruned by compaction>
  - Reversible via: <the snapshot path written below; optionally a verified `git show <commit SHA>:<repo-relative TASK_STATE path>` for the same pre-compaction bytes>
  ```
- **Write the pre-compaction snapshot BEFORE pruning, and cite it.** Run `mkdir -p <task-root>/.wos/compaction` first: the directory does not exist on any task until the first compaction, so a copy into it fails until it is created, and the invalid-output rule below would then refuse every first run. Copy the current `TASK_STATE.md` byte for byte to `<task-root>/.wos/compaction/<ISO-8601-timestamp>_TASK_STATE.md`, then prune, then cite that path in `Reversible via`. The snapshot is an APPLIED write and gets its own line in `### Artifact changes`. Do not write the pruned file until the byte-for-byte snapshot is confirmed. Add a git pointer only after verifying that its blob contains those same pre-compaction bytes.
  - WHY this replaces the git-only pointer: `projects/` is gitignored in this repository (`.gitignore`), so for a task living there `git show` resolves to nothing and the field promised a reversal that never existed. Verified 2026-08-11 across six real tasks: seven `Reversible via` pointers, three different invented paths and two naming a session transcript that no longer exists.
  - Honest limit of the snapshot: `.wos` is gitignored too, so it survives between sessions on one machine, not between machines and not in the remote. It is a local undo, not a backup. When the task folder IS git-tracked and a matching pre-compaction blob is verified, cite both.
- Lossy compaction is intentional. The Compaction history entry lists what was dropped so the user can audit the decision; the snapshot above reverses any over-eager drop.
- **Provenance-preserving compaction (per ADR-0093).** The `.wos/VERIFICATION_LOG.jsonl` audit chain is append-only and SHALL NOT be rewritten, pruned, or summarized by this command. Recover a dropped fact from the pre-compaction snapshot and trace its origin through the VERIFICATION_LOG entry (owner, run_id, ts, sha) that wrote its section. A verified git blob is an additional recovery route. The Compaction history `Provenance of dropped facts` field SHALL cite that trace-level provenance so a dropped fact is recoverable at the audit-chain level, alongside the snapshot. This is the compress operation of the write / select / compress / isolate context-operations model (`wos/context-budget.md`): compression that keeps provenance, rather than a plain lossy summary, is what makes the compaction safe to run mid-flight on a long session.
- If the model is uncertain whether a fact is still load-bearing, KEEP IT. Compaction is conservative; under-compacting is recoverable in a later run, over-compacting requires restoring from the snapshot above (or from git where the task folder is tracked).
- **Record yourself as the last completed step.** After preserving the prior bytes in the snapshot, write `compact-task-memory` and the date to `## Last completed step`. A resumed session reads that field to decide whether to warn about context rot (`resume-from-state` suppresses the warning when the prior step was this command), and in a cold session the field is the only source on disk for that answer.
- **Harvest before you prune (mobile dogfood 2026-07-29).** WHEN the compaction would drop entries from `## Current known facts`, `## Risks to watch`, or `## Ruled-out hypotheses`, name those entries in the `### Handoff` and route to `harvest-session-learnings` before the pruned file is written, so a durable lesson is captured while it is still on the page. Route only: do NOT inline-load `harvest-session-learnings` in this turn, which exists to shed context, and do NOT write `LEARNINGS.md` here (that command owns it, append-only). The local snapshot preserves the pre-compaction bytes, but it does not publish durable lessons for later consumers; harvest routes that knowledge into the artifact those consumers read. The source run compacted twice across about 21 hours and reached delivery with no `LEARNINGS.md` at all.
- Do NOT compact when:
  - `TASK_STATE.md` is at or below its phase threshold from `wos/context-budget.md ## Context-rot thresholds` (discovery 3000, planning 5000, implementation 8000, review/closure/delivery 6000), excluding `## Compaction history` (return `NO_OP_TRACE` with "task memory not large enough to benefit from compaction; resume cost is already low"). Measure the same way the callers do: `sync-task-state`, `where-we-at` and `resume-from-state` route here on exactly that comparison, so gating on anything else refuses the calls they send. Slice count is NOT the gate: a discovery-phase task with no closed slices can still be over threshold, and refusing it on age left the caller routing to a command that could never accept.
  - Artifacts disagree (return `NO_OP_TRACE` and route to `state-reconcile`).
  - The model cannot identify which facts are stale vs load-bearing (return `NO_OP_TRACE` with a request for the user to specify or to advance one more slice first).
- Set **Work complexity** based on the compaction depth: usually LOW (mechanical filter), MEDIUM if the task has 5+ slices and large fact accumulation, HIGH only if cross-cutting context that affects multiple slices needs careful preservation.

Required output:
1. Whether TASK_STATE.md should be compacted now and why (or `NO_OP_TRACE` reason if not)
2. Exact slimmed content for TASK_STATE.md (proposed under PROPOSED-by-default in Plan mode)
3. Exact `## Compaction history` entry to append
4. Reduction metrics (lines before / after; categories dropped)
5. Audit list: what was dropped that the model believes is no longer load-bearing
6. Recommended next command (typically `sync-task-state` to flush other small updates, or `resume-from-state` if compaction is preparing for handoff)
7. What should explicitly NOT be done as a result of this compaction (do not change SLICES/, do not touch DECISIONS.md, do not modify INVARIANTS_AND_NON_GOALS.md)

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
- The slimmed TASK_STATE.md preserves all "preserve verbatim" categories without paraphrase (canonical decisions, recommended next step, current phase, objective, invariants, source of truth, constraints).
- The `## Compaction history` entry is appended with reduction metrics, dropped categories, resolved questions moved, mitigated risks moved, a 2-4 sentence summary, and the pre-compaction snapshot pointer; git is additional only when its exact pre-compaction bytes were verified.
- `### Artifact changes` marks TASK_STATE.md as `APPLIED` only when explicitly persisting in Agent mode; otherwise `PROPOSED` for Plan/Ask review. The gate is deliberate on this command alone, because the compaction is lossy (ADR-0220).
- The dropped-fact audit list is explicit; over-eager drops can be challenged by the user and recovered from the snapshot.
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
Optimize for resumability after compaction, fidelity to canonical decisions, conservative filtering (when uncertain, KEEP), and clear audit trail of what was dropped so the user can reverse over-eager compaction from the snapshot.
