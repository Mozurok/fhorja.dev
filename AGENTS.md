# AGENTS.md

Rules for any coding agent working inside this repository. Tool-agnostic on purpose: Claude Code, Codex, Cursor, and anything else read this same file.

**Start engineering work by running `task-init`.** Any change to this repository is a task: a
one-line docs edit is a task, a typo fix is a task. Do not edit a file before the task folder
exists. A short pipeline is what small work gets, so its size is a reason to take that pipeline,
never a reason to skip the workflow. Then follow the `Run now:` line of each command's
Handoff without waiting to be asked.

When a task is already active, read its `TASK_STATE.md` first and continue from
`## Recommended next step` rather than starting a new one.

## 1. What this repository is

Fhorja is a workflow operating system for AI-assisted engineering work: markdown, bash, and a small amount of Python. It runs no application code and stores no user data.

- `WORKFLOW_OPERATING_SYSTEM.md` is the normative specification.
- `commands/*.md` is the canonical source of truth for which commands exist (<!-- count:commands -->98<!-- /count --> of them).
- `.claude/skills/<name>/SKILL.md` is generated from `commands/<name>.md`. Never edit it by hand.
- `wos/<topic>.md` is lazy-loaded reference material. Load a topic only when the inline spec section is not enough.
- `docs/adr/` holds the decisions. Read the relevant ADR before changing the contract it documents.

## 2. Which tree am I in

Run `git remote get-url origin` before you write anything, and read the answer:

- The maintainer's private staging tree, on a separate private remote that only the maintainer can open. The maintainer's own work lands there first, and the local maintainer memory in that tree says which tree it is.
- `Mozurok/fhorja.dev`: the public MIT distribution. It receives releases.
- Any other remote: a fork or an installed copy. In an installed copy, do not edit the workflow files. In a fork you mean to contribute from, follow `CONTRIBUTING.md` and open a pull request against `Mozurok/fhorja.dev`.

Between releases the staging tree is normally ahead of the public one. That distance is the release process, not drift. Do not rewrite text in one tree because the other still carries an older wording, and do not move a change into the public tree outside the release path.

A release overwrites the public tree (ADR-0188), so a pull request merged there is ported into the staging tree before the next release. The staging commit that ports it carries the line `Ported-from-public: <sha>`, and every release commit in the public tree carries `Mirror-sync: <staging sha>`. `./scripts/release-preflight.sh` refuses a public commit that has neither.

## 3. Installing the catalog

- `./scripts/bootstrap-user-setup.sh` prepares a machine for the first time.
- `./scripts/sync-workflow-slash-commands.sh` installs or refreshes the commands and skills for Claude Code, Cursor, and Codex. `--dry-run` prints what it would write and changes nothing.
- Profiles: `--profile=minimal` installs the <!-- count:commands-minimal -->24<!-- /count --> spine commands,
  `--profile=core` installs <!-- count:commands-core -->52<!-- /count -->,
  and `--profile=full` installs every command. Omitting `--profile` installs the minimal command set
  and mirrors every skill; skills sync by default, and `--no-skills` skips them.

## 4. The spine

The default path is `task-init`, `implementation-plan`, `approve-plan`, `implement-approved-slice`, `branch-commit` (ADR-0184, ADR-0208), which on an attended run with a configured remote continues into `pr-package --apply` and a draft PR (ADR-0233); a declared `Operating mode: assisted` restores the older stop at the local commit. When the approved plan shows a wave of two or more independent slices and the harness gives each sub-agent its own worktree, `implement-fleet` runs that wave in place of `implement-approved-slice` (ADR-0243). A command joins it only when `task-init` names the disqualifier that adds it: `impact-analysis` for a scope that needs more than one sentence or touches five or more files, `decision-interview` for a decision the request does not contain or a change that spans packages or adds an external service, and `invariants-and-non-goals`, `test-strategy` and `review-hard` for an auth, payments, compliance, PII, or multi-tenant surface. One route is shorter: when no disqualifier fires in an attended run, the change fits one sentence and touches at most two named files, and every decision the request lacks is a normal-impact provisional decision the draft PR lists, `task-init` writes the approved slice itself and `implement-approved-slice` runs `scripts/check-doc-sync.sh --against HEAD` in place of the plan review (ADR-0225, ADR-0239).

