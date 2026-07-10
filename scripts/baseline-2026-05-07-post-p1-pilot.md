# WOS token baseline — P0 measurement

Method: chars / 4.0 (approximation; ~10% precision vs Claude tokenizer).
Anthropic prompt cache: write 1.25×, read 0.1×, min cacheable Opus 4.7 = 4.096 tokens.

## Root-level documents

| File | Chars | Words | ~Tokens |
|---|---:|---:|---:|
| `WORKFLOW_OPERATING_SYSTEM.md` | 65.335 | 8.804 | 16.334 |
| `CLAUDE.md` | 3.249 | 472 | 812 |
| `README.md` | 21.230 | 2.529 | 5.308 |
| `WORKFLOW_DEMO.md` | 14.721 | 1.783 | 3.680 |
| `COMMAND_PROMPT_STUBS.md` | 7.447 | 879 | 1.862 |
| `ROADMAP.md` | 6.353 | 892 | 1.588 |
| `CONTRIBUTING.md` | 6.855 | 950 | 1.714 |
| `CHANGELOG.md` | 5.707 | 703 | 1.427 |

## Commands (33 files) — sorted by token count

| File | Chars | Words | ~Tokens |
|---|---:|---:|---:|
| `db-context-supabase.md` | 13.850 | 1.929 | 3.462 |
| `incident-triage.md` | 13.242 | 1.931 | 3.310 |
| `task-init.md` | 12.798 | 1.870 | 3.200 |
| `project-bootstrap.md` | 12.366 | 1.787 | 3.092 |
| `code-locate.md` | 11.376 | 1.692 | 2.844 |
| `pr-package.md` | 10.387 | 1.550 | 2.597 |
| `direction-adjust.md` | 9.403 | 1.360 | 2.351 |
| `implementation-plan.md` | 9.358 | 1.340 | 2.340 |
| `capture-references.md` | 9.116 | 1.328 | 2.279 |
| `impact-analysis.md` | 8.904 | 1.288 | 2.226 |
| `test-strategy.md` | 8.196 | 1.190 | 2.049 |
| `post-review-pivot.md` | 8.043 | 1.137 | 2.011 |
| `resolve-contract-gaps.md` | 7.947 | 1.142 | 1.987 |
| `implement-approved-slice.md` | 7.708 | 1.134 | 1.927 |
| `state-reconcile.md` | 7.597 | 1.067 | 1.899 |
| `pr-feedback-ingest.md` | 7.568 | 1.073 | 1.892 |
| `contract-signoff.md` | 7.506 | 1.077 | 1.876 |
| `implement-slice-complement.md` | 7.342 | 1.047 | 1.836 |
| `decision-interview.md` | 7.179 | 1.029 | 1.795 |
| `capture-observation.md` | 7.067 | 1.036 | 1.767 |
| `slice-closure.md` | 7.041 | 1.040 | 1.760 |
| `targeted-questions.md` | 6.842 | 1.003 | 1.710 |
| `invariants-and-non-goals.md` | 6.610 | 952 | 1.652 |
| `im-stuck.md` | 6.450 | 974 | 1.612 |
| `sync-task-state.md` | 6.427 | 937 | 1.607 |
| `branch-commit.md` | 6.405 | 989 | 1.601 |
| `where-we-at.md` | 6.265 | 919 | 1.566 |
| `review-hard.md` | 5.964 | 864 | 1.491 |
| `prompt-shape.md` | 5.682 | 854 | 1.420 |
| `resume-from-state.md` | 5.600 | 817 | 1.400 |
| `workflow-guide.md` | 5.437 | 828 | 1.359 |
| `team-update.md` | 5.186 | 794 | 1.296 |
| `what-next.md` | 5.125 | 773 | 1.281 |
| **TOTAL** | **265.987** | **38.751** | **66.495** |

- Mean: 2.015 tokens/command
- Largest: `db-context-supabase.md` (3.462 tokens)
- Smallest: `what-next.md` (1.281 tokens)

## Shared blocks (7 files)

| File | Chars | Words | ~Tokens |
|---|---:|---:|---:|
| `README.md` | 4.179 | 600 | 1.045 |
| `artifact-changes-default.md` | 277 | 38 | 69 |
| `command-transcript-lean.md` | 214 | 37 | 54 |
| `command-transcript-standard.md` | 298 | 52 | 74 |
| `handoff-body.md` | 239 | 38 | 60 |
| `mandatory-context-bootstrap.md` | 777 | 108 | 194 |
| `standard-output-layout.md` | 65 | 9 | 16 |
| **TOTAL** | **6.049** | **882** | **1.512** |

