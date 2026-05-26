# Diagnostic Report — `figure_grandfather_hands`

**ONE OR MORE GATES FAILED** — see per-gate details below.

| Gate | Status | Failures | Warnings |
| ---- | ------ | -------: | -------: |
| Gate 1 — Pre-Hunyuan Synth Views (Zero123++) | FAIL | 5 | 2 |
| Gate 2 — Post-Hunyuan Geometry | PASS | 0 | 1 |
| Gate 3 — Multi-View Beauty Renders | PASS | 0 | 0 |
| Gate 5 — PBR Texture Contract | skipped | 0 | 0 |

## Gate 1 — Pre-Hunyuan Synth Views (Zero123++)

**Failures**

- [view_1] CLIP semantic gate: P(asset)=0.01 < 0.4 — view reads more like "a smooth featureless placeholder block with no surface detail" than the asset prompt
- [view_3] CLIP semantic gate: P(asset)=0.28 < 0.4 — view reads more like "a blank untextured grey 3D primitive" than the asset prompt
- [view_4] object coverage 0.071 below floor 0.1 — view shows a sliver of the mesh, likely an edge-on view of a flat depth-card
- [view_4] CLIP semantic gate: P(asset)=0.01 < 0.4 — view reads more like "a corrupted distorted 3D render with no recognizable subject" than the asset prompt
- [view_5] CLIP semantic gate: P(asset)=0.02 < 0.4 — view reads more like "a corrupted distorted 3D render with no recognizable subject" than the asset prompt

**Warnings**

- [view_1] foreground colour diverges (L1 0.39 from the other views' consensus) — view may show a different subject/background; check multi-view coherence
- [view_3] foreground colour diverges (L1 0.91 from the other views' consensus) — view may show a different subject/background; check multi-view coherence

**Key metrics**

```json
{
  "luminance_mean_across_views": 0.572763572136561,
  "luminance_std_across_views": 0.0627128927315368,
  "luminance_std_threshold": 0.15,
  "fg_colour_median": [
    0.537675142288208,
    0.5205777883529663,
    0.5049580335617065
  ],
  "fg_colour_divergence_max": 0.9088334441184998,
  "fg_colour_divergence_threshold": 0.22,
  "clip_prompt": "A pair of bare hands and forearms suitable for a first-person camera rig: visible from mid-forearm to fingertips.",
  "clip_real_prob_floor": 0.4
}
```

## Gate 2 — Post-Hunyuan Geometry

**Warnings**

- mesh is non-watertight (open edges present) — acceptable for open-form assets

**Key metrics**

```json
{
  "bbox_extents": [
    0.892219066619873,
    1.9949678182601929,
    0.9931735694408417
  ],
  "bbox_depth_ratio": 0.44723481674906185,
  "bbox_depth_threshold": 0.1,
  "vertex_count": 322612,
  "face_count": 645234,
  "face_target": 40000,
  "raw_poly_cap": 2000000,
  "face_budget_low": 20000,
  "centroid": [
    0.13512717722545392,
    -0.01979512872157152,
    -0.15654327804954857
  ],
  "centroid_offset_ratios": [
    0.06773401354579145,
    0.009922530348802723,
    0.07846907434630682
  ],
  "centroid_offset_threshold": 0.3,
  "manifold": false
}
```

## Gate 3 — Multi-View Beauty Renders

**Key metrics**

```json
{
  "luminance_mean_across_views": 0.47349350651105243,
  "luminance_std_across_views": 0.05229621479464087,
  "luminance_std_threshold": 0.15,
  "fg_colour_note": "cross-view colour check skipped: 3 foreground view(s) < 5 needed for a stable consensus"
}
```

## Remediation

Mapped from [`ASSET_GENERATION_OVERVIEW.md §4`](../../docs/design-docs/ASSET_GENERATION_OVERVIEW.md):
- **D1 / D5 (pre-Hunyuan)** — Zero123++ produced bad synth views. Re-roll `--multi-view-seed`, raise `--multi-view-steps` (75 → 100), or fix the ref.png (stage 0.25 might be over-denoising — try `--refine-ref-strength 0.40`). Do NOT proceed to Hunyuan with these views: it will collapse to a depth-card.
- **D1 / D5** — Hunyuan produced a flat depth-card. Re-run with `--multi-view` (now default) and N≥3 seed ensemble; if it persists across seeds, raise `octree_resolution` and increase `inference_steps`.

