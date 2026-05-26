# Generation Stages — Deep Dive (0 through 6)

> Complete breakdown of all pipeline stages: inputs, outputs, tools, failure modes, recovery.
> See [@claude.md](claude.md), [@architecture.md](architecture.md), [@orchestrator.md](orchestrator.md).

---

## Overview: Mesh Pipeline Stage Sequence

For `mesh` and `animated` kinds:

```
Stage 0    [optional]  Generate ref image from text          (FLUX.1)
Stage 0.25 [default]   Refine ref image to style            (FLUX.2 [klein])
Stage 0.5  [optional]  Multi-view synthesis                 (Zero123++)
Stage 1                Mesh generation from refined ref     (Hunyuan3D 2.1)
Stage 2                PBR texture baking                   (Blender Cycles)
Stage 2b   [optional]  AI material projection               (ComfyUI SDXL+CN)
Stage 3                Optimization (Draco, KTX2, cleanup) (gltf-transform)
Stage 4                LOD variant generation              (gltf-transform)
Stage 5                Collision hull generation           (trimesh)
Stage 6a               Registry append                     (register_asset.py)
Stage 6b               Public export                       (export_babylon.py)
```

For other kinds (splat, tileset, etc.): only stages 1 + 6.

---

## Stage 0: Reference Image Auto-Generation (Optional)

**Tool:** `generate_ref_image.py`
**Trigger:** `--auto-ref` flag or no `ref.png` found
**Prerequisite:** ComfyUI + FLUX.1 model available
**Input:** asset id, optional prompt override, optional seed
**Output:** `prompts/asset-templates/<id>/ref.png`

### Flow

```python
def generate_ref_image(asset_id: str, seed: int = None):
    # Load FLUX.1 workflow JSON
    workflow = load_json("prompts/_flux_workflows/default.json")
    
    # Build prompt from template (or use --auto-ref-prompt override)
    prompt = template.description + " Digital Diorama style..."
    
    # Set parameters
    workflow["FLUX_Sampler"]["inputs"]["seed"] = seed or random()
    workflow["FLUX_Sampler"]["inputs"]["prompt"] = prompt
    
    # Submit to ComfyUI
    response = requests.post("http://localhost:8188/prompt", json=workflow)
    uuid = response.json()["prompt_id"]
    
    # Poll /history/{uuid} until complete
    image_data = poll_until_done(uuid)
    
    # Save to ref.png
    save_png(image_data, f"prompts/asset-templates/{asset_id}/ref.png")
```

**Typical duration:** 60–90 seconds on RTX 5090 + FLUX.1 model
**VRAM:** ~6 GB

**Failure modes:**
- ComfyUI not running → exit 2
- FLUX.1 model missing → exit 2
- Prompt too vague → output doesn't match intent (manual review needed)

**Recovery:** delete `ref.png`, adjust prompt or seed in template, re-run stage 0

---

## Stage 0.25: Reference Image Refinement (Default)

**Tool:** `refine_ref_image.py`
**Trigger:** Always (unless `--no-refine-ref`)
**Prerequisite:** ComfyUI + FLUX.2 [klein] model available
**Input:** `ref.png`, denoise strength (0.0–1.0)
**Output:** refined `ref.png` + archive copy `ref.original.png`

### Flow

```python
def refine_ref_image(ref_path: Path, asset_id: str, strength: float = 0.50):
    # Archive original
    shutil.copy(ref_path, ref_path.parent / "ref.original.png")
    
    # Load FLUX.2 [klein] img2img workflow
    workflow = load_json("prompts/_flux_workflows/refine.json")
    
    # Load ref.png as input image
    ref_image_b64 = base64.b64encode(ref_path.read_bytes()).decode()
    workflow["LoadImage"]["inputs"]["image"] = ref_image_b64
    
    # Set denoise strength (lower = preserve geometry, higher = restyle)
    workflow["FLUX_Sampler_img2img"]["inputs"]["denoise"] = strength
    
    # Refinement prompt (canonical, from _STYLE_GUIDE.md)
    REFINE_PROMPT_SUFFIX = (
        "Restyle this photograph to match the Digital Diorama look: filmic "
        "desaturated palette, tactile weathered realism, hyper-realistic PBR "
        "materials with micro-bump and roughness variation, 1994 Rwanda "
        "documentary photography aesthetic. Preserve the subject's geometry, "
        "pose, and composition exactly..."
    )
    workflow["FLUX_Sampler_img2img"]["inputs"]["prompt"] = REFINE_PROMPT_SUFFIX
    
    # Submit to ComfyUI
    response = requests.post("http://localhost:8188/prompt", json=workflow)
    uuid = response.json()["prompt_id"]
    
    # Poll until complete
    refined_data = poll_until_done(uuid)
    
    # Overwrite ref.png with refined output
    save_png(refined_data, ref_path)
```

