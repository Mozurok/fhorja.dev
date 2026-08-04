---
name: implement-slice-complement
description: |-
  Execute a bounded micro-delta (adjustments, fixes, polish, missed checklist items) that stays inside the same slice intent and DECISIONS.md, then record evidence in slice notes and/or TASK_STATE.md without churning unrelated artifacts. Use when a slice was already implemented or is ready-to-close-with-follow-ups and you discovered a narrow gap (bug, typo, test, log line, copy, small refactor under the same acceptance story), you can state the work as a numbered micro-delta list, and the file touch set is small with named primary paths. Do not use when work belongs to net-new scope (use implementation-plan plus a new slice), correctness-critical ambiguity is open (route upstream to targeted-questions or decision-interview), the change would materially alter signed-off decisions (use post-review-pivot), only state memory needs updating (use sync-task-state), only closure judgment is needed (use slice-closure), or the micro-delta list is empty or vague.
metadata:
  category: execution-and-closure
  primary-cursor-mode: Agent
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
  suggested-model: claude-sonnet-4-6
---

Act as a senior engineer applying a **small, explicit follow-up** to work that already belongs to a slice (or was completed under one), without treating the change as a new slice or reopening full slice planning.

Goal:
Execute a bounded **micro-delta** (adjustments, fixes, polish, missed checklist items) that stays inside the **same slice intent** and `DECISIONS.md`, then record evidence in slice notes and/or `TASK_STATE.md` routing without churning unrelated artifacts.

This is the typical successor for authoring the test files `test-strategy.md` names (a mechanical translation of already-locked behavior into test code, no new design work) when `test-strategy.md` itself stops short of writing them. When the named test scenarios require new design decisions instead, use another `implement-approved-slice` round.

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
- **anchor slice**: `SLICES/<NN>_<slice-slug>.md` path **or** explicit slice id + slug from `IMPLEMENTATION_PLAN.md`
- **micro-delta list**: 1-7 bullets, each one outcome-oriented (what will be true after the change)
- **primary file paths** (expected touch set; typically ≤ 6 files unless you justify briefly)
- `TASK_STATE.md`, `DECISIONS.md`, `IMPLEMENTATION_PLAN.md`
- relevant real codebase context
- product workspace path if implementation is outside `my_work_tasks`

Task repository files to create or update (only if materially changed):
- the anchor slice file (add a **Complement** subsection: deltas, validation, residual risks): `PROPOSED` unless persisting in Agent mode
- `TASK_STATE.md` only if routing/blockers change; otherwise prefer `sync-task-state` after execution

Operating rules:
- Treat the micro-delta list as **hard scope**: anything outside it is out of scope for this command.
- **Handoff:** end with the adaptive `### Handoff` block per `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full).
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
<!-- shared:reference-grounding -->
**Reference grounding (execution gate).** Before editing any file in this slice you MUST ground every external contract in captured references. This gate is mandatory, not advisory.

1. Detect. Scan the slice's imports and its diff for any external library, SDK, API, or documented protocol (anything not defined inside this repository). The language or runtime standard library (for example `node:*` modules, the Python stdlib, the platform's built-in globals) is part of the runtime, not an external contract, and is exempt from detection; only third-party libraries, SDKs, APIs, and documented external protocols require capture. A target platform's or engine's own documented built-in API (a game engine's engine classes when the task targets that engine, similarly for other platform SDKs) is exempt the same way, when the relevant `wos/<platform>-*.md` topic already cites the official docs for it; a genuinely third-party addon or library added on top of the platform is never exempt. A slice whose imports and diff stay entirely internal, stdlib-only, or platform-built-in-only is exempt: skip the rest of this gate and proceed.

2. Refuse when uncaptured. IF the slice uses an external contract that is not present in `projects/<client>__<project>/REFERENCES.md`, you MUST NOT edit. Stop, name the missing contract in one short refusal block, and route the user to `capture-references` to capture it (official docs, signature, version). This holds in every task tier. Do not fetch the web here; `capture-references` is the only authorized capture path.

3. Read and cite when captured. WHEN the contract is present in `REFERENCES.md`, read that entry (including any `Implementation contract` block) before you write code, and emit a `Grounded in:` line in the execution summary naming each `REFERENCES.md` entry or local doc you relied on. An edit that touches an external contract without a `Grounded in:` line is invalid output. This cite requirement is NOT conditional on capture: WHEN the thing you relied on is the dependency's own published source rather than a captured entry or a doc (the tier rule 6 admits), the `Grounded in:` line SHALL name the file path, the line range, and the version you read, whether or not that library also has a `REFERENCES.md` entry. Rule 6's case reaches here even when rule 1 stayed silent and the contract was never captured. A bare claim of having read the source is not a cite: every other tier produces a referent a reviewer can open, and this one is held to the same bar (ADR-0121, ADR-0109).

4. Design assets are external contracts too (ADR-0051). WHEN this slice implements from a design source (Figma node, screen, or component spec), pull the exact node via the design MCP (`get_design_context` / `get_screenshot` / `get_variable_defs`, `download_assets` for real assets) BEFORE editing and build from the pulled values: no placeholder boxes, guessed measurements, or assumed copy. Design-to-code slices are NOT exempt when imports are internal. IF the node is unavailable, stop and ask for the link. Placeholders need an approved `Asset-fidelity: placeholder` decision in `IMPLEMENTATION_PLAN.md`.

Do not implement an external API from memory. WHEN the captured entry and your recollection disagree, the captured entry wins (per `WORKFLOW_OPERATING_SYSTEM.md` `## Evidence priority`).

