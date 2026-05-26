# Validation Gates — 6-Gate Quality Assurance

> Complete breakdown of the validation gate system that ensures asset quality before registration.
> Each gate is a quality checkpoint; aggregated results guide recovery.
> See [@claude.md](claude.md), [@architecture.md](architecture.md), [@generation-stages.md](generation-stages.md).

---

## Gate System Overview

```
┌──────────────────────────────────────────────────────────────┐
│           Asset Pipeline Validation Harness                 │
│                                                              │
│  Gate 0: Input validation (inline in asset_pipeline.py)    │
│    ↓                                                         │
│  Gate 1: Reference image validation (stage 0/0.25 output)  │
│    ↓                                                         │
│  Gate 2: Geometry validation (stage 1 output)              │
│    ↓                                                         │
│  Gate 3: View synthesis validation (stage 0.5 output)      │
│    ↓                                                         │
│  Gate 4: Aggregate diagnostic (meta-gate, collects 1–5)    │
│    ↓                                                         │
│  Gate 5: PBR texture validation (stage 2 output)           │
│    ↓                                                         │
│  🎯 PASS / RETRY / FAIL                                     │
└──────────────────────────────────────────────────────────────┘
```

Each gate:
1. Validates a specific stage output
2. Writes a JSON report to `processed/diagnostics/<id>.*.json`
3. Either continues (exit 0) or fails hard (exit 2)
4. Gate 4 aggregates all reports and recommends action

---

## Gate 0: Input Validation

**Tool:** inline in `asset_pipeline.py`
**Trigger:** Before any generation
**Input:** CLI args, template YAML, asset id
**Output:** validation or early exit (exit 1 = bad input)

### Checks

```python
def validate_inputs(asset_id: str, kind: str, template_path: Path):
    # Asset ID pattern
    if not re.match(r'^[a-z_][a-z0-9_]{2,}$', asset_id):
        die(f"Invalid asset_id: {asset_id} (must be snake_case, ≥ 3 chars)", 1)
    
    # Kind validation
    if kind not in VALID_KINDS:
        die(f"Unknown kind: {kind}", 1)
    
    # Template YAML structure (if mesh/animated)
    if kind in ("mesh", "animated"):
        if not template_path.exists():
            die(f"Template not found: {template_path}", 1)
        
        template = yaml.safe_load(template_path.read_text())
        required_fields = ["asset_name", "category", "era_scope"]
        for field in required_fields:
            if field not in template:
                die(f"Template missing required field: {field}", 1)
    
    # Reference image (if not --auto-ref)
    if kind in ("mesh", "animated") and not args.auto_ref:
        ref_path = Path(template["reference_image"])
        if not ref_path.exists():
            die(f"Reference image not found: {ref_path}", 1)
    
    # Server health (if generation required)
    if kind in ("mesh", "animated"):
        if not _comfy_alive() and not _hunyuan_alive():
            die("ComfyUI and/or Hunyuan3D not running", 1)
    
    return True
```

**Failure modes:**
- Invalid asset id → exit 1
- Unknown kind → exit 1
- Missing template (mesh/animated) → exit 1
- Bad template YAML → exit 1
- Reference image missing (no --auto-ref) → exit 1
- Servers not running → exit 1

**Exit code:** 1 (bad input, operator error)

---

## Gate 1: Reference Image Validation

**Tool:** `validate_ref_image.py`
**Trigger:** After stage 0 or 0.25
**Input:** `prompts/asset-templates/<id>/ref.png`
**Output:** `processed/diagnostics/<id>.ref_image.json`

### Checks

```python
@dataclass
class RefImageReport:
    asset_id: str
    ref_path: str
    
    # Checks
    exists: bool                  # file found?
    file_size: int               # bytes (warn if < 100 KB)
    dimensions: tuple[int, int]  # (width, height)
    resolution_floor: bool       # width × height ≥ 1024²
    aspect_ratio: float          # width / height (warn if extreme < 0.5 or > 2.0)
    color_space: str             # sRGB (expected)
    alpha_channel: bool          # has alpha (warn if yes)
    
    # Summary
    passed: bool
    warnings: list[str]
    recommended_action: str      # pass | retry_with_new_ref | fail
```

### Validation Rules

