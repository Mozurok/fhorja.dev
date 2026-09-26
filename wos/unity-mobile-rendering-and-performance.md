---
activation: model_decision
description: Mechanism knowledge for the render-pipeline decision on a Unity mobile 3D target (the three-way choice, HDRP's enumerated platform list and its compute-shader requirement, and why the pipeline is a project-level commitment rather than a setting); load when declaring the render pipeline for a Unity mobile feature.
---

# wos/unity-mobile-rendering-and-performance

Lazy-loaded reference for the render-pipeline declaration a Unity mobile 3D plan must carry (ADR-0132). It exists because the pipeline choice is the Unity analogue of Godot's renderer tier: made once, expensive to reverse, and silently constraining every feature written afterwards.

Scope, stated up front. This topic covers the **pipeline decision** and nothing else. Numeric mobile budgets (draw calls, triangle counts, texture memory, frame time), the SRP Batcher and GPU instancing, texture compression, shader variant stripping, Addressables lifecycle, and Adaptive Performance thermal handling are **absent**, because no source for them was captured. `performance-budget` owns numeric budgets in any case; route the mechanism content to `capture-references` before writing it here. An absent section is not an implied default.

## The choice is three-way and it is project-level

Unity's own characterisations (https://docs.unity3d.com/Manual/render-pipelines-overview.html):

- **Universal Render Pipeline (URP)**: "a Scriptable Render Pipeline that you can customize. It lets you create scalable graphics across a wide range of platforms."
- **High Definition Render Pipeline (HDRP)**: "lets you create cutting-edge, high-fidelity graphics on high-end platforms."
- **Built-In Render Pipeline**: "a general purpose render pipeline with limited options for customization."

A project uses one. They are not interchangeable, and a feature authored against one is not portable to another by default. That is what makes this a plan-time declaration rather than a settings toggle.

## What actually rules HDRP out for mobile, stated precisely

This is worth getting exactly right, because the imprecise version of it is easy to repeat and wrong in a way that matters.

HDRP's documentation (https://docs.unity3d.com/Packages/com.unity.render-pipelines.high-definition@17.6/manual/System-Requirements.html) enumerates its supported platforms: Windows and Windows Store with DirectX 11 or 12 and Shader Model 5.0; PlayStation 4 and PlayStation 5; Xbox One and Xbox Series X and S; "MacOS (minimum version 10.13) using Metal graphics"; and Linux and Windows with Vulkan.

**iOS and Android do not appear in that list.** The page never states "HDRP does not support mobile"; it enumerates what it does support, and mobile is absent from the enumeration.

Two mechanism-level requirements sit on top:

- "HDRP only works on these platforms if the device you use supports Compute Shaders."
- "HDRP doesn't support OpenGL or OpenGL ES devices."

Reason from those two sentences and the platform list, not from a blanket claim. The distinction is practical: the constraint is a graphics-API and compute-capability question, so it is checkable against a specific target rather than assumed from the word "mobile".

**What the Unity documentation does NOT say, and this topic will not say for it:** the overview page makes no explicit "use URP for mobile" recommendation. It says URP scales across a wide range of platforms and HDRP targets high-end ones, and routes the selection question to a separate page not captured here. So the honest form of the guidance is: URP is the pipeline whose stated scope covers a wide platform range, and HDRP's enumerated platform list excludes mobile. A plan choosing URP for a mobile target is well-founded; a plan asserting that Unity recommends it is citing something no captured page says.

## The declaration a mobile 3D plan carries

`unity-scene-plan` requires a declared pipeline for a 3D target, mirroring the Godot renderer-tier declaration (ADR-0117 D-9, hardened by ADR-0118 and ADR-0119). The mirror is at plan time only: since ADR-0209 the Godot closure floor records a missing declaration rather than blocking, and this Unity rule has no closure floor at all; a 3D plan without it is incomplete output of `unity-scene-plan`. The declaration states:

1. **The pipeline**: URP, HDRP, or Built-in (deprecated, supported through Unity 6.7 LTS; https://docs.unity3d.com/6000.5/Documentation/Manual/built-in-render-pipeline.html).
2. **The target graphics API** on each shipping platform, because HDRP's constraint is expressed in those terms (compute shader support; not OpenGL or OpenGL ES).
3. **Why**, in one line, when the choice is anything other than URP on a mobile target, since that is the case where the platform list argues against it.

A 3D plan with no declared pipeline is incomplete, for the same reason a Godot 3D plan with no renderer tier is: a feature authored against the wrong one is not portable, and nothing at build time says so early.

## Deliberately absent

Named so absence is not mistaken for coverage. Each is routed to `capture-references` before anyone writes it:

- Numeric mobile budgets of any kind. `performance-budget` owns these, and no captured source supplies a Unity mobile figure, so any number written today would be invented.
- SRP Batcher, GPU instancing, static and dynamic batching.
- Texture compression (ASTC and alternatives) and the texture memory ceiling.
- Shader variant stripping and its build-size effect.
- Addressables runtime lifecycle, including the reference-count double-release failure mode.
- Adaptive Performance and thermal throttling, which the research round called the sharpest asymmetry against Godot's static frame cap.
