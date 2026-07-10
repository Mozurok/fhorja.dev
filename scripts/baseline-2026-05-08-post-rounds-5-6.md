# WOS token baseline — P0 measurement

Method: chars / 4.0 (approximation; ~10% precision vs Claude tokenizer).
Anthropic prompt cache: write 1.25×, read 0.1×, min cacheable Opus 4.7 = 4.096 tokens.

## Root-level documents

| File | Chars | Words | ~Tokens |
|---|---:|---:|---:|
| `WORKFLOW_OPERATING_SYSTEM.md` | 53.191 | 7.170 | 13.298 |
| `CLAUDE.md` | 5.146 | 706 | 1.286 |
| `README.md` | 24.219 | 2.864 | 6.055 |
| `WORKFLOW_DEMO.md` | 14.721 | 1.783 | 3.680 |
| `COMMAND_PROMPT_STUBS.md` | 7.447 | 879 | 1.862 |
| `ROADMAP.md` | 7.299 | 1.002 | 1.825 |
| `CONTRIBUTING.md` | 6.855 | 950 | 1.714 |
| `CHANGELOG.md` | 13.884 | 1.670 | 3.471 |

## Commands (33 files) — sorted by token count

| File | Chars | Words | ~Tokens |
|---|---:|---:|---:|
| `db-context-supabase.md` | 14.796 | 2.061 | 3.699 |
| `incident-triage.md` | 14.326 | 2.068 | 3.582 |
| `task-init.md` | 13.608 | 1.971 | 3.402 |
| `project-bootstrap.md` | 13.390 | 1.923 | 3.348 |
| `code-locate.md` | 12.511 | 1.861 | 3.128 |
| `pr-package.md` | 11.240 | 1.667 | 2.810 |
| `direction-adjust.md` | 10.548 | 1.522 | 2.637 |
| `implementation-plan.md` | 10.200 | 1.453 | 2.550 |
| `capture-references.md` | 10.161 | 1.471 | 2.540 |
| `impact-analysis.md` | 9.894 | 1.426 | 2.474 |
| `post-review-pivot.md` | 9.162 | 1.299 | 2.290 |
| `test-strategy.md` | 9.063 | 1.319 | 2.266 |
| `resolve-contract-gaps.md` | 8.824 | 1.257 | 2.206 |
| `implement-approved-slice.md` | 8.709 | 1.272 | 2.177 |
| `state-reconcile.md` | 8.603 | 1.204 | 2.151 |
| `pr-feedback-ingest.md` | 8.576 | 1.210 | 2.144 |
| `implement-slice-complement.md` | 8.460 | 1.196 | 2.115 |
| `contract-signoff.md` | 8.238 | 1.176 | 2.060 |
| `capture-observation.md` | 8.090 | 1.173 | 2.022 |
| `decision-interview.md` | 8.013 | 1.141 | 2.003 |
| `slice-closure.md` | 7.843 | 1.155 | 1.961 |
| `targeted-questions.md` | 7.695 | 1.116 | 1.924 |
| `invariants-and-non-goals.md` | 7.397 | 1.061 | 1.849 |
| `im-stuck.md` | 7.366 | 1.116 | 1.842 |
| `sync-task-state.md` | 7.272 | 1.055 | 1.818 |
| `branch-commit.md` | 7.232 | 1.125 | 1.808 |
| `where-we-at.md` | 7.196 | 1.061 | 1.799 |
| `review-hard.md` | 6.850 | 992 | 1.712 |
| `prompt-shape.md` | 6.697 | 1.003 | 1.674 |
| `resume-from-state.md` | 6.466 | 949 | 1.616 |
| `workflow-guide.md` | 6.447 | 988 | 1.612 |
| `team-update.md` | 5.974 | 907 | 1.494 |
| `what-next.md` | 5.929 | 891 | 1.482 |
| **TOTAL** | **296.776** | **43.089** | **74.195** |

- Mean: 2.248 tokens/command
- Largest: `db-context-supabase.md` (3.699 tokens)
- Smallest: `what-next.md` (1.482 tokens)

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

- Total: 53.191 chars / 7.170 words / **~13.298 tokens**

**Top 12 WOS sections by size:**

| Section | Chars | ~Tokens |
|---|---:|---:|
| Global output contract | 7.465 | 1.866 |
| Command roles | 6.847 | 1.712 |
| Cross-cutting workflow guardrails | 4.043 | 1.011 |
| LLM execution contract | 3.124 | 781 |
| Definition of done (command outputs) | 2.842 | 710 |
| Project-level memory | 2.531 | 633 |
| Cursor mode policy | 2.427 | 607 |
| Recommended workflows by task shape | 2.411 | 603 |
| Repository structure | 2.234 | 558 |
| Default workflow | 1.938 | 484 |
| Required task files | 1.791 | 448 |
| Multi-repo support (v1) | 1.698 | 424 |

## Cache scenario projection (5-step typical flow)

Flow modeled: `task-init` → `impact-analysis` → `implementation-plan` → `implement-approved-slice` → `pr-package`.
Assumption: each command loads full WOS (13.298 tokens) + its own command file + all shared blocks (1.512 tokens) + current TASK_STATE (2.557 tokens) + ~300 tokens user input.

| Step | Command | Cmd ~tok | TASK_STATE ~tok | Total static (cacheable) | Total dynamic |
|---|---|---:|---:|---:|---:|
| 1 | `task-init.md` | 3.402 | 2.557 | 14.810 | 6.259 |
| 2 | `impact-analysis.md` | 2.474 | 2.557 | 14.810 | 5.331 |
| 3 | `implementation-plan.md` | 2.550 | 2.557 | 14.810 | 5.407 |
| 4 | `implement-approved-slice.md` | 2.177 | 2.557 | 14.810 | 5.034 |
| 5 | `pr-package.md` | 2.810 | 2.557 | 14.810 | 5.667 |

### Scenario costs (token-equivalents for the full 5-step flow)

| Scenario | Description | ~Token-equivalents | vs A |
|---|---|---:|---:|
| **A** | Current arch, full WOS, cache hit (default Claude Code) | 52.134 | 1.00× |
| **B** | Current arch, full WOS, no cache (new chat per command) | 101.748 | 1.95× |
| **C** | After P1 (WOS_CORE ≤3k + topics lazy), with cache | 35.143 | 0.67× |
| **D** | After P1+P2+P3 (WOS_CORE + shared deduped), with cache | 33.895 | 0.65× |
| **E** | After Agent Skills migration (lazy body load), with cache | 36.870 | 0.71× |

### Key observations

- WOS alone is **13.298 tokens** (18% of all commands combined).
- Shared blocks total **1.512 tokens** but get **inlined into 33 commands** by `sync-shared-blocks.sh` — actual repo footprint is ~33× higher than the source.
- Largest WOS section is **'Global output contract'** at 1.866 tokens (single section bigger than several commands combined).
- Min cacheable size for Opus 4.7 is 4.096 tokens. WOS+shared = 14.810 tokens, well above the threshold (cache works).
- After P1 (WOS_CORE ≤3k), static portion drops to 4.512 tokens — still above the 4.096-token cache floor, so we keep cache benefits.
- Scenario A → C delta: **33% fewer token-equivalents** in a typical 5-step session.
- Scenario A → E (full Skills migration) delta: **29% fewer token-equivalents** — biggest win comes from lazy body load.
- Scenario A vs B (no cache fallback): cache currently saves **49%** vs cold reads. If a user clears chat per command, they pay full price every time.
