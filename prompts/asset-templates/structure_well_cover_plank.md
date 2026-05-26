---
asset_name: structure_well_cover_plank
category: structure
era_scope: shared
reference_image: structure_well_cover_plank/ref.png
seed: 481107
inference_steps: 50
target_poly_lod0: 2500
materials_runtime:
  - mat_wood_weathered
collision: convex_hull
notes: |
  Runtime owner: this mesh carries the `cellar_door_latch` Memory Fragment
  trigger (see witness-interactive-vite/src/bootstrap/main.ts). The
  interactable raycast must hit the plank's visible top face cleanly.
---

# Wooden plank cover for stone well, rural Rwandan family compound

A square wooden cover for the top of `structure_well_stone_ring`. ~1.3 m
× 1.3 m × 8 cm thick, made from three or four planks joined together
side-by-side with two horizontal ledger boards on the underside (not
visible from above, but the cross-section reads at the edges). Hand-hewn,
unfinished wood — same family as the gate and door, but a different
piece (slightly different grain).

A simple iron ring or iron handle countersunk into the top face, just
off-centre — this is the "latch" the investigator lifts to reveal the
cellar entrance below. The ring lies flat against the plank, so the cover
reads as flush from a distance.

The cover sits **on top of** the well ring, not flush with it — there is
~1 cm of overhang on each side. A few of the planks may show a hairline
gap (1–2 mm) where seasonal expansion has pulled them apart slightly.

The cover is era-shared. In 2026 it sits at a slightly skewed angle (per
the runtime placement, rotated ~10° around Y) and the iron ring has more
surface rust; the mesh is the same.

Materials: one PBR slot (`mat_wood_weathered` style) plus a small metallic
patch on the iron ring (`metallic ≈ 0.85`, `roughness ≈ 0.6`). If Hunyuan
emits a single material, that's acceptable; the runtime can split for
optical fidelity in a later pass.

Geometry: a single mesh. Pivot/origin at the centre of the top face.

Lighting at bake: neutral overcast, 5000 K, no strong directional shadows.

## Style

Apply the [Digital Diorama style guide](_STYLE_GUIDE.md). Hand-hewn planks
with grey-silvered weathering; the iron ring is wrought, lightly pitted, not
factory-cast. The plank gaps (1–2 mm) are part of the surface story.

## Reference image

`prompts/asset-templates/structure_well_cover_plank/ref.png` should depict:

A square wooden plank cover for a well opening, ~1.3 m × 1.3 m × ~8 cm,
photographed from a slight overhead angle so the top face plus one edge are
both visible (cross-ledger boards just legible in the edge cross-section).
Three or four hand-hewn planks butted side-by-side, hairline gaps (1–2 mm)
between adjacent planks. A simple wrought-iron ring or iron handle
countersunk into the top face, slightly off-centre, lying flat against the
plank. Light surface rust on the iron, mid-brown weathered wood. No
fasteners visible from the top face. Background: neutral mid-grey or
seamless. Filmic desaturated palette.
