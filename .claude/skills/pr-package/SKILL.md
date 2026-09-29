---
name: pr-package
description: |-
  Prepare a clean delivery package for GitHub from the real git diff against an explicit base branch, persisted as PR_PACKAGE.md. Produces the branch name, commit messages, the git commands, PR title and body, and reviewer attention points, and never invents work outside the diff. Per-repo when SOURCE_OF_TRUTH.md has a Repositories section. Use when scope is complete and the diff is real and stable. Do not use during active implementation, when the diff is still changing, when you only need a quick branch and commit name (use branch-commit), when the trigger is review feedback (use pr-feedback-ingest or post-review-pivot), or when the need is only slice closure (use slice-closure). After the draft, use self-critique-and-revise.
metadata:
  category: "delivery-and-communication"
  primary-cursor-mode: "Ask"
  multi-repo-aware: "true"
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
> - `Definition of done (command output)`: PR narrative matches the real diff vs the explicit base branch (no invented work).


Act as a senior engineer preparing a full delivery package for the active engineering task based on the real git diff.

Goal:
Prepare a clean delivery package for GitHub using the actual implementation changes in the current branch compared against an explicit integration base branch, then persist the result in the task repository.

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
- target repo (only for multi-repo tasks where `SOURCE_OF_TRUTH.md` has a `## Repositories` section): the repo identifier this invocation packages. Must match one entry in the `## Repositories` section. Multi-repo tasks invoke `pr-package` once per repo, with one invocation producing one repo's PR. See the spec `## Multi-repo support (v1)` for the schema.
- explicit git base branch to compare against (example: `origin/main`, `origin/staging`, or a named remote branch). WHEN an attended chain on a task branch reached this command from `branch-commit --apply` and no base was given, use the `Base branch:` line in `TASK_STATE.md ## Resume notes` (the branch the task branch was cut from), else the base recorded in `SOURCE_OF_TRUTH.md` (or `TASK_PREFERENCES.md`), else `origin/HEAD`, and cite which one supplied it instead of asking (ADR-0233). For multi-repo tasks, this is the base branch for the `target repo` (which may differ across repos and is recorded per-repo in `## Repositories`).
- current local branch name (as shown by `git branch --show-current`)
- working tree context (as shown by `git status --porcelain` or an explicit statement that the working tree is clean)
- explicit diff commands used (at minimum):
  - `git fetch <remote> <base>` (run first; the diff is taken against the freshly fetched ref, never a stale local one)
  - `git diff <base>...HEAD`
  - optional: `git diff --stat <base>...HEAD`
  - `git status --porcelain` plus `git diff` and `git diff --staged` WHEN the committed diff is empty. Uncommitted work in the working tree is still the change under delivery: package it and say plainly that it is uncommitted, so the branch-and-commit steps come before the push step. An empty `<base>...HEAD` is NOT proof there is nothing to deliver, and reporting a healthy package over an empty diff is the silent-empty-scope failure this line exists to prevent.
- real git diff vs the explicit base branch, or the working-tree diff when the branch carries no commits yet
- latest validation/test evidence if available
- last completed step from TASK_STATE.md (command + summary)

Task repository files to create or update (only if materially changed):
- PR_PACKAGE.md
- TASK_STATE.md

