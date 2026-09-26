---
name: direction-adjust
description: |-
  Capture a small-to-medium course correction realized mid-task, not from external review: record it as a numbered D-N entry in DECISIONS.md, update TASK_STATE.md, and route back to the right command. Use when the realization came from your own work, is worth recording, does not invalidate the whole approach, and the current slice is recoverable with a small change of plan. Do not use when the trigger is external review or PR feedback (use pr-feedback-ingest or post-review-pivot), when it invalidates the entire task scope (use task-init for a new task), when it is too small to record (use capture-observation), when it is loop or confusion (use im-stuck), or when it requires reopening locked decisions (use decision-interview).
metadata:
  category: "contracts-and-decisions"
  primary-cursor-mode: "Ask"
  multi-repo-aware: "false"
  context-layers-consumed: "memory"
  context-layers-produced: "memory"
  tools: "Read, Write, Edit, Bash, Glob, Grep"
  x-wos-profiles: "minimal, core, full"
  provenance: "first-party"
  suggested-model: "claude-sonnet-5"
---
> **Output contract, in brief.** This body is over the per-skill re-injection cap, so
> after a compaction the sections below are truncated away while this summary survives.
> They remain authoritative in full; re-read this file before emitting if you need them.
>
> - `Standard output layout (required)`: Produce the command output using this structure (English only):
> - `Artifact changes`: List files in the task repository that would change, or `None`.
> - `Command transcript`: Keep this section operational and brief; do not restate file content already listed in `### Artifact changes`.
> - `Handoff`: Use the adaptive ending format from `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full per...
> - `Definition of done (command output)`: The adjustment is recorded as a numbered `D-N: mid-task adjustment` entry in `DECISIONS.md` with concise reasoning, or, when it is...


Act as a senior/staff engineering direction adjustment for the active engineering task.

Goal:
Capture a small-to-medium course correction that the user realized mid-task (not from external review), record it as a decision in `DECISIONS.md`, update `TASK_STATE.md` to reflect the adjusted direction, and route back to the appropriate command to continue the work.

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
- TASK_STATE.md (must reflect current phase and last completed step)
- DECISIONS.md (current canonical decisions)
- IMPLEMENTATION_PLAN.md (current plan that is being adjusted)
- the user's description of the realization: what was being done, what was noticed, what should change
- optional: which slice or phase the adjustment affects

Task repository files to update:
- DECISIONS.md (append a new decision recording the adjustment with a `D-N: mid-task adjustment` prefix, or a provisional `### P-N` under `## Provisional decisions` per the attended-chain rule below)
- DECISIONS.md `## Decision history` (WHEN the mid-task realization is new evidence that contradicts an already-persisted NON-decision claim, record a defeasible-claim revision here per the ADR-0109 / D-10 write rule in `wos/substrate-peers.md ## Decision history`: append-only, name the contradicting evidence and its provenance rank, mark `[OPEN]`; `task-close` blocks on an unresolved one)
- TASK_STATE.md (update `Last completed step` if it is now wrong, update `Recommended next step` to reflect the adjusted direction, update `Risks to watch` if the adjustment introduces new risk)
- IMPLEMENTATION_PLAN.md (only if the adjustment changes plan text; default is to leave plan as-is and note the adjustment in `DECISIONS.md`)
- relevant SLICES/*.md (only if the active slice scope must change to reflect the adjustment)

Operating rules:
- Do not implement production code.
- **Handoff:** end with the adaptive `### Handoff` block per `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full).
- **Substrate write protocol (per ADR-0034, K.2).** MANDATORY for every substrate section this command writes (the `DECISIONS.md` section receiving the new D-N entry, which is `## Locked decisions`, plus `## Decision history` when this turn records a defeasible-claim revision, and each updated `TASK_STATE.md` section). Follow `commands/_shared/substrate-write-protocol.md`: emit the `<!-- wos:write owner=direction-adjust section='## X' ... -->` transaction header and append one JSONL line per section write to `active/<task>/.wos/VERIFICATION_LOG.jsonl`. Header placement per `commands/_shared/substrate-write-protocol.md ## Transaction header`: the transaction header goes on its own line IMMEDIATELY above the `## <section>` heading line. NEVER place it below the heading, and NEVER above a `### D-N` entry inside the section; a header placed below the heading leaves the section counted as header-less by the K.4 drift scan (`scripts/scan-substrate-headers.sh`), which checks only the line immediately preceding each `## ` heading.
- Treat the adjustment as a new decision, not a silent edit. The output must produce a numbered entry (`D-N`, or `P-N` under the attended-chain rule below) for `DECISIONS.md`.
- Make the adjustment auditable: clearly show what direction was being followed before, what changed, and why.
- Validate the adjustment against existing locked decisions and invariants. If the adjustment contradicts a locked decision, surface this explicitly and route to `decision-interview` instead of silently overwriting.
- Validate the adjustment against `INVARIANTS_AND_NON_GOALS.md` if present. If the adjustment crosses a non-goal or invalidates an invariant, surface this and require user confirmation before proceeding.
- **Attended chain on a task branch (ADR-0233; the P-N format rests on its provisional P-1).** WHILE this command runs in an attended chain on a task branch (a `Task branch:` line in `TASK_STATE.md ## Resume notes`), no `Operating mode: assisted` is declared, and the realization is the agent's rather than one the person described, it SHALL be recorded as a provisional `### P-N` under `DECISIONS.md ## Provisional decisions`, in the format `commands/decision-interview.md` gives its provisional mode, instead of a `D-N: mid-task adjustment`, and the chain SHALL continue. The two conflict rules above do not wait for a person in such a chain. IF the adjustment contradicts a locked D-N or crosses an invariant or non-goal THEN this command SHALL NOT apply it: the work keeps following the locked decision or the invariant, the adjustment is recorded as a P-N with `Impact: high` naming the D-N or the invariant it would change, and the chain continues on the current direction until the person answers. An unattended, background or fleet-dispatched run keeps the rules above.
- Keep the new `DECISIONS.md` entry concise: 2-5 lines covering what changed and why.
- Update `TASK_STATE.md` minimally: only fields actually affected by the adjustment. Do not rewrite unrelated sections.
- If the adjustment requires re-planning (the slice scope is now wrong, or the slice order needs to change), the recommended next command must be `implementation-plan` or `state-reconcile`, not blind continuation.
- If the adjustment is small enough that the current slice can absorb it without re-planning, the recommended next command is the slice-execution command appropriate to the phase (typically `implement-approved-slice`).
- Treat task-memory write policy per `WORKFLOW_OPERATING_SYSTEM.md`: write the file and mark it `APPLIED`.

Required output:
1. Summary of the adjustment in plain language: "before, the direction was X; now, the direction is Y; the trigger was Z".
2. The new `DECISIONS.md` entry to append, formatted as `D-N: mid-task adjustment - <one-line title>` followed by 2-5 lines of detail.
3. The updated fields in `TASK_STATE.md` (only the fields that actually change).
4. The validation result against locked decisions: `compatible`, `requires decision-interview`, `violates invariant: <which one>`, or, in an attended chain on a task branch, `recorded as provisional P-N` (with `not applied` when it conflicts).
5. The recommended next command, with reasoning about whether the adjustment requires re-planning or fits the current slice.
6. Recommended editor mode for that next command.
7. Recommended work complexity (`LOW` | `MEDIUM` | `HIGH` | `N/A`) for the next step.

### Substrate digest fallback
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
- List files in the task repository that would change, or `None`.
- For each file, mark `APPLIED` / `PROPOSED` / `SKIP` and follow the task-memory write policy in `WORKFLOW_OPERATING_SYSTEM.md` (task memory is `APPLIED` in every mode; a section this command does not own gets a `<!-- PROPOSED by <command>: ... -->` block for its owner, ADR-0034).
- Default for this command: `APPLIED` patches on `DECISIONS.md` and `TASK_STATE.md`; conditionally on `IMPLEMENTATION_PLAN.md` or `SLICES/*.md` only when the adjustment requires it.

### Command transcript
- Keep this section operational and brief; do not restate file content already listed in `### Artifact changes`.
- Max 4 lines in normal runs.
- Max 3 lines in no-op runs (including `NO_OP_TRACE`).
- Include `NO_OP_TRACE` (1-3 lines) if the realization is too small to record as a decision (route to `capture-observation` instead) or if the adjustment turns out to require a heavier path (route to `decision-interview` or `state-reconcile`).

### Handoff
Use the adaptive ending format from `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full per session state). Every Handoff is one fenced `text` block with all four lines, `Run now:`, `Mode:`, `Work complexity:` and `Reason:`, on a stop and on a refusal too; the terminal form is `Run now: none` with `Mode: N/A`.

### Definition of done (command output)
- The adjustment is recorded as a numbered `D-N: mid-task adjustment` entry in `DECISIONS.md` with concise reasoning, or, when it is the agent's own realization in an attended chain on a task branch, as a provisional `### P-N` with its `Evidence:`, `Impact:` and `Status: provisional` lines.
- Every substrate write carries its `wos:write` transaction header on its own line IMMEDIATELY above the `## <section>` heading, never below the heading and never above a `### D-N` entry inside the section, per `commands/_shared/substrate-write-protocol.md ## Transaction header`.
- `TASK_STATE.md` updates are minimal and target only fields affected by the adjustment.
- Validation against locked decisions and invariants is explicit; the output names any conflict and routes to a heavier command rather than silently overwriting.
- The adjustment never overrides locked decisions in place. Conflicts route to `decision-interview`, or, in an attended chain on a task branch, are recorded as an `Impact: high` P-N while the work keeps following the locked decision.
- The adjustment never violates invariants or crosses non-goals silently. Conflicts surface for user confirmation; in an attended chain on a task branch that confirmation is asked in the draft pull request through the P-N, not by stopping.
- `Artifact changes` marks each patch as `APPLIED`.
- `Handoff` has non-empty `Run now`, `Mode`, `Work complexity`, and `Reason` fields, plus `Resume context` only in Mode B; ending after the decision entry without a Handoff is invalid output.
- The recommended next command is appropriate to the size of adjustment: small adjustments resume current slice; medium adjustments trigger `implementation-plan` or `state-reconcile`; conflicts trigger `decision-interview`.
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
Optimize for auditability of the direction change, protection of locked decisions and invariants, minimal disruption to in-progress work, and clear routing to the right next step based on the size of the adjustment.
