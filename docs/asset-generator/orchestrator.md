# CLI Orchestrator & Core Pipeline

> `witness.py` and `asset_pipeline.py` — the user-facing entry point and core stage orchestration engine.
> See [@claude.md](claude.md) and [@architecture.md](architecture.md).

---

## witness.py — User-Facing CLI

**Location:** `tools/witness.py`
**Purpose:** Server management, template discovery, pipeline delegation
**Entry point:** `python tools/witness.py <command> [options]`

### Commands

#### `start` — Start ComfyUI and/or Hunyuan3D

```bash
python tools/witness.py start                       # Both services
python tools/witness.py start --no-hunyuan          # ComfyUI only (for stage 0 ref gen)
python tools/witness.py start --no-comfy            # Hunyuan3D only
```

**Logic:**
1. Check if service already alive via HTTP health check
2. If missing: launch via subprocess.Popen (ComfyUI) or docker run (Hunyuan3D)
3. Poll health endpoint until ready or timeout (120s per service)
4. Return exit code 0 (ok) or 1 (failed)

**ComfyUI startup:**
- Python venv: `/home/royce3/ComfyUI/venv/bin/python`
- Main: `/home/royce3/ComfyUI/main.py`
- Log: `/tmp/comfyui.log`
- Listen: `http://localhost:8188`

**Hunyuan3D startup:**
- Image: `witness-hunyuan-sm120:latest` (custom build with torch 2.12.0+cu130)
- Docker flags:
  - `--gpus all` — GPU pass-through
  - `--privileged` — required for RTX 5090 + driver 595.71.05 (cuInit() workaround)
  - `--shm-size=16g` — model worker IPC
  - Volume mounts: model_cache (HuggingFace + Triton kernels), custom model_worker.py patch
- Container name: `witness-hunyuan`
- API endpoint: `http://localhost:8081`

#### `stop` — Stop Services

```bash
python tools/witness.py stop                        # Both
python tools/witness.py stop --no-hunyuan           # ComfyUI only
python tools/witness.py stop --no-comfy             # Hunyuan3D only
```

**Logic:**
- ComfyUI: find PID in `/tmp/comfyui.pid` (or infer from log), send SIGTERM
- Hunyuan3D: `docker stop witness-hunyuan`

#### `status` — Server Health & Model Inventory

```bash
python tools/witness.py status
```

**Outputs:**
- ComfyUI online? (HTTP GET `/system_stats`)
- Hunyuan3D online? (HTTP GET `/docs`)
- Installed models (Flux variants, ControlNet, etc.)
- Generated assets count
- Phase 1 progress

#### `generate` — Generate a Single Asset

```bash
python tools/witness.py generate <asset_id> \
    [--kind mesh|splat|tileset|navmesh|nme|animated] \
    [--multi-view] \
    [--no-refine-ref] \
    [--refine-ref-strength 0.0..1.0] \
    [--fast] \
    [--seed NNNN] \
    [--steps NN] \
    [--no-ai-project] \
    [--source FILE] \
    [--root URL] \
    [--terrain GLB]
```

**Execution:**
1. Load template: `prompts/asset-templates/<asset_id>.md`
2. Infer asset kind from CLI or template
3. Delegate to `asset_pipeline.py` with all args
4. Exit with code from pipeline (0, 2, or 3)

**Common usage patterns:**
```bash
# Standard mesh (default)
python tools/witness.py generate prop_ledger_book

# With multi-view synthesis (stage 0.5)
python tools/witness.py generate vegetation_eucalyptus_mature --multi-view

# Skip FLUX.2 refinement (stage 0.25) for iteration
python tools/witness.py generate structure_rugo_main_house --no-refine-ref

# Faster draft quality
python tools/witness.py generate my_asset --fast --steps 20

# Splat capture
python tools/witness.py generate my_splat --kind splat --source captures/my.spz

# 3D Tileset reference
python tools/witness.py generate terrain --kind tileset --root https://example/tileset.json

# Navigation mesh from terrain
python tools/witness.py generate compound_nav --kind navmesh --terrain processed/glb/terrain.glb

# Node Material Editor JSON
python tools/witness.py generate stone_surface --kind nme --source materials/stone.nme.json

# Animated character
python tools/witness.py generate figure_grandfather --kind animated
```

#### `batch` — Generate Multiple Assets Sequentially

```bash
python tools/witness.py batch prop_altar_candle prop_altar_photo_frame prop_ledger_book \
    [--multi-view] [--fast] [--skip-failed]
```

**Execution:**
- For each asset id: call `witness.py generate` sequentially
- `--skip-failed`: continue to next asset if one fails (else stop on first error)
- Log progress to stdout

#### `list` — Show Available Templates

```bash
python tools/witness.py list
```

