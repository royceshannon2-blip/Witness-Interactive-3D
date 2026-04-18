# CLAUDE.md — Witness Interactive 3D

## Project Overview
A first-person, photoreal historical interactive work set in the Bisesero Hills, Rwanda. Built with **Babylon.js 9** and **Havok Physics**, with assets generated locally on an RTX 5090 via **Hunyuan3D 2.1** and delivered as 8K-PBR Draco/KTX2 `.glb`.

The web application lives in `witness-interactive-vite/`. Always prefix terminal commands with `cd witness-interactive-vite`.

### Where to start reading
- [`docs/design-docs/MASTER.md`](docs/design-docs/MASTER.md) — umbrella doc, repo map, gap analysis.
- [`ARCHITECTURE.md`](ARCHITECTURE.md) — module boundaries and dependency graph.
- [`docs/current-state/PROTOTYPE_AUDIT.md`](docs/current-state/PROTOTYPE_AUDIT.md) — honest review of the current `main.ts` prototype. **Read before touching it.**

## Development Workflows

### Asset Pipeline (Local 5090)
- **Geometry:** Generate base meshes via local Hunyuan3D 2.1.
- **Texturing:** Bake 8K PBR maps (albedo, normal, roughness, metalness) in Blender/Substance.
- **Format:** Export as `.glb` (GLTF) with Draco mesh compression and KTX2 texture compression.
- **Shaders:** Use the Node Material Editor (NME) for complex historical effects (weathered stone, flowing water).

See [`docs/design-docs/ASSET_PIPELINE.md`](docs/design-docs/ASSET_PIPELINE.md) for the full pipeline spec.

### Physics (Havok)
- Initialize `HavokPhysics()` before scene creation.
- Use `PhysicsAggregate` for all interactive historical artifacts.
- Default gravity: `new BABYLON.Vector3(0, -9.81, 0)`.
- **Status:** not yet installed. Add `@babylonjs/havok` before implementing `src/engine/Physics.ts`.

## Narrative Architecture

All narrative/branching logic is separated from 3D rendering code. Full spec in [`docs/design-docs/NARRATIVE.md`](docs/design-docs/NARRATIVE.md) and [`witness-interactive-vite/src/narrative/README.md`](witness-interactive-vite/src/narrative/README.md).

- **StateManager** (`src/narrative/StateManager.ts`): Global game state, flags, progress. Serializable for save/load.
- **Actions** (`src/narrative/Actions.ts`): Event bus bridging story branches to 3D events (audio, camera, animation).
- **NarrativeController** (`src/narrative/NarrativeController.ts`): High-level API for scenes.
- **Graph** (`src/narrative/Graph.json`): DAG of all branches, puzzles, and endings.

### Branching Rules
- **Never code linear paths.** All progression must read from `Graph.json`.
- **State-driven logic**: player choices update flags in `StateManager`. 3D events respond by subscribing to `actionBus`.
- **Narrative → 3D is one-way**: the narrative layer emits; scenes react. Scenes never query or mutate narrative state directly except through `NarrativeController`.
- **Future tools**: consider **InkJS** for dialogue-heavy branches, **XState** for state-machine logic.

### Adding a new puzzle or branch
1. Define the node in `src/narrative/Graph.json` with `requiredFlags` and `unlocksFlags`.
2. Add handler logic in `src/narrative/Actions.ts` if state transitions need side effects.
3. Update [`docs/design-docs/NARRATIVE.md`](docs/design-docs/NARRATIVE.md) with the new branch in the Mermaid diagram.
4. Subscribe the 3D scene to `actionBus.onStateChange()` to respond visually.

## Technical Standards

### Naming
- **CamelCase** for classes/files: `TimeManager.ts`, `FamilyCompound.ts`.
- **camelCase** for variables/functions: `initializeHavok()`, `compoundMesh`.
- **UPPER_SNAKE_CASE** for constants: `MAX_TEXTURE_RES = 8192`.

### Visual Quality
- Use `PBRMaterial` for all historical surfaces. No `StandardMaterial`.
- Lighting: `EnvironmentTexture` (`.env`), `ShadowGenerator` with PCSS.
- Post-processing: `DefaultRenderingPipeline` with ACES tone-mapping, SSAO2, FXAA. Bloom sparingly, for emissive sources only.
- Set `anisotropicFilteringLevel = 16` on ground and architectural textures.

### Performance
- Use **Thin Instances** for repeated environmental props (folly, rocks, fences).
- Use **Havok Physics** — do not use Cannon or Ammo.
- Use **async/await** for all `AssetContainer` loading.
- See [`.claude/rules/babylon-patterns.md`](.claude/rules/babylon-patterns.md) for full Babylon 9 conventions.

## Critical Commands
- `npm run dev` — launch Vite dev server.
- `npm run build` — TypeScript check + production build.
- `npm run preview` — preview the production build.
- `npx babylonjs-viewer` — preview generated `.glb` assets.

## Documentation Rules
From [`.claude/rules/documentation.md`](.claude/rules/documentation.md):

1. Update `ARCHITECTURE.md` whenever a new service, schema, or API contract is introduced.
2. Append a technical summary to `docs/decisions/CHANGELOG_DETAILED.md` after every completed task.
3. Every new function/class has a docstring explaining its role in the larger architecture.
4. All diagrams are Mermaid.

## Reference Snippet — High-Fidelity Scene Setup
```typescript
const setupHighFidelity = (scene: BABYLON.Scene) => {
  scene.createDefaultEnvironment({ createGround: false, createSkybox: false });
  const pipeline = new BABYLON.DefaultRenderingPipeline("highQuality", true, scene);
  pipeline.samples = 4;
  pipeline.fxaaEnabled = true;
  pipeline.bloomEnabled = true;
  pipeline.imageProcessing.toneMappingEnabled = true;
  pipeline.imageProcessing.toneMappingType =
    BABYLON.ImageProcessingConfiguration.TONEMAPPING_ACES;
  new BABYLON.SSAO2RenderingPipeline("ssao", scene, 1.0, [scene.activeCamera!]);
};
```
