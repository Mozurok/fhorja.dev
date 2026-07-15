---
activation: model_decision
description: Full per-command roles + guard rails. Load on routing disputes that the inline ## Command roles index does not resolve.
---

# wos/command-roles.md

Full per-command role detail: distinctness rules, guard rails, multi-repo hints, and edge-case routing.

Load this file when:
- the compact index in `WORKFLOW_OPERATING_SYSTEM.md` `## Command roles` is not enough to choose between commands
- onboarding a new contributor to the workflow
- designing a flow that crosses 3+ commands and you need distinctness rules between them
- a guard rail or precondition is implicated and the operating-rules block in the command file alone is ambiguous

Authoritative content for command intent and routing nuance: the spec `## Command roles` index defers to this file on conflicts. Operational guard rails enforced at execution time still live in each `commands/<name>.md` `Operating rules:` section; this file complements that, it does not replace it.

---

### project-bootstrap
Role:
- canonical zero-state entry point for a brand-new project, product, initiative, or client engagement
- creates `projects/<client>__<project>/` plus the project-level memory files (`PROJECT_CHARTER.md`, `REFERENCES.md`) and empty `active/` and `archive/` subfolders
- runs an adaptive minimum-question flow (objective, stack, repositories, references, constraints, non-goals); records `[not decided yet]` placeholders for anything the user has not decided rather than inventing answers
- never creates a task folder; the first task is created by the next `task-init` run
- distinct from `task-init` (which assumes the project folder already exists) and from `capture-references` (which only appends to `REFERENCES.md` for an already bootstrapped project)
- guard rail: refuses to run when `projects/<client>__<project>/` already exists (route the user to `task-init` or `capture-references`)

Typical next commands:
- `task-init` (default; start the first task under the freshly bootstrapped project)
- `capture-references` (when the user wants to seed external references before opening the first task)

### task-init
Role:
- mandatory start of every task
- creates the task folder and required base files
- when `PROJECT_CHARTER.md` exists, seeds `SOURCE_OF_TRUTH.md` automatically from project-level memory; when it does not, warns and proceeds with placeholders (does not block)
- can run in Ask for drafting or Agent for file creation in `my_work_tasks`

Typical next command:
- `impact-analysis`

### task-workspace
Role:
- opt-in, git-gated provisioning of one durable git worktree and a `task/<task-slug>` branch for the active task (ADR-0074)
- records the `## Workspace` section (worktree path, task branch, base branch) in `SOURCE_OF_TRUTH.md`
- runs standalone to retrofit a task already in progress; `task-init` routes to it when isolation is requested
- never tears down (that is `task-close`); distinct from the ephemeral slice-level worktrees `implement-fleet` creates