**Denoise strength by category** (from `asset_pipeline.py`):
- `vegetation_`: 0.60 (push palette hard; foliage color varies wildly)
- `structure_`: 0.40 (protect geometry: doorways, roof pitches)
- `prop_`: 0.50 (balance materials + geometry)
- `figure_`: 0.50 (anatomy-aware; higher denoise warps limbs)
- Default: 0.50

**Archive scheme:** On first run, `ref.png` → `ref.original.png`. Re-runs read from `.original.png` so denoise doesn't compound. To start fresh with new source: delete both, re-drop `ref.png`, pipeline treats next run as clean slate.

**Typical duration:** 15–25 seconds on RTX 5090
**VRAM:** ~3 GB

**Failure modes:**
- FLUX.2 model missing → exit 2
- Input image corrupted → exit 2

---

## Stage 0.5: Multi-View Synthesis (Optional)

**Tool:** `generate_multi_views.py`
**Trigger:** `--multi-view` flag
**Prerequisite:** Python env with diffusers + Zero123++ weights
**Input:** `ref.png`, seed
**Output:** 6 canonical view PNGs at `processed/views/<id>/{front,back,left,right,top,bottom}.png`

### Flow

```python
def generate_multi_views(ref_image: Path, asset_id: str, seed: int = 481116):
    """
    Use Zero123++ to generate 6 orthogonal views from single reference.
    Views used by stage 1 (Hunyuan multi-view mesh) + stage 2 (projection).
    """
    from diffusers import DiffusionPipeline
    
    # Load Zero123++ (or Zero123 if ++ unavailable)
    pipe = DiffusionPipeline.from_pretrained(
        "sudo-ai/zero123plus-v1.2",
        custom_pipeline="zero123plus",
        torch_dtype=torch.float16,
        device_map="auto"
    )
    
    # Load reference image
    ref_pil = Image.open(ref_image)
    
    # Generate 6 views (elevation, azimuth combinations)
    # Canonical orientations: front (0°), back (180°), left (90°), right (270°),
    # top (overhead), bottom (underside)
    CANONICAL_VIEWS = [
        ("front",  (0, 0)),       # elev, azim
        ("right",  (0, 270)),
        ("back",   (0, 180)),
        ("left",   (0, 90)),
        ("top",    (90, 0)),
        ("bottom", (-90, 0)),
    ]
    
    output_dir = REPO_ROOT / "processed" / "views" / asset_id
    output_dir.mkdir(parents=True, exist_ok=True)
    
    for view_name, (elev, azim) in CANONICAL_VIEWS:
        # Zero123++ samples with elevation/azimuth pose
        image = pipe(
            ref_pil,
            num_inference_steps=30,
            guidance_scale=3.0,
            elevation=elev,
            azimuth=azim,
            camera_distance=100,
            seed=seed + hash(view_name) % 10000  # Deterministic per-view seed
        ).images[0]
        
        # Save
        view_path = output_dir / f"{view_name}.png"
        image.save(view_path, "PNG")
        print(f"  Saved: {view_path}")
```

**Typical duration:** 50–70 seconds for all 6 views
**VRAM:** ~8 GB peak

**Failure modes:**
- Zero123++ weights missing / download failed → exit 2
- Seed mismatch (non-deterministic generation on some setups)

**Recovery:** re-run with explicit seed, or omit `--multi-view` and use single-view mesh

---

## Stage 1: Mesh Generation (Hunyuan3D 2.1)

