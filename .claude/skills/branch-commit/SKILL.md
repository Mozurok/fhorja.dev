---
name: branch-commit
description: |-
  Return a branch name and a concise commit message (at most 3 lines: a subject and an optional 2-line body) for the current task, grounded in the real `git diff` rather than a paraphrase of the task summary, and with `--apply` optionally create that commit after showing the staged diff in the same turn. Use when the user only needs quick branch and commit naming right before committing, full PR packaging is unnecessary, and there is a real inspectable diff (staged or unstaged changes, or a branch diff vs an integration base); use `--apply` when the commit-evidence closure floor needs a commit to exist. Do not use when the task needs a complete PR package (use pr-package), there is no diff yet (naming a branch from a task summary alone is the failure mode this command exists to avoid; ask the user to stage at least one change first), or the diff is still too unclear to summarize safely.
metadata:
  category: "delivery-and-communication"
  primary-cursor-mode: "Ask"
  multi-repo-aware: "false"
  context-layers-consumed: "memory"
  context-layers-produced: "memory"
  tools: "Read, Write, Edit, Bash, Glob, Grep"
  x-wos-profiles: "minimal, core, full"
  provenance: "first-party"
  suggested-model: "claude-haiku-4-5"
---
> **Output contract, in brief.** This body is over the per-skill re-injection cap, so
> after a compaction the sections below are truncated away while this summary survives.
> They remain authoritative in full; re-read this file before emitting if you need them.
>
> - `Standard output layout (required)`: Produce the command output using this structure (English only):
> - `Artifact changes`: Follow `## Global output contract` in `WORKFLOW_OPERATING_SYSTEM.md` for `APPLIED` / `PROPOSED` / `SKIP` rules. Every listed file...
> - `Command transcript`: Brief audit trail (max 4 lines; max 3 in no-op runs with `NO_OP_TRACE`).
> - `Handoff`: Use the adaptive ending format from `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full per...
> - `Definition of done (command output)`: Output names the exact diff source used (`git diff`, `git diff --staged`, or `git diff <base>...HEAD`); paraphrasing from the task...


Act as a concise engineering delivery assistant.

Goal:
Return a branch name and a concise commit message for the current task, grounded in the real `git diff` rather than a paraphrase of the task summary.

Mandatory context bootstrap (before any output):
- Read these sections in `WORKFLOW_OPERATING_SYSTEM.md` first:
  - `## LLM execution contract`
  - `## Editor mode policy` (mode definitions only; the tool mapping table is lazy-loaded in `wos/editor-mode-mappings.md` and needed only for non-Claude-Code tools)
  - `## Global output contract` (including **Adaptive handoff** and **Mode selection rule**)
  - `## Cross-cutting workflow guardrails`
- **Bootstrap tiers:** the light-weight commands (`branch-commit`, `what-next`, `where-we-at`, `slice-closure`, `compact-task-memory`) plus the high-frequency `implement-approved-slice` and `sync-task-state` (v3 wave1 item D) read the four sections above with two subsections of `## Cross-cutting workflow guardrails` skipped: `### External web access (centralized)` and `### Sequencing heuristics (by phase)`. Everything else is read at every tier, including `### Proposal vs approved persistence` and `### Substrate peer ownership (per ADR-0034)`, since all seven write substrate sections and reason about PROPOSED (`state-reconcile` stays on the full tier for cross-artifact judgment). The full tier is measured at 11678 tokens, the four always-read sections combined; the two skipped subsections are 1,035 of those (measured 2026-09-24), so the reduced tier is about 10,643. The leaf-reviewer tier (`verify-against-rubric`, ADR-0226) reads only `## Global output contract`, measured at 4841 tokens, plus its rubric.
- **Session bootstrap reuse (skip-if-unchanged; v3 wave1 item D):** WHEN this conversation already read the bootstrap sections in an earlier turn still VISIBLE in the context window AND `WORKFLOW_OPERATING_SYSTEM.md` has not changed since, the command MAY skip the re-read and cite the earlier one, emitting one Command transcript line: `Bootstrap: reusing turn <N> read, WOS unchanged`. Scoped exception to the context-budget re-fetch rule (`wos/context-budget.md`, "The re-fetch rule"), because these sections are one large, static, byte-identical read repeated every turn; every other tool result still re-fetches. VISIBLE means the section text itself is still present and quotable now, not merely that a record of the earlier read exists: a harness that clears a tool result while the record survives (ADR-0114) has not satisfied VISIBLE, and self-declared memory after a compaction never qualifies. A stateless-per-turn harness is excluded. The transcript line is mandatory; a silent skip is invalid output.
- **Resolving `WORKFLOW_OPERATING_SYSTEM.md` and a relative `wos/<topic>.md`.** Both resolve the same way: try the canonical workflow repository root FIRST, then the installed docs directory (`~/.claude/workflow-docs/` or `~/.cursor/workflow-docs/`, the spec at that root and topics under its `wos/`). Repository first, because the installed copy is a snapshot no sync prunes; preferring it would hide a `wos/` edit from every command until a reinstall. Name the resolved root in `### Command transcript`, and say so explicitly when NEITHER resolved rather than continuing silently, since several of these loads are MANDATORY.
- Read additional sections only when relevant to this command's role.
- Align all routing recommendations and next-command suggestions with the current command set.
- **Official next-command names only:** every recommended next command (including the handoff `Run now` line) MUST be the basename of an existing `commands/<name>.md` file in this workflow repository. Never invent names. One exception: `Run now: none` with `Mode: N/A` declares the chain ended with no honest next step, defined under `### Official command names (routing integrity)` (ADR-0126); use it only then, never to end a chain that has a real next step.

