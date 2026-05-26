# Asset Generator Architecture — Complete System Documentation

> **Hub & Spoke TOC for the Witness Interactive 3D asset generation system.**
> All asset creation, optimization, validation, and registration flows originate here.

## Overview

The asset generator is a **Python-native orchestration system** that produces publication-ready 3D assets for Witness Interactive 3D. It manages six asset kinds (mesh, splat, tileset, navmesh, nme, animated) through a unified orchestrator, delegating to specialized tools for generation, optimization, validation, and registry management.

**Entry point:** `python tools/witness.py generate <asset_id>`

**Core orchestrator:** `tools/asset_pipeline.py` (normative spec @ `.claude/rules/asset-pipeline.md`)

**Registry:** `docs/asset-index.md` (auto-managed, do not hand-edit)

---

## Table of Contents

### 1. System Architecture & Design
- [@architecture.md](architecture.md) — data flow, component ownership, integration points
- [@orchestrator.md](orchestrator.md) — `witness.py` CLI and `asset_pipeline.py` core logic
- [@asset-kinds.md](asset-kinds.md) — decision tree, stage mapping, kind-specific rules

### 2. Generation Pipeline (Stages 0–6)
- [@generation-stages.md](generation-stages.md) — complete stage breakdown:
  - Stage 0: Reference auto-generation (FLUX.1/FLUX.2)
  - Stage 0.25: Reference refinement (FLUX.2 [klein] img2img)
  - Stage 0.5: Multi-view synthesis (Zero123++)
  - Stage 1: Mesh generation (Hunyuan3D 2.1)
  - Stage 2: PBR texturing & baking (Blender Cycles)
  - Stage 2b: AI material projection (optional, ComfyUI SDXL)
  - Stage 3: Optimization (Draco, KTX2, LOD gen, collision)
  - Stage 4: LOD variant generation
  - Stage 5: Collision hull generation
  - Stage 6: Registration & export

### 3. Tools Reference
- [@tools.md](tools.md) — all 20+ Python tools in `tools/`; signatures, contracts, failure modes
- [@blender-pipeline.md](blender-pipeline.md) — Blender-specific tools (bake_pbr.py, reproject_views.py, etc.)

### 4. Validation System
- [@validation-gates.md](validation-gates.md) — 6-gate validation harness:
  - Gate 0: Input validation
  - Gate 1: Reference image check (stage 0 output)
  - Gate 2: Geometry validation (Hunyuan output)
  - Gate 3: View synthesis validation (stage 0.5)
  - Gate 4: Aggregate diagnostic report
  - Gate 5: PBR texture contract

### 5. Prompts & LLM Orchestration
- [@prompts.md](prompts.md) — prompt system, templates, dynamic variables, style guide
- [@style-guide.md](style-guide.md) — **Digital Diorama** visual language applied to all assets

### 6. Registry & Export
- [@registry-export.md](registry-export.md) — asset registration, versioning, public export to `public/assets/`

---

## Quick Command Reference

```fish
# Server management
python tools/witness.py start                 # ComfyUI + Hunyuan3D
python tools/witness.py start --no-hunyuan    # ComfyUI only
python tools/witness.py stop                  # Stop all
python tools/witness.py status                # Health + model inventory

# Asset generation
python tools/witness.py generate prop_ledger_book                # default mesh
python tools/witness.py generate vegetation_eucalyptus_mature --multi-view
python tools/witness.py generate my_splat --kind splat --source captures/my.spz
python tools/witness.py generate compound_nav --kind navmesh --terrain glb_path

# Batch processing
python tools/witness.py batch prop_altar_candle prop_altar_photo_frame

# List available templates
python tools/witness.py list
```

---

## Architecture Map — Stage Ownership

```
Stage 0    (ref auto-gen)      ← generate_ref_image.py
Stage 0.25 (ref refine)        ← refine_ref_image.py + FLUX.2 [klein]
Stage 0.5  (multi-view)        ← generate_multi_views.py + Zero123++
Stage 1    (mesh gen)          ← generate_asset.py + Hunyuan3D 2.1
Stage 2    (PBR bake)          ← texture_asset.py + blender/bake_pbr.py
Stage 2b   (AI projection)     ← texture_asset.py + ComfyUI SDXL + ControlNet
Stage 3    (optimize)          ← optimize_asset.py (cleanup, draco, KTX2)
Stage 4    (LOD gen)           ← generate_lods.py (gltf-transform)
Stage 5    (collision)         ← generate_collision.py (trimesh convex hull)
Stage 6    (register + export) ← register_asset.py + export_babylon.py
```

