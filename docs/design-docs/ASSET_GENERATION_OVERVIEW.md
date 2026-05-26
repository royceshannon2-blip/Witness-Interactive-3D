# Asset Generation Architecture — Comprehensive Overview & Quality Plan

**Status:** Re-audit complete 2026-05-22 (revised after root-cause analysis of "white flat squares" failure mode)
**Owner:** @royceshannon2
**Related:** [`ASSET_PIPELINE.md`](ASSET_PIPELINE.md) (stage specs), [`RENDERING.md`](RENDERING.md) (PBR contract), [`../../prompts/asset-templates/_STYLE_GUIDE.md`](../../prompts/asset-templates/_STYLE_GUIDE.md) (Digital Diorama)

---

## 0. ROOT-CAUSE ANALYSIS — Why Current Outputs Are White Flat Squares

The 2026-05-22 re-audit traced the "two flat untextured squares" failure mode on `figure_grandfather_hands` (and likely all single-photo-reference assets) to **four foundational defects** in the pipeline. These cascade — fixing only one will not produce triple-A output.

| # | Defect | Where | Evidence |
|---|---|---|---|
| 1 | **Hunyuan produces depth-cards, not 3D meshes, from single-view input** | `tools/generate_asset.py` — `--multi-view` is opt-in and was off for the failing run | Raw GLB bbox: X ±1.0, Y ±1.0, **Z ±0.018** — 0.03 units thick. 297k verts spread on a near-flat plane. |
| 2 | **Hunyuan inference steps silently clamped from 60 → 20** | `generate_asset.py:59` — `min(args.steps, 20)` with comment "API max is 20" | Template `figure_grandfather_hands.md` requests `inference_steps: 60`; logs would show 20 ran. Cause of the cap (worker enforcement vs. stale default) is unverified. |
| 3 | **Blender beauty renders are entirely black** | `tools/blender/bake_pbr.py:render_views()` — no lights added, `film_transparent=True`, world background is empty | `processed/views/figure_grandfather_hands/back.beauty.png`, `bottom.beauty.png` are 100% black. `left.beauty.png` is a 1-pixel vertical line (side view of a near-2D plane). |
| 4 | **AI projection (stage 2b) is fed dark / empty conditioning** | Downstream consequence of #1 + #3 | `front.pbr.png` shows extremely dark hands; `figure_grandfather_hands_albedo.ai.png` has **only the bottom half of the UV filled** — the top half is black because UV unwrap of a flat mesh produces front-patch + back-patch, and the back patch was unlit. |

### Secondary issues that compound the above

- **Procedural fallback is wrong-looking.** When AI projection fails or produces low-coverage output, `bake_pbr.py:build_material()` falls back to Voronoi/Noise networks that produce blobby procedural patterns unrelated to the asset (e.g., bubbled "skin" instead of weathered hand texture).
- **No early validation.** The pipeline runs the full ~2 hour bake + optimization chain on geometrically broken raw GLBs. The audit's previous "post-mesh sanity check" recommendation was rated MEDIUM; it should be HIGH because it would catch defect #1 in seconds.
- **Stage 2b uses SDXL with a 280-character truncated prompt window.** The Digital Diorama description is several hundred words; SDXL gets a paragraph and loses style fidelity.

### The pipeline's previous quality bet was wrong

The original audit (May 22 morning) prioritized adding **validation infrastructure** (P0: post-Hunyuan validator, channel-packing checker) but did not propose touching the **input quality controls** (multi-view default, step cap, lighting). Validation alone catches failures after the fact; it does not produce triple-A output. **This revised plan inverts the priority: fix the foundations first, then add validation gates as fail-fast checks.**

---

## 1. FULL PIPELINE ARCHITECTURE (current implementation)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    WITNESS ASSET GENERATION WORKFLOW                     │
└─────────────────────────────────────────────────────────────────────────┘

STAGE 0: Reference Image Generation
  Input:  asset template (<id>.md)
  ├─ Flux.1 [dev] @1024² / 40 steps  →  raw ref.png
  │  via ComfyUI at localhost:8188
  └─ [FALLBACK] hand-dropped ref.png accepted
  Output: prompts/asset-templates/<id>/ref.png

