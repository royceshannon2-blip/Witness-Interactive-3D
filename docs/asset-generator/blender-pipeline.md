# Blender Pipeline — PBR Baking & Materials

> Headless Blender tools for stage 2 PBR baking, material families, and optional stage 2b reprojection.
> See [@generation-stages.md](generation-stages.md) for stage overview.

---

## Blender Tools Overview

```
tools/blender/
├── bake_pbr.py              ← Stage 2: headless PBR bake (Cycles)
├── reproject_views.py       ← Stage 2b prep: UV reprojection setup
├── material_families.py     ← Material library (OpenPBR Principled BSDF)
├── render_validation.py     ← Diagnostic: beauty + normal + depth renders
└── ...
```

All tools use headless Blender (no GUI). Invoked via subprocess by `texture_asset.py`.

---

## bake_pbr.py — Stage 2 PBR Texture Baking

**Purpose:** Bake Albedo, Normal, Roughness, Metallic, AO textures using Blender Cycles
**Entry point (via texture_asset.py):** internal subprocess call
**Input:** raw GLB from Hunyuan3D
**Output:** PBR texture maps (8K PNG) + textured GLB export

### Bake Pipeline (Pseudo-code)

```python
def bake_pbr_main():
    # Stage 2a: Setup
    bpy.ops.wm.read_factory_settings()  # Fresh Blender scene
    
    # Stage 2a.1: Import raw GLB
    bpy.ops.import_scene.gltf(filepath=raw_glb_path)
    
    # Stage 2a.2: Infer material family from asset id
    family = infer_family(asset_id)  # e.g., "leather" → mat_leather_ledger
    
    # Stage 2a.3: Setup UV unwrapping
    for obj in bpy.context.scene.objects:
        if obj.type != "MESH":
            continue
        
        mesh = obj.data
        
        # Smart UV unwrap if missing
        if not mesh.uv_layers:
            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.mode_set(mode="EDIT")
            bpy.ops.mesh.select_all(action="SELECT")
            bpy.ops.uv.smart_project(angle_limit=0.785)  # ~45°
            bpy.ops.object.mode_set(mode="OBJECT")
    
    # Stage 2a.4: Apply Principled BSDF material per family
    for obj in bpy.context.scene.objects:
        if obj.type != "MESH":
            continue
        
        mesh = obj.data
        mat = bpy.data.materials.new(name=f"{asset_id}_mat")
        mat.use_nodes = True
        links = mat.node_tree.links
        
        # Clear default node setup
        for node in mat.node_tree.nodes:
            mat.node_tree.nodes.remove(node)
        
        # Create Principled BSDF
        principled = mat.node_tree.nodes.new("ShaderNodeBsdfPrincipled")
        output = mat.node_tree.nodes.new("ShaderNodeOutputMaterial")
        links.new(principled.outputs["BSDF"], output.inputs["Surface"])
        
        # Populate BSDF inputs from material family
        family_params = material_families[family]  # from material_families.py
        principled.inputs["Base Color"].default_value = family_params["base_color"]
        principled.inputs["Roughness"].default_value = family_params["roughness"]
        principled.inputs["Metallic"].default_value = family_params.get("metallic", 0.0)
        
        # Subsurface scattering (if cloth/skin)
        if family in ("cloth", "skin"):
            principled.inputs["Subsurface Weight"].default_value = family_params.get("subsurface", 0.05)
        
        # Assign material to mesh
        mesh.materials.append(mat)
    
    # Stage 2b: Render 6 canonical views
    setup_camera()  # Orthographic, facing origin
    for view_name, (elev, azim) in CANONICAL_VIEWS.items():
        orient_camera(elev, azim)
        render_and_save(f"processed/views/{asset_id}/{view_name}.png")  # Beauty
        render_and_save(f"processed/views/{asset_id}/{view_name}_depth.exr", pass_type="Z_Depth")  # 16-bit depth
    
    # Stage 2c: Bake textures
    bpy.context.scene.render.engine = "CYCLES"
    bpy.context.scene.cycles.samples = 256  # High quality
    
    # Create image textures for baking targets
    for tex_name in ["albedo", "normal", "roughness", "metallic", "ao"]:
        img = bpy.data.images.new(name=tex_name, width=8192, height=8192)
        
        # Assign to material nodes
        for obj in bpy.context.scene.objects:
            if obj.type != "MESH":
                continue
            
            for mat in obj.data.materials:
                # Create image texture node
                img_node = mat.node_tree.nodes.new("ShaderNodeTexImage")
                img_node.image = img
                mat.node_tree.nodes.active = img_node  # Mark for baking
        
        # Bake
        bpy.ops.object.bake(
            type=BAKE_TYPE_MAP[tex_name],  # "COMBINED", "NORMAL", "ROUGHNESS", etc.
            margin=8,
            use_clear=True
        )
        
        # Save
        img.filepath_raw = f"processed/textures/{asset_id}/{tex_name}.png"
        img.file_format = "PNG"
        img.save()
    
    # Stage 2d: Export textured GLB
    bpy.ops.export_scene.gltf(
        filepath=f"processed/glb/{asset_id}.textured.glb",
        export_format="GLB",
        export_image_format="PNG",
        export_materials=True,
        export_colors=False
    )
```