**Tool:** `generate_asset.py`
**Trigger:** Always (for mesh/animated kinds)
**Prerequisite:** Hunyuan3D container running at localhost:8081
**Input:** `ref.png` (+ optional 6 view PNGs), Hunyuan parameters
**Output:** `processed/glb/raw/<id>.glb` (200K–900K faces)

### API Contract

**Hunyuan3D HTTP API** (patched model_worker):

```
POST /send
  Body: JSON
    {
      "image": "<base64>",           # primary reference
      "images": ["<b64>", ...],      # optional multi-view list (6 PNGs)
      "remove_background": true,
      "texture": false,              # texture pass disabled (done in stage 2)
      "seed": 481116,
      "octree_resolution": 512,      # 512 (standard) or 768 (hero, higher VRAM)
      "num_inference_steps": 50,     # upstream default, can be 20–80
      "guidance_scale": 8.0,         # was 5.0; 8.0 pushes harder
      "num_chunks": 8000,
      "face_count": 40000,
      "type": "glb"
    }
  Response: { "uid": "<uuid>" }

GET /status/{uid}
  Response: {
    "status": "processing" | "texturing" | "completed" | "error",
    "model_base64": "..."            # only if status == completed
  }
```

### Flow

```python
def generate_asset(ref_image: Path, asset_id: str, steps: int = 50, seed: int = 481116):
    # Encode reference
    image_b64 = base64.b64encode(ref_image.read_bytes()).decode()
    
    # Optionally encode multi-view images
    view_b64_list = None
    if args.view:
        view_b64_list = [base64.b64encode(Path(v).read_bytes()).decode() for v in args.view]
    
    # Build payload
    payload = {
        "image": image_b64,
        "images": view_b64_list,  # sent if multi-view
        "remove_background": True,
        "texture": False,
        "seed": seed,
        "octree_resolution": 512,
        "num_inference_steps": steps,
        "guidance_scale": 8.0,
        "num_chunks": 8000,
        "face_count": 40000,
        "type": "glb",
    }
    
    # POST /send
    r = requests.post("http://localhost:8081/send", json=payload)
    uid = r.json()["uid"]
    
    # Poll /status/{uid} until completed
    start = time.time()
    while time.time() - start < 1800:  # 30 min timeout
        r = requests.get(f"http://localhost:8081/status/{uid}")
        status = r.json()["status"]
        
        if status == "completed":
            model_b64 = r.json().get("model_base64")
            if not model_b64:
                print("ERROR: generation succeeded but no mesh data returned")
                sys.exit(1)
            
            # Decode and save
            glb_bytes = base64.b64decode(model_b64)
            output_path = PROCESSED / "glb" / "raw" / f"{asset_id}.glb"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(glb_bytes)
            return 0
        
        elif status == "error":
            print(f"ERROR: {r.json().get('message', 'unknown')}")
            sys.exit(1)
        
        else:  # processing or texturing
            elapsed = time.time() - start
            print(f"  [{elapsed:6.0f}s] {status}")
            time.sleep(10)
```

**Typical duration:** 8–15 minutes (depending on steps, octree_resolution)
**VRAM:** ~25 GB peak

**Multi-view advantage:** Hunyuan patched `model_worker.py` accepts `images` list; upstream uses single view. Multi-view produces more detailed geometry (fewer artifacts, better shape closure).

**Failure modes:**
- Container not running → exit 1
- OOM on GPU (octree_resolution too high) → Hunyuan silent fail, returns 0-byte sentinel → exit 1
- Reference image bad quality / off-style → degenerate mesh (flat, depth-card) → caught by Gate 2
- Seed mismatch on re-run (non-deterministic generation)

**Recovery:** see Gate 2 logic in [@orchestrator.md](orchestrator.md)

---

## Stage 2: PBR Texture Baking

**Tool:** `texture_asset.py` (delegates to `blender/bake_pbr.py`)
**Trigger:** Always (for mesh/animated kinds)
**Prerequisite:** Blender 4.0+ with Cycles, processed/glb/raw/<id>.glb
**Input:** raw GLB, asset id, material family (auto-detect or explicit)
**Output:**
- `processed/glb/<id>.textured.glb`
- `processed/textures/<id>/{albedo,normal,mr,ao}.png` (8K, before KTX2)
- `processed/views/<id>/{front,back,left,right,top,bottom}.{png,exr}` (beauty + depth)