STAGE 0.25: Reference Refinement (ALWAYS ON for mesh/animated)
  Input:  ref.png (from stage 0 or hand-dropped)
  ├─ FLUX.2 [klein] 9B Base img2img  →  refined ref.png
  │  denoise strength by category:
  │    • vegetation: 0.60  (push palette hard)
  │    • structure:  0.40  (protect geometry)
  │    • prop/figure: 0.50 (balanced)
  ├─ Preserves pre-refine as ref.original.png
  └─ Idempotent: re-runs no-op if ref.original.png exists
  Output: ref.png (refined), ref.original.png (audit copy)

STAGE 0.5: Multi-View Augmentation  ◀── ALWAYS-ON for mesh/animated (--no-multi-view opts out)
  Input:  ref.png   (OR real_views/ — author photos, win over synthesis)
  ├─ rembg cut-out + frame_subject (centre/square @85%)  ◀── kills the slab root cause
  ├─ Zero123++ v1.2  →  6 canonical views   [SKIPPED when real_views supplied]
  │  elevations: 30°/-20° across azimuths 30°/90°/150°/210°/270°/330°
  │  output: 320×320 PNG per view
  ├─ Gate 1: validate_views.py --indexed — pixel + all-view CLIP + cross-view colour
  └─ Sequential VRAM: Flux exits → Zero123++ runs → Hunyuan picks up
  Output: prompts/asset-templates/<id>/views/view_0..N.png

STAGE 1: Mesh Generation (Hunyuan3D 2.1)
  Input:  ref.png + multi-view list (now always 6 views)
  ├─ Docker container @ localhost:8081
  │  • Multi-view → GLB (patched model_worker.py accepts list)
  │  • Inference steps: ◀── 50-75 target (currently capped at 20; needs worker fix)
  │  • Octree resolution: ◀── 512 target for hero (currently 256 default)
  │  • Guidance scale: ◀── 8-10 target for prompt adherence (currently 5)
  ├─ ◀── NEW: ensemble mode — N seeds in parallel, pick highest-scoring
  └─ ◀── NEW: post-gen geometric validator (bbox, manifold, poly count)
  Output: processed/glb/raw/<id>.glb (~30–150 MB, unoptimized)

STAGE 2: Texturing & PBR Bake
  ├─ 2a: Blender headless (bake_pbr.py)
  │       • Import raw GLB
  │       • Pre-bake decimation (--target-faces 40000)
  │       • Smart UV unwrap if missing
  │       • ◀── NEW: 3-point lighting + HDRI for view renders (NOT black anymore)
  │       • ◀── NEW: real depth EXR via Cycles render layers + compositor
  │       • Cycles bake @ 8K:
  │         - Albedo (color)
  │         - Metallic-Roughness (R=unused, G=roughness, B=metallic)
  │         - Normal map (OpenGL Y+)
  │         - AO (ambient occlusion)
  │       • Export textured GLB
  │       Output: processed/textures/<id>_*.png, textured GLB (~500MB)
  │
  └─ 2b: AI Projection  ◀── REPLACE SDXL with FLUX.2 [klein]
         ├─ Render 6 views + real depth maps from textured GLB
         ├─ FLUX.2 [klein] + ControlNet (depth) projects material maps
         │  prompt = FULL asset description + PBR modifiers + Digital Diorama + negative
         │  per-view prompt variation ("front view of X", "back view of X", ...)
         ├─ Blender UV-reprojects AI views back onto mesh UV
         ├─ ◀── NEW: LPIPS multi-view consistency check (fail-fast on incoherent projection)
         └─ Output: final textured GLB with AI-projected materials

