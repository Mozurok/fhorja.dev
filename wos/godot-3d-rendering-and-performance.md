---
activation: model_decision
description: Mechanism knowledge for 3D rendering and performance in Godot 4.x (the three renderer tiers and what each drops, the four limitation classes that persist regardless of tier, and the nine optimization techniques); load when planning or profiling a Godot 3D project on desktop or mobile.
---

# wos/godot-3d-rendering-and-performance

This topic grounds the how of 3D rendering and performance in Godot 4.x. The first thing a 3D project decides is which of three renderers it targets, because the tiers differ by removed features rather than by speed alone: a feature written against Forward+ is not portable downward by default. After that, four limitation classes bite regardless of tier, and nine documented techniques are the levers. Cite it while choosing a tier or reading a profile; it explains mechanisms and does not decide anything or set a number. `performance-budget` declares the numeric budget; this topic carries the mechanism behind those numbers. The 2D counterpart is `wos/godot-2d-mobile-rendering-performance.md`, which owns the 2D batching, `Engine.max_fps`, and thermal caps; the frame-rate and battery caps there are dimension-neutral and are not restated here.

## The three renderer tiers

Renderer choice is a capability decision, not a quality slider. https://docs.godotengine.org/en/stable/tutorials/rendering/renderers.html

- **Forward+** is the most advanced and is the default on desktop.
- **Mobile** targets, in the documentation's own words, "newer mobile devices, desktop XR, standalone XR, or desktop". It drops volumetric fog, screen-space reflections, SDFGI, and TAA.
- **Compatibility** uses OpenGL and is "the least advanced renderer, suited for low-end desktop and mobile platforms". It is the only renderer available on web. On top of the Mobile gaps it also drops VoxelGI, SSIL, compute shaders, decals, and particle trails.
- Neither Mobile nor Compatibility can access `RenderingDevice`. Anything built on it is a Forward+-only path.

Two consequences worth planning around rather than discovering:

- A 3D feature authored against Forward+ has no automatic fallback on Mobile or Compatibility. The feature is absent, not degraded, so the plan states its tier before the scene is built. This is why `godot-scene-plan` treats a 3D scene plan without a declared renderer tier as incomplete.
- The iOS simulator supports only the Compatibility renderer. https://docs.godotengine.org/en/stable/tutorials/export/exporting_for_ios.html A 3D scene verified in the simulator is therefore not evidence for the tier the shipped build uses; that check belongs on a device.

## The four limitation classes

These persist regardless of tier and regardless of engine version. https://docs.godotengine.org/en/stable/tutorials/3d/3d_rendering_limitations.html

- **Texture size.** "Mobile GPUs are typically limited to 4096x4096 textures." A source asset above that ceiling is a mobile-target defect at import time, not at runtime.
- **Color banding.** Compatibility carries the lowest color precision of all rendering methods, so gradients and dark scenes band worst exactly on the tier chosen for reach.
- **Depth buffer precision.** Wide near-to-far ranges lose precision and produce z-fighting; the lever is tightening the camera's near and far planes, not adding geometry.
- **Transparency sorting.** "Transparent objects are sorted back to front before being drawn based on the Node3D's position, not the vertex position in world space." This is the class most worth naming explicitly: it is a correctness-shaped defect with no platform fix, it has no 2D analogue, and it presents as art looking wrong rather than as an error. A large or elongated transparent mesh whose origin sits far from its visible surface will sort against expectation.

## The nine optimization techniques

The documented technique set, in the order the source presents it. https://docs.godotengine.org/en/stable/tutorials/performance/optimizing_3d_performance.html

1. Culling: view frustum (automatic) and occlusion.
2. Transparent object management. "Transparent objects are rendered from back to front to make blending with what is behind work. As a result, try to use as few transparent objects as possible."
3. Level of detail (LOD).
4. Billboards and imposters.
5. Automatic instancing. Note the tier interaction: this is a Forward+ feature and is unavailable on Mobile.
6. Manual instancing via MultiMesh. "MultiMesh allows the drawing of many thousands of objects at very little performance cost, making it ideal for flocks, grass, particles." The 2D sibling `MultiMeshInstance2D` carries the same tradeoff, documented in `wos/godot-2d-mobile-rendering-performance.md`: no per-instance culling and no per-instance scripts.
7. Baked lighting. "Consider using baked lighting, especially for mobile. This can look fantastic, but has the downside that it will not be dynamic." The source also warns that realtime lighting and shadows may simply be too much for lower power mobile devices.
8. Animation and skinning optimization.
9. Large world management.

Four of these (LOD, occlusion culling, baked lighting, MultiMesh) have no equivalent in the 2D performance topic. That gap is the substantive reason a 3D project needs this file rather than a mode on the 2D one.

## What this topic cannot tell you

Stated plainly so an absent number is not mistaken for an unstated default.

- **There are no numeric 3D budgets here.** No captured source gives a frame-time, draw-call, triangle-count, or memory threshold per renderer tier. `performance-budget` marks every device-specific 3D number `PROPOSED-pending-baseline` for exactly this reason, and the only way to replace a proposed number is a measurement on a representative device.
- **Mitigation mechanics for the four limitation classes are not documented in the captured set.** The classes are named; the specific project settings and node properties that mitigate each are not. Treat a mitigation you have not read in the engine docs as unverified.
- **The renderer-selection project-setting path is not captured.** The three tiers and their targets are documented; the setting that switches between them was not in the captured content.
- **Desktop export is uncaptured.** No source in the set covers Windows, macOS, or Linux export, so this topic says nothing about the desktop ship path even though desktop is where Forward+ is the default.

## Measuring

The 2D topic's measuring discipline applies unchanged and is not restated: profile a release export on a representative device, read the in-engine monitors before changing anything, and measure a sustained session so thermal throttling shows up. See `wos/godot-2d-mobile-rendering-performance.md` `## Measuring`. The 3D-specific addition is that the renderer tier is part of the measurement's identity: a profile taken under Forward+ says nothing about the same scene under Mobile, because the feature set differs rather than the speed.
