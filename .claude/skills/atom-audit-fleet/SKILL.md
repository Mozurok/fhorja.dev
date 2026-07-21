---
name: atom-audit-fleet
description: |-
  Orchestrator-workers variant of atom-audit. Dispatches N Haiku workers (3-5 atoms each) to audit every atom under packages/design-system/src/atoms/ in parallel against COMPONENT_GUIDELINES.md rules; merges per-worker rows into ATOM_AUDIT.md table. Use when atom count >= 6 (per cost-effectiveness threshold) AND COMPONENT_GUIDELINES.md exists. Do not use when atom count < 6 (use atom-audit single-agent), when COMPONENT_GUIDELINES.md is missing, or when only 1-2 atoms changed (use design-spec-review per-component).
metadata:
  category: execution-and-closure
  primary-cursor-mode: Ask
  multi-repo-aware: false
  context-layers-consumed:
    - memory
    - retrieved
  context-layers-produced:
    - memory
  tools:
    - Read
    - Write
    - Edit
    - Bash
    - Glob
    - Grep
    - Task
  x-wos-profiles:
    - full
  provenance: first-party
  token-budget: 4200
  suggested-model: claude-sonnet-4-6
  orchestrator: true
  workers:
    - role: atom-auditor
      tier: claude-haiku-4-5
      contract_ref: commands/_shared/worker-contract.md
  max_fanout: 20
  convergence:
    pattern: barrier
    timeout_ms: 600000
    partial_ok: true
  merge_strategy: union
  tags:
    - adr-0038
    - substrate-bullet-orphan
    - fleet-orchestrator
  worker_input_schema: |
    {
      "type": "object",
      "required": ["atom_paths", "guidelines_path"],
      "properties": {
        "atom_paths": {"type": "array", "items": {"type": "string"}, "minItems": 1, "maxItems": 5},
        "guidelines_path": {"type": "string"}
      }
    }
  worker_output_schema: |
    {
      "type": "object",
      "required": ["status", "rows"],
      "properties": {
        "status": {"enum": ["satisfied", "needs_revision", "max_iterations_reached", "failed", "interrupted"]},
        "rows": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["component", "memo", "callbacks", "inline_styles", "press_anim", "touch_target", "a11y", "reduced_motion", "changes_needed"],
            "properties": {
              "component": {"type": "string"},
              "memo": {"enum": ["pass", "warn", "fail", "n/a"]},
              "callbacks": {"type": "integer"},
              "inline_styles": {"type": "integer"},
              "press_anim": {"enum": ["pass", "warn", "fail", "n/a"]},
              "touch_target": {"enum": ["pass", "warn", "fail", "n/a"]},
              "a11y": {"enum": ["good", "partial", "missing"]},
              "reduced_motion": {"enum": ["pass", "warn", "fail", "n/a"]},
              "changes_needed": {"type": "integer", "minimum": 0}
            }
          }
        }
      }
    }
---

Act as a senior/staff design system orchestrator dispatching N atom-auditor sub-agents and synthesizing their partials into the canonical `ATOM_AUDIT.md` table.

Goal:
Audit every atom in `packages/design-system/src/atoms/` against `docs/research/COMPONENT_GUIDELINES.md` in parallel: dispatch N Haiku workers (3-5 atoms per worker), wait for convergence, merge their structured rows into `ATOM_AUDIT.md`. ~10x token reduction vs `atom-audit` single-agent expected when atom count >= 6, because Haiku per-token cost is much lower and the rule checks are mechanically schema-bounded.

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
- project workspace path
- path to atoms directory (default: `packages/design-system/src/atoms/`)
- path to COMPONENT_GUIDELINES.md (default: `docs/research/COMPONENT_GUIDELINES.md`)
- path to ATOM_AUDIT.md (default: `docs/research/ATOM_AUDIT.md`; created from `templates/ATOM_AUDIT.md` if absent)
- optional: explicit max_fanout override (defaults to 20)
- optional: explicit per-worker batch size (default 4; range 3-5)

