# System Architecture — Asset Generator

> Data flow, component ownership, and integration contracts for the Witness asset generation pipeline.
> See [@claude.md](claude.md) for the full hub.

---

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        User CLI (witness.py)                            │
│  start | stop | status | generate | list | batch | gui                 │
└──────────────────────────┬──────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                 Asset Pipeline Orchestrator                             │
│              (asset_pipeline.py — normative spec)                       │
│                                                                         │
│  • Asset kind dispatch (mesh, splat, tileset, navmesh, nme, animated)  │
│  • Stage sequencing (0 → 0.25 → 0.5 → 1 → 2 → 2b → 3 → 4 → 5 → 6)   │
│  • Server health checks + VRAM scheduling                              │
│  • Validation gate integration                                         │
│  • Registry row append + export                                        │
└──────────────────────────┬──────────────────────────────────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
        ▼                  ▼                  ▼
  ┌──────────┐   ┌──────────────┐   ┌──────────────┐
  │  Mesh    │   │   Splat /    │   │  Tileset /   │
  │          │   │  Tileset /   │   │  NavMesh /   │
  │  Pipeline│   │  NavMesh /   │   │  NME         │
  │          │   │  NME Branch  │   │              │
  │  (Stages │   │              │   │  (1–2 stages)│
  │   0–6)   │   │  (1–2 stages)│   │              │
  └────┬─────┘   └──────┬───────┘   └──────┬───────┘
       │                │                   │
       │                │                   │
       ▼                ▼                   ▼
┌────────────────────────────────────────────────────────┐
│          Generation + Optimization Tools               │
│                                                        │
│ [Stage 0] generate_ref_image.py (FLUX.1)             │
│ [Stage 0.25] refine_ref_image.py (FLUX.2)            │
│ [Stage 0.5] generate_multi_views.py (Zero123++)      │
│ [Stage 1] generate_asset.py (Hunyuan3D 2.1)          │
│ [Stage 2] texture_asset.py (Blender + optional AI)   │
│ [Stage 3] optimize_asset.py (Draco/KTX2/cleanup)     │
│ [Stage 4] generate_lods.py (gltf-transform)          │
│ [Stage 5] generate_collision.py (trimesh hull)       │
│ [Stage 6] register_asset.py + export_babylon.py      │
└────────────────────────────────────────────────────────┘
       │
       ▼
┌────────────────────────────────────────────────────────┐
│             Validation Gate System                     │
│                                                        │
│ Gate 0 – Input validation (asset id, paths, env)     │
│ Gate 1 – Ref image validation (stage 0 output)       │
│ Gate 2 – Geometry validation (stage 1 output)        │
│ Gate 3 – View synthesis validation (stage 0.5)       │
│ Gate 4 – Aggregate diagnostics (all sidecars)        │
│ Gate 5 – PBR texture contract (stage 2 output)       │
│                                                        │
│ Handlers: validate_*.py + diagnostic_report.py       │
└────────────────────────────────────────────────────────┘
       │
       ▼