Operating rules:
- When the PR package file does not exist yet in the task folder, seed it from repo-root `templates/PR_PACKAGE.md`, then fill with real `git` output via this command. For single-repo tasks the file is `PR_PACKAGE.md`; for multi-repo tasks (when `SOURCE_OF_TRUTH.md` has a `## Repositories` section) the file is `PR_PACKAGE.<repo>.md` where `<repo>` matches the `target repo` input.
- Multi-repo handling: branch behavior on the presence of `## Repositories` in `SOURCE_OF_TRUTH.md`. When the section exists, require explicit `target repo` input matching one entry; produce `PR_PACKAGE.<repo>.md` (not `PR_PACKAGE.md`); use the base branch declared for that repo in the `## Repositories` entry. Reject invocations missing the `target repo` input or with an identifier that does not match any entry. When the section is absent, run as single-repo (existing behavior, no change). One invocation produces one repo's PR; multi-repo tasks invoke `pr-package` N times for N repos. Cross-repo coordination notes (rollout order, dependencies between PRs) live in `TASK_STATE.md` `Risks to watch` plus per-PR body cross-reference lines (`Related PR: <other-repo-PR-url>`); they are not consolidated into a single shared `PR_PACKAGE.md`.
- **`--apply`: push the branch and open a DRAFT PR (ADR-0185, Agent mode only).** Without the flag this command prepares and writes nothing outward, which is the behavior every prior run had. WITH the flag, and only in Agent mode, do this in one turn and in this order:
  1. Display first, act second. Print the remote name and its URL, the branch that will be pushed, the base branch, the PR title, and the full PR body. A push to the wrong remote is the failure this display exists to catch, so the URL is printed literally and never summarised.
  2. Refuse and stop when any of these hold, naming which one fired: the run is unattended or fleet-dispatched (a background session failing the ADR-0237 test in `wos/cross-cutting-workflow-guardrails.md ### Unattended sessions` counts), or is not in Agent mode; no configured remote for the product repo; the branch is the base branch; the working tree has uncommitted changes in the diff scope; or the remote URL is a mirror or distribution repo rather than the development one. Name which refusal fired. Then check the head branch's audience: IF it already exists on the remote (`git ls-remote --heads <remote> <branch>` prints a line) and it is neither `task/<task-dir>` nor the `Task branch:` this task recorded, THEN it is a branch other people may pull, and pushing to it is an act whose audience is not bounded (stop reason 1): display the branch, the remote URL and the commits the push would add, obtain an explicit confirmation in this same turn, and push only after it.
  3. Check the audience before opening the draft. Read the target repository's files under `.github/workflows/` and list every workflow triggered on `pull_request` whose type set includes `opened`, which is the default type set when `types:` is absent, and every workflow triggered on `push` whose `branches` and `branches-ignore` filters match the head branch (no filter matches every branch), because the push fires those. Cite the files read and both verdicts. The push and the draft clear without confirmation only where none of those workflows reaches anyone outside the repository. A workflow reaches outside when it deploys a preview, posts to an external service, notifies a channel, or requests review. IF such a workflow exists, or the workflow files cannot be read, THEN the push and the draft are an act whose audience is not bounded: display the raw PR body and the exact destination, obtain an explicit confirmation in this same turn, and push and open the draft only after it. Do not assume a draft pull request is quiet in general. Whether a given repository fires on `pull_request: opened` is a per-repository fact, and reading it is this command's duty.
  4. Push the branch, then open the PR as a DRAFT. Never `--ready`, never merge, never force-push. Host account: before opening the draft, confirm the host CLI can see the repository (`gh repo view <owner>/<repo>`). IF the active account cannot, THEN try the other accounts `gh auth status` lists for that host, the remote owner's first, and pass the first one that can see the repository to the PR calls only, in that one command's environment (`GH_TOKEN=$(gh auth token --user <account>) gh pr create ...`). Never switch the active account, and never print or store the token. IF no logged-in account can see the repository, THEN stop after the push, name the missing login, and route the person to `gh auth login`; the pushed branch stays. A task-branch push and a draft PR reach a bounded audience: the host requests no code-owner review on a draft and notifies on ready-for-review, so the audience boundary sits at that transition rather than at this one, and this flag never crosses it. WHERE any command marks a draft ready for review, that transition SHALL display the PR URL, the base branch, and the reviewer set that will be notified, and SHALL obtain an explicit confirmation in that same turn. That is the confirmation opening the draft no longer carries.
  5. The explicit `--apply` invocation IS the authorization for (4). Do not ask a second time. Print the resulting PR URL.
  6. Route without asking (ADR-0233). WHEN the draft opened, the chain ends: the Handoff SHALL be `Run now: none`, `Mode: N/A`, and its `Reason:` SHALL name marking the PR ready for review and merging as the person's acts, with the PR URL. WHEN the refusal at (2) that fired was the branch being the base branch or uncommitted changes in the diff scope, and the run is attended, the Handoff SHALL be `Run now: branch-commit --apply`, `Mode: Agent`, since committing on the task branch is the step that clears it. Every other refusal keeps its stop.
  Merge stays human and has no flag. `branch-commit --apply` writes local history that reaches nobody else, and this one puts a branch and a draft on the shared host, so the two authorizations are separate on purpose.
