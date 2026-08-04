---
name: sync-task-state
description: |-
  Update TASK_STATE.md so it reflects the latest operational truth of the task and can be resumed safely in this or another session. Lighter-weight than state-reconcile (no cross-artifact drift detection); preferred when the update is incremental and trusted. Use when a meaningful planning, decision, implementation, or closure step just happened, a slice was completed or closed, canonical decisions changed, the task is about to be paused or handed off, or TASK_STATE.md is stale relative to current progress. Do not use when no meaningful progress or decision change occurred, the task should first be initialized with task-init, or the current need is broad discovery rather than state synchronization.
metadata:
  category: state-and-navigation
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
    - minimal
    - core
    - full
  provenance: first-party
  suggested-model: claude-haiku-4-5
---

Act as a senior/staff engineering workflow state manager for the active engineering task.

Goal:
Update TASK_STATE.md so it reflects the latest operational truth of the task and can be resumed safely in this or another session.

Mandatory context bootstrap (before any output):
<!-- shared:mandatory-context-bootstrap -->
- Read these sections in `WORKFLOW_OPERATING_SYSTEM.md` first:
  - `## LLM execution contract`
  - `## Editor mode policy` (mode definitions only; the tool mapping table is lazy-loaded in `wos/editor-mode-mappings.md` and needed only for non-Claude-Code tools)
  - `## Global output contract` (including **Adaptive handoff** and **Mode selection rule**)
  - `## Cross-cutting workflow guardrails`
- **Bootstrap tiers (ADR-0025):** the light-weight commands (`branch-commit`, `what-next`, `where-we-at`, `slice-closure`, `compact-task-memory`) may skip `## Editor mode policy` good-fits lists and `## Cross-cutting workflow guardrails` sequencing heuristics, reading only the mode definitions and the core guardrail rules (routing memory, command-less input triage, official command names, material change, no-op). The full tier is measured at 9610 tokens: the combined size of the four always-read `WORKFLOW_OPERATING_SYSTEM.md` sections listed above. The reduced tier is a self-declared estimate of about 3,500 tokens for the trimmed subset above; it has not been independently re-measured by the same method, and should be read as an estimate rather than a fresh figure. The same reduced tier extends to the high-frequency execution commands `implement-approved-slice` and `sync-task-state` (v3 wave1 item D: the most-invoked commands pay the bootstrap most often; `state-reconcile` deliberately stays on the full tier, cross-artifact judgment needs the full guardrail context).
- **Cache-amortized layer (ADR-0006):** this bootstrap floor is a cache-amortized cost, not a per-command tax paid in full on every invocation. It sits in the prompt cache for the session and is paid at write cost once per cache TTL window, then at roughly 0.1x on cached reads inside that window. Account for it separately from any per-skill Load budget (the generated `.claude/skills/<name>/SKILL.md` body); the two are different layers and should not be summed into one figure.
- **Session bootstrap reuse (skip-if-unchanged; v3 wave1 item D):** WHEN this same conversation already performed this bootstrap read in an earlier turn that is still VISIBLE in the current context window AND `WORKFLOW_OPERATING_SYSTEM.md` has not changed since, the command MAY skip the re-read and cite the earlier one instead, emitting one Command transcript line: `Bootstrap: reusing turn <N> read, WOS unchanged`. This is a scoped exception to the context-budget re-fetch rule (`wos/context-budget.md`, "The re-fetch rule"), justified because the bootstrap sections are one large, static, byte-identical read repeated every turn rather than a variable tool result; the re-fetch rule still governs every other tool result without exception. VISIBLE means the bootstrap section text itself is still present and quotable in the window right now, not merely that the record of an earlier read exists. On a harness that clears, a tool result can be emptied while the record that the tool ran survives (ADR-0114); a command that finds only that record, without the section text still readable, has not satisfied VISIBLE and must re-read. Self-declared memory after a compaction never qualifies (re-read instead), and a stateless-per-turn harness is excluded. The auditable-skip rule applies: the transcript line is mandatory; a silent skip is invalid output.
- **Resolving a relative `wos/<topic>.md`.** Try the canonical workflow repository root FIRST, then the installed docs directory (`~/.claude/workflow-docs/wos/` or `~/.cursor/workflow-docs/wos/`). Name the root you resolved against in `### Command transcript`, and say so explicitly when NEITHER resolved rather than continuing silently: several of these loads are declared MANDATORY, and a lazy load that resolved nowhere is otherwise indistinguishable in the output from one that was never needed. Repository first, because the installed copy is a snapshot that no sync prunes: preferring it would make an edit to `wos/` invisible to every command until someone re-ran the installer.
- Read additional sections only when relevant to this command's role.
- Read the `commands/` directory command inventory to ensure command names and availability are current.
- Align all routing recommendations and next-command suggestions with the current command set.
- **Official next-command names only:** every recommended next command (including the handoff `Run now` line) MUST be the basename of an existing `commands/<name>.md` file in this workflow repository. Never invent names.

