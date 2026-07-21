---
name: capture-observation
description: |-
  Append a single observation, question, hypothesis, or concern to TASK_STATE.md as task memory without disrupting in-progress work or requiring a full state sync. Lean append-only; never restructures other artifacts. Use when something surfaces mid-work that should be remembered for later (during planning, implementation, or review), when you noticed something not actionable now but should not be lost, when you want to log a hypothesis to validate before closure, or when a small concern does not justify decision-interview or targeted-questions but deserves to be on record. Do not use when the observation is a canonical decision (use decision-interview or sync-task-state), invalidates the current direction (use direction-adjust), requires several artifact changes (use sync-task-state or state-reconcile), or when there is no active task folder yet (run task-init first).
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
    - core
    - full
  provenance: first-party
  token-budget: 2700
  suggested-model: claude-haiku-4-5
---

Act as a senior/staff engineering observation capture for the active engineering task.

Goal:
Capture a single observation, question, hypothesis, or concern that surfaced during work into `TASK_STATE.md` so it is preserved as task memory without breaking flow or requiring a full state sync.

Mandatory context bootstrap (before any output):
<!-- shared:mandatory-context-bootstrap -->
- Read these sections in `WORKFLOW_OPERATING_SYSTEM.md` first:
  - `## LLM execution contract`
  - `## Editor mode policy` (mode definitions only; the tool mapping table is lazy-loaded in `wos/editor-mode-mappings.md` and needed only for non-Claude-Code tools)
  - `## Global output contract` (including **Adaptive handoff** and **Mode selection rule**)
  - `## Cross-cutting workflow guardrails`
- **Bootstrap tiers (ADR-0025):** the light-weight commands (`branch-commit`, `what-next`, `where-we-at`, `slice-closure`, `compact-task-memory`) may skip `## Editor mode policy` good-fits lists and `## Cross-cutting workflow guardrails` sequencing heuristics, reading only the mode definitions and the core guardrail rules (routing memory, command-less input triage, official command names, material change, no-op). This reduces bootstrap from ~6,750 to ~3,500 tokens for these commands.
- Read additional sections only when relevant to this command's role.
- Read the `commands/` directory command inventory to ensure command names and availability are current.
- Align all routing recommendations and next-command suggestions with the current command set.
- **Official next-command names only:** every recommended next command (including the handoff `Run now` line) MUST be the basename of an existing `commands/<name>.md` file in this workflow repository. Never invent names.

Required inputs:
- active task folder path
- TASK_STATE.md (must already exist)
- the observation itself (one to three lines, free form)
- optional: tag classifying the observation (`question` | `hypothesis` | `concern` | `note`)

Task repository files to update:
- TASK_STATE.md (append-only, in the `Open questions / blockers` section or a new `Observations` section if not present)

Operating rules:
- Do not implement production code.
- Do not interpret, paraphrase, or expand the observation. Capture verbatim with light formatting.
- Do not trigger reasoning, analysis, or follow-up questions. The point of this command is fast capture, not exploration.
- **Handoff:** end with the adaptive `### Handoff` block per `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full). Default `Run now`: read TASK_STATE.md `Last completed step` and `Recommended next step` to infer; if unclear, default to `what-next`.
- **Substrate write protocol (per ADR-0034, K.2 2026-06-04 -- dogfood).** MANDATORY for every write to `TASK_STATE.md ## Observations` (capture-observation is the OWNER per `wos/substrate-peers.md`; this is the only true append-only freeform section in the matrix). Per `commands/_shared/substrate-write-protocol.md ## Concrete computation`:
  1. Compute `sha_before` via the canonical `sha_of_section` bash helper (`null` ONLY on the first observation captured in this task; subsequent appends compute against the existing section bytes).
  2. Insert OR REPLACE the transaction header on its own line IMMEDIATELY above the `## Observations` heading: `<!-- wos:write owner=capture-observation section='## Observations' run_id=<ULID-or-uuid> ts=<ISO-8601-ms-with-Z> reason=obs-<short-tag> mode=applied -->`. Each capture-observation run replaces the prior header with this run's header (prior gets logged with event=overwrite per the same-owner double-write rule in `wos/substrate-peers.md ## Conflict resolution`).
  3. Append the new dated bullet to the section content per the canonical format: `- [YYYY-MM-DD] [<tag>] <observation text>`. Never edit prior bullets.
  4. Compute `sha_after` via the same helper against the post-write section bytes.
  5. Append exactly one JSON line to `active/<task>/.wos/VERIFICATION_LOG.jsonl` per the 12-field schema in `wos/substrate-peers.md ## Audit trail`. `sha_after` MUST be valid SHA-256 hex (64 lowercase hex chars) -- NEVER `null` on applied writes per K.5 validator. `sha_before` is `null` ONLY on the first observation captured for the task.
  6. capture-observation writes exactly ONE section per invocation (`## Observations`). The protocol does not multi-section here.

  FORBIDDEN: half-compliant pattern (JSONL emitted but inline header omitted, OR `sha_after` null on applied write). K.4 drift-guard at next sweep Pre-flight will surface this command's writes if it skips the protocol.
