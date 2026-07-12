---
activation: model_decision
description: Godot 4.x 2D mobile asset pipeline (import settings, texture filtering and compression, atlases and sprite sheets, AnimatedSprite2D vs AnimationPlayer, the placeholder-to-final swap policy, sourcing and licensing hygiene). Load when planning or auditing the art and asset layer of a 2D mobile game.
---

# wos/godot-2d-asset-pipeline

How a Godot 4.x 2D mobile game gets art in, keeps it crisp and cheap, and swaps placeholders for final assets without churn. This topic exists because the dogfood behind ADR-0084 shipped with no art at all (the default icon only) and locked "random colors as placeholder, no assets yet" as a decision, with nothing in the flow covering how real assets would later land. Load this when `godot-scene-plan` enumerates the resources and sub-scenes a feature needs, when auditing why sprites look blurry or a build is heavy, or when deciding the placeholder-asset policy ADR-0084 requires. This is a reference to cite for concrete settings and known traps, not a decision engine; the routing and the decisions stay in the commands.

## The forcing rule (ADR-0084)

Placeholders are a decision, not a drift. When a game ships or plans with placeholder art (colored rectangles, programmer sprites), that is a recorded placeholder-asset policy in `DECISIONS.md`: what is placeholder, what "final" means, and the swap trigger (a milestone, an art delivery). This keeps "we will add art later" from becoming a silent permanent state, and it lets the swap be a clean slice rather than a scattered hunt. A placeholder with no recorded policy is the failure mode; the policy is the fix.

## Import settings (get these right once)

Godot imports every source file into its own `.import` sidecar; the source plus the sidecar are what you commit, and the `.godot/imported/` cache is regenerated (gitignore it). https://docs.godotengine.org/en/stable/tutorials/assets_pipeline/import_process.html

- Texture filter drives the whole art style. Pixel art: set filtering to Nearest (in the import preset or per-texture) so it stays crisp instead of blurring; smooth art: keep Linear. Setting this per-project default in the import defaults saves re-doing it per file. https://docs.godotengine.org/en/stable/tutorials/2d/2d_sprite_animation.html
- On mobile, prefer VRAM-compressed textures for large images to cut memory and bandwidth, and lossless for small UI and pixel art where compression artifacts show. The compression mode is an import setting, not a runtime one. https://docs.godotengine.org/en/stable/tutorials/assets_pipeline/importing_images.html
- Keep source art at the resolution you display; importing a 4K sprite to draw it at 128px wastes memory. Resolution independence comes from the stretch mode and the camera, not from oversized textures (see `wos/godot-2d-mobile-rendering-performance.md`).

## Atlases and sprite sheets (draw-call and memory economy)

- Pack many small sprites into one texture atlas so they share a texture and batch into fewer draw calls; a screen of individually-loaded PNGs is both more draw calls and more texture-switch overhead. Use `AtlasTexture` regions, or a build-time packer. https://docs.godotengine.org/en/stable/classes/class_atlastexture.html
- For frame-by-frame animation, a `SpriteFrames` resource slices a sprite sheet into named animations for `AnimatedSprite2D`. https://docs.godotengine.org/en/stable/classes/class_spriteframes.html
- Import third-party sheets and skeletal animation (Aseprite, TexturePacker, Spine) through their vetted importers rather than hand-slicing; note the importer as a project dependency.

## Animating sprites: which node

- `AnimatedSprite2D` for straightforward frame-by-frame sprite animation driven by a `SpriteFrames` resource; simplest for a character with a few looping states. https://docs.godotengine.org/en/stable/tutorials/2d/2d_sprite_animation.html
- `AnimationPlayer` (or `AnimationTree`) when the animation drives more than frames: position, modulate, scale, calling methods, emitting signals, or blending states. It is the general animation node; reach for it when frame-flipping is not enough. https://docs.godotengine.org/en/stable/tutorials/animation/introduction.html
- For simple, code-driven motion (a tween on scale or modulate for juice), a `Tween` is lighter than an `AnimationPlayer` track; see the feedback layer in `wos/godot-mobile-interaction-and-feel.md`.

## Placeholder-to-final swap (make it a clean slice)

- Keep placeholders behind the same node and scene structure the final asset will use: a `Sprite2D` (or `AnimatedSprite2D`) whose texture is a `ColorRect`, or a flat-fill `GradientTexture2D`/`ImageTexture`, swaps to the real texture by changing one resource, not by restructuring the scene. `PlaceholderTexture2D` is not this: in the real Godot 4 API it is a non-rendering, lazy/deferred-load stand-in (it reserves a declared size and draws nothing), not a visible flat-fill placeholder, so a sprite textured with it renders invisible. Confirm the class's actual rendering behavior against the project's real Godot version before relying on it for anything meant to be seen.
- Address art through named resources or an exported `Texture2D` on the scene, not hard-coded `load()` paths scattered through logic, so the swap is one edit per asset.
- The swap is a planned slice (the policy's trigger fired), tracked like any other, not an ad-hoc find-and-replace.

## Sourcing and licensing hygiene

- Record the source and license of every third-party asset (CC0, CC-BY with attribution required, a purchased license). A game that ships art it cannot legally distribute is a real defect, not a polish item. Keep an asset-credits list from the first imported asset.
- Prefer CC0 or clearly-licensed packs for placeholders so a placeholder never quietly becomes a licensing liability if it survives to release.
- AI-generated art carries its own license and provenance questions; treat it as a decision to record, not a default.

## Handoff to the commands

`godot-scene-plan` lists the resources and sub-scenes a feature needs (its Step 6) and records the placeholder-asset policy. Import-setting and atlas choices are engine facts to cite here; the rendering-cost side (draw calls, texture memory budgets) lives in `wos/godot-2d-mobile-rendering-performance.md` and defers device numbers to `performance-budget`. Class availability and import-preset details vary by Godot version; flag an emitted setting against the project's actual version rather than assuming.
