---
asset_name: structure_rugo_door
category: structure
era_scope: past
reference_image: structure_rugo_door/ref.png
seed: 481104
inference_steps: 50
target_poly_lod0: 3000
materials_runtime:
  - mat_wood_weathered
collision: convex_hull
---

# Wooden plank door, rural Rwandan dwelling

A vertical-plank wooden door, single leaf, hung from a simple wooden frame.
Dimensions ~0.95 m wide × 1.95 m tall × 8 cm thick. Three or four vertical
planks fastened together with two horizontal ledger boards on the inside
face (visible only when the door is open). Surface is hand-planed but
unfinished — no varnish, no paint. Subtle natural patina from sun and rain.

The door should be modelled in a slightly-open position (about 0.55 rad /
30° open from closed), so that when instantiated at the doorway of the
`structure_rugo_main_house` it reads as a welcoming household — per the
1994 echo's documentary tone, this is a lived-in home before the night
of the events.

A simple iron handle or a worn wooden knob on the outside face, no lock,
no keyhole. No carved decoration, no painted text, no symbols.

Materials: a single PBR slot (`mat_wood_weathered` style — mid-brown,
roughness ≈ 0.85, no metallic on the wood; the metal handle uses a
small secondary slot or shares the same material if Hunyuan emits a
single texture set).

Geometry: a single mesh, no skeleton. The door's hinge axis is the left
vertical edge; the asset's pivot/origin should sit at the bottom-left
corner so the runtime can rotate it open from a closed pose if needed.

Lighting at bake: neutral overcast, 5000 K, no strong directional shadows.
No people, no carry handles, no extra hardware.

## Style

Apply the [Digital Diorama style guide](_STYLE_GUIDE.md). Favour axe-mark
texture, knot eyes, and grey-silvered weathering on the wood; the iron
handle should read as wrought (slightly pitted) rather than cast.

## Reference image

`prompts/asset-templates/structure_rugo_door/ref.png` should depict:

A vertical-plank wooden door, single leaf, isolated against a neutral
background. Three or four hand-planed planks butted side-by-side, two
horizontal ledger boards on the inside face partially visible (door is
shown in a roughly 30°-open pose so both faces read). A simple wrought-iron
handle or worn wooden knob on the outside face. Hand-hewn, unfinished
mid-brown wood with natural sun-and-rain patina, no varnish, no paint, no
carved decoration, no painted text. Dimensions read as ~0.95 m × ~1.95 m.
Filmic desaturated palette. Background: seamless mid-grey or pale plaster
wall.
