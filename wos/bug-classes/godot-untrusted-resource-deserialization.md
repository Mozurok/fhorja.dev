---
name: godot-untrusted-resource-deserialization
category: security
default-severity: P0
cwe: [CWE-502]
languages: [gdscript]
file-patterns: ["**/*.gd", "**/*.tres", "**/*.res"]
perspectives: [security]
reversibility-check: false
---

# godot-untrusted-resource-deserialization

## Trigger

Code loads a Godot resource (`.tres` or `.res`) or a `PackedScene` from a path that an attacker can control or write to (a downloaded save file, imported user-generated content, a networked payload, anything under `user://`). Godot resource files can embed sub-resources and reference scripts, and the loader instantiates those objects and can run their script code (a `@tool` script, an object whose `_init()` executes, a set script) during load. The result is arbitrary code execution on the player's device, not just corrupted data. This is why the engine documentation states plainly that a `.tres` or `.res` save must never be loaded from an untrusted source (https://docs.godotengine.org/en/stable/tutorials/io/saving_games.html), and why a safe-loader flag was added upstream (https://github.com/godotengine/godot/pull/98168).

## Detection

Look for a load call whose path is untrusted (under `user://`, fetched over the network, imported, or built from user input), especially for save data:

- `ResourceLoader.load("user://savegame.tres")` or `ResourceLoader.load(path)` where `path` points at `user://`, a download, or imported content
- the global `load(path)` on the same kind of runtime path (distinct from `preload`, which is compile-time `res://` only)
- `ResourceLoader.load_threaded_request(path)` followed by `load_threaded_get(path)` on an untrusted path
- `PackedScene` loaded from `user://` or a download, then `.instantiate()` on the result
- any save/import/download routine that round-trips game state through a `.tres` or `.res` file instead of a data-only format

Exclude:
- `preload(...)` and `load("res://...")` of assets bundled in the export; `res://` is read-only and shipped by you, so it is trusted
- `ResourceLoader.load` on a path proven to resolve under `res://`
- reads that parse a data-only format (`JSON.parse_string`, `FileAccess.get_var(...)` written with `full_objects=false`), which do not instantiate scripts
- a documented safe-resource loader that strips scripts and unknown types before instantiating (for example https://github.com/derkork/godot-safe-resource-loader)

## Retrieval

- the function that performs the load and the expression that builds the path argument
- the origin of that path (save-slot routine, download handler, import picker, network message) to decide if it is user-controlled or writable
- the paired write side (what produced the file) to confirm whether it is a resource dump or a data-only serialization
- any existing save-format or safe-loader helper in the project

## Analysis prompt

Given the load call:
1. What is the path source? Is it under `user://`, downloaded, imported, received over the network, or otherwise attacker-writable, versus a `res://` bundled asset?
2. What type is loaded (`.tres`, `.res`, `PackedScene`) and is it instantiated or set as a script anywhere after load?
3. Could a hand-crafted file at that path embed a script or a `@tool` object that runs code during load or instantiation? Trace what executes.
4. Is a data-only path available instead (JSON, or `FileAccess.store_var`/`get_var` with `full_objects=false`), and would it carry the same state?
5. Recommended fix: never load `.tres`/`.res`/`PackedScene` from untrusted input. Serialize save and user-generated data as JSON or as `full_objects=false` binary via `FileAccess.store_var`, or route the load through a safe-resource loader that strips scripts and allowlists types. Validate and version the payload on read.

## Severity rubric

- P0: a `.tres`, `.res`, or `PackedScene` is loaded from `user://`, a downloaded file, a network payload, or user-generated content (arbitrary code execution; always P0 for this class)
- P1: the loaded path is user-writable but currently reached only by trusted flows, where one refactor would expose it to attacker input
- P2: the pattern is present but the path provably resolves under `res://` bundled content; note it so a later change to the source does not silently make it exploitable

## Confidence factors

- HIGH: `ResourceLoader.load` / `load` / `load_threaded_request` on a literal `user://` path or one built from downloaded or network content, especially a save or import routine
- MEDIUM: the path variable's origin is indirect but flows from a save, download, or import helper, and the loaded value is instantiated or scripted
- LOW: the path could be `res://` through a helper, but the loader is generic enough that a future untrusted source would run scripts

## Examples

### Positive (the bug)

```gdscript
# user:// is player-writable; a crafted savegame.tres can embed a script
# that runs on load. This is remote code execution, not a bad-save error.
func load_game() -> SaveData:
    return ResourceLoader.load("user://savegame.tres") as SaveData
```

### Negative (safe)

```gdscript
# Data-only JSON: parsing never instantiates a script.
# FileAccess and JSON.parse_string are Godot 4.x; Godot 3 used File and JSON.parse.
func load_game() -> Dictionary:
    var f := FileAccess.open("user://save.json", FileAccess.READ)
    if f == null:
        return {}
    var parsed: Variant = JSON.parse_string(f.get_as_text())
    return parsed if parsed is Dictionary else {}
```
