# Agent directive template

Paste this into the always-loaded instruction file of the repository you work in: `CLAUDE.md` for
Claude Code, `AGENTS.md` for Codex and agents that read it, `.cursor/rules/fhorja.mdc` with
`alwaysApply: true` in its frontmatter for Cursor. One time, per repository.

Installing Fhorja gives an agent the commands. This gives it the instruction to use them. Measured
2026-09-01: with the skills installed and nothing else, an agent handed a one-file task does the
task and never opens one. With the paragraph below in the always-loaded file, the same model on the
same brief ran `task-init`, `implementation-plan` and `implement-approved-slice` and halted at the
commit-evidence floor. See `docs/adr/0189-the-directive-is-the-missing-install-step.md`. That floor
still refuses on its own terms; on an attended git repository with a configured remote, what comes
after it is different now: `branch-commit --apply` and `pr-package --apply` run on without a human
stop, all the way to a pushed task branch and a draft PR (ADR-0233).

---

**Start engineering work by running `task-init`.** Any change to this repository is a task: a
one-line docs edit is a task, a typo fix is a task. Do not edit a file before the task folder
exists. A short pipeline is what small work gets, so its size is a reason to take that pipeline,
never a reason to skip the workflow. Then follow the `Run now:` line of each command's
Handoff without waiting to be asked.

When a task is already active, read its `TASK_STATE.md` first and continue from
`## Recommended next step` rather than starting a new one.

---

## Adjusting it

The wording above is what was measured. Change it if your repository needs different words, and
keep the three things it does:

1. It names the entry command, so there is nothing to infer.
2. It says a small change is still a task, which is the judgment that stops an agent from starting.
   In both runs without this line the agent produced a correct answer and no task, which reads as
   having decided the work was too small to deserve ceremony.
3. It says to follow the `Run now:` line without being asked, which is the ADR-0186 chaining
   contract, extended by ADR-0233 to the draft PR on a repository with a remote, stated where the
   agent will actually read it.

Removing any of the three has not been measured. Removing the second is the one most likely to
undo the effect.