┌────────────────────────────────────────────────────────┐
│            Output Artifacts & Registry                │
│                                                        │
│ processed/glb/<id>.glb (+ .lod1.glb, .lod2.glb)      │
│ processed/glb/<id>.collision.glb                      │
│ processed/textures/<id>/ (albedo, normal, mr, ao)    │
│ processed/views/<id>/ (6 canonical renders)          │
│ processed/diagnostics/<id>.*.json (gate reports)     │
│                                                        │
│ docs/asset-index.md (registry — append-only)         │
│ witness-interactive-vite/public/assets/<id>.* (export)│
└────────────────────────────────────────────────────────┘
```

---

## Component Ownership Map

### Core Orchestration

| Module | Responsibility | Exit Code |
|--------|----------------|-----------|
| `witness.py` | CLI entry point, server management, template discovery | 0 (success) or 1 (fail) |
| `asset_pipeline.py` | Stage sequencing, kind dispatch, validation integration, registry + export | 0 (ok), 2 (gen fail), 3 (reg fail) |

### Generation Stages

| Stage | Tool(s) | Input | Output | Exit Code on Fail |
|-------|---------|-------|--------|-------------------|
| 0 | `generate_ref_image.py` | asset id, prompt template, optional seed | `prompts/asset-templates/<id>/ref.png` | 2 |
| 0.25 | `refine_ref_image.py` | ref.png, denoise strength | refined ref.png, archive copy | 2 |
| 0.5 | `generate_multi_views.py` | ref.png, seed | 6 canonical view PNGs | 2 |
| 1 | `generate_asset.py` | ref.png (+ optional 6 views), prompt, Hunyuan params | `processed/glb/raw/<id>.glb` | 2 |
| 2 | `texture_asset.py` (→ `blender/bake_pbr.py`) | raw GLB, material family, asset id | PBR maps + textured GLB | 2 |
| 2b | `texture_asset.py` (→ ComfyUI) | 6 view renders, depth maps, asset prompt | AI-projected albedo maps | 2 |
| 3 | `optimize_asset.py` | textured GLB, target face count, texture caps | Draco + KTX2 GLB(s), collision GLB | 2 |
| 4 | `generate_lods.py` | LOD0 GLB, simplification ratios | LOD1 + LOD2 GLBs | 2 |
| 5 | `generate_collision.py` | optimized GLB (source for hull) | collision hull GLB | 2 |
| 6a | `register_asset.py` | asset id, era, kind, GLB path, diagnostics | appended row in `docs/asset-index.md` | 3 |
| 6b | `export_babylon.py` | asset id, kind | copy to `witness-interactive-vite/public/assets/` | 3 |

### Validation System

| Gate | Validator | Input | Output | Trigger | Exit Code |
|------|-----------|-------|--------|---------|-----------|
| 0 | `asset_pipeline.py` (inline) | asset id, kind, args | validation or early exit | before stage 0 | 1 |
| 1 | `validate_ref_image.py` | ref.png | report JSON + exit | after stage 0 / 0.25 | 0 (warn) or 2 (fail) |
| 2 | `validate_geometry.py` | raw GLB | report JSON + exit | after stage 1 | 0 (warn) or 2 (fail) |
| 3 | `validate_views.py` | 6 view renders + depth maps | report JSON + exit | after stage 0.5 | 0 (warn) or 2 (fail) |
| 4 | `diagnostic_report.py` | all gate JSON sidecars | aggregate JSON + stdout | after each gate | 0 (all gates) |
| 5 | `validate_pbr.py` | PBR maps (albedo, normal, mr) | report JSON + exit | after stage 2 | 0 (warn) or 2 (fail) |

### Blender Integration

| Tool | Stage | Purpose | Input | Output |
|------|-------|---------|-------|--------|
| `blender/bake_pbr.py` | 2 | PBR texture baking | raw GLB + material family | 6-view renders + baked textures |
| `blender/reproject_views.py` | 2b prep | UV reprojection setup | baked maps + canonical views | projection-ready mesh state |
| `blender/material_families.py` | 2 | Material library | asset family tag | Principled BSDF parameters |
| `blender/render_validation.py` | post-2 | Diagnostic renders | optimized GLB | beauty + normal + depth EXRs |

---

## Data Flow — Mesh Asset (Typical Path)

```
1. User runs: python tools/witness.py generate prop_ledger_book

2. witness.py:
   • Load template: prompts/asset-templates/prop_ledger_book.md (YAML + description)
   • Confirm server health (ComfyUI + Hunyuan3D)
   • Delegate to asset_pipeline.py