### Key Parameters

| Parameter | Default | Tuning |
|-----------|---------|--------|
| Cycles samples | 256 | Increase for cleaner bakes (slower); decrease for speed |
| Texture size | 8192 (8K) | 4096 (4K) for env props, 8192 for hero |
| UV margin | 8px | Increases island padding (prevents edge artefacts) |
| Subsurface | family-dependent | Cloth/skin only; controls light penetration |

### Bake Type Map

```python
BAKE_TYPE_MAP = {
    "albedo": "COMBINED",       # Diffuse color (no shadows, no specular)
    "normal": "NORMAL",         # Surface-space normal
    "roughness": "ROUGHNESS",   # Roughness map
    "metallic": "METALLIC",     # Metallic map
    "ao": "AO",                 # Ambient occlusion
}
```

### Failure Modes

- **Smart UV unwrap fails:** degenerate mesh, skipped with warning
- **Out of VRAM:** Blender killed during bake; fallback to lower sample count or smaller texture size
- **Export fails:** permissions issue on processed/glb/ or processed/textures/

### Duration

- **Render 6 views:** ~10 seconds
- **Bake 5 texture maps @ 8K:** ~5–10 minutes (depends on Cycles sample count + VRAM)
- **Export GLB:** ~1 minute

**Total Stage 2:** 5–10 minutes

---

## material_families.py — Material Library

**Purpose:** OpenPBR material definitions per asset family
**Imports:** `from tools.blender.material_families import material_families`

### Structure