- **Handoff:** end with the adaptive `### Handoff` block per `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full).
- **Operating mode (ADR-0008, ADR-0162).** WHEN `TASK_STATE.md ## Resume notes` contains `Operating mode: minimal`, `strict`, `teaching`, or `assisted`, load `wos/operating-modes.md` and apply that mode. WHEN the line is absent, use this command's native rules. Auto-suggestion is not a declaration.
- Do not reopen broad analysis.
- Do not focus only on the latest slice.
- Treat the full current task diff against the explicit base branch as the delivery scope.
- Before producing output, verify the diff is stable enough to package; if it is still moving quickly, return a no-op and route to stabilization steps.
- **Base freshness and merge prediction (mobile dogfood 2026-07-29):** run `git fetch <remote> <base>` before taking any diff, and report the base ref's age plus the commit count since the fork point (`git rev-list --count <base>...HEAD` and its inverse). Then run a merge dry-run (`git merge-tree` or a throwaway merge) and list every conflicting file under `Reviewer attention points`; a predicted conflict on a file this branch rewrote is a reviewer decision, not a footnote. A claim that *this branch* changed a value SHALL be grounded in the merge-base diff (`git diff $(git merge-base <base> HEAD) HEAD -- <path>`), never in a comparison against the integration branch head, which reports the other side's movement as yours. Order matters: base-sync happens BEFORE the final review pass, never between review and push, because a post-review base merge breaks the reviewed-tree-equals-pushed-tree guarantee and a host-repo ship gate may then refuse to clear its review badge. When the base has moved and no sync has happened, say so and route to the sync before packaging.
- No-op rule for artifacts:
  - If `PR_PACKAGE.md` would not materially change versus the current diff, do not rewrite it.
  - If `TASK_STATE.md` would not materially change, do not rewrite it.
  - Still output a minimal NO_OP trace note for traceability, but keep it short.
- Summarize the real implementation work across the branch.
- Focus only on real code, tests, configs, migrations, or runtime-relevant changes.
- Keep commit messages concise and human.
- The main commit message must be at most 2 lines.
- Prefer one clean main commit unless the diff clearly justifies more.
- Do not invent work not grounded in the diff.
- Always write the PR body for humans on GitHub: do not reference paths into the workflow repository or the task repository, command filenames, or internal workflow artifacts.
- **Three sections for what the person has not seen (ADR-0233).** The PR body SHALL carry `Not delivered, needs you` first, then the summary, then `Decisions made without you` and `Not verified`, in plain language a reviewer on GitHub can act on, with no workflow ids, task paths or command names in them:
  - `Not delivered, needs you`: every `Not delivered, needs you:` line in `TASK_STATE.md ## Open questions / blockers`, plus every `## Requested deliverables` row still in scope and not delivered, each with the one thing the person must decide or supply. A deliverable the user named SHALL appear here rather than be left out of the PR.
  - `Decisions made without you`: every `### P-N` under `DECISIONS.md ## Provisional decisions` that no `Confirms: P-N` or `Supersedes: P-N` line under `## Locked decisions` names and no later P-N's `Replaces: P-N` line names (ADR-0235: list only the newest entry of a replacement chain), numbered in the PR, each stated as the choice made and the evidence for it (a product-repo file and line, or the request's words). Entries with `Impact: high` (data, security, payments or cost) SHALL come first, each marked `Confirm before merge`.
  - `Not verified`: every check the agent could not honestly run on itself, read from three sources: `Not verified: <check>` lines in `TASK_STATE.md ## Open questions / blockers`, `unverified:` lines in the `SLICES/` notes (closure floors, `review-hard`), and the `unverified: blinded plan review not run` line in the `IMPLEMENTATION_PLAN.md` Approval log. Each item says what a person has to run or look at.
  WHEN a section has nothing to list, it SHALL read `None.` rather than be dropped, so a reviewer can tell an empty list from a missing one. `PR_PACKAGE.md`'s internal section keeps the map from each PR number to its `P-N`, so an answer given on the PR can replace the matching provisional decision. WHEN a project PR template is rendered, the three sections go above the template's own sections.
- **Complete explicit staging (P2-3, careers-page dogfooding 2026-06-23):** the `add` step MUST list every file in the task's delivery scope by explicit path. Never emit `git add -A` / `.` / `*` (a global hook blocks it and it contaminates commits with tooling files). When the file set is large, list them all anyway, grouped by directory; completeness is what removes the temptation to reach for a wildcard. There is no per-task opt-in to `-A`.
- **Consume task preferences (P2-3):** read `TASK_PREFERENCES.md` in the task folder if present (its shape is `templates/TASK_PREFERENCES.md`), and honor its durable delivery preferences (base branch, commit convention, PR-template path). This is the consume side that a captured preference relies on; a preference in `TASK_STATE.md ## Observations` alone is NOT read back, so durable delivery preferences belong in `TASK_PREFERENCES.md`.
- **Project PR template (P2-6, careers-page dogfooding 2026-06-23):** detect the product repo's `.github/PULL_REQUEST_TEMPLATE.md` (resolve the repo path from `SOURCE_OF_TRUTH.md`; or the path named in `TASK_PREFERENCES.md`). When it exists, render item 8 (the PR description) into that template, filling each section from the real diff and leaving unknown checklist items unchecked. When it does not exist, emit the generic PR body unchanged.