Required inputs:
- current task summary (for orientation only, never the primary source for the commit message)
- explicit diff source, exactly one of:
  - `git diff` (unstaged), `git diff --staged` (staged), or `git diff <base>...HEAD` (branch ahead of base; derive it against a freshly fetched base, see `pr-package` for the base-freshness rule)
- the actual diff output (paths and hunks, not the stat summary alone) so the commit message can name the real change
- current branch name (from `git branch --show-current`) so the branch suggestion only proposes a rename when the existing name is generic
- `git status --porcelain` when running `--apply`. None of the three diff forms above lists an UNTRACKED file, so a slice that created new files would otherwise be committed without them, which is the exact uncommitted-work failure the commit-evidence floor exists to catch.
- last completed step from TASK_STATE.md (command + summary), if available

Operating rules:
- Return in English.
- **Handoff:** end with the adaptive `### Handoff` block per `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full).
- **Operating mode (ADR-0008, ADR-0162).** WHEN `TASK_STATE.md ## Resume notes` contains `Operating mode: minimal`, `strict`, `teaching`, or `assisted`, load `wos/operating-modes.md` and apply that mode. WHEN the line is absent, use this command's native rules. Auto-suggestion is not a declaration.
- Summarize from the **real diff**, not from the task summary. The commit subject must name a path or behavior visible in the diff; generic phrasings like "update task" or "improve flow" are invalid output unless that is literally what the diff shows.
- Return one suggested branch name (or explicitly say "keep current branch: `<name>`" when the existing name already reflects the diff scope).
- Return one commit message with a subject line ≤ 72 characters and an optional body of at most 2 short lines, for a total of max 3 lines. Prefer Conventional Commits style (`feat:`, `fix:`, `docs:`, `chore:`, etc.) when it fits the diff.
- If the diff spans multiple unrelated concerns, do not paper over it: flag the split and recommend either staging the commits separately or running `pr-package` for a structured delivery.
- If naming would not materially improve clarity versus the last recorded branch/commit guidance, return a no-op and route forward instead of inventing new names.
- **Auto-deliver on full completion:** when the diff covers all remaining slices in IMPLEMENTATION_PLAN.md (i.e., the task is fully implemented), update TASK_STATE.md phase to "delivered" as part of this command's output. This eliminates the need for a separate `sync-task-state` call after commit just to mark the task as delivered.
- **`--apply` mode (creates the commit; OFF by default).** Without the flag this command only names things and changes nothing, exactly as before. WITH `--apply` it creates the commit it just proposed, under all of the following, every one of which is a refusal condition on its own:
  Every condition is stated against WHAT ENDS UP IN THE COMMIT, never against what the command intended to stage. Staging intent is not a guarantee: the index may already hold something, and a path may carry both reviewed and unreviewed content.
  1. **Agent mode only.** IF the run is in Ask, Plan, or Debug mode THEN the command SHALL refuse and SHALL NOT create a commit. `primary-cursor-mode: Ask` above still describes the default naming-only use; `--apply` is the secondary mode and it requires Agent.
  2. **Never unattended.** IF the run is unattended, background, or fleet-dispatched THEN `--apply` SHALL refuse regardless of any recorded approval. An external execution layer may use its `ref-attested` or driver-owned-branch route. Direct-use `autonomous-run` owns neither route and records `deferred: pending human commit (<one-line context>)` (ADR-0100, ADR-0197). A local commit is still a git object on a branch a human did not pick.
  3. **Show the content, not a file list.** After staging and BEFORE any call that moves HEAD, the command SHALL print: the exact commit message; `git status --porcelain` (so a file that is new rather than modified is visible, which a diff alone never shows); and `git diff --staged --stat` plus `git diff --staged`. A NAME LIST IS NOT SUFFICIENT: a path can carry staged hunks the user reviewed and working-tree edits they did not, so identity of files says nothing about content of the commit. A working-tree-only display (empty index, unstaged `git diff`) is invalid output. Incomplete display is a refuse: HEAD unchanged, no commit.
  4. **Create the commit in this turn after the display (ADR-0163).** A local commit reaches nobody outside this checkout, so its audience is bounded and the confirmation rule for an unbounded audience does not apply. Reversibility is not the reason. An unrecoverable local commit would still reach nobody, and a published page that can be deleted has already been read. Do not wait for a second human confirmation. Merging, force-pushing, marking a pull request ready for review, and MCP egress each open the audience and keep their own confirmation rules. The branch push and the draft pull request belong to `pr-package --apply`, which carries its own display and refusal conditions. After a complete display at (3), create the commit. The `--apply` invocation on an attended Agent run is enough.
  5. **Commit exactly what was shown.** What to stage (ADR-0219): WHEN the index already holds staged changes on entry, that set is the selection, so add nothing to it and name in the display every unstaged edit and untracked path left out; WHEN the index is empty, stage the paths the task's work changed. Staging SHALL name each path explicitly, including a path that is currently untracked; `git add -A`, `git add .`, and globs are forbidden. The commit SHALL be created with a bare `git commit` carrying message flags only. `git commit -a`, `git commit -am`, and a pathspec (`git commit -- <path>...`) are all forbidden, because each one rebuilds the named paths from the WORKING TREE and commits content the display never showed. A pathspec is not a narrower commit: an edit made to a listed path after the display lands inside the commit while `git diff --staged` showed the earlier content. Only a bare `git commit` writes the index that was displayed. IF `git diff --staged --name-only` does not match the displayed set exactly THEN the command SHALL refuse rather than commit a superset.
  6. **Prove the content, not the names.** Immediately after the display at (3) the command SHALL record `git write-tree` as `T_shown` and `git rev-parse HEAD` as `HEAD_before`. Immediately before creating the commit it SHALL re-run `git write-tree`; IF the value differs from `T_shown` THEN the index moved after the display and the command SHALL refuse, HEAD unchanged. After committing it SHALL assert that `git rev-parse HEAD^{tree}` equals `T_shown`, and SHALL cite `T_shown`, `HEAD_before`, the post-commit `git rev-parse HEAD`, and `git show --stat --name-only HEAD`. A file-name comparison SHALL NOT stand in for this proof: two trees can carry identical paths and different content, which is exactly what a pathspec commit produces.
  7. **Commit on the task branch, or refuse on the default branch.** Before staging, the command SHALL read `git branch --show-current` and cite the value it read. IF the current branch is the repository default branch (`origin/HEAD` when it resolves, otherwise `main` or `master`) AND the invocation did not name that branch (neither the user request that carried `--apply` nor the `Task branch:` line in `TASK_STATE.md ## Resume notes` contains it) THEN the command SHALL NOT commit there. WHEN that `Task branch:` line names a different branch that exists locally, the command SHALL run `git switch <that branch>` before staging, which carries the working-tree edits along, cite the branch it left and the one it reached, and continue without asking (ADR-0233): task-init already named the branch. WHEN the task has no `Task branch:` line, the run is attended with a configured remote, and no `Operating mode: assisted` is declared, the command SHALL create the branch the way `task-init` does (`git switch -c task/<task-dir>`, with the same `-2` suffix on a taken name), write the `Task branch:` and `Base branch:` lines into `TASK_STATE.md ## Resume notes`, and continue. IF the switch fails, or neither case applies THEN the command SHALL refuse and SHALL NOT create a commit; it SHALL print the branch name it read and route to `task-workspace` for an isolated worktree and task branch, or ask the user to name the branch explicitly. A detached HEAD counts as unnamed and refuses the same way. None of conditions 1 to 6 looks at the current branch, so a run that satisfies all six can still land a commit on the one branch where a later `git reset` competes with whatever someone else already pulled. Committing to the default branch is a choice the invocation has to make out loud.
  Reach for a stronger capability tier than the `suggested-model` hint above when running `--apply`: the hint is calibrated for naming, and this mode writes to git history.
