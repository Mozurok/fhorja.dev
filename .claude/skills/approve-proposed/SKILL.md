---
name: approve-proposed
description: |-
  Atomically persist every file marked PROPOSED in the most recent prior assistant turn's `### Artifact changes` block. Invoked on request only; it is not part of any default chain. The ADR-0001 mode gate it once serviced is gone, and what remains is the staged write: a command chose to stage a PROPOSED block inside a section it does not conventionally own (optional since ADR-0232 made ownership descriptive), and the user wants it promoted without waiting for the owner command. Use when the prior assistant turn ended with a `### Artifact changes` block containing one or more files marked PROPOSED and you have read and accepted the inline content for each. Do not use when the prior turn had no `### Artifact changes` block, every artifact is APPLIED or SKIP, you have not yet read the proposed content, or you want to approve only a subset (run the original command in Agent mode for partial approval).
metadata:
  category: "state-and-navigation"
  primary-cursor-mode: "Agent"
  multi-repo-aware: "false"
  context-layers-consumed: "history, memory"
  context-layers-produced: "memory"
  tools: "Read, Write, Edit, Bash, Glob, Grep"
  x-wos-profiles: "core, full"
  provenance: "first-party"
  suggested-model: "claude-haiku-4-5"
---

Act as a senior/staff engineer executing a single batch-persist of every file the prior assistant turn proposed under `### Artifact changes`.

Goal:
Read the most recent prior assistant turn in the conversation history, identify every file marked `PROPOSED` in its `### Artifact changes` block, and write all of them atomically. Print a single recap line listing what landed.

Mandatory context bootstrap (before any output):
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
- the conversation history containing the most recent prior assistant turn with an `### Artifact changes` block (already in context when the command runs)
- active task folder path (for resolving relative artifact paths)

Task repository files to update:
- every file listed in the prior turn's `### Artifact changes` block that is marked `PROPOSED` (full inline content or update-delta)

Operating rules:
- Do not propose anything. This command is for executing prior proposals, not creating new ones.
- **Source-of-truth turn**: the "prior assistant turn" means the most recent assistant message whose `### Artifact changes` block is NON-EMPTY and carries at least one `PROPOSED` file. Skip intervening user messages, tool results, assistant messages with no Artifact-changes block, AND assistant messages whose Artifact-changes block is empty (a NO_OP `None` / `NO_FILE_CHANGES` block): an empty block does NOT shadow an earlier real proposal (D-4, 2026-07-18). STOP walking back at the first intervening block that carried real `APPLIED` or `SKIP` decisions: never reach past a block the user already acted on, so a superseded proposal is never resurrected. This preserves ADR-0024's rule that you never walk back across multiple *decision-bearing* Artifact-changes turns; it only skips empty NO_OP blocks that would otherwise hide the latest real proposal.
- **Stacked live proposals are never silently dropped (worktree dogfood 2026-08-04).** WHEN, walking back under the rule above, you find an EARLIER non-empty `PROPOSED` block that no intervening block resolved as `APPLIED` or `SKIP`, that block is a LIVE proposal, not a superseded one. Persist its files too when their paths do not collide with the latest block's. On a path collision the latest block wins and the earlier file is listed under `Skipped (superseded by a later proposal): <list>`. Emitting nothing about the earlier block is invalid output: on the source run three proposed files evaporated this way and one of them, `IMPACT_ANALYSIS.md`, was never written.
- **Content required**: persist files that have either (a) full inline content or (b) an update-delta (semantic description of changes to an existing file). For full inline: write the content as-is. For update-delta: read the current file on disk, apply the described changes, and write the result. If a file is marked `PROPOSED` but its content is vague or unresolvable (e.g., "see content above", "same as last turn"), do NOT persist it; list it under `Skipped (incomplete inline)` in the recap.
- **Path resolution**: every file path in the prior block must resolve to a real path inside the active task folder OR inside the workflow repository (for workflow meta-edits). If a path resolves outside both, do NOT persist it; list it under `Skipped (path outside scope)` in the recap.
- **Atomic batch**: perform all qualifying writes in this single turn (one Write per file). Do not split across multiple turns. Do not interleave Write calls with conversational prose.
- **No partial mode**: this command is all-or-nothing for the qualifying subset. If the user wants partial approval, they re-run the source command in Agent mode or edit the proposals before running this command.
- **No-op cases**:
  - Prior turn has no `### Artifact changes` block: NO_OP with explicit explanation ("most recent assistant turn does not contain an Artifact changes block; nothing to approve").
  - Prior block contains no `PROPOSED` files (all `APPLIED` or `SKIP`): NO_OP with explicit explanation.
  - All PROPOSED files match on-disk content already: NO_OP with explicit explanation ("all proposed files are identical to current on-disk content; nothing to write").
