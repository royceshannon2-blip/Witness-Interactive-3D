# Asset Style Guide — Digital Diorama

**Applies to every asset in `prompts/asset-templates/`.**

See [`memory/visual_style_digital_diorama.md`](../../../.claude/projects/-home-royce3-Desktop-Witness-Interactive-3D/memory/visual_style_digital_diorama.md) for the source rule.

## Core look — "Digital Diorama"

- **Tactile, weathered, lived-in.** Surfaces show their age: mortar that has lost its
  surface, wood that has weathered grey, plaster that has chipped at the corners,
  cloth that has worn at the cuffs. Avoid the smooth, idealised look of AAA
  console assets; lean toward the gritty intimacy of a documentary still.
- **Hyper-realistic PBR.** Each asset must ship with Albedo, Normal, Roughness,
  and Ambient Occlusion maps. Grit reads through micro-bump and roughness
  variation more than through colour.
- **Filmic / desaturated palette.** Muted historical tones, no vivid saturation.
  Reds tend ochre, greens tend olive/blue-green, browns tend warm-grey, whites
  tend cream-buff. Imagine a colour-graded documentary print from 1994.
- **Macro cinematography in mind.** The runtime renders these assets under tight
  FOV + shallow depth-of-field (`DefaultRenderingPipeline.depthOfFieldEnabled`),
  so surface detail at close range matters more than silhouette legibility at
  distance.

## Reference-image rules

Every asset has a per-id folder at `prompts/asset-templates/<id>/`. Drop a single
`ref.png` (or `.jpg`) into it. The reference image is what Hunyuan3D 2.1 sees;
its quality bounds the output's quality.

**Image specs (apply to all assets):**
- Resolution: ≥ 1024 × 1024 (Hunyuan accepts ≥ 512² but quality scales with input).
- Background: neutral (white, mid-grey, soft graduated grey, or seamless outdoor
  light). No competing subjects, no posters, no other people in frame unless the
  asset is a `figure_*` (hands).
- Lighting: **overcast / soft diffuse**, ~5000 K, no harsh directional shadows.
  Diffuse north-light through a window is ideal for indoor shoots; a heavy overcast
  sky is ideal for outdoor shoots. Avoid golden-hour, blue-hour, or stylised
  studio lighting — those bias Hunyuan's PBR bake.
- Style coherence: the photograph itself should already read as part of the
  Digital Diorama palette. If the source is colour-saturated, desaturate it
  to ~50–60% of original saturation before saving as `ref.png`. If shadows
  are crushed, lift them slightly.
- Crop: subject centred, 10–15% headroom around the longest dimension.
- No watermarks, no UI overlays, no captions.

**Per-asset specifics** are in the `## Reference image` section at the end of
each `<id>.md` template, plus the `README.md` of each per-id folder.

## Stage 0.25 — automatic ref refinement

Every `--kind mesh|animated` run pushes the asset's `ref.png` through
**FLUX.2 [klein] 9B Base** img2img before stage 0.5 (Zero123++) and stage 1
(Hunyuan3D) see it. This is *always-on*; pass `--no-refine-ref` to opt out
when iterating on a ref that is already on-style.

**Archive scheme.** On the first refine pass, the pipeline copies the
incoming `ref.png` to `ref.original.png` (the audit / rollback copy) and
then overwrites `ref.png` with the refined output. Re-runs read from
`ref.original.png` so denoise does not compound. If you need to swap in a
new source, delete both files first; the next run will treat it as a clean
slate.

**Canonical refine prompt suffix** (single source of truth — kept in sync
with `REFINE_PROMPT_SUFFIX` in [`tools/refine_ref_image.py`](../../tools/refine_ref_image.py)):

> Restyle this photograph to match the Digital Diorama look: filmic
> desaturated palette, tactile weathered realism, hyper-realistic PBR
> materials with micro-bump and roughness variation, 1994 Rwanda
> documentary photography aesthetic. Preserve the subject's geometry,
> pose, and composition exactly. Overcast 5000 K diffuse daylight,
> neutral mid-grey background, no harsh shadows, no people other than any
> already present, no watermarks, no captions.

If you edit the suffix here, edit `REFINE_PROMPT_SUFFIX` to match — the
two need to stay byte-identical so authors and the orchestrator describe
the same target style.

**Per-category denoise defaults** (from `REFINE_STRENGTH_BY_CATEGORY` in
`tools/asset_pipeline.py`):

| Category prefix | Denoise | Why |
|---|---|---|
| `vegetation_` | 0.60 | Push palette hard; foliage colour in stock photos varies wildly and silhouette tolerance is high. |
| `structure_`  | 0.40 | Protect doorways, roof pitches, window placement. A small palette nudge suffices. |
| `prop_`       | 0.50 | Hero objects: materials + geometry both matter. |
| `figure_`     | 0.50 | Hands / people: higher denoise warps anatomy. |
| (other)       | 0.50 | Default — propose a new row before adding a new category. |

Override per-run with `--refine-ref-strength <0..1>`. For permanent
changes to a category, edit the table in `tools/asset_pipeline.py` and
note the reasoning in `docs/decisions/CHANGELOG_DETAILED.md`.

## What "tactile" looks like per material family

| Material family | Visual cues to favour | Avoid |
|---|---|---|
| Mud brick / plaster | Hand-applied troweling, mineral efflorescence, edge chips, soft mid-tones | Painted finishes, decorative texture |
| Corrugated tin | Rust streaks in troughs, mild dents, mineral water-staining, matte | Clean factory-fresh galvanised sheen |
| Hand-hewn wood | Axe marks, knot eyes, end-grain crack, grey-silvered weathering | Sanded uniform planks, varnish |
| Stone + mortar | Lichen patches, mortar wash, drip-stain runs, irregular field stones | Cut/dressed regular blocks |
| Cotton cloth | Frayed edges, micro-weave bump, dust-staining at cuffs | Crisp ironed surfaces, prints |
| Leather (ledger) | Pocket-rub patina, edge-cracking at corners, soft sheen on high-touch areas | Polished show-leather |
| Wax (candle) | Drip trails fused to base, soot-darkened wick crater | Pristine taper geometry |
| Skin (hands) | Subtle subsurface scatter, broadened knuckles, fine micro-folds | Render-clean smooth doll skin |

## Crosslinks

- [`docs/design-docs/ASSET_PIPELINE.md §3.1`](../../docs/design-docs/ASSET_PIPELINE.md) — prompt template schema.
- [`docs/design-docs/OPENING_SEQUENCE.md §7`](../../docs/design-docs/OPENING_SEQUENCE.md) — runtime cinematography (DOF, FOV).
- [`docs/design-docs/RENDERING.md`](../../docs/design-docs/RENDERING.md) — material library + post-processing pipeline.
- [`docs/design-docs/PHASE1_ASSET_LIST.md`](../../docs/design-docs/PHASE1_ASSET_LIST.md) — Phase 1 catalogue + status.
