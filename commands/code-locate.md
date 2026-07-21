---
name: code-locate
description: Given a behavior description, locate candidate code paths and line ranges in the active codebase that probably implement it. Output up to 10 candidates with HIGH/MEDIUM/LOW confidence, one-line rationale per candidate, and an explicit search trail; propose a SOURCE_OF_TRUTH.md update so the next workflow step (typically impact-analysis) runs with concrete files instead of a vague codebase pointer. Per-repo when multi-repo. Use when the first real step is "where is this code?" (file paths not yet known), SOURCE_OF_TRUTH.md names the codebase but not specific files, you are about to run impact-analysis and the file list is missing, the user has a clear behavior description but no path or file pointers, or a failing test or runtime symptom names a behavior but not the implementation file. Do not use when file paths are already explicit, the codebase is tiny and the layout is known, the need is general architectural understanding (use impact-analysis), or no active task folder exists yet.
metadata:
  category: discovery-and-scoping
  primary-cursor-mode: Ask
  multi-repo-aware: true
  context-layers-consumed: [memory]
  context-layers-produced: [memory]
  tools: [Read, Write, Edit, Bash, Glob, Grep]
  x-wos-profiles: [core, full]
  provenance: first-party
  token-budget: 3800
  suggested-model: claude-sonnet-4-6
---
# code-locate

Act as a senior engineer locating code in the active codebase for the engineering task.

Goal:
Given a behavior description, locate candidate code paths and line ranges in the active codebase that probably implement that behavior. Output a bounded list of candidates with confidence and one-line rationale per candidate, then propose a `SOURCE_OF_TRUTH.md` update block so the next workflow step (typically `impact-analysis`) can run with concrete files instead of a vague codebase pointer.

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
- `TASK_STATE.md` (current phase)
- `SOURCE_OF_TRUTH.md` (current state, even if vague, so the patch is correctly scoped)
- behavior description in 1 to 3 lines (what the code in question does or should do)
- search type, exactly one of: `implementation` (production code), `tests` (test files), `config` (configuration files), `any` (no restriction)
- product workspace path (where the actual code lives, for example `~/code/acme-platform`). For single-repo tasks, this is the only repo. For multi-repo tasks, this is the workspace path matching `target repo` (see below).
- target repo (only for multi-repo tasks where `SOURCE_OF_TRUTH.md` has a `## Repositories` section): the repo identifier to search. Must match one entry in the `## Repositories` section. See the spec `## Multi-repo support (v1)` for the schema.
- search scope hint if known (path prefix, language, glob, etc.), to narrow the search
- failing test name and assertion message, if the locate is triggered by a failing test
- last completed step from `TASK_STATE.md` (command and summary)

Task repository files to update:
- `SOURCE_OF_TRUTH.md` (propose appending or updating `Main files in scope` with the located candidates; HIGH and MEDIUM confidence only)
- `TASK_STATE.md` only if the locate result materially changes operational state (rare; typically the `SOURCE_OF_TRUTH.md` update is the only artifact change)

Operating rules:
- Do not implement code. This command is read-only search.
- **Handoff:** end with the adaptive `### Handoff` block per `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact, Mode B full, or Mode C parallel-fanout when triggered).
- **Mode C eligibility (parallel fanout, per ADR-0032):** when the search target is a codebase with >1000 files OR the task is multi-repo with `## Repositories` listed in `SOURCE_OF_TRUTH.md`, emit a `Delegate now:` directive in the handoff dispatching one sub-agent per repo (or per high-level dir for single-repo scale). Each sub-agent returns up to 3 candidate paths from its scope; the parent integrates the merged candidate list (still capped at 10 total) and emits the normal Mode A handoff for the next step. Skip Mode C when codebase is small (<1000 files) and single-repo: inline search is cheaper than dispatch overhead.
- Return at most 10 candidate paths. If more than 10 plausible candidates exist, return the 10 most relevant and explicitly note that more exist plus how to narrow the search.
- Each candidate must include:
  - file path, relative to the product workspace
  - line range (for example `42-67`) when a specific function or block is the candidate; use `*` only when the entire file is the candidate
  - confidence level, exactly one of `HIGH` (direct match: function name, comment, type signature obviously aligns), `MEDIUM` (likely match: name or context aligns but not definitive), `LOW` (possible match: contextually adjacent, worth a look but may be wrong)
  - one-line rationale (why this candidate matches the behavior description)
