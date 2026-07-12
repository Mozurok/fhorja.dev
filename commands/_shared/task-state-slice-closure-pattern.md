Canonical TASK_STATE.md 5-section write pattern. It was defined at slice closure (its origin and empirical validation: pilot-repo session 2026-06-04, 21 slice closures, ~6 section updates per closure stably converged on this set) and is followed by EVERY command that stamps TASK_STATE.md after a meaningful step (slice-closure, approve-plan, implement-fleet, release-plan, ai-feature-eval-harness, the verify fleets, and peers). Read "closure" below as "the step this command just completed", then edit exactly these 5 sections in this order:

1. `## Current phase` -- if the phase shifted (e.g., discovery -> implementation), update the phase label and any inline progress notes.
2. `## Last completed step` -- replace with `Command: <cmd>`, `Mode: <mode>`, `Summary: <1-2 line outcome>`. This becomes the recovery anchor for `resume-from-state`.
3. `### In progress` (nested under `## Current status`, not a standalone H2, per `task-init.md`'s canonical TASK_STATE.md template) -- if a slice closed cleanly with no follow-up, set to `(nenhum)` / `(none)`. If a follow-up surfaced inside the slice, list it here as the immediate next item.
4. `## Recommended next step` -- replace with `Command: <next>`, `Mode: <mode>`, `Why: <one line>`. Aligns with the Handoff `Run now` line.
5. `## Current closure target` -- if a slice or epic just closed, advance this to the next closure target (next slice or next epic). If the same target still applies, keep it (no-edit OK).

Optional 6th section:

6. `## Resume notes` -- update only when external context shifted (a referenced repo moved, a decision was made elsewhere, etc.). Most slice closures do not touch this.

Rules:

- Use Edit (not Write) per section. Avoid full file rewrites; they invalidate prompt cache and lose audit trail.
- If a section would not materially change, skip it (per `## Material change (definition)` in `WORKFLOW_OPERATING_SYSTEM.md`).
- All 5 mandatory sections must be present in the file. If any is missing, propose adding the missing section first as a separate edit before continuing the closure update.
- Total edits per closure typically range 4-6. More than 8 indicates either drift recovery (mark in transcript) or that `slice-closure` is being misused for closure of multiple slices at once (split into separate runs).
