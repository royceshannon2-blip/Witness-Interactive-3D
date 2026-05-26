# Asset Pipeline Rule — Local Hunyuan3D 2.1 + Babylon 9

**Scope:** every 3D asset that ships in this project. **No exceptions for "just a placeholder."** A primitive box authored inline in a `world/` module is allowed only as a temporary scaffold, and only if a `// TODO(asset-pipeline)` comment names the asset id that will replace it.

This rule is normative. If an instruction in this file conflicts with a code suggestion, follow this file.

---

## 1. The pipeline is the only source of new assets

All net-new 3D content is produced locally on the RTX 5090 via the tool chain in [`tools/`](../../tools/) and the spec in [`docs/design-docs/ASSET_PIPELINE.md`](../../docs/design-docs/ASSET_PIPELINE.md). There is no fallback to cloud generators, marketplace downloads, or "fetch from a CDN at runtime."

**The user-facing entry point is `tools/witness.py`:**

```
python tools/witness.py generate <id> [--kind mesh|splat|tileset|navmesh|nme|animated]
```

`witness.py` handles server management, smart ref detection, VRAM scheduling, and all pipeline flags in a single cohesive CLI. It delegates to `tools/asset_pipeline.py` internally — but `asset_pipeline.py` is not the user-facing command.

Anything you build for this project must enter through `tools/witness.py generate`. Direct calls to the underlying scripts (`generate_asset.py`, `optimize_asset.py`, etc.) are fine for iteration, but `witness.py generate` is the canonical entry point and the only path that writes the registry.

---

## 2. Required asset kinds and their branches

The orchestrator dispatches on `--kind`. Pick the right branch — do not bolt a splat into the GLB branch or a tileset into the splat branch.

| `--kind`   | Inputs                                  | Hunyuan? | Output(s)                                                     | Runtime owner |
|------------|-----------------------------------------|----------|---------------------------------------------------------------|---------------|
| `mesh`     | ref.png (hand-drop or Flux stage 0) + prompt template; ref is always refined through FLUX.2 [klein] stage 0.25 unless `--no-refine-ref` | yes | `<id>.glb` (Draco + KTX2, 3 LODs) + collision GLB | `AssetLibrary` |
**Stage 2 AI projection is on by default.** After Hunyuan shape generation the pipeline runs `texture_asset.py --ai-project`: ComfyUI SDXL + ControlNet (depth) projects material maps from the 6 canonical views before the Blender Cycles PBR bake. Pass `--no-ai-project` to skip (procedural bake only, faster, lower quality).

