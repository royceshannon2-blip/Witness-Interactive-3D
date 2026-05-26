# Tools Reference — Complete Directory

> Complete documentation of all 20+ Python tools in `tools/`. Each entry covers signature, inputs/outputs, failure modes, dependencies.
> See [@claude.md](claude.md), [@architecture.md](architecture.md), [@generation-stages.md](generation-stages.md).

---

## Orchestration Tools

### witness.py — User-Facing CLI

**Purpose:** Server management, template discovery, pipeline delegation
**Entry point:** `python tools/witness.py <command> [options]`

See [@orchestrator.md](orchestrator.md) for detailed documentation.

**Commands:**
- `start [--no-hunyuan|--no-comfy]` — boot services
- `stop [--no-hunyuan|--no-comfy]` — stop services
- `status` — health check + model inventory
- `generate <id> [--kind] [--multi-view] [--seed] [...]` — single asset
- `batch <id1> <id2> ... [--skip-failed]` — sequential batch
- `list` — show templates
- `gui` — TBD GUI wrapper

**Key functions:**
- `_comfy_alive()` — HTTP health check ComfyUI
- `_hunyuan_alive()` — HTTP health check Hunyuan3D
- `_start_comfyui()` — subprocess.Popen with log
- `_start_hunyuan()` — docker run with privileged flag
- `detect_models()` — query ComfyUI model inventory
- `list_templates()` — glob prompts/asset-templates/*.md

**Dependencies:** requests, subprocess, pathlib

---

### asset_pipeline.py — Core Orchestrator (Normative Spec)

**Purpose:** Stage sequencing, kind dispatch, validation integration, registry management
**Entry point:** `python tools/asset_pipeline.py <asset_id> --kind <kind> [stage-specific args]`

See [@orchestrator.md](orchestrator.md) for detailed documentation.

**Key classes:**
- `PipelineContext(dataclass)` — mutable state across stages
- `Pipeline` — orchestrator methods

**Key functions:**
- `validate_id()` — enforce snake_case, ≥ 3 chars
- `refine_strength_for()` — category-aware denoise strength lookup
- `run_mesh_pipeline()` — full mesh generation flow
- `run_splat_pipeline()` — splat validation + registration
- `run_tileset_pipeline()` — tileset reference registration
- `run_navmesh_pipeline()` — navmesh generation from terrain
- `run_nme_pipeline()` — NME JSON validation + registration
- `run_animated_pipeline()` — mesh + Blender rigging

**Constants:**
- `VALID_KINDS` — allowed asset kinds
- `VALID_ERAS` — present, past, shared
- `RETRY_SEED_STRIDE` — 10,000 (seed increment for auto-retry)
- `REFINE_STRENGTH_BY_CATEGORY` — denoise strength per category
- `SPLAT_EXTS` — valid splat file extensions

**Exit codes:** 0 (ok), 2 (generation failed), 3 (registration failed)

**Dependencies:** subprocess, json, yaml, pathlib, datetime

---

## Generation Tools

### generate_ref_image.py — Stage 0 Reference Generation

**Purpose:** Auto-generate reference image from asset description using FLUX.1
**Entry point:** `python tools/generate_ref_image.py <asset_id> [--prompt] [--seed] [--workflow default|hero]`

**Inputs:**
- `asset_id`: snake_case id (e.g., prop_ledger_book)
- `--prompt`: override prompt (default: read from template description)
- `--seed`: reproducibility seed (default: random)
- `--workflow`: FLUX.1 workflow variant (default | hero)

**Outputs:**
- `prompts/asset-templates/<asset_id>/ref.png` (2K PNG)

**Process:**
1. Load FLUX.1 workflow JSON (default.json or hero.json)
2. Encode prompt into workflow
3. POST to ComfyUI, poll until complete
4. Decode base64 response, save PNG

**Failure modes:**
- ComfyUI not running → exit 2
- FLUX.1 model missing → exit 2
- Prompt too vague → inspect output, retry with refined prompt

**Duration:** 60–90 seconds | **VRAM:** 6 GB

**Dependencies:** requests, base64, PIL, pathlib

---

### refine_ref_image.py — Stage 0.25 Reference Refinement

**Purpose:** Refine reference image to Digital Diorama style using FLUX.2 [klein] img2img
**Entry point:** `python tools/refine_ref_image.py <ref_image_path> <asset_id> [--strength 0.0..1.0]`

**Inputs:**
- `ref_image_path`: path to ref.png
- `asset_id`: for archiving + strength lookup
- `--strength`: denoise strength (default: auto from category)

**Outputs:**
- `prompts/asset-templates/<asset_id>/ref.png` (refined, overwrites)
- `prompts/asset-templates/<asset_id>/ref.original.png` (archive copy)

**Process:**
1. Archive ref.png → ref.original.png
2. Load FLUX.2 [klein] img2img workflow
3. Encode ref.png as input image
4. Set denoise strength
5. POST to ComfyUI, poll until complete
6. Overwrite ref.png with refined output

**Denoise strength by category:**
- `vegetation_`: 0.60 (push palette hard)
- `structure_`: 0.40 (preserve geometry)
- `prop_`: 0.50 (balance)
- `figure_`: 0.50 (anatomy)
- Default: 0.50

**Failure modes:**
- FLUX.2 model missing → exit 2
- Input image corrupted → exit 2

**Duration:** 15–25 seconds | **VRAM:** 3 GB

**Dependencies:** requests, PIL, pathlib

---

### generate_multi_views.py — Stage 0.5 Multi-View Synthesis

**Purpose:** Generate 6 canonical orthogonal views from single reference using Zero123++
**Entry point:** `python tools/generate_multi_views.py <ref_image_path> <asset_id> [--seed]`

**Inputs:**
- `ref_image_path`: path to ref.png
- `asset_id`: for output directory
- `--seed`: reproducibility (default: 481116)

**Outputs:**
- `processed/views/<asset_id>/{front,back,left,right,top,bottom}.png` (2K each)

**Canonical orientations:**
- `front` (0°, 0°)
- `right` (0°, 270°)
- `back` (0°, 180°)
- `left` (0°, 90°)
- `top` (90°, 0°) overhead
- `bottom` (-90°, 0°) underside

**Process:**
1. Load Zero123++ model (diffusers pipeline)
2. Load ref.png as PIL Image
3. For each canonical view: call pipeline with elevation/azimuth
4. Save each view PNG

**Failure modes:**
- Zero123++ weights missing → exit 2
- Seed mismatch (non-deterministic)

**Duration:** 50–70 seconds for 6 views | **VRAM:** 8 GB

**Dependencies:** diffusers, torch, PIL, numpy, pathlib

---

### generate_asset.py — Stage 1 Mesh Generation (Hunyuan3D)

**Purpose:** Submit reference to Hunyuan3D 2.1 API server, poll until mesh generated
**Entry point:** `python tools/generate_asset.py <ref_image_path> <asset_id> [--steps] [--seed] [--octree-resolution] [--view] [...]`

**Inputs:**
- `ref_image_path`: reference PNG/JPG
- `asset_id`: output naming
- `--steps`: inference steps (default 50, range 20–80)
- `--seed`: reproducibility (default 1234)
- `--octree-resolution`: 512 (standard) or 768 (hero, higher VRAM)
- `--view <path>`: multi-view PNGs (repeatable, ≤ 6)
- `--guidance-scale`: classifier-free guidance (default 8.0)

**Outputs:**
- `processed/glb/raw/<asset_id>.glb` (200K–900K faces, unoptimized)

**API:**
- POST `/send` → uid
- GET `/status/{uid}` → status + model_base64

**Failure modes:**
- Hunyuan3D not running → exit 1
- OOM (octree_resolution too high) → silent fail, 0-byte sentinel → exit 1
- Ref image bad quality → degenerate mesh (flat) → caught by Gate 2

**Duration:** 8–15 minutes | **VRAM:** 25 GB peak

**Dependencies:** requests, base64, pathlib

---

## Optimization & Processing Tools

### optimize_asset.py — Stage 3 GLB Optimization

**Purpose:** Draco compression, KTX2 texture compression, detached-component cleanup, simplification
**Entry point:** `python tools/optimize_asset.py <raw_glb_path> [--target-faces] [--max-texture-size] [--draco-level] [--no-cleanup] [--no-ktx2]`

**Inputs:**
- `raw_glb_path`: processed/glb/raw/<id>.glb
- `--target-faces`: decimation target (default from template)
- `--max-texture-size`: texture downscale cap (default 8192)
- `--draco-level`: 0–7 (default 7, maximum)
- `--no-cleanup`: skip detached-component stripping
- `--no-ktx2`: skip KTX2 compression (keep PNG)

**Outputs:**
- `processed/glb/<asset_id>.glb` (optimized, 70–90% size reduction)
- Updated texture maps in `processed/textures/<asset_id>/` (KTX2)

**Process:**
1. Strip detached components (trimesh)
   - Keep components ≥ 1% of largest volume
2. Simplify to target face count (gltf-transform)
3. Compress textures (KTX2: UASTC normals, ETC1S color)
4. Apply Draco geometry compression

**Failure modes:**
- gltf-transform not found → exit 1
- trimesh load fails → skip cleanup, continue
- KTX2 encoder missing → exit 1

**Duration:** 2–3 minutes | **VRAM:** < 2 GB

**Dependencies:** trimesh, subprocess (gltf-transform, KTX2 encoder), PIL, numpy, pathlib

---

### generate_lods.py — Stage 4 LOD Generation

**Purpose:** Generate LOD1 (50% faces) and LOD2 (15% faces) from LOD0
**Entry point:** `python tools/generate_lods.py <lod0_glb_path> [--draco-level 7] [--force]`

**Inputs:**
- `lod0_glb_path`: processed/glb/<id>.glb (optimized)
- `--draco-level`: compression level (default 7)
- `--force`: overwrite existing LODs

**Outputs:**
- `processed/glb/<id>.lod1.glb` (50% faces, 2K textures)
- `processed/glb/<id>.lod2.glb` (15% faces, 512 textures)

**LOD specs:**
- LOD0 (0–15 m): full detail, 8K textures
- LOD1 (15–50 m): 50% faces, 2K textures
- LOD2 (50+ m): 15% faces, 512 textures

**Process:**
1. For each LOD spec: simplify geometry (gltf-transform)
2. Downscale textures to tier-appropriate resolution
3. Apply Draco compression (consistent with LOD0)

**Failure modes:**
- gltf-transform not installed → exit 1
- Simplification fails (degenerate mesh) → skip that LOD

**Duration:** 1–2 minutes | **VRAM:** < 2 GB

**Dependencies:** subprocess (gltf-transform), pathlib

---

### generate_collision.py — Stage 5 Collision Hull Generation

**Purpose:** Generate convex hull from mesh for physics collision
**Entry point:** `python tools/generate_collision.py <source_glb_path> <asset_id> [--source-is-textured]`

**Inputs:**
- `source_glb_path`: processed/glb/<id>.glb (optimized)
- `asset_id`: output naming
- `--source-is-textured`: hint to use textured GLB if Draco decode fails

**Outputs:**
- `processed/glb/<asset_id>.collision.glb` (convex hull, simple geometry)

**Process:**
1. Load source GLB (may be Draco-compressed)
   - If decode fails: fallback to textured GLB
2. Extract all mesh geometry
3. Compute combined convex hull (trimesh)
4. Export to collision GLB

**Collision strategy** (from template):
- `convex_hull`: bounding polyhedron
- `mesh`: export original geometry as-is
- `none`: skip

**Failure modes:**
- trimesh not installed → exit 1
- Both source + textured GLB missing → exit 2
- Draco decompression fails → fallback, continue

**Duration:** < 30 seconds | **VRAM:** < 1 GB

**Dependencies:** trimesh, pathlib

---

## Registration & Export Tools

### register_asset.py — Stage 6a Asset Registration

**Purpose:** Append asset row to docs/asset-index.md
**Entry point:** `python tools/register_asset.py <asset_id> <era> [--glb-path] [--kind mesh] [--source <str>] [--diagnostics-dir]`

**Inputs:**
- `asset_id`: snake_case id
- `era`: present|past|shared
- `--glb-path`: GLB location (default: processed/glb/<id>.glb)
- `--kind`: asset kind (default: mesh)
- `--source`: provenance string (default: GLB filename)
- `--diagnostics-dir`: where to find gate reports (default: processed/diagnostics)

**Outputs:**
- Appended row in `docs/asset-index.md`

**Registry row format:**
```
| prop_ledger_book | mesh | processed/glb/prop_ledger_book.glb | shared | ... | 2026-05-25 | 8,000 | ✅ 6/6 |
```

**Process:**
1. Read face count from `<id>.geometry.json` (Gate 2 report)
2. Read gate status from `<id>.aggregate.json` (Gate 4 report)
3. Format markdown row
4. Append to registry

**Fallbacks:** missing diagnostics → report "n/a"

**Failure modes:**
- `docs/asset-index.md` not writable → exit 3
- Diagnostic JSON missing → use "n/a", continue

**Duration:** < 1 second

**Dependencies:** pathlib, datetime, json

---

### export_babylon.py — Stage 6b Public Export

**Purpose:** Copy optimized GLBs to witness-interactive-vite/public/assets/ for runtime loading
**Entry point:** `python tools/export_babylon.py <asset_id> [--glb] [--lod1] [--lod2] [--collision]`

**Inputs:**
- `asset_id`: target asset
- `--glb`: LOD0 path (default: processed/glb/<id>.glb)
- `--lod1`: LOD1 path (default: processed/glb/<id>.lod1.glb)
- `--lod2`: LOD2 path (default: processed/glb/<id>.lod2.glb)
- `--collision`: collision hull path (default: processed/glb/<id>.collision.glb)

**Outputs:**
- `witness-interactive-vite/public/assets/<id>.glb`
- `witness-interactive-vite/public/assets/<id>.lod1.glb`
- `witness-interactive-vite/public/assets/<id>.lod2.glb`
- `witness-interactive-vite/public/assets/<id>.collision.glb` (optional)

**Process:**
1. Create dest dir if missing
2. For each input GLB: copy to public/assets/
3. Skip missing files

**Failure modes:**
- `witness-interactive-vite/public/assets/` not writable → exit 3
- Source GLB missing → skip, continue

**Duration:** < 5 seconds

**Dependencies:** shutil, pathlib

---

## Validation & Diagnostic Tools

See [@validation-gates.md](validation-gates.md) for detailed gate documentation.

### validate_geometry.py — Gate 2 Geometry Validation

### validate_pbr.py — Gate 5 PBR Texture Validation

### validate_views.py — Gate 3 Multi-View Validation

### validate_ref_image.py — Gate 1 Reference Image Validation

### diagnostic_report.py — Gate 4 Aggregate Diagnostic

---

## Utility & Diagnostic Tools

### validate_fragments.py

**Purpose:** Validate narrative graph fragments (not part of asset pipeline)

---

### diagnostic_report.py — Aggregate Diagnostics

**Purpose:** Collect all gate JSON sidecars and produce aggregate diagnostic recommendation
**Entry point:** `python tools/diagnostic_report.py <asset_id> [--diagnostics-dir] [--output-path]`

**Inputs:**
- `asset_id`: target asset
- `--diagnostics-dir`: where gate reports live (default: processed/diagnostics)

**Outputs:**
- `processed/diagnostics/<asset_id>.aggregate.json`

```json
{
  "asset_id": "prop_ledger_book",
  "gates_ran": ["1", "2", "3", "4", "5"],
  "gates_failed": [],
  "recommended_action": "pass",
  "summary": "All gates passed"
}
```

**Recommended action values:**
- `pass`: all gates succeeded
- `retry_with_new_seed`: Gate 2 geometry failed → bump seed, re-run stage 1
- `retry_with_refined_ref`: ref image issue → re-run stage 0.25
- `fail`: gates failed, requires manual intervention

**Dependencies:** json, pathlib

---

## Blender Tools

See [@blender-pipeline.md](blender-pipeline.md) for detailed documentation.

### blender/bake_pbr.py — Stage 2 PBR Baking

### blender/reproject_views.py — Stage 2b Projection Prep

### blender/material_families.py — Material Library

### blender/render_validation.py — Diagnostic Renders

---

**Last updated:** 2026-05-25 | **See also:** [@generation-stages.md](generation-stages.md), [@validation-gates.md](validation-gates.md), [@blender-pipeline.md](blender-pipeline.md)