Task repository files to update:
- ATOM_AUDIT.md (sole owner of merged result; the orchestrator is the SOLE writer per `wos/substrate-peers.md`)
- TASK_STATE.md `## Last completed step` per the canonical 5-section write pattern in `commands/_shared/task-state-slice-closure-pattern.md`
- `.wos/fleet-inbox/<run_id>/` directory (gitignored; one partial per worker)
- `.wos/VERIFICATION_LOG.jsonl` (one line per merged section + one per per-worker classification event)

Operating rules:
- **Handoff:** end with the adaptive `### Handoff` block per `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract`.
- **Step 1: Enumerate atoms.** List every directory under the atoms path. For each, locate the main component file (`<Name>/index.tsx` or `<Name>/<Name>.tsx`). Filter out non-atom artifacts (test files, story files, type-only files).
- **Step 2: Compute batches.** Partition atom paths into batches of `batch_size` (default 4). N batches = N workers. If N == 0, NO_OP_TRACE: nothing to audit. If N > `max_fanout`, STOP with NO_OP_TRACE listing the overflow; recommend running on a subdirectory first.
- **Step 3: Verify prerequisites.** Confirm COMPONENT_GUIDELINES.md exists; ATOM_AUDIT.md exists (or create from template). If COMPONENT_GUIDELINES.md is missing, NO_OP_TRACE and route to `design-bootstrap`.
- **Step 4: Verify tier guard.** Orchestrator runs Sonnet-class; workers run Haiku-class (both per the `suggested-model` frontmatter, not pinned in prose, so a model-generation bump updates one field instead of the body). Orchestrator tier >= worker tier per `wos/sub-agent-orchestration.md ## Tier-aware dispatch protocol`. PASS.
- **Step 5: Dispatch workers.** For each batch, invoke a stateless sub-agent via the host's primitive (Claude Code `Task` tool with `subagent_type: general-purpose` and a Haiku-class tier hint per `suggested-model`). Pass `task_input` matching `worker_input_schema`: `{atom_paths: [...], guidelines_path: "<path>"}`. Each worker MUST return its result via the `StructuredOutput` tool keyed `artifact=fleet-inbox/<run_id>/<worker_id>` (ADR-0038 Rule 1; prose `.partial.md` returns FORBIDDEN, a typed `.partial.json` is replay-only) per the worker contract.
- **Step 6: Each worker (instruction template).** Worker reads guidelines_path; for each atom in atom_paths, reads the main component file; mechanically checks: `memo` (is React.memo / forwardRef-memo wrap present? prop count threshold), `callbacks` (count of inline arrow callbacks not wrapped in useCallback), `inline_styles` (count of object-literal style={{...}}), `press_anim` (useAnimatedPress vs useState transform if press handler present), `touch_target` (44pt iOS / 48dp Android minimum if interactive), `a11y` (accessibilityRole + accessibilityLabel for icon-only buttons + accessibilityState for interactive variants), `reduced_motion` (useReducedMotion() check if transform/translate animation). Sum failing rules into `changes_needed`. Return `{status: "satisfied", rows: [...]}`.
- **Step 7: Wait for convergence.** Barrier pattern: wait for all N workers to terminate OR `timeout_ms` (10 min default) to elapse. Read all files in `active/<task>/.wos/fleet-inbox/<run_id>/`. Classify per `commands/_shared/convergence-policy.md` failure table.
- **Step 8: Merge.** Apply `union` merge strategy: collect all rows from all surviving partials; deduplicate by `component` key (each atom audited by exactly one worker; duplicates would indicate a bug -- log `event=fleet-merge` warning with `partials=[...]`). Sort rows by `changes_needed` descending then `component` ascending (highest-impact fixes surface first).
- **Step 9: Write ATOM_AUDIT.md.** Emit transaction header above the table section; replace the `## Summary Table` section content with the merged rows; append a new row to `## Audit history` with date + total `changes_needed` sum + cleared delta vs previous run.
- **Step 10: Emit VERIFICATION_LOG.jsonl.** One line per per-worker classification event (`event=merge_include`, `event=worker_failed`, `event=worker_timeout`, etc.) plus one line for the merged section (`event=fleet-merge`, `partials=[worker_id, ...]`, `strategy=union`).
- **Step 10.5: Scan substrate orphans (ADR-0038 Rule 3 gate).** After the substrate write in Step 9 and the VERIFICATION_LOG emission in Step 10, invoke `python3 scripts/scan-substrate-orphans.py <ATOM_AUDIT.md path> <TASK_STATE.md path>` against every file this command touched. On non-zero exit code: roll back the `## Summary Table` section replacement in `ATOM_AUDIT.md` (restore the pre-write snapshot), append a line `event=orphan_detected` (with `files=[...]` and `exit_code=<n>`) to `.wos/VERIFICATION_LOG.jsonl`, and return NO_OP_TRACE routing to manual repair per `wos/bug-classes/substrate-bullet-orphan.md`. On exit code 0, proceed to Step 11. The orphan-scan gate is non-negotiable per ADR-0038 Rule 3.
- **Step 11: Update TASK_STATE.md.** Per the canonical 5-section write pattern. Include the audit summary: total atoms audited, total changes_needed, top-3 fix groupings (rules with most failing atoms).
- Workers NEVER write substrate, because parallel workers writing the same file would race and corrupt the merged result and scramble provenance; routing every write through the orchestrator's one apply step keeps the merge deterministic and attributable (ADR-0038 Rule 2). The orchestrator is the SOLE writer of `ATOM_AUDIT.md`.
- Do NOT implement fixes here. This command produces the audit only; fixes flow through normal slice pipeline (`task-init` per fix grouping -> `impact-analysis` -> `implementation-plan` -> `implement-approved-slice`).
- If COMPONENT_GUIDELINES.md added a new rule not represented in the worker_output_schema columns, NO_OP_TRACE: route to a schema-extension slice first (worker_output_schema update + ATOM_AUDIT.md column add).

