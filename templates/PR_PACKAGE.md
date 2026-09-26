# PR package (template)

Copy to the task folder as `PR_PACKAGE.md` and fill before or during `@commands/pr-package.md`. Replace placeholders in angle brackets. **Do not** paste paths from the workflow repository or the task repository into the GitHub PR body.

## Git context (required)

- **Base branch (integration target):** `<e.g. origin/main>`
- **Current branch:** `<local branch name>`
- **Diff commands used (audit trail):**
  - `git diff <base>...HEAD`
  - Optional: `git diff --stat <base>...HEAD`
- **Base fetch age:** `<when the base ref was last fetched, e.g. 2 hours ago>`
- **Commits since fork point (both directions):** `<N on this branch, M on the base since the fork>`
- **Merge dry-run:** `<clean, or the list of predicted conflicting files>`

## Delivery scope (from real diff)

- **Summary:** `<what changed vs base, in plain language>`
- **Out of scope (explicit):** `<what this PR does not do>`

## Suggested git metadata

- **Branch name:** `<suggested-branch-slug>`
- **Main commit message (max 2 lines):**
  ```
  <subject line>

  <optional body line>
  ```
- **Additional commits (only if justified):** `<none | list>`

## Suggested git commands (adapt to your remote)

```bash
git fetch <remote>
git checkout <branch>
git status
git add <paths>
git commit -m "<message>"
git push -u <remote> <branch>
```

## PR title (paste-ready)

`<PR title>`

## PR description (paste-ready for GitHub)

### Not delivered, needs you

`<each requested deliverable not delivered, with the one thing the person must decide or supply; or None.>`

### Summary

`<2 to 6 sentences for reviewers>`

### Decisions made without you

`<numbered; high-impact ones (data, security, payments, cost) first, each marked Confirm before merge; each states the choice and its evidence; or None.>`

### Not verified

`<each check the agent could not run on itself, with what a person has to run or look at; or None.>`

### How to test

`<commands or steps; include expected result>`

### Risk / rollout

`<deploy order, migrations, feature flags, rollback>`

### Screenshots / evidence

`<if applicable, or N/A>`

## Reviewer attention

- `<file or topic 1>`
- `<file or topic 2>`

## Internal workflow (do not put in GitHub)

- **Recommended next command:** `<official basename>`
- **Recommended editor mode:** `<Ask | Plan | Agent | Debug>`
- **Decision map (PR number to provisional decision):** `<1: P-N, 2: P-N | none>`
