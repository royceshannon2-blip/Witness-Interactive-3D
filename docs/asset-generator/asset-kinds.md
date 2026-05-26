# Asset Kinds — Decision Tree & Specifications

> Six asset kinds supported by the orchestrator; decision tree, stage mapping, kind-specific rules.
> See [@claude.md](claude.md) and [@architecture.md](architecture.md).

---

## Decision Tree — "What Kind of Asset Do I Need?"

Use this to pick `--kind`:

### 1. Is it a discrete prop, structure, or vegetation card?
→ **`mesh`** (Hunyuan3D-generated GLB)

**Examples:** ledger book, altar photo frame, tree, door, well ring, family shrine slab

**Inputs:**
- `ref.png`: hand-dropped or auto-generated reference image (≥1024²)
- Prompt template: at `prompts/asset-templates/<id>.md` (YAML + description)
- Optional: `--seed`, `--steps`, `--multi-view`

**Outputs:**
- `processed/glb/<id>.glb` (LOD0, optimized, Draco + KTX2)
- `processed/glb/<id>.lod1.glb` (LOD1, 50% faces)
- `processed/glb/<id>.lod2.glb` (LOD2, 15% faces)
- `processed/glb/<id>.collision.glb` (convex hull)
- `processed/textures/<id>/*.ktx2` (albedo, normal, mr, ao)
- `docs/asset-index.md` (registry row appended)

**Stages:** 0.25, 0.5 (optional), 1, 2, 2b (optional), 3, 4, 5, 6

**Runtime:** AssetLibrary

---

### 2. Is it a real-world captured volumetric asset (photogrammetry, NeRF, Niantic .spz)?
→ **`splat`** (Gaussian splat or Signed Distance Function format)

**Examples:** archaeological site capture, environmental background, hero volumetric

**Inputs:**
- `--source <file>`: `.spz` (Niantic Scaniverse), `.ply` (Gaussian splat), `.splat`, `.sog`, or `.sogs` (other volumetric formats)

**Outputs:**
- `processed/splats/<id>.spz` (normalized, if input was convertible format)
- Or `processed/splats/<id>.ply` (if source was .ply-only)
- `docs/asset-index.md` (registry row appended)

**Stages:** 1 (validation/normalization), 6 (registration/export)

**Runtime:** SplatLibrary (Babylon.js 9 native `.ply` / `.splat` / `.spz` support)

**Note:** No Hunyuan generation. Input must be pre-captured. Stage 1 validates format + bounds, optionally converts.

---

### 3. Is it a massive geospatial dataset that streams by camera position (city, region, satellite terrain)?
→ **`tileset`** (3D Tiles standard)

**Examples:** terrain mesh from Cesium Ion, satellite orthotile set, city 3D capture

**Inputs:**
- `--root <URL or path>`: 3D Tiles `tileset.json` root (either remote HTTPS or local file)

**Outputs:**
- `processed/tilesets/<id>.tileset.json` (reference, may be symlink to remote)
- `docs/asset-index.md` (registry row appended)

**Stages:** 1 (validation), 6 (registration/export)

**Runtime:** TilesetMount + 3DTilesRendererJS adapter (Babylon.js + Draco decompression)

**Note:** The orchestrator does not download or copy tileset data; it records the URL/path in the registry. Runtime fetches on demand.

---

### 4. Do you need pathfinding constraints for AI agents or "where the player can walk"?
→ **`navmesh`** (RecastJS output)

**Examples:** walkable terrain, room connectivity graph, compound bounds

**Inputs:**
- `--terrain <GLB path>`: one or more source GLBs (terrain meshes)

**Outputs:**
- `processed/navmeshes/<id>.nav.bin` (RecastJS serialized navmesh)
- `docs/asset-index.md` (registry row appended)

**Stages:** 1 (generate via RecastJSPlugin.createNavMesh), 6 (registration/export)

**Runtime:** `engine/Navigation.ts` (deferred loading on demand)