### Blender Headless Bake Flow

```python
def bake_pbr(asset_id: str, raw_glb_path: Path):
    """
    Headless Blender Cycles:
      1. Load raw GLB
      2. Smart UV unwrap (if missing UVs)
      3. Identify material family (mud brick, tin, wood, stone, cloth, leather, etc.)
      4. Create Principled BSDF with family-tuned parameters
      5. Bake Albedo / Normal / MR @ 8K
      6. Export textured GLB
    """
    import bpy
    
    # Clear default scene
    bpy.ops.wm.open_mainfile(filepath=str(bpy.context.blend_data.filepath))
    
    # Import raw GLB
    bpy.ops.import_scene.gltf(filepath=str(raw_glb_path))
    
    # Get material family (from template or auto-detect via asset id prefix)
    family = infer_material_family(asset_id)
    
    # For each mesh object:
    for obj in bpy.context.scene.objects:
        if obj.type != "MESH":
            continue
        
        mesh = obj.data
        
        # Smart UV unwrap if no UVs
        if not mesh.uv_layers:
            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.mode_set(mode="EDIT")
            bpy.ops.mesh.select_all(action="SELECT")
            bpy.ops.uv.smart_project()
            bpy.ops.object.mode_set(mode="OBJECT")
        
        # Apply Principled BSDF material
        mat = bpy.data.materials.new(name=f"{asset_id}_mat")
        mat.use_nodes = True
        bsdf = mat.node_tree.nodes["Principled BSDF"]
        
        # Set base parameters per family
        params = material_families[family]
        bsdf.inputs["Base Color"].default_value = params["base_color"]
        bsdf.inputs["Roughness"].default_value = params["roughness"]
        bsdf.inputs["Metallic"].default_value = params["metallic"]
        bsdf.inputs["Normal Map"].default_value = params.get("normal", (0.5, 0.5, 1.0, 1.0))
        
        # Assign material to mesh
        mesh.materials.append(mat)
    
    # Setup render engine + bake settings
    bpy.context.scene.render.engine = "CYCLES"
    bpy.context.scene.cycles.samples = 256
    
    # Render 6 canonical views
    for view_name, (cam_angle, cam_distance) in CANONICAL_VIEWS.items():
        render_and_save_view(view_name, cam_angle, cam_distance)
    
    # Bake Albedo, Normal, Roughness, Metallic, AO
    bake_texture_maps(asset_id, texture_size=8192)
    
    # Export to textured GLB
    bpy.ops.export_scene.gltf(
        filepath=str(processed_glb / f"{asset_id}.textured.glb"),
        export_image_format="PNG",
        export_image_quality=95,
    )
```

**Typical duration:** 5–10 minutes
**VRAM:** ~5 GB

**Key parameters:**
- Texture size: 8192 (8K) for hero assets, 4096 (4K) for env props
- Cycles samples: 256–512 (higher = cleaner, slower)
- Material family: inferred from asset id prefix or explicit via `--family`

**Failure modes:**
- Blender not installed → exit 1
- Raw GLB corrupted / missing → exit 1
- Smart UV unwrap fails (degenerate mesh) → warning, skip unwrap, proceed with existing UVs
- Out of VRAM → Blender crashes → exit 2

---

## Stage 2b: AI Material Projection (Optional)

**Tool:** `texture_asset.py` (delegates to ComfyUI SDXL + ControlNet)
**Trigger:** `--ai-project` flag
**Prerequisite:** ComfyUI + SDXL model + ControlNet (depth) installed
**Input:** 6 canonical view renders + 16-bit depth maps (stage 2 output), asset prompt
**Output:** AI-projected Albedo maps (in `processed/textures/<id>/`)

### SDXL + ControlNet (Depth) Projection

