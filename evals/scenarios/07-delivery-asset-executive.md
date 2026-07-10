# Eval scenario 07: delivery-asset for executive audience

- **Tags**: delivery-asset, audience-fit, no-leakage, grounding
- **Last reviewed**: 2026-05-08
- **Status**: active

## Goal

Validates that `delivery-asset` produces an audience-appropriate artifact (here: an executive summary) grounded in task-memory, with no workflow-path leakage and no invented metrics. Also validates the filename convention `DELIVERY_ASSET_<format>_<audience>.md`.

This exercises:

- The "no workflow-path leakage" rule (`my_work_tasks/`, `commands/`, `TASK_STATE.md`, etc. forbidden in the asset body).
- The "no invented metrics" rule (only metrics anchored in task artifacts may appear).
- The filename convention for multiple assets per task.
- The Handoff contract.
- Audience-appropriate framing (executives vs engineering vs customers).

## Setup

Assume an active task at `projects/acme__widget-pricing/active/2026-05-08_initial-price-query/` is essentially complete. Paste these task-memory artifacts as context:

`TASK_STATE.md`:

```text
# TASK_STATE
## Task summary
Implement GET /v1/prices/:customer_id endpoint.
## Current phase
delivery
## Objective
GET /v1/prices/:customer_id returns the customer's effective price list, with 404 for customers with no prices.
## Last completed step
- Command: pr-package
- Mode: Ask
- Summary: PR_PACKAGE.md proposed; PR draft assembled; reviewer attention points listed.
## Current status
### Completed
- Slice 01: handler wired, both tests green, lint clean.
### In progress
- (none)
### Not started
- (none)
```

`DECISIONS.md`:

```text
# DECISIONS
D-1: GET /v1/prices/:customer_id returns 404 when the customer has no price list (not 200 with empty body).
D-2: The handler is read-only; price computation runs in a nightly batch job, not inline.
```

`PR_PACKAGE.md` (excerpt):

```text
# PR_PACKAGE
## Suggested PR title
Add GET /v1/prices/:customer_id endpoint with 200/404 handling
## PR description
This change adds a thin read-only handler for per-customer price lookups...
- src/handlers/prices.ts (new): the handler itself.
- src/routes.ts: 1-line route registration.
- tests/handlers/prices.spec.ts (new): 2 integration tests covering the 200 (with prices) and 404 (no prices) paths.
```

## Input prompt

```text
Run @commands/delivery-asset.md

Active task: projects/acme__widget-pricing/active/2026-05-08_initial-price-query/
Audience: executives
Format: executive-summary
Tone: formal
Length: tight
Mode: Ask
```

## Expected response shape

- Response begins with delivery-asset's persona line.
- `### Artifact changes` lists `DELIVERY_ASSET_executive-summary_executives.md` PROPOSED in the active task folder.
- The proposed asset follows the canonical wrapper: `## Metadata` (Format, Audience, Tone, Length, Generated date, Grounded in), `## Body` (the actual deliverable), optionally `## Notes for the sender (NOT to be sent)`.
- The Body starts with a one-line standalone summary (some executives only read the first line).
- The Body is short (length=`tight` means ≤200 words).
- The Body cites concrete delivered work (the new endpoint, the 404 handling decision, the test coverage) without naming files, paths, or workflow internals.
- The Body does NOT contain any of: `my_work_tasks/`, `commands/`, `TASK_STATE.md`, `DECISIONS.md`, `IMPLEMENTATION_PLAN.md`, `PR_PACKAGE.md`, `projects/<...>__<...>/`, `src/handlers/prices.ts`, slice numbers, commit SHAs, or other internal vocabulary.
- The Body does NOT invent metrics (no "improves price query latency by 40%", no "saves 3 engineering hours per week", no "reduces support tickets by 25%") that are not in the task artifacts.
- `### Handoff` block at the end. `Run now:` is `team-update` (the asset is one of several outputs and a quick team channel update may also be wanted), `pr-package` (if a PR update is needed alongside), or `state-reconcile` (if grounding revealed drift).

## Pass criteria

1. **Filename**: the asset is named `DELIVERY_ASSET_executive-summary_executives.md` (lowercase + hyphenated values verbatim).
2. **Wrapper structure**: `## Metadata` (with all required fields), `## Body`, optional `## Notes for the sender`. No body content outside this structure.
3. **Body opens with a standalone summary line**: the first line of the Body summarizes the delivery in one sentence.
4. **Length compliance**: with `tight` selected, the Body is ≤200 words.
5. **Audience fit**: language is appropriate for executives (impact-first framing, business outcomes, low jargon density, no implementation specifics like "we wired a thin Express handler over the prices_view").
6. **No workflow-path leakage**: the Body contains zero occurrences of any forbidden internal vocabulary listed above. This is the single most important pass criterion.
7. **No invented metrics**: every claim in the Body traces to a concrete fact in the task-memory artifacts (the endpoint exists; 404 handling per D-1; tests pass per the slice closure). Marketing-style metrics not in the source artifacts are absent.
8. **Handoff intact**: response ends with a complete Handoff. Mode B `Resume context:` includes the task path.

## Failure modes to watch

- **Workflow-path leakage** (single most damaging): the Body says "see PR_PACKAGE.md for details" or "this work is tracked at projects/acme__widget-pricing/active/..." or "the full plan is in IMPLEMENTATION_PLAN.md". Any of these violate the audience contract; executives do not have or want that context.
- **Implementation specifics in an executive summary**: the Body talks about Express handlers, file names, line counts. Engineering-broader audience would tolerate this; executives should not see it.
- **Invented business impact**: the Body claims "reduces query latency by 40%" or "improves customer support efficiency" with no source in the task artifacts. The task added a feature; impact metrics require measurement, which is not in scope.
- **Unanchored deadlines or names**: the Body mentions a launch date or a stakeholder by name when neither appears in `TASK_STATE.md`, `DECISIONS.md`, or `PROJECT_CHARTER.md`.
- **Wrong filename**: `executive_summary_executives.md` (underscore instead of hyphen), `DELIVERY_ASSET_for-executives.md` (audience missing format), or any deviation from the convention.
- **Length overflow**: `tight` was requested but the Body is 500 words. Either re-run with `standard` length explicitly, or trim to fit; do not silently exceed.

## Notes

- Related ADRs: [ADR-0001](../../docs/adr/0001-proposed-by-default.md) (PROPOSED-by-default; the asset is PROPOSED in Ask mode), [ADR-0002](../../docs/adr/0002-paste-this-next-contract.md) (Handoff contract).
- Related commands: `commands/delivery-asset.md`, `commands/team-update.md`, `commands/pr-package.md`. The three are complementary: pr-package for the GitHub PR, team-update for quick team-internal status, delivery-asset for audience-specific outward-facing artifacts.
- The "no workflow-path leakage" rule is the single most important property of this command. Models that have been reading the workflow internals throughout the task tend to want to reference them; the rule says do not.
- Multiple delivery assets per task are expected. A typical post-launch task might generate `DELIVERY_ASSET_executive-summary_executives.md`, `DELIVERY_ASSET_release-note_customers.md`, and `DELIVERY_ASSET_slack-post_engineering-broader.md` from the same task-memory base.

## History

- 2026-05-08: scenario authored. Initial pass criteria defined; not yet run against a model.