## Templates (2 files)

| File | Chars | Words | ~Tokens |
|---|---:|---:|---:|
| `PR_PACKAGE.md` | 1.602 | 236 | 400 |
| `review-hard-checklist.md` | 1.771 | 291 | 443 |
| **TOTAL** | **3.373** | **527** | **843** |

## TASK_STATE sample (representative)

- Path: `projects/bmazurok__my-work-tasks/active/2026-05-02_prepare-for-public-agpl-release/TASK_STATE.md`
- Chars: 10.228 | Words: 1.447 | ~Tokens: 2.557

## WORKFLOW_OPERATING_SYSTEM.md detail

- Total: 65.335 chars / 8.804 words / **~16.334 tokens**

**Top 12 WOS sections by size:**

| Section | Chars | ~Tokens |
|---|---:|---:|
| Global output contract | 8.059 | 2.015 |
| Cross-cutting workflow guardrails | 7.565 | 1.891 |
| Command roles | 6.847 | 1.712 |
| Repositories | 6.383 | 1.596 |
| Repository structure | 4.444 | 1.111 |
| Project-level memory | 3.269 | 817 |
| Definition of done (command outputs) | 2.842 | 710 |
| Cursor mode policy | 2.427 | 607 |
| Recommended workflows by task shape | 2.411 | 603 |
| LLM execution contract | 2.010 | 502 |
| Default workflow | 1.938 | 484 |
| Required task files | 1.791 | 448 |

## Cache scenario projection (5-step typical flow)

Flow modeled: `task-init` → `impact-analysis` → `implementation-plan` → `implement-approved-slice` → `pr-package`.
Assumption: each command loads full WOS (16.334 tokens) + its own command file + all shared blocks (1.512 tokens) + current TASK_STATE (2.557 tokens) + ~300 tokens user input.

| Step | Command | Cmd ~tok | TASK_STATE ~tok | Total static (cacheable) | Total dynamic |
|---|---|---:|---:|---:|---:|
| 1 | `task-init.md` | 3.200 | 2.557 | 17.846 | 6.057 |
| 2 | `impact-analysis.md` | 2.226 | 2.557 | 17.846 | 5.083 |
| 3 | `implementation-plan.md` | 2.340 | 2.557 | 17.846 | 5.197 |
| 4 | `implement-approved-slice.md` | 1.927 | 2.557 | 17.846 | 4.784 |
| 5 | `pr-package.md` | 2.597 | 2.557 | 17.846 | 5.454 |

### Scenario costs (token-equivalents for the full 5-step flow)

| Scenario | Description | ~Token-equivalents | vs A |
|---|---|---:|---:|
| **A** | Current arch, full WOS, cache hit (default Claude Code) | 56.021 | 1.00× |
| **B** | Current arch, full WOS, no cache (new chat per command) | 115.805 | 2.07× |
| **C** | After P1 (WOS_CORE ≤3k + topics lazy), with cache | 34.020 | 0.61× |
| **D** | After P1+P2+P3 (WOS_CORE + shared deduped), with cache | 32.772 | 0.59× |
| **E** | After Agent Skills migration (lazy body load), with cache | 35.748 | 0.64× |

### Key observations

- WOS alone is **16.334 tokens** (25% of all commands combined).
- Shared blocks total **1.512 tokens** but get **inlined into 33 commands** by `sync-shared-blocks.sh` — actual repo footprint is ~33× higher than the source.
- Largest WOS section is **'Global output contract'** at 2.015 tokens (single section bigger than several commands combined).
- Min cacheable size for Opus 4.7 is 4.096 tokens. WOS+shared = 17.846 tokens, well above the threshold (cache works).
- After P1 (WOS_CORE ≤3k), static portion drops to 4.512 tokens — still above the 4.096-token cache floor, so we keep cache benefits.
- Scenario A → C delta: **39% fewer token-equivalents** in a typical 5-step session.
- Scenario A → E (full Skills migration) delta: **36% fewer token-equivalents** — biggest win comes from lazy body load.
- Scenario A vs B (no cache fallback): cache currently saves **52%** vs cold reads. If a user clears chat per command, they pay full price every time.
