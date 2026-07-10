---
activation: model_decision
description: Godot 4.x 2D scene architecture (scene independence, autoload vs shared Resource, the sparing signal bus, save systems) plus the mobile auto-save-on-pause trigger. Load when planning or reviewing a 2D-mobile Godot project's structure or save layer.
---

# wos/godot-2d-architecture.md

Lazy reference for how a Godot 4.x 2D-mobile project is structured and how it persists state. Load this when `godot-scene-plan` is about to lay out the node tree, autoloads, signals, and save schema, or when reviewing a slice that touches global state, saving, or the app's background behavior. It grounds the plan in real Godot 4 API so the model does not fall back to training defaults or Godot 3 names. This is a reference to cite, not a decision engine: the per-task choice and its rationale still live in DECISIONS.md. GDScript is the default here; Godot 3 API differences are flagged inline. This topic owns the mobile save-on-pause trigger; nothing else in the cluster should redocument it.

## Scene independence

Godot's structural rule is that each scene is self-contained and communicates by "call down, signal up." A node may call methods on the children it owns, and a child raises a signal instead of reaching up to its parent, so the child stays reusable in another tree. https://docs.godotengine.org/en/stable/tutorials/best_practices/scene_organization.html

The removal test decides parent versus sibling: if a node cannot exist without another, the dependency is a parent-child relationship and the parent owns it; if two nodes could each stand alone, they are siblings and must not reference each other directly. An ancestor mediates between siblings; siblings never reach across the tree with `get_node("../Sibling")`.

Five ways to keep scenes decoupled, from tightest-owned to most distant:

- Call down: a parent calls methods on children it directly owns. Ownership is explicit, so this coupling is acceptable.
- Signal up: a child emits a signal; the parent or an ancestor connects and reacts. The child never names its parent.
- Exported dependency: assign a collaborator through an exported `NodePath` or `Node` set in the inspector rather than a hardcoded relative path that breaks when the tree moves.
- Groups: use `add_to_group` and `get_tree().call_group` for one-to-many messaging where the sender needs no direct reference.
- Shared Resource or signal bus: for distant or runtime-instanced nodes that cannot see each other, route through a shared Resource (see below) or a thin signal-bus autoload, used sparingly.

Signal hygiene keeps the decoupling from leaking: connect in code, keep a 1:1 connect-to-disconnect ratio, and disconnect in `_exit_tree` so a freed scene leaves no ghost connection that double-fires later. https://blog.febucci.com/2024/12/godot-signals-architecture/

## Autoloads and global state

An autoload (singleton) is a node that lives at the root for the whole session. Reserve it for isolated global systems that own their own data: score, inventory, scene switching, an audio bus manager. Do not use it as a dump for cross-cutting logic. https://docs.godotengine.org/en/stable/tutorials/scripting/singletons_autoload.html

- Never `free()` or `queue_free()` an autoload. Removing the singleton node crashes the engine. https://docs.godotengine.org/en/stable/tutorials/scripting/singletons_autoload.html
- A signal-bus autoload (often named `Events`) that only declares and emits signals connects distant or runtime-spawned nodes. Use it sparingly. It bundles unrelated signals in one file and forces a whole-codebase search to trace who listens, which trades away the traceability that direct connections give. https://www.gdquest.com/tutorial/godot/design-patterns/event-bus-singleton/
- Prefer a shared Resource over an autoload when the state needs both a current value and a change notification. A Resource that emits its own `changed` signal lets a node spawned later read the current value and then subscribe, which a fire-and-forget signal bus cannot do. https://blog.febucci.com/2024/12/godot-signals-architecture/

Decision shorthand: autoload for global behavior and systems, shared Resource for observable state a late node must read and watch, signal bus only for genuinely distant nodes.

## Save and cross-scene state

Write saves to `user://`, never `res://`. The project path is read-only in an exported build, so a write to `res://` that works in the editor fails on device. Open with `FileAccess.open(path, FileAccess.WRITE)` and read back with `FileAccess.READ`. https://docs.godotengine.org/en/stable/tutorials/io/saving_games.html

Choose the serialization deliberately, because each choice carries a different risk:

