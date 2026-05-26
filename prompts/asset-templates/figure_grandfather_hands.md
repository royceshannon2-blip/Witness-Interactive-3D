---
asset_name: figure_grandfather_hands
category: figure
era_scope: past
reference_image: figure_grandfather_hands/ref.png
seed: 481116
inference_steps: 60
target_poly_lod0: 40000
materials_runtime:
  - mat_skin_weathered
  - mat_cloth_past_sleeve
collision: none
kind_hint: animated   # rigged hands; will require Blender pass before runtime
# Hero detail pass (stage 2b-detail): re-project the front-facing hands at a
# higher blend weight + lower denoise so knuckles, tendons, and the pale scar
# survive the six-view average instead of being smoothed out. detail_reference
# is optional — if supplied it MUST be framed to match the `front` view
# (a front-on close-up); otherwise the front beauty render is used.
detail_view: front
detail_weight: 3.0
detail_denoise: 0.42
# detail_reference: figure_grandfather_hands/ref_hands_closeup.png
notes: |
  HERO ASSET — first-person hands for the 1994 grandfather, shown during
  every Past-era echo (MISSION_BLUEPRINT.md §2 "Echoes"). The player sees
  these hands as Grandfather hides neighbors in the cellar, helps the
  boat depart, watches from the ravine, etc. The hands are the only
  body part visible during echoes.

  Same rigging contract as `figure_investigator_hands`. Use the same
  bone hierarchy so the runtime can swap the FP hand mesh between
  Present and Past eras without re-binding the IK rig.
---

# First-person grandfather hands — 1994, weathered

A pair of bare hands and forearms suitable for a first-person camera rig:
visible from mid-forearm to fingertips. The hands belong to a middle-aged
to older Rwandan man (the grandfather) — weathered from a life of
herding, farming, and household labor. Pose at rest: both hands held just
below the bottom of the camera frame, fingers slightly curled, thumbs
relaxed; this is the same neutral resting pose as
`figure_investigator_hands` so the runtime can transition between them
in a fade.

Skin: weathered, with a deeper warm mid-brown tone than the investigator
pair. Visible signs of long manual labor — slightly rougher skin texture,
broadened knuckles, a thin pale scar across the back of the right hand
(small, ~3 cm, faded). Nails are short and clean. No jewellery, no
wristwatch. Slight tendon visibility on the back of the hands. No
militaria, no weapons, no ritual marks.

Sleeves: long-sleeved cotton work shirt, faded khaki/olive, rolled up
to mid-forearm. The cloth is more worn than the investigator's sleeve —
slight fraying at the rolled edge, an unevenly stitched repair patch
visible on the inside of one forearm (subtle, ~4 cm × 2 cm).

Geometry: a single mesh containing both hands and forearm sleeves. LOD0
~40000 tris (hero first-person detail — matches `target_poly_lod0` in the
frontmatter, which the face-budget gate enforces).

Materials: two PBR slots.
- `mat_skin_weathered` for hand and forearm flesh (warm deep-brown
  albedo, roughness ≈ 0.65 — slightly rougher than the investigator's
  skin to read as weathered, no metallic, subtle subsurface).
- `mat_cloth_past_sleeve` for the long-sleeve fabric (faded khaki,
  roughness ≈ 0.9, no metallic, micro-weave bump).

Pivot: same as `figure_investigator_hands` so the runtime can swap
without re-binding.

Rigging spec (post-Hunyuan, Blender pass):
- Same bone hierarchy as `figure_investigator_hands` (identical names,
  identical T-pose).
- Idle and grasp clips authored on this rig.
- Additional clips needed for the four Act-2 echoes: place-mat,
  load-into-boat, write-by-starlight, set-photo-on-altar. Those are
  authored in a later pass; this template names them so the rig sheet
  is complete.

Lighting at bake: neutral overcast, 5000 K, no strong directional shadows.

## Style

Apply the [Digital Diorama style guide](_STYLE_GUIDE.md). Weathered skin
with deeper subsurface, broadened knuckles, fine tendon visibility on the
back of the hands. Cloth shows fraying and wear at the cuffs. Read as a
working man's hands in 1994 — the surface tells the story.

## Reference image

`prompts/asset-templates/figure_grandfather_hands/ref.png` should depict:

Both hands and forearms of a middle-aged to older Rwandan man (the
grandfather), shown **complete and fully within the frame** — nothing cropped
at the wrists or fingertips. The camera looks down onto the **tops of both
hands**: the view shows the **knuckled, veined upper surface of the hands** —
broadened knuckles, branching surface veins, and raised tendon ridges running
from wrist to fingers, with a thin pale ~3 cm scar across the upper surface of
the right hand. The **fingers curl gently downward and forward, their tips
dipping away from the camera**, so the rounded tops of the fingers and the
knuckles read with real depth and volume. **Every finger is distinct and held
slightly apart** — clear separation between the fingers, never flattened,
splayed, or fused together. The two hands sit side by side with a small gap
between them, the wrists entering from rolled work-shirt cuffs.

Skin: weathered, warm deep-brown, signs of long manual labor — slightly
rougher texture, broadened knuckles, a **thin pale scar across the back of
the right hand** (~3 cm, faded), short clean nails, slight tendon visibility,
**no jewellery, no wristwatch, no ritual marks, no weapons, no militaria**.
Sleeves: long-sleeved cotton work shirt in faded khaki or olive, rolled up to
mid-forearm, slight fraying at the rolled cuff, a small uneven stitched repair
patch (~4 cm × ~2 cm) visible on the inside of one forearm — subtle.

Filmic desaturated palette. The subject must be clearly separated from a
**plain, uncluttered background** with strong subject-to-background contrast
so the hand silhouette is unambiguous — **no table, no surface, no ground
plane, no held objects**. Photograph or photoreal 3D render, sharp focus
across the whole subject.