```python
material_families = {
    "leather_ledger": {
        "base_color": (0.35, 0.25, 0.15, 1.0),  # RGB + Alpha (dark brown)
        "roughness": 0.75,
        "metallic": 0.0,
        "subsurface": 0.0,
        "ior": 1.5,
        "notes": "Hand-worn leather. Pocket rub patina on high-touch areas."
    },
    "paper_aged": {
        "base_color": (0.85, 0.78, 0.68, 1.0),  # Cream-buff
        "roughness": 0.95,
        "metallic": 0.0,
        "subsurface": 0.05,  # Light penetration for page thickness
        "ior": 1.3,
        "notes": "Off-white aged paper. Slight SSS for translucency at edges."
    },
    "mud_brick": {
        "base_color": (0.55, 0.40, 0.25, 1.0),  # Terra-cotta
        "roughness": 0.85,
        "metallic": 0.0,
        "subsurface": 0.0,
        "notes": "Hand-applied troweling. Mineral efflorescence, edge chips."
    },
    "tin_corrugated": {
        "base_color": (0.70, 0.68, 0.65, 1.0),  # Muted grey-silver
        "roughness": 0.45,  # Lower = shinier (metal sheet)
        "metallic": 0.85,
        "subsurface": 0.0,
        "notes": "Rust streaks in troughs. Mild dents. Water-staining."
    },
    "wood_hewn": {
        "base_color": (0.35, 0.28, 0.20, 1.0),  # Grey-silvered
        "roughness": 0.88,
        "metallic": 0.0,
        "subsurface": 0.0,
        "notes": "Axe marks. Knot eyes. End-grain cracks. Weathered grey."
    },
    "stone_mortar": {
        "base_color": (0.50, 0.45, 0.40, 1.0),  # Neutral grey
        "roughness": 0.95,
        "metallic": 0.0,
        "subsurface": 0.0,
        "notes": "Lichen patches. Mortar wash. Drip-stain runs. Irregular stones."
    },
    "cloth_cotton": {
        "base_color": (0.70, 0.65, 0.60, 1.0),  # Muted off-white
        "roughness": 0.92,
        "metallic": 0.0,
        "subsurface": 0.1,  # Fabric has light penetration
        "notes": "Frayed edges. Micro-weave bump. Dust-staining at cuffs."
    },
    "candle_wax": {
        "base_color": (0.95, 0.92, 0.85, 1.0),  # Pale cream
        "roughness": 0.60,  # Waxy sheen
        "metallic": 0.0,
        "subsurface": 0.15,  # Wax is translucent
        "notes": "Drip trails fused to base. Soot-darkened wick crater."
    },
    "skin_hands": {
        "base_color": (0.75, 0.60, 0.50, 1.0),  # Warm brown
        "roughness": 0.45,
        "metallic": 0.0,
        "subsurface": 0.25,  # Significant SSS (blood flow)
        "ior": 1.4,
        "notes": "Subtle subsurface scatter. Broadened knuckles. Fine micro-folds."
    }
}
```

### Family Detection

```python
def infer_family(asset_id: str) -> str:
    """
    Infer material family from asset id prefix.
    
    Examples:
      prop_ledger_book → "leather_ledger"
      structure_rugo_tin_roof → "tin_corrugated"
      vegetation_eucalyptus_mature → fallback to "wood_hewn"
    """
    # Asset-specific overrides (hand-written)
    overrides = {
        "prop_ledger_book": "leather_ledger",
        "prop_altar_candle": "candle_wax",
        "structure_rugo_tin_roof": "tin_corrugated",
        "structure_rugo_main_house": "mud_brick",
        "figure_investigator_hands": "skin_hands",
        "figure_grandfather_hands": "skin_hands",
    }
    
    if asset_id in overrides:
        return overrides[asset_id]
    
    # Category-based fallback
    category = asset_id.split("_")[0]
    category_fallback = {
        "prop": "wood_hewn",
        "structure": "mud_brick",
        "vegetation": "wood_hewn",
        "figure": "skin_hands",
    }
    
    return category_fallback.get(category, "wood_hewn")
```

### Adding a New Material Family

1. Add entry to `material_families` dict with OpenPBR parameters
2. Update `infer_family()` overrides if asset-specific
3. Update `_STYLE_GUIDE.md` with visual cues
4. Document in template notes

---

## reproject_views.py — Stage 2b Reprojection Prep (TBD)

**Purpose:** Prepare UV-space geometry for AI material projection (stage 2b)
**Status:** Stub; full implementation deferred

When stage 2b (AI projection) is enabled:
1. Stage 2 renders 6 canonical views + depth maps
2. Stage 2b (ComfyUI) projects SDXL-painted materials onto those views
3. `reproject_views.py` would UV-unwrap and set up re-bake with new albedo input
4. Final bake uses new albedo, original normal/roughness/metallic

**Current status:** See [@generation-stages.md](generation-stages.md) Stage 2b note — as of 2026-05-25, AI projection produces incomplete coverage ("white squares"). Recommend `--no-ai-project` (procedural PBR only) for Phase 1.

---

## render_validation.py — Diagnostic Renders

**Purpose:** Generate beauty + normal + depth EXR diagnostic renders for reviewing bake quality

Called post-stage-2 to visually inspect:
- Baked albedo color
- Normal map direction (visualized as RGB)
- Depth map for correctness

**Outputs:** `processed/diagnostics/<id>/` PNG/EXR files (not in critical path)