**All under orchestration:** `asset_pipeline.py` → `witness.py`

---

## File Structure

```
tools/
├── witness.py                    ← User-facing CLI entry point
├── witness_gui.py                ← TBD GUI wrapper
├── asset_pipeline.py             ← Core orchestrator (normative spec)
├── generate_ref_image.py          ← Stage 0: FLUX.1 ref generation
├── refine_ref_image.py            ← Stage 0.25: FLUX.2 img2img refinement
├── generate_asset.py              ← Stage 1: Hunyuan3D 2.1 API client
├── generate_multi_views.py        ← Stage 0.5: Zero123++ multi-view
├── texture_asset.py               ← Stage 2 + 2b: PBR baking + AI projection
├── optimize_asset.py              ← Stage 3: Draco, KTX2, cleanup
├── generate_lods.py               ← Stage 4: LOD1/LOD2 generation
├── generate_collision.py           ← Stage 5: Convex hull generation
├── register_asset.py              ← Stage 6a: Registry append
├── export_babylon.py              ← Stage 6b: Copy to public/assets/
├── validate_*.py                  ← Validation gates (5 validators)
├── diagnostic_report.py           ← Aggregates validation results
├── blender/
│   ├── bake_pbr.py               ← Blender headless: PBR bake (stage 2)
│   ├── reproject_views.py         ← Blender headless: UV reproject (stage 2b prep)
│   ├── material_families.py       ← Material library + procedural defaults
│   ├── render_validation.py       ← View-space diagnostic renders
│   └── ...
└── hunyuan_patch/
    └── model_worker.py           ← Patched Hunyuan multiview handler
```

```
prompts/
├── asset-templates/
│   ├── <id>.md                   ← Prompt template (YAML frontmatter + description)
│   ├── <id>/
│   │   ├── ref.png / ref.jpg     ← Hand-dropped or auto-generated reference
│   │   ├── ref.original.png      ← Archive copy (stage 0.25 audit)
│   │   └── README.md             ← Per-asset notes
│   └── _STYLE_GUIDE.md           ← **Digital Diorama** design system
├── _flux_workflows/
│   ├── default.json              ← Stage 0 default FLUX.1 workflow
│   ├── hero.json                 ← Stage 0 hero-asset FLUX.1 variant
│   └── refine.json               ← Stage 0.25 FLUX.2 [klein] img2img
└── _pbr_workflows/
    ├── sdxl_depth_pbr.json       ← Stage 2b SDXL + ControlNet (depth)
    └── flux2_klein_pbr.json      ← Alternative FLUX.2-based projection
```

---

## Key Concepts

### Asset ID Naming Pattern

All assets follow `<category>_<name>[_<variant>]`:
- `category`: one of {vegetation, structure, prop, figure, animated, ...}
- `name`: descriptive snake_case identifier
- `variant`: optional suffix for family variants

**Examples:** `prop_ledger_book`, `vegetation_eucalyptus_mature`, `structure_rugo_main_house`

### Era Tagging

Every asset is tagged with an era scope:
- `present`: 2026 investigator era only
- `past`: 1994 witness era only
- `shared`: both eras

Applied at runtime via `tagNode()` / `tagLight()` in `CHRONOS_SWITCH.md` system.

### Asset Kinds (Decision Tree)

| Kind | Input | Hunyuan | Output | Runtime Owner |
|------|-------|---------|--------|--------------|
| `mesh` | ref.png + prompt | ✓ | GLB (3 LODs + collision) | AssetLibrary |
| `splat` | .spz/.ply/.sog | — | normalized splat | SplatLibrary |
| `tileset` | 3D Tiles root URL | — | tileset.json ref | TilesetMount |
| `navmesh` | terrain GLB(s) | — | .nav.bin RecastJS output | Navigation.ts |
| `nme` | Node Material Editor JSON | — | .nme.json registered | MaterialLibrary |
| `animated` | ref.png + prompt + rig | ✓ | GLB with animations | AssetLibrary |

### OpenPBR Material Standard

All mesh & animated outputs use **OpenPBR** (metallic-roughness):
- **Albedo** (sRGB): base color, per-texel
- **Normal** (OpenGL Y+): surface-space normal
- **Metallic-Roughness** (packed): R=unused, G=roughness, B=metallic
- **Ambient Occlusion** (optional): baked shadow

