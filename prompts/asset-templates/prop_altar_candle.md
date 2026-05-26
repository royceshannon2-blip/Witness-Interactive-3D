---
asset_name: prop_altar_candle
category: prop
era_scope: past
reference_image: prop_altar_candle/ref.png
seed: 481114
inference_steps: 50
target_poly_lod0: 2500
materials_runtime:
  - mat_wax_white
collision: convex_hull
---

# Candle stub on household altar

A short cylindrical wax candle, ~5 cm diameter × ~12 cm tall — a stub that
has been burning intermittently over years of household use. The visible
surface tells its story: hardened wax drip-trails running down one side
from the rim, a slightly off-centre wick crater on the top face, a wick
of dark twisted cotton emerging ~2 cm from the crater (unlit in the
authored asset; the runtime will add an emissive flame in a later VFX
pass).

The wax body is matte white with a faint warm undertone. Hardened drips
form a small irregular pool around the base of the candle (a thin
~5 mm collar of fused wax on the surface the candle stands on — modelled
as part of this asset so the placement reads as long-used).

The candle is a Past-era only asset. The runtime does not place it in
2026 (only the wax-stained slab remains there).

Material: one PBR slot (`mat_wax_white` style — slightly warm white,
roughness ≈ 0.45, no metallic, a hint of subsurface scattering if the
loader supports it).

Geometry: a single mesh. LOD0 ~2500 tris. The wick is geometry, not a card.

Pivot: the centre of the bottom face (the wax-pool collar).

Lighting at bake: neutral overcast, 5000 K, no strong directional shadows.
No flame — runtime handles emissive in a later pass.

## Style

Apply the [Digital Diorama style guide](_STYLE_GUIDE.md). Drip-trail
geometry, fused wax-pool collar, and soot-darkened wick crater are the
surface stories. Filmic warm-white palette — the wax reads cream, not
bright white.

## Reference image

`prompts/asset-templates/prop_altar_candle/ref.png` should depict:

A short cylindrical white wax candle stub, ~5 cm diameter × ~12 cm tall,
standing alone on a neutral matte surface. Photographed at a slight angle
(15–30°) so the cylinder profile, the top crater, and one face of the drip
trails all read. Hardened wax drip-trails running down one side from the
rim (irregular, frozen mid-run). Off-centre wick crater on the top face,
~1 cm wide, slightly darkened. A wick of dark twisted cotton emerges from
the crater, ~2 cm long, **unlit** (no flame, no glow). Around the base, a
small hardened wax-pool collar (~5 mm thick) fused to the surface the
candle stands on. Slight warm undertone in the wax. Filmic desaturated
palette. Background: neutral mid-grey or pale wood surface.
