---
name: unity-scene-prefab-yaml-corruption
category: data-integrity
default-severity: P1
cwe: [CWE-436]
languages: [csharp]
file-patterns: ["**/*.unity", "**/*.prefab", ".gitattributes", ".gitconfig", "**/*.asset"]
perspectives: [maintainer]
reversibility-check: true
---

# unity-scene-prefab-yaml-corruption

Unity-scoped by mechanism: the defect is a conflict between git's line-oriented merge and Unity's own YAML serialization of scenes and prefabs. Single-stack for the same reason as `unity-asset-identity-break` (ADR-0130 D-3 carve-out).

## Trigger

Unity serializes scenes and prefabs as YAML, and ships a dedicated merge tool for them: "Use the **UnityYAMLMerge** tool to merge scene and prefab files in a semantically correct way" (https://docs.unity3d.com/6000.3/Documentation/Manual/SmartMerge.html). A generic three-way text merge does not model the document's structure, so it can resolve a conflict into a file that parses as valid YAML while the scene hierarchy, component references, or GameObject relationships inside it are wrong.

This is CWE-436, an interpretation conflict: git's text merger and Unity's YAML reader disagree about what the bytes mean, and only the second one is authoritative.

The class covers two failure shapes. The first is a merged `.unity` or `.prefab` produced without UnityYAMLMerge configured. The second is hand-authored or hand-patched scene and prefab YAML, which is the same hazard reached by a different route and the one that matters most for agent-driven work: an agent editing a `.prefab` as text is doing precisely what the tool exists to prevent, and the corruption passes a syntax check.

## Detection

Look for:
- A repository with `.unity` or `.prefab` files under version control and no `merge.tool` plus `mergetool.unityyamlmerge` pair configured, so a conflicting merge falls through to the default text merger.
- A diff that edits a `.unity`, `.prefab`, or `.asset` file as raw text rather than through the Editor: hand-written `fileID` or `guid` values, reordered YAML documents, or hand-edited component blocks.
- Conflict markers (`<<<<<<<`, `=======`, `>>>>>>>`) surviving inside a `.unity` or `.prefab`, or evidence they were resolved by hand.
- A scene or prefab whose YAML document anchors (`--- !u!<classID> &<fileID>`) are duplicated or missing, or whose `m_Component` list references a `fileID` no document in the file defines.
- Project settings forcing binary serialization while the merge tooling assumes text, or the reverse, which makes the merge path silently different from the one documented.
- A `.gitattributes` with no `merge=unityyamlmerge` entry for scene and prefab paths.

Exclude:
- A change that touches a scene or prefab only through the Editor, with no conflict resolved on that file.
- Files under `Library/` or `Temp/`, which are generated.
- A deliberate, reviewed text edit to a `.asset` ScriptableObject with a flat schema and no component graph.

## Retrieval

- The git merge configuration (`.gitconfig`, `.git/config`, `.gitattributes`) for a unityyamlmerge entry.
- The full diff of any `.unity`, `.prefab`, or `.asset` in the change.
- The YAML document headers and the `m_Component` and `m_Children` reference lists in any touched scene or prefab.
- Whether the change originated in the Editor or in a text editor.

## Analysis prompt

Given the change:
1. Is UnityYAMLMerge configured as the merge tool for scene and prefab paths, so a conflict is resolved semantically rather than by line?
2. Was any `.unity` or `.prefab` in this change merged, and if so by which tool?
3. Was any scene or prefab edited as raw text rather than through the Editor?
4. Do all `fileID` references inside each touched file resolve to a document defined in that same file?
5. Has the touched scene or prefab actually been opened in the Editor since the change, which is the only real proof the graph still loads?
6. Recommended fix: configure UnityYAMLMerge (`merge.tool = unityyamlmerge` plus a `mergetool.unityyamlmerge` entry invoking `UnityYAMLMerge merge -p "$BASE" "$REMOTE" "$LOCAL" "$MERGED"`), and reserve hand-editing of scene and prefab YAML for cases where the file has been opened in the Editor afterwards to confirm it still loads.

## Severity rubric

- P0: a merged or hand-edited scene or prefab is committed with unresolved or dangling `fileID` references, so the scene fails to load or loads with missing components.
- P1: scene and prefab files are under version control with no UnityYAMLMerge configured, so the next conflicting merge corrupts silently.
- P2: configuration is correct and the concern is an unreviewed text edit to a flat `.asset` with no component graph.

## Confidence factors

- HIGH: conflict markers or dangling `fileID` references are present inside a `.unity` or `.prefab`, or the diff hand-authors YAML component blocks.
- MEDIUM: scene and prefab files are tracked with no merge tool configured, but no conflicting merge has occurred yet in this change.
- LOW: the concern is a flat `.asset` edit with no reference graph to break.

## Examples

### Positive (the bug)

```yaml
# A hand-patched prefab. The GameObject lists a component fileID that no
# document in the file defines. This parses as valid YAML and loads as a
# prefab with a missing component; nothing errors at import time.
--- !u!1 &6512847362849201
GameObject:
  m_Component:
  - component: {fileID: 6512847362849202}
  - component: {fileID: 8899000011112222}   # no such document below
--- !u!4 &6512847362849202
Transform:
  m_LocalPosition: {x: 0, y: 0, z: 0}
```

### Negative (not the bug)

```gitconfig
# Conflicts on scenes and prefabs are resolved by the tool that models
# the document, not by the line-oriented default.
[merge]
    tool = unityyamlmerge

[mergetool "unityyamlmerge"]
    trustExitCode = false
    cmd = '/Applications/Unity/Unity.app/Contents/Helpers/UnityYAMLMerge' merge -p "$BASE" "$REMOTE" "$LOCAL" "$MERGED"
```