```python
def project_pbr_sdxl(asset_id: str, views_dir: Path, depth_dir: Path):
    """
    ComfyUI SDXL + ControlNet (depth):
    For each canonical view:
      1. Load render (beauty.png) + depth map (depth.exr, normalize to 0–255)
      2. SDXL conditioned on depth map (ControlNet)
      3. Prompt: asset description + PBR directives
      4. Output painted albedo map (same resolution as view)
      5. Re-project onto UV space
      6. Re-bake at 8K with new albedo
    """
    
    # Load SDXL + ControlNet workflow
    workflow = load_json("prompts/_pbr_workflows/sdxl_depth_pbr.json")
    
    # Asset description prompt
    prompt = template.description  # e.g., "worn leather-bound notebook..."
    pbr_suffix = (
        "Photorealistic PBR material. Hyper-realistic surface detail, "
        "micro-bump, roughness variation. Tactile weathered finish."
    )
    full_prompt = f"{prompt} {pbr_suffix}"
    
    for view_name in CANONICAL_VIEWS:
        # Load beauty render
        beauty_path = views_dir / f"{view_name}.png"
        beauty_b64 = base64.b64encode(beauty_path.read_bytes()).decode()
        
        # Load + normalize depth (16-bit EXR → 8-bit PNG)
        depth_path = depth_dir / f"{view_name}_depth.exr"
        depth_np = load_exr(depth_path)  # shape (H, W, 3)
        depth_norm = (depth_np[:, :, 0] / depth_np.max() * 255).astype(np.uint8)
        depth_b64 = base64.b64encode(Image.fromarray(depth_norm).tobytes()).decode()
        
        # Set workflow inputs
        workflow["LoadImage_beauty"]["inputs"]["image"] = beauty_b64
        workflow["ControlNetLoader"]["inputs"]["control_image"] = depth_b64
        workflow["SDXL_Sampler"]["inputs"]["prompt"] = full_prompt
        
        # Generate
        r = requests.post("http://localhost:8188/prompt", json=workflow)
        uuid = r.json()["prompt_id"]
        painted_image = poll_until_done(uuid)
        
        # Save painted albedo
        painted_path = processed_textures / asset_id / f"{view_name}_painted.png"
        painted_image.save(painted_path)
    
    # Re-project painted albedo maps onto UV space
    # (requires blender/reproject_views.py + UV-space projection)
    # Then re-bake with new albedo input
```

**Typical duration:** 10–15 minutes for 6 views
**VRAM:** ~8 GB peak

**Failure modes:**
- SDXL or ControlNet model missing → exit 2
- Depth map invalid / all zeros → projection fails → exit 2
- ComfyUI timeout

**Note:** As of 2026-05-25, stage 2b is marked optional and known to produce incomplete coverage ("white square" artefacts). Recovery: use `--no-ai-project`, rely on procedural PBR bake only (faster, lower quality).

---

## Stage 3: Optimization (Draco + KTX2 + LOD)

**Tool:** `optimize_asset.py`
**Trigger:** Always
**Prerequisite:** gltf-transform CLI, KTX2 encoder, trimesh (Python)
**Input:** `processed/glb/<id>.textured.glb`, target face count
**Output:** `processed/glb/<id>.glb` (optimized, Draco + KTX2)

### Optimization Passes

```python
def optimize_asset(textured_glb: Path, asset_id: str, target_faces: int):
    """
    Three passes:
      1. Detached-component cleanup (trimesh)
      2. Simplify + weld (gltf-transform)
      3. Texture compression (KTX2: UASTC normals, ETC1S colour)
      4. Draco geometry compression
    """
    
    # Pass 1: Strip floating islands
    scene = trimesh.load(textured_glb, force="scene", process=False)
    for mesh in scene.geometry.values():
        components = mesh.split(only_watertight=False)
        largest = max(components, key=lambda m: m.volume)
        # Keep components >= 1% of largest volume
        kept = [c for c in components if c.volume >= 0.01 * largest.volume]
        # Merge back
        if len(kept) < len(components):
            scene.geometry = {f"mesh_{i}": m for i, m in enumerate(kept)}
            scene.export(textured_glb)
    
    # Pass 2: Simplify + weld (gltf-transform)
    # target_faces typically 0.5× or 1.0× of LOD0 target from template
    cmd = [
        "gltf-transform", "simplify", str(textured_glb),
        "--ratio", str(target_faces_actual / vertex_count),  # calculated
        "--error", "0.001",  # max error tolerance
        "--aggressive", "true"
    ]
    subprocess.run(cmd)
    
    # Pass 3: Compress textures
    for map_name in ["albedo", "normal", "mr"]:
        map_path = TEXTURES_DIR / asset_id / f"{map_name}.png"
        if not map_path.exists():
            continue
        
        # Downsize if > max_texture_size (typically 8192)
        max_size = 8192 if "hero" in asset_id else 4096
        downsample_to(map_path, max_size)
        
        # KTX2 compression
        if "normal" in map_name:
            # UASTC for high-frequency (normal maps)
            compress_to_ktx2(map_path, mode="UASTC", quality=4)
        else:
            # ETC1S for low-frequency (albedo, roughness, metallic)
            compress_to_ktx2(map_path, mode="ETC1S", quality=128)
    
    # Pass 4: Draco compression
    cmd = ["gltf-transform", "draco", str(optimized_glb),
           "--level", "7",
           "--quantizePosition", "14",
           "--quantizeNormal", "10",
           "--quantizeTexCoord", "12"]
    subprocess.run(cmd)
```

