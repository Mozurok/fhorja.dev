---
name: implement-slice-complement
description: |-
  Execute a bounded micro-delta (adjustments, fixes, polish, missed checklist items) that stays inside the same slice intent and the locked decisions, then record evidence in slice notes without churning unrelated artifacts. Use when a slice is implemented or ready-to-close-with-follow-ups, you found a narrow gap (bug, typo, test, log line, copy, small refactor under the same acceptance story), and you can state it as a numbered micro-delta list over a small named file set. Do not use when the work is net-new scope (use implementation-plan plus a new slice), when correctness-critical ambiguity is open (use targeted-questions or decision-interview), when it would materially alter signed-off decisions (use post-review-pivot), when only memory needs updating (use sync-task-state), or when only closure judgment is needed (use slice-closure).
metadata:
  category: "execution-and-closure"
  primary-cursor-mode: "Agent"
  multi-repo-aware: "false"
  context-layers-consumed: "memory"
  context-layers-produced: "memory"
  tools: "Read, Write, Edit, Bash, Glob, Grep"
  x-wos-profiles: "minimal, core, full"
  provenance: "first-party"
  suggested-model: "claude-sonnet-5-5"
---

Act as a senior engineer applying a **small, explicit follow-up** to work that already belongs to a slice (or was completed under one), without treating the change as a new slice or reopening full slice planning.

Goal:
Execute a bounded **micro-delta** (adjustments, fixes, polish, missed checklist items) that stays inside the **same slice intent** and `DECISIONS.md`, then record evidence in slice notes, in `TASK_STATE.md` routing, or in both without churning unrelated artifacts.

This is the typical successor for authoring the test files `test-strategy.md` names (a mechanical translation of already-locked behavior into test code, no new design work) when `test-strategy.md` itself stops short of writing them. When the named test scenarios require new design decisions instead, use another `implement-approved-slice` round.

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
- active task folder path
- **anchor slice**: `SLICES/<NN>_<slice-slug>.md` path **or** explicit slice id + slug from `IMPLEMENTATION_PLAN.md`
- **micro-delta list**: 1-7 bullets, each one outcome-oriented (what will be true after the change)
- **primary file paths** (expected touch set; typically ≤ 6 files unless you justify briefly)
- `TASK_STATE.md`, `DECISIONS.md`, `IMPLEMENTATION_PLAN.md`
- relevant real codebase context
- product workspace path if implementation is outside the task repository

Task repository files to create or update (only if materially changed):
- the anchor slice file (add a **Complement** subsection: deltas, validation, residual risks): `APPLIED`
- `TASK_STATE.md` only if routing/blockers change; otherwise prefer `sync-task-state` after execution