The minimal profile carries that path plus the commands a task reaches for most often around it: `slice-closure`, `implement-slice-complement`, `sync-task-state`, `where-we-at`, `what-next`, `capture-observation`, `capture-references`, `incident-triage`, `pr-package` and `task-close`, with `impact-analysis`, `decision-interview`, `test-strategy` and `review-hard` for the escalations. It also carries `implement-fleet`, the default for a parallel wave (ADR-0243), and `verify-against-rubric`, the reviewer `approve-plan` and `review-hard` dispatch, and the three commands that reviewer routes to: `direction-adjust`, `resolve-contract-gaps` and `contract-signoff` (ADR-0229). The frontmatter `x-wos-profiles` field of each command is the source for that list.

## 5. Build rules

- Edit `commands/<name>.md`. Never edit `.claude/skills/` by hand.
- After editing a command file: `./scripts/build-agent-skills.sh`.
- After editing `commands/_shared/<name>.md`: `./scripts/sync-shared-blocks.sh`.
- After editing `wos/closure-floors.md`: `python3 scripts/build-closure-floor-views.py`.
- After adding an artifact that a count marker counts: `./scripts/reconcile-counts.sh --all`.
- A new command is registered in every command registry the lint checks, or the lint reports a gap.
- A new ADR gets a row in `docs/adr/README.md`. A new eval scenario gets a row in `evals/README.md`.
- An accepted ADR's Decision text is immutable. Its Status line is maintained metadata and is
  updated when something supersedes it (ADR-0166). See section 6.
- Removing or renaming a command, or changing the shape of the `### Handoff` block, is an interface
  change: an external read-only consumer reads `commands/*.md` and `docs/command-catalog.json`.
  Record that the paired check against it was run and what it returned, or that the owner
  authorized the change with the consumer left untouched. No tracked file names that consumer.
- `./scripts/lint-commands.sh` must exit 0 before you commit, and `python3 evals/scripts/structural-evals.py` must exit 0 with no `[FAIL]` line. The lint does not run the structural checks; run both.
- Before any push to the public tree, run `./scripts/release-preflight.sh <public-tree-dir>` and read every line it prints.

## 6. Changing a rule

A rule lives in an editable surface: `WORKFLOW_OPERATING_SYSTEM.md`, `wos/`, `commands/`, or this
file. An ADR records WHY a decision was made. The two are not the same artifact, and the ADR is not
where a rule is kept.

- To change a rule, edit the surface that holds it. Do not write an ADR whose purpose is to route
  around an older ADR's text.
- Write an ADR when the decision shapes a contract consumers rely on, has non-obvious tradeoffs, had
  a real alternative rejected for stated reasons, or would be expensive to undo. Otherwise the
  CHANGELOG entry and the commit message are the record.
- When a new decision supersedes an older one, mark the older ADR's Status line and declare the
  supersession in the new ADR's first 15 lines (ADR-0166). Never edit the old Decision text, and
  never delete the file.
- An ADR that no live surface cites and that states no rule is finished. It is the historical record
  working as intended; it needs no maintenance.
- Numbering is the next free 4-digit number, zero-padded, from `docs/adr/template.md`. Status is
  one of Accepted, Proposed, Deprecated, or a supersession note.
- When an ADR changes what a command does or where it routes, search `evals/scenarios/` for the
  command's name, not the ADR's number, and revise every scenario that tests the old behavior in
  the same change. A scenario that never cited the ADR is exactly the one a search by number
  misses: ADR-0208 changed `approve-plan` and scenario 61 kept testing the removed mechanism until
  a run failed on it (2026-09-22).

`scripts/flow-audit.py` is read-only: it writes nothing but its report, to stdout or an explicit
`--out` path, and emits command names only, never task content or project identities. Its lint line
is advisory and never changes the exit status.

## 7. Writing rules

- No em-dash and no en-dash anywhere. The lint fails on those bytes.
- English for normative content. English or Portuguese for documentation prose, consistent within a file.
- Write like a person wrote it: no decorative bold, no emoji, no Title Case headers, no slash disjunctions in prose.
- Never commit a client name, a ticket id, or an absolute path under `/Users/`.
- Never add a tool or session attribution to a commit message, a PR body, or any file: no co-author trailer, no session link, no "generated with" line.

## 8. Where to look next

`wos/repository-structure.md` maps every directory and names the generator behind each generated file.