**Multi-view input (stage 0.5) is default-on for `mesh|animated`.** The ref is background-removed + framed (rembg + `frame_subject`), then either Zero123++ synthesises 6 views, OR — when real photos are supplied via `--real-views <dir>` (auto-detected at `prompts/asset-templates/<id>/real_views/`) — those captures are staged directly and synthesis is skipped. Real angles beat synthesised ones for all-angle accuracy and are the preferred path for posed/specific assets (e.g. first-person hands, where the FLUX text prior won't render a dorsal pose). All views pass Gate 1 (per-view pixel + all-view CLIP + cross-view colour) before the Hunyuan ensemble. `--no-multi-view` opts out (single-image Hunyuan). **Requires `rembg`+`onnxruntime` in the ComfyUI venv**, or background removal no-ops with a loud warning and the slab artefact returns.
| `splat`    | `.ply` / `.splat` / `.spz` capture      | no       | normalised `<id>.spz` (or `.ply`) + bounding box + thumbnail  | `SplatLibrary` |
| `tileset`  | 3D Tiles root URL or local tileset.json | no       | registered `<id>.tileset.json` reference                      | `TilesetMount` |
| `navmesh`  | terrain/ground GLB(s)                   | no       | `<id>.nav.bin` (RecastJSPlugin output)                        | runtime build via `engine/Navigation.ts` (deferred) |
| `nme`      | Node Material Editor JSON (hand-authored or NME export) | no | `<id>.nme.json` registered in materials index | `MaterialLibrary` |
| `animated` | ref.png (same chain as mesh: stage 0 → 0.25 refinement → optional stage 0.5 multi-view) + prompt + skeletal rig | yes (mesh) + Blender Cycles bake (with AI projection by default) | `<id>.glb` with embedded animations | `AssetLibrary` |

**OpenPBR is the material default.** All `mesh` and `animated` outputs must ship with PBR textures packed per [`ASSET_PIPELINE.md §3.3`](../../docs/design-docs/ASSET_PIPELINE.md): R-unused / G-roughness / B-metallic in the metallic-roughness texture, OpenGL Y+ normal map convention, KTX2 compression (UASTC for normals, ETC1S for color/MR).

`StandardMaterial` is forbidden in source meshes (see [`babylon-patterns.md`](babylon-patterns.md)); the pipeline rejects any GLB whose `material.type !== "MR"` at the `optimize_asset.py` validation step.

---

## 3. Decision tree — "I need a new asset, what do I run?"

Use this when picking the kind. Do not invent new combinations.

1. **Is it a discrete prop, structure, vegetation card, or hero object?** → `mesh`. Hunyuan generates from a reference image + prompt. PBR baked, Draco + KTX2, 3 LODs, collision.
2. **Is it real-world captured volumetric data (a photogrammetry scan, a Niantic .spz, etc.) used as background or hero environment?** → `splat`. Babylon 9 has native `.ply` / `.splat` / `.spz` / SOG support. Pipeline normalises and registers.
3. **Is it a massive geospatial dataset that must stream by camera position (city, region, satellite terrain)?** → `tileset`. Use 3DTilesRendererJS adapter. Pipeline records the root URL/path; no local conversion.
4. **Do you need pathfinding constraints for AI agents or "where the player can walk"?** → `navmesh`. Built from one or more existing GLBs via `RecastJSPlugin.createNavMesh`. The pipeline serialises the result.
5. **Is it a shader for a unique surface (weathered stone, flowing water, a texture-based area light, a procedural texture / flow map / particle attractor pass)?** → `nme`. The Node Material Editor JSON is the source of truth; the pipeline registers it under a stable id.
6. **Is it an animated character, animal, or environmental prop with skeletal animation?** → `animated`. Hunyuan-generated mesh + Blender-authored rig + GLTF skeletal export. `AssetLibrary` instantiates and exposes the `AnimationGroup` array.

If your request doesn't match one of these six, **stop and ask**. Do not extend the orchestrator without updating this rule.

---

## 4. Naming, registration, and runtime resolution

Every asset must:

- Use the snake_case id pattern `<category>_<name>_<variant?>` from [`ASSET_PIPELINE.md §4.1`](../../docs/design-docs/ASSET_PIPELINE.md).
- Land in `processed/` with the canonical layout for its kind (see §4.2 of the design doc; splats in `processed/splats/`, tilesets in `processed/tilesets/`, navmeshes in `processed/navmeshes/`, NME JSON in `processed/materials/`).
- Be registered via `tools/register_asset.py` (or the orchestrator, which calls it). The registry is `docs/asset-index.md`.
- Be exported into `witness-interactive-vite/public/assets/` via `tools/export_babylon.py` so the runtime resolver can find it under `/assets/<id>.<ext>`.

Runtime code never hardcodes file paths. It calls one of:

- `assetLibrary.preload([...ids])` then `assetLibrary.instantiate(id)` for GLBs.
- `splatLibrary.load(id)` for splats (returns a `GaussianSplattingMesh`).
- `tilesetMount.attach(id, root)` for 3D Tiles.

Any path resolution lives behind the resolver in `AssetLibrary.setResolver(...)` and its siblings. Never inline a `/assets/foo.glb` literal in a `world/` module.

---

## 5. Forbidden shortcuts

These are bugs, not style preferences:

- **Inline `MeshBuilder.CreateBox` (and friends) for anything visible to the player without a `// TODO(asset-pipeline): replace with <asset_id>` comment.** The vertical-slice prototype is allowed to ship primitives, but each one must name the asset that will replace it.
- **Adding a `StandardMaterial`.** Use `MaterialLibrary.get(...)` or author an NME node material.
- **Adding a `<script src="...cdn...">` for any 3D library** (splat loader, 3DTilesRenderer, recast-detour). Add the npm package and import statically.
- **Bypassing `optimize_asset.py`.** Uncompressed GLBs that ship in `public/assets/` will be caught by CI.
- **Editing a generated GLB by hand.** If you need to change the geometry, change the prompt + seed and regenerate. Reproducibility is a release requirement (see [`ASSET_PIPELINE.md §9 Q5`](../../docs/design-docs/ASSET_PIPELINE.md#9-open-questions)).
- **Deleting `ref.original.png` to "reset" an asset.** That file is the audit / rollback copy of the pre-refine reference (see [`ASSET_PIPELINE.md §3` stage 0.25 callout](../../docs/design-docs/ASSET_PIPELINE.md)) — stage 0.25 reads from it on re-runs so denoise never compounds. If you genuinely need a clean slate, delete both `ref.original.png` *and* `ref.png` and re-drop the new source. The orchestrator will treat the next run as a fresh stage 0.
- **Skipping era tagging.** Every instantiated mesh, light, and audio source must call `tagNode` / `tagLight` per [`CHRONOS_SWITCH.md §3.2`](../../docs/design-docs/CHRONOS_SWITCH.md). The pipeline records the asset's default `era_scope` in the registry; the runtime applies it at instantiate time unless overridden.

---

## 6. Pre-flight checklist for any task that adds a 3D asset

Before writing code that references a new asset, walk this list:

- [ ] Asset id chosen per `<category>_<name>_<variant?>`.
- [ ] Prompt template authored at `prompts/asset-templates/<id>.md` (mesh / animated kinds).
- [ ] `python tools/asset_pipeline.py <id> --kind <kind>` runs to completion.
- [ ] Mesh / animated only: `prompts/asset-templates/<id>/ref.original.png` exists alongside `ref.png` after the run (stage 0.25 archived the pre-refine source). If only `ref.png` exists, stage 0.25 was skipped via `--no-refine-ref` — that's a conscious choice you should record in the CHANGELOG entry.
- [ ] Registry entry exists in `docs/asset-index.md`.
- [ ] Public copy exists at `witness-interactive-vite/public/assets/<id>.<ext>`.
- [ ] Mesh path: 3 LODs present at `<id>.glb`, `<id>.lod1.glb`, `<id>.lod2.glb`.
- [ ] Runtime caller uses the appropriate library (`AssetLibrary` / `SplatLibrary` / `TilesetMount`), not a literal URL.
- [ ] `CHANGELOG_DETAILED.md` entry mentions the new asset id.

If any box is unchecked, the asset is not "wired" and the task is not done.

---

## 7. CLI-GUI Parity Rule

**Any new flag, option, or subcommand added to `tools/witness.py` must also be exposed in the asset generation GUI.**

This is a mandatory requirement, not optional. The CLI and GUI are dual interfaces to the same pipeline, and they must remain synchronized:

- When you add a flag like `--no-ai-project` or `--multi-view` to the CLI, the GUI must present the corresponding control (checkbox, dropdown, toggle, etc.).
- When you add a new `--kind` variant or generation mode, the GUI must support it as a selectable option.
- GUI stubs that say "TBD" or "not yet wired" are a blocker for CLI feature merges.

**Location:** The GUI lives in `witness-interactive-vite/src/ui/` (or its logical equivalent). Check `ARCHITECTURE.md` for the current UI module structure.

**Why:** Users should never discover that a CLI feature "isn't available in the GUI yet." The two interfaces are equally canonical; feature parity is release quality, not polish.

---

## 8. Crosslinks

- [`docs/design-docs/ASSET_PIPELINE.md`](../../docs/design-docs/ASSET_PIPELINE.md) — full pipeline spec (stages, naming, failure modes).
- [`docs/design-docs/RENDERING.md`](../../docs/design-docs/RENDERING.md) §3 — material library contract.
- [`.claude/rules/babylon-patterns.md`](babylon-patterns.md) — Babylon 9 conventions (PBR, Havok, ThinInstances, async loading).
- [`.claude/rules/documentation-standards.md`](documentation-standards.md) — how to consult cloned Babylon docs before writing pipeline code.
- [`witness-interactive-vite/src/io/AssetLibrary.ts`](../../witness-interactive-vite/src/io/AssetLibrary.ts) — runtime owner for GLB containers.
- [`witness-interactive-vite/src/io/SplatLibrary.ts`](../../witness-interactive-vite/src/io/SplatLibrary.ts) — runtime owner for Gaussian splats.
- [`witness-interactive-vite/src/io/TilesetMount.ts`](../../witness-interactive-vite/src/io/TilesetMount.ts) — runtime owner for 3D Tiles.