STAGE 3: Optimization & Compression
  Input:  textured GLB
  ├─ [3a] Detached-component cleanup (trimesh)
  │       • Strips floating islands > 1% of largest component volume
  ├─ [3b] Mesh simplification (weld + gltf-transform)
  │       • Pre-Draco face reduction: --target-faces 40000
  │       • Weld merges UV-seam duplicates
  ├─ [3c] Draco compression (gltf-pipeline)
  │       • Geometry: level 7
  ├─ [3d] KTX2 texture compression (toktx)
  │       • Normals: UASTC (lossless)
  │       • Albedo/MR: ETC1S (lossy)
  └─ ◀── NEW: PBR channel-packing validator (fail-fast on mis-packed MR)
  Output: processed/glb/<id>.glb (~1–4 MB per LOD)

STAGE 4: LODs (Decimated Variants)
  ├─ LOD0 (full)
  ├─ LOD1: 50% reduction (15–50 m)
  └─ LOD2: 85% reduction (50+ m)

STAGE 5: Collision Hulls (V-HACD)
  └─ ≤16 hulls per asset

STAGE 6: Validation Renders (Blender Cycles + HDRI turntable)
  └─ 4 azimuth × 3 elevation = 12 frames

STAGE 7: Asset Registration
  ├─ Append docs/asset-index.md row
  └─ Export to public/assets/<id>.glb

RUNTIME RESOLUTION (Babylon.js)
  ├─ AssetLibrary.load(id) → LOD0 + LOD1 + LOD2 + metadata
  ├─ tagNode(mesh, era_scope) applies layer masks
  └─ instantiate(asset, scope) → cloned + placed scene
```

---

## 2. DATA FLOW DIAGRAM (target state)

```
author writes prompt
       ↓
[0: Flux.1 ref gen] → ref.png (or hand-drop)
       ↓
[0.25: FLUX.2 refine] ──→ ref.original.png (audit copy)
       ↓
[0.5: Zero123++ multi-view] ──→ 6 views + CLIP-score gate
       ↓                                ↓ (fail → retry/halt)
[1: Hunyuan3D ENSEMBLE (N seeds)] ──→ N raw GLBs
       ↓                                ↓ (validator gates each)
[1.5: pick best by geometric score] → 1 raw GLB
       ↓
[2a: Blender bake]
   ├─ lighting + HDRI in scene
   ├─ Cycles render layers: beauty + depth + normal
   ├─ decimate 40K, smart UV
   └─ bake 8K Albedo/MR/Normal/AO
       ↓
[2b: FLUX.2 [klein] + depth ControlNet] → 6 PBR-styled views
       ↓                                    ↓ (LPIPS consistency gate)
[2c: Blender UV reproject]
       ↓
[3a–3d: cleanup / simplify / Draco / KTX2 + channel validator]
       ↓
[4: LOD generation]
       ↓
[5: V-HACD collision]
       ↓
[6: Validation renders + visual audit]
       ↓
[7: Register + export]
       ↓
Runtime: AssetLibrary.instantiate(id) → Babylon scene

⚠ At every ┃ gate, hard-fail + auto-retry with new seed (up to 3 attempts)
  Failure writes processed/diagnostics/<id>.report.md and exits non-zero
