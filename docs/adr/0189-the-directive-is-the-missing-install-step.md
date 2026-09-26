# ADR-0189: The directive is the missing install step

- **Status**: Accepted
- **Date**: 2026-09-01
- **Tags**: invocation, install, express, adr-0186, adr-0184, always-loaded, friction, measured

## Context

ADR-0184 made Express the default tier and ADR-0186 made the handoff continue the chain. Both
shipped. Neither made the workflow run, and the 2026-08-31 complaint that started the arc, the
workflow stopping to ask, survived them.

Two measurements, four days apart, locate why.

The 2026-08-27 dogfood told three models to follow the workflow. All three chained `task-init` to
`implementation-plan` to `implement-approved-slice` with no human turn between commands, and all
three halted at the same place, before `branch-commit`, on a floor the prompt never named.

On 2026-09-01 the same kind of brief was given with no such instruction, in a clone of this
repository, with all 98 skills on disk and `CLAUDE.md` loaded. The model read the repo accurately,
cited an ADR's own Notes section, ran the lint, edited the file, and reported. It created no task
folder and ran no command. Twice.

Once the chain starts it carries itself. Nothing makes it start.

Stated structurally: the installer writes 98 skills and 89 slash commands into a user's environment
and touches no always-loaded instruction file. Measured 2026-09-01, `sync-workflow-slash-commands.sh`
has zero references to `CLAUDE.md` or `AGENTS.md`. Fhorja installs a vocabulary and never installs
the instruction to speak it.

## Decision

The directive is part of the install, and it ships as `templates/AGENT_DIRECTIVE.template.md`: one
paragraph the user pastes, once per repository, into that repository's always-loaded instruction
file.

The installer does NOT write it. Writing into a user's instruction file is exactly the class of act
ADR-0046 gates, and a tool that edits the file governing an agent's behavior without being asked is
the thing this repository refuses in every other place. The README names the paste as the third
install step, and the template says where it goes.

This is a one-time setup step, not a per-task one. It costs the user a paste once and removes a
decision from every task after it, which is the trade the whole arc is about.

## The measurement

A paired A/B on 2026-09-01. Same brief, same tree, same model, one variable.

The brief was the 2026-08-27 dogfood's, chosen for its three-model baseline and because the sentence
it asks for is verifiably absent from `docs/FAQ.md` (0 occurrences of "override Express", measured
before running).

**Without the paragraph:** no task folder. A correct edit, verified with the lint, with an accurate
citation, and no workflow.

**With it:** `task-init` wrote the five files with substrate headers and bound Express;
`implementation-plan` wrote the plan; `implement-approved-slice` wrote a slice note plus an evidence
file and made the edit; the run halted before `branch-commit` stating "the commit-evidence floor
needs a commit". The same stopping point the dogfood reached under a hand-written instruction.

## Consequences

### Positive

- The arc's two contract decisions become reachable. ADR-0186's chaining rule is load-bearing only
  once something enters the chain, and now something does.
- The install step that was missing is named, so a user who follows the README gets a workflow that
  starts rather than a catalog that waits.

### Negative

- One model, one brief, one repository. The effect is measured, not established: nothing here says a
  five-file change or a different provider behaves the same way. The template says so.
- The directive lives in a file this repository does not own once Fhorja is installed elsewhere. A
  user who edits it, or whose tool reads a different file, silently loses the effect and nothing
  detects that.
- It is prose steering behavior, which is weaker than a mechanism. It is what was measured to work;
  a stronger mechanism is not ruled out and is not built here.

### Neutral

- No command changed. No generated skill changed. The `Run now:` grammar, the tiers and the floors
  are untouched.
- This repository's own `CLAUDE.md` carries the paragraph, so the dogfood matches the instruction.

## Alternatives considered

### Alternative 1: the installer appends the paragraph to the user's instruction file

- Rejected. It writes into the file that governs the agent's behavior in the user's own repository,
  without being asked, which is the act ADR-0046 exists to gate. Offering it interactively is a
  coherent future option; doing it silently is not.

### Alternative 2: rewrite `task-init`'s skill description so it fires on any task

- Not rejected, unmeasured. Today the description explains what the command CREATES ("Initialize the
  official task folder ... Creates README.md, TASK_STATE.md ..."), and its trigger clause, "Use when
  starting a new task from zero", is written in the vocabulary of someone already inside the
  workflow. Rewriting the trigger is cheaper and less invasive than a paste, and
  `evals/scripts/routing-probe.py` already exists to measure descriptions. It was not tested here
  and stays the first thing to try next.

### Alternative 3: an MCP prompt surface as the entry point

- Rejected on prior measurement, not re-tested: the 2026-07-10 connector work found MCP prompts are
  not model-invocable, which is the whole requirement here.

### Alternative 4: a CLI entry point

- Rejected for this decision. It moves the human action from typing a brief to typing a command plus
  a brief, which is not less friction, and it does nothing when the user simply talks to the agent.

## References

- [ADR-0184](./0184-express-is-the-default-tier.md): Express as the default tier.
- [ADR-0186](./0186-the-handoff-continues-the-chain.md): the chaining contract this makes reachable.
- [ADR-0046](./0046-no-auto-install-skill-trust.md): why the installer does not write the paragraph.
- `projects/bmazurok__my-work-tasks/active/2026-08-31_express-as-behavior/TRANSPORT_PROOF.md`: the
  A/B, its limits, and the two eval-harness defects the runs found.
