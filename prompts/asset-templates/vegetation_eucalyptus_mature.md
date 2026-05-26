---
asset_name: vegetation_eucalyptus_mature
category: vegetation
era_scope: shared
reference_image: vegetation_eucalyptus_mature/ref.png
seed: 481109
inference_steps: 40
target_poly_lod0: 6000
materials_runtime:
  - mat_eucalyptus_bark
  - mat_eucalyptus_leaf
collision: cylinder_trunk_only
notes: |
  Used as a `ThinInstance` source mesh — the runtime instances 6+ copies
  for the eucalyptus grove on the player's LEFT at the compound spawn.
  Pivot must be at the ground-line for consistent thin-instance placement.
---

# Mature eucalyptus tree (Eucalyptus globulus / camaldulensis), Bisesero Hills

A single mature eucalyptus tree, ~8–10 m tall, characteristic of the
plantation-planted groves found across the Rwandan highlands. Tall straight
trunk with the species' distinctive shedding bark — long curling strips of
buff-and-grey bark peeling away from a smooth pale under-bark in patches.
Trunk diameter at breast height ~25–35 cm. Slight lean (≤ 5°) for natural
silhouette variation.

Branching: the lower 3–4 m of trunk is mostly bare (typical for plantation
eucalyptus — lower branches drop as the tree matures). Above that, the
crown opens into a sparse canopy of long narrow leaves on drooping branches.

Foliage: long lanceolate leaves, ~10–20 cm each, blue-green to grey-green,
hanging from the branches rather than held up. Crown should read as **open
and irregular**, not a solid sphere — eucalyptus crowns let a lot of light
through.

Geometry: a single mesh combining trunk + branches + foliage cards. The
foliage uses alpha-cutout cards (planar polygons with leaf cluster textures
on each). Total target poly count must fit a thin-instanced grove: keep
LOD0 at ~6000 tris max.

Materials: two PBR slots. `mat_eucalyptus_bark` for the trunk + branches
(roughness ≈ 0.9, no metallic, the bark colour shifts from grey to buff in
patches). `mat_eucalyptus_leaf` for the foliage cards (alpha-cutout opacity,
albedo blue-green ~ #5a7060, two-sided rendering, no metallic).

Lighting at bake: neutral overcast, 5000 K, no strong directional shadows.
No people, no birds, no rope ties, no carved marks on the trunk.

Pivot: the centre of the trunk base at ground-line, so thin-instance
placements drop cleanly onto the terrain.

## Style

Apply the [Digital Diorama style guide](_STYLE_GUIDE.md). The shedding-bark
patches and the buff-against-grey contrast are the visual signature of the
species; don't smooth them away. Foliage cards must read as alpha-cut
clusters at close camera distance.

## Reference image

`prompts/asset-templates/vegetation_eucalyptus_mature/ref.png` should depict:

A single mature eucalyptus tree (*Eucalyptus globulus* or *E. camaldulensis*),
~8–10 m tall, photographed standing alone against an open background. The
full tree visible from base to crown tip. Trunk: tall, straight, with the
species' characteristic shedding bark — long curling strips of buff-and-grey
bark peeling away in patches to expose smooth pale under-bark. Trunk
diameter at breast height ~25–35 cm, slight ≤ 5° lean. Lower 3–4 m of trunk
is mostly bare (typical plantation eucalyptus). Crown: sparse and irregular,
long lanceolate blue-green-to-grey-green leaves hanging downward on drooping
branches — lets a lot of light through. Filmic desaturated foliage tones,
sky pale neutral. No other trees, no people, no compound structures in frame.
