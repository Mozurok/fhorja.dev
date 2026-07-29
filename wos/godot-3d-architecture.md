---
activation: model_decision
description: Mechanism knowledge for 3D scene architecture in Godot 4.x (GridMap and MeshLibrary level building, navigation meshes and agents, the physics body taxonomy in its 3D form, and what the 2D architecture topic already covers); load when planning the node structure of a Godot 3D feature.
---

# wos/godot-3d-architecture

This topic grounds the structural decisions a Godot 3D feature makes before any GDScript is written: how a level is built, how agents find their way through it, and which physics body each moving thing is. It is deliberately thin on anything the 2D architecture topic already owns. Scene-tree composition, autoload and singleton discipline, signal wiring, and save state are dimension-neutral, so `wos/godot-2d-architecture.md` remains the source for them and they are not restated here. What follows is what 3D adds. Godot 4.x is assumed.

## Building the level: GridMap and MeshLibrary

The 3D counterpart to the 2D tilemap workflow, and the closest structural analogue a 2D-experienced reader has. https://docs.godotengine.org/en/stable/tutorials/3d/using_gridmaps.html

- "Gridmaps are a tool for creating 3D game levels, similar to the way TileMap works in 2D."
- The unit of content is a **MeshLibrary**, authored as an ordinary scene of `MeshInstance3D` nodes with optional collision shapes and navigation data, then exported as a resource. A `GridMap` node is assigned that library and painted with the editor panel's Paint, Selection, Erase, Fill, Move, and Duplicate tools.
- Scope it correctly: "GridMap is not a general-purpose system for placing nodes on a grid, but rather a specific, optimized system, designed to place meshes with collisions and navigation." Reaching for it to lay out arbitrary nodes on a grid is using the wrong tool.
- Collision shape choice is per-mesh: a convex body suits simple meshes, while complex geometry wants a trimesh static body.
- Import gotcha worth knowing before authoring the library: only the materials inside the meshes carry into the generated MeshLibrary.

## Navigation

Independent of both rendering and physics, which is the first thing to internalize because it means a navmesh can be correct while the agent still does not move. https://docs.godotengine.org/en/stable/tutorials/navigation/navigation_introduction_3d.html

Two systems, chosen by the shape of the level:

- **NavigationServer3D**, mesh-based. "NavigationServer3D provides a powerful server API to find the shortest path between two positions on an area defined by a navigation mesh." It scales to large worlds: "Mesh-based navigation scales well with large game worlds as a large area can often be defined with a single polygon when it would require many, many grid cells."
- **AStar3D**, grid-based, for cell-oriented gameplay with predefined positions.

The helper nodes and what each is actually for:

- `NavigationRegion3D` holds a `NavigationMesh` defining the walkable area. Baking is done in the editor by giving the region child geometry and pressing Bake Navmesh, or at runtime.
- `NavigationAgent3D` performs pathfinding and avoidance. The agent queries the server during `_physics_process()` and moves toward the next waypoint with ordinary physics movement such as `CharacterBody3D.move_and_slide()`. Pathfinding gives you a waypoint, not motion.
- `NavigationLink3D` connects positions across arbitrary distance (a jump, a ladder, a teleport). It declares that a connection exists and its cost; the traversal itself is yours to script.
- `NavigationObstacle3D` constrains agent avoidance only. It does not affect pathfinding; changing the navigation mesh is what does.

One timing trap the source names explicitly: "Wait for the NavigationServer synchronization by awaiting one frame in the script." A path queried in the same frame the region is added is queried against a map that is not yet synchronized. This is the 3D sibling of the one-frame visibility resolution documented for `VisibleOnScreenEnabler2D` in `wos/godot-2d-mobile-rendering-performance.md`, and it fails the same way: silently, with a plausible-looking empty result.

## Physics bodies

The taxonomy is dimension-neutral and the official introduction says so directly: every 2D physics object and collision shape has a direct equivalent in 3D. https://docs.godotengine.org/en/stable/tutorials/physics/physics_introduction.html Choose by control model, not by dimension:

- **Area**: overlap detection and physics-property influence. Trigger volumes, gravity or damping zones.
- **StaticBody**: immobile environment. Does not move from collisions but can impart motion to what touches it.
- **RigidBody**: full simulation from applied forces. The engine owns its movement; you do not set its position directly.
- **CharacterBody**: collision-detecting but moved by your code. Players and enemies that need exact control. This is the body a `NavigationAgent3D` normally drives.

Two rules the source states that are easy to violate in a 3D editor:

- "In order to detect collisions, at least one `Shape2D` must be assigned to the object." The 3D equivalent holds; a body with no shape silently collides with nothing.
- "Be careful to never scale your collision shapes in the editor." Resize with the shape's own size handles, never the node scale handles. In 3D this is easier to do by accident, because scaling a visual mesh to fit a level feels natural and drags the collision shape with it.

Recorded honestly: the page cited above documents the 2D node names and asserts the 3D equivalence rather than listing the 3D names. Treat a specific 3D class name you have not read in the class reference as unverified.

## What this topic deliberately does not cover

- Scene-tree composition, autoloads, signal wiring, and save state. Dimension-neutral; see `wos/godot-2d-architecture.md`.
- Renderer tiers, the limitation classes, and the optimization techniques. See `wos/godot-3d-rendering-and-performance.md`, which also owns the tier declaration that a 3D scene plan must state.
- Asset sourcing and the import path. See `wos/godot-3d-asset-pipeline.md`.
- Camera rigs and follow behavior. No captured source covers them, so nothing is asserted here.
- Lighting and environment baking as an authoring workflow. The performance topic covers baked lighting as an optimization technique; the authoring workflow itself is uncaptured.
