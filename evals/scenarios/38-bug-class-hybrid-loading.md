# Scenario 38 -- Bug-Class Hybrid Loading

## Purpose

Validate that `wos/bug-classes/_index.md` correctly implements hybrid loading: the global catalog at `wos/bug-classes/*.md` is always loaded, and optional project-local overrides at `projects/<client>__<project>/bug-classes/*.md` are layered on top, with local files taking precedence on name collision. This ensures repo-wide consistency rules remain canonical while allowing per-project specialization without forking the global catalog.

## Setup

- Fhorja engine present with full global bug-class catalog at `packages/wos-engine/internal/wos/bug-classes/` (61 entries as of slice baseline).
- Two project folders staged under `projects/`:
  - `projects/bmazurok__control/` -- no `bug-classes/` subdirectory (baseline case).
  - `projects/acme__demo-app/bug-classes/custom-rule.md` -- one project-local file.
  - `projects/acme__demo-app/bug-classes/unhandled-async-error.md` -- intentional name collision with a global file, with locally tuned content.
- `wos/bug-classes/_index.md` defines the hybrid loading contract.
- `commands/repo-consistency-sweep.md` is the consuming command under test.

## Scenarios

### Scenario A -- Global-only loading (no project overrides)

- Given the user runs `repo-consistency-sweep` from a project context with no `bug-classes/` folder (e.g. `bmazurok__control`).
- When the sweep bootstraps its bug-class set.
- Then it loads exactly the 61 global entries from `wos/bug-classes/*.md` and reports zero local overrides.

### Scenario B -- Hybrid loading with project override

- Given the user runs `repo-consistency-sweep` from `acme__demo-app`, which has a local `bug-classes/` folder containing one new rule (`custom-rule.md`) and one collision (`unhandled-async-error.md`).
- When the sweep bootstraps its bug-class set.
- Then it loads the 61 global entries, adds `custom-rule.md` as a project-only addition, and replaces the global `unhandled-async-error.md` with the local version. Final loaded count: 62, with one collision resolved in favor of local.

## Pass criteria

1. `_index.md` is read first and explicitly states the hybrid loading contract (global + optional project-local; local wins on collision).
2. In Scenario A, the sweep loads all 61 global files and zero local files, with no errors about missing project folders.
3. In Scenario B, the sweep loads 60 global files + 1 global file shadowed by local + 1 new local file, for an effective total of 62 active rules.
4. On collision, the locally overridden bug-class is the one used by the sweep's checks (content from the project file, not the global file).
5. The sweep emits a clear log line or summary listing which bug-classes came from global vs project-local, so the user can audit precedence.
6. Project-local `bug-classes/` directories that do not exist are treated as a no-op, not as an error.
7. The loader respects ADR-0007: project memory directories are gitignored, so project-local bug-classes never leak into the shared repo history.
8. Re-running the sweep is idempotent: the same global+local set produces the same loaded catalog on repeat invocations.

## Failure modes

- Sweep silently ignores project-local `bug-classes/` and only loads globals, missing project-specific rules.
- Collision resolution goes the wrong way (global wins over local), making project overrides useless.
- Sweep errors out when `projects/<client>__<project>/bug-classes/` does not exist, instead of treating absence as a no-op.
- Project-local bug-class files get committed to the shared repo, violating ADR-0007's gitignore boundary.

## Notes

- Contract source: `packages/wos-engine/internal/wos/bug-classes/_index.md`.
- Consumer under test: `packages/wos-engine/internal/commands/repo-consistency-sweep.md`.
- Governance: ADR-0007 (project memory layout + gitignored project folders) establishes why project-local bug-classes live under `projects/<client>__<project>/` and never enter the shared catalog.
- Collision policy is "local wins" because project overrides exist precisely to tune or suppress a global rule that does not fit the project's context.
