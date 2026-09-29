---
name: review-hard
description: |-
  Review the current task changes for real correctness, safety, and maintainability risks before slice closure or PR prep, and recommend the smallest safe next step. Surfaces meaningful issues (not cosmetic feedback); not a replacement for external review systems. Returns no-op when the review would not materially change conclusions. Use when a slice or task-level implementation was completed, the user wants a focused engineering risk review before closure or PR prep, or the current need is to surface meaningful issues. Do not use when no meaningful implementation has happened yet, the task is still in discovery or contract refinement or planning, or the goal is full external code review replacement rather than a focused internal risk check. Supports an opt-in `--consistency N` consensus mode (off by default) that runs N independent review passes over the same changes and merges them by consensus, per ADR-0073.
metadata:
  category: "execution-and-closure"
  primary-cursor-mode: "Ask"
  multi-repo-aware: "false"
  context-layers-consumed: "memory"
  context-layers-produced: "memory"
  tools: "Read, Write, Edit, Bash, Glob, Grep"
  x-wos-profiles: "minimal, core, full"
  provenance: "first-party"
  suggested-model: "claude-opus-5-5"
---
> **Output contract, in brief.** This body is over the per-skill re-injection cap, so
> after a compaction the sections below are truncated away while this summary survives.
> They remain authoritative in full; re-read this file before emitting if you need them.
>
> - `Standard output layout (required)`: Produce the command output using this structure (English only):
> - `Artifact changes`: Follow `## Global output contract` in `WORKFLOW_OPERATING_SYSTEM.md` for `APPLIED` / `PROPOSED` / `SKIP` rules. Every listed file...
> - `Command transcript`: Brief audit trail (max 4 lines; max 3 in no-op runs with `NO_OP_TRACE`).
> - `Handoff`: Use the adaptive ending format of `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract`. Every Handoff is one fenced `text` b...
> - `Definition of done (command output)`: Issues are ranked must/should/optional with concrete references to code/tests.


Act as a skeptical senior/staff engineer performing a pre-PR engineering risk check for the active engineering task.

Goal:
Review the current task changes for real correctness, safety, and maintainability risks, then recommend the smallest safe next step, with explicit no-op behavior when the review would not materially change conclusions.

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
- TASK_STATE.md
- DECISIONS.md
- IMPLEMENTATION_PLAN.md
- relevant real code changes
- latest validation/test results, if available
- last completed step from TASK_STATE.md (command + summary)
- optional: `--consistency N` to run N independent review passes over the same changes and merge them by consensus (off by default; `N=3` recommended), per ADR-0073