**Typical duration:** 2–3 minutes
**VRAM:** < 2 GB

**Face reduction targets** (from template `target_poly_lod0`):
- Hero props (ledger, candle, frame): ~8K faces
- Medium structures: ~20K faces
- Large structures: ~40K faces

**File size reduction:** 70–90% compared to raw Hunyuan output

**Failure modes:**
- gltf-transform not installed → exit 1
- Detached-component trimesh load fails → skip cleanup, continue
- KTX2 encoder missing → exit 1

---

## Stage 4: LOD Variant Generation

**Tool:** `generate_lods.py`
**Trigger:** Always
**Prerequisite:** gltf-transform CLI
**Input:** `processed/glb/<id>.glb` (optimized LOD0)
**Output:** `processed/glb/<id>.lod1.glb` (50%), `processed/glb/<id>.lod2.glb` (15%)

### LOD Simplification

```python
def generate_lods(lod0_glb: Path):
    """
    LOD0 (0–15 m):   full detail,  8K textures
    LOD1 (15–50 m):  50% faces,    2K textures
    LOD2 (50+ m):    15% faces,    512 textures
    """
    
    LOD_SPECS = [
        ("lod1", 0.50, 2048, "LOD1 50% faces"),
        ("lod2", 0.15, 512,  "LOD2 15% faces"),
    ]
    
    for suffix, simplify_ratio, texture_size, label in LOD_SPECS:
        lod_path = lod0_glb.parent / f"{lod0_glb.stem}.{suffix}.glb"
        
        # Simplify geometry
        cmd = [
            "gltf-transform", "simplify", str(lod0_glb),
            "--ratio", str(simplify_ratio),
            "--error", "0.001",
            str(lod_path)
        ]
        subprocess.run(cmd)
        
        # Compress textures (smaller for distant LODs)
        compress_lod_textures(lod_path, texture_size)
        
        # Apply Draco (consistent with LOD0)
        cmd = ["gltf-transform", "draco", str(lod_path), "--level", "7"]
        subprocess.run(cmd)
        
        print(f"  {label} → {lod_path}")
```

**Typical duration:** 1–2 minutes for both LODs
**VRAM:** < 2 GB

**Failure modes:**
- gltf-transform not installed → exit 1
- Simplification fails on degenerate mesh → skip that LOD

---

## Stage 5: Collision Hull Generation

**Tool:** `generate_collision.py`
**Trigger:** Always (for mesh/animated kinds)
**Prerequisite:** trimesh + numpy
**Input:** `processed/glb/<id>.glb` (optimized LOD0)
**Output:** `processed/glb/<id>.collision.glb` (convex hull)

### Collision Hull Generation