- `FileAccess.store_var` and `get_var`: compact binary. Keep the object flag off (`store_var(value, false)` and `get_var(data, false)`) so no Object or script is serialized or instantiated. This is the safe binary default. https://docs.godotengine.org/en/stable/tutorials/io/saving_games.html
- JSON via `JSON.stringify` and `JSON.parse_string`: human-readable and diffable, but engine types like `Vector2` and `Color` are not JSON-native, so encode them manually (store components as plain arrays or numbers) and reconstruct on load. https://docs.godotengine.org/en/stable/tutorials/io/saving_games.html
- The Persist-group pattern: put savable nodes in a `Persist` group, give each a `save()` method returning a dictionary, and iterate the group on save. Keep Persist nodes non-nested so load-time instantiation order stays simple. https://docs.godotengine.org/en/stable/tutorials/io/saving_games.html

Security boundary: never load a `.tres` or `.res` save from an untrusted source. `ResourceLoader.load` on a resource file can run scripts embedded in that file at load time, which is arbitrary code execution (CWE-502). Treat any save a player can edit, share, or sync from the cloud as untrusted. Godot's safe-resource loading option and the `godot-safe-resource-loader` addon exist for exactly this case; for player-facing saves prefer `store_var` with objects off or JSON. https://github.com/godotengine/godot/pull/98168 , https://github.com/derkork/godot-safe-resource-loader

Stamp a schema version field in every save so an old file migrates instead of crashing on a field that moved. For state that must survive a scene change, hold it in an autoload or a shared Resource, not in the scene being freed; a shared Resource with a `changed` signal lets the incoming scene read the value and subscribe.

## Mobile lifecycle

Godot delivers app lifecycle through node notifications handled in `_notification(what)`. On Android and iOS, sending the app to the background delivers `NOTIFICATION_APPLICATION_PAUSED`; returning delivers `NOTIFICATION_APPLICATION_RESUMED`. https://docs.godotengine.org/en/stable/tutorials/inputs/handling_quit_requests.html

Auto-save on `NOTIFICATION_APPLICATION_PAUSED`. Once the app is backgrounded, the OS can terminate it without any further callback, and the suspend window is only about 5 seconds, so the save must be fast and synchronous: a small payload, no `await`, written before the handler returns. Save on pause rather than on quit, because a swiped-away or OS-killed mobile app may never deliver a close or quit notification at all. https://docs.godotengine.org/en/stable/tutorials/inputs/handling_quit_requests.html

- Godot 3 flag: these constants were `NOTIFICATION_APP_PAUSED` and `NOTIFICATION_APP_RESUMED` in Godot 3. Godot 4 renamed them to `NOTIFICATION_APPLICATION_PAUSED` and `NOTIFICATION_APPLICATION_RESUMED`. Do not plan against the Godot 3 names.
- Desktop analog: intercept the window close with `NOTIFICATION_WM_CLOSE_REQUEST` after `get_tree().set_auto_accept_quit(false)`. The mobile pause path and the desktop close path are separate; wire both if you ship both. The Android back button arrives as `NOTIFICATION_WM_GO_BACK_REQUEST`. https://docs.godotengine.org/en/stable/tutorials/inputs/handling_quit_requests.html
- Scope note: this topic owns save-on-pause only. The `max_fps` and vsync battery caps live in the performance topic; haptic amplitude and audio latency live in the interaction-and-feel topic. Do not duplicate those here.

## When this grounds a command

- `godot-scene-plan`: load this before laying out the node tree so the plan cites real Godot 4 API for autoloads, signals, and the exported-dependency and group patterns. Its save-state fold should take the `user://` path rule, the serialization choice, the untrusted-resource boundary, and the save-on-pause trigger straight from the Save and Mobile lifecycle sections rather than inventing a save schema.
- Cross-links: `wos/godot-2d-mobile-performance.md` owns rendering, `max_fps`, and the battery and thermal caps; `wos/godot-mobile-interaction-and-feel.md` owns touch input, haptics, and juice. The save-on-pause trigger stays here and only here.
- This is a reference to cite, not a rule to apply blindly. Name the pattern in DECISIONS.md and record why the task chose it.