Operating rules:
- **Runtime-debug-payload triage FIRST (ADR-0088).** FIRST ACTION, before any review step: IF the invocation args are a runtime-debug payload (pasted runtime logs such as an `adb logcat` or Metro dump, a stack trace or crash signature, a "still happening" or "got the error again" symptom) THEN the command SHALL route it to `incident-triage` BEFORE any review work and SHALL NOT absorb it into a review. `incident-triage` owns the debug loop: it classifies the failure, applies the instrument-first locus gate, and maintains the ruled-out-hypotheses ledger (ADR-0088). A payload that mixes real code-risk observations with runtime-debug logs is split: review the code-risk part here and route the runtime-debug part to `incident-triage`. This triage is payload-shape-conditional and additive; a normal code-review invocation is unaffected. It exists because the rn-dogfood audit showed `review-hard` used ~10 times as an ad-hoc debug-iterate loop with pasted logs, and the 2026-07-10 connector dogfood showed the clause skipped when it sat mid-list: the payload was absorbed and diagnosed inline. First position plus eval scenario 102 is the enforcement fix.
- **Mechanical compliance check for the rule above.** Before composing any other output section, the command SHALL first state explicitly, as its very first line of output, whether the invocation args are a runtime-debug payload (a literal "Runtime-debug payload: yes" or "Runtime-debug payload: no" line). A response that proceeds to any other section without this explicit line first SHALL be treated as not satisfying this command's Definition of done. This exists because an audit found the rule above fired in narration (the model recognized a runtime-debug payload) but was still not acted on twice in one session; a first-line explicit statement makes compliance checkable instead of trusting narration.
- **Handoff:** end with the adaptive `### Handoff` block per `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full).
- **Declare the scan set before reviewing, and name the residual after (B22, 2026-09-17).** This command's verdict is the highest-stakes one in the workflow, and until now it stated what it FOUND without ever stating what it LOOKED AT.
  - BEFORE reading anything: state the scan set. Derive it, do not assemble it by feel: the files under review are the union of the slices' `Scope:` lines, or `git diff --name-only <base>` when the review covers a branch. State the criterion set too, normally the `wos/bug-classes/` categories this pass will apply. Both go in the output before the findings.
  - AFTER the pass: emit the coverage record. `python3 scripts/compute-task-outcome.py --review-coverage <task-slug> --project <client__project> --units-declared N --units-checked N --criteria "<named set>" --residual "<what was not checked and why>" --findings N >> projects/<client__project>/OUTCOMES.jsonl`. The helper only prints the line; the `>>` is the append (ADR-0217). Resolve `scripts/compute-task-outcome.py` against the WORKFLOW ROOT (the clone, or the installed docs directory, which ships it per ADR-0217), never against the task repository; when it is in neither, name that in `### Command transcript` instead of reporting the append.
  - `--residual` is required and an empty one is REFUSED, not degraded. A de-scope is allowed; silence is not. That is the rule `commands/_shared/deliverable-reconcile.md` already applies to the deliverable ledger, and this moves it to a second object. A pass that reached everything writes why that is credible; it does not write nothing.
  - Why it exists, stated so nobody removes it as ceremony. A verdict with no declared scope is a claim about the COMPLEMENT of what was checked, and nothing grounds that. It is why "are you sure?" has no stable answer: each re-ask finds something real, so no earlier round was ever trustworthy, and there is no round at which asking stops being productive. Measured against the literature on 2026-09-17: re-asking is repeated sampling and its coverage keeps rising, so the loop does not terminate on its own. A declared scope plus a named residual terminates it, because reopening then requires NAMING a unit or a criterion rather than asking again.
  - The contract this creates, and it cuts both ways. A finding inside a unit this pass declared checked-clean is not a successful re-ask, it is a PROCESS DEFECT, and it gets recorded as one. A finding inside the residual is expected and costs the pass nothing.
  - No confidence value anywhere in this block. Coverage says what was looked at, never how sure the looking felt, and a certainty field here is the exact shape ADR-0109 D-2 forbids.

- **Operating mode (ADR-0008, ADR-0162).** WHEN `TASK_STATE.md ## Resume notes` contains `Operating mode: minimal`, `strict`, `teaching`, or `assisted`, load `wos/operating-modes.md` and apply that mode. WHEN the line is absent, use this command's native rules. Auto-suggestion is not a declaration.
- **Playtest-payload triage (ADR-0084).** Before reviewing, check whether the invocation args are playtest feedback rather than a request for a code-risk review: notes that the game runs but plays wrong, a mechanic feels off, a screen flow is missing, or difficulty or pacing is bad. That payload is not an engineering-risk review input; route it to `pr-feedback-ingest --playtest` (the first-class playtest ingestion path) instead of absorbing it into the review. This exists because the dogfood behind ADR-0084 had both of its core-mechanic corrections pasted into `review-hard` args for want of a designated path. A payload that mixes real code-risk observations with playtest notes is split: review the code-risk part here and route the playtest part onward. This triage is payload-shape-conditional and additive; a normal code-review invocation is unaffected.
- Before producing output, verify the review would materially change risk judgment versus the latest recorded state and artifacts.
- If the diff and validation evidence are unchanged since the last meaningful review, do not generate new churn; return a no-op and route forward.
- No-op rule for artifacts:
  - If `TASK_STATE.md` would not materially change, do not rewrite it.
  - Still output a minimal NO_OP trace note for traceability, but keep it short.