- If no `HIGH`-confidence candidates exist, do not pad the list with low-confidence guesses. Explicitly say `no HIGH-confidence candidates found` and list what was searched (paths, globs, terms).
- Make the search scope explicit. The output must include a `What was searched` section listing paths or globs scanned and search terms used. The user must be able to judge coverage.
- Make the search scope's negative space explicit too. If the search excluded common locations (vendor, node_modules, generated code, build artifacts), say so under `What was excluded`.
- Do not invent paths. If a candidate cannot be confirmed by reading the file, mark its confidence as `LOW` and state what would confirm it.
- Multi-repo handling: branch behavior on the presence of `## Repositories` in `SOURCE_OF_TRUTH.md`. If the section exists, require explicit `target repo` input matching one entry; restrict search to that repo's workspace path. If the section is absent, run as single-repo (existing behavior, no change). Reject unknown repo identifiers with an explicit error rather than searching the wrong workspace.
- Treat task-memory write policy per `WORKFLOW_OPERATING_SYSTEM.md`: `PROPOSED` in Ask mode, `APPLIED` only when explicitly persisting in Agent mode.
- No-op rule for artifacts:
  - If `SOURCE_OF_TRUTH.md` already names the same files the locate would propose, do not rewrite it; emit `NO_OP_TRACE` and route forward.
  - If the search produced no `HIGH` and no `MEDIUM` candidates, do not patch `SOURCE_OF_TRUTH.md`; route to clarification (`targeted-questions`) instead.

Required output:
1. Behavior description echoed back in 1 line (so the user can confirm the locate matched their intent)
2. Search type used (`implementation` / `tests` / `config` / `any`)
3. `What was searched`: paths or globs scanned and search terms used
4. `What was excluded`: common skipped locations and why (vendor, generated, build artifacts, etc.)
5. Up to 10 candidates, each with: path, line range, confidence, one-line rationale
6. Negative result note when no `HIGH`-confidence candidate was found
7. Proposed `SOURCE_OF_TRUTH.md` update block (`Main files in scope` section) listing only `HIGH` and `MEDIUM` candidates
8. Recommended next command (typically `impact-analysis` with the now-populated `SOURCE_OF_TRUTH.md`)

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
- Default for this command: `PROPOSED` patch on `SOURCE_OF_TRUTH.md` only.

### Command transcript
- Keep this section operational and brief; do not restate file content already listed in `### Artifact changes`.
- Max 4 lines in normal runs.
- Max 3 lines in no-op runs (including `NO_OP_TRACE`).
- Include `NO_OP_TRACE` (1-3 lines) when no candidate was found, when the locate would not change `SOURCE_OF_TRUTH.md`, or when search scope was insufficient (route to user clarification).

### Handoff
<!-- shared:handoff-body -->
Use the adaptive ending format from `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full per session state).

### Definition of done (command output)
- Output lists at most 10 candidates; padding the list with `LOW`-confidence guesses to inflate the count is invalid output.
- Each candidate includes path, line range (or `*` for full file), confidence (`HIGH` / `MEDIUM` / `LOW`), and one-line rationale; missing any of these fields per candidate is invalid output.
- `What was searched` section is explicit (paths or globs and search terms); output without it is invalid because the user cannot judge coverage.
- `What was excluded` section names common skipped locations (vendor, generated, build artifacts, etc.); silent exclusion is invalid output.
- When no `HIGH`-confidence candidate exists, output explicitly says so and lists what was searched; vague "I could not find anything specific" without the search trail is invalid output.
- `SOURCE_OF_TRUTH.md` update block is provided when at least one `HIGH` or `MEDIUM` candidate exists; output without that patch when it would help the next step is invalid.
- Paths cited are real (verified by reading the file or directory listing); inventing paths to fill the list is invalid output and contradicts the `fail closed` rule.
- Multi-repo validation: when `SOURCE_OF_TRUTH.md` has a `## Repositories` section, output rejects invocations missing the `target repo` input or with an identifier that does not match any entry; running search against the wrong workspace silently is invalid output. Single-repo tasks (no `## Repositories` section) behave identically to the v1.0 contract.
- Handoff block is complete per the adaptive format in `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract`.
- The recommended next command defaults to `impact-analysis` (now able to run with concrete files); other valid options are `targeted-questions` (when locate result requires user clarification) or `incident-triage` (when locate was triggered by a failing test or incident and the result reveals a clear hotfix path).
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
Optimize for bounded output, accurate path-and-line citations, explicit search coverage, and protection against invented paths. The command exists to move the user from "vague codebase pointer" to "concrete files in scope" with high signal and minimal hallucination risk.

<!-- cache-breakpoint -->
