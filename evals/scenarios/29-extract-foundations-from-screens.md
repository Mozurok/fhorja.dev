# Eval scenario 29: extract-foundations-from-screens output contract

- **Tags**: extract-foundations-from-screens, design-system, foundations, idempotency, review-queue
- **Last reviewed**: 2026-06-05
- **Status**: active

## Goal

Validates that `extract-foundations-from-screens` aggregates raw design tokens (hex colors, spacing values) from multiple SCREEN_SPEC documents and produces per-foundation Markdown files (`foundations/color.md`, `foundations/spacing.md`) with role mappings, idempotent locked role preservation across re-runs, and explicit `## Review queue` routing for conflicts and off-grid values rather than silent resolution or rounding.

This is a two-turn scenario: turn 1 runs against three fresh SCREEN_SPECs; turn 2 re-runs after a fourth SCREEN_SPEC is added with conflicting values, to prove idempotency and the review queue contract.

## Setup

Requires a design folder with three SCREEN_SPEC files, e.g.:

- `design/screens/SIGN_IN_SPEC.md` -- `#0066FF` (primary CTA), spacing `8`, `16`, `24`.
- `design/screens/DASHBOARD_SPEC.md` -- `#0066FF` (header bar), `#1A1A1A` (text), spacing `8`, `16`, `32`.
- `design/screens/SETTINGS_SPEC.md` -- `#1A1A1A` (text), `#FF3B30` (destructive), spacing `8`, `16`, `24`, off-grid `6` and `10`.

For turn 2, add `design/screens/ONBOARDING_SPEC.md` introducing `#0055EE` mapped to "primary CTA" (conflicts with locked `#0066FF`) and off-grid spacing `14`.

## Input prompt (turn 1: first extraction)

```text
Run @commands/extract-foundations-from-screens.md

source_specs: design/screens/SIGN_IN_SPEC.md, design/screens/DASHBOARD_SPEC.md, design/screens/SETTINGS_SPEC.md
output_dir: design/foundations/
Mode: Agent
```

## Input prompt (turn 2: re-run with conflict)

```text
Run @commands/extract-foundations-from-screens.md

source_specs: design/screens/SIGN_IN_SPEC.md, design/screens/DASHBOARD_SPEC.md, design/screens/SETTINGS_SPEC.md, design/screens/ONBOARDING_SPEC.md
output_dir: design/foundations/
Mode: Agent
```

## Expected response shape (turn 1: first extraction)

- Writes `design/foundations/color.md` with a role table (role :: hex :: source SCREEN_SPEC :: lock status), and `design/foundations/spacing.md` with the resolved on-grid scale.
- Locked role mappings stamped: `#0066FF -> primary-cta (locked)`, `#1A1A1A -> text-primary (locked)`, `#FF3B30 -> destructive (locked)`.
- Off-grid spacing values `6` and `10` routed to a `## Review queue` section with the source SCREEN_SPEC and the candidate on-grid neighbors, not silently rounded.
- `### Artifact changes` lists both foundation files as `APPLIED` (Agent mode).

## Expected response shape (turn 2: re-run idempotent + conflict)

- `color.md` preserves the locked `#0066FF -> primary-cta` mapping verbatim; `#0055EE` does NOT overwrite it.
- `#0055EE` claiming the same `primary-cta` role is appended to `## Review queue` with both contenders, source SCREEN_SPECs, and a "human decision required" note.
- Off-grid `14` appended to `spacing.md` `## Review queue` alongside still-unresolved `6` and `10`.
- Already-locked roles and on-grid spacing values are unchanged; the diff is additive (review queue entries only).

## Pass criteria

1. **Per-foundation files**: produces `foundations/color.md` and `foundations/spacing.md` as separate artifacts, not a single dump.
2. **Role mappings present**: each color carries an explicit role (e.g. `primary-cta`, `text-primary`, `destructive`) sourced from SCREEN_SPEC context, not just a raw hex list.
3. **Locks preserved across re-runs**: turn 2 leaves every locked mapping from turn 1 byte-identical; idempotency holds when no conflict exists.
4. **Conflicts route to Review queue**: turn 2 routes `#0055EE` vs locked `#0066FF` for `primary-cta` into `## Review queue` and does NOT silently overwrite or auto-pick.
5. **Off-grid spacing not rounded**: values `6`, `10`, `14` land in `spacing.md` `## Review queue` with their source SCREEN_SPEC, never silently mapped to `8` or `16`.
6. **Provenance**: every token in both files cites the SCREEN_SPEC it came from (file path or anchor), so a reviewer can verify.
7. **Additive diff on re-run**: turn 2 changes are limited to new review-queue entries and any genuinely new tokens; no churn on previously locked rows.
8. **Handoff**: both turns end with a complete `### Handoff` block routing to `design-spec-review` or the next foundation command.

## Failure modes to watch

- **Silent conflict resolution**: turn 2 replaces `#0066FF` with `#0055EE` for `primary-cta` without surfacing the conflict.
- **Silent off-grid rounding**: `6`/`10`/`14` rounded to `8`/`16` without a review queue entry.
- **Lock churn**: turn 2 rewrites locked rows (reordered, recased, re-sourced) breaking idempotency even when the underlying value is unchanged.
- **Lost provenance**: tokens land in foundations files with no traceable SCREEN_SPEC source, so a human cannot audit the extraction.

## Notes

- Related commands: `commands/extract-foundations-from-screens.md`, `commands/screen-spec.md` (upstream producer), `commands/design-spec-review.md` (downstream consumer).
- The `## Review queue` contract is the single place where ambiguity is surfaced; the command must never resolve color-role conflicts or off-grid spacing on its own.
- Idempotency is the property under test in turn 2: re-runs must be safe to invoke repeatedly without churn.

## History

- 2026-06-05: scenario authored alongside the extract-foundations-from-screens command.
