# Prototype Audit — `witness-interactive-vite/src/main.ts`

- **Status:** Draft
- **Author:** Claude (via @royceshannon2)
- **Subject file:** `witness-interactive-vite/src/main.ts` — 1029 lines, single file
- **Commit under audit:** working tree at 2026-04-17
- **Verdict:** **Throw out. Salvage patterns, not code.**

This audit is brutal by request. The goal is clarity on what to keep, rewrite, or discard — not to dunk on the prototype. It exists because writing it was valuable; the habits it built are not the same as the file it produced.

---

## 1. Headline

The prototype is a **procedurally-generated 1994 Kigali roadside scene with blocky figures, a militia truck, and checkpoints.** The project is **a photoreal 2026 investigation of the Bisesero Hills, with a 1994 dual-era mechanic and environmental storytelling that explicitly avoids violent decoration.**

These are not the same game. The prototype does not move the shipping project forward. It was useful as a **Babylon 9 sketchbook** — the author learned lighting, PBR materials, terrain sampling, building primitives, post-processing pipeline setup. Those skills are the deliverable, not this file.

**Recommendation:** preserve `main.ts` on a `prototype/kigali-sketch` branch for reference. Start `src/bootstrap/main.ts` from scratch when implementation begins.

---

## 2. Scale of the problem

| Metric | Value | Problem |
|---|---|---|
| Lines in one file | 1029 | Target: < 100 per module, < 300 ever. |
| `createScene` function length | ~1000 | Single function; should be 5–10 orchestration calls. |
| Inline material definitions | 16 | Should live in `engine/Materials.ts`, imported by name. |
| Inline mesh-builder helpers | 10 (`createRugo`, `createShopfront`, `createChurch`, `createCheckpoint`, `createJerryCan`, `createBicycle`, `createFigure`, `createMilitaryTruck`, `createEucalyptus`, `createMatookeClump`) | Each should be its own module under `world/` with a single default export. |
| Hard-coded coordinates | 18 positions | Should be authored data (JSON) or derived from a location spec. |
| `// FIX:` comments | 11 | Tells a clear story: the same pattern (heightfield sampling for placement) was debugged at least a dozen times before it stabilized. Salvage the pattern; delete the comments with the code. |
| `@babylonjs/havok` imports | 0 | Project rules mandate Havok. |
| Narrative system imports | 0 | Zero integration with the game's entire narrative architecture. |

---

## 3. What to salvage

These are ideas, not code. Copy them into the new modules manually; do not `cp` from `main.ts`.

| Salvageable pattern | Current location | Move to |
|---|---|---|
| Heightfield function → vertex displacement | L162–183 | `world/Terrain.ts` |
| `getApproxHeight(x, z)` sampler | L187–193 | `world/Terrain.ts` (exported helper) |
| `getFootprintMinHeight(cx, cz, w, d)` — prevents buildings from floating | L197–207 | `world/Terrain.ts` |
| `isFlat(cx, cz, radius, tolerance)` — placement guard | L217–231 | `world/Terrain.ts` |
| `tube(from, to, radius, mat)` helper for bike frame | L564–595 | Generalise to `world/props/ProcPrimitives.ts`. Useful for rebar, fence wire, cables. |
| PBR material starting values (laterite, tin roof, eucalyptus leaf translucency) | L59–150 | `engine/Materials.ts`. Values are plausible starting points for rural Bisesero; keep them, retune with real reference photos. |
| Post-fx stack: ACES tone-map + vignette + grain + sharpen | L906–925 | `engine/RenderingPipeline.ts`. Intensities need to drop (grain 11 → ~4, vignette 2.8 → ~1.4 for Present; different profile for Past). |
| Layered directional lights (sun, sky hemisphere, storm rim) | L37–52 | `engine/Lighting.ts`. The three-light approach is correct for Bisesero's overcast/humid look. |
| Lightning timer state machine | L930–953 | Move to an optional `engine/WeatherFX.ts` — but only wire it in Past era, and only for specific narrative beats, not as constant ambience. |

---

## 4. What to throw out entirely

These have no analogue in the target design. Do not port them.