**Note:** Built from existing GLB(s). Stage 1 parses input GLB, builds navmesh using RecastJS parameters (agent radius, step height, etc.), serializes to binary.

---

### 5. Is it a custom shader for a unique surface (weathered stone, flowing water, procedural texture, particle attractor)?
→ **`nme`** (Node Material Editor JSON)

**Examples:** water shader with flow maps, procedural stone material, particle effect material

**Inputs:**
- `--source <file>`: Node Material Editor `.nme.json` (hand-authored or NME export)

**Outputs:**
- `processed/materials/<id>.nme.json` (registered JSON)
- `docs/asset-index.md` (registry row appended)

**Stages:** 1 (validation), 6 (registration/export)

**Runtime:** MaterialLibrary (Babylon.js NME runtime deserializer)

**Note:** No generation. Source is hand-authored or exported from Babylon NME UI. Stage 1 validates JSON schema, checks for unsupported nodes.

---

### 6. Is it an animated character, animal, or environmental prop with skeletal animation?
→ **`animated`** (Hunyuan3D-generated mesh + Blender skeletal rig + GLTF animation export)

**Examples:** investigator hands (first-person), grandparent spirit figure, animal, NPC

**Inputs:**
- `ref.png`: reference image (hand-dropped or auto-generated) — same as mesh
- `--rig <blend file>`: Blender `.blend` with skeletal rig armature
- Prompt template: at `prompts/asset-templates/<id>.md` (same format as mesh)

**Outputs:**
- `processed/glb/<id>.glb` (LOD0, with embedded AnimationGroup array)
- `processed/glb/<id>.lod1.glb` (LOD1 with animations)
- `processed/glb/<id>.lod2.glb` (LOD2 with animations)
- `processed/glb/<id>.collision.glb`
- `processed/textures/<id>/*.ktx2`
- `docs/asset-index.md` (registry row appended)

**Stages:** 0.25, 0.5 (optional), 1, 2, 2b (optional), 3 (Blender re-rig + bake), 4, 5, 6

**Runtime:** AssetLibrary (instantiate + play AnimationGroup)

**Note:** Stage 1 produces base mesh (like mesh kind). Stage 3 adds Blender rigging step: import rig, re-bake with skinning, export GLTF animations.

---

## Kind Comparison Table

| Kind | Hunyuan | Input | Stages | Output LODs | Collision | Runtime |
|------|---------|-------|--------|-------------|-----------|---------|
| `mesh` | ✓ | ref.png + prompt | 0.25, 0.5, 1, 2, 2b, 3, 4, 5, 6 | 0, 1, 2 + collision | ✓ (hull) | AssetLibrary |
| `splat` | — | .spz/.ply/.sog | 1, 6 | — | — | SplatLibrary |
| `tileset` | — | tileset.json URL | 1, 6 | — | — | TilesetMount |
| `navmesh` | — | terrain GLB(s) | 1, 6 | — | — | Navigation.ts |
| `nme` | — | .nme.json | 1, 6 | — | — | MaterialLibrary |
| `animated` | ✓ | ref.png + prompt + rig | 0.25, 0.5, 1, 2, 2b, 3, 4, 5, 6 | 0, 1, 2 + collision | ✓ (hull) | AssetLibrary |

---

## Stage Mapping per Kind

### Mesh & Animated
```
Stage 0    (optional)  ← generate_ref_image.py (FLUX.1)
Stage 0.25 (default)   ← refine_ref_image.py (FLUX.2)
Stage 0.5  (optional)  ← generate_multi_views.py (Zero123++)
Stage 1                ← generate_asset.py (Hunyuan3D)
Stage 2                ← texture_asset.py (Blender bake)
Stage 2b   (optional)  ← texture_asset.py (ComfyUI projection)
Stage 3                ← optimize_asset.py (Draco/KTX2)
Stage 4                ← generate_lods.py (LOD1/LOD2)
Stage 5                ← generate_collision.py (hull)
Stage 6a               ← register_asset.py
Stage 6b               ← export_babylon.py
```