Required inputs:
- active task folder path
- TASK_STATE.md
- SOURCE_OF_TRUTH.md
- DECISIONS.md
- IMPLEMENTATION_PLAN.md
- latest relevant task artifacts
- current known task status

Task repository files to update:
- TASK_STATE.md

Operating rules:
- Do not implement production code.
- **Handoff:** end with the adaptive `### Handoff` block per `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full).
- **Substrate write protocol (per ADR-0034, K.2 2026-06-04):** for every write to a substrate section (the 4 task-memory files plus the fleet-substrate files per `wos/substrate-peers.md ## Fleet-substrate files`), emit the transaction header AND append one `.wos/VERIFICATION_LOG.jsonl` line per `commands/_shared/substrate-write-protocol.md`. Shadow mode at launch -- writers emit, no reader enforces.
- **Bounded slice-status propagation (opt-in, Slice-08 P2).** DEFAULT = OFF: with no propagation scope declared, this command writes ONLY `TASK_STATE.md` (its stated update scope above) and nothing else changes. Propagation fires ONLY when the run declares the bounded scope `propagate-slice-status=<subset of {IMPLEMENTATION_PLAN, SOURCE_OF_TRUTH, README, TEST_STRATEGY}>`; it is a bounded set of named siblings, never a global flag. For each named target write the bounded slice-status field (closed enum: `in-progress | implemented-pending-closure | closed | closed-with-followups | not-ready`) honoring its write regime:
  - Regime 1 (SUBSTRATE -- inline `<!-- wos:write owner=sync-task-state ... -->` header + one `.wos/VERIFICATION_LOG.jsonl` line reusing THIS run's run_id/ts): `IMPLEMENTATION_PLAN.md` sets the field on the `### Slice N` `Status:` line and LOGS the H3-scoped co-write at the owning `## Slices` H2; `SOURCE_OF_TRUTH.md` writes/extends the `## Slice status` H2 pointer with a header above that H2 and one JSONL line naming `section='## Slice status'` (`sha_after` a real 64-hex, never null on the applied write).
  - Regime 2 (PLAIN -- direct Edit only, NO wos:write header, NO JSONL line): `README.md` and `TEST_STRATEGY.md` are outside the substrate set and outside `scan-substrate-headers.sh`; a header there would be pointless drift.
  G5 state-reconcile drift detection stays intact: every Regime-1 write still emits its header + JSONL line, and the Regime-2 files stay out of the substrate scan.
- **Context-rot guardrail (ADR-0023):** before producing the output, estimate the current TASK_STATE.md token count (excluding the `## Compaction history` section). Compare against the phase threshold from `wos/context-budget.md ## Context-rot thresholds` (discovery: 3000; planning: 5000; implementation: 8000; review/closure/delivery: 6000). If current count exceeds the threshold, emit a single-line warning in `### Command transcript`: `WARN: TASK_STATE.md is ~Ntokens (phase threshold: Mthreshold). Consider running compact-task-memory before continuing.` The warning is INFORMATIONAL; proceed with the normal output. Suppress the warning if the immediately prior step was `compact-task-memory`.
- Treat TASK_STATE.md as the operational memory for the current task.
- Keep it concise, structured, and implementation-oriented.
- Reflect the current workflow truth based on:
  - latest approved plan
  - latest canonical decisions
  - latest review or test-strategy outputs
  - latest completed implementation or slice-closure step
  - latest `repo-consistency-sweep` pointer (if a SWEEP snapshot was written, preserve the `## Latest sweep` line or inline pointer under `## Risks to watch`; do not strip it during sync)
  - git-authority risk carry-forward: WHEN `## Risks to watch` carries a `Recommended action: git init -b main (requires human authorization)` line from `task-init`'s Git-authority preflight, preserve it across syncs until the resolution is confirmed (the codebase is a git repository) or an explicit human waiver is recorded; `sync-task-state` itself never runs git
- Do not restate broad historical analysis unless it still matters operationally.
- If TASK_STATE.md conflicts with newer approved artifacts, correct it explicitly.
- If the task state is unclear, say what evidence is missing instead of inventing it.
- Set **Work complexity** from current phase, blast radius, and the **next** recommended command (not from bravado). Use `N/A` only when the next step has no meaningful capability tradeoff. Never name model SKUs.
- **Post-commit delivery sync is handled by `branch-commit`:** when all slices are complete and committed, `branch-commit` auto-updates TASK_STATE.md phase to "delivered". A separate `sync-task-state` call solely to mark "delivered" after commit is unnecessary and should be skipped (see anti-pattern: redundant post-commit sync).
- **Quick reanchor maintenance (ADR-0111):** rebuild the `## Quick reanchor` block mechanically on every sync: Active decisions from the non-superseded D-N entries (one line each, truncated at a clause boundary such as a comma or semicolon, never a fixed word count; cap 10 with an explicit overflow line pointing at DECISIONS.md; `none locked yet` when empty), current slice from `IMPLEMENTATION_PLAN.md ## Slices`, phase and next step mirroring their own sections. Backfill: when a legacy task lacks the block, add it as the first H2 on this sync (same precedent as the Work complexity backfill below).
- Prefix each `## Canonical decisions` bullet with its D-N id, so reanchoring survives truncation and cross-checks stay mechanical (ADR-0111 free-rider).
- If **Work complexity (for next execution step)** is missing from `TASK_STATE.md` (for example older tasks created before that subsection existed), add the full subsection in this run using the same structure as `task-init` (heading, `LOW | MEDIUM | HIGH | N/A` line, and one-line rationale).

TASK_STATE.md must contain (template order, 20 sections per ADR-0111):
1. Quick reanchor (first H2 by design; see the maintenance rule above)
2. Task summary
3. Current phase
4. Objective
5. Requested deliverables (ledger per ADR-0056)
6. Recommended pipeline (per ADR-0025/ADR-0101)
7. Source of truth
8. Current known facts
9. Canonical decisions
10. Open questions / blockers
11. Last completed step
12. Current status
13. Active files in scope
14. Constraints / things that must not change
15. Risks to watch
16. Recommended next step
17. Resume notes
18. Task scope level
19. Current closure target
20. Work complexity (for next execution step): one of `LOW`, `MEDIUM`, `HIGH`, or `N/A`, plus a one-line rationale (definitions in `WORKFLOW_OPERATING_SYSTEM.md`)

Required output:
1. Whether TASK_STATE.md should be updated and why
2. Exact content for TASK_STATE.md
3. Recommended next command
4. Recommended editor mode
5. Why this is the correct next step
6. What should explicitly not be done yet

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
Follow `## Global output contract` in `WORKFLOW_OPERATING_SYSTEM.md` for `APPLIED` / `PROPOSED` / `SKIP` rules.

### Command transcript
<!-- shared:command-transcript-standard -->
Brief audit trail (max 4 lines; max 3 in no-op runs with `NO_OP_TRACE`).

### Handoff
<!-- shared:handoff-body -->
Use the adaptive ending format from `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full per session state).

### Definition of done (command output)
- `TASK_STATE.md` reflects the latest approved truth without inventing decisions.
- Any stale/contradictory state is called out explicitly with evidence pointers.
- `### Artifact changes` marks `TASK_STATE.md` as `APPLIED` only when persisting; otherwise `PROPOSED`.
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
Optimize for resumability, continuity, low ambiguity, and strict alignment with the latest approved task truth.

<!-- cache-breakpoint -->
