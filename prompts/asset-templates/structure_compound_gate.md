---
asset_name: structure_compound_gate
category: structure
era_scope: shared
reference_image: structure_compound_gate/ref.png
seed: 481105
inference_steps: 50
target_poly_lod0: 3500
materials_runtime:
  - mat_wood_weathered
collision: convex_hull
---

# Wooden compound gate, rural Rwandan family compound entrance

A simple two-post-and-beam gate: two square-section wooden posts (each ~25 cm
× 25 cm × 1.6 m tall, sunk into the ground), spanned by a horizontal beam
(~3 m × 18 cm × 18 cm) at ~1.7 m height. No swinging gate-leaf attached —
the gate is the framework only; the opening between the posts is the way
in. Posts are hand-hewn (not perfectly square — gentle taper, axe-mark
texture on the visible faces).

A single horizontal cross-rail at mid-height between the two posts, ~6 cm
thick, lashed to each post with simple natural-fibre rope (modeled as a
small braided coil at each lashing point). The cross-rail can have a
slight sag.

The composition reads as a threshold — the player walks through it at the
moment they arrive at the compound. The gate is shared between eras: in
1994 it is intact and recently maintained; in 2026 it is the same wood,
weathered grey, slightly leaning, but standing. The runtime derives
both eras by cloning the material.

Materials: one PBR slot (`mat_wood_weathered` style — desaturated brown,
roughness ≈ 0.9, no metallic). Subtle bump from the axe-mark texture on
the post faces.

Geometry: a single mesh, no animated parts. Total bounding box about
3.2 m wide × 1.8 m tall × 0.3 m deep. The pivot/origin should be the
midpoint of the ground-line between the two posts (so the runtime can
position it on the spawn axis).

Lighting at bake: neutral overcast, 5000 K, no strong directional shadows.
No signage, no painted text, no carved symbols.

## Style

Apply the [Digital Diorama style guide](_STYLE_GUIDE.md). The wood should
read as a weathered grey-brown — axe-mark texture on the posts is the
primary surface story.

## Reference image

`prompts/asset-templates/structure_compound_gate/ref.png` should depict:

A simple two-post-and-beam wooden entrance gate at a rural East African
compound, photographed straight-on or from a slight angle showing the
gate frame in three dimensions. Two square-section hand-hewn posts
(~25 cm × 25 cm × ~1.6 m above ground), spanned by a horizontal beam at
~1.7 m height (~3 m × ~18 cm × ~18 cm). A single mid-height cross-rail
between the posts (~6 cm thick) lashed to each post with simple natural-fibre
rope (small braided coil at each lashing point). Posts gently taper; axe-mark
faces visible on the visible surfaces of each post. No swinging gate-leaf,
no surrounding fence, no signage. Filmic desaturated wood tones. Background:
overcast sky behind the gate frame, or seamless neutral mid-grey.