### Splat, Tileset, NavMesh, NME
```
Stage 1    ← validate_source / normalize_format
Stage 6a   ← register_asset.py
Stage 6b   ← export_babylon.py
```

---

## Template YAML Frontmatter

Every prompt template at `prompts/asset-templates/<id>.md` must have:

```yaml
---
asset_name: <id>                      # e.g., prop_ledger_book
category: <cat>                       # vegetation, structure, prop, figure, animated
era_scope: <era>                      # present, past, shared
reference_image: <id>/ref.png         # path relative to prompts/asset-templates/
seed: NNNNN                           # Hunyuan seed (reproducibility)
inference_steps: NN                   # Hunyuan steps (default 50)
target_poly_lod0: NNNNN               # target face count for LOD0 (use to set simplification target)
materials_runtime:                    # (optional) PBR material family or custom slots
  - mat_leather_ledger
  - mat_paper_aged
collision: convex_hull                # collision strategy (convex_hull, mesh, none)
kind: mesh                            # (optional, default mesh) mesh|splat|tileset|navmesh|nme|animated
notes: |                              # (optional) brief usage notes
  HERO PROP — the title artefact. Player picks it up and examines in ledger UI.
---
```

**Frontmatter fields used by pipeline:**
- `seed`: passed to Hunyuan3D
- `inference_steps`: passed to Hunyuan3D
- `target_poly_lod0`: used by validate_geometry.py (Gate 2) to check face count
- `materials_runtime`: used by texture_asset.py to select material family
- `collision`: used by generate_collision.py (stage 5)
- `era_scope`: passed to register_asset.py → docs/asset-index.md

---

## Kind-Specific CLI Patterns

```fish
# Mesh — most common
python tools/witness.py generate prop_ledger_book
python tools/witness.py generate prop_ledger_book --multi-view --seed 12345

# Splat
python tools/witness.py generate my_splat --kind splat --source captures/site.spz

# Tileset
python tools/witness.py generate terrain_tiles --kind tileset \
    --root https://example.com/3dtiles/terrain/tileset.json

# NavMesh
python tools/witness.py generate compound_walkable --kind navmesh \
    --terrain processed/glb/structure_rugo_main_house.glb

# NME (Node Material)
python tools/witness.py generate water_material --kind nme \
    --source prompts/materials/water_flow.nme.json

# Animated
python tools/witness.py generate figure_grandfather_hands --kind animated \
    --rig prompts/asset-templates/figure_grandfather_hands/rig.blend
```

---

## Asset Registration

**All kinds:** appended to `docs/asset-index.md` as a single row.

**Columns:**
1. Asset ID
2. Kind
3. Path (relative to repo root)
4. Era label (present, past, shared)
5. Source (filename or URL)
6. Registered (date)
7. Faces (from diagnostics, or "n/a")
8. Gates (pass/fail summary, or "n/a")

**Example rows:**
```
| prop_ledger_book | mesh | processed/glb/prop_ledger_book.glb | shared | stage 1 raw output | 2026-05-25 | 8,000 | ✅ 6/6 |
| my_splat | splat | processed/splats/my_splat.spz | present | captures/site.spz | 2026-05-25 | n/a | n/a |
| terrain | tileset | processed/tilesets/terrain.tileset.json | shared | https://example.com/3d/tileset.json | 2026-05-25 | n/a | n/a |
```

---

## Cross-References

- **Normative rule:** [`.claude/rules/asset-pipeline.md`](../../.claude/rules/asset-pipeline.md) — must read before adding any asset
- **Generation stages:** [@generation-stages.md](generation-stages.md) — deep dive into stages 0–6
- **Prompt system:** [@prompts.md](prompts.md) — template authoring, dynamic variables
- **Runtime integration:** [`docs/design-docs/NARRATIVE.md`](../design-docs/NARRATIVE.md) — asset state, interactivity
- **Material families:** [@blender-pipeline.md](blender-pipeline.md) — material library, PBR setup

---

**Last updated:** 2026-05-25 | **See also:** [@orchestrator.md](orchestrator.md), [@tools.md](tools.md)
