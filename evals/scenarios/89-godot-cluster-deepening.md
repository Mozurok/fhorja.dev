# Eval scenario 89: Godot cluster deepening surfaces the security bug-classes on a Godot project, capability-scoped

- **Tags**: ADR-0078, godot, game-dev, 2d-mobile, bug-classes, repo-consistency-sweep, capability-routed, security
- **Last reviewed**: 2026-07-02
- **Status**: active

## Goal

Validates **ADR-0078** (the Godot 2D-mobile cluster deepening): the two net-new Godot security bug-classes (`godot-untrusted-resource-deserialization`, CWE-502; `godot-monetization-integrity`, CWE-602) are detected by `repo-consistency-sweep` on a Godot project, are capability-scoped (a non-Godot sweep does not raise them), and the Godot reference topics ground the finding instead of training-default guessing.

This exercises:

- Detection: an untrusted `ResourceLoader.load` on a `user://` save is flagged as CWE-502 arbitrary code execution; a client-side entitlement grant is flagged as CWE-602 monetization integrity.
- Capability scoping: the two classes are raised only because the project is Godot (GDScript, `project.godot`); they must not appear on a non-Godot sweep.
- Category discipline: both classes are category `security` (no new `game-godot` category, per D-3).
- Grounding: the recommended fix cites the Godot 2D-mobile reference topics (safe serialization from `wos/godot-2d-architecture.md`, server-side purchase verification behind the monetization class), not invented API.
- No cluster growth: the deepening adds topics and bug-classes, not a third command.

## Setup

A fixture Godot 2D-mobile project (a `project.godot`, GDScript `.gd` files) with two seeded defects: a save loader that calls `ResourceLoader.load("user://savegame.tres")` on a player-editable file, and a purchase handler that grants premium currency directly in the client-side `purchases_updated` signal without server verification. At least one implemented slice exists so `repo-consistency-sweep` is in scope.

## Input prompt

```text
Run @commands/repo-consistency-sweep.md for projects/acme__game/active/2026-07-02_iap-and-saves/. The slice added a save/load system (user:// .tres) and a Google Play in-app purchase flow (GodotGooglePlayBilling). Check the change against the bug-class library before PR packaging.
```

## Expected response shape

- The sweep raises `godot-untrusted-resource-deserialization` (P0, CWE-502) on the `ResourceLoader.load` of the `user://` save, explaining that a `.tres`/`.res` from an untrusted source runs embedded scripts on load.
- The sweep raises `godot-monetization-integrity` (P0, CWE-602) on the client-side grant, requiring server-side purchase-token verification, dedupe by token, and grant only on `PURCHASED`.
- Both findings are category `security`; neither introduces a new category.
- The recommended fixes cite the cluster knowledge (safe serialization with `store_var` objects-off or JSON, a safe-resource loader; server-side verification), not a fabricated API.
- Response ends with a `### Handoff` block routing forward (for example to `implement-approved-slice` for the fix or `pr-package` once clean).

## Pass criteria

1. Both Godot security bug-classes are raised with their correct CWE (CWE-502 and CWE-602) and P0 severity.
2. Each finding maps to the correct seeded defect (deserialization on the save load, integrity on the client-side grant).
3. Both are reported under the `security` category; no `game-godot` category is invented (D-3).
4. The fixes are grounded in the Godot reference topics or bug-class remediation, with no invented Godot API or version.
5. The response does not treat the deepening as a new command and names no specific MCP server.
6. The handoff routes to an official command that exists in `commands/`.

## Failure modes to watch

- **Miss**: the sweep does not carry the Godot classes and reports only generic security findings (or nothing), which means the capability routing failed to load them on a Godot project.
- **Over-trigger**: the same classes are raised on a non-Godot fixture (a plain TypeScript repo), which means they are not capability-scoped.
- **Category drift**: a finding is filed under a new `game-godot` category, violating D-3.
- **Fabrication**: an invented Godot API, a Godot 3 name (`OpenSimplexNoise`, `NOTIFICATION_APP_PAUSED`), or a made-up billing method in the remediation.

## Notes

- Related ADRs: [ADR-0078](../../docs/adr/0078-godot-2d-mobile-cluster-deepening.md), [ADR-0069](../../docs/adr/0069-godot-2d-mobile-cluster.md) (the cluster this deepens).
- Related files: `wos/bug-classes/godot-untrusted-resource-deserialization.md`, `wos/bug-classes/godot-monetization-integrity.md`, `wos/godot-2d-architecture.md`, `commands/repo-consistency-sweep.md`.
- Known issues: none yet (first run pending).

## History

(Pending first run.)