PR_PACKAGE.md must include:
1. Explicit base branch, current branch, and the exact diff commands used, ready to paste (for auditability), plus the base ref's fetch age, the commit count since the fork point, and the merge dry-run result (clean, or the list of predicted conflicting files)
2. Delivery scope based on diff vs the explicit base branch
3. Suggested branch name
4. Suggested main commit message
5. Optional additional commit messages, only if justified
6. Suggested git commands:
   - fetch
   - checkout branch confirmation if useful
   - add
   - commit
   - push
7. Suggested PR title
8. PR description in markdown, ready to paste into GitHub (rendered into the product repo's `.github/PULL_REQUEST_TEMPLATE.md` when one exists, per the Project PR template rule; otherwise the generic body), carrying the `Not delivered, needs you`, `Decisions made without you` and `Not verified` sections per the three-sections rule
9. Reviewer attention points
10. Recommended next command
11. Recommended editor mode

Required output:
1. Exact content for PR_PACKAGE.md (full document if create/update; otherwise a short NO_OP note)
2. Exact TASK_STATE.md update block, or explicit `TASK_STATE: NO_CHANGE`
3. Recommended next command
4. Recommended editor mode
5. Why this is the correct next step
6. What should explicitly not be done yet

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
- PR narrative matches the real diff vs the explicit base branch (no invented work).
- The diff is both an upper and a lower bound on the narrative: every path/hunk that materially changes behavior in `git diff <base>...HEAD` appears in the PR description, and every claim in the narrative is grounded in a path or hunk in that diff. Summarizing from `TASK_STATE.md`, `DECISIONS.md`, or `IMPLEMENTATION_PLAN.md` without citing the real diff is invalid output (under-reporting and over-promising are both regressions).
- Includes explicit diff commands, current branch, and working tree notes (clean vs dirty) grounded in real `git` output.
- The base was fetched in this run and the package states its age, the commit count since the fork point, and the merge dry-run result. A package produced from an unfetched base ref, or one that omits the merge prediction, is invalid output.
- All 11 items of `PR_PACKAGE.md must include` are present, or each omission carries an explicit one-line `SKIP: <reason>` note. Silent omission of items such as `Reviewer attention points`, working tree status, or the verbatim diff commands is invalid output.
- The PR body carries `Not delivered, needs you`, `Decisions made without you` and `Not verified`, each listing its entries or reading `None.`; a provisional decision or an unfinished named deliverable that the task memory holds and the PR body omits is invalid output, and so is a high-impact decision not marked `Confirm before merge`.
- An `--apply` run that opened the draft ends with `Run now: none` and names ready for review and merge as the person's; routing onward to an act that opens the audience is invalid output.
- An `--apply` run names the workflow files it read under the target repository's `.github/workflows/` and states the `pull_request: opened` verdict and the `push` verdict for the head branch; a push to a branch already on the remote that is not this task's branch waits for a same-turn confirmation. Opening a draft pull request without that check, or asserting that draft pull requests are quiet without reading the repository's triggers, is invalid output.
- The PR package file (`PR_PACKAGE.md` for single-repo, `PR_PACKAGE.<repo>.md` for multi-repo) is `APPLIED`; never put task-memory paths into GitHub PR text.
- Multi-repo validation: when `SOURCE_OF_TRUTH.md` has a `## Repositories` section, output rejects invocations missing the `target repo` input or with an identifier that does not match any entry; producing `PR_PACKAGE.md` (without repo suffix) in multi-repo mode is invalid output; using a base branch other than the one declared in the matched `## Repositories` entry is invalid output unless the user explicitly overrides with one-line justification. Single-repo tasks (no `## Repositories` section) behave identically to the v1.0 contract.
- Output ends with a complete `### Handoff` block per the adaptive format in `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract`. A response that ends after `PR_PACKAGE.md` content without a complete Handoff is invalid output.
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
Optimize for accuracy against the real diff, reviewer clarity, and full-task delivery quality.