```python
def generate_collision_hull(source_glb: Path, asset_id: str):
    """
    Generate convex hull from optimized mesh for physics collision.
    Stored separately so runtime can choose to load collision GLB or render GLB.
    """
    
    # Load source GLB (can be Draco-compressed)
    # Note: trimesh can decode Draco; if it fails, use textured GLB as source
    try:
        scene = trimesh.load(source_glb, force="scene", process=False)
    except:
        # Fallback to textured GLB (contains uncompressed geom)
        textured_glb = source_glb.parent / f"{asset_id}.textured.glb"
        scene = trimesh.load(textured_glb, force="scene", process=False)
    
    # Extract all meshes, compute combined convex hull
    all_vertices = []
    all_faces = []
    offset = 0
    
    for geom in scene.geometry.values():
        all_vertices.extend(geom.vertices)
        all_faces.extend(geom.faces + offset)
        offset = len(all_vertices)
    
    # Create combined mesh
    combined = trimesh.Trimesh(vertices=all_vertices, faces=all_faces)
    
    # Compute convex hull
    hull = combined.convex_hull
    
    # Export to collision GLB
    collision_path = source_glb.parent / f"{asset_id}.collision.glb"
    hull.export(collision_path, file_type="glb")
    
    print(f"  Collision hull: {hull.vertices.shape[0]} vertices, "
          f"{hull.faces.shape[0]} faces")
```

**Typical duration:** < 30 seconds
**VRAM:** < 1 GB

**Collision strategy** (from template):
- `convex_hull`: bounding convex polyhedron (fast, loses internal detail)
- `mesh`: export original mesh as-is (slower, more accurate, but skinny features break)
- `none`: skip collision generation (not recommended)

**Failure modes:**
- trimesh not installed → exit 1
- Draco decompression fails → fallback to textured GLB, continue

---

## Stage 6a: Asset Registration

**Tool:** `register_asset.py`
**Trigger:** Always
**Prerequisite:** `docs/asset-index.md` writable, diagnostics JSON sidecars exist
**Input:** asset id, era, kind, GLB path, diagnostics dir
**Output:** appended row in `docs/asset-index.md`

### Registration Logic

```python
def register_asset(asset_id: str, era: str, kind: str, glb_path: str):
    # Read diagnostic sidecars
    faces = read_face_count(f"processed/diagnostics/{asset_id}.geometry.json")
    gates = read_gate_status(f"processed/diagnostics/{asset_id}.aggregate.json")
    
    # Build row
    row = (
        f"| {asset_id} | {kind} | {glb_path} | "
        f"{era_label(era)} | {source} | {datetime.now().strftime('%Y-%m-%d')} | "
        f"{faces} | {gates} |"
    )
    
    # Append to registry
    with open("docs/asset-index.md", "a") as f:
        f.write(row + "\n")
    
    print(f"✓ Registered: {asset_id}")
```

**Registry fields:**
1. Asset ID
2. Kind
3. Path (relative to repo)
4. Era label
5. Source (filename or URL)
6. Registered (date)
7. Faces (face count or "n/a")
8. Gates (pass/fail summary or "n/a")

**Failure modes:**
- `docs/asset-index.md` not writable → exit 3
- Diagnostic JSON missing → faces / gates fall back to "n/a", continue

---

## Stage 6b: Public Export

**Tool:** `export_babylon.py`
**Trigger:** Always
**Prerequisite:** `witness-interactive-vite/public/assets/` exists and writable
**Input:** asset id, GLB paths (LOD0, LOD1, LOD2, collision)
**Output:** files in `witness-interactive-vite/public/assets/<id>*`

### Export Logic

```python
def export_babylon(asset_id: str, lod0: Path, lod1: Path, lod2: Path, collision: Path):
    dest_dir = REPO_ROOT / "witness-interactive-vite" / "public" / "assets"
    dest_dir.mkdir(parents=True, exist_ok=True)
    
    for src_path, dest_name in [
        (lod0, f"{asset_id}.glb"),
        (lod1, f"{asset_id}.lod1.glb"),
        (lod2, f"{asset_id}.lod2.glb"),
        (collision, f"{asset_id}.collision.glb"),
    ]:
        if src_path.exists():
            shutil.copy(src_path, dest_dir / dest_name)
            print(f"  Exported: {dest_name}")
```

**Failure modes:**
- `witness-interactive-vite/public/assets/` not writable → exit 3
- Source GLB missing → skip that file, continue

---

**Last updated:** 2026-05-25 | **See also:** [@tools.md](tools.md), [@validation-gates.md](validation-gates.md), [@orchestrator.md](orchestrator.md)
