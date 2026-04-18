# Rendering — Design Document

- **Status:** Stub (outline only — content TBD)
- **Owner:** @royceshannon2
- **Parent:** [`MASTER.md`](MASTER.md)
- **Target code home:** `witness-interactive-vite/src/engine/`

The contract for scene construction, lighting, materials, post-processing, and physics. What a "production-quality render" means for this project.

---

## 1. Objective
*(To be written.)*

Describe the visual bar (photoreal, emotionally restrained, documentary rather than cinematic), and the cost bar (60 fps on a mid-range desktop GPU).

## 2. Scope
- **In scope:** PBR material library, lighting rig, post-processing pipeline, Havok physics init, per-era rendering profiles.
- **Out of scope:** Per-location mesh authoring (see `WORLD.md`), UI rendering (see forthcoming `UI.md`).

## 3. Material library
Subsections to fill:
- 3.1 Shared PBR palette: `laterite`, `brick`, `concrete`, `tinRoof`, `eucalyptus`, `matooke`, `cloth{Red,Blue,White}`, `sandbag`, `jerrycan`, etc.
- 3.2 Freeze policy: all library materials frozen at registration.
- 3.3 Variant policy: weathered vs. pristine variants for Chronos Switch — one base material, per-era albedo/roughness override, or separate instances? (Decision TBD — ADR candidate.)
- 3.4 Anisotropic filtering: `16` on ground and architectural textures per `CLAUDE.md`.

## 4. Lighting rig
- 4.1 Sun (DirectionalLight): per era. Past = warm, afternoon, 1994 April. Present = overcast, cool, 2026 April.
- 4.2 Sky (HemisphericLight): muted, per era.
- 4.3 Rim / storm light: narrative-driven accent for specific beats.
- 4.4 Environment texture (`.env`): HDRI per era; Bisesero morning mist vs. overcast afternoon.
- 4.5 Shadow strategy: PCSS, 2048 shadow map on sun, no shadow on sky/rim.

## 5. Post-processing pipeline
Subsections to fill:
- 5.1 Shared stack: ACES tone-mapping, FXAA, SSAO2, sharpen.
- 5.2 Per-era profile:
  - **Present:** desaturation curve, cooler grade, heavier vignette, more grain.
  - **Past:** higher contrast, warmer grade, subtler vignette, moderate grain.
- 5.3 Bloom: emissive-only, threshold high, scale low.
- 5.4 Transition crossfade: two pipelines blended for 1.2s on era switch.

## 6. Physics (Havok)
- 6.1 Init sequence: `HavokPhysics()` awaited before scene creation.
- 6.2 Gravity: `(0, -9.81, 0)`. No fudge factors.
- 6.3 Aggregate usage: `PhysicsAggregate` for interactive props only. Terrain uses a collision mesh, not physics.
- 6.4 Performance budget: max N active aggregates per frame (N TBD).

## 7. Performance budget
- Target: 60 fps at 1080p on a mid-range desktop GPU (e.g., RTX 3060).
- Drawcall budget: *(TBD)*.
- Triangle budget per location: *(TBD)*.
- Shadow-casting mesh count: *(TBD)*.
- LOD distances: *(TBD)*.

## 8. Trade-offs
- **A. Forward vs. deferred** — Babylon's default is forward; no deferred pipeline planned.
- **B. One pipeline with per-era profile vs. two pipelines crossfaded** — latter is cleaner for transition, but costs VRAM.
- **C. Real-time GI vs. baked lightmaps** — leaning baked for static geometry, real-time for moving elements.

## 9. Failure modes
- WebGL context loss — engine must recover without crashing the scene.
- Shader compilation failure on initial load — fall back to unlit material, log error.
- Frame drops below 30 fps — debug overlay (dev-only) shows which subsystem is over budget.

## 10. Milestones
*(To be written.)*

## 11. Open questions
- Q1: Is HDR output (Display P3, ACES output transform) required, or is sRGB 8-bit sufficient for v1?
- Q2: Do we support MSAA, FXAA, or both? Pipeline fights between them.
- Q3: Screen-space reflections — valuable for the lake? Or too expensive?
