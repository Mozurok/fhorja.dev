# ADR-0185: `pr-package --apply` pushes the branch and opens a draft PR

- **Status**: Accepted; superseded in part by [ADR-0233](./0233-the-attended-chain-runs-to-the-draft-pr.md) on attended runs: the chain runs `--apply` itself after the last commit, reversing Alternative 1. The display, the refusals, draft only and the human merge stand.
- **Date**: 2026-08-31
- **Tags**: pr-package, branch-commit, egress, human-gate, draft-pr, adr-0163, friction

## Context

`branch-commit --apply` writes local git history on one authorization (ADR-0163), reasoning that a
local commit is reversible through `git reset` and the reflog, so it is not an irreversible outward
act. The same rule says push, merge, force-push and MCP egress stay behind their own confirmation.

That left the last step manual. `pr-package` produced everything needed, the branch name, the
commit message, the PR title, the PR body ready to paste, and a list of suggested git commands
including `push`, and then a person retyped them. The maintainer named this on 2026-08-31: the
human should enter at the end to check the work, and then ask for the push and the draft PR rather
than perform them.

Asking is a confirmation. What was missing was a command that treats the ask as one.

## Decision

`pr-package` gains an `--apply` flag, Agent mode only. Without it the command behaves exactly as
before and writes nothing outward.

With it, in one turn and in this order:

1. **Display first, act second.** Print the remote name and its URL literally, the branch to push,
   the base, the PR title and the full PR body. A push to the wrong remote is the failure this
   display exists to catch, so the URL is never summarised.
2. **Refuse and name the refusal** when there is no configured remote, when the branch is the base
   branch, when the diff scope has uncommitted changes, or when the remote is a mirror or
   distribution repository rather than the development one.
3. **Push, then open the PR as a DRAFT.** Never ready-for-review, never merge, never force-push.
4. **The `--apply` invocation is the authorization.** No second prompt. Print the resulting URL.

Merge stays human and gets no flag.

The reason a draft is allowed on one authorization while merge is not: a draft notifies no
reviewer and can be closed, so it is recoverable in the way that matters. A merge is not. This is
the same reversibility test ADR-0163 used for the local commit, applied one step further out and
stopping where reversibility stops.

## Consequences

### Positive

- The chain runs from prompt to draft PR with the human entering once, at the end, to check the
  work and say go. That is the shape the maintainer asked for.
- The refusal list makes the wrong-remote push, which is the expensive mistake here, a named stop
  rather than a discovery.

### Negative

- This is the first command in the workflow that acts outward. A draft PR is visible to anyone with
  repository access, so a mistake is public in a way a local commit is not. Mitigated by the
  display, the four refusals, draft-only, and the flag being explicit rather than a default.
- The mirror-remote refusal depends on recognising a mirror. It is a judgment, unlike the other
  three, which are checkable.

### Neutral

- Bare `pr-package` is unchanged. Every existing run keeps its behavior.
- `branch-commit --apply` is untouched. Local history and outward action stay separate
  authorizations on purpose.

## Alternatives considered

### Alternative 1: push automatically at the end of the Express chain

- Rejected. Express removes stops that buy nothing; this one buys the check that the work is right
  before it leaves the machine. Removing it would be removing the only remaining human read.

### Alternative 2: open the PR ready for review

- Rejected. Ready-for-review notifies people, and being notified cannot be undone by closing the
  PR. Draft keeps the act recoverable.

### Alternative 3: put the flag on `branch-commit`

- Rejected. `branch-commit` writes local history and `pr-package` owns the delivery package and
  already computes the base, the title and the body. Two authorizations for two different acts.

## References

- [ADR-0163](./0163-apply-commits-locally-without-confirm.md): the display-then-act rule and the
  reversibility test this extends.
- `commands/pr-package.md`: the rule.
- `COMMAND_PROMPT_STUBS.md`: the gated-flag table row, per the ADR-0029 discipline.
