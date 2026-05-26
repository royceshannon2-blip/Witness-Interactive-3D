---
asset_name: structure_rugo_main_house
category: structure
era_scope: shared
reference_image: structure_rugo_main_house/ref.png
seed: 481102
inference_steps: 60
target_poly_lod0: 12000
materials_runtime:
  - mat_brick_mud         # past variant
  - mat_concrete_weathered # present variant
collision: convex_hull
---

# Rural Rwandan family house (rugo dwelling), Bisesero Hills

A single-room rectangular dwelling typical of the highland family compounds of
the Western Province of Rwanda. Sun-dried mud-brick walls (adobe), roughly
5.5 m wide × 4.5 m deep × 2.6 m tall, with a flat top edge to support a
separate corrugated-tin roof (modelled as a sibling asset, not part of this
mesh). Walls are slightly battered (thicker at the base, narrower at the top).
A single small rectangular window opening on the front face, off-centre toward
the right; one doorway opening on the front face, off-centre toward the left,
positioned for a separate wooden door asset to be slotted in. No window
shutters, no glass, no signage, no painted text — windows and doors are
modelled as openings only.

Surface texture: hand-applied mud plaster, slightly uneven across the wall
face, with subtle horizontal bands where successive plaster coats overlapped.
Faint salt-and-mineral efflorescence near the base of the walls. A few small
chips where dried mud has fallen away to reveal the rougher under-layer.

The mesh must be **silhouette-identical** between the Present (overgrown
ruin) and Past (intact) eras — the runtime swaps materials, not geometry.
Do not add collapse damage, ivy, or rubble piles to the mesh itself. Those
are layered at the runtime via era-specific material variants and separate
overgrowth assets.

Materials: a single PBR slot (`mat_brick_mud` style — earthy red-brown, high
roughness ≥ 0.9, no metallic). Subtle bump from the hand-applied plaster.
The runtime will clone this material to derive both era variants.

Geometry: a single mesh, no skeleton, no rigging, no animated parts. Wall
thickness should be a real two-sided geometry (≥ 25 cm thick) so the cellar
interior can be authored against the inside surface in a later pass.

Lighting at bake: neutral overcast, 5000 K, no strong directional shadows.
No people, no smoke, no roof, no door — those are separate assets.

## Style

Apply the [Digital Diorama style guide](_STYLE_GUIDE.md): tactile weathered
realism, filmic desaturated palette, hyper-realistic PBR (Albedo + Normal +
Roughness + AO). Read as documentary, not catalogue.

## Reference image

`prompts/asset-templates/structure_rugo_main_house/ref.png` should depict:

A single-room rural Rwandan family dwelling, photographed from a ¾ front
angle on an overcast morning. Sun-dried mud-brick walls with visible
hand-applied plaster (uneven horizontal bands, mineral efflorescence near
the base, soft chips where dried mud has fallen away). Flat top edge ready
for a separate tin roof to be slotted on. One small rectangular window
opening off-centre toward the right of the front face; one doorway opening
off-centre toward the left, no door installed. Wall corners slightly
battered (thicker at the base). Earthy red-brown / warm grey tone, filmic
desaturation. No roof, no door, no people, no other structures in frame.
Background: neutral overcast sky or seamless mid-grey.