- **After the commit, the chain goes to the draft PR (ADR-0233).** WHEN `--apply` created the commit, the diff completes the last slice (the auto-deliver condition above), the run is attended, no `Operating mode: assisted` is declared, and the product repository has a configured remote, the Handoff SHALL be `Run now: pr-package --apply`, `Mode: Agent`, without asking which way to go. The push and the draft belong to that command and its own refusals and audience check. WHERE no remote is configured, or `Operating mode: assisted` is declared, the chain SHALL end at the local commit as before, and the Handoff SHALL name `pr-package --apply` as the person's to run or ask for. WHEN slices remain, the Handoff routes to the next slice as before.

Required output:
1. Diff source actually used (one of `git diff`, `git diff --staged`, `git diff <base>...HEAD`), verbatim, for auditability
2. One-line summary of what the diff changes (paths + behavior)
3. Suggested branch name (or `keep current branch: <name>` with reason)
4. Suggested commit message (subject ≤ 72 chars, optional ≤ 2-line body, total ≤ 3 lines)
5. Multi-concern flag if the diff covers unrelated scopes, with recommended split
6. `--apply` runs only: `T_shown` (the `git write-tree` recorded after the display), the pre-commit and post-commit `git rev-parse HEAD` values, the post-commit `git rev-parse HEAD^{tree}`, the explicit list of staged paths, the branch the run read from `git branch --show-current`, and, when that branch is the default, the phrase in the invocation that named it; when condition 7 switched to or created the task branch, the branch it left and the branch it committed on. A run that created a commit without showing the display at (3) is invalid output.

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
Use the adaptive ending format from `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full per session state). Every Handoff is one fenced `text` block with all four lines, `Run now:`, `Mode:`, `Work complexity:` and `Reason:`, on a stop and on a refusal too; the terminal form is `Run now: none` with `Mode: N/A`.

### Definition of done (command output)
- Output names the exact diff source used (`git diff`, `git diff --staged`, or `git diff <base>...HEAD`); paraphrasing from the task summary without citing a diff is invalid output.
- Commit subject line names a path or behavior visible in the diff; generic phrasings like "update task" or "improve flow" are invalid unless the diff really is just that.
- Branch name is specific, stable, and matches repo conventions; reuse of an already-correct branch is preferred over a fresh rename.
- Commit message is ≤ 3 lines total (subject + optional 2-line body); body is omitted when the subject is sufficient.
- Multi-concern diffs are flagged explicitly with a recommended split (smaller commits or `pr-package`); silently merging unrelated concerns into one commit is invalid output.
- `### Artifact changes` is `None` in a naming-only run that did not auto-deliver; a run that set the `TASK_STATE.md` phase to `delivered` per the auto-deliver rule names `TASK_STATE.md` there. In an `--apply` run it names the commit that was created (the pre-commit and post-commit `git rev-parse HEAD` values, `T_shown`, the post-commit `git rev-parse HEAD^{tree}`, and the branch the run read); a mode that writes to git history cannot also assert it changed nothing.
- An attended `--apply` run that committed the last slice with a configured remote and no declared assisted mode hands off `Run now: pr-package --apply`; ending that run with a question about what comes next is invalid output.
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
Optimize for clarity and brevity.