```

---

## 3. QUALITY CONTROL — Current vs Target

### Current state (and why "white flat squares" ship today)

| Stage | What runs | What's broken |
|---|---|---|
| 0–0.25 | Prose → Flux → FLUX.2 refine | Adequate; ref.png quality is fine on grandfather_hands |
| 0.5 | Zero123++ multi-view | **NEVER RUNS — opt-in flag was off for all current assets** |
| 1 | Hunyuan single-image, 20 steps, octree 256, guidance 5 | **Generates near-2D depth-cards; silently caps steps below template request** |
| 2a | Blender Cycles bake | **Beauty renders are black (no lights); depth EXR was lost in Blender 5.x upgrade** |
| 2b | SDXL + depth ControlNet | **Prompt truncated to 280 chars; conditioning input is dark/empty; per-view prompt = same string** |
| 2c | Blender UV reproject | Works, but receives garbage from 2b |
| 3 | Draco + KTX2 | No PBR channel-packing validation |

### Target state (every box must be green for triple-A)

| Stage | Quality control | Status |
|---|---|---|
| 0.5 | **Always-on** multi-view, CLIP-validated | ✅ DONE (Phase B, 2026-05-22) |
| 1 | Always-on multi-seed ensemble (configurable N), best-of-N selection by geometric score | ✅ DONE (Phase E, 2026-05-22) |
| 1 | Lift Hunyuan step cap (worker investigation) or compensate with octree 512 + guidance 8-10 | ✅ DONE (Phase B, 2026-05-22) |
| 1 | Post-Hunyuan geometric validator: bbox-not-flat (Z/max(X,Y) > 0.1), manifold, poly budget ±50% | ✅ DONE (Phase A, 2026-05-22) |
| 2a | 3-point lighting + HDRI in render_views; depth EXR restored via render-layer compositor | ✅ DONE (Phase C, 2026-05-22) |
| 2a | Cycles samples adaptive (per-category density × material complexity) | TODO (deferred — Cycles samples currently fixed at template default via `--bake-samples`) |
| 2b | **Replace SDXL with FLUX.2 [klein]**; full template body in prompt; negative prompt from MUST-NOT constraints; per-view prompt variation | ✅ DONE (Phase D, 2026-05-22) |
| 2b | LPIPS consistency gate across adjacent views | ✅ DONE (Phase A, 2026-05-22) |
| 3 | PBR channel-packing validator (R≈0, G=roughness, B=metallic, Y+ normal convention) | ✅ DONE (Phase A, 2026-05-22) |
| All | Hard-fail + auto-retry (3 seeds) on validation failure; emit diagnostic report | ✅ DONE (Phase F, 2026-05-22) |
| All | Poly-count / texture-coverage / consistency metrics logged to asset-index.md | ✅ DONE (2026-05-24) — face_count + gates verdict in asset-index.md via updated register_asset.py |

---

## 4. APPROVED IMPROVEMENT PLAN (2026-05-22 decisions)

These supersede the previous P0/P1/P2 ordering. They reflect the user directive: **maximum quality, prompt adherence, speed does not matter.**

### Approved Decisions

| # | Decision | Rationale |
|---|---|---|
| D1 | **Multi-view always-on** for mesh + animated, with CLIP-score pre-validation of the 6 synth views | Fixes root cause #1 (flat geometry). CLIP gate fails fast if Zero123++ produced garbage views (e.g., from a poor ref). Adds ~3-5 min per asset + ~30s validation overhead. |
| D2 | **Investigate Hunyuan step cap** AND lift it AND bump octree to 512 AND bump guidance to 8-10 | Belt-and-suspenders: even if the API cap is truly enforced, finer octree + stricter guidance recovers detail. If the cap is just a stale default, lifting it gives the largest quality boost. |
| D3 | **Replace SDXL with FLUX.2 [klein]** in stage 2b | FLUX.2 already runs in ComfyUI for stage 0.25; better prompt adherence; longer prompt window (~512 tokens vs SDXL's 77). Requires authoring `flux2_pbr_projection.json` workflow. |
| D4 | **Refactor bake_pbr.py** to use Cycles render layers properly: lighting (HDRI + 3-point), depth EXR + normal EXR via compositor, beauty pass via single render call | Fixes root causes #3 and #4. ~1 day of Blender plumbing but produces correct conditioning inputs for stage 2b regardless of which projector runs. |
| D5 | **Multi-seed ensemble always-on for ALL assets** | User directive. Multiplies compute by N (default N=3, configurable per template). Best-of-N selection uses the geometric validator from D6 below. |
| D6 | **Hard-fail + auto-retry with up to 3 different seeds** on validation failure at any stage | After 3 failures, halt the pipeline, write `processed/diagnostics/<id>.report.md` with failure metrics, exit non-zero. Triple-A means we do not ship broken art. |

### Validation Gates (introduced by D1, D2, D5, D6)

Every gate is a hard fail with auto-retry. Each gate's metric must be configurable per template.

```
Gate 1 (stage 0.5):  per-view luminance/contrast/coverage in range
                     all-view CLIP contrast test: P(real subject) ≥ 0.40 for
                       EVERY view — softmax of prompt vs failure-mode negatives
                       (grey primitive / featureless block / blob / corrupt);
                       transformers CLIP; runs for synth AND real-view sets
                     cross-view foreground-colour within tolerance (WARN, ≥5 views)
