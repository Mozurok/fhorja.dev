# Eval scenario 67: pr-package product-repo PR-template detection

- **Tags**: P2-6, pr-package, pr-template, product-repo, delivery, careers-page-dogfooding
- **Last reviewed**: 2026-06-23
- **Status**: active

## Goal

Validates **product-repo PR-template detection** in `commands/pr-package.md` (careers-page dogfooding
P2-6). When the product repo has a `.github/PULL_REQUEST_TEMPLATE.md`, `pr-package` must render the
PR description (item 8) into that template, filling each section from the real diff and leaving
unknown checklist items unchecked. When no template exists, it emits the generic body unchanged.
This closes the careers-page miss where the user had to hand-paste the house PR template because
pr-package produced a generic body.

This exercises:

- Template detection at the product-repo path from `SOURCE_OF_TRUTH.md` (or `TASK_PREFERENCES.md`).
- Rendering the diff-grounded body into the template (not replacing the diff grounding).
- Graceful fallback to the generic body when no template exists.
- The complete-explicit-staging rule (P2-3): the `add` step lists every task file by path, never `-A`.

## Setup

A single-repo task ready for delivery with a real, stable diff vs `origin/main`.

## Input prompt (turn 1: product repo HAS a PR template)

```text
Run @commands/pr-package.md

Task folder: projects/acme__site/active/2026-06-23_pricing-page/
Base branch: origin/main. Branch: feat/pricing-page. Diff is stable (6 files).
The product repo has .github/PULL_REQUEST_TEMPLATE.md with sections: ## Summary, ### Changes Made,
### Pre-Merge Checklist (checkboxes), ### Testing Completed (checkboxes).
Mode: Agent
```

## Input prompt (turn 2: no PR template)

```text
Same task, but the product repo has no .github/PULL_REQUEST_TEMPLATE.md.
Run @commands/pr-package.md. Mode: Agent
```

## Expected response shape (turn 1: template present)

- Item 8 (PR description) is rendered into the house template: ## Summary and ### Changes Made are
  filled from the real diff; checklist items are left unchecked for the human.
- Item 6 (git commands) stages every one of the 6 files by explicit path; no `git add -A` / `.` / `*`.

## Expected response shape (turn 2: no template)

- Item 8 emits the generic PR body unchanged (no fabricated template sections).
- Staging is still complete explicit paths.

## What a FAIL looks like

- Turn 1 emits the generic body and ignores the house template (the careers-page miss).
- Turn 1 invents checklist results instead of leaving them unchecked, or emits `git add -A`.
- Turn 2 fabricates a template that does not exist in the repo.