- If `TASK_STATE.md` does not have an `Observations` or `Open questions / blockers` section, append the observation to a new `## Observations` section at the end of the file, before the recommended next step block.
- Use a dated bullet format: `- [YYYY-MM-DD] [<tag>] <observation>`. Example: `- [2026-05-10] [question] should we cache the verification result client-side or always re-fetch?`
- Treat task-memory write policy per `WORKFLOW_OPERATING_SYSTEM.md`: `PROPOSED` in Ask mode, `APPLIED` only in Agent mode.
- This command must not modify any other section of `TASK_STATE.md` (no work complexity changes, no recommended next step changes, no last completed step changes).
- Output is intentionally minimal. Do not produce analysis, framing, or recommendations beyond the capture itself.
- **Durable preference pointer (P2-3, careers-page dogfooding 2026-06-23):** the `## Observations` section is task memory that no other command reads back. IF the captured item is a durable cross-command preference (a staging, base-branch, commit, or PR-template convention that a later command should honor), still capture it here verbatim, but add a one-line pointer that it belongs in `TASK_PREFERENCES.md` (which delivery commands consume). Do not write `TASK_PREFERENCES.md` yourself; this command stays single-section and append-only.

Required output:
1. The observation as it will be appended (verbatim with applied dating and tag formatting).
2. The exact line(s) being added to `TASK_STATE.md`.
3. The location in `TASK_STATE.md` where they will be inserted (existing section vs new section).
4. Reminder that no other state changed.
5. Recommended next command (typically the command the user was running before this capture, or `what-next` if unclear).
6. Recommended editor mode for that next command.
7. Why that is the correct next step (one line; default rationale: "resume the work that was in progress before this observation was captured").

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
- List files in `my_work_tasks/` that would change, or `None`.
- For each file, mark `APPLIED` / `PROPOSED` / `SKIP` and follow the task-memory write policy in `WORKFLOW_OPERATING_SYSTEM.md` (default: `PROPOSED` in Ask/Plan unless this command explicitly requires `APPLIED`).
- Default for this command: `PROPOSED` patch on `TASK_STATE.md` only.

### Command transcript
<!-- shared:command-transcript-lean -->
Brief audit trail (max 3 lines; max 2 in no-op runs with `NO_OP_TRACE`).

### Handoff
<!-- shared:handoff-body -->
Use the adaptive ending format from `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full per session state).

### Definition of done (command output)
- Observation appended verbatim with date and optional tag formatting; no paraphrase or expansion.
- Only `TASK_STATE.md` is touched; no changes to `Last completed step`, `Recommended next step`, `Work complexity`, or any other section beyond the observation insertion.
- `Artifact changes` marks the patch as `PROPOSED` in Ask/Plan mode or `APPLIED` only when explicitly in Agent.
- `Handoff` block is complete per the adaptive format in `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract`; ending after the artifact change without a Handoff is invalid output.
- `Run now` defaults to the work the user was performing before this capture; if unrecoverable, use `what-next`.
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
Optimize for speed of capture, fidelity to the user's wording, minimal disruption to in-progress work, and resumability of whatever the user was doing before triggering capture.

<!-- cache-breakpoint -->