**Output:**
- Markdown table: asset_id | kind | era | status
- Kind inferred from template YAML `kind` field (default: `mesh`)
- Status: `todo` (no ref.png) | `pending` (ref exists, not generated) | `generated` (exists in processed/glb/)

#### `gui` — TBD GUI Wrapper (Future)

```bash
python tools/witness.py gui
```

Placeholder for Qt/Tkinter UI. Not currently implemented; see `tools/witness_gui.py` stub.

---

### Helper Functions (witness.py)

| Function | Purpose |
|----------|---------|
| `_comfy_alive(server)` | HTTP GET `/system_stats` on ComfyUI; return bool |
| `_hunyuan_alive(server)` | HTTP GET `/docs` on Hunyuan3D; return bool |
| `_hunyuan_container_running()` | `docker ps --filter name=witness-hunyuan`; return bool |
| `_start_comfyui()` | subprocess.Popen + wait for ready |
| `_start_hunyuan(wait=True)` | `docker run --privileged --gpus all` + wait loop |
| `_object_info_list()` | Query ComfyUI `/object_info/<node>` for available models |
| `detect_models()` | Parse ComfyUI model inventory; return capabilities dict |
| `list_templates()` | Glob `prompts/asset-templates/*.md` (exclude `_*.md` stubs) |

---

## asset_pipeline.py — Core Orchestrator

**Location:** `tools/asset_pipeline.py`
**Purpose:** Stage sequencing, kind dispatch, validation integration, registry append
**Entry point:** `python tools/asset_pipeline.py <asset_id> --kind <kind> [stage-specific args]`

> This is the **normative specification** for the asset generation pipeline.
> See `.claude/rules/asset-pipeline.md` for the rule.

### Architecture

```
def asset_pipeline.main():
    • Parse CLI args + environment
    • Validate inputs (asset id pattern, kind, paths, etc.)
    • Load template YAML (if mesh/animated)
    • Instantiate PipelineContext(asset_id, kind, ...)
    • Dispatch on kind:
        mesh / animated  → Pipeline.run_mesh_pipeline()
        splat            → Pipeline.run_splat_pipeline()
        tileset          → Pipeline.run_tileset_pipeline()
        navmesh          → Pipeline.run_navmesh_pipeline()
        nme              → Pipeline.run_nme_pipeline()
    • Return exit code (0, 2, or 3)
```

### Asset ID Validation

```python
def validate_id(asset_id: str) -> bool:
    # Pattern: ^[a-z_][a-z0-9_]{2,}$
    # Enforce snake_case, no hyphens, no CAPS
    # Example: prop_ledger_book, vegetation_eucalyptus_mature
```

### PipelineContext Dataclass

Holds mutable state across all stages:

```python
@dataclass
class PipelineContext:
    asset_id: str
    kind: str                        # mesh, splat, tileset, navmesh, nme, animated
    era: str                         # present, past, shared
    
    # Paths
    template_path: Path
    processed_glb_dir: Path
    processed_textures_dir: Path
    processed_views_dir: Path
    diagnostics_dir: Path
    
    # Stage outputs (set progressively)
    ref_image: Path                  # after stage 0 / 0.25
    raw_glb: Path                    # after stage 1
    textured_glb: Path               # after stage 2
    optimized_glb: Path              # after stage 3
    lod1_glb: Path                   # after stage 4
    lod2_glb: Path                   # after stage 5
    collision_glb: Path
    
    # Gates
    gates_ran: list[str]             # [0, 1, 2, 3, 4, 5] for mesh pipeline
    gates_failed: list[str]
    
    # Helper: row formatting for registry
    def row(self) -> str:
        # Return markdown table row for docs/asset-index.md
        # Reads diagnostics to fill face count + gate status
```

### Mesh Pipeline (Typical Flow)

