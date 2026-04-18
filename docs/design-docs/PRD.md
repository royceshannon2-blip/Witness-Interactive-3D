PRD: Hyper-Realistic Rwanda 1994 Environment
Product vision
Create a photoreal, historically grounded, interactive Rwanda 1994 scene for cinematic storytelling, educational immersion, or game production. The environment should feel physically real, emotionally restrained, and visually authentic rather than stylized. The AI should generate a production-ready Babylon.js scene, a local asset pipeline, and all supporting code needed to assemble, light, and optimize the world.

Objectives
Build a dense, believable Rwanda landscape with rolling hills, terraced agriculture, red clay roads, banana groves, eucalyptus trees, simple homes, churches, market areas, and Kigali-adjacent urban edges.

Generate and import all 3D assets locally on a high-end GPU workstation using Hunyuan3D 2.1 or equivalent local tooling, then export as GLB/GLTF with PBR textures.

Use Babylon.js PBRMaterial/PBRMetallicRoughnessMaterial for all environment materials, with physically based albedo, roughness, metallic, bump, and environment reflections.

Apply post-processing and lighting that maximize realism: ACES tone mapping, bloom, FXAA or MSAA, SSAO, shadow maps, and an HDR environment texture.

Enable optional Havok physics for physically believable interaction, debris, foliage collisions, object stacking, and trigger zones.

Target outcome
The final product should allow an AI coding agent to generate:

A Babylon.js scene setup.

A local asset generation workflow.

A terrain and biome layout system.

A lighting and post-processing configuration.

A material library for earth, vegetation, roofs, roads, concrete, cloth, wood, and metal.

A physics-ready interaction layer using Havok.

A loading and optimization system for GLB, Draco, and KTX2 assets.

Visual direction
Reference quality
The scene should emulate a high-end film-grade environment with:

Dense atmospheric depth.

Soft morning haze and humid valley light.

Strong contrast between lush hills and dry red soil.

Natural imperfections: uneven roads, weathered walls, patched roofs, broken fences, and hand-built structures.

Subtle storytelling props: bicycles, cooking pots, laundry lines, market goods, water containers, roadside signage, and worn footpaths.

Color palette
Earth reds and umbers for clay paths and exposed soil.

Deep greens for banana leaves, pasture, and hillside vegetation.

Muted whites, grays, and rust tones for masonry, churches, and tin roofs.

Desaturated clothing and weathered surfaces for realism.

Avoid oversaturated tropical postcard colors.

Atmosphere
Early-morning mist in valleys.

Heat shimmer in midday areas.

Light smoke or dust volumes near roads and compounds.

Cloud layers that soften the sun and create broad, diffused lighting.

Scope
In scope
One primary explorable zone, plus distant background terrain.

Terrain, foliage, architecture, roads, props, and atmospheric effects.

Local asset generation and baking pipeline.

High-quality rendering pipeline and camera setup.

Optional physics interactions.

Out of scope
Photographic human likenesses.

Recreating identifiable real-world trauma scenes in a sensational way.

Complex AI NPC simulation for initial release.

Multiplayer systems.

Networked persistence.

Content guidelines
The environment should be historically grounded but not exploitative. Use realism to support context, education, or storytelling, not spectacle. Avoid inserting gratuitous violence into the environment as decoration. If conflict cues are needed, keep them subtle, environmental, and narrative-driven.

Technical requirements
Engine
Babylon.js as the rendering engine.

Babylon GUI only if needed for debug or immersive overlay.

Babylon loaders for GLTF/GLB import.

Rendering
Use PBRMaterial or PBRMetallicRoughnessMaterial for all major surfaces.

Use an HDR environment texture or .env reflection setup.

Enable ACES tone mapping.

Add SSAO for contact depth.

Add bloom sparingly for emissive lights, not for the whole scene.

Enable FXAA/MSAA through DefaultRenderingPipeline.

Physics
Use Havok via Babylon’s HavokPlugin.

Enable gravity and collision bodies for key props, rubble, doors, fences, and interactable objects.

Use physics triggers for gates, doorways, objective zones, and cutscene areas.

Asset generation
Use Hunyuan3D 2.1 locally on the RTX 5090 for mesh generation and PBR texture synthesis.

Bake 8K textures where justified, then downscale adaptively for runtime use.

Export assets as .glb with compressed textures when possible.

Use KTX2 and Draco for runtime efficiency, even if generation speed is not the priority.

Performance strategy
Prioritize visual fidelity over generation speed, but preserve interactive runtime stability.

Use LODs for trees, buildings, and distant props.

Stream distant terrain or reduce far-zone complexity.

Use texture atlases for small props and clutter.

Limit dynamic shadows to key light sources and key set pieces.

World-building requirements
Terrain
Wide rolling hills with steep, layered slopes.

Terracing for agriculture.

Mud tracks and footpaths cutting through fields.

Wet and dry soil variation.

Small drainage channels and erosion marks.

Vegetation
Banana trees, eucalyptus stands, grasses, shrubs, cassava patches, and sparse cultivated plots.

Irregular growth patterns, not uniform scatter.

Regionally plausible density and scale.

Structures
Mud-brick and concrete homes.

Simple church buildings.

Market stalls.

Administrative or roadside structures.

Corrugated metal roofing with rust and dents.

Weathered painted surfaces and patched masonry.

Props
Bicycles.

Water jugs.

Cooking items.

Wooden benches.

Plastic containers.

Cloth lines.

Signs, crates, bags, and farming tools.

AI build instructions
The AI must generate
A Babylon.js project structure.

A scene bootstrap with camera, sky, lighting, post-process, and environment setup.

A terrain system with layered materials and elevation variation.

A local import pipeline for GLB assets.

A local asset generation prompt pack for Hunyuan3D 2.1.

A PBR material library for reusable surfaces.

A physics layer using Havok.

A test harness for visual validation.

The AI should follow these practices
Prefer PBR over StandardMaterial.

Use Babylon’s default rendering pipeline for anti-aliasing, bloom, and image processing.

Add SSAO for depth and realism.

Use glTF/GLB with Draco/KTX2 for high-end asset delivery.

Keep generation local and reproducible on the 5090 workstation.

Deliverables
Code deliverables
scene.ts or scene.js

terrain.ts

materials.ts

physics.ts

assetPipeline.ts

config.json

prompts/ folder for Hunyuan3D generation prompts

Art deliverables
Terrains.

Vegetation sets.

Building kits.

Road and dirt variants.

Market and village props.

Atmospheric textures and HDRI references.

Documentation deliverables
Setup instructions.

Asset naming conventions.

Local generation workflow.

Runtime performance tuning checklist.

Historical authenticity checklist.

Acceptance criteria
Scene loads in Babylon.js without errors.

All major surfaces use PBR-based materials.

At least one SSAO and one default rendering pipeline effect are active.

Assets import successfully as GLB/GLTF.

Physics works with Havok-enabled interaction zones.

Local generation workflow supports Hunyuan3D 2.1 and PBR texture output.

Visual output reads as Rwanda in 1994 through geography, architecture, materials, and atmosphere.

