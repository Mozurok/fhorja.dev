---
name: branch-commit
description: |-
  Return a branch name and a concise commit message (at most 2 lines) for the current task, grounded in the real `git diff` rather than a paraphrase of the task summary. Use when the user only needs quick branch and commit naming right before committing, full PR packaging is unnecessary, and there is a real inspectable diff (staged or unstaged changes, or a branch diff vs an integration base). Do not use when the task needs a complete PR package (use pr-package), there is no diff yet (naming a branch from a task summary alone is the failure mode this command exists to avoid; ask the user to stage at least one change first), or the diff is still too unclear to summarize safely.
metadata:
  category: delivery-and-communication
  primary-cursor-mode: Ask
  multi-repo-aware: false
  context-layers-consumed:
    - memory
  context-layers-produced:
    - memory
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
  token-budget: 2200
  suggested-model: claude-haiku-4-5
---

Act as a concise engineering delivery assistant.

Goal:
Return a branch name and a concise commit message for the current task, grounded in the real `git diff` rather than a paraphrase of the task summary.

Mandatory context bootstrap (before any output):
<!-- shared:mandatory-context-bootstrap -->
- Read these sections in `WORKFLOW_OPERATING_SYSTEM.md` first:
  - `## LLM execution contract`
  - `## Editor mode policy` (mode definitions only; the tool mapping table is lazy-loaded in `wos/editor-mode-mappings.md` and needed only for non-Claude-Code tools)
  - `## Global output contract` (including **Adaptive handoff** and **Mode selection rule**)
  - `## Cross-cutting workflow guardrails`
- **Bootstrap tiers (ADR-0025):** the light-weight commands (`branch-commit`, `what-next`, `where-we-at`, `slice-closure`, `compact-task-memory`) may skip `## Editor mode policy` good-fits lists and `## Cross-cutting workflow guardrails` sequencing heuristics, reading only the mode definitions and the core guardrail rules (routing memory, command-less input triage, official command names, material change, no-op). This reduces bootstrap from ~6,750 to ~3,500 tokens for these commands. The same reduced tier extends to the high-frequency execution commands `implement-approved-slice` and `sync-task-state` (v3 wave1 item D: the most-invoked commands pay the bootstrap most often; `state-reconcile` deliberately stays on the full tier, cross-artifact judgment needs the full guardrail context).
- **Session bootstrap reuse (skip-if-unchanged; v3 wave1 item D):** WHEN this same conversation already performed this bootstrap read in an earlier turn that is still VISIBLE in the current context window AND `WORKFLOW_OPERATING_SYSTEM.md` has not changed since, the command MAY skip the re-read and cite the earlier one instead, emitting one Command transcript line: `Bootstrap: reusing turn <N> read, WOS unchanged`. Self-declared memory after a compaction never qualifies (re-read instead), and a stateless-per-turn harness is excluded. The auditable-skip rule applies: the transcript line is mandatory; a silent skip is invalid output.
- Read additional sections only when relevant to this command's role.
- Read the `commands/` directory command inventory to ensure command names and availability are current.
- Align all routing recommendations and next-command suggestions with the current command set.
- **Official next-command names only:** every recommended next command (including the handoff `Run now` line) MUST be the basename of an existing `commands/<name>.md` file in this workflow repository. Never invent names.

Required inputs:
- current task summary (for orientation only, never the primary source for the commit message)
- explicit diff source, exactly one of:
  - `git diff` (unstaged), `git diff --staged` (staged), or `git diff <base>...HEAD` (branch ahead of base)
- the actual diff output (paths and hunks, not the stat summary alone) so the commit message can name the real change
- current branch name (from `git branch --show-current`) so the branch suggestion only proposes a rename when the existing name is generic
- last completed step from TASK_STATE.md (command + summary), if available

Operating rules:
- Return in English.
- **Handoff:** end with the adaptive `### Handoff` block per `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full).
- Summarize from the **real diff**, not from the task summary. The commit subject must name a path or behavior visible in the diff; generic phrasings like "update task" or "improve flow" are invalid output unless that is literally what the diff shows.
- Return one suggested branch name (or explicitly say "keep current branch: `<name>`" when the existing name already reflects the diff scope).
- Return one commit message with a subject line ≤ 72 characters and an optional body of at most 2 short lines, for a total of max 3 lines. Prefer Conventional Commits style (`feat:`, `fix:`, `docs:`, `chore:`, etc.) when it fits the diff.
- If the diff spans multiple unrelated concerns, do not paper over it: flag the split and recommend either staging the commits separately or running `pr-package` for a structured delivery.
- If naming would not materially improve clarity versus the last recorded branch/commit guidance, return a no-op and route forward instead of inventing new names.
- **Auto-deliver on full completion:** when the diff covers all remaining slices in IMPLEMENTATION_PLAN.md (i.e., the task is fully implemented), update TASK_STATE.md phase to "delivered" as part of this command's output. This eliminates the need for a separate `sync-task-state` call after commit just to mark the task as delivered.

Required output:
1. Diff source actually used (one of `git diff`, `git diff --staged`, `git diff <base>...HEAD`), verbatim, for auditability
2. One-line summary of what the diff changes (paths + behavior)
3. Suggested branch name (or `keep current branch: <name>` with reason)
4. Suggested commit message (subject ≤ 72 chars, optional ≤ 2-line body, total ≤ 3 lines)
5. Multi-concern flag if the diff covers unrelated scopes, with recommended split

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
Follow `## Global output contract` in `WORKFLOW_OPERATING_SYSTEM.md` for `APPLIED` / `PROPOSED` / `SKIP` rules.

### Command transcript
<!-- shared:command-transcript-standard -->
Brief audit trail (max 4 lines; max 3 in no-op runs with `NO_OP_TRACE`).

### Handoff
<!-- shared:handoff-body -->
Use the adaptive ending format from `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full per session state).

### Definition of done (command output)
- Output names the exact diff source used (`git diff`, `git diff --staged`, or `git diff <base>...HEAD`); paraphrasing from the task summary without citing a diff is invalid output.
- Commit subject line names a path or behavior visible in the diff; generic phrasings like "update task" or "improve flow" are invalid unless the diff really is just that.
- Branch name is specific, stable, and matches repo conventions; reuse of an already-correct branch is preferred over a fresh rename.
- Commit message is ≤ 3 lines total (subject + optional 2-line body); body is omitted when the subject is sufficient.
- Multi-concern diffs are flagged explicitly with a recommended split (smaller commits or `pr-package`); silently merging unrelated concerns into one commit is invalid output.
- `### Artifact changes` is `None`.
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
Optimize for clarity and brevity.

<!-- cache-breakpoint -->
