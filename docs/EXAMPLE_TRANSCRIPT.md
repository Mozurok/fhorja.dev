# A real session, walked end to end

This is the actual Fhorja task that built and shipped [fhorja.dev](https://fhorja.dev), walked from `task-init` to `task-close`. It is here to answer one fair question a skeptic asks about any workflow demo: **is this real work, or a scripted illusion of it?**

## What this is (and what it is not)

Every excerpt below is copied from the task's own persisted files: `BRIEF.md`, `DECISIONS.md`, the per-slice notes under `SLICES/`, `LEARNINGS.md`, and the append-only `.wos/VERIFICATION_LOG.jsonl`. Those files were written by the commands as the work happened, not composed afterward for a demo.

Being honest about the format: this is a **guided reconstruction from those real artifacts**, not a raw chat log. The commands, outputs, decisions, timestamps, and hashes are real and unedited except for cropping. What you do not get here is the full back-and-forth prose of the chat; you get the durable record the workflow left on disk, which is the thing that actually survives a session. Where a number or claim is shown, it is the number the file records.

The task folder itself lives in a private working repo (project memory is gitignored by design, see [ADR-0007](./adr/0007-project-level-memory.md)), so the cross-check you *can* run is the output: the site is live at fhorja.dev, and the workflow that built it is this public repo.

## The task at a glance

Pulled from the verification log's first and last lines:

```
first entry:  2026-07-10T20:31:52Z   owner=task-init     ## Task summary
last entry:   2026-07-12T00:11:03Z   owner=task-close    ## Work complexity
```

- Wall-clock span: about 28 hours across two days (not one sitting; the workflow is built for exactly this, closing the laptop and resuming).
- 25 canonical decisions recorded (`D-1` through `D-25`), several superseding earlier ones.
- 29 implementation slices.
- 460 append-only verification-log entries, each a SHA-256-hashed section write.

The command owners that appear in the log, by write count, are the real shape of the work:

```
111  implement-approved-slice      25  decision-interview
102  implementation-plan           19  slice-closure
 56  direction-adjust               6  task-close
 48  approve-plan                   5  stack-recommend / a11y-audit / release-plan
 34  implement-fleet                4  frontend-system-design
 30  task-init                      2  review-hard
```

Note the 56 `direction-adjust` writes. Real work changes direction. The hero visual was built, then replaced (`D-24` superseded `D-7`/`D-14`); the demo video plan (`D-2`) was superseded by an interactive transcript (`D-8`). None of that is hidden; each pivot is its own dated decision.

## 1. Intake: `problem-framing` writes a brief

Before a task folder existed, `problem-framing` questioned whether the stated problem was the right one and wrote `BRIEF.md`. Its problem statement:

> Fhorja has no public-facing surface, so the v1.0 announcement has nowhere to point and the paid connector (mcp.fhorja.dev, live pre-billing) has no product page anchor.

And its five named deliverables (this list becomes the coverage ledger that closure checks against):

```
1. fhorja.dev live (landing page deployed on the owned domain).
2. Hero terminal typing animation (code-driven).
3. POC demo video of the core loop recorded from a real session.
4. mcp.fhorja.dev anchor section with product status.
5. Design reference set in REFERENCES.md plus a11y and performance budget reports passing before launch.
```

## 2. `task-init`: the folder and the memory

`task-init` created the task folder and seeded the five mandatory files. Its first verification-log line is the one shown above, `owner=task-init`, `## Task summary`, at `2026-07-10T20:31:52Z`.

## 3. Decisions get recorded once, with reasoning

`DECISIONS.md` holds 25 entries. The first six, verbatim and cropped:

```
- D-1 (2026-07-10, intake): the approach is static-first with a design-first
  flow. Capture design references, lock a design direction, build, and gate
  launch on a11y and performance budgets; the stack is decided inside the task
  via stack-recommend. A full app framework and a no-code builder were
  considered and rejected at intake.
- D-2 (2026-07-10): the POC demo video SHALL record the real core loop in a
  Claude Code session ... [Superseded by D-8]
- D-4 (2026-07-10): the site SHALL build on the STACK_RECOMMENDATION.md pins:
  Astro 7.0.7, Tailwind CSS 4.3.2, Node 24 LTS, Cloudflare Workers static
  assets, and @lhci/cli 0.15.1 as the CI gate. Adjustments route through a new
  D-N, not silent drift.
- D-6 (2026-07-10): the design direction SHALL be dark, terminal-first, and
  sober ... near-black base, a single terminal window as the hero artifact.
```

The `[Superseded by D-8]` marker on `D-2` is the point: decisions are not deleted when they change, they are superseded on the record, so the reasoning stays traceable.

## 4. Slices: each one closes on real command output

`implementation-plan` broke the work into 29 slices. Slice 01 (`repo scaffold and deploy`) closed with this validation block, copied verbatim:

```
## Validation completed
- Exit criterion 1 (build SHALL exit 0 on the pinned set): MET.
  `npx astro build` output: "[build] 1 page(s) built in 146ms / Complete!",
  explicit build exit: 0; dist/ contains index.html and _astro.
- Exit criterion 2 (wrangler config SHALL match the CURRENT_PATTERNS shape): MET.
  Shown: grep finds "directory": "./dist" and zero "main" occurrences.
- Pins verified from the installed package.json (shown: astro@7.0.7
  tailwindcss@4.3.2 @tailwindcss/vite@4.3.2).
```

A slice does not close on "looks done." It closes on the exit criterion being MET with the command output shown.

## 5. The honesty moment worth reading

The most convincing evidence that this is not theater is a mistake the workflow caught on itself. From `LEARNINGS.md`, verbatim:

> **Learning: verify claimed-real outputs by running the command before shipping them.** What happened: a drafted "real" fragment (`ls commands/*.md | wc -l` -> 94) was FALSE against the live repo (real output: 85; nine persona commands are directories, not `.md` files). Caught only because the curation step ran the command instead of trusting the count marker.

A number that was going onto the public site was wrong, and it was caught because the rule is to run the command, not recall the answer. That is the same reason the site now says "12-command loop, 94-command catalog" and not a rounder, prettier number.

## 6. The tamper-evident proof: the verification log

Every substrate write across the session appended one line to `.wos/VERIFICATION_LOG.jsonl` with a timestamp, the owning command, the section, and a SHA-256 of the written bytes. Five lines sampled across the 460, compacted:

```
2026-07-10T20:31:52Z  task-init                 TASK_STATE.md   ## Task summary        sha:36d5e5cc3dcc
2026-07-11T00:14:40Z  direction-adjust          DECISIONS.md    ## Approved decisions  sha:ceaf98a8f898
2026-07-11T07:16:00Z  implement-approved-slice  TASK_STATE.md   ## Last completed step sha:e240714f2c5f
2026-07-11T11:35:00Z  release-plan              TASK_STATE.md   ## Work complexity     sha:64b89183e6cc
2026-07-12T00:11:03Z  task-close                TASK_STATE.md   ## Work complexity     sha:4850288aebc7
```

The timestamps span the real two-day window. The hashes make silent after-the-fact edits detectable. This log is generated by the commands during execution; it is not something you would author by hand to fake a session.

## 7. `task-close`: reconcile every named deliverable

At the end, `task-close` checked each of the five named deliverables (plus the ones added mid-task via `direction-adjust`) and marked it done with evidence. Cropped:

```
- fhorja.dev live [done; deployed 2026-07-11 on Cloudflare Workers with the
  fhorja.dev custom domain attached (commit 0c6f676)]
- Interactive terminal transcript walkthrough [done; TranscriptDemo, ten
  schema-gated scenarios (D-8, D-16e)]
- Design references + a11y + performance budget passing before launch [done;
  REFERENCES.md, ACCESSIBILITY_AUDIT.md, PERFORMANCE_BUDGET.md all passing]
```

The task folder then moved from `active/` to `archive/`. That transition is the only official way a task ends.

## How to verify the parts that are public

- **The output**: [fhorja.dev](https://fhorja.dev) is the live site this task shipped.
- **The workflow**: this repository is the exact command set (`commands/`) and spec (`WORKFLOW_OPERATING_SYSTEM.md`) that produced the artifacts quoted above.
- **The site's own honesty note**: the fhorja.dev demos are labeled as scripted walkthroughs on small fictional example apps, and only verifiable fragments are called real. That labeling and this document are the same commitment from two directions.