- Exempt from the no-op rule: a silent omission in the `## Requested deliverables` ledger (a deliverable with no row, or a row dropped without a recorded de-scope; per the deliverable-reconcile gate below) is always a must-fix finding, even when the diff and validation evidence are unchanged since the last review. A vanished deliverable is exactly the silent omission the gate exists to catch, so it is never suppressed as no-op churn.
- Focus on:
  - correctness
  - unsafe assumptions
  - hidden regressions
  - contract and schema mismatches
  - migration/data risks
  - concurrency or idempotency issues
  - weak or misleading tests
  - overengineering
  - maintainability
  - an external vendor contract point (auth format, delivery mechanism, payload shape) that is captured but self-acknowledged as unconfirmed, especially when evidenced only by a vendor demo/example payload rather than a live capture
  - drift from `DECISIONS.md` or the active slice, and scope creep: unrelated refactors, drive-by files, or follow-ups folded into the diff instead of listed
  - edge cases the plan or slice named, handled or explicitly deferred, and error paths that lose data or report a false success
  - authz, tenancy, PII, secrets, or payment-adjacent paths, whenever the diff touches one
  - a rollback or feature-flag story that is not credible for the change size
  - validation the slice or `TASK_STATE.md` cites but that never ran, and flaky or skipped tests that hide a regression
  - observability (logs, metrics, and errors enough to debug this change in production) and performance or capacity impact
- Distinguish clearly between:
  - must fix
  - should fix
  - optional improvements