Compression: UASTC for normals, ETC1S for color/MR. KTX2 container.

---

## Critical Paths & Decision Points

### When to regenerate?

- **Swap the reference image** → delete `ref.png` + `ref.original.png` → re-run stage 0.25
- **Tweak the seed** → re-run stage 1 (Hunyuan3D) with new `--seed`
- **Change material prompt** → re-run stage 2 (Blender bake)
- **Adjust LOD targets** → re-run stage 4 (gltf-transform simplify)
- **Fix collision** → re-run stage 5 (trimesh convex hull)

### When does stage 0.25 trigger?

- Automatically on every `mesh` / `animated` run
- Reads from `ref.original.png` if present (denoise doesn't compound)
- Skipped with `--no-refine-ref` flag

### Validation failure recovery

If a gate fails, the aggregate diagnostic (`processed/diagnostics/<id>.aggregate.json`) recommends:
- `retry_with_new_seed`: bump seed by `RETRY_SEED_STRIDE` (10,000)
- `retry_with_refined_ref`: re-run stage 0.25 + 1 with fresh seed
- `pass` / `fail`: gates passed or require manual intervention

---

## Performance & VRAM Budgets

**RTX 5090 (32 GB VRAM), target Phase 1 assets:**

- **Stage 0 (Flux.1):** ~6 GB, ~90s per image
- **Stage 0.25 (Flux.2 [klein]):** ~3 GB, ~20s per image
- **Stage 0.5 (Zero123++):** ~8 GB, ~60s for 6 views
- **Stage 1 (Hunyuan3D):** ~25 GB at octree_resolution 512, ~8–15 min per mesh
- **Stage 2 (Blender Cycles):** ~5 GB, ~5–10 min per asset
- **Stages 3–6:** CPU-bound, < 1 min combined

**Total single-asset time:** 30–40 minutes (mesh with AI projection) or 20–30 minutes (mesh + procedural PBR)

---

## Cross-References

- **Normative rule:** [`.claude/rules/asset-pipeline.md`](../../.claude/rules/asset-pipeline.md)
- **Design spec:** [`docs/design-docs/ASSET_PIPELINE.md`](../design-docs/ASSET_PIPELINE.md)
- **Babylon.js runtime:** `AssetLibrary`, `SplatLibrary`, `TilesetMount` in `witness-interactive-vite/src/io/`
- **Narrative integration:** [`docs/design-docs/NARRATIVE.md`](../design-docs/NARRATIVE.md) — asset triggers, state changes
- **Rendering & materials:** [`docs/design-docs/RENDERING.md`](../design-docs/RENDERING.md) — post-processing, material families
- **Era system:** [`docs/design-docs/CHRONOS_SWITCH.md`](../design-docs/CHRONOS_SWITCH.md) — runtime era tagging

---

## For Developers

### Adding a new asset

1. Choose asset id (`<category>_<name>[_<variant>]`)
2. Author prompt template at `prompts/asset-templates/<id>.md` (YAML frontmatter + description)
3. Drop reference image at `prompts/asset-templates/<id>/ref.png` (or auto-gen with `--auto-ref`)
4. Run: `python tools/witness.py generate <id> [--kind mesh] [--multi-view] [...]`
5. Check diagnostics: `cat processed/diagnostics/<id>.aggregate.json`
6. Verify registry entry: `cat docs/asset-index.md | tail -1`
7. Confirm public copy: `ls witness-interactive-vite/public/assets/<id>*`
8. Update CHANGELOG: `docs/decisions/CHANGELOG_DETAILED.md`

### Debugging a generation failure

```fish
# Check which stage failed
cat processed/diagnostics/<id>.aggregate.json

# Re-run with verbose output
python tools/asset_pipeline.py <id> --kind mesh --image prompts/asset-templates/<id>/ref.png

# Check server logs
tail -100 /tmp/comfyui.log
docker logs witness-hunyuan 2>&1 | tail -100

# Inspect intermediate artefacts
ls -la processed/views/<id>/              # Stage 2 6-view renders
ls -la processed/textures/<id>/           # Stage 2 baked maps
ls -la processed/glb/raw/<id>.glb         # Stage 1 raw Hunyuan output
```

---

**Documentation updated:** 2026-05-25 | **Next review:** after M20 audio integration
