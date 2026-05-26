---
asset_name: structure_family_shrine_slab
category: structure
era_scope: shared
reference_image: structure_family_shrine_slab/ref.png
seed: 481108
inference_steps: 50
target_poly_lod0: 3000
materials_runtime:
  - mat_concrete_weathered
collision: convex_hull
notes: |
  Carries the Act 4 `shrineAnchor` proximity trigger (see
  witness-interactive-vite/src/bootstrap/main.ts makePathChecker). The
  trigger raycast must hit the slab's visible top face cleanly. The ledger
  (`prop_ledger_book`) rests on top of this slab in Phase 1 first-frame
  composition (OPENING_SEQUENCE.md §6).
---

# Family household altar slab, rural Rwandan compound

A low rectangular stone-and-mortar altar, ~0.95 m wide × 0.55 m deep ×
~0.32 m tall. Hand-fitted small field stones with mortar, similar
construction to the well ring but shorter and with a flat slab top
(roughly cast in mortar, hand-troweled — the top is mostly flat but has
gentle high spots).

The slab is era-shared. In 1994 it carries an upright photo frame, a
candle stub, and the ledger book; in 2026 it is cracked along one
diagonal, the frame has fallen flat, and the ledger remains where it
was placed (per the narrative — the player's grandmother left it for
them to find). The mesh itself is the same in both eras; the dressing
on top is composed of separate prop assets.

Surface: the top is matte, slightly mottled by years of incense and
candle-wax. The mortar between stones on the sides is intact in 1994
and partly absent in 2026 (handled at runtime by material cloning).

Materials: one PBR slot (`mat_concrete_weathered` style — neutral
warm-grey, roughness ≈ 0.85, no metallic). Bump captures the small
field stones and the troweled top.

Geometry: a single mesh. Pivot/origin at the centre of the ground-line
under the slab (not under the top face). The top face should be flat
within ±2 cm so the ledger sits cleanly.

Lighting at bake: neutral overcast, 5000 K, no strong directional shadows.
No items on top of the slab — those are separate assets (ledger, frame,
candle).

## Style

Apply the [Digital Diorama style guide](_STYLE_GUIDE.md). The wax-and-incense
mottling on the top face and the lichen-shadow on the mortar are the
surface stories. Filmic warm-grey palette.

## Reference image

`prompts/asset-templates/structure_family_shrine_slab/ref.png` should
depict:

A low rectangular household altar / shrine of stone-and-mortar construction
typical of rural East African family compounds. ~0.95 m wide × ~0.55 m
deep × ~0.32 m tall. Hand-fitted small field stones (similar in spirit to
the well ring but flatter and shorter), mortar visible in the joints
(intact in this reference; the runtime derives the 2026 weathered variant).
Flat hand-troweled mortar top with subtle high spots and slight wax-and-
soot mottling from years of household candle use. **The top must be empty —
no candle, no frame, no ledger, no items in the reference image**.
Photographed from a ¾ angle showing the top face plus one long side.
Background: neutral mid-grey or seamless plaster wall. Desaturated palette.
