---
asset_name: structure_rugo_tin_roof
category: structure
era_scope: shared
reference_image: structure_rugo_tin_roof/ref.png
seed: 481103
inference_steps: 50
target_poly_lod0: 4000
materials_runtime:
  - mat_tin_roof
collision: convex_hull
---

# Corrugated-tin roof slab, Rwandan rural dwelling

A single-pitch corrugated steel roof sheet, sized to sit on top of
`structure_rugo_main_house` (6.2 m × 5.0 m, ~12 cm thick at the visible edge,
ridge offset slightly to the rear so rainwater runs down the front fall).
Standard-gauge corrugated profile (~75 mm wave pitch, ~18 mm wave amplitude).
Rolled edges on the long sides; a slight overhang of ~20 cm beyond the wall
line on all four edges.

Surface state: lightly weathered but readable as a single material. Faint
streaks of rust running down the corrugation troughs, no holes, no missing
sections, no patches. The runtime will derive Present-era variants
(deep rust, lichen patches) and Past-era variants (cleaner, mid-life paint
finish) by cloning the material.

Materials: a single PBR slot (`mat_tin_roof` style — desaturated rust-orange
base color, roughness ≈ 0.55, metallic ≈ 0.35, mild anisotropy along the
corrugation direction). OpenGL normal map convention.

Geometry: a single mesh, no animated parts. Capture the corrugation faithfully
— it reads as a silhouette element at distance.

Lighting at bake: neutral overcast, 5000 K, no strong directional shadows.
No mounting hardware, no nails, no rope tie-downs visible — those are
distinct authoring choices that don't generalise across compounds. No
ridge cap.

## Style

Apply the [Digital Diorama style guide](_STYLE_GUIDE.md). Favour matte
mineral-streaked oxidation over crisp factory-fresh galvanised sheen.

## Reference image

`prompts/asset-templates/structure_rugo_tin_roof/ref.png` should depict:

A single corrugated steel roof panel sized to sit atop a small dwelling
(approximately 6 m × 5 m). Photographed from above at a slight angle so the
~75 mm corrugation pitch and the rolled long edges are both legible. Surface
is mildly weathered — faint rust streaks running down inside the corrugation
troughs, light dust staining, no holes or missing sections, no patches.
~20 cm overhang on all four edges. Filmic desaturated tone — the rust reads
ochre, not orange. Background: neutral mid-grey or soft graduated overcast.
No mounting hardware visible, no fasteners, no surrounding house.
