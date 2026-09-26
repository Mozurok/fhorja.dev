---
activation: model_decision
description: Recommended model SKU and Codex reasoning-effort keyed on the escalations a task records, the override rules, and the refresh cadence for the table. Non-normative guidance the user may override per task. Load when choosing which model to run a task with, or when the six-week SKU refresh comes due; command handoff lines stay vendor-neutral and never carry a SKU.
---

# wos/model-routing.md

Moved out of ADR-0025 on 2026-08-30 by ADR-0172; the ADR records the decision, this topic carries the operational table that has to be updated.

Each row maps a recorded escalation to a recommended Claude model. This is non-normative guidance (the user may override at runtime), but defaults reduce the "always use Opus" anti-pattern (Claude Max 20x users routinely waste plan capacity by running Opus for a single-file task with no escalation fired).

| What the task recorded | Default model | Codex reasoning-effort default | Rationale |
|---|---|---|---|
| `Escalations: none` | `claude-haiku-4-5` | `low` | Single-file, known decisions, under 5 files. The fastest model with near-frontier intelligence; handles trivial-to-moderate edits without quality loss. |
| `impact-analysis` fired | `claude-sonnet-5` | `medium` | Multi-file, some research. The vendor describes it as the best combination of speed and intelligence, at $2/$10 per MTok against Opus 5.5's $4/$20. Sweet spot for most coding work. |
| `decision-interview` fired | `claude-sonnet-5` (default) then `claude-opus-5-5` | `medium` then `high` | Multi-package or non-obvious tradeoffs. Start Sonnet; escalate to Opus when integration risk is high. |
| a strict surface | `claude-opus-5-5` | `high` | Auth, payments, compliance, multi-tenant. The vendor's stated model for long-running agentic coding and knowledge work, and its recommended starting point for most workloads. Worth the cost when blast radius is large. |
| long-horizon agentic work, or Opus 5.5 at higher effort still falling short | `claude-fable-5-1` | `high` | The vendor's own escalation path off Opus 5.5, in its words: for demanding reasoning and long-horizon agentic work. $10/$50 per MTok, slower. Not a default for anything; a deliberate step up. |

Model IDs and roles read from https://platform.claude.com/docs/en/models/overview on 2026-09-22, HTTP 200. Roles are the vendor's own descriptions, not a benchmark claim of ours: this table has no independent measurement behind it and should not be read as one. Haiku 4.5 is still current and kept its row. The other three SKUs this table carried until that date (Sonnet 4.6, Opus 4.7 and Opus 4.8) are still available as legacy models. Their exact IDs are deliberately NOT spelled here: a blind global sed over this tree on 2026-09-17 rewrote this very sentence, so it claimed the table had carried the NEW ids while calling them legacy in the same breath. A rename sweep rewrites the prose ABOUT the thing as readily as the thing, so the drift degraded the routing rather than breaking it, which is precisely why nothing surfaced it for 9.6 weeks.

Changed on 2026-09-22, five days after the previous scan and inside its cadence window: Claude Opus 5.5 (`claude-opus-5-5`) became the vendor's recommended starting point and Claude Opus 5 moved to its legacy list, still available. Two consequences for this table. The Opus rows now name 5.5, and 5.5 runs at `medium` effort by default on the API, where Opus 5 was not listed with a lower default, so a strict-surface task that wants `high` has to set it rather than inherit it. A six-week cadence could not have caught this: a model launch does not wait for the calendar.

Dated and worth watching: `claude-haiku-4-5` retires "not sooner than October 15, 2026", about four weeks after this scan. It is the only row here with a retirement date inside the next cadence window.

Codex column note (v3 wave1, item I): the effort defaults are a PROPOSED mapping, not validated. The only cross-model dogfood to date (bv3, 2026-07-20/21) ran a single effort setting for the whole session, undifferentiated by tier. The Override rules below apply to the effort column textually (escalating up is always valid; do not demote below the row's default; per-task, recorded in TASK_STATE.md).

### Override rules

- Picking a stronger model than the row suggests is always valid. When in doubt, pick stronger. There is no ladder of named tiers to walk up: ADR-0207 retired the labels and kept the escalations, and a strict surface is a categorical trip condition rather than the top rung.
- Dropping from Opus to Sonnet on a strict surface is NOT recommended. If the routing feels wrong, fix the recorded escalations at task-init, which emits the fired disqualifier rather than a label; do not demote the model.
- Override is per-task, not per-session. The chosen model is recorded in `TASK_STATE.md` beside the `Escalations:` line so it survives session breaks.

### Verification cadence

Last scanned: 2026-09-22
Cadence: 6 weeks

Every 6 weeks, open the vendor's model overview, update the SKUs and roles in this table, and move the
`Last scanned:` line above. Coding-model SOTA moves fast. Stale SKUs degrade the routing more than no
routing at all, and that sentence was already in this file on 2026-07-11 while the table sat 9.6 weeks
past its own cadence with nothing measuring it. The two lines above are machine-readable for exactly
that reason; `scripts/check-doc-currency.sh` reads them and reports the age in lint.

### Why hardcode SKUs here

The "no model SKUs in handoff lines" rule in `WORKFLOW_OPERATING_SYSTEM.md` → `## Global output contract` → `### Work complexity (capability routing)` exists for *runtime handoff lines* read by external tools (Cursor, others) that need vendor-neutral routing. This topic is the project-level configuration where SKU choice belongs (it moved out of ADR-0025 under ADR-0172); updating one file is cheaper than updating handoff lines across every command when SOTA shifts.

### Tracking

`scripts/track-model-usage.sh` parses Claude Code session transcripts and writes a per-session CSV (model used, message count, tool-use count, timestamps, project folder) to a maintainer-local, gitignored path. It is a usage baseline, not a routing audit: it records no escalations and no per-task record, so whether a task followed this table's recommendation and what cost delta that produced is not measured yet.