```python
def run_mesh_pipeline(ctx: PipelineContext) -> int:
    # Stage 0.25: Ref refinement (FLUX.2 [klein] img2img)
    if not ctx.no_refine_ref:
        step("Stage 0.25 — Ref image refinement (FLUX.2)")
        refine_strength = refine_strength_for(ctx.asset_id)
        cmd = [
            GATE_PYTHON, REFINE_REF_IMAGE,
            str(ctx.ref_image),
            "--strength", str(refine_strength),
            "--asset-id", ctx.asset_id,
            "--output-dir", str(ctx.template_path.parent)
        ]
        if subprocess.run(cmd).returncode != 0:
            return die("Stage 0.25 failed", 2)
        # refine_ref_image.py archives ref.png → ref.original.png
        # and overwrites ref.png with refined output
    
    # Gate 1: Ref image validation
    step("Gate 1 — Validate reference image")
    gate1_report = ctx.diagnostics_dir / f"{ctx.asset_id}.ref_image.json"
    if not run_validator(VALIDATE_REF_IMAGE, ctx.ref_image, gate1_report):
        ctx.gates_failed.append("1")
        return die("Gate 1 failed; check diagnostics", 2)
    ctx.gates_ran.append("1")
    
    # [Optional] Stage 0.5: Multi-view synthesis
    if ctx.multi_view:
        step("Stage 0.5 — Multi-view synthesis (Zero123++)")
        cmd = [MULTI_VIEW_PYTHON, GENERATE_MULTI_VIEWS, ...]
        if subprocess.run(cmd).returncode != 0:
            return die("Stage 0.5 failed", 2)
        # Outputs: processed/views/<id>/{front,back,left,right,top,bottom}.png
        
        # Gate 3: View synthesis validation
        step("Gate 3 — Validate multi-view renders")
        gate3_report = ctx.diagnostics_dir / f"{ctx.asset_id}.views.json"
        if not run_validator(VALIDATE_VIEWS, processed_views_dir, gate3_report):
            ctx.gates_failed.append("3")
            return die("Gate 3 failed", 2)
        ctx.gates_ran.append("3")
    
    # Stage 1: Mesh generation (Hunyuan3D 2.1)
    step("Stage 1 — Mesh generation (Hunyuan3D 2.1)")
    view_paths = [...]  # if multi_view else []
    cmd = [
        GATE_PYTHON, GENERATE_ASSET,
        str(ctx.ref_image),
        ctx.asset_id,
        "--steps", str(ctx.steps),
        "--seed", str(ctx.seed),
        "--output-dir", str(ctx.processed_glb_dir / "raw"),
        *("--view " + str(v) for v in view_paths),
    ]
    if subprocess.run(cmd).returncode != 0:
        return die("Stage 1 failed", 2)
    ctx.raw_glb = ctx.processed_glb_dir / "raw" / f"{ctx.asset_id}.glb"
    
    # Gate 2: Geometry validation
    step("Gate 2 — Validate geometry")
    gate2_report = ctx.diagnostics_dir / f"{ctx.asset_id}.geometry.json"
    if not run_validator(VALIDATE_GEOMETRY, ctx.raw_glb, gate2_report):
        if ctx.aggregate_from(gate2_report).get("recommended_action") == "retry_with_new_seed":
            # Automatic retry (bump seed, re-run stage 1)
            ctx.seed += RETRY_SEED_STRIDE
            return run_mesh_pipeline(ctx)  # Recursive retry
        ctx.gates_failed.append("2")
        return die("Gate 2 failed", 2)
    ctx.gates_ran.append("2")
    
    # Stage 2: PBR baking (+ optional 2b AI projection)
    step("Stage 2 — PBR baking (Blender Cycles)")
    cmd = [
        GATE_PYTHON, TEXTURE_ASSET,
        "--asset-id", ctx.asset_id,
        "--glb", str(ctx.raw_glb),
        "--family", ctx.template.material_family or "auto",
        "--texture-size", str(ctx.texture_size),
        *("--ai-project" if ctx.ai_project else [])
    ]
    if subprocess.run(cmd).returncode != 0:
        return die("Stage 2 failed", 2)
    ctx.textured_glb = ctx.processed_glb_dir / f"{ctx.asset_id}.textured.glb"
    
    # Gate 5: PBR texture contract
    step("Gate 5 — Validate PBR textures")
    gate5_report = ctx.diagnostics_dir / f"{ctx.asset_id}.pbr.json"
    if not run_validator(VALIDATE_PBR, ctx.processed_textures_dir / ctx.asset_id, gate5_report):
        ctx.gates_failed.append("5")
        return die("Gate 5 failed", 2)
    ctx.gates_ran.append("5")
    
    # Stage 3: Optimization
    step("Stage 3 — Optimize (Draco + KTX2 + cleanup)")
    cmd = [GATE_PYTHON, OPTIMIZE_ASSET, str(ctx.textured_glb), ...]
    if subprocess.run(cmd).returncode != 0:
        return die("Stage 3 failed", 2)
    ctx.optimized_glb = ctx.processed_glb_dir / f"{ctx.asset_id}.glb"
    
    # Stage 4: LOD generation
    step("Stage 4 — Generate LODs (gltf-transform)")
    cmd = [GATE_PYTHON, GENERATE_LODS, str(ctx.optimized_glb)]
    if subprocess.run(cmd).returncode != 0:
        return die("Stage 4 failed", 2)
    ctx.lod1_glb = ctx.processed_glb_dir / f"{ctx.asset_id}.lod1.glb"
    ctx.lod2_glb = ctx.processed_glb_dir / f"{ctx.asset_id}.lod2.glb"
    
    # Stage 5: Collision generation
    step("Stage 5 — Generate collision hull (trimesh)")
    cmd = [GATE_PYTHON, GENERATE_COLLISION, str(ctx.optimized_glb), ...]
    if subprocess.run(cmd).returncode != 0:
        return die("Stage 5 failed", 2)
    ctx.collision_glb = ctx.processed_glb_dir / f"{ctx.asset_id}.collision.glb"
    
    # Gate 4: Aggregate diagnostic
    step("Gate 4 — Aggregate diagnostics")
    gate4_report = ctx.diagnostics_dir / f"{ctx.asset_id}.aggregate.json"
    if not run_validator(DIAGNOSTIC_REPORT, ctx.diagnostics_dir, gate4_report):
        return die("Gate 4 failed", 2)
    ctx.gates_ran.append("4")
    
    # Stage 6a: Registration
    step("Stage 6a — Register asset")
    cmd = [
        GATE_PYTHON, REGISTER_ASSET,
        ctx.asset_id, ctx.era,
        "--glb-path", str(ctx.optimized_glb),
        "--diagnostics-dir", str(ctx.diagnostics_dir)
    ]
    if subprocess.run(cmd).returncode != 0:
        return die("Stage 6a failed", 3)
    
    # Stage 6b: Export to public/assets/
    step("Stage 6b — Export for runtime")
    cmd = [
        GATE_PYTHON, EXPORT_BABYLON,
        "--asset-id", ctx.asset_id,
        "--glb", str(ctx.optimized_glb),
        "--lod1", str(ctx.lod1_glb),
        "--lod2", str(ctx.lod2_glb),
    ]
    if subprocess.run(cmd).returncode != 0:
        return die("Stage 6b failed", 3)
    
    step("✓ Pipeline complete")
    return 0
```

