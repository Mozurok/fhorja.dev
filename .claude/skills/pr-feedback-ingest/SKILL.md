---
name: pr-feedback-ingest
description: |-
  Turn PR feedback (Greptile, CI, bots, humans) into a structured traceable backlog aligned with TASK_STATE.md, DECISIONS.md, and IMPLEMENTATION_PLAN.md so the next execution step can be a narrow implement-approved-slice or a small planning touch without losing alignment. Corrective scope only. Use when a PR is open or updated and review feedback exists, you want to map each feedback item to files/slices/task-memory updates before coding, or feedback is mostly corrective (bugs, style, missing tests, wrong field usage) under existing scope. Do not use when feedback requires a new product direction or contract (use post-review-pivot first then replan), no active task folder exists, there is no feedback payload to ingest (paste, export, or link summary), or only TASK_STATE.md drift exists without new PR signals (use state-reconcile or sync-task-state). Gated opt-in modes, off by default: --playtest (ADR-0069) ingests Godot playtest notes; --mcp-pull (ADR-0082) pulls feedback through a vetted MCP.
metadata:
  category: delivery-and-communication
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
  x-wos-profiles:
    - core
    - full
  provenance: first-party
  token-budget: 2600
  suggested-model: claude-sonnet-4-6
---

Act as a senior/staff engineer consolidating **pull-request review feedback** (including automated tools such as **Greptile** and GitHub inline comments) into task memory and an actionable correction plan aligned with the **current** decisions and implementation plan.