Required output:
1. Atom count enumerated + batch breakdown (N workers, atoms per worker)
2. Dispatch summary: N dispatched, M satisfied, K needs_revision, L failed, P interrupted, T timed out
3. Merge summary: total rows merged, dedup count, conflict count
4. Per-rule failure breakdown: which rules have most failing atoms
5. Top 3 suggested fix groupings (each a candidate slice for `task-init`)
6. Path to the updated ATOM_AUDIT.md
7. Recommended next command (typically `task-init` for the highest-priority fix grouping)

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
- Every atom under the atoms path has exactly one row in the merged ATOM_AUDIT.md table.
- Every rule from COMPONENT_GUIDELINES.md is represented as a column; new rules trigger NO_OP_TRACE schema-extension routing.
- `changes_needed` integer per row matches the count of failing rules in that row.
- Audit history row appended for this run with date + total + cleared delta.
- Top 3 fix groupings suggested in the output (NOT in the file).
- Worker contract violations explicitly listed in `### Command transcript`.
- No code fixes applied by this command; output explicitly says "produces audit only, fixes flow through task-init".
- Substrate peer rule respected: ATOM_AUDIT.md `## Summary Table` and `## Audit history` are owned by this command per the substrate ownership matrix (folded entry added in K.2 retrofit; until then, this command is the de-facto owner via `templates/ATOM_AUDIT.md` convention).
- `scan-substrate-orphans.py` exit code 0 on every touched file (ATOM_AUDIT.md, TASK_STATE.md). A non-zero exit blocks completion, triggers Step 10.5 rollback, and routes to manual repair per `wos/bug-classes/substrate-bullet-orphan.md`.
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
This is the J.6 PILOT -- the first real orchestrator under ADR-0034, now also bound by ADR-0038 (Workflow tool as canonical parallel-orchestration primitive). The three ADR-0038 rules apply: (1) structured output is mandatory (enforced via `worker_output_schema`), (2) substrate writes sequence through a deterministic apply step (Step 8 merge + Step 9 sole-writer replace), (3) the apply step MUST detect and prevent the substrate-bullet-orphan failure class per `wos/bug-classes/substrate-bullet-orphan.md` -- gated by Step 10.5 invoking `scripts/scan-substrate-orphans.py`. If the orchestrator cannot determine which row belongs to which atom (duplicate `component` keys across partials, or atom not represented), it refuses to write that row and flags the ambiguity in `### Command transcript`. Silent dropping is forbidden. The pilot is the eval-baseline for K.7 -- the harness compares this command's output against `atom-audit` single-agent on identical inputs to validate the ~10x cost-reduction claim.

<!-- cache-breakpoint -->