### Splat Pipeline

```python
def run_splat_pipeline(ctx: PipelineContext) -> int:
    # Simple: source validation → normalization → registration → export
    step("Stage 1 — Normalize splat (if needed)")
    
    if ctx.source.suffix in {".spz", ".ply", ".splat", ".sog"}:
        # Copy/convert to processed/splats/<id>.spz
        pass
    else:
        return die(f"Unsupported splat format: {ctx.source.suffix}", 2)
    
    step("Stage 2 — Register & export")
    # Similar to mesh 6a/6b
    return 0
```

### Tileset, NavMesh, NME Pipelines

Similar brevity — typically 1–2 stages, no generation, direct registration.

---

### Configuration & Environment

**Module-level constants (apply globally):**

| Constant | Purpose | Example |
|----------|---------|---------|
| `COMFYUI_PYTHON` | Python venv for stage 0/0.25 | `/home/royce3/ComfyUI/venv/bin/python` |
| `GATE_PYTHON` | Validation venv (can override) | `os.environ.get("WITNESS_GATE_PYTHON", COMFYUI_PYTHON)` |
| `MULTI_VIEW_PYTHON_DEFAULT` | Stage 0.5 venv (can override) | `os.environ.get("WITNESS_MULTI_VIEW_PYTHON", ...)` |
| `RETRY_SEED_STRIDE` | Seed increment for auto-retry | `10_000` |
| `REFINE_STRENGTH_BY_CATEGORY` | Denoise strength per asset category | `{"vegetation": 0.60, "structure": 0.40, ...}` |
| `VALID_KINDS` | Allowed asset kinds | `("mesh", "splat", "tileset", "navmesh", "nme", "animated")` |
| `VALID_ERAS` | Allowed era scopes | `("present", "past", "shared")` |

**Environment overrides:**
```bash
WITNESS_GATE_PYTHON=/path/to/python           # Minimal validator venv
WITNESS_MULTI_VIEW_PYTHON=/path/to/python     # Zero123++ venv
```

---

### Exit Codes

| Code | Meaning | Action |
|------|---------|--------|
| 0 | Full success | Proceed to runtime |
| 2 | Generation/processing failed | Check `processed/diagnostics/<id>.aggregate.json` |
| 3 | Registration/export failed | Check file permissions, registry file, export dir |

---

### Validation Retry Logic

When Gate 2 (geometry) fails:

1. Parse `processed/diagnostics/<id>.geometry.json`
2. If `recommended_action == "retry_with_new_seed"`:
   - Increment `ctx.seed += RETRY_SEED_STRIDE`
   - Re-call `run_mesh_pipeline(ctx)` (recursive)
   - Max retries: hard-coded or configurable?
3. Else: fail with exit code 2

**Note:** Recursive retry keeps the same asset_id, only bumps seed. Useful for when Hunyuan randomly produces flat/degenerate output.

---

### Dry-run / Validation-only Mode (TBD)

Not yet implemented; would be useful:
```bash
python tools/asset_pipeline.py prop_ledger_book --kind mesh --dry-run
# Validate template, check paths, verify servers alive — but don't generate
```

---

**Last updated:** 2026-05-25 | **See also:** [@architecture.md](architecture.md), [@generation-stages.md](generation-stages.md), [@tools.md](tools.md)