Typical next command:
- `impact-analysis` (or the task's discovery step)

### task-init-fleet
Role:
- orchestrator-workers variant of `task-init` per ADR-0034 (J.8 PILOT, 2026-06-04), structural contract per ADR-0038 (PENDING lived runs)
- Opus orchestrator decomposes a multi-stream brief into N >= 3 independent sub-tasks; dispatches N Sonnet workers
- each worker runs the full task-init flow for ONE sub-task (5 mandatory files + `## Recommended pipeline` per ADR-0025)
- max_fanout 10; barrier convergence 10-min timeout; union merge
- orchestrator owns `INITIATIVE_INDEX.md` (cross-task index, one row per sub-task with date, slug, objective, status, cross-links, recommended next command)
- decomposition validation pre-dispatch: unique slugs, scope disjointness, cross_links form a DAG, complexity tier declared
- workers NEVER write INITIATIVE_INDEX.md; orchestrator is SOLE writer

Guard rails:
- requires N >= 3 sub-tasks (else NO_OP_TRACE -> route to `task-init` single-instance)
- requires same client_project across all sub-tasks (mixing FORBIDDEN)
- when in doubt about decomposition, NO_OP_TRACE -> route to `decision-interview` on the parent brief (silent over-splitting is worse than under-splitting)
- workers MUST NOT touch INITIATIVE_INDEX.md; substrate peer rule enforced
- when `PROJECT_CHARTER.md` is missing, warn but proceed; workers use explicit placeholders

Typical next commands:
- per-sub-task: `impact-analysis` or per the complexity tier emitted in that sub-task's TASK_STATE.md `## Recommended pipeline`
- overall coordination: `where-we-at` on each in sequence; `decision-interview` if cross-task conflicts surfaced

### code-locate
Role:
- read-only code search to locate candidate paths and line ranges that probably implement a described behavior
- audience: any user about to run `impact-analysis` who does not yet have concrete files in `SOURCE_OF_TRUTH.md`
- output: bounded list of up to 10 candidates with `HIGH` / `MEDIUM` / `LOW` confidence, one-line rationale per candidate, explicit search trail (paths searched, exclusions), and a proposed `SOURCE_OF_TRUTH.md` patch listing only `HIGH` and `MEDIUM` candidates
- guard rail: must not invent paths (fail closed with `no HIGH-confidence candidates found` plus search trail); padding the list with `LOW`-confidence guesses to inflate count is invalid output
- multi-repo support (G4 v1): when `SOURCE_OF_TRUTH.md` has a `## Repositories` section, requires explicit `target repo` input matching one entry and restricts search to that repo's workspace path; rejects missing or unknown repo identifiers

Typical next commands:
- `impact-analysis` once `SOURCE_OF_TRUTH.md` is populated with concrete files
- `targeted-questions` when the locate result requires user clarification (ambiguous behavior description, multiple plausible interpretations)
- `incident-triage` when the locate was triggered by a failing test or incident and the result reveals a clear hotfix path

### code-context-map
Role:
- opt-in; generates a durable, AI-readable structural map of a target codebase (files, imports, signatures, invoke edges, typed external boundary calls: db/http/queue), or a seed-anchored import chain from one file, and writes it to a gitignored folder (`.code-context-map/MAP.md`, plus an optional human `MAP.html`) inside that codebase
- audience: an assistant that needs fast structural orientation before editing a repo, onboarding, or refreshing a stale map
- output: a ranked, token-budgeted, layered Markdown map - Layer 1 (repo digest + module import adjacency + boundary summary) always; Layer 2 (per in-scope module: fan-in-ranked signatures + invoke edges + typed boundary edges) on demand and budget-capped; for `chain:<seed-file>` an Import chain section (per-hop imports by `direction` up to `max-hops` or `all`, cycle-guarded, fan-in-ranked); with the `html` flag a self-contained interactive `MAP.html` projection in the same gitignored folder
- mechanism: ripgrep-based extraction by default, assembled by reasoning, with optional parser augmentation (tree-sitter, `madge`, or `dependency-cruiser`) only if already present in the target repo; regenerate-on-invoke with a `branch@sha` freshness marker; no required parser dependency, no embeddings, no flow-graphs in v1; a ripgrep-only chain is labeled `grep-seed (non-authoritative)`; single-pass by default, a consent-gated fleet only past a context-window threshold
- guard rail: never commit the map (ensures `.code-context-map/` is gitignored); never fabricate entries (every line traces to a real `file:line`); never emit a flat whole-repo signature dump (blows the token budget); the map is a seed for `grep`, not an authoritative or exhaustive index, and the code wins on any disagreement
- distinct from `code-locate` (ephemeral per-behavior search returning up to 10 candidates, not a durable whole-repo map), `impact-analysis` (per-task blast-radius consumer that can read the map, not a producer), and `db-context-supabase` (introspects DB schema into task memory, not code structure into the product repo)
- governing decisions: `docs/adr/0027-code-context-map-and-product-repo-artifacts.md` and `docs/adr/0057-code-flow-map-seed-anchored-evolution.md` (the chain scope, hybrid extraction, HTML projection, and consent-gated fleet path)

Typical next commands:
- `impact-analysis` to scope a change using the map
- `code-locate` to pinpoint a specific behavior the map surfaced
- `what-next` when no task is active

### impact-analysis
Role:
- bounded technical understanding
- blast radius and affected-area assessment
- multi-repo support (G4 v1): when `SOURCE_OF_TRUTH.md` has a `## Repositories` section, produces per-repo blast radius under `### Repo: <identifier>` subsections in `IMPACT_ANALYSIS.md`; silently omitting any listed repo is invalid

Typical next commands:
- `invariants-and-non-goals`
- `targeted-questions`
- `decision-interview`
- `implementation-plan`
- `approve-proposed` (when this command emitted a PROPOSED `IMPACT_ANALYSIS.md` and the user reviewed and accepts the inline content; batch-persist idiom from ADR-0024)

### invariants-and-non-goals
Role:
- define what must not change
- lock boundaries before planning or implementation

Typical next commands:
- `targeted-questions`
- `decision-interview`
- `implementation-plan`
- `approve-proposed` (when this command emitted a PROPOSED `INVARIANTS_AND_NON_GOALS.md` and the user accepts the inline content as-is)

### targeted-questions
Role:
- ask the minimum factual questions needed to proceed safely

Typical next commands:
- `decision-interview`
- `implementation-plan`
- `resolve-contract-gaps`

### decision-interview
Role:
- ask the minimum decision-level questions that affect behavior, data, or rollout safety
- two modes: interview (no LOCK picks in this turn; PROPOSED-by-default per ADR-0001) and persist (LOCK picks present; APPLIED in the same turn per the `LOCK-pick recognition` operating rule)

Typical next commands:
- `resolve-contract-gaps`
- `implementation-plan`
- `approve-proposed` (alternative to LOCK picks: when interview-mode emits a PROPOSED `DECISIONS.md`, the user can also batch-persist via this sibling command instead of re-typing LOCK picks)

### problem-framing
Role:
- optional pre-task intake (Phase 0.5, ADR-0058); question whether the stated objective is the right problem before any task folder exists
- socratic, one question per message, prefer multiple choice; explore the goal before proposing a solution, propose 2-3 approaches, then write a five-field task-level BRIEF.md (problem, success criteria, non-goals, recommended approach, named deliverables) that task-init consumes and moves into the new task folder
- strong do-not-use-when gate (anti-ceremony): NO_OP straight to task-init for an already-one-sentence-clear objective, a bug fix or hotfix, or when an active task already exists
- distinct from decision-interview (in-task decision locking) and targeted-questions (in-task factual gaps): problem-framing precedes the task

Typical next commands:
- `task-init`
- `project-bootstrap` (when the project is not yet bootstrapped)

### db-context-supabase
Role:
- opt-in, provider-specific snapshot of the active Supabase database for the active task: validates the Supabase MCP server is configured and reachable, then introspects a user-scoped subset of tables, columns, types, and (depending on depth) RLS policies, functions, and recent migrations
- output: creates or fully regenerates `DB_CONTEXT.md` in the active task folder with snapshot metadata (provider, project ref, last refreshed date, depth, scope) and grounded schema content; appends at most one `## DB context` cross-link in `SOURCE_OF_TRUTH.md`
- distinct from `code-locate` (locates source code, not schema), `capture-references` (project-level external memory, not task-level DB schema), and `capture-observation` (manual note, no introspection)
- guard rail: read-only introspection only (no `INSERT` / `UPDATE` / `DELETE` / `DROP` / `ALTER` / `TRUNCATE` / `GRANT` / `REVOKE`); never invents schema; refuses to dump entire databases (asks to narrow scope when a schema has more than 25 tables and no narrowing list); never modifies task-scoped artifacts other than `DB_CONTEXT.md` and the single cross-link in `SOURCE_OF_TRUTH.md`
- precondition: requires a Supabase MCP server reachable from the current session; if not configured, stops with `NO_OP_TRACE` plus a single actionable line directing the user to configure the MCP server (does not auto-configure)
- multi-repo: single-repo by default in v1; multi-repo support is not in scope for this command

Typical next commands:
- whichever command the user was running before this capture (read `Last completed step` in `TASK_STATE.md` to infer)
- `impact-analysis` when the prior step was `task-init` and discovery is the natural next move
- `implementation-plan` when discovery is already complete and the snapshot was the last gating input
- `decision-interview` when the snapshot reveals a schema-level ambiguity that must be resolved before planning

### db-context-postgres
Role:
- opt-in, provider-agnostic snapshot of a generic Postgres database (GCP Cloud SQL, GKE Autopilot, self-hosted, AWS RDS) for the active task; uses `psql` or `pg_dump --schema-only` instead of Supabase MCP
- introspection covers: extensions, tables, columns, indexes, foreign keys, RLS policies (when present), server version; optional depth flag for functions + triggers
- output: creates or fully regenerates `DB_CONTEXT.md` in the active task folder; appends one `## DB context` cross-link in `SOURCE_OF_TRUTH.md`
- distinct from `db-context-supabase` (which targets Supabase MCP specifically); use this when the project uses non-Supabase Postgres
- guard rail: read-only introspection only; never invents schema; refuses to dump entire DB without narrowing; never logs password/full DATABASE_URL in snapshot

Typical next commands:
- whichever command the user was running before this capture
- `impact-analysis` when the prior step was `task-init`
- `implementation-plan` when discovery is complete
- `decision-interview` when the snapshot reveals schema-level ambiguity

### resolve-contract-gaps
Role:
- turn ambiguity into canonical implementation-safe decisions

Typical next commands:
- `contract-signoff`
- `implementation-plan`

### contract-signoff
Role:
- harden wording and remove interpretation risk from approved decisions

Typical next command:
- `implementation-plan`

### direction-adjust
Role:
- record a mid-task course correction (small-to-medium adjustment from the user's own work, not from external review) as a numbered `D-N: mid-task adjustment` entry in `DECISIONS.md` plus minimal `TASK_STATE.md` updates
- audience: any user mid-task who realized the current direction needs adjustment from their own work (not external review)
- distinct from `post-review-pivot` (external review feedback), `decision-interview` (heavyweight re-evaluation), and `capture-observation` (no decision, just memory)
- guard rail: must not silently override locked decisions or invariants; conflicts surface and route to `decision-interview`

Typical next commands:
- `implement-approved-slice` when the adjustment fits the current slice
- `implementation-plan` or `state-reconcile` when the slice scope must change
- `decision-interview` when the adjustment contradicts a locked decision

### implementation-plan
Role:
- define safe phases or slices before any implementation
- assign **work complexity** per slice (`LOW` / `MEDIUM` / `HIGH`) so execution and resumption can pick an appropriate editor capability tier without naming model SKUs

Typical next commands:
- `test-strategy`
- `sync-task-state`
- `implement-approved-slice`
- `approve-proposed` (when this command emitted a PROPOSED `IMPLEMENTATION_PLAN.md` and the user accepts the inline plan as-is; batch-persist idiom from ADR-0024)
- `self-critique-and-revise` (when the user wants a locked-rubric self-critique on the proposed plan before persisting; ADR-0021)

### test-strategy
Role:
- define the smallest high-signal test plan

Typical next commands:
- `sync-task-state`
- `implement-approved-slice`

### sync-task-state
Role:
- update the operational memory after meaningful progress or decision changes
- keep **work complexity** for the next step in `TASK_STATE.md` aligned with phase, risk, and the recommended next command when that assessment materially changes
- not mandatory when a short single-slice task already has accurate state and the next obvious move is delivery

Typical next commands:
- depends on the new state

### compact-task-memory
Role:
- lossy compaction of `TASK_STATE.md` when task memory has grown beyond a useful working size
- preserves canonical decisions, recommended next step, current phase, objective, invariants, source of truth, constraints, last completed step, resume notes, and work complexity verbatim
- filters stale facts, resolved questions, and mitigated risks into a `## Compaction history` audit entry with git-SHA pointer for reversibility
- distinct from `sync-task-state` (incremental, append-only, never lossy) and `state-reconcile` (drift repair, no shrinking)
- primary editor mode is Plan (PROPOSED-by-default per ADR-0001); the user reviews the slimmed proposal before persisting
- ADR-0015 codifies the contract; ADR-0023 names the per-phase thresholds that warn when compaction is recommended

Typical next commands:
- `sync-task-state`, `resume-from-state`, `what-next`, or the next planned slice
- never compact again immediately after compacting (the context-rot warning suppresses double-noise)

### approve-plan
Role:
- atomically lock `IMPLEMENTATION_PLAN.md` as the approved execution baseline
- symmetric counterpart to `approve-proposed` but plan-specific (not for arbitrary PROPOSED artifacts)
- appends `## Approval log` entry with date + slice count + first slice id
- updates `TASK_STATE.md` per the canonical 5-section pattern (`commands/_shared/task-state-slice-closure-pattern.md`)

Guard rails:
- refuses with NO_OP_TRACE when IMPLEMENTATION_PLAN.md contains `[NEEDS CLARIFICATION:]` markers
- refuses when the plan was not last touched by `implementation-plan` or `self-critique-and-revise`
- idempotent: refuses to re-approve a plan already marked APPROVED for the same revision
- does not modify slice content or decision content (locking-only)

Typical next commands (waves-aware per ADR-0042):
- `implement-fleet` when the first remaining wave in the plan's `## Execution waves` has size 2 or more with `Scope` and `Depends-on` declared
- `implement-approved-slice` (for the first slice in the locked plan) otherwise, or whenever the slice DAG is a chain

### approve-proposed
Role:
- atomically persist every file marked `PROPOSED` in the most recent prior assistant turn's `### Artifact changes` block
- single-command batch-persist idiom (ADR-0024 adendum to ADR-0001) that closes the two-step latency described in ADR-0001
- Agent mode by definition (writes files); does NOT propose anything
- locked five-line recap in `### Command transcript`: Persisted / Skipped (already current) / Skipped (incomplete inline) / Skipped (path outside scope) / Skipped (no PROPOSED marker). Lines with zero entries are omitted; lines with entries appear in the locked order
- atomic semantics: if any proposal contradicts a locked decision in `TASK_STATE.md ## Canonical decisions`, NO writes happen and the command emits a FAIL naming the contradiction (no partial persist)
- three explicit no-op cases emit `NO_OP_TRACE`: prior turn has no `### Artifact changes`; prior block has no `PROPOSED` files; all PROPOSED files already match on-disk content
- source-of-truth turn rule: "prior turn" means the MOST RECENT assistant message containing an `### Artifact changes` block; intervening turns without it are skipped; older Artifact-changes turns are not walked back
- inline-content requirement: only files with FULL final content inline under their bullet are persisted; "see above" or partial fragments are skipped with a recap-line reason
- does NOT replace ADR-0001; users can still re-run source commands in Agent mode (path a) or copy-paste manually (path c)
- guard rail: refuses to accept new content via user input; only executes the prior batch

Typical next commands:
- `sync-task-state` (when persisted files materially change task state)
- `where-we-at` (macro checkpoint after a multi-file persist)
- whichever command produced the original proposals (when the persist closes that command's loop)
- `state-reconcile` (when the batch surfaced a contradiction worth investigating beyond the locked-decision rollback)

### state-reconcile
Role:
- cross-check `TASK_STATE.md` against other task artifacts and observable evidence
- propose minimal patches when drift is material (especially after many edits or parallel artifact changes)
- read-only `memory-lint` mode (ADR-0053): runs `scripts/memory-lint.sh` to surface dead relative cross-links, orphaned `SLICES/` files, and stale `TASK_STATE.md` facts, and writes nothing (deterministic checks live in the script; the stale-fact judgment lives in the command)
- prefer this over `sync-task-state` when **multiple sources disagree** or trust in routing memory is low
- distinct from `compact-task-memory` (no shrinking; preserves existing facts and only patches contradictions) and from `approve-proposed` (no persistence of new PROPOSED files; only edits to already-existing state)

Typical next commands:
- `sync-task-state` (if only `TASK_STATE.md` still needs a clean write pass)
- `compact-task-memory` (when the reconciled state is correct but heavy; cleanup follows after patches land)
- `approve-proposed` (when the proposed patches are accepted as-is and the user wants to batch-persist them)
- `what-next`
- `resume-from-state`
- upstream contract/plan commands when drift is `BLOCKING`

### implement-approved-slice
Role:
- canonical single-slice execution path and the `implement-fleet` fallback
- minimal, bounded implementation of a single approved slice

Typical next commands (waves-aware and terminal-safe per ADR-0042):
- `implement-fleet` when the remaining `## Execution waves` show a wave of size 2 or more with `Scope` and `Depends-on` declared
- `implement-approved-slice` for the next sequential slice when the remainder is a chain
- `sync-task-state` for the LOW/MEDIUM inline-close path (keeps `TASK_STATE.md` fresh without a separate prompt)
- `slice-closure` (HIGH complexity or exit criteria not fully verifiable inline)
- `review-hard`
- `where-we-at` (multi-slice) or `task-close` when this was the last slice in the plan

### implement-fleet
Role:
- orchestrator-workers variant of `implement-approved-slice` per ADR-0041 (PILOT); executes independent approved slices in parallel
- computes waves from `IMPLEMENTATION_PLAN.md` `Scope` + `Depends-on`, validates file-scope disjointness pre-dispatch, runs one worktree-isolated worker per slice per wave, and gates each wave on an integrated build + typecheck + test
- not a replacement for `implement-approved-slice` (the canonical single-slice unit and the fallback); falls back to it when the DAG is a chain or a wave cannot be made disjoint

Typical next commands:
- `slice-closure` per completed slice
- `pr-package` when all waves pass
- `implement-approved-slice` for a slice held or failed by a wave (dependency, scope overlap, worker failure, or integration-gate failure)

### implement-slice-complement
Role:
- bounded **micro-deltas** after slice work (polish, small fixes, missed checklist items) still inside the same slice intent and `DECISIONS.md`
- not a substitute for a new slice or contract change

Typical next commands:
- `slice-closure` when closure evidence should be refreshed
- `sync-task-state` when only operational memory needs alignment
- `review-hard` when risk warrants another pass before PR
- `implement-approved-slice` only if the complement attempt exposed material new scope (re-plan first if needed)

### slice-closure
Role:
- determine whether the current slice is actually ready to close
- if this is effectively a single-slice task, can route directly toward delivery

Typical next commands:
- `sync-task-state`
- next slice implementation
- `pr-package`
- `where-we-at` only if the task is larger or still ambiguous
- `task-close` when this was the last slice and the whole task is ending
- `approve-proposed` (when slice-closure emitted PROPOSED slice notes plus `TASK_STATE.md` updates and the user accepts them as-is)

### task-close
Role:
- terminal task lifecycle transition; the symmetric counterpart to `task-init` and the only official way to close a whole task
- verifies the spec done-conditions (implementation complete, review complete, team approval, merge into integration branch), each met with evidence or explicitly waived in solo / Phase-1 contexts
- on pass: sets `TASK_STATE.md` to its final closed state and moves the task folder `active/YYYY-MM-DD_<slug>/` -> `archive/YYYY-MM-DD_<slug>/` (`archive/` canonical, `done/` legacy alias)
- on a failed gate: blocks (does not move) and routes to the smallest unblocking action
- idempotent (`NO_OP_TRACE` when already archived with final state); never deletes artifacts

Distinctness:
- vs `slice-closure`: that command closes a single slice (slice scope); `task-close` closes the whole task and performs the archive move
- vs `where-we-at`: that command only assesses progress; `task-close` performs the terminal transition
- vs `task-init`: symmetric opposite (init opens, close closes)
- guard rail: do not invent closure aliases (`task-archive`, `close-task`, `finish`); `task-close` is the only valid name

Typical next commands:
- `delivery-asset` or `pr-package` when delivery framing is still pending
- `task-init` for a genuinely new follow-up task
- none, when the task is fully done

### harvest-session-learnings
Role:
- on-demand, session-wide retrospective sweep; the produce-side of the reflexion-learnings loop (ADR-0017), whose consume-side `task-init` already reads
- reads the working session plus the active task's artifacts, judges which lessons generalize beyond this task, and appends them to the task's `LEARNINGS.md`
- every appended entry is anchored (`file:line`, slice header, command name, or timestamped `TASK_STATE.md` row) per `templates/LEARNINGS.md` `## Entry shape` and de-duplicated against existing entries
- append-only: it never edits, reorders, compacts, or prunes a prior entry (ADR-0017 item 6); LEARNINGS compaction is out of scope for every command
- `NO_OP_TRACE` when the session produced nothing durable; returns a manufactured lesson never

Distinctness:
- vs `capture-observation`: that command captures one in-flight note verbatim without judgment; this command judges what is durable across the whole session before writing
- vs `slice-closure`: that command captures the inline `### Learnings` of one slice as it closes; this command is a session-wide sweep that can run mid-task or at the end
- vs `task-close`: that command is the terminal lifecycle move; this one only harvests learnings and writes no other state
- scope guard: writes only the active task's `LEARNINGS.md`; a cross-project lesson is flagged as a pointer to `USER_MEMORY.md` (ADR-0016), not written here

Typical next commands:
- `slice-closure` or `task-close` when the harvest ran at closure
- `sync-task-state` when state moved during the session
- the prior in-progress command, when harvesting mid-task

### review-hard
Role:
- focused pre-PR engineering risk check
- not a replacement for external review systems

Typical next commands:
- `slice-closure`
- `repo-consistency-sweep`
- `where-we-at`
- `pr-package`

### repo-consistency-sweep
Role:
- proactive defect-class detection against the curated `wos/bug-classes/` library (<!-- count:bug-templates -->78<!-- /count --> templates across <!-- count:bug-categories -->22<!-- /count --> categories, CWE-grounded)
- handles convention drift, ordering bugs, type-safety gaps, security and multi-tenant invariants, and operability issues
- scoped to defect detection (the lower-value half of code review per Bacchelli and Bird 2013); does not replace human design discussion, knowledge transfer, or `review-hard` (which does correctness/safety risk)
- meta-learning loop via `pr-feedback-ingest` candidate templates output

Guard rails:
- do not implement fixes (analysis and reporting only)
- do not invent findings (if the diff is clean, say so)
- suppress declined findings from REVIEW_PREFERENCES.md when file hash is unchanged (D-11)
- return no-op when no diff or diff hash unchanged since last run (D-9)

Typical next commands:
- `pr-package` (0 findings or all declined)
- `implement-slice-complement` (P0 finding)
- `apply-sweep-triage` (user wants to persist triage decisions)

### apply-sweep-triage
Role:
- persist user triage decisions (apply, decline, discuss) from a SWEEP snapshot into project-level REVIEW_PREFERENCES.md
- declined entries suppress re-reporting of the same finding on future sweep runs (D-11) until the file changes (file-hash aging)
- deduplicates by bug-class + file-path before appending

Guard rails:
- do not modify the SWEEP snapshot (read-only historical record)
- do not implement code fixes (persistence only)
- return no-op if all findings in the snapshot are still `triage: unset`

Typical next commands:
- `pr-package`
- `repo-consistency-sweep` (re-run after fixes)

### skill-vet
Role:
- read-only safety inspection of a third-party agent skill or plugin before it is installed or trusted
- reads every file (not just SKILL.md), compares declared vs actual behavior, and scans for exfiltration, secret access, out-of-directory and agent-config writes, shell execution, and hidden or zero-width Unicode
- returns INSTALL / SANDBOX / DECLINE for a human to approve (ADR-0046)
- distinct from `security-review` (own-code attack surface) and `repo-consistency-sweep` (first-party pattern matching)

Guard rails:
- READ-ONLY: never install, enable, execute, move, or fetch; the verdict is a recommendation, the human decides
- a URL source is captured via `capture-references` first; skill-vet points at the local copy
- read the description and every file, not just the body (payloads ride in on test or auxiliary files and hidden Unicode)

Next:
- `capture-references` (if the source is a URL not yet captured)
- human approval of the verdict

### mcp-server-vet
Role:
- read-only safety inspection of a third-party MCP server before it is added to a config or trusted
- enumerates the config entry and every advertised tool (name, description, input schema, declared scope), compares declared vs actual, and scans for tool-description poisoning, over-broad or undeclared scopes, egress and credential access, agent-config writes, shell execution, and hidden or zero-width Unicode
- returns ADD / SANDBOX / DECLINE for a human to approve (ADR-0070)
- distinct from `skill-vet` (third-party skill or plugin directories) and `security-review` (own-code attack surface)

Guard rails:
- READ-ONLY: never add to a config, enable, start, or fetch; the verdict is a recommendation, the human decides
- a URL or registry source is captured via `capture-references` first; mcp-server-vet points at the local copy
- inspect the declared surface, not a README (the attack rides in tool descriptions, scopes, and hidden Unicode)
- static pre-trust inspection only; runtime egress monitoring is out of scope (external tools own that)

Next:
- `capture-references` (if the source is a URL not yet captured)
- human approval of the verdict

### security-review
Role:
- dedicated security assessment covering threat modeling, OWASP ASVS L1 checklist, auth/authz flow tracing, and operational security reminders
- distinct from `review-hard` (general correctness/safety risk) and `repo-consistency-sweep` (pattern-matching defect classes)
- grounded in OWASP ASVS 5.0 (17 chapters, 350 requirements at L1); references CWE Top 25 for vulnerability classification

Guard rails:
- do not implement fixes (analysis and reporting only)
- do not invent threats; if the code is secure, say so
- return no-op when the diff has no security surface (pure docs, style refactors, test-only changes)
- include operational reminders (npm audit, secret scan, HTTPS, CORS) as actionable commands, not vague suggestions

Typical next commands:
- `implement-slice-complement` (if P0 security finding)
- `pr-package` (if secure or only P2 deferrals)
- `repo-consistency-sweep` (if not yet run)

### where-we-at
Role:
- macro checkpoint against the approved plan
- broader than slice closure
- useful mainly for multi-slice or longer-running tasks

Typical next commands:
- `what-next`
- `implement-approved-slice`
- `implement-slice-complement` when the gap is a small explicit follow-up under a known slice
- `pr-package`

### autonomous-run
Role:
- controller for the autonomous delivery track (ADR-0044; `wos/autonomous-track.md`)
- drives an approved, waved `IMPLEMENTATION_PLAN.md` through bounded execution behind two human gates (plan-approval upstream via `approve-plan`, draft-diff merge downstream via `approve-proposed` / `review-hard`) and a runtime governor
- a thin dispatcher over existing primitives: runs `implement-approved-slice` as the single writer per slice, calls `scripts/autonomy/` (stop-check, governor, classify-slice) between slices, emits PROPOSED diffs only and never merges
- escalates any boundary slice (schema, contract, migration, security) or any test/eval-touching slice to the human gate mid-run (D6/D12); defaults to escalate on uncertainty
- distinct from `implement-fleet` (parallel slices, still human-gated per wave, not an end-to-end loop) and from `implement-approved-slice` (executes one slice; `autonomous-run` sequences many under the governor)
- refuses any permissive headless or auto-merge mode (D9); refuses an unapproved plan and routes to `approve-plan`

Typical next commands:
- `approve-proposed`
- `review-hard`
- `implement-approved-slice` (for an escalated slice the human approves)

### resume-from-state
Role:
- reconstruct task truth after context loss or new session start

Typical next commands:
- `what-next`
- command appropriate to the resumed phase

### what-next
Role:
- fast routing answer
- should stay short and operational

### portfolio-review
Role:
- read-only cross-task board across every active task in all projects (portfolio-level, not one active task)
- runs `scripts/portfolio-review.sh` to classify each task (done-unclosed / blocked / my-move / stale / in-flight) and recommends one action per row
- never writes any task's memory; surfaces finished-but-unarchived tasks and whose-move-it-is

Guard rails:
- distinct from `what-next` (routes a single active task) and `where-we-at` (deep checkpoint of one task); portfolio-review is the only command that looks across all tasks at once
- read-only: no substrate writes, no per-task deep dives (those live in each task's own commands)

Typical next commands:
- per row: `task-close` (done-unclosed), `where-we-at` (stale), `approve-plan` / `decision-interview` (my-move), or the named unblocking command (blocked)

### workflow-guide
Role:
- pedagogical explanation of current phase and next 2-3 steps
- audience: users still learning the workflow (onboarding, first few sessions); experienced users default to `what-next` (single answer, lower overhead)

### im-stuck
Role:
- recovery from loops, false progress, stale state, or phase confusion

### incident-triage
Role:
- triage a concrete observed technical failure (stack trace, error output, failing test, runtime symptom, or production alert) and route to the smallest decisive next step
- audience: any user facing a real failure who needs to decide between a hotfix shortcut and full task ceremony
- output: failure classified into one of `REGRESSION` / `NEW_BUG` / `CONFIG` / `EXTERNAL_DEPENDENCY` / `REPRODUCIBILITY` / `DIAGNOSTIC_INSUFFICIENT`; recommended fix size as one of `HOTFIX` / `SLICE` / `INVESTIGATION` / `ESCALATE`; smallest decisive next step as a concrete action with paths, commands, or specific queries
- distinct from `im-stuck` (no concrete failure signal, just confusion) and from `task-init` (failure-shaped, not feature-shaped)
- guard rail: validates against locked decisions and invariants; conflicts route to `decision-interview` rather than silent override; `BLOCKING_PROD` plus `HOTFIX` requires an explicit `Why this skip is safe` justification

Typical next commands:
- `branch-commit` then `pr-package` when fix size is `HOTFIX`
- `implement-approved-slice` or `implementation-plan` when fix size is `SLICE`
- `impact-analysis` or `targeted-questions` when fix size is `INVESTIGATION`
- `capture-observation` plus `team-update` when fix size is `ESCALATE`
- `decision-interview` when the proposed fix conflicts with a locked decision

### capture-references
Role:
- canonical command for appending external references to project-level `REFERENCES.md` with freshness metadata (URL, accessed date, summary, optional verbatim key points, tags)
- accepts URLs to fetch or topics to search; fetches and summarizes within source-of-truth boundaries (no invention beyond what the page says)
- deduplicates by URL; skipping duplicates is a `NO_OP` outcome with `NO_OP_TRACE`
- must not modify any task-scoped artifact; the only file it appends to is `projects/<client>__<project>/REFERENCES.md`
- distinct from `capture-observation` (task-level memory, no web fetch) and from `targeted-questions` (asks the user, does not pull from external sources)
- routing: defaults back to whatever command was running before this capture; falls back to `task-init` after a fresh `project-bootstrap` or `what-next` when uncertain

Typical next commands:
- whichever command the user was running before the capture
- `task-init` (when a fresh `project-bootstrap` just ran and the user is about to open the first task)
- `what-next` (when uncertain)

### capture-observation
Role:
- lean append of a single observation, question, hypothesis, or concern to `TASK_STATE.md` without disrupting in-progress work
- audience: any user mid-task who notices something worth remembering
- output: append-only single observation to `TASK_STATE.md` with date and optional tag (`question` | `hypothesis` | `concern` | `note`)
- distinct from `sync-task-state` (does not reflect progress, only memory) and from `targeted-questions` (does not ask the model to produce questions, records the user's own observation verbatim)
- routing: defaults back to whatever command was running before this capture; falls back to `what-next`

### autonomous-board
Role:
- read-only board-of-record view for an `autonomous-run` task (ADR-0044 D7; `wos/autonomous-track.md`)
- maps each slice and wave to a column (to-do, in-progress, escalated, proposed, done) sourced only from the Fhorja artifacts (spec, `IMPLEMENTATION_PLAN.md`, `TASK_STATE.md`, `SLICES/`)
- the Fhorja-internal substitute for an external work tracker; reads no tracker and writes nothing (`context-layers-produced: []`)
- distinct from `where-we-at` (progress judgment against the plan, may write `TASK_STATE.md`) and from `what-next` (routing only); `autonomous-board` is a pure status render for autonomous runs
- routing: back to `autonomous-run` to continue, or `approve-proposed` for diffs at the merge gate

### pr-package
Role:
- prepare delivery artifacts based on the real diff vs an explicit base branch
- must require the base branch explicitly
- multi-repo support (G4 v1): when `SOURCE_OF_TRUTH.md` has a `## Repositories` section, requires explicit `target repo` input; produces `PR_PACKAGE.<repo>.md` per invocation; uses the base branch declared in the matched `## Repositories` entry; multi-repo tasks invoke this command once per repo; cross-repo coordination notes live in `TASK_STATE.md` plus per-PR body cross-references (`Related PR: <url>`)

### pr-feedback-ingest
Role:
- consolidate PR review signals (Greptile, CI, bots, humans) into a traceable matrix aligned with `DECISIONS.md`, `IMPLEMENTATION_PLAN.md`, and `TASK_STATE.md`
- map each item to paths or slices and route conflicts to contract or pivot commands instead of silent fixes
- corrective scope only; not a substitute for a direction change

Typical next commands:
- `implement-approved-slice` when fixes fit approved slices
- `implement-slice-complement` when mapped items are explicit micro-deltas under an existing slice
- `implementation-plan` or slice edits when the matrix implies new micro-work ordering
- `sync-task-state` or `state-reconcile` when memory must reflect the ingested backlog
- `post-review-pivot` or `decision-interview` when feedback contradicts locked decisions
- `pr-package` again when the diff and reviewer-facing notes are stable after fixes

### post-review-pivot
Role:
- absorb PR or team feedback that changes direction while keeping the same task thread
- produce a pivot digest and proposed updates to plan, slices, and task memory before re-execution
- route to contract or planning commands when policy or scope text must change

Typical next commands:
- `targeted-questions` or `decision-interview` when facts or policy are still open
- `resolve-contract-gaps` or `contract-signoff` when canonical wording must change
- `implementation-plan` when the slice graph must be rewritten
- `test-strategy` when validation posture changes with the pivot
- `implement-approved-slice` when the pivot is already fully specified as an approved slice
- `state-reconcile` when memory artifacts disagree after the pivot is described
- `pr-package` again when the diff and narrative are stable after the pivot

### branch-commit
Role:
- lightweight naming support grounded in the real `git diff` (one of `git diff`, `git diff --staged`, or `git diff <base>...HEAD`)
- summarizes the actual change in a branch name + ≤3-line commit message; never paraphrases the task summary as a substitute for inspecting the diff

### team-update
Role:
- short status communication for any team channel (Slack, Discord, Teams, email, PR comment, standup)
- channel-portable: no channel-specific markup injected; user adds decoration manually if needed

### prompt-shape
Role:
- shape the exact next prompt when precision or handoff quality matters

### external-research
Role:
- synthesize multiple external sources into a task-scoped `EXTERNAL_RESEARCH.md` grounded in `REFERENCES.md` entries (project-level memory)
- each source MUST be captured first via `capture-references` (deduplication by URL; freshness metadata; `Context within project` field per ADR-0018)
- produces a comparative analysis plus a model recommendation visually separated from the source-grounded findings; never invents claims; every conclusion is anchored in a captured source
- surfaces cross-source relationships explicitly: reinforcing (multiple sources agree), contradicting (factual disagreement needing resolution), different-framing (different aspects of the same question; NOT contradiction)
- pre-ADR-0018 entries without the `Context within project` field are grandfathered; missing field annotated in the synthesis (`[Context within project: not captured]`) without blocking
- distinct from `capture-references` (single-source append) and `code-locate` (internal codebase search)
- read-only over external content; never re-fetches sources the user already captured

Typical next commands:
- `decision-interview` when synthesis surfaces new policy or behavioral questions
- `implementation-plan` when synthesis closes the question and planning can proceed
- `targeted-questions` when synthesis surfaces factual gaps
- `capture-references` again when a follow-up source is needed before re-running the synthesis

### external-research-fleet
Role:
- orchestrator-workers variant of `external-research` per ADR-0034 (J.9 PILOT, 2026-06-04), structural contract per ADR-0038 (PENDING lived runs)
- promotes the inline Mode C delegation in `external-research` (ADR-0032) to a first-class orchestrator with worker contract + provenance
- Sonnet orchestrator dispatches N >= 3 Sonnet workers (one per angle or source-group), barrier convergence 15-min timeout, union merge
- caller pre-decomposes the parent question into angles AND pre-assigns sources to angles; orchestrator does NOT auto-decompose
- each worker grounds claims strictly in its assigned sources; returns structured `claims[]` with `source_ref`, optional `verbatim_quote`, and `confidence` (high/medium/low/unclear-from-source)
- orchestrator performs cross-angle reconciliation per ADR-0018: tags claim groups as REINFORCING (>=2 angles agree), CONTRADICTING (>=2 angles disagree; flagged), DIFFERENT-FRAMING (distinct facets; not a contradiction)
- emits ONE merged EXTERNAL_RESEARCH.md with the canonical synthesis format + `## Conflicts surfaced` section when CONTRADICTING groups detected + ONE consolidated recommendation visually separated from analysis
- workers NEVER write EXTERNAL_RESEARCH.md or REFERENCES.md; orchestrator is SOLE writer of both files in fleet mode

Guard rails:
- requires N >= 3 angles (else NO_OP_TRACE -> route to `external-research` inline)
- requires every angle have >= 1 source assigned; no source assigned to more than one angle
- contradictions are SURFACED not RESOLVED (the recommendation may state which side the orchestrator favors, but conflicts remain visible for user validation)
- silent claim over-grouping (collapsing distinct claims) hides contradictions; under-grouping inflates "reinforcing" count -> when in doubt, leave separate
- requires Mode C parallel fanout eligibility per ADR-0032; refuses if request is already small enough for inline synthesis

Typical next commands:
- `decision-interview` when CONTRADICTING groups surfaced (the conflict is the next decision)
- `implementation-plan` when synthesis converged on a path
- `targeted-questions` when reconciliation surfaced factual gaps a worker could not close

### stack-recommend
Role:
- research and recommend a technology stack for the active project grounded in official documentation, quality articles, and AAA company engineering practices
- produces `STACK_RECOMMENDATION.md` inside the active task folder with exact stable version numbers, compatibility matrix, trade-offs, and confidence assessment per layer
- searches official docs/release pages for latest stable versions; cross-references quality articles and AAA company tech blogs; optionally incorporates user-provided reference links
- every recommendation cites at least one source; never recommends beta/RC/canary versions
- captures new sources into project-level `REFERENCES.md` using `capture-references` format
- distinct from `external-research` (generic multi-source synthesis) and `project-bootstrap` (captures existing decisions but does not recommend)

Typical next commands:
- `implementation-plan` when stack is decided and planning can proceed
- `decision-interview` when trade-offs need user input before locking the stack
- `project-bootstrap` when the stack recommendation feeds a new project being initialized
- `design-bootstrap` when the project also has a Figma file to extract
- `feature-library-scout` when the decided stack will need per-feature library choices (one granularity below the layers; ADR-0045)

### stack-currency-check
Role:
- verify the patterns the model is about to use for a given framework+version are current per official docs, before greenfield implementation
- caches the result as project-level `CURRENT_PATTERNS.md`; treats an existing one as stale after 30 days
- prevents the "gold-standard audit" anti-pattern where training-data defaults ship outdated patterns (e.g. Supabase `getSession` when `getUser` is current; sequential `await` when `Promise.all` is recommended)
- distinct from `stack-recommend` (choosing the stack itself) and `capture-references` (fetching an arbitrary URL)

Typical next commands:
- `implementation-plan` when the patterns are confirmed current and planning can proceed
- `impact-analysis` when currency findings change the blast radius
- `decision-interview` when a pattern gap surfaces a real decision

### feature-library-scout
Role:
- discover and vet the community-validated best-in-class library for each concrete feature problem in the product (lists, camera, forms, keyboard, sheets, navigation, gestures, animation)
- ranks candidates by adoption signal relative to the stack's ecosystem: registry downloads, dependents, release cadence, last release, source-host stars and trend, maintenance health, framework/platform fit (the axis that matters for the stack: React Native Expo/New-Architecture; web SSR/RSC/edge/bundle; backend runtime version)
- stack-agnostic across registries (npm, PyPI, crates.io, Go module index, Maven Central, etc.); never JavaScript-only
- researches across five angles: internet, product repository, package registry, AAA-company practices, reference repos solving the same problem
- writes `FEATURE_LIBRARIES.md` in the active task folder; funnels every cited source into project-level `REFERENCES.md`; recommendations are optional guidance, never mandates
- operates one granularity below `stack-recommend`: it picks per-feature libraries, not stack layers, and never re-picks layers (ADR-0045, D-Boundary)
- distinct from `stack-recommend` (stack layers), `stack-currency-check` (framework pattern currency), and `external-research` (synthesis of already-captured sources)

Typical next commands:
- `decision-interview` when a library pick needs the maintainer's ruling
- `implementation-plan` when the per-feature picks are clear and planning can proceed
- `feature-library-scout-fleet` when the feature-problem list is large enough to warrant one worker per problem

### feature-library-scout-fleet
Role:
- orchestrator-workers variant of `feature-library-scout` (ADR-0038, ADR-0045) for products whose feature set decomposes into N >= 3 distinct feature problems
- the orchestrator (the authorized fetcher and the sole writer) decomposes the feature set, captures adoption signals for each problem's candidates into project-level `REFERENCES.md`, then dispatches one Sonnet worker per problem
- each worker ranks its problem's candidate libraries by adoption signal grounded strictly in captured sources and returns a typed payload via the `StructuredOutput` tool; workers never fetch the web and never write `FEATURE_LIBRARIES.md` or `REFERENCES.md`
- the orchestrator merges per-problem rankings into one `FEATURE_LIBRARIES.md` (union merge, dedup sources by URL, one recommended pick per problem) and runs `scripts/scan-substrate-orphans.py` as the apply gate
- recommendations are optional guidance; the boundary with `stack-recommend` (stack layers) is preserved
- distinct from `feature-library-scout` (the inline single-agent variant for 1-3 problems)

Typical next commands:
- `decision-interview` when a per-problem pick needs the maintainer's ruling
- `implementation-plan` when the per-feature picks are clear and planning can proceed

### api-contract-review
Role:
- review an API contract (endpoints, request/response shapes, error codes, auth model) BEFORE implementation
- checks naming consistency, versioning, pagination, idempotency, and alignment with existing endpoints
- distinct from `review-hard` (post-implementation engineering risk) and `repo-consistency-sweep` (pattern matching on already-written code)

Typical next commands:
- `implementation-plan` when the contract is sound and implementation can proceed
- `decision-interview` when a contract choice needs a policy decision
- `impact-analysis` when the contract change implicates broader blast radius

### graphql-contract-review
Role:
- review a GraphQL schema and BFF contract BEFORE implementation, against a GraphQL-specific checklist (schema shape and nullability, errors-as-data, N+1 and DataLoader, query cost and depth, cursor connections, federation entity ownership, breaking-change gate, BFF auth and thinness, partial-failure degradation)
- the GraphQL and BFF counterpart to `api-contract-review`, which owns REST and HTTP; same design-time review role, different checks
- capability-routed, not stack-locked; reviews GraphQL on any stack
- distinct from `review-hard` (post-implementation engineering risk) and `repo-consistency-sweep` (pattern matching on already-written code)

Typical next commands:
- `implementation-plan` when the schema and BFF contract are sound and implementation can proceed
- `decision-interview` when a schema or federation choice needs a policy decision
- `impact-analysis` when the contract change implicates broader blast radius

### frontend-architecture-review
Role:
- design-time review of a frontend architecture at scale; the first step is a micro-frontend adopt/don't-adopt gate that defaults against adoption (prefer a modular monolith until 3 or more independently deploying teams and real coordination pain exist)
- then checks team-and-domain boundaries, independent deployability, governed shared dependencies, design-system sharing, runtime isolation, cross-app communication, routing and composition tier, rendering strategy, state at scale, a performance budget across the composition, and governance and failure handling
- capability-routed, not stack-locked
- distinct from `frontend-system-design` (designs one system), the contract reviews (`api-contract-review`, `graphql-contract-review`), and `review-hard` (post-implementation risk)

Typical next commands:
- `implementation-plan` when the architecture is sound and implementation can proceed
- `decision-interview` when an architecture choice (adopt micro-frontends, rendering strategy) needs a policy decision
- `impact-analysis` when the change implicates broader blast radius

### frontend-system-design
Role:
- produce a staff-grade frontend system-design RFC for the active task: a 12-section design document covering web and mobile (problem, requirements, architecture, data model, API and interface contract, rendering and delivery, state management, performance budget, accessibility, security, rollout, trade-offs)
- default RFC mode writes the design doc for real work; an `--interview` mode reframes the same structure for a frontend system-design interview round (RADIO-aligned)
- capability-routed, not stack-locked: designs on whatever stack the task uses, never assumes React
- distinct from `problem-framing` (questions whether the problem is right, pre-task), `implementation-plan` (slices an already-designed change), `impact-analysis` (blast radius of an existing codebase), and `api-contract-review` (reviews one API contract in isolation)

Typical next commands:
- `implementation-plan` to slice the designed work
- `decision-interview` when the design surfaced a decision that must be locked
- `approve-plan` when the design feeds directly into an existing plan

### backend-system-design
Role:
- produce a staff-grade backend system-design RFC for the active task: a 12-section design document for a new service, endpoint, or backend feature (problem, requirements, high-level architecture, data model and storage, API and interface contract, caching and data access, scaling and bottlenecks, reliability and SLOs, security, observability, rollout and migration, trade-offs)
- capability-routed, not stack-locked, and scale-honest: designs for the task's real scale and never imports sharding, multi-region, or a message bus without a stated requirement forcing it
- the backend sibling of `frontend-system-design`; composes with `slo-define` (targets), `performance-budget`, `api-contract-review` (endpoint audit), `migration-safety-steward` (DDL safety), and `release-plan` (rollout) rather than duplicating them; cites `wos/cache-update-strategies.md` and `wos/architecture-tradeoffs.md`
- distinct from `impact-analysis` (blast radius of an existing change), `implementation-plan` (slices an already-designed change), and `api-contract-review` (reviews one API contract in isolation)

Typical next commands:
- `implementation-plan` to slice the designed work
- `decision-interview` when the design surfaced a decision that must be locked
- `approve-plan` when the design feeds directly into an existing plan

### delivery-asset
Role:
- generate an outward-facing delivery artifact (executive summary, slack or email update, demo script, release note, blog post draft) from the current task's work
- audience-aware and format-aware: filename convention is `DELIVERY_ASSET_<format>_<audience>.md` inside the active task folder
- distinct from `pr-package` (GitHub-scoped; one PR per repo) and `team-update` (channel-portable but team-internal status note)
- grounds every claim in `TASK_STATE.md`, `DECISIONS.md`, `IMPLEMENTATION_PLAN.md`, and `PR_PACKAGE.md` when present
- never invents metrics, customer impact, or marketing claims; never leaks workflow file paths or internal command names into the public surface
- guard rail: refuses to fabricate quantitative claims that are not present in source artifacts; surfaces gaps explicitly rather than guessing

Typical next commands:
- `team-update` when a shorter internal version is also needed
- `pr-package` when the same closure also needs reviewer-facing notes
- `sync-task-state` when delivery framing surfaces a material state change worth recording

### verify-against-rubric
Role:
- spawn a stateless sub-agent (Claude Code `Task` tool, Cursor agent mode subagent, or equivalent) with ONLY the artifact path + locked rubric
- sub-agent has no access to TASK_STATE.md, DECISIONS.md, or conversation history (isolated context)
- returns structured per-criterion verdict (satisfied / needs_revision / failed) plus 1-2 line reason per criterion
- main thread does NOT re-evaluate; persists verdict to VERIFICATION_LOG.md and updates TASK_STATE.md to reference the verdict id

Guard rails:
- refuses (NO_OP_TRACE) when rubric is vague ("feature works", "looks good"); routes to `resolve-contract-gaps`
- never on LOW or MEDIUM complexity slices (use `self-critique-and-revise` instead -- cheaper, same-context, sufficient)
- sub-agent context isolation is the load-bearing differentiator vs `self-critique-and-revise`; do not collapse them

Typical next commands:
- on `satisfied`: `pr-package` submission, or the next planned slice
- on `needs_revision`: `implement-slice-complement` with verdict feedback inline
- on `failed`: `direction-adjust` or `decision-interview` per failure type

### verify-against-rubric-fleet
Role:
- orchestrator-workers generalization of `verify-against-rubric` per ADR-0034 (J.10 PILOT, 2026-06-04), structural contract per ADR-0038 (PENDING lived runs)
- Sonnet orchestrator dispatches N >= 4 stateless Sonnet workers in parallel against ONE shared locked rubric
- each worker receives ONLY artifact + rubric + criteria (no sibling artifacts, no TASK_STATE, no DECISIONS, no prior history); independence is the load-bearing property -- the Anthropic Outcomes +10pp uplift collapses to groupthink if cohort tally leaks into worker prompts
- max_fanout 20; barrier convergence 10-min timeout; union merge
- orchestrator emits ONE VERIFICATION_LOG.md cohort entry with per-artifact verdict table, aggregate pass/fail/needs_revision counts, AND failure clustering (criteria with >= 50% failure rate -> SYSTEMIC; < 50% -> LOCALIZED)
- failure clustering is the novel deliverable: difference between "N artifacts to fix" (downstream) vs "criterion C3 fails on 14 of N artifacts -> rubric or spec is the root cause" (upstream remediation)

Guard rails:
- refuses (NO_OP_TRACE) when rubric is vague; routes to `resolve-contract-gaps`
- requires N >= 4 artifacts (else NO_OP_TRACE -> route to `verify-against-rubric` single-artifact)
- requires >= 2 criteria (single-criterion rubric trivializes; route to `verify-against-rubric`)
- workers MUST NOT see sibling artifacts or cohort running tallies (independence)
- mixed rubrics in one fleet run FORBIDDEN -- re-run per rubric
- SYSTEMIC clusters are HYPOTHESES (orchestrator suggests upstream remediation but does NOT auto-route)

Typical next commands:
- on SYSTEMIC clusters: `decision-interview` on the rubric OR `direction-adjust` on the upstream spec
- on LOCALIZED issues: `implement-slice-complement` per artifact with verdict feedback inline
- on full cohort `satisfied`: `pr-package` submission of the cohort

### self-critique-and-revise
Role:
- evaluator-optimizer pattern (ADR-0021) applied to one of three draft artifact types: `IMPLEMENTATION_PLAN.md`, `SLICES/<NN>-*.md`, or `PR_PACKAGE.md`
- runs a LOCKED per-artifact-type rubric (7 criteria per type with verdicts `PASS | FAIL | WEAK`) and emits both a `## Critique` and a `## Revised draft`
- includes a `## Diff summary` of changes the revision applied AND a `## Not applied` section listing judgment-driven items deferred to the user (not auto-applied because they require human input)
- PROPOSED-by-default in Plan mode; the user reviews the revised draft before persisting
- distinct from `review-hard` (judges only, no revision), `direction-adjust` (records D-N entry, no artifact revision), `post-review-pivot` (external feedback, not self-critique), and `state-reconcile` (multi-artifact drift repair, not single-artifact revision)
- other artifact types (`TASK_STATE.md`, `DECISIONS.md`, `commands/*.md`) are out of scope; the command emits `NO_OP_TRACE` and routes the user to the right command

Typical next commands:
- `implementation-plan` again (Plan mode) when the revision is approved and lands in `IMPLEMENTATION_PLAN.md`
- `implement-approved-slice` when the revised slice is now approval-ready
- `pr-package` when the revised PR package is approval-ready
- `direction-adjust` when the critique surfaced a decision-level realization beyond artifact revision

### godot-scene-plan
Role:
- plan the Godot scene and node structure for a 2D game feature before any GDScript: the scene tree and node types and responsibilities, autoloads (singletons), signal wiring, the input map, and the resources and sub-scenes to create
- produces `GODOT_SCENE_PLAN.md`, a design-time plan an MCP-driven editor or a human builds against
- capability-routed and MCP-agnostic: names no specific MCP server, because the contract is the scene design, not the tool that applies it (DECISIONS D-1, D-4)
- part of the Godot 2D-mobile game-dev cluster (ADR-0069); GDScript default, version-flexible
- distinct from `problem-framing` in its game-design mode (frames whether the game idea is right), `implementation-plan` (slices an already-planned build), `impact-analysis` (blast radius of an existing project), and `godot-runtime-verify` (verifies a running scene at runtime)

Typical next commands:
- `implementation-plan` to slice the build from the scene plan
- `decision-interview` when the plan surfaced an architecture decision to lock
- `targeted-questions` when a factual gap blocks the plan

### godot-runtime-verify
Role:
- verify a built Godot 2D scene at runtime: run it (press-play in the editor or a headless run), read the captured debugger output, classify any runtime errors against a Godot taxonomy, and decide a PASS/FAIL runtime gate for the slice's acceptance behavior
- the run's actual output IS the Layer-1 runtime evidence (ADR-0048, `wos/gate-conditions.md`); a claimed-but-not-shown run is `unverified`, exactly like an asserted "tests pass"
- this is the "feedback edge": it catches the runtime bugs the static checks (lint, typecheck) never see (EXTERNAL_RESEARCH.md A2)
- MCP-agnostic about the runner (an MCP run tool, the Godot CLI `--headless`, or a human pressing play); it verifies the output, it does not prescribe the runner (DECISIONS D-1)
- verifies and routes the fix; it does not write or fix code; a hold-until-pass loop carries the bounded-retry cap (`wos/gate-conditions.md` interactive bounded retry)
- part of the Godot 2D-mobile game-dev cluster (ADR-0069)
- distinct from `godot-scene-plan` (plans the scene pre-code), `implement-approved-slice` and `implement-slice-complement` (write or fix code), `incident-triage` (sizes a fix from a concrete failure), and `review-hard` (Layer 2 design risk, after this Layer 1 gate)

Typical next commands:
- `slice-closure` or `review-hard` on a PASS (Layer 2 after the Layer 1 runtime gate is green)
- `incident-triage` on a FAIL whose cause or fix size is unclear
- `implement-slice-complement` on a FAIL with a bounded known fix inside the slice intent

### app-runtime-verify
Role:
- verify a built mobile/app runtime: run it (device, emulator/simulator, or headless), read the captured runtime output, classify runtime errors against a per-stack taxonomy, and decide a PASS/FAIL runtime gate for the slice's acceptance behavior
- the run's actual output IS the Layer-1 runtime evidence (ADR-0048, `wos/gate-conditions.md`); a claimed-but-not-shown run is `unverified`, exactly like an asserted "tests pass"
- React Native/Expo is the first documented adapter (taxonomy: NATIVE_CRASH, NAVIGATION_TEARDOWN, JS_ERROR, MISSING_NATIVE_MODULE, STARTUP_CRASH, ANR, PERMISSION_OR_CONFIG, CLEAN); a native crash class is judged from the native log, not the JS console; `wos/rn-expo-runtime-evidence.md` documents the capture path
- capability-routed and MCP-agnostic about the runner (an MCP run tool, an emulator, a device, or a headless run); it verifies the output, it does not prescribe the runner
- verifies and routes the fix; it does not write or fix code; a hold-until-pass loop carries the bounded-retry cap (`wos/gate-conditions.md` interactive bounded retry)
- capability-routed, not part of the Godot cluster (ADR-0087)
- distinct from `godot-runtime-verify` (Godot scenes), `implement-approved-slice` and `implement-slice-complement` (write or fix code), `incident-triage` (sizes a fix from a concrete failure), and `review-hard` (Layer 2 design risk, after this Layer 1 gate)

Typical next commands:
- `slice-closure` or `review-hard` on a PASS (Layer 2 after the Layer 1 runtime gate is green)
- `incident-triage` on a FAIL whose cause or fix size is unclear (and, for an upstream-bug escalation, its ADR-0086 read-comments gate)
- `implement-slice-complement` on a FAIL with a bounded known fix inside the slice intent

### design-bootstrap
Role:
- zero-state entry for design system work
- reads Figma via MCP (get_variable_defs, get_metadata, get_libraries)
- scaffolds foundation docs with real tokens, component/screen inventories, directory structure, OPEN_QUESTIONS.md
- analogous to `project-bootstrap` for project-level memory

Guard rails:
- do not invent tokens or components not present in Figma
- mark anything derived but not directly observed as `(proposed)`
- token naming must follow `wos/design-system-conventions.md` (semantic-first)

Typical next commands:
- `component-spec` (document individual components from inventory)
- `screen-spec` (document individual screens from inventory)

### component-spec
Role:
- generates a 15-section component spec from a Figma component via MCP
- sections: purpose, anatomy, variants, sizes, states (6 mandatory), a11y, motion, haptics, platform, security, performance, API, usage, anti-patterns, decisions
- marks every observation as confirmed (from Figma) or proposed (inferred)

Guard rails:
- do not invent visual properties not present in Figma
- reference foundation tokens by semantic name, not raw values
- states not visible in Figma (focused, loading) must be marked (proposed)

Typical next commands:
- next component from inventory
- `screen-spec`
- `journey-map`

### screen-spec
Role:
- generates a 12-section screen spec from a Figma frame via MCP
- sections: purpose, layout sketch, spacing, components used, data deps, copy, a11y, interactions, error states, related screens, open questions, decisions
- maps elements to DS components by name and tier

Guard rails:
- reference components by DS name, not visual description
- mark data dependencies and error states as (proposed) since Figma has no data layer

Typical next commands:
- next screen from inventory
- `journey-map`
- `implementation-plan`

### image-to-spec
Role:
- generates a spec from a raw image file (a screenshot, mockup, captured screen) when there is no Figma source
- `--component` produces a COMPONENT_SPEC-shaped doc; `--screen` produces a SCREEN_SPEC-shaped doc; no flag auto-detects (single element vs full screen) and states the choice
- reads the image with vision; writes only a spec doc

Guard rails:
- marks every observation `(proposed)`, never `confirmed`, since an image is an inference source not a source of truth; visible copy is the only verbatim content
- never calls the Figma MCP, generates into Figma, fetches the web, or produces code (it emits a spec, not an implementation)
- distinct from `component-spec` / `screen-spec` (Figma-sourced) and from `generate_figma_design` (image into Figma)

Typical next commands:
- `component-spec` / `screen-spec` (upgrade against Figma when one becomes available)
- `design-spec-review` (check an implementation against this spec)
- `implementation-plan` (build from the spec)

### journey-map
Role:
- documents a user journey across 3+ screens
- sections: outcome, screens, components, flow diagram, critical states (4+ minimum), reference pattern, a11y, security, performance, open questions, decisions
- project-specific (not reusable across projects; for reusable patterns use `pattern-doc`)

Typical next commands:
- `pattern-doc` (when a reusable pattern emerges from the journey)
- `implementation-plan`

### pattern-doc
Role:
- documents a reusable UX pattern applicable across multiple screens and projects
- sections: problem, solution, when to use, when not, components, variants, a11y, examples (good/bad), related patterns, decisions
- Polaris-inspired; patterns live in `docs/research/patterns/`

Typical next commands:
- `implementation-plan`
- next pattern

### design-spec-review
Role:
- verifies component/screen implementation against its spec doc
- 10 checks: variants, sizes, states, a11y, tokens, motion/haptics, TypeScript API, Storybook story, anti-patterns, platform specifics
- distinct from `review-hard` (general risk) and `repo-consistency-sweep` (pattern matching)

Guard rails:
- do not implement fixes (analysis only)
- if no spec doc exists, return no-op and route to `component-spec` or `screen-spec`
- if implementation is faithful to spec, say so clearly

Typical next commands:
- `implement-slice-complement` (if findings need fixing)
- `pr-package`

### foundation-audit
Role:
- compares code tokens vs foundation docs vs optionally Figma variables
- detects: undocumented tokens, unimplemented tokens, value drift, possible renames
- 3-way comparison (code, docs, Figma) when Figma URL is provided

Guard rails:
- do not modify token files or docs (analysis only)
- every finding must cite actual code value AND doc value

Typical next commands:
- `implement-slice-complement` (to fix drift)
- `pr-package`

### extract-foundations-from-screens
Role:
- reads a batch of `SCREEN_SPEC.md` files, unions raw values (hex colors, typography tuples, spacing px, radii px)
- buckets each value into a role token per per-foundation rules (color: surface/text/accent; typography: display/heading/body/caption; spacing: 4px grid; radii: 8/12/16/24 progression)
- writes or updates `foundations/color.md`, `foundations/typography.md`, `foundations/spacing.md`, `foundations/radii.md` against existing FOUNDATION templates
- idempotent: locked role-to-value mappings from prior runs are preserved; collisions and off-grid values go to a `## Review queue` section

Guard rails:
- never overwrite locked role-to-value mappings (always route collisions to `## Review queue`)
- never silently round off-grid spacing/radii values into the scale
- never invent role names beyond the canonical vocabulary (semantic refinement is a human review step)
- do not emit code artifacts (Tailwind, CSS variables) -- that belongs to a later `emit-foundations-tokens` step

Typical next commands:
- `foundation-audit` (verify extracted role tokens vs code)
- `component-spec` (start consuming the new role tokens)

### atom-audit
Role:
- tier-scoped audit of every atom under `packages/design-system/src/atoms/` (or equivalent)
- checks each atom against rules in `docs/research/COMPONENT_GUIDELINES.md` (memo, callbacks, inline styles, press anim, touch target, a11y, reduced motion)
- produces or refreshes `docs/research/ATOM_AUDIT.md` table; appends row to Audit history
- groups findings into top 3 fix groupings as candidate slices

Guard rails:
- analysis only; no code fixes applied by this command
- requires COMPONENT_GUIDELINES.md to exist (route to `design-bootstrap` or a guidelines-bootstrap slice otherwise)
- columns of ATOM_AUDIT.md must match rules in COMPONENT_GUIDELINES.md (extend table first if guidelines added a rule)

Typical next commands:
- `task-init` (per fix grouping; one task per rule cluster)
- `pr-package`

### atom-audit-fleet
Role:
- orchestrator-workers variant of `atom-audit` per ADR-0034 (J.6 PILOT, 2026-06-04), structural contract per ADR-0038 (PENDING lived runs)
- Sonnet orchestrator dispatches N Haiku workers, each auditing 3-5 atoms
- batch by batch_size (default 4); max_fanout 20; barrier convergence with 10-min timeout; union merge by `component` key
- workers check the same 7 rules as `atom-audit`: memo, callbacks, inline styles, press anim, touch target, a11y, reduced motion
- orchestrator is SOLE writer of `ATOM_AUDIT.md` per `wos/substrate-peers.md`
- per-worker classification events + one fleet-merge line logged to `.wos/VERIFICATION_LOG.jsonl`

Guard rails:
- analysis only; no code fixes applied (same as `atom-audit`)
- requires COMPONENT_GUIDELINES.md to exist (NO_OP_TRACE + route to `design-bootstrap` otherwise)
- requires atom count >= 6 to be cost-effective; below threshold use `atom-audit` single-agent
- if COMPONENT_GUIDELINES.md added new rule not in worker_output_schema, NO_OP_TRACE: route to schema-extension slice first
- workers NEVER write substrate; orchestrator is SOLE writer

Typical next commands:
- `task-init` (per fix grouping; one task per rule cluster) -- same as `atom-audit`
- `pr-package`

### screen-spec-fleet
Role:
- orchestrator-workers variant of `screen-spec` per ADR-0034 (J.7 PILOT, 2026-06-04; Bruno's primary multi-agent scenario), structural contract per ADR-0038 (PENDING lived runs)
- Sonnet orchestrator dispatches N Sonnet workers (1 screen each) in parallel
- each worker runs the full 12-step `screen-spec` flow for ONE Figma frame: `get_design_context` -> `get_screenshot` -> components -> layout -> spacing -> data -> copy -> a11y -> interactions -> error states -> related -> write file
- max_fanout 20; barrier convergence with 15-min timeout (Figma MCP latency); union merge
- workers write their own spec file directly (no overlap by construction since `(screen_number, persona, slug)` is unique)
- orchestrator is SOLE writer of `SCREEN_MAP.md` and `routes.md` per `wos/substrate-peers.md`
- one persona per fleet run (mixing personas FORBIDDEN to keep merge keys unambiguous)
- per-worker classification events + one fleet-merge line per substrate file logged to `.wos/VERIFICATION_LOG.jsonl`

Guard rails:
- analysis only; produces spec docs + index updates, no code implementation
- caller MUST pre-enumerate frames into manifest (`{screen_number, slug, persona, figma_node_id, journey?, route?}` per screen); orchestrator does NOT auto-discover frames
- requires Figma MCP available (`get_design_context`, `get_screenshot`); NO_OP_TRACE if missing
- requires foundations + SCREEN_MAP.md to exist; NO_OP_TRACE + route to `design-bootstrap` if foundations missing
- requires N >= 6 to be cost-effective; below threshold use `screen-spec` single
- duplicate `(screen_number, persona, slug)` triples in manifest -> NO_OP_TRACE with list of dupes
- workers NEVER write SCREEN_MAP or routes; orchestrator is SOLE writer

Typical next commands:
- `journey-map` (if fleet covered a complete journey end-to-end)
- `task-init` (per screen group for implementation)

### inventory-snapshot
Role:
- enumerate every Figma component in the upstream library via MCP (`get_libraries` / `get_metadata`)
- classify each by tier (atom / molecule / organism / layout) per `wos/design-system-conventions.md`
- check WOS-UI traceability per row: spec doc / code dir / Storybook story present or empty
- compute delta vs previous snapshot (ADDED / RENAMED / DEPRECATED / RESCOPED)
- refresh priority queue (top 5 components to document next)
- write `docs/research/_inventory/figma_components.md`

Guard rails:
- read-only against WOS-UI surface (spec docs, code, stories); only inventory file is written
- when tier is ambiguous, mark `(proposed)` and surface as open question rather than guessing

Typical next commands:
- `component-spec` (on #1 priority entry)
- `task-init` (if multiple components need batch documentation)

### jtbd-switch-interviewer
Role:
- K.8 CUSTOM persona (L2; folder-shaped layout) per ADR-0034 + `wos/maturity-ladder.md`
- senior JTBD switch-interview researcher (Christensen / Moesta lineage) walking users backward through trigger -> struggle -> switch timeline
- captures the four forces of adoption (push, pull, anxiety, habit) with verbatim user quotes; refuses to synthesize a force without at least one quote backing it
- rolls up across interviews into STRONG / EMERGING / ANECDOTAL pattern strength; never lets ANECDOTAL drive a PROPOSED decision
- writes `<task>/JTBD_INTERVIEWS.md` (persona report) + PROPOSED blocks under DECISIONS.md / TASK_STATE.md / IMPLEMENTATION_PLAN.md only at L1; promotion via Pattern A handoff per `wos/substrate-peers.md`
- maintains explicit "We do not have evidence for X" gap subsection so absence-of-evidence is not silently treated as evidence-of-absence

Guard rails:
- refuses (NO_OP_TRACE) when the hypothesis names only a feature wishlist with no incumbent OLD solution to switch from
- never paraphrase: paraphrase laundering is the primary failure mode the persona prevents
- never write substrate directly at L1; PROPOSED blocks only + Handoff routing to owner command
- never let ANECDOTAL (n=1) cluster drive a PROPOSED decision proposal

Typical next commands:
- `decision-interview` (promote PROPOSED D-N drafts)
- `capture-observation` (when quote bank surfaces a single high-signal observation worth capturing distinct from a full decision)
- `implementation-plan` (when STRONG ANXIETY or HABIT risks need plan-level mitigation)

### release-plan
Role:
- design a pre-deploy release/rollout strategy for a change: pick the pattern (feature flag / canary / blue-green / progressive delivery) by risk and infra, then the exposure ramp, the promotion metric + threshold, and the rollback trigger + mechanism
- stack/infra-agnostic (reasons over exposure unit / advance signal / rollback action); designs the rollout, never runs a deploy
- produces `<task>/RELEASE_PLAN.md`; post-deploy-verifier consumes its promotion metric + rollback mechanism (D-1)

Guard rails:
- promotion-metric threshold cites SLO_SPEC when present, or is marked PROPOSED-pending-baseline; never an invented number
- rollback mechanism named from what the repo actually has, never assumed
- D-1 boundary: designs the rollout; post-deploy-verifier consumes it; standing-pipeline rollback audit reserved for the future pipeline-gate-review
- a trivial reversible change gets SKIP/NO_OP routing to branch-commit / pr-package, not a manufactured rollout plan

Typical next commands:
- `post-deploy-verifier` (author the post-deploy checks that consume this plan)
- `decision-interview` (lock a rollout policy)
- `pr-package` (deliver the change)
- `slo-define` (the promotion metric needs an SLO basis)

### postmortem-author
Role:
- K.8 CUSTOM persona (L1 at launch; folder-shaped layout) per ADR-0034 + `wos/maturity-ladder.md`
- senior reliability engineer authoring a blameless postmortem for a resolved incident: timeline, contributing causes (no individual fault), impact vs error budget, owned action items
- produces `<task>/POSTMORTEM.md`; incident-triage (ESCALATE / significant HOTFIX) and task-close route into it for significant incidents
- distinct from incident-triage (live triage + the inline `### Learnings` quick reflexion) and slo-define (the contract this measures impact against)

Guard rails:
- blameless: contributing causes are systemic, never individual fault; a postmortem that names a person has failed
- every action item is concrete, verifiable, and owned; never "be more careful"
- a routine slice or trivial fix is routed back (the inline incident-triage `### Learnings` covers it), not given a full postmortem
- an action item that is real work routes to task-init; do not do the fix here
- never write substrate directly at L1; PROPOSED blocks only + Handoff routing

Typical next commands:
- `task-init` (a follow-up fix task)
- `slo-define` (the incident exposed a missing SLO)
- `decision-interview` (a policy action item)
- `task-close` (this closes the incident task)

### slo-define
Role:
- K.8 CUSTOM persona (L1 at launch; folder-shaped layout) per ADR-0034 + `wos/maturity-ladder.md`
- senior reliability engineer defining a service's reliability contract before incidents: SLIs, SLO target + window, error-budget math (100% minus SLO), and the error-budget policy
- produces `<task>/SLO_SPEC.md`; the SLO threshold grounds post-deploy-verifier negative checks and SLO burn weights incident-triage urgency (D-1/D-3)
- distinct from incident-triage (reactive triage) and post-deploy-verifier (per-slice verification); both consume this contract

Guard rails:
- every SLO target cites a baseline/SLA/user-target or is marked PROPOSED-pending-baseline; never a fabricated 99.9%
- SKIP when no observability stack can measure the SLIs (route to decision-interview); never invent an unmeasurable SLO
- defines the contract only; never instruments an SLI or runs a probe
- never write substrate directly at L1; PROPOSED blocks only + Handoff routing

Typical next commands:
- `decision-interview` (lock the SLO target + budget policy)
- `post-deploy-verifier` (use the SLO in a deploy's negative checks)
- `incident-triage` (a live failure is burning the budget)
- `implementation-plan` (slice the instrumentation work)

### ai-feature-eval-harness
Role:
- design a repeatable, dataset-backed evaluation plan for a product AI feature (model-backed or non-deterministic output)
- defines measurable success criteria, a held-out labeled eval set, per-criterion grading (code-based first, LLM-as-judge only for nuanced criteria), and a pass threshold + regression rule
- code-graded tier composes with ADR-0048 (a passing deterministic gate is Layer-1 evidence); the LLM-graded tier is added signal
- produces AI_EVAL_PLAN.md

Guard rails:
- gate on a model-backed output: deterministic behavior routes to test-strategy, not here
- distinct from verify-against-rubric (judges Fhorja's own command artifacts, not the user's product feature)
- reject vague success criteria; restate measurably or mark NEEDS a measurable definition
- no train/eval leakage in the dataset split
- plans the eval; does not build or run the harness

Typical next commands:
- `test-strategy` (deterministic behavior coverage for the same change)
- `implementation-plan` (slice the harness build)
- `decision-interview` (lock the quality target)
- `implement-approved-slice`

### performance-budget
Role:
- K.8 CUSTOM persona (L1 at launch; folder-shaped layout) per ADR-0034 + `wos/maturity-ladder.md`
- senior performance-budget auditor declaring numeric non-functional budgets (Core Web Vitals, latency percentiles, payload/bundle size, key-operation cost) before a change ships
- per-metric budget: threshold + percentile + measurement source + regression action
- declares numbers only; routes enforcement to the consuming repo's deterministic gate (ADR-0048) and post-deploy-verifier; never runs a load test itself
- produces `<task>/PERFORMANCE_BUDGET.md` with the budget table (no silent omission) + PROPOSED budget policy under DECISIONS.md

Guard rails:
- every threshold cites a source (measured/standard/SLA/user-target) or is marked PROPOSED-pending-baseline; never a guessed number asserted as measured
- every row has a concrete regression action; never bare "monitor it"
- a no-performance-surface task returns SKIP/NO_OP routing to decision-interview, never an empty budget
- spec-only; never runs a load test or profiler (that collides with the ADR-0048 gate contract)
- never write substrate directly at L1; PROPOSED blocks only + Handoff routing

Typical next commands:
- `test-strategy` (functional coverage for the same change)
- `post-deploy-verifier` (live-signal verification post-ship)
- `implementation-plan` (slice the optimization work)
- `decision-interview` (lock the budget policy)
- `implement-slice-complement` (small optimizations under an open slice)

### a11y-audit
Role:
- K.8 CUSTOM persona (L1 at launch; folder-shaped layout) per ADR-0034 + `wos/maturity-ladder.md`
- senior accessibility auditor mapping a UI surface (screen, flow, or component set) to WCAG 2.2 at a named conformance level (A/AA/AAA)
- whole-surface per-criterion conformance ledger; every applicable success criterion gets a row, labeled machine-checkable or manual-review
- delegates contrast (1.4.3/1.4.11) to color-contrast-architect and single-component spec fidelity to design-spec-review
- produces `<task>/ACCESSIBILITY_AUDIT.md` with the full ledger (no silent omission) + a manual-review queue + PROPOSED conformance target under DECISIONS.md

Guard rails:
- never assert a machine verdict for a manual-judgment criterion; no checker ran means MANUAL-REVIEW, not a guessed PASS/FAIL
- never recompute contrast; cite CONTRAST_AUDIT.md or Handoff to color-contrast-architect
- surface-type labeling mandatory (web ARIA/DOM vs native accessibility API); never assume a DOM on a native surface
- a no-UI-surface task returns SKIP/NO_OP routing to decision-interview, never an empty ledger
- never write substrate directly at L1; PROPOSED blocks only + Handoff routing

Typical next commands:
- `color-contrast-architect` (contrast rows pending)
- `design-spec-review` (single-component fidelity)
- `implementation-plan` (slice the remediation)
- `decision-interview` (lock the conformance target)
- `implement-slice-complement` (small fixes under an open slice)

### color-contrast-architect
Role:
- K.8 CUSTOM persona (L2; folder-shaped layout) per ADR-0034 + `wos/maturity-ladder.md`
- senior design-system color contrast architect auditing every documented foreground/background pair against WCAG 2.2 AA/AAA per design context (normal text, large text, UI components, focus indicators)
- pairwise audit across light and dark themes BEFORE visual choices lock
- computes contrast ratio per WCAG 2.2 relative-luminance formula; never rounds up to clear a threshold
- multi-context pairs scored against the strictest applicable threshold
- produces `<task>/CONTRAST_AUDIT.md` with full matrix (no silent omission) + PROPOSED contrast policy under DECISIONS.md

Guard rails:
- never emit "fix it" as remediation; persona's value is the suggested token delta (hex or alias-chain)
- never silently omit a documented pair; matrix MUST cover every input pair
- when in doubt about design context, flag multi-context and score against strictest threshold (do not guess)
- never write substrate directly at L1; PROPOSED blocks only + Handoff routing

Typical next commands:
- `screen-spec` (audit cleared the visual bar for next screen)
- `foundation-audit` (multiple foundation tokens need rework)
- `decision-interview` (PROPOSED contrast policy needs locking)
- `targeted-questions` (missing pairs blocked the audit at Step 1)

### rls-auth-boundary-auditor
Role:
- K.8 CUSTOM persona (L3; folder-shaped; multi-repo-aware) per ADR-0034 + `wos/maturity-ladder.md`
- senior database security architect auditing Supabase RLS policies for tenant isolation gaps BEFORE the migration ships
- follow-the-data discipline: traces EVERY relationship (FK, join table, materialized view, audit/log table) to confirm policy chain is unbroken
- catches: USING without WITH CHECK (insert path bypass), RLS without FORCE ROW LEVEL SECURITY (table-owner bypass), missing policies on join/audit tables, missing tenant predicates, SECURITY DEFINER functions without RLS-aware guards, unjustified service_role bypass paths
- produces `<task>/RLS_AUDIT.md` with per-table posture table (PASS / GAP / FAIL) + migration-shaped remediation (concrete CREATE POLICY / ALTER TABLE statements)

Guard rails:
- never silently omit a tenant-scoped table touched by the migration set
- never emit prose advice ("consider tightening") as remediation; every fix MUST be migration-shaped SQL
- gaps MUST cite a concrete failure mode tied to the SQL under audit (not "looks weak")
- never write substrate directly at L1; PROPOSED blocks only + Handoff routing

Typical next commands:
- `implementation-plan` (slice the remediation work)
- `decision-interview` (multi-policy tradeoffs need user input)
- `approve-proposed` (findings clear-cut; no decisions need locking)

### migration-safety-steward
Role:
- K.8 CUSTOM persona (L2; folder-shaped layout) per ADR-0034 + `wos/maturity-ladder.md`
- senior database migration safety steward auditing DDL for production-unsafe patterns BEFORE the migration is applied
- per-statement verdict table (SAFE / NEEDS-PHASING / UNSAFE) with no silent grouping; even a file with 12 CREATE INDEX lines yields 12 rows
- pattern classification: ADD-COLUMN-NULLABLE / ADD-COLUMN-NOT-NULL / DROP-COLUMN / RENAME-COLUMN / ALTER-TYPE / CREATE-INDEX / DROP-INDEX / ADD-FK / ADD-CHECK / ADD-UNIQUE / TRIGGER-CHANGE / OTHER-DDL
- canonical safe-variant rules per pattern: backfill phase for NOT NULL; two-phase for DROP-COLUMN; double-write for RENAME-COLUMN; CONCURRENTLY for CREATE-INDEX; NOT VALID + VALIDATE for ADD-FK; etc.
- biases NEEDS-PHASING when row count or deploy strategy is unknown; flags IRREVERSIBLE operations for explicit user confirmation via Handoff to `decision-interview`
- produces `<task>/MIGRATION_SAFETY.md` (per-statement verdict + risks grouped P0/P1/P2 + recommended phasing + rollback plan + irreversible-operations subsection)

Guard rails:
- never emit prose advice as remediation; every fix MUST be statement-shaped SQL or online-DDL tool invocation
- never silently group statements in the verdict table
- bias toward NEEDS-PHASING under uncertainty; cost of false SAFE on production migration is irreversible
- never write substrate directly at L1; PROPOSED blocks only + Handoff routing

Typical next commands:
- `implementation-plan` (re-slice migration into safe phases when NEEDS-PHASING surfaced)
- `decision-interview` (IRREVERSIBLE confirmation or non-trivial tradeoffs)
- `approve-proposed` (all statements SAFE; only output is verdict table + risk acknowledgements)

### post-deploy-verifier
Role:
- K.8 CUSTOM persona (L3; folder-shaped; multi-repo-aware) per ADR-0034 + `wos/maturity-ladder.md`
- senior reliability engineer producing the per-slice post-deploy verification PLAN (distinct from `verify-against-rubric` which renders the verdict)
- maps every acceptance criterion (AC-N) to the smallest-resolution live signal that proves or refutes it
- signal classes: structured log query (with exact field filters), dashboard panel (URL + scoped tags + time bounded by deploy window), smoke-test user flow (exact route + form inputs + expected DOM/API shape), feature-flag toggle check (exact key), DB invariant query (exact SQL or view name)
- includes at least one NEGATIVE CHECK that would prove the change did NOT ship (catches silent no-op deploys)
- rollback trigger checklist names specific humans (or named on-call rotation handle) + exact rollback command / flag-flip syntax
- multi-repo split: backend signals to `POST_DEPLOY_PLAN.backend.md`, frontend to `POST_DEPLOY_PLAN.frontend.md`, cross-repo correlation notes in backend file
- produces `<task>/POST_DEPLOY_PLAN.md` (or per-repo variants) + PROPOSED `## Post-deploy checks` block for slice file via Pattern A handoff to `slice-closure`

Guard rails:
- every AC MUST map to at least one named live signal (zero orphan ACs)
- every signal MUST be query-shaped (no "check the logs"-class vagueness)
- at least one negative check is mandatory (silent no-op deploys are the failure mode)
- rollback checklist MUST name specific humans + exact commands (implicit "the on-call will know" is forbidden)
- trim shotgun "check everything" lists: every signal traces to one AC or one named risk

Typical next commands:
- `verify-against-rubric` (plan revealed a frozen rubric is now authorable)
- `slice-closure` (apply ## Post-deploy checks PROPOSED block, close slice)
- `direction-adjust` (plan surfaced a needed follow-up slice)
- `approve-proposed` (land PROPOSED blocks immediately)
