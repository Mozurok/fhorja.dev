# PR package (template)

Copy to the task folder as `PR_PACKAGE.md` and fill before or during `@commands/pr-package.md`. Replace placeholders in angle brackets. **Do not** paste `my_work_tasks/` paths into the GitHub PR body.

## Git context (required)

- **Base branch (integration target):** `<e.g. origin/main>`
- **Current branch:** `<local branch name>`
- **Diff commands used (audit trail):**
  - `git diff <base>...HEAD`
  - Optional: `git diff --stat <base>...HEAD`

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

### Summary

`<2–6 sentences for reviewers>`

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