- **Severity floor for unresolved external contracts (ADR-0108).** An external-vendor contract point that is captured but explicitly flagged as unconfirmed (in `REFERENCES.md`, a PR note, or task memory) is ALWAYS at minimum a must-fix when it sits on a security-critical or fully-gating path (auth, payment, PII, or any point where a wrong assumption blocks 100% of a code path, not an edge case). This holds even when a workaround exists, even when the code "degrades gracefully" on failure, and even when the point is already written down as a known risk: being on the record is not the same as being gated, and a flat PR-notes bullet reads as an ordinary accepted trade-off to both human and automated reviewers. Do not downgrade this class of finding to should-fix or optional on the grounds that "it's already flagged" -- flag it as must-fix and require either a live verification of the real vendor behavior or an explicit `decision-interview` record of the accepted risk before the finding can be closed.
- **Provisional decisions (ADR-0233).** Drift is measured against `## Locked decisions` and `## Provisional decisions` both. A product choice the diff makes that neither records is a must-fix routed to `decision-interview`, which in an attended chain on a task branch records a provisional P-N; there the accepted-risk record the severity floor above asks for may be a P-N with `Impact: high`, left for the person to confirm before merge. In that chain, at the pre-PR final pass, a row `decision-interview` left `in-scope` under "Not delivered, needs you" does not invalidate this output, because the draft PR lists it.
- Tag each finding with an impact band (LOW, MEDIUM, HIGH) and a rough effort band, then order findings by impact relative to effort, with impact as the primary key, so the highest value per unit of effort surfaces first. Effort is a tiebreak, never a reason to drop a cheap critical fix.
- Call out what should not have changed if relevant.
- If the implementation is solid, say so clearly rather than inventing feedback.
- Treat this as a focused pre-PR engineering risk check, not a replacement for external review systems.
- **Discharge rules for dismissing a finding (mobile dogfood 2026-07-29).** The burden of proof sits on the dismissal, not on the finding. "Consistent with the surrounding file" is not a valid dismissal: local precedent is descriptive, not normative. "Pre-existing pattern" excuses only a line the diff did NOT touch; the moment a diff touches a line, that line is this review's business. A dismissal that names neither a cited rule nor an inspected fact is an unresolved finding, not a closed one.
- **Verified-clean is not a finding.** A hypothesis this review checked and refuted, and a mechanism it inspected and found sound, route to `incident-triage` for its `## Ruled-out hypotheses` ledger (that command is the section's sole owner per `wos/substrate-peers.md`). They never enter the findings list, which carries only items with a proposed action. On the source run, 33 of 81 canonical findings were verified-clean markers or INFO-level observations with no action, so a third of the fixer's triage budget went to items that were never findings.
- **Read-only fan-out by default (D-5 of the parallel-work research, ADR-0236).** WHEN the diff under review splits into 3 or more independent file groups (by package, module or directory, whichever keeps related files together), dispatch one read-only `judgment` worker per group, at most 9 at once, overflow in sequential sub-batches, per `WORKFLOW_OPERATING_SYSTEM.md ## Parallel workflow`. Each worker receives its group's diff and the review criteria this command applies, reads, and returns its findings; it writes nothing but its one assigned return file. This command is the only writer: it merges and dedupes the findings, runs the cross-group pass over the seams between groups itself, with the authoring context it already holds, and writes every artifact. Below 3 groups the review stays a single pass. The `--consistency` passes and refuters below count toward the 9 at once.
- **Opt-in self-consistency consensus mode (`--consistency N`, per ADR-0073).** This mode is OFF by default; without the flag the changes are reviewed once, split across group workers per the bullet above when there are 3 or more groups. When invoked with `--consistency N`, run N independent review passes with fresh context over the same changes, each a `judgment` dispatch (ADR-0236; `wos/model-routing.md ## Dispatch roles`), then merge the findings by consensus-of-N (the strategy defined in `commands/_shared/worker-contract.md`): a finding that appears in at least `ceil(N/2)` passes is high-confidence; a finding that appears in fewer passes is a singleton, kept as advisory and labeled, never silently dropped. Cost guard: total review cost multiplies by N, so this is strictly opt-in and `N=3` is the recommended setting; reserve it for high-stakes changes where the added confidence is worth the spend.
- **Two-field verdict and a refuter stage (ADR-0122, extends ADR-0073).** Under `--consistency N`, record each finding as two fields, not one: `premise` (stands | falls) and `proposed fix` (take | refuted, with the reason). A finding whose premise is real but whose suggested fix would make things worse is a common and currently inexpressible outcome; splitting the fields is what lets the review say so instead of choosing between adopting a harmful fix and discarding a true finding. Then, after the N raise passes and BEFORE the findings are handed on, dispatch a fixed small refuter count (default 3), each a `judgment` dispatch, ONCE over the whole surviving must-fix and should-fix set, instructed to disprove each finding and to default to refuted when uncertain, and record every killed finding with the citation that disproved it. Do not fan out one refuter per finding: `wos/context-budget.md` measures 400k to 1.3M tokens per 10-agent batch, and a real run carried 35 queued fixes. Agreement between raise passes reading the same file the same way is correlated, not independent, so N agreeing passes raise confidence in what was noticed, never in whether it is true. A verification stage that only ever confirms is not verifying.

- **A zero-finding verdict is not a terminal state (ADR-0145, extends ADR-0033).** WHEN this review's verdict names zero must-fix and zero should-fix findings AND the diff under review touched product code, the output SHALL NOT emit `Run now: none`, and SHALL route to `verify-against-rubric` with the slice's exit criteria as the locked rubric and the diff as the artifact; that reviewer is a `judgment` dispatch. The sub-agent receives the diff and the rubric ONLY, never this review's findings, narration, or reasoning, per the ADR-0033 isolation contract. This command reviews with the authoring context in the window, which is what makes it good at the findings it does produce; a zero-finding verdict is the one result that context cannot check about itself, because a same-context reviewer can audit a finding it produced and cannot audit the absence of one it did not. ADR-0033's existing trigger fires only once findings exist, which is the opposite of the case this rule covers. A documentation-only or task-memory-only diff does not trigger it. WHEN no sub-agent can be dispatched in an attended chain on a task branch, write `unverified: zero-finding verdict not independently reviewed` into the slice notes, for the draft PR's "Not verified" list, and continue (ADR-0233). The measured case: one ticket returned CLEAN on three consecutive runs over the same diff with Layer 1 green, and external bots filed two real defects in it minutes later; a second ticket's self-review stated the correct hypothesis, ran the search that answers it, returned CLEAN, and an external bot filed exactly that defect.

- **Probe hygiene (worktree dogfood 2026-08-04).** This command NEVER modifies in place an existing file of the tree under review. No exception, not even with a backup. (1) An empirical probe runs on a NEW file, uniquely named with the reserved prefix `zz-probe-<slug>`, created where the project's runner can resolve it, and removed in the same run. "Never inside the repository" is the wrong rule: the probe that worked had to live in `__tests__`, because the test imports by relative path and depends on the app's jest config, and a copy under `/tmp` resolves neither the import nor the transform. (2) Every path manipulation runs from an absolute root: use an absolute path or a subshell `(cd x && ...)`, never a bare `cd` that leaves a later relative path pointing elsewhere. Cleanup ends by printing `git status --porcelain` in the output; an `|| echo` of success after a failed command is invalid output. On the source run the restore printed `-- test file restored, tree clean --` over a committed file it had just corrupted, because the `cp` ran after a `cd` and the relative path broke. (3) A probe whose runtime fails for a reason unrelated to the hypothesis under test is a BROKEN probe, not evidence either way: record it inconclusive and do not promote the red to a confirmation.

Required output:
1. Overall assessment
2. Must-fix issues
3. Should-fix issues
4. Test gaps
5. Over-engineering gate: flag single-caller abstractions, speculative config or flags nobody asked for, dead code left behind, a construction far larger than the need, and unrequested generality. Ground each flag in "no current caller" or "not in DECISIONS.md" so it stays evidence-based. Advisory and subject to the no-op rule, not a forced finding.
6. Final verdict
7. Exact TASK_STATE.md update block, or explicit `TASK_STATE: NO_CHANGE`
8. Recommended next command
9. Recommended editor mode
10. Why this is the correct next step
11. What should explicitly not be done yet

### Review prompt scaffold (optional)
When the review directives in this command are ambiguous, parse them in three labeled parts: Instructions (what to do), Context (background, not a rule), and Constraints (hard limits that override the rest). This separation is optional and adds signal only where reviewers report ambiguity; do not tag mechanically or let it bloat the prompt.
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
### Deliverable reconcile (closure gate, per ADR-0056)
**Deliverable reconcile (per ADR-0056).** Reconcile the task's `## Requested deliverables` ledger in `TASK_STATE.md` against the delivered work. The gate is lifecycle-aware: it hard-fails only when the run is finalizing the whole task, and reports without failing at a mid-task checkpoint.

1. Locate the ledger. Read `## Requested deliverables` in `TASK_STATE.md`. WHEN the section is absent (a legacy task that predates the ledger), OR its only row is the `- none named` sentinel (a brief that named no concrete deliverable), this gate is a no-op: skip it and proceed.

2. Classify the context. A finalization run is `task-close`, or `review-hard` run as the pre-PR final pass. A checkpoint run is `where-we-at` or `slice-closure` (and any `review-hard` run that is not the pre-PR final). At a checkpoint a row still tagged `in-scope` that is not yet done is normal remaining work, not a defect.

3. Define reconciled vs silent omission. A row is reconciled when it is `done` (in the delivered work) or `de-scoped:<reason>` with that reason recorded in `DECISIONS.md`. A deliverable named in the brief that has NO ledger row at all, or a row that was dropped without a recorded de-scope, is a silent omission. To detect the no-row case you MUST cross-check the ledger against the brief: read the task's `README.md` (which `task-init` seeds from the brief) and the original request when it is in conversation context, and confirm every deliverable named there has a `## Requested deliverables` row. WHEN no brief artifact is available to cross-check, reconcile the rows that exist and state in the output that ledger-vs-brief completeness could not be re-verified (do not claim it was).

4. Apply the gate by context.
   - WHEN finalizing: IF any row is unreconciled (still `in-scope`, or a silent omission per step 3), THEN this command's output is invalid. Name each unreconciled deliverable, state whether it should be delivered or de-scoped, and route to `implementation-plan` (plan the missing work) or `decision-interview` (a de-scope, which only the person's answer records). A provisional decision never de-scopes (ADR-0233): in an attended chain on a task branch the row stays `in-scope` and is listed as `Not delivered, needs you: <deliverable>: <what is undecided>` in `TASK_STATE.md ## Open questions / blockers`, and `task-close` still holds it unreconciled, while `review-hard`'s pre-PR pass only lists it.
   - WHILE at a checkpoint: report each not-yet-done `in-scope` row as remaining work and do NOT invalidate output on that basis. A silent omission (step 3) is NOT normal progress: name the missing deliverable, record it in the `TASK_STATE.md` checkpoint output as a must-address finding (never a bare one-line mention), and route it as the finalization branch does. Neither case invalidates the output at a checkpoint; that happens only when finalizing.