| Artifact | Location | Why out |
|---|---|---|
| **Procedural human figures** (`createFigure`) | L742–801 | Blocky box-figures (legs, torso, head spheres). Inappropriate for the subject matter. PRD §content-guidelines forbids exploitative depiction; these are closer to a placeholder than a design, and in a scene about genocide the placeholder reads as disrespect. If we need distant crowds in Past, use silhouetted billboards or actual authored GLBs — never procedural boxes. |
| **Militia truck + checkpoints** as constant environmental dressing | L433–491, L806–856, L881–884 | PRD: "Avoid inserting gratuitous violence into the environment as decoration. If conflict cues are needed, keep them subtle, environmental, and narrative-driven." These are not narrative-driven here; they are scenery. The Past 1994 era will have specific scripted beats where a checkpoint or truck appears as an earned storytelling moment — not as persistent props. |
| **Kigali urban road layout** — flanking buildings on a straight road | L862–875 | Wrong location. Bisesero is terraced hills with a compound, a cellar, a lake shore, a ravine, and heights. None of this layout maps. |
| **GLB export button in HUD** | L978–992 | Dev-only feature exposed to the end user. Move to a dev overlay gated by `import.meta.env.DEV`. |
| **`counter.ts` in src/** | N/A (separate file) | Vite template leftover. Delete. |
| **Hard-coded "KIGALI · APRIL 1994" HUD text** | L961 | Wrong location + wrong information-model. The player's era display (if any) should read from `TimeManager.currentEra` and the location should come from a scene registry. |
| **Gravity fudge factor** `-9.81 * 0.06` | L10 | No justification. Either it's real gravity, or it's a moon level. If camera bobbing is the reason, fix that in the controller. |
| **`scene.onPointerDown = () => engine.enterPointerlock()`** | L1005 | Global pointer handler conflicts with any UI interaction. Belongs in `interaction/PlayerController.ts` with proper pointerlock enter/exit lifecycle. |
| **Random-without-seed placement** | L864, L868, L877–879, L886–890 | `Math.random()` everywhere. Same world looks different on every reload. No save-load possible. Use a seeded PRNG or authored positions. |
| **Per-spoke individual meshes on the bike** | L640–650 | 16 spokes × N bikes = 16N meshes. The `babylon-patterns.md` rule mandates thin instances for repeated props. Bake the bike wheel as a single mesh or use a `ThinInstanceBuffer`. |

---

## 5. What to rewrite (keep the intent, change the shape)

| Subsystem (in prototype) | Reason for rewrite | Target home |
|---|---|---|
| `createScene` monolith | 1000-line function, all logic inline. | Break into `SceneFactory.create()` → calls `Lighting.build`, `Terrain.build`, then per-location `FamilyCompound.build`, etc. |
| Material definitions + `freeze()` pass | Materials are created inline, frozen at one point, then more materials are created (not frozen) inside builders. Inconsistent. | All materials defined in `engine/Materials.ts`. Freeze on registration. Builders import by name: `materials.brick`, `materials.tinRoof`. |
| Terracing via `Math.floor(height / TERRACE) * TERRACE` | Applied to the *entire* ground. Real Rwandan terracing is only on cultivated slopes, with irregular edges and drainage channels. | `world/Terrain.ts` exposes a biome map. Terracing is a biome feature, not a global transform. |
| `createEucalyptus` / `createMatookeClump` as ad-hoc mesh builders | Each tree is built from scratch with its own material instances. | One authored GLB per plant species, then `ThinInstancedMesh` scattered across a density map. |
| HUD label + crosshair + button in `AdvancedDynamicTexture` | All thrown into one fullscreen texture. | `ui/HUD.ts` owns the HUD layer. `ui/LedgerUI.ts` owns the ledger. Dev tools in a separate `ui/DevOverlay.ts` behind a flag. |
| Shadow generator at 1024, PCF | `CLAUDE.md` mandates PCSS. | Use `usePercentageCloserFiltering = true` with quality `HIGH` and a 2048 map for the sun shadow. |
| `UniversalCamera` with gravity + collisions + WASD | Works, but there's no crouch/prone, no interact prompt, no ducking for `Hidden` perspective mode. | `interaction/PlayerController.ts` wraps a `UniversalCamera`, exposes crouch, interact raycast, and a `setMovementProfile()` for Protector/Hidden modes. |

---

## 6. Violations of project rules

Cross-referenced against `CLAUDE.md`, `.claude/rules/babylon-patterns.md`, and `docs/design-docs/PRD.md`.

| Rule | Rule source | Prototype status |
|---|---|---|
| "Use Havok Physics — do not use Cannon or Ammo." | `babylon-patterns.md` | Violated. No physics of any kind. Havok not in `package.json`. |
| "Use Thin Instances for repeated environmental props." | `babylon-patterns.md` | Violated. No instancing anywhere. Every sandbag, spoke, leaf is its own mesh. |
| "Use Async/Await for all AssetContainer loading." | `babylon-patterns.md` | N/A — no assets are loaded. Everything is procedural. |
| "Prefer PBRMaterials over StandardMaterials." | `babylon-patterns.md` | Followed ✅. |
| "Mandatory Lighting: EnvironmentTexture (.env), ShadowGenerator with PCSS." | `CLAUDE.md` | Violated. No environment texture; shadow generator uses PCF at 1024 res. |
| "Set anisotropicFilteringLevel = 16 for ground and architectural textures." | `CLAUDE.md` | Not applicable (no textures) but the absence of this suggests that when textures arrive this will be overlooked. |
| "All progression must read from Graph.json." | `CLAUDE.md` | Violated by omission — there is no progression at all. |
| "Avoid inserting gratuitous violence into the environment as decoration." | `PRD.md` | **Violated.** The militia truck, checkpoints, and sandbag emplacements are permanent scenery, not narrative beats. |
| "Out of scope: Photographic human likenesses." | `PRD.md` | Technically followed (figures are blocky), but the spirit is missed — the figures do not serve the narrative. |
| "Dense atmospheric depth. Soft morning haze and humid valley light." | `PRD.md` | Partially followed. Exponential fog is there; haze layering and valley mist are not. |

---

## 7. Specific line-level issues

Numbered for reference. Not exhaustive — a sampling.

1. **L10** — `scene.gravity = new BABYLON.Vector3(0, -9.81 * 0.06, 0)`. Magic fudge factor, no comment. Remove.
2. **L15** — `scene.fogColor = new BABYLON.Color3(0.64, 0.60, 0.53)`. Warm tan fog for a humid valley is wrong — Bisesero mist is cool blue-grey. Retune.
3. **L17–30** — `UniversalCamera` configured inline; should be a `PlayerController` class.
4. **L54** — Shadow generator at 1024 with PCF, not PCSS. Violates rule.
5. **L150** — `[...].forEach(m => m.freeze())`. Freezes the shared set, but subsequent builders (`doorMat` L333, `shutterMat` L370, `plankMat` L464, `crossMat` L411) create unfrozen materials with per-instance names. Materials explode in count.
6. **L164** — `if (!positions) return scene;` — early return from a scene builder that has already attached lights, camera, and materials. The returned scene is half-constructed. Either throw or handle before starting.
7. **L175–180** — Terracing applied to every vertex, then a road cut via `Math.abs(x) < roadWidth`. Bisesero has no straight road like this.
8. **L188–193** — `getApproxHeight` does nearest-neighbor sampling, not bilinear. Close enough for placement; incorrect if you ever need a smooth normal.
9. **L301** — `createRugo` takes a `wallMat` param but callers pass `brickMat` or `concreteMat` at random (L867). No design logic behind the material choice.
10. **L377** — `createChurch` hard-coded at `(-18, 28)`. Not data-driven.
11. **L511–514** — `createBicycle` has an `isFlat` guard with a `console.warn` fallback. Good instinct. Generalize: every placement should go through a `PlacementGuard` that logs, recovers, or rejects.
12. **L754–801** — `createFigure` uses `BABYLON.MeshBuilder.CreateBox` for legs/arms/torso and `CreateSphere` for head. Throw out (see §4).
13. **L884** — `createMilitaryTruck(7, 19, 0.12)` — scenery, not narrative. Throw out (see §4).
14. **L901** — `camera.position.y = getApproxHeight(0, -8) + 1.65` — spawn height fixup done imperatively after the camera is already in the scene. Belongs in a `spawnPlayer(scene, spawnPoint)` function.
15. **L906–925** — Post-processing pipeline hard-coded; no era profile. Present and Past eras should share structure but have different intensities.
16. **L935–953** — Lightning state machine in `registerBeforeRender`. Works, but lives in `createScene`. Belongs in `WeatherFX.ts`, opt-in per location.
17. **L987–991** — GLB export button. Move to dev overlay.
18. **L1005** — `scene.onPointerDown = () => engine.enterPointerlock()`. Overwrites; should `add` a pointer observable with proper teardown.

---

## 8. What the prototype *did* teach

Crediting the sketch honestly:

- The heightfield + footprint-sampling approach is the right instinct. Every `// FIX:` comment on placement is a hard-won debug. The pattern transfers.
- The PBR palette (earth reds, muted greens, weathered whites) reads correctly for the region. The values are a good starting point for real retune with reference photos.
- The three-light pattern (sun + hemisphere + storm rim) is the right skeleton for Bisesero's overcast look.
- The vignette + grain + sharpen pass is a solid film-grade default. Intensities are too strong; structure is right.
- Building bikes from primitives rather than authoring them as GLBs may actually be the right call for v1 — but via thin instances, not per-mesh.

---

## 9. Conclusion and next steps

**Do not refactor `main.ts`.** The scope of rewrite exceeds the scope of what's there. Start fresh in `src/bootstrap/main.ts` when implementation begins, pulling salvageable patterns into their target modules.

Before that, the unblockers are:
1. [`CHRONOS_SWITCH.md`](../design-docs/CHRONOS_SWITCH.md) written (currently stub).
2. [`RENDERING.md`](../design-docs/RENDERING.md) written (currently stub).
3. `@babylonjs/havok` installed, `engine/Physics.ts` stubbed.
4. One Bisesero location (Family Compound, Present era) modeled as a target — even as a greybox, so rendering and layer-mask code have something to live against.

Then the vertical slice in [`MASTER.md §7`](../design-docs/MASTER.md#7-work-ordering) becomes actionable.

**Preserve the prototype.** Tag the current commit `prototype/kigali-sketch` before any new work touches the file. It has reference value for lighting, materials, and terrain sampling.