5. Live-verify a security-critical or fully-gating contract before it satisfies this gate (ADR-0108). A captured `REFERENCES.md` entry does NOT satisfy this gate on its own when BOTH of the following hold: (a) the contract governs a security-critical or fully-gating path (authentication, authorization, payment, PII handling, or any point where a wrong assumption blocks 100% of a code path rather than an edge case), AND (b) the only evidence for the exact point in question is a vendor's demo/example/sandbox payload (not a live capture of the real production delivery mechanism) OR the captured entry itself marks the point `[unclear in source]` or otherwise documents it as unconfirmed. WHEN both hold, you MUST NOT implement against the assumed shape until either a live capture (a real request/response from the actual mechanism, e.g. via a webhook capture endpoint, a sandbox call with real credentials, or a vendor support confirmation) replaces the inference, OR the assumption and its accepted risk are recorded as an explicit, named entry via `decision-interview` rather than silently built into the code. This closes the gap the 2026-07-15 tms-webhook-integration dogfood exposed: a captured reference existed and was cited, but it was evidenced only by the vendor's demo payload, and the auth-format point was already marked unconfirmed in the same reference set, yet implementation proceeded and shipped a code path that could never authenticate a real request.

6. Claim-keyed boundary test, additive to the import scan (ADR-0109, D-9). The scan in rule 1 fires on the slice's import-and-diff surface. A SECOND test fires on a load-bearing claim regardless of whether the import surface changed: WHEN you are about to assert behavior of an external library, SDK, API, or documented protocol as a basis for the edit (which version returns what, which default changed, which parameter is required), that claim MUST trace to the grounded set (a captured `REFERENCES.md` entry, a doc read this session, the dependency's own published source read this session, or a live capture per rule 5), or you MUST NOT rely on it. The published-source tier (ADR-0121) exists for the case the other tiers cannot reach: a point the vendor's documentation simply does not state, which a captured entry records as `[unclear in source]` and which does not warrant rule 5's live capture. It is ADDITIVE and never an escape hatch: rule 2 is unchanged, so an external contract absent from `REFERENCES.md` still stops the edit and still routes to `capture-references`, and reading source is not a substitute for capturing it. Cite it per rule 3. The two tests are complementary and neither replaces the other. The case each catches: rule 1 catches a NEW external contract entering via a changed import; this rule catches a fix INSIDE a library the repository already imports, where the import surface is unchanged (rule 1 stays silent) but the claim about that library's runtime behavior is outside the grounded set. For a bug fix in an already-imported library, rule 1 does not fire and this rule does. The full doctrine is `wos/active-epistemic-humility.md` and the universal block `commands/_shared/claim-grounding.md`; this rule is its execution-time face inside the grounding gate.

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
- Every micro-delta bullet is addressed or explicitly deferred with evidence.
- Changes remain inside `DECISIONS.md` and the anchor slice intent; spills route outward instead of silent scope growth.
- Slice complement notes are `PROPOSED` unless persisting in Agent mode; product edits follow repo reality.
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
Optimize for **continuity**: small, reviewable deltas with a clear audit trail back to the slice they complement.

<!-- cache-breakpoint -->