3. asset_pipeline.py (pseudo-flow):
   
   Stage 0.25 [ref refine]:
   • Check: ref.png exists? If not, run stage 0 first.
   • refine_ref_image.py: FLUX.2 [klein] img2img (unless --no-refine-ref)
   • Output: prompts/asset-templates/prop_ledger_book/ref.png + .original.png
   
   [Gate 1] validate_ref_image.py → processed/diagnostics/prop_ledger_book.ref_image.json
   
   [Optional] Stage 0.5 [multi-view]:
   • generate_multi_views.py: Zero123++ (6 canonical views)
   • Output: processed/views/prop_ledger_book/{front,back,left,right,top,bottom}.png
   
   [Gate 3] validate_views.py → processed/diagnostics/prop_ledger_book.views.json
   
   Stage 1 [mesh gen]:
   • generate_asset.py: POST to Hunyuan3D /send with ref.png (+ optional 6 views)
   • Poll /status/{uid} until completed
   • Output: processed/glb/raw/prop_ledger_book.glb (~200K–900K faces)
   
   [Gate 2] validate_geometry.py → processed/diagnostics/prop_ledger_book.geometry.json
   
   Stage 2 [PBR bake]:
   • texture_asset.py → blender/bake_pbr.py (headless Blender)
   • Render 6 canonical views (beauty + 16-bit depth EXR)
   • Bake Albedo / Normal / MR / AO @ 8K
   • Smart UV unwrap (if missing)
   • Output:
     - processed/glb/prop_ledger_book.textured.glb
     - processed/textures/prop_ledger_book/{albedo,normal,mr}.ktx2
     - processed/views/prop_ledger_book/*.exr (16-bit depth)
   
   [Optional Stage 2b] AI projection (--ai-project):
   • texture_asset.py → ComfyUI: SDXL + ControlNet (depth-guided)
   • Repaint Albedo from projected material maps
   • Re-bake at 8K with new Albedo
   
   [Gate 5] validate_pbr.py → processed/diagnostics/prop_ledger_book.pbr.json
   
   Stage 3 [optimize]:
   • optimize_asset.py:
     1. Strip detached components (trimesh)
     2. Weld + simplify to target_poly_lod0 (~8000 faces for hero)
     3. Compress textures (UASTC normals, ETC1S colour)
     4. Apply Draco geometry compression
   • Output: processed/glb/prop_ledger_book.glb (optimized)
   
   Stage 4 [LOD gen]:
   • generate_lods.py: gltf-transform simplify
   • LOD1 (50% faces) → prop_ledger_book.lod1.glb
   • LOD2 (15% faces) → prop_ledger_book.lod2.glb
   
   Stage 5 [collision]:
   • generate_collision.py: trimesh convex hull from optimized GLB
   • Output: processed/glb/prop_ledger_book.collision.glb
   
   [Gate 4] diagnostic_report.py: aggregate all gate reports
   → processed/diagnostics/prop_ledger_book.aggregate.json
   
   Stage 6a [register]:
   • register_asset.py: append row to docs/asset-index.md
   • Extract face count from gate 2 report
   • Extract gate status from gate 4 report
   • Row: | prop_ledger_book | mesh | processed/glb/... | shared | ... | 2026-05-25 | 8,000 | ✅ 6/6 |
   
   Stage 6b [export]:
   • export_babylon.py: copy artefacts to public/assets/
   • prop_ledger_book.glb → witness-interactive-vite/public/assets/
   • prop_ledger_book.lod1.glb → witness-interactive-vite/public/assets/
   • prop_ledger_book.lod2.glb → witness-interactive-vite/public/assets/

4. Success:
   • Runtime loads via AssetLibrary.instantiate("prop_ledger_book")
   • Babylon.js applies LOD selection (0–15m, 15–50m, 50+m)
   • Camera tags applied via tagNode() (CHRONOS_SWITCH.md)
```

---

## State & Artifact Layout

### Processed Directory Structure

```
processed/
├── glb/
│   ├── raw/                      ← Stage 1 raw Hunyuan output
│   │   └── <id>.glb
│   └── <id>.glb                  ← Stage 3 final optimized mesh (LOD0)
│   └── <id>.lod1.glb             ← Stage 4 LOD1
│   └── <id>.lod2.glb             ← Stage 4 LOD2
│   └── <id>.collision.glb        ← Stage 5 collision hull
├── textures/
│   └── <id>/
│       ├── albedo.ktx2           ← Stage 2/2b output (8K ETC1S)
│       ├── normal.ktx2           ← Stage 2 output (8K UASTC)
│       ├── mr.ktx2               ← Stage 2 output (8K ETC1S), R unused / G roughness / B metallic
│       └── ao.ktx2               ← Stage 2 output (optional 8K ETC1S)
├── views/
│   └── <id>/
│       ├── front.png             ← Stage 0.5 canonical view (2K)
│       ├── back.png
│       ├── left.png
│       ├── right.png
│       ├── top.png
│       ├── bottom.png
│       ├── front_depth.exr       ← Stage 2 16-bit depth (for projection)
│       ├── back_depth.exr
│       └── ... (all 6 views × 2 = 12 files)
├── splats/                       ← Splat assets (kind: splat)
│   └── <id>.spz
├── tilesets/                     ← Tileset references (kind: tileset)
│   └── <id>.tileset.json
├── navmeshes/                    ← Navigation meshes (kind: navmesh)
│   └── <id>.nav.bin
├── materials/                    ← Node Material Editor (kind: nme)
│   └── <id>.nme.json
└── diagnostics/
    └── <id>.*.json               ← Gate reports + aggregate diagnostic
        ├── <id>.ref_image.json   ← Gate 1 report
        ├── <id>.geometry.json    ← Gate 2 report
        ├── <id>.views.json       ← Gate 3 report
        ├── <id>.pbr.json         ← Gate 5 report
        └── <id>.aggregate.json   ← Gate 4 aggregate
```

### Prompts Directory Structure

```
prompts/
├── asset-templates/
│   ├── <id>.md                   ← Template YAML + prose
│   └── <id>/                     ← Per-asset folder
│       ├── ref.png               ← Reference image (user-dropped or stage 0 output)
│       ├── ref.original.png      ← Archive copy (set by stage 0.25)
│       ├── README.md             ← Per-asset notes
│       └── rig.blend             ← [animated kind only] Blender skeletal rig
├── _flux_workflows/
│   ├── default.json              ← Stage 0 FLUX.1 workflow (standard assets)
│   ├── hero.json                 ← Stage 0 FLUX.1 variant (hero props)
│   └── refine.json               ← Stage 0.25 FLUX.2 [klein] img2img workflow
└── _pbr_workflows/
    ├── sdxl_depth_pbr.json       ← Stage 2b SDXL + ControlNet
    └── flux2_klein_pbr.json      ← Alternative FLUX.2 projection
```

---

## Integration Contracts

### With Babylon.js Runtime (witness-interactive-vite/)

**AssetLibrary Contract:**
- Input: asset id (e.g., `prop_ledger_book`)
- Path resolution: `/assets/<id>.glb` (LOD0), `/assets/<id>.lod1.glb`, `/assets/<id>.lod2.glb`
- Output: `AssetContainer` with LOD meshes instantiable

**Expected files in `witness-interactive-vite/public/assets/`:**
```
assets/
├── prop_ledger_book.glb
├── prop_ledger_book.lod1.glb
├── prop_ledger_book.lod2.glb
├── structure_rugo_main_house.glb
├── structure_rugo_main_house.lod1.glb
├── structure_rugo_main_house.lod2.glb
└── ...
```

### With Narrative System

See [@claude.md](claude.md) cross-reference: [`docs/design-docs/NARRATIVE.md`](../design-docs/NARRATIVE.md)

- Assets are placed in scenes via `NarrativeController` action handlers
- Asset state is tracked in `StateManager` (picked up, examined, etc.)
- Asset visibility / interactivity tied to `requiredFlags` and `unlocksFlags` in narrative graph

---

## Error Handling & Recovery

### Pipeline Exit Codes

| Code | Meaning | Recovery |
|------|---------|----------|
| 0 | Full success | None — proceed to runtime |
| 1 | Input/validation failed | Re-run with corrected inputs |
| 2 | Generation/processing failed | Check aggregate diagnostic, retry with new seed or refined ref |
| 3 | Registration/export failed | Ensure `docs/asset-index.md` is writable; check `public/assets/` perms |

### Diagnostic Workflow

On any non-zero exit:

1. **Check aggregate diagnostic:**
   ```bash
   cat processed/diagnostics/<id>.aggregate.json
   ```

2. **Recommended action field hints at recovery:**
   - `pass`: gates succeeded — issue is elsewhere
   - `retry_with_new_seed`: increment seed, re-run stage 1
   - `retry_with_refined_ref`: delete `ref.original.png` + `ref.png`, re-drop new source, re-run
   - `fail`: manual intervention needed (see per-gate report for details)

3. **Per-gate details:**
   ```bash
   cat processed/diagnostics/<id>.geometry.json      # Gate 2: mesh issues
   cat processed/diagnostics/<id>.pbr.json           # Gate 5: texture issues
   ```

---

## Concurrency & Locking

**No distributed locking.** Asset pipeline assumes single-user local execution:
- One RTX 5090 per developer
- ComfyUI + Hunyuan3D single-instance on localhost:8188 + localhost:8081
- File writes to `processed/` are atomic (Python's `Path.write_*` is atomic)
- Registry append is serialized (single writer to `docs/asset-index.md`)

If running batch jobs, use OS-level process isolation (e.g., `witness.py batch` runs sequentially).

---

## Performance Characteristics

See [@claude.md](claude.md) for VRAM budgets. Critical path for Phase 1 hero assets (mesh + AI PBR):

- **Stage 0:** 90s + VRAM: 6 GB
- **Stage 0.25:** 20s + VRAM: 3 GB
- **Stage 0.5:** 60s + VRAM: 8 GB (multi-view only)
- **Stage 1:** 8–15 min + VRAM: 25 GB
- **Stage 2:** 5–10 min + VRAM: 5 GB
- **Stage 2b:** 10–15 min + VRAM: 8 GB (optional)
- **Stages 3–6:** 2 min total + VRAM: < 2 GB (CPU-bound)

**Total:** 30–40 minutes (with AI projection) or 20–30 minutes (procedural PBR)

---

**Last updated:** 2026-05-25 | **See also:** [@orchestrator.md](orchestrator.md), [@generation-stages.md](generation-stages.md)
