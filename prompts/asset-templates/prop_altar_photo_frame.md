---
asset_name: prop_altar_photo_frame
category: prop
era_scope: shared
reference_image: prop_altar_photo_frame/ref.png
seed: 481113
inference_steps: 50
target_poly_lod0: 4000
materials_runtime:
  - mat_wood_weathered
  - mat_paper_aged    # photo-card slot
collision: convex_hull
notes: |
  Runtime owner: this mesh is the `familyRecords` anchor (Act 2 evidence
  M6b — see witness-interactive-vite/src/bootstrap/main.ts). In 1994 it
  stands upright on the altar; in 2026 it lies fallen, glass gone. The
  runtime composes the era state from the same source mesh (rotation +
  material variant), so the asset must look correct standing.
---

# Standing photograph frame, household altar piece

A simple rectangular wooden picture frame, sized to hold a small portrait
photograph. Overall dimensions ~0.42 m wide × 0.32 m tall × 4 cm thick at
the rim. A thin wooden moulding around the edge (~3 cm rim width). A
back-stand kicked out at an angle on the back face, so the frame can
stand upright without leaning on anything.

The frame holds a paper photograph (treated here as a flat inset panel,
not a separate asset). The photograph itself should be modelled as a
recessed plane ~32 cm × 22 cm inside the rim. The image content of the
photograph is **deliberately neutral** — a soft pale grey-buff rectangle
with the faint suggestion of a portrait composition (a single oval
indicating a face shape, no recognisable likeness). The runtime can swap
in a higher-fidelity texture later; the geometry just needs to read as
"there is a photograph here".

No glass plane in front of the photograph — in 1994 the glass is implied
but not modelled; in 2026 it would be missing.

Era variance: shared mesh. The 1994 pose has the frame upright on its
back-stand; the 2026 pose has the frame lying face-down on the altar slab.
Both use the same mesh; the runtime applies the rotation.

Materials: two PBR slots.
- `mat_wood_weathered` for the frame moulding (mid-brown, roughness ≈ 0.85).
- `mat_paper_aged` for the recessed photograph plane (pale grey-buff,
  roughness ≈ 0.95).

Geometry: a single mesh. LOD0 ~4000 tris.

Pivot: the centre of the bottom edge of the frame (so it stands cleanly
on the altar slab top face).

Lighting at bake: neutral overcast, 5000 K, no strong directional shadows.

## Style

Apply the [Digital Diorama style guide](_STYLE_GUIDE.md). Worn wooden
moulding, no varnish, the inset paper has age-yellowing at the edges.
Filmic desaturated palette.

## Reference image

`prompts/asset-templates/prop_altar_photo_frame/ref.png` should depict:

A simple rectangular wooden picture frame, ~42 cm × ~32 cm, standing upright
on its back-stand on a neutral matte surface. Photographed at eye level,
slightly angled (5–10°) so the back-stand kick-out is just visible. Frame
moulding ~3 cm rim, mid-brown weathered wood with light surface wear. No
glass plane in front. The photograph inside the frame must be **deliberately
neutral** — a soft pale grey-buff rectangle with at most the faint
suggestion of a portrait composition (a single oval shape indicating a
face, **no recognisable likeness, no real person, no skin detail**). The
photograph reads as faded paper rather than as a portrait. Filmic
desaturated palette. Background: neutral mid-grey or seamless.
