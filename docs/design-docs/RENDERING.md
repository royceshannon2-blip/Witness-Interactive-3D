# Rendering — Design Document

- **Status:** Draft (§1–§11 filled 2026-04-18)
- **Owner:** @royceshannon2
- **Parent:** [`MASTER.md`](MASTER.md)
- **Target code home:** `witness-interactive-vite/src/engine/`
- **Related:** [`CHRONOS_SWITCH.md §3.4–§3.6`](CHRONOS_SWITCH.md#34-post-fx-profiles-per-era) — per-era pipeline blending. [`ASSET_PIPELINE.md`](ASSET_PIPELINE.md) — texture delivery format. [`AUDIO_ARCHITECTURE.md`](AUDIO_ARCHITECTURE.md) — transition audio cadence.

The contract for scene construction, lighting, materials, post-processing, and physics. Defines what "production-quality render" means for *this* project — a photoreal but emotionally restrained documentary register, not a film-grade spectacle.

---

## 1. Objective

Two bars, simultaneously held:

**Visual bar — documentary realism, not cinema.**
- Photoreal PBR materials, historically accurate (laterite, mud brick, tin roof, eucalyptus).
- Lighting: plausible April Bisesero — direct afternoon sun for 1994, overcast morning for 2026. No "movie lighting" (no golden-hour every shot, no fill from nowhere).
- Post: subtle grade, sparing bloom, soft grain. The image should read as "a camera was here, once," not "this was color-timed in Resolve."
- Restraint per PRD: no decorative violence, no horror-movie color grading, no spectacle-bloom on fire or blood.

**Performance bar — 60 fps at 1080p on a mid-range desktop (RTX 3060 / RX 6700 or better).**
- Draw call budget: ≤ 1500 per frame (§7).
- Shadow-casting meshes: ≤ 150 per frame.
- LOD tiers: 3 per authored asset.

These are not aspirational. They constrain all downstream decisions (asset count, material variant count, shadow map resolution).

---

## 2. Scope

- **In scope:** PBR material library, per-era lighting rig, post-processing pipeline (shared + per-era profiles), Havok physics initialization, LOD strategy, performance budgets.
- **Out of scope:** Per-location mesh authoring (see [`WORLD.md`](WORLD.md)), asset generation and compression (see [`ASSET_PIPELINE.md`](ASSET_PIPELINE.md)), UI rendering (investigator's interface, ledger UI — future `UI.md`), per-era visibility gating (see [`CHRONOS_SWITCH.md §3.2`](CHRONOS_SWITCH.md#32-layer-masks)).

---

## 3. Material library

### 3.1 Shared PBR palette

All environment surfaces use `PBRMaterial`. No `StandardMaterial`. The library is flat (no inheritance), shared (each material is a single JS object, instanced via `freeze()` and `clone()` for tint variants only).

Registered at scene init in `engine/Materials.ts`:

| ID | Surface | Base color | Roughness | Metallic | Normal | Notes |
|---|---|---|---|---|---|---|
| `mat_laterite` | Red-clay path, eroded soil | albedo 8K | 0.85 | 0.0 | high freq | wet-dry variants via roughness bake |
| `mat_brick_mud` | Mud-brick wall (rugo) | albedo 4K | 0.9 | 0.0 | medium | two tonal variants |
| `mat_brick_fired` | Fired brick (later builds) | albedo 4K | 0.75 | 0.0 | low | cement-mortar variant |
| `mat_concrete_weathered` | Church, administrative walls | albedo 4K | 0.8 | 0.0 | low | moss variant for 2026 |
| `mat_tin_roof` | Corrugated sheet, rust patches | albedo 4K | 0.6 (dented), 0.45 (smooth) | 0.8 | high | three rust densities |
| `mat_eucalyptus_bark` | Tree trunks | albedo 4K | 0.85 | 0.0 | high |  |
| `mat_eucalyptus_leaf` | Canopy cards | albedo+opacity 2K | 0.7 | 0.0 | baked from geometry | subsurface approx via vertex color |
| `mat_matooke_leaf` | Banana leaves | albedo+opacity 2K | 0.7 | 0.0 | baked from geometry | sheen via anisotropy=0.3 |
| `mat_grass_tall` | Elephant grass | cards 1K | 0.75 | 0.0 | baked from geometry | wind vertex anim |
| `mat_cloth_white` | Laundry, scarves | albedo 1K | 0.9 | 0.0 | weave normal | dirty/clean variants |
| `mat_cloth_kitenge` | Traditional print | albedo 2K | 0.85 | 0.0 | weave normal | three print variants |
| `mat_wood_weathered` | Dock, doors, benches | albedo 2K | 0.85 | 0.0 | medium | split-grain variant |
| `mat_metal_jerrycan` | Plastic jerrycan (read as metal due to sheen) | albedo 1K | 0.4 | 0.1 | smooth | faded yellow variant |
| `mat_water_lake` | Lake Kivu surface | procedural node material | animated | 0.0 | dual-normal scroll | calm / mist variants |

All materials have: `albedoTexture`, `metallicRoughnessTexture` (channel-packed: R=unused, G=roughness, B=metallic), `bumpTexture`. Ambient occlusion is baked into albedo at authoring time. `ambientTextureStrength = 1.0`.

### 3.2 Freeze policy

All library materials are frozen at registration (`material.freeze()`) before the first frame. Cloning for tint or era variants happens at location load time, never per-frame. Frozen materials skip uniform re-upload and are required for `ThinInstance` rendering.

If a variant needs to mutate a uniform at runtime (rare — mostly water), the material is not frozen but is flagged as `freezeActiveMeshes = false` on the mesh side.

### 3.3 Variant policy (Chronos Switch)

One base material, separate cloned instances per era. The 2026 variant has moss/wet/decay overlay baked into its albedo and roughness. The 1994 variant is the pristine version.

Alternative rejected: shader-driven era blend via a uniform. Rejected because (a) the blend would only animate during the ≤ 2 s transition window — not worth a permanently more expensive shader, (b) the 2026 and 1994 albedos are not linear interpolations of each other (moss is not "a bit green-er" than clean brick; it's a different BRDF contribution).

ADR candidate: this decision is simple enough that it may never need an ADR, but if the variant count explodes we revisit.

### 3.4 Anisotropic filtering

`anisotropicFilteringLevel = 16` on:
- Ground textures (`mat_laterite`, `mat_grass_tall`).
- Architectural façades (`mat_brick_*`, `mat_concrete_weathered`, `mat_tin_roof`) at grazing viewing angles.

Default `4` elsewhere. Per `CLAUDE.md` project rule.

---

## 4. Lighting rig

One rig per era. Lights are duplicated, not animated. See [`CHRONOS_SWITCH.md §3.5`](CHRONOS_SWITCH.md#35-lighting-strategy) for why. All lights are tagged via `tagLight(light, scope)` from `src/core/LayerMasks.ts`.

### 4.1 Sun (DirectionalLight)

**Present (2026):**
- Direction: `(-0.4, -0.9, -0.15)` — mid-morning, slightly west of overhead, overcast.
- Color: `Color3.FromHSV(210, 0.08, 0.95)` — cool gray-blue.
- Intensity: `0.6`.
- Specular: `0.2` — dimmed; overcast skies have diffuse specular.

**Past (1994, June afternoon):**
- Direction: `(-0.7, -0.55, -0.45)` — afternoon, declining west.
- Color: `Color3.FromHSV(35, 0.25, 1.0)` — warm amber.
- Intensity: `1.4`.
- Specular: `1.0`.

Both cast shadows via a single `ShadowGenerator` per light; see §4.5.

### 4.2 Sky (HemisphericLight)

Fills the shadowed side. Tinted toward the ground.

**Present:** color `Color3(0.45, 0.5, 0.55)`, groundColor `Color3(0.3, 0.28, 0.25)`, intensity `0.4`.
**Past:** color `Color3(0.6, 0.55, 0.45)`, groundColor `Color3(0.35, 0.28, 0.2)`, intensity `0.5`.

### 4.3 Rim / storm light

A third, narrative-driven `DirectionalLight` (or `SpotLight` for interior beats) activated by specific `actionBus` events. Not persistent.

**Usage:**
- Path A climactic moment: cellar candlelight, intensity `0.8`, color warm `(1, 0.7, 0.4)`.
- Path B boat-loading dusk: rim light from lake-side, color `(0.9, 0.5, 0.3)`, intensity `0.4`.
- Path C ravine night-watch: very low-intensity moon light `(0.3, 0.35, 0.45)`, intensity `0.15`.

Rim lights are tagged to their specific era + fragment via the layer-mask helpers; they do not persist across fragments.

### 4.4 Environment texture (`.env`)

Per era. Baked from a plausible Bisesero horizon using a generated HDRI.

| Era | File | Tone |
|---|---|---|
| Present | `public/env/bisesero_overcast_morning.env` | Overcast, wet-season morning, diffuse. Sky: muted grays. |
| Past | `public/env/bisesero_clear_afternoon.env` | Clear April afternoon, high sun. Sky: warm-tinted blue. |

Both environments are 128×128 specular cubemap + SH irradiance, compressed. Budget: ~8 MB combined.

`scene.environmentTexture` is swapped during Chronos Switch transition (§3.6 of CHRONOS_SWITCH.md), at the mid-crossfade point. No linear interpolation — straight swap; the crossfade of pipelines hides the discontinuity.

### 4.5 Shadow strategy

**One `ShadowGenerator` per era sun.** `useContactHardeningShadow = true` (PCSS). Shadow map resolution: `2048` per era (4096 if budget allows — deferred to M2 playtest).

- `bias = 0.005`, `normalBias = 0.02`.
- `transparencyShadow = true` for vegetation alpha-cards.
- Shadow-casting meshes ≤ 150 per frame (§7 budget).

Hemispheric and rim lights never cast shadows.

### 4.6 Emissive surfaces

Minimal. Only three contexts emit:
- Interior candle/oil lamp during Path A cellar fragment — one emissive material, intensity 3.0.
- Distant militia flashlight (never shown directly, only emission reflecting on far façades) — one emissive sphere mesh, hidden from camera.
- 2026 flashlight held by the investigator (future addition, post-M3).

No blood, no fire. The PRD forbids decorative violence; emissive is not a storytelling license to add either.

---

## 5. Post-processing pipeline

`DefaultRenderingPipeline` is the backbone. Two named pipeline instances at init: `pipelinePresent` and `pipelinePast`. The active pipeline is swapped during Chronos Switch transition by animating `pipeline.imageProcessing.contrast`, `pipeline.imageProcessing.exposure`, and overall pipeline opacity via blend (the outgoing pipeline's last-frame texture is drawn over the incoming pipeline's first frame, alpha-blended over 1.8 s — see `CHRONOS_SWITCH.md §3.6`).

### 5.1 Shared stack

Applied identically regardless of era:

| Effect | Config |
|---|---|
| Tone-mapping | ACES (`ImageProcessingConfiguration.TONEMAPPING_ACES`) |
| Color space | Linear → sRGB out |
| FXAA | Enabled (`pipeline.fxaaEnabled = true`); MSAA disabled — pipeline conflict (§5.5) |
| SSAO2 | `totalStrength = 1.0`, `radius = 0.8`, `blurH = true`, `blurV = true`, `expensiveBlur = false` |
| Sharpen | `edgeAmount = 0.15` — very subtle |
| Samples (MSAA on pipeline RT) | 1 (FXAA only; §5.5) |

### 5.2 Per-era profile

| Dimension | Present (2026) | Past (1994) |
|---|---|---|
| Saturation | `-0.15` (desaturated) | `+0.10` (saturated) |
| Contrast | `0.9` | `1.1` |
| Exposure | `0.95` (slight under) | `1.05` (slight over) |
| Color grade LUT | `lut_present_cool.png` — cool shadows, slight green | `lut_past_warm.png` — amber highlights |
| Vignette | `weight = 0.6`, color `(0.1, 0.12, 0.15)`, eccentricity `1.5` | `weight = 0.3`, color `(0.2, 0.15, 0.1)`, eccentricity `1.2` |
| Film grain | `intensity = 0.4`, `animated = true` | `intensity = 0.15`, `animated = true` |
| Fog density | `0.028` (valley mist at 40 m) | `0.012` (clear at 150 m) |
| Fog color | `(0.75, 0.78, 0.82)` — overcast gray | `(0.82, 0.78, 0.68)` — warm haze |

Numbers are small intentionally. The PRD's restraint rule applies here: dramatic color grading (heavy teal shadows, crushed blacks) is forbidden. The reader should notice the difference only on A/B comparison.

### 5.3 Bloom

Emissive-only. Threshold high, scale low.

- `bloomEnabled = true`.
- `bloomThreshold = 1.2` (Present), `0.9` (Past) — Past's afternoon sun glints on tin roofs and lake water, so threshold is slightly lower.
- `bloomWeight = 0.15`.
- `bloomKernel = 64`.
- `bloomScale = 0.5`.

No hero bloom. If a surface looks "bloomy," the threshold gets raised until only actual light sources contribute.

### 5.4 Transition crossfade

During a Chronos Switch transition (1.8 s total per `CHRONOS_SWITCH.md §3.6`):

1. At `transitionStarted`, both pipelines render simultaneously to offscreen RTs.
2. A composite shader blends the two RTs: `outColor = mix(pipelinePresent.output, pipelinePast.output, t)` where `t` is the eased crossfade curve.
3. At `transitionCompleted`, the outgoing pipeline is unbound from its RT; only the incoming pipeline runs.

Cost: during transition, scene is rendered twice (once per pipeline). At 1.8 s per transition and a target cadence of ~1 transition per 2 minutes of play, the average overhead is 1.5%. Peak overhead during the transition is ~2× frame time — acceptable because input is damped during transition (§3.6).

### 5.5 MSAA vs. FXAA

Chose FXAA. MSAA conflicts with `DefaultRenderingPipeline`'s internal RT management; enabling both produces washed-out edges. If a future WebGPU backend is targeted, revisit — WebGPU has cleaner MSAA-in-pipeline support.

---

## 6. Physics (Havok)

### 6.1 Init sequence

Before scene creation, in `engine/Physics.ts`:

```typescript
import HavokPhysics from "@babylonjs/havok";
import { HavokPlugin } from "@babylonjs/core/Physics/v2/Plugins/havokPlugin";

export async function initPhysics(scene: Scene) {
  const havok = await HavokPhysics();
  const plugin = new HavokPlugin(true, havok);
  scene.enablePhysics(new Vector3(0, -9.81, 0), plugin);
}
```

Must be `await`ed before any `PhysicsAggregate` is constructed. `main.ts` owns the await point.

### 6.2 Gravity

`(0, -9.81, 0)`. No tuning. Terrain is authored to plausible scale (human-height references real).

### 6.3 Aggregate usage

`PhysicsAggregate` only for:
- Interactive props the player can touch, lift, or knock over (jerrycan, bicycle, cooking pot, stone-stack).
- Dynamic environmental elements (a door that closes, a latch that lifts, a boat that rocks).
- Triggers for entering/exiting a zone (doorways, threshold markers, fragment activation radii).

**Never** for:
- Terrain mesh (uses a non-physics collision mesh per §6.5).
- Vegetation instances (thin instances, no physics).
- Static architecture (walls, roofs, dock — static colliders, never aggregates).

### 6.4 Performance budget

≤ 30 active dynamic aggregates per frame. Aggregates for meshes tagged to the inactive era are disabled via `body.disablePreStep = true` + `body.setMotionType(STATIC)` to cost nothing in the Havok step.

### 6.5 Collision mesh vs. render mesh

Terrain and large architecture use separate collision meshes — simplified versions of the render mesh, authored in Blender at decimation ratio ≈ 0.2. Stored in `processed/collisions/` and loaded by `world/` modules alongside their render counterparts. Collision meshes are never parented to a camera layer mask — collision is era-independent; visibility is not.

---

## 7. Performance budget

Target: **60 fps at 1920×1080 on RTX 3060 / RX 6700.** The RTX 5090 authoring workstation is not the perf target.

| Resource | Budget | Measurement |
|---|---|---|
| Draw calls | ≤ 1500 | Babylon Inspector → Statistics → "Active meshes" × materials |
| Triangles | ≤ 1.5 M | Inspector → "Active faces" |
| Shadow-casting meshes | ≤ 150 | Count of meshes with `receiveShadows` or added to generator |
| Dynamic physics aggregates | ≤ 30 | `scene.getPhysicsEngine().getImpostors()` filtered to non-static |
| Light count (active era) | ≤ 4 simultaneously active | 2 sun/sky + up to 2 rim lights |
| Texture VRAM | ≤ 800 MB | KTX2 compressed; hero textures 4K, majority 2K, small props 1K |
| LOD count per authored asset | 3 tiers | Distance-based: 0–15 m LOD0, 15–50 m LOD1, 50 m+ LOD2 |
| LOD transition distances | `15 m, 50 m` | Hysteresis band of ±2 m |

Debug overlay (dev build only) flags when any budget is exceeded at runtime.

---

## 8. Trade-offs

### A. Forward vs. deferred rendering

Babylon 9's default is forward. Deferred is not planned. Forward is correct for this project: few dynamic lights (≤ 4), heavy reliance on baked environment and shadow maps, transparent vegetation cards throughout.

### B. One pipeline with per-era profile vs. two pipelines crossfaded

Chose two pipelines. Cleaner transition; each pipeline's settings are frozen at construction and never mutated during play. VRAM overhead of the second pipeline's offscreen RT is ~12 MB at 1080p RGBA16F — acceptable.

Alternative: one pipeline whose uniforms (saturation, contrast, vignette, fog density) lerp between era values during transition. Rejected because the per-era LUT is not lerp-friendly (different LUT files, not a color-temperature shift), and the `environmentTexture` swap forces a discontinuity regardless.

### C. Real-time GI vs. baked lightmaps

Leaning baked for static geometry (terrain, architecture, vegetation), real-time (sun direct + environment SH) for dynamic elements (props, the player's interactions). This keeps the shader path simple and performance predictable.

Lightmap pipeline not yet specified. Deferred to M5+; first-fragment quality does not require it.

### D. Per-mesh `layerMask` vs. per-mesh `metadata.era` + runtime enable

Chose `layerMask`. `setEnabled(false)` suppresses not just rendering but physics and raycasting, which breaks camera picks on era-shared collision meshes. `layerMask` suppresses only rendering — physics and picks continue on the camera's current mask, which is what we want.

---

## 9. Failure modes

| Failure | Detection | Mitigation |
|---|---|---|
| WebGL context loss (tab backgrounded, driver hiccup, alt-tab on some platforms). | `engine.onContextLostObservable`. | Pause the render loop; on regain, call `engine.onContextRestoredObservable` handler to re-create `DefaultRenderingPipeline` instances and re-upload `.env` textures. Shader cache is preserved. |
| Shader compilation failure on initial load. | Babylon logs an error; mesh renders with default material. | Fall back to unlit magenta material (intentionally ugly, as a development signal). Log error to console with mesh name. |
| Frame rate below 30 fps for > 2 s. | Rolling average in `debug/PerfMonitor.ts`. | Dev-only overlay flags the offending subsystem (draw call spike, shadow-cast spike, aggregate spike). No runtime dynamic quality reduction — we fix the authoring, not the runtime. |
| Per-era LUT fails to load. | `Texture.onLoadObservable` never fires within 3 s. | Fall back to identity LUT (no color grade); log warning. Should never happen in prod builds. |
| `.env` missing. | `CubeTexture` load error. | Scene falls back to a default-blue environment; log error. Catastrophic for visual quality but not a crash. |
| Physics plugin fails to initialize (Havok WASM load failure). | `HavokPhysics()` rejects. | Throw at `main.ts` boot; show a load-error UI. The game requires physics for interactions; this is a hard fail. |
| `ShadowGenerator` runs out of memory on mobile GPUs. | OOM error from WebGL. | Deferred — mobile is not a v1 target. Per PRD, desktop browser only. |
| SSAO produces banding on low-VRAM GPUs. | Visual inspection only. | Disable `expensiveBlur`, lower `samples` from 16 → 8, fall back to SSAO1 if needed. |

---

## 10. Milestones

**M1 — Materials library stub.** `engine/Materials.ts` with the 14 base materials registered and frozen, stub textures (solid colors + checker normal). Enables location authoring to start without finished PBR assets.

**M2 — Per-era pipeline crossfade.** `engine/RenderingPipeline.ts` implements both pipelines and the blend shader. Dev-only keyboard hotkey toggles era for manual testing. Blocks first-fragment work.

**M3 — Vertical slice lighting.** Family Compound's Present and Past lighting rigs authored to artist-director approval. Baselines all other locations.

**M4 — Havok wire-up.** `engine/Physics.ts` installed, `@babylonjs/havok` added to `package.json`, init sequence validated with a single dynamic aggregate (a jerrycan on a table).

**M5 — Real PBR textures.** First 4 assets pipelined from Hunyuan3D through bake → compress → load. Replaces stub materials for the Family Compound.

**M6 — Shadow tuning.** Final shadow map resolution, cascade config (if any) decided after M3 playtesting. ADR at this point if cascades are adopted.

**M7 — Perf pass.** Full location under budget. LOD distances validated. SSAO cost measured; consider deferring to post-fx profile per era.

---

## 11. Open questions

- Q1: **HDR output (Display P3 / Rec.2020)?** Valuable for high-end monitors, zero cost if the tonemapper supports it. Deferred — evaluate once a playable build is in hand.
- Q2: **MSAA vs. FXAA + TAA.** TAA is tempting for the documentary aesthetic (slight temporal smoothing), but Babylon's TAA support is immature as of v9. Stay with FXAA for v1; revisit in v1.1.
- Q3: **Screen-space reflections on the lake.** The lake is narratively important (Path B). SSR would make it noticeably more alive. Cost: 1–2 ms per frame. Decide at M3 after Family Compound lighting lands — if we are comfortably under budget, add SSR for the Lake Shore location only.
- Q4: **Baked lightmaps for static geometry.** Would lift quality at flat lighting cost. Authoring cost: a Blender bake pass per location. Decide at M5.
- Q5: **Variable rate shading (WebGPU).** Deferred; WebGL 2 is the v1 backend.
