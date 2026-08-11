---
name: unity-asset-identity-break
category: data-integrity
default-severity: P1
cwe: [CWE-1076, CWE-476]
languages: [csharp]
file-patterns: ["**/*.meta", "**/*.unity", "**/*.prefab", "**/*.asset", ".gitignore", "Assets/**"]
perspectives: [maintainer]
reversibility-check: false
---

# unity-asset-identity-break

Unity-scoped by mechanism, not by preference: the `.meta` sidecar and its GUID are a Unity asset-identity system with no counterpart in other engines, so this template stays single-stack for the same reason `migration-risk-lock-or-irreversible` is SQL-only (ADR-0130 D-3 carve-out).

## Trigger

Unity assigns every asset a unique ID on import and stores it, plus all import settings, in a sidecar `.meta` file. That ID is how every reference to the asset is resolved, which is what lets an asset be moved or renamed without breaking anything. The failure is the inverse: "If an asset loses its `.meta` file, any reference to that asset is broken in your project" (https://docs.unity3d.com/6000.0/Documentation/Manual/AssetMetadata.html).

The defect is any change that separates an asset from its `.meta` file, or that adds an asset without one: a file created or moved outside the Editor, a `.gitignore` that excludes `*.meta`, a partial commit that lands the asset but not its sidecar, or a merge that drops one side.

This is a high-value class for agent-written Unity work specifically. An agent creating or moving files through the filesystem rather than the Editor produces exactly this state, the project still compiles, and the breakage surfaces later and elsewhere: "If a texture asset loses its `.meta` file, any materials that use that texture lose their reference to that texture", and "If a script asset loses its `.meta` file, any GameObjects or Prefabs that have that script assigned instead have an unassigned script component, and lose their functionality."

## Detection

Look for:
- An asset file under `Assets/` with no sibling `.meta` file, or a `.meta` file with no corresponding asset (an orphan left by a delete that did not remove both).
- `.gitignore` rules that exclude `*.meta`, or that exclude a directory under `Assets/` without excluding its meta files consistently.
- A diff that adds, moves, renames, or deletes a file under `Assets/` and touches an uneven number of paired files (asset changed, `.meta` untouched, or the reverse).
- A GUID appearing in a `.unity` or `.prefab` file that no `.meta` in the tree declares, which is the serialized form of a broken reference.
- A script rename where the class name and the file name diverge, since Unity resolves a `MonoBehaviour` by the meta GUID and the class must still be findable.
- An empty directory under `Assets/` that version control cannot store: the manual notes "some version control systems (VCS) can't store empty folders", so "the VCS stores the `.meta` file as added or removed, but doesn't store the change of adding or removing the folder itself."

Exclude:
- Files outside `Assets/` (under `Library/`, `Temp/`, `obj/`, `Logs/`), which are generated and correctly ignored.
- A `.meta` for a file that was intentionally deleted in the same change, where both sides are removed together.
- Packages resolved through the Package Manager, whose metas live inside the package, not the project tree.

## Retrieval

- The full diff of paths under `Assets/`, paired asset-and-meta.
- The project `.gitignore`, and the canonical Unity gitignore it was derived from.
- Any `.unity` or `.prefab` touched by the change, for the GUID references they carry.
- The output of a tree walk listing assets with no matching `.meta` and metas with no matching asset.

## Analysis prompt

Given the change:
1. Does every added or moved file under `Assets/` carry its `.meta` sibling in the same change?
2. Does every removed file remove its `.meta` too, leaving no orphan?
3. Does `.gitignore` exclude any `.meta` file, directly or through a directory rule?
4. Do the GUIDs referenced by any touched `.unity` or `.prefab` all resolve to a `.meta` present in the tree?
5. Was any asset created or moved outside the Unity Editor, which is the state that produces a missing or regenerated meta?
6. Recommended fix: restore the original `.meta` rather than letting Unity regenerate one. A regenerated meta carries a NEW GUID, so it does not repair the existing references; it creates a second break. When the original is unrecoverable, the references must be reassigned deliberately.

## Severity rubric

- P0: a `.meta` is missing for a script or prefab that gameplay depends on, so components deserialize unassigned and the feature is silently dead in a build.
- P1: a `.meta` is missing or orphaned for any other asset, or `.gitignore` excludes metas, so the break reaches anyone who clones the repo.
- P2: metas are intact and the concern is hygiene, such as an orphan meta for an already-deleted asset.

## Confidence factors

- HIGH: a file was added under `Assets/` with no `.meta` in the same change, or `.gitignore` excludes `*.meta`.
- MEDIUM: paths were moved and the meta pairing cannot be confirmed from the diff alone.
- LOW: metas are paired and the concern is an orphan or an empty-directory edge case.

## Examples

### Positive (the bug)

```gitignore
# Assets/ largely tracked, but this rule silently strips every sidecar.
# Every asset reference in every scene and prefab breaks on a fresh clone.
*.meta
```

```text
# A diff that adds a script without its identity file.
+ Assets/Scripts/Player/DashAbility.cs
# (no Assets/Scripts/Player/DashAbility.cs.meta)
#
# The project compiles. On another machine Unity imports the script and
# mints a NEW GUID, so every prefab that referenced the old one shows
# "The associated script can not be loaded" and the component is inert.
```

### Negative (not the bug)

```text
# Both sides move together, so the GUID and every reference to it survive.
R  Assets/Scripts/Player/DashAbility.cs      -> Assets/Scripts/Abilities/DashAbility.cs
R  Assets/Scripts/Player/DashAbility.cs.meta -> Assets/Scripts/Abilities/DashAbility.cs.meta
```
