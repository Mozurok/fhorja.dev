---
activation: model_decision
description: Mechanism knowledge for sourcing and importing 3D assets in a Godot 4.x project (the CC0 source set and their license terms, the glTF and Blend import path, and the texture and poly-count constraints the renderer tiers impose); load when planning a 3D project's art supply or its import step.
---

# wos/godot-3d-asset-pipeline

This topic grounds where 3D assets come from and what constrains them on the way in. Two things make it distinct from the 2D pipeline: the license question has a clean answer that a workflow can act on, and the import formats are engine-level rather than image-level. It is a reference for planning an art supply, not a tutorial and not an endorsement of any one vendor. The 2D counterpart is `wos/godot-2d-asset-pipeline.md`; anything dimension-neutral there (the placeholder-asset policy, the import-then-commit discipline) applies unchanged and is not restated.

## The license question, and why it has a clean answer

For a project distributed under a permissive license, CC0 is the term that matters, because it adds no obligation on top of what the project already carries. It is not merely "free to use": it waives attribution.

- **Poly Haven** publishes 3D models, textures, and HDRIs under CC0. "You can use our assets for any purpose, including commercial work" and "You do not need to give credit or attribution when using them (although it is appreciated)." Redistribution inside a shipped product is explicitly permitted, which is the term that lets a build or a demo repository carry the assets rather than only linking them. https://polyhaven.com/license
- **Quaternius** publishes low-poly model packs under "Creative Commons Zero v1.0 Universal", stated as "Free to use in any project, even commercially! (CC0)". A single pack supplies over 100 models plus an animated character with 18 animations. https://quaternius.itch.io/ultimate-platformer-pack
- **A curated CC0 index** lists Poly Haven, Kenney.nl, and Quaternius as 3D model sources and ambientCG, Texture Ninja, and Wikimedia Commons as texture sources, stating the premise independently of any one publisher: "CC0 = No copyright, 100% free to use for any purpose even commercially." https://github.com/madjin/awesome-cc0

Two operational rules follow from the sources themselves:

- **Acquisition stays a human or documented-link step.** Poly Haven's CC0 grant covers the assets only; its terms of service separately prohibit scraping and data mining without permission. An automated fetch is therefore out of bounds even though the assets are public domain.
- **Verify per source, not per site class.** The CC0 claim above is per-publisher and was read on each publisher's own page. A site being listed on an index is not itself a license.

## Style coverage

The supply is not locked to one look, which matters when a project's art direction is decided after the asset source.

- Stylised low-poly is covered by Quaternius, whose models arrive rigged and animated.
- Photoreal props, environments, and HDRIs are covered by Poly Haven.
- Textures specifically are covered by ambientCG and Texture Ninja, named on the index above. Their license terms were not read directly and are therefore unverified here; read them before relying on them.

## The import path

- **glTF and Blend are the practical routes into Godot.** The Quaternius packs ship FBX, OBJ, glTF, and Blend, and glTF and Blend are the two named as the Godot import path, so a project on those formats needs no conversion step. https://quaternius.itch.io/ultimate-platformer-pack
- **Rigs are engine-portable but unverified.** Quaternius' Universal Animation Library states a universal humanoid rig compatible with Unreal Engine, Godot, and Unity. https://quaternius.com/packs/universalanimationlibrary.html That a rig and its animations import and retarget cleanly in a specific Godot version is a claim no captured source tests; treat it as a thing to verify in the project, not a property to assume.

## Constraints the renderer tier imposes on assets

The asset decision and the renderer decision are not independent. See `wos/godot-3d-rendering-and-performance.md` for the tier definitions.

- **Texture ceiling.** Mobile GPUs are typically limited to 4096x4096 textures, so a source texture above that is a mobile-target defect caught at import, not at runtime. A photoreal source set aimed at desktop will routinely exceed it.
- **LOD is a technique, not an asset property.** The optimization set includes mesh LOD, but whether a downloaded asset ships LOD levels is per-asset and is not stated by any captured source.
- **Poly counts are uncaptured.** No captured source gives poly counts, texture resolutions, LOD levels, or collision-shape data for any asset source. This is the single largest gap in this topic and it is exactly the gap that blocks answering whether a given CC0 pack is mobile-viable. Measure the asset; do not infer it from the source's reputation.

## What this topic cannot tell you

- Whether any specific pack is mobile-viable, for the poly-count reason above.
- Whether a Quaternius rig retargets cleanly in a given Godot version.
- The license terms of ambientCG and Texture Ninja, which are named on an index but were not read at source.
- Anything about CC0 audio, music, or sound effects. No captured source covers non-visual asset supply, so a 3D project's audio supply is unaddressed here. The 2D audio topic `wos/godot-2d-audio.md` covers the engine-side mechanism, which is dimension-neutral, but not the sourcing question.