Gate 2 (stage 1):    bbox depth ≥ 0.10 × max(width, height)
                     manifold == True
                     poly count within [0.5×, 2.0×] of template target_poly_lod0
                     centroid offset ≤ 0.3 × max(bbox dimension)
Gate 3 (stage 2a):   beauty render pixel-coverage ≥ 60% (i.e. NOT a black image)
                     depth EXR exists and has non-zero variance
Gate 4 (stage 2b):   mean LPIPS across opposed view pairs ≤ 0.45  (= consistency ≥ 0.55)
                     albedo texture coverage ≥ 80% non-black pixels
Gate 5 (stage 3):    MR R channel mean ≤ 0.05
                     normal map is Y+ convention (sample 100 pixels; check G channel ≥ R channel on average)
```

### Removed / De-prioritized from Previous Plan

| Item | Why removed |
|---|---|
| "Reference image quality scoring" (audit P1) | Superseded by CLIP-score on the multi-view synth (Gate 1) — that's a stronger signal than scoring the input ref alone. |
| "Multi-seed ref ensemble" (audit P2) | Replaced by multi-seed mesh ensemble (D5) — better to vary the expensive step where variation actually matters. |
| "Inference step adaptation by category" (audit P1) | All assets now use the maximum step count permitted by the worker; per-category tuning premature until the cap question (D2) is resolved. |
| "Channel-packing validator as a warning" (audit P0) | Now a hard-fail gate (Gate 5). No warnings — pass or fail. |

### Net change to pipeline compute time

| Asset class | Before (single-photo, no ensemble) | After (multi-view + ensemble N=3) | Multiplier |
|---|---|---|---|
| Iteration | ~25 min | ~80 min | ~3.2× |
| Hero asset (validation renders + ensemble N=5) | ~90 min | ~4–5 hr | ~3× |

User has accepted the trade.

---

## 5. IMPLEMENTATION SEQUENCE (recommended order)

Each phase is independently shippable; later phases depend on earlier validation gates being in place.

### Phase A — Validation gates (foundation)

**Goal:** Stop shipping broken art. Make all subsequent quality work measurable.

1. Implement `tools/validate_geometry.py` (post-Hunyuan validator: bbox-not-flat, manifold, poly budget, centroid).
2. Implement `tools/validate_pbr.py` (channel packing, normal convention).
3. Implement `tools/validate_views.py` (beauty coverage, depth variance, LPIPS consistency).
4. Add `tools/diagnostic_report.py` to emit `processed/diagnostics/<id>.report.md` on failure.
5. Wire all gates into `tools/asset_pipeline.py` with hard-fail semantics.

### Phase B — Fix Hunyuan input quality

1. Make `--multi-view` default ON for mesh/animated kinds; add `--no-multi-view` escape hatch.
2. Add CLIP-score validation in `generate_multi_views.py`; emit `views/_scores.json`.
3. Investigate Hunyuan worker step cap (check `model_worker.py` in container).
4. Lift the cap if possible; in any case bump `octree_resolution` default to 512 and `guidance_scale` to 8.0.

### Phase C — Fix Blender bake

1. Refactor `tools/blender/bake_pbr.py:render_views()` to add 3-point + HDRI lighting (mirror `render_validation.py`).
2. Restore depth EXR output via Blender 5.x Compositor node-group API; emit normal EXR alongside.
3. Convert to single render call producing beauty/depth/normal as separate output sockets of one render layer.

### Phase D — Replace stage 2b projector

1. Author `prompts/_pbr_workflows/flux2_pbr_projection.json` (FLUX.2 [klein] + depth ControlNet).
2. Rewrite `tools/texture_asset.py:ai_project()` to call the FLUX.2 workflow.
3. Use full template body (no 280-char truncation) + negative prompt parsed from MUST-NOT constraints.
4. Add per-view prompt variation ("front view of...", "back view of...", etc).

### Phase E — Multi-seed ensembling

1. Implement `tools/ensemble_generate.py` orchestrating N parallel Hunyuan jobs.
2. Score each candidate by Gate 2 metrics; pick highest-scoring.
3. Cleanup non-winning candidates; retain winner's raw GLB and seed metadata.

### Phase F — Auto-retry harness

1. Wrap the pipeline in a retry loop with seed advancement on failure.
2. Cap at 3 attempts; surface aggregated failure report.

### Validation milestones

After each phase, re-run the canary asset (`figure_grandfather_hands` — the documented failure case from this audit). Promote to triple-A reference when:

- Bbox depth ≥ 30% of max(width, height) (real hands, not depth-card)
- Beauty renders show lit, fully-visible hands from all 6 angles
- Albedo coverage ≥ 95% across both UV patches
- PBR projection passes LPIPS consistency
- Visual audit reads as a weathered grandfather's hands at macro DOF

---

## 6. ARCHITECTURAL BOTTLENECKS — Updated

| Bottleneck | Current | Plan | Net gain |
|---|---|---|---|
| **Hunyuan input quality** | Single-image flat-card output | Multi-view always-on (D1) | Eliminates flat-square failure mode |
| **Hunyuan step count** | Hardcoded clamp to 20 | Investigate worker + bump octree/guidance (D2) | Topology and prompt fidelity |
| **Stage 2a lighting** | Empty world, no lights → black renders | HDRI + 3-point (D4) | Stage 2b input is usable |
| **Stage 2a depth pass** | Lost in Blender 5.x | Restore via compositor (D4) | Real depth-ControlNet conditioning |
| **Stage 2b projector** | SDXL with 280-char prompt | FLUX.2 [klein] with full body + negatives (D3) | Style adherence and prompt fidelity |
| **Reliability** | Silent garbage at every stage | Hard-fail + auto-retry (D6) | Triple-A or visibly reject |
| **Variance** | Single seed | Ensemble N=3 always-on (D5) | Best-of-N geometric quality |

---

## 7. SUMMARY — Approved Work Items

| Phase | Items | Touches | Estimated effort |
|---|---|---|---|
| A | Validation gates + diagnostics | new validate_*.py scripts; asset_pipeline.py | 2 days |
| B | Multi-view always-on + Hunyuan tuning | asset_pipeline.py, generate_asset.py, generate_multi_views.py; investigate Docker worker | 1 day |
| C | Blender bake lighting + depth refactor | bake_pbr.py | 1 day |
| D | FLUX.2 stage 2b | texture_asset.py; new ComfyUI workflow file | 1.5 days |
| E | Multi-seed ensemble | new ensemble_generate.py; asset_pipeline.py | 1 day |
| F | Auto-retry harness | asset_pipeline.py wrapper | 0.5 day |

Total: ~7 working days. Each phase produces a measurable quality lift on the canary asset.

---

## 8. CANARY ASSET — `figure_grandfather_hands`

This asset is the documented failure case. Its prompt template requests `inference_steps: 60` and `target_poly_lod0: 10000`; current output is a 0.03-unit-thick depth card with only the bottom half of the UV textured. Each phase above is validated against re-runs of this asset.

Triple-A acceptance criteria:

- [ ] Bbox depth ≥ 0.3 × max(width, height)
- [ ] Manifold mesh, no inverted normals
- [ ] All 6 beauty renders show lit, visible hands
- [ ] Albedo: > 95% UV coverage, no large black regions
- [ ] PBR: weathered skin reads at macro DOF; tendon visibility, knuckle broadening, scar visible
- [ ] Cloth sleeve material distinguishable from skin (separate material slot honoured)
- [ ] Passes all 5 validation gates without retry
- [ ] Visual audit: indistinguishable from a documentary-photographed real hand at first-person camera distance

---

## 9. Implementation Checklist

### Phase A — Validation ✅ DONE 2026-05-22
- [x] `tools/validate_geometry.py` (Gate 2)
- [x] `tools/validate_pbr.py` (Gate 5)
- [x] `tools/validate_views.py` (Gates 3, 4)
- [x] `tools/diagnostic_report.py`
- [x] Wire all gates into `asset_pipeline.py`

### Phase B — Input quality ✅ DONE 2026-05-22
- [x] Multi-view default-ON
- [x] CLIP-score gate on synth views (Gate 1)
- [x] Investigate Hunyuan worker step cap; document findings
- [x] Octree 512 / guidance 8.0 defaults

### Phase C — Blender bake ✅ DONE 2026-05-22
- [x] HDRI + 3-point lighting in `render_views()`
- [x] Real depth EXR via Cycles compositor (normal EXR deferred — depth alone covers the projector input)
- [x] Single render call → beauty + depth multi-output

### Phase D — FLUX.2 stage 2b ✅ DONE 2026-05-22
- [x] `prompts/_pbr_workflows/flux2_klein_pbr.json` (no depth CN — depth conditioning encoded in lit beauty render)
- [x] `texture_asset.py:ai_project()` rewrite to FLUX.2 klein
- [x] Full prompt body (~512 token window vs SDXL's 77)
- [x] Per-view seed offset for variation

### Phase E — Ensemble ✅ DONE 2026-05-22
- [x] `run_stage1_ensemble()` in `asset_pipeline.py` (replaces standalone `ensemble_generate.py`)
- [x] Best-of-N selection via composite score (depth ×3 + face-budget proximity + 0.4·(1-centroid) + 0.10·manifold)

### Phase F — Retry harness ✅ DONE 2026-05-22
- [x] 3-attempt retry loop in `witness.py cmd_generate` with `RETRY_SEED_STRIDE=10_000`
- [x] Reads `recommended_action` from aggregate report; halts on `halt_and_fix_pipeline`

### Stages 4–5 — LOD + Collision ✅ DONE 2026-05-24
- [x] `tools/generate_lods.py` — gltf-transform weld → simplify → draco; LOD1 (50%) + LOD2 (15%)
- [x] `tools/generate_collision.py` — trimesh convex decomposition (CoACD if available); self-forks into GATE_PYTHON venv to access trimesh; uses pre-Draco `bake_input` to avoid Draco decode failure
- [x] Wire both stages into `asset_pipeline.py` (replace TBD placeholders); `--no-lods` + `--no-collision` escape hatches
- [x] LOD + collision files copied to `public/assets/` after generation
- [x] `--no-lods`, `--no-collision`, `--collision-max-hulls` flags in `witness.py`

### Metrics in asset-index ✅ DONE 2026-05-24
- [x] `register_asset.py` rewritten: 8-column row format; reads Faces from `<id>.geometry.json` and Gates from `<id>.aggregate.json`; accepts `--kind`, `--source`, `--diagnostics-dir`
- [x] `asset_pipeline.py` header updated to 8 columns; `PipelineContext.row()` emits `n/a` for non-mesh kinds; passes new flags to `register_asset.py` subprocess
- [x] `docs/asset-index.md` rebuilt with 8-column header; duplicate/malformed rows cleaned up

### Canary
- [x] Acceptance criteria documented in §8 above
- [ ] Re-run `figure_grandfather_hands` end-to-end (in flight 2026-05-22+)
- [ ] Capture before/after renders in `processed/renders/_audit/`
- [x] CHANGELOG_DETAILED.md entry for Phases C–F and Stages 4–5 + metrics

### Remaining deferred
- [ ] Adaptive Cycles samples per-category (deferred — `--bake-samples` flag covers the need manually)
- [ ] `blender_animate.py` skeleton embed for the `animated` asset kind (no animated assets in Phase 1 list)

---

**Document Status:** Updated 2026-05-24 (Stages 4–5 LOD/collision + metrics complete). Re-audit 2026-05-22 (post-conversation). Supersedes the morning audit.
