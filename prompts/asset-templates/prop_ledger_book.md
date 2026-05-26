---
asset_name: prop_ledger_book
category: prop
era_scope: shared
reference_image: prop_ledger_book/ref.png
seed: 481112
inference_steps: 60
target_poly_lod0: 8000
materials_runtime:
  - mat_leather_ledger
  - mat_paper_aged
collision: convex_hull
notes: |
  HERO PROP — the title artefact of "The Shepherd's Ledger". The player's
  first interactable; sits on top of `structure_family_shrine_slab` at
  spawn (OPENING_SEQUENCE.md §6). Must read cleanly at close inspection
  (the player will pick it up and examine pages in the ledger UI).
---

# The shepherd's ledger — a leather-bound hand-written notebook

A worn leather-bound notebook, the size and weight of an A5 (~21 cm × 15 cm
× ~3 cm thick when closed). The cover is dark brown leather, hand-stitched
along the spine with coarse natural thread, no embossing, no title, no
ornamentation — a plain working book that has clearly been carried in a
pocket for years.

Closed pose: the book lies flat on its back cover, slightly skewed (~5°
rotation around its vertical axis), so the front cover faces upward but
is angled toward where the camera will rest at spawn. The leather shows
the patina of long handling: a soft sheen near the corners where fingers
have worn the surface, slight darkening along the spine where the binding
flexes when opened, no cracks or tears.

The page block visible at the open (right) edge: cream-to-buff pages,
slightly fanned (~1–2 mm spread), with thin red-and-blue ledger-style
ruling running across each page (visible at the edge as faint bands
of colour). A length of dark fabric ribbon (~3 mm wide, slightly frayed)
trails from between two pages near the middle, hanging off the right
edge by about 8 cm — a bookmark left in place.

The cover has no buckle, no clasp. No human-written text is visible from
the outside.

Materials: two PBR slots.
- `mat_leather_ledger`: dark brown leather, roughness ≈ 0.75, subtle
  normal map for grain, very slight specular highlight.
- `mat_paper_aged`: warm off-white pages, roughness ≈ 0.95, no metallic,
  faint subsurface scattering for the page block edge if Hunyuan supports.

Geometry: a single mesh. The book closed is one solid object; the runtime
treats the page-flipping interactions as a UI overlay, not as 3D mesh
animation. LOD0 ~8000 tris — this is a hero prop the player inspects up
close.

Pivot: the centre of the bottom face of the closed book (so it sits flat
on the altar slab when placed at y = slab_top).

Lighting at bake: neutral overcast, 5000 K, no strong directional shadows.
The page edge should be visible — a faint warm light on the right side
during bake is acceptable to help read the page block, but no painted-on
shadows.

## Style

Apply the [Digital Diorama style guide](_STYLE_GUIDE.md). This is the hero
prop the player picks up at first frame — the worn corners, soft pocket-rub
patina on the leather, and the slight fan of the page block must read at
close camera distance. Filmic warm-mid-tone palette.

## Reference image

`prompts/asset-templates/prop_ledger_book/ref.png` should depict:

A worn leather-bound A5-sized notebook (~21 cm × ~15 cm × ~3 cm thick), CLOSED,
lying flat on a neutral matte surface. Photographed from straight-on top OR
from a ¾ angle (a ¾ angle reads better — both the front cover and the page
edge are then visible). Cover: dark brown leather, hand-stitched along the
spine with coarse natural thread, **no embossing, no title, no writing
visible anywhere**. Subtle patina near the corners (lighter where fingers
have worn the leather), slight darkening along the spine. No cracks, no
tears, no buckle, no clasp. Page block at the right open edge: cream-to-buff
pages slightly fanned (~1–2 mm spread), thin red-and-blue ledger ruling
visible at the edge as faint colour bands. A dark fabric ribbon bookmark
(~3 mm wide, slightly frayed) emerges from between two pages near the
middle and trails ~8 cm off the right edge. Filmic desaturated palette,
warm mid-browns. Background: neutral mid-grey or pale wood-grain surface.
