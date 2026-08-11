# ADR-0128: The no-VCS workspace waiver reaches the slice-level commit-evidence floor

- **Status**: Accepted
- **Date**: 2026-08-06
- **Tags**: closure-enforcement, commit-evidence, slice-closure, implement-approved-slice, bounded-deferral, refines-adr-0100, extends-adr-0084, dogfood-driven, kimi-dogfood

## Context

ADR-0100 narrowed the commit-evidence floor to three routes: a cited commit, a waiver covering only genuinely discardable work, or a bounded deferral recorded as `deferred: pending human commit`. It considered the unattended case explicitly, where git operations are forbidden by ground rules, and answered bounded deferral on purpose: the run ends open, and that is the honest outcome. At `task-close` it left one escape, the user-authorized archive-with-waiver naming the preserved uncommitted work, for the audit-purpose dogfood-folder case.

That escape exists at `task-close` and nowhere else. `slice-closure` and the `implement-approved-slice` inline-close path have the three routes and no fourth.

A case the ADR did not model then hit it. A human is present at the keyboard, working in a scratch workspace, and declares that this workspace will not have version control at all. In the Kimi K3 dogfood the user answered the question verbatim: no git for this flow, it is a local test, no repository is being created for it. The three routes then evaluate as follows. The work is not committable, because there is no repository and the user has declined to create one. The work is not discardable, because it is the deliverable. And `deferred: pending human commit` is false on its face: the human has already said the commit will never happen, which is precisely the permanent skip ADR-0098 rules out for the sibling floors.

The run's behaviour is the evidence that the floor was unenforceable rather than strict. It closed five slices inline, marking each `closed (inline)` outside all three routes, and then reached for the `task-close` archive-with-waiver to legalize the whole set retroactively. A floor that gets contorted rather than obeyed is not doing the work the floor exists for, and every intermediate state it produced was a slice claiming a closure route it did not have.

The distinction that matters is not attended versus unattended. It is whether the workspace has version control at all. ADR-0100's bounded deferral is correct wherever a commit is possible later: a git-backed repo with a forbidden or absent operator has a real future in which the work gets committed. A directory that is not a repository, in which the operator has declined to make one, has no such future, and pretending it does writes a false deferral into the record.

## Decision

Add a fourth route to the commit-evidence floor at both slice-level homes (`implement-approved-slice` inline-close and `slice-closure`), recorded in `wos/closure-floors.md` beside the existing three. It is narrower than the `task-close` escape it mirrors, and all three of its conditions must hold:

1. The workspace genuinely has no version control. `git rev-parse --is-inside-work-tree` fails at the product path, and no other VCS is in use. This is a fact the command checks, not a claim it accepts.
2. The user has declined version control for this workspace explicitly, in their own words, in this session. The decision is recorded verbatim in the slice notes, in the user's own language, next to the fact from condition 1.
3. The preserved work is named. The slice notes state exactly which paths hold the uncommitted deliverable, so a later reader can find it.

Recorded as `no-vcs waiver: <workspace path> (<verbatim user decision>)`. With all three present the slice may close, and the floor is satisfied. With any one absent the floor is unsatisfied and the existing routing is unchanged.

Three things this route deliberately does not do:

- It does not fire on a git-backed repository. A repo whose operator is merely absent, forbidden, or unattended stays on ADR-0100's bounded deferral, unchanged. This is the case ADR-0100 decided and it is not reopened.
- It does not infer the decision. Silence, an unanswered question, a model's reading of the situation, and an inference from "no `.git` present" are each not a user decision. The verbatim record is the attester, which is why condition 2 asks for the user's own words rather than a paraphrase.
- It does not travel to `task-close`. That home already has its own escape with its own ceremony, and the two are recorded separately so neither is read as authorizing the other.

## Consequences

### Positive

- The slice-level floor becomes satisfiable in the one case where it was not, so slices stop closing outside their own routes and the record stops carrying false deferrals.
- The asymmetry ADR-0100 introduced is closed: a decision the user can make at the end of a task, they can now make when it is actually taken.
- The fact check in condition 1 makes the route harder to reach than the `task-close` escape, which rests on user authorization alone.

### Negative

- One more escape on a floor that exists to prevent escapes. Mitigated by the three-condition conjunction, one of which is a verifiable fact about the filesystem rather than an assertion.

### Neutral

- The genuine-throwaway waiver and the bounded deferral are unchanged in wording and ceremony.
- No new command.

## References

- Refines ADR-0100 (bounded deferral at the commit-evidence floor), which refined ADR-0084 (closure commit gate).
- Inherits ADR-0098's bounded-versus-permanent doctrine: this route exists precisely because "pending human commit" is a permanent skip in a workspace that will never have a repository.
- Dogfood evidence: Kimi K3 session `a6f1a135`, 2026-08-06, turn 7 (the user's verbatim decision) and turn 15 (the retroactive `task-close` legalization).