- **No new proposals**: if the user input contains additional instructions beyond "approve", ignore them. This command does not accept new content; it only executes the prior batch. To propose new artifacts, re-run the source command.
- **Recap format (locked)**: the `### Command transcript` section MUST contain exactly one recap line per outcome class, in this order:
  1. `Persisted: <comma-separated-list-of-paths>` (omit line if empty)
  2. `Skipped (already current): <list>` (omit if empty)
  3. `Skipped (incomplete inline): <list>` (omit if empty)
  4. `Skipped (path outside scope): <list>` (omit if empty)
  5. `Skipped (no PROPOSED marker): <list>` (omit if empty)
- **Conflict-check rule**: before persisting any file, compare the proposed content's references to locked decisions in `TASK_STATE.md ## Canonical decisions`. If the proposal contradicts a locked decision, FAIL with a clear error naming the contradiction; do NOT persist anything in this turn (atomic rollback).
- **Why this still exists (ADR-0232).** Ownership is descriptive: a co-writer may write a section directly, logging the conventional owner in `reason`. Staging a PROPOSED block is the choice for a write the user wants to read before it lands, and this command is how that staged write lands in one batch. It is never required for a write outside the matrix row.
- **Substrate write protocol (per ADR-0034, K.2, ADR-0101).** WHEN a persisted file is a K.2 substrate file per `commands/_shared/substrate-write-protocol.md`, replace the proposer's mode=proposed transaction header with this run's `owner=approve-proposed ... mode=applied` header and append one `event=approve` JSONL line per applied file to `active/<task>/.wos/VERIFICATION_LOG.jsonl` with valid sha_before/sha_after (`bash scripts/emit-substrate-write.sh` is the invokable path); non-substrate files are unaffected.
- **Handoff:** end with the adaptive `### Handoff` block per `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full).

Required output:
1. The `### Artifact changes` block listing every persisted file as `APPLIED` (no inline content needed; the content already lived in the prior turn). Files that did not persist appear marked `SKIP` with a one-line reason.
2. The `### Command transcript` block with the recap lines per the format above.
3. A one-line summary stating how many files persisted vs how many were skipped.
4. Recommended next step, next command, editor mode, and why (typically routing back to whichever command produced the original proposals, OR to `sync-task-state` if the persisted files materially change task state).
5. What should explicitly not be done yet.

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
Follow `## Global output contract` in `WORKFLOW_OPERATING_SYSTEM.md` for `APPLIED` / `PROPOSED` / `SKIP` rules. Every listed file carries one of those three tokens, in Lean output too; a prose verb like "written" is not a label.

### Command transcript
Brief audit trail (max 4 lines; max 3 in no-op runs with `NO_OP_TRACE`).

### Handoff
Use the adaptive ending format of `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract`. Every Handoff is one fenced `text` block with all four lines, `Run now:`, `Mode:`, `Work complexity:` and `Reason:`, on a stop and on a refusal too; the terminal form is `Run now: none` with `Mode: N/A`. A new `Mode:`, a model or a fresh session is never a stop, an offered choice is one, and `Reason:` names a role, never a model.
### Definition of done (command output)
- Every file the prior turn marked `PROPOSED` (full inline or update-delta) is either persisted as `APPLIED` or explicitly skipped with a recap-line reason. Silent omission is invalid.
- The `### Command transcript` recap follows the locked five-line format (Persisted / Skipped already current / Skipped incomplete inline / Skipped path outside scope / Skipped no PROPOSED marker). Lines that have zero entries are omitted; lines that have entries appear in the locked order.
- No new artifacts are introduced beyond what the prior turn proposed. Adding files this command "thinks" should also be written is invalid output.
- No-op runs include `NO_OP_TRACE` and name the no-op cause (no Artifact-changes block / no PROPOSED files / all already current).
- Conflict-with-locked-decision runs do NOT persist anything; they emit a clear FAIL with the contradiction named.
- Output ends with a complete `### Handoff` block per the adaptive format in `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract`.
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
Optimize for: zero ambiguity about what landed on disk, atomic batch semantics, and recap clarity. The user must be able to read the recap and immediately know which files exist on disk now, which were skipped and why, and what to run next.
