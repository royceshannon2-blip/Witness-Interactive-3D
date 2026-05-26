---
asset_name: vegetation_eucalyptus_sapling
category: vegetation
era_scope: past
reference_image: vegetation_eucalyptus_sapling/ref.png
seed: 481110
inference_steps: 40
target_poly_lod0: 3500
materials_runtime:
  - mat_eucalyptus_bark
  - mat_eucalyptus_leaf
collision: cylinder_trunk_only
notes: |
  Used as a `ThinInstance` source mesh for the 1994 (Past-era) eucalyptus
  grove — the grove was younger then; trees show as saplings.
---

# Young eucalyptus tree (sapling), Bisesero Hills

A young eucalyptus tree, ~4–5 m tall, the same species family as
`vegetation_eucalyptus_mature` but at an earlier life stage — the
plantation grove the family planted decades before 1994 reads as
mid-life in the Past era and as a mature stand in the Present era.

Trunk: straight, ~10–15 cm diameter at breast height. Bark is smoother
and lighter than the mature version, with less peeling — the
characteristic shedding has just started. Foliage starts lower on the
trunk (~1 m up) than on the mature version, with a denser, more
juvenile crown.

Foliage: long lanceolate leaves but a higher density of them per branch;
the crown reads as a softer, more compact silhouette than the mature
tree, while still letting light through.

Geometry: a single mesh combining trunk + branches + foliage cards.
LOD0 target ~3500 tris (smaller crown = lower poly).

Materials: same two PBR slots as `vegetation_eucalyptus_mature` —
`mat_eucalyptus_bark` (slightly lighter base color, less peeled patch
contrast) and `mat_eucalyptus_leaf` (slightly brighter green, alpha-cutout
foliage cards).

Lighting at bake: neutral overcast, 5000 K.

Pivot: the centre of the trunk base at ground-line.

## Style

Apply the [Digital Diorama style guide](_STYLE_GUIDE.md). Smoother bark
than the mature reference, but already the first signs of peeling. Crown
denser and softer in silhouette.

## Reference image

`prompts/asset-templates/vegetation_eucalyptus_sapling/ref.png` should
depict:

A young eucalyptus tree (same species family as
`vegetation_eucalyptus_mature/ref.png`), ~4–5 m tall, photographed standing
alone against an open neutral background. Full tree visible base to crown.
Trunk: straight, ~10–15 cm diameter at breast height, bark is smoother and
lighter than the mature reference — the characteristic shedding has just
started, only small bark patches showing. Foliage starts lower on the trunk
(~1 m up) than on the mature tree. Crown: denser, more compact, softer
silhouette than the mature crown, but still letting light through. Same
filmic desaturated palette, slightly brighter green than the mature
reference. No people, no other trees in frame.