A de-scope is allowed; silence is not. This generalizes the repo-level "reject silent omission of any repo in `## Repositories`" completeness check from repositories to user-named deliverables.
### References status (finalization, X2)
**References reconcile (X2, 2026-07-18).** Reconcile the references a task cited (its `REFERENCES.md` deliverable, an `EXTERNAL_RESEARCH.md`, or the project-level references it grounded in) against what the task actually shipped, enforcing "cite only what you used." Lifecycle-aware: it reports at a mid-task checkpoint and hard-fails only when finalizing the whole task.

1. Gate on presence. This sub-check fires only WHEN the task produced or cited references: a `REFERENCES.md` or `EXTERNAL_RESEARCH.md` in the task folder, or a `Grounded in:` citation in the shipped work. WHEN none is present, it is a no-op: skip and proceed.

2. Classify the context. A finalization run is `task-close` (or `review-hard` as the pre-PR final pass). A checkpoint run is `slice-closure` or `where-we-at`. At a checkpoint a cited reference not yet reflected is normal in-progress work, not a defect.

3. Reconcile cited vs reflected. For each reference the task cited, confirm the shipped work materially reflects it (a real layout, behavior, or decision traceable to that reference), not merely a name-drop. A reference cited with no material trace in the shipped work is a cited-but-unused reference: this is the failure the brief names ("if the final result does not reflect the references you cited, the REFERENCES.md is wrong").

4. Apply the gate by context.
   - WHEN finalizing: IF any cited reference is unused (no material trace) THEN name it and require either removing the citation or pointing to where it is reflected, and route to `implement-slice-complement` (fix the citation) before closing.
   - WHILE at a checkpoint: report each cited-but-unused reference as a must-address finding (name it, route to `implement-slice-complement`), and do NOT invalidate the whole output on that basis.

"Cite only what you used" is the invariant. This is the produce-side gate for the `capture-references` and `external-research` artifacts, the design-and-research analog of the deliverable-reconcile completeness check.
### Definition of done (command output)
- Issues are ranked must/should/optional with concrete references to code/tests.
- No invented problems; if solid, say so clearly.
- `TASK_STATE.md` updates are `APPLIED`.
- A runtime-debug payload in the invocation args was routed to incident-triage (or split per the triage rule) BEFORE any review step; absorbing one into a review is invalid output.
- The explicit "Runtime-debug payload: yes/no" line is present as the first line of output, and if "yes", the response routed to incident-triage instead of continuing the review.
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
Maximize signal. Prioritize correctness, safety, and maintainability over stylistic commentary.
