---
asset_name: vegetation_elephant_grass
category: vegetation
era_scope: shared
reference_image: vegetation_elephant_grass/ref.png
seed: 481111
inference_steps: 35
target_poly_lod0: 1500
materials_runtime:
  - mat_grass_tall
collision: none
notes: |
  Used as a `ThinInstance` source mesh — the runtime instances dozens of
  clumps across the compound. Pivot at the ground-line, no collision.
---

# Tall grass clump (elephant grass, Pennisetum purpureum), rural Rwandan compound

A single clump of tall tropical grass, ~0.5–0.8 m tall, the kind that grows
in dense stands across abandoned compounds in the Rwandan highlands. Blades
are long (30–60 cm), narrow (1–2 cm wide), arching outward from a tight
root base. The clump reads as a small fountain of green blades, with the
outer blades curling down under their own weight.

Geometry: a small set of intersecting alpha-cutout cards. Each card carries
a cluster of blade silhouettes painted in PBR-friendly diffuse + alpha.
The clump should look slightly different from any angle (use 3–4 intersecting
cards arranged at varying rotations).

Material: one PBR slot (`mat_grass_tall` style — alpha-cutout opacity,
albedo blue-green to olive-green range, roughness ≈ 0.95, no metallic,
two-sided rendering).

Era variance: shared. In 2026 the runtime tints the material darker and
denser (overgrown look); in 1994 it tints brighter and more cleared. The
mesh itself is the same.

Lighting at bake: neutral overcast, 5000 K. No flowering heads, no seed
stalks (those are a later asset if needed).

Pivot: centre of the clump's root base at ground-line.

## Style

Apply the [Digital Diorama style guide](_STYLE_GUIDE.md). Desaturated
olive-to-blue-green palette. The outer blades drooping under their own
weight read as the visual signature — keep that fountain silhouette.

## Reference image

`prompts/asset-templates/vegetation_elephant_grass/ref.png` should depict:

A single isolated clump of tall tropical grass (*Pennisetum purpureum* /
elephant grass) at ground level, ~0.5–0.8 m tall, photographed from a low
angle (camera ~30–60 cm above ground) against a neutral background or pale
sky. Long narrow arching blades (30–60 cm long, 1–2 cm wide) fanning
outward from a tight root base; outer blades curl down under their own
weight. The clump reads as a small fountain. Filmic desaturated olive /
blue-green palette. No flowering heads, no seed stalks, no other vegetation
in frame. Background: neutral mid-grey, pale overcast sky, or soft dirt
out of focus.