---

## Material Families Reference

### Heritage Materials (Digital Diorama)

**Mud brick / plaster (structure_rugo_main_house)**
- Base: (0.55, 0.40, 0.25) terra-cotta
- Roughness: 0.85
- Features: hand troweling, efflorescence, edge chips

**Corrugated tin (structure_rugo_tin_roof)**
- Base: (0.70, 0.68, 0.65) muted grey
- Roughness: 0.45, Metallic: 0.85
- Features: rust streaks, dents, water-staining

**Hand-hewn wood**
- Base: (0.35, 0.28, 0.20) grey-silvered
- Roughness: 0.88
- Features: axe marks, knot eyes, weathered grey

**Stone + mortar**
- Base: (0.50, 0.45, 0.40) neutral grey
- Roughness: 0.95
- Features: lichen patches, mortar wash, drip stains

### Artifacts & Objects

**Leather (ledger book)**
- Base: (0.35, 0.25, 0.15) dark brown
- Roughness: 0.75
- Features: pocket-rub patina, edge-cracking

**Paper (aged)**
- Base: (0.85, 0.78, 0.68) cream-buff
- Roughness: 0.95, Subsurface: 0.05 (translucency)
- Features: aged off-white, slight SSS for page edges

**Cloth (cotton)**
- Base: (0.70, 0.65, 0.60) muted off-white
- Roughness: 0.92, Subsurface: 0.1
- Features: frayed edges, micro-weave, dust-staining

**Wax (candle)**
- Base: (0.95, 0.92, 0.85) pale cream
- Roughness: 0.60 (waxy sheen), Subsurface: 0.15
- Features: drip trails, soot crater

### Figures & Hands

**Skin (human hands)**
- Base: (0.75, 0.60, 0.50) warm brown
- Roughness: 0.45, Subsurface: 0.25 (significant SSS)
- Features: subsurface scatter, broadened knuckles, micro-folds

---

## Blender Version & Dependencies

**Minimum version:** Blender 4.0+ (Cycles compositor, modern node structure)
**Python:** via Blender's internal Python (bpy module)
**Rendering:** Cycles (not Eevee or other)

**Key Blender APIs:**
- `bpy.ops.import_scene.gltf()` — GLB import
- `bpy.ops.uv.smart_project()` — automatic UV unwrapping
- `bpy.data.materials.new()` + `.use_nodes = True` — node material creation
- `ShaderNodeBsdfPrincipled` — OpenPBR material node
- `bpy.ops.object.bake()` — texture baking
- `bpy.ops.export_scene.gltf()` — GLB export

---

## Troubleshooting Blender Issues

### "Blender not found"
```bash
which blender  # Should resolve to /usr/bin/blender or similar
# If not, either:
# 1. Install Blender (apt, download, conda)
# 2. Set BLENDER_BIN env var in texture_asset.py
```

### Bake produces solid grey textures
- Likely cause: Principled BSDF not properly configured
- Check: material_families.py parameters for your asset family
- Verify: camera is ortho, facing mesh, no obstructions

### UV unwrap fails silently
- Mesh too degenerate for Smart UV project
- Check Gate 2 (geometry validation) — likely caught there first
- Manual UV layout in Blender if asset is hero prop

### Out of VRAM during bake
- Reduce Cycles sample count (512 → 256 → 128)
- Reduce texture size (8192 → 4096)
- Reduce num of bake passes (bake only albedo + normal, skip roughness/metallic)

---

## Cross-References

- **Stage 2 overview:** [@generation-stages.md](generation-stages.md#stage-2-pbr-texture-baking)
- **Stage 2b projection:** [@generation-stages.md](generation-stages.md#stage-2b-ai-material-projection-optional)
- **Material library design:** [@prompts.md](prompts.md#digital-diorama-style-guide)
- **Material family table:** `_STYLE_GUIDE.md` (reference materials section)

---

**Last updated:** 2026-05-25 | **See also:** [@generation-stages.md](generation-stages.md), [@prompts.md](prompts.md), [@tools.md](tools.md)