Operating rules:
- Treat the micro-delta list as **hard scope**: anything outside it is out of scope for this command.
- **Handoff:** end with the adaptive `### Handoff` block per `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full).
- **Operating mode (ADR-0008, ADR-0162).** WHEN `TASK_STATE.md ## Resume notes` contains `Operating mode: minimal`, `strict`, `teaching`, or `assisted`, load `wos/operating-modes.md` and apply that mode. WHEN the line is absent, use this command's native rules. Auto-suggestion is not a declaration.
- **Net-new admission check (before editing, per the careers-page dogfooding 2026-06-23):** compare each micro-delta against the anchor slice's intent AND the plan's deferred / out-of-scope / later-milestone items. IF a delta matches a deferred milestone or introduces net-new behavior (make a deferred feature functional, add an animation, integrate a new data source, add a screen or endpoint), it is NOT a micro-delta: REFUSE before editing, name the matched deferred item, and route to `implementation-plan` (new slice) or `direction-adjust`. Net-new work arriving phrased as a complement request is the exact case this gate exists to catch; the mid-execution spill check below does not, because it only fires once editing has already started.
- If execution reveals the list was too small and work **spills** into new behavior mid-edit, **stop**, summarize the spill, and hand off to `implementation-plan` or `implement-approved-slice` (do not silently expand).
- Do not invent new slice ids; you are complementing an **existing** slice narrative.
- **This command owns the post-review fix leg (mobile dogfood 2026-07-29).** A batch of fixes answering review findings (a local review pass, PR bot comments, CI) that stays inside the anchor slice's intent belongs here, one invocation per batch, each leaving its record in the slice notes. The upstream step is `pr-feedback-ingest`, which turns the raw feedback into a traceable backlog; this command executes a bounded slice of that backlog. The failure this closes is not a missing command but skipped routing: on the source run the review-and-fix leg ran about 20 hand-applied fixes across 12 hours with no command driving it and no record written, and task memory ended up asserting the opposite of the truth about whether the work could ship. A fix batch with no recorded owner is how a long session loses its state.
- Prefer the smallest diff; no drive-by refactors.
- Honor the YAGNI restraint ladder the plan applied (exist, stdlib, native, installed dep, one line, minimum viable; defined in full in `implementation-plan`): the micro-delta adds no abstraction, config, or dependency the slice does not already require.
- Set **work complexity** for this run realistically (often `LOW`, sometimes `MEDIUM`); never name model SKUs. If the complement touches auth, tenancy, migrations, or crypto paths, bias **up** per `WORKFLOW_OPERATING_SYSTEM.md`.
- After changes, summarize: files touched, validation run, what was intentionally unchanged, residual risks.
- No-op rule: if the micro-deltas are already satisfied on disk, return **no-op** with `NO_OP_TRACE` and route to `slice-closure` or `sync-task-state`.
- **Verification divergence check (cross-reference).** The same rule in `implement-approved-slice` applies here: WHEN a verification check's expected value differs from its actual value, implement-slice-complement SHALL require an explanation before treating the check as passed.
- **Layer-2 coverage of the commit this run produces (worktree dogfood 2026-08-04).** WHEN this run produces a commit newer than the Layer-2 verdict cited in the slice notes, the run SHALL record `Layer-2 coverage: <named case per wos/closure-floors.md>` or `Layer-2 coverage: none, routes to review-hard`. Writing `inherits` without one of the two is invalid output: this command owns the post-review fix leg, so it is where an unreviewed commit most often enters a slice already treated as reviewed.

Required output:
1. Restated anchor slice + micro-delta list + path list
2. Work complexity for this run (`LOW` | `MEDIUM` | `HIGH` | `N/A`) and one line why
3. Execution summary vs the list (checkbox mapping)
4. Proposed slice complement notes (or `NO_CHANGE` with rationale)
5. Recommended next command
6. Recommended editor mode
7. Why this is the correct next step
8. What should explicitly not be done yet
9. Net-new admission verdict: `micro-delta` (proceed) or `net-new` (refused and routed), with the deferred-item / new-behavior check that justifies it. Emit before any edit; this is what makes the admission check non-skippable.

### Reference grounding (execution gate)
**Reference grounding (execution gate).** Before editing any file in this slice you MUST ground every external contract in captured references. This gate is mandatory, not advisory.

1. Detect. Scan the slice's imports and its diff for any external library, SDK, API, or documented protocol (anything not defined inside this repository). The language or runtime standard library (for example `node:*` modules, the Python stdlib, the platform's built-in globals) is part of the runtime, not an external contract, and is exempt from detection; only third-party libraries, SDKs, APIs, and documented external protocols require capture. A target platform's or engine's own documented built-in API (a game engine's engine classes when the task targets that engine, similarly for other platform SDKs) is exempt the same way, when the relevant `wos/<platform>-*.md` topic already cites the official docs for it; a genuinely third-party addon or library added on top of the platform is never exempt. A slice whose imports and diff stay entirely internal, stdlib-only, or platform-built-in-only is exempt: skip the rest of this gate and proceed.

2. Apply the rest (lazy-loaded; `wos/reference-grounding.md`). WHEN step 1 finds an external contract, load `wos/reference-grounding.md` before you edit and apply every rule there exactly as written. It carries: refuse when uncaptured, read and cite when captured, design assets as contracts (ADR-0051), live-verify a security-critical or fully-gating contract (ADR-0108), and the two claim-keyed tests (ADR-0109 D-9, ADR-0146). This load is CONDITIONAL on step 1: a slice that touches no external contract has nothing to ground and loads nothing. The execution summary SHALL cite which rules were read and applied (G3 safeguard).
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
- Every micro-delta bullet is addressed or explicitly deferred with evidence.
- Changes remain inside `DECISIONS.md` and the anchor slice intent; spills route outward instead of silent scope growth.
- Slice complement notes are `APPLIED`; product edits follow repo reality.
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
Optimize for **continuity**: small, reviewable deltas with a clear audit trail back to the slice they complement.