1. **Existence:** file must exist
2. **File size:** warn if < 100 KB (likely too small/compressed)
3. **Resolution floor:** 1024² minimum (Hunyuan quality degrades on small images)
4. **Dimensions:** aspect ratio 0.5–2.0 (warn if extreme)
5. **Color space:** expect sRGB (not CMYK, grayscale)
6. **Alpha channel:** warn if present (shouldn't need transparency)

### Report Example

```json
{
  "asset_id": "prop_ledger_book",
  "ref_path": "prompts/asset-templates/prop_ledger_book/ref.png",
  "checks": {
    "exists": true,
    "file_size": 2456789,
    "dimensions": [1536, 1024],
    "resolution_floor": true,
    "aspect_ratio": 1.5,
    "color_space": "sRGB",
    "alpha_channel": false
  },
  "passed": true,
  "warnings": [],
  "recommended_action": "pass"
}
```

**Failure modes:**
- File not found → fail
- File < 1024² → fail
- Extreme aspect ratio → warn (continue)
- Bad color space → warn (continue)

**Exit code:** 0 (warn or pass), 2 (fail)

---

## Gate 2: Geometry Validation

**Tool:** `validate_geometry.py`
**Trigger:** After stage 1 (Hunyuan3D output)
**Input:** `processed/glb/raw/<id>.glb`
**Output:** `processed/diagnostics/<id>.geometry.json`

### The Problem Gate 2 Solves

Hunyuan3D occasionally produces degenerate output:
- Flat depth cards (thin Z-axis, < 2% of width/height)
- Off-center or upside-down geometry
- Floating debris islands
- Vertex count outliers

This gate catches those before wasting 5+ hours on baking.

### Checks

```python
@dataclass
class GeometryReport:
    asset_id: str
    glb_path: str
    
    # Metrics
    vertex_count: int
    face_count: int
    bounds: tuple[float, float, float]  # (width, height, depth)
    bbox_depth_ratio: float              # min(extents) / max(extents)
    centroid_offset: tuple[float, float, float]
    is_manifold: bool
    has_non_manifold_edges: bool
    
    # Thresholds
    depth_ratio_check: bool              # >= 0.10
    poly_budget_check: bool              # within [0.5×, 2.0×] target
    vertex_count_check: bool             # in [1K, 2M]
    centroid_offset_check: bool          # <= 0.3 × max(extents)
    manifold_check: bool                 # strictly true or warning-only
    
    # Summary
    passed: bool
    failed_checks: list[str]
    warnings: list[str]
    recommended_action: str  # pass | retry_with_new_seed | fail
```

### Validation Rules

1. **Bbox depth ratio:** min(extents) / max(extents) ≥ 0.10
   - Catches flat depth cards (< 2% Z-thickness fails)
   - Formula: if width=512px, height=512px, Z=25px → 25/512 ≈ 0.049 → FAIL

2. **Poly budget:** face_count ∈ [0.5 × target, 2.0 × target]
   - Target from template `target_poly_lod0` field
   - Catches Hunyuan degenerate output (too few faces)
   - Warns on high-poly output (will be decimated later, acceptable)

3. **Vertex count:** 1K–2M
   - Sanity bound on degenerate output

4. **Centroid offset:** |centroid| ≤ 0.3 × max(extents)
   - Catches upside-down or off-origin geometry

5. **Manifold:** ideally true, but warning-only (hero meshes can have intentional holes/cuts)
   - Strict check with `--strict-manifold` flag

### Report Example

```json
{
  "asset_id": "prop_ledger_book",
  "glb_path": "processed/glb/raw/prop_ledger_book.glb",
  "metrics": {
    "vertex_count": 24650,
    "face_count": 8234,
    "bounds": [0.18, 0.21, 0.03],
    "bbox_depth_ratio": 0.14,
    "centroid_offset": [-0.005, 0.001, 0.008],
    "is_manifold": true
  },
  "checks": {
    "depth_ratio_check": true,
    "poly_budget_check": true,
    "vertex_count_check": true,
    "centroid_offset_check": true,
    "manifold_check": true
  },
  "passed": true,
  "failed_checks": [],
  "warnings": [],
  "recommended_action": "pass"
}
```

### Failure Diagnosis

**Flat depth card detected:**
```json
{
  "failed_checks": ["depth_ratio_check"],
  "recommended_action": "retry_with_new_seed",
  "notes": "Likely single-view collapse; try --multi-view or new seed"
}
```

**Too few faces:**
```json
{
  "failed_checks": ["poly_budget_check"],
  "recommended_action": "retry_with_new_seed",
  "notes": "Face count 1,200 < target 4,000 (30%); degenerate output"
}
```

**Exit code:** 0 (pass + warnings), 2 (fail)

**Recovery:** retry with new seed (Gate 4 recommends `retry_with_new_seed`)

---

## Gate 3: View Synthesis Validation

**Tool:** `validate_views.py`
**Trigger:** After stage 0.5 (if `--multi-view` used)
**Input:** `processed/views/<id>/{front,back,left,right,top,bottom}.png` + depth EXRs
**Output:** `processed/diagnostics/<id>.views.json`

### Checks

```python
@dataclass
class ViewsReport:
    asset_id: str
    views_dir: str
    
    # Completeness
    views_found: dict[str, bool]       # front, back, left, right, top, bottom
    depth_maps_found: dict[str, bool]
    
    # Per-view metrics
    dimensions: dict[str, tuple]       # resolution per view
    consistency_check: bool            # all views same resolution?
    depth_map_validity: dict[str, bool] # depth range non-trivial?
    
    # Summary
    passed: bool
    missing_views: list[str]
    invalid_depth_maps: list[str]
    recommended_action: str           # pass | fail
```

### Validation Rules

1. **Completeness:** all 6 views present
2. **Resolution:** all views same size
3. **Depth validity:** depth map min/max span (not flat)
4. **File integrity:** loadable as PNG/EXR

### Report Example

```json
{
  "asset_id": "prop_ledger_book",
  "views_dir": "processed/views/prop_ledger_book",
  "completeness": {
    "front": true,
    "back": true,
    "left": true,
    "right": true,
    "top": true,
    "bottom": true,
    "depth_front": true,
    "depth_back": true,
    "depth_left": true,
    "depth_right": true,
    "depth_top": true,
    "depth_bottom": true
  },
  "consistency": {
    "all_same_resolution": true,
    "resolution": [2048, 2048]
  },
  "depth_validity": {
    "front": true,
    "back": true,
    "left": true,
    "right": true,
    "top": true,
    "bottom": true
  },
  "passed": true,
  "missing_views": [],
  "invalid_depth_maps": [],
  "recommended_action": "pass"
}
```

**Exit code:** 0 (pass), 2 (fail)

---

## Gate 4: Aggregate Diagnostic (Meta-Gate)

**Tool:** `diagnostic_report.py`
**Trigger:** After all preceding gates
**Input:** sidecars `<id>.*.json` (gates 1, 2, 3, 5)
**Output:** `processed/diagnostics/<id>.aggregate.json`

### Purpose

Collect all gate reports and recommend next action. This is the operator's signal for what to do next.

### Report Structure

```json
{
  "asset_id": "prop_ledger_book",
  "gates_ran": ["1", "2", "3", "5"],
  "gates_failed": [],
  "summary": "All gates passed",
  "recommended_action": "pass",
  "timestamp": "2026-05-25T14:23:18Z"
}
```

### Recommended Actions

| Action | Meaning | Operator Action |
|--------|---------|-----------------|
| `pass` | All gates passed | Proceed to runtime (asset is ready) |
| `retry_with_new_seed` | Gate 2 (geometry) failed | Increment seed by 10,000, re-run stage 1 |
| `retry_with_refined_ref` | Gate 1 (ref image) failed | Re-run stage 0.25 with adjusted strength |
| `manual_review_required` | Multiple gate failures | Inspect individual gate reports, debug manually |
| `fail` | Unrecoverable failure | Stop, requires manual intervention |

### Automatic Retry Logic (asset_pipeline.py)

When Gate 2 fails with `recommended_action == "retry_with_new_seed"`:

```python
if aggregate_json.get("recommended_action") == "retry_with_new_seed":
    ctx.seed += RETRY_SEED_STRIDE  # 10,000
    return run_mesh_pipeline(ctx)  # Recursive call, re-run stage 1 only
```

Max retries: configurable (TBD, currently unbounded with user override).

**Exit code:** 0 (always, just a report)

---

## Gate 5: PBR Texture Validation

**Tool:** `validate_pbr.py`
**Trigger:** After stage 2 (Blender bake output)
**Input:** `processed/textures/<id>/{albedo,normal,mr}.ktx2` (or PNG before compression)
**Output:** `processed/diagnostics/<id>.pbr.json`

### The Problem Gate 5 Solves

Stage 2b (AI projection) can produce "white square" artefacts: SDXL projection paints only a fraction of UV space, leaving rest at Blender's mid-grey default.

### Checks

```python
@dataclass
class PBRReport:
    asset_id: str
    textures_dir: str
    
    # Completeness
    has_albedo: bool
    has_normal: bool
    has_mr: bool
    all_decodable: bool
    
    # Resolution
    resolution: tuple[int, int]
    resolution_match: bool      # all maps same size?
    resolution_floor: bool      # >= 1024 for hero, 512 else
    
    # Albedo checks
    albedo_fill_ratio: float    # % pixels at default fill colour (mid-grey)
    albedo_luminance_mean: float # mean pixel luminance
    albedo_checks: dict[str, bool]
    
    # Normal map checks
    normal_rg_means: tuple[float, float]  # R, G channel means (expect ~0.5)
    normal_b_mean: float                   # B channel mean (expect > 0.55)
    normal_checks: dict[str, bool]
    
    # MR packing checks
    mr_r_channel_mean: float    # should be very small (R=unused)
    mr_variance: dict[str, float]  # G (roughness) + B (metallic) variance
    mr_checks: dict[str, bool]
    
    # Summary
    passed: bool
    failed_checks: list[str]
    recommended_action: str
```

### Validation Rules

1. **Completeness:** albedo, normal, mr present and decodable
2. **Resolution match:** all maps same width/height
3. **Resolution floor:** ≥ 1024² for hero, ≥ 512² otherwise
4. **Albedo fill:** < 5% pixels at default fill colour (catches half-projected output)
5. **Albedo luminance:** mean ∈ [0.05, 0.85] (not all-black, not white-card)
6. **Normal distribution:**
   - R channel mean near 0.5 (±0.10)
   - G channel mean near 0.5 (±0.10)
   - B channel mean > 0.55 (surface-aligned, not inverted)
7. **MR packing:**
   - R channel ≤ 5/255 (unused per OpenPBR spec)
   - G (roughness) variance ≥ 1e-4 (not flat)
   - B (metallic) variance ≥ 1e-4 (not flat)

### Report Example

```json
{
  "asset_id": "prop_ledger_book",
  "textures_dir": "processed/textures/prop_ledger_book",
  "completeness": {
    "has_albedo": true,
    "has_normal": true,
    "has_mr": true,
    "all_decodable": true
  },
  "resolution": [8192, 8192],
  "checks": {
    "resolution_match": true,
    "resolution_floor": true,
    "albedo_fill": true,
    "albedo_luminance": true,
    "normal_distribution": true,
    "mr_packing": true
  },
  "passed": true,
  "failed_checks": [],
  "recommended_action": "pass"
}
```

### Failure Example (AI Projection Artefact)

```json
{
  "asset_id": "prop_ledger_book",
  "failed_checks": ["albedo_fill"],
  "albedo_fill_ratio": 0.35,
  "notes": "35% of albedo at mid-grey default; AI projection incomplete",
  "recommended_action": "retry_with_refined_ref"
}
```

**Exit code:** 0 (pass), 2 (fail with recommendation to re-run stage 2)

---

## Gate Workflow Example: Happy Path vs. Retry

### Happy Path (All Gates Pass)

```
Gate 1: PASS (ref image valid)
Gate 2: PASS (mesh valid)
Gate 3: PASS (views valid, if multi-view)
Gate 4: aggregate → recommended_action = "pass"
Gate 5: PASS (textures valid)
        ↓
    ✅ Asset ready for registration
```

### Retry Path (Gate 2 Fails)

```
Gate 1: PASS
Gate 2: FAIL (flat depth card)
Gate 4: aggregate → recommended_action = "retry_with_new_seed"
        ↓
    Increment seed by 10,000
    Re-run stage 1 (Hunyuan3D)
        ↓
Gate 2 (retry): PASS
Gate 4 (retry): PASS
Gate 5: PASS
        ↓
    ✅ Asset ready for registration
```

---

## Integration with asset_pipeline.py

Each gate is called via subprocess in asset_pipeline.py:

```python
def run_mesh_pipeline(ctx: PipelineContext) -> int:
    # ...
    
    # Gate 1
    if not run_validator(VALIDATE_REF_IMAGE, ctx.ref_image, ctx.diag_dir / f"{ctx.asset_id}.ref_image.json"):
        ctx.gates_failed.append("1")
        return die("Gate 1 failed", 2)
    ctx.gates_ran.append("1")
    
    # Gate 2
    if not run_validator(VALIDATE_GEOMETRY, ctx.raw_glb, ctx.diag_dir / f"{ctx.asset_id}.geometry.json"):
        # Check aggregate for retry recommendation
        agg = load_json(ctx.diag_dir / f"{ctx.asset_id}.aggregate.json")
        if agg.get("recommended_action") == "retry_with_new_seed":
            ctx.seed += RETRY_SEED_STRIDE
            return run_mesh_pipeline(ctx)  # Recursive retry
        ctx.gates_failed.append("2")
        return die("Gate 2 failed", 2)
    ctx.gates_ran.append("2")
    
    # ... continue through stages 3–5, run gates 3 and 5 ...
    
    # Gate 4 (aggregate)
    run_validator(DIAGNOSTIC_REPORT, ctx.diag_dir, ctx.diag_dir / f"{ctx.asset_id}.aggregate.json")
    ctx.gates_ran.append("4")
    
    return 0  # Success
```

---

**Last updated:** 2026-05-25 | **See also:** [@tools.md](tools.md), [@generation-stages.md](generation-stages.md), [@architecture.md](architecture.md)
