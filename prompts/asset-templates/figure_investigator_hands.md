---
asset_name: figure_investigator_hands
category: figure
era_scope: present
reference_image: figure_investigator_hands/ref.png
seed: 481115
inference_steps: 60
target_poly_lod0: 10000
materials_runtime:
  - mat_skin_warm
  - mat_cloth_present_sleeve
collision: none
kind_hint: animated   # rigged hands; will require Blender pass before runtime
notes: |
  HERO ASSET — first-person hands for the 2026 investigator (the grandchild
  returning to the compound). Visible whenever the camera looks down or
  when the player picks up an object. Rigging is required before runtime
  use — this template specifies geometry + materials; the orchestrator's
  `--kind animated` branch will pair this mesh with a hand rig later.

  Until the rig pass lands, the runtime can instantiate the geometry-only
  GLB as a static FP-hands prop that follows the camera with no fingers
  articulating.
---

# First-person investigator hands — 2026, neutral

A pair of bare hands and forearms suitable for a first-person camera rig:
visible from mid-forearm to fingertips, with the wrists at the elbow-end
of the model. The hands belong to a young-adult investigator (the
grandchild) — neither weathered nor childlike. Pose: held at rest
slightly out of view (just below the bottom of the camera frame when
the camera is at standing eye-height looking forward).

Authored pose: both hands relaxed, fingers slightly curled, thumbs
loose. Palms facing each other but not touching. The forearm sleeves
are visible.

Skin: clean, no scars, no jewellery, no nail polish, no wristwatch. Skin
tone is warm mid-brown, but the model should not over-commit to a
specific identity — a deliberately neutral cast that the runtime can
adjust via material tint later.

Sleeves: long-sleeved cotton, mid-grey, rolled up to mid-forearm. No
buttons visible, no logo, no print. The sleeve cuffs are loose, with
a small fold over.

Geometry: a single mesh containing both hands and forearm sleeves. The
sleeves are part of the same mesh, not separate assets. LOD0 ~10000 tris
(hands need fine surface detail at close camera distance).

Materials: two PBR slots.
- `mat_skin_warm` for hand and forearm flesh (warm mid-brown albedo,
  roughness ≈ 0.55, no metallic, subtle subsurface if loader supports).
- `mat_cloth_present_sleeve` for the long-sleeve fabric (mid-grey,
  roughness ≈ 0.85, no metallic, slight micro-weave bump).

Pivot: the world origin should fall at the camera position, with the
hands' wrists at roughly (-0.18, -0.30, +0.35) and (+0.18, -0.30, +0.35)
relative to the camera. Use a standard FPS-hand authoring convention
(camera at origin, looking down -Z).

Rigging (post-Hunyuan, Blender pass):
- Standard 5-finger hand rig per hand (15 phalanges × 2).
- Wrist + forearm rotation bone per arm.
- Idle pose authored as the resting clip.
- Pickup pose authored as the grasp clip (for the ledger).
- Per ASSET_PIPELINE.md §2: skeletal rigging is deferred for v1; this
  template names the rig spec for the orchestrator's `--kind animated`
  branch when the Blender pipeline lands.

Lighting at bake: neutral overcast, 5000 K, no strong directional shadows.

## Style

Apply the [Digital Diorama style guide](_STYLE_GUIDE.md). Subtle subsurface
scatter on the skin, fine micro-folds at the knuckles, micro-weave bump on
the cotton. Read as documentary, not catalogue.

## Reference image

`prompts/asset-templates/figure_investigator_hands/ref.png` should depict:

A pair of bare hands and forearms framed as a first-person view — the
camera sits at adult standing eye-height (~1.65 m) looking down at the
hands resting in front of the chest, fingers just below the bottom of the
frame. Both hands relaxed, fingers slightly curled, thumbs loose, palms
facing each other but not touching. Visible from mid-forearm to fingertips.
Skin: young-adult, warm mid-brown, **clean — no scars, no jewellery, no
nail polish, no wristwatch, no rings**, short clean nails. Long-sleeved
cotton shirt, mid-grey, rolled up to mid-forearm with a small fold-over;
no buttons, no logo, no print visible. Filmic desaturated palette.
Background: neutral mid-grey or a soft out-of-focus wood floor / earth
ground (whatever reads as "looking down at the ground"). Photograph or
high-quality 3D render — either is acceptable as a reference; a render
gives more pose control.