Goal:
Turn PR feedback into a structured, traceable backlog that matches `TASK_STATE.md`, `DECISIONS.md`, and `IMPLEMENTATION_PLAN.md`, so the next execution step can be a narrow `implement-approved-slice` (or a small planning touch) without losing alignment.

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
- PR identifier (URL and/or number) and branch names if known
- feedback payload: Greptile summary, GitHub review comments, check annotations, or a consolidated paste
- `TASK_STATE.md`
- `SOURCE_OF_TRUTH.md`
- `DECISIONS.md`
- `IMPLEMENTATION_PLAN.md`
- optional: `SLICES/*.md`, `TEST_STRATEGY.md`, `PR_PACKAGE.md`, `INVARIANTS_AND_NON_GOALS.md`
- optional: `git diff <base>...HEAD` or `--stat` when tying comments to the diff
- optional: `--playtest` to ingest playtest notes (a tester's observations of a Godot build) instead of PR feedback (DECISIONS D-2, ADR-0069; off by default, corrective scope only)
- optional: `--mcp-pull` to pull PR review threads through a vetted, connected code-review or issue-tracker MCP instead of a pasted payload (DECISIONS D-1..D-4 of the 2026-07-03 mcp-integrations task; off by default, corrective scope only)

Operating rules:
- Do not implement production code in this command.
- **Handoff:** end with the adaptive `### Handoff` block per `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full).
- Tag each ingested item with **source** and **severity** (`must-fix` | `should-fix` | `nit` | `question` | `out-of-scope`).
- Map each `must-fix` / `should-fix` to: target path(s), slice id if any, and whether it fits an **existing approved slice** or needs a **new** slice proposal.
- If an item conflicts with `DECISIONS.md`, stop treating it as a simple fix: mark `question`, route to `decision-interview` or `post-review-pivot` in the handoff.
- Deduplicate repeated Greptile vs human comments; keep one canonical row per underlying issue.
- **Bug-class candidate detection (meta-learning):** after building the feedback matrix, compare each `must-fix` or `should-fix` finding against the current bug-class library (`wos/bug-classes/*.md`). If a finding does not match any existing class's `## Trigger` description, flag it as a **candidate template** in a dedicated output section (see below). This closes the learning loop: findings that `repo-consistency-sweep` would have missed become candidates for new bug-class templates, growing the library from real evidence.
- **Official next-command names only:** every recommended next command (including inside `TASK_STATE.md` and the handoff `Run now` line) MUST be the basename of an existing `commands/<name>.md` file in this workflow repository. Never invent names.
- Set **work complexity** for the **next** step from the density of `must-fix` items (definitions in `WORKFLOW_OPERATING_SYSTEM.md`). Never name model SKUs.
- If ingestion would not materially change task memory or routing, return **no-op** with `NO_OP_TRACE`.
- **Playtest-feedback mode (gated, off by default; DECISIONS D-2, ADR-0069; routing hardened by ADR-0084).** When invoked with `--playtest`, the payload is a tester's playtest notes for a Godot build rather than PR review feedback, and the command produces the same traceable feedback matrix with `source` tagged `playtest`. This mode is the designated destination for playtest feedback: `godot-runtime-verify` routes the operator's playtest notes here from its `PLAYTEST_RUNBOOK.md` handoff, and `review-hard` routes playtest-shaped args here rather than absorbing them (ADR-0084), so the loop no longer depends on the operator discovering the flag. The same severity scale and the same conflict rule hold: a playtest note that demands a new game-design direction or reopens a locked decision is `question`/`out-of-scope` and routes to `decision-interview` or `post-review-pivot`, not folded into the corrective backlog. Scope stays corrective (gameplay bugs, missing feedback, wrong tuning under the existing design); the candidate-bug-class step still runs. A recorded `## Feel verdict` block (per `wos/godot-mobile-interaction-and-feel.md ## Feel verdict checklist (D-4 gate)`) is a first-class payload for this mode: each per-dimension line that is not PASS becomes one matrix row with `source` tagged `playtest`, and the row's provenance cites the verdict's date and build; the D-4 closure floors route a FAIL verdict here, so this mode is where a failed feel gate turns into a corrective backlog. This mode swaps the input source; it does not change the matrix shape, the corrective-only scope, or the routing rules. Without the flag the command ingests PR feedback exactly as before.
- **MCP-pull mode (gated, off by default; DECISIONS D-1..D-4 of the 2026-07-03 mcp-integrations task).** When invoked with `--mcp-pull`, the review threads are pulled from a vetted, connected code-review or issue-tracker MCP instead of a pasted payload, and the command produces the same traceable feedback matrix with `source` tagged `mcp` and each item's URL recorded as its provenance pointer (per the shared MCP capability routing rules below). The same severity scale and the same conflict rule hold: a pulled item that demands a new product direction or reopens a locked decision is `question`/`out-of-scope` and routes to `decision-interview` or `post-review-pivot`, not folded into the corrective backlog. Scope stays corrective (bugs, style, missing tests, wrong field usage under existing scope); the candidate-bug-class step still runs. This mode swaps the input source; it does not change the matrix shape, the corrective-only scope, or the routing rules. IF the pull fails or the connected MCP is unreachable THEN the command states the failure explicitly and falls back to the pasted-payload path; it does not fabricate items. Without the flag, or with no vetted MCP connected, the command ingests PR feedback exactly as before.

Feedback matrix (required content, first block under `### Artifact changes` before per-file bullets):
- Columns: `id` | `source` | `summary` | `severity` | `in_scope` (yes/no) | `target` (paths or slice) | `next_action` (one verb: fix / clarify / defer / reject)

Candidate templates section (optional; emitted only when at least 1 candidate exists):

```
### Candidate bug-class templates

Findings below did not match any existing class in `wos/bug-classes/`. Consider writing a template if the pattern recurs.

| finding_id | source | pattern_summary | suggested_class_name | suggested_category |
|---|---|---|---|---|
| ... | Greptile | ... | ... | ... |
```

The user decides whether to create a new template at `wos/bug-classes/<suggested_class_name>.md`. This section is informational; no action is required.

Required output:
1. Feedback matrix (compact; required)
2. Per-file update plan or explicit `NO_CHANGE` per file
3. Exact proposed patches or full file blocks for each `PROPOSED` change
4. Candidate bug-class templates section (if any un-matched findings exist)
5. Recommended next command (must exist in `commands/*.md`)
6. Recommended editor mode
7. Recommended work complexity (`LOW` | `MEDIUM` | `HIGH` | `N/A`) for that next step
8. Why this is the correct next step
9. What should explicitly not be done yet

### MCP capability routing (gated, opt-in)
<!-- shared:mcp-capability-routing -->
**MCP capability routing (gated, opt-in; D-1..D-4 of the 2026-07-03 mcp-integrations task).** This command MAY use a connected MCP server for the specific ingest or egress path its Operating rules name. The rules below are the shared contract; the command adds only its surface-specific lines.

1. Trust gate (no bypass). The target server MUST be declared in the consuming repo's project-scoped `.mcp.json`, human-approved (ADR-0046), and inspected via `mcp-server-vet` (ADR-0070) BEFORE any use. A server missing any of the three is not connected for the purposes of this rule; the command proceeds on its manual path as if no MCP existed.

2. Capability routing only. Normative text, prompts, and examples route by capability ("an issue-tracker MCP", "a code-review MCP", "a messaging MCP", "a knowledge-base MCP"), never by vendor or server product name. The only place a concrete name appears is the user's own local configuration, echoed back verbatim when naming a destination or source.

3. Failure policy (visible fallback, never fabrication). IF the connected MCP is unreachable, times out, or returns malformed data THEN the command SHALL state the failure explicitly and continue on its manual path (paste-based input, or paste-ready output); it SHALL NOT fabricate or repair data silently and SHALL NOT hard-fail. With no MCP connected at all, the command behaves exactly as it did before this rule existed.

4. Ingest (task-init seed source, pr-feedback-ingest --mcp-pull). The mapping consumes exactly four capability-routed fields: title, body, identifier, URL. Title and body feed the task description or feedback payload; identifier and URL become a provenance pointer recorded in the receiving artifact (`source: mcp`, the server as locally named, the item URL). Fields beyond these four are ignored. MCP-sourced text is external input: it never overrides locked decisions or widens scope on its own, and the receiving command's existing scope rules (corrective-only, ADR-0056 ledger) apply to it unchanged.

5. Egress (team-update, delivery-asset). Sending produced content to a connected MCP requires an explicit user confirmation IN THAT TURN, given AFTER the command displays the exact payload and the destination (the server as locally named plus the channel, page, or space). One post requires one confirmation: no session-level standing approval exists, consent is never remembered across turns, and multiple posts are never batched under one confirmation. IF the send fails THEN the command reports the failure and leaves the text paste-ready; the produced artifact remains the primary output either way.

### Standard output layout (required)
<!-- shared:standard-output-layout -->
Produce the command output using this structure (English only):

### Artifact changes
- Start with the **Feedback matrix** block (required).
- List each file in `my_work_tasks/` that would change, or `None`.
- For each file, mark `APPLIED` / `PROPOSED` / `SKIP` and follow the task-memory write policy in `WORKFLOW_OPERATING_SYSTEM.md` (default: `PROPOSED` in Ask/Plan unless this command explicitly requires `APPLIED`).

### Command transcript
<!-- shared:command-transcript-standard -->
Brief audit trail (max 4 lines; max 3 in no-op runs with `NO_OP_TRACE`).

### Handoff
<!-- shared:handoff-body -->
Use the adaptive ending format from `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full per session state).

### Definition of done (command output)
- Every `must-fix` / `should-fix` row has a target and a mapped next action.
- Conflicts with `DECISIONS.md` are explicitly escalated, not silently “fixed”.
- `### Artifact changes` marks `APPLIED` only when persisting in Agent mode; otherwise `PROPOSED`.
- If any `must-fix` or `should-fix` finding does not match an existing bug-class in `wos/bug-classes/`, it appears in the `### Candidate bug-class templates` section with a suggested class name and category.
- The `--playtest` mode (when invoked) ingests playtest notes into the same feedback matrix (source `playtest`), keeps the corrective-only scope, and routes new-direction notes to `decision-interview` or `post-review-pivot`; without the flag the PR-feedback ingest is unchanged.
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
Make Greptile and human feedback executable as the smallest aligned slice set, without scope creep.

<!-- cache-breakpoint -->
