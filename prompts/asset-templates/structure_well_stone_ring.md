---
asset_name: structure_well_stone_ring
category: structure
era_scope: shared
reference_image: structure_well_stone_ring/ref.png
seed: 481106
inference_steps: 50
target_poly_lod0: 4500
materials_runtime:
  - mat_concrete_weathered
collision: convex_hull
---

# Stone-and-mortar well ring, rural Rwandan family compound

The visible above-ground portion of a hand-dug well: a roughly circular
cylinder of fitted stone with mortar fill, ~1.2 m outside diameter, ~0.7 m
tall, ~15 cm wall thickness. The stones are local field stones — irregular,
mostly fist-to-head-sized, fitted by hand, with mortar visible in the
joints. The top edge is flat enough to seat a plank cover (sibling asset
`structure_well_cover_plank`).

A single shallow notch on the inside of the ring near one edge, ~10 cm
wide × ~5 cm deep, where a hand-twisted rope has worn a groove from years
of bucket-draws. The notch is the only asymmetry; otherwise the ring is
radially regular.

The ring is shared between eras: 1994 it is clean, lichen-free, the mortar
is intact; 2026 the mortar has lost most of its surface, lichen has
colonised the upper north face, and the worn rope groove has deepened.
The runtime derives both eras by cloning the material; the geometry is
the same.

Important: the inside of the ring opens downward to a vertical shaft. The
shaft itself is not part of this mesh — the runtime can author the
darkness below as a black opening or as a separate cellar-entry asset.
The bottom of this mesh (where the ring meets ground) is flat.

Materials: one PBR slot (`mat_concrete_weathered` style — neutral grey,
roughness ≈ 0.9, no metallic). Bump captures the individual stones'
relief and the worn mortar.

Geometry: a single mesh, no animated parts. Pivot/origin at the centre of
the circle, at ground level. No animated water, no bucket, no rope coil
visible on top — those are separate assets.

Lighting at bake: neutral overcast, 5000 K, no strong directional shadows.

## Style

Apply the [Digital Diorama style guide](_STYLE_GUIDE.md). Lichen patches,
mortar wash, and the worn rope-groove on the inside lip are the surface
stories that sell the asset. Filmic mid-grey palette.

## Reference image

`prompts/asset-templates/structure_well_stone_ring/ref.png` should depict:

The above-ground portion of a hand-dug rural well, photographed from a ¾
angle so both the inside curvature and the outside masonry read. Roughly
circular ring of irregular field stones (fist-to-head-sized) fitted by
hand with visible mortar in the joints. ~1.2 m outer diameter, ~0.7 m tall,
~15 cm wall thickness. The top edge is flat enough to seat a plank cover.
A single shallow worn notch on the inside lip near one edge (~10 cm wide,
~5 cm deep) where rope-draws have eroded the stone. Pale lichen patches on
the upper north face. Mortar shows surface wash and minor loss. No bucket,
no rope coil, no plank cover. Background: open ground or neutral mid-grey.
Desaturated grey-stone palette.
